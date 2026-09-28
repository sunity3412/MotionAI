#!/usr/bin/env python3
"""Firestore 보안 규칙 — Rules REST 로 시험(--test) · 현재 조회(--current) · 배포(--release).

왜 REST 인가(38-06 T3): firebase CLI 가 이 맥/리포에 없고 감사 밖 패키지 설치는 금지
(CLAUDE.md §7). 기존 Admin 서비스 계정(sunity_shared.auth._load_service_account_dict —
FIREBASE_SA_JSON / FIREBASE_SA_PATH / FIREBASE_SA_PARAM 3원)으로 firebaserules.googleapis.com
을 직접 부르면 같은 자격으로 test · rulesets · releases 가 전부 된다. google-auth · requests
는 backend/.venv 에 이미 있다(운영 규칙 배포 스크립트 선례 0 — PATTERNS "No Analog Found",
REST 문서를 따른다).

사용:
  FIREBASE_SA_PATH=<sa.json> backend/.venv/bin/python backend/scripts/deploy_firestore_rules.py --test
      # projects:test — 규칙 파일 + backend/tests/firestore_rules_cases.json (읽기 전용, 배포 0)
  ... --current --out /tmp/firestore.rules.bak
      # 현재 release 의 rulesetName + 규칙 원문 저장 (GET 만 — 38-09 의 롤백 원본)
  ... --release
      # rulesets POST → releases PATCH.  ★ 38-09 belle 승인 뒤에만. 38-06 에서는 실행 금지.
  ... --dry-run --test|--release
      # 보낼 body 만 출력, HTTP 0

롤백 = 이전 규칙 파일(--current --out 으로 저장한 것)로 --release.
exit code: --test 는 실패 케이스 수 · 권한 거부(403)는 응답 원문 출력 + 2(38-09 가 belle
콘솔 폴백으로 갈 신호) · 그 외 HTTP 오류 1 · 인자 오류 2(argparse).
자격 증명 값은 어디에도 출력하지 않는다(T-38-06-6).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_LAYER = REPO / "backend" / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

RULES_API = "https://firebaserules.googleapis.com/v1"
SCOPES = (
    "https://www.googleapis.com/auth/firebase",
    "https://www.googleapis.com/auth/cloud-platform",
)
RELEASE_ID = "cloud.firestore"  # Firestore 규칙 release 의 고정 이름
DEFAULT_RULES = REPO / "firestore.rules"
DEFAULT_CASES = REPO / "backend" / "tests" / "firestore_rules_cases.json"


# ─────────────────── 순수 함수 (pytest 대상, 네트워크 0) ───────────────────


def build_test_body(rules_text: str, cases: list[dict]) -> dict:
    """POST projects/{p}:test 본문 — 규칙 원문 + TestSuite."""
    return {
        "source": {"files": [{"name": "firestore.rules", "content": rules_text}]},
        "testSuite": {"testCases": list(cases)},
    }


def build_ruleset_body(rules_text: str) -> dict:
    """POST projects/{p}/rulesets 본문."""
    return {"source": {"files": [{"name": "firestore.rules", "content": rules_text}]}}


def build_release_body(project: str, ruleset_name: str) -> dict:
    """PATCH projects/{p}/releases/cloud.firestore 본문 — 새 ruleset 을 가리키게."""
    return {
        "release": {
            "name": f"projects/{project}/releases/{RELEASE_ID}",
            "rulesetName": ruleset_name,
        }
    }


def load_cases(path) -> list[dict]:
    """케이스 파일의 `testCases` 를 그대로(빈 목록은 오류 — 0건 통과를 성공으로 읽지 않게)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("testCases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path}: testCases 가 비어 있다")
    return cases


def case_label(index: int, case: dict) -> str:
    req = case.get("request") or {}
    auth = req.get("auth") or {}
    return (
        f"#{index + 1} {case.get('expectation')} uid={auth.get('uid')} "
        f"{req.get('method')} {req.get('path')}"
    )


def summarize_test_results(resp_json: dict, cases: list[dict]) -> tuple[int, list[str]]:
    """(passed, failed 라벨 목록). `testResults[i].state == 'SUCCESS'` 가 통과.

    `issues`(규칙 구문/컴파일 오류)가 하나라도 있으면 전부 실패 — 규칙이 컴파일되지 않으면
    케이스 결과는 의미가 없다. 결과가 케이스보다 짧으면 빠진 케이스는 실패(state=None).
    """
    issues = resp_json.get("issues") or []
    results = resp_json.get("testResults") or []
    failed: list[str] = []
    if issues:
        for issue in issues:
            failed.append(f"[issue] {issue.get('severity')}: {issue.get('description')}")
        failed.extend(f"{case_label(i, c)} state=None(issue)" for i, c in enumerate(cases))
        return 0, failed
    passed = 0
    for i, case in enumerate(cases):
        state = results[i].get("state") if i < len(results) else None
        if state == "SUCCESS":
            passed += 1
        else:
            failed.append(f"{case_label(i, case)} state={state}")
    return passed, failed


def _project_from_firebaserc(path) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return (data.get("projects") or {}).get("default") or None


def resolve_project(explicit: str | None) -> str:
    """--project → .firebaserc projects.default → SA project_id 순."""
    if explicit:
        return explicit
    from_rc = _project_from_firebaserc(REPO / ".firebaserc")
    if from_rc:
        return from_rc
    from sunity_shared.auth import _load_service_account_dict

    return _load_service_account_dict()["project_id"]


# ─────────────────── seam (테스트가 monkeypatch 하는 지점 — 네트워크·자격 증명) ───────────────────


def get_access_token() -> str:
    """Admin SA → OAuth2 access 자격(google-auth). 값은 어디에도 출력하지 않는다."""
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    from sunity_shared.auth import _load_service_account_dict

    creds = service_account.Credentials.from_service_account_info(
        _load_service_account_dict(), scopes=list(SCOPES)
    )
    creds.refresh(Request())
    return creds.token


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _json_or_raw(r) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:2000]}
    return data if isinstance(data, dict) else {"raw": data}


def http_post(url: str, body: dict, token: str, *, method: str = "POST") -> tuple[int, dict]:
    """(status, json). method 는 POST(test·rulesets) 또는 PATCH(releases)."""
    import requests

    r = requests.request(method, url, json=body, headers=_headers(token), timeout=60)
    return r.status_code, _json_or_raw(r)


def http_get(url: str, token: str) -> tuple[int, dict]:
    import requests

    r = requests.get(url, headers=_headers(token), timeout=60)
    return r.status_code, _json_or_raw(r)


# ─────────────────── 동작 ───────────────────
#
# 엔드포인트(Firebase Rules REST v1 — RULES_API 하나로 조립한다):
#   POST  https://firebaserules.googleapis.com/v1/projects/{p}:test                 (--test, 읽기 전용)
#   GET   https://firebaserules.googleapis.com/v1/projects/{p}/releases/cloud.firestore  (--current)
#   GET   https://firebaserules.googleapis.com/v1/{rulesetName}                     (--current, 원문)
#   POST  https://firebaserules.googleapis.com/v1/projects/{p}/rulesets             (--release 1/2)
#   PATCH https://firebaserules.googleapis.com/v1/projects/{p}/releases/cloud.firestore  (--release 2/2)


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _http_failure(status: int, resp: dict, what: str) -> int:
    """403 = 권한 거부 → 원문 출력 + 2(콘솔 폴백 신호). 그 외 → 원문 출력 + 1."""
    print(f"{what}: HTTP {status}")
    _print_json(resp)
    return 2 if status == 403 else 1


def run_test(project: str, token: str, rules_text: str, cases: list[dict]) -> int:
    """projects:test — 케이스별 한 줄(ALLOW/DENY expected=… state=…), 실패 건수를 반환."""
    url = f"{RULES_API}/projects/{project}:test"
    status, resp = http_post(url, build_test_body(rules_text, cases), token)
    if status != 200:
        return _http_failure(status, resp, "projects:test")
    passed, failed = summarize_test_results(resp, cases)
    results = resp.get("testResults") or []
    for i, case in enumerate(cases):
        req = case.get("request") or {}
        result = results[i] if i < len(results) else {}
        state = result.get("state")
        print(
            f"{case.get('expectation')} expected={case.get('expectation')} state={state} "
            f"uid={(req.get('auth') or {}).get('uid')} {req.get('method')} {req.get('path')}"
        )
        if state != "SUCCESS":
            for msg in result.get("debugMessages") or []:
                print(f"    {msg}")
    for f in failed:
        print(f"FAIL {f}")
    print(f"projects:test {passed}/{len(cases)} passed")
    return len(failed)


def run_current(project: str, token: str, out: str | None) -> int:
    """현재 release 의 rulesetName + 규칙 원문(GET 만, 쓰기 0). --out 이면 파일로 저장."""
    status, rel = http_get(f"{RULES_API}/projects/{project}/releases/{RELEASE_ID}", token)
    if status != 200:
        return _http_failure(status, rel, "releases.get")
    ruleset_name = rel.get("rulesetName")
    if not ruleset_name:
        print("release 응답에 rulesetName 이 없다")
        _print_json(rel)
        return 1
    status, rs = http_get(f"{RULES_API}/{ruleset_name}", token)
    if status != 200:
        return _http_failure(status, rs, "rulesets.get")
    files = (rs.get("source") or {}).get("files") or []
    content = (files[0].get("content") or "") if files else ""
    print(
        f"current release name={rel.get('name')} rulesetName={ruleset_name} "
        f"updateTime={rel.get('updateTime')} files={len(files)}"
    )
    if out:
        Path(out).write_text(content, encoding="utf-8")
        print(f"saved {out} ({len(content)} chars)")
    else:
        print(content)
    return 0


def run_release(project: str, token: str, rules_text: str) -> int:
    """rulesets POST → releases PATCH. ★ 38-09 belle 승인 뒤에만."""
    status, rs = http_post(
        f"{RULES_API}/projects/{project}/rulesets", build_ruleset_body(rules_text), token
    )
    if status != 200:
        return _http_failure(status, rs, "rulesets.create")
    ruleset_name = rs.get("name")
    if not ruleset_name:
        print("rulesets.create 응답에 name 이 없다 — release 로 넘어가지 않는다")
        _print_json(rs)
        return 1
    print(f"ruleset created name={ruleset_name} createTime={rs.get('createTime')}")
    status, rel = http_post(
        f"{RULES_API}/projects/{project}/releases/{RELEASE_ID}",
        build_release_body(project, ruleset_name),
        token,
        method="PATCH",
    )
    if status != 200:
        return _http_failure(status, rel, "releases.patch")
    print(
        f"released name={rel.get('name')} rulesetName={rel.get('rulesetName')} "
        f"updateTime={rel.get('updateTime')}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Firestore 규칙 — Rules REST 로 --test / --current / --release (--dry-run 은 body 만)."
    )
    ap.add_argument("--rules", default=str(DEFAULT_RULES), help="규칙 파일(기본 리포 루트 firestore.rules)")
    ap.add_argument("--cases", default=str(DEFAULT_CASES), help="projects:test 케이스 JSON")
    ap.add_argument("--project", default=None, help="기본 .firebaserc projects.default → SA project_id")
    ap.add_argument("--test", action="store_true", help="projects:test (읽기 전용)")
    ap.add_argument("--current", action="store_true", help="현재 release 규칙 조회(GET 만)")
    ap.add_argument("--release", action="store_true", help="실배포 — 38-09 belle 승인 뒤에만")
    ap.add_argument("--dry-run", action="store_true", help="보낼 body 만 출력, HTTP 0")
    ap.add_argument("--out", default=None, help="--current 의 규칙 원문 저장 경로(롤백 원본)")
    args = ap.parse_args(argv)
    if not (args.test or args.current or args.release):
        ap.error("--test / --current / --release 중 하나 이상이 필요하다")

    project = resolve_project(args.project)
    rules_text = (
        Path(args.rules).read_text(encoding="utf-8") if (args.test or args.release) else ""
    )
    cases = load_cases(args.cases) if args.test else []

    if args.dry_run:
        print(f"DRY-RUN project={project} (HTTP 0)")
        if args.current:
            print(f"GET {RULES_API}/projects/{project}/releases/{RELEASE_ID}")
        if args.test:
            print(f"POST {RULES_API}/projects/{project}:test")
            _print_json(build_test_body(rules_text, cases))
        if args.release:
            print(f"POST {RULES_API}/projects/{project}/rulesets")
            _print_json(build_ruleset_body(rules_text))
            print(f"PATCH {RULES_API}/projects/{project}/releases/{RELEASE_ID} (rulesetName 은 POST 응답)")
        return 0

    if args.release:
        print("★ --release: 규칙을 실배포한다 — 38-09 belle 승인 뒤에만 실행할 것.")
    token = get_access_token()
    rc = 0
    if args.current:
        rc = max(rc, run_current(project, token, args.out))
    if args.test:
        rc = max(rc, run_test(project, token, rules_text, cases))
    if args.release:
        rc = max(rc, run_release(project, token, rules_text))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
