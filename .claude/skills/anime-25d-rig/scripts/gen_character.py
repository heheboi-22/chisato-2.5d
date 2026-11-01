#!/usr/bin/env python3
"""Draw a rig-friendly anime character with an Illustrious SDXL checkpoint.

See-through + Anime2.5DRig rig best from a symmetric, straight-on, upper-body picture with the
face large in frame, hands out of the way and a plain background. This script wraps the
character's own Danbooru tags in the tags that ask for exactly that.

  # candidates at 1024
  python gen_character.py --ckpt waiIllustriousSDXL_v170.safetensors --out gen --seeds 1-12 \
      --tags "nishikigi chisato, lycoris recoil, lycoris uniform, red dress, blue neck ribbon, red eyes"
  # the chosen one, img2img'd up to See-through's 1280
  python gen_character.py --ckpt ... --out hires --tags "..." --hires gen/seed_0004.png --seeds 4 --size 1280

CLIP reads only 77 tokens of each prompt and SDXL silently drops the rest, so the script counts
them and refuses a prompt that would be cut (put the character's tags first and keep them short).
"""
import argparse
import os
import sys

import torch
from diffusers import (EulerAncestralDiscreteScheduler, StableDiffusionXLImg2ImgPipeline,
                       StableDiffusionXLPipeline)

QUALITY = "masterpiece, best quality"
RIG = ("1girl, solo, upper body, looking at viewer, straight-on, symmetrical, smile, "
       "white background, simple background, arms at sides")
NEGATIVE = ("worst quality, bad quality, lowres, closed eyes, ^_^, hands, v, from side, profile, "
            "detailed background, nude, text, watermark, blurry, cropped head")


def seeds_of(spec):
    out = []
    for part in str(spec).split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def tokens(pipe, text):
    # BOS and EOS take two of the 77.
    return len(pipe.tokenizer(text, truncation=False).input_ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="Illustrious-family SDXL .safetensors")
    ap.add_argument("--tags", required=True, help="the character's Danbooru tags, most important first")
    ap.add_argument("--rig_tags", default=RIG, help="override the rig-friendly framing tags")
    ap.add_argument("--negative", default=NEGATIVE)
    ap.add_argument("--out", default="gen")
    ap.add_argument("--seeds", default="1-12")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--cfg", type=float, default=6.0)
    ap.add_argument("--hires", help="img2img this picture up to --size instead of drawing new ones")
    ap.add_argument("--strength", type=float, default=0.42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    prompt = f"{QUALITY}, {args.tags}, {args.rig_tags}"

    pipe = StableDiffusionXLPipeline.from_single_file(args.ckpt, torch_dtype=torch.float16)
    for name, text in (("prompt", prompt), ("negative", args.negative)):
        n = tokens(pipe, text)
        print(f"{name}: {n}/77 tokens")
        if n > 77:
            sys.exit(f"{name} is {n} tokens; CLIP keeps 77 and the rest is dropped. Shorten --tags.")
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")
    pipe.enable_vae_tiling()

    if args.hires:
        from PIL import Image
        i2i = StableDiffusionXLImg2ImgPipeline(**pipe.components)
        src = Image.open(args.hires).convert("RGB").resize((args.size, args.size), Image.LANCZOS)
        img = i2i(prompt=prompt, negative_prompt=args.negative, image=src, strength=args.strength,
                  num_inference_steps=args.steps, guidance_scale=args.cfg,
                  generator=torch.Generator("cuda").manual_seed(seeds_of(args.seeds)[0])).images[0]
        name = os.path.splitext(os.path.basename(args.hires))[0] + f"_hires{args.size}.png"
        img.save(os.path.join(args.out, name))
        print("saved", os.path.join(args.out, name))
        return

    for seed in seeds_of(args.seeds):
        img = pipe(prompt=prompt, negative_prompt=args.negative, width=args.size, height=args.size,
                   num_inference_steps=args.steps, guidance_scale=args.cfg,
                   generator=torch.Generator("cuda").manual_seed(seed)).images[0]
        img.save(os.path.join(args.out, f"seed_{seed:04d}.png"))
        print("saved seed", seed, flush=True)


if __name__ == "__main__":
    main()
