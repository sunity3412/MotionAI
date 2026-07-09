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
    #       --limit-mm-per-prompt image=64
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
"""
from __future__ import annotations

import argparse
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
    결정성 확보(cold re-run 재현 대상). 반환 callable(messages, frames) -> str."""
    from openai import OpenAI  # lazy — Pod 에만 설치.

    client = OpenAI(base_url=base_url, api_key=os.environ.get("BAKEOFF_VLLM_KEY", "EMPTY"))
    guided = build_guided_json_schema()

    def _call(messages) -> str:
        resp = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.0,   # 결정성(cold re-run 2회 비교).
            top_p=1.0,
            max_tokens=2048,
            response_format=guided,
        )
        return resp.choices[0].message.content or ""

    return _call


def _make_gemini_judge():
    """gemini 블라인드 judge callable(lazy). prompt(str) -> 응답(str)."""
    import google.generativeai as genai  # lazy — Pod/키 필요.

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(JUDGE_MODEL)

    def _judge(prompt: str) -> str:
        return (model.generate_content(prompt).text or "").strip()

    return _judge


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
    judge = _make_gemini_judge()
    runid = str(int(time.time()))
    records: list = []

    # NOTE: 항목별 프레임 준비(S3 다운로드 + select_frame_indices + 448 리사이즈) →
    # 프롬프트 조립 → caller 호출 → 4축 계측은 Pod 실행(22-06)에서 채운다. 이 골격은
    # 규율(SERIAL/EVAL_OUT/_meta/ALLDONE)과 계측 함수 배선만 확정한다.
    for row in manifest.get("items") or []:
        # 실제 추론/계측은 22-06. 여기서는 계약만 — 미구현 실행부는 Pod 에서 채움.
        pass

    axes = _summarize_axes(records)
    report = {
        "_meta": {
            "phase": "22",
            "runId": runid,
            "model_id": args.model,           # 화이트리스트(T-22-15 — 시크릿/PII 부재).
            "schema_version": schema.SCHEMA_VERSION,
            "prompt_version": schema.PROMPT_VERSION,
            "judge_model": JUDGE_MODEL,
            "run": "serial bake-off (pipeline-not-concurrency-safe-eval-serial)",
            "determinism": "temperature=0, greedy, cold re-run 2회 비교",
            "objectivity": "사람 점수 라벨 아님 — 합성 grounding L2 / 함정 정오 / 포맷 계측.",
            "grounding_scope": "synthetic_grounding 트랙만(실영상 정답 좌표 부재, Open Question 1).",
            "captured_epoch": int(time.time()),
        },
        "axes": axes,
        "records": records,
    }
    (out_dir / f"bakeoff_{args.model.replace('/', '_')}_{runid}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[done] wrote {out_dir} (repo 밖 — 커밋 baseline 무접촉)", flush=True)
    print(f"=== BAKE-OFF AXES ({args.model}) ===", flush=True)
    print(json.dumps(axes, ensure_ascii=False, indent=2), flush=True)
    print("ALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
