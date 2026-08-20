# Required Human Actions - Deployment dan Pengujian Akhir

Training Kaggle sudah selesai pada run `20260820T143551Z`; jangan menjalankan
ulang hanya untuk memperoleh artefak yang sama. Human review 72/72, validator,
dan analyzer juga sudah selesai.

1. Buat RunPod Secure Cloud On-Demand Pod RTX A5000 24 GB dan unggah
   `artifacts/deployment/taniadaptif_runpod_deployment.zip`.
2. Ikuti `docs/DEPLOYMENT_RUNBOOK.md`: bootstrap, buat dua token acak yang
   berbeda, lalu start stack sampai remote `gpu_preflight.json` lulus.
3. Jalankan real e2e probe dari Windows. Jangan lanjut jika hasil masih mock,
   CPU, hash berbeda, atau status bukan `success`.
4. Jalankan Flutter pada Android menggunakan ignored
   `config/production.local.json`, tampilkan gambar nyata, dan ambil screenshot
   hasil tanpa menampilkan token.
5. Berikan naskah skripsi BAB I-III agar draf hasil dapat diselaraskan dengan
   rumusan masalah, metode, istilah, dan format kampus.
6. Jalankan uji perangkat fisik, validasi ahli pertanian, dan farmer UAT dengan
   instrumen yang sudah disiapkan. Jangan mengisi hasil atau tanda tangan secara
   otomatis.
7. Buat dan tandatangani APK release hanya dengan keystore resmi milik penulis.
