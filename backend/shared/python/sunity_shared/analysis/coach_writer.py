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
    "다른지 듣고, 각 관절에 대해 두 가지를 모두 만든다:\n"
    "1) 카드 짧은 한 줄 코칭 (현장 실행 지시, 따뜻하고 구체적, 과장 없음)\n"
    "2) 자세히 모달 — 다중 원인 후보 + 각 case 처방 + 부상 경고 + 코치 권고\n"
    "\n"
    "원인은 학생이 정확히 모르므로 '이런 경우 어깨가 내려갈 수 있어요' 식으로 "
    "3~5가지 가능성을 제시하고, 각 case 마다 그 case 인 것 같으면 어떻게 "
    "연습할지 알려준다. 부상 위험이 보이면 명시. 마지막은 코치와 영상 함께 "
    "확인하라는 권고로 마무리한다.\n"
    "\n"
    "JSON 으로만 답한다. 다른 텍스트, 마크다운, 주석 금지."
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
    """Phase 12.5 T9: 짧은 detail + 긴 detail2 (causes/injuryRisk/coachNote) 한 호출.

    응답 형식:
    {
      "<관절key>": {
        "detail": "카드 본문 한 줄 (실행 지시)",
        "detail2": {
          "causes": [
            {"title": "원인 짧은 제목", "explanation": "1~2문장 설명",
             "fix": "이 case 면 이렇게 연습"},
            ... 3~5개
          ],
          "injuryRisk": "부상 위험 한 줄 (없으면 키 자체 생략)",
          "coachNote": "코치와 영상 함께 확인하라는 마무리 한 줄"
        }
      },
      ...
    }
    """
    lines = [
        f"- {j['key']} ({j.get('labelKo', '')}): 기준 대비 평균 "
        f"{round(float(j.get('deviation_deg', 0)))}도 차이"
        + (f", 방향 {j['direction']}" if j.get("direction") else "")
        for j in joints
    ]
    schema_hint = (
        '{"<관절key>": {"detail": "한 줄", "detail2": '
        '{"causes": [{"title":"...", "explanation":"...", "fix":"..."}, ...], '
        '"injuryRisk": "...", "coachNote": "..."}}, ...}'
    )
    return (
        "다음 관절들의 교정 코칭을 생성해줘:\n"
        + "\n".join(lines)
        + "\n\n각 관절에 대해 'detail' (카드 본문 한 줄) 과 'detail2' (자세히 모달용 — "
        "causes 3~5개 + injuryRisk + coachNote) 둘 다 만들어줘.\n"
        f"\nJSON 형식: {schema_hint}"
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
        """{joint_key: {"detail": str, "detail2"?: {...}}} 반환.

        Phase 12.5 T9 (2026-06-07): 한 호출에 짧은 detail + 긴 detail2 둘 다 생성.
        - detail = 카드 본문 한 줄 (현재 build_tips 가 사용)
        - detail2 = 자세히 모달용 (causes/injuryRisk/coachNote)

        호환성: 키 없거나 실패 시 {} (assemble 폴백 — 수치 기반 한 줄만).
        legacy 호출자 (기존 build_tips) 가 string 만 기대하면 detail 만 추출 가능.

        context: {"mode", "joints": [{key, labelKo, deviation_deg, direction}, ...]}
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
                max_completion_tokens=2500,  # detail2 길이 — 3 joints × 5 causes 박제 박제
            )
            data = json.loads(resp.choices[0].message.content)
            return {
                k: _normalize_entry(v)
                for k, v in data.items()
                if isinstance(v, (str, dict))
            }
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 코칭 생성 실패 — 수치 폴백 사용")
            return {}


def _normalize_entry(v) -> dict | str:
    """LLM 응답 1개 entry 정규화. dict 면 detail/detail2 분리, str 면 legacy 한 줄.

    LLM 이 가끔 detail/detail2 대신 다른 키 (예: tip, advice) 박제 박제 박제 박제
    — graceful 처리 (지원되는 키만 추출, 나머지 무시).
    """
    if isinstance(v, str):
        return {"detail": v}
    if not isinstance(v, dict):
        return {"detail": ""}
    out: dict = {}
    detail = v.get("detail") or v.get("tip") or v.get("advice")
    if isinstance(detail, str):
        out["detail"] = detail
    d2 = v.get("detail2") or v.get("more") or v.get("details")
    if isinstance(d2, dict):
        causes = d2.get("causes")
        if isinstance(causes, list):
            norm_causes = []
            for c in causes:
                if not isinstance(c, dict):
                    continue
                norm_causes.append({
                    "title": str(c.get("title", "")),
                    "explanation": str(c.get("explanation", "")),
                    "fix": str(c.get("fix", "")),
                })
            if norm_causes:
                detail2: dict = {"causes": norm_causes}
                ir = d2.get("injuryRisk")
                if isinstance(ir, str) and ir.strip():
                    detail2["injuryRisk"] = ir
                cn = d2.get("coachNote")
                if isinstance(cn, str) and cn.strip():
                    detail2["coachNote"] = cn
                else:
                    detail2["coachNote"] = "강사와 함께 영상을 보며 확인해 보세요."
                out["detail2"] = detail2
    return out
