"""Jawaban UTS Big Data - VERSI 2: validasi rinci per ZOM / per grid ERA5 / per tahun.

Beda dari versi 1: versi 1 memakai rata-rata 6 grid ERA5 dan satu baris rata-rata 5 ZOM.
Versi 2 memecah semuanya: MAE per ZOM, MAE per grid ERA5, MAE per tahun, dan memilih grid
ERA5 terdekat ke pusat Kabupaten Kebumen.

Jalankan: .venv/bin/python jawaban_uts2.py   (venv ada di folder ini)
"""
from pathlib import Path

import pandas as pd
import xarray as xr
import fitz

ROOT = Path(__file__).resolve().parent          # semua input & output di folder ini
PDF = ROOT / "BMKG_Pemutakhiran_ZOM_1991-2020.pdf"
NC = ROOT / "reanalysis-era5-single-levels-timeseries-sfcs2bqs4hp.nc"
OUT = ROOT
ZOM = ["JATENG_16", "JATENG_17", "JATENG_18", "JATENG_19", "JATENG_20"]
NO_ZOM = dict(zip(ZOM, range(229, 234)))        # NO.ZOM nasional, hal. 79
DAERAH = {
    "JATENG_16": "Banjarnegara selatan, Kebumen utara, sebagian kecil Wonosobo barat laut",
    "JATENG_17": "Sebagian kecil Banyumas tenggara, Cilacap timur, sebagian besar Kebumen",
    "JATENG_18": "Purworejo selatan, Kebumen timur",
    "JATENG_19": "Sebagian kecil Kebumen timur, Purworejo barat laut, Wonosobo barat daya",
    "JATENG_20": "Sebagian Banjarnegara tenggara, sebagian kecil Kebumen timur laut, Wonosobo tengah",
}
HAL_DASARIAN = range(117, 129)                  # lampiran E, hal. 107-118
RENTANG = ("2024-01-01", "2025-12-31")
PUSAT = (-7.7167, 109.6667)                     # pusat administratif Kab. Kebumen
BULAN = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGT", "SEP", "OKT", "NOV", "DES"]
KOL = [f"{b} {r}" for b in BULAN for r in ("I", "II", "III")]


def dasarian(t):
    return (t.month - 1) * 3 + (1 if t.day <= 10 else 2 if t.day <= 20 else 3)


def bmkg_dasarian():
    doc = fitz.open(PDF)
    tabel = {}
    for idx in HAL_DASARIAN:
        ws = doc[idx].get_text("words")
        ys = sorted({w[1] for w in ws})
        grup = []
        for y in ys:
            if grup and y - grup[-1][-1] <= 3:
                grup[-1].append(y)
            else:
                grup.append([y])
        for g in grup:
            sel = [w[4] for w in sorted([w for w in ws if min(g) - .01 <= w[1] <= max(g) + .01],
                                        key=lambda w: w[0])]
            if len(sel) == 38 and all(s.isdigit() for s in sel):
                tabel[int(sel[0])] = [int(v) for v in sel[1:37]]
    doc.close()
    assert all(NO_ZOM[z] in tabel for z in ZOM), "NO.ZOM tidak ketemu di lampiran E"
    df = pd.DataFrame({z: tabel[NO_ZOM[z]] for z in ZOM}, index=KOL).T
    df.insert(0, "NO_ZOM", [NO_ZOM[z] for z in ZOM])
    df.insert(1, "Daerah", [DAERAH[z] for z in ZOM])
    return df


def era5():
    """Dasarian per grid (36x6) dan per tahun per grid (36x6x2)."""
    ds = xr.open_dataset(NC)
    tp = (ds["tp"] * 1000).sel(valid_time=slice(*RENTANG))       # m/jam -> mm
    df = tp.to_dataframe().reset_index()
    df["tahun"] = df["valid_time"].dt.year
    df["no"] = [dasarian(t) for t in df["valid_time"]]
    df["grid"] = df["latitude"].astype(str) + "," + df["longitude"].astype(str)
    per_tahun = {y: df[df.tahun == y].groupby(["no", "grid"])["tp"].sum().unstack("grid")
                 .reindex(range(1, 37)) for y in sorted(df.tahun.unique())}
    per_tahun = {y: g.set_axis(KOL) for y, g in per_tahun.items()}
    # rata-rata antar tahun (bukan jumlah) agar setara dengan normal BMKG per tahun
    das = pd.concat(per_tahun.values()).groupby(level=0).mean().reindex(KOL)
    return das, per_tahun


def mae(a, b):
    return float((a - b).abs().mean())


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # --- Bagian 1: BMKG ---
    bmkg = bmkg_dasarian()
    y1 = bmkg.drop(columns=["NO_ZOM", "Daerah"]).mean(axis=0)    # rata-rata 5 ZOM
    bmkg.to_csv(OUT / "1_bmkg_dasarian_perZOM.csv", index=False)
    print("BAGIAN 1: BMKG 5 ZOM x 36 dasarian, total rata-rata", round(y1.sum(), 1), "mm/tahun")

    # --- Bagian 2: ERA5 per grid ---
    das, per_tahun = era5()
    das_tampil = das.rename(columns=lambda c: f"ERA5 {c}")
    das_tampil.to_csv(OUT / "2_era5_dasarian_perGrid.csv", index_label="Dasarian")
    rata_grid = das.mean(axis=1)                                # rata-rata 6 grid (pembanding v1)
    print("BAGIAN 2: grid", list(das.columns), "| MAE rata-rata grid =", round(mae(y1, rata_grid), 2))

    # grid terdekat ke pusat Kab. Kebumen
    grid_list = [tuple(map(float, c.split(","))) for c in das.columns]
    dekat = min(grid_list, key=lambda g: (g[0] - PUSAT[0]) ** 2 + (g[1] - PUSAT[1]) ** 2)
    dekat = f"{dekat[0]},{dekat[1]}"

    # --- Bagian 3: MAE per ZOM / per grid / per tahun ---
    per_zom = pd.DataFrame({"MAE (mm)": {z: mae(bmkg.loc[z].drop(["NO_ZOM", "Daerah"]).astype(float),
                                                   rata_grid) for z in ZOM}})
    per_zom.index.name = "ZOM"
    per_grid = pd.DataFrame({"MAE (mm)": {c: mae(y1, das[c]) for c in das.columns}})
    per_grid.index.name = "Grid ERA5"
    per_tahun_df = pd.DataFrame({"MAE (mm)": {str(y): mae(y1, g.mean(axis=1)) for y, g in per_tahun.items()}})
    per_tahun_df.index.name = "Tahun"
    print("BAGIAN 3: MAE per ZOM", {k: round(v, 1) for k, v in per_zom["MAE (mm)"].items()})
    print("          MAE per grid", {k: round(v, 1) for k, v in per_grid["MAE (mm)"].items()})
    print("          MAE per tahun", {k: round(v, 1) for k, v in per_tahun_df["MAE (mm)"].items()})

    # tabel detail 36 baris (padanan slide 7)
    detail = pd.DataFrame({"No": range(1, 37), "Dasarian": KOL,
                           "BMKG rata-rata 5 ZOM": y1.values.round(1),
                           f"ERA5 {dekat} (terdekat)": das[dekat].values.round(1),
                           "ERA5 rata-rata 6 grid": rata_grid.values.round(1)})
    detail["Selisih"] = (detail["BMKG rata-rata 5 ZOM"] - detail[f"ERA5 {dekat} (terdekat)"]).round(1)
    detail["Nilai Mutlak"] = detail["Selisih"].abs()
    detail.to_csv(OUT / "3_validasi_detail_perDasarian.csv", index=False)

    mae_terpilih = detail["Nilai Mutlak"].mean()
    rekap = {"MAE (BMKG vs rata-rata 6 grid)": round(mae(y1, rata_grid), 2),
             f"MAE (BMKG vs grid {dekat})": round(mae_terpilih, 2),
             "MAE terbaik antar grid": round(per_grid["MAE (mm)"].min(), 2),
             "Grid terbaik": per_grid["MAE (mm)"].idxmin(),
             "MAE terburuk antar ZOM": round(per_zom["MAE (mm)"].max(), 2),
             "ZOM terburuk": per_zom["MAE (mm)"].idxmax()}
    rekap_df = pd.Series(rekap, name="Nilai").rename_axis("Keterangan")
    rekap_df.to_csv(OUT / "3_rekap_MAE.csv")

    with pd.ExcelWriter(OUT / "Jawaban_UTS2_BigData.xlsx") as w:
        detail.to_excel(w, sheet_name="3.Validasi detail", index=False)
        per_zom.to_excel(w, sheet_name="3.MAE per ZOM")
        per_grid.to_excel(w, sheet_name="3.MAE per grid")
        per_tahun_df.to_excel(w, sheet_name="3.MAE per tahun")
        rekap_df.to_frame().to_excel(w, sheet_name="3.Rekap MAE")
        bmkg.T.to_excel(w, sheet_name="1.BMKG per ZOM")
        das_tampil.to_excel(w, sheet_name="2.ERA5 per grid")
        for y, g in per_tahun.items():
            g.rename(columns=lambda c: f"ERA5 {c}").to_excel(w, sheet_name=f"2.ERA5 {y}")
    print("Workbook:", OUT / "Jawaban_UTS2_BigData.xlsx")

    # --- Bagian 4: grafik + README ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 6))
    for c in das.columns:
        ax.plot(range(1, 37), das[c], lw=1.2, alpha=.8, label=f"ERA5 grid {c}")
    ax.plot(range(1, 37), y1, "k-o", ms=4, lw=2.5, label="BMKG rata-rata 5 ZOM")
    ax.set_xticks(range(1, 37))
    ax.set_xticklabels(KOL, rotation=90, fontsize=7)
    ax.set_xlabel("Dasarian")
    ax.set_ylabel("Curah hujan (mm/dasarian)")
    ax.set_title("Versi 2 - Sebaran 6 grid ERA5 vs BMKG, Kebumen | "
                 f"MAE rata-rata grid = {rekap['MAE (BMKG vs rata-rata 6 grid)']} mm")
    ax.grid(alpha=.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "grafik_uts2_grid_era5.png", dpi=200)

    luar = detail["Nilai Mutlak"]
    (OUT / "README.md").write_text(f"""# Jawaban UTS Big Data - Versi 2 (rinci per ZOM / per grid / per tahun)

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
Rata-rata 5 ZOM = {y1.sum():.1f} mm/tahun (terbasah dasarian {y1.idxmax()} = {y1.max():.1f} mm,
terkering {y1.idxmin()} = {y1.min():.1f} mm). Inkonsistensi bawaan dokumen: JUMLAH/CH_THN (JATENG_16
2755) != jumlah 36 dasarian (3433) - dipakai tabel dasarian karena soal minta nilai dasarian.

## Bagian 2 - ERA5 per grid
tp per jam (m) x 1000 -> mm, dijumlahkan per dasarian per grid, tanpa dirata-ratakan lebih dulu.
Grid terdekat pusat Kabupaten Kebumen ({PUSAT[0]}, {PUSAT[1]}) = **{dekat}**.

## Bagian 3 - Validasi MAE
MAE = (1/36) SUM |y1 - y2|.

| Cakupan | MAE (mm/dasarian) |
|---|---|
| BMKG vs rata-rata 6 grid ERA5 | {rekap['MAE (BMKG vs rata-rata 6 grid)']} |
| BMKG vs grid terdekat ({dekat}) | {rekap[f'MAE (BMKG vs grid {dekat})']} |
| Terbaik antar grid | {rekap['MAE terbaik antar grid']} (grid {rekap['Grid terbaik']}) |
| Terburuk antar ZOM | {rekap['MAE terburuk antar ZOM']} ({rekap['ZOM terburuk']}) |

Per ZOM: {', '.join(f'{k} = {v:.1f}' for k, v in per_zom['MAE (mm)'].items())}
Per grid: {', '.join(f'{k} = {v:.1f}' for k, v in per_grid['MAE (mm)'].items())}
Per tahun: {', '.join(f'{k} = {v:.1f}' for k, v in per_tahun_df['MAE (mm)'].items())}

Dasarian paling menyimpang: {luar.idxmax()} ({detail.loc[luar.idxmax(), 'Dasarian']}, mutlak {luar.max():.1f} mm);
paling cocok: {luar.idxmin()} ({detail.loc[luar.idxmin(), 'Dasarian']}, mutlak {luar.min():.1f} mm).

## Kesimpulan
Mengganti rata-rata dengan per-grid tidak menurunkan MAE secara berarti (selisih antar grid kecil),
artinya kesalahan bukan soal pemilihan grid melainkan perbedaan iklim antara satu titik dan zona
ZOM 5 kabupaten/wonosobo/banjarnegara. Koreksi terbesar tetap pada dasarian transisi musim.
""")
    print("BAGIAN 4 selesai:", OUT / "README.md")


if __name__ == "__main__":
    main()