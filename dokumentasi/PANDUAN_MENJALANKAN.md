# Panduan Lengkap Menjalankan Aplikasi TaniAdaptif

## 📋 Persyaratan Sistem

### Wajib:
1. **Node.js** v16+ → [Download](https://nodejs.org)
2. **Flutter** 3.x → [Download](https://flutter.dev)
3. **Git** → [Download](https://git-scm.com)

### Opsional (untuk AI):
4. **Python** 3.9+ → [Download](https://python.org)

---

## 🚀 Cara Menjalankan

### Langkah 1: Jalankan Backend Node.js

```bash
# Buka Terminal 1
cd D:\TaniAdaptif\backend-nodejs

# Install dependencies (cukup sekali)
npm install

# Jalankan server
npm run dev
```

Server akan berjalan di: `http://localhost:3000`

Cek di browser:
- `http://localhost:3000/api/kesehatan`
- `http://localhost:3000/api/cuaca/52.03.09.2002`

### Langkah 2: Jalankan Aplikasi Flutter

```bash
# Buka Terminal 2
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif

# Install dependencies (cukup sekali)
flutter pub get

# Jalankan di Chrome
flutter run -d chrome
```

Aplikasi akan terbuka di Chrome → `http://localhost:XXXXX`

### Langkah 3 (Opsional): Jalankan Inference API Visual

```bash
# Buka Terminal 3
cd D:\TaniAdaptif

# Install Python dependencies untuk mock provider
pip install -r inference_api\requirements.txt

# Jalankan server visual mock
uvicorn inference_api.app.main:app --host 0.0.0.0 --port 5000
```

Server inference visual akan berjalan di: `http://localhost:5000`

Endpoint penting:
- `http://localhost:5000/health`
- `http://localhost:5000/v1/model-info`
- `POST http://localhost:5000/v1/generate`

Catatan: mode default adalah `mock`, aman untuk laptop tanpa GPU. Stable Diffusion/Diffusers provider hanya dijalankan di server GPU.

---

## 🔄 Alur Aplikasi

1. **Splash Screen** → Logo TaniAdaptif (3 detik)
2. **Dashboard** → Menampilkan cuaca ASLI dari BMKG untuk Aikmel
3. **Klik "Dapatkan Rekomendasi"** → Form input lahan
4. **Isi form** (tanaman sebelumnya, ketersediaan air, jenis lahan)
5. **Klik "Proses Rekomendasi"** → Menampilkan:
   - Ringkasan cuaca
   - 2 rekomendasi tanaman dengan prioritas
   - Alasan rekomendasi
   - Simulasi visual (jika inference API aktif)

---

## 🌐 Endpoint API

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/kesehatan` | Cek server |
| GET | `/api/cuaca/52.03.09.2002` | Cuaca Aikmel |
| GET | `/api/rekomendasi/tanaman` | Daftar tanaman |
| POST | `/api/rekomendasi` | Rekomendasi manual |
| POST | `/api/rekomendasi/otomatis` | Rekomendasi + cuaca BMKG |
| GET | `http://localhost:5000/health` | Cek inference API visual |
| POST | `http://localhost:5000/v1/generate` | Generate simulasi visual |

---

## 📁 Struktur File Penting

```
TaniAdaptif/
├── backend-nodejs/          # Server REST API
│   ├── src/
│   │   ├── index.js        # Entry point server
│   │   ├── routes/         # Endpoint API
│   │   ├── services/       # Logika bisnis
│   │   └── config/         # Database & aturan
│   └── data/               # Database SQLite
├── backend-python/          # Server AI
│   ├── main.py             # FastAPI server
│   └── requirements.txt    # Python dependencies
└── mobile-flutter/
    └── tani_adaptif/       # Aplikasi Flutter
        ├── lib/
        │   ├── screens/    # Halaman aplikasi
        │   ├── models/     # Struktur data
        │   ├── services/   # Koneksi backend
        │   └── config/     # Konfigurasi
        └── web/            # Web support
```

---

## 🧪 Testing

### Test Backend
```bash
# Endpoint kesehatan
http://localhost:3000/api/kesehatan

# Cuaca Aikmel (data BMKG asli)
http://localhost:3000/api/cuaca/52.03.09.2002

# Rekomendasi (via Thunder Client)
POST http://localhost:3000/api/rekomendasi
Body: {"curahHujan":"sedang","ketersediaanAir":"cukup","tanamanSebelumnya":"padi"}
```

### Test Inference API (jika Python aktif)
```bash
cd D:\TaniAdaptif
pytest inference_api\tests
```

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Server tidak jalan | Cek Node.js terinstall: `node --version` |
| Cuaca error | Pastikan server backend jalan, cek internet |
| Flutter gagal | Jalankan `flutter doctor` |
| Port sudah dipakai | Ganti PORT di file `.env` |
| "Gagal memuat cuaca" | Pastikan backend jalan di Terminal 1 |
