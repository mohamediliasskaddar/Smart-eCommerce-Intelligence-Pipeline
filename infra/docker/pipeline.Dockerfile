FROM python:3.10-slim

WORKDIR /app

COPY requirements/pipeline.txt .

RUN pip install --no-cache-dir -r requirements/pipeline.txt

# Copy necessary directories
COPY pipeline/ ./pipeline/

# default run = full pipeline
CMD ["python", "pipeline/run_pipeline.py"]