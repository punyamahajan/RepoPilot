FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY codeimpact/frontend/package*.json ./
RUN npm ci
COPY codeimpact/frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /repopilot
COPY codeimpact/requirements.txt /tmp/codeimpact-requirements.txt
RUN pip install --no-cache-dir -r /tmp/codeimpact-requirements.txt
COPY codeimpact/ codeimpact/
COPY --from=frontend /frontend/dist /repopilot/codeimpact/frontend/dist
ENV CODEIMPACT_REPO_ROOT=/workspace CODEIMPACT_STATE_DIR=/state ANONYMIZED_TELEMETRY=False
EXPOSE 5070
CMD ["uvicorn", "codeimpact.api:app", "--host", "0.0.0.0", "--port", "5070", "--workers", "1"]
