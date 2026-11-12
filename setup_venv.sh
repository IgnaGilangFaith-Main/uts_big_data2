#!/usr/bin/env bash
# Siapkan lingkungan di folder ini (dipakai kalau .venv belum ada / dipindah ke komputer lain).
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
echo "Selesai. Jalankan: .venv/bin/python jawaban_uts.py"
