# Python slim imajını kullan
FROM python:3.10-slim

# Çalışma dizini oluştur
WORKDIR /app

# Gerekli dosyaları kopyala
COPY requirements.txt ./

# Sanic ve diğer bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Sanic uygulamasını başlat
CMD ["python", "main.py"]
