"""quick-260930-o0u Task 1 — 운영 스크립트 instructor_link.py 의 main (실 Firestore 0).

잠그는 계약:
  · --help — 자격 초기화 없이 show · unlink 두 서브커맨드.
  · uid 형식 위반(빈 값 · '/' · '__x__' · 129자) — exit 2, 자격 초기화도 Firestore 호출도 0.
  · unlink — doc 없으면 exit 1 + "연결이 없어요". 있으면 지우고 한 줄(uid·code·supplierUid).
    --dry-run 은 읽기만 하고 "would unlink" 로 시작하는 한 줄, doc 은 남는다.
  · show — 있으면 필드 넷(linkedAt 은 KST), 없으면 exit 1.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin as fa
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "instructor_link.py"
# 2026-09-30 05:00:00 UTC = 14:00:00 KST
LINKED_AT = dt.datetime(2026, 9, 30, 5, 0, 0, tzinfo=dt.timezone.utc)
LINK = {"code": "BELLE", "supplierUid": "s1", "displayName": None, "linkedAt": LINKED_AT}


@pytest.fixture
def script(monkeypatch):
    spec = importlib.util.spec_from_file_location("instructor_link_script", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["instructor_link_script"] = mod
    spec.loader.exec_module(mod)
    init_calls: list[str] = []
    monkeypatch.setattr(mod, "_ensure_credentials", lambda: init_calls.append("init"))
    mod._init_calls = init_calls
    yield mod
    sys.modules.pop("instructor_link_script", None)


def test_help_lists_two_subcommands_without_credentials(script, capsys):
    with pytest.raises(SystemExit) as ei:
        script.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "show" in out and "unlink" in out
    assert script._init_calls == []


@pytest.mark.parametrize("bad", ["", "   ", "a/b", "__x__", "x" * 129, ".", ".."])
@pytest.mark.parametrize("cmd", ["show", "unlink"])
def test_bad_uid_exit_2_without_firestore(script, monkeypatch, bad, cmd):
    touched: list[str] = []
    monkeypatch.setattr(fa, "_doc", lambda path: touched.append(path))
    assert script.main([cmd, "--uid", bad]) == 2
    assert touched == []
    assert script._init_calls == []


def test_unlink_missing_doc_exit_1(script, fake_firestore, capsys):
    assert script.main(["unlink", "--uid", "u1"]) == 1
    assert "연결이 없어요" in capsys.readouterr().err


def test_unlink_deletes_and_prints_one_line(script, fake_firestore, capsys):
    fake_firestore.store["instructorLinks/u1"] = dict(LINK)
    assert script.main(["unlink", "--uid", "u1"]) == 0
    out = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(out) == 1
    assert out[0].startswith("unlinked ")
    for piece in ("uid=u1", "code=BELLE", "supplierUid=s1"):
        assert piece in out[0]
    assert "instructorLinks/u1" not in fake_firestore.store
    assert script._init_calls == ["init"]


def test_unlink_dry_run_keeps_doc(script, fake_firestore, capsys):
    fake_firestore.store["instructorLinks/u1"] = dict(LINK)
    assert script.main(["unlink", "--uid", "u1", "--dry-run"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("would unlink")
    assert "code=BELLE" in out and "supplierUid=s1" in out
    assert fake_firestore.store["instructorLinks/u1"] == LINK


def test_show_prints_fields_in_kst(script, fake_firestore, capsys):
    fake_firestore.store["instructorLinks/u1"] = dict(LINK)
    assert script.main(["show", "--uid", "u1"]) == 0
    out = capsys.readouterr().out
    for piece in ("BELLE", "s1", "displayName=-", "2026-09-30 14:00:00"):
        assert piece in out
    assert "instructorLinks/u1" in fake_firestore.store


def test_show_missing_exit_1(script, fake_firestore, capsys):
    assert script.main(["show", "--uid", "u1"]) == 1
    assert "연결이 없어요" in capsys.readouterr().err


def test_firestore_admin_get_and_delete_empty_uid_none():
    assert fa.get_instructor_link("") is None
    assert fa.delete_instructor_link("") is None
