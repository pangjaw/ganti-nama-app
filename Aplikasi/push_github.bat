@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo ==================================================
echo PUSH PROJECT KE GITHUB
echo ==================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git tidak ditemukan. Pastikan Git sudah terinstall.
    goto fail
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo ERROR: Folder ini bukan repository Git.
    goto fail
)

for /f "delims=" %%b in ('git branch --show-current') do set "BRANCH=%%b"
if "%BRANCH%"=="" (
    echo ERROR: Branch aktif tidak terdeteksi.
    goto fail
)

for /f "delims=" %%u in ('git remote get-url origin 2^>nul') do set "REMOTE=%%u"
if "%REMOTE%"=="" (
    echo ERROR: Remote origin belum diset.
    echo Jalankan: git remote add origin URL_REPO_GITHUB
    goto fail
)

echo Branch : %BRANCH%
echo Remote : %REMOTE%
echo.

echo Status saat ini:
git status --short
echo.

set "DEFAULT_MSG=update app"
set /p "COMMIT_MSG=Pesan commit (Enter = %DEFAULT_MSG%): "
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=%DEFAULT_MSG%"

echo.
echo Stage perubahan tracked dan script ini...
git add -u
if errorlevel 1 goto fail

git add -- "%~nx0"
if errorlevel 1 goto fail

for /f %%i in ('git ls-files --others --exclude-standard ^| find /c /v ""') do set "UNTRACKED_COUNT=%%i"
if not "!UNTRACKED_COUNT!"=="0" (
    echo.
    echo Catatan: file baru lain berikut TIDAK otomatis ikut commit:
    git ls-files --others --exclude-standard
    echo.
    echo Kalau ada yang memang perlu ikut, jalankan manual:
    echo git add nama-file
    echo lalu jalankan script ini lagi.
)

git diff --cached --quiet
if errorlevel 1 (
    echo.
    echo Membuat commit...
    git commit -m "%COMMIT_MSG%"
    if errorlevel 1 goto fail
) else (
    echo.
    echo Tidak ada perubahan staged untuk di-commit.
)

echo.
echo Sinkronisasi dengan origin/%BRANCH%...
git pull --rebase origin "%BRANCH%"
if errorlevel 1 goto fail

echo.
echo Push ke GitHub...
git push -u origin "%BRANCH%"
if errorlevel 1 goto fail

echo.
echo ==================================================
echo SELESAI: push ke GitHub berhasil.
echo ==================================================
pause
exit /b 0

:fail
echo.
echo ==================================================
echo GAGAL: proses dihentikan. Baca pesan error di atas.
echo ==================================================
pause
exit /b 1
