"""Phase 22 Wave 1 bake-off 하네스 — Qwen 3.6-VL-8B vs InternVL 3.5-8B 4축 계측.

D-04 bake-off 의 계측기다. 양 백본을 **동일 조건**(동일 시스템 프롬프트 + few-shot +
guided JSON)에서 4축으로 재고, 승자 하나를 ANALYSIS 엔진 백본으로 고른다. 이 파일은
계측 로직(순수 함수)과 실행 골격을 담고, 실제 추론(vLLM serve)은 Pod 에서 22-06 이
수행한다. run_sweep.py(phase24) 골격을 복사해 검증된 eval 규율을 승계한다:
EVAL_OUT_DIR repo-밖 강제 / SERIAL / _meta provenance / cold re-run / ALLDONE 마커.

── 4축 (변별력 지표, 22-RESEARCH FT-01 / NLM Q7) ──
  A. grounding  = 예측-정답 관절 L2 평균. **synthetic_grounding 트랙만** (실영상엔
                  진짜 정답 좌표 없음 — Open Question 1, [[analysis-objectivity...]]).
  B. temporal   = 시계열 순서/역재생 함정 정오. trap 트랙 CircularEval(선택지 순서 전
                  조합 정답 시만 1점 — MMBench 방식). 언어 프라이어 shortcut 검출.
  C. json       = 파싱 성공률 + REPORT_KEYS Exact Match + CER(레벤슈타인 편집거리).
                  schema.normalize_report 화이트리스트 + guided JSON 으로 포맷 통제.
  D. coaching   = LLM-as-a-Judge — 외부 최상위 모델(gemini-3.5-flash)이 결함 분석의
                  생체역학 타당성을 1~5 블라인드 채점(모델명 은닉, 주입 가능 callable).

── 객관성 하드가드 ([[analysis-objectivity-no-human-scores]]) ──
  모델은 점수를 절대 내지 않는다. bake-off 4축은 모델-산출 점수가 아니라 우리 태스크의
  변별력(합성 grounding L2 / 함정 정오 / 포맷 준수 / judge 블라인드)을 잰다. 사람 점수
  ground-truth 라벨 영구 금지. real/hard_negative label = 영상 파생 입력 라벨.

── 동시성 ([[pipeline-not-concurrency-safe-eval-serial]]) ──
  SERIAL — 한 모델·한 항목 순차. vLLM serve 는 후보 백본을 한 번에 하나만 기동
  (--model 인자). 두 백본 동시 로드 = VRAM OOM + cross-contamination.

── Pod 실행 env (22-06, GPU + vLLM + Gemini judge 필요) ──
    # 후보 모델을 한 번에 하나 serve (예: Qwen):
    #   python3 -m vllm.entrypoints.openai.api_server \
    #       --model $CANDIDATE_MODEL --port 8000 --dtype bfloat16 \
    #       --limit-mm-per-prompt '{"image": 64}'
    # (vllm 0.24 실측: --limit-mm-per-prompt 는 JSON dict 형식 — 구식 key=value
    #  는 제거됨. video 키 불필요 — 요청은 image 파트만 사용.)
    source /workspace/aws_env.sh && \
    export EVAL_OUT_DIR=/workspace/sunity_eval_out \
           BAKEOFF_VLLM_URL=http://127.0.0.1:8000/v1 \
           BAKEOFF_MODEL=$CANDIDATE_MODEL \
           FIREBASE_SA_PATH=/workspace/firebase-sa.json \
           VIDEO_BUCKET=sunity-motion-pilot-videos && \
    export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
    cd /workspace/SunityMotion/backend && \
    PYTHONPATH=shared/python:training:. python3 evals/phase22/run_bakeoff.py --model $BAKEOFF_MODEL

정확한 HF/ms-swift 모델 ID 는 22-06(RESEARCH A6)에서 확정 — 여기서는 --model 인자로
파라미터화하고 추측 ID 를 사실로 하드코딩하지 않는다.

── 실행부 (22-06 채움, 2026-07-11) ──
  · real/hard_negative = 프레임(9fps 추출→64 서브샘플→448 JPEG) + RTMW 좌표 캐시
    (BAKEOFF_COORDS_CACHE, extract_eval_coords.py 로 사전 추출) → 리포트 JSON.
    zero-shot + few-shot(고정 소형 예시 1개 — 모델 공통, 공정) 두 모드.
  · synthetic_grounding = 베이스 좌표(BASE_SYNTH_ITEM, kip-up correct 캐시)에
    perturb.perturb_sequence(seed 고정) → 모델 corrected_coords vs 원좌표 L2.
  · trap = make_temporal_trap(seed 고정) 좌표 시퀀스 — frame 번호는 제시 순서로
    재부여(원 번호 유지 시 함정 정답 누출). 2지선다 × 선택지 순서 전 조합
    (CircularEval). trap 은 zero-shot 고정(리포트 포맷 무관 트랙).
  · 결정성 = 레코드별 raw sha256 저장 — cold re-run 리포트 간 해시 비교(러너).
  · judge 429/RESOURCE_EXHAUSTED → 부분 리포트 저장 후 exit 4 (즉시 중단 원칙).
  · 추가 env: BAKEOFF_FIXTURES_DIR(기본 /workspace/bakeoff_fixtures),
    BAKEOFF_COORDS_CACHE(기본 /workspace/phase22_coords_cache).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent  # backend/
for _p in (BACKEND / "shared" / "python", BACKEND, BACKEND / "training"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# schema = 학습 JSONL·bake-off·서빙이 공유하는 유일한 규격 소스(22-01). 순수 모듈이라
# import-time 로드 안전(vision_veto enum 은 lazy). GPU/네트워크 의존 0.
from datagen import schema  # noqa: E402
from datagen import perturb  # noqa: E402 — 합성/함정 트랙 생성 (순수, numpy 단독).
from datagen.build_jsonl import _coords_to_frames  # noqa: E402 — 좌표 표현 단일 owner.
from distill import pod_coords  # noqa: E402 — 좌표 캐시 키/로드 단일 owner 재사용.
from distill.gemini_teacher import DEFAULT_TASK_JOINTS, build_rtmw_text  # noqa: E402

MANIFEST_PATH = HERE / "fixtures" / "manifest.yaml"

# ── 산출물 경로 (phase24 run_sweep 근본원인 4 동일 패턴 — pod repo 오염 방지) ────
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_PHASE_SUBDIR = "phase22"

# 프레임 서브샘플 예산 + 리사이즈(VLM 입력 정합, NLM Q7). 9fps 배열 인덱스만 —
# 원 영상 재추출 금지([[still-pair]] 위상 불일치 실증, schema.select_frame_indices).
FRAME_BUDGET = 64
FRAME_RESIZE = 448  # 448x448 리사이즈.

# 코칭 judge 모델(외부 최상위, 블라인드). [[gemini-latest-model-versions]] Flash.
JUDGE_MODEL = "gemini-3.5-flash"


def _eval_out_dir() -> Path:
    root = Path(os.environ.get(_EVAL_OUT_ENV) or _EVAL_OUT_DEFAULT)
    return (root.expanduser() / _PHASE_SUBDIR).resolve()


def _resolve_out_dir() -> Path:
    """출력 디렉토리 확정 — repo 안이면 즉시 중단(baseline/커밋 소스 오염 차단).

    phase24 run_sweep _resolve_out_dir 와 동일 규율: bake-off 리포트가 git 커밋본을
    덮어써 게이트가 오염 기준으로 판정하는 사고를 원천 차단한다(25-SWEEP 근본원인 4).
    """
    out = _eval_out_dir()
    repo_root = BACKEND.parent.resolve()
    if out == repo_root or repo_root in out.parents:
        raise SystemExit(
            f"[eval-out] EVAL_OUT_DIR={out} 가 repo({repo_root}) 안을 가리킨다 — "
            "bake-off 산출물이 커밋 baseline 을 오염시킨다. repo 밖 경로로 설정하라 "
            f"(기본 {_EVAL_OUT_DEFAULT})."
        )
    return out


# ===========================================================================
# 4축 계측 함수 — 순수(모델 호출 없음, GPU/네트워크 무관). test_bakeoff_harness 검증.
# ===========================================================================
def score_grounding(pred, truth) -> float:
    """A. grounding L2 — 예측 좌표 vs 정답 좌표의 관절별 유클리드 거리 평균.

    synthetic_grounding 트랙 전용(정답=perturb 원좌표). pred/truth 는 동일 shape 의
    (..., C>=2) 배열 — 마지막 축의 앞 2채널(x,y)만 사용. NaN(가려짐) 좌표는 계측 제외.
    동일 좌표 → 0.0, (dx,dy) 균일 오프셋 → sqrt(dx^2+dy^2). shape 불일치 → ValueError.
    """
    p = np.asarray(pred, dtype=float)
    t = np.asarray(truth, dtype=float)
    if p.shape != t.shape:
        raise ValueError(f"pred/truth shape 불일치: {p.shape} vs {t.shape}")
    if p.shape[-1] < 2:
        raise ValueError(f"좌표 채널 C>=2 필요 — got {p.shape}")
    diff = p[..., :2] - t[..., :2]
    dist = np.sqrt((diff * diff).sum(axis=-1))  # 관절(·프레임)별 L2.
    mask = ~np.isnan(dist)
    if not mask.any():
        return float("nan")  # 전부 가려짐 → 계측 불가.
    return float(dist[mask].mean())


def score_temporal(predictions, correct) -> float:
    """B. temporal CircularEval — 시계열/역재생 함정 정오(0/1).

    predictions 가 리스트(선택지 순서 셔플 전 조합의 답)면 **전부** correct 와 일치할
    때만 1.0(MMBench CircularEval). 단일 값이면 == correct 판정. trap 트랙에서 정답
    correct='is_trap' 인데 모델이 정방향('forward')을 제출하면 0.0 → 언어 프라이어
    shortcut 검출. 빈 predictions → 0.0.
    """
    if isinstance(predictions, (list, tuple)):
        preds = list(predictions)
        if not preds:
            return 0.0
        return 1.0 if all(p == correct for p in preds) else 0.0
    return 1.0 if predictions == correct else 0.0


def score_json(raw) -> dict:
    """C. json 준수 — {parse, exact_match, cer}.

    · parse       = raw 가 dict(파싱 성공) → 1.0, 아니면 0.0.
    · exact_match = 최상위 키가 REPORT_KEYS 와 정확히 일치 **AND** 알파벳 정렬(철칙 2)
                    → 1.0. 키 누락/여분/정렬 위반 각각 0.0.
    · cer         = 예측 키 문자열 vs 기대 키 문자열 레벤슈타인 편집거리 / 기대 길이.
    schema.normalize_report 로 화이트리스트 검증(T-22-14 tampering 방어 — 스키마 밖
    키/거대 배열은 통과 못 하고 감점으로 계측, 크래시 아님).
    """
    expected_keys = list(schema.REPORT_KEYS)
    expected_keystr = ",".join(expected_keys)
    if not isinstance(raw, dict):
        return {"parse": 0.0, "exact_match": 0.0, "cer": 1.0}
    # normalize 는 항상 성공(방어적) — 파싱 자체는 dict 여부로 판정.
    schema.normalize_report(raw)
    raw_keys = list(raw.keys())
    sorted_ok = raw_keys == sorted(raw_keys, key=str)
    keys_match = sorted(raw_keys, key=str) == expected_keys
    exact = 1.0 if (keys_match and sorted_ok) else 0.0
    pred_keystr = ",".join(str(k) for k in raw_keys)
    cer = _cer(pred_keystr, expected_keystr)
    return {"parse": 1.0, "exact_match": exact, "cer": cer}


def build_judge_prompt(coaching_text: str) -> str:
    """D. 코칭 judge 블라인드 프롬프트 — 작성 모델명/후보명 **미포함**(공정성).

    외부 judge 가 어느 후보(Qwen/InternVL)의 출력인지 모른 채 생체역학 타당성만
    1~5 로 채점하게 한다. 이 문자열에 모델/후보 식별자가 새면 채점이 편향되므로
    test 가 부재를 강제한다(test_bakeoff_harness Test 4)."""
    return (
        "다음 폴스포츠 코칭 피드백의 생체역학적 타당성을 1~5 정수로 채점하라.\n"
        "블라인드 채점 — 작성 주체 정보는 제공되지 않는다. 결함 원인 분석이 관절\n"
        "운동학상 타당하고 처방이 구체적이면 높게, 일반론·모순이면 낮게 준다.\n"
        "숫자 1~5 하나만 출력.\n\n"
        "[코칭 피드백]\n"
        f"{coaching_text}\n"
    )


def score_coaching(coaching_text: str, judge) -> float:
    """D. 코칭 논리 — 주입된 judge callable 로 블라인드 1~5 채점.

    judge 는 prompt(str) -> 응답(str|number) 인 주입 가능 callable(테스트는 mock,
    Pod 는 gemini). 반환은 1~5 실수. 파싱 실패 시 float('nan'). judge 호출부를
    주입 가능 설계로 둬 pod-free 로 검증(모델 호출 없이 로직만)."""
    prompt = build_judge_prompt(coaching_text)
    raw = judge(prompt)
    return _parse_judge_score(raw)


def score_svg_wellformed(svg_spec) -> float:
    """F2 관측 — svg_spec wellformedness(스키마 유효 + target_angle_deg 수치형).

    선정 점수 축이 **아님**(베이스 모델 bake-off 에서 svg 품질 낮은 게 정상). 리포트
    _meta 관측치로만 남긴다. 정식 svg_spec 게이트는 SFT 후 22-07 assert_gates
    (check_svg_spec_validity)가 담당. 1.0=wellformed, 0.0=아님."""
    if not isinstance(svg_spec, dict):
        return 0.0
    if sorted(svg_spec.keys(), key=str) != list(schema.SVG_SPEC_KEYS):
        return 0.0
    tad = svg_spec.get("target_angle_deg")
    return 1.0 if isinstance(tad, (int, float)) and not isinstance(tad, bool) else 0.0


# ── 계측 보조 (순수) ────────────────────────────────────────────────────────
def _cer(pred: str, ref: str) -> float:
    """레벤슈타인 편집거리 / 기대 문자열 길이(Character Error Rate). ref 빈 문자열이면
    pred 빈=0.0, 아니면 1.0. 순수 DP."""
    if not ref:
        return 0.0 if not pred else 1.0
    dist = _levenshtein(pred, ref)
    return dist / len(ref)


def _levenshtein(a: str, b: str) -> int:
    """표준 편집거리 DP(삽입/삭제/치환 비용 1)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def _parse_judge_score(raw) -> float:
    """judge 응답에서 1~5 정수 추출. 숫자/문자열 모두 허용, 범위 밖·파싱 실패 → nan."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        val = float(raw)
    else:
        import re

        m = re.search(r"[1-5]", str(raw or ""))
        if not m:
            return float("nan")
        val = float(m.group(0))
    return val if 1.0 <= val <= 5.0 else float("nan")


# ===========================================================================
# 미니셋 로드 / 타입 라우팅 (순수).
# ===========================================================================
def load_manifest(path=None) -> dict:
    """평가 미니셋 매니페스트 로드. 순수 파일 I/O."""
    p = Path(path) if path else MANIFEST_PATH
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def items_by_type(manifest: dict) -> dict:
    """items 를 type 별로 그룹핑. real/hard_negative/synthetic_grounding/trap."""
    out: dict = {}
    for row in manifest.get("items") or []:
        out.setdefault(row.get("type"), []).append(row)
    return out


def grounding_items(manifest: dict) -> list:
    """grounding L2 계측 대상 = synthetic_grounding 트랙만(실영상 정답 좌표 부재)."""
    return [r for r in (manifest.get("items") or []) if r.get("type") == "synthetic_grounding"]


# ===========================================================================
# 프롬프트 조립 (schema 재사용 — 동일 시스템 프롬프트 통제).
# ===========================================================================
def build_system_prompt(joint_keys) -> str:
    """양 모델 동일 시스템 프롬프트 = bind_key_prompt(관절 키 사전 바인딩) + D-01 리포트
    키 선언. schema.bind_key_prompt 를 그대로 재사용해 학습·서빙과 프롬프트 일치."""
    key_line = schema.bind_key_prompt(joint_keys)
    report_keys = ", ".join(schema.REPORT_KEYS)
    return (
        "너는 폴스포츠 자세 분석기다. 영상과 관절 좌표(JSON)를 받아 결함을 짚고 측정만\n"
        "한다 — 점수/severity 는 절대 내지 않는다(감점은 별도 엔진). 출력은 아래 최상위\n"
        f"키만 알파벳 오름차순으로: [{report_keys}]. 결측은 키 삭제 없이 Null 로 고정.\n"
        f"{key_line}"
    )


def build_guided_json_schema() -> dict:
    """guided decoding response_format(json_schema) — REPORT_KEYS 최상위 구조 강제.

    vLLM/NIM response_format 로 포맷 변수를 통제해 순수 추론력만 비교(22-RESEARCH
    'Don't Hand-Roll' — 정규식 파싱 대신 guided JSON). 값 스키마는 느슨(모델별 표현
    차이 허용), 최상위 키 집합만 고정."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sunity_report_v1",
            "schema": {
                "type": "object",
                "properties": {k: {} for k in schema.REPORT_KEYS},
                "required": list(schema.REPORT_KEYS),
                "additionalProperties": False,
            },
        },
    }


# ===========================================================================
# 모델 백엔드 (lazy — import-time GPU/네트워크 의존 0).
# ===========================================================================
def _make_vllm_caller(base_url: str, model_id: str):
    """vLLM OpenAI 호환 endpoint 호출 callable 생성(lazy openai import).

    한 번에 한 모델(--model)만 기동된 endpoint 를 가리킨다. temp 0 + greedy 로
    결정성 확보(cold re-run 재현 대상). 반환 callable(messages, response_format=None)
    -> str — 기본 guided REPORT_KEYS 스키마, trap 트랙은 2지선다 enum 스키마 주입."""
    from openai import OpenAI  # lazy — Pod 에만 설치.

    client = OpenAI(
        base_url=base_url,
        api_key=os.environ.get("BAKEOFF_VLLM_KEY", "EMPTY"),
        timeout=1800.0,  # 상한 제거 후 최장 생성(잔여 컨텍스트 전부) 대비.
        max_retries=1,
    )
    guided = build_guided_json_schema()

    def _call(messages, response_format=None) -> str:
        # max_tokens 미지정 — vLLM 이 (max_model_len - prompt) 로 자동 상한. 고정
        # 2048 은 전 프레임 corrected_coords JSON 을 중간 절단해 grounding/json/
        # coaching 3축을 하네스가 죽이는 계측 결함이었다 (2026-07-11 run5 실증:
        # unparsed 전 레코드가 좌표 배열 한복판 ~3.6K자에서 절단).
        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.0,   # 결정성(cold re-run 2회 비교).
            top_p=1.0,
            response_format=response_format or guided,
        )
        return resp.choices[0].message.content or ""

    return _call


def _make_gemini_judge():
    """gemini 블라인드 judge callable(lazy). prompt(str) -> 응답(str).

    SDK = google-genai(신형, gemini_teacher._ensure_client 와 동일 계열) — 구
    google.generativeai 는 deprecated 라 학습 Pod venv 에 설치하지 않는다
    (2026-07-11, 22-06 실행부). temperature 0 = judge 결정성."""
    from google import genai  # lazy — Pod/키 필요.

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def _judge(prompt: str) -> str:
        resp = client.models.generate_content(
            model=JUDGE_MODEL, contents=prompt, config={"temperature": 0.0}
        )
        return (getattr(resp, "text", None) or "").strip()

    return _judge


class QuotaAbort(RuntimeError):
    """Gemini judge 429/RESOURCE_EXHAUSTED — 즉시 중단 신호(배치 원칙과 동일)."""


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper()


# ===========================================================================
# 실행부 헬퍼 (22-06 채움) — 프레임/좌표/메시지 준비 + 트랙별 러너.
# ===========================================================================
_FIXTURES_DIR_ENV = "BAKEOFF_FIXTURES_DIR"
_COORDS_CACHE_ENV = "BAKEOFF_COORDS_CACHE"
_FIXTURES_DIR_DEFAULT = "/workspace/bakeoff_fixtures"
_COORDS_CACHE_DEFAULT = "/workspace/phase22_coords_cache"

# 합성/함정 트랙 공통 베이스 좌표 = kip-up correct RTMW 캐시 (결정적 — 전 모델 동일).
BASE_SYNTH_S3_KEY = "fixtures/phase15/kip-up/correct.mp4"
PROFILE_PATH = BACKEND / "training" / "datagen" / "rtmw_error_profile.json"

_EXTRACTOR = None  # FfmpegFrameExtractor 싱글톤 (영상당 1회 추출).


def _fixtures_dir() -> Path:
    return Path(os.environ.get(_FIXTURES_DIR_ENV) or _FIXTURES_DIR_DEFAULT)


def _coords_cache_dir() -> Path:
    return Path(os.environ.get(_COORDS_CACHE_ENV) or _COORDS_CACHE_DEFAULT)


def _load_coords_rows(s3_key: str):
    """RTMW 좌표 캐시 로드 (pod_coords 단일 owner 키 규칙). miss → None (fail-loud
    는 호출자 — 사전 추출은 extract_eval_coords.py 담당, venv 에서 재추출 금지)."""
    key = pod_coords.coords_cache_key({"s3_key": s3_key})
    return pod_coords.load_cached_coords(str(_coords_cache_dir()), key)


def rows_to_array(rows, joint_keys=DEFAULT_TASK_JOINTS):
    """좌표 행([{'frame', '<joint>': [dx,dy,conf]|None}]) → ((T,J,3) [0,1] 정규화,
    frame 번호 리스트). 이산화 역변환 = /999 (schema Pattern 2 역방향). None → NaN."""
    keys = list(joint_keys)
    arr = np.full((len(rows), len(keys), 3), np.nan, dtype=float)
    frame_numbers: list[int] = []
    for i, row in enumerate(rows):
        frame_numbers.append(int(row.get("frame", i)))
        for j, name in enumerate(keys):
            v = row.get(name)
            if isinstance(v, (list, tuple)) and len(v) >= 2 and v[0] is not None and v[1] is not None:
                arr[i, j, 0] = float(v[0]) / 999.0
                arr[i, j, 1] = float(v[1]) / 999.0
                arr[i, j, 2] = float(v[2]) if len(v) > 2 and v[2] is not None else 1.0
    return arr, frame_numbers


def array_to_rows(arr, frame_numbers, joint_keys=DEFAULT_TASK_JOINTS):
    """(T,J,C) [0,1] 배열 → 좌표 행 (build_jsonl._coords_to_frames 단일 owner 재사용).
    frame 필드는 호출자가 준 번호로 재부여 — trap 트랙은 제시 순서 번호를 넘겨
    원 frame 번호 누출을 막는다."""
    rows = _coords_to_frames(np.asarray(arr, dtype=float), list(joint_keys), list(range(len(arr))), 1.0, 1.0)
    for row, fn in zip(rows, frame_numbers):
        row["frame"] = int(fn)
    return rows


def parse_corrected_coords(report: dict, frame_numbers, joint_keys=DEFAULT_TASK_JOINTS):
    """정규화 리포트의 corrected_coords → (T,J,2) [0,1] 배열 (grounding 계측 입력).

    행 매칭은 frame 필드 우선, 부재 시 순서. 결측/파싱 불가 관절 = NaN (score_grounding
    이 계측 제외). corrected_coords 자체가 None/비리스트 → 전-NaN (grounding nan)."""
    keys = list(joint_keys)
    t = len(frame_numbers)
    out = np.full((t, len(keys), 2), np.nan, dtype=float)
    rows = (report or {}).get("corrected_coords")
    if not isinstance(rows, list):
        return out
    by_frame = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        f = row.get("frame")
        by_frame[int(f) if isinstance(f, (int, float)) else i] = row
    for i, fn in enumerate(frame_numbers):
        row = by_frame.get(int(fn)) or (rows[i] if i < len(rows) and isinstance(rows[i], dict) else None)
        if not row:
            continue
        for j, name in enumerate(keys):
            v = row.get(name)
            if isinstance(v, (list, tuple)) and len(v) >= 2 and v[0] is not None and v[1] is not None:
                try:
                    out[i, j, 0] = float(v[0]) / 999.0
                    out[i, j, 1] = float(v[1]) / 999.0
                except (TypeError, ValueError):
                    pass
    return out


def prepare_frame_images(local_video_path: str, budget: int = FRAME_BUDGET, size: int = FRAME_RESIZE):
    """영상 → base64 JPEG 리스트. 파이프라인 9fps 추출(FfmpegFrameExtractor) 후
    select_frame_indices 서브샘플 + 448×448 리사이즈 (원 영상 재추출 금지 규율 —
    9fps 배열 인덱스만 선택)."""
    global _EXTRACTOR
    import base64
    import io

    from PIL import Image
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    if _EXTRACTOR is None:
        _EXTRACTOR = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    frames = _EXTRACTOR.extract(str(local_video_path))
    idxs = schema.select_frame_indices(len(frames), budget)
    out: list[str] = []
    for i in idxs:
        img = Image.fromarray(np.asarray(frames[i])).resize((size, size), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        out.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    return out


# ── 메시지 조립 (전 모델 동일 — 공정성) ────────────────────────────────────
_REPORT_TASK_TEXT = (
    "위 영상 프레임(시간 순)과 RTMW 관절 좌표를 분석해 D-01 통합 리포트 JSON 만 "
    "출력하라. 가려짐/튄 좌표는 corrected_coords 로 보정하고, 결함은 faults[] 로 "
    "짚고 측정한다. 점수(score/severity/overall/points)는 절대 출력하지 않는다."
)
_SYNTH_TASK_TEXT = (
    "아래 RTMW 관절 좌표 시퀀스에는 가려짐(Null)과 튄 좌표가 섞여 있다 (영상 없음 — "
    "좌표만으로 추론). 뼈길이 일관성·시간 연속성을 근거로 전 프레임·전 관절의 보정 "
    "좌표를 corrected_coords 에 [{\"frame\": N, \"<관절>\": [dx, dy], ...}] 형식"
    "(000~999 정수 그리드)으로 출력하라. 나머지 리포트 키는 Null 허용."
)


def _fewshot_pair():
    """few-shot 고정 예시 1개 — 소형 입력 + 이상적 리포트 (모델 공통, 결정적).

    합성 소형 좌표라 특정 동작/실영상 정답 누출 없음. 포맷 시연이 목적."""
    ex_rows = [
        {"frame": 0, "left_knee": [500, 500, 0.9], "right_knee": [520, 510, 0.9]},
        {"frame": 9, "left_knee": None, "right_knee": [530, 505, 0.9]},
    ]
    ex_report = {
        "coaching": "왼 무릎이 프레임 9에서 가려짐 — 직전 궤적 기준으로 보정했다. 무릎 신전을 유지하라.",
        "corrected_coords": [
            {"frame": 0, "left_knee": [500, 500], "right_knee": [520, 510]},
            {"frame": 9, "left_knee": [510, 502], "right_knee": [530, 505]},
        ],
        "faults": [],
        "segments": [{"end_frame": 9, "label": "hold", "start_frame": 0}],
        "svg_spec": None,
        "time_anchors": [],
    }
    user_text = (
        "[예시 입력]\n동작: 예시 홀드.\n"
        + build_rtmw_text(ex_rows)
        + "\n" + _REPORT_TASK_TEXT
    )
    return [
        {"role": "user", "content": [{"type": "text", "text": user_text}]},
        {"role": "assistant", "content": json.dumps(ex_report, ensure_ascii=False, sort_keys=True)},
    ]


def build_report_messages(coords_rows, frames_b64, motion, shots: str):
    """리포트 태스크 메시지 — 동일 시스템 프롬프트 + (few-shot 시 예시 1) + 사용자
    턴(동작명 + 좌표 텍스트 + 프레임 이미지)."""
    system = build_system_prompt(DEFAULT_TASK_JOINTS)
    msgs: list = [{"role": "system", "content": system}]
    if shots == "few":
        msgs.extend(_fewshot_pair())
    motion_line = f"분석 대상 동작: {motion}.\n" if motion else ""
    task = _REPORT_TASK_TEXT if frames_b64 else _SYNTH_TASK_TEXT
    content: list = [{"type": "text", "text": motion_line + build_rtmw_text(coords_rows) + "\n" + task}]
    for b64 in frames_b64 or []:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    msgs.append({"role": "user", "content": content})
    return msgs


_TRAP_OPTION_FORWARD = "자연스러운 시간 진행 (정상 순서)"
_TRAP_OPTION_TRAP = "시간 순서가 깨져 있음 (역재생 또는 셔플)"


def build_trap_schema() -> dict:
    """trap 2지선다 guided 스키마 — {'answer': '1'|'2'}."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "trap_choice_v1",
            "schema": {
                "type": "object",
                "properties": {"answer": {"type": "string", "enum": ["1", "2"]}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    }


def build_trap_messages(coords_rows, option_order: tuple):
    """trap 판정 메시지 — 좌표 시퀀스 + 2지선다 (option_order 로 순서 순열,
    CircularEval). frame 번호는 호출자가 제시 순서로 재부여했음을 전제."""
    options = {"forward": _TRAP_OPTION_FORWARD, "trap": _TRAP_OPTION_TRAP}
    lines = [f"{i + 1}. {options[key]}" for i, key in enumerate(option_order)]
    text = (
        "아래 RTMW 관절 좌표 시퀀스(frame 은 제시 순서)를 보고 물리적 운동 연속성 "
        "관점에서 판정하라 (영상 없음 — 좌표만으로 추론).\n"
        + build_rtmw_text(coords_rows)
        + "\n다음 중 하나를 고르라:\n" + "\n".join(lines)
        + '\nJSON {"answer": "1" 또는 "2"} 만 출력.'
    )
    system = "너는 폴스포츠 모션 시계열 분석기다. 좌표의 물리적 연속성만 근거로 판정한다."
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": [{"type": "text", "text": text}]},
    ]


# ── 트랙별 러너 — record dict 반환 (오류는 호출자에서 집계) ─────────────────
def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _judge_or_abort(judge, coaching_text: str):
    """judge 호출 — 429/RESOURCE_EXHAUSTED 는 QuotaAbort 로 승격(즉시 중단 원칙)."""
    if judge is None or not coaching_text:
        return None
    try:
        return score_coaching(coaching_text, judge)
    except Exception as exc:  # noqa: BLE001 - quota 만 승격, 그 외 nan 기록.
        if _is_quota_error(exc):
            raise QuotaAbort(str(exc)[:200]) from exc
        return float("nan")


def run_report_item(item: dict, caller, judge, shots: str) -> dict:
    """real/hard_negative 리포트 태스크 실행 + C/D축(+F2 관측) 계측."""
    rec: dict = {"id": item.get("id"), "type": item.get("type"), "mode": shots}
    s3_key = item.get("s3_key")
    if not s3_key:
        rec.update(skipped=True, note="s3_key null (relocate pending) — 계측 제외")
        return rec
    local = _fixtures_dir() / s3_key
    if not local.exists():
        rec.update(skipped=True, note=f"영상 없음: {local} — setup prefetch 확인")
        return rec
    coords_rows = _load_coords_rows(s3_key)
    if not coords_rows:
        rec.update(skipped=True, note="RTMW 좌표 캐시 miss — extract_eval_coords.py 선행 필요")
        return rec
    frames_b64 = prepare_frame_images(str(local))
    msgs = build_report_messages(coords_rows, frames_b64, item.get("motion"), shots)
    raw = caller(msgs)
    rec["raw_sha"] = _sha(raw)
    rec["raw"] = raw
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        parsed = raw
    rec["json"] = score_json(parsed if isinstance(parsed, dict) else str(parsed))
    if isinstance(parsed, dict):
        report = schema.normalize_report(parsed)
        rec["svg_wellformed"] = score_svg_wellformed(report.get("svg_spec"))
        if item.get("type") == "hard_negative":
            rec["hardneg_flagged_fault"] = bool(report.get("faults"))
        coaching = report.get("coaching")
        rec["coaching"] = _judge_or_abort(judge, coaching if isinstance(coaching, str) else "")
    return rec


def _base_sequence():
    """합성/함정 트랙 베이스 좌표 — (arr(T,J,3) 정규화, frame 번호). 캐시 필수."""
    rows = _load_coords_rows(BASE_SYNTH_S3_KEY)
    if not rows:
        raise SystemExit(
            f"[base] {BASE_SYNTH_S3_KEY} 좌표 캐시 miss — extract_eval_coords.py 를 먼저 실행하라."
        )
    return rows_to_array(rows)


def run_synth_item(item: dict, caller, base_arr, base_frames, profile, shots: str) -> dict:
    """synthetic_grounding — perturb(seed) → corrected_coords vs 원좌표 L2 (A축)."""
    rec: dict = {"id": item.get("id"), "type": "synthetic_grounding", "mode": shots,
                 "seed": item.get("seed"), "stage": item.get("stage")}
    rng = np.random.default_rng(int(item["seed"]))
    res = perturb.perturb_sequence(
        base_arr.copy(), profile, int(item.get("stage") or 1), rng, joint_keys=DEFAULT_TASK_JOINTS
    )
    in_rows = array_to_rows(res.perturbed, base_frames)
    msgs = build_report_messages(in_rows, [], "synthetic (좌표 보정 태스크)", shots)
    raw = caller(msgs)
    rec["raw_sha"] = _sha(raw)
    rec["raw"] = raw
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        parsed = raw
    rec["json"] = score_json(parsed if isinstance(parsed, dict) else str(parsed))
    if isinstance(parsed, dict):
        report = schema.normalize_report(parsed)
        pred = parse_corrected_coords(report, base_frames)
        rec["grounding"] = score_grounding(pred, res.original[..., :2])
    else:
        rec["grounding"] = float("nan")
    return rec


def run_trap_item(item: dict, caller, base_arr, base_frames) -> dict:
    """trap — make_temporal_trap(seed) 좌표, 2지선다 전 순열(CircularEval) → B축."""
    rec: dict = {"id": item.get("id"), "type": "trap", "mode": "zero", "seed": item.get("seed")}
    rng = np.random.default_rng(int(item["seed"]))
    trap_seq = perturb.make_temporal_trap(base_arr.copy(), rng)
    # frame 번호 = 제시 순서(0..T-1) — 원 번호 유지 시 순열이 그대로 정답을 누출한다.
    rows = array_to_rows(trap_seq, list(range(len(trap_seq))))
    trap_schema = build_trap_schema()
    preds: list[str] = []
    raws: list[str] = []
    for order in (("forward", "trap"), ("trap", "forward")):
        raw = caller(build_trap_messages(rows, order), response_format=trap_schema)
        raws.append(raw)
        try:
            ans = str(json.loads(raw).get("answer") or "")
        except (json.JSONDecodeError, ValueError, AttributeError):
            ans = ""
        chosen = order[0] if ans == "1" else order[1] if ans == "2" else "invalid"
        preds.append("is_trap" if chosen == "trap" else "forward" if chosen == "forward" else "invalid")
    rec["raw_sha"] = _sha("||".join(raws))
    rec["raw"] = raws
    rec["predictions"] = preds
    rec["temporal"] = score_temporal(preds, "is_trap")
    return rec


# ===========================================================================
# main — SERIAL bake-off 실행(Pod 전용). 계측 함수는 위에서 pod-free 로 검증됨.
# ===========================================================================
def _summarize_axes(records: list) -> dict:
    """4축 항목별 기록 → 축 요약(평균/카운트). None 은 제외."""
    def _avg(vals):
        vs = [v for v in vals if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v))]
        return float(np.mean(vs)) if vs else None

    return {
        "grounding_l2_mean": _avg([r.get("grounding") for r in records]),
        "temporal_acc": _avg([r.get("temporal") for r in records]),
        "json_parse_rate": _avg([(r.get("json") or {}).get("parse") for r in records]),
        "json_exact_match": _avg([(r.get("json") or {}).get("exact_match") for r in records]),
        "json_cer_mean": _avg([(r.get("json") or {}).get("cer") for r in records]),
        "coaching_judge_mean": _avg([r.get("coaching") for r in records]),
        "svg_wellformed_rate": _avg([r.get("svg_wellformed") for r in records]),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Phase 22 bake-off 하네스 (SERIAL, Pod 실행)")
    parser.add_argument(
        "--model",
        default=os.environ.get("BAKEOFF_MODEL"),
        help="후보 백본 모델 ID(한 번에 하나). 정확한 HF/ms-swift ID 는 22-06 확정.",
    )
    parser.add_argument("--vllm-url", default=os.environ.get("BAKEOFF_VLLM_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--shots", choices=("zero", "few", "both"), default="both",
                        help="프롬프트 모드 — zero-shot/few-shot/둘 다(기본).")
    parser.add_argument("--skip-judge", action="store_true",
                        help="코칭 judge 생략 (cold re-run 결정성 비교 전용 — 과금 0).")
    parser.add_argument("--run-tag", default=os.environ.get("BAKEOFF_RUN_TAG"),
                        help="리포트 파일명 runId (cold re-run 구분 — 예: run1/run2/run3).")
    parser.add_argument("--dry-run", action="store_true", help="계측 함수 로드 + 미니셋 파싱만(무-추론).")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    by_type = items_by_type(manifest)
    print(
        f"[setup] manifest items={len(manifest.get('items') or [])} "
        f"types={ {k: len(v) for k, v in by_type.items()} } (SERIAL, one model at a time)",
        flush=True,
    )

    if args.dry_run:
        # pod-free 스모크 — 계측 함수 로드 + 라우팅만 확인(추론 없음).
        print(f"[dry-run] grounding_items={len(grounding_items(manifest))} "
              f"axes={list(_summarize_axes([]).keys())}", flush=True)
        print("ALLDONE", flush=True)
        return 0

    if not args.model:
        raise SystemExit("--model(또는 BAKEOFF_MODEL) 필수 — 후보 백본 ID 지정(22-06 확정 ID).")

    out_dir = _resolve_out_dir()  # repo 밖 — 커밋 baseline 무접촉.
    out_dir.mkdir(parents=True, exist_ok=True)

    # 실 추론 경로(Pod). 로컬(22-05)에서는 여기 도달 전에 dry-run/테스트로 검증한다.
    caller = _make_vllm_caller(args.vllm_url, args.model)
    judge = None if args.skip_judge else _make_gemini_judge()
    runid = args.run_tag or str(int(time.time()))
    shots_modes = ["zero", "few"] if args.shots == "both" else [args.shots]
    records: list = []
    errors = 0
    quota_abort_note = None

    base_arr, base_frames = _base_sequence()
    profile = perturb.load_profile(PROFILE_PATH)

    items = manifest.get("items") or []
    try:
        for row in items:  # SERIAL — 한 항목씩 (pipeline-not-concurrency-safe).
            typ = row.get("type")
            t0 = time.monotonic()
            try:
                if typ in ("real", "hard_negative"):
                    for mode in shots_modes:
                        rec = run_report_item(row, caller, judge, mode)
                        rec["elapsed_s"] = round(time.monotonic() - t0, 2)
                        records.append(rec)
                elif typ == "synthetic_grounding":
                    for mode in shots_modes:
                        rec = run_synth_item(row, caller, base_arr, base_frames, profile, mode)
                        rec["elapsed_s"] = round(time.monotonic() - t0, 2)
                        records.append(rec)
                elif typ == "trap":
                    rec = run_trap_item(row, caller, base_arr, base_frames)
                    rec["elapsed_s"] = round(time.monotonic() - t0, 2)
                    records.append(rec)
            except QuotaAbort:
                raise
            except Exception as exc:  # noqa: BLE001 - 항목 오류는 기록 후 계속(원인 보존).
                errors += 1
                records.append({"id": row.get("id"), "type": typ, "error": str(exc)[:300]})
                print(f"[error] {row.get('id')}: {str(exc)[:160]}", flush=True)
            print(f"[item] {row.get('id')} done ({typ})", flush=True)
    except QuotaAbort as exc:
        quota_abort_note = f"Gemini judge quota — 중단: {exc}"
        print(f"[ABORT] {quota_abort_note}", flush=True)

    def _by_mode(mode):
        return [r for r in records if r.get("mode") == mode]

    trap_recs = [r for r in records if r.get("type") == "trap"]
    hardneg_recs = [r for r in records if r.get("type") == "hard_negative" and not r.get("skipped")]
    axes = _summarize_axes(records)
    report = {
        "_meta": {
            "phase": "22",
            "runId": runid,
            "model_id": args.model,           # 화이트리스트(T-22-15 — 시크릿/PII 부재).
            "schema_version": schema.SCHEMA_VERSION,
            "prompt_version": schema.PROMPT_VERSION,
            "judge_model": JUDGE_MODEL if judge is not None else None,
            "shots_modes": shots_modes,
            "base_synth_item": BASE_SYNTH_S3_KEY,
            "frame_budget": FRAME_BUDGET,
            "frame_resize": FRAME_RESIZE,
            "run": "serial bake-off (pipeline-not-concurrency-safe-eval-serial)",
            "determinism": "temperature=0, greedy — raw_sha 를 cold re-run 리포트 간 비교",
            "objectivity": "사람 점수 라벨 아님 — 합성 grounding L2 / 함정 정오 / 포맷 계측.",
            "grounding_scope": "synthetic_grounding 트랙만(실영상 정답 좌표 부재, Open Question 1).",
            "errors": errors,
            "quota_abort": quota_abort_note,
            "captured_epoch": int(time.time()),
        },
        "axes": axes,
        "axes_by_mode": {m: _summarize_axes(_by_mode(m)) for m in shots_modes},
        # 함정(trap) 트랙 별도 표기 — 정상 트랙과의 변별 확인용 (shortcut 경고 판단).
        "trap_track": {
            "n": len(trap_recs),
            "acc": _summarize_axes(trap_recs).get("temporal_acc"),
            "per_item": {r.get("id"): r.get("temporal") for r in trap_recs},
        },
        "hard_negative_track": {
            "n": len(hardneg_recs),
            "flagged_fault": {r.get("id"): r.get("hardneg_flagged_fault") for r in hardneg_recs},
        },
        "records": records,
    }
    out_path = out_dir / f"bakeoff_{args.model.replace('/', '_')}_{runid}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote {out_path} (repo 밖 — 커밋 baseline 무접촉)", flush=True)
    print(f"=== BAKE-OFF AXES ({args.model}) ===", flush=True)
    print(json.dumps(axes, ensure_ascii=False, indent=2), flush=True)
    if quota_abort_note:
        print("PARTIAL (quota abort)", flush=True)
        return 4
    if errors > len(items) // 2:
        print("TOO MANY ERRORS", flush=True)
        return 5
    print("ALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
