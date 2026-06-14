"""Phase 4 정은지 5영상 재처리 rollback 스크립트.

reprocess_reference_motions_phase4.py 가 active pointer 를 phase4_v1 로 flip 한 뒤
문제 발생 시 이전 버전으로 되돌리기 위해 사용.

Usage:
  cd /workspace/SunityMotion/backend
  source pod.env
  export PYTHONPATH=$PWD:$PWD/shared/python
  python scripts/rollback_reference_motions_phase4.py --to-version pre_phase4

계약 참조:
  D-09: versioned/atomic write + rollback 경로 존재
  T-04-W5-05: rollback 스크립트가 잘못된 버전으로 activeVersion flip 하는 위협 대응
  BLOCKER-2: top-level mirror 복원 — activeVersion 만 되돌리면 top-level mirror 가
             phase4 값으로 남아 consumer 가 여전히 새 값을 봄 (대칭 복원 필수)
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log.addHandler(_h)

# Firestore reference 와 1:1 — reprocess 스크립트와 항상 동기 유지.
MOTION_IDS = [
    "ref-sideway-spin",
    "ref-climb",
    "ref-invert",
    "ref-foxtop",
    "ref-foxtop-split",
]

# top-level mirror 복원 대상 필드 (flip 의 top-level mirror 와 동일 필드 세트, W3 정합)
_MIRROR_FIELDS = [
    "angles",
    "anglesJointKeys",
    "anglesFrames",
    "joints3d",
    "joints3dKeys",
    "joints3dFrames",
    "coordDim",
    "space",
    "pipelineVersion",
    "reprocessedAt",
    "keypointReport",
]


def _rollback_one(
    fs_client,
    motion_id: str,
    to_version: str,
) -> None:
    """1 motion — activeVersion flip + top-level mirror 복원 (D-09, BLOCKER-2).

    단계:
      (a) 현재 activeVersion + top-level 핵심 필드 출력 (사용자 확인용, T-04-W5-05).
      (b) reference/{motion_id}.activeVersion = to_version 업데이트.
      (c) top-level 복원: reference/{motion_id}/versions/{to_version} 의 consumer 필드
          를 reference/{motion_id} top-level 에 merge.

    T-04-W5-05: rollback 실행 전 현재 activeVersion 출력 → 사용자가 확인 가능하도록.
    BLOCKER-2: activeVersion 만 되돌리면 top-level mirror 가 phase4 값으로 남아
               consumer/3D viewer 가 여전히 새 값을 봄 — mirror 동기 필수.
    """
    ref_doc = fs_client.collection("reference").document(motion_id)

    # (a) 현재 상태 출력 (T-04-W5-05 — 사용자 확인용)
    current_snap = ref_doc.get().to_dict() or {}
    current_version = current_snap.get("activeVersion", "unknown")
    print(
        f"  [{motion_id}] 현재 activeVersion={current_version!r} → {to_version!r} 로 롤백",
        flush=True,
    )

    # (b) activeVersion flip
    ref_doc.update({"activeVersion": to_version})
    log.info("  [%s] activeVersion → %r", motion_id, to_version)

    # (c) top-level 복원 — versions/{to_version} 스냅샷에서 consumer 필드 복원 (BLOCKER-2)
    version_doc = ref_doc.collection("versions").document(to_version)
    version_snap = version_doc.get().to_dict() or {}

    if not version_snap:
        print(
            f"  [{motion_id}] 경고: versions/{to_version} 스냅샷 없음 — "
            f"top-level mirror 복원 생략 (pre_phase4 백업이 없을 경우 발생).",
            flush=True,
        )
        return

    # consumer 소비 필드만 top-level 에 merge (BLOCKER-2, W3 정합)
    restore_fields: dict = {
        k: version_snap[k]
        for k in _MIRROR_FIELDS
        if k in version_snap
    }

    if restore_fields:
        ref_doc.update(restore_fields)
        log.info(
            "  [%s] top-level mirror 복원 완료 (%d 필드)", motion_id, len(restore_fields)
        )
    else:
        print(
            f"  [{motion_id}] 경고: versions/{to_version} 에 복원할 필드 없음.",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--to-version",
        type=str,
        default="pre_phase4",
        help="롤백 대상 버전 (기본 'pre_phase4' — reprocess flip 전 스냅샷).",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=None,
        help="Override motion id list (기본 MOTION_IDS 전체 5개).",
    )
    args = parser.parse_args()

    motion_ids: list[str] = args.motions if args.motions else MOTION_IDS

    print(
        f"=== rollback 시작 — to_version={args.to_version!r} "
        f"/ motions={motion_ids} ===",
        flush=True,
    )

    # Firestore 초기화
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

    for motion_id in motion_ids:
        try:
            _rollback_one(fs_client, motion_id, args.to_version)
        except Exception as exc:  # noqa: BLE001
            print(
                f"  [{motion_id}] rollback FAIL — {exc}", file=sys.stderr, flush=True
            )

    print(
        f"\nrollback 완료. activeVersion → {args.to_version!r} + top-level mirror 복원",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
