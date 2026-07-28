#!/usr/bin/env python3
"""Derive the public Case Architecture image variants from the approved Higgsfield asset.

Only ``images/higgsfield-case-architecture-hero.png`` is an allowed input, and only when it
still hashes to the approved cleaned derivative recorded in
``design/berhelaw-cinematic-2026-07-27/higgsfield-asset-brief.md``. The original model output
baked the firm name into the left field and is not approved for public use, so the hash guard
is the thing that keeps the rejected generation out of the build.

Three planes come out of the one source:

* ``world``   full 16:9 frame, the hero poster/environment behind the copy.
* ``object``  right-hand crop of the folded-plane object, composited with ``mix-blend-mode``
              on capable desktop so it reads as a separate depth plane.
* ``mobile``  deliberate portrait recomposition that keeps the object in the upper/right
              field and leaves a calm lower field so the first-viewport CTA stays readable.

Run ``python3 scripts/make_case_architecture_assets.py`` after changing any of the geometry
below, then rebuild the site.
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "images" / "higgsfield-case-architecture-hero.png"
APPROVED_SHA256 = "b889acb291485cdabdc8833f4ed2e1024ca034989aec2cd12de972b671c83861"

# The masked headline field of the approved derivative is a flat #020913, which is also the
# spec's ink black. Recomposition uses that exact colour so seams stay invisible.
FIELD = (2, 9, 19)

# The object begins where the flat mask ends; measured, not guessed.
OBJECT_LEFT = 1180

AVIF_QUALITY = 55
WEBP_QUALITY = 78

# (name, pixel widths, format list) - PNG stays at the smallest listed width so the
# legacy fallback stays inside the performance budget.
PLANS = [
    ("case-architecture-world", (1200, 1600, 2400), 1200),
    ("case-architecture-object", (800, 1200), 800),
    ("case-architecture-mobile", (720, 1080), 720),
]


def approved_source():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != APPROVED_SHA256:
        raise SystemExit(
            f"refusing to build: {SOURCE.relative_to(ROOT)} hashes to {digest}, "
            f"not the approved cleaned derivative {APPROVED_SHA256}"
        )
    return Image.open(SOURCE).convert("RGB")


def object_crop(source):
    """Right-hand crop holding the folded-plane object and its cobalt ribbons."""
    return source.crop((OBJECT_LEFT, 0, source.width, source.height))


def mobile_composition(source):
    """Portrait recomposition: object anchored upper/right, calm field below for the CTA.

    Nothing is generated here. The object crop is scaled and feathered onto the source's own
    background colour, so the result is a crop of the approved art rather than new imagery.
    """
    canvas_w, canvas_h = 1080, 1440
    canvas = Image.new("RGB", (canvas_w, canvas_h), FIELD)

    crop = object_crop(source)
    target_w = 860
    target_h = round(target_w * crop.height / crop.width)
    crop = crop.resize((target_w, target_h), Image.LANCZOS)

    # Feather every edge so the paste dissolves into the identical field colour.
    feather = 80
    mask = Image.new("L", (target_w, target_h), 0)
    ImageDraw.Draw(mask).rectangle(
        (feather, feather, target_w - feather, target_h - feather), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(feather / 2))

    # Upper/right anchor: the right edge bleeds off-canvas and the top is cropped, which
    # leaves roughly the lower 40% and the left quarter as calm field for the headline
    # and the first-viewport CTA.
    canvas.paste(crop, (canvas_w - target_w + 70, -50), mask)
    return canvas


def encode(image, stem, widths, png_width):
    written = []
    for width in widths:
        height = round(width * image.height / image.width)
        resized = image.resize((width, height), Image.LANCZOS)
        for suffix, params in (
            ("avif", {"quality": AVIF_QUALITY}),
            ("webp", {"quality": WEBP_QUALITY, "method": 6}),
        ):
            path = ROOT / "images" / f"{stem}-{width}.{suffix}"
            resized.save(path, **params)
            written.append(path)
        if width == png_width:
            path = ROOT / "images" / f"{stem}-{width}.png"
            resized.save(path, "PNG", optimize=True)
            written.append(path)
    return written


def main():
    source = approved_source()
    planes = {
        "case-architecture-world": source,
        "case-architecture-object": object_crop(source),
        "case-architecture-mobile": mobile_composition(source),
    }
    written = []
    for stem, widths, png_width in PLANS:
        written += encode(planes[stem], stem, widths, png_width)
    for path in sorted(written):
        with Image.open(path) as opened:
            size = opened.size
        print(f"{path.relative_to(ROOT)}  {size[0]}x{size[1]}  {path.stat().st_size / 1024:.1f} KB")
    print(f"wrote {len(written)} variants from the approved source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
