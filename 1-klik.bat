@echo off
echo ===================================================
echo 🚀 MEMULAI PROSES UPDATE SINTELIS UTILITY
echo ===================================================

echo.
echo [1/5] Menarik update terbaru dari GitHub...
git pull origin main

echo.
echo [2/5] Merakit ulang Docker Image...
docker build -t asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest .

echo.
echo [3/5] Mengunggah ke Google Cloud Registry...
docker push asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest

echo.
echo [4/5] Menerbangkan ke Google Cloud Run...
call gcloud run deploy sintelis-utility --image asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest --region asia-southeast2 --allow-unauthenticated

echo.
echo [5/5] Memulai Hosting Firebase...
call firebase deploy --only hosting

echo.
echo ===================================================
echo 🎉 PROSES SELESAI! SINTELIS SUDAH TER-UPDATE!
echo Silakan lakukan Hard Refresh (Ctrl+F5) di browser.
echo ===================================================
pause