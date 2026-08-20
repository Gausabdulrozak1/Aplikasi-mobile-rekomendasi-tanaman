# ML Pipeline TaniAdaptif

Pipeline audit, kurasi, caption, split, dan eksperimen LoRA Stable Diffusion
1.5 untuk empat komoditas.

## Pilot Publik Satu Kelas

Eksperimen pertama tetap tersedia melalui
`configs/pilot_padi.yaml` dengan satu kelas `padi`, trigger
`gaus_padi_public`, maksimum 100 gambar, 800 langkah, dan checkpoint setiap
200 langkah, dengan dataloader worker 0. Pilot ini memakai gambar publik dan
tidak boleh diklaim sebagai representasi lokal Aikmel. Variabel
`TANIADAPTIF_CONFIG` yang dipilih saat preparation juga digunakan notebook
train/evaluate. Trigger pilot tidak menggantikan trigger final empat kelas di
bawah.

| Class ID | Trigger final | Sumber final | Target kurasi |
| --- | --- | --- | ---: |
| `padi` | `taniadaptif_padi` | `public` + `local_aikmel` | 80-100 |
| `jagung` | `taniadaptif_jagung` | `public` | 80-100 |
| `cabai` | `taniadaptif_cabai` | `public` | 80-100 |
| `kacang_tanah` | `taniadaptif_kacang_tanah` | `public` | 80-100 |

Tidak ada kewajiban atau rencana pengumpulan foto lokal untuk jagung, cabai,
dan kacang tanah. Foto publik tidak diberi klaim lokal. Stable Diffusion hanya
membuat simulasi visual; rekomendasi tanaman tetap berasal dari rule engine
dan data BMKG.

## Struktur Raw

Struktur logis sumber:

```text
data/raw/padi/public/
data/raw/padi/local_aikmel/
data/raw/jagung/public/
data/raw/cabai/public/
data/raw/kacang_tanah/public/
```

Folder fisik tiga kelas public-only saat ini bernama `publik/`. Konfigurasi
memetakannya ke `source_type: public`, sehingga raw tidak perlu dipindahkan.
Pipeline tidak mengubah atau menghapus file raw.

Provenance per gambar disimpan di
`data/dataset_source_manifest.csv`. Nilai sumber, lisensi, izin, tanggal,
lokasi, dan review yang belum diketahui tetap kosong dan dilaporkan melalui
`data/reports/provenance_warnings.csv`.

## Setup Lokal Ringan

```powershell
cd D:\TaniAdaptif
.\.venv\Scripts\python.exe -m pip install -r ml_pipeline\requirements\dev.txt
```

Requirements lokal tidak memasang Torch, Diffusers, Transformers,
Accelerate, xFormers, atau BitsAndBytes.

## CLI

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli audit --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli prepare --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli screen --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli validate --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli report --config ml_pipeline\configs\dataset_public_multicrop.yaml --all-classes
```

`prepare` menyiapkan kandidat dan gate review. Dataset final 80/20 dengan seed
42, isolasi kelompok duplikat, dan metadata source-aware hanya dibuat setelah
seluruh keputusan review yang diwajibkan tersedia.

`screen` menjalankan proxy CPU ringan (ketajaman, entropi, pencahayaan,
proporsi piksel hijau, border-edge, dan indikasi close-up). Proxy tidak
mengklaim klasifikasi semantik dan tidak menggantikan gate review manusia.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest ml_pipeline\tests -q
.\.venv\Scripts\python.exe -m ruff check ml_pipeline
.\.venv\Scripts\python.exe -m ruff format --check ml_pipeline
```

Fixture test dibuat di temporary directory dan tidak menggantikan dataset
penelitian.

Validasi ulang gerbang paket final dan tulis laporan Markdown/JSON:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.dataset.cli validate-package `
  --config ml_pipeline/configs/dataset_public_multicrop.yaml `
  --all-classes
```

Artefak training yang disinkronkan dari Colab dapat diperiksa tanpa memuat
model atau memasang Torch:

```powershell
.\.venv\Scripts\python.exe -m ml_pipeline.src.training.validate_run `
  --output-dir D:\path\to\synced_smoke_output `
  --expected-steps 100 `
  --lora-filename multisource_multicrop_smoke_lora.safetensors
```

Validator menolak manifest non-success, checkpoint akhir tanpa file, struktur
SafeTensors yang tidak valid atau tanpa tensor data, loss non-finite, fatal
log, environment tanpa GPU, atau validation image empat kelas yang tidak dapat
dibuka sebagai gambar.

Untuk pipeline multicrop, nama LoRA canonical hanya didefinisikan pada
`configs/training_public_multicrop.yaml`. Notebook training menormalisasi
keluaran default Diffusers `pytorch_lora_weights.safetensors` ke nama tersebut
tanpa menghapus file default dan tanpa training ulang jika canonical sudah
valid.

## Kaggle GPU - Jalur Final

Upload paket fixed berikut sebagai Kaggle Dataset private:

```text
artifacts/dataset_packages/dataset_multicrop_v1_kaggle_fixed.zip
```

Import notebook standalone berikut, Add Input, aktifkan GPU dan Internet, lalu
jalankan **Run All**:

```text
ml_pipeline/notebooks/00_train_lora_multicrop_kaggle_final.ipynb
```

Notebook memverifikasi SHA paket, decode seluruh dataset, melakukan loader
probe, smoke 100 langkah, main 1600 langkah, sanity, evaluasi, dan export.
Training tidak dijalankan di laptop lokal. Ikuti
`docs/KAGGLE_FINAL_RUN_GUIDE.md`. Notebook Colab dipertahankan sebagai bukti
historis dan bukan entrypoint final.
