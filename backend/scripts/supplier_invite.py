"""공급자 메일 초대 운영 CLI (quick-260930-lfw, 38-DESIGN-v2 §W1 "운영 스크립트").

서브커맨드 일곱 개:
  create --email --code --name [--days 14]   초대 만들기. 코드 A-Z·2-9 4~8자(O·0·I·1·L 금지)·중복 금지.
                                             출력 = 공급자에게 보낼 링크 줄 + 안내 문장 줄.
  extend --email [--days 14]                 대기 중(pending) 초대의 만료를 지금부터 days 로.
  revoke --email                             대기 중 초대 취소. 수락된 초대는 deactivate 로.
  list                                       초대 표 + 공급자 명단 표(운영 터미널 — 메일 원문 출력.
                                             기록 문서에 옮길 때는 가린다).
  migrate-ssm [--dry-run]                    SSM `/sunity/motion/supplier-uids` ∪ `/sunity/motion/belle-uid`
                                             를 suppliers/supplierCodes 로 옮긴다. 이미 있으면 skip.
                                             코드는 옛 규칙 그대로(BELLE — 플래너 결정 (c)).
  deactivate --uid                           권한 회수 — suppliers·supplierCodes active False + 그 uid 가
                                             수락한 초대 revoked(한 트랜잭션, 결정 (h)).
  reactivate --uid                           되살리기의 유일한 길 — suppliers·supplierCodes active True.

이 스크립트는 SSM 을 쓰지 않는다(읽기만). SSM 되돌림은 배포 절차(260930-lfw-DEPLOY.md E0)에서
AWS CLI 로 한 번 했다.

자격: Firebase Admin SA = 리포 루트 SA 파일을 FIREBASE_SA_PATH 로(snapshot_reference_baseline.py
관례). SSM 읽기 = 셸의 AWS_PROFILE(sunity-motion). 둘 다 서브커맨드 실행 안에서만 초기화한다 —
`--help` 는 자격 없이 돈다.

종료 코드: 0 성공 · 1 Firestore 쪽 거부(ValueError — 문구를 stderr 에) · 2 입력 규칙 위반(Firestore 호출 전).
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

from sunity_shared import firestore_admin, models  # noqa: E402  (클라이언트는 첫 호출 때 lazy)
from sunity_shared.supplier_invites import (  # noqa: E402
    SupplierCodeConflict,
    normalize_invite_email,
    validate_invite_code,
)

_SA_JSON = _REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json"
_REGION = "ap-northeast-2"
BELLE_UID_PARAM = "/sunity/motion/belle-uid"
SUPPLIER_LINK = "https://d2ivnoigym2xlu.cloudfront.net/supplier"
# 공급자에게 보내는 안내 — 운영 도구 문구(앱 문구 규율 밖).
INVITE_MESSAGE = "이 링크를 열고 {email} Google 계정으로 로그인해 주세요. {date}까지 유효해요."
_KST = _dt.timezone(_dt.timedelta(hours=9))


def _kst_date(ms: int) -> str:
    return _dt.datetime.fromtimestamp(int(ms) / 1000, _KST).strftime("%Y-%m-%d")


def _ensure_credentials() -> None:
    """SA 파일을 FIREBASE_SA_PATH 로(이미 지정됐으면 그대로)."""
    if not (os.environ.get("FIREBASE_SA_JSON") or os.environ.get("FIREBASE_SA_PATH")) and _SA_JSON.exists():
        os.environ["FIREBASE_SA_PATH"] = str(_SA_JSON)


def _read_ssm(name: str) -> str | None:
    """SSM 값 **읽기**. 없으면 None."""
    import boto3

    ssm = boto3.client("ssm", region_name=_REGION)
    try:
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        return None


def _auth_user(uid: str) -> tuple[str | None, str | None]:
    """Firebase Auth 레코드의 (email, display_name)."""
    from sunity_shared import auth as _auth

    _auth._ensure_firebase()
    from firebase_admin import auth as fb_auth

    user = fb_auth.get_user(uid)
    return user.email, user.display_name


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


# ─────────────────────── 서브커맨드 ───────────────────────


def _cmd_create(args) -> int:
    try:
        email = normalize_invite_email(args.email)
        code = validate_invite_code(args.code)
    except ValueError as e:
        _err(str(e))
        return 2
    if not args.name.strip():
        _err("--name 이 비었어요.")
        return 2
    _ensure_credentials()
    try:
        doc = firestore_admin.create_supplier_invite(email, code, args.name.strip(), days=args.days)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"초대 만듦 code={doc.get('code', code)} 만료={_kst_date(doc['expiresAt'])} (KST)")
    print()
    print(SUPPLIER_LINK)
    print(INVITE_MESSAGE.format(email=email, date=_kst_date(doc["expiresAt"])))
    return 0


def _cmd_extend(args) -> int:
    try:
        email = normalize_invite_email(args.email)
    except ValueError as e:
        _err(str(e))
        return 2
    _ensure_credentials()
    try:
        doc = firestore_admin.extend_supplier_invite(email, args.days)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"연장 email={email} 만료={_kst_date(doc['expiresAt'])} (KST)")
    return 0


def _cmd_revoke(args) -> int:
    try:
        email = normalize_invite_email(args.email)
    except ValueError as e:
        _err(str(e))
        return 2
    _ensure_credentials()
    try:
        firestore_admin.revoke_supplier_invite(email)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"취소 email={email} status=revoked")
    return 0


def _fmt_ms(ms) -> str:
    return _kst_date(ms) if isinstance(ms, int) and not isinstance(ms, bool) else "-"


def _cmd_list(_args) -> int:
    _ensure_credentials()
    invites = firestore_admin.list_supplier_invites()
    suppliers = firestore_admin.list_suppliers()
    print(f"[초대 {len(invites)}건]  email | code | name | status | 만료(KST) | acceptedUid")
    for inv in invites:
        print(
            f"  {inv.get('email')} | {inv.get('code')} | {inv.get('displayName')} | "
            f"{inv.get('status')} | {_fmt_ms(inv.get('expiresAt'))} | {inv.get('acceptedUid') or '-'}"
        )
    print(f"[공급자 {len(suppliers)}명]  uid | code | name | active | email | since(KST)")
    for sup in suppliers:
        print(
            f"  {sup.get('uid')} | {sup.get('code') or '-'} | {sup.get('displayName') or '-'} | "
            f"{sup.get('active')} | {sup.get('email') or '-'} | {_fmt_ms(sup.get('since'))}"
        )
    return 0


def _cmd_migrate(args) -> int:
    _ensure_credentials()
    supplier_map = models.parse_supplier_uids(_read_ssm(models.SUPPLIER_UIDS_PARAM_DEFAULT))
    belle_uid = (_read_ssm(BELLE_UID_PARAM) or "").strip()
    print(f"belle-uid: {belle_uid or '-'}")
    union: dict[str, str | None] = dict(supplier_map)
    if belle_uid and belle_uid not in union:
        union[belle_uid] = None
    print(f"대상 uid {len(union)}개 (supplier-uids {len(supplier_map)} ∪ belle-uid)")
    now_ms = firestore_admin._now_ms()
    for uid, code in union.items():
        email, name = _auth_user(uid)
        if args.dry_run:
            state = "skip(이미 있음)" if firestore_admin.get_supplier(uid) is not None else "create"
            print(f"plan uid={uid} code={code or '-'} email={email or '-'} name={name or '-'} -> {state}")
            continue
        try:
            created = firestore_admin.upsert_supplier(
                uid, email=email, code=code, display_name=name, active=True, since_ms=now_ms
            )
        except (ValueError, SupplierCodeConflict) as e:
            _err(f"실패 uid={uid} code={code}: {e}")
            return 1
        print(f"{'created' if created else 'skip'} uid={uid} code={code or '-'} email={email or '-'}")
    return 0


def _cmd_set_active(args, active: bool) -> int:
    _ensure_credentials()
    try:
        out = firestore_admin.set_supplier_active(args.uid, active)
    except ValueError as e:
        _err(str(e))
        return 1
    verb = "reactivate" if active else "deactivate"
    print(
        f"{verb} uid={args.uid} code={out.get('code') or '-'} "
        f"revokedInvite={out.get('revokedInvite') or '-'}"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="supplier_invite.py",
        description="공급자 메일 초대 운영 — create/extend/revoke/list/migrate-ssm/deactivate/reactivate",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="초대 만들기 (링크 + 안내 두 줄 출력)")
    c.add_argument("--email", required=True)
    c.add_argument("--code", required=True, help="A-Z·2-9 4~8자, O·0·I·1·L 금지")
    c.add_argument("--name", required=True, help="선수 이름(크게 보기 제목)")
    c.add_argument("--days", type=int, default=models.SUPPLIER_INVITE_DEFAULT_DAYS)

    e = sub.add_parser("extend", help="대기 중 초대 만료 연장")
    e.add_argument("--email", required=True)
    e.add_argument("--days", type=int, default=models.SUPPLIER_INVITE_DEFAULT_DAYS)

    r = sub.add_parser("revoke", help="대기 중 초대 취소")
    r.add_argument("--email", required=True)

    sub.add_parser("list", help="초대·공급자 표")

    m = sub.add_parser("migrate-ssm", help="SSM 명단을 suppliers/supplierCodes 로 (SSM 읽기만)")
    m.add_argument("--dry-run", action="store_true")

    d = sub.add_parser("deactivate", help="권한 회수 (수락 초대 revoked 까지)")
    d.add_argument("--uid", required=True)

    ra = sub.add_parser("reactivate", help="되살리기 (유일한 길)")
    ra.add_argument("--uid", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "create":
        return _cmd_create(args)
    if args.cmd == "extend":
        return _cmd_extend(args)
    if args.cmd == "revoke":
        return _cmd_revoke(args)
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "migrate-ssm":
        return _cmd_migrate(args)
    if args.cmd == "deactivate":
        return _cmd_set_active(args, False)
    return _cmd_set_active(args, True)


if __name__ == "__main__":
    sys.exit(main())
