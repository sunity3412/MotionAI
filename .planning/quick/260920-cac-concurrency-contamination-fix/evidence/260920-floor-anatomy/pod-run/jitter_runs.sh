#!/bin/bash
# How stable is the phase recognizer on identical footage?
#
# The technique cache is keyed by video hash, so re-uploading the same file returns
# the same cached moments and the same score - which says nothing about how the
# recognizer behaves. These five copies are stream-copies of the same clip with a
# different metadata comment: identical frames, identical duration, different bytes,
# therefore a cache miss and a fresh recognizer call each time.
#
# What varies between runs is the recognizer alone.
set -u
REPO=/Users/kimtaesung/Dev/SunityMotion
OUT=/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13/jitter_results.jsonl
FX=/Users/Shared/sunity-fx

for i in 1 2 3 4 5; do
  echo "$(date '+%H:%M:%S') START jitter #$i" >&2
  "$REPO/backend/.venv/bin/python" "$REPO/backend/scripts/e2e_app_path.py" \
    --video "$FX/ps-v$i.mp4" --mode mode1 --reference ref-power-spin --timeout 900 \
    2>/dev/null | tail -1 | \
    "$REPO/backend/.venv/bin/python" -c "
import sys, json
raw = sys.stdin.read().strip()
try:
    d = json.loads(raw)
except Exception:
    d = {'parse_error': raw[:200]}
d['variant'] = $i
print(json.dumps(d, ensure_ascii=False))
" >> "$OUT"
  echo "$(date '+%H:%M:%S') DONE  jitter #$i -> $(tail -1 "$OUT" | head -c 160)" >&2
done
echo "JITTER DONE" >&2
