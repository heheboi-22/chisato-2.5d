#!/bin/bash
# render.sh <model.psd> <name> [seconds] — record the rig at 60fps and compose an MP4.
set -e
cd /root/chisato25d
export PATH=/opt/node24/bin:$PATH
export CHROME=/root/render-goodenough-battery-20261031-100553/node_modules/.remotion/chrome-for-testing/linux64/chrome-linux64/chrome
rm -rf frames_$2
node scripts/record.js --url "http://127.0.0.1:8765/?obs=1&model=$1" --out frames_$2 --seconds ${3:-12} --fps 60 --warmup 2 --pointer
/root/see-through/.venv/bin/python scripts/compose.py --frames frames_$2 --fps 60 --out out/$2.mp4 --size 1080
