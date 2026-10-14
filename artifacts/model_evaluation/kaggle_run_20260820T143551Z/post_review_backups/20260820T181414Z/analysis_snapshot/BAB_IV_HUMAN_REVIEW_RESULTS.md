# Hasil Evaluasi Manusia Base vs LoRA

- Status: `complete_validated_human_review`
- Kondisi berpasangan: 36
- Gambar dinilai: 72
- SHA-256 CSV: `0fdfb5ec26f6f11cbfcea79cc6f46a778e92b90827da958201b8b9feb57b3aa7`
- Peran reviewer yang dilaporkan: Peneliti (72 baris)

## Ringkasan Keseluruhan

| Metrik | Base | LoRA | Selisih LoRA-Base | LoRA menang / seri / Base menang | p exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| Komoditas sesuai | 86,111% | 94,444% | 8,333 poin persentase | 3 / 33 / 0 | 0,250000 |
| Kualitas konteks lahan (mean; median) | 4,028; 4,500 | 3,861; 4,000 | -0,167 mean | 6 / 21 / 9 | 0,607239 |
| Realisme visual (mean; median) | 4,028; 4,500 | 3,861; 4,000 | -0,167 mean | 6 / 21 / 9 | 0,607239 |

## Ringkasan Per Kelas

| Kelas | N pasangan | Benar Base | Benar LoRA | Median konteks Base/LoRA | Median realisme Base/LoRA | Confusion Base/LoRA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| padi | 9 | 100,000% | 100,000% | 4,000 / 4,000 | 4,000 / 4,000 | 0 / 0 |
| jagung | 9 | 100,000% | 100,000% | 5,000 / 4,000 | 5,000 / 4,000 | 0 / 0 |
| cabai | 9 | 100,000% | 100,000% | 5,000 / 5,000 | 5,000 / 5,000 | 0 / 0 |
| kacang_tanah | 9 | 44,444% | 77,778% | 2,000 / 4,000 | 2,000 / 4,000 | 5 / 2 |

## Batas Interpretasi

- Skor 1-5 bersifat ordinal; median menjadi ringkasan utama dan mean hanya deskriptif.
- Exact sign test menguji arah selisih pasangan setelah nilai seri dikeluarkan.
- Exact McNemar menggunakan pasangan discordant untuk penilaian komoditas benar/salah.
- Nilai p bersifat eksploratif dan tidak membuktikan ketepatan agronomi atau hubungan kausal.
- Identitas reviewer tidak diverifikasi secara independen oleh perangkat lunak.
- Brightness, contrast, dan entropy tetap proxy otomatis yang dilaporkan terpisah.
