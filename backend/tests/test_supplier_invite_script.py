"""quick-260930-lfw Task 2 — 운영 스크립트 supplier_invite.py 의 main (실 Firestore·SSM·Auth 0).

잠그는 계약:
  · create — 코드·메일 규칙 위반은 exit 2 + Firestore 호출 0. 성공은 링크 줄 + 안내 문장 줄.
    firestore_admin ValueError(이미 수락된 메일 등)는 exit 1 + stderr 에 그 문구.
  · deactivate / reactivate — set_supplier_active 에 위임(False / True), 결과 출력.
  · migrate-ssm — SSM 을 **읽기만** 한다. --dry-run 은 upsert 0. 두 번 돌리면 두 번째는 전부 skip.
  · --help — 자격 초기화 없이 일곱 서브커맨드.
테스트 메일은 전부 가짜 주소(example.com)다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin as fa
from sunity_shared import models
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "supplier_invite.py"
EMAIL = "person@example.com"
T0 = 1_700_000_000_000


@pytest.fixture
def script(monkeypatch):
    spec = importlib.util.spec_from_file_location("supplier_invite_script", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["supplier_invite_script"] = mod
    spec.loader.exec_module(mod)
    init_calls: list[str] = []
    monkeypatch.setattr(mod, "_ensure_credentials", lambda: init_calls.append("init"))
    mod._init_calls = init_calls
    yield mod
    sys.modules.pop("supplier_invite_script", None)


class _Rec:
    def __init__(self, result=None):
        self.result = result
        self.calls: list[tuple] = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.parametrize(
    "argv",
    [
        ["create", "--email", "A@B.com", "--code", "eunji", "--name", "정은지"],
        ["create", "--email", "not-mail", "--code", "MXKR", "--name", "정은지"],
        ["create", "--email", "a/b@example.com", "--code", "MXKR", "--name", "정은지"],
    ],
)
def test_create_rule_violation_exit_2_without_firestore(script, monkeypatch, argv):
    rec = _Rec()
    monkeypatch.setattr(fa, "create_supplier_invite", rec)
    assert script.main(argv) == 2
    assert rec.calls == []
    assert script._init_calls == []


def test_create_prints_link_and_instruction(script, monkeypatch, capsys):
    # 2026-10-14 02:00 KST 만료 — 안내 줄 날짜는 KST 로 찍는다.
    expires = 1_791_910_800_000
    rec = _Rec({"email": EMAIL, "code": "MXKR", "expiresAt": expires})
    monkeypatch.setattr(fa, "create_supplier_invite", rec)
    code = script.main(["create", "--email", " Person@Example.com", "--code", "mx kr",
                        "--name", "정은지", "--days", "14"])
    assert code == 0
    args, kwargs = rec.calls[0]
    assert (args, kwargs) == ((EMAIL, "MXKR", "정은지"), {"days": 14})
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert lines[-2] == "https://d2ivnoigym2xlu.cloudfront.net/supplier"
    assert lines[-1] == (
        f"이 링크를 열고 {EMAIL} Google 계정으로 로그인해 주세요. "
        f"{script._kst_date(expires)}까지 유효해요."
    )
    assert script._kst_date(expires) == "2026-10-14"


def test_create_firestore_value_error_exit_1(script, monkeypatch, capsys):
    msg = "이미 수락된 메일이에요 — 새 초대를 만들 수 없어요. 권한을 되살리려면 reactivate --uid 를 쓰세요."
    monkeypatch.setattr(fa, "create_supplier_invite", _Rec(ValueError(msg)))
    assert script.main(["create", "--email", EMAIL, "--code", "MXKR", "--name", "정은지"]) == 1
    err = capsys.readouterr().err
    assert msg in err and "reactivate" in err


def test_extend_and_revoke_delegate(script, monkeypatch):
    ext = _Rec({"email": EMAIL, "expiresAt": T0})
    rev = _Rec({"email": EMAIL, "status": "revoked"})
    monkeypatch.setattr(fa, "extend_supplier_invite", ext)
    monkeypatch.setattr(fa, "revoke_supplier_invite", rev)
    assert script.main(["extend", "--email", EMAIL, "--days", "7"]) == 0
    assert ext.calls[0] == ((EMAIL, 7), {})
    assert script.main(["revoke", "--email", EMAIL]) == 0
    assert rev.calls[0] == ((EMAIL,), {})
    monkeypatch.setattr(fa, "revoke_supplier_invite", _Rec(ValueError("권한 회수는 deactivate")))
    assert script.main(["revoke", "--email", EMAIL]) == 1


def test_deactivate_delegates_false_and_prints(script, monkeypatch, capsys):
    rec = _Rec({"code": "TESTB", "revokedInvite": "p***@example.com"})
    monkeypatch.setattr(fa, "set_supplier_active", rec)
    assert script.main(["deactivate", "--uid", "X"]) == 0
    assert rec.calls == [(("X", False), {})]
    out = capsys.readouterr().out
    assert "TESTB" in out and "p***@example.com" in out


def test_reactivate_delegates_true(script, monkeypatch):
    rec = _Rec({"code": "TESTB", "revokedInvite": None})
    monkeypatch.setattr(fa, "set_supplier_active", rec)
    assert script.main(["reactivate", "--uid", "X"]) == 0
    assert rec.calls == [(("X", True), {})]
    monkeypatch.setattr(fa, "set_supplier_active", _Rec(ValueError("되살릴 공급자가 없어요")))
    assert script.main(["reactivate", "--uid", "X"]) == 1


def _wire_ssm(script, monkeypatch, uids="uidA:BELLE, uidB", belle="uidA"):
    values = {models.SUPPLIER_UIDS_PARAM_DEFAULT: uids, script.BELLE_UID_PARAM: belle}
    reads: list[str] = []

    def _read(name):
        reads.append(name)
        return values[name]

    monkeypatch.setattr(script, "_read_ssm", _read)
    users = {"uidA": ("Belle@Example.com", "벨"), "uidB": (None, None)}
    monkeypatch.setattr(script, "_auth_user", lambda uid: users[uid])
    return reads


def test_migrate_dry_run_prints_plan_without_upsert(script, monkeypatch, capsys):
    reads = _wire_ssm(script, monkeypatch)
    ups = _Rec(True)
    monkeypatch.setattr(fa, "upsert_supplier", ups)
    monkeypatch.setattr(fa, "get_supplier", lambda uid: None)
    assert script.main(["migrate-ssm", "--dry-run"]) == 0
    assert ups.calls == []
    assert set(reads) == {models.SUPPLIER_UIDS_PARAM_DEFAULT, script.BELLE_UID_PARAM}
    out = capsys.readouterr().out.splitlines()
    assert "belle-uid: uidA" in out
    plan = [ln for ln in out if ln.startswith("plan ")]
    assert len(plan) == 2
    assert any("uid=uidA" in ln and "code=BELLE" in ln for ln in plan)
    assert any("uid=uidB" in ln and "code=-" in ln for ln in plan)


def test_migrate_twice_second_run_all_skip(script, monkeypatch, capsys, fake_firestore):
    monkeypatch.setattr(fa, "_now_ms", lambda: T0)
    _wire_ssm(script, monkeypatch)
    assert script.main(["migrate-ssm"]) == 0
    first = {k: dict(v) for k, v in fake_firestore.store.items()}
    assert set(first) == {"suppliers/uidA", "suppliers/uidB", "supplierCodes/BELLE"}
    assert first["suppliers/uidA"] == {"email": "belle@example.com", "code": "BELLE",
                                       "displayName": "벨", "active": True, "since": T0}
    assert first["suppliers/uidB"]["code"] is None
    capsys.readouterr()
    assert script.main(["migrate-ssm"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert sum(1 for ln in out if ln.startswith("skip ")) == 2
    assert not any(ln.startswith("created ") for ln in out)
    assert fake_firestore.store == first


def test_help_lists_seven_subcommands_without_credentials(script, capsys):
    with pytest.raises(SystemExit) as ei:
        script.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    for name in ("create", "extend", "revoke", "list", "migrate-ssm", "deactivate", "reactivate"):
        assert name in out
    assert script._init_calls == []


def test_script_never_writes_ssm():
    src = _SCRIPT.read_text(encoding="utf-8")
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    assert not any("put_parameter" in ln for ln in code_lines)
