"""D-11 JSON 규격 + D-01 통합 리포트 v1 스키마 단일 owner (22-01 Task 1).

이 모듈이 학습 JSONL 조립(22-04)·bake-off(22-05)·서빙 파서(22-08)가 공유하는
유일한 규격 소스다. 규격을 코드 리뷰가 아니라 테스트로 고정한다 (test_schema.py).

── D-11 4철칙 (GSPO Format Compliance Reward 파싱 에러 0 목표) ──
  1. 결측 = Null(None) 바인딩 고정 — 가려짐/블러여도 키 삭제 금지, 스키마 구조 고정.
  2. 키 알파벳 오름차순 정렬 — 출력 구조 규칙성 인지로 파싱 오류 영점화.
  3. 프롬프트 상단에 대상 관절 키 리스트 1회 사전 바인딩 → 배열에는 값만 나열
     (bind_key_prompt).
  4. 태스크 무관 관절(얼굴 이목구비 68 + 손가락 42) 입력 전 사전 필터 (filter_joints).
  + 좌표는 상대좌표 ×1000 = 000~999 3자리 정수 이산화 (discretize; CogVLM 방식,
    <loc_NNN> 어휘 확장 아님 — 토크나이저 무접촉, 22-RESEARCH Pattern 2).

── D-01 통합 리포트 v1 (모델은 점수를 절대 내지 않는다) ──
  REPORT_KEYS 5출력 = coaching / corrected_coords / faults / segments / svg_spec /
  time_anchors. score/severity/overall/points 계열 필드는 영구 부재 — 짚기·측정·앵커
  까지만 하고, 감점은 Phase 24 감점 규칙 엔진(불변, [[scoring-must-be-transparent-
  deduction-tally]]). faults[] 는 deduction_engine 소비 계약(DEDUCTION_CONSUMED_KEYS)
  의 상위집합이라 swap 후 감점 엔진이 결함을 무수정 채점한다 (lockstep).

numpy 외 서드파티 의존 0, boto3/네트워크 0. fault_category 검증만 shared layer 의
vision_veto.FAULT_CATEGORIES 단일 owner 를 재사용한다 (새 분류 발명 금지).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# ── 버전 상수 (gemini_vision_scorer PROMPT_VERSION/SCHEMA_VERSION 전례) ──
# 프롬프트 조각(bind_key_prompt)·REPORT/FAULT 스키마 구조를 바꾸면 반드시 bump.
# 변경 시 날짜+이유를 상수 옆 주석에 기록해 학습 데이터 provenance 를 고정한다.
SCHEMA_VERSION = "ft-v1.0"  # ft-v1.0 (2026-07-09, 22-01): D-11+D-01 초판.
PROMPT_VERSION = "ft-v1.0"  # ft-v1.0 (2026-07-09, 22-01): 키 사전 바인딩 조각 초판.

# ── D-01 통합 리포트 v1 최상위 키 (알파벳 정렬, score 계열 부재) ──
REPORT_KEYS: tuple[str, ...] = (
    "coaching",         # 코칭 문장 (D-02 shadow 소비; 학습엔 포함).
    "corrected_coords",  # CoT 진단 기반 보정 좌표 (D-10a 자가 라벨 트랙의 출력).
    "faults",           # 결함 짚기/측정대상 (전 동작 균등) — FAULT_ITEM_KEYS 서브스키마.
    "segments",         # sub-action 구간 분할.
    "svg_spec",         # 렌더용 기하 스펙 (목표 각도·힘 방향·이상 궤적; 픽셀 생성 아님).
    "time_anchors",     # 결함 프레임/타임스탬프 시간 앵커.
)

# ── faults[] 서브스키마 (deduction_engine 계약 상위집합, 점수/severity 부재) ──
#
# gemini_vision_scorer SCHEMA v8.1 differences[] 를 미러한다 — 편차는 코드 산술이므로
# 각도쌍(student/reference_angle_deg)이 필수. 감점 엔진(deduction_engine)이 소비하는
# 키(DEDUCTION_CONSUMED_KEYS)의 상위집합이라 자체 모델 swap 후에도 무수정 채점된다.
# severity/score 는 의도적으로 부재: 모델은 짚기·측정만, 점수는 Phase 24 엔진(ND-02).
FAULT_ITEM_KEYS: tuple[str, ...] = (
    "approx_angle_deviation_deg",  # 각도쌍 불가 편차 폴백(도). 미상 0.
    "body_part",                   # 결함 부위 자유텍스트 (라우팅 입력).
    "correct_state",               # 정타 상태 서술.
    "fault_category",              # FAULT_CATEGORIES 고정 enum (라우터 1순위 소비).
    "fault_state",                 # 결함 상태 서술 (라우팅 입력).
    "ipsf_note",                   # IPSF 기준 노트.
    "measurement_basis",           # 무엇을 어떻게 쟀는지 DESCRIPTIVE 서술.
    "part_scope",                  # upper_body/core/lower_body/line.
    "reference_angle_deg",         # 기준(정타) 각도 추정(도).
    "root_cause_hypothesis",       # '~로 보임' 원인 가설 (단정·숫자 점수 금지).
    "source",                      # geometry | vision_hypothesis.
    "student_angle_deg",           # 학생(평가 대상) 각도 추정(도).
)

# ── deduction_engine 소비 계약 (lockstep 기준) ──
#
# deduction_engine 이 supported_differences 항목에서 실제로 읽는 키를 명시한다:
#   · explicit_measured_deviation_deg → student_angle_deg / reference_angle_deg
#   · _vision_measured_deviation 폴백 → approx_angle_deviation_deg
#   · criteria_for_fault / fault_key_from_difference 라우팅 → body_part / fault_state /
#     correct_state / ipsf_note / fault_category
# severity 는 소비하지 않는다 (ND-02: severity 는 비채점 라벨). 이 상수가 FAULT_ITEM_KEYS
# 의 부분집합이어야 감점 엔진이 무수정 소비 — test_schema.py 가 drift 시 FAIL 시킨다.
DEDUCTION_CONSUMED_KEYS: tuple[str, ...] = (
    "approx_angle_deviation_deg",
    "body_part",
    "correct_state",
    "fault_category",
    "fault_state",
    "ipsf_note",
    "reference_angle_deg",
    "student_angle_deg",
)

# ── svg_spec 기하 데이터 스키마 (픽셀 생성 아님 — 렌더러가 소비하는 벡터/각도) ──
SVG_SPEC_KEYS: tuple[str, ...] = (
    "force_vector",       # 교정 힘 방향 벡터 [dx, dy].
    "ideal_trajectory",   # 이상 궤적 점열.
    "target_angle_deg",   # 목표 각도(도).
)

# ── time_anchors / segments 서브스키마 (frame = 9fps canonical time key) ──
TIME_ANCHOR_KEYS: tuple[str, ...] = ("fault_category", "frame", "timestamp")
SEGMENT_KEYS: tuple[str, ...] = ("end_frame", "label", "start_frame")

# ── 태스크 무관 관절 사전 필터 프리픽스 (RTMW 133 중 얼굴 68 + 손가락 42) ──
#
# 133관절 전부 넣으면 토큰 폭발 (노트 2·7). 분석 목적과 무관한 얼굴 이목구비·손가락
# 뼈대는 입력 전 삭제한다. 프리픽스/키워드 매칭 — 몸통/사지 키만 남긴다.
TASK_IRRELEVANT_JOINTS: tuple[str, ...] = (
    "face",                                    # RTMW 얼굴 윤곽 68점.
    "left_hand", "right_hand",                 # 손 root/손가락 42점.
    "thumb", "index", "middle", "ring", "pinky", "little",  # 손가락 관절.
    "eye", "ear", "nose", "mouth", "lip", "brow", "cheek", "chin", "jaw",  # 이목구비.
)

# vision_veto.FAULT_CATEGORIES 를 shared layer 에서 재사용 (단일 owner). 무겁지 않은
# 순수 모듈이므로 import-time 에 로드하되, 경로 주입은 여기서 1회.
_BACKEND = Path(__file__).resolve().parents[2]
_SHARED = _BACKEND / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))


def valid_fault_categories() -> tuple[str, ...]:
    """FAULT_CATEGORIES 단일 owner 재사용 (새 분류 발명 금지). lazy import — shared
    layer 미주입 환경에서도 스키마 상수 접근은 가능하게 한다."""
    from sunity_shared.analysis.vision_veto import FAULT_CATEGORIES

    return tuple(FAULT_CATEGORIES)


# ---------------------------------------------------------------------------
# discretize / undiscretize — 상대좌표 ×1000 = 000~999 3자리 정수 이산화 (Pattern 2).
# ---------------------------------------------------------------------------
def discretize(xy, width: float, height: float) -> tuple[int, int]:
    """(x, y) 픽셀 좌표 → (dx, dy) 000~999 3자리 정수 그리드.

    상대 비율(x/width, y/height)을 [0,1]로 정규화 후 999 스케일 반올림 — 왕복 오차는
    그리드 1칸(1/1000) 이하. <loc_NNN> 어휘 확장이 아니라 정수 텍스트(CogVLM 방식)
    이므로 토크나이저 무접촉. width/height ≤ 0 이면 ValueError."""
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height must be > 0: {width!r},{height!r}")
    x, y = float(xy[0]), float(xy[1])
    dx = int(round(_clamp01(x / width) * 999))
    dy = int(round(_clamp01(y / height) * 999))
    return dx, dy


def undiscretize(dxy, width: float, height: float) -> tuple[float, float]:
    """(dx, dy) 3자리 정수 그리드 → (x, y) 픽셀 좌표 (discretize 역함수)."""
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height must be > 0: {width!r},{height!r}")
    dx, dy = int(dxy[0]), int(dxy[1])
    x = (dx / 999.0) * width
    y = (dy / 999.0) * height
    return x, y


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


# ---------------------------------------------------------------------------
# filter_joints — 태스크 무관 관절 사전 필터 (D-11 철칙 4).
# ---------------------------------------------------------------------------
def filter_joints(coords: dict, task_joints=None) -> dict:
    """관절 dict 에서 얼굴 이목구비·손가락(TASK_IRRELEVANT_JOINTS)을 삭제.

    task_joints 가 주어지면 그 집합에 든 관절만 남긴다(무관 관절 이중 차단). None
    이면 TASK_IRRELEVANT_JOINTS 프리픽스 매칭만으로 필터. 순수 — 입력 미변형(새 dict).
    """
    allowed = set(task_joints) if task_joints else None
    out: dict = {}
    for name, val in (coords or {}).items():
        if _is_irrelevant_joint(name):
            continue
        if allowed is not None and name not in allowed:
            continue
        out[name] = val
    return out


def _is_irrelevant_joint(name: str) -> bool:
    lname = str(name or "").lower()
    return any(marker in lname for marker in TASK_IRRELEVANT_JOINTS)


# ---------------------------------------------------------------------------
# select_frame_indices — 9fps 배열 인덱스 균등 서브샘플 (Pattern 1).
# ---------------------------------------------------------------------------
def select_frame_indices(total_frames: int, budget: int = 64) -> list[int]:
    """9fps 원 프레임 배열에서 균등 stride 서브샘플 인덱스 리스트.

    원 영상 재추출 절대 금지 — 파이프라인 9fps 프레임 배열의 인덱스로만 선택한다
    (260705-h5z 위상 불일치 실증). stride = ceil(T/budget). 반환 인덱스는 전부
    [0, total_frames) 범위이며 frame 필드의 canonical time key 로 쓰인다
    (timestamp = frame / 9.0)."""
    if total_frames <= 0:
        return []
    budget = max(1, int(budget))
    stride = max(1, math.ceil(total_frames / budget))
    return list(range(0, total_frames, stride))


# ---------------------------------------------------------------------------
# bind_key_prompt — 대상 관절 키 리스트 사전 바인딩 프롬프트 조각 (D-11 철칙 3).
# ---------------------------------------------------------------------------
def bind_key_prompt(keys) -> str:
    """대상 관절 키를 알파벳 정렬로 1회 선언하는 시스템 프롬프트 조각.

    데이터 배열에는 값만 나열하도록 유도 → 시각 추론에만 집중, 학습 효율 극대화
    (노트 2·7). 순수 문자열 빌더 (부수효과 0)."""
    sorted_keys = sorted(str(k) for k in (keys or ()))
    joined = ", ".join(sorted_keys)
    return (
        "대상 관절 키 (알파벳 오름차순, 데이터에는 값만 나열): "
        f"[{joined}]. 결측 좌표는 키 삭제 없이 Null 로 고정한다."
    )


# ---------------------------------------------------------------------------
# normalize_report — D-11 철칙 1·2 단일 owner + 화이트리스트 + enum 강제.
# ---------------------------------------------------------------------------
def normalize_report(raw: dict) -> dict:
    """모델 출력(raw) → D-01 정규 리포트.

    · 화이트리스트 REPORT_KEYS 밖 키는 통과하지 않는다 (T-22-02 tampering 방어).
    · 결측 REPORT_KEYS 는 삭제 대신 None 으로 고정 (철칙 1).
    · faults[] 항목은 FAULT_ITEM_KEYS Null 고정 + fault_category 를 FAULT_CATEGORIES
      단일 owner 로 검증(밖 값 → None; 새 분류 발명 금지).
    · 전 dict 키를 알파벳 정렬로 재방출 (철칙 2, 재귀).
    순수 — raw 미변형(새 dict 반환).

    방어(2026-07-10, 22-04 시험 배치 fix): raw 가 dict 아니면(최상위 배열 등) {} 취급 —
    전 REPORT_KEYS Null 리포트로 graceful degrade (list.get AttributeError 사망 금지).

    중첩 타입 강제(2026-07-11, 22-04 full batch fix — 구조 불변이라 SCHEMA_VERSION
    유지): 교사가 svg_spec 등 중첩 구조를 JSON-문자열/평문으로 내는 케이스 실증
    (assemble 크래시). 최상위 화이트리스트만으론 부족 — 중첩 필드도 여기 단일 지점
    에서 타입 강제한다(산탄 가드 금지):
      · svg_spec → SVG_SPEC_KEYS dict, time_anchors/segments → 항목 dict 리스트,
        corrected_coords → 리스트, coaching → str.
      · str 로 온 구조 필드는 json.loads 1회 복구 시도 — 성공+타입 일치면 채택,
        아니면 해당 필드만 None (행 폐기 아님 — 다른 라벨은 유효, graceful)."""
    raw = raw if isinstance(raw, dict) else {}
    valid_categories = _safe_valid_categories()
    out: dict = {}
    for key in REPORT_KEYS:
        val = raw.get(key)
        if key == "faults":
            val = _normalize_faults(val, valid_categories)
        elif key == "svg_spec":
            val = _normalize_keyed_dict(val, SVG_SPEC_KEYS)
        elif key == "time_anchors":
            val = _normalize_item_list(val, TIME_ANCHOR_KEYS)
        elif key == "segments":
            val = _normalize_item_list(val, SEGMENT_KEYS)
        elif key == "corrected_coords":
            val = _normalize_untyped_list(val)
        elif key == "coaching":
            val = val if isinstance(val, str) or val is None else None
        out[key] = _sort_keys(val)
    # 이미 REPORT_KEYS 순서로 넣었지만, 방어적으로 알파벳 재정렬(중첩 값은 _sort_keys 처리).
    return {k: out[k] for k in sorted(out)}


def _coerce_structured(value):
    """str 로 온 중첩 구조를 json.loads 로 1회 복구 시도 — 실패(평문)면 그대로 반환.

    호출자가 isinstance 타입 검사로 최종 None 처리한다 (필드 단위 graceful drop)."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _normalize_keyed_dict(value, keys):
    """중첩 dict 필드 → keys 화이트리스트 + Null 고정. dict 아니면(복구 후에도) None."""
    if value is None:
        return None
    value = _coerce_structured(value)
    if not isinstance(value, dict):
        return None
    return {k: value.get(k) for k in sorted(keys)}


def _normalize_item_list(value, item_keys):
    """중첩 리스트 필드 → 항목별 item_keys Null 고정. 리스트 아니면(복구 후에도) None."""
    if value is None:
        return None
    value = _coerce_structured(value)
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        item = _coerce_structured(item)
        item = item if isinstance(item, dict) else {}
        out.append({k: item.get(k) for k in sorted(item_keys)})
    return out


def _normalize_untyped_list(value):
    """자유 스키마 리스트(corrected_coords — 관절 키가 동적) → 리스트 타입만 강제."""
    if value is None:
        return None
    value = _coerce_structured(value)
    return value if isinstance(value, list) else None


def _normalize_faults(value, valid_categories):
    """faults → 항목 정규화 리스트. 리스트 아니면(복구 후에도) None.

    구 동작(str 이면 문자 단위 iteration 으로 전-Null 항목 양산)은 폐기 — 타입 불일치는
    필드 None 으로 명시한다(진단 가능, 쓰레기 항목 0)."""
    if value is None:
        return None
    value = _coerce_structured(value)
    if not isinstance(value, list):
        return None
    return [_normalize_fault_item(item, valid_categories) for item in value]


def _normalize_fault_item(item, valid_categories) -> dict:
    """faults[] 단일 항목 → FAULT_ITEM_KEYS Null 고정 + fault_category enum 검증."""
    item = item if isinstance(item, dict) else {}
    result: dict = {}
    for key in FAULT_ITEM_KEYS:
        val = item.get(key)
        if key == "fault_category" and val is not None:
            if val not in valid_categories:
                val = None  # enum 밖 값 거부 → Null (키 삭제 금지).
        result[key] = val
    return {k: result[k] for k in sorted(result)}


def _sort_keys(value):
    """dict 키를 알파벳 정렬로 재귀 재방출 (list 원소도 재귀). 스칼라는 그대로."""
    if isinstance(value, dict):
        return {k: _sort_keys(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        return [_sort_keys(v) for v in value]
    return value


def _safe_valid_categories() -> tuple[str, ...]:
    """FAULT_CATEGORIES 재사용 — shared layer 미주입 시 빈 튜플(전 category None 처리
    안 함)로 graceful. 정상 경로에서는 vision_veto enum 을 강제한다."""
    try:
        return valid_fault_categories()
    except Exception:  # noqa: BLE001 — 규격 접근은 shared layer 없이도 죽지 않는다.
        return ()
