# Sanic tabanlı Python uygulaması için Dockerfile
FROM python:3.11-slim

# Çalışma dizini ayarla
WORKDIR /app

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulamayı kopyala
COPY . /app/

# Sanic uygulamasını çalıştır
ENTRYPOINT ["python", "/app/main.py"]
