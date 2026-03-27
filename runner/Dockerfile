FROM python:3.12-slim

WORKDIR /app

# git is required to install tvDatafeed from GitHub
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything the runner touches at runtime
COPY shared/          shared/
COPY api/             api/
COPY strategies/      strategies/
COPY impulse-notifier/ impulse-notifier/
COPY runner/          runner/

ENV PYTHONPATH=/app

# Health check exposed by runner/main.py
EXPOSE 8080

CMD ["python", "runner/main.py"]
