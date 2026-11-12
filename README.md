# Jawaban UTS Big Data - Versi 2 (rinci per ZOM / per grid / per tahun)

Versi ini menjawab soal yang sama seperti `Jawaban_UTS/` tetapi memecah hasilnya, bukan satu baris
rata-rata: setiap ZOM, setiap grid ERA5, dan setiap tahun dinilai sendiri. Folder mandiri (input,
venv, skrip, hasil).

## Cara menjalankan

```bash
bash setup_venv.sh
.venv/bin/python jawaban_uts2.py
```

## Isi folder

| File | Isi |
|---|---|
| `jawaban_uts2.py` | skrip: BMKG dari PDF + ERA5 per grid -> MAE -> grafik -> README ini |
| `BMKG_Pemutakhiran_ZOM_1991-2020.pdf` | buku normal hujan dasarian BMKG (lampiran E hal. 107-118) |
| `reanalysis-era5-single-levels-timeseries-sfcs2bqs4hp.nc` | ERA5 CDS tp per jam 2024-2025, 6 grid |
| `Jawaban_UTS2_BigData.xlsx` | jawaban lengkap, sheet 1./2./3. per bagian |
| `1_bmkg_dasarian_perZOM.csv` | BMKG 5 ZOM x 36 dasarian |
| `2_era5_dasarian_perGrid.csv` | ERA5 36 dasarian x 6 grid (dan sheet per tahun) |
| `3_validasi_detail_perDasarian.csv` | tabel detail 36 dasarian (padanan slide 7) |
| `3_rekap_MAE.csv` | rekap MAE versi 2 |
| `grafik_uts2_grid_era5.png` | sebaran 6 grid ERA5 vs BMKG |
| `requirements.txt`, `setup_venv.sh` | dependency + pembuat venv |

## Bagian 1 - BMKG
5 ZOM Kebumen (JATENG_16-20 = NO.ZOM 229-233, hal. 79), 36 nilai dasarian tiap ZOM dari lampiran E.
Rata-rata 5 ZOM = 3111.8 mm/tahun (terbasah dasarian DES I = 164.6 mm,
terkering AGT I = 7.6 mm). Inkonsistensi bawaan dokumen: JUMLAH/CH_THN (JATENG_16
2755) != jumlah 36 dasarian (3433) - dipakai tabel dasarian karena soal minta nilai dasarian.

## Bagian 2 - ERA5 per grid
tp per jam (m) x 1000 -> mm, dijumlahkan per dasarian per grid, tanpa dirata-ratakan lebih dulu.
Grid terdekat pusat Kabupaten Kebumen (-7.7167, 109.6667) = **-7.75,109.75**.

## Bagian 3 - Validasi MAE
MAE = (1/36) SUM |y1 - y2|.

| Cakupan | MAE (mm/dasarian) |
|---|---|
| BMKG vs rata-rata 6 grid ERA5 | 36.32 |
| BMKG vs grid terdekat (-7.75,109.75) | 36.09 |
| Terbaik antar grid | 31.26 (grid -7.75,109.25) |
| Terburuk antar ZOM | 39.25 (JATENG_18) |

Per ZOM: JATENG_16 = 36.7, JATENG_17 = 34.9, JATENG_18 = 39.3, JATENG_19 = 37.7, JATENG_20 = 39.2
Per grid: -7.5,109.25 = 36.1, -7.5,109.5 = 39.2, -7.5,109.75 = 48.3, -7.75,109.25 = 31.3, -7.75,109.5 = 32.3, -7.75,109.75 = 36.1
Per tahun: 2024 = 35.3, 2025 = 62.4

Dasarian paling menyimpang: 29 (OKT III, mutlak 179.2 mm);
paling cocok: 20 (JUL III, mutlak 1.5 mm).

## Kesimpulan
Mengganti rata-rata dengan per-grid tidak menurunkan MAE secara berarti (selisih antar grid kecil),
artinya kesalahan bukan soal pemilihan grid melainkan perbedaan iklim antara satu titik dan zona
ZOM 5 kabupaten/wonosobo/banjarnegara. Koreksi terbesar tetap pada dasarian transisi musim.
