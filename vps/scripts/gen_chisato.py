#!/usr/bin/env python3
"""Generate front-facing Chisato Nishikigi bust-up illustrations for See-through.

See-through + Anime2.5DRig rig best from a symmetric, straight-on, upper-body picture
with the face large in frame, hands out of the way and a plain background.

  python gen_chisato.py --ckpt waiIllustriousSDXL_v170.safetensors --out gen --seeds 1-12
  python gen_chisato.py --ckpt ... --out gen --hires gen/seed_0007.png --size 1280
"""
import argparse
import os

import torch
from diffusers import (EulerAncestralDiscreteScheduler, StableDiffusionXLImg2ImgPipeline,
                       StableDiffusionXLPipeline)

# Both prompts stay under CLIP's 77 tokens: SDXL drops whatever comes after.
PROMPT = (
    "masterpiece, best quality, nishikigi chisato, lycoris recoil, 1girl, solo, "
    "lycoris uniform, red dress, blue neck ribbon, upper body, "
    "looking at viewer, straight-on, symmetrical, smile, red eyes, "
    "white background, simple background, arms at sides"
)
NEGATIVE = (
    "worst quality, bad quality, lowres, closed eyes, ^_^, hands, v, from side, profile, "
    "detailed background, nude, text, watermark, blurry, cropped head"
)


def seeds_of(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default="gen")
    ap.add_argument("--seeds", default="1-8")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--cfg", type=float, default=6.0)
    ap.add_argument("--hires", help="upscale this picture with img2img to --size")
    ap.add_argument("--strength", type=float, default=0.42)
    ap.add_argument("--prompt_extra", default="")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    prompt = PROMPT + (", " + args.prompt_extra if args.prompt_extra else "")

    pipe = StableDiffusionXLPipeline.from_single_file(args.ckpt, torch_dtype=torch.float16)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")
    pipe.enable_vae_tiling()

    if args.hires:
        from PIL import Image
        i2i = StableDiffusionXLImg2ImgPipeline(**pipe.components)
        src = Image.open(args.hires).convert("RGB").resize((args.size, args.size), Image.LANCZOS)
        seed = seeds_of(args.seeds)[0]
        img = i2i(prompt=prompt, negative_prompt=NEGATIVE, image=src, strength=args.strength,
                  num_inference_steps=args.steps, guidance_scale=args.cfg,
                  generator=torch.Generator("cuda").manual_seed(seed)).images[0]
        name = os.path.splitext(os.path.basename(args.hires))[0] + f"_hires{args.size}.png"
        img.save(os.path.join(args.out, name))
        print("saved", name)
        return

    for seed in seeds_of(args.seeds):
        img = pipe(prompt=prompt, negative_prompt=NEGATIVE, width=args.size, height=args.size,
                   num_inference_steps=args.steps, guidance_scale=args.cfg,
                   generator=torch.Generator("cuda").manual_seed(seed)).images[0]
        img.save(os.path.join(args.out, f"seed_{seed:04d}.png"))
        print("saved seed", seed, flush=True)


if __name__ == "__main__":
    main()
