FROM python:3.10-slim

WORKDIR /app

# install deps
COPY requirements/dashboard.txt .
COPY .env.example .env

RUN pip install --no-cache-dir -r dashboard.txt

# Copy necessary directories and shared modules
COPY dashboard/ ./dashboard/
COPY llm/ ./llm/
COPY storage.py .

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]