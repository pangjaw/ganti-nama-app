<<<<<<< HEAD
# Menggunakan mesin Python versi ringan
FROM python:3.9-slim

# Mengatur lokasi kerja di dalam kontainer
WORKDIR /app

# Menginstal Poppler dan Tesseract OCR versi Linux (otomatis tanpa klik Next/Finish)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Menyalin daftar kebutuhan dan menginstalnya
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh file script dan animasi ke dalam kontainer
COPY . .

# Membuka pintu 8501
EXPOSE 8501

# Perintah otomatis saat kontainer menyala
=======
# Menggunakan mesin Python versi ringan
FROM python:3.9-slim

# Mengatur lokasi kerja di dalam kontainer
WORKDIR /app

# Menginstal Poppler dan Tesseract OCR versi Linux (otomatis tanpa klik Next/Finish)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Menyalin daftar kebutuhan dan menginstalnya
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh file script dan animasi ke dalam kontainer
COPY . .

# Membuka pintu 8501
EXPOSE 8501

# Perintah otomatis saat kontainer menyala
>>>>>>> 5bd528b57b8940ab566c871e3f902783fe0f895b
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.headless", "true"]