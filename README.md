# Chisato 2.5D

Nishikigi Chisato (Lycoris Recoil) as a moving 2.5D character — blinking, turning her head with
parallax, following the pointer, hair swinging — built the way the
[libwaifu/waifu2d demo](https://x.com/ling0322/status/2116457843981455648) is:

1. **Picture** — a front-facing bust-up drawn by WAI-Illustrious SDXL v17 (`scripts/gen_chisato.py`),
   upscaled to 1280² with img2img.
2. **Layers** — [See-through](https://github.com/shitagaki-lab/see-through) splits it into
   ~20 inpainted, depth-ordered layers (hair front/back, face, eyes, brows, mouth, ears, clothes, ribbon).
3. **Rig** — `scripts/build_psd.py` renames/merges those layers the way
   [Anime2.5DRig](https://github.com/852wa/Anime2.5DRig) (MIT, vendored in `rig/`) wants them,
   and Anime2.5DRig rigs and animates it in the browser with WebGL.
4. **Video** — `scripts/record.js` records the rig frame by frame on a virtual clock (60 fps,
   no dropped frames) and `scripts/compose.py` puts it on a background and encodes an MP4.

## Look at it

```bash
python3 -m http.server 8765 --directory rig
```

Open http://127.0.0.1:8765 — `chisato.psd` loads on its own. `?obs=1` is the clean view without
the editor (transparent background). Toggle マウス追従 to make her follow the pointer; keys
`1`–`7` are expressions. Needs a browser with WebGL.

## Remake it (on the GPU VPS)

Everything heavy runs on `labkm-vps` in `/root/chisato25d`, reusing `/root/see-through/.venv`.

```bash
python scripts/gen_chisato.py --ckpt models/waiIllustriousSDXL_v170.safetensors --out gen --seeds 1-12
python scripts/gen_chisato.py --ckpt ... --out hires --hires gen/seed_0004.png --seeds 4 --size 1280 --steps 30
(cd /root/see-through && .venv/bin/python inference/scripts/inference_psd.py \
   --srcp /root/chisato25d/hires/seed_0004_hires1280.png --save_dir /root/chisato25d/st_out \
   --save_to_psd --tblr_split --group_offload)
python scripts/build_psd.py st_out/seed_0004_hires1280.psd rig/chisato.psd --pad 160
python3 -m http.server 8765 --bind 127.0.0.1 --directory rig &
./scripts/render.sh chisato.psd chisato 12      # -> out/chisato.mp4
```
