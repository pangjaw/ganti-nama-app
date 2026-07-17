#!/usr/bin/env python3
# download_p3ste_rekap.py
# Production-ready parallel PDF downloader for P3-STE rekap checklist
# Features: parallel download (5 concurrent), auto-captcha solve, temp profile (no locks),
# cookie persistence, configurable filters, retry with exponential backoff, resume/skip.

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlencode, urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Global claim set for race-condition-free parallel downloads
_claimed_urls: set[str] = set()
_claim_lock = asyncio.Lock()

# ─── Constants ──────────────────────────────────────────────────────────────
BASE_URL = "https://p3-ste.kai.id"
REKAP_PATH = "/rekap_checklist"
LOGIN_FILE = Path(__file__).with_name(".p3ste-logins.json")
COOKIE_FILE = Path(__file__).with_name(".p3ste-cookies.json")
FAILED_FILE = Path(__file__).with_name(".p3ste-failed.json")
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "P3STE"

TYPE_FALLBACK = {"perawatan": "2", "pemeriksaan": "1"}

# Default filters (0 = all)
DEFAULT_FILTERS = {
    "asset": "0",
    "category": "0",
    "daop": "0",
    "resort": "0",
    "nipp": "0",
    "noasset": "0",
    "hasil": "baik",
    "status": "done",
}


# ─── Data Classes ───────────────────────────────────────────────────────────
@dataclass
class DownloadResult:
    saved: int = 0
    skipped: int = 0
    failed: list[tuple[int, int, str]] = None  # (page_no, idx, error)

    def __post_init__(self):
        if self.failed is None:
            self.failed = []


# ─── Progress UI ────────────────────────────────────────────────────────────
class Progress:
    def __init__(self):
        self.percent = -1

    def set(self, percent: int, message: str):
        percent = max(self.percent, max(0, min(100, percent)))
        self.percent = percent
        bar = "#" * (percent // 5) + "." * (20 - percent // 5)
        sys.stdout.write(f"\r[{bar}] {percent:3d}% {message:<60.60}")
        sys.stdout.flush()

    def line(self, message: str):
        if self.percent >= 0:
            sys.stdout.write("\n")
            sys.stdout.flush()
        print(message)

    def done(self, message: str):
        self.set(100, "Selesai")
        sys.stdout.write("\n")
        sys.stdout.flush()
        print(message)


class NullProgress:
    def set(self, percent: int, message: str):
        pass

    def line(self, message: str):
        print(message)

    def done(self, message: str):
        print(message)


# ─── Utility Functions ──────────────────────────────────────────────────────
def parse_date(value: str) -> str:
    value = value.strip()
    try:
        return datetime.strptime(value, "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        raise SystemExit("Tanggal harus format dd/mm/yyyy. Contoh: 27/06/2026")


def month_year_folder(awal: str, akhir: str) -> str:
    """Generate folder name like 'Januari 2025' from date range (dd/mm/yyyy)."""
    try:
        dt = datetime.strptime(awal, "%d/%m/%Y")
        months_id = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        return f"{months_id[dt.month - 1]} {dt.year}"
    except Exception:
        return datetime.now().strftime("%B %Y")


def ask_date(label: str) -> str:
    return parse_date(input(f"{label} (dd/mm/yyyy): "))


def ask_type() -> str:
    while True:
        value = input("Tipe checklist [Perawatan/Pemeriksaan]: ").strip().lower()
        if value in TYPE_FALLBACK:
            return value.title()
        print("Pilih: Perawatan atau Pemeriksaan.")


def safe_name(name: str) -> str:
    return re.sub(r'[<>:\\"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "download.pdf"


def unique_path(folder: Path, name: str) -> Path:
    path = folder / safe_name(name)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 10_000):
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Terlalu banyak file bernama mirip: {path.name}")


def filename_from_headers(url: str, headers: dict[str, str], fallback: str) -> str:
    disposition = headers.get("content-disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.I)
    if match:
        return unquote(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', disposition, re.I)
    if match:
        return match.group(1)
    name = Path(urlparse(url).path).name
    return name or fallback


def is_print_pdf_target(target: dict[str, str]) -> bool:
    url = target.get("url", "")
    path = urlparse(url).path
    return (
        target.get("text", "").strip().lower() == "cetak"
        and "/cetak_checklist/report/" in path
        and "/exports/pdf/" in path
    )


def build_rekap_url(awal: str, akhir: str, type_value: str, filters: dict) -> str:
    params = {
        "awal": awal,
        "akhir": akhir,
        "type": type_value,
        **filters,
    }
    return f"{BASE_URL}{REKAP_PATH}?{urlencode(params)}"


# ─── Login Store ────────────────────────────────────────────────────────────
def load_login_store() -> dict:
    if not LOGIN_FILE.exists():
        return {"selected": "", "logins": {}}
    try:
        data = json.loads(LOGIN_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise SystemExit(f"File login rusak: {LOGIN_FILE}")
    data.setdefault("selected", "")
    data.setdefault("logins", {})
    return data


def save_login_store(data: dict):
    LOGIN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def selected_login(data: dict) -> dict | None:
    name = data.get("selected", "")
    return data.get("logins", {}).get(name)


def create_login_data():
    data = load_login_store()
    name = input("Nama data login: ").strip()
    if not name:
        print("Nama kosong. Batal.")
        return
    nipp = input("NIPP: ").strip()
    if not nipp:
        print("NIPP kosong. Batal.")
        return
    save_password = input("Simpan password lokal? [y/N]: ").strip().lower() == "y"
    password = getpass.getpass("Password: ") if save_password else ""
    data["logins"][name] = {"nipp": nipp, "password": password}
    data["selected"] = name
    save_login_store(data)
    print(f"Data login dibuat dan dipilih: {name}")


def choose_login_data():
    data = load_login_store()
    names = sorted(data["logins"])
    if not names:
        print("Belum ada data login.")
        return
    for i, name in enumerate(names, 1):
        marker = "*" if name == data.get("selected") else " "
        print(f"{i}. {marker} {name} ({data['logins'][name].get('nipp', '-')})")
    raw = input("Pilih nomor: ").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= len(names)):
        print("Pilihan tidak valid.")
        return
    data["selected"] = names[int(raw) - 1]
    save_login_store(data)
    print(f"Data login dipilih: {data['selected']}")


def read_credentials(login_data: dict | None = None) -> tuple[str, str]:
    login_data = login_data or {}
    nipp = os.getenv("P3STE_NIPP") or login_data.get("nipp") or input("NIPP: ").strip()
    password = os.getenv("P3STE_PASSWORD") or login_data.get("password") or getpass.getpass("Password: ")
    if not nipp or not password:
        raise SystemExit("NIPP/password kosong.")
    return nipp, password


# ─── Captcha Auto-Solve ─────────────────────────────────────────────────────
async def solve_captcha_text(text: str) -> str:
    """Auto-solve simple math captcha like '3 + 5'."""
    text = text.strip()
    match = re.search(r"(\d+)\s*([+\-xX*/])\s*(\d+)", text)
    if not match:
        return ""
    a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
    if op in ("+", ""):
        return str(a + b)
    if op == "-":
        return str(a - b)
    if op in ("x", "X", "*"):
        return str(a * b)
    if op == "/":
        return str(a // b) if b != 0 else "0"
    return ""


async def read_captcha_text(page) -> str:
    text = await page.evaluate(
        """() => {
            for (const el of document.querySelectorAll('form#form-login span, form#form-login .text-center')) {
                const text = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                if (/^\\d+\\s*[+\\-xX*/]\\s*\\d+$/.test(text)) return text;
            }
            return '';
        }"""
    )
    return text.strip()


async def read_login_feedback(page) -> str:
    text = await page.evaluate(
        """() => {
            const bad = [/^\\d+\\s*[+\\-xX*/]\\s*\\d+$/, /^masuk$/i, /^captcha$/i, /^show$/i];
            for (const el of document.querySelectorAll(
                '.alert, .invalid-feedback, .text-danger, .text-warning, .error, [role="alert"], form#form-login p, form#form-login div'
            )) {
                const text = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                if (!text || text.length < 4) continue;
                if (bad.some((rx) => rx.test(text))) continue;
                if (/nipp|password|captcha|salah|gagal|invalid|tidak sesuai|login/i.test(text)) return text;
            }
            return '';
        }"""
    )
    return text.strip()


async def is_login_page(page) -> bool:
    return await page.locator("#nipp").count() > 0 and await page.locator("#kata_sandi").count() > 0


async def login(page, login_data: dict | None = None):
    nipp, password = read_credentials(login_data)

    for attempt in range(1, 4):
        captcha_text = await read_captcha_text(page)
        if captcha_text:
            captcha = await solve_captcha_text(captcha_text)
            if captcha:
                print(f"Captcha auto-solve: {captcha_text} = {captcha}")
            else:
                captcha = input(f"Captcha {captcha_text} = ").strip()
        else:
            captcha = input("Captcha tidak terbaca. Lihat browser lalu isi jawaban: ").strip()

        await page.locator("#nipp").fill(nipp)
        await page.locator("#kata_sandi").fill(password)
        await page.locator("#captcha").fill(captcha)
        await page.locator("#form-login button[type='submit'], #form-login button").first.click()

        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            pass

        if not await is_login_page(page):
            print("Login OK.")
            return

        feedback = await read_login_feedback(page)
        if feedback:
            print(f"Login belum berhasil. Coba lagi ({attempt}/3). Pesan web: {feedback}")
        else:
            print(f"Login belum berhasil. Coba lagi ({attempt}/3). Cek captcha atau password.")

    raise SystemExit("Login gagal 3x.")


# ─── Page Interaction ───────────────────────────────────────────────────────
async def detect_type_value(page, tipe: str) -> str:
    value = await page.evaluate(
        """(label) => {
            label = label.toLowerCase();
            for (const option of document.querySelectorAll('select option')) {
                const text = (option.textContent || '').trim().toLowerCase();
                if (text === label) return option.value;
            }
            return '';
        }""",
        tipe,
    )
    return value or TYPE_FALLBACK[tipe.lower()]


async def wait_table(page, wait_ms: int):
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_timeout(wait_ms)


async def table_state(page) -> dict:
    return await page.evaluate(
        """() => {
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const loadingSelectors = [
                '.dataTables_processing', '[id$="_processing"]', '.loader-box',
                '.loader-wrapper', '.loader', '.spinner-border', '.spinner-grow',
                '[class*="loading"]', '[class*="loader"]', '[class*="spinner"]',
                '[id*="loading"]', '[id*="loader"]', '[id*="spinner"]'
            ];
            const rows = [...document.querySelectorAll('table tbody tr')].filter((row) => {
                const text = (row.textContent || '').replace(/\\s+/g, ' ').trim();
                return visible(row) && text && !/no data|tidak ada|kosong|empty|processing|loading/i.test(text);
            });
            const processing = [...document.querySelectorAll(loadingSelectors.join(','))].some((el) => visible(el));
            const body = document.body?.innerText || '';
            const empty = /no data available|tidak ada data|data kosong|tidak ditemukan/i.test(body);
            const printButtons = [...document.querySelectorAll('a, button')].filter(
                (el) => visible(el) && (el.textContent || '').includes('Cetak')
            ).length;
            const infoEl = [...document.querySelectorAll('.dataTables_info, [id$="_info"]')].find((el) => visible(el));
            const infoText = (infoEl?.textContent || '').replace(/\\s+/g, ' ').trim();
            let totalData = 0;
            let match = infoText.match(/dari\\s+(\\d+)\\s+data/i) || infoText.match(/of\\s+(\\d+)\\s+(entries|data)/i);
            if (match) totalData = parseInt(match[1], 10) || 0;

            const pageNumbers = [...document.querySelectorAll(
                '.pagination a, .pagination button, [id$="_paginate"] a, [id$="_paginate"] button, .paginate_button'
            )]
                .filter((el) => visible(el))
                .map((el) => (el.textContent || '').trim())
                .filter((text) => /^\\d+$/.test(text))
                .map((text) => parseInt(text, 10));
            const totalPages = pageNumbers.length ? Math.max(...pageNumbers) : 0;
            return { rows: rows.length, processing, empty, printButtons, totalData, totalPages, infoText };
        }"""
    )


async def wait_table_data(page, timeout_ms: int, progress: Progress, start: int, end: int, label: str):
    started = time.monotonic()
    ready_since = 0.0
    while True:
        state = await table_state(page)
        if (state["rows"] or state["empty"]) and not state["processing"]:
            if not ready_since:
                ready_since = time.monotonic()
            stable_ms = int((time.monotonic() - ready_since) * 1000)
            if stable_ms >= 2_500:
                progress.set(end, f"{label}: siap ({state['rows']} baris)")
                return
        else:
            ready_since = 0.0

        elapsed_ms = int((time.monotonic() - started) * 1000)
        if elapsed_ms > timeout_ms:
            progress.line(f"{label}: timeout, lanjut dengan state terakhir: {state}.")
            return

        span = max(1, end - start)
        percent = start + min(span - 1, int(span * elapsed_ms / timeout_ms))
        loading = "loading" if state["processing"] else "tunggu"
        progress.set(percent, f"{label}: {loading}, rows={state['rows']}, cetak={state['printButtons']}")
        await page.wait_for_timeout(500)


async def set_page_size_100(page, wait_ms: int, progress: Progress, timeout_ms: int):
    await wait_table_data(page, timeout_ms, progress, 35, 50, "Data 10")
    changed = await page.evaluate(
        """() => {
            for (const select of document.querySelectorAll('select')) {
                const option = [...select.options].find((item) => item.value === '100' || item.textContent.trim() === '100');
                if (!option) continue;
                select.value = option.value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
            return false;
        }"""
    )
    if changed:
        progress.set(55, "Set tampilan 100 data")
        await wait_table(page, wait_ms)
        await wait_table_data(page, timeout_ms, progress, 55, 70, "Data 100")
    else:
        progress.line("Pilihan 100 data tidak ditemukan. Lanjut apa adanya.")


async def find_print_targets(page) -> list[dict[str, str]]:
    return await page.evaluate(
        """() => [...document.querySelectorAll('a')]
            .filter((el) => {
                const text = (el.textContent || '').trim();
                const style = getComputedStyle(el);
                const href = el.href || el.getAttribute('href') || '';
                return text === 'Cetak'
                    && href.includes('/cetak_checklist/report/')
                    && href.includes('/exports/pdf/')
                    && style.display !== 'none'
                    && style.visibility !== 'hidden';
            })
            .map((el) => ({
                tag: el.tagName.toLowerCase(),
                text: (el.textContent || '').trim(),
                url: el.href || el.getAttribute('href') || '',
            }))"""
    )


async def click_next_page(page, wait_ms: int, progress: Progress, timeout_ms: int) -> bool:
    clicked = await page.evaluate(
        """() => {
            const candidates = [...document.querySelectorAll('a, button')].filter((el) => {
                const text = (el.textContent || '').trim().toLowerCase();
                const cls = (el.className || '').toString().toLowerCase();
                const parentCls = (el.parentElement?.className || '').toString().toLowerCase();
                const disabled = el.disabled || cls.includes('disabled') || parentCls.includes('disabled');
                return !disabled && (text === 'next' || text === 'berikutnya' || cls.includes('next') || parentCls.includes('next'));
            });
            if (!candidates.length) return false;
            candidates[0].click();
            return true;
        }"""
    )
    if clicked:
        progress.set(96, "Buka halaman berikutnya")
        await wait_table(page, wait_ms)
        await wait_table_data(page, timeout_ms, progress, 96, 98, "Halaman berikutnya")
    return bool(clicked)


# ─── Browser Context (Temp Profile = No Locks) ──────────────────────────────
async def create_browser_context(pw, output_dir: Path, show: bool):
    """Launch persistent context with temp user-data-dir to avoid ProcessSingleton locks."""
    user_data_dir = tempfile.mkdtemp(prefix="p3ste-")
    try:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir,
            channel="msedge",
            headless=not show,
            accept_downloads=True,
            downloads_path=str(output_dir),
        )
    except Exception:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=not show,
            accept_downloads=True,
            downloads_path=str(output_dir),
        )

    # Load cookies if exist
    if COOKIE_FILE.exists():
        try:
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            await context.add_cookies(cookies)
        except Exception:
            pass

    browser = context.browser
    return context, browser, user_data_dir


async def save_cookies(context):
    """Persist cookies for next run (skip login)."""
    try:
        cookies = await context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
    except Exception:
        pass


# ─── Download Functions ─────────────────────────────────────────────────────
async def download_url(page, output_dir: Path, url: str, index: int, progress: Progress) -> bool:
    """Direct HTTP download via page context."""
    absolute_url = urljoin(page.url, url)
    response = await page.context.request.get(absolute_url, timeout=30_000)
    body = await response.body()
    headers = {key.lower(): value for key, value in response.headers.items()}
    content_type = headers.get("content-type", "")

    if not response.ok:
        progress.line(f"Cetak #{index}: HTTP {response.status}.")
        return False
    if not body.startswith(b"%PDF") and "pdf" not in content_type.lower():
        progress.line(f"Cetak #{index}: bukan PDF ({content_type or 'content-type kosong'}).")
        return False

    filename = filename_from_headers(response.url, headers, f"p3ste-cetak-{index}.pdf")
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    target = unique_path(output_dir, filename)
    target.write_bytes(body)
    progress.line(f"Download: {target.name}")
    return True


async def click_download(page, url: str, output_dir: Path, index: int, progress: Progress, timeout_ms: int = 60_000) -> bool:
    """Fallback: click button and wait for download event."""
    button = page.locator(
        f"a.btn.btn-danger:visible[href*='/cetak_checklist/report/'][href*='/exports/pdf/'][href='{url}']"
    ).first
    if await button.count() == 0:
        # fallback by nth if URL match fails
        all_buttons = page.locator("a.btn.btn-danger:visible[href*='/cetak_checklist/report/'][href*='/exports/pdf/']")
        count = await all_buttons.count()
        for i in range(count):
            btn = all_buttons.nth(i)
            href = await btn.get_attribute("href")
            if href and url in href:
                button = btn
                break

    try:
        async with page.expect_download(timeout=timeout_ms) as download_info:
            await button.click()
        download = await download_info.value
        target = unique_path(output_dir, download.suggested_filename)
        await download.save_as(target)
        progress.line(f"Download: {target.name}")
        return True
    except PlaywrightTimeoutError:
        progress.line(f"Cetak #{index}: timeout click download ({timeout_ms/1000}s).")
        return False
    except Exception as e:
        progress.line(f"Cetak #{index}: click download error ({e}).")
        return False


async def download_one_target(page, output_dir: Path, target: dict, index: int, progress: Progress) -> bool:
    """Try HTTP download first, fallback to click with retry."""
    url = target["url"]

    # 1. HTTP download
    try:
        if await download_url(page, output_dir, url, index, progress):
            return True
    except Exception:
        pass

    # 2. Click fallback with retries
    for attempt in range(3):
        try:
            if await click_download(page, url, output_dir, index, progress, timeout_ms=60_000):
                return True
        except Exception:
            pass
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff

    return False


# ─── Parallel Download ──────────────────────────────────────────────────────
async def crawl_all_targets(page, args, progress: Progress) -> list[tuple[int, dict]]:
    """Crawl all pages, collect all print targets."""
    all_targets = []
    page_no = 1
    while True:
        progress.line(f"Crawl halaman {page_no}...")
        targets = [t for t in await find_print_targets(page) if is_print_pdf_target(t)]
        all_targets.extend([(page_no, t) for t in targets])
        if not await click_next_page(page, args.wait_ms, NullProgress(), args.table_timeout_ms):
            break
        page_no += 1
    progress.line(f"Total target ditemukan: {len(all_targets)} dari {page_no} halaman")
    return all_targets


async def download_targets_parallel(
    page, output_dir: Path, targets: list[tuple[int, dict]], progress: Progress, max_concurrent: int = 5
) -> DownloadResult:
    """Download all targets in parallel with semaphore."""
    semaphore = asyncio.Semaphore(max_concurrent)
    result = DownloadResult()

    async def download_one(page_no, target, idx):
        async with semaphore:
            url = target["url"]
            # Atomic claim to prevent race condition
            if not await claim_url(url):
                result.skipped += 1
                return
            
            # Double-check file exists after claim (in case another process created it)
            existing = file_exists_skip(output_dir, url)
            if existing:
                result.skipped += 1
                return

            success = await download_one_target(page, output_dir, target, idx, NullProgress())
            if success:
                result.saved += 1
            else:
                result.failed.append((page_no, idx, "download failed after retries"))

    tasks = [download_one(pn, t, i) for i, (pn, t) in enumerate(targets)]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Retry failed sequentially
    if result.failed:
        progress.line(f"Retry {len(result.failed)} file gagal secara sequential...")
        new_failed = []
        for page_no, idx, err in result.failed:
            target = targets[idx][1]
            success = await download_one_target(page, output_dir, target, idx, progress)
            if success:
                result.saved += 1
            else:
                new_failed.append((page_no, idx, f"retry: {err}"))
        result.failed = new_failed

    progress.done(f"Selesai. Berhasil: {result.saved}, Skip: {result.skipped}, Gagal: {len(result.failed)}")
    if result.failed:
        progress.line("File gagal:")
        for pn, idx, err in result.failed:
            progress.line(f"  Hal {pn} #{idx}: {err}")

    # Save failed for --retry-failed
    FAILED_FILE.write_text(json.dumps(result.failed, indent=2), encoding="utf-8")
    return result


def file_exists_skip(output_dir: Path, url: str) -> Path | None:
    """Return path if file exists and >1KB, else None."""
    name = Path(urlparse(url).path).name
    if not name or not name.lower().endswith(".pdf"):
        return None
    candidate = output_dir / safe_name(name)
    if candidate.exists() and candidate.stat().st_size > 1000:
        return candidate
    return None


async def claim_url(url: str) -> bool:
    """Atomically claim a URL for download. Returns True if claimed, False if already claimed."""
    async with _claim_lock:
        if url in _claimed_urls:
            return False
        _claimed_urls.add(url)
        return True


# ─── Main Flow ──────────────────────────────────────────────────────────────
async def prepare_rekap_page(context, args: argparse.Namespace, login_data: dict | None, progress: Progress,
                              awal: str, akhir: str, tipe: str, filters: dict) -> tuple[object, dict]:
    page = context.pages[0] if context.pages else await context.new_page()

    progress.set(15, "Buka P3-STE")
    await page.goto(f"{BASE_URL}{REKAP_PATH}")
    await wait_table(page, args.wait_ms)

    if await is_login_page(page):
        progress.line("Login dibutuhkan.")
        await login(page, login_data)
        progress.set(25, "Login OK")
        await page.goto(f"{BASE_URL}{REKAP_PATH}")
        await wait_table(page, args.wait_ms)
        # Save cookies after successful login
        await save_cookies(context)

    progress.set(30, "Baca tipe checklist")
    type_value = await detect_type_value(page, tipe)

    progress.set(35, "Terapkan filter")
    await page.goto(build_rekap_url(awal, akhir, type_value, filters))
    await wait_table(page, args.wait_ms)
    await set_page_size_100(page, args.wait_ms, progress, args.table_timeout_ms)

    state = await table_state(page)
    total_data = int(state.get("totalData") or state.get("rows") or 0)
    rows = max(1, int(state.get("rows") or 1))
    total_pages = int(state.get("totalPages") or (total_data + rows - 1) // rows)

    summary = {
        "awal": awal,
        "akhir": akhir,
        "tipe": tipe,
        "rows": int(state.get("rows") or 0),
        "total_data": total_data,
        "total_pages": total_pages,
        "print_buttons": int(state.get("printButtons") or 0),
        "info_text": str(state.get("infoText") or ""),
    }
    return page, summary


async def run_parallel(args: argparse.Namespace, login_data: dict | None, filters: dict) -> None:
    """Parallel download mode: crawl all -> download batch."""
    awal = args.awal or ask_date("Tanggal awal")
    akhir = args.akhir or ask_date("Tanggal akhir")
    tipe = args.tipe or ask_type()
    awal = parse_date(awal)
    akhir = parse_date(akhir)
    if tipe.lower() not in TYPE_FALLBACK:
        raise SystemExit("Tipe harus Perawatan atau Pemeriksaan.")

    # Subfolder by month/year from start date
    month_folder = month_year_folder(awal, akhir)
    output_dir = Path(args.output).expanduser() / month_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    progress = Progress()

    async with async_playwright() as pw:
        progress.set(5, "Buka browser")
        context, browser, user_data_dir = await create_browser_context(pw, output_dir, bool(args.show))

        try:
            page, summary = await prepare_rekap_page(
                context, args, login_data, progress, awal, akhir, tipe, filters
            )

            progress.set(20, "Mulai crawl semua halaman...")
            all_targets = await crawl_all_targets(page, args, progress)

            if not all_targets:
                progress.done("Tidak ada file untuk di-download")
                return

            # Clear claim set for new run
            global _claimed_urls
            async with _claim_lock:
                _claimed_urls.clear()

            progress.set(40, f"Download paralel {len(all_targets)} file (max {args.concurrent} sekaligus)...")
            await download_targets_parallel(page, output_dir, all_targets, progress, max_concurrent=args.concurrent)

        finally:
            await context.close()
            await browser.close()
            # Cleanup temp profile dir
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except Exception:
                pass


async def run_summary(args: argparse.Namespace, login_data: dict | None, filters: dict) -> dict:
    """Summary only mode: just fetch counts."""
    awal = args.awal or ask_date("Tanggal awal")
    akhir = args.akhir or ask_date("Tanggal akhir")
    tipe = args.tipe or ask_type()
    awal = parse_date(awal)
    akhir = parse_date(akhir)
    month_folder = month_year_folder(awal, akhir)
    output_dir = Path(args.output).expanduser() / month_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    progress = NullProgress()

    async with async_playwright() as pw:
        progress.set(5, "Buka browser")
        context, browser, user_data_dir = await create_browser_context(pw, output_dir, bool(args.show))

        try:
            _, summary = await prepare_rekap_page(
                context, args, login_data, progress, awal, akhir, tipe, filters
            )
            progress.done(
                f"Ringkasan siap. Total data: {summary['total_data']}. Total halaman: {summary['total_pages']}."
            )
            return summary
        finally:
            await context.close()
            await browser.close()
            shutil.rmtree(user_data_dir, ignore_errors=True)


async def retry_failed(args: argparse.Namespace, login_data: dict | None, filters: dict) -> None:
    """Retry only failed downloads from last run."""
    if not FAILED_FILE.exists():
        print("Tidak ada file gagal tersimpan.")
        return

    try:
        failed = json.loads(FAILED_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("File gagal rusak.")
        return

    if not failed:
        print("Tidak ada file gagal untuk di-retry.")
        return

    print(f"Retry {len(failed)} file gagal...")
    # For retry, we need to re-crawl to get fresh URLs/buttons
    # This is simplified - just re-run full parallel download
    # which will skip existing files and retry failed ones
    await run_parallel(args, login_data, filters)


def normalize_args(args: argparse.Namespace) -> tuple[str, str, str, Path]:
    awal = args.awal or ask_date("Tanggal awal")
    akhir = args.akhir or ask_date("Tanggal akhir")
    tipe = args.tipe or ask_type()
    awal = parse_date(awal)
    akhir = parse_date(akhir)
    if tipe.lower() not in TYPE_FALLBACK:
        raise SystemExit("Tipe harus Perawatan atau Pemeriksaan.")
    
    # Subfolder by month/year from start date
    month_folder = month_year_folder(awal, akhir)
    output_dir = Path(args.output).expanduser() / month_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    return awal, akhir, tipe, output_dir


def build_filters(args: argparse.Namespace) -> dict:
    """Build filter dict from CLI args, defaulting to DEFAULT_FILTERS."""
    filters = DEFAULT_FILTERS.copy()
    if args.daop is not None:
        filters["daop"] = args.daop
    if args.resort is not None:
        filters["resort"] = args.resort
    if args.category is not None:
        filters["category"] = args.category
    if args.asset is not None:
        filters["asset"] = args.asset
    if args.nipp is not None:
        filters["nipp"] = args.nipp
    if args.noasset is not None:
        filters["noasset"] = args.noasset
    if args.hasil is not None:
        filters["hasil"] = args.hasil
    if args.status is not None:
        filters["status"] = args.status
    return filters


def self_test():
    assert parse_date("01/06/2026") == "01/06/2026"
    assert safe_name('a:b*c?.pdf') == "a_b_c_.pdf"
    assert "type=2" in build_rekap_url("01/06/2026", "27/06/2026", "2", DEFAULT_FILTERS)
    assert is_print_pdf_target({
        "text": "Cetak",
        "url": "https://p3-ste.kai.id/cetak_checklist/report/perawatan/exports/pdf/706783?false",
    })
    assert not is_print_pdf_target({"text": "Cetak Checklist", "url": "https://p3-ste.kai.id/cetak_checklist"})
    print("Self-test OK")


def menu(args: argparse.Namespace):
    while True:
        data = load_login_store()
        selected = data.get("selected") or "-"
        print()
        print("=== P3-STE Downloader ===")
        print(f"Login dipilih: {selected}")
        print("1. Buat data login")
        print("2. Pilih data login")
        print("3. Tampilkan total halaman dan data (summary)")
        print("4. Proses download (parallel)")
        print("5. Retry file gagal")
        print("0. Keluar")
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            create_login_data()
        elif choice == "2":
            choose_login_data()
        elif choice == "3":
            data = load_login_store()
            login_data = selected_login(data)
            if not login_data:
                print("Belum ada login dipilih. NIPP/password akan ditanya manual jika login dibutuhkan.")
            filters = build_filters(args)
            summary = asyncio.run(run_summary(args, login_data, filters))
            print(f"Total data: {summary['total_data']}")
            print(f"Total halaman: {summary['total_pages']}")
            print(f"Info tabel: {summary['info_text'] or '-'}")
        elif choice == "4":
            data = load_login_store()
            login_data = selected_login(data)
            if not login_data:
                print("Belum ada login dipilih. NIPP/password akan ditanya manual jika login dibutuhkan.")
            filters = build_filters(args)
            asyncio.run(run_parallel(args, login_data, filters))
        elif choice == "5":
            data = load_login_store()
            login_data = selected_login(data)
            filters = build_filters(args)
            asyncio.run(retry_failed(args, login_data, filters))
        elif choice == "0":
            return
        else:
            print("Pilihan tidak valid.")


def has_direct_args(args: argparse.Namespace) -> bool:
    return bool(args.direct or args.awal or args.akhir or args.tipe or args.summary_only or args.retry_failed)


def main():
    parser = argparse.ArgumentParser(description="Download PDF rekap checklist P3-STE (parallel, robust).")
    parser.add_argument("--awal", help="Tanggal awal format dd/mm/yyyy")
    parser.add_argument("--akhir", help="Tanggal akhir format dd/mm/yyyy")
    parser.add_argument("--tipe", choices=["Perawatan", "Pemeriksaan"], help="Tipe checklist")
    parser.add_argument("--output", default=str(DEFAULT_DOWNLOAD_DIR), help="Folder download")
    parser.add_argument("--show", action="store_true", help="Tampilkan browser (non-headless)")
    parser.add_argument("--wait-ms", type=int, default=5_000, help="Waktu tunggu setelah loading tabel (ms)")
    parser.add_argument("--table-timeout-ms", type=int, default=120_000, help="Batas tunggu data tabel muncul (ms)")
    parser.add_argument("--concurrent", type=int, default=5, help="Jumlah download paralel (default: 5)")
    parser.add_argument("--direct", action="store_true", help="Lewati menu dan langsung proses")
    parser.add_argument("--summary-only", action="store_true", help="Hanya tampilkan ringkasan (tidak download)")
    parser.add_argument("--retry-failed", action="store_true", help="Retry file gagal dari run sebelumnya")
    parser.add_argument("--self-test", action="store_true", help="Cek fungsi dasar tanpa buka browser")

    # Filter arguments (default 0 = all)
    parser.add_argument("--daop", help="Filter DAOP (default: 0=all)")
    parser.add_argument("--resort", help="Filter Resort (default: 0=all)")
    parser.add_argument("--category", help="Filter Category (default: 0=all)")
    parser.add_argument("--asset", help="Filter Asset (default: 0=all)")
    parser.add_argument("--nipp", help="Filter NIPP (default: 0=all)")
    parser.add_argument("--noasset", help="Filter No Asset (default: 0=all)")
    parser.add_argument("--hasil", default="baik", help="Filter Hasil (default: baik)")
    parser.add_argument("--status", default="done", help="Filter Status (default: done)")

    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    data = load_login_store()
    login_data = selected_login(data)

    filters = build_filters(args)

    if args.summary_only:
        asyncio.run(run_summary(args, login_data, filters))
        return

    if args.retry_failed:
        asyncio.run(retry_failed(args, login_data, filters))
        return

    if has_direct_args(args):
        asyncio.run(run_parallel(args, login_data, filters))
    else:
        menu(args)


if __name__ == "__main__":
    main()
