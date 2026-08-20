# Evaluation Rubric - Multisource Multicrop LoRA

Evaluasi membandingkan base Stable Diffusion 1.5 dengan LoRA memakai parameter
identik. Minimal tiga prompt per kelas dan total minimal 12 prompt.

## Skala 1-5

| Skor | Arti |
| ---: | --- |
| 1 | Gagal total atau tidak dapat dinilai |
| 2 | Banyak kesalahan; identitas/konteks lemah |
| 3 | Cukup dikenali tetapi masih ada masalah nyata |
| 4 | Baik, relevan, dengan kesalahan kecil |
| 5 | Sangat baik dan konsisten dengan prompt |

Nilai aspek berikut secara terpisah:

- `visual_quality_1_5`: ketajaman, struktur tanaman, dan artefak visual.
- `crop_identity_1_5`: kesesuaian komoditas dengan trigger.
- `prompt_adherence_1_5`: kesesuaian dengan kondisi yang diminta prompt.
- `agricultural_relevance_1_5`: kewajaran konteks pertanian.

Skor tidak boleh diisi sebelum gambar diperiksa.

## Class Confusion Review

Untuk setiap hasil LoRA, isi:

| Kolom | Cara mengisi |
| --- | --- |
| `expected_class` | Kelas dari prompt; sudah diisi notebook |
| `predicted_visual_class` | Kelas yang benar-benar terlihat menurut reviewer |
| `prompt` | Prompt yang dipakai; sudah diisi notebook |
| `seed` | Seed generation; sudah diisi notebook |
| `reviewer_score` | Keyakinan/kualitas identitas kelas, 1-5 |
| `class_correct` | `true` atau `false` setelah review |
| `mixed_crop_detected` | `true` jika dua komoditas atau lebih tercampur |
| `notes` | Kesalahan visual dan alasan penilaian |

Periksa khusus:

- prompt padi menghasilkan jagung;
- prompt jagung menghasilkan padi;
- prompt cabai menghasilkan tanaman lain;
- prompt kacang tanah menghasilkan tanaman lain;
- dua komoditas atau lebih muncul tanpa diminta;
- output dengan trigger tidak berbeda secara bermakna dari base model.

## Ringkasan

Setelah seluruh review selesai, hitung per kelas:

- jumlah gambar yang dinilai;
- persentase `class_correct`;
- persentase `mixed_crop_detected`;
- median setiap skor 1-5;
- contoh keberhasilan;
- contoh kegagalan.

Jangan mengisi sel kosong sebagai nol. Laporkan jumlah review yang benar-benar
selesai.

## Keputusan Fallback

Investigasi adapter terpisah jika class correctness di bawah 80 persen atau
mixed crop di atas 20 persen dan masalah muncul pada lebih dari satu prompt.
Sebelum fallback, periksa label, balance dataset, caption, trigger, dan
parameter training. Ambang ini adalah aturan operasional eksperimen, bukan
klaim standar terbaik.
