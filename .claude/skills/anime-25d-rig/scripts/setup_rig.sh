#!/bin/bash
# setup_rig.sh <dest-dir> <model.psd> — vendor Anime2.5DRig into <dest-dir> and make it open
# <model.psd> (copied in next to index.html) on load.
#
# The sample PSDs (18 MB) and tests are left out. app.js gets one patch: outside ?obs=1 mode it
# loads ?model= or the bundled model straight away instead of waiting for a drop.
set -euo pipefail
DEST=${1:?dest dir}
PSD=${2:?model psd}
NAME=$(basename "$PSD")
TMP=$(mktemp -d)
git clone --depth 1 https://github.com/852wa/Anime2.5DRig.git "$TMP/rig" >/dev/null 2>&1
mkdir -p "$DEST"
rsync -a --exclude .git --exclude __pycache__ --exclude 'sample*.psd' --exclude tests \
  --exclude start_obs.bat "$TMP/rig/" "$DEST/"
rm -rf "$TMP"
cp "$PSD" "$DEST/$NAME"

python3 - "$DEST/lib/app.js" "$DEST/index.html" "$NAME" <<'EOF'
import sys
app, html, name = sys.argv[1:]
s = open(app, encoding="utf-8").read()
s = s.replace("const SAMPLE_FILES={A:'sample2.psd',B:'sample.psd'};",
              "const SAMPLE_FILES={A:'%s',B:'%s'};" % (name, name))
old = """}else{
  sync.startPolling();
  if(CAMERA_MODE)setAuto('cam',true);
}"""
new = """}else{
  sync.startPolling();
  if(CAMERA_MODE)setAuto('cam',true);
  // anime-25d-rig: open the bundled model straight away (?model= picks another).
  {const path=RT.safeRelativePath(QUERY.get('model')||SAMPLE_FILES.A,'.psd');
   if(path)loadModel(fetchSource(path),path.split('/').pop());}
}"""
if old not in s:
    sys.exit("app.js changed upstream: autoload patch not applied (rig still works by drag & drop)")
open(app, "w", encoding="utf-8").write(s.replace(old, new))
h = open(html, encoding="utf-8").read()
h = h.replace("sample2.psd", name).replace("sample.psd", name)
open(html, "w", encoding="utf-8").write(h)
print("rig ready, model", name)
EOF
