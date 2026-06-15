"""정은지 reference 11개의 downstream 4필드 백필 orchestrator (Pod GPU 직접 실행).

목적 (D-01 / D-02 / R1 / R2 / R6 / R2-3 / R2-5 / R3-2 / R4-1 / R4-2 / R5):
  reference 백필은 학생 `_process` 가 호출하는 SAME `sunity_shared.analysis` 함수들을
  거치되, REFERENCE_V1_FORCE_CONFIG (pinned config) 로 거친다 — provably exact FOR THAT
  CONFIG, NOT "student path exact". 운영 `_process` 는 env-driven `_preflight_label_gate_passed()`
  + Layer-2-조건부 `technique_profile` 을 넘기지만, 본 reference pin 은 그것들을 None 으로
  고정한다 (R2). 또한 force motion_id 는 FallbackRecognizer profile (= None) 에서 resolve 되어
  known-reference contact/boost 가 발동하지 않는다 (R4-2).

산출 4필드:
  · meanAngles          — STORED active phase4_v1 angles 의 nanmean (R1, 재추론 X)
  · techniqueProfile    — FallbackRecognizer().recognize(STORED angles) EXTEND (R1, 재추론 X)
  · bodyNormalizationProfile — measure_body_profile(live pose_frames) (D-02 hybrid)
  · forceDirectionPattern    — infer_force_direction_pattern(force_signals(live frames)) (D-02 hybrid)

핵심 데이터 흐름:
  meanAngles + EXTEND 의 source 는 STORED active phase4_v1 `angles` (R1) — belle 가
  시각적으로 검수한 active pose 가 authoritative (D-01/D-02). RTMW 재추론은 ONLY live
  `pose_frames` (raw keypoints_3d + confidence) 를 얻기 위함이며, 이것은
  BodyNormalizationProfile + ForceDirectionPattern 만 소비한다 (phase4_v1 엔 raw
  keypoint/confidence 가 없음). 재추론 angles 는 검증 전용 — stored-vs-rerun 각도
  integrity gate 가 발산 시 (meanAngleDelta > MEAN_EPSILON_DEG OR p99 > P99_EPSILON_DEG —
  robust, RTMW transient spike 허용) 전체 seed 를 중단한다 (R1).

실행 (Pod, `-m` 미사용):
  # 1) 먼저 credential + 11-doc completeness gate (no S3/RTMW). 14-03 Task 1 이 호출.
  python backend/scripts/backfill_reference_downstream.py --check-firestore \\
      --motions ref-climb,ref-foxtop,ref-foxtop-split,ref-invert,ref-sideway-spin,\\
ref-combo,ref-elbow-twist-sister,ref-kip-up,ref-pdshape,ref-peter-pan,ref-power-spin
  # 2) dry-run (split JSON stdout, 파일 미생성)
  python backend/scripts/backfill_reference_downstream.py --bucket sunity-motion-pilot-videos --dry-run
  # 3) real-run (gate 통과 시에만 fixture write)
  python backend/scripts/backfill_reference_downstream.py --bucket sunity-motion-pilot-videos \\
      --output /workspace/reference-downstream-backfill.json

산출 fixture (R2-5 split):
  { generatedAt, seedPayload: { <id>: {meanAngles, techniqueProfile,
    bodyNormalizationProfile, forceDirectionPattern, captureViews} },
    diagnostics: { <id>: {storedAnglesHash, rerunAnglesHash, anglesFrames,
    maxAngleDelta, meanAngleDelta, forceSignalsReportSummary, meanAnglesSource,
    techniqueProfileSource, forceConfig, forceMotionIdSource, forceMotionId} } }

NEVER writes Firestore. NEVER touches joints3d/angles/activeVersion (Pitfall 4 / D-02).

[per [[reference-library-phase4-all11]] (Pitfall 1), [[firestore-nested-array-flat]],
 [[reference-v1-pinned-force-config]], [[runpod-gpu-env]], Plan 14-02 Task 1]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import math
import os
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# sys.path 주입 — shared/python layer (in-script, `-m` 미사용; extract_reference_body_profiles.py:39 패턴).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

# 헤비 의존 (imageio / rtmlib / boto3 / firebase-admin) 는 main()/각 모드 안에서 lazy
# import — `--help` 가 Mac 로컬에서도 exit 0 (의존성 부재 시 fail-fast 는 실행 시점).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("backfill_reference_downstream")


# ── 11-id 전체 motion 상수 (Pitfall 1 / [[reference-library-phase4-all11]]) ──
# 기존 5 (Plan 06-03) + 후속 6. --motions 기본은 11-union. 절대 5-subset default 금지.
ALL_MOTION_IDS: tuple[str, ...] = (
    # 원본 5
    "ref-climb",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-invert",
    "ref-sideway-spin",
    # 후속 6
    "ref-combo",
    "ref-elbow-twist-sister",
    "ref-kip-up",
    "ref-pdshape",
    "ref-peter-pan",
    "ref-power-spin",
)

# ── REFERENCE_V1_FORCE_CONFIG (R2 + R4-2) ──────────────────────────────────
# reference v1 의 PINNED force-config 를 config 객체에 박제한다 (behavior 아닌
# 명시 값으로 기록). 학생 _process 의 env-driven 값과 의도적으로 다르다:
#   recognizer=FallbackRecognizer, technique_profile=None, preflight=None,
#   Layer-2 off, fallback/null motion_id.
# Phase 15 비교 시 reference force 필드는 이 config 하에서 생성된 것으로 취급해야
# 한다 — selected-referenceMotionId force semantics 를 가정하면 안 된다 (R4-2).
# test_reference_backfill.py:74 의 REFERENCE_V1_FORCE_CONFIG 와 1:1 일치.
REFERENCE_V1_FORCE_CONFIG: dict = {
    "recognizer": "FallbackRecognizer",
    "techniqueProfileForForceSignals": None,
    "preflightLabelGatePassed": None,
    "forceSignalsLayer2Enabled": False,
    # R4-2 — fallback/null force motion_id 선택을 config 에 기록.
    "forceMotionIdSource": "fallback_profile_motion_id",
    "forceMotionId": None,
}

# stored-vs-rerun 각도 integrity gate 임계 (R1) — ROBUST 버전.
# RTMW 는 길고 복잡한(가림/모호한) 동작의 일부 프레임에서 비결정적이다 — 동일 영상·동일
# 코드인데도 ref-combo 가 한 실행 23.43° → 다음 실행 0.193° (단일 프레임 keypoint L/R
# swap 류). MAX 단일 프레임 게이트는 이 transient spike 에 걸려 매 실행 다른 motion 이
# 랜덤 실패한다 (11/11 동시 통과가 운에 의존). 따라서 gate 는 SYSTEMATIC shift 만 본다:
#   · meanAngleDelta > MEAN_EPSILON_DEG  (전체 평균 이동 = 진짜 pose-version 변화)
#   · p99AngleDelta  > P99_EPSILON_DEG   (분위 99%까지 이동 = 산발적 spike 가 아님)
# transient single-frame spike (mean≈0, p99≈0, max 만 큼) 는 허용 — 학생 _process 도
# 같은 RTMW 로 같은 프레임 모호성을 겪으므로 일관적이다. 진단용 maxAngleDelta 는 계속 기록.
# 향후 신규 전문가/동작에도 일관 동작 (belle 2026-06-15 robust gate 결정).
MEAN_EPSILON_DEG = 0.1
P99_EPSILON_DEG = 1.0

# 백필 re-inference 의 frame-extraction fps. phase4_v1 active angles 는
# reprocess_reference_motions_phase4.py --target-fps 18.0 ("pipeline 정합") 로 생성됐다
# (예: ref-climb anglesFrames=257). 백필 rerun 이 9fps 면 frame 수가 어긋나(≈172)
# stored-vs-rerun angle gate (R1) 가 항상 frame-count mismatch 로 abort 한다.
# 따라서 rerun 은 phase4_v1 과 동일한 18fps 로 추출해야 gate 가 정렬되고,
# body/force 필드도 stored pose 와 같은 frame 기반으로 산출된다.
# (학생 _process 는 FfmpegFrameExtractor() 기본 9fps — reference(18) vs student(9) 의
#  fps 차이는 Phase 14 가 만든 게 아닌 기존 조건이며 Mode 1 비교 정합은 Phase 15 의 몫.)
REFERENCE_TARGET_FPS = 18.0

# 단일시점 baseline (D-03) — 모든 motion captureViews=1.
DEFAULT_CAPTURE_VIEWS = 1


# ── 산출 dataclass ─────────────────────────────────────────────────────────
@dataclasses.dataclass
class ReferenceDownstreamResult:
    """compute_reference_downstream 단일 산출.

    test_reference_backfill.py 의 D-01 parity 테스트는 `.force_signals_report` 를
    직접 읽으므로 ForceSignalsReport 원본을 그대로 노출한다 (직접 호출 reference 와
    동일 객체 비교). seed_payload 는 camelCase flat dict (seedable), diagnostics 는
    별도 (never seeded).
    """

    mean_angles: dict
    technique_profile: dict
    body_normalization_profile: dict
    force_direction_pattern: dict
    capture_views: int
    # 원본 report — parity 테스트가 overall_confidence/warnings/phase_boundaries 비교.
    force_signals_report: object
    diagnostics: dict

    def seed_payload(self) -> dict:
        """R2-5 — seedable 5필드만. forceSignalsReportSummary / hashes 는 제외."""
        return {
            "meanAngles": self.mean_angles,
            "techniqueProfile": self.technique_profile,
            "bodyNormalizationProfile": self.body_normalization_profile,
            "forceDirectionPattern": self.force_direction_pattern,
            "captureViews": self.capture_views,
        }


def _snake_to_camel(key: str) -> str:
    parts = key.split("_")
    if not parts:
        return key
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


def _dataclass_to_camel_dict(obj):
    """pipeline._dataclass_to_camel_case_dict (app.py:1362) 와 동일 shape 재사용.

    dataclass / Enum / list / tuple / dict / scalar 5-case. 새 converter shape 를
    hand-roll 하지 않는다 (seedPayload 가 _process 산출과 동일 camelCase 보장).
    """
    from enum import Enum

    if obj is None:
        return None
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        raw = dataclasses.asdict(obj)
        return {_snake_to_camel(k): _dataclass_to_camel_dict(v) for k, v in raw.items()}
    if isinstance(obj, Enum):
        return str(obj.value)
    if isinstance(obj, (list, tuple)):
        return [_dataclass_to_camel_dict(x) for x in obj]
    if isinstance(obj, np.ndarray):
        # WR-06 — dataclass 필드에 raw ndarray 가 leaf 로 섞이면 scalar fallback
        # 으로 흘러 Firestore 직렬화/NaN 가드를 우회한다. list 로 명시 변환.
        return [_dataclass_to_camel_dict(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _dataclass_to_camel_dict(v) for k, v in obj.items()}
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def _technique_profile_to_camel(profile) -> dict:
    """TechniqueProfile EXTEND surface → camelCase flat dict.

    joint_expectations 는 dict[str, str] (flat) — nested-array 무관. key_moments /
    hold_window 등 비-seedable 필드는 제외 (seedPayload 는 lean).
    """
    return {
        "name": str(profile.name),
        "category": str(profile.category),
        # JOINT_KEYS → 'extend'/'bent_ok'/'contact' flat dict (line 채점 source).
        "jointExpectations": dict(profile.joint_expectations),
    }


def _sha256_angles(arr: np.ndarray) -> str:
    """STORED / re-run angles 의 canonical sha256 (diagnostics 용)."""
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
    return hashlib.sha256(a.tobytes()).hexdigest()


def compute_reference_downstream(
    pose_frames,
    *,
    pole_axis_measurement,
    angles: np.ndarray,
    fps: float = 9.0,
    motion_id: str | None = None,
    mode_context: str = "mode1",
    force_config: dict | None = None,
) -> ReferenceDownstreamResult:
    """4 downstream 필드 산출 — SAME sunity_shared 함수, REFERENCE_V1_FORCE_CONFIG (R6).

    meanAngles / techniqueProfile 는 `angles` 인자 (orchestrator 가 STORED active
    phase4_v1 angles 로 set, R1) 에서만 산출 — 절대 재추론 angles 가 아니다.
    bodyNormalizationProfile / forceDirectionPattern 은 `pose_frames` (live RTMW) 에서.

    R2 — 학생 _process 는 env 기반 _preflight_label_gate_passed() 를 전달하므로 이것은
    "student path exact" 가 아니라 "same functions under reference-v1 pinned config" 다.
    env flip (PREFLIGHT_LABEL_GATE_PASSED=1) 시 force-signal confidence 가 갈라진다
    (test_r2_env_flip_divergence 가 증명).
    """
    from sunity_shared.analysis import force_pattern as fp
    from sunity_shared.analysis import force_signals as fs
    from sunity_shared.analysis import skeleton
    from sunity_shared.analysis.body_normalization_measurer import (
        measure_body_profile,
    )
    from sunity_shared.analysis.technique import FallbackRecognizer

    if force_config is None:
        force_config = REFERENCE_V1_FORCE_CONFIG

    stored = np.asarray(angles, dtype=float)
    if stored.ndim != 2:
        raise ValueError(
            f"angles must be 2D (T, J), got shape {stored.shape}"
        )

    # ── meanAngles (R1) — STORED angles 의 nanmean. 재추론 X. ──────────────
    with np.errstate(all="ignore"):
        mean_vec = np.nanmean(stored, axis=0)
    mean_angles = {
        skeleton.JOINT_KEYS[i]: (
            float(mean_vec[i]) if math.isfinite(float(mean_vec[i])) else None
        )
        for i in range(min(len(skeleton.JOINT_KEYS), stored.shape[1]))
    }

    # ── techniqueProfile (R1) — FallbackRecognizer EXTEND from STORED angles. ─
    # D-01 동일 fn (_process:1610). Fallback per A1 default (NOT Gemini).
    profile = FallbackRecognizer().recognize(stored)
    technique_profile = _technique_profile_to_camel(profile)

    # ── bodyNormalizationProfile (D-02 hybrid) — live pose_frames. ──────────
    # measure_body_profile (_process:1171) 는 raw keypoints_3d (+confidence) 필요
    # → phase4_v1 flat 에는 없음 → 재추론 frames 가 유일 source.
    body_profile = measure_body_profile(pose_frames)
    body_normalization_profile = _dataclass_to_camel_dict(body_profile)

    # ── forceDirectionPattern (D-02 hybrid) — REFERENCE_V1_FORCE_CONFIG. ─────
    # R4-2 — force motion_id 는 FallbackRecognizer profile 에서 resolve (= None).
    # FallbackRecognizer 는 motion_id 를 set 하지 않으므로 None → known-reference
    # contact/boost 가 발동하지 않는다. 본 reference 의 force 필드는 known-reference
    # 의미 없이 생성되므로 Phase 15 는 reference 가 selected-referenceMotionId force
    # semantics 를 썼다고 가정하면 안 된다 (R4-2).
    force_motion_id = getattr(profile, "motion_id", None)

    # R2 — compute_force_signals 에 STORED angles (이미 temporal_fill 1회, caller
    # 책임) + 주입 pole_axis_measurement (R6) 전달. preflight=None + technique=None +
    # motion_id=None 으로 PIN → D-01 EXACT parity under REFERENCE_V1_FORCE_CONFIG
    # (test_d01_reference_v1_pinned_config_parity 의 직접 호출 reference 와 동일).
    force_signals_report = fs.compute_force_signals(
        pose_frames,
        pole_axis_measurement,
        body_profile,
        angles=stored,
        fps=fps,
        motion_id=force_motion_id,  # R4-2 — None
        technique_profile=None,  # REFERENCE_V1_FORCE_CONFIG layer-2 off
        preflight_label_gate_passed=None,  # pinned None (NOT env-driven)
    )

    # A4 — _apply_motion_id_boost 는 motion_id is not None 일 때만 fire (R4-2: 미발동).
    fpi = fp.infer_force_direction_pattern(
        force_signals_report,
        motion_id=force_motion_id,  # R4-2 — None
        mode_context=mode_context,  # type: ignore[arg-type]
    )
    force_direction_pattern = _dataclass_to_camel_dict(fpi)

    diagnostics = {
        "meanAnglesSource": "reference.phase4_v1.angles",
        "techniqueProfileSource": "reference.phase4_v1.angles",
        "forceConfig": dict(force_config),
        "forceMotionIdSource": "fallback_profile_motion_id",
        "forceMotionId": force_motion_id,
        "forceSignalsReportSummary": {
            "overallConfidence": str(force_signals_report.overall_confidence),
            "warnings": list(force_signals_report.warnings or []),
            "phases": [b.phase for b in force_signals_report.phase_boundaries],
        },
    }

    return ReferenceDownstreamResult(
        mean_angles=mean_angles,
        technique_profile=technique_profile,
        body_normalization_profile=body_normalization_profile,
        force_direction_pattern=force_direction_pattern,
        capture_views=DEFAULT_CAPTURE_VIEWS,
        force_signals_report=force_signals_report,
        diagnostics=diagnostics,
    )


# ── --check-firestore gate (R2-3 + R3-2) ───────────────────────────────────
def _run_check_firestore(motion_ids: list[str]) -> int:
    """credential + completeness gate — NEVER calls S3 or RTMW.

    auth._ensure_firebase() (FIREBASE_SA_JSON / FIREBASE_SA_PATH / FIREBASE_SA_PARAM
    via auth._load_service_account_dict) 사용 — 절대 hand-rolled credentials.Certificate
    path 금지. 각 doc 에 대해 activeVersion + angles + anglesJointKeys + anglesFrames
    present AND frame-count sanity (anglesFrames > 0 AND len(angles) ==
    anglesFrames * len(anglesJointKeys)) 검사. keys-not-values OK/FAIL 라인 출력.
    모든 요청 motion 통과 시에만 exit 0; missing creds OR incomplete doc → 비-0.

    Pod production gate (14-03 Task 1) 는 11개 전부 명시 전달 → non-ref-climb
    completeness 실패가 expensive S3/RTMW 전에 fail fast (T-14-15).
    """
    # lazy import — Mac `--help` 에서도 exit 0.
    try:
        from sunity_shared import auth as _auth
        from sunity_shared import firestore_admin
    except ImportError as e:  # pragma: no cover
        log.error("sunity_shared import 실패: %s", e)
        return 2

    # credential gate — auth._ensure_firebase (SA 소스 = FIREBASE_SA_*).
    try:
        _auth._ensure_firebase()
    except Exception as e:  # noqa: BLE001 — credential 실패는 actionable 메시지로.
        log.error(
            "Firebase SA 미마운트/미설정 — Pod 에 FIREBASE_SA_JSON / FIREBASE_SA_PATH / "
            "FIREBASE_SA_PARAM 중 하나 필요. (%s)",
            e,
        )
        return 2

    failed: list[str] = []
    for mid in motion_ids:
        try:
            doc = firestore_admin.get_reference_motion(mid)
        except Exception as e:  # noqa: BLE001
            log.error("[%s] FAIL — read error: %s", mid, e)
            failed.append(mid)
            continue
        if doc is None:
            log.error("[%s] FAIL — reference doc 없음", mid)
            failed.append(mid)
            continue

        active_version = doc.get("activeVersion")
        angles = doc.get("angles")
        joint_keys = doc.get("anglesJointKeys")
        frames = doc.get("anglesFrames")

        # keys-not-values — present 여부만 출력 (실제 값 미출력, 보안).
        present = {
            "activeVersion": active_version is not None,
            "angles": angles is not None,
            "anglesJointKeys": joint_keys is not None,
            "anglesFrames": frames is not None,
        }
        if not all(present.values()):
            missing = [k for k, v in present.items() if not v]
            log.error("[%s] FAIL — 필드 누락: %s", mid, missing)
            failed.append(mid)
            continue

        # frame-count sanity — anglesFrames > 0 AND len(angles) == frames * J.
        try:
            n_frames = int(frames)
            n_j = len(joint_keys)
            n_angles = len(angles)
        except (TypeError, ValueError) as e:
            log.error("[%s] FAIL — frame-count 타입 오류: %s", mid, e)
            failed.append(mid)
            continue
        if n_frames <= 0 or n_angles != n_frames * n_j:
            log.error(
                "[%s] FAIL — frame-count 불일치: anglesFrames=%d jointKeys=%d "
                "len(angles)=%d (expected %d)",
                mid,
                n_frames,
                n_j,
                n_angles,
                n_frames * n_j,
            )
            failed.append(mid)
            continue

        log.info(
            "[%s] OK — activeVersion+angles+anglesJointKeys+anglesFrames present, "
            "frames=%d jointKeys=%d",
            mid,
            n_frames,
            n_j,
        )

    if failed:
        log.error(
            "--check-firestore FAIL — incomplete/missing motions: %s (총 %d/%d 실패)",
            failed,
            len(failed),
            len(motion_ids),
        )
        return 1
    log.info(
        "--check-firestore OK — 요청 %d개 motion 전부 completeness 통과 (S3/RTMW 미실행)",
        len(motion_ids),
    )
    return 0


# ── full backfill path ─────────────────────────────────────────────────────
def _read_stored_angles(firestore_admin, motion_id: str) -> tuple[np.ndarray, str]:
    """STORED active phase4_v1 angles 읽기 + reshape (T,J) (R1, A).

    Returns (stored_angles (T,J), storedAnglesHash). incomplete 시 RuntimeError.
    """
    doc = firestore_admin.get_reference_motion(motion_id)
    if doc is None:
        raise RuntimeError(f"reference/{motion_id} doc 없음")
    angles = doc.get("angles")
    joint_keys = doc.get("anglesJointKeys")
    frames = doc.get("anglesFrames")
    if angles is None or joint_keys is None or frames is None:
        raise RuntimeError(
            f"reference/{motion_id} incomplete — angles/anglesJointKeys/anglesFrames 누락"
        )
    n_frames = int(frames)
    n_j = len(joint_keys)
    if n_frames <= 0 or len(angles) != n_frames * n_j:
        raise RuntimeError(
            f"reference/{motion_id} frame-count 불일치 (anglesFrames={n_frames} "
            f"jointKeys={n_j} len(angles)={len(angles)})"
        )
    stored = np.asarray(angles, dtype=float).reshape(n_frames, n_j)
    return stored, _sha256_angles(stored)


def _process_one(
    motion_id: str,
    video_path: Path,
    extractor,
    rtmw_engine,
    stored_angles: np.ndarray,
    stored_hash: str,
) -> tuple[dict, dict]:
    """단일 motion full backfill → (seedPayload[id], diagnostics[id]).

    B (live frames) → C (angle integrity gate) → D (compute) → E (split).
    angle gate 발산 시 RuntimeError (caller 가 전체 seed 중단, R1).
    """
    from sunity_shared.analysis.features import (
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.pole_geometry import (
        build_pole_axis_measurement,
    )
    from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array
    from sunity_shared.analysis.temporal import temporal_fill

    t0 = time.time()

    # (B) LIVE FRAMES — vertical-fallback PoleAxis + RTMW estimate (D-02 hybrid).
    frames = extractor.extract(str(video_path))
    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    pose_frames = rtmw_engine.estimate(frames, default_pole)
    if not pose_frames:
        raise RuntimeError(f"pose_frames empty for {motion_id}")
    pole_meas = build_pole_axis_measurement(default_pole, line=None, frame_index=None)

    # (C) ANGLE INTEGRITY GATE (R1) — re-run angles 는 검증 전용, meanAngles/EXTEND 의
    #     source 가 아니다. ONE temporal_fill (Pitfall 3 — double-smooth 금지).
    kp = to_coco17_array(pose_frames)
    rerun_angles = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))
    rerun_frames = int(rerun_angles.shape[0])
    if rerun_frames != len(pose_frames):
        raise RuntimeError(
            f"[{motion_id}] frame-alignment 실패 — rerun angles frames={rerun_frames} "
            f"!= len(pose_frames)={len(pose_frames)}"
        )
    # stored (T,J) vs rerun (T',J) — frame 수가 다르면 element-wise delta 불가
    # (pose-version 재검증 문제). 같은 길이일 때만 delta 산출, 다르면 abort.
    if stored_angles.shape[0] != rerun_angles.shape[0]:
        raise RuntimeError(
            f"[{motion_id}] stored vs rerun frame 수 불일치 — pose-version 재검증 필요 "
            f"(stored T={stored_angles.shape[0]} rerun T={rerun_angles.shape[0]})"
        )
    diff = np.abs(stored_angles - rerun_angles)
    # WR-04 — NaN-coverage 게이트. nanmean/nanpercentile 은 stored/rerun 의 NaN
    # 위치가 어긋난 element 를 조용히 무시하므로, joint column 단위로 NaN-coverage 가
    # 갈라진 경우(예: stored 는 knee 있음, rerun 은 유실) robust 통계가 보지 못한다.
    # 비교 가능한(non-NaN) element 비율이 낮으면 pose-version drift 로 보고 abort.
    comparable = np.isfinite(diff)
    coverage = float(comparable.mean()) if diff.size else 1.0
    if coverage < 0.95:
        raise RuntimeError(
            f"[{motion_id}] angle gate — NaN coverage {coverage:.2%} < 95%, "
            f"pose-version 재검증 필요 (stored/rerun NaN 위치 divergence)."
        )
    max_delta = float(np.nanmax(diff)) if diff.size else 0.0
    mean_delta = float(np.nanmean(diff)) if diff.size else 0.0
    p99_delta = float(np.nanpercentile(diff, 99)) if diff.size else 0.0
    rerun_hash = _sha256_angles(rerun_angles)
    # 진단 로깅 — divergence 가 단일 프레임 spike(예: L/R flip) 인지 pervasive 인지 분류용.
    if diff.size:
        p95 = float(np.nanpercentile(diff, 95))
        over1 = int(np.count_nonzero(diff > 1.0))
        fi, ji = (int(x) for x in np.unravel_index(int(np.nanargmax(diff)), diff.shape))
        log.info(
            "[%s] angle-delta diag: max=%.3f mean=%.4f p95=%.3f p99=%.3f over1deg=%d/%d argmax=(frame=%d,joint=%d)",
            motion_id, max_delta, mean_delta, p95, p99_delta, over1, diff.size, fi, ji,
        )
    # ROBUST gate (R1) — systematic shift 만 차단, RTMW transient single-frame spike 허용.
    gate_failed = (
        not math.isfinite(mean_delta)
        or not math.isfinite(p99_delta)
        or mean_delta > MEAN_EPSILON_DEG
        or p99_delta > P99_EPSILON_DEG
    )
    if gate_failed:
        raise RuntimeError(
            f"[{motion_id}] stored-vs-rerun angle gate 실패 — meanAngleDelta={mean_delta:.4f} "
            f"(>{MEAN_EPSILON_DEG}) 또는 p99AngleDelta={p99_delta:.3f} (>{P99_EPSILON_DEG}); "
            f"maxAngleDelta={max_delta:.3f} (참고). pose-version 재검증 문제 — derived-field 백필 X, "
            f"전체 real seed 중단 (R1)."
        )

    # (D) COMPUTE — REFERENCE_V1_FORCE_CONFIG, STORED angles + 주입 pole_meas.
    result = compute_reference_downstream(
        pose_frames,
        pole_axis_measurement=pole_meas,
        angles=stored_angles,  # R1 — STORED, 재추론 angles 아님.
        fps=REFERENCE_TARGET_FPS,  # phase4_v1 정합 (18fps) — 추출 fps 와 일치.
        motion_id=motion_id,
        mode_context="mode1",
        force_config=REFERENCE_V1_FORCE_CONFIG,
    )

    # (E) SPLIT FIXTURE — seedPayload (5필드) + diagnostics (hashes/deltas/summary).
    seed = result.seed_payload()
    diag = dict(result.diagnostics)
    diag.update(
        {
            "storedAnglesHash": stored_hash,
            "rerunAnglesHash": rerun_hash,
            "anglesFrames": rerun_frames,
            "maxAngleDelta": max_delta,
            "meanAngleDelta": mean_delta,
            "p99AngleDelta": p99_delta,
            # DEFERRED 결정: raw forceSignalsReport 를 Firestore 에 persist 할지는
            # 미정 — 현재는 diagnostics summary 만 (artifact-only).
        }
    )

    log.info(
        "[%s] frames=%d body_conf=%s maxAngleDelta=%.4f %.1fs",
        motion_id,
        len(pose_frames),
        seed["bodyNormalizationProfile"].get("confidence"),
        max_delta,
        time.time() - t0,
    )
    return seed, diag


def _has_nan_or_inf(obj) -> bool:
    """seedPayload 내부에 NaN/inf scalar 가 있으면 True (R5 all-or-nothing)."""
    # WR-02 — np.float32 등 float-비서브클래스 numpy scalar 도 명시 포함
    # (np.float64 만 float subclass 라 우회될 수 있음).
    if isinstance(obj, (float, np.floating)):
        return not math.isfinite(float(obj))
    if isinstance(obj, dict):
        return any(_has_nan_or_inf(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_nan_or_inf(v) for v in obj)
    return False


def _run_backfill(args, motion_ids: list[str]) -> int:
    """full backfill path — STORED read → S3 → RTMW → compute → gate → split JSON."""
    # 헤비 의존 fail-fast 체크 (Wave-0 요구).
    try:
        import boto3  # noqa: F401
        import imageio  # noqa: F401
    except ImportError as e:
        log.error("헤비 의존 부재 (%s). Pod 에서 pip install imageio boto3 후 재시도.", e)
        return 2
    try:
        import firebase_admin  # noqa: F401
    except ImportError as e:
        log.error("firebase-admin 부재 (%s).", e)
        return 2

    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
    if not region:
        log.error("AWS_DEFAULT_REGION 환경변수 필요 (예: ap-northeast-2).")
        return 2

    import boto3 as _boto3

    from sunity_shared import firestore_admin
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import (
        RTMWPoseEngine,
    )

    s3 = _boto3.client("s3", region_name=region)
    # phase4_v1 정합 — 18fps 추출 (stored anglesFrames 와 frame 정렬, R1 gate 통과).
    extractor = FfmpegFrameExtractor(target_fps=REFERENCE_TARGET_FPS)
    rtmw_engine = RTMWPoseEngine()

    log.info(
        "backfill start motions=%d mode=%s (AWS region=%s)",
        len(motion_ids),
        "dry-run" if args.dry_run else "real-run",
        region,
    )

    seed_payload: dict[str, dict] = {}
    diagnostics: dict[str, dict] = {}
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in motion_ids:
            log.info("--- %s ---", motion_id)
            try:
                # (A) STORED ANGLES READ (R1) — meanAngles/EXTEND 의 유일 source.
                stored_angles, stored_hash = _read_stored_angles(
                    firestore_admin, motion_id
                )
                # S3 download — keys-not-values (bucket/key 만, 시크릿 미출력).
                video_path = td_path / f"{motion_id}.mp4"
                key = f"reference/{motion_id}.mp4"
                log.info("S3 download s3://%s/%s", args.bucket, key)
                s3.download_file(args.bucket, key, str(video_path))
                seed, diag = _process_one(
                    motion_id,
                    video_path,
                    extractor,
                    rtmw_engine,
                    stored_angles,
                    stored_hash,
                )
                seed_payload[motion_id] = seed
                diagnostics[motion_id] = diag
            except Exception:  # noqa: BLE001 — per-motion 격리 (로깅), exit 은 all-or-nothing.
                log.error("[%s] FAIL — %s", motion_id, traceback.format_exc())
                failures.append(motion_id)

    # ── all-or-nothing gate (R5) ──────────────────────────────────────────
    nan_inf = any(_has_nan_or_inf(v) for v in seed_payload.values())
    gate_failed = (
        len(failures) > 0
        or len(seed_payload) != len(ALL_MOTION_IDS)
        or nan_inf
    )

    fixture = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "seedPayload": seed_payload,
        "diagnostics": diagnostics,
    }

    if args.dry_run:
        # dry-run → split JSON stdout, 파일 미생성.
        print(json.dumps(fixture, ensure_ascii=False, indent=2))
        log.info(
            "dry-run 완료 — %d/%d motion 측정 (failures=%d nan_inf=%s). 파일 미생성.",
            len(seed_payload),
            len(ALL_MOTION_IDS),
            len(failures),
            nan_inf,
        )
        return 0

    if gate_failed and not args.allow_partial_diagnostic:
        # R5 — seedable fixture 미생성. 진단 JSON 만 (있으면) write 후 비-0 exit.
        log.error(
            "all-or-nothing gate 실패 — failures=%d len(seedPayload)=%d (need %d) "
            "nan_inf=%s. seedable fixture 미생성 (--allow-partial-diagnostic 로 강제).",
            len(failures),
            len(seed_payload),
            len(ALL_MOTION_IDS),
            nan_inf,
        )
        if args.output:
            diag_path = args.output.with_suffix(".diagnostic.json")
            diag_path.parent.mkdir(parents=True, exist_ok=True)
            diag_path.write_text(
                json.dumps(
                    {
                        "generatedAt": fixture["generatedAt"],
                        "diagnostics": diagnostics,
                        "failures": failures,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            log.info("진단 JSON → %s", diag_path)
        return 1

    # gate 통과 (또는 --allow-partial-diagnostic) → seedable fixture write.
    if not args.output:
        log.error("real-run 에는 --output 필요.")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2))
    log.info(
        "real-run 완료 — %d/%d motion. → %s (%.1f KB)",
        len(seed_payload),
        len(ALL_MOTION_IDS),
        args.output,
        args.output.stat().st_size / 1024,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "정은지 reference 11개의 downstream 4필드 (meanAngles + techniqueProfile + "
            "bodyNormalizationProfile + forceDirectionPattern) 백필 orchestrator. "
            "Pod GPU 직접 실행 (CPU NaN). --check-firestore 먼저 (R2-3/R3-2)."
        )
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="S3 bucket (예: sunity-motion-pilot-videos). full backfill 에 필요.",
    )
    parser.add_argument(
        "--output",
        default=None,
        type=Path,
        help="seedable JSON 출력 경로 (real-run 필수, 예: /workspace/reference-downstream-backfill.json)",
    )
    parser.add_argument(
        "--motions",
        default=None,
        help=(
            "쉼표 분리 motion id list. 미지정 시 11-union 전체 (Pitfall 1 — 절대 5-subset "
            "default 금지). --check-firestore 의 Pod production gate 는 11개 전부 명시 전달."
        ),
    )
    parser.add_argument(
        "--check-firestore",
        action="store_true",
        help=(
            "R2-3/R3-2 — credential + completeness gate. NEVER S3/RTMW. 요청 motion 전부 "
            "activeVersion+angles+anglesJointKeys+anglesFrames + frame-count sanity 검사 후 "
            "exit. 11개 전부 명시 시 fail-fast 게이트, 1개 시 순수 credential 체크."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="split JSON 을 stdout 으로만 출력. 파일 미생성.",
    )
    parser.add_argument(
        "--allow-partial-diagnostic",
        action="store_true",
        help=(
            "R5 우회 — all-or-nothing gate 실패 시에도 seedable fixture 강제 생성 "
            "(진단 전용, 운영 seed 금지)."
        ),
    )
    args = parser.parse_args()

    # --motions 미지정 → 11-union (Pitfall 1). 절대 5-subset default 금지.
    if args.motions:
        motion_ids = [m.strip() for m in args.motions.split(",") if m.strip()]
    else:
        motion_ids = list(ALL_MOTION_IDS)
    if not motion_ids:
        log.error("--motions 가 비어있음")
        sys.exit(2)

    if args.check_firestore:
        sys.exit(_run_check_firestore(motion_ids))

    if not args.bucket:
        log.error("full backfill 에는 --bucket 필요 (또는 --check-firestore).")
        sys.exit(2)
    sys.exit(_run_backfill(args, motion_ids))


if __name__ == "__main__":
    main()
