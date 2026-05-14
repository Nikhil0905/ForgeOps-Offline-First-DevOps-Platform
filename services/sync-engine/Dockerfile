FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY sync.py .
RUN pip install --no-cache-dir requests

VOLUME ["/data"]
CMD ["python", "sync.py"]
