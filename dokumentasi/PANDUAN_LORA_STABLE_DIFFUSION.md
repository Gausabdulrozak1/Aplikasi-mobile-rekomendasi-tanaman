# Panduan LoRA Stable Diffusion untuk TaniAdaptif

Panduan ini menyiapkan training LoRA tanaman untuk aplikasi TaniAdaptif dengan target:

- Platform training: Google Colab Free Tier dengan GPU T4.
- Base model: `stable-diffusion-v1-5/stable-diffusion-v1-5`.
- Tool: Kohya/sd-scripts via notebook Colab.
- Dataset: 80-100 gambar per kelas.
- Kelas: padi, jagung, cabai, kacang tanah.

Catatan pilihan tool: untuk Colab, saya pilih jalur Kohya/sd-scripts CLI, bukan GUI penuh. Ini lebih stabil di Colab karena tidak bergantung pada tunnel/Gradio. Mesin training-nya tetap ekosistem Kohya.

## Prinsip Aman untuk Laptop

Laptop AMD Ryzen 3 5300U jangan dipakai untuk training LoRA atau generate Stable Diffusion berat.

Yang boleh dilakukan di laptop:

- Buka Google Colab.
- Upload dan rapikan dataset di Google Drive.
- Edit kode Flutter, Node.js, atau dokumen.
- Menjalankan backend aplikasi biasa.

Yang jangan dilakukan di laptop:

- Menjalankan Kohya training lokal.
- Menjalankan Stable Diffusion WebUI lokal.
- Menjalankan ComfyUI lokal dengan model besar.
- Install CUDA/PyTorch GPU lokal untuk training.

Semua proses berat dilakukan di Colab. Laptop hanya menjadi kontrol/browser.

## Struktur Dataset di Google Drive

Buat folder seperti ini di Google Drive:

```text
MyDrive/
  TaniAdaptif/
    dataset_lora/
      train/
        5_ta_padi/
        5_ta_jagung/
        5_ta_cabai/
        5_ta_kacang_tanah/
      output/
      logs/
```

Angka `5_` berarti gambar dalam folder itu diulang 5 kali oleh trainer. Dengan 80-100 gambar per kelas, repeat 5 cukup masuk akal untuk eksperimen awal di T4.

## Trigger Token

Gunakan token khusus berikut:

| Kelas | Trigger token |
| --- | --- |
| Padi | `ta_padi` |
| Jagung | `ta_jagung` |
| Cabai | `ta_cabai` |
| Kacang tanah | `ta_kacang_tanah` |

Trigger token wajib muncul di awal caption setiap gambar.

## Format Caption

Setiap gambar harus punya file `.txt` dengan nama yang sama.

Contoh:

```text
padi_001.jpg
padi_001.txt
```

Isi `padi_001.txt`:

```text
ta_padi, rice plant, rice field, vegetative stage, wet soil, cloudy weather, realistic agricultural photo
```

Contoh caption per kelas:

```text
ta_padi, rice plant, rice field, seedling stage, wet soil, realistic agricultural photo
ta_jagung, corn plant, dry field, vegetative stage, tropical farm, realistic agricultural photo
ta_cabai, chili plant, red chili fruit, garden bed, sunny weather, realistic agricultural photo
ta_kacang_tanah, peanut plant, mixed garden, low bush plant, dry soil, realistic agricultural photo
```

Gunakan Bahasa Inggris sederhana untuk caption karena Stable Diffusion 1.5 lebih kuat memahami prompt Inggris.

## Kualitas Dataset

Target minimal:

- 80-100 gambar padi.
- 80-100 gambar jagung.
- 80-100 gambar cabai.
- 80-100 gambar kacang tanah.

Prioritaskan:

- Foto jelas, tidak buram.
- Tanaman menjadi subjek utama.
- Variasi tahap tumbuh: bibit, vegetatif, berbunga/berbuah, siap panen.
- Variasi kondisi lahan: sawah, tegalan, kebun campur.
- Variasi cuaca/lahan: basah, normal, kering.

Hindari:

- Gambar dengan watermark besar.
- Gambar terlalu gelap.
- Foto terlalu banyak objek lain.
- Duplikasi gambar yang sama.
- Gambar hasil AI untuk dataset utama, kecuali dipisahkan sebagai eksperimen.

## Setting Training Awal

Setting awal yang aman untuk T4:

```text
resolution: 512
train_batch_size: 1
mixed_precision: fp16
save_precision: fp16
network_dim: 32
network_alpha: 16
optimizer: AdamW8bit
learning_rate: 1e-4
text_encoder_lr: 5e-5
max_train_epochs: 4
cache_latents: true
gradient_checkpointing: true
```

Jika Colab kehabisan VRAM:

1. Turunkan `network_dim` dari `32` ke `16`.
2. Pastikan `train_batch_size` tetap `1`.
3. Matikan preview/sample yang terlalu sering.
4. Restart runtime Colab, lalu lanjutkan.

## Alur Kerja

1. Siapkan dataset di Google Drive.
2. Pastikan tiap gambar punya caption `.txt`.
3. Buka notebook `dokumentasi/tani_adaptif_lora_sd15_colab.ipynb` di Google Colab.
4. Pilih runtime GPU T4.
5. Jalankan validasi dataset.
6. Jalankan training.
7. Ambil hasil `.safetensors` dari folder:

```text
MyDrive/TaniAdaptif/dataset_lora/output/
```

## Nama Output LoRA

Output awal:

```text
taniadaptif_sd15_lora.safetensors
```

File ini nanti dipakai oleh backend AI untuk generate gambar simulasi tanaman.

## Prompt Uji Setelah Training

Padi:

```text
ta_padi, rice plant in a rice field, vegetative stage, wet soil, cloudy tropical weather, realistic agricultural photo
```

Jagung:

```text
ta_jagung, corn plant in dry field, healthy green leaves, sunny tropical weather, realistic agricultural photo
```

Cabai:

```text
ta_cabai, chili plant with red chili fruit, garden bed, realistic agricultural photo
```

Kacang tanah:

```text
ta_kacang_tanah, peanut plant in mixed garden, low bush plant, dry soil, realistic agricultural photo
```

Negative prompt:

```text
cartoon, illustration, blurry, low quality, deformed plant, watermark, text, logo, human, animal
```

## Integrasi ke Aplikasi

Setelah LoRA jadi, tahap berikutnya:

1. Simpan LoRA `.safetensors`.
2. Buat backend AI bisa memuat base model SD 1.5 + LoRA.
3. Endpoint `/generate` mengembalikan URL gambar asli.
4. Flutter menampilkan gambar dari `gambar_url`.

Untuk laptop lokal, mode default backend AI tetap `mock`. Mode Stable Diffusion berat sebaiknya dijalankan di Colab, server GPU cloud, atau mesin dengan GPU khusus.

