#!/usr/bin/env python3
"""Tile pictures (or transparent frames, on a flat colour) into one sheet to look at.

  python contact_sheet.py 'gen/seed_*.png' sheet.jpg --cols 4 --tile 330
  python contact_sheet.py 'frames/f_*.png' strip.jpg --every 30 --cols 4 --tile 400
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("out")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile", type=int, default=330)
    ap.add_argument("--every", type=int, default=1, help="take every Nth file")
    ap.add_argument("--max", type=int, default=24)
    args = ap.parse_args()

    files = sorted(glob.glob(args.pattern))[::args.every][:args.max]
    if not files:
        raise SystemExit("no files match " + args.pattern)
    t, cols = args.tile, args.cols
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (t * cols, t * rows), (235, 225, 220))
    for k, f in enumerate(files):
        im = Image.open(f).convert("RGBA")
        bg = Image.new("RGBA", im.size, (235, 225, 220, 255))
        bg.alpha_composite(im)
        tile = bg.convert("RGB").resize((t, t))
        ImageDraw.Draw(tile).text((5, 5), os.path.basename(f), fill="black")
        sheet.paste(tile, ((k % cols) * t, (k // cols) * t))
    sheet.save(args.out, quality=88)
    print("wrote", args.out, len(files), "tiles")


if __name__ == "__main__":
    main()
