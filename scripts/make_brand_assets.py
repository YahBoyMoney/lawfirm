#!/usr/bin/env python3
"""Create the compact public header/footer derivative of the authorized APC logo."""
import hashlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "images" / "the-berhe-law-firm-apc-logo-white.png"
OUTPUT = ROOT / "images" / "the-berhe-law-firm-apc-logo-white-320.webp"
APPROVED_SHA256 = "60dc2afa2437af718b9c28abca7dee057ae9ba1f1a15a07012db218020c76e8e"
WIDTH = 320


def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != APPROVED_SHA256:
        raise SystemExit(f"refusing to derive logo: authorized source hash changed ({digest})")
    with Image.open(SOURCE) as source:
        height = round(WIDTH * source.height / source.width)
        resized = source.convert("RGBA").resize((WIDTH, height), Image.Resampling.LANCZOS)
        resized.save(OUTPUT, "WEBP", lossless=True, method=6)
    print(f"{OUTPUT.relative_to(ROOT)} {WIDTH}x{height} {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
