FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements/pipeline.txt .
COPY .env.example .env

RUN pip install --no-cache-dir -r pipeline.txt

COPY pipeline/ ./pipeline/
COPY storage.py .

CMD ["python", "pipeline/run_pipeline.py"]