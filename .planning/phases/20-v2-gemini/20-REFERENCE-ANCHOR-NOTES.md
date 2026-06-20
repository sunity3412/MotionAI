# Phase 20 — Reference-Anchored Vision Veto (Mode1) + Mode3 Hold — Implementation Notes

> NOT the 20-04 SUMMARY. The orchestrator finalizes 20-04 after the Pod 6-pair
> generalization eval. This file records the code changes; Pod eval is **pending**.

belle decision (2026-06-20): **Mode1 비교 앵커 + Mode3 보류**. The single-video
(vacuum) vision veto can't tell a mild fault from correct form — it over-penalizes
everything (v2: 정은지 정타→50) or under-penalizes everything (v3: 잘못된 kip-up→100).
Comparing the student video AGAINST the 정은지 reference (like a coach) is the
principled fix. Mode3 has no fixed reference → veto held; absolute dims + prev-video
delta stand.

## What changed

### A. Adapter — `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py`

- `assess_fault_severity(local_video_path, at_seconds=None, reference_video_path=None)`
  — new optional `reference_video_path`.
  - When provided → **COMPARISON mode**: uploads BOTH videos via `_upload_video`
    (reference/정타 first, student second), calls `_call_gemini_comparison`.
  - When None → single-video path unchanged (back-compat). Mode3 won't call it.
- `_COMPARISON_PROMPT` + `_build_comparison_prompt(at_seconds)` — **generic**
  comparison prompt. Frames video 1 = 기준(정타), video 2 = 학생, same motion. Reports
  `dominant_severity` (none/minor/moderate/major) for the student's deviation vs the
  reference; camera angle/distance/background/quality explicitly NOT a fault; no
  numeric scores. Reuses the same response schema as the single-video prompt.
- `VisionVetoCache.build_key` — added `reference_hash` component (None → `'noref'`).
  Cache is now keyed on the (student, reference) PAIR. Different reference → different
  key; comparison key ≠ single-video key.
- `PROMPT_VERSION` / `SCHEMA_VERSION` bumped `v3.0 → v4.0` (comparison prompt = new
  cache generation; stale single-video verdicts auto-invalidated).
- `_call_gemini_comparison` — contents = ["기준(정타) 영상:", ref, "평가 대상(학생) 영상:",
  student, comparison_prompt]; temperature 0.0, schema, thinking unchanged.
- Objectivity guards intact: no score/overall/rating/점수 in schema; `_SCORE_PATTERN`
  leak guard; graceful None on any failure (key absent / API error / score leak).

### B. Pipeline — `backend/functions/pipeline/app.py`

- `_apply_vision_veto(..., mode=None, reference_video_path=None)`:
  - `mode == MODE_SELF` → **HOLD**: passthrough with status `mode3_held` (no adapter
    call, no download).
  - `mode == MODE_EXPERT` + `reference_video_path is None` → `missing_reference`
    (graceful — no vacuum judging).
  - `mode == MODE_EXPERT` + reference → comparison veto via `assess_fault_severity`,
    then `apply_downward_cap` as before (applied / not_applicable / skipped_error).
  - `mode == None` → single-video back-compat path preserved (existing callers/tests).
  - status enum docstrings updated with `mode3_held`, `missing_reference`.
- `_process` MODE_EXPERT branch: when veto is ON, downloads the 정은지 reference video
  from `ref["videoS3Key"]` to a `delete=False` temp file (`_s3.download_file`),
  holding it in `reference_local_video_path` (initialized to None **before the outer
  try** so it is always in scope for cleanup). Reference download failure → graceful
  (falls through to `missing_reference`).
- Veto call site threads `mode=mode, reference_video_path=reference_local_video_path`,
  wrapped in try/finally that unlinks the temp file. The `_process` outer `finally`
  also unlinks it (idempotent safety net — no leak even if an exception fires between
  download and the veto call).
- RunPod server (`runpod_inference/server.py`) reuses `_process` (single code path) —
  inherits the change with zero edits.

## Anti-curve-fit compliance ([[scoring-redesign-must-generalize-no-overfit]])

- Comparison prompt grep: **0 motion names** (kip-up/spin/climb/peter/elbow/pdshape/
  power/sister/정은지/jeong), **0 numeric expected answers**. The only numbers are the
  score-prohibition negative examples (85점/89%/8/10/100/100), identical in spirit to
  the original single-video prompt.
- Caps **unchanged** (D-02): `vision_veto.py` not modified — minor=None, moderate=75,
  major=50. Severity comes from Gemini's comparison; caps stay spec-anchored.

## Tests (all pass — pod-free, mocked adapter)

`cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_vision_veto.py tests/test_pipeline_mode3.py -q`
→ **64 passed**.

New coverage:
- Adapter: comparison uploads both + parses severity; cache key includes
  reference_hash (different reference → different key); comparison key ≠ single-video
  key; single-video back-compat (default None).
- Pipeline: Mode3 → `mode3_held` (no cap even with active caps + major stub);
  Mode1 + reference None → `missing_reference`; Mode1 + reference + major → applied/
  capped (reference path reaches adapter); Mode1 + reference + none → not_applicable
  (정타 보존, 위양성 회귀 가드).

No TS touched — visionVeto status (`mode3_held`/`missing_reference`) is
backend-internal; not surfaced to the app contract, so the 3-way lockstep is
unaffected and `npm run typecheck` not required.

## PENDING (orchestrator)

- **Pod 6-pair generalization eval** on the RunPod GPU — validates that the generic
  comparison prompt distinguishes success/fail pairs WITHOUT curve-fitting to any
  specific motion. Not run here (executor does not run Pod eval).
- 20-04 SUMMARY finalization after the eval.

## Commits

- `0157a28` feat(20): reference-anchored comparison in vision scorer (Mode1)
- `3443696` feat(20): wire reference-anchored vision veto in pipeline (Mode1) + hold Mode3
- `d72928f` test(20): reference-anchored veto — comparison adapter + Mode1/Mode3 pipeline

## UI A1 + B1 — Mode1 headline/score reconciliation + veto reason surfacing

belle 디바이스 발견(데모 #/TestFlight): Mode1 헤드라인이 "정은지 선수와 관절각 100%
일치해요. 거의 다 왔어요!" 인데 octagon 점수는 75 (비전 거부권 하향) — 신뢰를 깨는
모순. belle: "내가 판단할 길이 없네" → 점수가 왜 내려갔는지 노출 필요.

**B1 — backend reason 박제 (점수 알고리즘 불변, display/reason 만):**

- `_apply_vision_veto` (app.py ~1737) applied 브랜치에 `"primaryFault":
  verdict.primary_fault` 추가. **applied 브랜치 전용** — 다른 status 불변.
  객관성: primaryFault 는 결함 DESCRIPTION(자연어)이지 점수/숫자 아님.
- 단일 호출부(`_process` line 2452) → runpod 도 `_process` 재사용이라 1 변경으로
  Lambda/Pod 양쪽 커버 (분기 0).

**3-way contract lockstep — applied variant 에 `primaryFault?: string` 추가:**

- `app/src/types/analysis.ts` VisionVeto `applied` 멤버 + 다른 멤버는 `primaryFault?: never`.
  legacy doc 호환 위해 optional.
- `backend/shared/python/sunity_shared/models.py` VISION_VETO_KEYS 에 `"primaryFault"`.
- `docs/contract.md` §4 visionVeto 표 + 규칙 문구.

**A1 — result.tsx 헤드라인 모순 차단:**

- `vetoApplied = result.visionVeto?.status === 'applied'`; 안전망 `mode1Contradiction =
  vetoApplied || result.overallScore < cmp.similarity`. 모순이면 similarity 헤드라인
  대신 `mode1VetoSummary` ("정은지 선수 기준으로 자세에서 교정할 점이 보여요.") 사용 —
  similarity 수치/" 거의 다 왔어요" 미노출, octagon overallScore 와 정합.
- veto 미적용(대다수 분석)은 기존 `mode1Summary` 그대로 (back-compat).

**B1 — reason 본문 노출:**

- 점수 카드(비억제 분기) octagon 아래 `vetoPrimaryFault` 있을 때만 1줄:
  "AI 영상 분석에서 발견한 점: {primaryFault}". 기존 `styles.scoringBasis` 재사용 —
  새 색/간격 하드코딩 0, 토큰만. legacy doc(primaryFault 부재)은 optional chaining 으로
  graceful 미렌더.

**테스트:** `test_pipeline_mode3.py` applied 브랜치 2건에 `primaryFault == "stub fault"`
단언 추가 + key-set allow 에 `primaryFault` 포함. 객관성 가드(`"score" not in veto`) 유지.
`test_pipeline_mode3.py` + `test_gemini_vision_scorer.py` + `test_vision_veto.py` ALL PASS,
`app npm run typecheck` clean.

> cap 값/scoring math 불변. EAS build 미실행 (orchestrator 담당).

---

## Phase 20 UI follow-ups — belle 디바이스 데모 finding #2/#3 (+ A4) — 프론트 전용

belle 가 새 EAS 빌드에서 보고한 UI 3건. 백엔드/contract 변경 0, 점수 math 불변,
토큰만 사용(하드코딩 hex/spacing 0), Korean copy, 이모지 0. `npm run typecheck` clean.

**A2 — KeypointOverlay 강조 마커 가독성** (`app/src/components/KeypointOverlay.tsx`, commit 49169fd)
- finding: "내 영상" 위 빨간 각도 마커가 "뭐라고 써있는지 보이지도 않고" (belle #2).
- floating 각도 pill 48×18 → 64×26, rx 9→13, 흰 외곽선(stroke) 추가.
- 각도 글자 10pt → 14pt, weight 600 → 700, 텍스트 자체에 얇은 흰 stroke(대비).
- 강조(brand) 관절 원: 반지름 10→14, 외곽선 1.5→2.4, **외곽선 색 brand→흰색**
  (같은 brand 외곽선이 영상 위에서 윤곽 소실 → "안 보임" 원인이라 흰 테두리로 분리).
- 비강조/저신뢰 원·강조 관절 선정(20° IPSF 허용오차) 로직 불변.

**A3 — 3D 자세 뷰어 빈 회색 박스** (`PoseViewer3D.tsx` + `result.tsx`, commit d537ef3)
- finding: "3D 자세 뷰어" 헤더 아래 빈 회색 박스 (joints3d 부재 doc, belle #3).
- 구: PoseViewer3D `return null` + result.tsx `{joints3d && ...}` 게이트 → 헤더만
  남거나 빈 박스. 이제 joints3d 부재 시 섹션 안에 빈 상태 문구 직접 표시:
  "이 분석에는 3D 자세 데이터가 없어요." + 한 줄 사유. result.tsx 는 항상
  PoseViewer3D 렌더(null 도 전달)해 빈 상태 분기 보장. design.md §0 빈 상태 패턴.

**A4 (light) — 자동 정렬 신뢰 배지** (`VideoCompare.tsx`, commit 9b0ada4)
- belle 호평: 시작점 다른 두 영상의 자동 시간 정렬 → "어떻게 신뢰를 전달하나".
- 두 영상 모두 있을 때 정적 배지 "자동 구간 맞춤"(brandTint chip) + 한 줄:
  "서로 다른 시작점을 핵심 구간 기준으로 자동 정렬했어요."
- LIGHT: 신규 백엔드 데이터/수치 confidence 없음(가짜 수치 금지). 수치 alignment
  confidence 는 `VideoCompare.tsx` 내 `TODO(deferred-backend)` 코드 주석으로 박제 —
  백엔드가 DTW 매칭 품질 등 내려주면 배지에 수치 표시.

> EAS build 미실행 (orchestrator 담당). 백엔드/Pod 변경 0.
