#!/usr/bin/env python3
"""Pod 종료 + 주소 되돌리기 한 단위 (quick-260919-t2v, belle 2026-09-19).

belle: *"pod 주소는 매일매일 새롭게 하는데"* — 기동 쪽은 `start_server.sh` 가
스스로 Lambda/SSM 을 갱신한다(endpoint_sync). **내리는 쪽도 같이 자동화하지 않으면
절반만 자동이라 또 어긋난다** — 종료된 Pod 주소가 Lambda 에 남고, 다음 사람이
"주소는 있는데 분석이 실패"를 디버깅하게 된다. 실제로 2026-09-19 실측에서 라이브
Lambda 가 **3세대 전 Pod**(elevev58iv4mox)을 가리키고 있었다.

되돌리는 값이 **빈 문자열이 아니라 자리표시자**인 이유:
  - 빈 값은 SSM 이 거부한다(`put_parameter` 빈 문자열 불가).
  - 키를 **삭제**하면 `sam deploy` 가 깨진다(템플릿이 그 키를 기대).
  - 지워도 분석이 살아나지 않는다 — Lambda CPU 폴백은 배포에서 ImportError 로 막혀
    있다(`pipeline/requirements.txt`). 즉 Pod 이 없으면 분석은 어차피 실패한다.
  → 그래서 "명백히 죽은 주소"를 남긴다. 로그에서 원인이 한눈에 보인다.

사용:
    backend/.venv/bin/python backend/scripts/pod_teardown.py            # 실행 중 Pod 전부
    backend/.venv/bin/python backend/scripts/pod_teardown.py <podId>    # 특정 Pod
    backend/.venv/bin/python backend/scripts/pod_teardown.py --urls-only  # 종료 없이 주소만
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

import boto3

REGION = "ap-northeast-2"
# 자격증명 — 로컬과 Pod 이 다르다. 로컬 기본 체인은 `sunity-api` 사용자로 풀리는데
# 그 사용자에겐 Lambda 권한이 **없다**(2026-09-19 실측: GetFunctionConfiguration
# AccessDenied). 로컬에선 `sunity-motion` 프로파일이 필요하고, Pod 에선 aws_env.sh 가
# 같은 신원의 키를 env 로 심어 두므로 프로파일이 존재하지 않는다.
# → 프로파일이 **있으면** 쓰고, 없으면 기본 체인(=Pod 의 env 키)으로 떨어진다.
_PROFILE = os.environ.get("SUNITY_AWS_PROFILE", "sunity-motion")
FN = "sunity-motion-pilot-pipeline"
PLACEHOLDER = "https://pod-down.invalid/analyze"
API_KEY_PARAM = "/sunity/motion/runpod-api-key"
GRAPHQL = "https://api.runpod.io/graphql"


def _session() -> boto3.Session:
    """로컬=프로파일, Pod=env 키. 위 주석의 신원 차이를 흡수한다."""
    try:
        if _PROFILE in boto3.Session().available_profiles:
            return boto3.Session(profile_name=_PROFILE)
    except Exception:  # noqa: BLE001 - 프로파일 조회 실패 = 기본 체인
        pass
    return boto3.Session()


def _gql(key: str, query: str) -> dict:
    req = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--urls-only"]
    urls_only = "--urls-only" in sys.argv[1:]
    sess = _session()
    ssm = sess.client("ssm", region_name=REGION)

    if not urls_only:
        key = ssm.get_parameter(Name=API_KEY_PARAM, WithDecryption=True)["Parameter"]["Value"]
        if args:
            targets = args
        else:
            data = _gql(key, "query{myself{pods{id name}}}")
            targets = [p["id"] for p in (data.get("data") or {}).get("myself", {}).get("pods", [])]
        if not targets:
            print("실행 중 Pod 없음 — 종료 생략")
        for pid in targets:
            _gql(key, f'mutation{{podTerminate(input:{{podId:"{pid}"}})}}')
            print(f"terminate {pid}")

    # 주소 되돌리기 — 나머지 env 키는 보존한다(통째 치환 금지).
    lam = sess.client("lambda", region_name=REGION)
    env = dict(lam.get_function_configuration(FunctionName=FN).get("Environment", {}).get("Variables", {}))
    if env.get("RUNPOD_ANALYZE_URL") == PLACEHOLDER:
        print(f"Lambda 이미 자리표시자 {PLACEHOLDER}")
    else:
        was = env.get("RUNPOD_ANALYZE_URL")
        env["RUNPOD_ANALYZE_URL"] = PLACEHOLDER
        lam.update_function_configuration(FunctionName=FN, Environment={"Variables": env})
        print(f"Lambda 되돌림 {was} -> {PLACEHOLDER}")

    for name, val in (("/sunity/motion/runpod-analyze-url", PLACEHOLDER),
                      ("/sunity/motion/runpod-pod-expected", "down")):
        ssm.put_parameter(Name=name, Value=val, Type="String", Overwrite=True)
    print("SSM 되돌림 (pod-expected=down)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
