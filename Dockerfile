# Dockerfile for VaultFlow Backend
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Spacy model
RUN python -m spacy download fr_core_news_lg

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to run the application (inits DB then starts app)
CMD python database.py && python main.py
