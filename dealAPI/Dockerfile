# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN --mount=type=secret,id=pip_config,dst=/etc/pip.conf pip install --no-cache-dir -r requirements.txt

# Copy project files
#COPY . .

# Expose port
EXPOSE 5000

# Start development server
CMD flask db upgrade && flask run --host=0.0.0.0
