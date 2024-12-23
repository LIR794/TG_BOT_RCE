FROM python:3.12-slim

ENV TZ="Europe/Moscow"

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y \
    git \
    nano \
    libpq-dev \
    python3-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]
