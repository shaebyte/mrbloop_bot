FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Standaard: start de poller daemon
# Overschrijf CMD in docker-compose voor de API-service
CMD ["python", "run.py"]
