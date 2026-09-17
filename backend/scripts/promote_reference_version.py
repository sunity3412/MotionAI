"""candidate 기준 버전을 active 로 승격 (Firestore 전용 — GPU/S3 무관).

33-17 설계는 "버전 쓰기"와 "active flip"을 분리한다
(`reprocess_reference_motions_phase4.py --no-flip` 으로 쓰고, 나중에 승격).
그런데 flip 은 그 스크립트의 main() 안에만 있어서, 승격만 하려면 GPU 재처리를
통째로 다시 돌려야 했다(refuse-overwrite 때문에 그마저 막힌다).

이 스크립트는 그 공백만 메운다 — candidate 문서를 읽어 `_flip_active_pointer` 를
**그대로** 호출한다(로직 재구현 0). 그 함수가 순서대로:
  (a) versions/pre_phase4 백업 (최초 1회, immutable preimage)
  (b) reference/{id}.activeVersion = version
  (c) top-level mirror (consumer 필드 + referenceKeypointReport)
  (d) reference/_release.activeCandidate = version   ← 단일 원자 flip
  (e) post-write verify (11/11 activeVersion + per-doc content hash)

롤백: `reference/_release.activeCandidate` 를 이전 값으로 되돌리거나
`rollback_reference_motions_phase4.py`.

사용:
  FIREBASE_SA_PATH=firebase-sa.json python3 backend/scripts/promote_reference_version.py \
      --version rot180_v1 --motions ref-climb ref-combo ... [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import reprocess_reference_motions_phase4 as rp  # noqa: E402

log = logging.getLogger("promote")

DEFAULT_MOTIONS = (
    "ref-climb", "ref-combo", "ref-elbow-twist-sister", "ref-foxtop",
    "ref-foxtop-split", "ref-invert", "ref-kip-up", "ref-pdshape",
    "ref-peter-pan", "ref-power-spin", "ref-sideway-spin",
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True, help="승격할 candidate version id")
    ap.add_argument("--motions", nargs="+", default=list(DEFAULT_MOTIONS))
    ap.add_argument("--dry-run", action="store_true",
                    help="candidate 완비 확인 + 현재 포인터만 출력, write 0")
    args = ap.parse_args()

    from sunity_shared import firestore_admin
    db = firestore_admin._db()

    rel = db.document("reference/_release").get()
    current = (rel.to_dict() or {}).get("activeCandidate") if rel.exists else None
    print(f"현재 reference/_release.activeCandidate = {current!r}")
    if current == args.version:
        print(f"이미 {args.version} 이 active — 할 일 없음")
        return 0

    completed, manifest = {}, {}
    missing = []
    for mid in args.motions:
        d = db.document(f"reference/{mid}/versions/{args.version}").get().to_dict()
        if not d:
            missing.append(mid)
            continue
        completed[mid] = d
        manifest[mid] = rp._release_doc_hash(d)
    if missing:
        print(f"★ candidate 부재 {len(missing)}건: {', '.join(missing)}", file=sys.stderr)
        print("전부 있어야 flip 한다 (T-04-W5-03 부분 flip 금지).", file=sys.stderr)
        return 1
    print(f"candidate {len(completed)}/{len(args.motions)} 완비")

    if args.dry_run:
        print("--dry-run — write 생략")
        return 0

    rp._flip_active_pointer(db, list(args.motions), completed,
                            version=args.version, manifest=manifest)
    print(f"\n승격 완료 → activeCandidate = {args.version}")
    print(f"롤백: reference/_release.activeCandidate 를 {current!r} 로 되돌린다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
