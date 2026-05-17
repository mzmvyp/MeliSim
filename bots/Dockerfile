FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir httpx==0.27.0 loguru==0.7.2

COPY traffic_bot.py /app/traffic_bot.py

CMD ["python", "-u", "/app/traffic_bot.py"]
