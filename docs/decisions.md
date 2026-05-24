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

## Tunnel coordinator design (production)

The tunnel coordinator is the single most security-sensitive component. Its job: route a Fargate worker's HTTPS traffic out through the *correct* user's home IP, and refuse to do so for anyone else.

### Routing mechanism: SOCKS5 username = signed job egress token

One SOCKS5 listener (port 1080) on the coordinator. Worker authenticates each SOCKS5 connection with a per-job token (RFC 1929 username/password auth). The token is the routing target.

```
Worker:    HTTPS_PROXY=socks5h://coordinator.internal:1080
           SOCKS5 auth: username=<job_egress_token>

Token shape (HMAC-signed, ~44 char base64):
  { "job_id", "user_id", "org_id", "allowed_hosts": [...], "exp" }

Coordinator on CONNECT:
  1. Verify token signature (key from Secrets Manager, rotated weekly)
  2. Extract user_id
  3. Lookup DynamoDB daemon_sessions[user_id] → connection_id
  4. Verify daemon WebSocket is alive (heartbeat within 30s)
  5. Check destination host is in token.allowed_hosts
  6. Forward TCP bytes through that user's WebSocket

Daemon on receiving forwarded bytes:
  7. Check destination host against its LOCAL allowlist (defense-in-depth)
  8. Open socket on user's home network
  9. Stream bytes back through WebSocket
```

### Why not per-user ports / per-user hostnames

Token-based auth scales to any user count with one listener. Per-user ports run out of port space and bloat security groups. Per-user hostnames add DNS + TLS cert management for no real gain.

### Daemon-side connection

```
Daemon → wss://coordinator.zitles.com/v1/daemon?token=<cognito JWT>
Coordinator validates JWT, writes daemon_sessions row:
  { user_id, connection_id, coordinator_task_id, last_seen }
Heartbeat every 30s. Row TTL = 90s. Coordinator clears the row on close.
```

### Failure modes are explicit

| When | Result |
|------|--------|
| Daemon offline at SOCKS5 CONNECT | Reply 0x04 (host unreachable, reason `daemon_offline`); worker writes `job.status="paused: awaiting daemon"`; user sees "Reconnect zitles-agent" in UI. |
| Token expired | SOCKS5 reply 0x02 (rule blocked); worker fetches new token from API. |
| Destination not in `allowed_hosts` | SOCKS5 reply 0x02; logged as audit event. |
| Daemon's local allowlist refuses | Connection drops; worker logs proxy error. |

**Workers never silently route through a different path.** If the user's daemon isn't there, the job stops.

### Scaling

- v1: single coordinator Fargate task. Handles ~5,000 concurrent WebSockets.
- v2: multi-task behind an NLB. DynamoDB `daemon_sessions` tells which task owns which user. Cross-task routing OR sticky LB on the daemon WS handshake.

### `chisel` is NOT the production tunnel

`chisel` is the POC scaffold only. It has no multi-tenant auth, no per-user allowlist, no per-request audit. **Production replaces it with the custom coordinator above** — ~2–3 dev weeks of work, included in v1 scope.

### Captcha handling — REVISED 2026-05-24

**Earlier decision (replaced):** "Captcha handling lives in the daemon (local browser popup)."

**Current decision:** **Captcha screenshots/iframes surface via the API + WebSocket push to the user's web UI.** User solves the captcha in their normal browser tab; the token/cookies flow back to the worker's Playwright session.

Why the change:
- Keeps the daemon as a pure SOCKS5 forwarder (no GUI, no browser dependency, no cookie-injection plumbing).
- Reuses the same `pending_inputs` / WebSocket-push pipeline we already need for semantic prompts ("which John Smith?").
- Worker's Playwright session stays the authoritative HTTP client; cookies remain in its TLS context.
- Daemon-side captcha may still be needed for sites with sophisticated browser-fingerprint detection — that's a v2 concern, not v1.

## Assumptions absorbed (revisit during build, not blocking)

- **Daemon auth:** one-time token paste from web UI into daemon config; daemon then holds long-lived Cognito JWT, refreshable via API.
- **Worker death recovery:** requeue from last phase checkpoint, max 3 retries, then dead-letter to a `failed_jobs` record for manual review.
- **Job IDs are UUIDs**, not sequential.
- **Every DynamoDB write includes `user_id` and `org_id`** from day one, even though only one user matters in v1.
- **API is stateless.** No in-memory sessions, no caches.
- **Semantic user input** (disambiguation, decisions, captcha responses) handled via DynamoDB `pending_inputs` + WebSocket push to UI.

## Threat model

- **Skill source hidden from app users.** End users only see API responses. Internal Zitles team has ECR pull access — acceptable.
- **Daemon failure is loud, not silent.** Job fails fast with a clear error; user knows immediately.
- **Single Anthropic key in v1.** Per-user/per-org cost attribution is via job metadata, not separate keys.
- **No proxy provider fallback in v1.** Paid residential proxies were tested and failed; daemon is the only egress path.

## Build order — thin slice first

1. Dockerize worker with skills baked in. Run one TMS (Berkeley 265-16-04-023) end-to-end inside the container locally.
2. Validate egress mechanics: route container traffic through `chisel` from laptop, confirm county portal sees home IP. (POC scaffolding only — see "Tunnel coordinator design" above; `chisel` is not the production tunnel.)
3. Push container to private ECR. Run as a Fargate task manually (no API, no queue yet).
4. Add API + DynamoDB + SQS + ECS RunTask trigger. Real product surface.
5. Build the production tunnel coordinator (FastAPI + WebSocket + SOCKS5 + token validation) and the `zitles-agent` daemon. `chisel` is retired at this point.

Step 5 is last, not first — every earlier step works without it.

## Security baseline for v1 (must ship)

Even for internal-only v1, these are required so the daemon doesn't look like spyware to a competent IT reviewer:

- **Dual-layer domain allowlist.** (1) Coordinator validates each SOCKS5 CONNECT against the `allowed_hosts` field in the per-job token. (2) Daemon also validates against its own server-supplied allowlist. Both must pass. Defense-in-depth: if the coordinator is compromised, the daemon still refuses unknown destinations.
- **Active-only tunneling.** Daemon forwards traffic only while a job is actively running. Idle = no tunnel.
- **Local audit log.** Rolling log on the user's machine: "proxied X requests to {domain} during job {job_id}." User-inspectable, IT-collectable.
- **Cloud audit trail.** Every job: who started it, what skill, what TMS, what egress, how many tokens, when it ended. CloudWatch + Athena over DynamoDB export.
- **Kill switch.** User can disconnect the daemon at any time; running jobs fail with `error: tunnel_disconnected`.
- **Encryption everywhere.** S3 + KMS, DynamoDB native encryption, TLS in transit. Already free with the chosen stack.

## Deferred to v2 (external customers / compliance)

- Code signing (Apple Developer + Windows EV cert) — ~$600/yr + ~1 week wiring
- Auto-update with signature verification (Sparkle or similar)
- SOC 2 Type II audit — ~$30–80k + 6–12 months
- Penetration test — ~$15–30k
- Vendor security questionnaire pre-fill (CAIQ, SIG)
- DPA / SCC templates for GDPR-adjacent customers
- BYOK for KMS

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
