# Build Sintelis Utility Portable
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Building Sintelis Utility Portable" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$TessDir = "tesseract"
$PopplerDir = "poppler"
$AppDir = (Get-Location).Path

# Cek Tesseract
if (-not (Test-Path "$TessDir\tesseract.exe")) {
    if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
        Write-Host "[COPY] Menyalin Tesseract dari system..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path $TessDir | Out-Null
        Copy-Item "C:\Program Files\Tesseract-OCR\*" $TessDir -Recurse -Force
    } else {
        Write-Host "[ERROR] Tesseract tidak ditemukan!" -ForegroundColor Red
        Write-Host " Install: https://github.com/UB-Mannheim/tesseract/wiki"
        exit 1
    }
}

# Cek tessdata ind
if (-not (Test-Path "$TessDir\tessdata\ind.traineddata")) {
    if (Test-Path "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata") {
        Write-Host "[INFO] Copy ind.traineddata..." -ForegroundColor Yellow
        Copy-Item "C:\Program Files\Tesseract-OCR\tessdata\ind.traineddata" "$TessDir\tessdata\" -Force
    }
}

# Siapkan argumen
$AddData = @(
    "--add-data", "app.py;.",
    "--add-data", "templates;templates",
    "--add-data", "$TessDir;tesseract"
)

if (Test-Path "$PopplerDir\pdftoppm.exe") {
    Write-Host "[INFO] Poppler ditemukan, akan dibundle." -ForegroundColor Green
    $AddData += "--add-data"
    $AddData += "poppler;poppler"
} else {
    Write-Host "[INFO] Poppler tidak ditemukan (tidak dibundle)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[BUILD] Mulai build dengan PyInstaller..." -ForegroundColor Magenta
Write-Host ""

$PyArgs = @(
    "--onefile", "--windowed"
) + $AddData + @(
    "--hidden-import", "pytesseract"
    "--hidden-import", "pdf2image"
    "--hidden-import", "PIL"
    "--hidden-import", "PIL._tkinter_finder"
    "--collect-all", "customtkinter"
    "--name", "Sintelis Utility"
    "portable_ui.py"
)

python -m PyInstaller $PyArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " BUILD SUKSES!" -ForegroundColor Green
    Write-Host " File: dist\Sintelis Utility.exe" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Build gagal. Cek output di atas." -ForegroundColor Red
}

Read-Host "Press Enter"
