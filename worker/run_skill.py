"""Worker entry point.

Loads a named skill via the Claude Agent SDK and runs it against a user prompt.
Writes a transcript + any skill-produced files under /work/{job_id}/, then (if
OUTPUT_S3_BUCKET is set) uploads the whole directory to s3://bucket/jobs/{job_id}/.

Env:
  ANTHROPIC_API_KEY   required
  RUN_SKILL           defaults to "title-abstract"
  RUN_PROMPT          defaults to a Berkeley County test TMS
  ORCH_MODEL          orchestrator model id; default claude-sonnet-4-6
  JOB_ID              auto-generated if not set
  OUTPUT_S3_BUCKET    if set, output dir is synced here at exit
  AWS_REGION          required if OUTPUT_S3_BUCKET is set
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query


DEFAULT_PROMPT = (
    "Run a complete title abstract for Berkeley County, "
    "TMS 265-16-04-023. Use the title-abstract skill."
)

# Sonnet 4.6 for orchestration. Opus 4.7 was 3× the cost for the same skill init
# in our smoke test (~$0.12 vs ~$0.04 projected) and orchestration doesn't need
# Opus reasoning. Haiku is too weak for multi-agent coordination.
DEFAULT_MODEL = "claude-sonnet-4-6"


def _new_job_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"job-{ts}-{uuid.uuid4().hex[:8]}"


JOB_ID = os.environ.get("JOB_ID") or _new_job_id()
OUTPUT_DIR = Path("/work") / JOB_ID
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


async def run() -> dict:
    skill = os.environ.get("RUN_SKILL", "title-abstract")
    prompt = os.environ.get("RUN_PROMPT") or (
        sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    )
    model = os.environ.get("ORCH_MODEL", DEFAULT_MODEL)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[worker] ANTHROPIC_API_KEY not set — aborting", file=sys.stderr)
        sys.exit(2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    options = ClaudeAgentOptions(
        cwd="/app",
        setting_sources=["project"],
        model=model,
        # No human to approve tool calls in a container; default permission mode
        # blocks every WebFetch/Bash/Write call. Server-side workers must bypass.
        # Safety comes from: (1) image only contains our skills, (2) network
        # egress goes through allowlisted SOCKS5 in v1, (3) task IAM is scoped
        # to only the resources we explicitly grant.
        permission_mode="bypassPermissions",
    )

    print(f"[worker] job_id={JOB_ID}", flush=True)
    print(f"[worker] output_dir={OUTPUT_DIR}", flush=True)
    print(f"[worker] skill={skill}  model={model}", flush=True)
    print(f"[worker] prompt={prompt!r}", flush=True)

    summary: dict = {
        "job_id": JOB_ID,
        "skill": skill,
        "model": model,
        "prompt": prompt,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None,
    }

    try:
        with TRANSCRIPT_PATH.open("w") as f:
            async for message in query(prompt=prompt, options=options):
                print(message, flush=True)
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "type": type(message).__name__,
                    "repr": repr(message),
                }) + "\n")
                # Capture the final ResultMessage for the summary
                if type(message).__name__ == "ResultMessage":
                    summary["result"] = {
                        "subtype": getattr(message, "subtype", None),
                        "is_error": getattr(message, "is_error", None),
                        "stop_reason": getattr(message, "stop_reason", None),
                        "duration_ms": getattr(message, "duration_ms", None),
                        "total_cost_usd": getattr(message, "total_cost_usd", None),
                        "text": getattr(message, "result", None),
                    }
    except Exception as e:
        summary["error"] = f"{type(e).__name__}: {e}"
        print(f"[worker] ERROR: {summary['error']}", file=sys.stderr, flush=True)
    finally:
        summary["ended_at"] = datetime.now(timezone.utc).isoformat()
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2))

    return summary


def _upload_to_s3(summary: dict) -> None:
    bucket = os.environ.get("OUTPUT_S3_BUCKET")
    if not bucket:
        print(f"[worker] OUTPUT_S3_BUCKET not set; output stays at {OUTPUT_DIR}", flush=True)
        return

    import boto3  # local import — only needed for upload path
    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    prefix = f"jobs/{JOB_ID}/"
    count = 0
    for p in OUTPUT_DIR.rglob("*"):
        if not p.is_file():
            continue
        key = prefix + str(p.relative_to(OUTPUT_DIR))
        s3.upload_file(str(p), bucket, key)
        count += 1
    print(
        f"[worker] uploaded {count} file(s) → s3://{bucket}/{prefix}",
        flush=True,
    )
    summary["s3_uri"] = f"s3://{bucket}/{prefix}"


if __name__ == "__main__":
    summary = asyncio.run(run())
    _upload_to_s3(summary)
    # Final breadcrumb for CloudWatch readers
    print(f"[worker] done. job_id={JOB_ID}", flush=True)
    sys.exit(1 if summary.get("error") else 0)
