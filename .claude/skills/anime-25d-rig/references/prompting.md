# Prompting a rig-friendly picture

Model: an Illustrious-family SDXL checkpoint. Default **WAI-Illustrious SDXL v17**
(`LyliaEngine/waiIllustriousSDXL_v170`, single 6.9 GB `.safetensors`). It knows popular anime
characters by their Danbooru tag. Sampler Euler Ancestral, 28 steps, CFG 6, 1024².

## The tags `gen_character.py` adds around the character's own

| What the rig needs | Positive | Negative |
|---|---|---|
| Bust-up, face large | `upper body` | `cropped head` |
| Frontal, symmetric (parallax balanced left/right) | `looking at viewer, straight-on, symmetrical` | `from side, profile` |
| Eyes open (the rig makes the blink) | `smile` | `closed eyes, ^_^` |
| Hands out of the way | `arms at sides` | `hands, v` |
| Clean separation | `white background, simple background` | `detailed background` |

## Character tags (`--tags`)

Most important first: character tag, series tag, outfit, hair/eye colour if the model drifts.
Examples:

- `nishikigi chisato, lycoris recoil, lycoris uniform, red dress, blue neck ribbon, red eyes`
- `inoue takina, lycoris recoil, lycoris uniform, blue dress, black hair, long hair, purple eyes`
- `hatsune miku, vocaloid, twintails, aqua hair, aqua necktie, detached sleeves`

## The 77-token trap

CLIP reads 77 tokens per prompt; diffusers' SDXL drops the rest with only a log warning. A
long first attempt lost the uniform, the white background and (from the negative) `closed
eyes` — so most pictures came out in a T-shirt with eyes shut. The script now counts tokens
and stops above 77. Drop decoration tags (`absurdres`, `very aesthetic`, `clean lineart`)
before character tags.

## Picking the seed

Generate 12, tile them, and choose:
1. Whole head inside the frame with some room above (hair touching the top edge clips when the head moves).
2. Frontal, both eyes open, no hands.
3. Character details right (accessories on the correct side, outfit).
4. Prefer a larger face (sharper eyes, better blink) as long as shoulders show.

Then img2img to 1280 at strength ~0.42: sharpens lines without changing the face.
