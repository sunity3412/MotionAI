#!/bin/bash
# Repeatability run: the champion's own footage, through the production app path,
# on today's code (ROT180 on, rot180_v1 references). One JSON line per analysis.
#
# Ordered by historical false-positive rate, highest first, so the run says
# something useful even if it has to be cut short.
set -u
REPO=/Users/kimtaesung/Dev/SunityMotion
OUT=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13/repeat_results.jsonl
FX=/Users/Shared/sunity-fx

run() {  # run <motion> <refId> <n>
  local m=$1 ref=$2 n=$3
  for i in $(seq 1 "$n"); do
    echo "$(date '+%H:%M:%S') START $m #$i" >&2
    "$REPO/backend/.venv/bin/python" "$REPO/backend/scripts/e2e_app_path.py" \
      --video "$FX/$m-correct.mp4" --mode mode1 --reference "$ref" --timeout 900 \
      2>/dev/null | tail -1 | \
      "$REPO/backend/.venv/bin/python" -c "
import sys, json
raw = sys.stdin.read().strip()
try:
    d = json.loads(raw)
except Exception:
    d = {'parse_error': raw[:200]}
d['motion'] = '$m'; d['run'] = $i
print(json.dumps(d, ensure_ascii=False))
" >> "$OUT"
    echo "$(date '+%H:%M:%S') DONE  $m #$i -> $(tail -1 "$OUT" | head -c 160)" >&2
  done
}

run power-spin ref-power-spin 4
run pdshape    ref-pdshape    2
run climb      ref-climb      2
run peter-pan  ref-peter-pan  1
run kip-up     ref-kip-up     1
echo "ALL DONE" >&2
