FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: start the poller daemon
# Override CMD in docker-compose for the API service
CMD ["python", "run.py"]
