"""등록 진단 — 공급자 기준 영상의 품질 지표 셋을 순수 함수로 (Phase 38 D-09 · REQ-38-4 · quick-261001-thx).

2026-10-01 belle 결정 — 진단만, 등록을 막지 않는다
──────────────────────────────────────────────────
38-14 대역 등록이 화분(multiple_people) · 대각선 출발(no_standing_start)로 연달아 거절됐다. belle 원문:
*"사실상 영상 분석이나 이런거에 아무런 지장없는 것들을 계쏙 이렇게 거부하는게 문제인건데 ... 내가 대각선
이야기하니까 그거 고친다고 하고 이렇게 하나씩 고치면 절대 안돼"*. 그래서 등록을 막는 것은 **분석 불가만**
남긴다 — 사람 없음(엔진 NoHumanError) · 포즈 재료 없음 · 파일 문제(파이프라인 `_register_reference` 소유).
이 모듈은 저신뢰 · 서 있는 시작 · 여러 명을 **한 번에** 진단으로 내린다: `diagnose_registration` 은 실패 사유
필드가 없는 `RegistrationDiagnostics` 를 돌려줄 뿐이고, 세 실패 코드를 내는 코드 경로 자체가 없다(테스트가
ast 로 잠근다). 진단은 Pod 로그 key=value 와 비공개 `reference/{refId}/private/registration` 의
`registrationDiagnostics` 에 남고, 공개는 사람 검수(review → approve) 뒤다.
이력: 2026-09-26~10-01 은 `check_registration` 이 low_confidence → no_standing_start 순서로 fail-closed 판정을
냈다(리뷰 R6, 측정 불가를 측정 결과 위반보다 먼저). 그 두 갈래는 진단 필드 둘(`low_confidence_joints` ·
`stand_material_unreadable`)로 그대로 남는다.

어떻게 재나 (문턱 숫자 무변경)
──────────────────────────
- 여러 명: 프레임별 사람 수 목록(엔진 반환값) 중 N >= 2 인 프레임 비율. 순서 무관. 정적 물체(화분)도 사람으로
  센다 — legacy 11개 원비율 0.23~0.57(38-14 오케스트레이터 Pod 실측).
- 저신뢰: keypointReport 관절별 신뢰도 중앙값 < LOW_CONFIDENCE_MEDIAN_MIN 인 관절 목록(report joints 순서).
- 서 있는 창 재료: 앞 n_stand 프레임에서 바닥·몸길이 재료(발목·어깨) 신뢰도 중앙값 < hold_height.MIN_CONF.
- 서 있는 시작: 앞 n_stand 프레임(기본 = 첫 STANDING_START_DEFAULT_SEC 초, 폼 clipRange 가 있으면 호출측이
  그걸로 덮는다)을 "서 있는 창" 으로 보고 hold_height 의 바닥 규칙(`hold_height.floor_reference_valid`)으로
  토큰 하나 — ok · floor_violation · no_floor_reference · stand_window_too_short. 상수·통계 복제 0.

서 있는 시작 = 바닥 일관성 규칙의 PROXY (한계)
────────────────────────────────────────────
바닥 규칙은 "어깨~발목 세로 길이 양수 + 창에서 발이 바닥 아래로 안 내려감" 만 본다. 웅크린 채 시작한
합성 좌표도 ok 다(리뷰 R6 재현 — test_floor_rule_is_a_proxy_crouch_passes). 자세 분류기가 아니다.
실영상 오분류율 [미확인].

입력 계약 (plan-checker 차단 1, 2026-09-28)
──────────────────────────────────────────
`report` = keypointReport **dict**(camelCase — 38-07 이 `_dataclass_to_camel_case_dict(build_keypoint_report(...))`
로 만든다, `test_hold_height._report` 형상: joints / frames / data / confidence). 비Mapping(`KeypointReport` frozen
dataclass 인스턴스 · None)은 `TypeError`(fail-loud) — `hold_height._arrays` 는 비Mapping 에 None 을 돌려 조용히
no_floor_reference 가 되므로, 배선 실수가 진단 값으로 위장되지 않게 그 **앞에서** 막는다. 형상 불량 Mapping 은
예외 없이 진단(standing_start = no_floor_reference, 저신뢰 목록 빈 값).
`person_counts` = `rtmw_engine.estimate_with_person_counts` 가 돌려주는 프레임별 사람 수(1차 추론 기준).

채점 무접촉: 산출은 로그와 비공개 진단 필드에만 쓰인다. `dimensions` · `assemble.build_mode1` · `_process` 에 닿지 않는다.
Pod · DB · 스토리지 SDK import 0 — numpy · stdlib · hold_height · keypoint_frame · skeleton 만.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from . import hold_height
from .keypoint_frame import _KEYPOINT_NAMES
from .skeleton import JOINT_LABEL_KO

# ── 문턱 3개 — RESEARCH A5~A7 [ASSUMED]. 상수 하나씩 두고 시험 영상 2차(sealed_test)로만 조정. 목표 숫자 금지. ──
# 2026-10-01 부터 셋 다 진단 값을 만드는 데만 쓴다 — 어느 것도 등록을 막지 않는다(모듈 docstring).

# [ASSUMED RESEARCH A6] 여러 명 = N>=2 프레임 비율 >= 이 값(경계 포함). 등록 판정에 쓰지 않는다
# (화분 오검출, legacy 11개 중 9개가 넘음). is_multiple_people 의 기본값으로만 남는다.
MULTI_PERSON_FRAME_RATIO = 0.30

# [ASSUMED RESEARCH A5] 서 있는 구간 기본 = 영상 첫 1.0초(폼 clipRange.execStartS 가 있으면 호출측이 그 값으로 덮는다).
# 시험 영상 2차로만 조정, 목표 숫자 금지.
STANDING_START_DEFAULT_SEC = 1.0

# [ASSUMED RESEARCH A7] 저신뢰 = 관절별 신뢰도 중앙값 < 이 값(표시 게이트 conf 0.5 와 같은 값).
# 메모리 conf-05-gate: "표시 게이트 conf 0.5 는 아무것도 안 가른다 — 문턱 바로 위아래 품질이 같다(5.06 vs 6.23도),
# 의미는 0.6 위부터". 그래서 잠정값이고 시험 영상 2차로만 조정, 목표 숫자 금지.
# hold_height.MIN_CONF(0.35, 측정 신뢰 하한)보다 낮추면 두 저신뢰 진단의 뜻이 뒤집힌다(test 가 잠근다).
LOW_CONFIDENCE_MEDIAN_MIN = 0.5

# 서 있는 창의 바닥·몸길이 재료 — hold_height._frame_series :109-121 이 바닥(발목 y 중앙값)·몸길이(발목−어깨)에 쓰는
# 관절. 이 넷 중 하나라도 서 있는 창에서 MIN_CONF 미만이면 바닥을 못 세운다(진단 stand_material_unreadable).
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

# 서 있는 시작 진단 토큰 — 로그 `standing_start=` 와 비공개 진단 `standingStart` 값.
STANDING_START_OK = "ok"
DETAIL_STAND_WINDOW_TOO_SHORT = "stand_window_too_short"   # n_stand < hold_height.MIN_STAND_FRAMES
DETAIL_NO_FLOOR_REFERENCE = "no_floor_reference"           # 바닥·몸길이를 못 세움(형상 이상 · 창 부족 · 몸길이 <= 0 · 재료 NaN)
DETAIL_FLOOR_VIOLATION = "floor_violation"                 # 창 낮은발 10% 분위가 바닥 아래(hold_height 문턱)


@dataclass(frozen=True)
class RegistrationDiagnostics:
    """등록 진단 — 실패 필드 없음(belle 2026-10-01). 값은 기존 원시 함수 결과 그대로.

    person_ratio = multiple_people_ratio(person_counts) · low_confidence_joints = low_confidence_joints(report)
    (report 순서) · stand_material_unreadable = standing_start_measurable(report, n_stand)[1] · standing_start =
    STANDING_START_OK 또는 DETAIL_* 토큰 · n_stand = 서 있는 창 프레임 수. 관절 이름은 영문 키(로그·운영 CLI 용).
    """

    person_ratio: float
    low_confidence_joints: tuple[str, ...]
    stand_material_unreadable: tuple[str, ...]
    standing_start: str
    n_stand: int

    def as_log_fields(self) -> str:
        """Pod 로그 key=value 한 줄 조각 — 빈 목록은 '-'."""
        return (
            f"person_ratio={self.person_ratio:.3f} "
            f"low_conf={','.join(self.low_confidence_joints) or '-'} "
            f"stand_unreadable={','.join(self.stand_material_unreadable) or '-'} "
            f"standing_start={self.standing_start} "
            f"n_stand={self.n_stand}"
        )

    def as_firestore_dict(self) -> dict:
        """비공개 doc `registrationDiagnostics` — camelCase 평면 dict(리스트는 문자열 리스트, 중첩 배열 아님)."""
        return {
            "personRatio": float(self.person_ratio),
            "lowConfidenceJoints": list(self.low_confidence_joints),
            "standMaterialUnreadable": list(self.stand_material_unreadable),
            "standingStart": self.standing_start,
            "nStand": int(self.n_stand),
        }


def _require_mapping(report) -> Mapping:
    """report 는 keypointReport dict — 비Mapping 은 TypeError(fail-loud, plan-checker 차단 1).

    hold_height._arrays 는 비Mapping 에 None 을 돌려 조용히 fail-closed 가 된다(카드 문장 소비처와 공유하므로
    손대지 않는다). 등록 진단은 그 앞에서 막아 배선 실수(dataclass 를 그대로 넘김)가 no_floor_reference 진단으로
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

    0 이면 diagnose_registration 이 stand_window_too_short 로 진단한다. 폼 clipRange 가 있으면 호출측(38-07)이
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

    hold_height._arrays 재사용. 형상 불량 dict 는 [] — 부위를 댈 수 없다(서 있는 시작 진단이
    no_floor_reference 로 남는다).
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
    (서 있는 시작 진단이 stand_window_too_short 로 남긴다). 형상 불량 dict 도 (True, []) —
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
    """서 있는 시작 → None(바닥 규칙 통과) 또는 DETAIL_* 토큰. 못 재면 통과가 아니다(no_floor_reference)."""
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
    """영문 관절 키 → 한국어 부위명(KEYPOINT_LABEL_KO). 모르는 키는 그대로 둔다."""
    return [KEYPOINT_LABEL_KO.get(n, n) for n in names]


def diagnose_registration(
    person_counts: Iterable[int], report: Mapping, *, n_stand: int
) -> RegistrationDiagnostics:
    """등록 진단 — 세 지표를 동시에 계산해 돌려준다. 실패 사유를 내지 않는다(belle 2026-10-01).

    `no_human` · 포즈 재료 없음 · 파일 문제는 호출측(`pipeline._register_reference`)이 이 함수 **전에** 막는다.
    비Mapping report 만 TypeError(배선 실수 fail-loud) — 그 밖의 어떤 dict · 사람 수 조합도 예외 없이 진단이 나온다.
    """
    _require_mapping(report)
    low = tuple(low_confidence_joints(report))
    _measurable, unreadable = standing_start_measurable(report, n_stand)
    detail = _standing_start_detail(report, n_stand)
    return RegistrationDiagnostics(
        person_ratio=float(multiple_people_ratio(person_counts)),
        low_confidence_joints=low,
        stand_material_unreadable=tuple(unreadable),
        standing_start=detail if detail is not None else STANDING_START_OK,
        n_stand=int(n_stand),
    )
