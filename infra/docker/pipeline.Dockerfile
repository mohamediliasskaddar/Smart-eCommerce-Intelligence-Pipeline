FROM python:3.10-slim

WORKDIR /app

COPY requirements/pipeline.txt .
COPY .env.example .env

RUN pip install --no-cache-dir -r pipeline.txt

# Copy necessary directories and shared modules
COPY pipeline/ ./pipeline/
COPY storage.py .

# default run = full pipeline
CMD ["python", "pipeline/run_pipeline.py"]