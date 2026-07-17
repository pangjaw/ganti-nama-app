@echo off
echo ===================================================
echo 🚀 MEMULAI PROSES UPDATE SINTELIS UTILITY
echo ===================================================


echo.
echo [1/4] Merakit ulang Docker Image...
docker build -t asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest .

echo.
echo [2/4] Mengunggah ke Google Cloud Registry...
docker push asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest

echo.
echo [3/4] Menerbangkan ke Google Cloud Run...
call gcloud run deploy sintelis-utility --image asia-southeast2-docker.pkg.dev/ganti-nama-file/sintelis-repo/sintelis-utility:latest --region asia-southeast2 --allow-unauthenticated --memory 1Gi --timeout 900 --concurrency 10

echo.
echo [4/4] Memulai Hosting Firebase...
call firebase deploy --only hosting --project ganti-nama-file

echo.
echo ===================================================
echo 🎉 PROSES SELESAI! SINTELIS SUDAH TER-UPDATE!
echo Silakan lakukan Hard Refresh (Ctrl+F5) di browser.
echo ===================================================
pause
