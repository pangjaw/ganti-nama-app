from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import download_p3ste_rekap as core
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

FORM_PATH = "/masterdataprogramrealisasi/form-add"
BATCH_SIZE = 5

TOP_SELECT_INDEX = {
    "tipe": 0,
    "kategori": 1,
    "periode": 2,
    "kode": 3,
    "lokasi": 4,
}

TOP_INPUT_INDEX = {
    "tanggal_program": 0,
    "tanggal_realisasi": 1,
    "jumlah_orang": 2,
}

TYPE_CONFIG = {
    "wesel": {
        "periode": "2 Mingguan",
        "kode_label": "PERAWATAN WESEL ELEKTRIK 2 MINGGUAN - (WESEL BIASA)",
        "kode_keywords": [["WESEL", "2 MINGGUAN"], ["WESEL"]],
        "operation_keywords": [["WESEL", "2 MINGGUAN"], ["WESEL"]],
    },
    "sinyal": {
        "periode": "Bulanan",
        "kode_label": "PERAWATAN PERAGA SINYAL ELEKTRIK 1 BULANAN - (-)",
        "kode_keywords": [["SINYAL", "BULANAN"], ["SINYAL"]],
        "operation_keywords": [["SINYAL", "BULANAN"], ["SINYAL"]],
    },
    "axc": {
        "periode": "Bulanan",
        "kode_label": "PERAWATAN AXLE COUNTER SIEMENS 1 BULANAN - (SIEMENS)",
        "kode_keywords": [["AXLE", "COUNTER", "BULANAN"], ["AXLE", "COUNTER"], ["AXLE"]],
        "operation_keywords": [["AXLE", "COUNTER", "BULANAN"], ["AXLE", "COUNTER"], ["AXLE"]],
    },
}


@dataclass
class JobConfig:
    jenis: str
    lokasi: str
    jumlah_orang: int
    start_finish: str
    items: list[str]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).upper()


def folded_text(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalize_text(value))


def unique_groups(groups: list[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    result: list[list[str]] = []
    for group in groups:
        cleaned = tuple(item for item in group if item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(list(cleaned))
    return result


def short_text_keyword_groups(value: str) -> list[list[str]]:
    norm = normalize_text(value)
    groups: list[list[str]] = []

    asset_match = re.search(
        r"\b(UB\.?\s*\d+[A-Z]?|B\.?\s*\d+[A-Z]?|JL\s*\d+[A-Z]?|J\s*\d+[A-Z]?|L\s*\d+[A-Z]?|W\s*\d+[A-Z]?\d?|ZP\s*\d+[A-Z]?)\b",
        norm,
    )
    asset_code = folded_text(asset_match.group(1)) if asset_match else ""

    loc_parts: list[str] = []
    loc_source = norm[asset_match.end():] if asset_match else norm
    for match in re.findall(r"\b[A-Z]{3}(?:-[A-Z]{3})?\b", loc_source):
        for part in match.split("-"):
            if part not in loc_parts:
                loc_parts.append(part)

    groups.append([norm])
    groups.append([folded_text(value)])
    if asset_code:
        groups.append([asset_code])
        if loc_parts:
            groups.append([asset_code, *loc_parts])
    return unique_groups(groups)


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def parse_schedule(value: str) -> str:
    match = re.fullmatch(r"(\d{2})(\d{2})(\d{4})\s+(\d{2})(\d{2})-(\d{2})(\d{2})", value.strip())
    if not match:
        raise SystemExit("Format waktu harus seperti: 01072026 0800-2300")

    day, month, year, start_h, start_m, end_h, end_m = match.groups()
    start_dt = datetime.strptime(f"{day}{month}{year}{start_h}{start_m}", "%d%m%Y%H%M")
    end_dt = datetime.strptime(f"{day}{month}{year}{end_h}{end_m}", "%d%m%Y%H%M")
    if end_dt < start_dt:
        raise SystemExit("Jam selesai tidak boleh lebih kecil dari jam mulai.")

    return f"{start_dt:%d/%m/%Y %H:%M} - {end_dt:%d/%m/%Y %H:%M}"


def tanggal_program_from_start_finish(value: str) -> str:
    match = re.match(r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}\s+-\s+\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}", value)
    if not match:
        raise SystemExit("Format Start-Finish Date tidak valid.")
    return match.group(1)


def ask_choice(prompt: str, allowed: set[str]) -> str:
    while True:
        value = input(prompt).strip().lower()
        if value in allowed:
            return value
        print(f"Pilih salah satu: {', '.join(sorted(allowed))}")


def ask_positive_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Isi angka lebih dari 0.")


def ask_multiline_items() -> list[str]:
    print("Paste daftar Short Text. Akhiri dengan baris kosong.")
    items: list[str] = []
    while True:
        line = input().strip()
        if not line:
            break
        items.append(normalize_text(line))
    if not items:
        raise SystemExit("Daftar Short Text kosong.")
    return items


def ask_job_config() -> JobConfig:
    jenis = ask_choice("Jenis [wesel/sinyal/axc]: ", set(TYPE_CONFIG))
    lokasi = input("Lokasi dropdown (contoh: Stasiun Bogor): ").strip()
    if not lokasi:
        raise SystemExit("Lokasi wajib diisi.")

    jumlah_orang = ask_positive_int("Jumlah orang: ")
    start_finish = parse_schedule(input("Tanggal dan jam [01072026 0800-2300]: "))
    items = ask_multiline_items()
    return JobConfig(
        jenis=jenis,
        lokasi=lokasi,
        jumlah_orang=jumlah_orang,
        start_finish=start_finish,
        items=items,
    )


def active_login_data() -> dict | None:
    return core.selected_login(core.load_login_store())


async def wait_ready(page, timeout_ms: int = 15_000) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_timeout(800)


async def open_form_page(page, login_data: dict | None) -> None:
    await page.goto(f"{core.BASE_URL}{FORM_PATH}")
    await wait_ready(page)
    if await core.is_login_page(page):
        print("Login dibutuhkan.")
        await core.login(page, login_data)
        await page.goto(f"{core.BASE_URL}{FORM_PATH}")
        await wait_ready(page)


async def set_visible_select_by_index(page, index: int, target_text: str, keyword_groups: list[list[str]] | None = None) -> str:
    result = await page.evaluate(
        """(payload) => {
            const norm = (value) => (value || '').replace(/\\s+/g, ' ').trim().toUpperCase();
            const fold = (value) => norm(value).replace(/[^A-Z0-9]+/g, '');
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const selects = [...document.querySelectorAll('select')].filter((el) => visible(el));
            const select = selects[payload.index];
            if (!select) {
                return { ok: false, reason: `select index ${payload.index} tidak ditemukan` };
            }

            const options = [...select.options].map((option) => ({
                value: option.value,
                text: norm(option.textContent),
                folded: fold(option.textContent),
            }));

            const target = norm(payload.text);
            const targetFolded = fold(payload.text);

            let chosen = options.find((option) => option.text === target)
                || options.find((option) => option.folded === targetFolded)
                || options.find((option) => option.text.includes(target))
                || options.find((option) => option.folded.includes(targetFolded));

            if (!chosen && payload.keyword_groups?.length) {
                for (const group of payload.keyword_groups) {
                    const words = group.map(norm).filter(Boolean);
                    chosen = options.find((option) => words.every((word) => option.text.includes(word)));
                    if (chosen) break;
                }
            }

            if (!chosen) {
                return {
                    ok: false,
                    reason: `opsi '${payload.text}' tidak ditemukan`,
                    options: options.map((option) => option.text).filter(Boolean),
                };
            }

            select.value = chosen.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.dispatchEvent(new Event('input', { bubbles: true }));
            return { ok: true, text: chosen.text };
        }""",
        {"index": index, "text": target_text, "keyword_groups": keyword_groups or []},
    )
    if not result.get("ok"):
        options = result.get("options") or []
        hint = f" Opsi terlihat: {options[:10]}" if options else ""
        raise RuntimeError(f"Gagal pilih dropdown '{target_text}': {result.get('reason')}.{hint}")
    await wait_ready(page, timeout_ms=5_000)
    return str(result["text"])


async def set_visible_input_by_index(page, index: int, value: str) -> None:
    result = await page.evaluate(
        """(payload) => {
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const inputs = [...document.querySelectorAll('input:not([type="hidden"])')].filter((el) => visible(el));
            const input = inputs[payload.index];
            if (!input) {
                return { ok: false, reason: `input index ${payload.index} tidak ditemukan` };
            }
            input.focus();
            input.value = payload.value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.blur();
            return { ok: true };
        }""",
        {"index": index, "value": value},
    )
    if not result.get("ok"):
        raise RuntimeError(f"Gagal isi input '{value}': {result.get('reason')}")
    await page.wait_for_timeout(300)


async def click_button_by_text(page, text: str) -> None:
    result = await page.evaluate(
        """(target) => {
            const norm = (value) => (value || '').replace(/\\s+/g, ' ').trim().toUpperCase();
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const button = [...document.querySelectorAll('button, a')]
                .find((el) => visible(el) && norm(el.textContent) === norm(target));
            if (!button) return false;
            button.click();
            return true;
        }""",
        text,
    )
    if not result:
        raise RuntimeError(f"Tombol '{text}' tidak ditemukan.")
    await page.wait_for_timeout(500)


async def row_count(page) -> int:
    return int(
        await page.evaluate(
            """() => {
                const visible = (el) => {
                    const style = getComputedStyle(el);
                    return style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && style.opacity !== '0'
                        && el.getClientRects().length > 0;
                };
                return [...document.querySelectorAll('table tbody tr')].filter((row) => visible(row)).length;
            }"""
        )
    )


async def add_funcloc_row(page) -> int:
    before = await row_count(page)
    await click_button_by_text(page, "Tambah FuncLoc")
    for _ in range(20):
        current = await row_count(page)
        if current > before:
            return current - 1
        await page.wait_for_timeout(300)
    raise RuntimeError("Baris FuncLoc baru tidak muncul.")


async def add_funcloc_rows(page, count: int) -> list[int]:
    rows: list[int] = []
    for _ in range(count):
        rows.append(await add_funcloc_row(page))
    return rows


async def set_row_short_text(page, row_index: int, target_text: str) -> None:
    keyword_groups = short_text_keyword_groups(target_text)
    last_result: dict | None = None
    for _ in range(30):
        result = await page.evaluate(
            """(payload) => {
                const norm = (value) => (value || '').replace(/\\s+/g, ' ').trim().toUpperCase();
                const fold = (value) => norm(value).replace(/[^A-Z0-9]+/g, '');
                const visible = (el) => {
                    const style = getComputedStyle(el);
                    return style.display !== 'none'
                        && style.visibility !== 'hidden'
                        && style.opacity !== '0'
                        && el.getClientRects().length > 0;
                };
                const rows = [...document.querySelectorAll('table tbody tr')].filter((row) => visible(row));
                const row = rows[payload.row_index];
                if (!row) {
                    return { ok: false, reason: `row ${payload.row_index} tidak ditemukan` };
                }

                const select = [...row.querySelectorAll('select')].find((el) => visible(el));
                if (!select) {
                    return { ok: false, reason: 'dropdown Short Text tidak ditemukan' };
                }

                const options = [...select.options].map((option) => ({
                    value: option.value,
                    text: norm(option.textContent),
                    folded: fold(option.textContent),
                }));
                const target = norm(payload.text);
                const targetFolded = fold(payload.text);

                let chosen = options.find((option) => option.text === target)
                    || options.find((option) => option.folded === targetFolded)
                    || options.find((option) => option.text.includes(target))
                    || options.find((option) => option.folded.includes(targetFolded));

                if (!chosen && payload.keyword_groups?.length) {
                    for (const group of payload.keyword_groups) {
                        const words = group.map((word) => fold(word)).filter(Boolean);
                        chosen = options.find((option) => words.every((word) => option.folded.includes(word)));
                        if (chosen) break;
                    }
                }

                if (!chosen) {
                    return {
                        ok: false,
                        reason: `Short Text '${payload.text}' tidak ada`,
                        options: options.map((option) => option.text).filter(Boolean),
                    };
                }

                select.value = chosen.value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                select.dispatchEvent(new Event('input', { bubbles: true }));
                return { ok: true };
            }""",
            {"row_index": row_index, "text": target_text, "keyword_groups": keyword_groups},
        )
        if result.get("ok"):
            await wait_ready(page, timeout_ms=5_000)
            return
        last_result = result
        await page.wait_for_timeout(500)

    options = (last_result or {}).get("options") or []
    hint = f" Opsi terlihat: {options[:15]}" if options else ""
    raise RuntimeError(f"Gagal pilih Short Text '{target_text}': {(last_result or {}).get('reason')}.{hint}")


async def set_row_start_finish(page, row_index: int, value: str) -> None:
    result = await page.evaluate(
        """(payload) => {
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const rows = [...document.querySelectorAll('table tbody tr')].filter((row) => visible(row));
            const row = rows[payload.row_index];
            if (!row) {
                return { ok: false, reason: `row ${payload.row_index} tidak ditemukan` };
            }

            const inputs = [...row.querySelectorAll('input:not([type="hidden"])')].filter((el) => visible(el));
            const target = inputs.find((el) => !el.readOnly && !el.disabled);
            if (!target) {
                return { ok: false, reason: 'input Start-Finish editable tidak ditemukan' };
            }

            target.focus();
            target.value = payload.value;
            target.dispatchEvent(new Event('input', { bubbles: true }));
            target.dispatchEvent(new Event('change', { bubbles: true }));
            target.blur();
            return { ok: true };
        }""",
        {"row_index": row_index, "value": value},
    )
    if not result.get("ok"):
        raise RuntimeError(f"Gagal isi Start-Finish Date: {result.get('reason')}")
    await page.wait_for_timeout(300)


async def set_row_operation_if_present(page, row_index: int, keyword_groups: list[list[str]]) -> None:
    result = await page.evaluate(
        """(payload) => {
            const norm = (value) => (value || '').replace(/\\s+/g, ' ').trim().toUpperCase();
            const visible = (el) => {
                const style = getComputedStyle(el);
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && style.opacity !== '0'
                    && el.getClientRects().length > 0;
            };
            const rows = [...document.querySelectorAll('table tbody tr')].filter((row) => visible(row));
            const row = rows[payload.row_index];
            if (!row) return { ok: false, skip: true };

            const selects = [...row.querySelectorAll('select')].filter((el) => visible(el));
            if (selects.length < 2) return { ok: true, skip: true };

            const select = selects[1];
            const current = norm(select.selectedOptions?.[0]?.textContent || '');
            if (current && !current.includes('PILIH')) return { ok: true, skip: true };

            const options = [...select.options].map((option) => ({
                value: option.value,
                text: norm(option.textContent),
            }));
            let chosen = null;
            for (const group of payload.keyword_groups || []) {
                const words = group.map(norm).filter(Boolean);
                chosen = options.find((option) => words.every((word) => option.text.includes(word)));
                if (chosen) break;
            }
            if (!chosen) return { ok: true, skip: true };

            select.value = chosen.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.dispatchEvent(new Event('input', { bubbles: true }));
            return { ok: true, skip: false };
        }""",
        {"row_index": row_index, "keyword_groups": keyword_groups},
    )
    if not result.get("ok"):
        raise RuntimeError("Gagal isi Operation.")
    await page.wait_for_timeout(200)


async def wait_submit_result(page) -> None:
    for _ in range(40):
        if "/show/" in page.url:
            await wait_ready(page, timeout_ms=5_000)
            return
        if await core.is_login_page(page):
            raise RuntimeError("Session kembali ke login saat submit.")
        await page.wait_for_timeout(500)
    await wait_ready(page, timeout_ms=5_000)


async def fill_top_form(page, job: JobConfig) -> None:
    config = TYPE_CONFIG[job.jenis]
    tanggal_program = tanggal_program_from_start_finish(job.start_finish)
    await set_visible_select_by_index(page, TOP_SELECT_INDEX["tipe"], "Perawatan")
    await set_visible_select_by_index(page, TOP_SELECT_INDEX["kategori"], "Sinyal")
    await set_visible_select_by_index(page, TOP_SELECT_INDEX["periode"], config["periode"])
    await set_visible_select_by_index(
        page,
        TOP_SELECT_INDEX["kode"],
        config["kode_label"],
        keyword_groups=config["kode_keywords"],
    )
    await set_visible_select_by_index(page, TOP_SELECT_INDEX["lokasi"], job.lokasi)
    await set_visible_input_by_index(page, TOP_INPUT_INDEX["tanggal_program"], tanggal_program)
    await set_visible_input_by_index(page, TOP_INPUT_INDEX["tanggal_realisasi"], "")
    await set_visible_input_by_index(page, TOP_INPUT_INDEX["jumlah_orang"], str(job.jumlah_orang))


async def fill_batch(page, job: JobConfig, batch_items: list[str]) -> None:
    config = TYPE_CONFIG[job.jenis]
    await fill_top_form(page, job)
    row_indexes = await add_funcloc_rows(page, len(batch_items))
    for row_index, item in zip(row_indexes, batch_items):
        await set_row_short_text(page, row_index, item)
        await set_row_start_finish(page, row_index, job.start_finish)
        await set_row_operation_if_present(page, row_index, config["operation_keywords"])


async def run_job(args: argparse.Namespace, login_data: dict | None, job: JobConfig) -> None:
    async with core.async_playwright() as pw:
        context = await core.create_browser_context(pw, Path.cwd(), show=args.show_browser)
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            batches = chunked(job.items, BATCH_SIZE)
            if args.show_browser:
                print("Browser tampil. Proses bisa dilihat langsung.")
            print(f"Mode tes. Isi batch 1/{len(batches)}: {len(batches[0])} item.")
            if len(batches) > 1:
                sisa = len(job.items) - len(batches[0])
                print(f"Mode tes hanya isi 5 item pertama. Sisa {sisa} item belum diproses.")
            await open_form_page(page, login_data)
            await fill_batch(page, job, batches[0])
            print("Mode tes selesai. Tidak klik Simpan/Kirim SAP.")
            if args.show_browser:
                input("Cek browser dulu. Tekan Enter untuk tutup browser...")
        finally:
            await context.close()


def menu(args: argparse.Namespace) -> None:
    while True:
        data = core.load_login_store()
        selected = data.get("selected") or "-"
        print()
        print("=== P3-STE Work Order ===")
        print(f"Login dipilih: {selected}")
        print("1. Buat data login")
        print("2. Pilih data login")
        print("3. Buat notif Work Order")
        print("0. Keluar")
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            core.create_login_data()
        elif choice == "2":
            core.choose_login_data()
        elif choice == "3":
            job = ask_job_config()
            asyncio.run(run_job(args, active_login_data(), job))
        elif choice == "0":
            return
        else:
            print("Pilihan tidak valid.")


def self_test() -> None:
    start_finish = parse_schedule("01072026 0800-2300")
    assert start_finish == "01/07/2026 08:00 - 01/07/2026 23:00"
    assert tanggal_program_from_start_finish(start_finish) == "01/07/2026"
    assert chunked(["A", "B", "C", "D", "E", "F"], 5) == [["A", "B", "C", "D", "E"], ["F"]]
    assert folded_text("SINYAL BLOK B.214 BOO-CLT") == "SINYALBLOKB214BOOCLT"
    assert ["ZP60", "BOO"] in short_text_keyword_groups("AXLE COUNTER ZP 60 BOO")
    assert ["JL92", "BOO"] in short_text_keyword_groups("SINYAL KELUAR DAN LANGSIR JL92 BOO")
    print("Self-test OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Buat notif Work Order P3-STE.")
    parser.set_defaults(show_browser=True)
    parser.add_argument("--show-browser", dest="show_browser", action="store_true", help="Tampilkan browser")
    parser.add_argument("--headless", dest="show_browser", action="store_false", help="Sembunyikan browser")
    parser.add_argument("--self-test", action="store_true", help="Cek fungsi dasar tanpa buka browser")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    menu(args)


if __name__ == "__main__":
    main()
