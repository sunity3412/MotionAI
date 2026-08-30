"""관절 편차 → 코칭 문장 (CoachWriter 구현, #7-follow Phase 1).

Cerebras LLM 으로 관절별 한국어 코칭 문장 생성. graceful — 키 미설정/호출
실패/타임아웃 시 {} 반환 → assemble 이 수치 기반 폴백 문장 사용(가짜 생성 아님).

API 키는 Parameter Store 에 두고 환경변수 CEREBRAS_KEY_PARAM 로 파라미터명을
주입 (auth.py 의 FIREBASE_SA_PARAM 패턴과 동일 — 코드/.env 하드코딩 금지).

Phase 32 (Plan 32-09, D-11) — 가변부 슬롯 한정:
  · 감점 카드 3단(상태→왜→행동) **골격은 phrasebook(승인 문구집)이 소유**한다.
    조립 순서 = 골격 먼저(파이프라인 _attach_translation_emission 이 phrasebook
    슬롯만 병합) — 이 writer 의 산출은 records 3단에 절대 병합되지 않고 기존
    tips/detail 지정 슬롯으로만 흐른다 (골격 대체 경로 0).
  · LLM 출력 사후 금지어 필터 — phrasebook.FORBIDDEN_PHRASES_PHRASEBOOK /
    FORBIDDEN_REGEX_PHRASEBOOK 위반 entry 는 폐기 후 골격/수치 폴백 사용
    (grep 게이트의 런타임 판, D-09/D-11).
  · 전체 실패({} 반환) 시에도 문구집 골격만으로 3단이 성립한다 (D-11 graceful).
"""

from __future__ import annotations

import json
import logging
import os
import re

from .phrasebook import FORBIDDEN_PHRASES_PHRASEBOOK, FORBIDDEN_REGEX_PHRASEBOOK

log = logging.getLogger()

# D-09/D-11 런타임 금지어 필터 재료 — 문구집 grep 게이트(test_phrasebook_forbidden)
# 와 동일 상수 단일 출처. 모듈 로드 시 1회 컴파일 (write() 호출마다 재컴파일 0).
_FORBIDDEN_REGEX_COMPILED: tuple[re.Pattern, ...] = tuple(
    re.compile(p) for p in FORBIDDEN_REGEX_PHRASEBOOK
)

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
    "[가변부 슬롯 한정 — 문구집 골격 보호]\n"
    "감점 카드의 상태·이유·행동 큐 골격 문장은 승인된 고정 문구집이 소유한다 — "
    "너의 출력은 골격을 대체하지 않으며, 지정된 가변부 슬롯(카드 detail 한 줄과 "
    "자세히 모달)에만 병합된다. 허용되는 가변부 역할: (1) 주입된 실측 수치를 "
    "문장에 자연스럽게 연결, (2) 조사·어미 자연화, (3) 응원 톤 조정. 주입 데이터와 "
    "무관한 새 교정 지시, '무릎을 더 펴세요' 수준의 일반론 조언, 어느 동작에나 "
    "붙는 범용 표어는 생성하지 않는다.\n"
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


def format_posture_axis_lines(posture_axes: dict | None) -> list[str]:
    """quick-260831-bjj — belle 08-17 판독 축(postureAxes) → 프롬프트 인과형 지시 라인.

    양 writer(Cerebras + Gemini coach_writer_v2)가 이 함수 하나를 공유한다 — 발화
    판정 로직이 두 곳에 중복되지 않게(B3 정합), 판정에 쓰는 부호·significant 는
    features.posture_axis_summary 산출값({studentDeg, referenceDeg, deltaDeg,
    significant})만 소비한다.

    발화 규칙 — significant=True 이고 **학생이 나쁜 방향일 때만** 렌더 (결함 코칭
    목적 — 기준 우위 전제. 학생이 더 꼿꼿/더 1자면 교정 지시가 성립하지 않는다):
      · uprightness delta > 0 — 학생이 기준보다 더 기울어짐 (belle 피터팬 원문
        "상체의 꼿꼿해짐이 전체적 영향" — 기준이 학생보다 상체 꼿꼿).
      · headSpine delta < 0 — 학생이 기준보다 덜 1자 (belle elbow r02cand03 원문
        "고개 — 기준은 들어 몸-머리가 1자").

    문구는 인과형(부위 → 행동 → 결과), 수치는 "N° 정도" 보조만 — "좁다" 식 상태
    서술 금지 (memory how-illustration-arrow-and-number-grammar). 발화 0건이면 빈
    list → 호출자 프롬프트 byte-불변 (zero behavior change).
    """
    if not isinstance(posture_axes, dict):
        return []
    body: list[str] = []
    upright = posture_axes.get("uprightness")
    if (
        isinstance(upright, dict)
        and upright.get("significant")
        and float(upright.get("deltaDeg", 0.0)) > 0.0
    ):
        mag = round(abs(float(upright["deltaDeg"])))
        body.append(
            f"- 상체 꼿꼿함: 학생 상체가 기준보다 {mag}° 정도 더 기울어져 있음 — "
            "'상체를 세워 꼿꼿하게 만들면 동작 전체 라인이 산다' 흐름의 인과형 "
            "지시로 반영."
        )
    head = posture_axes.get("headSpine")
    if (
        isinstance(head, dict)
        and head.get("significant")
        and float(head.get("deltaDeg", 0.0)) < 0.0
    ):
        mag = round(abs(float(head["deltaDeg"])))
        body.append(
            f"- 머리-척추 1자: 학생 머리-척추 정렬이 기준보다 {mag}° 정도 덜 펴져 "
            "있음 — '고개를 들어 머리와 척추가 1자가 되게' 흐름의 인과형 지시로 반영."
        )
    if not body:
        return []
    return [
        "",
        "[자세 축 실측] (기준-학생 자세 축 비교 실측 — 아래를 부위 → 행동 → 결과 "
        "인과형 문장으로 코칭에 반영. 수치는 'N° 정도' 보조로만, 상태 서술 단독 금지):",
        *body,
    ]


def _build_prompt(
    joints: list[dict],
    motion_name: str | None = None,
    branch: str | None = None,
    angle_fixture: dict | None = None,
    vision_fault: dict | None = None,
    posture_axes: dict | None = None,
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

    # quick-260831-bjj — belle 08-17 판독 축. 발화 0건이면 빈 블록 = byte-불변.
    posture_lines = format_posture_axis_lines(posture_axes)
    posture_block = ("\n" + "\n".join(posture_lines) + "\n") if posture_lines else ""

    return (
        prefix
        + "다음 관절들의 교정 코칭을 생성해줘:\n"
        + "\n".join(lines)
        + vision_block
        + posture_block
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
                            # quick-260831-bjj — belle 08-17 판독 축 (없으면 None graceful).
                            posture_axes=context.get("postureAxes"),
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.4,
                # 관절 수에 비례해 잡는다. 2500 고정은 "3 joints × 5 causes" 기준이라,
                # 관절이 더 잡히는 긴 영상에서 응답이 잘렸다(62초 3/3 실패, 18초 0건).
                max_completion_tokens=_completion_budget(len(joints)),
            )
            choice = resp.choices[0]
            content = choice.message.content or ""
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 잘린 응답을 통째로 버리면 코칭 전체가 수치 폴백으로 **조용히** 떨어진다.
                # 완결된 관절 항목만 건져 쓴다 — 3개 중 2개라도 살리는 편이 0개보다 낫다.
                # ★로그를 API 실패와 분리한다: 원인이 다르면 이름도 달라야 한다
                #   (08-28 unknown_mode 교훈 — 서로 다른 실패를 한 이름으로 뭉치지 말 것).
                data = _salvage_partial_json(content)
                log.warning(
                    "Cerebras 응답 잘림(finish_reason=%s, %d자) — 완결 항목 %d개만 사용",
                    getattr(choice, "finish_reason", None),
                    len(content),
                    len(data),
                )
            out: dict = {}
            for k, v in data.items():
                if not isinstance(v, (str, dict)):
                    continue
                entry = _normalize_entry(v)
                # 32-09 (D-09/D-11) — 사후 금지어 필터: 위반 entry 는 통째로 폐기
                # → 해당 관절은 문구집 골격/수치 폴백 사용 (grep 게이트의 런타임 판).
                if _violates_forbidden_copy(entry):
                    log.warning(
                        "Cerebras 출력 금지어 검출 — entry 폐기(골격/폴백 사용) joint=%s",
                        k,
                    )
                    continue
                out[k] = entry
            return out
        except Exception:  # noqa: BLE001
            log.exception("Cerebras 코칭 생성 실패 — 수치 폴백 사용")
            return {}


def _completion_budget(joint_count: int) -> int:
    """관절 수에 맞춘 출력 토큰 상한.

    detail + detail2(causes/injuryRisk/coachNote) 한 관절이 대략 700~800 토큰을 쓴다.
    기존 고정값 2500 은 관절 3개까지만 감당했고, 그 이상에서 응답이 잘려 코칭이
    통째로 수치 폴백으로 떨어졌다. 하한은 기존 값과 같게 두어 짧은 영상의 동작은
    바이트 단위로 불변이다.
    """
    return max(2500, min(8000, 850 * max(joint_count, 0) + 700))


def _salvage_partial_json(text: str) -> dict:
    """잘린 JSON 오브젝트에서 **완결된 최상위 항목만** 건진다.

    응답이 `{"shoulder": {...}, "hip": {...`  처럼 중간에서 끊겼을 때, 마지막으로
    온전히 닫힌 최상위 값까지만 잘라 유효한 오브젝트로 되돌린다. 하나도 못 건지면
    빈 dict — 그때는 기존대로 수치 폴백이다.
    """
    if not text:
        return {}
    cuts: list[int] = []
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if esc:
            esc = False
            continue
        if in_str:
            if ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 1:  # 최상위 값 하나가 온전히 닫혔다
                cuts.append(i)
    for cut in reversed(cuts):
        try:
            return json.loads(text[: cut + 1] + "}")
        except json.JSONDecodeError:
            continue
    return {}


def _violates_forbidden_copy(entry) -> bool:
    """정규화된 entry 내 모든 string 에 금지어(리터럴+정규식) 검사 (D-09/D-11).

    스코프 = 사용자에게 렌더될 수 있는 LLM 산출 전체 (detail / detail2.causes
    title·explanation·fix / injuryRisk / coachNote). 위반 1건이면 entry 전체 폐기
    — 부분 살리기(문장 절단)는 하지 않는다 (문구 품질 보호, 폴백은 골격/수치).
    """
    strings: list[str] = []

    def _walk(v) -> None:  # noqa: ANN001
        if isinstance(v, str):
            strings.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                _walk(x)
        elif isinstance(v, list):
            for x in v:
                _walk(x)

    _walk(entry)
    for s in strings:
        if any(phrase in s for phrase in FORBIDDEN_PHRASES_PHRASEBOOK):
            return True
        if any(rx.search(s) for rx in _FORBIDDEN_REGEX_COMPILED):
            return True
    return False


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
