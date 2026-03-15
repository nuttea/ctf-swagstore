FROM python:3.10-slim

WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションをコピー
COPY chatbot_attack_simulator.py .

# 非rootユーザーで実行
RUN useradd -m -u 1000 simulator && \
    chown -R simulator:simulator /app
USER simulator

# シミュレーターを実行
CMD ["python", "-u", "chatbot_attack_simulator.py"]





