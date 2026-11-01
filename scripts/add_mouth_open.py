#!/usr/bin/env python3
"""Add a mouth_open layer (from inpaint_mouth.py) to a rig PSD; See-through's mouth becomes mouth_close.

The open mouth is cut out as the convex hull of where the inpainted picture differs from
See-through's face layer inside the inpaint mask, so the layer covers the old smile line too.

  python add_mouth_open.py rig/x.psd inp/seed_0005.png st_out/<name>/face.png inp/mask.png rig/x.psd \
      --pad 160
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw
from psd_tools import PSDImage
from scipy import ndimage
from scipy.spatial import ConvexHull


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("psd")
    ap.add_argument("inpainted", help="full picture with the open mouth (inpaint_mouth.py output)")
    ap.add_argument("face", help="See-through's face.png")
    ap.add_argument("mask", help="inpaint_mouth.py's mask.png")
    ap.add_argument("out")
    ap.add_argument("--pad", type=int, default=160, help="the --pad build_psd.py used")
    ap.add_argument("--thr", type=int, default=18, help="colour difference that counts as changed")
    ap.add_argument("--preview", help="write a jpg of the cut layer over the face")
    args = ap.parse_args()

    inp = np.asarray(Image.open(args.inpainted).convert("RGB"))
    face = np.asarray(Image.open(args.face).convert("RGBA"))
    mask = np.asarray(Image.open(args.mask).convert("L")) > 0
    d = np.abs(inp.astype(int) - face[..., :3].astype(int)).max(-1)
    m = ndimage.binary_opening((d > args.thr) & mask, iterations=1)
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m = lab == 1 + int(np.argmax(sizes))
    ys, xs = np.nonzero(m)
    pts = np.c_[xs, ys]
    poly = [tuple(map(float, pts[i])) for i in ConvexHull(pts).vertices]
    hull = Image.new("L", inp.shape[1::-1], 0)
    ImageDraw.Draw(hull).polygon(poly, fill=255)
    hm = ndimage.binary_erosion(np.asarray(hull) > 0, iterations=1)
    a = ndimage.gaussian_filter(hm.astype(float), 0.8)
    rgba = np.dstack([inp, (a * 255).round().astype(np.uint8)])
    ys, xs = np.nonzero(a > 0.01)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    layer = Image.fromarray(rgba[y0:y1, x0:x1])
    print(f"mouth_open {x0},{y0} {x1 - x0}x{y1 - y0}")

    dx, dy = args.pad // 2, args.pad
    src = PSDImage.open(args.psd)
    out = PSDImage.new(mode="RGBA", size=src.size, depth=8)
    for l in src:
        if l.name == "mouth_open":
            continue
        name = "mouth_close" if l.name == "mouth" else l.name
        out.create_pixel_layer(l.topil().convert("RGBA"), name=name, top=l.top, left=l.left,
                               opacity=255)
        if name == "mouth_close":
            out.create_pixel_layer(layer, name="mouth_open", top=int(y0) + dy, left=int(x0) + dx,
                                   opacity=255)
    out.save(args.out)
    print("saved", args.out, [l.name for l in out])

    if args.preview:
        f = Image.fromarray(face).crop((x0 - 30, y0 - 30, x1 + 30, y1 + 30))
        g = f.copy()
        g.alpha_composite(layer, (30, 30))
        s = Image.new("RGB", (f.width * 2 + 10, f.height), (255, 255, 255))
        s.paste(f.convert("RGB"), (0, 0))
        s.paste(g.convert("RGB"), (f.width + 10, 0))
        s.resize((s.width * 3, s.height * 3), Image.LANCZOS).save(args.preview)


if __name__ == "__main__":
    main()
