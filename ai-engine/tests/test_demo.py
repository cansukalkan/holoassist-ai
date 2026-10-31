"""The local demo serves packaged assets without exposing server files."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import local_app


def test_demo_page_has_local_only_content_policy():
    with TestClient(local_app()) as client:
        response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert '<html lang="tr">' in response.text


def test_demo_console_has_coherent_scenarios_and_no_inline_handlers():
    html = Path("ai-engine/holoassist/api/static/index.html").read_text(encoding="utf-8")
    js = Path("ai-engine/holoassist/api/static/app.js").read_text(encoding="utf-8")
    assert "style=" not in html
    assert "onclick=" not in html
    assert "innerHTML" not in js
    for scenario in ("information", "critical", "tracking", "unknown", "injection"):
        assert f'data-scenario="{scenario}"' in html
    for element_id in (
        "motor-reticle-label",
        "motor-reticle-critical",
        "exp-pill-safety",
        "exp-pill-sensor",
        "exp-pill-diag",
    ):
        assert f'id="{element_id}"' in html


@pytest.mark.parametrize("filename,mime", [("app.js", "javascript"), ("style.css", "text/css")])
def test_packaged_assets_available(filename, mime):
    with TestClient(local_app()) as client:
        response = client.get("/demo/assets/" + filename)
    assert response.status_code == 200
    assert mime in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "path", ["/demo/assets/.env", "/demo/assets/%2e%2e/%2e%2e/app.py", "/demo/assets/unknown.js"]
)
def test_static_directory_does_not_expose_backend_files(path):
    with TestClient(local_app()) as client:
        response = client.get(path)
    assert response.status_code == 404
