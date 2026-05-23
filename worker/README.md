# worker

Job worker container. One Fargate task per job, ephemeral (~10–60 min).

Contents:
- Python 3.11
- Claude Agent SDK
- Playwright + Chromium
- wkhtmltopdf
- Skills baked in from `../skills/`

Lifecycle:
1. Spawned by ECS RunTask in response to an SQS message
2. Reads job from DynamoDB
3. Sets `HTTPS_PROXY` to the tunnel coordinator's per-user SOCKS5 endpoint
4. Loads the named skill via Agent SDK and runs it
5. Writes phase checkpoints to DynamoDB, blobs to S3
6. Exits when done

Demo flag: `--unsafe-cloud-egress` skips the tunnel (cloud IP, captcha risk) — for stakeholder demos only.

Not implemented yet — placeholder.
