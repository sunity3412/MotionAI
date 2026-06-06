"""관절 편차 → 코칭 문장 (CoachWriter 구현, #7-follow Phase 1).

Cerebras LLM 으로 관절별 한국어 코칭 문장 생성. graceful — 키 미설정/호출
실패/타임아웃 시 {} 반환 → assemble 이 수치 기반 폴백 문장 사용(가짜 생성 아님).

API 키는 Parameter Store 에 두고 환경변수 CEREBRAS_KEY_PARAM 로 파라미터명을
주입 (auth.py 의 FIREBASE_SA_PARAM 패턴과 동일 — 코드/.env 하드코딩 금지).
"""

from __future__ import annotations

import json
import logging
import os

log = logging.getLogger()

_SYSTEM = (
    "너는 폴스포츠 자세 교정 코치다. 학생 관절 각도가 전문가 기준과 얼마나 "
    "다른지 듣고, 각 관절에 대해 따뜻하고 구체적인 교정 코칭을 한국어 한 문장으로 "
    "준다. 과장 없이 바로 실행할 수 있게 쓴다."
)


def _load_api_key() -> str | None:
    param_name = os.environ.get("CEREBRAS_KEY_PARAM")
    if not param_name:
        return None
    try:
        import boto3  # Lambda 런타임 제공

        ssm = boto3.client("ssm")
        return ssm.get_parameter(Name=param_name, WithDecryption=True)[
            "Parameter"
        ]["Value"]
    except Exception:  # noqa: BLE001
        log.exception("Cerebras 키 로드 실패")
        return None


def _build_prompt(joints: list[dict]) -> str:
    lines = [
        f"- {j['key']} ({j.get('labelKo', '')}): 기준 대비 평균 "
        f"{round(float(j.get('deviation_deg', 0)))}도 차이"
        + (f", 방향 {j['direction']}" if j.get("direction") else "")
        for j in joints
    ]
    return (
        "다음 관절들의 교정 코칭을 생성해줘:\n"
        + "\n".join(lines)
        + '\n\nJSON 으로만 답해. 형식: {"관절key": "코칭문장", ...}'
    )


class CerebrasCoachWriter:
    # 박제 (2026-06-06): llama3.1-8b deprecated (Cerebras 정책 변경, 404 not_found).
    # 박제 모델 = gpt-oss-120b (OpenAI gpt-oss 120B Apache 2.0, 한국어 OK)
    # + zai-glm-4.7 (preview). gpt-oss-120b 안정성 정합.
    def __init__(self, model: str = "gpt-oss-120b") -> None:
        self._model = model
        self._client = None
        api_key = _load_api_key()
        if not api_key:
            return  # graceful — write() 가 {} 반환, assemble 폴백 사용
        try:
            from cerebras.cloud.sdk import Cerebras

            self._client = Cerebras(api_key=api_key)
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 클라이언트 초기화 실패")
            self._client = None

    def write(self, context: dict) -> dict:
        """{joint_key: 코칭문장}. 키 없거나 실패 시 {} (assemble 폴백에 위임).

        context: {"mode", "joints": [{key, labelKo, deviation_deg, direction}, ...]}
        호출부(pipeline)가 joints 를 안 넘기면 빈 dict — 폴백 동작.
        """
        if self._client is None:
            return {}
        joints = context.get("joints")
        if not joints:
            return {}
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _build_prompt(joints)},
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            data = json.loads(resp.choices[0].message.content)
            return {k: v for k, v in data.items() if isinstance(v, str)}
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 코칭 생성 실패 — 수치 폴백 사용")
            return {}
