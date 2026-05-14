FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional: install Trivy for deeper image scanning
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
    | sh -s -- -b /usr/local/bin || echo "Trivy install skipped (offline)"

COPY scanner.py .
RUN pip install --no-cache-dir requests

CMD ["python", "scanner.py"]
