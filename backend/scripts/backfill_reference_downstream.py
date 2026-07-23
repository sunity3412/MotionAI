"""정은지 reference 11개의 downstream 필드 candidate-aware 백필 orchestrator (Pod GPU).

33-04 재작성 (codex concern 2 / suggestion 3):
  기존 스크립트는 (a) TOP-LEVEL phase4_v1 angles (get_reference_motion:구 461) 를
  source 로 읽고, (b) "NEVER writes Firestore" 로 seed JSON 만 뱉고, (c) 추출 fps 를
  REFERENCE_TARGET_FPS=18.0 로 하드코딩하고, (d) keypointReport / bodyComparisonSourcePose
  를 산출하지 않았다. C+M3 substrate 트랙에서는 활성(phase4_v1)이 아니라 **candidate
  버전**(reference/{id}/versions/{candidate}) 이 authoritative source 이므로, 이 스크립트는:
    · candidate 버전에서 새 angles/keypointReport 를 읽고 (top-level 절대 미접촉),
    · 파생 필드를 전부 재산출한 뒤,
    · 같은 candidate 버전 문서에 MERGE 백한다 (activeVersion/top-level 무접촉 — flip 은 33-07),
    · fps 는 candidate 메타(keypointReport.fps) 또는 --target-fps CLI 에서 읽는다 (18.0 하드코딩 제거),
    · bodyComparisonSourcePose 는 실존 producer(extract_reference_body_profiles._build_source_pose)
      로 산출해 11 doc 전부 채운다.

candidate consumer 필드(angles/joints3d/keypointReport)는 33-03 재추출본을 재사용하고,
live pose_frames 는 bodyNormalizationProfile / forceDirectionPattern / bodyComparisonSourcePose /
referenceKeypointReport 산출에만 한 번 추론한다 (raw keypoints/confidence 는 candidate flat 에 없음).

산출/merge 필드 (전부 candidate 버전 문서로):
  · meanAngles                — candidate angles 의 nanmean (재추론 X)
  · techniqueProfile          — FallbackRecognizer().recognize(candidate angles) (재추론 X)
  · bodyNormalizationProfile  — measure_body_profile(live pose_frames)
  · forceDirectionPattern     — infer_force_direction_pattern(force_signals(live)) (REFERENCE_V1_FORCE_CONFIG)
  · bodyComparisonSourcePose  — _build_source_pose(live pose_frames) (대표 frame = 평균 conf 최대)
  · keypointReport            — build_keypoint_report(live, fps=candidate fps) — fps 라벨 9.0
  · referenceKeypointReport   — 동상 (mode1 소비 경로)
  · captureViews              — 단일시점 baseline (D-03) = 1

integrity gate (R1) — candidate angles 와 live rerun angles 의 systematic shift 만 차단
(meanAngleDelta > MEAN_EPSILON_DEG OR p99 > P99_EPSILON_DEG). RTMW transient single-frame
spike 는 허용. gate 가 걸리면 임계를 올리지 말고 원인 조사 (D-29). 채점 산식 무접촉 (D-20).
REFERENCE_V1_FORCE_CONFIG (pinned) 유지.

실행 (Pod, `-m` 미사용):
  # 1) credential + 11-doc completeness gate (no S3/RTMW).
  python backend/scripts/backfill_reference_downstream.py --check-firestore \\
      --motions ref-climb,ref-combo,...,ref-power-spin
  # 2) dry-run — candidate source → derive → 산출 dump stdout, Firestore 미write.
  python backend/scripts/backfill_reference_downstream.py \\
      --reference-version phase33-cm3-run1 --bucket sunity-motion-pilot-videos --dry-run
  # 3) real-run — gate 통과 시 candidate 버전 문서에 MERGE + 산출 dump.
  python backend/scripts/backfill_reference_downstream.py \\
      --reference-version phase33-cm3-run1 --bucket sunity-motion-pilot-videos \\
      --write-candidate --output /workspace/reference-downstream-backfill.json

candidate 버전 문서에만 MERGE 한다. top-level / activeVersion / joints3d / angles 는
절대 write 하지 않는다 (Pitfall 4 / D-02 / 33-17 candidate!=active 가드).

[per [[reference-library-phase4-all11]] (Pitfall 1), [[firestore-nested-array-flat]],
 [[reference-v1-pinned-force-config]], [[runpod-gpu-env]], 33-CONTEXT D-18~D-30, codex concern 2]
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

# sys.path 주입 — shared/python layer + scripts 디렉터리(sibling producer 재사용).
_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR.parents[0] / "shared" / "python"))
sys.path.insert(0, str(_SCRIPTS_DIR))

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

# stored-vs-rerun 각도 integrity gate 임계 (R1) — ROBUST 버전. 재fit 금지 (D-29).
# RTMW 는 길고 복잡한(가림/모호한) 동작의 일부 프레임에서 비결정적이다 — 동일 영상·동일
# 코드인데도 ref-combo 가 한 실행 23.43° → 다음 실행 0.193° (단일 프레임 keypoint L/R
# swap 류). MAX 단일 프레임 게이트는 이 transient spike 에 걸려 매 실행 다른 motion 이
# 랜덤 실패한다. 따라서 gate 는 SYSTEMATIC shift 만 본다:
#   · meanAngleDelta > MEAN_EPSILON_DEG  (전체 평균 이동 = 진짜 pose-version 변화)
#   · p99AngleDelta  > P99_EPSILON_DEG   (분위 99%까지 이동 = 산발적 spike 가 아님)
# transient single-frame spike (mean≈0, p99≈0, max 만 큼) 는 허용 — 학생 _process 도
# 같은 RTMW 로 같은 프레임 모호성을 겪으므로 일관적이다. 진단용 maxAngleDelta 는 계속 기록.
# gate 가 걸리면 임계를 올리지 말고 원인 조사 (33-04 D-29 / [[calibration-source-hard-gate]]).
MEAN_EPSILON_DEG = 0.1
P99_EPSILON_DEG = 1.0

# 단일시점 baseline (D-03) — 모든 motion captureViews=1.
DEFAULT_CAPTURE_VIEWS = 1

# candidate 버전 문서 하위경로 템플릿 (33-17 versions/{candidate}).
_VERSIONS_SUBPATH = "reference/{motion_id}/versions/{version}"


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


def _keypoint_report_to_camel(report) -> dict:
    """KeypointReport dataclass → Firestore camelCase dict.

    extract_reference_keypoint_reports._camel_case_report 와 1:1 (flat list 필드).
    """
    return {
        "version": report.version,
        "joints": list(report.joints),
        "frames": int(report.frames),
        "fps": float(report.fps),
        "data": list(report.data),
        "confidence": list(report.confidence),
        "reliability": list(report.reliability),
        "axisData": list(report.axis_data),
        "axisMask": list(report.axis_mask),
        "warnings": list(report.warnings),
    }


def _sha256_angles(arr: np.ndarray) -> str:
    """candidate / re-run angles 의 canonical sha256 (diagnostics 용)."""
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

    meanAngles / techniqueProfile 는 `angles` 인자 (orchestrator 가 candidate 버전
    angles 로 set, R1) 에서만 산출 — 절대 재추론 angles 가 아니다.
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

    # ── meanAngles (R1) — candidate angles 의 nanmean. 재추론 X. ────────────
    with np.errstate(all="ignore"):
        mean_vec = np.nanmean(stored, axis=0)
    mean_angles = {
        skeleton.JOINT_KEYS[i]: (
            float(mean_vec[i]) if math.isfinite(float(mean_vec[i])) else None
        )
        for i in range(min(len(skeleton.JOINT_KEYS), stored.shape[1]))
    }

    # ── techniqueProfile (R1) — FallbackRecognizer EXTEND from candidate angles. ─
    # D-01 동일 fn (_process:1610). Fallback per A1 default (NOT Gemini).
    profile = FallbackRecognizer().recognize(stored)
    technique_profile = _technique_profile_to_camel(profile)

    # ── bodyNormalizationProfile (D-02 hybrid) — live pose_frames. ──────────
    # measure_body_profile (_process:1171) 는 raw keypoints_3d (+confidence) 필요
    # → candidate flat 에는 없음 → 재추론 frames 가 유일 source.
    body_profile = measure_body_profile(pose_frames)
    body_normalization_profile = _dataclass_to_camel_dict(body_profile)

    # ── forceDirectionPattern (D-02 hybrid) — REFERENCE_V1_FORCE_CONFIG. ─────
    # R4-2 — force motion_id 는 FallbackRecognizer profile 에서 resolve (= None).
    # FallbackRecognizer 는 motion_id 를 set 하지 않으므로 None → known-reference
    # contact/boost 가 발동하지 않는다. 본 reference 의 force 필드는 known-reference
    # 의미 없이 생성되므로 Phase 15 는 reference 가 selected-referenceMotionId force
    # semantics 를 썼다고 가정하면 안 된다 (R4-2).
    force_motion_id = getattr(profile, "motion_id", None)

    # R2 — compute_force_signals 에 candidate angles (이미 temporal_fill 1회, caller
    # 책임) + 주입 pole_axis_measurement (R6) 전달. preflight=None + technique=None +
    # motion_id=None 으로 PIN → D-01 EXACT parity under REFERENCE_V1_FORCE_CONFIG.
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
        "meanAnglesSource": "reference.candidate.angles",
        "techniqueProfileSource": "reference.candidate.angles",
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
    present AND frame-count sanity 검사. keys-not-values OK/FAIL 라인 출력.
    모든 요청 motion 통과 시에만 exit 0; missing creds OR incomplete doc → 비-0.
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


# ── candidate 버전 read / merge helpers (33-04) ─────────────────────────────
def _read_candidate_doc(firestore_admin, motion_id: str, version: str) -> dict:
    """reference/{id}/versions/{version} 직접 read (top-level 미접촉).

    33-17 shadow overlay 와 별개로 candidate 문서 자체를 직접 읽는다 — 백필은 candidate
    를 source AND merge target 으로 명시 소유해야 하기 때문 (codex concern 2).
    """
    path = _VERSIONS_SUBPATH.format(motion_id=motion_id, version=version)
    snap = firestore_admin._doc(path).get()
    if not snap.exists:
        raise RuntimeError(
            f"reference/{motion_id}/versions/{version} 문서 부재 — 33-03 재추출 candidate 없음"
        )
    return snap.to_dict() or {}


def _candidate_angles(doc: dict, motion_id: str) -> tuple[np.ndarray, str]:
    """candidate 버전 angles 읽기 + reshape (T,J). Returns (angles, hash)."""
    angles = doc.get("angles")
    joint_keys = doc.get("anglesJointKeys")
    frames = doc.get("anglesFrames")
    if angles is None or joint_keys is None or frames is None:
        raise RuntimeError(
            f"candidate {motion_id} incomplete — angles/anglesJointKeys/anglesFrames 누락"
        )
    n_frames = int(frames)
    n_j = len(joint_keys)
    if n_frames <= 0 or len(angles) != n_frames * n_j:
        raise RuntimeError(
            f"candidate {motion_id} frame-count 불일치 (anglesFrames={n_frames} "
            f"jointKeys={n_j} len(angles)={len(angles)})"
        )
    stored = np.asarray(angles, dtype=float).reshape(n_frames, n_j)
    return stored, _sha256_angles(stored)


def _resolve_target_fps(doc: dict, cli_fps: float | None, motion_id: str) -> float:
    """추출 fps 결정 — CLI > candidate keypointReport.fps. 18.0 하드코딩 폴백 없음.

    C+M3 은 학생 경로(9fps)와 기질을 맞추는 게 목적이므로 fps 는 candidate 메타에서
    읽는다 (33-03 재추출본 keypointReport.fps = 9.0). CLI --target-fps 로 명시 override 가능.
    둘 다 없으면 에러 (18.0 로 조용히 폴백 금지 — codex concern 2).
    """
    if cli_fps is not None:
        return float(cli_fps)
    kp = doc.get("keypointReport")
    if isinstance(kp, dict) and kp.get("fps"):
        return float(kp["fps"])
    raise RuntimeError(
        f"candidate {motion_id}: fps 를 결정할 수 없음 — candidate keypointReport.fps 부재 "
        f"AND --target-fps 미지정 (REFERENCE_TARGET_FPS 하드코딩 폴백 제거됨)."
    )


def _merge_into_candidate(
    firestore_admin, motion_id: str, version: str, fields: dict
) -> None:
    """파생 필드를 candidate 버전 문서에 MERGE (top-level/activeVersion 무접촉).

    검증은 firestore_admin 의 scoped validator 재사용:
      · meanAngles / techniqueProfile / bodyNormalizationProfile → flat-no-nested-array.
      · forceDirectionPattern → scoped force-pattern validator (findings[].warnings 허용).
      · keypointReport / referenceKeypointReport → scoped keypoint-report validator.
      · bodyComparisonSourcePose → flat-no-nested-array.
    """
    firestore_admin._validate_flat_dict_no_nested_array(
        fields["meanAngles"], path="meanAngles"
    )
    firestore_admin._validate_flat_dict_no_nested_array(
        fields["techniqueProfile"], path="techniqueProfile"
    )
    firestore_admin._validate_flat_dict_no_nested_array(
        fields["bodyNormalizationProfile"], path="bodyNormalizationProfile"
    )
    firestore_admin._validate_force_pattern_inference(
        fields["forceDirectionPattern"], path="forceDirectionPattern"
    )
    firestore_admin._validate_keypoint_report(
        fields["keypointReport"], path="keypointReport"
    )
    firestore_admin._validate_keypoint_report(
        fields["referenceKeypointReport"], path="referenceKeypointReport"
    )
    firestore_admin._validate_flat_dict_no_nested_array(
        fields["bodyComparisonSourcePose"], path="bodyComparisonSourcePose"
    )

    now_ms = int(time.time() * 1000)
    payload: dict = {}
    for k, v in fields.items():
        payload[k] = v
        payload[f"{k}UpdatedAt"] = now_ms
    payload["downstreamBackfillVersion"] = "phase33-cm3-04"
    payload["downstreamBackfilledAt"] = now_ms

    path = _VERSIONS_SUBPATH.format(motion_id=motion_id, version=version)
    firestore_admin._doc(path).set(payload, merge=True)
    log.info(
        "merge into candidate ok motion_id=%s version=%s body_conf=%s force_findings=%d "
        "keypointReport.fps=%s",
        motion_id,
        version,
        fields["bodyNormalizationProfile"].get("confidence"),
        len(fields["forceDirectionPattern"].get("findings") or []),
        fields["keypointReport"].get("fps"),
    )


def _mean_angles_summary(mean_angles: dict) -> dict:
    """meanAngles 를 dump 용 요약 (전 관절 값이 아니라 통계 + 유한 개수)."""
    vals = [v for v in mean_angles.values() if isinstance(v, (int, float))]
    if not vals:
        return {"count": 0, "finite": 0}
    arr = np.asarray(vals, dtype=float)
    return {
        "count": len(mean_angles),
        "finite": int(np.isfinite(arr).sum()),
        "min": round(float(np.nanmin(arr)), 3),
        "max": round(float(np.nanmax(arr)), 3),
        "mean": round(float(np.nanmean(arr)), 3),
    }


# ── full backfill path (candidate source → derive → merge) ──────────────────
def _process_one(
    motion_id: str,
    video_path: Path,
    extractor,
    rtmw_engine,
    candidate_angles: np.ndarray,
    candidate_hash: str,
    target_fps: float,
) -> tuple[dict, dict]:
    """단일 motion candidate 백필 → (mergeFields[id], diagnostics[id]).

    B(live frames) → C(angle integrity gate vs candidate) → D(compute) →
    E(source_pose + keypoint reports). angle gate 발산 시 RuntimeError (caller 중단, R1).
    """
    from sunity_shared.analysis.assemble import build_keypoint_report
    from sunity_shared.analysis.features import (
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.pole_geometry import (
        build_pole_axis_measurement,
    )
    from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array
    from sunity_shared.analysis.temporal import temporal_fill

    # bodyComparisonSourcePose 실존 producer 재사용 (codex — concrete producer 명시).
    # extract_reference_body_profiles._build_source_pose: 대표 frame = 평균 keypoint
    # confidence 최대 → to_coco17_array 단일 frame 슬라이스 (17×4 flat, torso_px).
    import extract_reference_body_profiles as erbp

    t0 = time.time()

    # (B) LIVE FRAMES — vertical-fallback PoleAxis + RTMW estimate (D-02 hybrid).
    # PR_INVERSION_ENABLED=1 env 하에서 RTMWPoseEngine 이 인버전 보정을 내부 적용 →
    # candidate(PR-on) 와 동일 기질. target_fps 는 candidate 와 일치 (기질 정합).
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
    #     source 가 아니다 (그건 candidate angles). ONE temporal_fill (double-smooth 금지).
    kp = to_coco17_array(pose_frames)
    rerun_angles = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))
    rerun_frames = int(rerun_angles.shape[0])
    if rerun_frames != len(pose_frames):
        raise RuntimeError(
            f"[{motion_id}] frame-alignment 실패 — rerun angles frames={rerun_frames} "
            f"!= len(pose_frames)={len(pose_frames)}"
        )
    if candidate_angles.shape[0] != rerun_angles.shape[0]:
        raise RuntimeError(
            f"[{motion_id}] candidate vs rerun frame 수 불일치 — pose-version 재검증 필요 "
            f"(candidate T={candidate_angles.shape[0]} rerun T={rerun_angles.shape[0]}). "
            f"target_fps={target_fps} 가 candidate 추출 fps 와 다를 수 있음."
        )
    diff = np.abs(candidate_angles - rerun_angles)
    # NaN-coverage 게이트 — joint column 단위 NaN-coverage divergence 차단.
    comparable = np.isfinite(diff)
    coverage = float(comparable.mean()) if diff.size else 1.0
    if coverage < 0.95:
        raise RuntimeError(
            f"[{motion_id}] angle gate — NaN coverage {coverage:.2%} < 95%, "
            f"pose-version 재검증 필요 (candidate/rerun NaN 위치 divergence)."
        )
    max_delta = float(np.nanmax(diff)) if diff.size else 0.0
    mean_delta = float(np.nanmean(diff)) if diff.size else 0.0
    p99_delta = float(np.nanpercentile(diff, 99)) if diff.size else 0.0
    rerun_hash = _sha256_angles(rerun_angles)
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
            f"[{motion_id}] candidate-vs-rerun angle gate 실패 — meanAngleDelta={mean_delta:.4f} "
            f"(>{MEAN_EPSILON_DEG}) 또는 p99AngleDelta={p99_delta:.3f} (>{P99_EPSILON_DEG}); "
            f"maxAngleDelta={max_delta:.3f} (참고). 임계 재fit 금지 (D-29) — 원인 조사. "
            f"pose-version 재검증 문제 — derived-field 백필 X, 전체 real seed 중단 (R1)."
        )

    # (D) COMPUTE — REFERENCE_V1_FORCE_CONFIG, candidate angles + 주입 pole_meas.
    result = compute_reference_downstream(
        pose_frames,
        pole_axis_measurement=pole_meas,
        angles=candidate_angles,  # R1 — candidate 버전 angles, 재추론 아님.
        fps=target_fps,  # candidate 추출 fps 와 일치.
        motion_id=motion_id,
        mode_context="mode1",
        force_config=REFERENCE_V1_FORCE_CONFIG,
    )

    # (E-1) bodyComparisonSourcePose — 실존 producer 재사용.
    source_pose_dict, rep_idx, rep_conf = erbp._build_source_pose(pose_frames)
    if source_pose_dict is None:
        raise RuntimeError(
            f"[{motion_id}] bodyComparisonSourcePose 산출 실패 (대표 frame conf/torso/NaN). "
            f"11/11 필수 — 비교 화면 깨짐 (T-33-30). derived-field 백필 X."
        )

    # (E-2) keypointReport + referenceKeypointReport — build_keypoint_report(live, 9fps).
    #   candidate fps 라벨(9.0) 로 산출 — top-level 18fps 라벨과 결별 (codex concern 2).
    report = build_keypoint_report(pose_frames, fps=target_fps)
    if report is None:
        raise RuntimeError(
            f"[{motion_id}] build_keypoint_report 반환 None — keypoints_2d 부재"
        )
    keypoint_report = _keypoint_report_to_camel(report)

    seed = result.seed_payload()
    merge_fields = {
        "meanAngles": seed["meanAngles"],
        "techniqueProfile": seed["techniqueProfile"],
        "bodyNormalizationProfile": seed["bodyNormalizationProfile"],
        "forceDirectionPattern": seed["forceDirectionPattern"],
        "captureViews": seed["captureViews"],
        "bodyComparisonSourcePose": source_pose_dict,
        "keypointReport": keypoint_report,
        # referenceKeypointReport (mode1 앱 소비 필드) — 동일 live 산출.
        "referenceKeypointReport": dict(keypoint_report),
    }

    diag = dict(result.diagnostics)
    diag.update(
        {
            "candidateAnglesHash": candidate_hash,
            "rerunAnglesHash": rerun_hash,
            "anglesFrames": rerun_frames,
            "targetFps": target_fps,
            "maxAngleDelta": max_delta,
            "meanAngleDelta": mean_delta,
            "p99AngleDelta": p99_delta,
            "sourcePoseRepFrame": rep_idx,
            "sourcePoseConfidence": rep_conf,
            "keypointReportFps": keypoint_report.get("fps"),
            "keypointReportFrames": keypoint_report.get("frames"),
        }
    )

    log.info(
        "[%s] frames=%d body_conf=%s keypointReport.fps=%s meanAngleDelta=%.4f p99=%.3f %.1fs",
        motion_id,
        len(pose_frames),
        merge_fields["bodyNormalizationProfile"].get("confidence"),
        keypoint_report.get("fps"),
        mean_delta,
        p99_delta,
        time.time() - t0,
    )
    return merge_fields, diag


def _has_nan_or_inf(obj) -> bool:
    """merge fields 내부에 NaN/inf scalar 가 있으면 True (all-or-nothing)."""
    # np.float32 등 float-비서브클래스 numpy scalar 도 명시 포함.
    if isinstance(obj, (float, np.floating)):
        return not math.isfinite(float(obj))
    if isinstance(obj, dict):
        return any(_has_nan_or_inf(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return any(_has_nan_or_inf(v) for v in obj)
    return False


def _dump_entry(motion_id: str, merge_fields: dict, diag: dict) -> dict:
    """per-candidate-doc VALUE dump (D-19 — 열어서 확인 가능한 산출)."""
    bnp = merge_fields["bodyNormalizationProfile"]
    fdp = merge_fields["forceDirectionPattern"]
    kp = merge_fields["keypointReport"]
    tp = merge_fields["techniqueProfile"]
    sp = merge_fields["bodyComparisonSourcePose"]
    return {
        "meanAnglesSummary": _mean_angles_summary(merge_fields["meanAngles"]),
        "techniqueProfile": {
            "name": tp.get("name"),
            "category": tp.get("category"),
            "jointExpectationsCount": len(tp.get("jointExpectations") or {}),
        },
        "bodyNormalizationProfile": {
            "confidence": bnp.get("confidence"),
            "estimatedHeightScale": bnp.get("estimatedHeightScale"),
            "shoulderHipRatio": bnp.get("shoulderHipRatio"),
            "nonNaN": not _has_nan_or_inf(bnp),
        },
        "forceDirectionPattern": {
            "findings": len(fdp.get("findings") or []),
            "warnings": len(fdp.get("warnings") or []),
        },
        "keypointReportFps": kp.get("fps"),
        "keypointReportFrames": kp.get("frames"),
        "referenceKeypointReportPresent": (
            merge_fields.get("referenceKeypointReport") is not None
        ),
        "bodyComparisonSourcePosePresent": sp is not None,
        "bodyComparisonSourcePoseValuesLen": len(sp.get("values") or []),
        "bodyComparisonSourcePoseConfidence": sp.get("confidence"),
        "meanAngleDelta": diag.get("meanAngleDelta"),
        "p99AngleDelta": diag.get("p99AngleDelta"),
        "maxAngleDelta": diag.get("maxAngleDelta"),
        "candidateAnglesHash": diag.get("candidateAnglesHash"),
        "rerunAnglesHash": diag.get("rerunAnglesHash"),
    }


def _run_backfill(args, motion_ids: list[str]) -> int:
    """candidate 백필 path — candidate read → S3 → RTMW → gate → merge into candidate."""
    if not args.reference_version:
        log.error("candidate 백필에는 --reference-version 필요 (예: phase33-cm3-run1).")
        return 2

    # 헤비 의존 fail-fast 체크.
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

    version = args.reference_version
    s3 = _boto3.client("s3", region_name=region)
    rtmw_engine = RTMWPoseEngine()

    write = bool(args.write_candidate) and not args.dry_run
    log.info(
        "candidate backfill start version=%s motions=%d mode=%s (AWS region=%s)",
        version,
        len(motion_ids),
        "dry-run" if not write else "real-run (merge into candidate)",
        region,
    )

    merged: dict[str, dict] = {}
    diagnostics: dict[str, dict] = {}
    dump: dict[str, dict] = {}
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for motion_id in motion_ids:
            log.info("--- %s ---", motion_id)
            try:
                # (A) CANDIDATE READ — angles/keypointReport (top-level 미접촉).
                cand_doc = _read_candidate_doc(firestore_admin, motion_id, version)
                cand_angles, cand_hash = _candidate_angles(cand_doc, motion_id)
                target_fps = _resolve_target_fps(cand_doc, args.target_fps, motion_id)
                extractor = FfmpegFrameExtractor(target_fps=target_fps)

                video_path = td_path / f"{motion_id}.mp4"
                key = f"reference/{motion_id}.mp4"
                log.info(
                    "S3 download s3://%s/%s (fps=%.4g)", args.bucket, key, target_fps
                )
                s3.download_file(args.bucket, key, str(video_path))

                merge_fields, diag = _process_one(
                    motion_id,
                    video_path,
                    extractor,
                    rtmw_engine,
                    cand_angles,
                    cand_hash,
                    target_fps,
                )
                merged[motion_id] = merge_fields
                diagnostics[motion_id] = diag
                dump[motion_id] = _dump_entry(motion_id, merge_fields, diag)
            except Exception:  # noqa: BLE001 — per-motion 격리, exit 은 all-or-nothing.
                log.error("[%s] FAIL — %s", motion_id, traceback.format_exc())
                failures.append(motion_id)

    # ── all-or-nothing gate ────────────────────────────────────────────────
    nan_inf = any(_has_nan_or_inf(v) for v in merged.values())
    gate_failed = (
        len(failures) > 0
        or len(merged) != len(motion_ids)
        or nan_inf
    )

    artifact = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "referenceVersion": version,
        "epsilons": {
            "meanEpsilonDeg": MEAN_EPSILON_DEG,
            "p99EpsilonDeg": P99_EPSILON_DEG,
        },
        "perCandidateDump": dump,
        "diagnostics": diagnostics,
        "failures": failures,
    }

    # per-candidate dump 는 항상 stdout (D-19 — 열어보는 산출).
    print(json.dumps(artifact, ensure_ascii=False, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
        log.info("artifact → %s (%.1f KB)", args.output, args.output.stat().st_size / 1024)

    if gate_failed:
        log.error(
            "all-or-nothing gate 실패 — failures=%d len(merged)=%d (need %d) nan_inf=%s. "
            "candidate MERGE 미실행.",
            len(failures),
            len(merged),
            len(motion_ids),
            nan_inf,
        )
        return 1

    if not write:
        log.info(
            "dry-run 완료 — %d/%d motion candidate 파생 산출 (Firestore write 0). "
            "--write-candidate 로 candidate 버전 문서에 MERGE.",
            len(merged),
            len(motion_ids),
        )
        return 0

    # gate 통과 + --write-candidate → candidate 버전 문서에 MERGE.
    for motion_id in motion_ids:
        _merge_into_candidate(
            firestore_admin, motion_id, version, merged[motion_id]
        )
    log.info(
        "real-run 완료 — %d/%d motion candidate versions/%s 에 MERGE (top-level/activeVersion 무접촉).",
        len(merged),
        len(motion_ids),
        version,
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "정은지 reference 11개의 downstream 필드 candidate-aware 백필 orchestrator. "
            "candidate 버전(reference/{id}/versions/{v}) 에서 read + merge. Pod GPU 직접 실행."
        )
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="S3 bucket (예: sunity-motion-pilot-videos). candidate 백필에 필요.",
    )
    parser.add_argument(
        "--reference-version",
        default=None,
        help=(
            "source AND merge target candidate 버전 id (예: phase33-cm3-run1). "
            "top-level/activeVersion 은 절대 미접촉 (flip 은 33-07)."
        ),
    )
    parser.add_argument(
        "--target-fps",
        default=None,
        type=float,
        help=(
            "추출 fps override. 미지정 시 candidate keypointReport.fps 에서 읽는다 "
            "(REFERENCE_TARGET_FPS=18.0 하드코딩 폴백 제거됨 — codex concern 2)."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        type=Path,
        help="산출 artifact JSON 출력 경로 (예: /workspace/reference-downstream-backfill.json)",
    )
    parser.add_argument(
        "--motions",
        default=None,
        help=(
            "쉼표 분리 motion id list. 미지정 시 11-union 전체 (Pitfall 1 — 절대 5-subset "
            "default 금지)."
        ),
    )
    parser.add_argument(
        "--check-firestore",
        action="store_true",
        help=(
            "credential + completeness gate. NEVER S3/RTMW. 요청 motion 전부 "
            "activeVersion+angles+anglesJointKeys+anglesFrames + frame-count sanity 검사 후 exit."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="candidate 파생 산출 + dump stdout, Firestore MERGE 미실행.",
    )
    parser.add_argument(
        "--write-candidate",
        action="store_true",
        help=(
            "gate 통과 시 candidate 버전 문서(reference/{id}/versions/{v}) 에 파생 필드 MERGE. "
            "top-level / activeVersion 은 절대 미접촉."
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
        log.error("candidate 백필에는 --bucket 필요 (또는 --check-firestore).")
        sys.exit(2)
    sys.exit(_run_backfill(args, motion_ids))


if __name__ == "__main__":
    main()
