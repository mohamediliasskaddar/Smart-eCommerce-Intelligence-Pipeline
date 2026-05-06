FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/agents.txt .
COPY .env.example .env

RUN pip install --no-cache-dir -r agents.txt

COPY agents/ ./agents/
COPY storage.py .

CMD ["python", "agents/agent_coordinator.py"]