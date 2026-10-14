# ruff: noqa: F821

import gc
import socket
import threading

import uvicorn


def request_json(url: str, *, token: str = "", method: str = "GET", body=None, timeout=30):
    headers = {
        "Accept": "application/json",
        "User-Agent": "TaniAdaptif-Sidang/1.0",
    }
    if token:
        headers["X-Inference-Token"] = token

    payload = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


running_uvicorn_threads = []
seen_servers = set()
for candidate_thread in threading.enumerate():
    target = getattr(candidate_thread, "_target", None)
    candidate_server = getattr(target, "__self__", None)
    if not isinstance(candidate_server, uvicorn.Server):
        continue
    if id(candidate_server) in seen_servers:
        continue
    seen_servers.add(id(candidate_server))
    running_uvicorn_threads.append((candidate_server, candidate_thread))

for previous_server, previous_thread in running_uvicorn_threads:
    print(f"Stopping previous Uvicorn thread: {previous_thread.name}")
    previous_server.should_exit = True

for _, previous_thread in running_uvicorn_threads:
    previous_thread.join(timeout=15)
    if previous_thread.is_alive():
        print(
            "WARNING: previous Uvicorn thread did not stop; "
            "a different local port will be selected."
        )

gc.collect()
torch.cuda.empty_cache()


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


available_ports = [port for port in range(5000, 5011) if port_is_available(FASTAPI_HOST, port)]
if not available_ports:
    raise SystemExit("STOP: tidak ada port FastAPI kosong pada rentang 5000-5010.")

FASTAPI_PORT = available_ports[0]
LOCAL_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}"

UVICORN_CONFIG = uvicorn.Config(
    FASTAPI_APP,
    host=FASTAPI_HOST,
    port=FASTAPI_PORT,
    log_level="info",
    access_log=False,
    proxy_headers=True,
    forwarded_allow_ips="127.0.0.1",
)
UVICORN_SERVER = uvicorn.Server(UVICORN_CONFIG)
UVICORN_THREAD = threading.Thread(
    target=UVICORN_SERVER.run,
    name=f"taniadaptif-fastapi-{FASTAPI_PORT}",
    daemon=True,
)
UVICORN_THREAD.start()

local_health = {}
last_local_error = "server belum merespons"
deadline = time.time() + 45
while time.time() < deadline:
    if not UVICORN_THREAD.is_alive():
        raise SystemExit(
            f"STOP: thread FastAPI berhenti sebelum siap pada port {FASTAPI_PORT}."
        )
    try:
        local_health = request_json(f"{LOCAL_URL}/health", timeout=3)
        if local_health.get("status") == "ok":
            break
        last_local_error = f"status={local_health.get('status', 'missing')}"
    except Exception as exc:
        last_local_error = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
    time.sleep(1)
else:
    raise SystemExit(
        "STOP: FastAPI gagal aktif. "
        f"URL={LOCAL_URL}; error terakhir={last_local_error}"
    )

local_ready = request_json(
    f"{LOCAL_URL}/ready",
    token=INFERENCE_API_TOKEN,
    timeout=15,
)
if local_ready.get("status") != "ready":
    raise SystemExit(
        "STOP: FastAPI aktif tetapi provider tidak ready: "
        + json.dumps(local_ready, indent=2)
    )

local_model_info = request_json(
    f"{LOCAL_URL}/v1/model-info",
    token=INFERENCE_API_TOKEN,
    timeout=15,
)
if not (
    local_model_info.get("base_model") == BASE_MODEL
    and local_model_info.get("lora_identifier") == LORA_IDENTIFIER
    and local_model_info.get("provider") == "diffusers"
):
    raise SystemExit(
        "STOP: FastAPI lokal tidak memakai model final: "
        + json.dumps(local_model_info, indent=2)
    )

print("FastAPI local health: PASS")
print("FastAPI local ready: PASS")
print("FastAPI server thread: PASS")
print("FastAPI port:", FASTAPI_PORT)
print("LOCAL_URL=" + LOCAL_URL)
