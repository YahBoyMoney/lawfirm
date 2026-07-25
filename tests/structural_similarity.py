"""Grayscale, blurred structural similarity used by the visual-departure gates.

The V2 brief fixes the measurement: convert both screenshots to grayscale, apply a
24px Gaussian blur so type and texture drop out, and compare what is left. What
survives that blur is the large-scale composition, which is exactly what the audit
found unchanged in the rejected release.

The SSIM implementation matches scikit-image's default (7x7 uniform window, the
sample-covariance correction, and the standard 0.01/0.03 stabilisers) so the numbers
are comparable to the audit that produced 0.796 desktop and 0.942 mobile.
"""
import numpy as np
from PIL import Image, ImageFilter

BLUR_RADIUS = 24
WINDOW = 7
DYNAMIC_RANGE = 255.0


def blurred_grayscale(path, size=None):
    with Image.open(path) as opened:
        image = opened.convert("L")
        if size is not None and image.size != size:
            image = image.resize(size, Image.LANCZOS)
        return np.asarray(image.filter(ImageFilter.GaussianBlur(BLUR_RADIUS)), dtype=np.float64)


def _window_mean(values, size):
    totals = np.cumsum(np.cumsum(values, axis=0), axis=1)
    totals = np.pad(totals, ((1, 0), (1, 0)))
    block = (
        totals[size:, size:] - totals[:-size, size:] - totals[size:, :-size] + totals[:-size, :-size]
    )
    return block / (size * size)


def structural_similarity(first, second, window=WINDOW):
    if first.shape != second.shape:
        raise ValueError(f"shape mismatch: {first.shape} vs {second.shape}")
    count = window * window
    correction = count / (count - 1)
    mean_a = _window_mean(first, window)
    mean_b = _window_mean(second, window)
    var_a = correction * (_window_mean(first * first, window) - mean_a * mean_a)
    var_b = correction * (_window_mean(second * second, window) - mean_b * mean_b)
    covariance = correction * (_window_mean(first * second, window) - mean_a * mean_b)
    c1 = (0.01 * DYNAMIC_RANGE) ** 2
    c2 = (0.03 * DYNAMIC_RANGE) ** 2
    numerator = (2 * mean_a * mean_b + c1) * (2 * covariance + c2)
    denominator = (mean_a**2 + mean_b**2 + c1) * (var_a + var_b + c2)
    return float(np.mean(numerator / denominator))


def compare(candidate_path, baseline_path):
    """Structural similarity of two screenshots after grayscale plus 24px blur."""
    with Image.open(baseline_path) as baseline:
        size = baseline.size
    return structural_similarity(
        blurred_grayscale(candidate_path, size),
        blurred_grayscale(baseline_path, size),
    )


def dark_pixel_share(path, threshold=45):
    """Fraction of the frame darker than the audit's luminance threshold."""
    with Image.open(path) as opened:
        pixels = np.asarray(opened.convert("RGB"), dtype=np.float64)
    luminance = 0.299 * pixels[..., 0] + 0.587 * pixels[..., 1] + 0.114 * pixels[..., 2]
    return float(np.mean(luminance < threshold))
