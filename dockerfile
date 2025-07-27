FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH so `src` is on the path
ENV PYTHONPATH="/app/src"

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run uvicorn and celery together
CMD uvicorn src.main:app --host 0.0.0.0 --port 8000 & celery -A src.celery_app worker --loglevel=info --concurrency=2 && wait
