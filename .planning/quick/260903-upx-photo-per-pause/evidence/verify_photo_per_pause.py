"""6동작 라이브 검증 — 감점 unit 수 == 확정 확대 사진 수 (belle 09-03 규칙, quick-260903-upx).

각 영상을 앱 경로(e2e_app_path.py)로 분석 → renderedCompare 등장 → 게이트 부착(holdState 보유 카드) 대기 →
expected_units(파이프라인과 같은 criterion_units_from_records) vs confirmed 카드 수 비교. 순차 실행(파이프라인 동시성 비안전).
사용: backend/.venv/bin/python verify_photo_per_pause.py [uid]
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path('/Users/kimtaesung/Dev/SunityMotion')
SP = Path('/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/b6261bd3-eff6-4149-b01d-4456b90e7924/scratchpad')
sys.path.insert(0, str(REPO / 'backend/shared/python'))
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
spec = importlib.util.spec_from_file_location('pipeline_app', REPO / 'backend/functions/pipeline/app.py')
papp = importlib.util.module_from_spec(spec); spec.loader.exec_module(papp)  # type: ignore[union-attr]
import firebase_admin  # noqa: E402
from firebase_admin import credentials, firestore  # noqa: E402
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(str(REPO / 'firebase-sa.json')))
db = firestore.client()

UID = sys.argv[1] if len(sys.argv) > 1 else 'verifyupx0903'
MOTIONS = [
    ('pdshape', 'ref-pdshape'), ('climb', 'ref-climb'), ('power-spin', 'ref-power-spin'),
    ('elbow-twist-sister', 'ref-elbow-twist-sister'), ('kip-up', 'ref-kip-up'), ('peter-pan', 'ref-peter-pan'),
]


def expected_units(result: dict) -> int:
    recs = ((result.get('deductionBreakdown') or {}).get('records')) or []
    vv = result.get('visionVeto') or {}
    fault_joints = list(vv.get('faultJoints') or [])
    units = fz.criterion_units_from_records(recs, fault_joints, papp._KISMAM_TO_KEYPOINT, max_units=max(4, len(recs)))
    return len(units), len(recs)


def wait_final(uid: str, aid: str, timeout_s: int = 900) -> dict:
    ref = db.document(f'users/{uid}/analyses/{aid}')
    t0 = time.time(); rendered_at = None
    while time.time() - t0 < timeout_s:
        d = ref.get().to_dict() or {}
        r = d.get('result') or {}
        zooms = r.get('faultZoomComparisons') or []
        gated = any(isinstance(z, dict) and z.get('holdState') for z in zooms)
        if r.get('renderedCompare') and rendered_at is None:
            rendered_at = time.time()
        if gated or (rendered_at and time.time() - rendered_at > 150):
            return d
        if d.get('status') in ('error', 'failed'):
            return d
        time.sleep(10)
    return ref.get().to_dict() or {}


rows = []
for motion, ref_id in MOTIONS:
    video = SP / 'fixtures' / f'{motion}-fault.mp4'
    if not video.exists():
        rows.append((motion, 'NO_VIDEO', '-', '-', '-')); print(rows[-1], flush=True); continue
    t0 = time.time()
    out = subprocess.run([str(REPO / 'backend/.venv/bin/python'), str(REPO / 'backend/scripts/e2e_app_path.py'),
                          '--video', str(video), '--mode', 'mode1', '--reference', ref_id, '--uid', UID],
                         capture_output=True, text=True, timeout=1500)
    line = [l for l in out.stdout.splitlines() if l.strip().startswith('{')]
    if not line:
        rows.append((motion, 'E2E_FAIL', out.stdout[-200:] + out.stderr[-200:], '-', '-')); print(rows[-1], flush=True); continue
    j = json.loads(line[-1]); aid = j['analysisId']
    d = wait_final(UID, aid)
    r = d.get('result') or {}
    zooms = r.get('faultZoomComparisons') or []
    conf = [z for z in zooms if z.get('tier') != 'advisory']
    exp, nrec = expected_units(r)
    gated = sum(1 for z in conf if z.get('holdState'))
    unmarked = sum(1 for z in conf if z.get('userMarked') is False)
    verdict = 'PASS' if len(conf) == exp else 'FAIL'
    rows.append((motion, verdict, f'score={r.get("overallScore")} unreliable={(r.get("attributionReliability") or {}).get("unreliable")}',
                 f'records={nrec} expected={exp} confirmed={len(conf)} gated={gated} unmarked={unmarked}',
                 f'aid={aid[:8]} {round(time.time() - t0)}s'))
    print(rows[-1], flush=True)
print('=== SUMMARY ===')
for row in rows:
    print(' | '.join(str(x) for x in row))
(SP / 'verify_photo_per_pause_results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
print('ALL PASS' if all(r[1] == 'PASS' for r in rows) else 'SOME FAIL')
