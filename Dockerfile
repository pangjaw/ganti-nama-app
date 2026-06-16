# Menggunakan mesin Python versi ringan
FROM python:3.9-slim

# Mengatur lokasi kerja di dalam kontainer
WORKDIR /app

# Menginstal Poppler dan Tesseract OCR versi Linux
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Menyalin daftar kebutuhan dan menginstalnya
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh file script dan template ke dalam kontainer
COPY . .

# Cloud Run menggunakan port dinamis via environment variable $PORT
ENV PORT=8501
EXPOSE 8501

# Jalankan Flask app menggunakan Gunicorn production server
CMD sh -c "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app"
