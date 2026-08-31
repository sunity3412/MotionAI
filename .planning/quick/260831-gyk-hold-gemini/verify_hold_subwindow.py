"""quick-260831-gyk Task 2 — 파워스핀 correct/fault 실데이터 재현 (Pod 불필요).

Firestore 에 저장된 angles (평탄 저장) 를 (T, J) 로 재구성해, 수리 전 의미
(힌트 창 verbatim 평균)와 수리 후 (`dimensions._select_window` 힌트-창-내부
안정 부창) 를 양쪽 영상에 대해 실측한다. 예측 부등식은 VERIFY.md 예측 블록에
스크립트 실행 전 박제됨 — 본 스크립트는 그 부등식을 assert 로 재검한다.

읽기 전용: Firestore get 만 사용 (set/update 호출 0 — T-gyk-02).
출력: 가명 uid/analysisId 만 (이미 .planning 에 박제된 식별자 — T-gyk-01).
SA 키는 경로만 참조, 내용 미출력.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

import numpy as np  # noqa: E402

import firebase_admin  # noqa: E402
from firebase_admin import credentials, firestore  # noqa: E402

from sunity_shared.analysis import dimensions, technique  # noqa: E402
from sunity_shared.analysis.gemini_technique_recognizer import (  # noqa: E402
    _hold_window_from_moments,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

SA_PATH = REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"

DOCS = {
    "correct": ("QAN8VPwk4Oh13FMhTenphxYPdxH2", "0bc7aedf1032474280d544a3a2ad418e"),
    "fault": ("8fPsUnXWNiOW9Y6cawCMcHGVb6z1", "0e53101beff4433e90159334554ba893"),
}
# 오케스트레이터 역산 확정치 — doc 에서 hold moments 도출 불가 시 correct 전용 폴백.
CORRECT_FALLBACK_WINDOW = (54, 90)
_TOL_DEG = 20.0  # dimensions._LINE_TOL_DEG 와 동일 의미 (leg_extension tol)
_MICRO_BENT_DEG = 160.0  # dimensions._SPLIT_FAIL_THRESHOLD_DEG (micro-bent 문턱)
_RK = JOINT_KEYS.index("right_knee")
_LK = JOINT_KEYS.index("left_knee")


def _client():
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(str(SA_PATH)))
    return firestore.client(app)


def _reshape_angles(doc: dict) -> np.ndarray:
    """평탄 angles + anglesJointKeys + anglesFrames → (T, J).

    firestore_admin.complete_analysis 저장 규약 + pipeline._reshape_prev_angles
    idiom (row-major, 열 = anglesJointKeys 순서) 재사용. 열 순서가 JOINT_KEYS 와
    다르면 재정렬.
    """
    flat = doc.get("angles")
    keys = list(doc.get("anglesJointKeys") or [])
    if not flat or not keys:
        raise SystemExit("doc 에 angles/anglesJointKeys 없음 — 재현 불가")
    arr = np.asarray(flat, dtype=float)
    if arr.size % len(keys) != 0:
        raise SystemExit(f"angles 길이 {arr.size} 가 J={len(keys)} 로 나눠지지 않음")
    arr = arr.reshape(-1, len(keys))
    frames = doc.get("anglesFrames")
    if frames is not None and int(frames) != arr.shape[0]:
        raise SystemExit(f"anglesFrames={frames} != 재구성 T={arr.shape[0]}")
    if keys != list(JOINT_KEYS):
        arr = arr[:, [keys.index(k) for k in JOINT_KEYS]]
    return arr


def _find_hint_window(doc: dict) -> tuple[str, tuple[int, int] | None]:
    """doc 의 gemini 캐시 필드들에서 hold moments → _hold_window_from_moments.

    도출 불가 시 (None 반환) 호출부가 폴백 규칙 적용 (VERIFY.md 예측 블록 규칙).
    """
    candidates: list[tuple[str, list]] = []
    for key in ("geminiA", "geminiB", "geminiC", "geminiD", "technique"):
        v = doc.get(key)
        if isinstance(v, dict) and isinstance(v.get("moments"), list):
            candidates.append((key + ".moments", v["moments"]))
    if isinstance(doc.get("moments"), list):
        candidates.append(("moments", doc["moments"]))
    for src, moments in candidates:
        win = _hold_window_from_moments(moments)
        if win is not None:
            return src, win
    return "(도출 불가)", None


def _knee_profile(hold_window: tuple[int, int] | None) -> technique.TechniqueProfile:
    """무릎만 EXTEND — 파워스핀 leg_extension 감점 경로와 동일한 무릎 채점 기질."""
    exp = {
        k: technique.JOINT_EXTEND if k.endswith("knee") else technique.JOINT_BENT_OK
        for k in JOINT_KEYS
    }
    return technique.TechniqueProfile(
        name="verify", category="unknown", joint_expectations=exp,
        hold_window=hold_window,
    )


def _leg_extension_measured_value(doc: dict) -> float | None:
    """doc result.deductionBreakdown.records 에서 leg_extension 의 measuredValue."""
    records = ((doc.get("result") or {}).get("deductionBreakdown") or {}).get("records")
    if not isinstance(records, list):
        return None
    for r in records:
        if not isinstance(r, dict):
            continue
        crit = str(r.get("criterionId") or r.get("criterion") or r.get("id") or "")
        if "leg_extension" in crit:
            mv = r.get("measuredValue")
            return float(mv) if mv is not None else None
    return None


def main() -> None:
    db = _client()
    results: dict[str, dict] = {}
    for label, (uid, aid) in DOCS.items():
        snap = db.document(f"users/{uid}/analyses/{aid}").get()
        if not snap.exists:
            raise SystemExit(f"{label}: doc 없음 — users/{uid}/analyses/{aid}")
        doc = snap.to_dict()
        a = _reshape_angles(doc)
        hint_src, hint = _find_hint_window(doc)
        fallback_used = False
        if hint is None and label == "correct":
            hint = CORRECT_FALLBACK_WINDOW
            hint_src = "역산 확정치 (54,90) — doc 에서 도출 불가"
            fallback_used = True
        print(f"== {label} ({uid[:8]}.../{aid[:8]}...) ==")
        print(f"  T={a.shape[0]} frames, J={a.shape[1]}")
        print(f"  힌트 창 소스: {hint_src} → {hint}")

        entry: dict = {"T": a.shape[0], "hint": hint, "fallback": fallback_used}

        if hint is not None:
            t = a.shape[0]
            s = max(0, min(int(hint[0]), t))
            e = max(s, min(int(hint[1]), t))
            verbatim_rk = float(np.nanmean(a[s:e, _RK])) if e > s else float("nan")
            print(f"  [수리 전 의미] 힌트 창 ({s},{e}) verbatim right_knee 평균 = {verbatim_rk:.2f} deg")
            entry["verbatim_rk"] = verbatim_rk
            mv = _leg_extension_measured_value(doc)
            entry["record_measured_value"] = mv
            if mv is not None:
                print(f"  doc leg_extension record measuredValue = {mv:.2f} deg")
            else:
                print("  doc 에 leg_extension 감점 record 없음")

        profile = _knee_profile(hint)
        sliced, (ws, we) = dimensions._select_window(a, profile)
        rk_mean = float(np.nanmean(sliced[:, _RK]))
        lk_mean = float(np.nanmean(sliced[:, _LK]))
        dev = dimensions.extension_deviation(a, profile)
        leg_deficit = float(max(dev[_LK], dev[_RK]))
        line = dimensions.line_score(a, profile)
        micro_bent = line == 0
        window_kind = "힌트-창-내부 부창" if hint is not None else "자동 hold_window (힌트 없음)"
        print(f"  [수리 후] {window_kind} = ({ws},{we})")
        print(f"    right_knee 평균 = {rk_mean:.2f} deg / left_knee 평균 = {lk_mean:.2f} deg")
        print(f"    leg_extension deficit (무릎 max) = {leg_deficit:.2f} deg (tol {_TOL_DEG:.0f})")
        print(f"    line_score = {line} / micro-bent(<{_MICRO_BENT_DEG:.0f}) 발화 = {micro_bent}")
        entry.update(
            subwindow=(ws, we), rk_mean=rk_mean, lk_mean=lk_mean,
            leg_deficit=leg_deficit, line_score=line, micro_bent=micro_bent,
        )
        results[label] = entry
        print()

    c, f = results["correct"], results["fault"]

    print("== 예측 부등식 판정 (VERIFY.md 예측 블록 순서) ==")

    # 예측 1 — 기질 동일성: verbatim 평균 == 감점 record measuredValue (± 0.01).
    mv = c.get("record_measured_value")
    vb = c.get("verbatim_rk")
    if mv is not None and vb is not None:
        print(f"  [1] 기질 동일성: verbatim {vb:.2f} vs record {mv:.2f} (|diff|={abs(vb - mv):.4f})")
        assert abs(vb - mv) < 0.01, "verbatim 평균이 감점 record measuredValue 와 불일치"
    elif vb is not None:
        print(f"  [1] 기질 동일성: record 부재 — 진단 박제치 135.81 과 대조 (verbatim {vb:.2f})")
        assert abs(vb - 135.81) < 0.1, "verbatim 평균이 진단 박제치 135.81 과 불일치"
    else:
        raise AssertionError("correct 힌트 창 부재 — 기질 동일성 검증 불가")
    print("      PASS")

    # 예측 2 — 부창 이동 관측 (홀드 구간 약 68 이후) — 관측 출력 (위에서 인쇄됨).
    print(f"  [2] 부창 이동: 힌트 {c['hint']} → 부창 {c['subwindow']} (관측)")

    # 예측 3 — 위양성 소멸 (hard).
    print(f"  [3] correct: rk_mean {c['rk_mean']:.2f} >= 170 / deficit {c['leg_deficit']:.2f} < {_TOL_DEG:.0f} / micro-bent {c['micro_bent']}")
    assert c["rk_mean"] >= 170.0, "부창 right_knee 평균 < 170 — 위양성 잔존"
    assert c["leg_deficit"] < _TOL_DEG, "leg_extension deficit >= tol — 감점 잔존"
    assert not c["micro_bent"], "line micro-bent 발화 — line 0점 잔존"
    print("      PASS")

    # 예측 4 — 방향 보존 (hard).
    print(f"  [4] 방향 보존: fault rk_mean {f['rk_mean']:.2f} < correct rk_mean {c['rk_mean']:.2f}")
    assert f["rk_mean"] < c["rk_mean"], "fault 홀드 무릎 평균이 correct 이상 — 방향 역전"
    print("      PASS")

    print()
    print("ALL PREDICTIONS PASS")


if __name__ == "__main__":
    main()
