FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY deploy.py .
RUN pip install --no-cache-dir requests

VOLUME ["/var/run/docker.sock"]

CMD ["python", "deploy.py"]
