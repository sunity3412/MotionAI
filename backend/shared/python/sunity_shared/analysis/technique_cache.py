"""TechniqueCache — 영상 hash 기반 Gemini 결과 캡싱 layer.

Plan 5-02 (2026-06-04). D-14 박제 — 같은 영상 재분석 시 Gemini 호출 0.
belle 시연 + Plan 5-05 sweep 재실행 비용/지연 0 효과.

박제 정신 (05-CONTEXT.md / 05-02-PLAN.md must_haves):
  · D-14: 영상 hash 캡싱 (SHA256 권장, S3 ETag fallback). hand-roll 금지.
  · D-16: lazy import (firebase-admin / boto3). 모듈 로드 시점 0 import.
  · [[firestore-nested-array-flat]]: KeyMoment list = flat dict array 박제.
    moments[i] 안 list/tuple value 거부 (TypeError) — Firestore crash 보호.
  · Open Question 4 (RESEARCH.md): yaml_version 박제 → yaml 갱신 시 자동
    stale invalidation. yaml = Plan 5-00 박제 정은지 reference 측정값 source.
  · B4 fix (2026-06-04 plan-checker iter 1+2 박제):
    - compute_yaml_version 절대 경로 박제 (Path(__file__).resolve().parents[4]).
      상대 경로 = CWD 의존 (Pod uvicorn cwd 와 Lambda cwd 다름) → yaml 발견 실패 시
      무성 빈 hash → cache 영구 stale-stable → D-14 invalidation 무효화.
    - strict=True default: FileNotFoundError 시 raise (무성 누락 처리 0).
    - strict=False: log.warning + sentinel string "yaml-missing-cache-disabled".
    - truncation 제거: 64자 full hex 박제.

소비처:
  · Plan 5-01 GeminiTechniqueRecognizer 어댑터 cache 인자 의존성 주입.
  · Plan 5-03 pipeline swap 의 Gemini 호출 직전 lookup + 호출 후 store.

박제 의존:
  · firestore_admin.get_gemini_cache / store_gemini_cache (Plan 5-02 Task 2 박제).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


# ─────────────────── 영상 hash (D-14) ───────────────────


def compute_video_hash(video_path: str | Path, *, chunk_size: int = 8192) -> str:
    """영상 SHA256 (stdlib hashlib) — belle 시연 + sweep 재실행 캡싱 key.

    streaming chunk 박제 — 100MB 영상도 메모리 spike 0.

    S3 ETag fallback (multipart upload 시 non-hex 우려) 박제: Pod 가 영상 다운로드
    후 SHA256 가 가장 안전 + 영상 정합 검증 효과 추가. ETag 박제는 별 plan 책임.

    Raises:
      FileNotFoundError: video_path 없음 — 무성 빈 hash 박제 금지 (D-14 정합).
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video path missing: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────── yaml_version (Open Question 4 + B4 fix) ───────────────────

# B4 fix (2026-06-04 plan-checker iter 1+2 박제): 절대 경로 박제.
#
# 박제 path 계산: 본 파일 = backend/shared/python/sunity_shared/analysis/technique_cache.py.
#   parents[0] = analysis/
#   parents[1] = sunity_shared/
#   parents[2] = python/
#   parents[3] = shared/
#   parents[4] = backend/
# → parents[4] / "judging_data" / "criteria" = backend/judging_data/criteria/.
#
# 박제 사유 (B4 fix):
#   상대 경로 = CWD 의존 → Pod uvicorn cwd 와 Lambda cwd 다름. yaml 발견 실패 시
#   무성 빈 hash → cache 영구 stale-stable → D-14 invalidation 무효화. 절대 경로
#   + 명시 raise 가 D-14 박제 정합. strict=True 가 default — 호출자가 명시적으로
#   strict=False 선택 시에만 sentinel 반환 (cache disable path).

_YAML_CRITERIA_DIR = (
    Path(__file__).resolve().parents[4] / "judging_data" / "criteria"
)

# Plan 5-00 박제 yaml 5개 (정은지 reference 측정값 source — 분기 2 path).
# 추가/삭제 시 본 tuple 갱신 + 단위 테스트 정합 박제.
_YAML_FILENAMES = (
    "ref-climb.yaml",
    "ref-foxtop.yaml",
    "ref-foxtop-split.yaml",
    "ref-invert.yaml",
    "ref-sideway-spin.yaml",
)

_YAML_MISSING_SENTINEL = "yaml-missing-cache-disabled"


def compute_yaml_version(*, strict: bool = True) -> str:
    """yaml 5개 (criteria/*.yaml) SHA256 합쳐 박제 → cache yaml_version key.

    Plan 5-00 박제 yaml 갱신 시 자동 변경 → cache invalidation (Open Question 4).

    Args:
      strict: True (default) 시 yaml 누락 → FileNotFoundError raise. False 시
        log.warning + sentinel "yaml-missing-cache-disabled" 반환 (cache disable).

    Returns:
      64자 hex string (B4 fix: truncation 제거) — 또는 sentinel (strict=False + 누락).

    Raises:
      FileNotFoundError: strict=True (default) + yaml 1개 이상 누락. 무성 누락
        처리 0 박제 (B4 fix — cache invalidation 정합 보호).
    """
    h = hashlib.sha256()
    missing: list[str] = []
    for filename in _YAML_FILENAMES:
        yaml_path = _YAML_CRITERIA_DIR / filename
        if not yaml_path.exists():
            if strict:
                raise FileNotFoundError(
                    "yaml criteria missing (B4 fix: cache invalidation 정합 보호 위해 "
                    f"strict raise): {yaml_path}"
                )
            missing.append(filename)
            continue
        with yaml_path.open("rb") as fp:
            h.update(fp.read())

    if missing:
        log.warning(
            "compute_yaml_version: yaml %d개 누락 (strict=False, cache disabled): %s",
            len(missing),
            missing,
        )
        return _YAML_MISSING_SENTINEL

    return h.hexdigest()  # full 64 chars (B4 fix: truncation 제거)


# ─────────────────── TechniqueCache 2단 layer ───────────────────


def _validate_flat_moments(payload: dict) -> None:
    """[[firestore-nested-array-flat]] 정합 검증.

    moments list 안 entry 가 flat dict 인지 + 각 value 가 scalar 인지 검사.
    nested list / tuple → TypeError (Firestore crash 보호 + 1차 차단선).
    """
    if "moments" not in payload or not payload["moments"]:
        return
    for i, m in enumerate(payload["moments"]):
        if not isinstance(m, dict):
            raise TypeError(
                f"moments[{i}] must be flat dict (firestore-nested-array-flat 박제): "
                f"got {type(m).__name__}"
            )
        for k, v in m.items():
            if isinstance(v, (list, tuple)):
                raise TypeError(
                    f"moments[{i}][{k}] must be scalar "
                    f"(firestore nested array 금지): got {type(v).__name__}"
                )


@dataclass
class TechniqueCache:
    """Firestore gemini_cache/{hash} 컬렉션 + in-memory layer 2단 박제.

    in-memory layer = Pod 단일 분석 내 중복 호출 흡수 (인스턴스 휘발).
    Firestore layer = Pod 재기동 / belle 시연 / sweep 재실행 영구 캡싱 (전역 공유).

    Cache key tuple = (video_hash, model_name, yaml_version).
      · video_hash: SHA256 (D-14 박제 영상 정합)
      · model_name: D-13 박제 모델 식별자 (default gemini-3.1-pro)
      · yaml_version: Plan 5-00 yaml 5개 SHA256 (Open Question 4 박제 invalidation)

    호출 path (Plan 5-01 어댑터):
      cache.lookup(video_path) → hit dict 또는 None
      cache.store(video_path, gemini_result) → in-memory + Firestore 박제

    의존 박제:
      sunity_shared.firestore_admin.get_gemini_cache / store_gemini_cache
      (Plan 5-02 Task 2 박제 helper — lazy import).
    """

    model_name: str = "gemini-3.1-pro"  # D-13 박제 — STATE.md "Phase 5 권장 모델"
    yaml_version: str = field(default_factory=compute_yaml_version)
    _memory: dict[str, dict] = field(default_factory=dict, init=False, repr=False)

    # ── lookup ──────────────────────────────────────────────

    def lookup(self, video_path: str | Path) -> dict | None:
        """video_path → hash → cache lookup (in-memory → Firestore).

        반환 dict schema (D-14 + Open Question 4 박제):
          {
            "motion": "ref-foxtop",
            "moments": [{"moment_key": "hold", "timestamp_seconds": 5.5,
                         "frame_index": 49, "confidence": 0.88}, ...],
            "joint_expectations": {"left_shoulder": "extend", ...},
            "model": "gemini-3.1-pro",
            "yaml_version": "abc123...",
            "video_hash": "...",
          }

        Returns:
          dict (hit) 또는 None (miss / 영상 없음 / Firestore 오류 / yaml/model mismatch).
        """
        # 영상 없음 graceful (분석 흐름 박제 보호)
        try:
            video_hash = compute_video_hash(video_path)
        except FileNotFoundError:
            log.warning("video path 없음 — cache lookup skip: %s", video_path)
            return None

        mem_key = self._mem_key(video_hash)

        # Step 1: in-memory hit (Pod 안 중복 흡수)
        if mem_key in self._memory:
            log.debug("TechniqueCache in-memory hit: %s", video_hash[:8])
            return dict(self._memory[mem_key])

        # Step 2: Firestore lookup (lazy import — D-16)
        try:
            from sunity_shared import firestore_admin

            doc = firestore_admin.get_gemini_cache(video_hash)
        except Exception as exc:  # noqa: BLE001 — Firestore 오류 graceful skip
            log.warning("Firestore gemini_cache lookup 실패: %s", exc)
            return None

        if doc is None:
            return None

        # yaml_version + model 정합 검증 (Open Question 4 박제 invalidation)
        if doc.get("yaml_version") != self.yaml_version:
            log.info(
                "cache yaml_version mismatch (stale) — invalidate: %s vs %s",
                doc.get("yaml_version"),
                self.yaml_version,
            )
            return None
        if doc.get("model") != self.model_name:
            log.info(
                "cache model mismatch — invalidate: %s vs %s",
                doc.get("model"),
                self.model_name,
            )
            return None

        # in-memory 갱신 (다음 lookup Firestore 미호출 박제)
        self._memory[mem_key] = dict(doc)
        log.info("TechniqueCache Firestore hit: %s", video_hash[:8])
        return dict(doc)

    # ── store ───────────────────────────────────────────────

    def store(self, video_path: str | Path, gemini_result: dict) -> None:
        """video_path → hash → in-memory + Firestore 박제.

        gemini_result 박제 시 yaml_version / model_name / video_hash 자동 추가.
        [[firestore-nested-array-flat]] 정합 검증 — nested list/tuple → TypeError.

        Raises:
          TypeError: moments entry 가 flat dict 아님 또는 value 가 list/tuple
            (firestore-nested-array-flat 박제 1차 차단선).
        """
        # nested-array 사전 검증 ([[firestore-nested-array-flat]])
        _validate_flat_moments(gemini_result)

        # 영상 없음 graceful (silent skip — 분석 진행 박제 보호)
        try:
            video_hash = compute_video_hash(video_path)
        except FileNotFoundError:
            log.warning("video path 없음 — cache store skip: %s", video_path)
            return

        doc = dict(gemini_result)
        doc["yaml_version"] = self.yaml_version
        doc["model"] = self.model_name
        doc["video_hash"] = video_hash

        # in-memory 박제 (Pod 안 중복 흡수)
        self._memory[self._mem_key(video_hash)] = dict(doc)

        # Firestore 박제 (lazy import — D-16). 실패 시 in-memory 만 유효.
        try:
            from sunity_shared import firestore_admin

            firestore_admin.store_gemini_cache(video_hash, doc)
        except Exception as exc:  # noqa: BLE001 — Firestore 오류 graceful
            log.warning(
                "Firestore gemini_cache store 실패 (in-memory 만 유효): %s", exc
            )

    # ── helpers ─────────────────────────────────────────────

    def _mem_key(self, video_hash: str) -> str:
        """in-memory cache key = (hash, model, yaml_version) tuple 직렬화."""
        return f"{video_hash}:{self.model_name}:{self.yaml_version}"
