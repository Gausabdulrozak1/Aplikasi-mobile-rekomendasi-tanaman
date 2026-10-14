# ruff: noqa: F821

import queue

local_health = request_json(f"{LOCAL_URL}/health", timeout=5)
local_ready = request_json(
    f"{LOCAL_URL}/ready",
    token=INFERENCE_API_TOKEN,
    timeout=15,
)
if local_health.get("status") != "ok" or local_ready.get("status") != "ready":
    raise SystemExit("STOP: FastAPI lokal belum sehat sebelum tunnel dibuat.")

previous_tunnel = globals().get("CLOUDFLARED_PROCESS")
if previous_tunnel is not None and previous_tunnel.poll() is None:
    previous_tunnel.terminate()
    try:
        previous_tunnel.wait(timeout=10)
    except subprocess.TimeoutExpired:
        previous_tunnel.kill()
        previous_tunnel.wait(timeout=5)

cloudflared_home = WORK_ROOT / "cloudflared_home"
cloudflared_home.mkdir(parents=True, exist_ok=True)
cloudflared_env = {**os.environ, "HOME": str(cloudflared_home)}
CLOUDFLARED_PROCESS = subprocess.Popen(
    [
        str(CLOUDFLARED_PATH),
        "tunnel",
        "--url",
        LOCAL_URL,
        "--no-autoupdate",
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    env=cloudflared_env,
)

tunnel_lines = queue.Queue()
tunnel_history = []


def collect_tunnel_output():
    assert CLOUDFLARED_PROCESS.stdout is not None
    for line in CLOUDFLARED_PROCESS.stdout:
        clean_line = line.rstrip()
        tunnel_history.append(clean_line)
        tunnel_lines.put(clean_line)


threading.Thread(
    target=collect_tunnel_output,
    name="taniadaptif-cloudflared-output",
    daemon=True,
).start()

tunnel_pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
KAGGLE_GPU_URL = ""
deadline = time.time() + 120
while time.time() < deadline and CLOUDFLARED_PROCESS.poll() is None:
    try:
        line = tunnel_lines.get(timeout=1)
    except queue.Empty:
        continue
    match = tunnel_pattern.search(line)
    if match:
        KAGGLE_GPU_URL = match.group(0)
        break

if not KAGGLE_GPU_URL:
    diagnostic = "\n".join(tunnel_history[-20:])
    raise SystemExit(
        "STOP: Cloudflare Quick Tunnel gagal menghasilkan URL HTTPS.\n" + diagnostic
    )

public_health = {}
last_health_error = "health belum merespons"
deadline = time.time() + 120
while time.time() < deadline:
    if CLOUDFLARED_PROCESS.poll() is not None:
        raise SystemExit("STOP: proses Cloudflare berhenti saat health check.")
    try:
        public_health = request_json(f"{KAGGLE_GPU_URL}/health", timeout=15)
        if public_health.get("status") == "ok":
            break
        last_health_error = f"status={public_health.get('status', 'missing')}"
    except Exception as exc:
        last_health_error = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
    time.sleep(2)
else:
    raise SystemExit(
        "STOP: URL Quick Tunnel tersedia tetapi health publik gagal. "
        f"Error terakhir: {last_health_error}"
    )

public_ready = {}
last_ready_error = "provider belum ready"
deadline = time.time() + 120
while time.time() < deadline:
    if CLOUDFLARED_PROCESS.poll() is not None:
        raise SystemExit("STOP: proses Cloudflare berhenti saat readiness check.")
    try:
        public_ready = request_json(
            f"{KAGGLE_GPU_URL}/ready",
            token=INFERENCE_API_TOKEN,
            timeout=20,
        )
        if public_ready.get("status") == "ready":
            break
        last_ready_error = f"status={public_ready.get('status', 'missing')}"
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise SystemExit(
                f"STOP: autentikasi readiness publik ditolak (HTTP {exc.code})."
            ) from exc
        last_ready_error = f"HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        last_ready_error = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
    time.sleep(2)
else:
    raise SystemExit(
        "STOP: readiness publik bukan ready setelah retry. "
        f"Error terakhir: {last_ready_error}"
    )

print("KAGGLE_GPU_URL=" + KAGGLE_GPU_URL)
print("Cloudflare public health: PASS")
print("Cloudflare public readiness: PASS")
