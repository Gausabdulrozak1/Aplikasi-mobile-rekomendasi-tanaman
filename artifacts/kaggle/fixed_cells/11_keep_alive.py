# ruff: noqa: F821

KEEP_ALIVE_MINUTES = 330
print(
    f"Service live selama maksimal {KEEP_ALIVE_MINUTES} menit. "
    "Biarkan cell ini berjalan saat sidang."
)

for elapsed_minutes in range(KEEP_ALIVE_MINUTES):
    if CLOUDFLARED_PROCESS.poll() is not None:
        raise RuntimeError("Cloudflare tunnel berhenti.")

    if elapsed_minutes % 15 == 0:
        check_health = request_json(f"{LOCAL_URL}/health", timeout=5)
        check_ready = request_json(
            f"{LOCAL_URL}/ready",
            token=INFERENCE_API_TOKEN,
            timeout=15,
        )
        if check_health.get("status") != "ok":
            raise RuntimeError("FastAPI health tidak lagi ok.")
        if check_ready.get("status") != "ready":
            raise RuntimeError("FastAPI provider tidak lagi ready.")
        print(
            f"KEEP_ALIVE minute={elapsed_minutes} "
            f"FASTAPI_PORT={FASTAPI_PORT} "
            f"KAGGLE_GPU_URL={KAGGLE_GPU_URL}"
        )

    time.sleep(60)

print("Keep-alive selesai. Run ulang cell tunnel untuk membuat URL baru.")
