#!/usr/bin/env python3
"""Put the recorded transparent frames on a background and encode an MP4.

  python compose.py --frames frames --fps 60 --out chisato.mp4 [--size 1080] \
      [--inner fff9f0 --outer ecc4be]

The background is a soft radial gradient, --inner at the middle into --outer at the corners
(default: warm cream into a dusty rose), with a faint drop shadow under the character so it
sits on it. Pick the two colours from the character's palette.
"""
import argparse
import glob
import os
import subprocess

import numpy as np
from PIL import Image, ImageFilter


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def background(w, h, inner="fff9f0", outer="ecc4be"):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.5, h * 0.42
    r = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2) / 0.75
    r = np.clip(r, 0, 1)[..., None]
    inner, outer = hex_rgb(inner), hex_rgb(outer)
    img = inner * (1 - r ** 1.6) + outer * (r ** 1.6)
    # A little grain so the gradient does not band once encoded.
    img += np.random.default_rng(0).normal(0, 1.2, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=0, help="output side in px (0 = frame size)")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--inner", default="fff9f0", help="background colour at the middle (hex)")
    ap.add_argument("--outer", default="ecc4be", help="background colour at the corners (hex)")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.frames, "f_*.png")))
    first = Image.open(files[0])
    w, h = first.size
    side = args.size or w
    bg = background(w, h, args.inner, args.outer)

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{side}x{round(side * h / w)}", "-r", str(args.fps), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    for f in files:
        fg = Image.open(f).convert("RGBA")
        # Soft shadow: the character's own alpha, blurred and offset down.
        a = fg.getchannel("A").filter(ImageFilter.GaussianBlur(18))
        shadow = Image.new("RGBA", fg.size, (120, 60, 60, 0))
        shadow.putalpha(a.point(lambda v: int(v * 0.22)))
        frame = bg.copy().convert("RGBA")
        frame.alpha_composite(shadow, (0, 14))
        frame.alpha_composite(fg)
        frame = frame.convert("RGB")
        if side != w:
            frame = frame.resize((side, round(side * h / w)), Image.LANCZOS)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", args.out, len(files), "frames")


if __name__ == "__main__":
    main()
