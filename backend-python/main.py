"""
TaniAdaptif - AI Image Generation Server
Server untuk generate gambar simulasi tanaman menggunakan AI
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="TaniAdaptif AI Server",
    description="API untuk generate gambar simulasi tanaman",
    version="1.0.0",
)

# CORS - biar bisa diakses dari Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# DATA TANAMAN (sama seperti di backend nodejs)
# ============================================
DATA_TANAMAN = {
    "padi": {
        "nama": "Padi",
        "warna_daun": "#4CAF50",
        "warna_buah": "#FFD700",
        "tinggi": 0.8,
        "bentuk": "rumput",
    },
    "jagung": {
        "nama": "Jagung",
        "warna_daun": "#388E3C",
        "warna_buah": "#F57C00",
        "tinggi": 1.5,
        "bentuk": "tongkol",
    },
    "kacang_tanah": {
        "nama": "Kacang Tanah",
        "warna_daun": "#66BB6A",
        "warna_buah": "#8D6E63",
        "tinggi": 0.3,
        "bentuk": "perdu",
    },
    "cabai": {
        "nama": "Cabai",
        "warna_daun": "#2E7D32",
        "warna_buah": "#D32F2F",
        "tinggi": 0.6,
        "bentuk": "perdu",
    },
}

# ============================================
# ENDPOINT: Health Check
# ============================================
@app.get("/kesehatan")
async def kesehatan():
    return {
        "status": "baik",
        "pesan": "Server AI TaniAdaptif berjalan",
        "mode": os.getenv("GENERATION_MODE", "mock"),
        "versi": "1.0.0",
    }

# ============================================
# ENDPOINT: Generate Gambar Simulasi
# ============================================
@app.post("/generate")
async def generate_gambar(data: dict):
    """
    Generate gambar simulasi tanaman.
    
    Input:
    {
        "tanaman": "padi",
        "tahap": "vegetatif",  # seedling, vegetatif, berbunga, panen
        "kondisi_lahan": "sawah",
        "cuaca": "cerah"
    }
    
    Output:
    {
        "status": "sukses",
        "gambar_url": "url_gambar",
        "deskripsi": "deskripsi prompt"
    }
    """
    tanaman = data.get("tanaman", "padi")
    tahap = data.get("tahap", "vegetatif")
    kondisi_lahan = data.get("kondisi_lahan", "sawah")
    cuaca = data.get("cuaca", "cerah")
    
    info = DATA_TANAMAN.get(tanaman, DATA_TANAMAN["padi"])
    
    # Buat prompt deskripsi (akan dipakai untuk Stable Diffusion nantinya)
    prompt = f"Tanaman {info['nama']} pada tahap {tahap} di lahan {kondisi_lahan}, cuaca {cuaca}, gaya fotografi pertanian"
    
    return {
        "status": "sukses",
        "gambar": {
            "tanaman": tanaman,
            "tahap": tahap,
            "prompt": prompt,
            "gambar_url": f"/static/{tanaman}_{tahap}.png",
            "warna_daun": info["warna_daun"],
            "warna_buah": info["warna_buah"],
        },
        "pesan": f"Gambar simulasi {info['nama']} tahap {tahap} berhasil diproses",
    }

# ============================================
# ENDPOINT: Info Tanaman
# ============================================
@app.get("/tanaman")
async def daftar_tanaman():
    return {
        "status": "sukses",
        "jumlah": len(DATA_TANAMAN),
        "data": [
            {
                "kode": k,
                "nama": v["nama"],
                "warna_daun": v["warna_daun"],
                "warna_buah": v["warna_buah"],
            }
            for k, v in DATA_TANAMAN.items()
        ],
    }

# ============================================
# JALANKAN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    print("=" * 50)
    print("🌾 TaniAdaptif AI Server")
    print(f"🔗 http://{host}:{port}")
    print(f"📚 Docs: http://{host}:{port}/docs")
    print(f"🎨 Mode: {os.getenv('GENERATION_MODE', 'mock')}")
    print("=" * 50)

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
    )
