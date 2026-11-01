#!/usr/bin/env python3
"""Draw an open mouth into a character picture with SDXL inpainting, for a mouth_open layer.

See-through gives only the mouth as drawn (usually a closed smile). Anime2.5DRig needs a
separate open mouth to show when the mouth opens, so this repaints just the mouth area of the
picture, in the same model and style, with an open mouth.

The face around the mouth is cut out and scaled up to 1024 so SDXL draws it at its working
size, the mouth is repainted inside a soft ellipse, and the result is scaled back and pasted
into the full picture.

  python inpaint_mouth.py --ckpt models/waiIllustriousSDXL_v170.safetensors \
      --src hires/seed_0003_hires1280.png --mouth st_out/seed_0003_hires1280/mouth.png \
      --tags "nishikigi chisato, lycoris recoil, red eyes" --out inp_b --seeds 1-8
"""
import argparse
import os

import numpy as np
import torch
from diffusers import (EulerAncestralDiscreteScheduler, StableDiffusionXLInpaintPipeline,
                       StableDiffusionXLPipeline)
from PIL import Image, ImageDraw, ImageFilter

PROMPT = ("masterpiece, best quality, {tags}, 1girl, solo, close-up, looking at viewer, "
          "open mouth, :d, smile, upper teeth only, tongue")
NEGATIVE = ("worst quality, bad quality, lowres, closed mouth, blurry, text, watermark, "
            "extra mouth, fangs, lipstick, lower teeth")


def seeds_of(spec):
    out = []
    for part in str(spec).split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--src", required=True, help="the picture See-through ran on")
    ap.add_argument("--mouth", required=True, help="See-through's mouth.png (finds the mouth)")
    ap.add_argument("--tags", required=True)
    ap.add_argument("--out", default="inp")
    ap.add_argument("--seeds", default="1-8")
    ap.add_argument("--crop", type=int, default=400, help="side of the face crop, in src px")
    ap.add_argument("--rx", type=float, default=1.35, help="mask half-width / mouth half-width")
    ap.add_argument("--ry", type=float, default=40, help="mask half-height, in src px")
    ap.add_argument("--drop", type=float, default=14, help="mask centre below the mouth line")
    ap.add_argument("--strength", type=float, default=0.95)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cfg", type=float, default=6.0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    src = Image.open(args.src).convert("RGB")
    a = np.asarray(Image.open(args.mouth).convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a > 64)
    mx0, mx1, my0, my1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (mx0 + mx1) / 2, (my0 + my1) / 2
    print(f"mouth {mx0},{my0}-{mx1},{my1}")

    # Mask: an ellipse a bit wider than the mouth, reaching down where the open mouth goes.
    mask = Image.new("L", src.size, 0)
    rx, ry, mcy = (mx1 - mx0) / 2 * args.rx, args.ry, cy + args.drop
    ImageDraw.Draw(mask).ellipse((cx - rx, mcy - ry, cx + rx, mcy + ry), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4))

    c = args.crop
    box = (int(cx - c / 2), int(cy - c * 0.55), int(cx + c / 2), int(cy + c * 0.45))
    crop = src.crop(box).resize((1024, 1024), Image.LANCZOS)
    cmask = mask.crop(box).resize((1024, 1024), Image.LANCZOS)

    base = StableDiffusionXLPipeline.from_single_file(args.ckpt, torch_dtype=torch.float16)
    pipe = StableDiffusionXLInpaintPipeline(**base.components)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")
    prompt = PROMPT.format(tags=args.tags)
    for name, text in (("prompt", prompt), ("negative", NEGATIVE)):
        n = len(pipe.tokenizer(text, truncation=False).input_ids)
        print(f"{name}: {n}/77 tokens")
        assert n <= 77, f"{name} over CLIP's 77 tokens"

    mask.save(os.path.join(args.out, "mask.png"))
    for seed in seeds_of(args.seeds):
        img = pipe(prompt=prompt, negative_prompt=NEGATIVE, image=crop, mask_image=cmask,
                   strength=args.strength, num_inference_steps=args.steps,
                   guidance_scale=args.cfg, width=1024, height=1024,
                   generator=torch.Generator("cuda").manual_seed(seed)).images[0]
        back = img.resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
        full = src.copy()
        full.paste(back, box[:2], mask.crop(box))
        full.save(os.path.join(args.out, f"seed_{seed:04d}.png"))
        print("saved seed", seed, flush=True)


if __name__ == "__main__":
    main()
