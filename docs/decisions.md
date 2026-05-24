# zitles-skills-platform — Architecture Decisions

**Date locked:** 2026-05-24
**Status:** Pre-implementation. Living document — revise as build progresses.

## Purpose

Multi-user hosted service for running internal Claude Skills (web-scraping pipelines) on AWS. v1 skills: `title-abstract` and `zitles-report-tools`. End users invoke skills via API and receive scraped output; skill source code stays inside the AWS account.

## Locked architecture

Single Fargate-only architecture. No Lambda anywhere.

```
User device                          AWS account 442063206610 (us-east-1)
─────────────────                    ──────────────────────────────────────
Browser (UI)        ───── HTTPS ──►  ALB ─► FastAPI tasks (Fargate)
                                                  │
zitles-agent daemon ── outbound WSS ► Tunnel coordinator (Fargate)
  - local SOCKS5                              ▲
  - captcha relay                             │ SOCKS5 (internal)
                                              │
                                     Worker task per job (Fargate)
                                       - Claude Agent SDK
                                       - Playwright + Chromium
                                       - wkhtmltopdf
                                       - Skills baked into image

API     → SQS → ECS RunTask spawns the worker
Worker  → writes phase checkpoints to DynamoDB
Worker  → writes blobs (PDFs, decisions.json, review.html) to S3
Egress  → workers route HTTPS through SOCKS5 → daemon → user's home ISP IP
```

## Stack

| Area | Choice |
|------|--------|
| AWS account | 442063206610 |
| Region | us-east-1 |
| Profile | `serverless-admin-zitles` |
| Compute | ECS Fargate for everything (API, worker, tunnel coordinator) |
| IaC | CDK in Python |
| API | FastAPI (Python) behind ALB |
| Worker | Python 3.11 + Claude Agent SDK + Playwright + wkhtmltopdf |
| Auth | Cognito User Pool `us-east-1_VrIJ4MP01` (develop pool, reused from zitles-api) |
| State | DynamoDB — tables: `jobs`, `job_events`, `daemon_sessions`, `pending_inputs` |
| Blobs | S3 bucket `zitles-skills-develop-jobs` |
| Skills | Baked into worker Docker image, stored in private ECR |
| Secrets | Secrets Manager for values; SSM `/zitles-agentic-platform/develop/*-secret-arn` holds the pointer |
| Tunnel | Single Fargate task; outbound WebSocket from daemon, exposes SOCKS5 to workers |
| Egress | Routed through user's residential IP via the daemon |

## Skills under management (v1)

- **title-abstract** — multi-agent SC title abstract pipeline. ~10–60 min per job. Uses Playwright, Google Vision OCR, Claude orchestration across 8 phases.
- **zitles-report-tools** — Python library invoked by `title-abstract`'s `report-builder` agent. Converts `decisions.json` to styled HTML/PDF.

Both live at `/Users/sujeewa/Documents/Zitles/Development/title-summary-reports-generator/zitles-agentic-platform/Skills/` today and will be copied into the worker image at build time.

## v1 policies (each is expandable later)

| Policy | v1 value | Path to expand |
|--------|----------|----------------|
| Concurrent jobs per user | 1 | Config var → flip to N |
| Daemon target OS | macOS | Add Windows + Linux |
| Daemon distribution | Internal Zitles team | External customers (needs signed installer, support) |
| No-daemon fallback | Fail-fast | Add `--unsafe-cloud-egress` flag (already in scope for demos) |
| Skill update flow | Rebuild image, push to ECR, redeploy | Hot reload from private S3 |
| Output retention | 30 days in S3 | Lifecycle to Glacier or extend |
| Environments | `develop` only | Add staging + production |
| Tunnel coordinator | Single Fargate task | Horizontal with consistent hashing on `user_id` |
| Anthropic API key | One shared key in Secrets Manager (ARN in SSM) | Per-org keys via Admin API |
| Orchestrator model | Sonnet 4.6 for orchestration; Haiku for OCR/extraction subagents | Pin per-skill or per-phase based on cost data |

## Conventions inherited from zitles-api

- Stages: local / develop / qa / staging / production
- **Secrets pattern:** real secret values live in AWS Secrets Manager; SSM under `/zitles-agentic-platform/<stage>/*-secret-arn` stores only the ARN pointer. Apps read the SSM pointer, then fetch the value. Example today: `/zitles-agentic-platform/develop/anthropic-secret-arn` → `arn:aws:secretsmanager:...:secret:zitles-agentic-platform/develop/anthropic-api-key-L1txwy`
- Cognito JWT validation, role + permission lookup
- Same AWS account, same region, same profile

## Conventions dropped from zitles-api

- Serverless Framework (we use CDK)
- Lambda handlers (we use FastAPI on Fargate)
- MongoDB Atlas (we use DynamoDB + S3)
- `mongodbMigrateUp` Lambda (DynamoDB is schemaless)

## Repo layout

Monorepo (single repo, location TBD):

```
zitles-skills-platform/
  api/         FastAPI service (Docker)
  worker/      Job worker container (Docker)
  daemon/      zitles-agent (macOS app)
  infra/       CDK stacks (api, worker, tunnel, data)
  skills/      Copy or git submodule of title-abstract + zitles-report-tools
  README.md
```

## Assumptions absorbed (revisit during build, not blocking)

- **Daemon auth:** one-time token paste from web UI into daemon config; daemon then holds long-lived JWT, refreshable via API.
- **Worker death recovery:** requeue from last phase checkpoint, max 3 retries, then dead-letter to a `failed_jobs` record for manual review.
- **Job IDs are UUIDs**, not sequential.
- **Every DynamoDB write includes `user_id` and `org_id`** from day one, even though only one user matters in v1.
- **API is stateless.** No in-memory sessions, no caches.
- **Daemon protocol carries `job_id` on every frame** — enables multi-job multiplexing later without a protocol break.
- **Captcha handling lives in the daemon** (local browser popup, cookie injection back into tunnel). Not routed through cloud.
- **Semantic user input** (disambiguation, decisions) handled via DynamoDB `pending_inputs` + WebSocket push to UI.

## Threat model

- **Skill source hidden from app users.** End users only see API responses. Internal Zitles team has ECR pull access — acceptable.
- **Daemon failure is loud, not silent.** Job fails fast with a clear error; user knows immediately.
- **Single Anthropic key in v1.** Per-user/per-org cost attribution is via job metadata, not separate keys.
- **No proxy provider fallback in v1.** Paid residential proxies were tested and failed; daemon is the only egress path.

## Build order — thin slice first

1. Dockerize worker with skills baked in. Run one TMS (Berkeley 265-16-04-023) end-to-end inside the container locally.
2. Validate egress: route container traffic through `chisel` from laptop, confirm county portal sees home IP.
3. Push container to private ECR. Run as a Fargate task manually (no API, no queue yet).
4. Add API + DynamoDB + SQS + ECS RunTask trigger. Real product surface.
5. Replace `chisel` with the custom `zitles-agent` daemon.

Step 5 is last, not first — every earlier step works without it.

## Explicitly NOT in v1 scope

- Production environment
- Per-org cost tracking dashboard
- Per-user Anthropic API keys
- Web UI polish (curl-driven during thin slice)
- Daemon auto-update
- Windows / Linux daemon builds
- Multi-skill orchestration in a single job (one skill per job)
- Marketplace / external customer onboarding
- Paid residential proxy fallback

## Open questions to resolve before coding step 1

- Repo location and naming (under `/Users/sujeewa/Documents/Zitles/Development/`?)
- DNS subdomain for develop API (`skills-api-develop.zitles.com`?) — depends on Route53 zone owner
- Whether `skills/` is a copy or a git submodule of the existing skills directory
