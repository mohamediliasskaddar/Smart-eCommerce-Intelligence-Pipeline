FROM python:3.10-slim

WORKDIR /app

# system deps (important for scraping tools)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/agents.txt .

RUN pip install --no-cache-dir -r agents.txt

# Copy necessary directories
COPY agents/ ./agents/

CMD ["python", "agents/agent_coordinator.py"]