"""gemini_vision_scorer — Gemini 결함-심각도 어댑터 (Plan 20-02).

목적 (20-CONTEXT D-01/D-02/D-06):
  Gemini Vision 으로 영상의 **결함 종류/위치/심각도(severity enum)** 만 산출한다.
  점수는 절대 내지 않는다 — severity 는 20-01 의 apply_downward_cap 에 먹여
  하향 캡으로만 변환된다(비전이 점수를 올려 위양성을 재발시키는 경로 0).

  line 차원이 아니라 overall cap 용 severity 다. 20-01(순수 cap 코어)과
  20-03(파이프라인 wiring) 사이의 adapter 경계.

객관성 hard gate (D-02 / [[analysis-objectivity-no-human-scores]] / MEDIUM-1):
  · build_schema() 의 response_schema 에 score/overall/rating/점수 필드 0.
    spike(spike_vision_grounding_pair.py:217)의 overall_qualitative 를
    production 스키마에 **복사 금지**(strict no-overall).
  · VisionVerdict 데이터클래스에 score 속성 영구 부재.
  · _SCORE_PATTERN = 구현 leak-guard. 응답 raw_text 에 "NN점/NN/100/NN%"
    누출 시 verdict 폐기(None) + WARNING. (이 상수의 *존재* 는 위반 아님 —
    내성검사 테스트가 build_schema()/dataclass 만 검사하므로 충돌 없음.)

결정론 (D-06 / TRUST-06 / MEDIUM-2):
  · temperature=0.0 (spike 0.1 → 0).
  · 전용 VisionVetoCache 키 =
    (video_hash, model_name, PROMPT_VERSION, SCHEMA_VERSION,
     input_granularity, at_seconds_bucket).
    recognizer 의 (video_hash, model, yaml_version) 키 재사용 금지 — severity
    verdict 는 prompt/schema 민감. **PROMPT_VERSION/SCHEMA_VERSION 변경 시
    stale verdict 자동 무효화** (프롬프트/스키마를 바꾸면 아래 상수도 bump 할 것).
  · input_granularity('whole') 를 키에 명시 포함 — future frame-input verdict 가
    whole-video verdict 와 키 충돌하지 않도록(iter2 non-blocking).
  · temp 0 단독으로는 bit-deterministic 보장 아님 — 실 보장은 캐시. 실 결정론
    (cache-warm byte-identity) 검증은 20-04 Pod sweep.

adapter-boundary (iter2 MEDIUM-1):
  · assess_fault_severity 는 **adapter-local 전제조건만** 검사 —
    API 키/client, 캐시, local 파일, Gemini 응답 유효성.
  · feature 토글은 **검사하지 않는다** — 토글은 pipeline(20-03)이 단독 소유.
    본 모듈은 pipeline 함수를 import 하지 않고 토글 helper 를 정의/복제하지
    않는다(env helper 중복 = drift 리스크). analysis core 는 import-light 유지.
    (정확한 토글 심볼 이름은 test_adapter_does_not_own_toggle 가 소스 부재로 단언.)

graceful (Pitfall 5):
  · 키 부재/API 실패 → verdict=None + WARNING (raise 0, 분석 흐름 안 막음).
    silent no-op 차단은 20-03 이 audit 필드(visionVeto)로 완성.

B4 hard gate:
  · caller 의 local_video_path 만 사용 — 영상 재다운로드/RTMW 재실행 0.

보안 (T-20-06):
  · GEMINI_API_KEY 절대 로그 금지. PII = video_hash 만(경로/원본 미로그).

lazy-import (coach_writer/recognizer 패턴, D-16):
  · google.genai 는 모듈 top-level import 금지 — _ensure_client() 함수 내부에서만.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

# ─────────────────── 버전 상수 (MEDIUM-2) ───────────────────
#
# 프롬프트 문자열(_PROMPT) 또는 build_schema() 구조를 변경하면 아래 상수도 반드시
# bump 해야 한다 — VisionVetoCache 키에 들어가 stale verdict 를 무효화한다.
# bump 하지 않으면 옛 프롬프트/스키마로 산출된 verdict 가 새 프롬프트/스키마 결과로
# 잘못 살아남는다(비결정론·오 verdict).
PROMPT_VERSION = "v6.1"  # v6.1 (2026-06-21): multi-fault — N샘플 differences union(median 1개 채택 폐기) + worst-pose 힌트 완화(전신 점검). severity 캡=median 유지 → cache 무효화
SCHEMA_VERSION = "v5.0"  # v5.0: 집계 verdict = 새 cache generation (단일 verdict 의미 변경)

# ─────────────────── 비교 multi-sample 집계 (Phase 20 robustify) ───────────────────
#
# belle 2026-06-20: Gemini 의 비교 판단은 결함을 일관되게 "본다"(5/5 같은 설명)지만
# 단일 severity 라벨이 minor↔moderate 로 흔들린다 → 단일 샘플은 비결정적. 비교 모드만
# N=VISION_VETO_SAMPLES 회 generateContent 후 rank-median severity 로 집계한다.
# 업로드는 1회만(ref+student 핸들 재사용) — N 회는 generateContent 만 반복(시간 절약).
# none=0/minor=1/moderate=2/major=3, 짝수 개수는 lower-middle(보수적). 0 파싱 → None.
# 집계 verdict 만 캐시 (cache-miss 에서만 N 샘플; hit 는 deterministic 반환).
VISION_VETO_SAMPLES = max(1, int(os.environ.get("GEMINI_VISION_VETO_SAMPLES", "3")))

# Gemini 모델 — [[gemini-latest-model-versions]] suffix(-preview) 필수.
DEFAULT_VISION_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")

# 입력 단위 마커 — 현재 항상 'whole'(whole-video 업로드, spike 패턴 = 안전 default).
# 미래 frame-input 최적화 시 'frame' 등으로 분기 → 캐시 키 충돌 방지(iter2 non-blocking).
INPUT_GRANULARITY = "whole"

# 'none' = 명백한 결함 없음(정타) → cap 미적용. over-penalization fix (2026-06-20).
_SEVERITY_ENUM = ("none", "minor", "moderate", "major")
_ALLOWED_SEVERITY = set(_SEVERITY_ENUM)

# 점수 라벨 누출 방어 — 응답 text 에 점수/일치율 숫자 패턴 검출 시 verdict 폐기.
# spike line 233 정규식 재사용. _SCORE_PATTERN 의 *존재* 는 객관성 위반이 아니라
# leak guard (내성검사 테스트는 build_schema()/dataclass 만 검사).
_SCORE_PATTERN = re.compile(r"\b\d{1,3}\s*(점|/\s*100|/\s*10|%|퍼센트)")

_FILES_TIMEOUT_S = 180.0
_FILES_POLL_S = 3.0

# 모듈 캐시 싱글톤 (recognizer 패턴) — _ensure_client() 가 1회만 client 생성.
_CLIENT = None


# ─────────────────── VisionVerdict 값객체 ───────────────────


@dataclass(frozen=True)
class VisionVerdict:
    """Gemini 결함-심각도 verdict (객관성 — score 필드 영구 부재).

    severity enum 만 20-01 의 apply_downward_cap 에 먹인다. 사람/AI 점수 라벨을
    ground truth 로 두는 것은 영구 금지([[analysis-objectivity-no-human-scores]]).

    Fields:
      primary_fault: 지배적 단일 결함 (도메인 자연어 설명). 점수 아님.
      severity: 'minor' | 'moderate' | 'major'. apply_downward_cap 입력.
      differences: 차이점 dict tuple (body_part/correct_state/fault_state/
        approx_angle_deviation_deg/severity/ipsf_note). nested-array 회피로 tuple.
    """

    primary_fault: str
    severity: str
    differences: tuple


# ─────────────────── response_schema (MEDIUM-1, no-score/no-overall) ───────────────────


def build_schema() -> dict:
    """response_schema — score/overall/rating/점수 필드 0 + overall_qualitative 0.

    spike build_schema(167-205) 리팩터 — spike 의 overall_qualitative(217) 는
    **복사 금지**(strict no-overall, MEDIUM-1). severity enum 만, 점수 0.
    """
    return {
        "type": "object",
        "properties": {
            "motion": {"type": "string"},
            "dominant_severity": {
                "type": "string",
                "enum": list(_SEVERITY_ENUM),
                "description": "영상 전체의 지배적 결함 수준. 정타(결함 없음)=none → cap 미적용. 점수 아님.",
            },
            "primary_fault": {
                "type": "string",
                "description": "지배적 단일 결함 (결함 없으면 '없음'. 도메인 설명, 숫자 점수 금지)",
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
                            "description": "기준 대비 각도 편차 추정(도). 미상이면 0.",
                        },
                        "severity": {
                            "type": "string",
                            "enum": list(_SEVERITY_ENUM),
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
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
        },
        "required": ["motion", "dominant_severity", "primary_fault", "differences"],
    }


# ─────────────────── 프롬프트 ───────────────────

_PROMPT = """\
당신은 IPSF(국제폴스포츠연맹) Code of Points 기준에 정통한 폴스포츠 동작 분석가입니다.

이 영상의 폴스포츠 동작 수행을 IPSF 기준으로 **공정하게 평가**하세요. 결함을 억지로
찾아내는 것이 목적이 아닙니다 — **명백한 결함이 있으면 그 심각도를, 없으면 "없음"을** 보고합니다.

가장 중요한 규칙 (반드시 준수):
1. **정타(올바른 수행)는 결함을 만들어내지 마세요.** 자세가 IPSF 기준에 부합하고 명백한
   결함이 없으면 dominant_severity='none' + differences=[] (빈 배열) + primary_fault='없음'
   으로 응답하세요. 전문 선수/숙련 수행은 대부분 'none' 또는 'minor' 입니다 — 사소한
   촬영 각도·미세 흔들림을 결함으로 격상하지 마세요.
2. dominant_severity 기준 (영상 전체의 지배적 결함 수준):
   - none     : 명백한 결함 없음 (IPSF 기준 정타). 점수를 깎을 이유 없음.
   - minor    : 경미 — 다듬으면 좋지만 동작 성립에 지장 없음.
   - moderate : 분명히 보이는 부분적 결함 (예: 다리 신전 부족, 라인 약간 흐트러짐).
   - major    : 동작의 본질/성공을 해치는 명백한 결함 (예: 핵심 그립 풀림, 핵심 자세 붕괴).
   확실치 않으면 한 단계 낮게(보수적으로) 보고하세요.
3. 점수를 매기지 마세요. "85점", "89%", "8/10", "100/100" 같은 숫자 점수/일치율 표현 금지.
   대신 **관절 각도(도)**, **라인 정렬/굽음**, **뻗기 갭(도)** 같은 관찰적 사실만 기술.
4. differences 에는 **실제로 관찰된 결함만** 담으세요 (없으면 빈 배열). 각 항목 severity 도
   none/minor/moderate/major 로 보수적으로.
5. primary_fault = 가장 지배적인 단일 결함 (결함 없으면 '없음').
6. 한국어로 작성. 추측이 불확실하면 confidence 를 낮게 표기."""


def _build_prompt(at_seconds: float | None) -> str:
    """프롬프트 + (있으면) worst-pose 시점 힌트. at_seconds 는 지금은 힌트일 뿐.

    프롬프트 문자열을 바꾸면 PROMPT_VERSION 도 bump 할 것 (캐시 무효화).
    """
    if at_seconds is None:
        return _PROMPT
    return f"{_PROMPT}\n\n참고: 약 {at_seconds:.1f}초 부근의 지배 결함 pose 에 특히 주목하세요."


# ─────────────────── 비교(reference-anchored) 프롬프트 (v4.0, Mode1) ───────────────────
#
# belle 결정 (2026-06-20): Mode1 = 기준(정은지 정타) 영상 대비 학생 영상 비교.
# 진공 단일 영상 판정은 mild fault 와 정타를 구별하지 못해 위양성(정타→50) 또는
# 위음성(잘못된 동작→100)을 낸다. 코치처럼 기준 영상과 비교하는 것이 원칙적 fix.
#
# curve-fit 금지 절대원칙 ([[scoring-redesign-must-generalize-no-overfit]]):
#   이 프롬프트는 **완전 generic** 비교다. 특정 동작명(kip-up 등) 0, 기대 답/점수 0,
#   특정 테스트 영상이 통과하도록 튜닝한 임계 0. severity 는 Gemini 의 비교 판단에서만
#   나온다. 일반화 검증은 orchestrator 가 Pod 6-pair eval 로 별도 수행한다.
_COMPARISON_PROMPT = """\
당신은 IPSF(국제폴스포츠연맹) Code of Points 기준에 정통한 폴스포츠 동작 분석가입니다.

두 개의 영상을 받습니다 — **같은 동작**을 수행한 두 영상입니다:
  · 첫 번째 영상 = IPSF 기준에 부합하는 **기준(정타) 영상**.
  · 두 번째 영상 = 평가 대상인 **학생 영상**.

학생 영상이 기준 영상 대비 얼마나 정확하게 동작을 수행했는지 **공정하게 비교**하세요.
목적은 결함을 억지로 찾는 것이 아니라, **기준 대비 명확하고 관찰 가능한 편차가 있으면
그 심각도를, 없으면 "없음"을** 보고하는 것입니다.

가장 중요한 규칙 (반드시 준수):
1. **기준과 사실상 동일하거나 사소한 차이만 있으면 결함을 만들어내지 마세요.** 학생이
   기준과 거의 같은 수준으로 수행했으면 dominant_severity='none' + differences=[] (빈
   배열) + primary_fault='없음' 으로 응답하세요. 억지 결함 격상 금지.
2. **촬영 각도/거리/배경/화질/조명/카메라 흔들림의 차이는 결함이 아닙니다.** 두 영상의
   촬영 조건이 달라도 그 자체를 편차로 보고하지 마세요. 오직 학생의 **자세/관절 각도/
   신전/라인** 이 기준 대비 어떻게 다른지만 평가하세요.
3. dominant_severity 기준 (기준 영상 대비 학생의 지배적 편차 수준):
   - none     : 기준과 사실상 동일 — 명확한 편차 없음. 점수를 깎을 이유 없음.
   - minor    : 경미한 편차 — 다듬으면 좋지만 동작 성립에 지장 없음.
   - moderate : 분명히 보이는 부분적 편차 (예: 기준 대비 다리 신전 부족, 라인 흐트러짐).
   - major    : 동작의 본질/성공을 해치는 명확한 편차 (예: 핵심 그립/자세가 기준과 다름).
   확실치 않으면 한 단계 낮게(보수적으로) 보고하세요.
4. 점수를 매기지 마세요. "85점", "89%", "8/10", "100/100" 같은 숫자 점수/일치율 표현 금지.
   대신 **기준 대비 관절 각도(도)**, **라인 정렬/굽음**, **뻗기 갭(도)** 같은 관찰적
   비교 사실만 기술하세요.
5. **전신을 빠짐없이 점검하세요 — 결함은 하나만 보고하지 마세요.** 다리/무릎/발끝,
   양 팔/팔꿈치/손목, 어깨, 골반/힙, 코어/허리, 전체 라인, 그립을 **각각** 기준과
   대조해, 명확하고 관찰 가능한 편차가 있는 부위를 **모두** differences 에 담으세요.
   예: 다리 신전 부족 + 왼팔이 기준보다 안쪽으로 굽음 + 라인 흐트러짐 → 세 항목 모두.
   (단, 1·2번 규칙은 그대로 — 정타/사소차/촬영조건은 결함이 아닙니다. 빠짐없이 보되
   억지로 만들지는 마세요.)
6. differences 각 항목 severity 는 none/minor/moderate/major 로 보수적으로. 각 항목에
   기준 대비 관찰 사실(correct_state/fault_state/approx_angle_deviation_deg/ipsf_note)을
   구체적으로 채우세요.
7. primary_fault = 기준 대비 가장 지배적인 단일 편차 (편차 없으면 '없음'). dominant_severity
   는 영상 전체의 **지배적** 편차 수준 1개 (개수가 아니라 가장 심한 정도 기준).
8. 한국어로 작성. 비교가 불확실하면 confidence 를 낮게 표기."""


def _build_comparison_prompt(at_seconds: float | None) -> str:
    """비교 프롬프트 + (있으면) worst-pose 시점 힌트. _build_prompt 미러.

    프롬프트 문자열을 바꾸면 PROMPT_VERSION 도 bump 할 것 (캐시 무효화).
    """
    if at_seconds is None:
        return _COMPARISON_PROMPT
    # C1: 힌트가 시선을 지배 부위 하나로 좁히지 않게 — 전신 점검을 함께 명시.
    return (
        f"{_COMPARISON_PROMPT}\n\n참고: 약 {at_seconds:.1f}초 부근이 지배 편차 pose 일 "
        "수 있으나, **영상 전체에서 다른 부위(특히 팔·어깨·코어)의 편차도 함께** "
        "빠짐없이 점검하세요."
    )


# ─────────────────── VisionVetoCache (전용, MEDIUM-2 + iter2) ───────────────────


@dataclass
class VisionVetoCache:
    """severity verdict 전용 캐시 — recognizer TechniqueCache 키 재사용 금지.

    키 = (video_hash, reference_hash, model_name, PROMPT_VERSION, SCHEMA_VERSION,
          input_granularity, at_seconds_bucket).
      · reference_hash 포함 (v4.0) → 비교(reference-anchored) verdict 는 (학생, 기준)
        PAIR 에 keying. 기준 영상이 바뀌면 다른 키 (다른 비교 = 다른 verdict).
        단일 영상(비교 아님) 경로는 reference_hash=None → 'noref' bucket.
      · PROMPT_VERSION/SCHEMA_VERSION 포함 → prompt/schema bump 시 자동 cache-miss
        (MEDIUM-2 stale 무효화).
      · input_granularity 포함 → whole-video verdict 와 future frame-input verdict
        키 충돌 0 (iter2 non-blocking).
      · at_seconds_bucket = at_seconds 를 정수초로 양자화(None → 'whole').

    저장 구조는 technique_cache 의 Firestore-backed 2단 layer 를 모방하되 전용
    namespace(_VISION_VETO_NS) 로 분리. in-memory layer = Pod 단일 분석 중복 흡수.
    Firestore I/O 는 _backend_get/_backend_put (lazy import — D-16, 실패 graceful).
    """

    _VISION_VETO_NS = "vision_veto"

    @staticmethod
    def build_key(
        *,
        video_hash: str,
        model_name: str,
        input_granularity: str = INPUT_GRANULARITY,
        at_seconds: float | None = None,
        reference_hash: str | None = None,
    ) -> str:
        """캐시 키 직렬화 — PROMPT_VERSION/SCHEMA_VERSION 은 호출 시점 상수 반영.

        PROMPT_VERSION/SCHEMA_VERSION 을 모듈 globals 에서 읽으므로 monkeypatch
        (테스트) / 실 bump 모두 즉시 키에 반영된다(stale 무효화).

        reference_hash (v4.0): 비교(reference-anchored) 경로면 기준 영상 hash 를 키에
        포함 → (학생, 기준) PAIR keying. None(단일 영상 경로)이면 'noref'.
        """
        bucket = "whole" if at_seconds is None else f"t{int(round(at_seconds))}"
        ref_bucket = "noref" if reference_hash is None else reference_hash
        # 모듈 globals 참조 — 테스트 monkeypatch 가 키에 반영되도록 globals() 경유.
        prompt_v = globals()["PROMPT_VERSION"]
        schema_v = globals()["SCHEMA_VERSION"]
        # N(samples) 변경 = 다른 집계 verdict → 키에 포함해 stale 무효화 (Phase 20).
        samples = globals()["VISION_VETO_SAMPLES"]
        return ":".join(
            (
                VisionVetoCache._VISION_VETO_NS,
                video_hash,
                ref_bucket,
                model_name,
                prompt_v,
                schema_v,
                input_granularity,
                bucket,
                f"n{samples}",
            )
        )

    def __init__(self) -> None:
        self._memory: dict[str, dict] = {}

    # ── lookup / store (verdict dict round-trip) ──

    def lookup(self, key: str) -> VisionVerdict | None:
        """키 → in-memory → Firestore. hit 시 VisionVerdict 복원, miss 시 None."""
        if key in self._memory:
            return self._verdict_from_doc(self._memory[key])
        try:
            doc = self._backend_get(key)
        except Exception as exc:  # noqa: BLE001 - Firestore 오류 graceful
            log.warning("VisionVetoCache backend lookup 실패 (miss 처리): %s", exc)
            return None
        if not doc:
            return None
        self._memory[key] = dict(doc)
        return self._verdict_from_doc(doc)

    def store(self, key: str, verdict: VisionVerdict) -> None:
        """verdict → flat dict → in-memory + Firestore (lazy, 실패 graceful)."""
        doc = {
            "primary_fault": verdict.primary_fault,
            "severity": verdict.severity,
            "differences": list(verdict.differences),
        }
        self._memory[key] = dict(doc)
        try:
            self._backend_put(key, doc)
        except Exception as exc:  # noqa: BLE001 - Firestore 오류 graceful
            log.warning("VisionVetoCache backend store 실패 (in-memory 만 유효): %s", exc)

    @staticmethod
    def _verdict_from_doc(doc: dict) -> VisionVerdict:
        diffs = doc.get("differences") or []
        return VisionVerdict(
            primary_fault=str(doc.get("primary_fault", "")),
            severity=str(doc.get("severity", "")),
            differences=tuple(diffs),
        )

    # ── Firestore-backed I/O (lazy import — D-16). 테스트는 monkeypatch. ──

    def _backend_get(self, key: str) -> dict | None:
        from sunity_shared import firestore_admin

        return firestore_admin.get_gemini_cache(self._scoped(key))

    def _backend_put(self, key: str, doc: dict) -> None:
        from sunity_shared import firestore_admin

        firestore_admin.store_gemini_cache(self._scoped(key), doc)

    def _scoped(self, key: str) -> str:
        """Firestore document id 안전화 — '/' 충돌 회피(전용 namespace 이미 prefix)."""
        return key.replace("/", "_")


# ─────────────────── Gemini client (lazy-import) ───────────────────


def _load_api_key() -> str:
    """env GEMINI_API_KEY 우선, 미설정 시 SSM. 키는 절대 로그 금지(T-20-06)."""
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        log.info("Gemini 키: env GEMINI_API_KEY (len=%d)", len(inline))
        return inline
    import boto3  # lazy — env 키 있으면 boto3 미사용(B4/효율)

    param = os.environ.get(
        "GEMINI_API_KEY_PARAM_NAME", "/sunity/motion/gemini-api-key"
    )
    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    resp = ssm.get_parameter(Name=param, WithDecryption=True)
    log.info("Gemini 키: SSM %s", param)
    return resp["Parameter"]["Value"]


def _ensure_client():
    """google.genai Client lazy-init + 모듈 캐시 싱글톤 (recognizer 패턴).

    Raises:
      RuntimeError: 키 부재/SDK 미설치/client 생성 실패. 호출자(assess_fault_severity)
        가 graceful None 으로 변환(Pitfall 5).
    """
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from google import genai  # lazy — top-level import 금지(D-16)

        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY 부재")
        _CLIENT = genai.Client(api_key=api_key)
    except Exception as exc:  # noqa: BLE001 - 키/SDK/생성 실패는 graceful None 으로
        raise RuntimeError(f"Gemini client 생성 실패: {exc}") from exc
    return _CLIENT


def _mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".mov", ".qt"):
        return "video/quicktime"
    if ext == ".webm":
        return "video/webm"
    return "video/mp4"


def _ascii_safe_path(path: str) -> tuple[str, str | None]:
    """genai SDK 가 파일명을 HTTP 헤더(ascii)에 넣어 한글 파일명은 UnicodeEncodeError.
    비-ASCII 경로면 ASCII 임시 파일로 복사 후 반환 (spike line 100 패턴)."""
    name = os.path.basename(path)
    try:
        name.encode("ascii")
        return path, None
    except UnicodeEncodeError:
        import shutil
        import tempfile

        suffix = os.path.splitext(path)[1]
        tmp = tempfile.NamedTemporaryFile(prefix="vveto_", suffix=suffix, delete=False)
        tmp.close()
        shutil.copyfile(path, tmp.name)
        return tmp.name, tmp.name


def _upload_video(client, local_video_path: str, _hint: object = None):
    """caller local 영상 → Gemini Files API ACTIVE 대기 (spike upload_and_wait 패턴).

    B4: caller local_video_path 만 사용 — S3 재다운로드/RTMW 재실행 0.
    """
    import time

    from google.genai import types as genai_types  # lazy

    upload_path, tmp_path = _ascii_safe_path(local_video_path)
    uploaded = client.files.upload(
        file=upload_path,
        config=genai_types.UploadFileConfig(mime_type=_mime(local_video_path)),
    )
    start = time.monotonic()
    while _state_name(uploaded) == "PROCESSING":
        if time.monotonic() - start > _FILES_TIMEOUT_S:
            raise TimeoutError(f"Files API processing > {_FILES_TIMEOUT_S}s")
        time.sleep(_FILES_POLL_S)
        uploaded = client.files.get(name=uploaded.name)
    if tmp_path is not None:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    state = _state_name(uploaded)
    if state and state != "ACTIVE":
        raise RuntimeError(f"Files API state={state} (ACTIVE 아님)")
    return uploaded


def _state_name(f) -> str:
    st = getattr(f, "state", None)
    if st is None:
        return ""
    return getattr(st, "name", None) or str(st)


# ─────────────────── 핵심 어댑터 ───────────────────


def assess_fault_severity(
    local_video_path: str,
    at_seconds: float | None = None,
    reference_video_path: str | None = None,
) -> VisionVerdict | None:
    """영상 → 결함-심각도 VisionVerdict | None (객관성·결정론·adapter-boundary).

    **iter2 MEDIUM-1: feature 토글 검사 0 — adapter-local 전제조건만.**
    vision veto 토글 env 는 읽지 않는다. 토글 게이트는 호출자(pipeline 20-03)
    책임. 본 어댑터는 키/client/캐시/local 파일/Gemini 응답 유효성만 게이트한다.

    두 가지 모드 (v5.0):
      · COMPARISON (reference_video_path 제공) — Mode1: 기준(정타) 영상 vs 학생 영상
        둘 다 1회 업로드 → 비교 프롬프트 N=VISION_VETO_SAMPLES 회 호출 → rank-median
        severity 집계 (단일 라벨 흔들림 제거, Phase 20 robustify). 업로드 핸들 재사용
        (영상당 1회). severity = 기준 대비 학생 편차. 캐시 키 = (student_hash,
        reference_hash, N) PAIR. cache hit 은 집계 verdict 를 deterministic 반환
        (재샘플링 0). belle 결정 (2026-06-20).
      · SINGLE (reference_video_path=None) — 단일 영상 진공 판정 (back-compat).
        Mode3 는 belle 보류로 이 어댑터를 호출하지 않지만 경로는 유지.

    Args:
      local_video_path: caller 가 이미 받은 학생 local 영상 (B4 — 재다운로드 0).
      at_seconds: worst-pose 시점 힌트(20-01 worst_pose_timestamp). 지금은 프롬프트
        힌트 + 캐시 키 bucket 으로만 사용(Open Q1 = whole-video 업로드 default).
      reference_video_path: 제공 시 COMPARISON 모드 — 기준(정타) local 영상.
        caller 가 S3 에서 받아 전달 (B4 — 어댑터는 재다운로드 0).

    Returns:
      VisionVerdict(primary_fault, severity, differences) hit/성공. **score 필드 없음.**
      None — 키 부재/API 실패(graceful, Pitfall 5) 또는 점수 누출(객관성 폐기).
    """
    # (1) adapter-local 전제조건: client (키 부재/SDK 실패 → graceful None).
    try:
        client = _ensure_client()
    except Exception as exc:  # noqa: BLE001 - Pitfall 5 graceful
        log.warning("Gemini client 사용 불가 — verdict=None (graceful): %s", exc)
        return None

    # (2) video_hash (+ 비교 시 reference_hash) → 캐시 키. hash 만 PII 로 로그.
    try:
        from .technique_cache import compute_video_hash

        video_hash = compute_video_hash(local_video_path)
        reference_hash = (
            compute_video_hash(reference_video_path)
            if reference_video_path is not None
            else None
        )
    except FileNotFoundError:
        log.warning("local 영상 없음 — verdict=None (graceful)")
        return None
    except Exception as exc:  # noqa: BLE001 - hash 실패 graceful
        log.warning("video_hash 산출 실패 — verdict=None (graceful): %s", exc)
        return None

    cache = VisionVetoCache()
    key = VisionVetoCache.build_key(
        video_hash=video_hash,
        model_name=DEFAULT_VISION_MODEL,
        input_granularity=INPUT_GRANULARITY,
        at_seconds=at_seconds,
        reference_hash=reference_hash,
    )

    # (3) cache hit → 저장 verdict 반환 (Gemini 호출 0, 결정론 D-06).
    cached = cache.lookup(key)
    if cached is not None:
        log.info("VisionVetoCache hit: %s", video_hash[:8])
        return cached

    # (4) miss → 영상 업로드 + generate_content (temp 0.0).
    #     COMPARISON 이면 기준+학생 둘 다 1회 업로드 후 N 회 비교 호출 → rank-median 집계.
    #     SINGLE 이면 1회 업로드 + 1회 호출 (back-compat, 집계 없음).
    try:
        uploaded = _upload_video(client, local_video_path, at_seconds)
        if reference_video_path is not None:
            ref_uploaded = _upload_video(client, reference_video_path, at_seconds)
            verdict = _aggregate_comparison_verdict(
                client, ref_uploaded, uploaded, at_seconds
            )
            if verdict is None:
                log.warning(
                    "비교 multi-sample 0 파싱 — verdict=None (graceful)"
                )
                return None
            cache.store(key, verdict)
            return verdict
        raw_text = _call_gemini(client, uploaded, at_seconds)
    except Exception as exc:  # noqa: BLE001 - API/업로드 실패 graceful (Pitfall 5)
        log.warning("Gemini 호출 실패 — verdict=None (graceful): %s", exc)
        return None

    # (5) 점수 누출 가드 (객관성 hard gate) — 누출 시 verdict 폐기. (단일 영상 경로)
    if _SCORE_PATTERN.search(raw_text or ""):
        log.warning("응답에 점수 누출 — 객관성 위반, verdict 폐기 (None)")
        return None

    # (6) 파싱 + severity 유효성.
    verdict = _parse_verdict(raw_text)
    if verdict is None:
        log.warning("Gemini 응답 파싱/유효성 실패 — verdict=None (graceful)")
        return None

    # (7) 캐시 저장 후 반환.
    cache.store(key, verdict)
    return verdict


# ─────────────────── 비교 multi-sample 집계 (Phase 20 robustify) ───────────────────

_SEVERITY_RANK = {"none": 0, "minor": 1, "moderate": 2, "major": 3}
_RANK_TO_SEVERITY = {v: k for k, v in _SEVERITY_RANK.items()}


def _aggregate_comparison_verdict(
    client, ref_uploaded, student_uploaded, at_seconds: float | None
) -> VisionVerdict | None:
    """업로드된 핸들 재사용으로 비교 호출 N 회 → rank-median severity 집계.

    belle 2026-06-20: Gemini 는 결함을 일관되게 보지만 단일 severity 라벨이 흔들린다.
    N=VISION_VETO_SAMPLES 회 generateContent 후 rank-median 으로 흔들림 제거.
    none=0/minor=1/moderate=2/major=3, 짝수 개수는 lower-middle(보수적).

    업로드는 호출자가 1회만 수행(핸들 재사용) — 여기서 재업로드 0 (시간 절약).
    각 샘플은 점수 누출 가드 + _parse_verdict 통과해야 인정. 0 인정 → None.
    primary_fault = severity == median 인 샘플 중 첫째, 없으면 최빈 description.
    """
    n = max(1, globals()["VISION_VETO_SAMPLES"])
    parsed: list[VisionVerdict] = []
    for _ in range(n):
        raw_text = _call_gemini_comparison(
            client, ref_uploaded, student_uploaded, at_seconds
        )
        # 점수 누출 가드 — 누출 샘플은 폐기(객관성), 집계에서 제외.
        if _SCORE_PATTERN.search(raw_text or ""):
            log.warning("비교 샘플 점수 누출 — 해당 샘플 폐기 (집계 제외)")
            continue
        v = _parse_verdict(raw_text)
        if v is not None:
            parsed.append(v)

    if not parsed:
        return None

    ranks = sorted(_SEVERITY_RANK.get(v.severity, 0) for v in parsed)
    # 짝수 개수 → lower-middle 인덱스로 보수적 선택 (median 의 아래쪽).
    median_idx = (len(ranks) - 1) // 2
    median_rank = ranks[median_idx]
    median_severity = _RANK_TO_SEVERITY[median_rank]

    # primary_fault: severity == median 인 첫 샘플, 없으면 최빈 description.
    median_match = [v for v in parsed if v.severity == median_severity]
    if median_match:
        chosen = median_match[0]
    else:
        chosen = _most_frequent_by_fault(parsed)

    return VisionVerdict(
        primary_fault=chosen.primary_fault,
        severity=median_severity,
        # C1 (belle 2026-06-21): 한 샘플의 differences 만 쓰면 다른 샘플이 본 결함
        # (왼팔 등)이 누락된다 → N 샘플 differences 를 union 한다(모든 결함 캐치).
        # severity(캡)는 median 유지(정타 100 보존). union 은 부위별 최고 severity/
        # deviation 만 남겨 noise 억제.
        differences=_union_differences(parsed),
    )


_BODYPART_SEVERITY_FLOOR = {"none", ""}


def _union_differences(verdicts: list) -> tuple:
    """N 샘플의 differences 를 union — 부위(body_part)별 최고 severity/deviation 1개.

    belle: "오류가 있으면 모두 잡아야". median 샘플 하나로는 다른 샘플이 본 부수
    결함(왼팔 등)을 잃는다. 정규화 body_part 키로 dedup, severity 가 더 심하거나
    deviation 이 더 큰 항목을 유지. severity='none'/빈 부위는 제외(노이즈). 순서는
    severity 내림차순(지배 결함이 앞). tuple 반환(nested-array 회피).
    """
    best: dict[str, dict] = {}
    for v in verdicts:
        for d in v.differences or ():
            part = str((d or {}).get("body_part", "")).strip()
            if not part:
                continue
            sev = str((d or {}).get("severity", "")).strip().lower()
            if sev in _BODYPART_SEVERITY_FLOOR:
                continue
            key = part.lower()
            cur = best.get(key)
            sev_rank = _SEVERITY_RANK.get(sev, 0)
            try:
                dev = float((d or {}).get("approx_angle_deviation_deg") or 0.0)
            except (TypeError, ValueError):
                dev = 0.0
            if cur is None or sev_rank > cur["_rank"] or (
                sev_rank == cur["_rank"] and dev > cur["_dev"]
            ):
                best[key] = {**d, "_rank": sev_rank, "_dev": dev}
    ordered = sorted(best.values(), key=lambda x: (-x["_rank"], -x["_dev"]))
    return tuple({k: v for k, v in d.items() if not k.startswith("_")} for d in ordered)


def _most_frequent_by_fault(verdicts: list) -> VisionVerdict:
    """primary_fault description 최빈 verdict (동률 시 첫 등장). 집계 폴백."""
    counts: dict[str, int] = {}
    first: dict[str, VisionVerdict] = {}
    for v in verdicts:
        counts[v.primary_fault] = counts.get(v.primary_fault, 0) + 1
        first.setdefault(v.primary_fault, v)
    best_fault = max(counts, key=lambda f: counts[f])
    return first[best_fault]


def _call_gemini(client, uploaded, at_seconds: float | None) -> str:
    """generate_content (temperature=0.0, response_schema, thinking) → raw text.

    temperature=0.0 = spike 0.1 에서 변경 (D-06 결정론 + A1 검증).
    """
    from google.genai import types as genai_types  # lazy

    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=build_schema(),
        temperature=0.0,
        max_output_tokens=4096,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=-1),
        http_options=genai_types.HttpOptions(timeout=180_000),
    )
    response = client.models.generate_content(
        model=DEFAULT_VISION_MODEL,
        contents=["분석 영상:", uploaded, _build_prompt(at_seconds)],
        config=config,
    )
    return getattr(response, "text", "") or ""


def _call_gemini_comparison(
    client, ref_uploaded, student_uploaded, at_seconds: float | None
) -> str:
    """비교(reference-anchored) generate_content — 기준 영상 먼저 + 학생 영상 (temp 0.0).

    contents 순서 = [기준 라벨, 기준 영상, 학생 라벨, 학생 영상, 비교 프롬프트].
    response_schema/temperature/thinking 는 단일 경로와 동일 (객관성·결정론 동일 보장).
    """
    from google.genai import types as genai_types  # lazy

    config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=build_schema(),
        temperature=0.0,
        max_output_tokens=4096,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=-1),
        http_options=genai_types.HttpOptions(timeout=180_000),
    )
    response = client.models.generate_content(
        model=DEFAULT_VISION_MODEL,
        contents=[
            "기준(정타) 영상:",
            ref_uploaded,
            "평가 대상(학생) 영상:",
            student_uploaded,
            _build_comparison_prompt(at_seconds),
        ],
        config=config,
    )
    return getattr(response, "text", "") or ""


def _parse_verdict(raw_text: str) -> VisionVerdict | None:
    """raw JSON → VisionVerdict. severity = differences 중 최악 또는 명시값.

    severity enum 유효성 검사 — 불명 시 None (graceful).
    """
    import json

    try:
        payload = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    primary_fault = str(payload.get("primary_fault", "")).strip()
    differences = payload.get("differences") or []
    if not isinstance(differences, list):
        differences = []

    # severity 우선순위: (1) Gemini 가 직접 보고한 dominant_severity(none 포함),
    # (2) 없으면 differences 중 최악, (3) 둘 다 없으면 'none'(cap 미적용 — 모호하면
    # 처벌 안 함). over-penalization fix: 정타에서 억지 cap 방지 (2026-06-20).
    declared = str(payload.get("dominant_severity", "")).strip().lower()
    if declared in _ALLOWED_SEVERITY:
        severity = declared
    else:
        severity = _dominant_severity(differences) or "none"

    return VisionVerdict(
        primary_fault=primary_fault,
        severity=severity,
        differences=tuple(d for d in differences if isinstance(d, dict)),
    )


def _dominant_severity(differences: list) -> str | None:
    """differences 중 최악 severity enum. 유효 라벨 없으면 None."""
    rank = {"none": 0, "minor": 1, "moderate": 2, "major": 3}
    worst = None
    worst_rank = 0
    for d in differences:
        if not isinstance(d, dict):
            continue
        sev = str(d.get("severity", "")).strip().lower()
        if sev in _ALLOWED_SEVERITY and rank[sev] > worst_rank:
            worst = sev
            worst_rank = rank[sev]
    return worst
