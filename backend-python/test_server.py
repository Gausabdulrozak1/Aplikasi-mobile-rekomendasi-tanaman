"""
Test script untuk verifikasi server AI berjalan
Cara pakai: python test_server.py
"""

import requests
import json

BASE_URL = "http://localhost:5000"


def test_kesehatan():
    """Test endpoint kesehatan"""
    print("\n🩺 Test Kesehatan Server...", end=" ")
    r = requests.get(f"{BASE_URL}/kesehatan")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "baik"
    print("✅ OK")
    print(f"   Pesan: {data['pesan']}")
    print(f"   Mode: {data['mode']}")


def test_tanaman():
    """Test daftar tanaman"""
    print("\n🌱 Test Daftar Tanaman...", end=" ")
    r = requests.get(f"{BASE_URL}/tanaman")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "sukses"
    print(f"✅ OK ({data['jumlah']} tanaman)")
    for t in data["data"]:
        print(f"   - {t['kode']}: {t['nama']}")


def test_generate():
    """Test generate gambar"""
    print("\n🎨 Test Generate Gambar...")

    # Test berbagai kombinasi
    test_cases = [
        {"tanaman": "padi", "tahap": "vegetatif", "kondisi_lahan": "sawah", "cuaca": "cerah"},
        {"tanaman": "jagung", "tahap": "berbunga", "kondisi_lahan": "tegalan", "cuaca": "berawan"},
        {"tanaman": "cabai", "tahap": "panen", "kondisi_lahan": "kebun", "cuaca": "cerah"},
    ]

    for tc in test_cases:
        print(f"\n   🔄 Generate {tc['tanaman']} ({tc['tahap']})...", end=" ")
        r = requests.post(f"{BASE_URL}/generate", json=tc)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "sukses"
        print("✅ OK")
        print(f"      Prompt: {data['gambar']['prompt'][:60]}...")
        print(f"      Warna daun: {data['gambar']['warna_daun']}")


def main():
    """Jalankan semua test"""
    print("=" * 50)
    print("🧪 TEST SERVER AI TANIADAPTIF")
    print("=" * 50)
    print(f"Server: {BASE_URL}")

    try:
        test_kesehatan()
        test_tanaman()
        test_generate()
        print("\n" + "=" * 50)
        print("🎉 SEMUA TEST BERHASIL!")
        print("=" * 50)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Tidak bisa konek ke server!")
        print("   Jalankan server dulu: python main.py")
    except AssertionError as e:
        print(f"\n❌ ERROR: Test gagal: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
