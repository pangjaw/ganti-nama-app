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
    if exist "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata" (
        echo [INFO] Copy ind.traineddata...
        copy "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata" "%TESS_DIR%\tessdata\" >nul
    )
)
echo.

REM Siapkan argumen add-data
set ADD_DATA=--add-data "app.py;." --add-data "core.py;." --add-data "templates;templates" --add-data "%TESS_DIR%;tesseract"

REM Poppler optional
if exist "poppler\pdftoppm.exe" (
    echo [INFO] Poppler ditemukan, akan dibundle.
    set ADD_DATA=%ADD_DATA% --add-data "poppler;poppler"
) else (
    echo [INFO] Poppler tidak ditemukan (tidak dibundle).
)

echo.
echo [BUILD] Mulai build dengan PyInstaller...
python -m PyInstaller --onefile --windowed ^
    --exclude-module "flask" ^
    --exclude-module "jinja2" ^
    --exclude-module "werkzeug" ^
    --exclude-module "markupsafe" ^
    --exclude-module "itsdangerous" ^
    --exclude-module "click" ^
    --exclude-module "openpyxl" ^
    --exclude-module "lxml" ^
    --exclude-module "pandas" ^
    --exclude-module "numpy" ^
    --exclude-module "pytest" ^
    --exclude-module "pygments" ^
    --exclude-module "rich" ^
    --exclude-module "pydantic" ^
    --exclude-module "cryptography" ^
    --exclude-module "chardet" ^
    --exclude-module "urllib3" ^
    --exclude-module "certifi" ^
    --exclude-module "requests" ^
    --exclude-module "fsspec" ^
    --exclude-module "sqlalchemy" ^
    --exclude-module "matplotlib" ^
    --exclude-module "scipy" ^
    --exclude-module "babel" ^
    --exclude-module "cssutils" ^
    --exclude-module "bs4" ^
    --exclude-module "tornado" ^
    --exclude-module "dask" ^
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
