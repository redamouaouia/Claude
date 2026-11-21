"""White versions of the company logo for the dark page backgrounds of Quality Dashboard V3.

Usage:  python make_logo_assets.py <logo.png>

<logo.png>: the logo in its usual colours, dark ink on a light or transparent background. Writes, in
out/brand/ (git-ignored, the logo is not stored in this repository):
- symbol_white.png: the symbol alone (the largest shape on the left of the logo), white, for the rail tile;
- logo_white.png: the whole logo, white, for the header.
The shapes are only recoloured, never redrawn: anti-aliased edges become transparency.
"""
import pathlib
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out" / "brand"


def coverage(img):
    """0..1 ink coverage of each pixel: dark ink = 1, light background or transparency = 0."""
    rgba = np.asarray(img.convert("RGBA")).astype(float)
    lum = rgba[..., :3].mean(axis=2)
    ink = np.percentile(lum[rgba[..., 3] > 200], 1)
    cov = np.clip((255 - lum) / (255 - ink), 0, 1)
    return cov * rgba[..., 3] / 255


def components(mask):
    """Connected shapes of a boolean mask, as a label array and a list of (label, x0, y0, x1, y1, size)."""
    h, w = mask.shape
    lab = np.zeros((h, w), int)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n = len(out) + 1
        lab[y0, x0] = n
        queue, xs, ys = deque([(y0, x0)]), [], []
        while queue:
            y, x = queue.popleft()
            xs.append(x)
            ys.append(y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        queue.append((yy, xx))
        out.append((n, min(xs), min(ys), max(xs), max(ys), len(xs)))
    return lab, out


def white(cov, keep, box, pad=4):
    x0, y0, x1, y1 = box
    h, w = cov.shape
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad + 1), min(h, y1 + pad + 1)
    alpha = (cov * keep)[y0:y1, x0:x1]
    out = np.zeros(alpha.shape + (4,), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.round(alpha * 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def main(src):
    cov = coverage(Image.open(src))
    lab, comps = components(cov > 0.2)
    comps = [c for c in comps if c[5] > 20]
    symbol = max((c for c in comps if c[1] == min(k[1] for k in comps)), key=lambda c: c[5])
    # anti-aliased edge pixels around the symbol belong to it: grow its mask by 2 px
    keep = lab == symbol[0]
    for _ in range(2):
        grown = keep.copy()
        grown[1:, :] |= keep[:-1, :]
        grown[:-1, :] |= keep[1:, :]
        grown[:, 1:] |= keep[:, :-1]
        grown[:, :-1] |= keep[:, 1:]
        keep = grown
    others = (lab > 0) & (lab != symbol[0])
    keep &= ~others
    OUT.mkdir(parents=True, exist_ok=True)
    white(cov, keep, symbol[1:5]).save(OUT / "symbol_white.png")
    box = (min(c[1] for c in comps), min(c[2] for c in comps), max(c[3] for c in comps), max(c[4] for c in comps))
    white(cov, np.ones_like(cov), box).save(OUT / "logo_white.png")
    print(f"{len(comps)} shapes; symbol {symbol[3] - symbol[1] + 1}x{symbol[4] - symbol[2] + 1} px, "
          f"logo {box[2] - box[0] + 1}x{box[3] - box[1] + 1} px -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
