from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

DATE_RE = re.compile(r"^\d{1,2}[-_/]\d{1,2}[-_/]\d{2,4}$")


def file_key(path: Path, words: int = 3) -> str:
    # ponytail: pakai prefix 3 kata + skip tanggal awal; cukup buat beda bulan.
    parts = [part.strip(".,;:()[]{}") for part in re.split(r"[\s_]+", path.stem) if part]
    if parts and DATE_RE.match(parts[0]):
        parts = parts[1:]
    return " ".join(parts[:words]).upper()


def scan(folder: Path, words: int = 3) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for item in folder.iterdir():
        if item.is_file() and item.suffix.lower() == ".pdf":
            groups[file_key(item, words)].append(item.name)
    return dict(groups)


def print_report(label_a: str, a: dict[str, list[str]], label_b: str, b: dict[str, list[str]]) -> None:
    keys = sorted(set(a) | set(b))
    diff_found = False

    for key in keys:
        files_a = sorted(a.get(key, []))
        files_b = sorted(b.get(key, []))
        if len(files_a) == len(files_b):
            continue

        diff_found = True
        # ponytail: beda hitung prefix = kandidat grup file yang kurang.
        if len(files_a) > len(files_b):
            print(f"[{label_b} kurang {len(files_a) - len(files_b)}] {key}")
        else:
            print(f"[{label_a} kurang {len(files_b) - len(files_a)}] {key}")

        print(f"  {label_a}:")
        for name in files_a:
            print(f"    - {name}")
        print(f"  {label_b}:")
        for name in files_b:
            print(f"    - {name}")

    if not diff_found:
        print("Aman. Hitung prefix 3 kata sama.")


def self_test() -> None:
    assert file_key(Path(r"17-06-2026_PERAWATAN WESEL ELEKTRIK 2 MINGGUAN_Serpong(1).pdf")) == "PERAWATAN WESEL ELEKTRIK"
    assert file_key(Path(r"PERAWATAN PERAGA SINYAL ELEKTRIK.pdf")) == "PERAWATAN PERAGA SINYAL"
    print("Self-test OK")


def ask_folder(label: str) -> Path:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title=f"Pilih folder {label}")
        root.destroy()
        if not selected:
            raise SystemExit("Folder belum dipilih. Batal.")
        path = Path(selected)
    except Exception:
        raw = input(f"Path folder {label}: ").strip().strip('"')
        if not raw:
            raise SystemExit("Path kosong. Batal.")
        path = Path(raw)

    if not path.is_dir():
        raise SystemExit(f"Folder tidak ada: {path}")
    return path


def ask_words() -> int:
    raw = input("Bandingkan berapa kata pertama? [3]: ").strip()
    if not raw:
        return 3
    try:
        words = int(raw)
    except ValueError:
        raise SystemExit("Harus angka.")
    if words < 1:
        raise SystemExit("Minimal 1.")
    return words


def main() -> None:
    parser = argparse.ArgumentParser(description="Bandingkan 2 folder PDF pakai prefix nama file.")
    parser.add_argument("--self-test", action="store_true", help="Jalankan cek cepat")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    words = ask_words()
    folder_a = ask_folder("A")
    folder_b = ask_folder("B")

    scan_a = scan(folder_a, words)
    scan_b = scan(folder_b, words)

    total_a = sum(len(v) for v in scan_a.values())
    total_b = sum(len(v) for v in scan_b.values())
    print(f"A: {folder_a} ({total_a} PDF, {len(scan_a)} key)")
    print(f"B: {folder_b} ({total_b} PDF, {len(scan_b)} key)")
    print()
    print_report(str(folder_a), scan_a, str(folder_b), scan_b)


if __name__ == "__main__":
    main()
