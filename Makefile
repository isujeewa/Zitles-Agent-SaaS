IMAGE_TAG ?= zitles-skills-worker:dev
TMS       ?= 265-16-04-023
COUNTY    ?= Berkeley

.PHONY: build worker-shell worker-run worker-smoke

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
