FROM python:3.12-slim
WORKDIR /repopilot
COPY requirements-evaluation.txt .
RUN pip install --no-cache-dir -r requirements-evaluation.txt
COPY app/ app/
COPY ingestion/ ingestion/
COPY evaluation/ evaluation/
COPY data/ data/
ENV PYTHONPATH=/repopilot/evaluation:/repopilot/app:/repopilot/ingestion
CMD ["python", "evaluation/run_evaluation.py"]
