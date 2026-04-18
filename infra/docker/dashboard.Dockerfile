FROM python:3.10-slim

WORKDIR /app

# install deps
COPY requirements/dashboard.txt .
RUN pip install --no-cache-dir -r dashboard.txt

# Copy necessary directories: dashboard and llm modules
COPY dashboard/ ./dashboard/
COPY llm/ ./llm/

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]