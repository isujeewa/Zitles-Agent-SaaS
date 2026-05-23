# api

FastAPI service. Accepts job requests, returns status, streams progress.

Routes (v1):
- `POST /api/v1/jobs` — submit a job
- `GET /api/v1/jobs/:id` — read status + progress
- `POST /api/v1/jobs/:id/input` — answer a pending input prompt
- `WS  /api/v1/jobs/:id/stream` — live progress events

Auth: Cognito JWT (develop pool `us-east-1_VrIJ4MP01`).

Runs as a long-lived Fargate task behind an ALB. No Lambda.

Not implemented yet — placeholder.
