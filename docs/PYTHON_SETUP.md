# Python Setup Lokal Aman

Python lokal hanya dibutuhkan untuk menjalankan test pipeline dan FastAPI mock.
Tidak ada training Stable Diffusion di laptop.

## Instalasi Ringan

Gunakan Python 3.10 atau 3.11. Setelah Python tersedia di PATH:

```powershell
cd D:\TaniAdaptif
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r ml_pipeline\requirements\base.txt
pip install -r inference_api\requirements.txt
```

Dependency di atas ringan dibanding Stable Diffusion. Paket berat seperti
`torch`, `diffusers`, dan `accelerate` hanya diperlukan di Colab atau server GPU
melalui `inference_api/requirements-diffusers.txt`.

## Test Lokal

```powershell
pytest ml_pipeline\tests
pytest inference_api\tests
```

## Menjalankan Mock API

```powershell
uvicorn inference_api.app.main:app --host 0.0.0.0 --port 5000
```

Mode default adalah `mock`, sehingga tidak memuat model Stable Diffusion.

## Yang Tidak Dilakukan di Laptop

Jangan jalankan perintah berikut di laptop Ryzen 3:

```powershell
pip install -r inference_api\requirements-diffusers.txt
```

Jalankan dependency Diffusers hanya di Colab/server GPU jika memang ingin
melakukan inference model nyata.

