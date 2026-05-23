# worker

Job worker container. One Fargate task per job, ephemeral (~10–60 min).

Contents:
- Python 3.10 (from `mcr.microsoft.com/playwright/python`)
- Claude Agent SDK
- Playwright + Chromium (in base image)
- wkhtmltopdf
- Skills baked into `/app/.claude/skills/` and `/app/skills/`

## Run locally (step 1 of the build order)

From the repo root:

```bash
# 1. Build the image
make build

# 2. Smoke test — verifies the SDK starts and discovers the skill
export ANTHROPIC_API_KEY=sk-ant-...
make worker-smoke

# 3. Real run — kicks off title-abstract for Berkeley TMS 265-16-04-023
make worker-run
```

Override target:
```bash
make worker-run COUNTY=Dorchester TMS=123-45-67-890
```

## Lifecycle (production shape — not yet implemented)

1. Spawned by ECS RunTask in response to an SQS message
2. Reads job from DynamoDB
3. Sets `HTTPS_PROXY` to the tunnel coordinator's per-user SOCKS5 endpoint
4. Loads the named skill via Agent SDK and runs it
5. Writes phase checkpoints to DynamoDB, blobs to S3
6. Exits when done

## Demo / debug flag

`--unsafe-cloud-egress` (not yet wired) will skip the tunnel and use the
container's own IP for egress. Captcha risk; demo-only.
