FROM python:3.12-slim
WORKDIR /repopilot
COPY requirements-dashboard.txt .
COPY codeimpact/requirements.txt codeimpact-requirements.txt
RUN pip install --no-cache-dir -r requirements-dashboard.txt -r codeimpact-requirements.txt
COPY dashboard/ dashboard/
COPY codeimpact/ codeimpact/
COPY evaluation/ evaluation/
COPY reports/ reports/
ENV PYTHONPATH=/repopilot
EXPOSE 5050
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "--threads", "4", "--timeout", "600", "dashboard.app:app"]
