# Multicrop LoRA Strategy

## Ruang Lingkup

Eksperimen mencakup empat komoditas:

| Komoditas | Trigger final | Sumber |
| --- | --- | --- |
| Padi | `taniadaptif_padi` | public + local_aikmel |
| Jagung | `taniadaptif_jagung` | public |
| Cabai | `taniadaptif_cabai` | public |
| Kacang tanah | `taniadaptif_kacang_tanah` | public |

Trigger sengaja netral terhadap asal gambar. Foto lokal hanya digunakan untuk
padi dan tidak mengubah trigger menjadi `aikmel_*`.

## Strategi Utama

Strategi awal adalah satu LoRA gabungan Stable Diffusion 1.5. Metadata
training mencampur empat kelas secara seimbang dan setiap caption memiliki
trigger kelasnya sendiri. Konfigurasi awal memakai rank 8, batch size 1,
gradient accumulation 4, dan 1600 langkah. Nilai tersebut adalah baseline
yang dapat diubah, bukan konfigurasi terbaik yang sudah terbukti.

Satu adapter dipilih lebih dahulu karena:

- deployment hanya memuat satu adapter;
- prompt generator cukup memilih satu trigger;
- eksperimen antarkelas dapat dibandingkan dalam konfigurasi yang sama;
- kebutuhan penyimpanan dan pergantian adapter lebih kecil.

## Hubungan dengan Rekomendasi

Alur keputusan aplikasi:

```text
BMKG + data lahan
        |
        v
rule-based recommendation engine
        |
        v
tanaman terpilih + kondisi yang boleh dinyatakan
        |
        v
prompt generator memilih taniadaptif_<class>
        |
        v
Stable Diffusion + LoRA membuat simulasi visual
```

Rule-based engine menentukan rekomendasi tanaman. Stable Diffusion tidak
menilai kelayakan agronomi dan tidak mengganti keputusan rule-based.

## Risiko Class Confusion

Class confusion terjadi jika output visual tidak sesuai trigger, misalnya
prompt padi menghasilkan jagung, cabai berubah menjadi tanaman lain, atau
dua komoditas muncul bersamaan tanpa diminta. Evaluasi juga memeriksa apakah
trigger memberi perubahan yang terlihat dibanding base model.

Review dilakukan menggunakan minimal 12 prompt, parameter identik untuk base
dan LoRA, serta kolom manual:

```text
expected_class
predicted_visual_class
prompt
seed
reviewer_score
class_correct
mixed_crop_detected
notes
```

Kolom visual tidak boleh diisi otomatis tanpa model klasifikasi tervalidasi
atau pemeriksaan manusia.

## Kapan Memakai Adapter Terpisah

Pertimbangkan empat LoRA terpisah setelah:

1. prompt dan trigger telah diverifikasi;
2. keseimbangan serta label dataset telah diperiksa;
3. training gabungan telah dievaluasi manusia;
4. class confusion tetap tinggi dan konsisten pada lebih dari satu prompt.

Kriteria operasional awal dapat memakai `class_correct` di bawah 80 persen
atau `mixed_crop_detected` di atas 20 persen pada review manusia. Ambang ini
adalah aturan eksperimen yang harus dilaporkan, bukan standar universal.

Konfigurasi fallback tersedia di
`ml_pipeline/configs/training_public_per_class_fallback.yaml` dan sengaja
dinonaktifkan. Tidak ada empat training terpisah yang dijalankan pada fase
ini.

## Perubahan API pada Fallback

Pada strategi gabungan, API memuat satu adapter dan meneruskan trigger sesuai
tanaman. Pada fallback, API harus memetakan `class_id` ke path adapter,
melepas adapter aktif, lalu memuat adapter kelas tujuan atau memakai cache
adapter yang didukung runtime.

Empat adapter meningkatkan:

- ukuran penyimpanan;
- waktu cold start dan pergantian adapter;
- kompleksitas cache serta health check;
- kebutuhan pengujian agar adapter yang dimuat sesuai rekomendasi.

Keuntungannya adalah isolasi kelas yang lebih kuat jika LoRA gabungan tidak
mampu membedakan komoditas secara konsisten.
