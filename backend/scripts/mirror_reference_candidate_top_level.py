"""candidate 버전 문서 → reference/{motion_id} top-level 선택적 미러
(quick-260816-r7k Task 3).

왜 reprocess_reference_motions_phase4.py 의 `_flip_active_pointer` 를 재사용하지
않는가 (PLAN.md <context> "의도적으로 피하는 것" 절 인용):
  (1) `_flip_active_pointer` 는 flip 마다 `reference/_release.activeCandidate`
      전역 필드도 함께 쓴다. 이 필드는 11개 기준 모션 컬렉션 전체에 걸친 단일 값인데,
      이 quick task 는 ref-climb 1개 모션만 새 candidate 로 옮기는 것이라
      "quick-260816-r7k" 를 이 전역 필드에 심으면 향후 다른 모션 승격 로직이 이 값을
      신뢰할 경우 혼란을 만든다 (현재 아무 코드도 `_release` 를 읽지 않음 — 확인됨.
      그래도 새로 심지 않는다).
  (2) `_flip_active_pointer` 는 `motion_ids` 리스트 전체가 완료돼야만 flip 하는
      전체 배치용 함수라, 단일 모션만 다루는 이 스크립트의 호출 계약과 맞지 않는다.
  이 스크립트는 `reference/{motion_id}` 단일 문서만 write 하고, `reference/_release`
  는 이 파일 어디에서도 참조하지 않는다 (grep "_release" 로 자기증명 가능 — 실제로
  이 파일에 그 문자열이 등장하는 곳은 이 docstring 뿐이다).

Usage (로컬, GPU 불요 — Firestore write 만):
  cd backend && PYTHONPATH=shared/python:. FIREBASE_SA_PATH=../firebase-sa.json \
    python3 scripts/mirror_reference_candidate_top_level.py \
      --motion-id ref-climb --version quick-260816-r7k
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# sys.path 주입 — shared/python layer (backup_reference_docs.py 패턴과 동일).
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent  # scripts/ → backend
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared import firestore_admin as fa  # noqa: E402

# candidate 버전 문서에서 top-level 로 그대로 복사할 base 필드 — 11개.
# reprocess_reference_motions_phase4.py 의 REQUIRED_KEYS(schema gate 가 이미 검증한
# 필드 집합)와 동일해야 한다.
BASE_FIELDS: tuple[str, ...] = (
    "angles",
    "anglesJointKeys",
    "anglesFrames",
    "keypointReport",
    "joints3d",
    "joints3dKeys",
    "joints3dFrames",
    "coordDim",
    "space",
    "pipelineVersion",
    "reprocessedAt",
)

# backfill_reference_downstream.py --write-candidate 가 같은 candidate 문서에 MERGE
# 하는 다운스트림 7필드. PLAN.md <objective> "다운스트림 백필 필요 여부 판단" 절 —
# mode1 채점의 각 축(각도/라인/힘 방향/체형정규화)과 비교 화면이 실제로 소비하므로
# 선택이 아니라 필수다.
DOWNSTREAM_FIELDS: tuple[str, ...] = (
    "meanAngles",
    "techniqueProfile",
    "bodyNormalizationProfile",
    "forceDirectionPattern",
    "captureViews",
    "bodyComparisonSourcePose",
    "referenceKeypointReport",
)


def _build_mirror_fields(candidate_doc: dict, version: str, now_ms: int) -> dict:
    """candidate 문서 → top-level set(merge=True) 대상 필드 dict.

    순수 함수 (Firestore/네트워크 무관) — validation.py 의 "순수 함수(boto3/네트워크
    무관)" 컨벤션과 동일 스타일. BASE_FIELDS + DOWNSTREAM_FIELDS 를 candidate_doc
    에서 그대로 복사하고, activeVersion 을 새 값으로 세팅하며, DOWNSTREAM_FIELDS
    각각에 대해 `{field}UpdatedAt` 감사 필드를 now_ms 로 남긴다 (top-level 을 보는
    쪽이 다운스트림 파생값의 신선도를 알 수 있게 — base 필드는 candidate 문서 자체의
    reprocessedAt 이 이미 그 역할을 하므로 컴패니언이 없다).

    fail-closed: BASE_FIELDS 또는 DOWNSTREAM_FIELDS 중 하나라도 candidate_doc 에
    없으면 ValueError. 부분 데이터를 조용히 top-level 에 write 하면, 같은 문서 안에서
    angles/joints3d 는 새 영상을, meanAngles 등은 구 영상을 가리키는 내부 불일치
    상태(threat_model T-r7k-04)를 그대로 재현하게 된다 —
    backfill_reference_downstream.py --write-candidate 를 먼저 실행해야 한다.
    """
    missing_base = [f for f in BASE_FIELDS if f not in candidate_doc]
    if missing_base:
        raise ValueError(
            f"candidate_doc 에 BASE_FIELDS 누락: {missing_base} — "
            "reprocess_reference_motions_phase4.py --no-flip 이 먼저 실행돼야 한다 "
            "(fail-closed)"
        )
    missing_downstream = [f for f in DOWNSTREAM_FIELDS if f not in candidate_doc]
    if missing_downstream:
        raise ValueError(
            f"candidate_doc 에 DOWNSTREAM_FIELDS 누락: {missing_downstream} — "
            "backfill_reference_downstream.py --write-candidate 가 먼저 실행돼야 한다 "
            "(fail-closed, T-r7k-04: 새 영상/구 영상 필드 혼재 내부 불일치 방지)"
        )

    mirror: dict = {field: candidate_doc[field] for field in BASE_FIELDS}
    mirror.update({field: candidate_doc[field] for field in DOWNSTREAM_FIELDS})
    mirror["activeVersion"] = version
    for field in DOWNSTREAM_FIELDS:
        mirror[f"{field}UpdatedAt"] = now_ms
    return mirror


def _doc_exists(snap) -> bool:
    """DocumentSnapshot 존재 여부. 실 Firestore(.exists) + 테스트 fake 양립.

    reprocess_reference_motions_phase4.py::_doc_exists 와 동일 방어 패턴.
    """
    exists = getattr(snap, "exists", None)
    if exists is None:
        return bool(snap.to_dict())
    return bool(exists)


def _mirror_one(motion_id: str, version: str) -> dict:
    """1 motion — candidate 읽기 → top-level set(merge=True).

    reference/_release 는 이 함수 어디에서도 참조하지 않는다(grep 으로 자기증명).
    반환: write 한 mirror_fields dict (호출측 로그/검증용).
    """
    version_path = f"reference/{motion_id}/versions/{version}"
    version_snap = fa._doc(version_path).get()
    if not _doc_exists(version_snap):
        raise ValueError(
            f"{motion_id}: {version_path} 없음 — "
            "reprocess_reference_motions_phase4.py --no-flip 를 먼저 실행해야 한다"
        )
    candidate_doc = version_snap.to_dict() or {}

    # T-04-W5-05 감사 로그 패턴 (rollback_reference_motions_phase4.py::_rollback_one
    # 과 동일 스타일) — write 전에 현재 top-level activeVersion 을 stdout 에 출력해
    # 누구든 실행 로그만 보고 이전 상태를 알 수 있게 한다.
    top_path = f"reference/{motion_id}"
    current_snap = fa._doc(top_path).get()
    current_doc = current_snap.to_dict() or {}
    current_version = current_doc.get("activeVersion", "unknown")
    print(
        f"  [{motion_id}] 현재 activeVersion={current_version!r} → {version!r}",
        flush=True,
    )

    now_ms = int(time.time() * 1000)
    mirror_fields = _build_mirror_fields(candidate_doc, version, now_ms)

    fa._doc(top_path).set(mirror_fields, merge=True)
    print(
        f"  [{motion_id}] top-level set(merge=True) 완료 — {len(mirror_fields)}개 필드",
        flush=True,
    )
    return mirror_fields


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "candidate 버전 문서(reference/{motion_id}/versions/{version}) 를 "
            "reference/{motion_id} top-level 에 선택적으로 미러. "
            "reference/_release 전역 포인터는 절대 미접촉(quick-260816-r7k <context> 참조)."
        )
    )
    ap.add_argument("--motion-id", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()

    mirror_fields = _mirror_one(args.motion_id, args.version)
    print(f"완료 — activeVersion={args.version!r}, 병합 필드 {len(mirror_fields)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
