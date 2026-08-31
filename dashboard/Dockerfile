FROM python:3.12-slim
WORKDIR /repopilot
COPY requirements-dashboard.txt .
RUN pip install --no-cache-dir -r requirements-dashboard.txt
COPY dashboard/ dashboard/
COPY evaluation/ evaluation/
COPY reports/ reports/
ENV PYTHONPATH=/repopilot
EXPOSE 5050
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "dashboard.app:app"]
