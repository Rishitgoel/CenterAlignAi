# CentrAlign AI - Autonomous AI Task Worker Production Container
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies for Playwright Chromium headless automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries
RUN playwright install chromium

# Copy application source code
COPY . .

# Create logs directory
RUN mkdir -p logs/suspended_tasks logs/jobs

EXPOSE 8000

# Default command launches FastAPI Mock ERP + Web Portal dynamically on Render's PORT
CMD ["sh", "-c", "uvicorn mock_erp.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
