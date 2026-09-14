#!/usr/bin/env python3
"""홀드 유지시간 측정 — IPSF 2초 요건의 기질 (스파이크, 2026-09-14).

## 왜 필요한가

IPSF Code of Points 2025-2027 V2 는 요소 미인정 조건으로 2초 홀드를 요구하고,
그 문구가 요소 기준에 **547회** 등장한다 — 사실상 모든 요소에 붙는다.

    p.19  "The athlete will NOT be awarded points if he/she fails to hold the
           position of a compulsory element for the required two (2) seconds"
    p.149 "The final position must be fixed for two seconds. The transition in and
           out of the compulsory element will not be counted towards the holding."

그런데 **우리는 이 양을 재지 않는다.** `dimensions.hold_window` 는 "얼마나 버텼나"가
아니라 "어느 구간을 채점할까"를 고르는 함수다 — 창 길이가 `t // 4` 로 **영상 길이에
비례해 고정**돼 있어서, 3초를 버티든 0.2초를 버티든 같은 크기의 창이 하나 나온다.
`holdDuration` 류 필드는 계약(analysis.ts / models.py)에도 없다.

## 이 측정이 깊이를 필요로 하지 않는 이유

"얼마나 오래 정지했나"는 시간축 양이다. 관절각이 2D 투영각이라 **절대값**은 틀릴 수
있지만, **변화량이 작다**는 판정은 투영과 무관하게 성립한다(카메라가 고정이면).
그래서 split(깊이 필요) 과 달리 지금 스택에서 바로 잴 수 있다.

## 임계값을 정하지 않는다

'정지'의 기준을 지금 하나로 박으면 curve-fit 이다. 대신 **여러 임계에서의 최장
홀드를 표로 내어 민감도를 보여준다.** belle 이 실제 영상과 대조해 고를 수 있게.

## 한계

- 카메라가 움직이면 정지 판정이 깨진다(핸드헬드 패닝). 폴 축 기준 좌표가 되면 완화된다.
- 전이 구간 제외(IPSF 요건)는 아직 안 한다 — 최장 연속 정지만 낸다.
- 9fps 샘플링이라 시간 해상도가 0.11초다. 2초 판정에는 충분하다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ANALYSIS_FPS = 9.0  # frame_extractor.py target_fps — keypointReport 의 18fps 가 아니다
IPSF_HOLD_SEC = 2.0


def longest_still_run(angles: np.ndarray, thresh_deg_per_frame: float) -> tuple[int, int, int]:
    """(최장 연속 정지 프레임수, 시작, 끝). 정지 = 프레임간 관절각 변화 평균 <= 임계."""
    if angles.shape[0] < 2:
        return 0, 0, 0
    delta = np.nanmean(np.abs(np.diff(angles, axis=0)), axis=1)  # (T-1,)
    still = delta <= thresh_deg_per_frame
    best = cur = 0
    best_end = 0
    for i, s in enumerate(still):
        cur = cur + 1 if s else 0
        if cur > best:
            best, best_end = cur, i + 1
    return best, best_end - best, best_end


def profile(angles: np.ndarray, fps: float = ANALYSIS_FPS) -> dict:
    delta = np.nanmean(np.abs(np.diff(angles, axis=0)), axis=1)
    out = {
        "frames": int(angles.shape[0]),
        "duration_s": round(angles.shape[0] / fps, 2),
        "delta_p10": round(float(np.nanpercentile(delta, 10)), 2),
        "delta_p50": round(float(np.nanpercentile(delta, 50)), 2),
        "delta_p90": round(float(np.nanpercentile(delta, 90)), 2),
        "holds": {},
    }
    for thr in (1.0, 2.0, 3.0, 5.0, 8.0):
        n, s, e = longest_still_run(angles, thr)
        out["holds"][thr] = {
            "frames": n, "sec": round(n / fps, 2),
            "at_sec": round(s / fps, 2),
            "meets_ipsf_2s": bool(n / fps >= IPSF_HOLD_SEC),
        }
    return out


def _from_reference(motion_id: str):
    repo = pathlib.Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repo / "backend" / "scripts"))
    import e2e_app_path as e2e
    db = e2e.firestore_client()
    d = db.document(f"reference/{motion_id}").get().to_dict() or {}
    if not d.get("angles"):
        return None
    return np.asarray(d["angles"], float).reshape(int(d["anglesFrames"]), -1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--references", nargs="*", default=None, help="기준 모션 id")
    ap.add_argument("--doc", nargs="*", default=None, help="로컬 분석 doc json")
    a = ap.parse_args()

    rows = []
    for m in (a.references or []):
        ang = _from_reference(m)
        if ang is not None:
            rows.append((m, ang))
    for p in (a.doc or []):
        d = json.load(open(p))
        r = d.get("result") or d
        if r.get("angles"):
            rows.append((pathlib.Path(p).stem,
                         np.asarray(r["angles"], float).reshape(int(r["anglesFrames"]), -1)))

    if not rows:
        raise SystemExit("입력 없음 — --references 또는 --doc")

    print(f"분석 {ANALYSIS_FPS:.0f}fps 기준 · IPSF 요건 {IPSF_HOLD_SEC:.0f}초")
    print(f"{'대상':<24}{'길이s':>7}{'변화 p50':>9}"
          + "".join(f"{'≤'+str(t)+'°':>9}" for t in (1.0, 2.0, 3.0, 5.0, 8.0)))
    for name, ang in rows:
        p = profile(ang)
        cells = "".join(
            f"{p['holds'][t]['sec']:>8.2f}{'*' if p['holds'][t]['meets_ipsf_2s'] else ' '}"
            for t in (1.0, 2.0, 3.0, 5.0, 8.0)
        )
        print(f"{name:<24}{p['duration_s']:>7.1f}{p['delta_p50']:>9.2f}{cells}")
    print(f"\n* = 2초 이상. 열 제목 = '정지' 판정 임계(프레임간 평균 관절각 변화, 도).")
    print("임계는 아직 안 정했다 — 민감도만 보여준다.")


if __name__ == "__main__":
    main()


# ── 회전 불변 자세 기술자 (2026-09-14 2차 시도) ────────────────────────────
# 1차(관절각)는 실패했다: 폴 동작은 몸이 폴 둘레를 도는데, 관절각은 투영각이라
# 자세가 고정이어도 회전만으로 값이 크게 변한다. 정은지 10편에서 엄격 임계 최장
# 홀드가 0.0~1.3초였고, 임계를 풀면 6.6초 영상에서 13초 홀드가 나와 측정이 무너졌다.
#
# 물리적 탈출구: **폴 축(연직) 둘레 회전은 모든 점의 y 좌표를 보존한다.**
# 그러니 키포인트의 세로 성분만 보면 '회전'과 '자세 변화'가 갈린다.
# 몸 중심 기준 + torso 로 정규화해 평행이동·거리변화도 제거한다.

def vertical_shape(joints_xy: np.ndarray) -> np.ndarray:
    """(T,J,2) → (T,J) 회전 불변 세로 형태 기술자.

    y 는 폴 축 둘레 회전에 불변. 골반 중점을 원점으로, torso 길이로 정규화.
    """
    hip = joints_xy[:, [11, 12], :].mean(1)          # (T,2)
    sh = joints_xy[:, [5, 6], :].mean(1)
    torso = np.linalg.norm(sh - hip, axis=-1)        # (T,)
    torso = np.where(torso < 1e-6, np.nan, torso)
    return (joints_xy[:, :, 1] - hip[:, 1:2]) / torso[:, None]


def hold_profile_shape(joints_xy: np.ndarray, fps: float = ANALYSIS_FPS) -> dict:
    """세로 형태 기술자의 프레임간 변화로 홀드 구간을 잰다."""
    v = vertical_shape(joints_xy)
    delta = np.nanmean(np.abs(np.diff(v, axis=0)), axis=1)   # torso 배수/프레임
    out = {
        "frames": int(len(v)),
        "duration_s": round(len(v) / fps, 2),
        "delta_p50": round(float(np.nanpercentile(delta, 50)), 4),
        "holds": {},
    }
    for thr in (0.005, 0.010, 0.020, 0.040):
        still = delta <= thr
        best = cur = 0
        for s in still:
            cur = cur + 1 if s else 0
            best = max(best, cur)
        out["holds"][thr] = {"sec": round(best / fps, 2),
                             "meets_ipsf_2s": bool(best / fps >= IPSF_HOLD_SEC)}
    return out
