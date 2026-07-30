"""무릎·팔꿈치 각도 베이크 go/no-go 측정 (읽기 전용, GPU 불필요).

이미 Firestore 에 올라와 있는 candidate `phase33-cm3-run1` 의 12관절
referenceKeypointReport 를 읽어, 기준측 ankle/elbow 가 fault_zoom 드로잉 게이트
(_KP_CONF_MIN = 0.5, 유한 좌표, (0,0) 아님)를 통과하는 프레임 비율을 센다.

통과율이 낮으면 12관절 기준을 확보해도 무릎·팔꿈치 각도는 fail-closed 로 안 그려진다
= 이 트랙 자체가 무의미. 그래서 GPU 를 쓰기 전에 이걸 먼저 잰다.
"""
from __future__ import annotations

import json
import math
import sys

import firebase_admin
from firebase_admin import credentials, firestore

CONF_MIN = 0.5  # fault_zoom._KP_CONF_MIN
CANDIDATE = "phase33-cm3-run1"
TARGETS = ("left_ankle", "right_ankle", "left_elbow", "right_elbow")
# 대조군 — 이미 각도가 그려지는 계열의 소스 관절
CONTROL = ("left_knee", "right_knee", "left_hip", "right_hip", "left_shoulder", "left_hand")


def gated(x: float, y: float, c: float) -> bool:
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(c)):
        return False
    if c < CONF_MIN:
        return False
    return not (x == 0.0 and y == 0.0)


def coverage(rep: dict, joint: str) -> tuple[float, int, int]:
    joints = list(rep.get("joints") or [])
    if joint not in joints:
        return (float("nan"), 0, 0)
    j = joints.index(joint)
    nj = len(joints)
    n = int(rep.get("frames") or 0)
    data = rep.get("data") or []
    conf = rep.get("confidence") or []
    ok = 0
    for f in range(n):
        di = (f * nj + j) * 2
        ci = f * nj + j
        if di + 1 >= len(data) or ci >= len(conf):
            continue
        if gated(float(data[di]), float(data[di + 1]), float(conf[ci])):
            ok += 1
    return (ok / n if n else float("nan"), ok, n)


def main() -> int:
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate("firebase-sa.json"))
    db = firestore.client()

    rows = []
    for doc in db.collection("reference").stream():
        mid = doc.id
        if mid.startswith("_"):
            continue
        vsnap = db.collection("reference").document(mid) \
                  .collection("versions").document(CANDIDATE).get()
        if not vsnap.exists:
            rows.append({"motion": mid, "error": f"no candidate {CANDIDATE}"})
            continue
        v = vsnap.to_dict() or {}
        rep = v.get("referenceKeypointReport")
        if not isinstance(rep, dict):
            rows.append({"motion": mid, "error": "no referenceKeypointReport on candidate"})
            continue
        row = {
            "motion": mid,
            "joints_n": len(rep.get("joints") or []),
            "frames": int(rep.get("frames") or 0),
            "fps": rep.get("fps"),
            "has_conf": bool(rep.get("confidence")),
        }
        for j in TARGETS + CONTROL:
            frac, ok, n = coverage(rep, j)
            row[j] = None if frac != frac else round(frac, 4)
        rows.append(row)

    rows.sort(key=lambda r: r.get("motion", ""))
    print(json.dumps(rows, ensure_ascii=False, indent=2))

    good = [r for r in rows if "error" not in r]
    print("\n=== 요약 (게이트 통과 프레임 비율, conf>=0.5 & 유효좌표) ===", file=sys.stderr)
    print(f"{'motion':26s} {'J':>3s} {'frames':>6s} | " +
          " ".join(f"{j.replace('left_','L.').replace('right_','R.'):>9s}" for j in TARGETS),
          file=sys.stderr)
    for r in good:
        vals = " ".join(
            f"{(r[j] if r[j] is not None else float('nan')):>9.3f}" for j in TARGETS
        )
        print(f"{r['motion']:26s} {r['joints_n']:>3d} {r['frames']:>6d} | {vals}", file=sys.stderr)
    for r in rows:
        if "error" in r:
            print(f"  ! {r['motion']}: {r['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
