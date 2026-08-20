from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import json
import platform
import sys
import time
import traceback
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load_percent", ctypes.c_ulong),
        ("total_physical_bytes", ctypes.c_ulonglong),
        ("available_physical_bytes", ctypes.c_ulonglong),
        ("total_page_file_bytes", ctypes.c_ulonglong),
        ("available_page_file_bytes", ctypes.c_ulonglong),
        ("total_virtual_bytes", ctypes.c_ulonglong),
        ("available_virtual_bytes", ctypes.c_ulonglong),
        ("available_extended_virtual_bytes", ctypes.c_ulonglong),
    ]


def memory_snapshot() -> dict[str, int | float | None]:
    if platform.system() != "Windows":
        return {
            "total_physical_bytes": None,
            "available_physical_bytes": None,
            "memory_load_percent": None,
        }

    status = MemoryStatusEx()
    status.length = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return {
        "total_physical_bytes": int(status.total_physical_bytes),
        "available_physical_bytes": int(status.available_physical_bytes),
        "memory_load_percent": int(status.memory_load_percent),
    }


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def contains_unsupported_warning(messages: list[str]) -> bool:
    markers = (
        "not currently supported on the dml backend",
        "dml_cpu_fallback",
        "cpu fallback",
        "privateuse1 backend",
    )
    return any(marker in message.casefold() for message in messages for marker in markers)


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "directml_check.json"
    md_path = output_dir / "directml_check.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    timings = report.get("timings_seconds", {})
    memory_before = report.get("memory_before", {})
    memory_after = report.get("memory_after", {})
    lines = [
        "# DirectML Check",
        "",
        f"- Status: `{report['status']}`",
        f"- Timestamp UTC: `{report['timestamp_utc']}`",
        f"- Python: `{report['python_version']}`",
        f"- Torch: `{report['dependencies'].get('torch')}`",
        f"- Torch-DirectML: `{report['dependencies'].get('torch-directml')}`",
        f"- Device: `{report.get('device')}`",
        f"- Device name: `{report.get('device_name')}`",
        f"- Forward passed: `{report.get('forward_passed', False)}`",
        f"- Backward passed: `{report.get('backward_passed', False)}`",
        f"- Optimizer step passed: `{report.get('optimizer_step_passed', False)}`",
        f"- Unsupported operation detected: `{report.get('unsupported_operation_detected', False)}`",
        "",
        "## Measurements",
        "",
        f"- Tensor operation seconds: `{timings.get('tensor_operation')}`",
        f"- Forward seconds: `{timings.get('forward')}`",
        f"- Backward seconds: `{timings.get('backward')}`",
        f"- Optimizer seconds: `{timings.get('optimizer')}`",
        f"- Available RAM before: `{memory_before.get('available_physical_bytes')}` bytes",
        f"- Available RAM after: `{memory_after.get('available_physical_bytes')}` bytes",
        "",
        "## Warnings",
        "",
    ]
    warning_messages = report.get("warnings", [])
    lines.extend(f"- {message}" for message in warning_messages)
    if not warning_messages:
        lines.append("- None")
    lines.extend(["", "## Error", "", f"```text\n{report.get('error') or 'None'}\n```", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")


def run_check() -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "dependencies": {
            "torch": package_version("torch"),
            "torch-directml": package_version("torch-directml"),
        },
        "device": None,
        "device_name": None,
        "device_count": None,
        "tensor_operation_passed": False,
        "forward_passed": False,
        "backward_passed": False,
        "optimizer_step_passed": False,
        "unsupported_operation_detected": False,
        "timings_seconds": {},
        "warnings": [],
        "memory_before": memory_snapshot(),
        "memory_after": None,
        "error": None,
        "traceback": None,
    }

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import torch
            import torch_directml

            device = torch_directml.device()
            report["device"] = str(device)
            if hasattr(torch_directml, "device_count"):
                report["device_count"] = int(torch_directml.device_count())
            if hasattr(torch_directml, "device_name"):
                report["device_name"] = str(torch_directml.device_name(0)).rstrip("\x00")

            torch.manual_seed(42)
            left = torch.arange(64, dtype=torch.float32).reshape(8, 8).to(device)
            right = torch.eye(8, dtype=torch.float32).to(device)
            started = time.perf_counter()
            tensor_checksum = (left @ right).sum().cpu().item()
            report["timings_seconds"]["tensor_operation"] = time.perf_counter() - started
            if tensor_checksum != 2016.0:
                raise RuntimeError(f"Unexpected DirectML tensor checksum: {tensor_checksum}")
            report["tensor_operation_passed"] = True

            model = torch.nn.Sequential(
                torch.nn.Linear(16, 8),
                torch.nn.ReLU(),
                torch.nn.Linear(8, 2),
            ).to(device)
            input_tensor = torch.linspace(-1, 1, 64, dtype=torch.float32).reshape(4, 16).to(
                device
            )
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            optimizer.zero_grad(set_to_none=True)

            started = time.perf_counter()
            output = model(input_tensor)
            loss = output.square().mean()
            loss_value = float(loss.detach().cpu().item())
            report["timings_seconds"]["forward"] = time.perf_counter() - started
            report["forward_passed"] = loss_value >= 0.0

            started = time.perf_counter()
            loss.backward()
            gradients = [
                parameter.grad.detach().cpu()
                for parameter in model.parameters()
                if parameter.grad is not None
            ]
            report["timings_seconds"]["backward"] = time.perf_counter() - started
            if not gradients or not all(torch.isfinite(gradient).all().item() for gradient in gradients):
                raise RuntimeError("DirectML backward produced missing or non-finite gradients")
            report["backward_passed"] = True

            started = time.perf_counter()
            optimizer.step()
            first_weight_checksum = float(next(model.parameters()).detach().cpu().sum().item())
            report["timings_seconds"]["optimizer"] = time.perf_counter() - started
            report["optimizer_step_passed"] = bool(first_weight_checksum)

            report["warnings"] = [str(item.message) for item in caught]
            report["unsupported_operation_detected"] = contains_unsupported_warning(
                report["warnings"]
            )
            required = (
                report["tensor_operation_passed"],
                report["forward_passed"],
                report["backward_passed"],
                report["optimizer_step_passed"],
            )
            if all(required) and not report["unsupported_operation_detected"]:
                report["status"] = "passed"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
    finally:
        report["memory_after"] = memory_snapshot()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal Windows DirectML feasibility check.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/local_ml"),
        help="Directory for directml_check.json and directml_check.md.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_check()
    write_reports(report, args.output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
