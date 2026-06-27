from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

BASE_URL = "https://p3-ste.kai.id"
REKAP_PATH = "/rekap_checklist"
PROFILE_DIR = Path(__file__).with_name(".p3ste-browser")
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "P3STE"
TYPE_FALLBACK = {"perawatan": "2", "pemeriksaan": "1"}


def parse_date(value: str) -> str:
    value = value.strip()
    try:
        return datetime.strptime(value, "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        raise SystemExit("Tanggal harus format dd/mm/yyyy. Contoh: 27/06/2026")


def ask_date(label: str) -> str:
    return parse_date(input(f"{label} (dd/mm/yyyy): "))


def ask_type() -> str:
    while True:
        value = input("Tipe checklist [Perawatan/Pemeriksaan]: ").strip().lower()
        if value in TYPE_FALLBACK:
            return value.title()
        print("Pilih: Perawatan atau Pemeriksaan.")


def safe_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "download.pdf"


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


def build_rekap_url(awal: str, akhir: str, type_value: str) -> str:
    params = {
        "awal": awal,
        "akhir": akhir,
        "type": type_value,
        "asset": "0",
        "category": "0",
        "daop": "1",
        "resort": "170",
        "nipp": "0",
        "noasset": "0",
        "hasil": "baik",
        "status": "done",
    }
    return f"{BASE_URL}{REKAP_PATH}?{urlencode(params)}"


def read_credentials() -> tuple[str, str]:
    nipp = os.getenv("P3STE_NIPP") or input("NIPP: ").strip()
    password = os.getenv("P3STE_PASSWORD") or getpass.getpass("Password: ")
    if not nipp or not password:
        raise SystemExit("NIPP/password kosong.")
    return nipp, password


async def is_login_page(page) -> bool:
    return await page.locator("#nipp").count() > 0 and await page.locator("#kata_sandi").count() > 0


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


async def login(page) -> None:
    nipp, password = read_credentials()

    for attempt in range(1, 4):
        captcha_text = await read_captcha_text(page)
        if captcha_text:
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

        print(f"Login belum berhasil. Coba lagi ({attempt}/3).")

    raise SystemExit("Login gagal 3x.")


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


async def wait_table(page, wait_ms: int) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_timeout(wait_ms)


async def set_page_size_100(page, wait_ms: int) -> None:
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
        print("Set tampilan 100 data. Tunggu loading...")
        await wait_table(page, wait_ms)
    else:
        print("Pilihan 100 data tidak ditemukan. Lanjut apa adanya.")


async def download_print_buttons(page, output_dir: Path) -> int:
    buttons = page.locator("a:has-text('Cetak'), button:has-text('Cetak')")
    count = await buttons.count()
    saved = 0

    for index in range(count):
        button = buttons.nth(index)
        try:
            async with page.expect_download(timeout=30_000) as download_info:
                await button.click()
            download = await download_info.value
            target = unique_path(output_dir, download.suggested_filename)
            await download.save_as(target)
            saved += 1
            print(f"Download: {target.name}")
        except PlaywrightTimeoutError:
            print(f"Tombol Cetak #{index + 1}: tidak menghasilkan download.")

    return saved


async def click_next_page(page, wait_ms: int) -> bool:
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
        await wait_table(page, wait_ms)
    return bool(clicked)


async def run(args: argparse.Namespace) -> None:
    awal = args.awal or ask_date("Tanggal awal")
    akhir = args.akhir or ask_date("Tanggal akhir")
    tipe = args.tipe or ask_type()
    awal = parse_date(awal)
    akhir = parse_date(akhir)
    if tipe.lower() not in TYPE_FALLBACK:
        raise SystemExit("Tipe harus Perawatan atau Pemeriksaan.")

    output_dir = Path(args.output).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        try:
            context = await pw.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                channel="msedge",
                headless=not args.show,
                accept_downloads=True,
                downloads_path=str(output_dir),
            )
        except Exception:
            context = await pw.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=not args.show,
                accept_downloads=True,
                downloads_path=str(output_dir),
            )

        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto(f"{BASE_URL}{REKAP_PATH}")
        await wait_table(page, args.wait_ms)
        if await is_login_page(page):
            print("Login dibutuhkan.")
            await login(page)
            await page.goto(f"{BASE_URL}{REKAP_PATH}")
            await wait_table(page, args.wait_ms)

        type_value = await detect_type_value(page, tipe)
        await page.goto(build_rekap_url(awal, akhir, type_value))
        await wait_table(page, args.wait_ms)
        await set_page_size_100(page, args.wait_ms)

        total = 0
        page_no = 1
        while True:
            print(f"Halaman {page_no}.")
            total += await download_print_buttons(page, output_dir)
            if not await click_next_page(page, args.wait_ms):
                break
            page_no += 1

        await context.close()
        print(f"Selesai. Total download: {total}. Folder: {output_dir}")


def self_test() -> None:
    assert parse_date("01/06/2026") == "01/06/2026"
    assert safe_name('a:b*c?.pdf') == "a_b_c_.pdf"
    assert "type=2" in build_rekap_url("01/06/2026", "27/06/2026", "2")
    print("Self-test OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download PDF rekap checklist P3-STE.")
    parser.add_argument("--awal", help="Tanggal awal format dd/mm/yyyy")
    parser.add_argument("--akhir", help="Tanggal akhir format dd/mm/yyyy")
    parser.add_argument("--tipe", choices=["Perawatan", "Pemeriksaan"], help="Tipe checklist")
    parser.add_argument("--output", default=str(DEFAULT_DOWNLOAD_DIR), help="Folder download")
    parser.add_argument("--show", action="store_true", help="Tampilkan browser")
    parser.add_argument("--wait-ms", type=int, default=3_000, help="Waktu tunggu setelah loading tabel")
    parser.add_argument("--self-test", action="store_true", help="Cek fungsi dasar tanpa buka browser")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
