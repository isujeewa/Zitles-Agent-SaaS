"""Worker entry point.

Loads a named skill via the Claude Agent SDK and runs it against a user prompt.

v1 (thin slice) — env-var driven, prints messages to stdout. Phase 4 replaces
stdout with DynamoDB checkpoints + S3 writes.

Env:
  ANTHROPIC_API_KEY  required
  RUN_SKILL          defaults to "title-abstract"
  RUN_PROMPT         defaults to a Berkeley County test TMS
"""
import asyncio
import os
import sys

from claude_agent_sdk import ClaudeAgentOptions, query


DEFAULT_PROMPT = (
    "Run a complete title abstract for Berkeley County, "
    "TMS 265-16-04-023. Use the title-abstract skill."
)


async def run() -> None:
    skill = os.environ.get("RUN_SKILL", "title-abstract")
    prompt = os.environ.get("RUN_PROMPT") or (
        sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[worker] ANTHROPIC_API_KEY not set — aborting", file=sys.stderr)
        sys.exit(2)

    options = ClaudeAgentOptions(
        cwd="/app",
        setting_sources=["project"],
    )

    print(f"[worker] skill={skill}", flush=True)
    print(f"[worker] prompt={prompt!r}", flush=True)
    print(f"[worker] cwd=/app  skills={os.environ.get('SKILLS_ROOT')}", flush=True)

    async for message in query(prompt=prompt, options=options):
        print(message, flush=True)


if __name__ == "__main__":
    asyncio.run(run())
