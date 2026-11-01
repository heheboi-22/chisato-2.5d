#!/bin/bash
# render.sh <rig-dir> <model.psd> <name> [seconds] [size]
#   Serve <rig-dir>, record <model.psd> in it at 60 fps on a virtual clock, compose an MP4.
#   -> frames_<name>/ (transparent PNGs at the PSD's size) and out/<name>.mp4
#
# Env: CHROME (Chrome/Chromium binary, required), PY (python with Pillow+numpy, default python3),
#      puppeteer-core installed in the working dir (npm i puppeteer-core@23) or on NODE_PATH,
#      PORT (default 8765), BG_INNER / BG_OUTER (background colours, hex), POINTER=0 to not
#      follow a scripted pointer.
set -euo pipefail
RIG=${1:?rig dir}; MODEL=${2:?model.psd inside rig dir}; NAME=${3:?name}
SECONDS_=${4:-12}; SIZE=${5:-1080}
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}; PORT=${PORT:-8765}
: "${CHROME:?set CHROME to a Chrome/Chromium binary}"

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$RIG" > "http_$NAME.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 50); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.2; done

rm -rf "frames_$NAME"
POINTER_FLAG=--pointer; [ "${POINTER:-1}" = 0 ] && POINTER_FLAG=
# record.js lives in the skill, so point node at the working dir's node_modules.
NODE_PATH="${NODE_PATH:-$PWD/node_modules}" CHROME="$CHROME" node "$HERE/record.js" --url "http://127.0.0.1:$PORT/?obs=1&model=$MODEL" \
  --out "frames_$NAME" --seconds "$SECONDS_" --fps 60 --warmup 2 $POINTER_FLAG
mkdir -p out
"$PY" "$HERE/compose.py" --frames "frames_$NAME" --fps 60 --out "out/$NAME.mp4" --size "$SIZE" \
  ${BG_INNER:+--inner "$BG_INNER"} ${BG_OUTER:+--outer "$BG_OUTER"}
