"""등록 판정 — 공급자 기준 영상의 실패 4형 중 셋을 순수 함수로 (Phase 38 D-09 · Success ② · REQ-38-4).

왜 있나
───────
공급자(정은지)가 링크로 올린 기준 영상은 사람이 검수하지 않고 자동 등록된다(D-09). 등록이 잘못되면 그 뒤
모든 Mode 1 점수가 그 영상을 기준으로 나오므로 등록 전에 넷을 기계로 거른다 — 사람 미검출 · 여러 명 ·
서 있는 시작 없음 · 저신뢰. 원시 함수는 셋이 이미 있었고(엔진 NoHumanError · hold_height 바닥 규칙 ·
keypoint confidence) 하나는 없었다(엔진이 사람 수 N 을 버렸다 → rtmw_engine.estimate_with_person_counts,
RESEARCH Q5). 판정을 순수 함수로 두면 Pod 없이 합성 입력으로 닫힌다(38-PATTERNS 패턴 4).

어떻게 재나
──────────
- 여러 명: 프레임별 사람 수 목록(엔진 반환값) 중 N >= 2 인 프레임 비율 >= MULTI_PERSON_FRAME_RATIO. 순서 무관.
- 저신뢰: keypointReport 관절별 신뢰도 중앙값 < LOW_CONFIDENCE_MEDIAN_MIN 인 관절 목록(report joints 순서).
  문구에는 12관절 한국어 부위명(KEYPOINT_LABEL_KO, joint_labels_ko)으로 실린다.
- 서 있는 시작: 앞 n_stand 프레임(기본 = 첫 STANDING_START_DEFAULT_SEC 초, 폼 clipRange 가 있으면 호출측이
  그걸로 덮는다)을 "서 있는 창" 으로 보고 hold_height 의 바닥 규칙(창 낮은발 10% 분위가
  −hold_height.FLOOR_VIOLATION_BODY_LENGTH 아래면 위반)을 `hold_height.floor_reference_valid` 로 판정한다 —
  상수·통계 복제 0.

판정 순서와 그 이유 (리뷰 R6, 2026-09-26)
────────────────────────────────────────
`no_human`(엔진 예외, 호출측) → `low_confidence`(측정 불가) → `multiple_people` → `no_standing_start`(측정 결과 위반).
측정 불가를 측정 결과 위반보다 먼저 — `hold_height.MIN_CONF`(0.35) 미만 발목은 `_frame_series` 가 바닥을 못 구해
None 을 돌려주므로, 옛 순서(여러 명 → 서 있는 시작 → 저신뢰)로는 발목 0.2 영상이 `no_standing_start` 로
오분류됐다(리뷰 로컬 재현 [확인]). 그래서 "측정 불가" 는 두 갈래로 잡는다: 관절 중앙값 < 문턱
(`low_confidence_joints`) **또는** 서 있는 창의 바닥 재료(발목·어깨)가 MIN_CONF 미만(`standing_start_measurable`).

서 있는 시작 = 바닥 일관성 규칙의 PROXY (한계)
────────────────────────────────────────────
바닥 규칙은 "어깨~발목 세로 길이 양수 + 창에서 발이 바닥 아래로 안 내려감" 만 본다. 웅크린 채 시작한
합성 좌표도 통과한다(리뷰 R6 재현 — test_floor_rule_is_a_proxy_crouch_passes). 자세 분류기가 아니다.
실영상 오분류율 [미확인]. 이 phase 는 분류기를 더하지 않고 가이드 ④ 문구("서 있는 자세인지는 사람이
확인해 주세요", D-16)로 한계를 남긴다. 시험 영상 2차로 실측한다.

입력 계약 (plan-checker 차단 1, 2026-09-28)
──────────────────────────────────────────
`report` = keypointReport **dict**(camelCase — 38-07 이 `_dataclass_to_camel_case_dict(build_keypoint_report(...))`
로 만든다, `test_hold_height._report` 형상: joints / frames / data / confidence). 비Mapping(`KeypointReport` frozen
dataclass 인스턴스 · None)은 `TypeError`(fail-loud) — `hold_height._arrays` 는 비Mapping 에 None 을 돌려 조용히
fail-closed 가 되므로, 배선 실수가 `no_standing_start` 로 위장되지 않게 그 **앞에서** 막는다. 형상 불량 Mapping 은
기존 fail-closed 그대로(T-38-05-1): ok=False · reason `no_standing_start` · detail `no_floor_reference`.
`person_counts` = `rtmw_engine.estimate_with_person_counts` 가 돌려주는 프레임별 사람 수(1차 추론 기준).

fail-closed
───────────
못 재면 통과시키지 않는다 — 바닥을 못 세우면 `no_standing_start`, 신뢰도 중앙값이 NaN 인 관절은 저신뢰.
`low_confidence` 는 항상 부위 목록이 1개 이상이다(38-03 페이지가 "잘 안 보인 부위: {joints}" 를 그대로 찍는다).

채점 무접촉: 산출은 등록 상태·실패 문구·로그에만 쓰인다. `dimensions` · `assemble.build_mode1` · `_process` 에 닿지 않는다.
Pod · DB · 스토리지 SDK import 0 — numpy · stdlib · hold_height · keypoint_frame · skeleton · models 만.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from . import hold_height
from .keypoint_frame import _KEYPOINT_NAMES
from .skeleton import JOINT_LABEL_KO
from ..models import REG_ERR_LOW_CONFIDENCE, REG_ERR_MULTIPLE_PEOPLE, REG_ERR_NO_STANDING_START

# ── 문턱 3개 — RESEARCH A5~A7 [ASSUMED]. 상수 하나씩 두고 시험 영상 2차(sealed_test)로만 조정. 목표 숫자 금지. ──

# [ASSUMED RESEARCH A6] 여러 명 = N>=2 프레임 비율 >= 이 값(경계 포함). 지나가는 사람(짧게)은 통과, 두 사람이
# 계속 있으면 실패. 시험 영상 2차로만 조정, 목표 숫자 금지.
MULTI_PERSON_FRAME_RATIO = 0.30

# [ASSUMED RESEARCH A5] 서 있는 구간 기본 = 영상 첫 1.0초(폼 clipRange.execStartS 가 있으면 호출측이 그 값으로 덮는다).
# 시험 영상 2차로만 조정, 목표 숫자 금지.
STANDING_START_DEFAULT_SEC = 1.0

# [ASSUMED RESEARCH A7] 저신뢰 = 관절별 신뢰도 중앙값 < 이 값(표시 게이트 conf 0.5 와 같은 값).
# 메모리 conf-05-gate: "표시 게이트 conf 0.5 는 아무것도 안 가른다 — 문턱 바로 위아래 품질이 같다(5.06 vs 6.23도),
# 의미는 0.6 위부터". 그래서 잠정값이고 시험 영상 2차로만 조정, 목표 숫자 금지.
# hold_height.MIN_CONF(0.35, 측정 신뢰 하한)보다 낮추면 "측정 불가를 먼저" 순서가 무너진다(test 가 잠근다).
LOW_CONFIDENCE_MEDIAN_MIN = 0.5

# 서 있는 창의 바닥·몸길이 재료 — hold_height._frame_series :109-121 이 바닥(발목 y 중앙값)·몸길이(발목−어깨)에 쓰는
# 관절. 이 넷 중 하나라도 서 있는 창에서 MIN_CONF 미만이면 바닥을 못 세우므로 "측정 불가" 다.
_FLOOR_JOINTS = ("left_ankle", "right_ankle", "left_shoulder", "right_shoulder")

# 12관절 한국어 부위명 — skeleton.JOINT_LABEL_KO 8개는 그 값 그대로(문자열 복사 0) + 손목·발목 4개.
# `left_hand`/`right_hand` 는 COCO-17 wrist 매핑(keypoint_frame :57-59)이라 "손목" 으로 부른다.
_EXTRA_LABEL_KO = {
    "left_hand": "왼쪽 손목",
    "right_hand": "오른쪽 손목",
    "left_ankle": "왼쪽 발목",
    "right_ankle": "오른쪽 발목",
}
KEYPOINT_LABEL_KO: dict[str, str] = {
    name: (JOINT_LABEL_KO[name] if name in JOINT_LABEL_KO else _EXTRA_LABEL_KO[name])
    for name in _KEYPOINT_NAMES
}

# no_standing_start 의 detail 토큰 — 38-07 은 reason 만 문구에 쓰고 detail 은 로그에 남긴다.
DETAIL_STAND_WINDOW_TOO_SHORT = "stand_window_too_short"   # n_stand < hold_height.MIN_STAND_FRAMES
DETAIL_NO_FLOOR_REFERENCE = "no_floor_reference"           # 바닥·몸길이를 못 세움(형상 이상 · 창 부족 · 몸길이 <= 0 · 재료 NaN)
DETAIL_FLOOR_VIOLATION = "floor_violation"                 # 창 낮은발 10% 분위가 바닥 아래(hold_height 문턱)


@dataclass(frozen=True)
class RegistrationVerdict:
    """등록 판정 — ok 면 reason None. reason 은 models.REG_ERR_* 그대로(38-07 이 REGISTRATION_ERROR_MESSAGE 키로 쓴다).

    joints = low_confidence 일 때 부위명(영문 키, report joints 순서, 1개 이상) — 문구는 joint_labels_ko 로.
    detail = 로그용 관측(사람 수 비율 · 저신뢰 갈래 · no_standing_start 토큰). 문구에 쓰지 않는다.
    """

    ok: bool
    reason: str | None = None
    joints: tuple[str, ...] = ()
    detail: str = ""


def _require_mapping(report) -> Mapping:
    """report 는 keypointReport dict — 비Mapping 은 TypeError(fail-loud, plan-checker 차단 1).

    hold_height._arrays 는 비Mapping 에 None 을 돌려 조용히 fail-closed 가 된다(카드 문장 소비처와 공유하므로
    손대지 않는다). 등록 판정은 그 앞에서 막아 배선 실수(dataclass 를 그대로 넘김)가 no_standing_start 로
    위장되지 않고 테스트에서 드러나게 한다.
    """
    if not isinstance(report, Mapping):
        raise TypeError(
            "keypoint report must be a Mapping (dict): pass "
            "_dataclass_to_camel_case_dict(build_keypoint_report(...)), "
            f"not the KeypointReport dataclass (got {type(report).__name__})"
        )
    return report


def default_stand_frames(fps, sec: float = STANDING_START_DEFAULT_SEC) -> int:
    """서 있는 구간 기본 프레임 수 = round(fps × sec). fps 를 못 믿으면(None · 0 이하 · 비유한) 0.

    0 이면 check_registration 이 stand_window_too_short 로 fail-closed 한다. 폼 clipRange 가 있으면 호출측(38-07)이
    이 값 대신 round(execStartS × fps) 를 넘긴다.
    """
    try:
        f = float(fps)
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(f) or f <= 0.0:
        return 0
    return int(round(f * sec))


def multiple_people_ratio(person_counts: Iterable[int]) -> float:
    """N>=2 인 프레임 수 / 전체 프레임 수. 빈 목록 0.0. 순서를 읽지 않는다. 0(미검출 프레임)은 N>=2 가 아니다."""
    counts = [int(n) for n in person_counts]
    if not counts:
        return 0.0
    return sum(1 for n in counts if n >= 2) / len(counts)


def is_multiple_people(person_counts: Iterable[int], ratio: float = MULTI_PERSON_FRAME_RATIO) -> bool:
    """여러 명 = 비율 >= ratio(경계 포함: 3/10 = 0.30 은 실패, 리뷰 R15b). 순서 무관."""
    return multiple_people_ratio(person_counts) >= ratio


def low_confidence_joints(report: Mapping, min_conf: float = LOW_CONFIDENCE_MEDIAN_MIN) -> list[str]:
    """관절별 신뢰도 중앙값 < min_conf 인 관절 이름 — report joints 순서. 중앙값이 NaN 이면 저신뢰(fail-closed).

    hold_height._arrays 재사용. 형상 불량 dict 는 [] — 부위를 댈 수 없으니 여기서 판정하지 않는다
    (check_registration 이 서 있는 시작 쪽에서 fail-closed 한다).
    """
    _require_mapping(report)
    arr = hold_height._arrays(report)
    if arr is None:
        return []
    _X, C, idx = arr
    out: list[str] = []
    for name, j in idx.items():   # idx 는 joints 순서(enumerate) — dict 삽입 순서가 곧 report 순서
        med = hold_height._nanmedian(C[:, j])
        if not (math.isfinite(med) and med >= min_conf):
            out.append(name)
    return out


def standing_start_measurable(report: Mapping, n_stand: int) -> tuple[bool, list[str]]:
    """서 있는 창(앞 n_stand 프레임)에서 바닥·몸길이 재료(_FLOOR_JOINTS)의 신뢰도 중앙값이 hold_height.MIN_CONF 이상인가.

    (True, []) = 측정 가능. (False, [관절…]) = 측정 불가 — 목록은 report joints 순서(관절별로 따로 본다: 한쪽 발목만
    안 읽혀도 그 발목이 오른다). 창이 MIN_STAND_FRAMES 미만이면 신뢰도 문제가 아니라 창 문제라 (True, [])
    (check_registration 이 no_standing_start/stand_window_too_short 로 보낸다). 형상 불량 dict 도 (True, []) —
    저신뢰가 아니다(부위를 댈 수 없다).
    """
    _require_mapping(report)
    n = int(n_stand)
    if n < hold_height.MIN_STAND_FRAMES:
        return True, []
    arr = hold_height._arrays(report)
    if arr is None:
        return True, []
    _X, C, idx = arr
    w0 = min(n, C.shape[0])
    unreadable: list[str] = []
    for name, j in idx.items():
        if name not in _FLOOR_JOINTS:
            continue
        med = hold_height._nanmedian(C[:w0, j])
        if not (math.isfinite(med) and med >= hold_height.MIN_CONF):
            unreadable.append(name)
    return (not unreadable), unreadable


def _standing_start_detail(report: Mapping, n_stand: int) -> str | None:
    """서 있는 시작 판정 → None(통과) 또는 no_standing_start 의 detail 토큰. 못 재면 통과가 아니다(fail-closed)."""
    n = int(n_stand)
    if n < hold_height.MIN_STAND_FRAMES:
        return DETAIL_STAND_WINDOW_TOO_SHORT
    arr = hold_height._arrays(report)
    if arr is None:
        return DETAIL_NO_FLOOR_REFERENCE
    T = arr[0].shape[0]
    valid = hold_height.floor_reference_valid(report, (n, T))
    if valid is None:
        return DETAIL_NO_FLOOR_REFERENCE
    return None if valid else DETAIL_FLOOR_VIOLATION


def standing_start_ok(report: Mapping, n_stand: int) -> bool:
    """서 있는 시작 = `hold_height.floor_reference_valid(report, (n_stand, T))` 가 True 일 때만 True.

    None(못 잼) · False(위반) 둘 다 False — fail-closed. 문턱은 hold_height.FLOOR_VIOLATION_BODY_LENGTH 하나
    (여기 복제 없음). PROXY 한계는 모듈 docstring — 웅크린 시작도 통과한다.
    """
    _require_mapping(report)
    return _standing_start_detail(report, n_stand) is None


def joint_labels_ko(names: Iterable[str]) -> list[str]:
    """영문 관절 키 → 한국어 부위명(KEYPOINT_LABEL_KO). 모르는 키는 그대로 둔다(문장을 못 만들어 등록을 죽이지 않는다)."""
    return [KEYPOINT_LABEL_KO.get(n, n) for n in names]


def check_registration(person_counts: Iterable[int], report: Mapping, *, n_stand: int) -> RegistrationVerdict:
    """등록 판정 — 순서 ① low_confidence ② multiple_people ③ no_standing_start ④ ok (리뷰 R6).

    `no_human` 은 여기서 판정하지 않는다 — 엔진 `NoHumanError`(rtmw_engine.estimate_with_person_counts) 를 호출측(38-07)이
    `models.REG_ERR_NO_HUMAN` 으로 매핑한다(전 프레임 미검출은 report 자체가 없다).
    ① 관절 중앙값 < 문턱 **또는** 서 있는 창의 바닥 재료 < MIN_CONF → joints = 두 목록 합집합(report 순서, 1개 이상).
    ② N>=2 프레임 비율 >= MULTI_PERSON_FRAME_RATIO.
    ③ 바닥 규칙 위반 또는 못 잼 → detail 토큰(stand_window_too_short · no_floor_reference · floor_violation).
    """
    _require_mapping(report)
    low = low_confidence_joints(report)
    measurable, unreadable = standing_start_measurable(report, n_stand)
    if low or not measurable:
        flagged = set(low) | set(unreadable)
        joints = tuple(n for n in (report.get("joints") or []) if n in flagged)
        detail = (
            f"median_below_{LOW_CONFIDENCE_MEDIAN_MIN:g}={','.join(low) or '-'};"
            f"stand_material_below_{hold_height.MIN_CONF:g}={','.join(unreadable) or '-'}"
        )
        return RegistrationVerdict(ok=False, reason=REG_ERR_LOW_CONFIDENCE, joints=joints, detail=detail)
    counts = [int(n) for n in person_counts]
    if is_multiple_people(counts):
        return RegistrationVerdict(
            ok=False, reason=REG_ERR_MULTIPLE_PEOPLE, detail=f"person_ratio={multiple_people_ratio(counts):.3f}",
        )
    stand_detail = _standing_start_detail(report, n_stand)
    if stand_detail is not None:
        return RegistrationVerdict(ok=False, reason=REG_ERR_NO_STANDING_START, detail=stand_detail)
    return RegistrationVerdict(ok=True)
