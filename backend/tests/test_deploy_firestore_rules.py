"""Plan 38-06 Task 3 — deploy_firestore_rules.py(Rules REST) 순수 빌더·요약·main 흐름 + firestore.rules 게이트.

네트워크 0 — `http_post` / `http_get` / `get_access_token` seam 을 monkeypatch 한다.
`--release` 는 여기서도, 이 플랜에서도 실행하지 않는다(38-09 belle 승인 뒤) — 호출 **순서**만 잠근다.
firestore.rules 는 텍스트 게이트(리뷰 R2·R13): 재귀 와일드카드 제거 · private 본인 읽기 ·
selfCheck 표식 create/update 거부(affectedKeys — coachReview merge-set 은 계속 되어야 한다).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import deploy_firestore_rules as dfr  # backend/scripts (tests/conftest.py 가 sys.path 주입)

REPO = Path(__file__).resolve().parents[2]
RULES_PATH = REPO / "firestore.rules"
CASES_PATH = REPO / "backend" / "tests" / "firestore_rules_cases.json"
SCRIPT_PATH = REPO / "backend" / "scripts" / "deploy_firestore_rules.py"

RULES_TEXT = "rules_version = '2';\nservice cloud.firestore { match /databases/{d}/documents { } }\n"
CASES = [
    {"expectation": "ALLOW", "request": {"auth": {"uid": "A"}, "path": "/databases/(default)/documents/x/1", "method": "get"}},
    {"expectation": "DENY", "request": {"auth": {"uid": "B"}, "path": "/databases/(default)/documents/x/1", "method": "get"}},
    {"expectation": "DENY", "request": {"path": "/databases/(default)/documents/x/1", "method": "get"}},
]


def _results(states: list[str]) -> dict:
    return {"testResults": [{"state": s} for s in states]}


# ─────────────────── 순수 body 빌더 ───────────────────


def test_build_test_body():
    body = dfr.build_test_body(RULES_TEXT, CASES)
    assert body == {
        "source": {"files": [{"name": "firestore.rules", "content": RULES_TEXT}]},
        "testSuite": {"testCases": CASES},
    }


def test_build_ruleset_body():
    assert dfr.build_ruleset_body(RULES_TEXT) == {
        "source": {"files": [{"name": "firestore.rules", "content": RULES_TEXT}]}
    }


def test_build_release_body():
    assert dfr.build_release_body("p", "projects/p/rulesets/abc") == {
        "release": {
            "name": "projects/p/releases/cloud.firestore",
            "rulesetName": "projects/p/rulesets/abc",
        }
    }


# ─────────────────── summarize_test_results ───────────────────


def test_summarize_all_pass():
    assert dfr.summarize_test_results(_results(["SUCCESS"] * 3), CASES) == (3, [])


def test_summarize_failure_names_case():
    passed, failed = dfr.summarize_test_results(_results(["SUCCESS", "FAILURE", "SUCCESS"]), CASES)
    assert passed == 2
    assert len(failed) == 1
    assert "#2" in failed[0] and "DENY" in failed[0] and "/x/1" in failed[0]


def test_summarize_issues_marks_all_failed():
    resp = {"issues": [{"description": "Unexpected 'foo'.", "severity": "ERROR"}],
            "testResults": [{"state": "SUCCESS"}] * 3}
    passed, failed = dfr.summarize_test_results(resp, CASES)
    assert passed == 0
    assert any(f.startswith("[issue]") and "Unexpected 'foo'." in f for f in failed)
    assert sum(1 for f in failed if f.startswith("#")) == len(CASES)


def test_summarize_missing_results_count_as_failed():
    passed, failed = dfr.summarize_test_results(_results(["SUCCESS"]), CASES)
    assert passed == 1
    assert len(failed) == 2
    assert all("state=None" in f for f in failed)


# ─────────────────── 케이스 파일 ───────────────────


def test_load_cases_reads_test_cases_file():
    cases = dfr.load_cases(CASES_PATH)
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))["testCases"]
    assert cases == raw
    assert len(cases) >= 12
    for c in cases:
        assert c["expectation"] in ("ALLOW", "DENY")
        assert c["request"]["path"].startswith("/databases/(default)/documents/")
        assert c["request"]["method"] in ("get", "list", "create", "update", "delete")
    assert sum(1 for c in cases if c["expectation"] == "DENY") >= 6


def test_cases_cover_required_scenarios():
    cases = dfr.load_cases(CASES_PATH)

    def find(**want):
        out = []
        for c in cases:
            r = c["request"]
            if all(
                (r.get("auth") or {}).get("uid") == v if k == "uid" else
                r.get(k) == v if k in ("path", "method") else c.get(k) == v
                for k, v in want.items()
            ):
                out.append(c)
        return out

    priv = "/databases/(default)/documents/reference/r1/private/registration"
    assert [c["expectation"] for c in find(uid="A", path=priv, method="get")] == ["ALLOW"]
    assert [c["expectation"] for c in find(uid="B", path=priv, method="get")] == ["DENY"]
    assert [c["expectation"] for c in find(uid=None, path=priv, method="get")] == ["DENY"]
    pub = "/databases/(default)/documents/reference/r1"
    assert [c["expectation"] for c in find(uid="B", path=pub, method="get")] == ["ALLOW"]
    assert [c["expectation"] for c in find(uid="B", path=pub + "/versions/v1", method="get")] == ["ALLOW"]
    assert [c["expectation"] for c in find(uid="B", path=pub, method="update")] == ["DENY"]
    ana = "/databases/(default)/documents/users/A/analyses/x"
    creates = find(uid="A", path=ana, method="create")
    assert sorted(c["expectation"] for c in creates) == ["ALLOW", "DENY"]
    for c in creates:
        has_marker = "selfCheckForReference" in c["request"]["resource"]["data"]
        assert c["expectation"] == ("DENY" if has_marker else "ALLOW")
    updates = find(uid="A", path=ana, method="update")
    assert sorted(c["expectation"] for c in updates) == ["ALLOW", "DENY"]
    for c in updates:
        before = c["resource"]["data"]
        after = c["request"]["resource"]["data"]
        assert before.get("selfCheckForReference") == "r1"  # 서버가 이미 표식을 쓴 doc
        changed = after.get("selfCheckForReference") != before.get("selfCheckForReference")
        assert c["expectation"] == ("DENY" if changed else "ALLOW")
        if not changed:
            assert "coachReview" in after  # 앱의 merge-set 은 계속 된다
    assert [c["expectation"] for c in find(uid="B", path=ana, method="get")] == ["DENY"]
    assert [c["expectation"] for c in find(uid="A", path=ana, method="delete")] == ["ALLOW"]


# ─────────────────── main 흐름 (seam monkeypatch, 네트워크 0) ───────────────────


@pytest.fixture
def seams(monkeypatch):
    calls: dict[str, list] = {"post": [], "get": []}
    monkeypatch.setattr(dfr, "get_access_token", lambda: "fake-access")
    monkeypatch.setattr(dfr, "http_get", lambda url, token: _boom("http_get", url))
    monkeypatch.setattr(dfr, "http_post", lambda url, body, token, method="POST": _boom("http_post", url))
    return calls


def _boom(name, url):
    raise AssertionError(f"{name} 호출됨: {url}")


def _rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "firestore.rules"
    p.write_text(RULES_TEXT, encoding="utf-8")
    return p


def _cases_file(tmp_path: Path) -> Path:
    p = tmp_path / "cases.json"
    p.write_text(json.dumps({"testCases": CASES}), encoding="utf-8")
    return p


def test_main_test_exit_code_equals_failures(seams, monkeypatch, tmp_path, capsys):
    def fake_post(url, body, token, method="POST"):
        seams["post"].append((method, url, body))
        return 200, _results(["SUCCESS", "FAILURE", "FAILURE"])

    monkeypatch.setattr(dfr, "http_post", fake_post)
    rc = dfr.main(["--test", "--rules", str(_rules_file(tmp_path)), "--cases", str(_cases_file(tmp_path)), "--project", "p"])
    assert rc == 2
    assert len(seams["post"]) == 1
    method, url, body = seams["post"][0]
    assert method == "POST"
    assert url == "https://firebaserules.googleapis.com/v1/projects/p:test"
    assert body == dfr.build_test_body(RULES_TEXT, CASES)
    out = capsys.readouterr().out
    assert "expected=ALLOW state=SUCCESS" in out
    assert "expected=DENY state=FAILURE" in out
    assert "fake-access" not in out


def test_main_test_all_pass_exit_0(seams, monkeypatch, tmp_path):
    monkeypatch.setattr(dfr, "http_post", lambda url, body, token, method="POST": (200, _results(["SUCCESS"] * 3)))
    rc = dfr.main(["--test", "--rules", str(_rules_file(tmp_path)), "--cases", str(_cases_file(tmp_path)), "--project", "p"])
    assert rc == 0


def test_main_test_403_exits_2_and_prints_body(seams, monkeypatch, tmp_path, capsys):
    denied = {"error": {"code": 403, "message": "The caller does not have permission", "status": "PERMISSION_DENIED"}}
    monkeypatch.setattr(dfr, "http_post", lambda url, body, token, method="POST": (403, denied))
    rc = dfr.main(["--test", "--rules", str(_rules_file(tmp_path)), "--cases", str(_cases_file(tmp_path)), "--project", "p"])
    assert rc == 2
    assert "PERMISSION_DENIED" in capsys.readouterr().out


def test_main_release_posts_ruleset_then_patches_release(seams, monkeypatch, tmp_path, capsys):
    def fake_post(url, body, token, method="POST"):
        seams["post"].append((method, url, body))
        if url.endswith("/rulesets"):
            return 200, {"name": "projects/p/rulesets/xyz", "createTime": "2026-09-28T00:00:00Z"}
        return 200, {"name": "projects/p/releases/cloud.firestore", "rulesetName": body["release"]["rulesetName"], "updateTime": "2026-09-28T00:00:01Z"}

    monkeypatch.setattr(dfr, "http_post", fake_post)
    rc = dfr.main(["--release", "--rules", str(_rules_file(tmp_path)), "--project", "p"])
    assert rc == 0
    assert [(m, u) for m, u, _ in seams["post"]] == [
        ("POST", "https://firebaserules.googleapis.com/v1/projects/p/rulesets"),
        ("PATCH", "https://firebaserules.googleapis.com/v1/projects/p/releases/cloud.firestore"),
    ]
    assert seams["post"][0][2] == dfr.build_ruleset_body(RULES_TEXT)
    assert seams["post"][1][2] == dfr.build_release_body("p", "projects/p/rulesets/xyz")
    assert "projects/p/rulesets/xyz" in capsys.readouterr().out


def test_main_release_stops_when_ruleset_create_fails(seams, monkeypatch, tmp_path):
    def fake_post(url, body, token, method="POST"):
        seams["post"].append((method, url))
        return 400, {"error": {"message": "bad rules"}}

    monkeypatch.setattr(dfr, "http_post", fake_post)
    rc = dfr.main(["--release", "--rules", str(_rules_file(tmp_path)), "--project", "p"])
    assert rc == 1
    assert len(seams["post"]) == 1  # releases PATCH 로 넘어가지 않는다


def test_main_current_is_get_only_and_writes_out(seams, monkeypatch, tmp_path, capsys):
    def fake_get(url, token):
        seams["get"].append(url)
        if url.endswith("/releases/cloud.firestore"):
            return 200, {"name": "projects/p/releases/cloud.firestore", "rulesetName": "projects/p/rulesets/old1", "updateTime": "2026-01-01T00:00:00Z"}
        assert url == "https://firebaserules.googleapis.com/v1/projects/p/rulesets/old1"
        return 200, {"name": "projects/p/rulesets/old1", "source": {"files": [{"name": "firestore.rules", "content": "OLD RULES"}]}}

    monkeypatch.setattr(dfr, "http_get", fake_get)  # http_post 는 seams 기본 → 호출되면 AssertionError
    out_path = tmp_path / "rules.bak"
    rc = dfr.main(["--current", "--project", "p", "--out", str(out_path)])
    assert rc == 0
    assert seams["get"] == [
        "https://firebaserules.googleapis.com/v1/projects/p/releases/cloud.firestore",
        "https://firebaserules.googleapis.com/v1/projects/p/rulesets/old1",
    ]
    assert out_path.read_text(encoding="utf-8") == "OLD RULES"
    assert "projects/p/rulesets/old1" in capsys.readouterr().out


def test_main_dry_run_prints_body_and_makes_no_http(seams, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(dfr, "get_access_token", lambda: _boom("get_access_token", "-"))
    rc = dfr.main(["--test", "--release", "--dry-run", "--rules", str(_rules_file(tmp_path)), "--cases", str(_cases_file(tmp_path)), "--project", "p"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "projects/p:test" in out and "projects/p/rulesets" in out
    assert '"testSuite"' in out and '"testCases"' in out
    assert "DRY-RUN" in out


def test_main_requires_an_action(seams, tmp_path):
    with pytest.raises(SystemExit):
        dfr.main(["--project", "p", "--rules", str(_rules_file(tmp_path))])


def test_project_resolution_prefers_explicit_then_firebaserc(tmp_path):
    assert dfr.resolve_project("explicit") == "explicit"
    rc_file = tmp_path / ".firebaserc"
    rc_file.write_text(json.dumps({"projects": {"default": "from-rc"}}), encoding="utf-8")
    assert dfr._project_from_firebaserc(rc_file) == "from-rc"
    assert dfr._project_from_firebaserc(tmp_path / "missing") is None
    assert dfr._project_from_firebaserc(REPO / ".firebaserc") == "sunity-ai-coach"


def test_script_never_prints_or_logs_the_token():
    src = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()
    bad = [l for l in src if ("print(" in l and "token" in l) or ("log" in l and "token" in l)]
    assert bad == []
    assert SCRIPT_PATH.read_text(encoding="utf-8").count("firebaserules.googleapis.com") >= 3


# ─────────────────── firestore.rules 게이트 (R2 · R13) ───────────────────


def test_rules_file_gates():
    text = RULES_PATH.read_text(encoding="utf-8")
    assert "match /reference/{document=**}" not in text  # 재귀 와일드카드 제거(좁힘)
    assert "match /reference/{refId} {" in text
    assert text.count("match /reference/{refId}/private/{doc}") == 1
    assert text.count("resource.data.supplierUid == request.auth.uid") == 1
    assert text.count("hasAny(['selfCheckForReference', 'selfCheckJobId'])") == 2  # create + update
    assert "request.resource.data.diff(resource.data).affectedKeys().hasAny(['selfCheckForReference', 'selfCheckJobId'])" in text
    assert "request.resource.data.keys().hasAny(['selfCheckForReference', 'selfCheckJobId'])" in text
    assert "match /reference/{refId}/versions/{version}" in text
    assert "match /{document=**} {\n      allow read, write: if false;" in text  # 기본 차단 유지
    assert "allow read, delete: if request.auth != null && request.auth.uid == uid;" in text
