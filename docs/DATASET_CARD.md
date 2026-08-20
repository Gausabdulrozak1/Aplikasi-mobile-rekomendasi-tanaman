# Dataset Card - TaniAdaptif Multicrop

Tanggal finalisasi: 2026-08-13  
Status metadata: **valid**.

Dataset ini disiapkan untuk fine-tuning LoRA Stable Diffusion 1.5 sebagai simulasi visual tanaman. Model visual tidak menentukan rekomendasi agronomi; rekomendasi tetap berasal dari rule-based engine dan data BMKG.

## Komoditas, Sumber, dan Split

| Kelas | Trigger | Kebijakan sumber | Audit files | Human accepted | Human rejected | Final | Train | Validation |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | `taniadaptif_padi` | public + local_aikmel | 249 | 95 | 5 | 95 | 76 | 19 |
| jagung | `taniadaptif_jagung` | public only | 130 | 101 | 29 | 100 | 80 | 20 |
| cabai | `taniadaptif_cabai` | public only | 120 | 97 | 23 | 97 | 78 | 19 |
| kacang_tanah | `taniadaptif_kacang_tanah` | public only | 125 | 97 | 28 | 97 | 78 | 19 |

## Kurasi

Semua gambar final memiliki keputusan manusia `accepted=yes`. Kelas dibatasi maksimum 100 gambar secara deterministik dengan seed 42. Split 80:20 mempertahankan kelas, aturan sumber padi, dan isolasi duplicate group.

Kandidat tambahan berasal dari dataset akademik CC BY 4.0 yang didokumentasikan dalam `docs/DATASET_ADDITIONAL_SOURCES.md`; provenance per gambar dipertahankan dalam source manifest, curation mapping, dan split manifest.

## Lisensi dan Batasan

- Gambar final public dengan metadata provenance lama yang belum lengkap: 240.
- Ketiadaan metadata lisensi bukan bukti bahwa hak penggunaan tersedia. Verifikasi provenance tetap diperlukan sebelum redistribusi publik atau penggunaan komersial.
- Dataset public membawa bias wilayah, kamera, varietas, fase tumbuh, dan komposisi.
- Kelas selain padi tidak diklaim mewakili kondisi khusus Aikmel.
- Trigger `taniadaptif_*` adalah identifier kelas model, bukan klaim lokasi.
- Belum ada hasil training atau evaluasi LoRA yang diklaim oleh dataset card ini.

## Caption

Caption menyebut trigger kelas, tanaman yang tumbuh di lingkungan pertanian, dan pencahayaan alami. Caption tidak menebak cuaca, musim, tanah, atau fase pertumbuhan.
