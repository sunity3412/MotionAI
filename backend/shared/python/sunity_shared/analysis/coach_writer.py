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
    "[처방 구조 규칙 — 반드시 지킨다]\n"
    "각 cause 의 explanation 은 '무엇 때문에(원인) → 무엇이 무너지는지(결과 기전)' "
    "사슬로 쓴다. 예: '왼팔 위치가 불안정해 상체 지지가 무너지고, 그로 인해 "
    "균형이 흐트러질 수 있어요'.\n"
    "상태 서술만 있는 문장 금지 — '상체가 흐트러졌어요' 처럼 원인 없이 상태만 "
    "말하는 explanation 은 만들지 않는다.\n"
    "각 cause 의 fix 는 그 원인일 경우 어떻게 연습/교정하는지 구체 행동 지시 "
    "(자세 큐, 반복 방법) 로 쓴다.\n"
    "detail(카드 한 줄) 은 관찰 서술이 아니라 바로 따라 할 수 있는 실행 지시형으로 쓴다.\n"
    "\n"
    "정확한 기준 각도만 인용하고 임의 수치를 생성하지 않으며, 동작별 정의 각도를 "
    "180° 로 일반화하지 않는다. 주입된 실측 데이터(관절 편차, 기준 각도, 비전 관찰)만 "
    "근거로 쓰고, 측정되지 않은 수치나 부위를 측정된 것처럼 말하지 않는다.\n"
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


def _format_angle_fixture_lines(angle_fixture: dict | None) -> list[str]:
    """Phase 13-B: 동작별 정의 각도 fixture → 프롬프트 주입 라인 (HIGH-1 / HIGH-3).

    angle_fixture 형식 (관절 → {angle, tolerance?, isExtension?, fault?}):
      {"left_shoulder": {"angle": 139.0, ...}, ...}
    NON-180 값도 그대로 인용 (180° 로 환원 금지). isExtension:true 인 관절만 신전(180°)
    문맥. None / 빈 fixture → "관절 각도 fixture 가 없습니다" 라인 (가짜 각도 0).
    """
    if not angle_fixture:
        return ["- 이 동작은 관절 각도 fixture 가 없습니다 (가짜 각도 인용 금지)."]
    lines = []
    for joint, spec in angle_fixture.items():
        if not isinstance(spec, dict):
            continue
        angle = spec.get("angle")
        if angle is None:
            continue
        is_ext = spec.get("isExtension")
        kind = " (신전 기준)" if is_ext else " (동작별 정의 각도)"
        lines.append(f"- {joint}: {round(float(angle), 1)}°{kind}")
    if not lines:
        return ["- 이 동작은 관절 각도 fixture 가 없습니다 (가짜 각도 인용 금지)."]
    return lines


def _format_vision_fault_lines(vision_fault: dict | None) -> list[str]:
    """23-02 Task 5 (D-10 HIGH-1): to_coach_context() 의 vision-fault → causes 프롬프트 라인.

    coach gate(eligible_for_coach)는 pipeline 이 이미 판단 — 여기 도달한 vision_fault 는
    주입 대상이다. rootCauseHypotheses(support-gated, "~로 보임" 가설형, D-13 MED-1)를
    causes 원인 사슬의 **출발점** 지시로 렌더한다 (quick-260704-fwb — 단순 '참고' 힌트에서
    승격). supportedDifferences 가 있으면 서술 텍스트 필드만 골라 실측 근거 라인으로
    추가 렌더 — 키 부재/형상 불일치 시 기존 동작 불변 (fabrication 0).
    빈/None → 빈 list (기존 동작 불변).
    """
    if not vision_fault:
        return []
    lines: list[str] = []
    hyps = vision_fault.get("rootCauseHypotheses") or []
    hyp_lines: list[str] = []
    for h in hyps:
        text = str((h or {}).get("text", "")).strip()
        if text:
            hyp_lines.append(f"- {text}")
    if hyp_lines:
        lines.extend([
            "",
            "비전 분석이 관찰한 가능한 원인 (이 가설을 causes 원인 사슬의 출발점으로 "
            "사용 — '~로 보임' 가설 어투 유지):",
        ])
        lines.extend(hyp_lines)
    # 실측 근거 (supportedDifferences) — 서술 텍스트 필드만, 방어적 (없으면 불변).
    diffs = vision_fault.get("supportedDifferences")
    if isinstance(diffs, list):
        diff_lines: list[str] = []
        for d in diffs:
            if not isinstance(d, dict):
                continue
            body_part = str(d.get("body_part") or "").strip()
            fault_state = str(d.get("fault_state") or "").strip()
            correct_state = str(d.get("correct_state") or "").strip()
            if not fault_state:
                continue
            line = "- " + (f"{body_part} — " if body_part else "") + fault_state
            if correct_state:
                line += f" (올바른 상태: {correct_state})"
            diff_lines.append(line)
        if diff_lines:
            lines.extend([
                "",
                "비전 분석 실측 관찰 (측정된 것만 — 여기 없는 수치/부위 생성 금지):",
            ])
            lines.extend(diff_lines)
    return lines


def _build_prompt(
    joints: list[dict],
    motion_name: str | None = None,
    branch: str | None = None,
    angle_fixture: dict | None = None,
    vision_fault: dict | None = None,
) -> str:
    """Phase 12.5 T9: 짧은 detail + 긴 detail2 (causes/injuryRisk/coachNote) 한 호출.

    Phase 13-B (criteria 7): motion_name/branch/angle_fixture 주입 (기본 None =
    기존 동작 불변). angle_fixture 가 있으면 동작별 정의 각도(NON-180 포함)를 user
    프롬프트에 prepend — LLM 이 정확한 각도를 인용하고 180° 로 환원하지 않게 한다.

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

    # Phase 13-B: 동작 컨텍스트 + 정의 각도 prepend (criteria 7).
    context_lines: list[str] = []
    if motion_name:
        context_lines.append(f"동작: {motion_name}")
    if branch == "branch1_ipsf_registered":
        context_lines.append(
            "기준: 세계 심사 기준(IPSF) — 동작별 정의 각도. EXTEND 인 팔꿈치/무릎은 180° 신전."
        )
    elif branch == "branch2_eunji_reference":
        context_lines.append("기준: 정은지 선수 기준 자세 (정은지 reference 측정값).")
    # angle_fixture 라인은 motion/branch 컨텍스트가 있을 때만 의미 있음.
    if motion_name or branch or angle_fixture is not None:
        context_lines.append("동작별 기준 각도 (이 값만 인용, 180° 로 일반화 금지):")
        context_lines.extend(_format_angle_fixture_lines(angle_fixture))

    prefix = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    # 23-02 Task 5 — 비전 결함 root-cause 를 causes 섹션 힌트로 명시 주입 (graceful 무시 아님).
    vision_lines = _format_vision_fault_lines(vision_fault)
    vision_block = ("\n" + "\n".join(vision_lines) + "\n") if vision_lines else ""

    return (
        prefix
        + "다음 관절들의 교정 코칭을 생성해줘:\n"
        + "\n".join(lines)
        + vision_block
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

        context: {"mode", "joints": [...], "motionName"?, "branch"?, "angleFixture"?}

        Phase 13-B: motionName/branch/angleFixture 가 있으면 _build_prompt 로 전달
        (동작 분기 + 정의 각도 주입). 없으면 None graceful (기존 동작 불변).
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
                    {
                        "role": "user",
                        "content": _build_prompt(
                            joints,
                            motion_name=context.get("motionName"),
                            branch=context.get("branch"),
                            angle_fixture=context.get("angleFixture"),
                            vision_fault=context.get("visionFault"),
                        ),
                    },
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
