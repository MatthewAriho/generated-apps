FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .

EXPOSE 8008

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8008", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "debug", "app:app"]
