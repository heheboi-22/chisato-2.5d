#!/usr/bin/env python3
"""Turn a See-through PSD into one Anime2.5DRig rigs cleanly.

  python build_psd.py in.psd out.psd [--keep-neck] [--pad 120]

- See-through's --tblr_split names the two halves of a pair "eyewhite-l" / "eyewhite-r";
  Anime2.5DRig does not know those names and splits left from right on its own, so each pair
  is drawn back into one layer named for the part, where the first half of it stood.
- The neck is drawn into the top of the clothes (Anime2.5DRig's README: a body with the neck
  in it bends far more cleanly than a neck layer and a clothes layer turning against each other)
  unless --keep-neck.
- Headwear (ribbons, clips) is moved to the top, over the front hair.
- Near-transparent haze is cleared and empty layers are dropped.
- --pad N widens the canvas by N above and N/2 to each side (it stays square), so the head has
  room to move without its hair running off the top of the picture.
- --fill-from SRC.png (the picture See-through was run on, white background) puts back body
  parts See-through left out of every layer -- typically the sleeves at the sides, which it
  sometimes drops from "topwear". Whatever of the character in SRC (below the top of the
  clothes) no layer covers goes into a "handwear" layer just behind the clothes, reaching
  --fill-overlap px in under them so no gap opens when the body bends.
"""
import argparse
import re

import numpy as np
from PIL import Image
from psd_tools import PSDImage
from scipy import ndimage


def canvas_of(layer, size):
    """The layer as an RGBA array the size of the document."""
    w, h = size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img = layer.topil()
    if img is None:
        return np.array(out)
    out.alpha_composite(img.convert("RGBA"), (max(layer.left, 0), max(layer.top, 0)))
    return np.array(out)


def over(top, bottom):
    """Porter-Duff top-over-bottom on straight-alpha uint8 RGBA arrays."""
    ta = top[..., 3:4] / 255.0
    ba = bottom[..., 3:4] / 255.0
    oa = ta + ba * (1 - ta)
    rgb = (top[..., :3] * ta + bottom[..., :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.concatenate([rgb, oa * 255], -1).round().clip(0, 255).astype(np.uint8)


def missing_body(src, parts, min_area, overlap):
    """RGBA of the character in `src` that no part covers, below the top of the clothes."""
    rgb = src[..., :3].astype(np.int16)
    whiteness = rgb.min(-1)
    # Background: the near-white region connected to the top or side edges. Not the bottom edge:
    # the body is cut off there, and white clothes touching it would count as background.
    lab, _ = ndimage.label(whiteness > 235)
    edge = np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, edge[edge > 0])
    fg = ~bg

    covered = np.zeros(fg.shape, np.uint8)
    for _, rgba in parts:
        np.maximum(covered, rgba[..., 3], out=covered)
    hole = fg & (covered < 128)
    top = next((rgba for name, rgba in parts if name == "topwear"), None)
    if top is not None and (top[..., 3] > 128).any():
        hole[: np.nonzero((top[..., 3] > 128).any(1))[0][0]] = False   # leave the head alone
    hole = ndimage.binary_opening(hole, iterations=2)                   # drop edge slivers
    lab, n = ndimage.label(hole)
    sizes = ndimage.sum(hole, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.nonzero(sizes >= min_area)[0])
    for i in np.nonzero(sizes >= min_area)[0]:
        ys, xs = np.nonzero(lab == i + 1)
        print(f"  fill: {int(sizes[i])} px at {xs.min()},{ys.min()}-{xs.max()},{ys.max()}")
    if not keep.any():
        return None
    fill = ndimage.binary_dilation(keep, iterations=overlap) & fg
    # Soft edge where the outline meets the white background, so no white fringe.
    edge_px = fill & ndimage.binary_dilation(bg, iterations=2)
    alpha = np.where(fill, 255, 0).astype(np.float32)
    alpha[edge_px] = np.clip((250 - whiteness[edge_px]) / 50.0, 0, 1) * 255
    out = np.zeros_like(src)
    out[..., :3] = src[..., :3]
    out[..., 3] = alpha.round().astype(np.uint8)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--keep-neck", action="store_true")
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--fill-from", help="source picture; put back body parts no layer covers")
    ap.add_argument("--fill-min-area", type=int, default=1500)
    ap.add_argument("--fill-overlap", type=int, default=16)
    args = ap.parse_args()

    psd = PSDImage.open(args.src)
    size = psd.size
    # Bottom to top, as psd_tools lists them.
    parts = []          # [name, rgba]
    index = {}
    for layer in psd:
        name = re.sub(r"-[lr]$", "", layer.name)
        rgba = canvas_of(layer, size)
        if name in index:
            k = index[name]
            parts[k][1] = over(rgba, parts[k][1])
        else:
            index[name] = len(parts)
            parts.append([name, rgba])

    if args.fill_from:
        src = np.array(Image.open(args.fill_from).convert("RGBA"))
        if src.shape[1::-1] != tuple(size):
            raise SystemExit(f"{args.fill_from} is {src.shape[1]}x{src.shape[0]}, PSD is {size}")
        fill = missing_body(src, parts, args.fill_min_area, args.fill_overlap)
        if fill is not None:
            if "handwear" in index:
                k = index["handwear"]
                parts[k][1] = over(parts[k][1], fill)
            else:                                   # just behind the clothes
                k = index.get("topwear", 0)
                parts.insert(k, ["handwear", fill])
                index = {p[0]: i for i, p in enumerate(parts)}

    if not args.keep_neck and "neck" in index and "topwear" in index:
        neck = parts[index["neck"]][1]
        k = index["topwear"]
        top = parts[k][1]
        if args.fill_from:
            # See-through can paint the inside of a high collar (dark) over the neck. Where both
            # layers cover a pixel, keep whichever matches the source picture.
            both = (neck[..., 3] > 128) & (top[..., 3] > 128)
            d_neck = np.abs(neck[..., :3].astype(np.int16) - src[..., :3]).sum(-1)
            d_top = np.abs(top[..., :3].astype(np.int16) - src[..., :3]).sum(-1)
            neck_front = ndimage.binary_closing(
                ndimage.binary_opening(both & (d_neck + 30 < d_top), iterations=2), iterations=2)
            lab, n = ndimage.label(neck_front)
            sizes = ndimage.sum(neck_front, lab, range(1, n + 1))
            neck_front = np.isin(lab, 1 + np.nonzero(sizes >= 300)[0])
            if neck_front.any():
                print(f"  neck shown over clothes: {int(neck_front.sum())} px")
                top = top.copy()
                top[neck_front, 3] = 0
        parts[k][1] = over(top, neck)               # clothes in front of the neck
        parts = [p for p in parts if p[0] != "neck"]

    # Hair ribbons and clips sit on the hair, but See-through's depth puts the front hair over
    # them (its front hair is painted in under the ribbon), which hides the ribbon.
    parts.sort(key=lambda p: p[0] == "headwear")

    dx, dy = args.pad // 2, args.pad
    out = PSDImage.new(mode="RGBA", size=(size[0] + 2 * dx, size[1] + dy), depth=8)
    for name, rgba in parts:
        rgba = rgba.copy()
        rgba[rgba[..., 3] < 6] = 0                  # See-through leaves a haze of near-zero alpha
        if rgba[..., 3].max() <= 8:
            continue
        ys, xs = np.nonzero(rgba[..., 3] > 0)
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
        out.create_pixel_layer(Image.fromarray(rgba[y0:y1, x0:x1]), name=name, top=int(y0) + dy,
                               left=int(x0) + dx, opacity=255)
        print(f"{name:12s} {x0},{y0} {x1 - x0}x{y1 - y0}")
    out.save(args.dst)
    print("saved", args.dst)


if __name__ == "__main__":
    main()
