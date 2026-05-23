# Worker image: Claude Agent SDK + Playwright + wkhtmltopdf + skills baked in.
#
# Base image already includes Chromium + Playwright deps, which saves ~5 min off
# the build vs installing them on top of python:3.11-slim.

FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

RUN apt-get update && apt-get install -y --no-install-recommends \
      wkhtmltopdf \
      ca-certificates \
      curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Skills baked in. title-abstract goes under .claude/skills/ so the Agent SDK
# auto-discovers it via setting_sources=["project"]. zitles-report-tools is a
# Python library invoked by the report-builder agent — kept on a known path.
COPY skills/title-abstract        /app/.claude/skills/title-abstract
COPY skills/zitles-report-tools   /app/skills/zitles-report-tools

COPY worker/run_skill.py /app/run_skill.py

ENV PYTHONUNBUFFERED=1 \
    SKILLS_ROOT=/app/.claude/skills \
    REPORT_TOOLS_ROOT=/app/skills/zitles-report-tools

ENTRYPOINT ["python", "/app/run_skill.py"]
