"""Phase 19 D-05 — Vision grounding spike: fault/correct 페어 비교.

목적 (19-CONTEXT D-05):
  보유 정은지 fault/correct 페어를 Gemini Vision 으로 비교 분석해
  known-answer 검증 앵커를 확보한다.
    1. "이 동작에서 정은지가 어디를 틀렸나" 정성 ground-truth (fault 위치/종류).
    2. 대략적 관절 각도 / 뻗기-갭 범위 (sanity 앵커).
  → 정답을 *알고* 재설계 채점기(D-01 감점식)를 known-answer 테스트.
  → 동시에 (a) 비전-추론 접근 도메인 de-risk, (b) Phase 18 eval fault 라벨 생성.

★ 경계 (절대 — [[scoring-redesign-must-generalize-no-overfit]]):
  이 출력은 sanity 앵커 / 일반화 검증용이지 임계값 curve-fit 타깃이 아니다.
  정답을 *아는 것* != 거기에 *맞추는 것*. 보유 셋 overfit 금지.

★ 객관성 가드 ([[analysis-objectivity-no-human-scores]]):
  Gemini 는 점수 숫자(예: 41/100, 89%) 를 출력하지 않는다. fault 위치/종류 +
  관절 각도/뻗기-갭(기하량) + 심각도 정성 라벨(minor/moderate/major) 만.
  점수 라벨링은 사람/AI 무관 영구 금지.

Pod 불필요: Gemini 는 외부 API. fault/correct 영상은 로컬.

키 로드:
  env GEMINI_API_KEY 우선. 미설정 시 SSM `/sunity/motion/gemini-api-key`
  (단 default AWS 프로필=sunity-api 는 권한 없음 → sunity-motion 프로필로 env export 권장):

    export GEMINI_API_KEY=$(aws ssm get-parameter \\
      --name /sunity/motion/gemini-api-key --with-decryption \\
      --query 'Parameter.Value' --output text \\
      --region ap-northeast-2 --profile sunity-motion)

실행:
  PYTHONPATH=backend/shared/python:. python3 \\
    -m backend.research.spikes.spike_vision_grounding_pair \\
    --motion climb \\
    --fault "~/Downloads/정은지 선수 추가 영상/클라임(잘못된예시).mp4" \\
    --correct "~/Downloads/정은지 선수 추가 영상/잘된 예시/fixtures:climb-correct.mp4" \\
    --out backend/research/spikes/reports/spike_vision_grounding_climb.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("spike_vision_grounding")

MODEL = "gemini-3.1-pro-preview"  # [[gemini-latest-model-versions]] — suffix 필수.
_FILES_TIMEOUT_S = 180.0
_FILES_POLL_S = 3.0


# ─────────────────────────── 키 로드 ───────────────────────────


def load_api_key() -> str:
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        log.info("Gemini 키: env GEMINI_API_KEY (len=%d)", len(inline))
        return inline
    # SSM fallback — 기본 프로필 권한 없으면 실패. env export 권장.
    import boto3  # lazy

    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    resp = ssm.get_parameter(
        Name="/sunity/motion/gemini-api-key", WithDecryption=True
    )
    log.info("Gemini 키: SSM /sunity/motion/gemini-api-key")
    return resp["Parameter"]["Value"]


# ─────────────────────────── Files API ───────────────────────────


def _mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".mov", ".qt"):
        return "video/quicktime"
    if ext == ".webm":
        return "video/webm"
    return "video/mp4"


def _state(f) -> str:
    st = getattr(f, "state", None)
    if st is None:
        return ""
    return getattr(st, "name", None) or str(st)


def _ascii_safe_path(path: str, label: str) -> tuple[str, str | None]:
    """genai SDK 가 파일명을 HTTP 헤더(ascii)에 넣어 한글 파일명은 UnicodeEncodeError.
    비-ASCII 경로면 ASCII 임시 파일로 복사 후 그 경로 반환. (tmp_path 는 정리용)."""
    name = Path(path).name
    try:
        name.encode("ascii")
        return path, None
    except UnicodeEncodeError:
        import shutil
        import tempfile

        tmp = tempfile.NamedTemporaryFile(
            prefix=f"vgrounding_{label}_", suffix=Path(path).suffix, delete=False
        )
        tmp.close()
        shutil.copyfile(path, tmp.name)
        log.info("[%s] 한글 파일명 → ASCII 임시 복사: %s", label, tmp.name)
        return tmp.name, tmp.name


def upload_and_wait(client, path: str, label: str):
    upload_path, tmp_path = _ascii_safe_path(path, label)
    log.info("[%s] 업로드 시작: %s", label, path)
    uploaded = client.files.upload(
        file=upload_path, config=genai_types.UploadFileConfig(mime_type=_mime(path))
    )
    start = time.monotonic()
    while _state(uploaded) == "PROCESSING":
        if time.monotonic() - start > _FILES_TIMEOUT_S:
            raise TimeoutError(f"[{label}] Files API processing > {_FILES_TIMEOUT_S}s")
        time.sleep(_FILES_POLL_S)
        uploaded = client.files.get(name=uploaded.name)
    state = _state(uploaded)
    if tmp_path is not None:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    if state != "ACTIVE":
        raise RuntimeError(f"[{label}] Files API state={state} (ACTIVE 아님)")
    log.info("[%s] ACTIVE (%.1fs)", label, time.monotonic() - start)
    return uploaded


# ─────────────────────────── 프롬프트 ───────────────────────────

PROMPT = """\
당신은 IPSF(국제폴스포츠연맹) Code of Points 기준에 정통한 폴스포츠 동작 분석가입니다.

두 영상은 **같은 선수가 같은 동작('{motion}')을 수행한 것**입니다.
- 첫 번째 = CORRECT (정확하게 수행한 기준 영상)
- 두 번째 = FAULT (의도적으로 잘못 수행한 영상)

두 영상을 직접 비교해, FAULT 영상에서 **무엇이·어디가 틀렸는지**를 IPSF 기준으로 짚으세요.

규칙 (반드시 준수):
1. 점수를 매기지 마세요. "41점", "89%", "8/10" 같은 숫자 점수/일치율 표현 금지.
2. 대신 **관절 각도(도)**, **신체 라인의 정렬/굽음**, **뻗기 갭(완전 신전 대비 부족분, 도)** 같은
   기하학적/관찰적 사실만 기술하세요. 각도는 "약 X도" 수준의 추정으로 충분합니다.
3. 심각도는 minor / moderate / major 세 단계 정성 라벨로만 표기.
4. CORRECT 와 FAULT 의 **차이**에 집중. 둘 다 같은 선수이므로 체형이 아니라 자세 수행의 차이를 보세요.
5. 한국어로 작성. 추측이 불확실하면 confidence 를 낮게 표기.

각 차이점마다: 신체 부위, CORRECT 상태, FAULT 상태, 대략적 각도 편차(도), 심각도, IPSF 관점 설명.
가장 지배적인 단일 결함(primary_fault)을 하나 지목하세요 (감점식 채점에서 점수를 크게 끌어내릴 결함)."""


def build_schema() -> dict:
    """response_schema (점수 필드 없음 — 객관성 가드)."""
    return {
        "type": "object",
        "properties": {
            "motion": {"type": "string"},
            "primary_fault": {
                "type": "string",
                "description": "점수를 가장 크게 끌어내릴 지배적 단일 결함 (도메인 설명)",
            },
            "differences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "body_part": {"type": "string"},
                        "correct_state": {"type": "string"},
                        "fault_state": {"type": "string"},
                        "approx_angle_deviation_deg": {
                            "type": "number",
                            "description": "CORRECT 대비 FAULT 각도 편차 추정(도). 미상이면 0.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "major"],
                        },
                        "ipsf_note": {"type": "string"},
                    },
                    "required": [
                        "body_part",
                        "correct_state",
                        "fault_state",
                        "severity",
                    ],
                },
            },
            "extension_gaps": {
                "type": "array",
                "description": "완전 신전 대비 뻗기 부족 관절 (뻗기-갭)",
                "items": {
                    "type": "object",
                    "properties": {
                        "joint": {"type": "string"},
                        "correct_extension": {"type": "string"},
                        "fault_extension": {"type": "string"},
                        "approx_gap_deg": {"type": "number"},
                    },
                    "required": ["joint", "approx_gap_deg"],
                },
            },
            "overall_qualitative": {
                "type": "string",
                "description": "FAULT 영상의 전반적 자세 품질 정성 평가 (숫자 점수 금지)",
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
        },
        "required": ["motion", "primary_fault", "differences", "overall_qualitative"],
    }


# 점수 라벨 누출 방어 — 응답 text 에 점수/일치율 숫자 패턴 검출 시 경고.
import re

_SCORE_PATTERN = re.compile(r"\b\d{1,3}\s*(점|/\s*100|/\s*10|%|퍼센트)")


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 19 D-05 vision grounding pair spike")
    p.add_argument("--motion", required=True)
    p.add_argument("--fault", required=True, help="FAULT 영상 로컬 path")
    p.add_argument("--correct", required=True, help="CORRECT 영상 로컬 path")
    p.add_argument("--out", required=True, help="결과 JSON 경로")
    p.add_argument("--model", default=MODEL)
    args = p.parse_args()

    fault_path = os.path.expanduser(args.fault)
    correct_path = os.path.expanduser(args.correct)
    for label, path in (("fault", fault_path), ("correct", correct_path)):
        if not os.path.isfile(path):
            log.error("[%s] 파일 없음: %s", label, path)
            return 2

    api_key = load_api_key()
    client = genai.Client(api_key=api_key)

    correct_file = upload_and_wait(client, correct_path, "CORRECT")
    fault_file = upload_and_wait(client, fault_path, "FAULT")

    prompt = PROMPT.format(motion=args.motion)
    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=build_schema(),
        temperature=0.1,
        max_output_tokens=4096,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=-1),
        http_options=genai_types.HttpOptions(timeout=180_000),
    )

    log.info("generate_content 호출 (model=%s)...", args.model)
    t0 = time.monotonic()
    try:
        # CORRECT 먼저, FAULT 두 번째 — 프롬프트 순서 정합.
        response = client.models.generate_content(
            model=args.model,
            contents=[
                "CORRECT 영상:",
                correct_file,
                "FAULT 영상:",
                fault_file,
                prompt,
            ],
            config=config,
        )
    except genai_errors.APIError as exc:
        log.error("Gemini APIError code=%s: %s", getattr(exc, "code", "?"), exc)
        return 3
    log.info("응답 수신 (%.1fs)", time.monotonic() - t0)

    raw_text = getattr(response, "text", "") or ""
    if _SCORE_PATTERN.search(raw_text):
        log.warning(
            "응답에 점수/일치율 숫자 패턴 검출 — 객관성 검토 필요 (저장은 진행)."
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        log.error("JSON 파싱 실패. raw text 저장.")
        payload = {"_raw": raw_text}

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "motion": args.motion,
        "model": args.model,
        "fault_video": fault_path,
        "correct_video": correct_path,
        "analysis": payload,
        "boundary_note": (
            "sanity 앵커 / 일반화 검증용. 임계값 curve-fit 타깃 아님. "
            "점수 라벨 금지 (객관성)."
        ),
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("저장: %s", out_path)

    # 콘솔 요약
    a = payload
    print("\n" + "=" * 60)
    print(f"동작: {args.motion}")
    print(f"지배 결함(primary_fault): {a.get('primary_fault', '?')}")
    print(f"신뢰도: {a.get('confidence', '?')}")
    print("-- 차이점 --")
    for d in a.get("differences", []):
        dev = d.get("approx_angle_deviation_deg")
        dev_s = f" (~{dev}도)" if dev else ""
        print(f"  [{d.get('severity', '?')}] {d.get('body_part', '?')}: "
              f"{d.get('fault_state', '?')}{dev_s}")
    print("-- 뻗기-갭 --")
    for g in a.get("extension_gaps", []):
        print(f"  {g.get('joint', '?')}: ~{g.get('approx_gap_deg', '?')}도")
    print(f"-- 정성 평가 --\n  {a.get('overall_qualitative', '?')}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
