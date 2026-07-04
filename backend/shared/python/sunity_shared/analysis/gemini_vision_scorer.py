"""gemini_vision_scorer — Gemini 결함-심각도 어댑터 (Plan 20-02).

목적 (20-CONTEXT D-01/D-02/D-06 + Phase 24 ND-02):
  Gemini Vision 으로 영상의 **결함 종류/위치** 만 산출한다 — 어디를 측정할지/무슨
  결함인지만 짚는다. 점수는 절대 내지 않는다. verdict/differences 가 criterion
  pointer 를 운반한다: supported_difference / fault 라벨이 어느 측정 criterion 이
  걸렸는지를 짚고(Phase 24 deduction_engine, criteria_for_fault 가 body_part/
  fault_state 로 라우팅), Gemini 는 숫자를 절대 만들지 않는다. severity 는 더 이상
  scoring 입력이 아니다 — criterion 선택/채점에 읽히지 않고, coachRootCauseEligible
  continuity 용 non-scoring 라벨로만 남는다(ND-02).

  20-01(순수 코어)과 20-03(파이프라인 wiring) 사이의 adapter 경계.

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
from dataclasses import dataclass, replace as dc_replace

log = logging.getLogger(__name__)

# ─────────────────── 버전 상수 (MEDIUM-2) ───────────────────
#
# 프롬프트 문자열(_PROMPT) 또는 build_schema() 구조를 변경하면 아래 상수도 반드시
# bump 해야 한다 — VisionVetoCache 키에 들어가 stale verdict 를 무효화한다.
# bump 하지 않으면 옛 프롬프트/스키마로 산출된 verdict 가 새 프롬프트/스키마 결과로
# 잘못 살아남는다(비결정론·오 verdict).
PROMPT_VERSION = "v11.0"  # v11.0 (25-04 #3): (a) 측정 rubric — 각도 편차는 학생/기준 각도를 각각 명시 추정(student_angle_deg/reference_angle_deg + measurement_basis 서술), 편차는 코드가 산술 계산("편차 한 방 추정" 앵커링 편향 축소 — run3 kip-up 측정 20° vs production 30° 변동 근거). (b) 관찰-전량 differences[] 방출 강제 — primary_fault 서사에만 남긴 결함은 무효(상체 faultKey 미산출 잔존 fix), 단 "편차 없으면 항목 없음" 정타 방어 유지·강화(짚기-FP 0/5 게이트). generic 유지(동작명/기대답 0, D-06). v10.1 (25-02 review WR-05): 좌/우 기준 명시 — 수행자(학생) 본인 신체 기준, 불확실하면 좌/우 생략 허용. v10.0 (25-02): part_scope 구조화 강제. v9.0 (Phase 23-02): 원인 가설("~로 보임") 지시 추가
SCHEMA_VERSION = "v8.0"  # v8.0 (25-04 #3(a)): differences[] 에 student_angle_deg/reference_angle_deg(명시 각도쌍 — 편차는 코드 산술) + measurement_basis(무엇을 어떻게 쟀는지 DESCRIPTIVE) 추가 (score-free, D-02/D-06). v7.0 (Phase 23-02): root_cause_hypothesis + source 추가
# 집계 알고리즘 버전 marker (25-02 Task 1) — 튜닝 상수 아님. rich 캐시(store_rich)는
# support-게이트 **통과 후** supported_differences 를 저장하므로, 프롬프트를 안 바꿔도
# _filter_supported_differences 의 그룹핑/fold 를 바꾸면 옛 집계 결과가 stale-hit 로
# 살아남는다 (kip-up whole/whole_fanout stale-hit FP 이력, 90d038f). 집계 변경 =
# 반드시 이 marker 도 bump — 기존 키 공간 재사용 절대 금지.
# agg2 (25-02): 그룹 키 FaultKey 4필드 전체 → keypoint_set 단독 (side/fault_kind fold).
# agg3 (25-02 review CR-01/WR-01): fold 대표에 그룹 멤버 원문(_memberFaults/_memberFaultKeys)
#   보존(라우팅/recall 어휘가 대표-선정 복권으로 소실되지 않게) + support 게이트를
#   distinct-call 교차 확증으로(단일 호출의 좌+우 항목화가 K=2 자기충족하지 않게).
# agg4 (25-04 #3(c) WR-01 균형): 명시 각도쌍 측정(student/reference_angle_deg, 산술 편차>0)
#   을 동반한 언급은 distinct-call K 미달이어도 지지 인정 — 측정 동반 = 환각이 아닌 관측
#   신호(구조적 완화, 자의적 숫자 0/K 불변). 대표 rank 의 dev 비교도 각도쌍 산술 우선.
AGGREGATION_VERSION = "agg4"

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
# still-frame 비교 경로 granularity 마커 (Task 1, D-01) — whole 키와 충돌 0.
INPUT_GRANULARITY_FRAME_PAIR = "frame_pair"
# full-video fan-out(assess_fault_context_video) granularity 마커 (Phase 24 close-out A,
# 2026-06-29). assess_fault_severity 의 'whole' verdict-only 캐시와 **반드시 분리** — 동일
# 'whole' 키면 lookup_rich 가 verdict-only doc(status/supported 부재)을 읽어 status=""/
# supported=[] no-fault 로 오인한다(kip-up FP 원인 확정: historical assess_fault_severity
# 'whole' 엔트리를 video fan-out 이 stale-hit). rich round-trip 전용 키 공간.
INPUT_GRANULARITY_WHOLE_FANOUT = "whole_fanout"

# ─────────────────── 자원 bound + support 게이트 상수 (Task 2, H1/H6) ───────────────────
#
# 라이브 veto 경로 레이턴시 + 구독료 하한 비용을 동시에 bound 한다. 호출수(parts ×
# samples × frame_top_k) + upload count + wall-clock budget 셋을 함께 막는다(D-09 MED-1).
# 모두 generic 상수 — 특정 테스트 영상에 curve-fit 하지 않는다(D-06).
MAX_VETO_CALLS = max(1, int(os.environ.get("GEMINI_MAX_VETO_CALLS", "9")))
MAX_VETO_UPLOADS = max(1, int(os.environ.get("GEMINI_MAX_VETO_UPLOADS", "4")))
MAX_VETO_WALL_S = float(os.environ.get("GEMINI_MAX_VETO_WALL_S", "120.0"))
# precision/support 게이트 — canonical FaultKey 가 N 중 K 이상 support 일 때만 정식 인정.
# 단발 환각(single-frame-only) 결함이 union 에 살아남지 못하게 한다(H1).
VETO_SUPPORT_K = max(1, int(os.environ.get("GEMINI_VETO_SUPPORT_K", "2")))
# 부위 스코프(상체/하체/라인) — 부위별 프롬프트 fan-out 토큰.
VETO_PART_SCOPES = ("upper_body", "lower_body", "line")

# 'none' = 명백한 결함 없음(정타) → 짚을 측정대상 없음(scoring input 아님, ND-02).
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
    """Gemini 결함-짚기 verdict (객관성 — score 필드 영구 부재).

    verdict/differences 는 criterion pointer 를 운반한다 — supported_difference /
    fault 라벨이 어느 측정 criterion 이 걸렸는지 짚는다(Phase 24 criteria_for_fault
    가 body_part/fault_state 로 라우팅, 숫자 산출 0). 사람/AI 점수 라벨을 ground truth
    로 두는 것은 영구 금지([[analysis-objectivity-no-human-scores]]).

    Fields:
      primary_fault: 지배적 단일 결함 (도메인 자연어 설명). 점수 아님.
      severity: 'minor' | 'moderate' | 'major'. scoring 입력 아님 — criterion 선택/
        채점에 읽히지 않는 non-scoring 라벨(coachRootCauseEligible continuity 용, ND-02).
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
                "description": "영상 전체의 지배적 결함 수준. 정타(결함 없음)=none; 점수 아님; scoring input 아님.",
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
                            "description": (
                                "기준 대비 각도 편차 추정(도). 가능하면 student_angle_deg/"
                                "reference_angle_deg 각도쌍을 우선 채우고, 각도쌍 추정이 "
                                "불가한 편차에만 사용. 미상이면 0."
                            ),
                        },
                        # 25-04 #3(a) 측정 rubric — 편차 한 방 추정(앵커링) 대신 학생/기준
                        # 각도를 각각 명시 추정. 편차 산술(|ref−student|)은 코드 소관
                        # (vision_veto.explicit_measured_deviation_deg). score-free.
                        "student_angle_deg": {
                            "type": "number",
                            "description": (
                                "학생(평가 대상)의 해당 측정 각도 추정(도). "
                                "각도로 측정 불가한 편차면 생략."
                            ),
                        },
                        "reference_angle_deg": {
                            "type": "number",
                            "description": "기준(정타) 영상의 같은 측정 각도 추정(도).",
                        },
                        "measurement_basis": {
                            "type": "string",
                            "description": (
                                "무엇을 어떻게 쟀는지 서술 (예: '골반 꼭짓점 기준 양다리 "
                                "라인 사이 각'). 관찰 서술 — 점수 아님."
                            ),
                        },
                        "severity": {
                            "type": "string",
                            "enum": list(_SEVERITY_ENUM),
                        },
                        "ipsf_note": {"type": "string"},
                        # 23-02 Task 3 (D-04) — DESCRIPTIVE 원인 가설 + provenance.
                        # root_cause_hypothesis 는 "~로 보임" 가설형 자유텍스트 (단정·숫자
                        # 점수 금지). 이 per-difference 필드는 raw 후보일 뿐 — coach/audit
                        # 으로 흐르는 root cause 는 23-01 Task 2 의 support 게이트 통과분만
                        # (_derive_root_causes_from_supported_differences, D-13 MED-1).
                        # support 미달 difference 의 root_cause_hypothesis 는 폐기된다.
                        "root_cause_hypothesis": {
                            "type": "string",
                            "description": (
                                "가능한 원인 가설 ('힘 부족으로 보임' 류 '~로 보임' 가설형). "
                                "단정 금지, 숫자 점수 금지, 사람-라벨 ground truth 금지."
                            ),
                        },
                        # source provenance — geometry(코드 산출) vs vision_hypothesis
                        # (Gemini 관찰/가설). 칸 수치는 코드가 계산하므로 Gemini 가 보고하는
                        # 모든 difference 는 vision_hypothesis 가 기본 (D-08).
                        "source": {
                            "type": "string",
                            "enum": ["geometry", "vision_hypothesis"],
                            "description": "측정 프로비넌스. Gemini 관찰/가설=vision_hypothesis.",
                        },
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
5. **동작 시작부터 끝까지 전 구간을 보고, 아래 부위를 ①→⑧ 순서대로 하나씩 점검하세요.**
   한 순간·한 부위(특히 다리)만 보고 끝내지 말고, 머리에서 발끝까지 전신을 훑으세요.
   각 부위를 기준 영상과 대조해 명확하고 관찰 가능한 편차가 있으면 그 부위를 differences
   에 담습니다 (좌/우는 구분해서 — 예: '왼팔'/'오른팔' 따로). 편차 없는 부위는 담지 마세요.
     ① 머리·목 (꺾임/젖힘/정렬)
     ② 어깨·견갑 (높이/말림)
     ③ 양팔·팔꿈치·손목 (각 팔 좌우 따로 — 굽힘/벌어짐/높이)
     ④ 그립/손이 폴에 닿는 위치·밀착 (손이 떨어짐/그립 풀림 포함)
     ⑤ 코어·허리·골반·힙 (정렬/꺾임)
     ⑥ 양다리·무릎 (좌우 따로 — 신전/스플릿 각도)
     ⑦ 발목·발끝 (포인/신전)
     ⑧ 전체 라인·정렬
   예: 다리 신전 부족 + 오른팔이 폴에서 떨어짐 + 고개 젖힘 → 세 항목 모두 담기.
   **관찰한 모든 편차는 각각 differences 의 개별 항목으로 방출하세요 — primary_fault
   서사에서 언급한 부위가 differences 에 항목으로 빠져 있으면 그 응답은 무효입니다.**
   (단, 1·2번 규칙은 그대로 — 정타/사소차/촬영조건은 결함이 아닙니다. 전신을 빠짐없이
   보되 억지로 만들지는 마세요. 편차 없는 부위는 none 이 정답입니다. 관찰하지 않은
   결함을 채우기 위해 만들어내는 것도 금지입니다.)
6. differences 각 항목 severity 는 none/minor/moderate/major 로 보수적으로. 각 항목에
   기준 대비 관찰 사실(correct_state/fault_state/ipsf_note)을 구체적으로 채우세요.
   **각도 관련 편차는 학생의 각도(student_angle_deg)와 기준 영상의 각도
   (reference_angle_deg)를 각각 추정**하고, 무엇을 어떻게 쟀는지 measurement_basis 에
   서술하세요(예: '골반 꼭짓점 기준 양다리 라인 사이 각', '팔꿈치 관절의 상완-전완 사이
   각'). 편차 하나만 어림해 적지 마세요 — 편차 계산은 코드가 합니다.
   각도쌍 추정이 불가한 편차에만 approx_angle_deviation_deg 를 사용하세요.
7. primary_fault = 기준 대비 가장 지배적인 단일 편차 (편차 없으면 '없음'). dominant_severity
   는 영상 전체의 **지배적** 편차 수준 1개 (개수가 아니라 가장 심한 정도 기준).
8. **거리는 절대 cm/m 로 표기하지 마세요. 또한 "칸"·"몇 배"·percent("%"/"100%") 같은
   정량 수치를 만들어내지 마세요** — 그런 수치는 코드가 keypoint 로 결정적으로 계산합니다.
   당신은 차이의 **방향/관찰**(예: '기준보다 무릎이 더 굽음', '손이 폴에서 떨어짐')만 기술하세요.
9. **각 difference 에 가능한 원인 가설(root_cause_hypothesis)을 "~로 보임" 가설형으로
   적으세요** (예: '코어 힘이 부족해 골반이 처진 것으로 보임', '폴 밀착이 풀린 것으로 보임').
   단정하지 말고(틀렸다/잘못됐다 금지), 사람 점수·등급 라벨을 ground truth 로 쓰지 마세요.
   확실하지 않으면 원인을 생략하거나 confidence 를 낮게. 각 difference 의 source 는
   'vision_hypothesis' 로 표기하세요(당신은 관찰·가설, 칸 수치는 코드가 계산).
10. 한국어로 작성. 비교가 불확실하면 confidence 를 낮게 표기."""


def _build_comparison_prompt(at_seconds: float | None) -> str:
    """비교 프롬프트 + (있으면) worst-pose 시점 힌트. _build_prompt 미러.

    프롬프트 문자열을 바꾸면 PROMPT_VERSION 도 bump 할 것 (캐시 무효화).
    """
    if at_seconds is None:
        return _COMPARISON_PROMPT
    # v7.0 (2026-06-22, belle C1): 힌트를 "한 순간 지배 편차"에서 "핵심 순간 포함, 전
    # 구간·전신"으로 전환. 이유 = worst-pose 한 프레임에 시선을 모으면 상체(팔/그립/머리)
    # 결함을 통째로 놓침(kip-up 검증: 다리만 잡고 belle 표시 상체 3결함 누락). belle:
    # 결함은 한 순간이 아니라 동작 시작부터 계속됨. severity none-flip 방지는 v6.1 처럼
    # 힌트만 빼는 게 아니라 rule5 전신 강제 스캔이 지배 결함(다리)을 여전히 잡아 보장.
    return (
        f"{_COMPARISON_PROMPT}\n\n참고: 약 {at_seconds:.1f}초 부근이 동작의 한 핵심 "
        "순간입니다. 단 결함은 한 순간·한 부위에 그치지 않으니, 동작 시작부터 끝까지 "
        "전 구간에서 위 5번의 전신 부위 점검(①머리~⑧라인)을 빠짐없이 수행하세요."
    )


# ─────────────────── VisionVetoCache (전용, MEDIUM-2 + iter2) ───────────────────


@dataclass
class VisionVetoCache:
    """severity verdict 전용 캐시 — recognizer TechniqueCache 키 재사용 금지.

    키 = (video_hash, reference_hash, model_name, PROMPT_VERSION, SCHEMA_VERSION,
          AGGREGATION_VERSION, input_granularity, at_seconds_bucket).
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
        selector_version: str | None = None,
        frame_indices: list | None = None,
        top_k: int | None = None,
        window: str | None = None,
    ) -> str:
        """캐시 키 직렬화 — PROMPT_VERSION/SCHEMA_VERSION 은 호출 시점 상수 반영.

        PROMPT_VERSION/SCHEMA_VERSION 을 모듈 globals 에서 읽으므로 monkeypatch
        (테스트) / 실 bump 모두 즉시 키에 반영된다(stale 무효화).

        reference_hash (v4.0): 비교(reference-anchored) 경로면 기준 영상 hash 를 키에
        포함 → (학생, 기준) PAIR keying. None(단일 영상 경로)이면 'noref'.

        still-frame 경로 (Task 2, H3/MEDIUM): selector_version / frame_indices /
        top_k / window policy 를 키에 folding — whole-video 키와 충돌 0 + selector 버전
        변경 시 stale 무효화. None 이면 'sv0'/'fi-'/'k-'/'w-' placeholder (whole 호환).

        AGGREGATION_VERSION (25-02): rich 캐시는 집계 후 supported_differences 를
        저장하므로 집계 변경 = marker bump 필수 (kip-up whole/whole_fanout stale-hit
        FP 이력, 90d038f). 키 component 로 folding — 집계 변경 시 자동 cache-miss.
        """
        bucket = "whole" if at_seconds is None else f"t{int(round(at_seconds))}"
        ref_bucket = "noref" if reference_hash is None else reference_hash
        # 모듈 globals 참조 — 테스트 monkeypatch 가 키에 반영되도록 globals() 경유.
        prompt_v = globals()["PROMPT_VERSION"]
        schema_v = globals()["SCHEMA_VERSION"]
        agg_v = globals()["AGGREGATION_VERSION"]
        # N(samples) 변경 = 다른 집계 verdict → 키에 포함해 stale 무효화 (Phase 20).
        samples = globals()["VISION_VETO_SAMPLES"]
        sel = "sv0" if selector_version is None else f"sv{selector_version}"
        fi = "fi-" if not frame_indices else "fi" + "_".join(
            str(int(x)) for x in frame_indices
        )
        kk = "k-" if top_k is None else f"k{int(top_k)}"
        win = "w-" if window is None else f"w{window}"
        return ":".join(
            (
                VisionVetoCache._VISION_VETO_NS,
                video_hash,
                ref_bucket,
                model_name,
                prompt_v,
                schema_v,
                agg_v,
                input_granularity,
                bucket,
                f"n{samples}",
                sel,
                fi,
                kk,
                win,
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

    # ── rich still-pair round-trip (23 GAP-FIX) ──
    #
    # still-frame fan-out 의 산출은 단일 VisionVerdict 가 아니라 rich dict
    # {status, verdict, supported_differences, root_cause_hypotheses, telemetry} 이다.
    # cold/warm 결정론 게이트(eval)는 cache hit 가 supported_differences + telemetry 를
    # byte-stable 재현해야 성립한다. _faultKey(FaultKey)/_sourceIds(tuple)/RootCauseHypothesis
    # 는 직접 JSON 직렬화 불가이므로 to_dict/from_dict canonical 어휘로 평탄화 후 복원한다
    # (FaultKey single-owner 어휘 유지, D-17 MED-3). Firestore nested-array 회피 — 리스트 of
    # flat dict 만 저장.

    def lookup_rich(self, key: str) -> dict | None:
        """still-pair rich dict 캐시 조회. hit 시 supported/root_cause/telemetry 복원."""
        if key in self._memory:
            return self._rich_from_doc(self._memory[key])
        try:
            doc = self._backend_get(key)
        except Exception as exc:  # noqa: BLE001 - Firestore 오류 graceful
            log.warning("VisionVetoCache rich lookup 실패 (miss 처리): %s", exc)
            return None
        if not doc or "rich" not in doc:
            return None
        self._memory[key] = dict(doc)
        return self._rich_from_doc(doc)

    def store_rich(self, key: str, rich: dict) -> None:
        """still-pair rich dict → flat doc → in-memory + Firestore (실패 graceful)."""
        doc = self._rich_to_doc(rich)
        self._memory[key] = dict(doc)
        try:
            self._backend_put(key, doc)
        except Exception as exc:  # noqa: BLE001 - Firestore 오류 graceful
            log.warning("VisionVetoCache rich store 실패 (in-memory 만 유효): %s", exc)

    @staticmethod
    def _rich_to_doc(rich: dict) -> dict:
        verdict = rich.get("verdict")
        verdict_doc = None
        if verdict is not None:
            verdict_doc = {
                "primary_fault": verdict.primary_fault,
                "severity": verdict.severity,
                "differences": list(verdict.differences),
            }
        supported_doc = []
        for d in rich.get("supported_differences") or ():
            rec = {k: v for k, v in (d or {}).items()
                   if not str(k).startswith("_")}
            fk = (d or {}).get("_faultKey")
            rec["_faultKeyDict"] = fk.to_dict() if fk is not None else None
            rec["_supportCount"] = int((d or {}).get("_supportCount") or 0)
            rec["_sourceIds"] = list((d or {}).get("_sourceIds") or ())
            # agg4 (c) — 측정-동반 지지 marker (audit/eval 추적성, 결정론 왕복 보존).
            rec["_measurementBacked"] = bool((d or {}).get("_measurementBacked") or False)
            # CR-01 멤버 메타 — list of flat map (Firestore nested-array 회피 정합).
            rec["_memberFaults"] = [
                {k: v for k, v in (m or {}).items() if not str(k).startswith("_")}
                for m in ((d or {}).get("_memberFaults") or ())
            ]
            rec["_memberFaultKeyDicts"] = [
                mfk.to_dict() for mfk in ((d or {}).get("_memberFaultKeys") or ())
            ]
            supported_doc.append(rec)
        causes_doc = []
        for rc in rich.get("root_cause_hypotheses") or ():
            causes_doc.append({
                "text": rc.text,
                "faultKeyDict": rc.fault_key.to_dict(),
                "sourceIds": list(rc.source_difference_ids or ()),
                "supportCount": int(rc.support_count or 0),
            })
        return {
            "rich": True,
            "status": str(rich.get("status", "")),
            "verdict": verdict_doc,
            "supported_differences": supported_doc,
            "root_cause_hypotheses": causes_doc,
            "telemetry": dict(rich.get("telemetry") or {}),
        }

    @staticmethod
    def _rich_from_doc(doc: dict) -> dict:
        from .vision_veto import FaultKey, RootCauseHypothesis

        verdict_doc = doc.get("verdict")
        verdict = None
        if verdict_doc:
            verdict = VisionVerdict(
                primary_fault=str(verdict_doc.get("primary_fault", "")),
                severity=str(verdict_doc.get("severity", "")),
                differences=tuple(verdict_doc.get("differences") or []),
            )
        supported = []
        for rec in doc.get("supported_differences") or ():
            d = {k: v for k, v in (rec or {}).items()
                 if k not in ("_faultKeyDict", "_supportCount", "_sourceIds",
                              "_measurementBacked",
                              "_memberFaults", "_memberFaultKeyDicts")}
            fkd = (rec or {}).get("_faultKeyDict")
            d["_faultKey"] = FaultKey.from_dict(fkd) if fkd else None
            d["_supportCount"] = int((rec or {}).get("_supportCount") or 0)
            d["_sourceIds"] = tuple((rec or {}).get("_sourceIds") or ())
            d["_measurementBacked"] = bool((rec or {}).get("_measurementBacked") or False)
            d["_memberFaults"] = tuple(
                dict(m or {}) for m in ((rec or {}).get("_memberFaults") or ())
            )
            d["_memberFaultKeys"] = tuple(
                FaultKey.from_dict(x)
                for x in ((rec or {}).get("_memberFaultKeyDicts") or ())
            )
            supported.append(d)
        causes = []
        for rc in doc.get("root_cause_hypotheses") or ():
            causes.append(RootCauseHypothesis(
                text=str((rc or {}).get("text", "")),
                fault_key=FaultKey.from_dict((rc or {}).get("faultKeyDict") or {}),
                source_difference_ids=tuple((rc or {}).get("sourceIds") or ()),
                support_count=int((rc or {}).get("supportCount") or 0),
            ))
        return {
            "status": str(doc.get("status", "")),
            "verdict": verdict,
            "supported_differences": supported,
            "root_cause_hypotheses": causes,
            "telemetry": dict(doc.get("telemetry") or {}),
        }

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
    # 이미지 분기 (Task 1, D-01) — still-frame 비교 입력. 명시 분기로 video fall-through 와 분리.
    if ext == ".png":
        return "image/png"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
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


def _upload_image(client, local_image_path: str):
    """caller local still 이미지 → Gemini Files API ACTIVE 대기 (Task 1, D-01).

    _upload_video 의 형제 — ACTIVE-wait/PROCESSING poll/TimeoutError/ascii-safe-path/
    tmp unlink 디시플린 동일, mime 만 이미지 분기(_mime). still-frame 비교 입력 swap.

    D-10 HIGH-2: 존재 가드 먼저 — 빈/없는 still 파일 업로드 방지 (path 검증 후 업로드).
    """
    import time

    from google.genai import types as genai_types  # lazy — top-level import 금지(D-16)

    # 존재 가드 (D-10 HIGH-2) — fake client/업로드 호출 전에 경로 검증.
    if not os.path.isfile(local_image_path):
        raise FileNotFoundError(f"still 이미지 없음: {local_image_path}")

    upload_path, tmp_path = _ascii_safe_path(local_image_path)
    uploaded = client.files.upload(
        file=upload_path,
        config=genai_types.UploadFileConfig(mime_type=_mime(local_image_path)),
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
    *,
    student_frame_path: str | None = None,
    reference_frame_path: str | None = None,
    part_scopes: list | None = None,
    frame_indices: list | None = None,
    selector_version: str | None = None,
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
    uploaded = None
    ref_uploaded = None
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
    finally:
        # 업로드 영상 정리 — Gemini File API 20GB(file_storage_bytes) 저장소 누수
        # 방지 (2026-06-22). 파일은 48h TTL 이지만 배치 sweep 은 그 전에 한도를
        # 채워 429 RESOURCE_EXHAUSTED 를 낸다(reference 가 분석마다 재업로드됨).
        # 캐시 hit 는 재업로드 0 이라 삭제해도 결정론 영향 없음. 삭제 실패 graceful.
        for _handle in (uploaded, ref_uploaded):
            _name = getattr(_handle, "name", None)
            if not _name:
                continue
            try:
                client.files.delete(name=_name)
            except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
                log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)

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


def assess_fault_context(
    student_frame_path: str,
    reference_frame_path: str,
    *,
    at_seconds: float | None = None,
    part_scopes: list | None = None,
    frame_indices: list | None = None,
    reference_frame_indices: list | None = None,
    selector_version: str | None = None,
) -> dict:
    """still-frame 쌍 → 부위별 fan-out rich dict (23 GAP-FIX — production wiring).

    **이것이 23-01/02 part-wise fan-out 의 production 진입점이다.** assess_fault_severity
    의 whole-video 경로(_aggregate_comparison_verdict)는 differences 에서 `_`-prefixed
    메타(`_faultKey` 등)를 strip 하므로 recall(faultKeys)이 비어버린다. 이 함수는 두 still
    IMAGE 를 업로드(_upload_image, NOT _upload_video)한 뒤 _run_part_frame_fanout 을 호출해
    canonical FaultKey + support 게이트 + root cause 가 보존된 rich dict 를 그대로 반환한다.

    반환 dict: {status, verdict, supported_differences, root_cause_hypotheses, telemetry}.
      · supported_differences[]._faultKey = FaultKey (to_trace_dict 가 faultKeys 산출).
      · telemetry.completedCalls = geminiCallCount (to_trace_dict).

    결정론 (D-06, eval cold/warm 게이트): still-granularity cache 키로 rich dict 를
    round-trip 한다 — cold miss → store_rich, warm hit → 동일 dict(재샘플링 0). cache 키는
    INPUT_GRANULARITY_FRAME_PAIR 마커 + (student, reference) image hash PAIR + at_seconds +
    selector_version + frame_indices 로 whole-video 키와 충돌 0.

    객관성/정리 디시플린은 assess_fault_severity 와 동일 — Gemini File API DELETE finally,
    _SCORE_PATTERN 점수 누출 가드(fan-out 내부 per-call 적용). 어떤 실패도 graceful:
    status="skipped_error" + 빈 supported/root_cause 로 분석 흐름을 막지 않는다(Pitfall 5).
    """
    scopes = list(part_scopes) if part_scopes else list(VETO_PART_SCOPES)

    def _skipped(telemetry: dict | None = None) -> dict:
        return {
            "status": "skipped_error",
            "verdict": None,
            "supported_differences": [],
            "root_cause_hypotheses": [],
            "telemetry": telemetry or {},
        }

    # (1) adapter-local 전제조건: client (키 부재/SDK 실패 → graceful skipped_error).
    try:
        client = _ensure_client()
    except Exception as exc:  # noqa: BLE001 - Pitfall 5 graceful
        log.warning("Gemini client 사용 불가 — still 비교 skipped (graceful): %s", exc)
        return _skipped()

    # (2) student/reference image hash → cache 키 (hash 만 PII 로 로그).
    try:
        from .technique_cache import compute_video_hash  # 파일 바이트 hash (이미지 호환).

        student_hash = compute_video_hash(student_frame_path)
        reference_hash = compute_video_hash(reference_frame_path)
    except FileNotFoundError:
        log.warning("still 이미지 없음 — still 비교 skipped (graceful)")
        return _skipped()
    except Exception as exc:  # noqa: BLE001 - hash 실패 graceful
        log.warning("still hash 산출 실패 — skipped (graceful): %s", exc)
        return _skipped()

    cache = VisionVetoCache()
    key = VisionVetoCache.build_key(
        video_hash=student_hash,
        model_name=DEFAULT_VISION_MODEL,
        input_granularity=INPUT_GRANULARITY_FRAME_PAIR,
        at_seconds=at_seconds,
        reference_hash=reference_hash,
        selector_version=selector_version,
        frame_indices=frame_indices,
    )

    # (3) cache hit → rich dict 결정론 반환 (Gemini 호출 0, 재샘플링 0).
    cached = cache.lookup_rich(key)
    if cached is not None:
        log.info("VisionVetoCache rich hit: %s", student_hash[:8])
        tel = dict(cached.get("telemetry") or {})
        tel["cacheKey"] = key
        tel["cacheHit"] = True
        cached["telemetry"] = tel
        return cached

    # (4) miss → 두 still IMAGE 업로드(영상 아님) + part-wise fan-out.
    student_uploaded = None
    ref_uploaded = None
    try:
        student_uploaded = _upload_image(client, student_frame_path)
        ref_uploaded = _upload_image(client, reference_frame_path)
        result = _run_part_frame_fanout(
            client, ref_uploaded, student_uploaded,
            part_scopes=scopes, at_seconds=at_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - 업로드/fan-out 실패 graceful (Pitfall 5)
        log.warning("still fan-out 실패 — skipped (graceful): %s", exc)
        return _skipped()
    finally:
        # 업로드 still 이미지 정리 — Gemini File API 저장소 누수 방지(48h TTL 전 배치
        # sweep 한도 소진 → 429). cache hit 는 재업로드 0 이라 삭제해도 결정론 영향 0.
        for _handle in (student_uploaded, ref_uploaded):
            _name = getattr(_handle, "name", None)
            if not _name:
                continue
            try:
                client.files.delete(name=_name)
            except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
                log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)

    # (5) telemetry 보강 — eval 하네스/trace 가 읽는 키 (cacheKey/Hit/frameIndices).
    tel = dict(result.get("telemetry") or {})
    tel["cacheKey"] = key
    tel["cacheHit"] = False
    if frame_indices is not None:
        tel["studentFrameIndices"] = list(frame_indices)
    if reference_frame_indices is not None:
        tel["referenceFrameIndices"] = list(reference_frame_indices)
    result["telemetry"] = tel

    # (6) cache 저장 후 반환 (resource_limited 도 저장 — 동일 입력 결정론 재현).
    cache.store_rich(key, result)
    return result


def assess_fault_context_video(
    student_video_path: str,
    reference_video_path: str,
    *,
    at_seconds: float | None = None,
    part_scopes: list | None = None,
) -> dict:
    """full-VIDEO 쌍 → 부위별 fan-out rich dict (Phase 24 close-out A, belle 2026-06-29).

    assess_fault_context 의 still-frame 변형 — 두 still IMAGE 대신 학생/기준 **영상 전체**를
    업로드(_upload_video)해 동일 _run_part_frame_fanout 을 돌린다. 산출(supported_differences
    +canonical FaultKey +support 게이트 +root cause)·감점 배선·정리 디시플린 전부 동일하고
    **입력만 full-video** 다.

    왜 (실측 근거): production still-frame 경로는 kip-up 같은 dynamic/inverted 동작에서 결함을
    못 잡았다(2026-06-29 A/B sweep: kip-up fault 99/100 위양성, vision eligible인데도 단편
    프레임이 결함 순간을 놓침, [[kipup-fp-is-stillframe-vision-not-alignment-gate]]). 반면
    full-video reference-anchored 비교는 6/6 변별([[vision-track-validated-alignment-gate-blocks-it]]).
    `_call_gemini_comparison` 프롬프트는 이미 "두 영상" 비교용이라 영상 입력이 더 정합이다
    (still 을 영상이라 라벨링하던 mismatch 해소). frame 선택/alignment 의존 0 — Gemini 가
    영상 안에서 결함 순간을 직접 찾는다.

    캐시: INPUT_GRANULARITY('whole') + (student, reference) 영상 hash PAIR → frame_pair 키와
    충돌 0. 결정론(eval cold/warm): rich dict round-trip 동일. 객관성/graceful 디시플린은
    assess_fault_context 와 동일(어떤 실패도 status='skipped_error').
    """
    scopes = list(part_scopes) if part_scopes else list(VETO_PART_SCOPES)

    def _skipped(telemetry: dict | None = None) -> dict:
        return {
            "status": "skipped_error",
            "verdict": None,
            "supported_differences": [],
            "root_cause_hypotheses": [],
            "telemetry": telemetry or {},
        }

    try:
        client = _ensure_client()
    except Exception as exc:  # noqa: BLE001 - Pitfall 5 graceful
        log.warning("Gemini client 사용 불가 — video 비교 skipped (graceful): %s", exc)
        return _skipped()

    try:
        from .technique_cache import compute_video_hash

        student_hash = compute_video_hash(student_video_path)
        reference_hash = compute_video_hash(reference_video_path)
    except FileNotFoundError:
        log.warning("영상 없음 — video 비교 skipped (graceful)")
        return _skipped()
    except Exception as exc:  # noqa: BLE001 - hash 실패 graceful
        log.warning("video hash 산출 실패 — skipped (graceful): %s", exc)
        return _skipped()

    cache = VisionVetoCache()
    key = VisionVetoCache.build_key(
        video_hash=student_hash,
        model_name=DEFAULT_VISION_MODEL,
        # 'whole_fanout' — assess_fault_severity 의 'whole' verdict-only 캐시와 분리(필수,
        # 위 상수 주석: lookup_rich stale-hit 차단). frame_pair 키와도 충돌 0.
        input_granularity=INPUT_GRANULARITY_WHOLE_FANOUT,
        at_seconds=at_seconds,
        reference_hash=reference_hash,
    )

    cached = cache.lookup_rich(key)
    if cached is not None:
        log.info("VisionVetoCache rich hit (video): %s", student_hash[:8])
        tel = dict(cached.get("telemetry") or {})
        tel["cacheKey"] = key
        tel["cacheHit"] = True
        cached["telemetry"] = tel
        return cached

    student_uploaded = None
    ref_uploaded = None
    try:
        student_uploaded = _upload_video(client, student_video_path)
        ref_uploaded = _upload_video(client, reference_video_path)
        result = _run_part_frame_fanout(
            client, ref_uploaded, student_uploaded,
            part_scopes=scopes, at_seconds=at_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - 업로드/fan-out 실패 graceful (Pitfall 5)
        log.warning("video fan-out 실패 — skipped (graceful): %s", exc)
        return _skipped()
    finally:
        for _handle in (student_uploaded, ref_uploaded):
            _name = getattr(_handle, "name", None)
            if not _name:
                continue
            try:
                client.files.delete(name=_name)
            except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
                log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)

    tel = dict(result.get("telemetry") or {})
    tel["cacheKey"] = key
    tel["cacheHit"] = False
    tel["inputGranularity"] = INPUT_GRANULARITY_WHOLE_FANOUT
    result["telemetry"] = tel
    cache.store_rich(key, result)
    return result


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
        # severity 는 median 유지(non-scoring 라벨, ND-02). union 은 부위별 최고 severity/
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


# ─────────────────── precision/support 게이트 (Task 2, H1 + D-09 HIGH-2) ───────────────────


def _filter_supported_differences(
    per_call_differences: list,
    *,
    part_scope_hint: str = "line",
    min_support_k: int = VETO_SUPPORT_K,
) -> list:
    """per-call difference list 들을 canonical FaultKey 로 정규화 후 N 중 K support 만 인정.

    raw body_part 문자열로 세면 "왼팔/left arm/왼쪽 팔꿈치" 가 분산돼 K 미달(recall 손실)
    + 모호한 "팔"이 양쪽 부풀림. 따라서 카운트 전에 각 difference 를 단일 owner
    `vision_veto.FaultKey` 로 정규화한다(D-09 HIGH-2 + D-17 MED-3). severity='none'/빈
    difference 는 인정 결함이 아니다(정타 보존). 단발(support<K)은 drop/descriptive-only.

    support 게이트 = **distinct call 교차 확증** (25-02 review WR-01): fold 후에는
    한 호출이 "왼쪽 어깨"+"오른쪽 어깨" 를 항목화하면 발생-건수 카운트로는 즉시 K=2
    자기충족된다(v10 프롬프트의 좌/우 개별 항목화 강제가 이를 증폭). H1 의 "N 중 K
    교차 확증" 의미를 보존하기 위해 게이트는 그 keypoint_set 을 언급한 **서로 다른
    call 수**로 판정한다. `_supportCount` 도 distinct-call 확증 수(신뢰도 표시 정합).

    측정-동반 예외 (25-04 #3(c) WR-01 균형, agg4): distinct-call K 미달 그룹이라도
    멤버 중 **명시 각도쌍 측정**(student_angle_deg + reference_angle_deg, 산술 편차>0
    — vision_veto.explicit_measured_deviation_deg)을 동반한 관측이 있으면 지지 인정.
    근거: 측정값을 동반한 언급은 단발 환각의 형상이 아니라 관측 신호다(환각 차단
    H1 의 표적은 근거-무 언급) — distinct-call 강화가 scope-집중 fan-out(부위당 1 call)
    에서 정당한 단일-scope 관측(예: 상체 결함은 upper_body call 에서만 보임)까지
    drop 하던 커버리지 손실을 구조적으로 복원한다. 새 튜닝 상수 0 / K=2 불변 /
    approx 추정(각도쌍 아님)은 예외 비대상(어림 편차는 확증 대체 불가). 정타 방어는
    프롬프트("편차 없으면 빈 배열") + severity none 필터가 그대로 담당(짚기-FP 0/5).
    대표/멤버 rank 의 dev 비교도 각도쌍 산술 편차 우선(폴백 approx).

    그룹 키 = **keypoint_set 단독** (25-02 Task 1, 25-RESEARCH §1 처방 (a)). FaultKey
    4필드 전체로 그룹하면 같은 부위 언급이 side("왼쪽 어깨"=left vs "어깨"=unknown) /
    fault_kind("굽음" vs "정렬 흐트러짐") fragment 로 분산돼 support K 미달 drop —
    kip-up fault 의 상체(어깨) 결함이 짚기에서 통째로 사라지던 원인. part_scope 는
    hint 균일이라 원래 무변별. 대표 `_faultKey.side` 는 그룹 내 명시(left/right) side
    가 유일하면 그 side, 혼재·부재면 "unknown"(25-01 pointed 매퍼가 unknown → 양측 해소).

    ⚠ rich 캐시는 집계 후 supported_differences 를 저장하므로 이 함수의 그룹핑 변경 =
    AGGREGATION_VERSION bump 필수 (kip-up whole/whole_fanout stale-hit FP 이력, 90d038f).

    멤버 보존 (25-02 review CR-01): fold 는 support 집계용일 뿐 — 라우터
    (`ipsf_criteria.criteria_for_fault`)는 RAW body_part 로 split_angle vs leg_extension
    을 가르므로("keypoint_set 단독 매핑 불가" 불변), 대표 1개만 남기면 같은 keypoint_set
    의 서로 다른 결함(스플릿 부족 vs 무릎 굽음)이 대표-선정 복권으로 라우팅에서 소실된다
    (kip-up split 감점 = vision-주입 유일 경로, belle 결정 A). 따라서 대표에
    `_memberFaults`(그룹 멤버 원문 dict, (body_part, fault_state) dedup — 대표 rank/dev
    규칙으로 최선 유지) + `_memberFaultKeys`(fold 전 원본 FaultKey — recall trace 어휘)
    를 부착한다. 엔진(deduction_engine.tally)은 멤버 각각을 라우팅한다.

    반환: support≥K 통과 difference list — 각 canonical 키별 대표 1개(최고 severity/dev),
    `_supportCount`/`_faultKey`/`_sourceIds`/`_memberFaults`/`_memberFaultKeys` 메타 부착.
    """
    from .vision_veto import explicit_measured_deviation_deg, fault_key_from_difference

    groups: dict[str, dict] = {}
    diff_id = 0
    for call_idx, call_diffs in enumerate(per_call_differences or ()):
        for d in call_diffs or ():
            diff_id += 1
            part = str((d or {}).get("body_part", "")).strip()
            if not part:
                continue
            sev = str((d or {}).get("severity", "")).strip().lower()
            if sev in _BODYPART_SEVERITY_FLOOR:
                continue  # none/빈 = 인정 결함 아님 (정타 보존).
            fk = fault_key_from_difference(d, part_scope_hint=part_scope_hint)
            key = fk.keypoint_set  # side/fault_kind fold — fragment 접합 (25-02).
            # (a)/(c) — 명시 각도쌍 산술 편차 우선 (rank 비교 + 측정-동반 판정 겸용).
            explicit = explicit_measured_deviation_deg(d)
            if explicit is not None:
                dev = explicit
            else:
                try:
                    dev = float((d or {}).get("approx_angle_deviation_deg") or 0.0)
                except (TypeError, ValueError):
                    dev = 0.0
            measured_backed = explicit is not None and explicit > 0.0
            sev_rank = _SEVERITY_RANK.get(sev, 0)
            cur = groups.get(key)
            if cur is None:
                cur = groups[key] = {
                    "calls": {call_idx},
                    "ids": [diff_id],
                    "fault_key": fk,
                    "sides": {fk.side} if fk.side in ("left", "right") else set(),
                    "best": {**d, "_rank": sev_rank, "_dev": dev},
                    "members": {},
                    "measured_backed": measured_backed,
                }
            else:
                cur["calls"].add(call_idx)
                cur["ids"].append(diff_id)
                cur["measured_backed"] = cur["measured_backed"] or measured_backed
                if fk.side in ("left", "right"):
                    cur["sides"].add(fk.side)
                if sev_rank > cur["best"]["_rank"] or (
                    sev_rank == cur["best"]["_rank"] and dev > cur["best"]["_dev"]
                ):
                    cur["best"] = {**d, "_rank": sev_rank, "_dev": dev}
                    cur["fault_key"] = fk  # 대표 difference 의 FaultKey 추적.
            # 멤버 원문 축적 (CR-01) — (body_part, fault_state) dedup, 대표 규칙과 동일한
            # rank→dev 비교로 항목별 최선 유지 (split 편차 등 vision-측정값 보존).
            mkey = (part, str((d or {}).get("fault_state", "")).strip())
            m = cur["members"].get(mkey)
            if m is None or sev_rank > m["_rank"] or (
                sev_rank == m["_rank"] and dev > m["_dev"]
            ):
                cur["members"][mkey] = {"d": {**d}, "fk": fk, "_rank": sev_rank, "_dev": dev}

    out: list = []
    for g in groups.values():
        if len(g["calls"]) < min_support_k and not g["measured_backed"]:
            # distinct-call 교차 확증 미달 + 명시 측정 비동반 → drop (H1 환각 차단,
            # WR-01). 측정-동반(각도쌍 산술>0) 관측은 단일 call 도 지지 인정 (agg4 (c)).
            continue
        # side 그룹-해소: 명시 side 가 유일하면 그 side, 혼재/부재면 unknown.
        sides = g["sides"]
        resolved_side = next(iter(sides)) if len(sides) == 1 else "unknown"
        rec = {k: v for k, v in g["best"].items() if not k.startswith("_")}
        rec["_supportCount"] = len(g["calls"])
        rec["_faultKey"] = dc_replace(g["fault_key"], side=resolved_side)
        rec["_sourceIds"] = tuple(g["ids"])
        rec["_measurementBacked"] = bool(g["measured_backed"])
        members = list(g["members"].values())
        rec["_memberFaults"] = tuple({**m["d"]} for m in members)
        rec["_memberFaultKeys"] = tuple(m["fk"] for m in members)
        out.append(rec)
    # severity 내림차순(지배 결함이 앞).
    out.sort(key=lambda r: -_SEVERITY_RANK.get(
        str(r.get("severity", "")).strip().lower(), 0
    ))
    return out


def _derive_root_causes_from_supported_differences(supported: list) -> list:
    """support 통과 difference 만으로 root cause 유도 + provenance 보존 (D-13 MED-1).

    drop 된 환각 difference 의 root cause 는 절대 새지 않는다(supported 입력만). 모든
    difference 가 drop 되면 root cause 0. 각 root cause 는 fault_key/source_difference_ids/
    support_count 를 보존한다.
    """
    from .vision_veto import RootCauseHypothesis

    causes: list = []
    for rec in supported or ():
        fk = rec.get("_faultKey")
        if fk is None:
            continue
        part = str(rec.get("body_part", "")).strip()
        fault_state = str(rec.get("fault_state", "")).strip()
        text = part if not fault_state else f"{part}: {fault_state}"
        causes.append(
            RootCauseHypothesis(
                text=text,
                fault_key=fk,
                source_difference_ids=tuple(rec.get("_sourceIds") or ()),
                support_count=int(rec.get("_supportCount") or 0),
            )
        )
    return causes


def _run_part_frame_fanout(
    client,
    ref_uploaded,
    student_uploaded,
    *,
    part_scopes: list,
    at_seconds: float | None,
    clock=None,
    wall_budget_s: float = MAX_VETO_WALL_S,
    max_calls: int = MAX_VETO_CALLS,
) -> dict:
    """부위별 프롬프트 fan-out — 호출/upload/wall-clock bound + fail-closed resource_limited.

    main path 의 normal `candidate_verdict` 는 planned call 전부 완료(samplingComplete=true)
    필수(D-13 HIGH-2, Option A). planned call 전부 완료 전 예산(호출/wall-clock) 소진은
    quorum 완료 여부와 무관하게 score-free `resource_limited` + telemetry 를 반환한다 —
    부분 샘플 verdict 는 wall-clock/cache 에 따라 흔들려 비결정적이라 위양성·결정론 게이트
    약화이므로 금지. 모든 호출은 _call_gemini_comparison(part_scope 전달).

    반환 dict: {status, verdict?, supported_differences, root_cause_hypotheses, telemetry}.
    """
    import time as _time

    _now = clock or _time.monotonic
    scopes = list(part_scopes) or list(VETO_PART_SCOPES)
    planned = min(len(scopes), max_calls)
    start = _now()
    per_call: list = []  # part_scope 별 difference list (support 집계 입력).
    parsed_verdicts: list = []
    completed = 0
    for idx in range(planned):
        # wall-clock budget 가드 — 호출 전 elapsed 확인 (fail-closed).
        if _now() - start > wall_budget_s:
            break
        raw_text = _call_gemini_comparison(
            client, ref_uploaded, student_uploaded, at_seconds,
            part_scope=scopes[idx],
        )
        completed += 1
        if _SCORE_PATTERN.search(raw_text or ""):
            continue  # 점수 누출 샘플 폐기(객관성).
        v = _parse_verdict(raw_text)
        if v is None:
            continue
        parsed_verdicts.append(v)
        per_call.append(list(v.differences or ()))

    duration_ms = int((_now() - start) * 1000)
    telemetry = {
        "completedCalls": completed,
        "plannedCalls": planned,
        "uploadCount": 2,
        "durationMs": duration_ms,
        "samplingComplete": completed >= planned,
    }

    # fail-closed (Option A) — planned call 전부 완료 전 예산 소진 → resource_limited.
    if completed < planned:
        return {
            "status": "resource_limited",
            "verdict": None,
            "supported_differences": [],
            "root_cause_hypotheses": [],
            "telemetry": telemetry,
        }

    # support 게이트 — 부위 union 으로 part_scope_hint='line'(혼합) 집계.
    supported = _filter_supported_differences(per_call, part_scope_hint="line")
    root_causes = _derive_root_causes_from_supported_differences(supported)
    # severity = 인정 결함의 median (정타 none 보존).
    if parsed_verdicts:
        ranks = sorted(_SEVERITY_RANK.get(v.severity, 0) for v in parsed_verdicts)
        median_rank = ranks[(len(ranks) - 1) // 2]
        median_severity = _RANK_TO_SEVERITY[median_rank]
    else:
        median_severity = "none"
    primary = parsed_verdicts[0].primary_fault if parsed_verdicts else "없음"
    verdict = VisionVerdict(
        primary_fault=primary,
        severity=median_severity,
        differences=tuple(
            {k: v for k, v in d.items() if not k.startswith("_")} for d in supported
        ),
    )
    return {
        "status": "candidate_verdict",
        "verdict": verdict,
        "supported_differences": supported,
        "root_cause_hypotheses": root_causes,
        "telemetry": telemetry,
    }


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


_PART_SCOPE_LABEL = {
    "upper_body": "상체(머리·목·어깨·양팔·팔꿈치·그립)",
    "lower_body": "하체(코어·허리·골반·양다리·무릎·발목)",
    "line": "전체 라인·정렬",
}


def _call_gemini_comparison(
    client, ref_uploaded, student_uploaded, at_seconds: float | None,
    part_scope: str | None = None,
) -> str:
    """비교(reference-anchored) generate_content — 기준 영상 먼저 + 학생 영상 (temp 0.0).

    contents 순서 = [기준 라벨, 기준 영상, 학생 라벨, 학생 영상, 비교 프롬프트].
    response_schema/temperature/thinking 는 단일 경로와 동일 (객관성·결정론 동일 보장).

    part_scope (Task 2, D-05): 제공 시 generic 부위-집중 프롬프트(특정 동작명/기대답
    금지, D-06). 두 영상 핸들은 분리 유지("나란히"=composite 아님, H3).

    구조화 강제 (25-02 Task 2, 25-RESEARCH §1 처방 (b)): scope 집중 호출에서 관찰한
    편차가 primary_fault 서사에만 남고 differences[] 미방출되면 support 집계가 아예
    못 본다(상체 결함 짚기 실패의 한 축). 레버 = per-move 특정성이 아닌 scope-집중
    특정성(flash-beats-pro 교훈) — 전 scope(upper/lower/line) 공통, 동작명 주입 0.
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
    prompt = _build_comparison_prompt(at_seconds)
    if part_scope:
        label = _PART_SCOPE_LABEL.get(part_scope, part_scope)
        # v11.0 (25-04 #3(b)): 세부-부위 순차 점검 + 관찰-전량 방출 강제 보강 — v10.1
        # 로도 상체(어깨) 관찰이 primary_fault 서사에만 남고 differences[] 미방출되던
        # 갭(run2/run3 kipup_upper). + (a) 측정 rubric(각도쌍) scope 호출에도 주입.
        # 정타 방어("편차 없으면 항목을 만들지 말 것")는 유지·강화(짚기-FP 0/5 게이트).
        prompt = (
            f"{prompt}\n\n참고: 이번에는 특히 [{label}] 부위에 집중해 기준 영상과 "
            "대조하세요. 이 부위에 속한 세부 부위를 하나씩 순서대로 점검하고, 관찰한 "
            "각 편차는 **하나도 빠짐없이** 반드시 differences[] 배열의 개별 항목으로 "
            "구조화하세요 — primary_fault 서사에만 언급하고 differences 에서 누락하는 "
            "것은 금지이며, 그런 응답은 무효입니다. body_part 에는 좌/우를 명시하세요"
            "(예: '왼쪽 어깨'). 좌/우는 화면(카메라) 기준이 아니라 **수행자(학생) 본인 "
            "신체 기준**입니다. 어느 쪽인지 확실하지 않으면 좌/우 없이 부위 이름만 "
            "적으세요(억지 지정 금지). 각도 관련 편차는 student_angle_deg 와 "
            "reference_angle_deg 로 학생/기준 각도를 각각 추정하고 measurement_basis "
            "에 잰 방법을 서술하세요(편차 계산은 코드 소관). 단 1·2번 규칙(정타/사소차/"
            "촬영조건은 결함 아님)은 그대로입니다 — 이 부위에 관찰 가능한 편차가 없으면 "
            "항목을 만들지 말고 빈 배열이 정답입니다."
        )
    response = client.models.generate_content(
        model=DEFAULT_VISION_MODEL,
        contents=[
            "기준(정타) 영상:",
            ref_uploaded,
            "평가 대상(학생) 영상:",
            student_uploaded,
            prompt,
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
    # (2) 없으면 differences 중 최악, (3) 둘 다 없으면 'none'(짚을 측정대상 없음 —
    # 모호하면 결함 지목 안 함). non-scoring 라벨일 뿐 채점 입력 아님(ND-02).
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
