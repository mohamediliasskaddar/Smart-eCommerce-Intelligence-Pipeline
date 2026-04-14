FROM python:3.10-slim

WORKDIR /app

# system deps (important for scraping tools)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary directories
COPY agents/ ./agents/
COPY llm/ ./llm/
COPY data/ ./data/
COPY pipeline/ ./pipeline/

CMD ["python", "agents/agent_coordinator.py"]