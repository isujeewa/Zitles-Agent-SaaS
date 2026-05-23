# infra

CDK (Python) stacks for the platform. Deployed to AWS account 442063206610 with profile `serverless-admin-zitles`.

Planned stacks:
- `data-stack` — DynamoDB tables, S3 buckets, SSM params
- `api-stack` — ECR repo + Fargate service + ALB for the API
- `worker-stack` — ECR repo + ECS task definition (RunTask invoked from API)
- `tunnel-stack` — Fargate service + ALB for the tunnel coordinator
- `queue-stack` — SQS queues + dead-letter queue
- `iam-stack` — task roles, execution roles, KMS keys

Not implemented yet — placeholder.
