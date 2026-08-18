"""교사 증류 배치 — Gemini 교사(gemini-3.1-pro-preview)로 짚기·측정·코칭 라벨 생성.

Plan 22-04 Task 1 (D-10b). 배치 흐름:
  (1) 크레딧/quota probe — 1건 시험 호출로 429(RESOURCE_EXHAUSTED) 시 즉시 중단
      ([[gemini-credits-depleted-2026-06-20]]) + client.files.list 잔량 로그.
  (2) manifest 행 순회(holdout=hard_negative_eval 제외, 고객 소스는 anonymized=true
      만) → S3 다운로드 → File API 업로드(ACTIVE 폴링) → 교사 모델에 schema.bind_key_
      prompt 시스템 프롬프트 + RTMW 좌표(select_frame_indices 서브샘플 행) 입력 →
      D-01 통합 리포트 JSON + <thought> 수신 → 즉시 client.files.delete(finally, 실패
      해도 삭제).
  (3) 필터: LLM judge(gemini-3.7-flash, 0~10 블라인드) < JUDGE_MIN_SCORE 폐기 + 반복
      루프 탐지 + 물리 불가 궤적 휴리스틱(속도/가속도) + 뼈길이 정합 + faults ⊇
      DEDUCTION_CONSUMED_KEYS 미충족 폐기.
  (4) 출력: 로컬 distill JSONL + 필터 통계(수락/폐기 사유별 카운트). video_hash 캐시로
      재실행 시 재업로드 0.

객관성 hard gate: judge 점수는 필터 임계로만 쓰고 라벨에 저장하지 않는다 — 사람/모델
숫자 점수 라벨 필드를 만들지 않는다([[analysis-objectivity-no-human-scores]]).
시크릿 = env GEMINI_API_KEY 우선 → SSM /sunity/motion/gemini-api-key(WithDecryption,
--profile sunity-motion). 키 값은 절대 로그하지 않는다(T-22-13).

google-genai/boto3 는 lazy import — 순수 필터/행선택 로직은 네트워크 0 으로 테스트된다.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

# datagen 규격 단일 owner 재사용 (bind_key_prompt / REPORT_KEYS / 서브샘플 / 이산화).
from datagen import schema

log = logging.getLogger("gemini_teacher")
from sunity_shared.gemini.config import DEFAULT_C_MODEL
if not log.handlers:
    log.setLevel(logging.INFO)

# ── 모델 string (단일 owner: [[gemini-latest-model-versions]], 2.5 계열 금지) ──
# 교사 = Pro(고품질 라벨), judge = Flash(저비용 블라인드 채점). 변경 시 근거 주석 필수.
TEACHER_MODEL = "gemini-3.1-pro-preview"
# 모델 문자열 하드코딩 금지 — 단일 owner = sunity_shared.gemini.config (quick-260818-lik).
JUDGE_MODEL = DEFAULT_C_MODEL

# ── 다단계 품질 필터 임계 (22-NLM-EXTRACT §6) ──
JUDGE_MIN_SCORE = 7        # LLM judge 0~10 중 7점 미만 폐기 (교사 결함 상속 방어).
_REPEAT_NGRAM = 4          # 반복 루프 탐지 n-gram 크기.
_REPEAT_MAX = 3            # 동일 n-gram 이 이 횟수 초과 반복되면 루프로 간주.
_MAX_FRAME_JUMP_NORM = 0.5  # 프레임간 정규화 좌표 점프 상한(물리 불가 속도 컷).
_BONE_LEN_TOL = 0.4        # 뼈길이 프레임간 변동 허용 비율(정합 이탈 시 물리 불가).

# ── File API 폴링(gemini_vision_scorer 전례 재사용 값) ──
_FILES_TIMEOUT_S = 180.0
_FILES_POLL_S = 3.0

# ── belle greenlight env 게이트 (과금 배치는 명시 승인 없이 실행 금지, DR-05) ──
_GREENLIGHT_ENV = "PHASE22_BELLE_GREENLIGHT"

_BACKEND = Path(__file__).resolve().parents[2]

_CLIENT = None  # google.genai Client 모듈 캐시 싱글톤.


# ---------------------------------------------------------------------------
# 시크릿 / 클라이언트 (lazy — 순수 로직 테스트는 네트워크 0).
# ---------------------------------------------------------------------------
def _load_api_key() -> str:
    """env GEMINI_API_KEY 우선 → SSM /sunity/motion/gemini-api-key(WithDecryption).

    키 값은 절대 로그하지 않는다(T-22-13). SSM 파라미터명만 로그.
    """
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        log.info("Gemini 키: env GEMINI_API_KEY")
        return env_key
    import boto3  # lazy

    param = os.environ.get("GEMINI_API_KEY_PARAM_NAME", "/sunity/motion/gemini-api-key")
    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    resp = ssm.get_parameter(Name=param, WithDecryption=True)
    log.info("Gemini 키: SSM %s", param)
    return resp["Parameter"]["Value"]


def _ensure_client():
    """google.genai Client lazy-init + 모듈 캐시 싱글톤 (gemini_vision_scorer 패턴)."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    from google import genai  # lazy — top-level import 금지(D-16)

    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 부재")
    _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


# ---------------------------------------------------------------------------
# File API 생명주기 — 업로드 ACTIVE 폴링 + 삭제(graceful). google.genai.types 무의존.
# ---------------------------------------------------------------------------
def _state_name(handle) -> str | None:
    """업로드 핸들 상태 이름 추출 — enum(.name)/문자열 양쪽 흡수."""
    state = getattr(handle, "state", None)
    if state is None:
        return None
    return getattr(state, "name", None) or str(state)


def _upload_and_wait(client, local_video_path: str):
    """local 영상 → Files API 업로드 후 ACTIVE 대기 (gemini_vision_scorer 패턴 복사).

    mime 는 SDK 가 확장자에서 추론하게 둔다(config 강제 불필요) — google.genai.types
    import 없이 fake client 로 테스트 가능. state 가 ACTIVE 아니면 RuntimeError.
    """
    uploaded = client.files.upload(file=local_video_path)
    start = time.monotonic()
    while _state_name(uploaded) == "PROCESSING":
        if time.monotonic() - start > _FILES_TIMEOUT_S:
            raise TimeoutError(f"Files API processing > {_FILES_TIMEOUT_S}s")
        time.sleep(_FILES_POLL_S)
        uploaded = client.files.get(name=uploaded.name)
    state = _state_name(uploaded)
    if state and state != "ACTIVE":
        raise RuntimeError(f"Files API state={state} (ACTIVE 아님)")
    return uploaded


def _delete_uploaded(client, handle) -> None:
    """업로드 파일 삭제 — 20GB 적체 누수 방지(2026-06-22). 삭제 실패 graceful."""
    name = getattr(handle, "name", None)
    if not name:
        return
    try:
        client.files.delete(name=name)
    except Exception:  # noqa: BLE001 - 정리 실패는 배치를 막지 않는다.
        log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", name)


def list_file_residue(client) -> int:
    """client.files.list 잔량 카운트 (누수 0 acceptance 계측용). 실패 시 -1."""
    try:
        return sum(1 for _ in client.files.list())
    except Exception:  # noqa: BLE001 - 계측 실패는 배치를 막지 않는다.
        log.warning("files.list 잔량 조회 실패 (graceful)")
        return -1


# ---------------------------------------------------------------------------
# 교사 프롬프트 — schema.bind_key_prompt + D-01 리포트 + 감점 계약 필드 요구.
# ---------------------------------------------------------------------------
def build_teacher_system_prompt(joint_keys, motion=None) -> str:
    """교사 시스템 프롬프트 — D-11 키 사전 바인딩 + D-01 통합 리포트 v1 산출 지시.

    faults[] 각 항목이 감점 엔진 계약(DEDUCTION_CONSUMED_KEYS) 필드를 그대로 산출하도록
    요구한다 — student_angle_deg/reference_angle_deg/measurement_basis/fault_category 가
    빠지면 새 REPORT_KEYS 조립 시 채점 불가(schema.faults ⊇ DEDUCTION_CONSUMED_KEYS).
    모델은 점수를 절대 내지 않는다(짚기·측정·앵커까지만; ND-02).

    시험 배치 진단 fix (2026-07-10, belle 승인): fault_category 를 "고정 enum"이라고만
    하고 유효값을 제공하지 않아 교사가 enum 밖 값 산출 → _normalize_fault_item 이 None
    강등 → 3/3 rejected_contract 추정. 유효값은 schema 단일 owner(_safe_valid_categories
    — shared layer 미로드 시 빈 튜플 graceful)에서 주입한다. 하드코딩 금지(새 분류 발명
    금지 [[scoring-dimensions-ipsf]] 정신). 정타 영상 억지 결함 방지 문장도 함께 명시.

    동작명 주입 fix (2026-07-10 2차, belle 승인): 동작명 미주입 시 교사가 무맥락
    "모든 관절 180°" 기준으로 위양성 결함을 짚었다(ref-climb 무릎 97° 실증 — climb 은
    무릎 굽힘이 기술의 일부). motion 이 있으면 동작명 + 기술조건부 판정 일반 원칙
    (technique.py 존재 이유와 동일 정신, [[scoring-dimensions-ipsf]] 기술조건부)을
    명시한다. 동작별 지식 하드코딩 나열 금지 — 모델 자체 지식 + 향후 technique
    profile 주입이 담당. motion None/빈값이면 기존 프롬프트와 동일(graceful).
    """
    key_line = schema.bind_key_prompt(joint_keys)
    report_keys = ", ".join(schema.REPORT_KEYS)
    fault_keys = ", ".join(schema.DEDUCTION_CONSUMED_KEYS)
    categories = schema._safe_valid_categories()
    category_line = (
        f"fault_category 유효값(반드시 이 목록의 값만 사용, 목록 밖 값 금지): "
        f"[{', '.join(categories)}].\n"
        if categories
        else ""  # shared layer 미로드 graceful — enum 나열 문장 생략.
    )
    motion_line = (
        f"분석 대상 동작: {motion}. 결함 판정은 이 동작의 정상 수행 형태를 기준으로만 "
        "합니다 — 이 동작에서 기술상 의도된 관절 굽힘·그립·자세는 결함으로 짚지 않습니다. "
        "모든 관절이 180° 신전이어야 한다는 무맥락 기준을 적용하지 마세요. 해당 동작의 "
        "기술 요건상 실제로 벗어난 부분만 결함입니다.\n"
        if motion
        else ""  # motion 미상 graceful — 동작 문장 생략(기존 프롬프트 동일).
    )
    return (
        "당신은 폴스포츠 모션 분석 전문가입니다. 선수의 운동 영상과 RTMW 비전 모델이 "
        "추출한 시계열 관절 좌표(JSON)를 입력받습니다. 가려짐이나 모션 블러로 잘못 추출된 "
        "좌표를 보정하고, 교정된 자세를 바탕으로 정밀한 짚기·측정·코칭을 제공하세요. "
        "반드시 <thought> 태그로 분석 과정을 먼저 서술한 뒤 JSON 리포트를 출력합니다.\n"
        f"{motion_line}"
        f"{key_line}\n"
        f"리포트 최상위 키(알파벳 정렬, 결측은 Null): [{report_keys}].\n"
        "faults[] 각 항목은 감점 엔진 계약 필드를 반드시 포함합니다: "
        f"[{fault_keys}]. student_angle_deg/reference_angle_deg 는 각도쌍(도), "
        "measurement_basis 는 무엇을 어떻게 쟀는지 서술, fault_category 는 고정 enum 입니다.\n"
        f"{category_line}"
        # 밀도 강화 (260715-wq9, belle 승인): 교사가 가장 뚜렷한 결함 하나만 짚는 관성
        # (진단상 fault 중앙값 1개/영상)이 학생에게 결함 미방출을 학습시켰다. 결함
        # 영상에서는 관찰되는 모든 결함을 각각 별도 항목으로 산출하도록 명시한다.
        # 바로 아래 정타 빈 배열 지시와 인접 배치해 다중 열거가 정타 위양성으로 번지지
        # 않게 한다(결함 영상=모두 짚기 / 정타 영상=빈 배열). 동작별 지식 하드코딩 없음.
        "결함 영상에서는 관찰되는 모든 결함을 빠짐없이 각각 별도 faults[] 항목으로 "
        "산출합니다 — 가장 뚜렷한 하나만 짚고 나머지를 생략하지 마세요.\n"
        "짚을 결함이 없으면 faults 는 빈 배열([])로 출력합니다 — 정타 영상에 억지 결함을 "
        "만들지 않습니다.\n"
        "점수(score/severity/overall/points 계열)는 절대 출력하지 않습니다 — 짚기·측정·"
        "앵커까지만 하고 감점은 별도 규칙 엔진이 담당합니다."
    )


def build_rtmw_text(coords_by_frame) -> str:
    """서브샘플 프레임 행만 RTMW_Data 텍스트로 직렬화 (belle 노트 §8 원형).

    coords_by_frame = [{'frame': int, '<joint>': [x, y, conf], ...}, ...] (원 9fps
    인덱스가 frame). 원 영상 재추출 없이 인덱스 서브샘플만 쓰는 Pattern 1 계약이라
    호출자가 select_frame_indices 로 고른 행만 넘긴다.
    """
    return "RTMW_Data: " + json.dumps(coords_by_frame, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# 교사/judge 호출 — delete-in-finally 가 핵심(DR-07, test 로 증명).
# ---------------------------------------------------------------------------
def _generate_teacher(client, model, uploaded, system_prompt, rtmw_text):
    """교사 generate_content 호출 → text 반환 (JSON mime 강제)."""
    resp = client.models.generate_content(
        model=model,
        contents=[uploaded, rtmw_text],
        config={
            "system_instruction": system_prompt,
            "temperature": 0.0,
            "response_mime_type": "application/json",
        },
    )
    return getattr(resp, "text", None)


def distill_video(
    client,
    local_video_path: str,
    coords_by_frame,
    joint_keys,
    *,
    teacher_model: str = TEACHER_MODEL,
    motion=None,
):
    """단일 영상 증류 — 업로드 → 교사 호출 → 즉시 삭제(finally). D-01 리포트 반환.

    업로드/생성 중 예외가 나도 finally 가 반드시 files.delete 를 호출한다 — File API
    20GB 적체 누수 방지(DR-07, test_gemini_teacher 로 증명). 반환 = normalize_report 를
    통과한 정규 리포트(화이트리스트/Null 고정/enum 강제) + raw_text(교사 원문 — 폐기 행
    진단용 보존, 2026-07-10 fix). 파싱 실패 시에도 raw_text 는 보존해 반환한다
    ({"thought": None, "report": None, "raw_text": ...}).

    motion = manifest row 의 동작명 — 프롬프트에 주입해 기술조건부 판정 유도(위양성
    결함 방지, 2026-07-10 2차 fix). None 이면 기존 프롬프트와 동일(graceful).
    """
    uploaded = None
    try:
        uploaded = _upload_and_wait(client, local_video_path)
        system_prompt = build_teacher_system_prompt(joint_keys, motion=motion)
        rtmw_text = build_rtmw_text(coords_by_frame)
        raw_text = _generate_teacher(
            client, teacher_model, uploaded, system_prompt, rtmw_text
        )
    finally:
        _delete_uploaded(client, uploaded)
    # 파싱 단계는 어떤 예외에도 raise 하지 않는다(2026-07-10 fix) — 진단 목적상 raw 는
    # 모든 실패에서 남아야 한다. 업로드/생성 예외(quota 429 포함)는 위에서 그대로
    # raise 되어 run_trial_batch 의 _is_quota_error 중단 로직이 보존된다.
    try:
        parsed = parse_teacher_report(raw_text)
    except Exception:  # noqa: BLE001 - 파싱 예외 → rejected_parse graceful, raw 보존.
        log.warning("교사 응답 파싱 예외 (graceful — raw 보존): %s", local_video_path)
        parsed = None
    if parsed is None:
        # 파싱 실패여도 원문은 보존 — 진단 없이 폐기 사유를 은폐하지 않는다.
        return {"thought": None, "report": None, "raw_text": raw_text}
    parsed["raw_text"] = raw_text
    return parsed


def parse_teacher_report(raw_text):
    """교사 raw text(<thought>...JSON) → (thought, normalize_report(dict)).

    <thought> 블록과 JSON 을 분리한다. JSON 파싱 실패 시 None 반환(graceful — 배치가
    폐기 카운트로 집계). 반환 = {"thought": str|None, "report": dict}.
    """
    if not raw_text:
        return None
    thought, body = _split_thought(raw_text)
    obj = _extract_json_object(body)
    if obj is None:
        return None
    return {"thought": thought, "report": schema.normalize_report(obj)}


def _split_thought(text: str) -> tuple[str | None, str]:
    """<thought>...</thought> 를 분리 — 태그 없으면 thought=None, 전체 body."""
    lower = text.lower()
    start = lower.find("<thought>")
    end = lower.find("</thought>")
    if start != -1 and end != -1 and end > start:
        thought = text[start + len("<thought>"):end].strip()
        body = (text[:start] + text[end + len("</thought>"):]).strip()
        return thought, body
    return None, text


def _coerce_report_dict(obj):
    """파싱 산출 → 리포트 dict 강제 (2026-07-10 fix: 최상위 배열 케이스).

    교사가 JSON 을 최상위 배열로 출력하는 케이스(시험 배치 5행 중 2행 실증)에서
    normalize_report(list) 가 AttributeError 로 죽고 raw 보존까지 실패했다. 규칙:
      · dict → 그대로.
      · 단일 원소 배열 + 원소가 dict → unwrap 하여 정상 경로.
      · 그 외(다원소/비 dict 배열, 스칼라) → None (rejected_parse graceful).
    """
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
        return obj[0]
    return None


def _extract_json_object(text: str):
    """text 에서 첫 최상위 JSON object 를 추출(코드펜스/서두 텍스트/배열 wrap 관용).

    반환은 항상 dict 또는 None — _coerce_report_dict 로 강제(비 dict 산출 차단)."""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    try:
        return _coerce_report_dict(json.loads(s))
    except (json.JSONDecodeError, ValueError):
        pass
    # 중괄호 균형으로 첫 object 스캔.
    depth = 0
    begin = -1
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                begin = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and begin != -1:
                try:
                    return _coerce_report_dict(json.loads(s[begin:i + 1]))
                except (json.JSONDecodeError, ValueError):
                    return None
    return None


def judge_report(client, report: dict, *, judge_model: str = JUDGE_MODEL, motion=None) -> int:
    """LLM judge — 리포트를 0~10 블라인드 채점(gemini-3.7-flash). 파싱 실패 시 0.

    judge 점수는 필터 임계로만 쓰고 라벨에 저장하지 않는다(객관성 hard gate). 점수만
    숫자로 요구해 파싱 단순화.

    루브릭 분기 fix (2026-07-10 3차): 시험 배치에서 두 방향 오채점 실증 —
      · 정타 리포트(faults=[] + 구체 코칭 3문장, ref-climb)가 3점 → 부당 폐기.
        구 루브릭이 "짚기·측정의 구체성"만 봐서 faults 빈 배열은 구조적 저점.
      · 이전 배치는 위양성 결함 포함 전부 10점 — 결함/숫자가 많으면 고득점하는
        휴리스틱으로 동작.
    fix = (a) faults 유무로 채점 기준을 명시 분기 (b) motion 주입으로 결함 판정
    타당성의 맥락 제공(교사 프롬프트 c5b14ef 와 동일 정신, None graceful)
    (c) 스케일 앵커 문장으로 전부 10점/전부 3점 붕괴 방지.
    """
    faults = (report or {}).get("faults")
    motion_line = (
        f"분석 대상 동작: {motion}. 결함 판정의 타당성은 이 동작의 기술 요건에 "
        "비추어 평가하세요 — 이 동작에서 기술상 의도된 자세를 결함으로 짚었다면 "
        "판정 오류로 감점 대상입니다.\n"
        if motion
        else ""  # motion 미상 graceful — 동작 문장 생략.
    )
    if faults:
        rubric_line = (
            "이 리포트는 결함(faults)을 짚었습니다. 채점 기준: 짚기·측정의 구체성·"
            "일관성·물리적 타당성 + 해당 동작의 기술 요건에 비춘 결함 판정의 타당성. "
            "억지 결함(동작상 정상 자세를 결함으로 짚음)이면 감점하세요. 결함 개수나 "
            "숫자가 많다는 이유만으로 고득점을 주지 마세요.\n"
        )
    else:
        rubric_line = (
            "이 리포트는 결함(faults)이 빈 배열입니다 — 정타 판정. 결함이 없다는 것 "
            "자체를 감점하지 마세요. 채점 기준: 코칭 문장의 구체성·기술 정합성·실행 "
            "가능성.\n"
        )
    prompt = (
        "다음 폴스포츠 모션 분석 리포트의 품질을 0~10 정수로만 채점하세요.\n"
        f"{motion_line}"
        f"{rubric_line}"
        "채점 앵커: 구체적이고 타당하면 8~10, 모호하거나 일반론이면 4~7, 부정확하거나 "
        "물리적으로 불가능한 서술이면 0~3.\n"
        "숫자 하나만 출력:\n"
        + json.dumps(report, ensure_ascii=False, sort_keys=True)
    )
    resp = client.models.generate_content(
        model=judge_model,
        contents=[prompt],
        config={"temperature": 0.0},
    )
    return _parse_judge_score(getattr(resp, "text", None))


def _parse_judge_score(text) -> int:
    """judge 응답에서 0~10 정수 추출 — 실패/범위 밖은 0(폐기 유발)."""
    if not text:
        return 0
    import re

    # 첫 정수 run 추출 — Korean 조사("9점")에서도 boundary 무관하게 잡힌다.
    m = re.search(r"\d+", str(text))
    if not m:
        return 0
    val = int(m.group(0))
    return val if 0 <= val <= 10 else 0


# ---------------------------------------------------------------------------
# 순수 필터 — judge 임계 / 반복 루프 / 물리 불가 궤적 / 뼈길이 / 감점 계약.
# ---------------------------------------------------------------------------
def judge_passes(score: int) -> bool:
    """judge 0~10 채점이 임계(JUDGE_MIN_SCORE) 이상이면 수락."""
    return int(score) >= JUDGE_MIN_SCORE


def has_repetition_loop(text, *, ngram: int = _REPEAT_NGRAM, max_repeat: int = _REPEAT_MAX) -> bool:
    """동일 토큰 n-gram 이 max_repeat 초과 반복되면 루프로 간주(반복 폐기, §6-b)."""
    if not text:
        return False
    tokens = str(text).split()
    if len(tokens) < ngram:
        return False
    seen: dict[tuple, int] = {}
    for i in range(len(tokens) - ngram + 1):
        gram = tuple(tokens[i:i + ngram])
        seen[gram] = seen.get(gram, 0) + 1
        if seen[gram] > max_repeat:
            return True
    return False


def is_physically_impossible(coords_seq, *, max_jump: float = _MAX_FRAME_JUMP_NORM) -> bool:
    """프레임간 정규화 좌표 점프가 max_jump 초과면 물리 불가 궤적으로 폐기(§6-c).

    coords_seq = (T, J, C) 또는 프레임별 [joint][xy] 리스트. NaN(가려짐)은 건너뛴다
    (Null 바인딩은 정상). numpy 는 lazy — 순수 계산.
    """
    import numpy as np

    arr = np.asarray(coords_seq, dtype=float)
    if arr.ndim != 3 or arr.shape[0] < 2:
        return False
    xy = arr[..., :2]
    diffs = np.abs(np.diff(xy, axis=0))
    finite = diffs[np.isfinite(diffs)]
    if finite.size == 0:
        return False
    return bool(np.nanmax(finite) > max_jump)


def bone_length_consistent(coords_seq, bone_pairs, *, tol: float = _BONE_LEN_TOL) -> bool:
    """뼈(관절쌍) 길이가 프레임간 tol 이내로 유지되면 정합(True). 강체 위반 시 False.

    bone_pairs = [(joint_i, joint_j), ...] 인덱스쌍. NaN 프레임은 제외. 유효 표본이
    부족하면 판정 불가로 True(보수적 — 폐기 남발 금지).
    """
    import numpy as np

    arr = np.asarray(coords_seq, dtype=float)
    if arr.ndim != 3 or arr.shape[0] < 2 or not bone_pairs:
        return True
    xy = arr[..., :2]
    for i, j in bone_pairs:
        if i >= xy.shape[1] or j >= xy.shape[1]:
            continue
        seg = xy[:, i, :] - xy[:, j, :]
        lengths = np.sqrt((seg ** 2).sum(axis=1))
        lengths = lengths[np.isfinite(lengths)]
        if lengths.size < 2:
            continue
        med = float(np.median(lengths))
        if med <= 1e-9:
            continue
        if float(np.max(np.abs(lengths - med)) / med) > tol:
            return False
    return True


def report_satisfies_deduction_contract(report: dict) -> bool:
    """faults[] 각 항목이 DEDUCTION_CONSUMED_KEYS 측정 필드를 채웠는지 검증(F1).

    각도쌍(student/reference_angle_deg) 또는 폴백(approx_angle_deviation_deg) 중 하나 +
    fault_category(enum) + body_part 가 있어야 감점 엔진이 무수정 소비한다. faults 가
    비었으면(정타) True — 짚을 결함이 없는 정상 케이스.
    """
    faults = (report or {}).get("faults")
    if not faults:
        return True
    for item in faults:
        if not isinstance(item, dict):
            return False
        has_angle_pair = (
            item.get("student_angle_deg") is not None
            and item.get("reference_angle_deg") is not None
        )
        has_fallback = item.get("approx_angle_deviation_deg") is not None
        if not (has_angle_pair or has_fallback):
            return False
        if not item.get("fault_category"):
            return False
        if not item.get("body_part"):
            return False
    return True


# ---------------------------------------------------------------------------
# 행 선택 — holdout 격리 + 고객 소스 anonymized 게이트 (D-12 / Pitfall 2).
# ---------------------------------------------------------------------------
def _is_customer_source(source) -> bool:
    """고객/실사용/파일럿 유래 소스면 True(anonymized 게이트 대상). 표기 변형 흡수."""
    s = str(source or "").lower()
    return any(m in s for m in ("customer", "pilot", "user"))


def eligible_for_distill(row: dict) -> bool:
    """증류 대상 행 판정 — holdout 격리 + s3_key 존재 + 고객 소스 anonymized=true.

    · holdout(hard_negative_eval 등) → 제외(실증 케이스 오염 금지, Pitfall 2).
    · s3_key 부재(미수집) → 제외.
    · 고객 소스(pilot/customer/user)는 anonymized is True 만 통과(D-12, 소급 불가).
    """
    if row.get("holdout"):
        return False
    if not row.get("s3_key"):
        return False
    if _is_customer_source(row.get("source")) and row.get("anonymized") is not True:
        return False
    return True


def selectable_rows(manifest: dict) -> list[dict]:
    """manifest 에서 증류 대상 행만 필터(eligible_for_distill)."""
    return [r for r in (manifest or {}).get("rows", []) if eligible_for_distill(r)]


# ---------------------------------------------------------------------------
# 필터 통계 — 수락/폐기 사유별 카운트 (SUMMARY 기록용).
# ---------------------------------------------------------------------------
@dataclass
class FilterStats:
    """증류 필터 통계 — 수락/폐기 사유별 카운트."""

    accepted: int = 0
    rejected_parse: int = 0
    rejected_judge: int = 0
    rejected_repetition: int = 0
    rejected_physics: int = 0
    rejected_bone: int = 0
    rejected_contract: int = 0
    reasons: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "rejected_parse": self.rejected_parse,
            "rejected_judge": self.rejected_judge,
            "rejected_repetition": self.rejected_repetition,
            "rejected_physics": self.rejected_physics,
            "rejected_bone": self.rejected_bone,
            "rejected_contract": self.rejected_contract,
        }


def evaluate_filters(
    parsed: dict | None,
    judge_score: int,
    coords_seq=None,
    bone_pairs=None,
) -> tuple[bool, str]:
    """단일 증류 후보에 전 필터를 적용 → (accepted, reason).

    순수 — 네트워크 0. reason 은 폐기 사유 문자열('accepted' 이면 수락).
    """
    if parsed is None or not parsed.get("report"):
        return False, "rejected_parse"
    report = parsed["report"]
    thought = parsed.get("thought") or ""
    coaching = report.get("coaching") or ""
    if not judge_passes(judge_score):
        return False, "rejected_judge"
    if has_repetition_loop(thought) or has_repetition_loop(coaching):
        return False, "rejected_repetition"
    if coords_seq is not None and is_physically_impossible(coords_seq):
        return False, "rejected_physics"
    if coords_seq is not None and bone_pairs and not bone_length_consistent(coords_seq, bone_pairs):
        return False, "rejected_bone"
    if not report_satisfies_deduction_contract(report):
        return False, "rejected_contract"
    return True, "accepted"


# ---------------------------------------------------------------------------
# quota probe — 1건 시험 호출 + files.list 잔량 로그 (배치 시작 전 게이트).
# ---------------------------------------------------------------------------
def probe_quota(client, *, judge_model: str = JUDGE_MODEL) -> dict:
    """1건 시험 호출로 크레딧/quota 확인 — 429(RESOURCE_EXHAUSTED) 시 ok=False.

    반환 = {"ok": bool, "residue": int, "error": str|None}. residue = files.list 잔량
    (누수 0 acceptance). 실패해도 예외 대신 dict 로 상태를 알린다(배치가 중단 판단).
    """
    residue = list_file_residue(client)
    try:
        resp = client.models.generate_content(
            model=judge_model,
            contents=["1"],
            config={"temperature": 0.0},
        )
        _ = getattr(resp, "text", None)
        return {"ok": True, "residue": residue, "error": None}
    except Exception as exc:  # noqa: BLE001 - probe 실패는 배치 중단 신호.
        msg = str(exc)
        exhausted = "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper()
        log.warning("quota probe 실패 (exhausted=%s)", exhausted)
        return {"ok": False, "residue": residue, "error": "quota_exhausted" if exhausted else "probe_error"}


def _greenlight_ready() -> bool:
    """belle greenlight env 확인 — 과금 배치는 명시 승인 없이 실행 금지(DR-05)."""
    return os.environ.get(_GREENLIGHT_ENV) == "1"


# ── 기본 대상 관절 (RTMW 133 중 몸통/사지 12 — bind_key_prompt 키 사전 바인딩) ──
DEFAULT_TASK_JOINTS: tuple[str, ...] = (
    "left_ankle", "left_elbow", "left_hip", "left_knee", "left_shoulder", "left_wrist",
    "right_ankle", "right_elbow", "right_hip", "right_knee", "right_shoulder", "right_wrist",
)


def _is_quota_error(exc: Exception) -> bool:
    """429 / RESOURCE_EXHAUSTED 판정 — 발생 시 배치 즉시 중단 신호."""
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper()


def _download_s3(bucket: str, key: str, dest_path: str) -> None:
    """S3 객체 → 로컬 다운로드 (boto3, ap-northeast-2). Pod 는 aws CLI 없음 → boto3."""
    import boto3  # lazy

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.download_file(bucket, key, dest_path)


def _trial_report_path(reports_dir: str, s3_key: str) -> str:
    """행별 진단 파일 경로 — s3_key slug(prefix 충돌 방지, pod_coords 캐시 키와 동일 규칙)."""
    slug = str(s3_key or "unknown").replace("/", "__")
    return os.path.join(reports_dir, f"{slug}.json")


def _save_trial_report(reports_dir: str, s3_key: str, payload: dict) -> str | None:
    """행별 (a) 교사 raw text (b) normalize 후 parsed (c) 수락/폐기 사유를 저장.

    폐기 행 진단이 목적 — 수락/폐기/오류 전부 저장한다(2026-07-10 fix: 시험 배치
    3/3 rejected_contract 인데 원문 미보존으로 확정 진단 불가였던 갭). 저장 실패는
    배치를 막지 않는다(graceful). 반환 = 저장 경로 또는 None.
    """
    try:
        os.makedirs(reports_dir, exist_ok=True)
        path = _trial_report_path(reports_dir, s3_key)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2, sort_keys=True)
        return path
    except Exception:  # noqa: BLE001 - 진단 저장 실패는 배치를 막지 않는다.
        log.warning("trial report 저장 실패 (graceful): %s", s3_key)
        return None


# ---------------------------------------------------------------------------
# 배치 러너 — max_rows 상한 + 429 즉시 중단 + File API 잔여물 검사 (belle-gated).
# ---------------------------------------------------------------------------
def run_trial_batch(
    manifest: dict,
    scratch_dir: str,
    *,
    max_rows: int = 10,
    bucket: str = "sunity-motion-pilot-videos",
    joint_keys=DEFAULT_TASK_JOINTS,
    coords_provider=None,
    client=None,
) -> dict:
    """증류 시험 배치 — 최대 max_rows 행만 처리(teacher ≤ max_rows, judge ≤ max_rows).

    행당 흐름: S3 다운로드 → distill_video(업로드→교사→즉시 삭제 finally) → judge →
    evaluate_filters → 수락/폐기 집계. 429/RESOURCE_EXHAUSTED 발생 시 즉시 중단하고
    aborted 사유를 반환한다(belle 승인 범위: 시험 배치 1회, DR-05).

    RTMW 좌표는 coords_provider(row) 로 주입 — 미주입 시 빈 서브샘플([])로 video-only
    호출(로컬 트라이얼은 Pod RTMW 추출 없음). 반환에 명시.

    행별 진단 보존(2026-07-10 fix): 교사 raw text + normalize 후 parsed + 수락/폐기
    사유를 scratch_dir/trial_reports/<s3_key slug>.json 에 저장한다 — 수락/폐기 모두.

    반환 dict: {stats, per_row, aborted, residue_before, residue_after, elapsed_s,
    n_processed, coords_injected, accepted_samples, trial_reports_dir}. S3 업로드/최종
    산출은 하지 않는다.
    """
    client = client or _ensure_client()
    os.makedirs(scratch_dir, exist_ok=True)
    reports_dir = os.path.join(scratch_dir, "trial_reports")
    rows = selectable_rows(manifest)[: max(0, int(max_rows))]
    stats = FilterStats()
    per_row: list[dict] = []
    accepted_samples: list[dict] = []
    aborted = None
    residue_before = list_file_residue(client)
    coords_injected = coords_provider is not None
    start = time.monotonic()

    for row in rows:
        s3_key = row["s3_key"]
        local = os.path.join(scratch_dir, os.path.basename(s3_key))
        vh = None
        parsed = None
        try:
            _download_s3(bucket, s3_key, local)
            try:
                from sunity_shared.analysis.technique_cache import compute_video_hash

                vh = compute_video_hash(local)
            except Exception:  # noqa: BLE001 - hash 실패는 배치를 막지 않는다.
                vh = None
            coords_by_frame = coords_provider(row) if coords_provider else []
            # motion 주입 — 기술조건부 판정 유도(무맥락 180° 위양성 방지, 2026-07-10 2차).
            parsed = distill_video(
                client, local, coords_by_frame, joint_keys, motion=row.get("motion")
            )
            judge_score = 0
            if parsed and parsed.get("report"):
                # motion 주입 — judge 도 결함 판정 타당성의 동작 맥락 확보(3차 fix).
                judge_score = judge_report(
                    client, parsed["report"], motion=row.get("motion")
                )
            accepted, reason = evaluate_filters(parsed, judge_score)
        except Exception as exc:  # noqa: BLE001 - 429 중단 / 기타 오류 폐기 집계.
            if _is_quota_error(exc):
                aborted = f"quota_exhausted at {s3_key}: {str(exc)[:160]}"
                per_row.append({"s3_key": s3_key, "result": "ABORT_429"})
                _save_trial_report(reports_dir, s3_key, {
                    "s3_key": s3_key, "result": "ABORT_429", "error": str(exc)[:200],
                    "raw_text": (parsed or {}).get("raw_text"),
                })
                break
            stats.rejected_parse += 1
            per_row.append({"s3_key": s3_key, "result": "error", "error": str(exc)[:160]})
            _save_trial_report(reports_dir, s3_key, {
                "s3_key": s3_key, "result": "error", "error": str(exc)[:200],
                "raw_text": (parsed or {}).get("raw_text"),
            })
            continue
        finally:
            try:
                os.remove(local)
            except OSError:
                pass

        setattr(stats, reason, getattr(stats, reason) + 1)
        per_row.append(
            {"s3_key": s3_key, "motion": row.get("motion"), "judge": judge_score, "result": reason}
        )
        # (a) 교사 raw (b) normalize 후 parsed (c) 사유 — 수락/폐기 모두 보존(진단 갭 fix).
        _save_trial_report(reports_dir, s3_key, {
            "s3_key": s3_key,
            "motion": row.get("motion"),
            "video_hash": vh,
            "raw_text": (parsed or {}).get("raw_text"),
            "parsed": {
                "thought": (parsed or {}).get("thought"),
                "report": (parsed or {}).get("report"),
            },
            "judge": judge_score,
            "result": reason,
        })
        if accepted and parsed:
            accepted_samples.append(
                {"video_hash": vh, "s3_key": s3_key, "motion": row.get("motion"),
                 "thought": parsed.get("thought"), "report": parsed.get("report")}
            )

    elapsed = time.monotonic() - start
    residue_after = list_file_residue(client)
    return {
        "stats": stats.as_dict(),
        "per_row": per_row,
        "aborted": aborted,
        "residue_before": residue_before,
        "residue_after": residue_after,
        "elapsed_s": round(elapsed, 2),
        "n_processed": len([p for p in per_row if p.get("result") != "ABORT_429"]),
        "coords_injected": coords_injected,
        "accepted_samples": accepted_samples,
        "trial_reports_dir": reports_dir,
    }


if __name__ == "__main__":  # pragma: no cover - 실행은 Task 4(belle-gated Pod 세션).
    if not _greenlight_ready():
        raise SystemExit(
            f"{_GREENLIGHT_ENV}=1 미설정 — 증류 배치는 belle 승인(DR-05) 후 실행. "
            "순수 필터/행선택 로직은 test_gemini_teacher.py 로 검증됨."
        )
    raise SystemExit("run_batch 실 실행은 22-04 Task 4(라이브 Pod + Gemini)에서 배선한다.")
