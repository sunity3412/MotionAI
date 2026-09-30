"""수강생 ↔ 강사 연결 운영 CLI (quick-260930-o0u, 38-DESIGN-v2 §W2 "해제는 운영 스크립트").

앱은 instructorLinks/{학생 uid} 를 한 번만 만들고(firestore.rules create-once), 바꾸거나 지우지
못한다. 수강생이 cs@sunity.ai 로 "강사를 바꾸고 싶다"고 알리면 운영자가 이 스크립트로 해제한다
(ClassDojo 형 운영 해제, 38-SCENARIOS 추천 코드 절). 해제된 수강생은 앱에서 다시 입력할 수 있다.

서브커맨드 두 개:
  show   --uid                 연결 doc 의 code · supplierUid · displayName · linkedAt(KST) 출력.
  unlink --uid [--dry-run]     연결 doc 을 지운다. 지우기 전 내용을 stdout 한 줄에 남긴다 — 이 줄이
                               해제 이력의 전부다(별도 이력 컬렉션 없음). --dry-run 은 읽기만.

운영 터미널 도구라 uid 는 원문 출력한다(supplier_invite.py list 와 같음). 기록 문서에 옮길 때는 가린다.

자격: Firebase Admin SA = 리포 루트 SA 파일을 FIREBASE_SA_PATH 로(supplier_invite.py 관례).
서브커맨드 실행 안에서만 초기화한다 — `--help` 와 uid 형식 검사는 자격 없이 돈다.

종료 코드: 0 성공 · 1 연결 없음 · 2 입력 규칙 위반(Firestore 호출 전).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_LAYER = _REPO / "backend" / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

from sunity_shared import firestore_admin  # noqa: E402  (클라이언트는 첫 호출 때 lazy)

_SA_JSON = _REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"
_KST = _dt.timezone(_dt.timedelta(hours=9))
_UID_MAX = 128


def _ensure_credentials() -> None:
    """SA 파일을 FIREBASE_SA_PATH 로(이미 지정됐으면 그대로)."""
    if not (os.environ.get("FIREBASE_SA_JSON") or os.environ.get("FIREBASE_SA_PATH")) and _SA_JSON.exists():
        os.environ["FIREBASE_SA_PATH"] = str(_SA_JSON)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _check_uid(uid) -> str:
    """Firestore doc id 로 쓸 수 있는 uid 인지 — 오타로 엉뚱한 경로를 지우지 않게(T-o0u-08).

    위반이면 ValueError. 규칙: 문자열 · 앞뒤 공백 제거 후 비어 있지 않음 · '/' 없음 ·
    128자 이하 · '.' '..' 아님 · '__' 로 시작하고 끝나는 예약 id 아님.
    """
    if not isinstance(uid, str):
        raise ValueError("uid 가 문자열이 아니에요.")
    u = uid.strip()
    if not u:
        raise ValueError("uid 가 비었어요.")
    if "/" in u:
        raise ValueError("uid 에 '/' 가 들어 있어요.")
    if len(u) > _UID_MAX:
        raise ValueError(f"uid 가 {_UID_MAX}자를 넘어요.")
    if u in (".", ".."):
        raise ValueError("uid 가 '.' 또는 '..' 이에요.")
    if u.startswith("__") and u.endswith("__"):
        raise ValueError("uid 가 '__…__' 예약 형식이에요.")
    return u


def _kst(value) -> str:
    """Firestore Timestamp(DatetimeWithNanoseconds) · datetime → KST 문자열, 그 밖은 '-'."""
    if isinstance(value, _dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=_dt.timezone.utc)
        return value.astimezone(_KST).strftime("%Y-%m-%d %H:%M:%S")
    return "-"


def _field(doc: dict, key: str) -> str:
    v = doc.get(key)
    return "-" if v is None or v == "" else str(v)


# ─────────────────────── 서브커맨드 ───────────────────────


def _cmd_show(args) -> int:
    try:
        uid = _check_uid(args.uid)
    except ValueError as e:
        _err(str(e))
        return 2
    _ensure_credentials()
    doc = firestore_admin.get_instructor_link(uid)
    if doc is None:
        _err(f"연결이 없어요 uid={uid}")
        return 1
    print(
        f"uid={uid} code={_field(doc, 'code')} supplierUid={_field(doc, 'supplierUid')} "
        f"displayName={_field(doc, 'displayName')} linkedAt={_kst(doc.get('linkedAt'))} (KST)"
    )
    return 0


def _cmd_unlink(args) -> int:
    try:
        uid = _check_uid(args.uid)
    except ValueError as e:
        _err(str(e))
        return 2
    _ensure_credentials()
    if args.dry_run:
        doc = firestore_admin.get_instructor_link(uid)
        verb = "would unlink"
    else:
        doc = firestore_admin.delete_instructor_link(uid)
        verb = "unlinked"
    if doc is None:
        _err(f"연결이 없어요 uid={uid}")
        return 1
    print(
        f"{verb} uid={uid} code={_field(doc, 'code')} supplierUid={_field(doc, 'supplierUid')} "
        f"displayName={_field(doc, 'displayName')} linkedAt={_kst(doc.get('linkedAt'))} (KST)"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="instructor_link.py",
        description="수강생 ↔ 강사 연결 운영 도구 (quick-260930-o0u)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="연결 doc 보기")
    s.add_argument("--uid", required=True, help="학생 uid")
    u = sub.add_parser("unlink", help="연결 해제 (지우기 전 내용을 한 줄로 출력)")
    u.add_argument("--uid", required=True, help="학생 uid")
    u.add_argument("--dry-run", action="store_true", help="읽기만 — 쓰기 0")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "show":
        return _cmd_show(args)
    return _cmd_unlink(args)


if __name__ == "__main__":
    sys.exit(main())
