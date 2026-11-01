---
name: anime-25d-rig
description: Turn an anime character into a moving 2.5D avatar (blinks, head turns with parallax, eyes follow the pointer, hair and accessories swing) and render a smooth 60fps video of it, the way the libwaifu/waifu2d demo does. Pipeline - draw a rig-friendly picture with an Illustrious SDXL model, split it into inpainted layers with See-through (shitagaki-lab/see-through), clean the PSD up for Anime2.5DRig (852wa/Anime2.5DRig), rig and animate it in the browser, record frame by frame on a virtual clock and compose an MP4. Use when the user wants a character "dibikin 2.5D / Live2D-like / VTuber-style / bisa gerak / kayak demo see-through", wants to rig a layered PSD from See-through, or asks to redo or improve such a result for another character.
---

# Anime 2.5D rig

Picture → See-through layers → Anime2.5DRig → 60fps MP4. Worked example and long-form
explanation (Indonesian): `TUTORIAL.md` at the root of the chisato-2.5d project; the finished
Chisato build is in `rig/`, `out/`, `vps/` there.

```
prompt ──WAI-Illustrious SDXL──▶ 1024² ──img2img──▶ 1280² ──See-through──▶ PSD (~20 layers)
      ──build_psd.py──▶ rig-ready PSD ──Anime2.5DRig (WebGL)──▶ record.js ──compose.py──▶ MP4
```

Everything heavy runs on the GPU box (`labkm-vps`: RTX A4000, ~11.6 GB usable VRAM). Write
code locally, `rsync` it up, run there, `rsync` results back. Keep the user's laptop light.

## What makes it look good (read before starting)

The result is ~70% the input picture. The previous failed attempt used existing art
(full-body screenshots, official art, a peace-sign pose, 768px) plus a home-made "shift
the layers" parallax: tiny face, no blink, stiff hair, blurry hole-filling. Don't repeat it.

- **Draw a new picture**, don't hunt for one: bust-up, straight-on, symmetrical, both eyes
  open, arms down out of frame, plain white background, face large, a little room above
  the hair. Illustrious models know most anime characters by Danbooru tag, no LoRA needed.
- **Use Anime2.5DRig for motion**, never a custom parallax renderer. It does mesh warping,
  anchors, blink (with a generic closed eye if the PSD has none), eye darts, two-spring hair
  physics, breathing, sway and pointer follow. waifu2d's rig is a port of it.
- **Look at every stage** (contact sheets), not just exit codes.

## Steps

Working dir on the VPS: one folder per character, e.g. `/root/<char>25d`. `S` below is this
skill's `scripts/` dir (rsync it up). `PY=/root/see-through/.venv/bin/python` has torch,
diffusers, psd_tools, Pillow, numpy. First-time machine setup: `references/setup.md`.

1. **Candidates**
   ```bash
   $PY $S/gen_character.py --ckpt models/waiIllustriousSDXL_v170.safetensors --out gen --seeds 1-12 \
     --tags "<character tag>, <series tag>, <outfit tags>, <eye colour>"
   $PY $S/contact_sheet.py 'gen/seed_*.png' gen_sheet.jpg      # pull back and look
   ```
   Pick a seed: whole head with headroom, frontal, eyes open, no hands, outfit right.
   The script refuses prompts over CLIP's 77 tokens. Prompt advice: `references/prompting.md`.
   Show the user the sheet and say which seed you picked and why.

2. **Hires to 1280** (See-through's working size)
   ```bash
   $PY $S/gen_character.py --ckpt ... --tags "<same>" --out hires --hires gen/seed_000N.png --seeds N --size 1280 --steps 30
   ```

3. **See-through** (~14 min per picture with offload; run in background, watch a status file)
   ```bash
   cd /root/see-through && nohup .venv/bin/python inference/scripts/inference_psd.py \
     --srcp /root/<char>25d/hires/seed_000N_hires1280.png --save_dir /root/<char>25d/st_out \
     --save_to_psd --tblr_split --group_offload > /root/<char>25d/st.log 2>&1 &
   ```
   `--group_offload` is required on this card (~10 GB peak). Running two pictures? Queue them
   in one script, not in parallel. Check `st_out/<name>/` PNGs: face inpainted under the bangs,
   back hair whole, accessories separate.

4. **Rig-ready PSD**
   ```bash
   $PY $S/build_psd.py st_out/<name>.psd rig/<char>.psd --pad 160
   ```
   Fixes: merges `-l/-r` pairs (rigger doesn't know those names → eyes wouldn't blink), moves
   `headwear` above `front hair` (else ribbons/clips vanish), folds `neck` into `topwear`
   (`--keep-neck` to skip), clears alpha haze, pads the canvas so hair doesn't clip at the top.
   Twin tails / wide hair: the pad adds `N/2` each side; raise it if hair touches the sides.

5. **Rig**: `bash $S/setup_rig.sh rig rig/<char>.psd` — vendors Anime2.5DRig into `rig/` and
   makes it open the model on load. View: `python3 -m http.server 8765 --directory rig` →
   `/` = editor, `/?obs=1&model=<char>.psd` = clean transparent view. Needs WebGL; the Claude
   desktop browser pane has none, so check visually through the recorder instead.

6. **Quick motion test**, then **render**
   ```bash
   npm i puppeteer-core@23          # once, in the working dir
   export CHROME=<chrome binary> PY
   # quick look: 8 s at 4 fps
   NODE_PATH=$PWD/node_modules node $S/record.js --url "http://127.0.0.1:8765/?obs=1&model=<char>.psd" \
     --out tf --seconds 8 --fps 4 --warmup 0.5 --pointer     # (serve rig/ first)
   $PY $S/contact_sheet.py 'tf/f_*.png' strip.jpg --every 4 --cols 4 --tile 400
   # final: 12 s, 60 fps, 1080², background from the character's palette
   BG_INNER=fff9f0 BG_OUTER=ecc4be bash $S/render.sh rig <char>.psd <char> 12 1080
   ```
   `render.sh` starts and stops its own static server. Output: `out/<char>.mp4` and
   `frames_<char>/` (transparent PNGs at PSD size, for re-compositing).

7. **Check the video**: face crop tiled at 10 fps — blinks happen, no gaps at the face/ear/neck
   edges when the head turns, accessories visible and swinging, nothing clipped.
   ```bash
   ffmpeg -i out/<char>.mp4 -vf "crop=560:420:260:200,fps=10,scale=280:-1,tile=8x6" -frames:v 1 face.jpg
   ```
   Then `rsync` `out/` (and whatever the user wants) back and send the MP4.

## Rules

- Don't commit, push, or delete anything the user didn't ask for. Ask before removing an
  older attempt's files, even on the VPS.
- Never `pkill -f <pattern>` / `pgrep -f` with a pattern that also appears in your own ssh
  command line — it matches (and kills) your own shell. Kill by PID, or use the `[h]ttp`
  bracket trick.
- Stop any server you start when done (`render.sh` cleans up its own).
- Long VPS jobs: `setsid nohup ... < /dev/null &`, then poll a status/log file.

## References

- `references/prompting.md` — tags that make a picture rig well, the 77-token limit, picking seeds.
- `references/setup.md` — installing See-through, the SDXL checkpoint, Chrome/puppeteer.
- `references/troubleshooting.md` — every failure met so far and its fix.
