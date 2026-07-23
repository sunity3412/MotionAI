# Phase 33: result-trust-recovery - Research

**Researched:** 2026-07-23
**Domain:** Expression/copy-layer of RN(Expo) result screen + backend fault-zoom crop pipeline + phrasebook data + Polly voice + illustration wiring. No scoring-math change (D-20).
**Confidence:** HIGH (all findings are direct code reads with file:line evidence; no external-library speculation)

## Summary

This is a **brownfield expression-layer phase**, not greenfield. Every deliverable modifies existing, wired code paths. The core disease ("표시가 서로 안 맞고 답이 없다") is traceable to **two structural seams**, both verified in code:

1. **Crop joints and on-screen items come from different sources.** Fault-zoom crops are built from `visionVeto.faultJoints` (Gemini-pointed joints) in `pipeline/app.py:2936`, while the on-screen "items" are `deductionBreakdown.records[]` (criteria). The app then tries to reconcile them with a **region-first, first-match** join (`result.tsx:1215` `selectedZoom` + `deductionLabels.ts:236`). For `source==='vision'` records (split_angle included) the record projects to the *entire* `vetoFaultJoints` set — so "다리 스플릿" matches the first arms/shoulder crop. This is defect #5 exactly.

2. **Phrasebook has zero motion-specific entries.** `phrasebook.json` `entries` = **13 keys, all `__common__.{criterion}`** (verified). The lookup machine (`phrasebook.py:144-151`) already supports `{motion_key}.{criterion}` → `__common__` → fail-closed. Machine ready, data empty → every motion gets the same cue. The same `cueLine` is what Polly reads as **voice** (`pipeline/app.py:_synthesize_coach_audio_items`, `Text=rec["cueLine"]`), so fixing W3 data fixes W2 voice content simultaneously.

The **A-0 gate (D-04) is feasible from existing committed data** — `backend/evals/phase25/baseline/phase25_sweep_report.json` (6 motions × 2 members) already records `visionVeto.faultJoints` (pointed), `seedObservation.{window_joints, fallback_joints}` (measured), and `activatedCriteria` per member. No new Pod inference is required to run the A-0 comparison. **But a caveat that itself is an A-0 finding:** in that baseline `window_joints` is empty for 11/12 members (measurement substrate collapses to a fixed `fallback_joints` superset), which is the substrate gap (`ref-student-substrate-gap.md`) showing through. That means "measured actual defect" is barely populated in existing data, so A-0 must lean on eyeballing the actual crop PNGs + reference frames, and the "어긋남 큼 → C+M3 진입" branch is a live possibility, not a formality.

**Primary recommendation:** Run A-0 first against the committed sweep report + a dump of belle's real doc; treat the crop-vs-item source split (seam #1) and the empty-phrasebook (seam #2) as the two mandatory root fixes. Do the phrasebook data before any crop code (it is code-change-0 and unblocks voice/subtitle coherence). Keep everything else additive-free per D-05.

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 ~ D-25 — verbatim intent)
- **D-01** belle 질문은 2회만 (목업 확인 1 + 실기기 UAT 1). 그 외 Claude 결정+문서화. 결정된 것(일러스트 2안) 재확인 금지.
- **D-02** 예시 동작(파워스핀·킵업) 매몰 금지 — 범위는 전역(phrasebook 13 entry 전부 `__common__`, crop 동작무관 공통, 오버레이 공통).
- **D-03** 표현으로 분석 오류 덮기 전부 기각.
- **D-04** A-0 게이트 신설 (웨이브 A 최선두). 6동작 짚은 부위 vs 실측 결함 부위 전수 대조, 보유 데이터로. 어긋남 큼 → C+M3 phase 33 편입 / 작음 → 표현 계층만. Claude 실측 판정.
- **D-05** 해법 순서 없앤다 → 자명하게 → 최후 한 줄. 새 문장 최대 1줄. 새 라벨·배지·범례 태스크 금지. 글자 늘리는 해법 기각.
- **D-06** "근거 동봉"은 내부 검수용, 사용자 화면 미노출.
- **D-07** 판정 기준 6개 (3초 짚기 / 형태로 차이 / 뭘 하라 / 최악 데이터 / 자기 근거 밝힘 / 더 단순). ⑥ 동급.
- **D-08** 최악 데이터 고정: 가림 / 인버전 / 회전 모션블러 / 프레임 밖 잘림 / 좌표 결측. 좋은 케이스만 목업 무효.
- **D-09** IPSF 전체 금지, 동작별 질의 4개 고정 (완성기준 / 흔한 실패 / 강사 교정어 / 어디를 보라). 출처 NotebookLM + 현장 리서치. fixture 6 우선 → 등재 11. 새 표기법 발명 금지.
- **D-10** 목업 = 정지 3컷 상태전이 (재생중→음성중 정지+강조→재개). HTML 1장. **belle 실 doc(uid `csKWYvI3WCPYPysNQ9KkWecaUvq1` / analysis `071df9f894d64d1696f106e613f51f5c`)만**, mock 금지, 부족 시 phase25eval 실 doc 보조. 안 2~3개 자체 검열 후 살아남은 것만.
- **D-11** 웨이브 A 순서: A-0 → ① 기준자세 표 → ② 코칭 문구 → ③ 확대비교 → ④ 영상 표시 → ⑤ 일러스트. 목업 ③④ 묶어 belle 1회.
- **D-12** 확대비교: 같은 순간·배율·표시 + 캡션 1문장. 안 되면 카드 미방출. 결함 8종 해소. 손볼 곳 = `analysis/fault_zoom*` + `result.tsx:1215`.
- **D-13** 영상 표시: 키포인트=숨김 기본+필요시 켜기 / 붉은 표시=행동까지 한 덩어리 / 바 마커=항목+이동 / 음성=시작 시 일시정지+부위 강조 / "적용 중"=멈춤 후 재생.
- **D-14** 코칭 문구 코드변경 0, 동작별 데이터. 하드 게이트=기준영상 방향 전수 대조, 모순 시 fail-closed.
- **D-15** 일러스트 2안 확정(재확인 금지). Claude: 세트 생성 → 해부학 전수 검수 → 앱 배선.
- **D-16** (웨이브 B) 수치를 설명에서 내역으로. 문구 모순 수정. 헤드라인급 수치 강등.
- **D-17** (웨이브 B) 상태바 겹침(버그) + 타입스케일 + 자세히보기 토글/스크롤 + 여백. A 앞으로 당기지 않음.
- **D-18** 오류 0 — 산출물마다 "틀리면 걸리는 장치" 한 쌍. 조용한 실패 금지. 표본 금지, 전수.
- **D-19** 눈으로 확인 의무 — 산출물 자체를 연다(이미지 전수 / JSON 방출값 / 시뮬 렌더 / doc 덤프 / 6동작 전수 재분석). belle 전에 Claude 먼저.
- **D-20** 채점 산식·임계값 무접촉.
- **D-21** 시뮬레이터 렌더 확인 후 OTA. expo-updates 재실행 2회째 적용.
- **D-22** `#FF4B33` 불변 · 라이트 · 하드코딩 금지(theme 토큰) · Figma 우선(텍스트 검색).
- **D-23** 검증 6동작 전수 동일 빈도. fixture 없는 등재 동작은 대체 검증 명시.
- **D-24** 조사 없이 바로 구현 금지.
- **D-25** Pod `rbpnmxhbfoeg35` OFF(볼륨 생존). crop 재생성·재분석은 Pod 재기동 전제, 실행 시점 belle 확인 후 Claude.

### Claude's Discretion
- 조사 안 2~3개 시각 관용구 선택 (D-07 자체 검열 후).
- 코칭 문구 실제 한국어 표현 (D-14 하드 게이트 통과 전제).
- 일러스트 결함별 세트 구성·수량 (D-15 해부학 검수 전제).
- 태스크 원자화·웨이브 배치 세부 (D-11 골격 내).

### Deferred Ideas (OUT OF SCOPE)
- 기준모션↔학생 기질 정합 (C+M3) — 별도 트랙, `.planning/debug/ref-student-substrate-gap.md`. **단 A-0 "어긋남 큼" 판정 시 phase 33 편입(D-04).**
- iCloud 영상 실기기 재확인 — UAT 항목 유지.
- 셀프서비스 reference 등록 — 미해당.

## Project Constraints (from CLAUDE.md)
- Tech stack 변경 금지: Expo+RN(TS) / Lambda(Python 3.12, SAM) / Firestore / S3+presigned / RTMW(NLF-legacy) / Cerebras+Gemini / Polly / EAS.
- 시크릿 = AWS Parameter Store. `.env` 하드코딩 금지.
- Firestore **nested-array 금지** → flat 저장 + reshape. `faultZoomComparisons[]` 각 항목은 scalar-only dict (검증 `firestore_admin._validate_dict_only_scalars`).
- Contract 3-way lockstep: `app/src/types/analysis.ts` + `sunity_shared/models.py` + `docs/contract.md` 동시 수정.
- 이모지 금지, 슬롭 금지, 작은 단위 작업, 의미있는 테스트만.
- 브랜드 `#FF4B33`, Pretendard, 라이트 전용, theme 토큰만. UI Figma 우선.
- `sam build --use-container` 필수 (Mac native binary → Lambda Linux 실패).
- **GSD 워크플로 강제** — Edit/Write 전 GSD 커맨드로 진입.

<phase_requirements>
## Phase Requirements (mapped to waves)
| Wave/ID | Description | Research support (codebase seam) |
|---|---|---|
| A-0 (D-04) | 짚은 부위 vs 실측 결함 부위 6동작 전수 대조 | `evals/phase25/baseline/phase25_sweep_report.json` (12 members, pointed/window/fallback/activated) + doc dump. §"A-0 gate feasibility" |
| A-1 (D-09) | 동작별 기준자세 4질의 표 | Domain research (out of researcher scope) — consumes `REGISTERED_MOTIONS` (10) + `CRITERION_GROUPS` |
| A-2 / W3 (D-14) | 코칭 문구 동작별 데이터 | `phrasebook.json` entries(13 `__common__`) + `phrasebook.py:144` `{motion_key}.{criterion}` lookup ready. Voice reads same `cueLine`. §"Phrasebook" |
| A-5 / W1 (D-12) | 확대비교 crop 백엔드 + 앱 연결 | `fault_zoom.py:build_fault_zoom_comparisons` + `pipeline/app.py:2907/2746` + `result.tsx:1215` + `deductionLabels.ts:236`. §"Fault-zoom" |
| A-6 / W2 (D-13) | 영상 위 표시 + 음성 동기화 | `KeypointOverlay.tsx` + `result.tsx` markers/cueWindows(1601)/coachAudio(1637) + `VideoCompare.tsx` audio/cue (audioCue.ts, cueTrack.ts) |
| A-7 / W6 (D-15) | 일러스트 세트 + 배선 | `samples/` 3 jpg, app wiring = 0 (grep). §"Illustration" |
| Wave B (D-16/17) | 수치 자리 / 타이포 / 개별버그 | `result.tsx` + `DeductionDetailSheet.tsx` + `ReferenceCornerSection.tsx` + `resultSections.ts` + `theme/typography.ts` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Crop generation (PNG compose, badge, marker) | Backend pipeline (RunPod/Lambda `fault_zoom.py`) | — | PNG is baked server-side; badge `40°` is drawn into pixels (`_mark`) |
| Crop joint selection (which region/joint) | Backend pipeline (`_build_fault_zoom_comparisons`) | — | Sourced from `visionVeto.faultJoints` — a scoring-adjacent artifact (read-only per D-20) |
| Item↔crop reconciliation | App (`result.tsx:selectedZoom` + `deductionLabels.ts`) | Backend (what joints it emits) | Join happens client-side; but the join is only as good as the joint provenance the backend emits |
| Coaching copy text | Backend data (`phrasebook.json`) + assembly (`phrasebook.py`) | LLM (variable tone only) | Skeleton owned by fixture; D-14 = data authoring, code-change-0 |
| Voice (TTS) | Backend post-stage (`_synthesize_coach_audio_items`, Polly neural) | App trigger (`audioCue.ts`) | Reads `cueLine` verbatim → W3 fix propagates to voice |
| Video overlay / markers / bar cues | App (`KeypointOverlay`, `VideoCompare`, `cueTrack`) | — | Pure render layer over stored frame indices |
| Illustration | App asset + component (to be built) | Claude asset-gen | Currently 0 wiring |

## Standard Stack

No new packages. This phase uses only already-installed, already-verified stack:

### Core (backend crop / voice)
| Library | Version | Purpose | Evidence |
|---------|---------|---------|----------|
| Pillow (`PIL`) | installed | crop resize + draw badge/marker/arc | `fault_zoom.py` `ImageDraw`, `_mark`, `_compose` |
| numpy | >=1.26,<3 | frame arrays `(T,H,W,3)` + angle math | `fault_zoom.py` throughout |
| boto3 (AWS Polly) | >=1.34,<2 (runtime) | `synthesize_speech` neural TTS | `pipeline/app.py:_get_polly_client`, `_synthesize_coach_audio_items` |
| boto3 (S3) | runtime | crop PNG + coach_audio mp3 upload/presign | `s3keys.build_coach_audio_key`, `playback-url/app.py` |

### Core (app render)
| Library | Version | Purpose | Evidence |
|---------|---------|---------|----------|
| react-native-svg | 15.12.1 | KeypointOverlay markers/numbers | `KeypointOverlay.tsx` |
| expo-video | ~3.0.16 | VideoCompare playback | `VideoCompare.tsx` |
| expo-image | (Expo SDK 54) | crop/illustration image render (recommend for illustration wiring) | verify before use |
| @react-native-async-storage/async-storage | 2.2.0 | overlay/audio toggle persistence | `KeypointOverlayToggle.tsx`, `audioCue.ts` |

**Installation:** none. Any illustration-wiring image component should reuse `expo-image` (already a transitive Expo dep) or `react-native`'s `Image`; do NOT add a new image library.

## Package Legitimacy Audit

**No external packages are installed in this phase.** All work uses already-present dependencies (Pillow, numpy, boto3, react-native-svg, expo-video, expo-image, async-storage). slopcheck / registry verification N/A. If the planner decides to add any package (not expected), gate it behind `checkpoint:human-verify` and run the legitimacy protocol.

## Architecture Patterns

### System Architecture Diagram (result-trust data flow)

```
                          ┌─────────────────── BACKEND (pipeline _process, RunPod/Lambda) ───────────────────┐
 student video ─PUT S3──▶ │  RTMW pose → keypointReport (9fps frames, angles)                                 │
 ref motion doc ────────▶ │        │                                                                          │
                          │        ├─▶ scoring → deductionBreakdown.records[]  (criteria; source vision|abs)  │
                          │        │        └── criterion e.g. split_angle / angle_vs_reference__left_hip     │
                          │        │                                                                          │
                          │        ├─▶ visionVeto.faultJoints  (Gemini-pointed joints)  ◀── SEAM #1 source A  │
                          │        │        + windowMedianAngleDeltas (measured; OFTEN EMPTY)                 │
                          │        │                                                                          │
                          │        ├─▶ _build_fault_zoom_comparisons(faultJoints)   ◀── crops built from A    │
                          │        │        fault_zoom.build_fault_zoom_comparisons(...)                      │
                          │        │        → PNG (badge °, marker circle BAKED IN via _mark)                 │
                          │        │        → faultZoomComparisons[] {joint, region, deficitDeg,              │
                          │        │            userFrameIdx, refFrameIdx, refMatch, tier}                    │
                          │        │                                                                          │
                          │        ├─▶ phrasebook.assemble_phrases(motion_key, criterion) ──▶ record.cueLine  │
                          │        │        (13 __common__ entries; motion_key branch data-empty)  ◀ SEAM #2  │
                          │        │                                                                          │
                          │        └─▶ Polly.synthesize_speech(Text=record.cueLine) ──▶ coachAudio.items[]    │
                          └───────────────────────── Firestore users/{uid}/analyses/{id} ────────────────────┘
                                                              │ onSnapshot
                                                              ▼
                          ┌──────────────────────────── APP result.tsx ─────────────────────────────────────┐
 record row tapped ─────▶ │ selectedRecord ─▶ projectDeductionRecordKeypoints(rec, vetoFaultJoints)          │
                          │        │   (source==='vision' ⇒ returns ALL vetoFaultJoints)  ◀── SEAM #1 join   │
                          │        ▼                                                                          │
                          │  selectedZoom = first faultZoomComparison whose region/joint ∩ projected ≠ ∅      │
                          │        │   (FIRST MATCH, no joint-accuracy)                                       │
                          │        ▼                                                                          │
                          │  Zoom card + KeypointOverlay(markers) + cueWindows(subtitle) + coachAudio(voice)  │
                          │        └── VideoCompare syncs playback ↔ cue ↔ audio (cueTrack.ts / audioCue.ts)  │
                          └──────────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 1: Crops are built from vision-veto joints, items from criteria (the disconnect)
**What:** `pipeline/app.py:2936` `fault_joints = list(vv.get("faultJoints") or [])`. If empty, falls back to top-2 keypoint deltas (`:2970-2974`). Crops therefore describe *Gemini-pointed joints*, while the item list is `deductionBreakdown.records[]` (criteria). They are joined only in the app.
**Consequence:** The crop's `joint`/`region` need not correspond to the record's criterion. The app join (`selectedZoom`) papers over this with region-first, first-match.
**Fix direction (D-03/D-12):** either emit crops keyed to the criterion that will be shown (make backend crop selection consume the same criterion set as `records[]`), or make the app join joint-exact (not region-first). This is a **root fix**, not a caption band-aid.

### Pattern 2: `source==='vision'` records project to the entire faultJoints set
**What:** `deductionLabels.ts:236` — `if (record.source === 'vision') return [...(faultJoints ?? [])];`. Split-angle (and other vision-injected) records don't project to leg-specific keypoints; they project to *all* pointed joints (which can be shoulders).
**Consequence:** This is defect #5 mechanically. "다리 스플릿" (a `source==='vision'` split_angle record) intersects a `left_shoulder`/arms crop because both reference the shoulder in `vetoFaultJoints`, and `selectedZoom` returns the first such card.
**Warning sign:** a card whose `joint`/`region` is an arm while the record criterion is `split_angle`.

### Pattern 3: Phrasebook lookup is ready; data is empty
**What:** `phrasebook.py:144-151` — exact order `{motion_key}.{criterion}` → `__common__.{criterion}` → fail-closed. `phrasebook.json entries` has **only `__common__.*` keys** (13). `assemble_phrases(motion_key, criterion)` is called in the pipeline per record.
**Fix direction (D-14):** author `"{motion_key}.{criterion}"` entries (e.g. `"ref-power-spin.split_angle"`) with the same slot schema (`statusLine/whyLine/cueLine/coachQuestion/exerciseId/exerciseReason`). No code change. Voice inherits `cueLine`.

### Pattern 4: Voice, subtitle, and coach text share one string
**What:** subtitle cue (`result.tsx:1601 cueWindows` → `rec.cueLine`), voice (`pipeline/app.py _synthesize_coach_audio_items` → `Text=rec["cueLine"]`), and the detail sheet all read `cueLine`. Spot-check-hidden records (`isRecordHidden`, `result.tsx:1604`) are excluded from cues/audio.
**Consequence:** one authoritative copy source; fixing phrasebook fixes all three surfaces at once. A wrong `cueLine` is spoken aloud — highest-trust-damage path.

### Anti-Patterns to Avoid (project-specific)
- **Editing one side of the contract only** — `faultZoomComparisons` shape lives in `models.py` + `analysis.ts` + `contract.md`; change all three.
- **Adding nested arrays/objects to a comparison item** — `_validate_dict_only_scalars` (`firestore_admin.py:1427`) rejects them; keep scalars.
- **Baking new labels into PNGs** — the `55°` badge baked by `_mark` (`fault_zoom.py:606`) is exactly what belle wants OFF (defect #6). Do not add more baked text; the D-05 direction is *less*, not more, on the pixel.
- **Adding a caption to reconcile a mismatched pair** — D-05: fix the pair (same moment/scale/source) or drop the card. Caption is last resort, ≤1 line.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TTS voice | custom audio synth | existing Polly path `_synthesize_coach_audio_items` | already wired, S3-stored, presigned via `playback-url` |
| Frame-index ↔ time mapping | new fps math | `fault_zoom._to_rep_idx` / `select_confident_frame` | fps mismatch (9fps frames vs 18fps ref keypointReport) is a known landmine; reuse |
| Cue/subtitle timing | new timer loop | `cueTrack.buildCueWindows` + `VideoCompare` 100ms tick | already opt-in wired (32-08/32-12) |
| Item↔zoom join | new matcher | fix existing `projectDeductionRecordKeypoints` / `selectedZoom` | one matcher, used by markers + cues + zoom (single source) |
| Coaching copy skeleton | LLM free-gen | `phrasebook.json` fixture | D-14/D-11 explicitly block general-advice LLM path |
| Crop compose | new image pipeline | `fault_zoom._side_crop`/`_compose`/`_mark` | 3-tier confidence fallback + grouping already exists |

**Key insight:** Nearly everything is already built and wired; the phase is about **correcting provenance and data**, not adding machinery. Adding machinery violates D-05.

## Runtime State / Regeneration Inventory

> Expression-layer phase, but several artifacts are **stored** and will NOT auto-update from a code/data edit.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored crop PNGs | `faultZoomComparisons[].png` are presigned S3 URLs of PNGs generated at analysis time (badge/marker baked in). Editing `fault_zoom.py` does **nothing** to already-stored docs. | **Data regeneration** = re-run analysis on Pod (D-25). Belle's doc `071df…` shows OLD crops. |
| Stored coachAudio mp3 | `result.coachAudio.items[]` = S3 mp3 synthesized from OLD `cueLine`. Phrasebook data edit does not re-synthesize existing docs. | Regenerate on re-analysis; or accept that only new analyses get corrected voice. |
| Phrasebook data | `backend/data/phrasebook.json` is bundled into the Lambda layer / Pod code. New `{motion_key}.*` entries take effect only on **new analyses**, not stored docs. | Code edit (data) + re-analysis to observe. |
| Firestore stored docs | Belle target doc + phase25eval docs are frozen snapshots. | Mockup (D-10) must read them as-is; verification (D-19) requires fresh re-analysis for changed crops/voice. |
| Pod lifecycle | Pod `rbpnmxhbfoeg35` OFF (volume alive). RTMW GPU + Gemini env required for re-analysis. | Re-boot per D-25, belle-gated. proxy URL change → Lambda env resync (see MEMORY current-pod runbook). |
| App illustrations | `samples/` assets are NOT bundled in `app/` (they live under `.planning/`). | Wiring = move/import assets into `app/` asset dir + component. |

**The canonical question answered:** After every repo file is edited, stored crop PNGs and coachAudio mp3 in S3/Firestore still carry the old pixels/voice. Only re-analysis (Pod) regenerates them — this is why D-25/D-19 demand the 6-motion re-sweep, not just a code diff.

## Common Pitfalls

### Pitfall 1: "Fixed the code, verified by tests" — but the stored artifact is unchanged
**What goes wrong:** Editing `fault_zoom.py` or `phrasebook.json` and calling it done; belle's doc still shows old crops/voice.
**Why:** crops/audio are generated-and-stored, not computed on read (§Runtime State).
**How to avoid (D-19):** open the actual regenerated PNG / dump the actual `faultZoomComparisons` / play the actual mp3. Re-analyze 6 fixtures on Pod.
**Warning sign:** completion note says "typecheck/pytest pass" with no artifact opened.

### Pitfall 2: fps mismatch corrupts frame pairing
**What goes wrong:** user frames = 9fps arrays, ref keypointReport = 18fps (phase4_v1), mode3 prev angles = 9fps but keypointReport upsampled 18fps. Naive indexing shows the wrong pose ("국면 어긋남", defect #4).
**Why:** three different fps spaces (`fault_zoom.py:1340-1345` docstring documents this).
**How to avoid:** always route frame indices through `_to_rep_idx` with the correct `dtw_ref_fps`; never hardcode 9/18.

### Pitfall 3: The "measured defect" you compare against is itself possibly wrong
**What goes wrong:** A-0 compares pointed vs measured and finds agreement, concluding "어긋남 작음" — but `window_joints` is empty and both pointed and measured collapse to the same fixed `fallback_joints` superset.
**Why:** substrate gap (`ref-student-substrate-gap.md`): ref(18fps, inversion-corrected) vs student(9fps) asymmetry + `find_action_segment` disabled. Verified: baseline sweep has `window_joints=[]` for 11/12 members.
**How to avoid:** A-0 must not treat empty-window agreement as "aligned." Cross-check against the actual crop PNG + reference video frame (eyeball), and treat empty measurement substrate as itself an "어긋남 큼" signal favoring C+M3 entry.

### Pitfall 4: Region-first join hides item↔crop mismatch
**What goes wrong:** `selectedZoom` returns the first card whose region intersects; a shoulder crop attaches to a split item.
**How to avoid:** make the join joint-exact, or make the backend emit criterion-keyed crops. (§Pattern 1/2)

### Pitfall 5: Adding text to "explain" — the D-05 trap
**What goes wrong:** captions/labels/legends multiply; screen gets busier; trust doesn't return.
**How to avoid:** the disease is *misalignment*, not *missing explanation*. Fix same-moment/same-scale/same-marking first (self-evident), ≤1 new line only if unavoidable, internal-only provenance (D-06).

## Code Examples (verified anchors — file:line)

### Crop payload emitted per item (the Firestore shape)
```python
# fault_zoom.py:1533-1556 — one faultZoomComparison item (scalar-only, Firestore flat)
item = {
    "joint": unit.joint,          # crop joint (from vv.faultJoints unit)
    "deficitDeg": deficit,        # baked as "40°" badge into PNG via _mark
    "png": png,                   # bytes → S3 → presigned URL in doc
    "userFrameIdx": int(u_kp_idx),# keypointReport index space (NOT 9fps frames)
    "refFrameIdx": int(r_kp_idx),
    "refMatched": not ref_match_failed,
}
# optional scalars: item["kind"] (deficit/advisory), item["region"] (legs/arms),
#                    item["refMatch"] ('dtw' | 'failed')
```

### Phrasebook lookup (machine ready, data empty)
```python
# phrasebook.py:143-151
entries = _load_phrasebook().get("entries", {})
if motion_key:
    specific = entries.get(f"{motion_key}.{criterion}")   # ← 0 such keys today
    if isinstance(specific, dict):
        return _entry_slots(specific)
common = entries.get(f"{_COMMON_PREFIX}.{criterion}")      # ← all 13 hits land here
if isinstance(common, dict):
    return _entry_slots(common)
return _fail_closed_slots()
```

### The app join that loses joint accuracy
```typescript
// result.tsx:1215-1229  +  deductionLabels.ts:236
// projectDeductionRecordKeypoints: source==='vision' ⇒ [...(faultJoints ?? [])]
const selectedZoom = useMemo(() => {
  if (!selectedRecord) return null;
  const kps = new Set(projectDeductionRecordKeypoints(selectedRecord, vetoFaultJoints));
  for (const z of result.faultZoomComparisons ?? []) {
    if (z.tier === 'advisory') continue;                  // defect #8: advisory never shown in sheet
    const zoomKps = z.region ? [...(REGION_MEMBER_KEYPOINTS[z.region] ?? [])] : [z.joint];
    if (zoomKps.some((k) => kps.has(k))) return z;        // FIRST region match → mismatch
  }
  return null;
}, [selectedRecord, vetoFaultJoints, result.faultZoomComparisons]);
```

### Voice reads cueLine (W3 → W2 coherence)
```python
# pipeline/app.py:_synthesize_coach_audio_items
resp = _get_polly_client().synthesize_speech(Text=rec["cueLine"], ...)  # neural
# → S3 coach_audio_{recordId}.mp3 → result.coachAudio.items[]
```

## Defect-8 → root-cause map (W1, from 32-UAT §A)

| # | Defect | Root cause (verified) | Where |
|---|--------|----------------------|-------|
| 1 | 정은지 쪽 표시 없음 | Gate B: ref side line drawing suppressed (kip-up inversion pose blows up) | `fault_zoom.py:1454-1457,1529` |
| 2 | 배율 불일치 | relaxed crop was 2× wider; unified to 1.8 (`_RELAXED_MARGIN` note) but ref full-frame fallback still differs in scale | `fault_zoom.py:_side_crop`, `_full_frame_fit` |
| 3 | 3장 같은 순간 (user34/ref90) | single worst_seconds / single override frame reused across cards; no phase spread | `fault_zoom.py:1370-1421` (one u_idx/r_idx for all units) |
| 4 | 국면 어긋남 | fps-mismatch + DTW match failure → ref full-frame center fallback | `fault_zoom.py:1416-1421` (ref_match_failed) |
| 5 | 항목↔크롭 오연결 (다리 스플릿 ↔ left_shoulder) | crops from `vv.faultJoints`, items from criteria; `source==='vision'` projects to ALL faultJoints; first-match join | `pipeline/app.py:2936` + `deductionLabels.ts:236` + `result.tsx:1221` |
| 6 | 각도 배지 PNG에 구움 | `_mark` draws `55°`/`30°` into pixels | `fault_zoom.py:606-634` |
| 7 | 인물 밖 잘림 | crop bbox from keypoints; low-confidence → relaxed/full fallback | `fault_zoom.py:_side_crop` 3-tier |
| 8 | advisory 미노출 | app skips `tier==='advisory'` in sheet join | `result.tsx:1222,1530` |

## State of the Art (project-local, not ecosystem)

| Old approach | Current approach | Impact for phase 33 |
|---|---|---|
| 각도 배지 PNG 구움 (신뢰 표시 목적) | belle: 앱 레이어로 분리 원함 (D-16, W4) | badge must move off pixel; but W4 is Wave B — coordinate so W1 crop change doesn't re-bake |
| region-first 카드 매칭 | joint-exact 필요 (D-12) | requires backend provenance change OR app join change |
| phrasebook 전부 `__common__` | 동작별 entry (D-14) | data authoring, code-change-0 |
| illustration `samples/` only | app 배선 (D-15) | move assets into `app/`, build component |

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | Belle's target doc `071df…` lives at Firestore `users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/071df9f894d64d1696f106e613f51f5c` and is dumpable with `firebase-admin` + `FIREBASE_SA_PATH` | A-0 / mockup | If path/access differs, mockup (D-10) blocked until a dump script + creds confirmed |
| A2 | Baseline `phase25_sweep_report.json` (2026-07-05, run7) is representative enough of current pointed/measured behavior for A-0's *feasibility*, though it predates phase 32 | A-0 | If phase-32 changes shifted joint provenance materially, A-0 should re-sweep on Pod (D-25) rather than trust 2026-07-05 |
| A3 | `expo-image` is available transitively (Expo SDK 54) for illustration wiring | Standard Stack | If absent, use RN `Image`; verify before install |
| A4 | The 6 fixtures (power-spin, peter-pan, elbow-twist-sister, pdshape, kip-up, climb) on S3 `fixtures/phase15/{motion}/{correct,fault}.mp4` are the D-23 전수 검증 set; the other 4 registered motions (ref-foxtop, ref-foxtop-split, ref-invert, ref-sideway-spin) have NO paired fixture | Verification | fixture-less registered motions need an alternative verification path per D-23 (e.g. belle real docs) |

## Open Questions (RESOLVED — routed to owning plans)

> These are intentional investigate-first (D-24) questions, each routed to a plan that resolves it during execution. Q1 → **33-01** (A-0 gate; literally changes phase scope via the HALT branch). Q2 → **33-04** T2 (seam-location decision). Q3 → **33-03** T2 (scope to per-motion `activatedCriteria`).

1. **[→ 33-01] Does A-0 conclude "어긋남 큼" (→ C+M3 into phase 33)?**
   - Known: baseline `window_joints` empty 11/12; measurement substrate collapses to fixed fallback. pointed(Gemini) is broad; activatedCriteria (shown items) is a third, different set.
   - Unclear: whether that divergence is large enough by D-04's eyeball standard against actual crop PNG + ref frames.
   - Recommendation: A-0 must dump belle's doc + open the 3 crop PNGs + the matched ref video frames, and compare against `activatedCriteria`. Treat empty-window as a divergence signal, not agreement. Document the branch decision (D-04).

2. **Fix seam #1 in backend (criterion-keyed crops) or app (joint-exact join)?**
   - Both are viable; backend change is more invasive (crop regeneration on Pod) but removes the mismatch at source. App join change is OTA-only but still depends on the crop carrying the right joint.
   - Recommendation: decide in A-3/A-5 planning after A-0; prefer the source (backend) fix if A-0 shows crops are built from the wrong joint set, else the app join.

3. **Which 6→11 motions get motion-specific phrasebook entries, and for which criteria combos?**
   - The realistic combo space = REGISTERED_MOTIONS(10) × emitted criteria (5 core + 8 `angle_vs_reference__*` + fallback). Not all combos emit for every motion (`emissionNote` in phrasebook `_meta`).
   - Recommendation: A-2 authors only the combos that actually emit per motion (read `activatedCriteria` per motion from the sweep report to scope the matrix), not all 198 cells.

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| RunPod Pod `rbpnmxhbfoeg35` (RTMW GPU) | crop/voice regeneration + 6-motion re-sweep (D-19/D-25) | ✗ (OFF, volume alive) | — | none — must reboot (belle-gated) |
| Gemini API key (belle) | vision veto during re-sweep | via SSM `/sunity/motion/gemini-api-key` | — | re-sweep incomplete without it |
| AWS Polly (neural) | voice re-synthesis | ✓ (Lambda/Pod boto3 + IAM) | runtime | subtitle-only if IAM/Polly fails |
| Firestore admin creds (`FIREBASE_SA_PATH`) | dump belle doc for A-0/mockup | ✓ locally (`firebase-sa.json`) | — | — |
| Committed baseline sweep report | A-0 without new inference | ✓ `evals/phase25/baseline/phase25_sweep_report.json` | 2026-07-05 run7 | re-sweep on Pod |
| iOS Simulator + Xcode 26.6 | D-21 render-before-OTA | ✓ (this Mac, per MEMORY) | — | — |
| Figma MCP (fileKey jrdI7kp245HkPfLB0nclsz) | UI/mockup reference (D-22) | ✓ | — | design.md secondary |

**Missing with no fallback:** RunPod Pod (blocks any crop/voice regeneration and the D-19/D-23 6-motion 전수 재분석). Plan must sequence Pod reboot (belle-gated) before A-5/A-6 verification and the final gate.

## A-0 Gate Feasibility (concrete field map)

**Doable from committed data, no new inference.** For each of the 12 members in `phase25_sweep_report.json` → `results[]`:

| A-0 concept | Field to read | Note |
|---|---|---|
| "짚은 부위 (crop/pointed)" | `visionVeto.faultJoints` (Gemini) + `collectObservation.pointedJoints` | crop joints derive from `faultJoints` (`pipeline/app.py:2936`) |
| "활성 criterion (shown item)" | `activatedCriteria` | the criteria that become `deductionBreakdown.records[]` |
| "실측 결함 부위 (measured)" | `seedObservation.window_joints` (primary) → `seedObservation.fallback_joints` | **window empty 11/12 — the finding** |
| deficit magnitude | `visionVeto.faultJointDeficits` | Gemini estimate |
| ground-truth eyeball | crop PNG (`faultZoomComparisons[].png` in the real doc) + ref video frame | required because measured substrate is thin |

**Procedure for A-0 (recommended):**
1. Read the 12-member baseline table (already extracted below) — quantify pointed vs measured vs activated divergence.
2. Dump belle's real doc `071df…` (`firebase-admin`, `users/{uid}/analyses/{id}`) and open its 3 crop PNGs + `activatedCriteria`.
3. For the specific defect-5 case, confirm `source==='vision'` split record projecting to shoulder.
4. Decide D-04 branch; document with the table + PNGs as evidence.

**Baseline extract (2026-07-05 run7, fault members):**
- `power-spin fault`: pointed=[knees,hips], **window=[]**, fallback=[elbows,shoulders,hips], activated=[hip, left_shoulder, right_hip, leg_extension] → shoulder activated though not pointed.
- `kip-up fault`: pointed=[left_hand,shoulders,hips,knees] (7), window=[shoulders,knees] (4), activated=[shoulders, split_angle] → pointed ⊋ measured ⊋ shown.
- `elbow-twist-sister fault`: pointed=[knees,hips], **window=[]**, activated=8 `angle_vs_reference__*` → shown items far exceed pointed.
- `peter-pan/pdshape fault`: pointed=None, **window=[]**, activated from fallback only.

This divergence pattern (three non-matching joint sets per member, empty measurement) is the substantive input to the D-04 branch decision.

## Validation Architecture (Nyquist — 전수 not sample, D-18/D-23)

### Test framework
| Property | Value |
|----------|-------|
| Backend | pytest (`backend/requirements-dev.txt`, >=8,<9); phase suites under `backend/tests/phaseNN/` |
| App | `tsc --noEmit` (`npm run typecheck`) — only static gate; no JS test runner |
| 6-motion re-analysis | `backend/evals/phase25/run_sweep.py` (serial, in-process `_process`, Pod GPU+Gemini) + `assert_gates.py` |
| Sim render | iOS Simulator (Xcode 26.6) screenshot per D-21 |

### Phase requirement → test map
| Wave | Behavior | Test type | Command / artifact | Exists? |
|------|----------|-----------|--------------------|---------|
| A-2 W3 | 동작별 cueLine emits + no `__common__` fallback for registered combos | data + unit | new `tests/phase33/test_phrasebook_motion_specific.py` (assert `assemble_phrases("ref-power-spin","split_angle")` != `__common__`) + emit-value dump | ❌ Wave 0 |
| A-2 W3 | 문구 방향 vs 기준영상 모순 0 (hard gate D-14) | manual eyeball (전수) | open each authored cue vs ref frame; fail-closed on contradiction | ❌ (procedure) |
| A-5 W1 | crop item↔criterion joint-exact | unit + eyeball | assert join returns joint-matching card; open all regenerated PNGs (전수) | ❌ Wave 0 |
| A-5 W1 | same-moment/scale/source pair or dropped | eyeball 전수 | open user/ref PNG pairs side by side | ❌ (procedure) |
| A-6 W2 | display ↔ item two-way match; no orphan marker | unit | extend `buildDeductionMarkers`/`selectedZoom` tests | ❌ Wave 0 |
| A-6 W2 | voice pause + region highlight on cue start | sim render | Simulator recording of cue transition | ❌ (procedure) |
| A-7 W6 | anatomy 전수 검수 (limb count, joint direction) | eyeball 전수 | open every illustration | ❌ (procedure) |
| all | 6-motion 전수 re-sweep green | integration | `run_sweep.py` cold+warm on Pod + `assert_gates.py` | ✓ harness exists |

### Sampling rate
- **Per task:** relevant `pytest backend/tests/phaseNN` + `npm run typecheck`.
- **Per wave (backend crop/voice):** 6-motion re-sweep (전수, D-23) — no per-motion sampling.
- **Phase gate:** all 6 fixtures re-analyzed + every regenerated PNG/mp3 opened (D-19) + Simulator render (D-21) → belle UAT.

### Wave 0 gaps
- [ ] `backend/tests/phase33/` — new test dir (phrasebook motion-specific, join joint-exact, orphan-marker).
- [ ] A-0 analysis script (read sweep report + dump belle doc) — or ad-hoc, but must produce the D-04 evidence table.
- [ ] Firestore doc-dump helper (none exists; `backend/scripts/` has no dump script) — small `firebase-admin` script keyed by uid/analysisId.
- [ ] fixture-less registered motions (ref-foxtop, ref-foxtop-split, ref-invert, ref-sideway-spin) alternative verification per D-23.

## Security Domain

`security_enforcement` not explicitly false → included, minimal applicability (UI/copy/crop phase, no auth/crypto change).

| ASVS Category | Applies | Standard control |
|---------------|---------|------------------|
| V5 Input Validation | yes | `firestore_admin._validate_dict_only_scalars` for `faultZoomComparisons[]`; `playback-url` recordId whitelist (`app.py:55`) |
| V6 Cryptography | no | no new secrets; existing SSM Parameter Store |
| V2/V3/V4 Auth/Session/Access | no | unchanged (Firebase ID-token verify in Lambdas) |

| Pattern | STRIDE | Mitigation (existing) |
|---------|--------|-----------------------|
| Presigned URL over-exposure (crop/audio) | Information disclosure | server-constructs canonical S3 key, TTL-bound presign (`s3keys` single source; `playback-url` re-sign) |
| Malformed doc field injected to render | Tampering | scalar-only validator + app-side normalize |

## Sources

### Primary (HIGH — direct code reads this session)
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` (build_fault_zoom_comparisons:1287, _mark:606, _group_fault_joints:110, _to_rep_idx:195, _REGION_JOINTS:72)
- `backend/functions/pipeline/app.py` (_build_fault_zoom_comparisons:2907, _render_fault_zoom:2746, _synthesize_coach_audio_items:3184+, spot_check:3315+)
- `backend/shared/python/sunity_shared/analysis/phrasebook.py` (assemble_phrases:118-151)
- `backend/data/phrasebook.json` (13 `__common__` entries + safety + failClosed; coverageMatrix `_meta`)
- `app/src/app/analysis/result.tsx` (selectedZoom:1215, matchZoomForRecord:1526, cueWindows:1601, coachAudio:1637)
- `app/src/lib/deductionLabels.ts` (projectDeductionRecordKeypoints:221, buildDeductionMarkers:242)
- `app/src/components/{KeypointOverlay,VideoCompare,KeypointOverlayToggle}.tsx`
- `backend/shared/python/sunity_shared/firestore_admin.py` (update_analysis_fault_zoom validation:1418-1435; analyses path:2014)
- `backend/shared/python/sunity_shared/analysis/gemini_motion_classifier.py` (REGISTERED_MOTIONS = 10)
- `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` (CRITERION_GROUPS)
- `backend/evals/phase25/{run_sweep.py, baseline/phase25_sweep_report.json}` (12-member pointed/measured data)
- `backend/evals/phase24/eval_keys.json` (6-motion fixture list `fixtures/phase15/{motion}/{correct,fault}.mp4`)

### Secondary (project docs)
- `33-CONTEXT.md`, `33-PLANNING-APPROACH.md`, `33-SEED.md`, `32-UAT-FINDINGS-2026-07-22.md`, `CLAUDE.md`, `app/CLAUDE.md`, MEMORY index.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all deps already installed and read in code.
- Architecture / seams: HIGH — both root seams verified with exact file:line and reproduced logic.
- A-0 feasibility: HIGH for feasibility; MEDIUM for the *conclusion* (baseline predates phase 32; belle doc not dumped this session).
- Pitfalls: HIGH — sourced from code + prior quick-task history.

**Research date:** 2026-07-23
**Valid until:** ~2026-08-06 (stable brownfield; re-verify if pipeline `_process` or `fault_zoom.py` changes before planning).
