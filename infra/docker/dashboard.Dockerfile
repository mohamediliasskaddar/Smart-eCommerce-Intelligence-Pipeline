FROM python:3.10-slim

WORKDIR /app

# install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy necessary directories: dashboard, llm modules, and data
COPY dashboard/ ./dashboard/
COPY llm/ ./llm/
COPY data/ ./data/
COPY agents/ ./agents/

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]