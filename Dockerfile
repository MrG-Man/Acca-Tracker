# Football Predictions App Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Create necessary directories
RUN mkdir -p logs data/backups static/uploads

# Expose port
EXPOSE 5000

# Health check - FIXED VERSION
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; \
    import sys; \
    response = requests.get('http://localhost:5000/health', timeout=5); \
    sys.exit(0 if response.status_code == 200 else 1)"

# Start command
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
