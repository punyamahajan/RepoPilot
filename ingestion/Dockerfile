FROM python:3.12-slim

WORKDIR /repopilot
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ingestion/ ingestion/
COPY data/ data/

EXPOSE 5001
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--chdir", "ingestion", "ingestion_service:app"]
