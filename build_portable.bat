@echo off
chcp 65001 >nul
title Build Sintelis Utility Portable

echo ============================================
echo  Building Sintelis Utility Portable
echo ============================================
echo.

REM Cek Tesseract OCR
set TESS_DIR=tesseract
if not exist "%TESS_DIR%\tesseract.exe" (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo [COPY] Menyalin Tesseract dari system...
        mkdir "%TESS_DIR%" 2>nul
        xcopy /E /I /Y "C:\Program Files\Tesseract-OCR" "%TESS_DIR%" >nul
    ) else (
        echo [ERROR] Tesseract tidak ditemukan!
        echo  Install dulu: https://github.com/UB-Mannheim/tesseract/wiki
        pause
        exit /b 1
    )
)

REM Cek tessdata bahasa Indonesia
if not exist "%TESS_DIR%\tessdata\ind.traineddata" (
    echo [WARN] Bahasa Indonesia tidak ditemukan di Tesseract.
    echo  Mengcopy dari system...
    if exist "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata" (
        copy "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata" "%TESS_DIR%\tessdata\" >nul
    )
)
echo.

REM Siapkan argumen add-data
set ADD_DATA=--add-data "app.py;." --add-data "templates;templates" --add-data "%TESS_DIR%;tesseract"

REM Poppler optional — hanya tambah jika ada
if exist "poppler\pdftoppm.exe" (
    echo [INFO] Poppler ditemukan, akan dibundle.
    set ADD_DATA=%ADD_DATA% --add-data "poppler;poppler"
) else (
    echo [INFO] Poppler tidak ditemukan (tidak dibundle).
    echo  Pastikan poppler terinstall di system atau PDF gagal diproses.
)

echo.
echo [BUILD] Mulai build dengan PyInstaller...
python -m PyInstaller --onefile --windowed ^
    %ADD_DATA% ^
    --hidden-import "pytesseract" ^
    --hidden-import "pdf2image" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --collect-all "customtkinter" ^
    --name "Sintelis Utility" ^
    portable_ui.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================
    echo  BUILD SUKSES!
    echo  File: dist\Sintelis Utility.exe
    echo ============================================
) else (
    echo.
    echo [ERROR] Build gagal. Cek output di atas.
)

pause
