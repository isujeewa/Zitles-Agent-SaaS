# Zitles-Agent-SaaS

Multi-user hosted service for running internal Claude Skills as a managed API. Skill source code stays inside the AWS account; end users invoke skills via REST and receive output.

## Status

Pre-implementation. See [docs/decisions.md](docs/decisions.md) for the locked architecture and the v1 build order.

## Layout

```
api/       FastAPI service (Docker) — accepts jobs, returns status
worker/    Job worker container — runs the Claude Agent SDK + Playwright
daemon/    zitles-agent — installs on user machines, proxies scraping traffic via residential IP
infra/     CDK stacks
skills/    Bundled skills (title-abstract, zitles-report-tools)
docs/      Architecture and ops docs
```

## Quick context

- **AWS account:** 442063206610 (us-east-1), profile `serverless-admin-zitles`
- **Stack:** Fargate everywhere (no Lambda), DynamoDB + S3, Cognito for auth
- **Why a daemon:** county recorder portals captcha cloud IPs; user-machine egress fixes it
- **v1 policy:** internal users only, macOS daemon only, 1 concurrent job per user

Full reasoning, threat model, and assumptions in [docs/decisions.md](docs/decisions.md).
