set -u
SP=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/4ecaa5a2-717b-43a6-a9c5-e152a330b7a3/scratchpad
REPO=/Users/kimtaesung/Dev/SunityMotion
DATA=$REPO/.planning/phases/35-server-rendered-comparison-video/data
PY=$REPO/backend/.venv/bin/python
cd $REPO/backend
for m in elbow powerspin kipup pdshapefault peterpan pdshape realupload; do
  extra=""
  [ -f "$DATA/$m/moments.json" ] && extra="$extra --moments-json $DATA/$m/moments.json"
  [ "$m" = "pdshapefault" ] && extra="$extra --pair-override-json $REPO/.planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/pdshape_pair_overrides.json"
  echo "== PROBE $m =="
  $PY scripts/render_compare_prototype.py \
    --doc-json "$DATA/$m/doc.json" --align-json "$DATA/$m/align.json" \
    --user-video "$SP/p35/$m/user.mp4" --ref-video "$SP/p35/$m/ref.mp4" \
    --audio-dir "$SP/p35/$m/audio" --workdir "$SP/p35/$m/render" \
    --out "$SP/p35/$m/probe_unused.mp4" --probe $extra 2>&1
  echo "== EXIT $m $? =="
done
