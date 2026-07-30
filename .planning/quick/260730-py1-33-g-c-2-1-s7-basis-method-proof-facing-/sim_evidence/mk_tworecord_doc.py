"""임시 검증 doc 생성/삭제 — 한 부위(어깨)에 감점 2건인 케이스 렌더 확인용.

승인 목업 case 1(부위 단위 시트 1개 안에 결함 블록 2개, belle "무릎 피는 거 하나 어디 갔냐")은
기존 renderable doc 이 전부 부위당 1건이라 렌더로 확인할 수 없다. 구조 확인만을 위해
powerspin 검증 doc 을 복제하고 r02(left_knee)의 criterion/jointKey 를 right_shoulder 로
재매핑한다 — **한국어 카피는 원본(무릎) 그대로라 문구는 합성이다.** 구조(시트 1개 / 블록 2개 /
번호 1·2)만 판정 대상.

사용: python3 mk_tworecord_doc.py create | delete
"""
from __future__ import annotations

import copy
import sys

import firebase_admin
from firebase_admin import credentials, firestore

UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
SRC = "powerspinFault1785373695"
DST = "tmp-33g2-tworecord-verify"
OLD, NEW = "left_knee", "right_shoulder"


def remap(obj):
    """criterion/jointKey/recordId 안의 관절명만 치환 (카피 텍스트는 건드리지 않음)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("criterion", "recordId", "jointKey") and isinstance(v, str):
                out[k] = v.replace(OLD, NEW)
            elif k == "jointKeys" and isinstance(v, list):
                out[k] = [x.replace(OLD, NEW) if isinstance(x, str) else x for x in v]
            else:
                out[k] = remap(v)
        return out
    if isinstance(obj, list):
        return [remap(x) for x in obj]
    return obj


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "create"
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate("firebase-sa.json"))
    db = firestore.client()
    ref = db.collection("users").document(UID).collection("analyses").document(DST)

    if action == "delete":
        existed = ref.get().exists
        ref.delete()
        print(f"deleted={existed} {DST}")
        return 0

    src = db.collection("users").document(UID).collection("analyses").document(SRC).get()
    if not src.exists:
        print(f"source {SRC} missing", file=sys.stderr)
        return 1
    d = copy.deepcopy(src.to_dict() or {})
    d = remap(d)
    d["analysisId"] = DST
    d["sourceLabel"] = "TEMP-33G2-render-check-DELETE-ME"
    d["fileName"] = "임시검증(어깨2건).mp4"
    d["createdAt"] = int(d.get("createdAt") or 0) + 1  # 목록 최상단
    ref.set(d)

    res = d.get("result") or {}
    recs = (res.get("deductionBreakdown") or {}).get("records") or []
    print("created", DST)
    print("  records:", [r.get("recordId") for r in recs])
    print("  cards  :", [c.get("criterion") for c in (res.get("faultZoomComparisons") or [])])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
