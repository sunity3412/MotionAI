"""Phase 17 Plan 06B Task 2 — Smart sampling 가중치 (AI-SPEC §7).

박제 정신:
  · AI-SPEC §7 Smart Sampling 표 7 rule 박제 — signal 기반 가중치 (isReference /
    guardrail / score 양극단 / causes 최소 / 영역 C flag / branch_3_auto / baseline).
  · Production 4-day rolling sample 으로 E5 PASS rate 측정 입력. 실제 escalation
    자체는 runtime config (Firestore visionConfig.regionC.model) 책임.
  · randomness 는 `_random` indirection 박제 — 테스트가 monkeypatch.

Sampling rules (priority order):
  1. isReference=True → 100% (weight 1.0, reason="reference_100").
  2. guardrail_triggered 박힘 → 100% (weight 1.0, reason="guardrail_100").
  3. score < 30 or score > 95 → 20% (reason="score_extreme_20").
  4. geminiB.causes len ≤ 3 (최소값 — generic 의심) → 30% (reason="causes_min_30").
  5. geminiC.occlusion_severe OR camera_angle_problematic → 15% (reason="flag_true_15").
  6. geminiA.routing_branch == "branch_3_auto" → 100% (reason="branch3_100").
  7. else → 2% baseline (reason="baseline_2").

Firestore eval/phase17 박제는 `record_eval_sample` helper — pipeline `_process` 가
샘플링 통과 시 호출 (본 모듈은 박제 함수만 제공, caller 가 박제 결정).
"""

from __future__ import annotations

import logging
import random
from typing import Any

log = logging.getLogger(__name__)


# rule weight 박제 — random 비교 threshold.
_W_SCORE_EXTREME: float = 0.2
_W_CAUSES_MIN: float = 0.3
_W_FLAG_TRUE: float = 0.15
_W_BASELINE: float = 0.02


def _random() -> float:
    """random.random indirection — 테스트가 monkeypatch."""
    return random.random()


def _causes_len_min(analysis_doc: dict[str, Any]) -> bool:
    """geminiB 의 joint causes 중 최소값이 ≤ 3 인지 박제 (generic 의심 신호)."""
    gemini_b = analysis_doc.get("geminiB")
    if not isinstance(gemini_b, dict):
        return False
    min_len: int | None = None
    for joint_key, joint_data in gemini_b.items():
        if joint_key.startswith("_"):  # reserved (_fallbackReason / _meta) skip.
            continue
        if not isinstance(joint_data, dict):
            continue
        detail2 = joint_data.get("detail2", {})
        if not isinstance(detail2, dict):
            continue
        causes = detail2.get("causes", [])
        if not isinstance(causes, list):
            continue
        if min_len is None or len(causes) < min_len:
            min_len = len(causes)
    return min_len is not None and min_len <= 3


def should_sample(analysis_doc: dict[str, Any]) -> tuple[bool, str]:
    """analysis_doc → (샘플링 여부, 이유 라벨) 박제 — AI-SPEC §7 표 정합.

    rule priority (먼저 매치되는 rule 채택):
      1. isReference=True → reference_100.
      2. guardrail_triggered → guardrail_100.
      3. score < 30 or > 95 → score_extreme_20.
      4. causes len ≤ 3 → causes_min_30.
      5. geminiC flag True → flag_true_15.
      6. branch_3_auto → branch3_100.
      7. else baseline_2.

    Args:
      analysis_doc: Firestore users/{uid}/analyses/{id} 의 dict (또는 그 subset).
        키: isReference (bool), guardrail_triggered (str|None), score (float),
        geminiB (dict), geminiC (dict), geminiA (dict).

    Returns:
      `(sampled, reason)` — sampled True 면 caller 가 Firestore eval/phase17 박제.
    """
    # 1. isReference.
    if analysis_doc.get("isReference") is True:
        return (True, "reference_100")

    # 2. guardrail_triggered.
    if analysis_doc.get("guardrail_triggered"):
        return (True, "guardrail_100")

    # 3. score 양극단.
    score = analysis_doc.get("score")
    if isinstance(score, (int, float)) and (score < 30 or score > 95):
        return (_random() < _W_SCORE_EXTREME, "score_extreme_20")

    # 4. causes 최소.
    if _causes_len_min(analysis_doc):
        return (_random() < _W_CAUSES_MIN, "causes_min_30")

    # 5. geminiC flag.
    gemini_c = analysis_doc.get("geminiC")
    if isinstance(gemini_c, dict) and (
        bool(gemini_c.get("occlusion_severe"))
        or bool(gemini_c.get("camera_angle_problematic"))
    ):
        return (_random() < _W_FLAG_TRUE, "flag_true_15")

    # 6. branch_3_auto.
    gemini_a = analysis_doc.get("geminiA")
    if isinstance(gemini_a, dict) and gemini_a.get("routing_branch") == "branch_3_auto":
        return (True, "branch3_100")

    # 7. baseline.
    return (_random() < _W_BASELINE, "baseline_2")


def record_eval_sample(
    analysis_id: str,
    uid: str,
    reason: str,
    payload: dict[str, Any],
) -> None:
    """Firestore eval/phase17/{analysis_id} 박제 — caller (pipeline) 가 샘플링 통과 시 호출.

    graceful 폴백 — firestore_admin 미가용 시 warning 만 박고 noop. eval 박제 실패가
    분석 흐름 차단 0.
    """
    try:
        from sunity_shared import firestore_admin
    except ImportError as exc:  # pragma: no cover
        log.warning("firestore_admin import 실패 — eval 박제 skip: %s", exc)
        return

    try:
        client = firestore_admin._db()
    except Exception as exc:  # noqa: BLE001
        log.warning("firestore_admin._db() 실패 — eval 박제 skip: %s", exc)
        return

    import time

    doc_path = f"eval/phase17/samples/{analysis_id}"
    try:
        client.document(doc_path).set(
            {
                "analysis_id": analysis_id,
                "uid": uid,
                "reason": reason,
                "sampled_at": int(time.time() * 1000),
                "payload": payload,
            },
            merge=True,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("eval/phase17 박제 실패 — graceful skip: %s", exc)


__all__ = ["should_sample", "record_eval_sample"]
