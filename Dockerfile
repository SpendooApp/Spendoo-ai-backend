# Dockerfile for Spendoo-ai-backend
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port for FastAPI (default: 8000)
EXPOSE 8000

# Start FastAPI app with uvicorn
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
