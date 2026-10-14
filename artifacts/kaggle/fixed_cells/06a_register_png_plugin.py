import io

from PIL import Image, PngImagePlugin

# Pillow dipasang ulang pada interpreter yang sama. Daftarkan seluruh plugin
# ke instance PIL.Image yang sedang dipakai Diffusers.
Image.init()
assert PngImagePlugin is not None

# Import plugin dapat menjadi no-op bila modul pernah dimuat sebelum reinstall.
# Daftarkan handler secara eksplisit pada registry Image yang aktif.
Image.register_save("PNG", PngImagePlugin._save)
Image.register_extensions("PNG", [".png", ".apng"])

if "PNG" not in Image.SAVE:
    raise SystemExit("STOP: Pillow PNG save handler belum terdaftar.")

png_probe = Image.new("RGB", (2, 2), color="black")
png_buffer = io.BytesIO()
png_probe.save(png_buffer, format="PNG")
png_probe_bytes = png_buffer.getvalue()

if png_probe_bytes[:8] != b"\x89PNG\r\n\x1a\n":
    raise SystemExit("STOP: Pillow gagal menghasilkan PNG valid.")

print("PIL PNG PLUGIN: PASS")
print("PIL PNG SAVE: PASS")
