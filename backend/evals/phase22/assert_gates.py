#!/usr/bin/env python3
"""Phase 22-07 SFT 출하 게이트 (D-15) — exit 0 = PASS.

phase24 assert_gates 골격 확장(재발명 금지): importable check_*, ARTIFACT-GATED
SKIPPED != FAIL, 독트린 docstring 승계. 입력 artifact = run_bakeoff.py 를 SFT(AWQ)
모델로 재실행한 리포트 2벌(run1/run2, EVAL_OUT_DIR/phase22/) — SERIAL 실행 전제.

박제 정신 (phase24 독트린 승계):
  · 객관성([[analysis-objectivity-no-human-scores]]): 사람 점수 라벨 절대 미사용.
    게이트 입력은 합성 교란 L2 / 결함 짚기 verdict / 포맷 계측뿐.
  · 절대 임계 밴드 금지([[scoring-redesign-must-generalize-no-overfit]]):
    synthetic_holdout 은 "보정 L2 < 무보정 L2" 상대 개선만 단언한다.
  · determinism scope 정직성: GPU/양자화 커널의 bit-비결정(다른 raw bytes)과
    VERDICT 결정성(같은 fault-set)을 분리한다 — 이 게이트는 후자만 단언.
    byte-level raw_sha 비교는 bake-off determinism_summary 트랙 소관.

Phase 24 4종 번안 근거 (D-15 — 모델은 점수를 내지 않으므로 원형 그대로 못 씀):
  · 추적성 → "출력 리포트의 측정값이 좌표에서 역산 가능한 형태" — fault 항목의
    각도 필드가 유한 수치이고 body_part/fault_category 라우팅 키가 존재해
    deduction_engine 이 무수정 소비 가능(DEDUCTION_CONSUMED_KEYS lockstep).
  · 단조성 → "교란 강도(stage) 증가 시 검출 결함 수 비감소" — 합성 트랙 stage
    1→2→3 의 평균 faults 수가 감소하면 FAIL.
  · 결정성 → cold 2회 verdict(fault_category set) 동일.
  · 일반화 → EVAL18 6페어 무회귀 + 전 동작 균등(motion_balance).

EVAL18 스코프 정직성: 이 게이트는 **하네스 직접 추론**(run_bakeoff 리포트)이지
파이프라인 swap 이 아니다 — Wave 3(22-08 서빙 배선) 전의 오프라인 재현이다.
변별 4페어(power-spin/peter-pan/elbow-twist-sister/pdshape)만 hard 게이트,
kip-up(known_false_positive)/climb(known_gate_blocked)은 명시 추적만(pairs.yaml).

게이트 모드 (DR-03):
  · 기본 main(): FAIL 1건이라도 있으면 exit 1. SKIPPED-only 면 exit 0 + 경고.
  · --require-pass: 전 게이트 PASS 가 아니면(SKIPPED 포함) exit 비0 —
    Wave 5(22-08) 진입 전 post-Pod 판정 모드. FAIL 상태 암묵 진행 금지.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_BACKEND = _HERE.parents[1]
for _p in (_BACKEND / "shared" / "python", _BACKEND / "training", _BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import yaml  # noqa: E402

from datagen import schema  # noqa: E402

# ── artifact 경로 (run_bakeoff 와 동일 해석 — repo 밖 EVAL_OUT_DIR) ──────────
_EVAL_OUT_ENV = "EVAL_OUT_DIR"
_EVAL_OUT_DEFAULT = "/tmp/sunity_eval_out"
_SFT_MODEL_ENV = "SFT_MODEL_ID"

_MANIFEST_PATH = _HERE / "fixtures" / "manifest.yaml"
_PAIRS_PATH = _HERE.parents[0] / "phase18" / "dataset" / "pairs.yaml"

# EVAL18 pair motion_id → bake-off 미니셋 real item id prefix (fixtures/manifest.yaml).
_PAIR_ITEM_PREFIX = {
    "power-spin": "real-powerspin",
    "peter-pan": "real-peterpan",
    "elbow-twist-sister": "real-elbowtwist",
    "pdshape": "real-pdshape",
    "kip-up": "real-kipup",
    "climb": "real-climb",
}

# svg 형식·존재 게이트 기준: 결함을 짚은 리포트의 과반이 wellformed svg_spec 을
# 실어야 한다(생물역학 정합 아님 — 형식·존재 계측, F2). 전량 null/garbage = FAIL.
_SVG_PRESENT_MIN_RATIO = 0.5


# ── 학습 범위 ↔ 게이트 정합 (2026-08-15) ─────────────────────────────────────
# ★게이트는 **우리가 가르치기로 한 것**만 판정해야 한다.
#   synthetic_holdout 은 corrected_coords(좌표 보정)를 요구하는데, 그것을 가르치는
#   것은 perturb 트랙 하나뿐이다. belle C1 결정(2026-07-15, quick-260715-wq9)이
#   "perturb 는 전부 faults=[] 라 결함 신호를 익사시키는 최대 주범"이라며 좌표 보정
#   학습을 **가역 descope** 했다(삭제 아님 — 플래그로 언제든 부활).
#   그런데 사이클 스크립트만 --with-perturb 로 되살려 써서 이 모순이 가려져 있었고,
#   2026-08-15 에 C1 대로 되돌리자 드러났다: **안 가르친 능력을 요구하는 게이트는
#   어떤 모델도 통과시킬 수 없다.** 승격 0(v4~v13·v27·v28)의 한 축이 이것이다.
#
#   그래서 학습셋 _meta.track_counts.perturb == 0 이면 이 게이트는 SKIPPED 다.
#   ★느슨하게 만드는 것이 아니다 — perturb 를 되살리면(SFT_WITH_PERTURB=1) 게이트도
#     같이 되살아난다. 판정 범위가 학습 범위를 따라가는 것뿐이고, 어느 쪽이든
#     리포트에 명시된다(은폐 0).
_CORPUS_META_ENV = "SFT_CORPUS_META"
_CORPUS_META_DEFAULT = "/workspace/phase22_distill_out/jsonl/_meta.json"


def load_corpus_meta():
    """학습셋 _meta.json — 부재/파손이면 None(호출자가 기존 판정 유지)."""
    p = pathlib.Path(os.environ.get(_CORPUS_META_ENV) or _CORPUS_META_DEFAULT)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def coord_correction_in_scope(corpus_meta=None) -> bool:
    """좌표 보정이 이번 학습의 범위인가 = perturb 트랙이 실렸는가.

    meta 를 못 읽으면 **범위 안(True)** 으로 본다 — 모르는 것을 근거로 게이트를
    끄지 않는다(fail-closed 방향: 판정을 유지하는 쪽).
    """
    meta = corpus_meta if corpus_meta is not None else load_corpus_meta()
    if not isinstance(meta, dict):
        return True
    counts = meta.get("track_counts")
    if not isinstance(counts, dict) or "perturb" not in counts:
        return True
    return bool(counts.get("perturb"))


def _artifact_path(model_id: str, run_tag: str) -> pathlib.Path:
    root = pathlib.Path(os.environ.get(_EVAL_OUT_ENV) or _EVAL_OUT_DEFAULT).expanduser()
    return (root / "phase22" / f"bakeoff_{model_id.replace('/', '_')}_{run_tag}.json").resolve()


def load_sft_report(model_id: str, run_tag: str = "run1"):
    """SFT 모델 bake-off 리포트 로드 — 부재 시 None (호출자가 SKIPPED 처리)."""
    p = _artifact_path(model_id, run_tag)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ── 레코드 파싱 보조 (순수) ─────────────────────────────────────────────────
def _finite(x):
    if x is None or isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _parsed_report(rec):
    """레코드 raw → normalize_report dict. 파싱 불가/skip → None.

    파서 = schema.extract_report_json 단일 진실(quick-260714-hv4) — 자유생성
    <thought> 프리앰블/산문 래핑 raw 에서도 유효 리포트를 추출한다. legacy guided
    출력(순수 JSON)은 하위호환 동일 결과. 추출 실패 = None (기존 실패 의미 동일 —
    4 게이트의 임계·비교식·SKIPPED 규칙은 무변경)."""
    raw = rec.get("raw")
    if not isinstance(raw, str) or rec.get("skipped"):
        return None
    parsed = schema.extract_report_json(raw)
    if parsed is None:
        return None
    return schema.normalize_report(parsed)


def _fault_items(report) -> list:
    faults = (report or {}).get("faults")
    return [f for f in faults if isinstance(f, dict)] if isinstance(faults, list) else []


def _records(report_doc, *, types=None, mode=None) -> list:
    out = []
    for r in report_doc.get("records") or []:
        if types and r.get("type") not in types:
            continue
        if mode and r.get("mode") != mode:
            continue
        out.append(r)
    return out


def _fault_verdict(report) -> tuple:
    """verdict = 정렬된 fault_category 튜플 (결정성 비교 단위 — raw bytes 아님)."""
    return tuple(sorted(str(f.get("fault_category")) for f in _fault_items(report)))


# ── (1) synthetic holdout — 보정 L2 상대 개선 (절대 밴드 금지) ───────────────
def check_synthetic_holdout(report_doc=None, model_id=None, corpus_meta=None) -> list[str]:
    """합성 교란 held-out: 보정 L2 평균 < 무보정 L2 평균 (상대 개선만).

    무보정 기준선 = 레코드의 grounding_uncorrected(교란좌표 vs 원좌표 L2 — 하네스가
    기록). 개선 없으면 FAIL. 절대 임계 밴드 단언 금지. artifact/필드 부재 → SKIPPED.
    학습셋의 perturb 트랙은 0행(22-04 _meta.track_counts)이라 합성 seed 전체가
    학습 미노출 held-out 이다.
    """
    if not coord_correction_in_scope(corpus_meta):
        return [
            "SKIPPED (perturb 트랙 0행 — 좌표 보정은 belle C1(2026-07-15) 로 descope. "
            "SFT_WITH_PERTURB=1 로 되살리면 이 게이트도 함께 복귀)"
        ]
    if report_doc is None:
        report_doc = load_sft_report(model_id) if model_id else None
        if report_doc is None:
            return ["SKIPPED (SFT bake-off run1 artifact absent)"]
    corrected, uncorrected = [], []
    for r in _records(report_doc, types={"synthetic_grounding"}):
        c = _finite(r.get("grounding"))
        u = _finite(r.get("grounding_uncorrected"))
        if u is None:
            return ["SKIPPED (grounding_uncorrected field absent — 구버전 하네스 리포트)"]
        if c is not None:
            corrected.append(c)
            uncorrected.append(u)
    if not corrected:
        return ["[synthetic_holdout] 보정 L2 계측 0건 — corrected_coords 전량 파싱 불가"]
    mean_c = sum(corrected) / len(corrected)
    mean_u = sum(uncorrected) / len(uncorrected)
    if not mean_c < mean_u:
        return [
            f"[synthetic_holdout] 보정 L2({mean_c:.4f}) 가 무보정({mean_u:.4f}) 대비 "
            f"개선 없음 (n={len(corrected)})"
        ]
    return []


# ── (2) motion balance — 전 동작 커버, kip-up 단독 금지 ─────────────────────
def check_motion_balance(report_doc=None, model_id=None, manifest=None) -> list[str]:
    """eval 결과가 전 동작(미보유 포함)을 커버하고 동작별 계측이 존재해야 한다.

    manifest 의 모든 real 항목(motion 명시)이 리포트에 비-skip 레코드를 가져야 하고,
    계측된 동작이 kip-up 단독이면 FAIL([[verify-all-fixtures-not-kipup-only]]).
    """
    if report_doc is None:
        report_doc = load_sft_report(model_id) if model_id else None
        if report_doc is None:
            return ["SKIPPED (SFT bake-off run1 artifact absent)"]
    if manifest is None:
        manifest = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    motion_by_id = {
        row.get("id"): row.get("motion")
        for row in manifest.get("items") or []
        if row.get("type") == "real"
    }
    measured_motions: set[str] = set()
    rec_ids = set()
    for r in _records(report_doc, types={"real"}):
        if r.get("skipped") or r.get("error"):
            continue
        rec_ids.add(r.get("id"))
        m = motion_by_id.get(r.get("id"))
        if m:
            measured_motions.add(m)
    for item_id, motion in motion_by_id.items():
        if item_id not in rec_ids:
            failures.append(f"[motion_balance] {item_id} (motion={motion}) 계측 레코드 없음")
    if measured_motions == {"kip-up"}:
        failures.append("[motion_balance] kip-up 단독 검증 — 전 동작 균등 위반")
    if len(measured_motions) < 2:
        failures.append(
            f"[motion_balance] 계측 동작 {sorted(measured_motions)} — 2개 미만"
        )
    return failures


# ── (3) EVAL18 무회귀 — 변별 4페어 hard, kip-up/climb 명시 추적 ──────────────
def check_eval18_no_regression(report_doc=None, model_id=None, pairs=None) -> list[str]:
    """EVAL18 6페어: SFT 모델의 결함 짚기(veto 대체 관점) verdict 가 baseline 변별과
    모순되지 않아야 한다 — 하네스 직접 추론(파이프라인 swap 아님, Wave 3 전 오프라인
    재현. 모듈 docstring 참조).

    expected=discriminate 4페어(hard): fault 멤버 faults >= 1 AND fault 멤버 결함 수가
    correct 멤버보다 strictly 많아야 한다(짚기 변별). kip-up(known_false_positive)/
    climb(known_gate_blocked)은 FAIL 없이 명시 추적 라인만 남긴다(silent 통과 금지).
    zero-shot 레코드만 사용(서빙 관련 모드).
    """
    if report_doc is None:
        report_doc = load_sft_report(model_id) if model_id else None
        if report_doc is None:
            return ["SKIPPED (SFT bake-off run1 artifact absent)"]
    if pairs is None:
        pairs = yaml.safe_load(_PAIRS_PATH.read_text(encoding="utf-8"))["pairs"]
    by_id = {r.get("id"): r for r in _records(report_doc, types={"real"}, mode="zero")}
    failures: list[str] = []
    for pair in pairs:
        motion = pair.get("motion_id")
        prefix = _PAIR_ITEM_PREFIX.get(motion)
        if not prefix:
            failures.append(f"[eval18] {motion}: 미니셋 매핑 없음 — manifest 확인 필요")
            continue
        fault_rep = _parsed_report(by_id.get(f"{prefix}-fault") or {})
        correct_rep = _parsed_report(by_id.get(f"{prefix}-correct") or {})
        expected = pair.get("expected")
        n_fault = len(_fault_items(fault_rep)) if fault_rep else None
        n_correct = len(_fault_items(correct_rep)) if correct_rep else None
        if expected != "discriminate":
            # known 처리 — FAIL 없이 명시 추적(pairs.yaml known_issue 승계).
            failures.append(
                f"SKIPPED (eval18 {motion}: expected={expected} — 명시 추적만, "
                f"faults fault={n_fault} correct={n_correct})"
            )
            continue
        if fault_rep is None or correct_rep is None:
            failures.append(
                f"[eval18] {motion}: 페어 레코드 파싱 불가 "
                f"(fault={'ok' if fault_rep else 'missing'}, "
                f"correct={'ok' if correct_rep else 'missing'})"
            )
            continue
        if n_fault < 1:
            failures.append(f"[eval18] {motion}: fault 멤버 결함 0건 — 짚기 실패")
        elif not n_fault > n_correct:
            failures.append(
                f"[eval18] {motion}: 변별 실패 — faults fault={n_fault} <= "
                f"correct={n_correct} (baseline discriminate 와 모순)"
            )
    return failures


# ── (4) determinism — cold 2회 verdict 동일 ─────────────────────────────────
def check_determinism(run1_doc=None, run2_doc=None, model_id=None) -> list[str]:
    """같은 입력 cold 2회(run1/run2) → 같은 verdict(fault_category set).

    temp 0 + greedy. GPU/AWQ 커널의 bit-비결정으로 raw bytes 가 달라질 수 있으므로
    byte(raw_sha) 가 아니라 VERDICT 동일성만 단언한다(분리 서술 — 모듈 docstring).
    """
    if run1_doc is None or run2_doc is None:
        if not model_id:
            return ["SKIPPED (SFT bake-off run1/run2 artifact absent)"]
        run1_doc = run1_doc or load_sft_report(model_id, "run1")
        run2_doc = run2_doc or load_sft_report(model_id, "run2")
        if run1_doc is None or run2_doc is None:
            return ["SKIPPED (SFT bake-off run1/run2 artifact absent)"]
    failures: list[str] = []

    def _verdicts(doc):
        out = {}
        for r in _records(doc, types={"real", "hard_negative"}):
            rep = _parsed_report(r)
            if rep is not None:
                out[f"{r.get('id')}|{r.get('mode')}"] = _fault_verdict(rep)
        return out

    v1, v2 = _verdicts(run1_doc), _verdicts(run2_doc)
    common = sorted(set(v1) & set(v2))
    if not common:
        return ["SKIPPED (determinism: 두 run 공통 파싱 레코드 0건)"]
    for key in common:
        if v1[key] != v2[key]:
            failures.append(
                f"[determinism] {key}: verdict 상이 — run1={v1[key]} run2={v2[key]}"
            )
    return failures


# ── (5) 추적성+단조성 번안 (모듈 docstring 근거) ─────────────────────────────
def check_traceability_and_monotonicity(report_doc=None, model_id=None) -> list[str]:
    """Phase 24 추적성·단조성의 D-15 번안 (모델은 점수를 내지 않음 — 근거는 모듈
    docstring).

    추적성: 파싱된 리포트의 모든 fault 항목에서 각도 필드(student/reference/approx)가
    존재하면 유한 수치여야 하고, 라우팅 키(body_part 또는 fault_category)가 있어야
    deduction_engine 이 무수정 소비 가능(DEDUCTION_CONSUMED_KEYS lockstep).
    단조성: 합성 트랙 stage 1→2→3 평균 검출 결함 수 비감소.
    """
    if report_doc is None:
        report_doc = load_sft_report(model_id) if model_id else None
        if report_doc is None:
            return ["SKIPPED (SFT bake-off run1 artifact absent)"]
    failures: list[str] = []
    # 추적성
    for r in _records(report_doc, types={"real", "hard_negative"}):
        rep = _parsed_report(r)
        if rep is None:
            continue
        for j, f in enumerate(_fault_items(rep)):
            tag = f"{r.get('id')}|{r.get('mode')}.faults[{j}]"
            for key in ("student_angle_deg", "reference_angle_deg", "approx_angle_deviation_deg"):
                val = f.get(key)
                if val is not None and _finite(val) is None:
                    failures.append(f"[traceability] {tag}: {key}={val!r} 비유한 수치")
            if not f.get("body_part") and not f.get("fault_category"):
                failures.append(f"[traceability] {tag}: 라우팅 키(body_part/fault_category) 전무")
    # 단조성 (stage별 평균 faults 수)
    by_stage: dict[int, list[int]] = {}
    for r in _records(report_doc, types={"synthetic_grounding"}):
        rep = _parsed_report(r)
        stage = r.get("stage")
        if rep is None or stage is None:
            continue
        by_stage.setdefault(int(stage), []).append(len(_fault_items(rep)))
    stages = sorted(by_stage)
    means = [sum(by_stage[s]) / len(by_stage[s]) for s in stages]
    for k in range(1, len(means)):
        if means[k] < means[k - 1]:
            failures.append(
                f"[monotonicity] stage {stages[k - 1]}→{stages[k]}: 평균 결함 수 감소 "
                f"({means[k - 1]:.2f}→{means[k]:.2f})"
            )
    return failures


# ── (6) svg_spec 게이트 — 폐기 (2026-08-30) ─────────────────────────────────
#
# belle 2026-08-24 결정으로 **일러스트 기능이 전면 제거**됐다(커밋 eddbdf0e/fb2eef19,
# lib 4종·테스트 4종·에셋 21장). `svg_spec` 은 그 일러스트를 그리기 위한 기하 스펙
# (목표 각도·힘 방향·이상 궤적)이었고, 소비처가 사라졌다.
#
# 실측(2026-08-30): `svg_spec` 을 읽는 코드는 이 게이트와 bake-off 관측치,
# 그리고 학습셋 방출부뿐이다 — **앱·분석 파이프라인에 소비처 0건**.
# `visualCards.ts`/`visual-worker` 는 Phase 31 참고코너(Wan 이미지)로 별개 물건이다.
#
# 그런데 이 게이트는 08-28 v34 판정에서 `wellformed 0/8` 로 FAIL 을 냈다. 원인도
# 데이터 공백이 아니라 배선 누락이었다 — `build_jsonl` 이 `reference_loader` 에서
# `target_angle_deg` 를 받는데, `full_batch.assemble_jsonl` 이 그 loader 를 **한 번도
# 넘기지 않는다**(기본값 None). 즉 **아무도 안 쓰는 필드가, 채워질 수 없는 배선으로,
# 승급을 막고 있었다.**
#
# 그래서 게이트를 뺀다. 필드 자체(schema.SVG_SPEC_KEYS, build_jsonl 방출)는 남긴다 —
# 이미 S3 에 있는 학습셋과의 계약을 깨지 않기 위해서다. 무해한 잉여다.
#
# ★되살리려면: 일러스트(또는 그 후신)가 실제 소비처로 돌아온 뒤에, `reference_loader`
#   배선부터 고치고 이 게이트를 복원할 것. 순서를 바꾸면 또 채워지지 않는 필드를
#   검사하게 된다. 함수 본문은 git 이력(이 커밋의 부모)에 있다.


# ── compose ─────────────────────────────────────────────────────────────────
def _split_skips(results):
    skips = [r for r in results if r.startswith("SKIPPED")]
    fails = [r for r in results if not r.startswith("SKIPPED")]
    return fails, skips


def run_all_checks(model_id: str) -> dict:
    """전 게이트 실행 → {label: (fails, skips)}. main()/테스트 공용."""
    run1 = load_sft_report(model_id, "run1")
    run2 = load_sft_report(model_id, "run2")
    results = {}
    for label, res in (
        ("synthetic_holdout", check_synthetic_holdout(run1)
         if run1 is not None else ["SKIPPED (SFT bake-off run1 artifact absent)"]),
        ("motion_balance", check_motion_balance(run1)
         if run1 is not None else ["SKIPPED (SFT bake-off run1 artifact absent)"]),
        ("eval18_no_regression", check_eval18_no_regression(run1)
         if run1 is not None else ["SKIPPED (SFT bake-off run1 artifact absent)"]),
        ("determinism", check_determinism(run1, run2)
         if run1 is not None and run2 is not None
         else ["SKIPPED (SFT bake-off run1/run2 artifact absent)"]),
        ("traceability_monotonicity", check_traceability_and_monotonicity(run1)
         if run1 is not None else ["SKIPPED (SFT bake-off run1 artifact absent)"]),
    ):
        results[label] = _split_skips(res)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Phase 22-07 SFT D-15 게이트")
    parser.add_argument("--model", default=os.environ.get(_SFT_MODEL_ENV),
                        help="SFT 모델 ID (bake-off 리포트 파일명 슬러그와 동일)")
    parser.add_argument("--require-pass", action="store_true",
                        help="전 게이트 PASS 강제 — SKIPPED 도 비0 exit (DR-03, Wave 5 진입 모드)")
    args = parser.parse_args(argv)
    if not args.model:
        print("--model(또는 SFT_MODEL_ID) 필수 — SFT AWQ 모델 ID/경로 슬러그", file=sys.stderr)
        return 2

    results = run_all_checks(args.model)
    failures = [f for fails, _ in results.values() for f in fails]
    skipped = [s for _, skips in results.values() for s in skips]

    if failures:
        print("Phase 22-07 gates FAIL:")
        for f in failures:
            print("  -", f)
        for s in skipped:
            print("  ·", s)
        return 1
    if args.require_pass and skipped:
        print("Phase 22-07 gates NOT ALL PASS (--require-pass — SKIPPED 잔존):")
        for s in skipped:
            print("  ·", s)
        return 3
    verdict = "PASS" if not skipped else "PASS (with SKIPPED — artifact 부재 경고)"
    print(f"Phase 22-07 gates {verdict}")
    for label, (fails, skips) in results.items():
        state = "SKIPPED" if skips and not fails else "PASS"
        print(f"  {label}: {state}")
    for s in skipped:
        print("  ·", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
