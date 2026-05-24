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

## Local egress test with chisel (stand-in for the daemon)

Until the real `zitles-agent` daemon ships, use `chisel` as a SOCKS5 tunnel
that proxies the worker's HTTPS traffic through the Mac's network. This is
how step 2 of the build order is validated.

```bash
# install once
brew install jpillora/tap/chisel || \
  curl -sLo /tmp/chisel.gz https://github.com/jpillora/chisel/releases/latest/download/chisel_$(uname -s)_$(uname -m).gz && \
  gunzip -f /tmp/chisel.gz && chmod +x /tmp/chisel && mv /tmp/chisel ~/.local/bin/chisel

# terminal 1 — "cloud coordinator"
chisel server --port 8080 --reverse

# terminal 2 — "user daemon" exposing reverse SOCKS5 on the server side
chisel client http://localhost:8080 R:1080:socks

# terminal 3 — run the worker through the tunnel
docker run --rm \
  -e HTTPS_PROXY=socks5h://host.docker.internal:1080 \
  -e HTTP_PROXY=socks5h://host.docker.internal:1080 \
  -e ANTHROPIC_API_KEY \
  zitles-skills-worker:dev
```

### Gotcha: SOCKS5 in Python

`urllib.request` does **not** honor `socks5h://` in `HTTPS_PROXY` — it tries
to do an HTTP CONNECT and the SOCKS5 server hangs up. Skills that hit the
internet directly (not via Playwright) must use a SOCKS-aware client:

- `httpx[socks]`
- `requests` + `PySocks` (`requests[socks]`)
- `curl` (already in the image)

Playwright's own proxy support takes `socks5://host:port` directly via
`page.goto(..., proxy={...})` or the browser launch args — no env-var
gymnastics needed.

### Out-of-scope for the proxy

The Anthropic API call from the Agent SDK should **not** route through the
tunnel — it'd waste user bandwidth and add latency to every model turn.
Production worker will set `NO_PROXY=api.anthropic.com,bedrock-runtime.*`
or scope the proxy per-tool.
