"""피터팬 실데이터 방향 검증 — belle 08-17 판독 축 (quick-260831-bjj Task 3).

========================= 사전 박제 판정 (실행 전 박제) =========================
belle 08-17 판독 원문 (memory belle-readings-20260817-discovery, 피터팬):
  "오른팔 어깨가 딱 곧게 펴지면서 상체의 꼿꼿해짐이 전체적 영향을 미치고"
  → 기준(정은지)이 학생보다 상체가 꼿꼿하다.

예측 (frames-before-numbers 규율 — 수치를 보기 전에 박제):
  ref uprightness median < user uprightness median
  (uprightness 0° = 수직 꼿꼿, 클수록 기울어짐 — 기준이 더 꼿꼿 = 기준 median 이 작다)

이 부등식 성립 = PASS. headSpine 은 관측만 출력한다 — 피터팬 원문에 머리 축
언급이 없고, 그 축의 정답지는 elbow r02cand03 건이라 방향 단정 금지.

FAIL 시: 정의를 데이터에 맞춰 비틀지 않는다 (curve-fit 금지,
judgment-must-not-fixate-on-recent-fixture). FAIL 그대로 verdict 파일에 남기고
SUMMARY 에 "완료 판정 미달 + 관측 수치" 로 보고 — 함수·배선은 유지.
================================================================================

실행: backend venv python (시스템 python3 금지).
데이터: .planning/phases/35-server-rendered-comparison-video/data/peterpan/align.json
  refKp (129,34) / userKp (91,34) = 17관절 x xy flat, 정규화 xy (y-down),
  refScore/userScore (T,17) 신뢰도.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
_SHARED = _ROOT / "backend" / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis.features import (  # noqa: E402
    POSTURE_DELTA_SIGNIFICANT_DEG,
    head_spine_alignment_series,
    posture_axis_summary,
    torso_uprightness_series,
)
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402

_ALIGN = (
    _ROOT
    / ".planning"
    / "phases"
    / "35-server-rendered-comparison-video"
    / "data"
    / "peterpan"
    / "align.json"
)

# conf < 0.5 게이트 — 각도 미표시 원인 조사에서 박제된 keypoint 신뢰 임계 선례
# (memory angle-bake-blocked-by-confidence, side_match._CONF_MIN 과 동일 값 재사용).
_CONF_MIN = 0.5


def _load_kp(doc: dict, kp_key: str, score_key: str) -> np.ndarray:
    """(T,34) flat xy + (T,17) score → (T,17,2), score < 0.5 keypoint 는 NaN."""
    kp = np.asarray(doc[kp_key], dtype=float).reshape(-1, 17, 2)
    score = np.asarray(doc[score_key], dtype=float)
    assert score.shape == kp.shape[:2], f"{score_key} 형상 불일치: {score.shape}"
    kp = kp.copy()
    kp[score < _CONF_MIN] = np.nan
    return kp


def main() -> None:
    doc = json.loads(_ALIGN.read_text(encoding="utf-8"))
    assert list(doc["joints17"]) == list(KEYPOINT_NAMES), (
        "joints17 이 skeleton.KEYPOINT_NAMES 순서와 다름 — 재배열 필요"
    )

    ref_kp = _load_kp(doc, "refKp", "refScore")
    user_kp = _load_kp(doc, "userKp", "userScore")
    print("피터팬 align.json 자세 축 방향 검증 (quick-260831-bjj Task 3)")
    print(f"refKp {ref_kp.shape}  userKp {user_kp.shape}  conf<{_CONF_MIN} → NaN 마스킹")
    print()
    print("[사전 박제 예측] belle 원문 '상체의 꼿꼿해짐' (기준이 학생보다 꼿꼿):")
    print("  ref uprightness median < user uprightness median  이면 PASS")
    print("  headSpine 은 관측만 (피터팬 원문에 머리 축 없음 — 방향 단정 금지)")
    print()

    # 상체 꼿꼿함 — 2D 입력 (z=0 패딩은 함수 내부), y-down 기본 up 벡터.
    ref_up = torso_uprightness_series(ref_kp)
    user_up = torso_uprightness_series(user_kp)
    up_summary = posture_axis_summary(user_up, ref_up)

    # 머리-척추 1자 — 관측만.
    ref_head = head_spine_alignment_series(ref_kp)
    user_head = head_spine_alignment_series(user_kp)
    head_summary = posture_axis_summary(user_head, ref_head)

    def _stats(name: str, ref_s: np.ndarray, user_s: np.ndarray) -> None:
        rv, uv = ref_s[np.isfinite(ref_s)], user_s[np.isfinite(user_s)]
        print(
            f"  {name}: ref median {np.nanmedian(ref_s):.2f}° "
            f"(유효 {rv.size}/{ref_s.size}) / "
            f"user median {np.nanmedian(user_s):.2f}° (유효 {uv.size}/{user_s.size})"
        )

    print("[실측]")
    _stats("uprightness (0°=수직 꼿꼿)", ref_up, user_up)
    _stats("headSpine   (180°=1자)   ", ref_head, user_head)
    print()

    print("[요약 — posture_axis_summary (delta = student - reference)]")
    print(f"  uprightness: {up_summary}")
    print(f"  headSpine  : {head_summary}")
    print(f"  significant 임계 = {POSTURE_DELTA_SIGNIFICANT_DEG}°")
    print()

    ref_med = float(np.nanmedian(ref_up))
    user_med = float(np.nanmedian(user_up))
    passed = np.isfinite(ref_med) and np.isfinite(user_med) and ref_med < user_med
    print("[판정]")
    print(
        f"  예측 부등식: ref uprightness median ({ref_med:.2f}°) "
        f"< user uprightness median ({user_med:.2f}°)"
    )
    print(f"  결과: {'PASS' if passed else 'FAIL'} — "
          + ("belle 원문 방향(기준이 더 꼿꼿)과 일치"
             if passed
             else "예측 부등식 불성립 — curve-fit 금지, FAIL 그대로 박제"))
    print()
    print("[headSpine 관측] (판정 아님 — 정답지는 elbow 건)")
    if head_summary is not None:
        direction = (
            "학생이 덜 1자 (delta<0)" if head_summary["deltaDeg"] < 0
            else "학생이 더 1자 (delta>0)"
        )
        print(f"  {direction}, delta {head_summary['deltaDeg']:.2f}°")
    else:
        print("  요약 불가 (유한값 부족)")


if __name__ == "__main__":
    main()
