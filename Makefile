IMAGE_TAG ?= zitles-skills-worker:dev
TMS       ?= 265-16-04-023
COUNTY    ?= Berkeley

# AWS POC
AWS_PROFILE  ?= serverless-admin-zitles
AWS_REGION   ?= us-east-1
ECR_REGISTRY ?= 442063206610.dkr.ecr.us-east-1.amazonaws.com
ECR_REPO     ?= zitles-skills-worker
ECR_TAG      ?= latest
CLUSTER      ?= zitles-skills
TASK_DEF     ?= zitles-skills-worker
SUBNETS      ?= subnet-0a2b9deaf74e2dff8,subnet-0a4f8a002a24da614,subnet-0b9bf1a9267ff895e
SECURITY_GRP ?= sg-0f971d482f104c133

.PHONY: build worker-shell worker-run worker-smoke ecr-login ecr-push fargate-smoke fargate-logs poc-deploy poc-destroy

build:
	docker build -f worker/Dockerfile -t $(IMAGE_TAG) .

# Open an interactive shell inside the worker image (for poking around).
worker-shell:
	docker run --rm -it \
	  -e ANTHROPIC_API_KEY=$$ANTHROPIC_API_KEY \
	  --entrypoint bash $(IMAGE_TAG)

# Run the worker against the default Berkeley TMS.
worker-run:
	docker run --rm -it \
	  -e ANTHROPIC_API_KEY=$$ANTHROPIC_API_KEY \
	  -e RUN_SKILL=title-abstract \
	  -e RUN_PROMPT="Run a complete title abstract for $(COUNTY) County, TMS $(TMS)." \
	  $(IMAGE_TAG)

# Smoke test: minimal prompt, just verify the SDK loads the skill.
worker-smoke:
	docker run --rm \
	  -e ANTHROPIC_API_KEY=$$ANTHROPIC_API_KEY \
	  -e RUN_PROMPT="List the skills you have available and stop." \
	  $(IMAGE_TAG)

# ─── AWS POC targets ────────────────────────────────────────────────────────

poc-deploy:
	aws --profile $(AWS_PROFILE) --region $(AWS_REGION) cloudformation deploy \
	  --stack-name ZitlesSkillsPocStack \
	  --template-file infra/poc.yaml \
	  --capabilities CAPABILITY_IAM \
	  --tags Project=zitles-skills-poc \
	  --no-fail-on-empty-changeset

poc-destroy:
	aws --profile $(AWS_PROFILE) --region $(AWS_REGION) cloudformation delete-stack \
	  --stack-name ZitlesSkillsPocStack
	@echo "Stack delete initiated. Tracking: aws cloudformation describe-stacks --stack-name ZitlesSkillsPocStack"

ecr-login:
	aws --profile $(AWS_PROFILE) --region $(AWS_REGION) ecr get-login-password | \
	  docker login --username AWS --password-stdin $(ECR_REGISTRY)

ecr-push: ecr-login
	docker tag $(IMAGE_TAG) $(ECR_REGISTRY)/$(ECR_REPO):$(ECR_TAG)
	docker push $(ECR_REGISTRY)/$(ECR_REPO):$(ECR_TAG)

# One-shot smoke test on Fargate. Returns the task ARN; use fargate-logs to follow.
fargate-smoke:
	@aws --profile $(AWS_PROFILE) --region $(AWS_REGION) ecs run-task \
	  --cluster $(CLUSTER) \
	  --task-definition $(TASK_DEF) \
	  --launch-type FARGATE \
	  --network-configuration "awsvpcConfiguration={subnets=[$(SUBNETS)],securityGroups=[$(SECURITY_GRP)],assignPublicIp=ENABLED}" \
	  --overrides '{"containerOverrides":[{"name":"worker","environment":[{"name":"RUN_PROMPT","value":"List your skills and stop. Do not use any tools."}]}]}' \
	  --query 'tasks[0].taskArn' --output text

# Tail logs for a given task ARN: make fargate-logs TASK=arn:...
fargate-logs:
	@TASK_ID=$$(echo $(TASK) | awk -F/ '{print $$NF}'); \
	aws --profile $(AWS_PROFILE) --region $(AWS_REGION) logs tail \
	  /aws/ecs/zitles-skills-worker \
	  --log-stream-names ecs/worker/$$TASK_ID \
	  --follow
