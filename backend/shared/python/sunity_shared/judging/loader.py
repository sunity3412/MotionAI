"""IPSF GeometricCriterion YAML 로더 (Plan 01-15 JUDGE-DATA-01).

YAML 스키마 (belle 라벨링):

    motion: ref-invert
    source: "IPSF Code of Points 2024 — invert family"
    criteria:
      setup_moment: []
      hold_moment:
        - joint: left_knee
          angle_target: 180.0
          tolerance_full: 20.0
          deduction_per_step: 0.2
          minimum_requirement: 130.0
          source_ref: "IPSF Code of Points 2024 §4.2.1 invert family knee extension"
        # ...
      peak_moment: []
      release_moment: []

규칙:
  · 4 phase 키 = setup_moment / hold_moment / peak_moment / release_moment 로 고정.
    내부적으로 moment_key 는 trailing "_moment" 제거 후 'setup' / 'hold' / 'peak' / 'release'.
  · 각 entry 의 누락 필드는 ValueError 로 즉시 차단 (객관 임계값 누락 = baseline 위반).
  · validate() 실패 entry 는 motion / moment_key / joint_key 를 메시지에 명시.
  · YAML 파싱 의존성 = PyYAML (pyyaml). backend/requirements-dev.txt 에 추가됨.
    Lambda 런타임에는 미사용 (현재 sunity_shared.judging 은 채점 데이터 스키마 전용).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .geometric_criterion import VALID_MOMENT_KEYS, GeometricCriterion

# 기본 데이터 디렉터리. backend/judging_data/criteria/{motion}.yaml.
# parents[5] 경로 도출:
#   __file__ = backend/shared/python/sunity_shared/judging/loader.py
#   parents[0] = judging/
#   parents[1] = sunity_shared/
#   parents[2] = python/
#   parents[3] = shared/
#   parents[4] = backend/
DEFAULT_CRITERIA_DIR: Path = (
    Path(__file__).resolve().parents[4] / "judging_data" / "criteria"
)

# YAML 키 ↔ moment_key 매핑.
_YAML_PHASE_KEYS = {
    "setup_moment": "setup",
    "hold_moment": "hold",
    "peak_moment": "peak",
    "release_moment": "release",
}


def _resolve_base_dir(base_dir: Path | None) -> Path:
    return base_dir if base_dir is not None else DEFAULT_CRITERIA_DIR


def _resolve_yaml_path(motion: str, base_dir: Path | None) -> Path:
    return _resolve_base_dir(base_dir) / f"{motion}.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    """PyYAML safe_load. import 실패 시 명확한 메시지로 ImportError."""
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PyYAML 미설치 — backend/requirements-dev.txt 에 'pyyaml>=6' 추가 후 "
            "`pip install -r backend/requirements-dev.txt` 실행. "
            "(Plan 01-15 judging YAML 로더 의존성)"
        ) from exc

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
    except yaml.YAMLError as exc:  # type: ignore[attr-defined]
        raise ValueError(
            f"YAML 파싱 실패 ({path}): {exc}. 해당 파일의 들여쓰기/quote 를 확인하세요."
        ) from exc

    if data is None:
        # 완전 빈 파일은 빈 dict 로 취급 (belle 라벨링 전 상태 허용).
        return {}
    if not isinstance(data, dict):
        raise ValueError(
            f"YAML 최상위가 dict 가 아닙니다 ({path}). 'motion'/'source'/'criteria' 구조 확인."
        )
    return data


def _entry_to_criterion(
    motion: str,
    moment_key: str,
    entry: Any,
    path: Path,
) -> GeometricCriterion:
    """단일 YAML entry → GeometricCriterion + validate(). 어디서 실패했는지 명시."""
    if not isinstance(entry, dict):
        raise ValueError(
            f"YAML criteria entry 가 dict 가 아닙니다 ({path}): "
            f"motion={motion} moment={moment_key} entry={entry!r}"
        )

    required = {
        "joint",
        "angle_target",
        "tolerance_full",
        "deduction_per_step",
        "minimum_requirement",
        "source_ref",
    }
    missing = required - entry.keys()
    if missing:
        raise ValueError(
            f"YAML criteria entry 필수 키 누락 ({path}): "
            f"motion={motion} moment={moment_key} 누락={sorted(missing)}"
        )

    try:
        criterion = GeometricCriterion(
            motion=motion,
            moment_key=moment_key,
            joint_key=str(entry["joint"]),
            angle_target=float(entry["angle_target"]),
            tolerance_full=float(entry["tolerance_full"]),
            deduction_per_step=float(entry["deduction_per_step"]),
            minimum_requirement=float(entry["minimum_requirement"]),
            source_ref=str(entry["source_ref"]),
        )
    except (TypeError, ValueError) as exc:
        # float() 변환 실패 등 — 어느 entry 인지 메시지에 박제.
        raise ValueError(
            f"YAML criteria entry 타입 변환 실패 ({path}): "
            f"motion={motion} moment={moment_key} joint={entry.get('joint')!r}: {exc}"
        ) from exc

    try:
        criterion.validate()
    except ValueError as exc:
        # validate() 메시지에 이미 motion/moment/joint 포함되지만 path 도 추가.
        raise ValueError(
            f"GeometricCriterion 검증 실패 ({path}): {exc}"
        ) from exc

    return criterion


def load_criteria(
    motion: str,
    base_dir: Path | None = None,
) -> list[GeometricCriterion]:
    """{motion}.yaml 로드 후 모든 phase entry 를 평탄화하여 list 반환.

    Args:
      motion: 기준 동작 ID (예: 'ref-invert'). 파일명 매핑 = base_dir/{motion}.yaml.
      base_dir: 데이터 디렉터리 override (기본 = backend/judging_data/criteria/).
                테스트 fixture 주입용.

    Returns:
      validate() 통과한 GeometricCriterion list. 빈 템플릿이면 [] 반환.

    Raises:
      FileNotFoundError: YAML 파일 미존재. 메시지에 belle 라벨링 안내.
      ValueError: YAML 파싱 / 스키마 / validate() 실패. 어느 entry 인지 명시.
      ImportError: PyYAML 미설치.
    """
    path = _resolve_yaml_path(motion, base_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"GeometricCriterion YAML 미존재: {path}. "
            f"backend/judging_data/criteria/{motion}.yaml 을 belle 라벨링으로 채워주세요 "
            f"(Plan 01-15 T-5 참조)."
        )

    data = _read_yaml(path)
    criteria_block = data.get("criteria", {}) if data else {}
    if not isinstance(criteria_block, dict):
        raise ValueError(
            f"YAML 'criteria' 블록이 dict 가 아닙니다 ({path}): "
            f"phase 키 (setup_moment / hold_moment / peak_moment / release_moment) 4개 dict 형태 필요."
        )

    results: list[GeometricCriterion] = []
    for yaml_phase_key, moment_key in _YAML_PHASE_KEYS.items():
        entries = criteria_block.get(yaml_phase_key, [])
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise ValueError(
                f"YAML '{yaml_phase_key}' 가 list 가 아닙니다 ({path}): "
                f"moment={moment_key} 형식은 entry list 여야 합니다."
            )
        for entry in entries:
            results.append(_entry_to_criterion(motion, moment_key, entry, path))

    # moment_key 가 VALID_MOMENT_KEYS 와 일치하는지 sanity check (방어).
    for c in results:
        if c.moment_key not in VALID_MOMENT_KEYS:  # pragma: no cover
            raise ValueError(
                f"내부 정합성 오류: moment_key={c.moment_key} ∉ {VALID_MOMENT_KEYS} ({path})."
            )

    return results


def load_grouped_criteria(
    motion: str,
    base_dir: Path | None = None,
) -> dict[str, list[GeometricCriterion]]:
    """load_criteria 결과를 moment_key 별로 그룹화한 dict 반환.

    Plan 01-13 Gemini key moment 추출 시 시점 → criteria lookup 편의용.
    빈 phase 도 빈 list 로 채워 4개 키 모두 존재함을 보장.
    """
    flat = load_criteria(motion, base_dir=base_dir)
    grouped: dict[str, list[GeometricCriterion]] = {k: [] for k in VALID_MOMENT_KEYS}
    for c in flat:
        grouped[c.moment_key].append(c)
    return grouped
