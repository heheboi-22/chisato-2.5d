# One-time setup (GPU machine)

Already done on `labkm-vps` (Nov 2026): See-through at `/root/see-through` with `.venv`, its
models in `~/.cache/huggingface/hub`, WAI checkpoint in `/root/chisato25d/models/`, node at
`/opt/node24/bin`, Chrome for Testing under
`/root/render-goodenough-battery-20261031-100553/node_modules/.remotion/chrome-for-testing/linux64/chrome-linux64/chrome`.
Check these exist before reinstalling anything. Reuse the checkpoint (symlink) instead of
downloading 6.9 GB again.

Disk: ~13 GB See-through models + 6.9 GB checkpoint + torch. ~1 GB per 12 s of recorded frames.

## See-through

```bash
cd /root && git clone https://github.com/shitagaki-lab/see-through.git && cd see-through
python3.12 -m venv .venv && source .venv/bin/activate
pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
ln -sf common/assets assets
```

Models (`layerdifforg/seethroughv0.0.2_layerdiff3d`, `24yearsold/seethroughv0.0.1_marigold`)
download on first run. Always run from the repo root. Low VRAM: `--group_offload` (~10 GB),
`inference_psd_quantized.py` (NF4, ~8 GB), `inference_psd_blockswap.py` (~8 GB bf16).

## SDXL checkpoint

```bash
$PY -c "from huggingface_hub import hf_hub_download as d; \
d('LyliaEngine/waiIllustriousSDXL_v170','waiIllustriousSDXL_v170.safetensors',local_dir='models')"
```

`from_single_file` fetches the small SDXL config files from the Hub on first load.

## Recorder

```bash
export PATH=/opt/node24/bin:$PATH
npm init -y && npm i puppeteer-core@23
```

Any Chrome/Chromium works; WebGL runs on SwiftShader (CPU) via
`--use-angle=swiftshader --enable-unsafe-swiftshader`, which is why recording uses a virtual
clock instead of real time.
