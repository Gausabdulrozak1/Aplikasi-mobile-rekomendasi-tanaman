import pytest

from inference_api.scripts.e2e_probe import ProbeError, inspect_png, normalize_backend_api_url


def test_normalize_backend_url_requires_https_for_real_evidence() -> None:
    assert normalize_backend_api_url("https://pod.example") == "https://pod.example/api"
    assert normalize_backend_api_url("https://pod.example/api/") == "https://pod.example/api"
    with pytest.raises(ProbeError, match="HTTPS"):
        normalize_backend_api_url("http://pod.example")


def test_normalize_backend_url_allows_local_contract_test_explicitly() -> None:
    assert (
        normalize_backend_api_url("http://127.0.0.1:3000", allow_http=True)
        == "http://127.0.0.1:3000/api"
    )


def test_inspect_png_reads_ihdr_dimensions() -> None:
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + (512).to_bytes(4, "big")
        + (512).to_bytes(4, "big")
    )
    assert inspect_png(payload) == {"width": 512, "height": 512, "size_bytes": 24}


def test_inspect_png_rejects_placeholder_bytes() -> None:
    with pytest.raises(ProbeError, match="PNG"):
        inspect_png(b"placeholder")
