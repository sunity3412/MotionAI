# Phase 14: 정은지 기준 모션 등록 (reference-motion-registration) - Research

**Researched:** 2026-06-15
**Domain:** Backfill of downstream engine outputs (EXTEND / BodyNormalizationProfile / ForceDirectionPattern + meanAngles) onto 11 stored phase4_v1 RTMW reference motions, via the student `_process` code path (분기 0, 코드 1벌). Admin-CLI driven. No app UI, no new filming.
**Confidence:** HIGH (all claims traced to source files with line evidence)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 저장된 phase4_v1 `joints3d` 재사용 + research 게이트 하이브리드. 11개 reference 가 RTMW 로 재처리되어 `joints3d`/`angles`/`keypointReport` 가 `reference/{id}/versions/phase4_v1` active 로 저장됨. Phase 14 는 이 검증된 pose 를 재사용하고, 그 위에 EXTEND / BodyNormalizationProfile / ForceDirectionPattern 을 학생 분석과 100% 동일한 _process 함수로 계산한다 (위양성 방지의 본질 = reference 와 학생이 동일 계산 경로).
- **D-02 (research 게이트 — planner 필수 검증):** 영상 전체 재추론(옵션2) 채택 안 함. **"Phase 6/9/EXTEND 함수가 소비하는 입력 ⊆ phase4_v1 에 저장된 데이터"** 를 검증 → 충족 시 stored 재사용, **부족한 필드에 한해서만** Pod 재추론(하이브리드). 전역 재추론 금지.
- **D-03:** 단일시점으로 통일. 다각도 캡처 프로토콜은 촬영 가이드 문서로만 남기고, 단일시점 입력도 graceful 처리, 다각도 부재 시 confidence 낮게 표기.
- **D-04:** admin CLI 스크립트. 운영자(belle)가 CLI 로 등록/백필. Phase 6 의 `extract_reference_body_profiles.py` + `seed-reference-body-profile.mjs` 패턴 확장. 앱 내 등록 UI 불필요.
- **D-05:** 기존 11개 reference 백필, 신규 촬영 0. Mode 1 v1 비교 대상 = 이 11개.

### Claude's Discretion
- 백필 스크립트 entrypoint 구조 (기존 reprocess/extract 확장 vs 신규 단일 스크립트)
- 버전 쓰기 전략 (phase4_v1 in-place merge vs 신 versioned write)
- atomic write/rollback 메커니즘
- 단, D-01 "동일 함수 재사용" + Firestore flat-array 규약([[firestore-nested-array-flat]] / [[firestore-index-entry-limit]]) 준수 필수.

### Deferred Ideas (OUT OF SCOPE)
- 선수·학원 셀프 업로드 + 동작 신청 플로우 (기술 실증 후 별도 후속 phase)
- 실제 다각도 촬영 기반 reference (단일시점/AI 합성 path 한계 도달 시 최후 수단)
- 신규 정은지 영상 촬영 등록 (Phase 14 = 기존 11개 백필 한정)
- **(ROADMAP 텍스트 무효화)** Phase 14 ROADMAP SC#1 의 "정은지 영상(다각도 권장) 업로드 → 등록" 은 CONTEXT D-03/D-05 로 SUPERSEDED. 영상 업로드/다각도 촬영 rig/신규 촬영 구현 = OUT.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REF-01 | 정은지 기준 모션을 다각도 캡처 프로토콜에 따라 등록할 수 있고, 등록 경로는 비교 분석 정확도가 최대화되는 방식(촬영 조건/앵글 통제 + BodyNormalizationProfile·EXTEND·ForceDirectionPattern 포함)으로 설계된다 | Backfill path (this research) computes EXTEND/normalization/force/meanAngles onto 11 stored references via the student `_process` downstream functions. "다각도 캡처 프로토콜" reduced to a markdown capture-guide deliverable per D-03 (촬영 조건 통제 = reproducible registration accuracy). |
</phase_requirements>

## Summary

The phase backfills four downstream outputs — `meanAngles`, EXTEND profile (`joint_expectations`), `BodyNormalizationProfile`, `ForceDirectionPattern` — onto the 11 reference motions that already carry phase4_v1 RTMW 3D pose. The decisive D-02 research gate asks whether the inputs consumed by the downstream functions are a subset of what phase4_v1 stores. **Verdict: HYBRID-NEEDED.** phase4_v1 stores flat arrays (`angles`, `joints3d` pole-aligned, `keypointReport`) but does **not** persist the rich `list[PoseFrame]` objects (`keypoints_3d` raw with confidence, `keypoints_2d`, `pole_extension_landmarks`, per-frame `reliability`/`pole_axis`) that `measure_body_profile` and `compute_force_signals` consume. Reconstructing sufficient PoseFrame objects from stored flat data is lossy and error-prone; re-running RTMW from the (already-stored) S3 video is the established, validated precedent (Phase 6's `extract_reference_body_profiles.py`). This does **not** violate D-02's "no global re-inference" rule because the re-inference is the *only* way to obtain the consumed inputs — D-02 explicitly permits Pod re-inference "부족한 필드에 한해서만". Critically, the re-inferred RTMW pose is used only as input to the new engine outputs; the **active phase4_v1 `joints3d`/`angles` are not replaced** (no re-validation burden, no BLOCKER-1 risk).

Field-level breakdown: **meanAngles = STORED-SUFFICIENT** (derivable from flat `angles`; app already derives it client-side via `deriveMeanAngles`). **EXTEND (FallbackRecognizer) = STORED-SUFFICIENT** (`recognize` consumes only `angles`). **BodyNormalizationProfile = HYBRID-NEEDED** (`measure_body_profile` reads raw `keypoints_3d`+confidence, not stored — but already backfilled by Phase 6 for the original 5; verify all 11). **ForceDirectionPattern = HYBRID-NEEDED** (`compute_force_signals` needs full PoseFrame list; `infer_force_direction_pattern` then consumes only the ForceSignalsReport).

**Primary recommendation:** Extend the Phase 6 Pod-side extractor (`extract_reference_body_profiles.py` pattern) into a single backfill script that, per motion, re-runs RTMW once from S3, then computes all four outputs through the *same* `sunity_shared.analysis` functions the student path calls, emits a JSON fixture, and seeds it via an extended `seed-reference-*.mjs` (atomic merge, `--dry-run`, idempotent). Do **not** touch `versions/phase4_v1` active `joints3d`/`angles`; write new top-level fields only. New fields are small (per-phase metrics + per-joint means) — no 40k index-entry risk.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| RTMW re-inference (hybrid) | RunPod GPU Pod | — | CUDA required; CPU NaN. Pod `qcf38vvsmub1y4` UP. Reuses `RTMWPoseEngine` + `FfmpegFrameExtractor`. |
| EXTEND / normalization / force / meanAngles computation | Backend ML core (`sunity_shared.analysis`) | RunPod Pod (executes) | Pure functions, identical to student `_process` (D-01 동일 코드 1벌). |
| Backfill orchestration (download→infer→measure→emit JSON) | Backend admin CLI (Pod-run) | — | D-04 admin CLI. Pattern: `extract_reference_body_profiles.py`. |
| Firestore atomic merge seed | Node admin script (`app/scripts/*.mjs`) | Firebase Admin SDK | Phase 6 precedent; ADC `sunity3412@gmail.com`. |
| Reference doc storage | Firestore `reference/{motionId}` | — | Top-level fields; GET /reference + app passthrough. |
| Mode 1 consumption of new fields | Phase 15 (NOT this phase) | — | Current `_process` mode1 does **not** read these from reference yet. Phase 14 = data prep only. |
| Capture guide (SC#3) | Markdown doc deliverable | — | No code. 촬영 조건/앵글/시점 수 documentation. |

## Primary Research Question — D-02 Verdict

> "Are the inputs CONSUMED by the downstream functions ⊆ the data STORED in phase4_v1?"

### What phase4_v1 actually stores

`backend/scripts/reprocess_reference_motions_phase4.py:291-303` (the write payload) + `_flip_active_pointer` top-level mirror (`:387-403`) [VERIFIED: codebase]:

| Stored field | Type | Source | Space |
|--------------|------|--------|-------|
| `angles` | flat list (T×8) | `compute_joint_angles` → `temporal_fill` | joint angles (deg) |
| `anglesJointKeys` | list[str] (8) | `skeleton.JOINT_KEYS` | — |
| `anglesFrames` | int (T) | — | — |
| `joints3d` | flat list (T×17×3) | `to_coco17_array[:, :, :3]` | **`space="pole_aligned"`** |
| `joints3dKeys` | list[str] (17 COCO) | `skeleton.KEYPOINT_NAMES` | — |
| `joints3dFrames` | int | — | — |
| `coordDim` | 3 | — | — |
| `space` | `"pole_aligned"` | — | — |
| `keypointReport` | dict | `build_keypoint_report` | 2D image-space data + confidence + reliability + axisData (UI overlay) |

**NOT stored:** the full `list[PoseFrame]` objects. Specifically absent: raw `keypoints_3d` (non-aligned, with per-keypoint `confidence`), `keypoints_3d_pole_aligned` as PoseFrame attrs (only the flat numeric copy is in `joints3d`), `pole_extension_landmarks` (grip/toe), per-frame `reliability`/`pole_axis`, `raw_keypoints_133`.
[VERIFIED: `backend/shared/python/sunity_shared/analysis/pose_frame.py:204-246` — PoseFrame fields vs reprocess payload]

### What each downstream function CONSUMES

#### 1. EXTEND profile — `technique.py`
`FallbackRecognizer.recognize(self, angles, frames=None)` consumes **only `angles`** (mean over T → `_EXTENSION_ZONE_DEG` 150° gate on elbows/knees → `joint_expectations`).
[VERIFIED: `backend/shared/python/sunity_shared/analysis/technique.py:92-113`]

- **Verdict: STORED-SUFFICIENT.** `angles` reshaped from flat phase4_v1 array is exact input. No re-inference needed for the Fallback path.
- *Caveat:* a Gemini technique recognizer would additionally use `frames=<video path>` (S3, re-runnable). For the v1 reference set the conservative FallbackRecognizer ("모르면 깎지 않는다") is the production recognizer when Gemini env is off. **[ASSUMED]** that reference backfill should use the same recognizer the student path will use against these references in Phase 15 — planner/discuss must confirm whether Gemini recognizer is intended for reference EXTEND (would require the S3 video, already available).

#### 2. BodyNormalizationProfile — `body_normalization_measurer.py`
`measure_body_profile(pose_frames)` reads `frame.keypoints_3d` (raw, NON-pole-aligned 3D + per-keypoint `confidence`) for every segment/torso measurement.
[VERIFIED: `body_normalization_measurer.py:85,99,174,342,369,387` — all read `frame.keypoints_3d`]

- Stored `joints3d` is `keypoints_3d_pole_aligned` (`space="pole_aligned"`), **not** raw `keypoints_3d`, and carries no per-keypoint confidence. So the consumed input is **not** a subset of stored data.
- **Verdict: HYBRID-NEEDED** (requires PoseFrame list ⇒ RTMW re-inference from S3 video).
- **Mitigation:** Phase 6 already backfilled `bodyNormalizationProfile` + `bodyComparisonSourcePose` for the original 5 motions via exactly this re-inference (`extract_reference_body_profiles.py`). **Planner must verify which of the 11 already have these fields** (the 6 added later — ref-combo, ref-elbow-twist-sister, ref-kip-up, ref-pdshape, ref-peter-pan, ref-power-spin — may be missing them, since the extractor's `DEFAULT_MOTION_IDS` = 5). See Runtime State Inventory.

#### 3. ForceDirectionPattern — `force_signals.py` + `force_pattern.py`
`compute_force_signals(pose_frames, pole_axis_measurement, body_profile, *, angles, fps, motion_id, ...)` calls:
- `compute_phase_boundaries(pose_frames, ...)` — uses pose_frames
- `compute_axis_deviation(pose_frames, ...)` — **3D pole-aligned path is primary** (`_shoulder_tilt_pole_aligned`/`_hip_tilt_pole_aligned` read `frame.keypoints_3d_pole_aligned`; 정은지/RTMW path). 2D fallback only when `keypoints_2d` AND a detected pole `line` exist. [VERIFIED: `force_signals.py:1068-1157,924-959`]
- `compute_stability_metrics(angles, ..., pose_frames, ...)` — uses `angles` (stored) + per-frame `reliability`. [VERIFIED: `force_signals.py:1221-1280`]
- `compute_contact_stability(pose_frames, ..., pole_axis_measurement, ...)` — needs `line` (2D) + `_observed_torso_length` (image_2d `keypoints_2d`) + `pole_extension_landmarks`. With vertical_fallback `line=None`, returns graceful None metrics with `pole_line_missing` warning — **same graceful path students hit**. [VERIFIED: `force_signals.py:1443-1542,898-903`]

`infer_force_direction_pattern(force_signals_report, motion_id, mode_context)` consumes **only the ForceSignalsReport** (no pose data). [VERIFIED: `force_pattern.py:642-666`]

- The axis-tilt and stability tiers *could* run from stored data (joints3d pole-aligned reshaped + angles + a reconstructed reliability), but `compute_force_signals` is hard-typed to `list[PoseFrame]` and reads PoseFrame attrs directly (`frame.keypoints_3d_pole_aligned`, `frame.reliability`, `frame.keypoints_2d`). Reconstructing a faithful PoseFrame list from `joints3d` + `keypointReport` is possible in principle but lossy (no raw confidence, no pole_extension_landmarks) and re-implements the adapter — a hand-roll risk.
- **Verdict: HYBRID-NEEDED.** Re-run RTMW once from S3 → feed the live `pose_frames` to `compute_force_signals` exactly as `_process` does (`backend/functions/pipeline/app.py:1899-1908`), then `infer_force_direction_pattern`.

### Net verdict table

| Field | Consumed input | In phase4_v1? | Verdict |
|-------|----------------|---------------|---------|
| `meanAngles` | `angles` (T×J) | ✅ flat `angles` | **STORED-SUFFICIENT** (app already derives via `deriveMeanAngles`) |
| EXTEND `joint_expectations` (Fallback) | `angles` only | ✅ | **STORED-SUFFICIENT** |
| EXTEND (if Gemini recognizer) | `angles` + video `frames` | video in S3 (re-runnable) | ASSUMED — confirm recognizer choice |
| `BodyNormalizationProfile` | `pose_frames.keypoints_3d` (raw + conf) | ❌ (stored is pole-aligned, no conf) | **HYBRID-NEEDED** (Phase 6 precedent; verify all 11) |
| `ForceDirectionPattern` | full `pose_frames` (3D-aligned + 2D + reliability + ext-landmarks) | ❌ | **HYBRID-NEEDED** |

**Bottom line for the planner:** A single Pod-side backfill that re-runs RTMW once per motion (identical to Phase 6) and threads the live `pose_frames`/`angles` through the *same* `sunity_shared.analysis` functions satisfies D-01 (동일 코드 1벌) and D-02 (hybrid only where consumed inputs are not stored). The active phase4_v1 `joints3d`/`angles` are read-only — never overwritten.

## Standard Stack

No new external packages. All computation reuses existing in-repo modules. [VERIFIED: codebase — no install step required]

### Core (reuse, no install)
| Module | Purpose | Why standard |
|--------|---------|--------------|
| `sunity_shared.analysis.body_normalization_measurer.measure_body_profile` | BodyNormalizationProfile | Same fn `_process` uses (`pipeline/app.py:1171`) |
| `sunity_shared.analysis.technique.FallbackRecognizer.recognize` | EXTEND `joint_expectations` | Same fn `_process` uses (`pipeline/app.py:1610`) |
| `sunity_shared.analysis.force_signals.compute_force_signals` | Force signals (4 metrics) | Same fn `_process` uses (`pipeline/app.py:1899`) |
| `sunity_shared.analysis.force_pattern.infer_force_direction_pattern` | ForceDirectionPattern | Same fn `_process` uses (`pipeline/app.py:1932`) |
| `sunity_shared.analysis.pose_engines.rtmw.rtmw_engine.RTMWPoseEngine` | RTMW re-inference (hybrid) | Pod GPU engine; `reprocess_*:481`, `extract_*:335` |
| `sunity_shared.analysis.frame_extractor.FfmpegFrameExtractor` | Frame extraction | `extract_*:328` (default fps) |
| `sunity_shared.analysis.pose_frame.to_coco17_array` / `PoleAxis` | array conv + vertical fallback | reprocess/extract precedents |
| `firebase-admin` (Python on Pod) | versioned/atomic Firestore write | `reprocess_*:540-549` |
| `firebase-admin` (Node, app devDependency ^13.10.0) | atomic merge seed | `seed-reference-body-profile.mjs:176` |

**Installation:** None. Pod env already has rtmlib/onnxruntime/boto3/imageio (per [[rtmw-blackwell-lean-bootstrap]] / [[runpod-gpu-env]]). `firebase-admin` Python on Pod and `firebase-admin` Node in `app/` are present.

## Package Legitimacy Audit

> Not applicable — this phase installs **no external packages**. All dependencies are in-repo modules or already-present runtime deps (rtmlib, onnxruntime, boto3, firebase-admin). slopcheck not run (nothing to check).

## Architecture Patterns

### System Architecture Diagram (backfill data flow)

```
                       ┌──────────────────────────────────────────────┐
   S3 video            │  RunPod Pod qcf38vvsmub1y4 (RTX PRO 4500)     │
  reference/{id}.mp4 ──┼─> FfmpegFrameExtractor.extract                │
                       │      │                                         │
                       │      ▼                                         │
                       │   RTMWPoseEngine.estimate(frames, vertical_pole)
                       │      │  → list[PoseFrame]  (live, full attrs)  │
                       │      ├──> measure_body_profile ──> BodyNormalizationProfile
                       │      ├──> to_coco17_array → compute_joint_angles → temporal_fill
                       │      │       │ angles (T×J)                     │
                       │      │       ├──> FallbackRecognizer.recognize → EXTEND profile
                       │      │       └──> mean(axis=0)            → meanAngles
                       │      └──> compute_force_signals(pose_frames, angles, …)
                       │              └──> infer_force_direction_pattern → ForceDirectionPattern
                       │      ▼                                         │
                       │   emit JSON fixture (camelCase, flat arrays)   │
                       └───────────────┬──────────────────────────────┘
                                       │ scp to local
                                       ▼
              seed-reference-*.mjs (Firebase Admin, --dry-run → batch.merge, idempotent)
                                       │
                                       ▼
        Firestore reference/{motionId}  (top-level new fields; phase4_v1 active untouched)
                                       │
                          GET /reference (passthrough) ──> app referenceMotions.ts (Mode 1 list)
                                       │
                                       ▼  (consumed in Phase 15, NOT Phase 14)
                                Mode 1 student-vs-reference comparison
```

### Recommended approach (Claude's Discretion resolved)

Two viable shapes; **recommend the extend-Phase-6-extractor shape**:

**Pattern A (recommended): extend `extract_reference_body_profiles.py` into a 4-output backfill.**
- Per motion: download S3 video → extract → RTMW estimate → from one `pose_frames`/`angles` compute all four outputs through the production functions.
- Add EXTEND (`FallbackRecognizer().recognize(angles)`), force (`compute_force_signals` + `infer_force_direction_pattern`), meanAngles (mean over T) alongside the existing body-profile measurement.
- Emit one JSON fixture; extend the `.mjs` seeder's required-field validation + merge payload.
- Why: minimal new surface, proven dry-run/atomic/idempotent cycle, single RTMW run per motion (no double inference).

**Pattern B: separate single backfill script.** Cleaner separation but duplicates the download/extract/RTMW boilerplate. Acceptable but redundant.

### Version write strategy (Claude's Discretion resolved)
- **Recommend: top-level merge of NEW fields only** (mirrors Phase 6's `seed-reference-body-profile.mjs` `batch.set(ref, payload, {merge:true})`), NOT a new `versions/phaseN` write. Reasons: (1) consumers read top-level directly (`referenceMotions.ts` + `firestore_admin.get_reference_motion`); (2) the new fields are derived data, not a pose re-version; (3) phase4_v1 active `joints3d`/`angles` stay authoritative and visually-verified.
- Add per-field `*UpdatedAt` epoch-ms timestamps (Phase 6 convention, `seed-*.mjs:209,213`).
- For rollback safety, optionally snapshot the pre-backfill top-level into `versions/pre_phase14` (mirror `reprocess_*:_flip_active_pointer (a)`), or rely on idempotent re-run + `--force`.

### Anti-Patterns to Avoid
- **Reconstructing PoseFrame from stored flat arrays for force/body-profile.** Lossy (no raw confidence, no pole_extension_landmarks); re-implements the RTMW adapter. Use live re-inference (Phase 6 precedent).
- **Overwriting active `joints3d`/`angles`.** D-02: keep belle's visually-verified pose authoritative. Only ADD fields.
- **Running the backfill with the default 5 motion IDs.** [[reference-library-phase4-all11]]: scripts default to 5; **always pass all 11 explicitly** (`--motions`/`--motion-ids`).
- **Storing nested arrays.** All matrices flat + keys ([[firestore-nested-array-flat]]); the `.mjs` seeder already rejects nested arrays in `warnings`/`values`.
- **Inventing severity/finding numbers.** force_pattern forbids fabrication (`test_force_pattern_no_severity_use.py`); 0-finding → empty list + umbrella warning.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Joint-angle / pose extraction | Custom angle math | `to_coco17_array` + `compute_joint_angles` + `temporal_fill` | Exact student path; smoothing already applied once (double-smooth banned, REVIEWS R5) |
| Body proportion measurement | Re-derive segment ratios | `measure_body_profile` | 7-field profile + robust median + fallback |
| EXTEND inference | Threshold elbows/knees yourself | `FallbackRecognizer.recognize` | Conservative "모르면 깎지 않음" semantics locked |
| Force metrics | Tilt/jerk/contact math | `compute_force_signals` | 4 metrics + confidence propagation + warnings |
| Force pattern inference | Map signals→patterns | `infer_force_direction_pattern` | Deterministic, fabrication-gated, Top-3 |
| Firestore camelCase conversion | Manual dict | `_dataclass_to_camel_case_dict` (pipeline) / `_bp_to_camel_dict` (extract) | Lockstep with stored format |
| Atomic seed + idempotency | New writer | `seed-reference-body-profile.mjs` pattern | dry-run/force/verify cycle proven |

**Key insight:** D-01 mandates the *same functions* — any hand-rolled equivalent breaks the false-positive-prevention guarantee (reference and student must traverse identical computation).

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Firestore `reference/{id}` × 11: `activeVersion=phase4_v1`, top-level mirror (`joints3d`/`angles`/`keypointReport` + 8 more), `versions/phase4_v1`, `versions/pre_phase4` backup. Body profile (`bodyNormalizationProfile`/`bodyComparisonSourcePose`) present for the **original 5** (`extract_reference_body_profiles.py` DEFAULT_MOTION_IDS); **unverified for the 6 added later** (ref-combo, ref-elbow-twist-sister, ref-kip-up, ref-pdshape, ref-peter-pan, ref-power-spin). | **Planner: add a Wave-0 audit task** that reads all 11 docs and lists which already have body profile vs missing. Backfill must cover all 11 (pass `--motions`). New fields ADD-only. |
| Live service config | None. No n8n/Datadog/Tailscale. Lambda `RUNPOD_ANALYZE_URL` already synced to Pod `qcf38vvsmub1y4` (CONTEXT). | None — verified by CONTEXT §운영 환경. |
| OS-registered state | None — no Task Scheduler / pm2 / launchd for this phase. | None. |
| Secrets/env vars | Pod needs `AWS_*`, `FIREBASE_SA_PATH`/`FIREBASE_SA_JSON`, `RTMW_ONNX_PATH` (extract script reads these). Node seeder needs ADC (`gcloud auth application-default login`, `sunity3412@gmail.com`). No new secret keys. | Confirm Pod env populated before run ([[runpod-gpu-env]] 2026-06-15 recipe). |
| Build artifacts | S3 reference videos `reference/{id}.mp4` (11) — re-inference source, presigned not needed (Pod has AWS creds). No egg-info/compiled artifacts affected. | Verify all 11 `.mp4` exist in `sunity-motion-pilot-videos`. |

**Canonical question — after every repo file is updated, what runtime state still carries old/missing data?** The 6 later-added references likely lack body profiles (extractor defaulted to 5) and **all 11** lack force/EXTEND/meanAngles backfill. These are *missing* fields, not stale strings — the backfill writes them fresh.

## Common Pitfalls

### Pitfall 1: Default-5 motion-ID trap
**What goes wrong:** Running reprocess/extract with default args processes only 5 of 11. **Why:** `MOTION_IDS`/`DEFAULT_MOTION_IDS` = 5 (Wave-5 originals). **Avoid:** always pass all 11 explicitly. **Warning signs:** belle's 2026-06-15 "추가된 레퍼런스 분석이 엉망" was exactly this. [VERIFIED: [[reference-library-phase4-all11]] + `reprocess_*:54-60`, `extract_*:59-65`]

### Pitfall 2: pole-aligned vs raw keypoint confusion
**What goes wrong:** Feeding stored `joints3d` (pole-aligned, no confidence) to `measure_body_profile` (expects raw `keypoints_3d` + confidence) yields wrong proportions or NaN. **Avoid:** use live `pose_frames` from re-inference. [VERIFIED: `body_normalization_measurer.py:85` vs `to_coco17_array:337-348`]

### Pitfall 3: Double temporal smoothing
**What goes wrong:** Calling `compute_force_signals` with raw angles re-smooths (REVIEWS R5 ban). **Avoid:** pass the already-`temporal_fill`ed angles, exactly as `_process` does. [VERIFIED: `force_signals.py:1596-1598`]

### Pitfall 4: Overwriting active phase4_v1 pose
**What goes wrong:** Re-running RTMW and writing new `joints3d` replaces belle's visually-verified pose, creating re-validation burden (the exact thing D-02 avoids). **Avoid:** backfill writes ONLY new fields; never touch `joints3d`/`angles`/`activeVersion`. [CITED: CONTEXT D-02]

### Pitfall 5: 40k index-entry limit
**What goes wrong:** Large flat arrays in a Firestore doc exceed 40k auto-index entries. **Why it's NOT a problem here:** new fields are small — `meanAngles` (8 floats), EXTEND `joint_expectations` (8 string entries), `bodyNormalizationProfile` (7 fields), `forceDirectionPattern`/`forceSignalsReport` (per-phase ≈ 5×small metric dicts, flat list[dict]). The large arrays (`joints3d`, `keypointReport`) already exist and already have index exemptions on collectionGroup `reference`+`versions`. **Avoid regardless:** do not add any new per-frame (T-scaled) array to the reference doc. [VERIFIED: [[firestore-index-entry-limit]] + [[reference-library-phase4-all11]] (exemption applied) + `force_signals.py:495-505` flat list[dict]]

## Code Examples

### Hybrid backfill core (per motion) — mirrors `_process` downstream, Pod-side
```python
# Source: synthesized from extract_reference_body_profiles.py:215-263
#         + pipeline/app.py:1171,1610,1899-1936 (same functions, same order)
from sunity_shared.analysis.body_normalization_measurer import measure_body_profile
from sunity_shared.analysis.technique import FallbackRecognizer
from sunity_shared.analysis import force_signals as fs, force_pattern as fp, skeleton
from sunity_shared.analysis.features import compute_joint_angles, joint_uncertainty
from sunity_shared.analysis.temporal import temporal_fill
from sunity_shared.analysis.pose_frame import PoleAxis, to_coco17_array
from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement  # vertical fallback
import numpy as np

vertical_pole = PoleAxis(axis_vector=(0.0,1.0,0.0), confidence_level="low",
                         source="vertical_fallback", frame_index=None)
frames = extractor.extract(local_mp4)
pose_frames = rtmw_engine.estimate(frames, vertical_pole)   # live PoseFrame list (HYBRID)

kp = to_coco17_array(pose_frames)
angles = temporal_fill(compute_joint_angles(kp), joint_uncertainty(kp))  # one smoothing

# 1) meanAngles (STORED-SUFFICIENT — but compute here for consistency)
mean = np.nanmean(angles, axis=0)
mean_angles = {k: float(mean[i]) for i, k in enumerate(skeleton.JOINT_KEYS)}

# 2) EXTEND profile (STORED-SUFFICIENT input: angles)
profile = FallbackRecognizer().recognize(angles)            # joint_expectations

# 3) BodyNormalizationProfile (HYBRID input: pose_frames)
body_profile = measure_body_profile(pose_frames)

# 4) ForceDirectionPattern (HYBRID input: pose_frames)
pole_meas = build_pole_axis_measurement(axis_3d=vertical_pole, line=None, frame_index=None)
# NOTE (D-01 parity, WARNING #2): the student `_process` passes
#   technique_profile=<recognizer output> and
#   preflight_label_gate_passed=_preflight_label_gate_passed() (env-driven).
# The v1 reference backfill PINS technique_profile=None and
#   preflight_label_gate_passed=None (recognizer=Fallback, layer-2 force-signal off)
#   so "동일 코드 1벌" is provably EXACT, not merely default-equivalent. The 14-01
#   parity test asserts the backfill helper passes the SAME preflight value the
#   student path uses under this pinned config (env flip would otherwise diverge).
fsr = fs.compute_force_signals(pose_frames, pole_meas, body_profile,
                               angles=angles, fps=9.0,
                               motion_id=getattr(profile, "motion_id", None),
                               technique_profile=None,
                               preflight_label_gate_passed=None)
fpi = fp.infer_force_direction_pattern(fsr, motion_id=getattr(profile, "motion_id", None),
                                       mode_context="mode1")
# → emit camelCase JSON via _dataclass_to_camel_case_dict-equivalent; seed via .mjs
```

### Atomic merge seed (extend existing pattern)
```js
// Source: app/scripts/seed-reference-body-profile.mjs:207-225 (extend payload + required-field list)
const docPayload = {
  meanAngles: data.meanAngles,
  techniqueProfile: data.techniqueProfile,          // EXTEND joint_expectations
  bodyNormalizationProfile: data.bodyNormalizationProfile,
  forceDirectionPattern: data.forceDirectionPattern,
  // ...UpdatedAt timestamps per field (Date.now())
};
batch.set(db.collection('reference').doc(motionId), docPayload, { merge: true });
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Reference body profile for 5 motions | All 11 need profile + force + EXTEND + meanAngles | 2026-06-15 (this phase) | Backfill must cover 11, not 5 |
| Reference pose = old 8-joint 2D | RTMW phase4_v1 17-joint 3D, all 11 active | 2026-06-15 | Backfill builds on verified 3D pose |
| Mode 1 reads `angles`/body profile from reference | Phase 15 will also read force/EXTEND from reference | Phase 15 (future) | Phase 14 = data prep only; current `_process` mode1 does NOT yet read these (`pipeline/app.py:1623-1715`) |

**Deprecated/outdated:**
- ROADMAP SC#1 "정은지 영상 업로드 등록 / 다각도 권장" — superseded by CONTEXT D-03/D-05 (backfill only, capture guide is doc-only).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reference EXTEND should use `FallbackRecognizer` (not Gemini recognizer) for the backfill | Primary Q #1 | If Gemini intended, backfill needs S3 video frames input (available) + Gemini env keys; EXTEND profile content differs (named technique vs "미상") |
| A2 | The 6 later-added references lack `bodyNormalizationProfile` (extractor defaulted to 5) | Runtime State Inventory | If they already have it, body-profile re-measure is redundant (harmless with `--force`); if not, missing it breaks Phase 15 Mode 1 |
| A3 | New reference fields should be top-level merge (not a new `versions/` doc) | Architecture Patterns | If versioned write expected, consumers (`referenceMotions.ts`, `get_reference_motion`) read top-level → would not see versioned data without a resolver |
| A4 | `mode_context="mode1"` is correct for reference force inference | Code Examples | reference is the Mode 1 target; if a neutral context is wanted, `infer_force_direction_pattern` branching differs slightly |
| A5 | Single-view confidence flagging = surface existing `bodyNormalizationProfile.confidence` + force report `overall_confidence` + a `singleView:true`/`captureViews:1` flag | Single-view handling | If a distinct schema field is required by Phase 15, contract update needed |

## Open Questions (RESOLVED)

1. **EXTEND recognizer choice (A1).** Fallback (angles-only, STORED-SUFFICIENT) vs Gemini (needs video, richer profile).
   - **A1 — RESOLVED:** Use `FallbackRecognizer` for the v1 backfill (CONTEXT A1 / conservative production default "모르면 깎지 않음"); Gemini reference EXTEND deferred (would need S3 video frames + Gemini env). Pinned in plan **14-02 Task 1** (`FallbackRecognizer().recognize(angles)`, NOT Gemini) and asserted by the **14-01** D-01 parity test.
2. **Body-profile coverage of the 6 later motions (A2).** Resolve with a Wave-0 read of all 11 docs before backfill (cheap, no GPU).
   - **A2 — RESOLVED:** A read-only Firestore audit in **14-01 Task 1** (`audit-reference-fields.mjs`) enumerates which of the 11 already carry `bodyNormalizationProfile` (and the other new fields). Backfill (14-02/14-03) covers all 11 regardless (`--motions` = 11-union); ADD-only `--force` makes a redundant re-measure harmless.
3. **Contract update.** `docs/contract.md` §`ReferenceMotion` does not list `meanAngles`/`techniqueProfile`/`bodyNormalizationProfile`/`forceDirectionPattern`. Backfill adds them ⇒ contract + `app/src/types/analysis.ts` should gain optional fields (3-way lockstep rule, CLAUDE.md Cross-cutting). App `referenceMotions.ts` `normalize()` ignores unknown fields gracefully, so the Mode 1 list will **not** break even before the type update [VERIFIED: `referenceMotions.ts:70+` defensive normalize].
   - **A3 — RESOLVED:** 3-way contract lockstep (`docs/contract.md` §3 + `app/src/types/analysis.ts` ReferenceMotion; Python `force_pattern.py`/`technique.py` already define the source shapes) is done in **14-01 Task 3**, adding `techniqueProfile?`/`forceDirectionPattern?`/`captureViews?` as OPTIONAL/nullable fields. Top-level merge (A3 assumption) confirmed — no versioned resolver needed.
4. **Single-view confidence representation (SC#4 / D-03).** Lightweight: all 11 are single-view, so set a `captureViews: 1` (or `singleView: true`) flag + rely on existing `confidence` fields. Confirm desired field name with discuss.
   - **A5 — RESOLVED:** Field name = `captureViews: number` (= 1 for the single-view v1 references) per RESEARCH A5, adopted by all three plans (14-01 contract field, 14-02 seeder/helper payload, 14-03 verify-read) alongside the existing `bodyNormalizationProfile.confidence` + force-report `overall_confidence`. No distinct schema field beyond `captureViews` for v1.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| RunPod Pod `qcf38vvsmub1y4` (RTX PRO 4500) | RTMW re-inference (HYBRID) | ✓ | UP, /health ok (CONTEXT) | None — CPU gives NaN; blocking if Pod down |
| rtmlib + onnxruntime (Pod) | RTMWPoseEngine | ✓ (assumed per env recipe) | per [[rtmw-blackwell-lean-bootstrap]] | None |
| imageio / imageio-ffmpeg (Pod) | FfmpegFrameExtractor | ✓ (assumed) | — | None |
| boto3 (Pod) | S3 video download | ✓ (assumed) | — | None |
| firebase-admin (Python, Pod) | versioned write (if used) | ✓ (`reprocess_*` uses) | >=6,<7 | Node seeder instead |
| firebase-admin (Node, app/) | atomic merge seed | ✓ devDependency | ^13.10.0 | — |
| ADC (`gcloud auth`) | Node seeder real-run | ✗ unknown on this machine | — | `--dry-run` first; belle runs `gcloud auth application-default login` |
| S3 `reference/{id}.mp4` × 11 | re-inference source | ? verify | — | None — missing video blocks that motion |

**Missing/blocking:** None confirmed missing, but Pod-side rtmlib/imageio/boto3 presence is [ASSUMED] from the env recipe — verify at run start (fail-fast import). ADC for the Node seeder is the one likely-missing human step (belle).

## Validation Architecture

> nyquist_validation = true (config.json). Test framework: pytest (`backend/requirements-dev.txt` pytest >=8,<9; tests under `backend/tests/`). Node has no JS test runner; app gate = `tsc --noEmit`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (backend) |
| Config file | none committed (no pytest.ini); tests in `backend/tests/` |
| Quick run | `cd backend && python -m pytest tests/ -x -q` |
| Full suite | `cd backend && python -m pytest tests/ -q` |
| App gate | `cd app && npm run typecheck` (`tsc --noEmit`) |

### Success Criterion → Validation Map
| SC | Behavior | Validation type | Command / check | Exists? |
|----|----------|-----------------|-----------------|---------|
| SC#1 | All 11 references appear in Mode 1 list | integration | `node app/scripts/<seed>.mjs --verify` reads all 11 + `referenceMotions.ts normalize()` returns 11; app `npm run typecheck` | ❌ Wave 0 (verify step) |
| SC#2 | Each reference has meanAngles + EXTEND + BodyNormalizationProfile + ForceDirectionPattern | integration | Post-seed Firestore read asserts 4 fields present + non-empty for all 11 (extend `.mjs` verify loop) | ❌ Wave 0 |
| SC#2 (compute) | Backfill outputs equal student-path outputs (D-01) | unit | pytest: feed a fixture `pose_frames`/`angles` to the backfill helper AND to `_process`'s downstream calls; assert identical dataclasses + SAME `preflight_label_gate_passed` value | ❌ Wave 0 (`backend/tests/test_reference_backfill.py`) |
| SC#3 | Capture guide documented | manual | review `docs/` markdown deliverable exists with 촬영 조건/앵글/시점 수 | manual |
| SC#4 | Single-view graceful + low confidence | unit | pytest: vertical-fallback `line=None` → force contact metrics return None + `pole_line_missing` warning (no crash); confidence flag set | ❌ Wave 0 |
| D-02 verdict | Stored-sufficient vs hybrid correctness | unit | pytest: assert `measure_body_profile`/`compute_force_signals` raise/NaN when fed reconstructed-from-flat data, proving HYBRID necessity; assert EXTEND/meanAngles match from `angles` alone (STORED-SUFFICIENT) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_reference_backfill.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -q` + `cd app && npm run typecheck`
- **Phase gate:** full suite green + manual Firestore read of all 11 (4 fields each) + belle visual spot-check before any flip; full suite before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/test_reference_backfill.py` — covers SC#2 (compute equals student path + same preflight value), SC#4 (single-view graceful), D-02 verdict assertions
- [ ] Firestore-read audit task (no GPU): list which of 11 already have body profile (resolves A2)
- [ ] Extend `.mjs` seeder `--verify` to assert the 4 new fields on all 11
- [ ] Capture-guide markdown skeleton (SC#3)
