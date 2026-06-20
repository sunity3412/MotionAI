"""v2 비전 거부권의 순수 코어 (Phase 20-01, D-01/D-02/D-05 + HIGH-3).

이 모듈은 numpy 외 의존이 0 이다 — boto3/Gemini/네트워크/firestore import 절대 금지.
Gemini 호출/파이프라인 wiring 은 후속 plan(20-02 adapter / 20-03 wiring)이 별도 모듈로
맡는다. 여기서는 phase 의 가장 중요한 안전 성질만 코드로 못 박는다:

  비전은 점수를 절대 올리지 않는다 (하향 전용, D-01).

왜 min() 으로 인코딩하나: kip-up 100/100 위양성(신뢰를 깬 사고)을 구조적으로 차단하기
위해서다. 가중블렌드/하한/상향연산은 비전이 점수를 올릴 수 있어 위양성을 재발시킨다 — 그래서
거부권은 오직 terminal min() 캡이다 (dimensions.overall_from_dimensions 의 min-of-core
overall 위에 합성된다, dimensions.py:384 정합).

cap 수치 출처도 데이터로 박제한다 (SEVERITY_CAP_PROVENANCE). 6페어에 curve-fit 하는
경로를 fail-closed 로 막기 위해, sensitivity manifest 의 실 sha256 가 없는 동안 cap 을
채우면 단위테스트(test_cap_fill_requires_real_manifest_sha)가 거부한다.

---
cap 활성화 모드 (provenance.method)
---
20-04 는 cap 수치를 **spec-anchored** 로 박는다 (belle 결정 2026-06-20):

  - major = 50  — belle 스펙 "잘못된 동작 ≤50" (CLAUDE.md core value /
    [[score-spec-95-100-elite-vision-fix]]) 을 그대로 못 박는다.
  - moderate = 75 — IPSF moderate-fault 의 원칙적 상한 (severity 의미 기반).
  - minor = None — 정타 무캡 (D-01 95~100 보존, 영구 None).

이 수치들은 데이터에 curve-fit 한 것이 아니라 belle 스펙 + IPSF severity 의미에서
나온다 (provenance.method == "spec_anchored", provenance.spec_basis 가 출처를
데이터로 박제). 6 deliberate-fault 페어는 회귀 검증(known-answer gate) 전용으로만
유지되며 cap 도출 입력으로 절대 쓰이지 않는다
(phase18_pairs_used_for_derivation == False, 영구 INVARIANT).

DEFERRED (후속 단계): 미보유 sensitivity 셋(온라인 영상)에서 cap 을 도출하는
generalization-tested eval — method == "sensitivity_derived" 경로. 그 경로에서는
sensitivity_manifest_sha256 가 실 sha 여야 cap 을 채울 수 있다 (HIGH-3 fail-closed).
현재는 미구현(derive_caps.py / sensitivity.yaml / eval_manifest 없음).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SEVERITY_CAP — severity → overall 상한 (20-04 spec-anchored 활성화).
#
# 수치는 데이터 curve-fit 이 아니라 belle 스펙 + IPSF severity 의미에서 나온다
# (provenance.method == "spec_anchored", provenance.spec_basis 가 데이터 출처):
#
#   - major = 50      — belle 스펙 "잘못된 동작 ≤50" 그대로 못 박음.
#   - moderate = 75   — IPSF moderate-fault 원칙적 상한 (severity 의미 기반).
#   - minor = None    — 정타 무캡, 영구 None (D-01 95~100 보존).
#
# 6페어(정은지 단일 선수 + fault)에 curve-fit 하는 것은 절대 금지다 — 6페어는
# 회귀 검증(known-answer gate) 전용이며 cap 도출 입력이 아니다
# (D-02 / [[scoring-redesign-must-generalize-no-overfit]] / [[sensitivity-gate-not-just-elite-low]]).
#
# DEFERRED: 미보유 sensitivity 셋 derive 경로(method=="sensitivity_derived")는
# 후속 단계에서 보강한다. 그 경로에서만 sensitivity_manifest_sha256 가 실 sha 여야
# cap 을 채울 수 있다 (HIGH-3 fail-closed). spec_anchored 모드는 sha 없이 cap 가능하되
# spec_basis 데이터가 출처를 박제한다.
# ---------------------------------------------------------------------------
SEVERITY_CAP: dict[str, int | None] = {
    "minor": None,     # 정타 무캡 — 영구 None (D-01 95~100 보존)
    "moderate": 75,    # IPSF moderate-fault 원칙적 상한 (spec_anchored)
    "major": 50,       # belle 스펙 "잘못된 동작 ≤50" (spec_anchored)
}

# ---------------------------------------------------------------------------
# SEVERITY_CAP_PROVENANCE — cap 도출 출처를 주석이 아닌 **데이터**로 박제 (HIGH-3).
#
# - method: cap 활성화 모드. "spec_anchored" = belle 스펙 + IPSF severity 의미로
#   박은 값(현재). "sensitivity_derived" = 미보유 sensitivity 셋 eval 도출(후속,
#   미구현). method 별로 fail-closed 가드가 다르다 (아래 spec_basis / sha 참조).
# - source: cap 수치의 출처 라벨. spec_anchored 모드에서는 belle 스펙 + IPSF severity.
# - spec_basis: cap 수치 근거를 **데이터**로 박제 (주석 아님). belle 스펙
#   "잘못된 동작 ≤50" 을 명시 — test_provenance_is_data_not_comment 가 검사.
# - sensitivity_manifest_sha256: sensitivity_derived 경로에서만 의미. derive 가
#   sensitivity manifest 의 실 sha256 으로 채운다. spec_anchored 모드에서는 None
#   (도출 입력 아님). cap 을 sensitivity_derived 로 채우려면 실 sha 여야 한다
#   (TODO/None 금지) — test_cap_fill_requires_real_manifest_sha 가 강제 (fail-closed).
# - phase18_pairs_used_for_derivation: 영구 False (INVARIANT). 6페어는 회귀 검증
#   (known-answer gate) 전용이며 derive 입력이 아니다 — 어떤 method 도 이 값을
#   True 로 바꿀 수 없다 (6페어 curve-fit fail-closed).
# ---------------------------------------------------------------------------
SEVERITY_CAP_PROVENANCE: dict[str, object] = {
    "method": "spec_anchored",
    "source": "belle_spec_ipsf_severity",
    "spec_basis": (
        'belle spec "잘못된 동작 ≤50" '
        "(CLAUDE.md core value / score-spec-95-100-elite-vision-fix); "
        "moderate=75 from IPSF moderate-fault severity meaning"
    ),
    "sensitivity_manifest_sha256": None,
    "phase18_pairs_used_for_derivation": False,
}


def apply_downward_cap(overall: int, severity: str | None) -> int:
    """v1 overall 을 vision severity 로 **하향만** 한다 (D-01 코어 invariant).

    severity → SEVERITY_CAP lookup 후 cap 이 있으면 min(overall, cap), 없으면 불변.
    None / 미지 키 / minor → 불변 (정타 95~100 보존).

    invariant: 반환값 ≤ overall 항상. 올림 경로(상향연산/하한/가중블렌드) 절대 금지 —
    비전이 점수를 올리면 위양성(kip-up 100/100)이 재발한다.
    """
    cap = SEVERITY_CAP.get(severity)  # 미지 severity → None (불변)
    if cap is None:
        return overall
    # 하향 전용: 입력보다 cap 이 높아도 절대 올리지 않는다 (min only).
    return min(overall, cap)


def worst_pose_timestamp(profile) -> float | None:
    """지배 결함 pose 시점을 key_moments 재사용으로 고른다 (D-05).

    우선순위: hold > peak > 전체. 각 그룹에서 가장 이른(min) timestamp 를 고른다.
    IPSF phase 평균 거부 — 평균은 Phase 19 에서 고친 "결함이 정상 관절에 희석되는"
    바로 그 버그다. 단일 지배 pose 만 선택한다.

    신규 Gemini moment 호출 0 — profile.key_moments(Phase 8/11 technique profile)
    만 읽는다 (순수). key_moments None/빈/속성 부재 → None (graceful).

    timestamp 단위는 초(영상 시작점 기준). frame_extractor.py target_fps = 9.0
    이지만 본 함수는 초 단위만 다룬다 (frame 변환은 호출 측 책임).
    """
    moments = getattr(profile, "key_moments", None) or ()
    if not moments:
        return None

    def _ts(group_key: str | None) -> float | None:
        if group_key is None:
            chosen = moments
        else:
            chosen = [
                m for m in moments if getattr(m, "moment_key", None) == group_key
            ]
        timestamps = [
            float(getattr(m, "timestamp_seconds"))
            for m in chosen
            if getattr(m, "timestamp_seconds", None) is not None
        ]
        return min(timestamps) if timestamps else None

    # 명시적 None 검사 — `or` 는 timestamp 0.0(영상 시작 hold)을 falsy 로 떨어뜨려
    # hold→peak 로 잘못 폴백한다. None 만 폴백 신호로 쓴다.
    for group in ("hold", "peak", None):
        ts = _ts(group)
        if ts is not None:
            return ts
    return None
