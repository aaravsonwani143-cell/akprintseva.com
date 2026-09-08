# AK Print Seva — High-Performance Cloud AI Microservice
# Lightweight, Free-Tier Compatible Container (Render / Hugging Face / Railway)
FROM python:3.11-slim

# Avoid prompts from debian
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install basic native libraries required by OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend engines (services) and cloud server
COPY services /app/services
COPY services/cloud-ai/server.py /app/server.py

# Expose standard cloud port
EXPOSE 8080

# Run microservice server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]
