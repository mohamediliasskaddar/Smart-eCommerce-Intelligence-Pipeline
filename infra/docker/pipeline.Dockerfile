FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary directories
COPY pipeline/ ./pipeline/
COPY data/ ./data/
COPY llm/ ./llm/
COPY agents/ ./agents/

# default run = full pipeline
CMD ["python", "pipeline/run_pipeline.py"]