FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY chatbot_attack_simulator.py .

# Run as non-root user
RUN useradd -m -u 1000 simulator && \
    chown -R simulator:simulator /app
USER simulator

# Run the simulator
CMD ["python", "-u", "chatbot_attack_simulator.py"]





