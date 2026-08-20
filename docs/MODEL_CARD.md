# Model Card - Multisource Multicrop SD 1.5 LoRA

Status: model training selesai dan artefak tervalidasi; evaluasi manusia masih
pending.

## Pilot Profile

Pilot pertama adalah LoRA padi publik satu kelas dengan trigger
`gaus_padi_public`, konfigurasi `pilot_padi.yaml`, 800 langkah, dan checkpoint
setiap 200 langkah. Pilot tidak mewakili visual lokal Aikmel dan bukan model
utama empat kelas.

## Model

- Base model: `stable-diffusion-v1-5/stable-diffusion-v1-5`
- Adapter: satu LoRA gabungan
- Output: `multisource_multicrop_lora.safetensors`
- Run ID: `20260820T143551Z`
- Size: 6.414.992 byte; 256 tensor
- SHA-256:
  `0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a`
- Classes: padi, jagung, cabai, kacang tanah
- Triggers: `taniadaptif_padi`, `taniadaptif_jagung`, `taniadaptif_cabai`,
  `taniadaptif_kacang_tanah`

## Intended Use

Model menghasilkan simulasi visual dari rekomendasi rule-based TaniAdaptif.
Model tidak menentukan komoditas, menggantikan BMKG, mendiagnosis penyakit,
atau membuktikan representasi lokal Aikmel.

## Training Data

Padi memakai public + local_aikmel; kelas lain public-only. Dataset final berisi
389 gambar: padi 95, jagung 100, cabai 97, dan kacang tanah 97. Split
stratified terdiri atas 312 train dan 77 validation. Review manusia dataset
menghasilkan 390 accepted dan 85 rejected sebelum pembatasan jagung menjadi 100.
Peringatan provenance lama dan dominasi sumber publik tetap dicatat sebagai
keterbatasan.

## Baseline Configuration

Sumber: `ml_pipeline/configs/training_public_multicrop.yaml`

- Resolution: 512
- Rank: 8
- Batch size: 1
- Gradient accumulation: 4
- Max steps: 1600
- Checkpoint interval: 200
- Mixed precision: fp16

Training aktual mencapai smoke 100 langkah dan main 1.600 langkah menggunakan
AdamW 8-bit pada 2 x Tesla T4. Konfigurasi baseline bukan klaim konfigurasi
terbaik.

## Evaluation

Evaluasi otomatis menghasilkan 36 kondisi berpasangan atau 72 gambar base dan
LoRA, ditambah empat sanity image. Seluruh file dan hash valid. Brightness,
contrast, dan entropy hanya proxy deskriptif. Gunakan contact sheet pada
`artifacts/model_evaluation/kaggle_run_20260820T143551Z/` dan
`docs/EVALUATION_RUBRIC.md` untuk menilai kualitas visual, identitas kelas,
prompt adherence, relevansi pertanian, class correctness, dan mixed crop. Semua
72 field penilaian tetap kosong sampai review manusia.

## Limitations

- Foto public tidak membuktikan representasi lokal Aikmel; dokumentasi lokal
  hanya tersedia untuk sebagian data padi.
- Output dapat mengandung artefak atau class confusion.
- QA pendahuluan menunjukkan padi serta sebagian cabai/kacang tanah perlu
  pemeriksaan identitas dan konteks lebih ketat; ini belum merupakan skor
  manusia.
- Kondisi agronomi pada gambar bukan prediksi ilmiah.
- Fallback empat adapter belum dilatih.
