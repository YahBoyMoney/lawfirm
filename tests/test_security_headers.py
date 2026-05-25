from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parsed_headers_for_path(target_path):
    text = (ROOT / "_headers").read_text(encoding="utf-8")
    headers = {}
    in_target_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            in_target_block = False
            continue
        if not line.startswith(" "):
            in_target_block = line.strip() == target_path
            continue
        if in_target_block and ":" in line:
            name, _, value = line.strip().partition(":")
            headers[name.strip()] = value.strip()
    return headers


def parsed_root_headers():
    return parsed_headers_for_path("/*")


def test_root_security_headers_present_and_well_formed():
    headers = parsed_root_headers()
    assert headers.get("Strict-Transport-Security", "").startswith("max-age=31536000")
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert headers.get("Origin-Agent-Cluster") == "?1"
    assert headers.get("X-DNS-Prefetch-Control") == "on"
    assert headers.get("X-Permitted-Cross-Domain-Policies") == "none"

    permissions_policy = headers.get("Permissions-Policy", "")
    for directive in (
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "interest-cohort=()",
        "browsing-topics=()",
        "payment=()",
        "usb=()",
        "magnetometer=()",
        "accelerometer=()",
        "gyroscope=()",
    ):
        assert directive in permissions_policy, f"Permissions-Policy missing {directive}"

    csp = headers.get("Content-Security-Policy", "")
    assert "form-action 'self' https://docs.google.com" in csp
    assert "connect-src 'self' https://docs.google.com" in csp
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    assert "frame-ancestors 'self'" in csp


def test_success_page_is_header_hardened_against_indexing():
    success_headers = parsed_headers_for_path("/success.html")
    assert success_headers.get("X-Robots-Tag") == "noindex, nofollow"

    html = (ROOT / "success.html").read_text(encoding="utf-8").lower()
    assert '<meta name="robots" content="noindex, nofollow"' in html
