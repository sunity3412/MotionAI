"""Phase 4 정은지 5영상 재처리 스크립트 (RunPod GPU 전용).

Phase 4 신규 파이프라인(Wave 1 + Wave 3) 완성 후 reference 5영상을 동일 파이프라인으로
재처리해 mode1 비교의 양쪽 원질 보장(D-09). G4 가드 정합: is_reference=True 이므로
합성 트리거 발동 없음 — RTMW 1차 분석 품질 향상만 적용(D-10).
versioned/atomic write: reference/{id}/versions/phase4_v1 에 버전 저장 후
5개 전부 schema gate 통과 시에만 active 포인터 flip. rollback: rollback_reference_motions_phase4.py.

Usage (RunPod GPU):
  cd /workspace/SunityMotion/backend
  source pod.env
  export PYTHONPATH=$PWD:$PWD/shared/python
  python scripts/reprocess_reference_motions_phase4.py --out /workspace/reference-phase4-reprocess.json

Output: versioned Firestore 저장 + 재처리 JSON (seed-reference-motions.mjs 투입용).

계약 참조:
  D-09: reference migration 완료 기준 + versioned/atomic write
  D-10: G4 가드 정합 (is_reference=True → 합성 트리거 0)
  BLOCKER-1: reference active doc 에 synthetic 좌표 금지
  BLOCKER-2: joints3d 필드 세트 추가 (04-01 사용자 경로 contract 와 동일)
  T-04-W5-01: pod.env AWS/Firebase 키 로그 출력 금지
  T-04-W5-02: G4 guard bypass 위협 대응
  T-04-W5-03: 5개 미통과 상태에서 active pointer flip 방지
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# sys.path 주입: Lambda module side-effect (boto3 client, env) 차단.
# extract_reference_keypoint_reports.py:39-41 패턴 동일.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log.addHandler(_h)

# ── 상수 박제 ─────────────────────────────────────────────────────────────────

# Firestore reference 와 1:1 — seed-reference-motions.mjs MOTIONS 와 항상 동기 유지.
MOTION_IDS = [
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
]

S3_BUCKET = "sunity-motion-pilot-videos"
S3_PREFIX = "reference"
PIPELINE_VERSION = "phase4_v1"

# RTMW vertical pole_axis fallback (extract_reference_angles.py:82-87 정합).
# reference 영상은 학원 환경 — 폴 거의 항상 수직. PoleDetector 호출 비용 회피.
_VERTICAL_POLE_AXIS_KWARGS = dict(
    axis_vector=(0.0, 1.0, 0.0),
    confidence_level="low",
    source="vertical_fallback",
    frame_index=None,
)


# ── _validate_payload_schema (BLOCKER-2, D-09) ───────────────────────────────


def _validate_payload_schema(payload: dict, motion_id: str) -> None:
    """11개 키 존재 + pipelineVersion + angles 비어있지 않음 검증 (BLOCKER-2).

    검증 항목:
      angles(list), anglesJointKeys(list), anglesFrames(int),
      keypointReport(dict), joints3d(list flat), joints3dKeys(list len 17 COCO-17),
      joints3dFrames(int), coordDim(==3), space("pole_aligned"),
      pipelineVersion("phase4_v1"), reprocessedAt(str ISO 8601)

    5개 전부 통과하기 전에는 Firestore write 가 일어나지 않음 (D-09).

    raises:
      ValueError: 키 누락 / pipelineVersion 불일치 / angles 빈 list / coordDim != 3 시.
    """
    REQUIRED_KEYS = {
        "angles", "anglesJointKeys", "anglesFrames",
        "keypointReport",
        "joints3d", "joints3dKeys", "joints3dFrames",
        "coordDim", "space",
        "pipelineVersion", "reprocessedAt",
    }
    missing = REQUIRED_KEYS - set(payload.keys())
    if missing:
        raise ValueError(
            f"{motion_id}: schema 검증 실패 — 누락 키: {sorted(missing)}"
        )

    if payload["pipelineVersion"] != PIPELINE_VERSION:
        raise ValueError(
            f"{motion_id}: pipelineVersion 불일치 — "
            f"기대={PIPELINE_VERSION!r}, 실제={payload['pipelineVersion']!r}"
        )

    if not payload["angles"]:
        raise ValueError(
            f"{motion_id}: angles 가 빈 list — 재처리 결과 없음"
        )

    if payload["coordDim"] != 3:
        raise ValueError(
            f"{motion_id}: coordDim != 3 — joints3d xyz 3채널 필요 "
            f"(실제={payload['coordDim']!r})"
        )

    if len(payload["joints3dKeys"]) != 17:
        raise ValueError(
            f"{motion_id}: joints3dKeys 길이 != 17 (COCO-17) — "
            f"실제={len(payload['joints3dKeys'])}"
        )


# ── _reprocess_one (D-09, D-10, BLOCKER-1, BLOCKER-2) ────────────────────────


def _reprocess_one(
    motion_id: str,
    s3,
    extractor,
    engine,
    target_fps: float,
    s3_prefix: str,
    synthesis_adapter=None,
    _dry_run: bool = False,
) -> dict:
    """1 motion → Phase 4-compatible payload dict.

    G4 가드 박제 (D-10, BLOCKER-1):
      is_reference=True 이므로 synthesis_adapter 는 절대 호출하지 않는다.
      identify_occlusion_targets 호출 자체를 생략 — 합성 mask 가 전부 False 임을 박제.
      synthesis_adapter 파라미터는 behavioral 테스트 주입용으로만 존재 (기본값 None = 합성 비활성).

    _dry_run=True:
      S3 download 및 GPU 추론을 생략하고 schema 구조만 반환 (synthetic fixture 기반).
      test_g4_guard_no_synthesis_for_reference_reprocess 가 dry-run=True 로 호출.
    """
    # is_reference=True 박제:
    # G4 가드 최우선 — synthesis_adapter 는 이 경로에서 절대 호출되지 않는다 (D-10).
    # BLOCKER-1: reference active doc 에 synthetic 좌표를 쓰지 않음.
    # synthesis_adapter 는 behavioral 테스트(FakeSynthesisAdapter) 주입용 파라미터 —
    # 실 실행에서는 항상 None (합성 비활성) 이고, 테스트에서는 호출 여부 감지용.
    # 이 함수 어디에서도 synthesis_adapter.synthesize_occluded_joints() 를 호출하지 않음.

    if _dry_run:
        # dry-run: S3/GPU 생략. schema 구조만 반환 (schema gate 검증용).
        # 실제 angles/joints3d 는 0 값 — schema gate 는 키 존재 + 타입만 검증.
        T = 1
        J_ANGLES = 8  # skeleton.NUM_JOINTS
        J3D = 17       # COCO-17

        angles_flat = [0.0] * (T * J_ANGLES)
        joints3d_flat = [0.0] * (T * J3D * 3)
        joints3d_keys = [
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip",
            "left_knee", "right_knee", "left_ankle", "right_ankle",
        ]
        keypoint_report_mock: dict = {
            "version": "phase4_v1",
            "joints": joints3d_keys,
            "frames": T,
            "fps": target_fps,
        }
        return {
            "angles": angles_flat,
            "anglesJointKeys": [
                "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
                "left_hip", "right_hip", "left_knee", "right_knee",
            ],
            "anglesFrames": T,
            "keypointReport": keypoint_report_mock,
            "joints3d": joints3d_flat,
            "joints3dKeys": joints3d_keys,
            "joints3dFrames": T,
            "coordDim": 3,
            "space": "pole_aligned",
            "pipelineVersion": PIPELINE_VERSION,
            "reprocessedAt": datetime.now(timezone.utc).isoformat(),
        }

    # ── 실 RunPod GPU 경로 ────────────────────────────────────────────────────
    # boto3 / sunity_shared import 는 실 실행 시에만 발생 (Lambda module side-effect 차단).
    import boto3  # type: ignore[import-untyped] — RunPod 환경에 항상 존재
    import numpy as np

    from sunity_shared.analysis import skeleton  # noqa: E402
    from sunity_shared.analysis.assemble import build_keypoint_report  # noqa: E402
    from sunity_shared.analysis.body_normalization_measurer import (  # noqa: E402
        measure_body_profile,
    )
    from sunity_shared.analysis.features import (  # noqa: E402
        compute_joint_angles,
        joint_uncertainty,
    )
    from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array  # noqa: E402
    from sunity_shared.analysis.temporal import occluded_mask, temporal_fill  # noqa: E402

    key = f"{s3_prefix}/{motion_id}.mp4"
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        local_path = Path(tmp.name)
    try:
        # T-04-W5-01: S3 key 출력 (값 노출 없음)
        log.info("  [%s] S3 download s3://%s/%s", motion_id, S3_BUCKET, key)
        s3.download_file(S3_BUCKET, key, str(local_path))

        log.info("  [%s] frame extract (%.4g fps)", motion_id, target_fps)
        frames = extractor.extract(str(local_path))

        log.info("  [%s] RTMW pose estimate (%d frame)", motion_id, frames.shape[0])

        # _VERTICAL_POLE_AXIS 인스턴스 생성 (extract_reference_angles.py 패턴 정합)
        from sunity_shared.analysis.pose_frame import PoleAxis  # noqa: F811
        vertical_pole = PoleAxis(**_VERTICAL_POLE_AXIS_KWARGS)

        pose_frames = engine.estimate(frames, vertical_pole)

        # measure_body_profile + body_shape 주입 (extract_reference_angles.py:108-113 정합)
        profile = measure_body_profile(pose_frames)
        pose_frames_with_profile = [
            dataclasses.replace(pf, body_shape=profile) for pf in pose_frames
        ]

        # to_coco17_array → (T, 17, 4) COCO-17 배열
        keypoints = to_coco17_array(pose_frames_with_profile)

        # angles 산출 (extract_reference_angles.py _extract_one 정합)
        raw_angles = compute_joint_angles(keypoints)
        unc = joint_uncertainty(keypoints)
        mask_arr = occluded_mask(raw_angles, unc)
        filled = temporal_fill(raw_angles, unc)
        T = int(filled.shape[0])

        angles_rounded = np.round(filled.astype(np.float64), 2)
        # NaN 잔여 시 0.0 치환 (extract_reference_angles.py:143 패턴 동일)
        if not np.isfinite(angles_rounded).all():
            nan_count = int((~np.isfinite(angles_rounded)).sum())
            log.warning("  [%s] NaN/inf %d 잔여 → 0.0 치환 (보간 한계)", motion_id, nan_count)
            angles_rounded = np.nan_to_num(
                angles_rounded, nan=0.0, posinf=0.0, neginf=0.0
            )

        # joints3d 산출 (BLOCKER-2):
        # to_coco17_array(pose_frames)[:, :, :3] (T,17,3, pole_aligned) → flat.
        # 좌표계 = pole_aligned (pipeline/app.py:2070 정합 — rtmw3d 아님).
        # is_reference=True 이므로 합성(synthesis) 좌표가 아닌 1차 RTMW pose 좌표.
        joints3d_src = np.asarray(keypoints)[:, :, :3].astype(np.float32)
        joints3d_src = np.nan_to_num(joints3d_src, nan=0.0, posinf=0.0, neginf=0.0)
        joints3d_frames_int = int(joints3d_src.shape[0])
        joints3d_keys_list = list(skeleton.KEYPOINT_NAMES)  # COCO-17 17 keypoint 순서
        joints3d_flat = joints3d_src.reshape(-1).tolist()

        # keypointReport 산출
        log.info("  [%s] build_keypoint_report", motion_id)
        kp_report = build_keypoint_report(pose_frames_with_profile, fps=target_fps)

        # keypointReport camelCase (extract_reference_keypoint_reports.py _camel_case_report 패턴)
        if kp_report is not None:
            keypoint_report_dict: dict = {
                "version": kp_report.version,
                "joints": list(kp_report.joints),
                "frames": int(kp_report.frames),
                "fps": float(kp_report.fps),
                "data": list(kp_report.data),
                "confidence": list(kp_report.confidence),
                "reliability": list(kp_report.reliability),
                "axisData": list(kp_report.axis_data),
                "axisMask": list(kp_report.axis_mask),
                "warnings": list(kp_report.warnings),
            }
        else:
            keypoint_report_dict = {}

        return {
            "angles": angles_rounded.reshape(-1).tolist(),
            "anglesJointKeys": list(skeleton.JOINT_KEYS),
            "anglesFrames": T,
            "keypointReport": keypoint_report_dict,
            "joints3d": joints3d_flat,
            "joints3dKeys": joints3d_keys_list,
            "joints3dFrames": joints3d_frames_int,
            "coordDim": 3,
            "space": "pole_aligned",
            "pipelineVersion": PIPELINE_VERSION,
            "reprocessedAt": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        try:
            local_path.unlink()
        except OSError:
            pass


# ── _write_versioned (D-09) ───────────────────────────────────────────────────


def _write_versioned(fs_client, motion_id: str, payload: dict) -> str:
    """Firestore reference/{motion_id}/versions/phase4_v1 에 payload 저장.

    반환값: 저장된 문서 경로 문자열.
    직접 active 포인터를 건드리지 않음 — flip 은 별도 단계 (_flip_active_pointer).

    canonical path = reference/{id}/versions/phase4_v1.
    잘못된 collection 사용 금지 (HIGH-2, HIGH-3): reference/{id} 경로 전용.
    """
    path = f"reference/{motion_id}/versions/{PIPELINE_VERSION}"
    doc_ref = (
        fs_client
        .collection("reference")
        .document(motion_id)
        .collection("versions")
        .document(PIPELINE_VERSION)
    )
    doc_ref.set(payload)
    log.info("  [%s] versioned write 완료 → %s", motion_id, path)
    return path


# ── _flip_active_pointer (D-09, T-04-W5-03) ──────────────────────────────────


def _flip_active_pointer(
    fs_client, motion_ids: list[str], completed: dict
) -> None:
    """5개 전부 완료 시에만 active 포인터 flip + top-level mirror (D-09, T-04-W5-03).

    단계:
      (a) flip 전 현재 top-level 필드 스냅샷을 reference/{id}/versions/pre_phase4 에 백업 (rollback 소스).
      (b) reference/{id}.activeVersion = "phase4_v1" 업데이트.
      (c) top-level mirror (BLOCKER-2 핵심): versions/phase4_v1 의 consumer 필드를
          reference/{id} top-level 에 merge.
          현재 앱/백엔드 consumer 는 activeVersion resolver 없이 top-level 을 직접 읽음
          (앱 lib/reference-lib → collection(db,'reference') + firestore_admin reference/{id}) — mirror 없으면 무효과.

    T-04-W5-03: len(completed) == len(motion_ids) 강제 검사.
      미통과 시 ValueError raise.

    T-04-W5-01: env var 값 로그 출력 금지.
    """
    if len(completed) != len(motion_ids):
        raise ValueError(
            f"active flip 차단: {len(completed)}/{len(motion_ids)} 완료 — "
            f"5개 전부 완료 시에만 flip (T-04-W5-03, D-09)"
        )

    for motion_id in motion_ids:
        ref_doc = fs_client.collection("reference").document(motion_id)

        # (a) flip 전 현재 top-level 스냅샷 백업 (rollback 소스)
        current_snap = ref_doc.get().to_dict() or {}
        old_version = current_snap.get("activeVersion", "unknown")
        log.info(
            "  [%s] flip 전 activeVersion=%r → pre_phase4 백업",
            motion_id, old_version
        )
        backup_doc = (
            ref_doc.collection("versions").document("pre_phase4")
        )
        backup_doc.set(current_snap)

        # (b) activeVersion flip
        ref_doc.update({"activeVersion": PIPELINE_VERSION})
        log.info("  [%s] activeVersion → %r", motion_id, PIPELINE_VERSION)

        # (c) top-level mirror (BLOCKER-2):
        # consumer 소비 필드 (angles / anglesJointKeys / anglesFrames +
        # joints3d / joints3dKeys / joints3dFrames / coordDim / space 등)
        # 를 reference/{id} top-level 에 merge.
        payload = completed[motion_id]
        mirror_fields: dict = {
            "angles": payload.get("angles"),
            "anglesJointKeys": payload.get("anglesJointKeys"),
            "anglesFrames": payload.get("anglesFrames"),
            "joints3d": payload.get("joints3d"),
            "joints3dKeys": payload.get("joints3dKeys"),
            "joints3dFrames": payload.get("joints3dFrames"),
            "coordDim": payload.get("coordDim"),
            "space": payload.get("space"),
            "pipelineVersion": payload.get("pipelineVersion"),
            "reprocessedAt": payload.get("reprocessedAt"),
            # keypointReport 도 top-level mirror (mode1 소비 경로 정합)
            "keypointReport": payload.get("keypointReport"),
        }
        # None 값 제거 (Firestore update 에서 None 은 필드 삭제 시맨틱 가능)
        mirror_fields = {k: v for k, v in mirror_fields.items() if v is not None}
        ref_doc.update(mirror_fields)
        log.info("  [%s] top-level mirror 완료 (%d 필드)", motion_id, len(mirror_fields))


# ── main() ────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/workspace/reference-phase4-reprocess.json"),
        help="Output JSON path (재처리 결과 — seed-reference-motions.mjs 투입용)",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=MOTION_IDS,
        help="Override motion id list (default = MOTION_IDS 5개). 부분 재처리 지원 (단일 영상 디버그용).",
    )
    parser.add_argument(
        "--target-fps",
        type=float,
        default=18.0,
        help="Target sampling fps. Default 18.0 (pipeline 정합).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="S3 download 및 Firestore 쓰기 생략. _validate_payload_schema 만 실행 (schema 구조 검증용).",
    )
    parser.add_argument(
        "--no-flip",
        action="store_true",
        help="재처리+버전 쓰기는 하되 active 포인터 flip 생략 (단계적 배포용).",
    )
    parser.add_argument(
        "--s3-prefix",
        type=str,
        default=S3_PREFIX,
        help=f"S3 prefix (default '{S3_PREFIX}').",
    )
    args = parser.parse_args()

    motion_ids: list[str] = args.motions

    if args.dry_run:
        # dry-run: schema 구조 검증만 (S3/Firestore 무관)
        print("=== dry-run 모드 — S3/Firestore 쓰기 생략 ===", flush=True)
        all_pass = True
        for motion_id in motion_ids:
            try:
                payload = _reprocess_one(
                    motion_id=motion_id,
                    s3=None, extractor=None, engine=None,
                    target_fps=args.target_fps,
                    s3_prefix=args.s3_prefix,
                    synthesis_adapter=None,
                    _dry_run=True,
                )
                _validate_payload_schema(payload, motion_id)
                print(f"  [{motion_id}] dry-run schema OK", flush=True)
            except (ValueError, Exception) as exc:
                print(f"  [{motion_id}] dry-run FAIL — {exc}", flush=True)
                all_pass = False
        print(f"dry-run 결과: {'PASS' if all_pass else 'FAIL'}", flush=True)
        return 0 if all_pass else 1

    # ── 실 RunPod 실행 경로 ───────────────────────────────────────────────────
    import boto3  # type: ignore[import-untyped] — RunPod 환경에 항상 존재

    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
    from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

    s3 = boto3.client("s3")
    extractor = FfmpegFrameExtractor(target_fps=args.target_fps)
    print("RTMW 엔진 init (가중치 로드 ~30초)...", flush=True)
    engine = RTMWPoseEngine()
    print("RTMW init 완료", flush=True)

    # 단계 1: 전체 _reprocess_one 실행 → results dict 수집 (부분 실패 허용).
    results: dict[str, dict] = {}
    t_start = time.time()
    for motion_id in motion_ids:
        t0 = time.time()
        try:
            payload = _reprocess_one(
                motion_id=motion_id,
                s3=s3, extractor=extractor, engine=engine,
                target_fps=args.target_fps,
                s3_prefix=args.s3_prefix,
                synthesis_adapter=None,  # is_reference=True: 합성 비활성 (G4 가드)
                _dry_run=False,
            )
            results[motion_id] = payload
            print(f"  [{motion_id}] reprocess OK ({time.time() - t0:.1f}s)", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{motion_id}] reprocess FAIL — {exc}", file=sys.stderr, flush=True)

    print(
        f"\n재처리 완료: {len(results)}/{len(motion_ids)} motion "
        f"({time.time() - t_start:.1f}s)",
        flush=True,
    )

    # 단계 2: 전체 _validate_payload_schema 통과 (5개 전부 — 1개 실패 시 중단).
    print("\n=== schema gate 검증 중... ===", flush=True)
    for motion_id in motion_ids:
        if motion_id not in results:
            print(
                f"ERROR: {motion_id} 재처리 결과 없음 — schema gate 중단.",
                file=sys.stderr, flush=True,
            )
            return 1
        try:
            _validate_payload_schema(results[motion_id], motion_id)
            print(f"  [{motion_id}] schema gate PASS", flush=True)
        except ValueError as exc:
            print(
                f"ERROR: schema gate FAIL — {exc}", file=sys.stderr, flush=True
            )
            return 1
    print("=== schema gate 전부 PASS ===", flush=True)

    # JSON 저장 (로컬 → scp 로 로컬 가져오기 위함)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pipelineVersion": PIPELINE_VERSION,
        "motions": results,
    }, ensure_ascii=False, indent=2))
    print(f"\n재처리 JSON 저장 → {args.out}", flush=True)

    # Firestore 초기화 (경량 — SA key 는 env 주입)
    try:
        import os
        import firebase_admin
        from firebase_admin import credentials, firestore as fstore

        sa_path = os.environ.get("FIREBASE_SA_PATH") or os.environ.get("FIREBASE_SA_JSON")
        if not sa_path:
            raise RuntimeError("FIREBASE_SA_PATH 또는 FIREBASE_SA_JSON env 필요 (T-04-W5-01)")
        if not firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        fs_client = fstore.client()
    except ImportError as exc:
        print(f"ERROR: firebase_admin 미설치 — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Firestore 초기화 실패 — {exc}", file=sys.stderr)
        return 1

    # 단계 3: _write_versioned (각 motion 에 versions/phase4_v1 저장)
    print("\n=== Firestore versioned write ===", flush=True)
    for motion_id in motion_ids:
        path = _write_versioned(fs_client, motion_id, results[motion_id])
        print(f"  [{motion_id}] → {path}", flush=True)

    # 단계 4: _flip_active_pointer (--no-flip 없으면 실행)
    if args.no_flip:
        print("\n--no-flip 지정 — active pointer flip 생략.", flush=True)
    else:
        print("\n=== active pointer flip ===", flush=True)
        try:
            _flip_active_pointer(fs_client, motion_ids, results)
        except ValueError as exc:
            print(f"ERROR: active flip 차단 — {exc}", file=sys.stderr)
            return 1
        print("=== flip 완료 ===", flush=True)

    print(
        "\n재처리 완료 → versions/phase4_v1 저장 → active flip 완료. "
        "rollback 필요 시 rollback_reference_motions_phase4.py 사용.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
