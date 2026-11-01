# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Outfit missing, eyes closed, background not white | Prompt over 77 CLIP tokens, tail dropped | Shorten; character tags first (`gen_character.py` now refuses) |
| Ugly result overall, tiny face, blurry | Existing full-body/angled/768px art used as input | Generate a bust-up frontal picture at 1280 |
| Eyes don't blink, layers "未分類" in the rig | `--tblr_split` names like `eyewhite-r`; rigger's `squash()` makes `eyewhiter`, no alias | `build_psd.py` merges `-l/-r` pairs |
| Ribbon / hair clip gone | See-through puts inpainted `front hair` over `headwear` | `build_psd.py` moves `headwear` to the top |
| Neck/clothes seam breaks when turning | Separate `neck` + `topwear` | Fold neck into topwear (default) |
| Hair clipped at the top while moving | Hair touches canvas edge | `--pad 160` (more for wide hair) |
| Every layer's bbox is the full canvas | Near-zero alpha haze | Cleared (`alpha < 6 → 0`); rigger also filters specks |
| Sleeves/arms missing in the rig | See-through lost them on that picture | Try another seed; compare candidates |
| "このブラウザではWebGLを使用できません" | Browser has no WebGL (Claude desktop pane) | Real Chrome/Firefox, or headless Chrome + SwiftShader |
| Choppy video | Real-time capture on a CPU renderer | `record.js` virtual clock (performance.now + rAF replaced) |
| Blank/old frames from `toDataURL` | Canvas has `preserveDrawingBuffer:false` | Step and read in the same `page.evaluate` (record.js does) |
| `Cannot find module 'puppeteer-core'` | record.js resolves modules from the skill dir | `NODE_PATH=$PWD/node_modules` (render.sh sets it) |
| `ERR_CONNECTION_REFUSED` when recording | Static server not up; `pgrep -f "http.server 8765"` matched the ssh command itself so the server was never started | Start the server unconditionally (render.sh does), wait for curl |
| ssh exits 255 mid-command | `pkill -f record.js` killed the ssh shell whose command line contained "record.js" | Kill by PID or `pgrep -f "[r]ecord.js"` |
| ssh hangs after starting a background job | Job kept the session's stdio | `setsid nohup cmd > log 2>&1 < /dev/null &` |
| See-through CUDA OOM | ~11.6 GB usable VRAM | `--group_offload` |
| Model load fails at "loaded … layers 0" timeout | PSD path wrong / >128 MB | Check `?model=` path relative to rig dir; PSD under 128 MB |
