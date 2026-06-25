"""Phase 24 sweep readback — visionVeto.status 진단.

run_sweep.py 가 남긴 baseline/phase24_sweep_report.json 의 analysisId 들로 Firestore
문서를 다시 읽어 각 멤버의 result.visionVeto.status (왜 breakdown 이 부착/미부착됐는지)
+ deductionBreakdown record 수 + overallScore 를 한 표로 출력한다. 채점 게이트 아님 —
관찰/진단용 (belle 검증 입력). 점수 재조정 금지.

실행 (Pod):
    cd /workspace/SunityMotion/backend && source /workspace/aws_env.sh && \
    export FIREBASE_SA_PATH=/workspace/firebase-sa.json && \
    PYTHONPATH=shared/python:. python3 evals/phase24/read_veto_status.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

UID = "phase24eval"


def main() -> int:
    report_path = HERE / "baseline" / "phase24_sweep_report.json"
    if not report_path.exists():
        print(f"NO REPORT at {report_path}", flush=True)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))

    from sunity_shared import firestore_admin as fa  # noqa: E402

    print(f"{'motion':22s} | {'label':7s} | {'status':10s} | {'overall':7s} | "
          f"{'veto.status':22s} | recs | criteria", flush=True)
    print("-" * 110, flush=True)
    for r in report.get("results", []):
        aid = r["analysisId"]
        d = fa.get_analysis(UID, aid) or {}
        res = d.get("result") or {}
        vv = res.get("visionVeto") or {}
        bd = res.get("deductionBreakdown") or {}
        recs = bd.get("records") if isinstance(bd, dict) else None
        crit = sorted({rr.get("criterion") for rr in (recs or [])}) if recs is not None else None
        print(
            f"{r['motion_id']:22s} | {r['label']:7s} | {str(d.get('status')):10s} | "
            f"{str(res.get('overallScore')):7s} | {str(vv.get('status')):22s} | "
            f"{len(recs) if recs is not None else '-':>4} | {crit}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
