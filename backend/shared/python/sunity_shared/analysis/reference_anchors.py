"""기준(reference) 각도 앵커 주석 로더 — **display 전용, 채점 무접촉 (D-44)**.

33-G §C-1 (quick-260730-l7t) — 승인 목업 7R `mockups/index.html` 780-814행
"A-5(33-12) 구현 지시"(4R 확정)의 데이터 계층:

    "기준 라이브러리는 11개 동작으로 고정(phase4_v1 pinned)이라, 기준 쪽 각도 앵커
     (어깨·팔꿈치·엉덩이 방향점)는 **기준 모션당 1회 수동 주석**으로 달아 앵커
     데이터로 저장하면 끝 — A-5 는 이 저장된 앵커를 읽어 그리기만 하면 돼요."

**왜 정적 좌표가 아니라 "관절 대입 선언"인가 (L-5):**
정적 좌표는 주석한 그 프레임에서만 유효하다. 그런데 기준 패널의 표시 프레임은
DTW 실측 순간(S11)이라 **학생마다 다르다** — 주석 프레임과 표시 프레임이 어긋나면
좌표가 몸 밖에 뜬다(6R 기각 사유와 같은 실패 모드). 그래서 저장하는 것은 좌표가
아니라 "이 criterion 에서 기준 report 에 없는 관절 X 는 관절 Y(또는 Y·Z 중점)로
대입해도 유효하다"는 **판정 1회**다. 대입 선언은 실 keypoint 를 따라가므로 어느
프레임에서도 유효하고, 환각 드로잉이 원리적으로 0이다 (좌표를 데이터로 받지
않으므로 임의 픽셀 지시 경로 자체가 없음 — T-l7t-01).

계약:
  · 파일 = `backend/judging_data/reference_anchors/{motion_id}.yaml`.
  · 순수 모듈 — boto3/네트워크/채점 모듈 import 0.
  · **모든 실패 경로는 예외 없이 빈 값.** fault_zoom 은 분석 흐름을 막지 않는
    부가물이라(fault_zoom 모듈 docstring) 주석 결손이 분석을 깨뜨려서는 안 된다.
  · 결과는 프로세스 캐시 1회 로드 — reference 는 pinned(phase4_v1)라 런타임 변동 0.
  · 미주석 모션은 **fail-closed**: `{}` → 호출측(fault_zoom)이 그 카드의 각도를
    그리지 않는다(L-6/L-7). 조용한 누락이 아니라 README 에 잔여 목록이 박제된다.

스키마 (README.md 와 lockstep):

    motion: ref-power-spin          # 필수, 파일명과 일치해야 함 (오배치 차단)
    annotated: "2026-07-30"         # 주석 날짜
    source: "무엇을 열어 확인했는지"  # 사람이 본 근거
    criteria:
      angle_vs_reference__left_shoulder:
        joint_substitutions:
          left_elbow: left_hand                     # 단일 관절 대입
          # 또는  left_elbow: {midpoint: [a, b]}    # 두 관절 중점 대입
        note: "근거 — 필수 (근거 없는 주석 금지)"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .keypoint_frame import _KEYPOINT_NAMES

log = logging.getLogger(__name__)

# 기본 데이터 디렉터리 — judging/loader.py DEFAULT_CRITERIA_DIR 관례 정합.
#   __file__ = backend/shared/python/sunity_shared/analysis/reference_anchors.py
#   parents[0] = analysis/ · [1] = sunity_shared/ · [2] = python/ · [3] = shared/
#   parents[4] = backend/
DEFAULT_ANCHOR_DIR: Path = (
    Path(__file__).resolve().parents[4] / "judging_data" / "reference_anchors"
)

# 허용 관절명 — keypoint_frame 이름공간 단일 출처 (오타 방어, T-l7t-01).
_ALLOWED_JOINTS: frozenset[str] = frozenset(_KEYPOINT_NAMES)

# 프로세스 캐시 (motion_id → 정규화된 criteria dict). base_dir override 는
# 캐시하지 않는다 — 테스트 fixture 주입 경로이므로 매번 읽는다.
_CACHE: dict[str, dict[str, dict]] = {}


def _read_yaml(path: Path) -> dict[str, Any] | None:
    """safe_load. 실패는 전부 None (예외 밖으로 새지 않음)."""
    try:
        import yaml  # noqa: PLC0415 - 로더 지연 import (judging/loader.py 선례)
    except ImportError:
        log.warning("reference_anchors: PyYAML 미설치 — 앵커 주석 비활성")
        return None
    try:
        with path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
    except Exception:  # noqa: BLE001 - 주석 결손이 분석을 막지 않는다
        log.warning("reference_anchors: yaml 파싱 실패 path=%s", path)
        return None
    return data if isinstance(data, dict) else None


def _normalize_declaration(decl: Any) -> str | dict[str, list[str]] | None:
    """대입 선언 정규화 — 관절명 str 또는 {'midpoint': [a, b]}. 위반 → None."""
    if isinstance(decl, str):
        return decl if decl in _ALLOWED_JOINTS else None
    if isinstance(decl, dict):
        mid = decl.get("midpoint")
        if (
            isinstance(mid, list)
            and len(mid) == 2
            and all(isinstance(m, str) and m in _ALLOWED_JOINTS for m in mid)
        ):
            return {"midpoint": [str(mid[0]), str(mid[1])]}
    return None


def _normalize_entry(motion_id: str, crit: str, raw: Any) -> dict | None:
    """criterion 항목 정규화. 스키마 위반은 **그 항목만 드롭** + 경고 로그."""
    if not isinstance(raw, dict):
        log.warning(
            "reference_anchors: 항목 드롭(비-dict) motion=%s criterion=%s",
            motion_id, crit,
        )
        return None
    note = raw.get("note")
    if not isinstance(note, str) or not note.strip():
        log.warning(
            "reference_anchors: 항목 드롭(note 부재 — 근거 없는 주석 금지) "
            "motion=%s criterion=%s",
            motion_id, crit,
        )
        return None
    subs_raw = raw.get("joint_substitutions")
    if not isinstance(subs_raw, dict) or not subs_raw:
        log.warning(
            "reference_anchors: 항목 드롭(joint_substitutions 부재/비-dict) "
            "motion=%s criterion=%s",
            motion_id, crit,
        )
        return None
    subs: dict[str, str | dict[str, list[str]]] = {}
    for absent, decl in subs_raw.items():
        if not isinstance(absent, str) or absent not in _ALLOWED_JOINTS:
            log.warning(
                "reference_anchors: 대입 대상 관절명 미등재 — 드롭 "
                "motion=%s criterion=%s joint=%r",
                motion_id, crit, absent,
            )
            continue
        norm = _normalize_declaration(decl)
        if norm is None:
            log.warning(
                "reference_anchors: 대입 선언 위반 — 드롭 "
                "motion=%s criterion=%s joint=%s decl=%r",
                motion_id, crit, absent, decl,
            )
            continue
        subs[absent] = norm
    if not subs:
        log.warning(
            "reference_anchors: 항목 드롭(유효 대입 0) motion=%s criterion=%s",
            motion_id, crit,
        )
        return None
    return {"joint_substitutions": subs, "note": note}


def load_reference_anchors(
    motion_id: str, base_dir: Path | None = None
) -> dict[str, dict]:
    """`{motion_id}.yaml` → {criterion id: {'joint_substitutions', 'note'}}.

    미주석/미존재/스키마 위반 = `{}` (예외 0, fail-closed). 위반 항목만 드롭하고
    나머지는 유지한다 — 한 줄 오타가 그 모션 전체 주석을 죽이지 않게.
    `motion` 필드가 파일명과 다르면 **전체 드롭** (오배치 주석이 다른 모션의 기하로
    유입되는 경로 차단, T-l7t-01).
    """
    if not isinstance(motion_id, str) or not motion_id:
        return {}
    use_cache = base_dir is None
    if use_cache and motion_id in _CACHE:
        return _CACHE[motion_id]

    directory = base_dir if base_dir is not None else DEFAULT_ANCHOR_DIR
    result: dict[str, dict] = {}
    try:
        path = directory / f"{motion_id}.yaml"
        if path.exists():
            data = _read_yaml(path)
            if data is not None:
                declared = data.get("motion")
                if declared != motion_id:
                    log.warning(
                        "reference_anchors: motion 필드 불일치 — 전체 드롭 "
                        "path=%s declared=%r expected=%s",
                        path, declared, motion_id,
                    )
                else:
                    block = data.get("criteria")
                    if isinstance(block, dict):
                        for crit, raw in block.items():
                            if not isinstance(crit, str) or not crit:
                                continue
                            entry = _normalize_entry(motion_id, crit, raw)
                            if entry is not None:
                                result[crit] = entry
                    elif block is not None:
                        log.warning(
                            "reference_anchors: criteria 블록이 dict 아님 — 전체 드롭 "
                            "path=%s",
                            path,
                        )
    except Exception:  # noqa: BLE001 - 어떤 실패도 분석 흐름을 막지 않는다
        log.warning("reference_anchors: 로드 실패 motion=%s", motion_id)
        result = {}

    if use_cache:
        _CACHE[motion_id] = result
    return result


def resolve_anchor_joint_xy(
    report: dict,
    frame_idx: int,
    joint: str,
    decl: Any,
    *,
    gated_kp=None,
) -> tuple[float, float] | None:
    """관절 `joint` 의 정규화 좌표 — report 직접 보유 우선, 부재 시 대입 선언 경유.

    · report 가 joint 를 신뢰 좌표로 보유 → 그 좌표 (**대입은 부재 관절 전용**).
    · 선언이 단일 관절명 → 그 관절의 신뢰 좌표.
    · 선언이 {'midpoint': [a, b]} → 두 관절 신뢰 좌표의 중점.
    · 소스 관절 중 하나라도 confidence 게이트 미달/결측 → None (추정 좌표로
      선을 긋지 않는다 — T-l7t-05).

    `gated_kp` = confidence 게이트 통과 좌표 조회자. 기본값은 fault_zoom._gated_kp
    를 **호출 시점 지연 import** 한다 — fault_zoom 이 본 모듈을 모듈 레벨로 import
    하므로(단방향) 여기서 모듈 레벨 import 를 하면 순환이 된다. 게이트 공식은
    한 벌만 두어야 하므로(중복 금지) 복제하지 않고 지연 import 로 재사용한다.
    """
    if gated_kp is None:
        from .fault_zoom import _gated_kp as gated_kp  # noqa: PLC0415

    direct = gated_kp(report, frame_idx, joint)
    if direct is not None:
        return direct

    norm = _normalize_declaration(decl)
    if norm is None:
        return None
    if isinstance(norm, str):
        return gated_kp(report, frame_idx, norm)
    a = gated_kp(report, frame_idx, norm["midpoint"][0])
    b = gated_kp(report, frame_idx, norm["midpoint"][1])
    if a is None or b is None:
        return None
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


__all__ = [
    "DEFAULT_ANCHOR_DIR",
    "load_reference_anchors",
    "resolve_anchor_joint_xy",
]
