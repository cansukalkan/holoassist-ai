"""Product and architecture website tests: strict CSP, synthetic labeling, and safe DOM usage."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from holoassist.api.app import local_app


def test_root_site_has_strict_security_headers_and_synthetic_scope():
    with TestClient(local_app()) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert '<html lang="tr">' in response.text
    assert "SENTETİK PROTOTİP" in response.text
    assert "guidance_allowed" in response.text
    assert 'href="/demo"' in response.text
    assert 'href="/docs"' in response.text


def test_site_html_contains_no_inline_styles_or_event_handlers():
    html = Path("ai-engine/holoassist/api/static/site.html").read_text(encoding="utf-8")
    assert "style=" not in html
    assert "onclick=" not in html


@pytest.mark.parametrize("filename,mime", [("site.js", "javascript"), ("site.css", "text/css")])
def test_site_packaged_assets_available_and_safe(filename, mime):
    with TestClient(local_app()) as client:
        response = client.get("/demo/assets/" + filename)
    assert response.status_code == 200
    assert mime in response.headers["content-type"]
    if filename == "site.js":
        assert "innerHTML" not in response.text


def test_html_routes_excluded_from_openapi_contract():
    with TestClient(local_app()) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/" not in paths
    assert "/demo" not in paths

