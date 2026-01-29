# Attack Simulator for Datadog AAP Testing
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    nmap \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir requests

# Copy attack scripts
COPY attack_simulator.py /app/
COPY zgrab_scan.sh /app/

# Make scripts executable
RUN chmod +x /app/attack_simulator.py /app/zgrab_scan.sh

CMD ["python", "/app/attack_simulator.py"]

