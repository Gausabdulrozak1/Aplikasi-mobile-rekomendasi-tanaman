# Kode Draw.io ERD dan Flowchart Tani Adaptif

File ini berisi kode Mermaid yang dapat dimasukkan ke Draw.io/diagrams.net melalui menu:

`Arrange > Insert > Advanced > Mermaid`

## ERD

Catatan rancangan:

- ERD hanya memuat data yang disimpan aplikasi.
- API BMKG dan Stable Diffusion LoRA API tidak dijadikan entitas ERD karena keduanya adalah layanan eksternal.
- Entitas `uat` dibuat terpisah karena pada implementasi database belum memiliki foreign key ke `petani`.

```mermaid
erDiagram
    PETANI ||--o{ LAHAN : memiliki
    LAHAN ||--o{ CUACA : memiliki_riwayat
    LAHAN ||--o{ REKOMENDASI : menghasilkan
    REKOMENDASI ||--o{ SIMULASI_VISUAL : divisualisasikan

    PETANI {
        INTEGER id PK
        TEXT nama
        TEXT email
        TEXT nomor_hp
        REAL latitude
        REAL longitude
        DATETIME dibuat_pada
    }

    LAHAN {
        INTEGER id PK
        INTEGER petani_id FK
        TEXT nama_lahan
        TEXT jenis_lahan
        TEXT ketersediaan_air
        TEXT tanaman_sebelumnya
        REAL latitude
        REAL longitude
        DATETIME dibuat_pada
    }

    CUACA {
        INTEGER id PK
        INTEGER lahan_id FK
        DATE tanggal
        REAL suhu
        REAL curah_hujan
        TEXT kategori_curah_hujan
        REAL kelembaban
        TEXT kondisi
        DATETIME dibuat_pada
    }

    REKOMENDASI {
        INTEGER id PK
        INTEGER lahan_id FK
        TEXT tanaman_sebelumnya
        TEXT tanaman_direkomendasikan
        TEXT alasan
        DATETIME dibuat_pada
    }

    SIMULASI_VISUAL {
        INTEGER id PK
        INTEGER rekomendasi_id FK
        TEXT prompt
        TEXT negative_prompt
        INTEGER seed
        TEXT url_gambar
        DATETIME dibuat_pada
    }

    UAT {
        INTEGER id PK
        TEXT responden
        INTEGER skor
        TEXT catatan
        DATETIME dibuat_pada
    }
```

## Flowchart Proses Rekomendasi dan Simulasi Visual

```mermaid
flowchart TD
    A([Mulai]) --> B[Pengguna membuka aplikasi]
    B --> C[/Input data lahan: kode wilayah, jenis lahan, ketersediaan air, tanaman sebelumnya/]
    C --> D{Input lengkap dan valid?}

    D -- Tidak --> E[Tampilkan pesan kesalahan]
    E --> C

    D -- Ya --> F[Ambil data cuaca dari API BMKG]
    F --> G{Data BMKG berhasil diambil?}

    G -- Tidak --> H{Cache cuaca tersedia?}
    H -- Tidak --> I[Tampilkan pesan gagal mengambil cuaca]
    I --> Z([Selesai])
    H -- Ya --> J[Gunakan data cache cuaca]

    G -- Ya --> K[Olah data cuaca BMKG]
    J --> K

    K --> L[Hitung total curah hujan 3 hari dan estimasi curah hujan bulanan]
    L --> M{Estimasi curah hujan bulanan}
    M -- lebih dari 200 mm --> N[Kategori hujan = tinggi]
    M -- 100 sampai 200 mm --> O[Kategori hujan = sedang]
    M -- kurang dari 100 mm --> P[Kategori hujan = rendah]

    N --> Q{Ketersediaan air = kurang?}
    O --> Q
    P --> Q

    Q -- Ya --> R[Gunakan air = terbatas untuk pencarian aturan dan tambahkan catatan peringatan]
    Q -- Tidak --> S[Gunakan nilai ketersediaan air sesuai input]

    R --> T[Bentuk kunci aturan: curahHujan_air_tanamanSebelumnya]
    S --> T

    T --> U[Cari kunci pada decision table aturan rotasi]
    U --> V{Aturan ditemukan?}
    V -- Tidak --> W[Gunakan aturan default]
    V -- Ya --> X[Gunakan aturan yang cocok]

    W --> Y[Susun rekomendasi tanaman, prioritas, dan alasan]
    X --> Y

    Y --> AA[Susun rencana mingguan 4 minggu dan jadwal tanam]
    AA --> AB[Bangun prompt simulasi visual berdasarkan rekomendasi dan kondisi lahan]
    AB --> AC{Pengguna meminta simulasi visual?}

    AC -- Tidak --> AD[Tampilkan hasil rekomendasi tanpa gambar]
    AC -- Ya --> AE[Kirim prompt ke Stable Diffusion LoRA API]
    AE --> AF{Gambar berhasil dibuat?}
    AF -- Tidak --> AG[Tampilkan rekomendasi dengan catatan gambar belum tersedia]
    AF -- Ya --> AH[Simpan URL gambar simulasi]

    AD --> AI[Simpan riwayat rekomendasi]
    AG --> AI
    AH --> AI
    AI --> AJ[Tampilkan cuaca, rekomendasi, alasan, jadwal, dan visual jika tersedia]
    AJ --> Z([Selesai])
```
