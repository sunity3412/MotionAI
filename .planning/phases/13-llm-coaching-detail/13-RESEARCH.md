# Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성 - Research

**Researched:** 2026-06-16
**Domain:** (Plan A) corrective-exercise mapping over existing analysis findings + RN result UI; (Plan B) real-LLM coaching activation (Cerebras) + IPSF/학원 branch copy in backend assemble/coach_writer
**Confidence:** HIGH (codebase paths grepped + read; NotebookLM primary source queried live; no new external packages)

## Summary

Phase 13 has **zero greenfield infrastructure risk**. Both halves attach to code that already exists and is exercised in production: Plan A maps onto the Phase 9 `ForcePatternInference` finding cards + Phase 3 `BodyProfile.painAreas` (both already in the Firestore `AnalysisResult` doc and rendered by `result.tsx`), and Plan B flips on the already-written `CerebrasCoachWriter` (already a graceful no-op when the key is unset) and extends the already-existing `assemble.build_dimension_explanation` (currently mode-aware only) with one `ipsfCode` branch. No new npm/PyPI package is required — `cerebras-cloud-sdk>=1.0,<2.0` is already pinned in `runpod_inference/requirements.txt` [VERIFIED: backend/runpod_inference/requirements.txt:46]. Latest PyPI version is 1.67.0 [VERIFIED: pypi registry].

The two genuinely new decisions are: (1) **where the exercise library lives** — recommendation: a committed JSON/YAML fixture under `backend/` (NOT Firestore), because it is static curated content, must stay in lockstep with the 3-way contract, and needs no per-user write path; and (2) **where `ipsfCode` comes from** — recommendation: keep the IPSF Code mapping as a **separate small backend fixture keyed by `motion_id`** (reusing/normalizing the data already in `backend/data/aka-mapping.json` + `reference-motions-branch2.json`), looked up at assemble time from `TechniqueProfile.motion_id`. Do **not** add `ipsf_code` as a scored field; it only branches copy.

The mandatory NotebookLM research (belle D-06) returned concrete, citable per-move IPSF hold-angle thresholds (notebook 96b061e8) and a defect→exercise + painArea→exercise + LTAD table (notebook e688fb4e). These are reproduced verbatim-with-citation below and are sufficient to author both the criteria-7 angle fixture and the exercise library without further lookups.

**Primary recommendation:** Plan A = ship a committed `backend/data/corrective_exercises.json` fixture + a pure `map_exercises(force_pattern_inference, pain_areas, motion_id) -> RecommendedExercise[]` function + a `recommendedExercises` field on `AnalysisResult` (3-way lockstep) + a "보완 운동" section in `result.tsx` after "코칭 팁" with a "다른 운동 보기" modal. Plan B = inject `CEREBRAS_KEY_PARAM` on the Pod, restart uvicorn, add an `ipsfCode` branch to `build_dimension_explanation`, and inject motion name + branch + the criteria-7 IPSF angle fixture into the `coach_writer` system prompt. Only criteria-5 (real video → real LLM E2E) needs the GPU Pod.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 연령·성별 입력 + 국민체력100 규준 맞춤 = **v2 연기** (PERS-04). v1 Phase 13 미소비.
- **D-02:** `backend/judging_data/fitness_norms_kspo.yaml` (커밋 3c937d9) = v1 에서 커밋된 채 대기, v1 미소비.
- **D-03:** 매핑 입력 = **Phase 9 실패 원인 후보 + BodyProfile `painAreas`**. 국민체력100 규준 제외. 체력 자동 등급배치 금지.
- **D-04:** 보완운동 라이브러리 = **greenfield**. NotebookLM 큐레이션. 초기 3~5 동작군 + 결함당 운동 5~10개.
- **D-05:** Phase 13 = **플랜 2개 분리**. Plan A = 보완운동(criteria 1-4, GPU 불필요, fixture 단위테스트). Plan B = 실 Cerebras LLM + `ipsfCode` 분기 + coach_writer 프롬프트 주입(criteria 5-8). criteria 5 E2E 검증만 Pod 필요.
- **D-06:** 리서치 비중 상향 + **NotebookLM 필수** (1차 소스). → 본 문서가 충족 (아래 §NotebookLM Primary-Source Findings).

### Claude's Discretion
- 보완운동 라이브러리 저장 형태(JSON fixture vs Firestore) = planner 재량. 단 contract-first 정합. → **권장: 커밋된 backend fixture (아래 Plan A Storage Decision 근거).**
- IPSF Code 매핑 테이블을 `studio-term-3branch` 데이터로 흡수할지 별도 둘지 = planner 재량. → **권장: 별도 작은 `motion_id → ipsfCode` fixture (아래 Plan B §ipsfCode Source).**

### Deferred Ideas (OUT OF SCOPE)
- 연령·성별 입력 + 국민체력100 규준 맞춤 리포트 → v2 PERS-04.
- 부상 위험 경고(SAFE) 본격 UI → v2. Phase 13 의 `injuryRisk` 는 LLM 출력 한 줄로만 유지.
- 회차별 성장 그래프, 영상 인앱 다운로드 → v2.
- 분기 3 (자동 수집) 카피 분기 → v2. v1 = 분기 1 (IPSF 등재) + 분기 2 (학원 통용 정은지) 만.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERS-03 (v1) | 분석 결과 → 보완 운동·스트레칭 자동 매핑 | Plan A: `map_exercises()` over `forcePatternInference.findings[].jointHint/sourceSignal` + `bodyProfile.painAreas`. Library curated from NotebookLM (§NotebookLM Findings table). |
| `studio-term-3branch-system` (memory) | 분기 1 (IPSF 등재) vs 분기 2 (학원 통용 정은지) 카피 분리 | Plan B: `ipsfCode` branch in `build_dimension_explanation`; source = `aka-mapping.json` (`isRegistered:true`, `ipsfCode`) vs `reference-motions-branch2.json` (`ipsfRegistered:false`). |
| SCORE-05 (5트랙, ref) | Page 9 절대 트랙 정합 — 보완운동/코칭은 채점 비유입 | Plan A/B both: BodyProfile/painAreas feed mapping+coaching ONLY, never scoring (models.py D-05). |
| TERM-* (ref) | 학원 용어 자연 노출 ("폭스탑" → "정은지 선수 기준") | Plan B criteria 8: branch-2 copy avoids "세계 심사 기준" for non-registered motions. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Exercise library storage | Backend / Static (committed fixture) | — | Static curated content; no per-user writes; must lockstep with 3-way contract. Firestore would add a read+seed path with zero benefit. |
| Exercise mapping logic | API/Backend (ML core, pure fn) | — | Pure function over existing `ForcePatternInference` + `BodyProfile`; numpy/AWS-free; unit-testable (mirrors `force_pattern.py` / `classify_findings` pattern). |
| Exercise display + "다른 운동 보기" | App (RN result.tsx + new modal) | — | UI-only; reuse Phase 12.5 modal pattern (`CoachingTipDetailModal`). |
| Real Cerebras LLM activation | RunPod GPU server env + Lambda env | API/Backend (`coach_writer.py` unchanged code path) | Code already written + graceful; activation = inject `CEREBRAS_KEY_PARAM` + uvicorn restart. |
| `ipsfCode` branch copy | API/Backend (`assemble.build_dimension_explanation`) | Backend fixture (`motion_id→ipsfCode`) | Copy branching only; no scoring impact; mode-aware baseline already lives here. |
| IPSF angle fixture → coach prompt | API/Backend (`coach_writer._build_prompt` + system prompt) | Backend fixture (per-move angles) | LLM cites correct degrees; fixture from NotebookLM CoP. |

## Standard Stack

### Core (all already present — NO new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cerebras-cloud-sdk` | `>=1.0,<2.0` (latest 1.67.0) | Real LLM coaching (`tip.detail2`) | Already pinned + wired in `coach_writer.py::CerebrasCoachWriter`; graceful no-op when key unset. [VERIFIED: backend/runpod_inference/requirements.txt:46] |
| `boto3` | Lambda/Pod runtime | SSM `get_parameter` for `CEREBRAS_KEY_PARAM` | Already used by `coach_writer._load_api_key()` (auth.py pattern). |
| `PyYAML` | present (judging_data loaders) | If library stored as `.yaml` | `force_signals._load_expected_contact_points` already `yaml.safe_load`s `contact_points.yaml`. |
| `react-native-svg` | 15.12.1 | Any exercise card iconography (optional) | Already installed; no new chart lib. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Committed JSON/YAML fixture for exercises | Firestore `exercises` collection | Firestore adds seed script + read latency + no-benefit write path. Choose fixture (static content, contract-locked). v2 self-service could revisit. |
| Cerebras `gpt-oss-120b` | Gemini coach writer (`coach_writer_v2`, Phase 17) | Phase 17 not done; `_ensure_gemini_coach_writer` falls back to Cerebras anyway. Phase 13 targets Cerebras path (criteria 5 wording). |
| `.json` for exercise library | `.yaml` | Either fine. JSON matches `aka-mapping.json`/`reference-motions-branch2.json` precedent in `backend/data/`. **Recommend `.json`** for consistency with existing `backend/data/*.json`. |

**Installation:** None. (Verify Pod has the dep: `python -c "import cerebras.cloud.sdk"`.)

## Package Legitimacy Audit

> Phase 13 installs **no new external packages**. All dependencies are pre-existing project deps. Audit is informational.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `cerebras-cloud-sdk` | PyPI (1.67.0) | mature (1.0→1.67 release history) | n/a | github.com/Cerebras/cerebras-cloud-sdk-python | not run (no install) | Already a project dep — Approved |
| `boto3` | Lambda runtime | mature | n/a | aws | not run | Runtime-provided — Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## NotebookLM Primary-Source Findings (D-06 — mandatory 1차 소스)

NotebookLM MCP/CLI was **available and queried live** (nlm 0.7.1, authenticated). Two canonical notebooks queried. Both answers are reproduced with their internal citation numbers; cite these in the fixture `source_ref` fields.

### A. Per-move IPSF / biomechanical hold angles — criteria-7 angle fixture source
> Notebook `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` "IPSF Rules and Advanced Strength Pole Moves Guide", query 2026-06-16. [CITED: NotebookLM 96b061e8]

| Move | Joint | Required angle | Tolerance | Fault |
|------|-------|----------------|-----------|-------|
| **Ayesha** | Bottom shoulder | 180° (flexed) | — | improper push-pull → loss of equilibrium (-0.5) |
| | Top shoulder | 110° | — | rounded shoulders (-0.2) |
| | Bottom elbow | 180° fully extended | 0° (no micro-bend) | not awarded (0) |
| | Top elbow | 20°–30° flexed | — | poor alignment (-0.2) |
| | Knees | 180° fully extended | 0° | micro-bend → 0 |
| **Iron X** | Body to pole | 90° horizontal | ±20° | beyond 20° → 0 |
| | Bottom shoulder | 180° flexed | — | collapse → absolute deduction |
| | Top shoulder | 90° abducted | — | rounding (-0.2) |
| | Bottom elbow | 180° extended | 0° | bend → fail |
| | Knees | 180° extended | 0° | bend → 0 |
| **Shoulder Mount** | Elbows (both) | 90° flexed | — | re-grip (-0.5) |
| | Knees | 180° extended (straight-leg var.) | 0° | bend → 0 |
| **Inside Leg Hang / Scorpio** | Split angle | ≥160° min | up to 20° (F-codes) | below min → 0 |
| | Hooked knee | 90°–110° flexed | — | slip → -0.5 |
| | Free knee | 180° extended | 0° | micro-bend → fail |
| **Jade Split** | Split angle | 180° | max 20° (min 160°) | <160° → unrecognized (0) |
| | Body to floor | 0° parallel | ±20° | torso tilt >20° → fail |
| | Knees | 180° extended | 0° | bend → 0 |
| **Invert (basic)** | Pelvis/spine | hips over head | ±20° from inverted baseline | no concrete per-joint degree; spatial requirement only |
| **Deadlift (Aerial)** | Knees | 180° extended | 0° | micro-bend → 0 |
| | Body/spine | 180° vertical | ±20° | >20° → 0 |

**Key fixture rule for criteria 7:** the IPSF "EXTEND→180°" target applies to **registered** moves (branch 1). For **branch-2 정은지 reference** moves (e.g. ref-foxtop), the criteria yamls already store 정은지 measured angles with `extension_class: BENT_OK` (e.g. `left_shoulder angle_target=139.02`, `right_shoulder=74.31` in `judging_data/criteria/ref-foxtop.yaml`) — these are the per-move angle source for branch-2 prompts, NOT 180°. This is exactly the criteria-8 "어색 표현 회피" requirement.

### B. Defect → exercise / painArea → exercise / LTAD — exercise library source
> Notebook `e688fb4e-a4fb-4e83-a168-9c4726a98e09` "폴스포츠에 대한 지식", query 2026-06-16. [CITED: NotebookLM e688fb4e]

**Defect → exercises (name | sets/reps | one-line purpose):**

| Defect key (maps to) | Exercises (≥5 each) |
|----------------------|---------------------|
| **grip_weak** (sourceSignal `late_contact`/`abnormal_release`, painArea `wrist`) | Farmer's Walk (왕복) · Hand Grippers (수시 반복) · Assisted Pull-ups (밴드 5~10회) · Dead Hang (5~10회/초) · Deadlift (10~15회) |
| **shoulder_unstable** (jointHint 광배/어깨, painArea `shoulder`) | Push-ups (8~12회) · Overhead Press (10~15회) · Scapular Depression Drills (매달려 버티기) · Arm Circles (전 10회/방향, 동적) · Cross-Shoulder Stretch (후 20~30s) |
| **core_weak** (sourceSignal `axis_tilt`/`high_jitter`, jointHint 코어) | Planks (30~60s) · Side Planks (양측 30~60s) · Russian Twists (10~15회) · Hanging Leg Raise (8~12회) · Supermans (10~15회) |
| **legs_not_extended** (sourceSignal line deficit knee/elbow, jointHint 무릎) | Squats (10~15회) · Lunges (양발 10~15회) · Calf Raises (15~20회) · High Kick (양발 10회, 능동) · Lateral Leg Raise (양측 10~15회) |
| **hip_hamstring_tight** (split deficit, jointHint 고관절/내전근) | Hamstring Stretch (후 20~30s) · Hip Flexor Stretch (후 20~30s) · Quad Stretch (후 20~30s) · Dynamic Leg Swings (전 10회) · PNF Stretch (파트너 수축/이완) |

**painArea → safe-reinforce / avoid (8 areas, PAIN_AREAS frozenset 정합):**

| painArea | 회피 | 보강 |
|----------|------|------|
| `shoulder` | 통증 시 매달리기 중단 | push 운동 밸런스 + 능동 견갑 안정화 |
| `wrist` | twisted grip / 꺾인 손목 고하중 제한 | Farmer's Walk + 악력기 (전완근 보호) |
| `lower_back` | 반동 데드리프트/뒤집기 회피 (감점 요인) | Supermans + 정적 Plank |
| `knee` | 오금 단독 체중 레그행 반복 감소 | Squat + Lunge (대퇴사두 강성) |
| `ankle` | sickled foot 정렬 회피 (감점 -0.1) | Calf Raises |
| `neck` | 무리한 숄더 마운트/스탠드 회피 | 가벼운 목 스트레칭 |
| `hip` | 웜업 없는 180°+ 다리찢기 강행 금지 | Leg Swings + 비둘기 자세 (모빌리티) |
| `elbow` | 엘보 그립 안쪽 과하중 경계 | 이두/삼두 근력 균형 (수직+수평 당기기) |

**LTAD progression (poleExperienceLevel 정합, 단 D-03: scoring/auto-grading 금지, 코칭 톤 only):**
- 입문(beginner): 기초 클라임 + 정적 스핀; 무리한 핸드스프링/인버트 배제.
- 초중급(intermediate): 수평 당기기·미는 운동 교차; 반동 아닌 코어/고관절 인버트.
- 전문가(advanced): 동적 플립/릴리즈; 주기화 + CoP 완전 이해.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────── PLAN A (no GPU) ────────────────┐
  Firestore AnalysisDoc.result                                              │
   ├─ forcePatternInference.findings[]  ─┐                                  │
   │     (sourceSignal, jointHint,       │   map_exercises()  (pure fn)     │
   │      phase, interpretation)         ├──▶  defect/painArea/motion keys  │
   ├─ bodyProfile.painAreas[]  ──────────┘        │                         │
   │     (Phase 3 self-input, snapshot)           ▼                         │
   │                                  corrective_exercises.json (fixture)   │
   │                                              │                         │
   │                                  result.recommendedExercises[]  ───────┼──▶ result.tsx
   │                                       (3-way lockstep field)           │     "보완 운동" section
   └──────────────────────────────────────────────────────────────────────┘     + "다른 운동 보기" modal

                         ┌──────────────── PLAN B ─────────────────────────┐
  pipeline _process / RunPod server                                         │
   ├─ TechniqueProfile.motion_id ──▶ motion_id→ipsfCode fixture             │
   │       │                              │                                 │
   │       │            assemble.build_dimension_explanation(... ipsfCode)  │
   │       │              ├─ branch1 (registered): "세계 심사 기준(IPSF)+180°"│
   │       │              └─ branch2 (정은지):      "정은지 선수 기준 자세"   │
   │       ▼                                                                 │
   │  coach_writer._build_prompt(joints, motion_name, branch, angle_fixture)│
   │       │   (CEREBRAS_KEY_PARAM set on Pod env → real Cerebras call)      │
   │       ▼                                                                 │
   │  tip.detail2 {causes, injuryRisk, coachNote}  ──▶ Firestore  ──▶ result.tsx
   └────────────────────────── criteria-5 E2E needs GPU Pod ────────────────┘
```

### Plan A — Storage Decision (RECOMMEND: committed backend fixture)
**What:** Curated, static exercise library = a committed file, NOT a Firestore collection.
**Why:** (1) content is static + curated (NotebookLM), no per-user writes; (2) must lockstep with the 3-way contract (a Firestore-only source can't be unit-tested against the contract); (3) precedent — `backend/data/aka-mapping.json`, `reference-motions-branch2.json`, `backend/judging_data/contact_points.yaml` are all committed fixtures loaded by pure code; (4) zero seed/ADC operational step (mirrors STATE memory `user-beginner-stepwise`).
**Where:** `backend/data/corrective_exercises.json` (JSON to match `backend/data/*.json` precedent).
**Key schema (recommend):**
```jsonc
{
  "schemaVersion": "1.0.0",
  "sourceNotebook": "e688fb4e-a4fb-4e83-a168-9c4726a98e09",
  "defects": {
    "core_weak": {
      "triggers": { "sourceSignals": ["axis_tilt","high_jitter"], "jointHints": ["코어"] },
      "exercises": [
        {"name":"플랭크","setsReps":"30~60초 유지","purpose":"공중 수평 자세 척추 처짐 저지","sourceRef":"NotebookLM e688fb4e [3]"}
      ]
    }
  },
  "painAreas": {
    "shoulder": {"avoid":"통증 시 매달리기 중단","exercises":[ ... ]}
  }
}
```
- **Mapping key schema (the join):** `force_pattern_inference.findings[].source_signal` + `.joint_hint` → defect key; `bodyProfile.painAreas[]` → painArea key; `technique_profile.motion_id` → optional move-specific gating (e.g. safety: 핸드스프링/데드리프트 only after Ayesha consistent — NotebookLM 96b061e8 safety gate). Dedup + cap at 3~5 (criteria 2). painAreas take priority for safety-avoid lines.

### Plan A — Exercise mapping function (pure, mirrors existing patterns)
**What:** `map_exercises(force_pattern_inference: dict | None, pain_areas: list[str], motion_id: str | None) -> list[dict]`
**When:** Called in `pipeline _process` right after `force_pattern_inference_dict` is built (it already exists at app.py ~1948), result threaded into `assemble.build_result(...)`.
**Pattern (follow `force_pattern.py` / `classify_findings`):** pure, numpy-free, module-level canned tables wrapped in `MappingProxyType`, frozenset validators, no AWS. Unit-testable with fixtures.

### Plan A — result.tsx attachment
`result.tsx` renders ordered sections: `동작 비교` → `실패 원인 후보`(ForcePatternCard, line 775) → `구간별 점수` → `세부 점수` → `코칭 팁`(line 854) → **[NEW] 보완 운동**. Attach a new `보완 운동` section after `코칭 팁` (~line 945). Reuse the Phase 12.5 modal pattern (`CoachingTipDetailModal` backdrop=pure View + top Pressable — the documented ScrollView-gesture gotcha fix) for "다른 운동 보기".

### Plan B — Real Cerebras activation path
**Code is already written and graceful.** `CerebrasCoachWriter.__init__` calls `_load_api_key()` → reads SSM param named by env `CEREBRAS_KEY_PARAM`; if unset/fails, `self._client=None` and `write()` returns `{}` → `assemble` numeric fallback (not fabrication). Activation steps (operational, not code):
1. Store Cerebras key in Parameter Store (SecureString), e.g. `/sunity/motion/cerebras-key`.
2. Set Lambda env `CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-key` (SAM template / `aws lambda update-function-configuration`).
3. Set the **Pod** env `CEREBRAS_KEY_PARAM` (the real `_process` runs on RunPod) + AWS creds for SSM read (Pod already has `AWS_ACCESS_KEY_ID` etc. per STATE) → **uvicorn restart** (`--workers 1` holds the singleton; the module-cached `_COACH_WRITER` is created at first `_process`, so restart picks up new env). memory `pod-ops-claude-runs`, `runpod-gpu-env`.
4. `GEMINI_COACH_ENABLED` (Phase 17 dual-track) is OFF by default → Cerebras-only path runs (pipeline app.py ~1860 `else` branch). Keep it OFF for Phase 13.
- **"uvicorn 재시작" = ** kill the running `uvicorn runpod_inference.server:app ...` and re-launch; `/health` should report `auth_configured:true, pipeline_loaded:true` (STATE Plan 08-03 pattern).
- **criteria 5 is the ONLY Pod-dependent item.** Code + unit tests (prompt assembly, `_normalize_entry`, branch copy) run locally with mocked Cerebras.

### Plan B — `ipsfCode` branch in build_dimension_explanation
**Current:** `build_dimension_explanation(assessments, dimension_scores, comparison, joint_angles, profile)` derives `mode` from `comparison["mode"]` and picks `_DIMENSION_BASELINES_MODE1/3`. (assemble.py:98-99)
**Add:** resolve `ipsf_code` from `profile.motion_id` via the new fixture, then branch the angle/line baseline copy:
- **branch 1 (registered, `ipsfCode` present):** "세계 심사 기준 (IPSF) — 어깨/무릎 180° 신전" (criteria 6).
- **branch 2 (정은지 reference, `ipsfRegistered:false`):** "정은지 선수 기준 자세" (criteria 6 + 8) — never say "세계 심사 기준" for branch-2.
- Pass `ipsf_code`/`branch` into `build_dimension_explanation` (new kwarg, default None → falls back to today's mode-aware copy = backward compatible, mirrors how `joint_angles`/`profile` were added in 12.5).

### Plan B — `ipsfCode` Source (RECOMMEND: separate small fixture keyed by motion_id)
`ipsf_code` does **not** exist anywhere in code today (grep confirmed) — only as data in `backend/data/aka-mapping.json` (`isRegistered:true`, has `ipsfCode`) and `reference-motions-branch2.json` (`ipsfRegistered:false`). `TechniqueProfile` has `motion_id` but no `ipsf_code`. **Recommend** a tiny derived fixture `backend/data/motion_ipsf_map.json` (`{motion_id: {ipsfCode|null, isRegistered, officialName}}`) generated from the two existing files, looked up at assemble time. Rationale: keeps `build_dimension_explanation` dependency-light (no aka-mapping parse coupling), and the branch only needs `isRegistered` + a display string. Do NOT add `ipsf_code` to `TechniqueProfile` scoring path (objectivity / D-05).

### Plan B — IPSF angle fixture → coach prompt (criteria 7)
`coach_writer._build_prompt(joints)` currently lists only deviation degrees. Extend signature to accept `motion_name`, `branch`, and a per-move `angle_fixture` (from §NotebookLM A, branch-1) or branch-2 정은지 measured angles (from the criteria yaml already on disk). Inject into the user prompt so the LLM cites correct degrees ("아이샤 아래 어깨 180°"). System prompt `_SYSTEM` gets a one-line "정확한 기준 각도만 인용, 임의 수치 생성 금지" guard.

### Anti-Patterns to Avoid
- **BodyProfile → scoring leak.** `painAreas`/`weightKg` must feed exercise mapping + coach context ONLY, never dimension scores (models.py D-05; existing `_build_coach_context` already passes `bodyProfile` graceful). Add a grep gate test.
- **Human-score labeling.** Exercise/branch copy must not encode belle/강사/심사자 scores; angle thresholds are objective IPSF/measured values only (memory `analysis-objectivity-no-human-scores`).
- **Editing one side of the contract.** `recommendedExercises` + any `ipsfCode` field must be added to `analysis.ts` + `models.py` + `docs/contract.md §4` together (the 3-way lockstep is enforced by existing drift tests).
- **Firestore nested arrays.** If `recommendedExercises` is a list-of-dicts, ensure `_validate_dict_only_scalars` / scoped validator path allows it (precedent: `force_pattern_inference` 8-key camelCase whitelist validator). Plan must add a scoped validator like `_validate_recommended_exercises`.
- **Hardcoding theme.** result.tsx exercise cards use `src/theme/` tokens only (#FF4B33, radius/spacing). Light theme.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM client / retry / JSON parse | New HTTP client | `CerebrasCoachWriter` (`write()` + `_normalize_entry`) | Already handles graceful fallback, JSON parse, key load. |
| Mode/branch copy plumbing | New explanation module | Extend `build_dimension_explanation` kwargs | mode-aware baseline + Largest-Remainder weight already there. |
| Findings input to mapping | Re-derive failure causes | Read `forcePatternInference.findings[]` | Phase 9 already produces Top-3 with `sourceSignal`/`jointHint`. |
| painArea input | New input form | `bodyProfile.painAreas` (Phase 3) | Already snapshotted in analysis doc + normalized server-side. |
| Modal with ScrollView | New sheet | Phase 12.5 `CoachingTipDetailModal` pattern | Documented backdrop/gesture fix. |
| Firestore validator | Loosen global validator | Add scoped `_validate_recommended_exercises` | Precedent: `_validate_force_pattern_inference` whitelist (nested-array ban preserved). |

**Key insight:** Phase 13 is ~80% wiring over existing, production-exercised structures. The novel content is the two curated fixtures (exercises + IPSF angles) — both fully sourced from NotebookLM above.

## Common Pitfalls

### Pitfall 1: Cerebras key set on Lambda but not on Pod
**What goes wrong:** Real `_process` runs on RunPod, not Lambda. Setting `CEREBRAS_KEY_PARAM` only on Lambda → `tip.detail2` stays empty in production.
**How to avoid:** Set env on the Pod + uvicorn restart; verify `/health` + run one real analysis and grep Firestore doc for `tips[].detail2`.
**Warning signs:** detail2 empty in real analysis but present in local mock.

### Pitfall 2: branch-2 move gets 180° / "세계 심사 기준" copy
**What goes wrong:** Defaulting all moves to IPSF-180° produces "세계 심사 기준" for 폭스탑 (criteria 8 fail).
**How to avoid:** Gate on `isRegistered` from the motion_ipsf fixture; branch-2 uses 정은지 measured angles from the criteria yaml (`extension_class: BENT_OK`).
**Warning signs:** ref-foxtop result says "180° 신전" or "세계 심사 기준".

### Pitfall 3: FallbackRecognizer → motion_id None → no branch / no move-specific angles
**What goes wrong:** When Gemini recognizer is off/low-confidence, `motion_id=None` → `ipsfCode` unresolved.
**How to avoid:** Graceful default = today's mode-aware baseline copy + generic exercises (no move gating). This is correct behavior (don't fabricate a branch). Document as expected.
**Warning signs:** crash on None motion_id — must be a graceful path.

### Pitfall 4: Exercise list explodes (10 painAreas × 5 defects)
**What goes wrong:** Union of all triggered exercises overwhelms the card (criteria 2 = 3~5).
**How to avoid:** Rank + dedup + cap (mirror `_rank_top3` in force_pattern.py); painArea-avoid lines prioritized for safety.

## Code Examples

### Reading Phase 9 findings + painAreas (the mapping inputs)
```python
# Source: backend/.../analysis/force_pattern.py (ForcePatternFinding fields) +
#         models.normalize_body_profile (painAreas)
# finding dict (camelCase, already in Firestore result.forcePatternInference.findings[]):
#   { "pattern", "phase", "sourceSignal", "reason", "interpretation",
#     "confidence", "jointHint", "warnings" }
# bodyProfile (snapshot): { "painAreas": ["shoulder","wrist", ...] }  # PAIN_AREAS frozenset
```

### Extending build_dimension_explanation (backward-compatible kwarg)
```python
# Source: backend/.../analysis/assemble.py:63 (current signature)
def build_dimension_explanation(
    assessments, dimension_scores, comparison,
    joint_angles=None, profile=None,
    ipsf_code: str | None = None, is_registered: bool | None = None,  # NEW (default None = today's behavior)
) -> dict[str, dict]:
    ...
    # branch: is_registered True -> "세계 심사 기준 (IPSF) + 180°"
    #         is_registered False -> "정은지 선수 기준 자세"
    #         None -> existing mode-aware baseline (backward compat)
```

### Cerebras graceful activation (already in code)
```python
# Source: backend/.../analysis/coach_writer.py:33-46, 89-105
# No code change to activate — set CEREBRAS_KEY_PARAM env + SSM param; restart uvicorn.
param_name = os.environ.get("CEREBRAS_KEY_PARAM")  # unset -> graceful {} -> numeric fallback
```

## Runtime State Inventory

> Phase 13 is mostly additive code + new fixtures, but Plan B activation touches live service config + secrets.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing Firestore `AnalysisResult` docs lack `recommendedExercises`/branch fields — frontend `normalize()` must null-guard (precedent: every prior phase). No migration of old docs needed (optional fields). | code edit (frontend null-guard) |
| Live service config | RunPod Pod env currently has NO `CEREBRAS_KEY_PARAM` (coach_writer is graceful no-op in prod today). Lambda env likewise. | API patch (Lambda env) + manual Pod env + uvicorn restart |
| OS-registered state | None — verified (no Task Scheduler/launchd refs for this phase). | none |
| Secrets/env vars | New SSM SecureString for Cerebras key (e.g. `/sunity/motion/cerebras-key`). Pod needs AWS creds (already present) to read it. | add SSM param + set `CEREBRAS_KEY_PARAM` on Lambda + Pod |
| Build artifacts | New fixtures `corrective_exercises.json` + `motion_ipsf_map.json` must be packaged into the Lambda layer / shipped to Pod (committed → `git pull` on Pod, per `gsd-pod-work-push-first`). | commit + Pod git pull |

## Common Pitfalls (contract)
- `recommendedExercises` field shape must be added to `analysis.ts` (TS interface) + `models.py` + `docs/contract.md §4` in a single atomic commit (drift tests enforce). Use camelCase in Firestore, snake_case dataclass, `_dataclass_to_camel_case_dict` conversion (existing helper).

## Validation Architecture

> nyquist_validation: enabled (no explicit false found in config — treat as on).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest `>=8,<9` (backend), `tsc --noEmit` (app) |
| Config file | none committed (pytest invoked by path); `app/tsconfig.json` strict |
| Quick run command | `python -m pytest backend/tests/phase13/ -x` |
| Full suite command | `python -m pytest backend/tests/ -q` + `cd app && npm run typecheck` |

### Phase Requirements → Test Map (criteria 1-8)
| Criterion | Behavior | Test type | Automated command | File Exists? |
|-----------|----------|-----------|-------------------|-------------|
| 1 | Exercise library fixture exists + schema-valid | unit | `pytest backend/tests/phase13/test_corrective_exercises_fixture.py -x` | ❌ Wave 0 |
| 2 | `map_exercises` returns 3~5 matched per analysis | unit | `pytest backend/tests/phase13/test_map_exercises.py -x` | ❌ Wave 0 |
| 3 | mapping uses findings + painAreas + motion | unit | `...::test_map_uses_findings_painareas_motion` | ❌ Wave 0 |
| 4 | "다른 운동 보기" library browse | manual (UI) + tsc | `cd app && npm run typecheck` + belle UAT | partial |
| 5 | real Cerebras detail2 E2E in Firestore | **Pod E2E (manual)** | run 1 real analysis on Pod, grep doc `tips[].detail2` | ❌ Pod |
| 6 | `ipsfCode` branch 1 vs 2 copy split | unit | `pytest backend/tests/phase13/test_dimension_explanation_ipsf_branch.py -x` | ❌ Wave 0 |
| 7 | coach prompt cites correct IPSF angles | unit (prompt assembly) | `pytest backend/tests/phase13/test_coach_prompt_angle_fixture.py -x` | ❌ Wave 0 |
| 8 | branch-2 avoids "세계 심사 기준" (grep gate) | unit (forbidden-phrase grep) | `...::test_branch2_no_world_judging_copy` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/phase13/ -x` (+ `tsc --noEmit` for frontend tasks)
- **Per wave merge:** `pytest backend/tests/ -q` (regression 0 — phase06/07/08/09 suites must stay green) + `npm run typecheck`
- **Phase gate:** full suite green + criteria-5 Pod E2E before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/phase13/__init__.py` + `conftest.py` + fixture loaders (mirror phase09 infra)
- [ ] `backend/tests/phase13/fixtures/` — sample `ForcePatternInference` JSON (Plan A input) + bodyProfile painAreas
- [ ] `corrective_exercises.json` + `motion_ipsf_map.json` fixtures themselves (content from §NotebookLM)
- [ ] Forbidden-phrase grep gate fixture for criteria 8 (precedent: `FORBIDDEN_PHRASES_PHASE9_REGEX`)

## Security Domain

> security_enforcement: enabled (absent in config = enabled).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (no new auth surface) | existing Firebase token auth unchanged |
| V5 Input Validation | yes | `models.normalize_body_profile` (painAreas frozenset) + new scoped Firestore validator for `recommendedExercises` |
| V6 Cryptography / Secrets | yes | Cerebras key in SSM SecureString (`WithDecryption=True`), never in code/.env (CLAUDE.md §3 / coach_writer pattern) |
| V8 Data Protection | yes | painAreas is self-input personal data — feeds mapping/coaching only, never logged with PII, never scored (D-05) |

### Known Threat Patterns for {Python Lambda + RN + Cerebras}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leak (Cerebras key in logs/code) | Information Disclosure | SSM param + `log.exception` never logs key value (existing `_load_api_key`) |
| LLM prompt injection via motion name | Tampering | motion_name from controlled recognizer enum (`REGISTERED_MOTIONS`), not free user text |
| Firestore nested-array write (rule break) | Tampering/DoS | scoped validator whitelist (precedent `_validate_force_pattern_inference`) |
| BodyProfile scoring leak | Tampering (analysis integrity) | grep-gate test + coach-context-only path (D-05) |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cerebras-cloud-sdk` | Plan B criteria 5 | ✓ (project dep) | >=1.0,<2.0 (1.67.0 latest) | graceful no-op → numeric fallback |
| Cerebras API key | criteria 5 real LLM | ✗ (not yet in SSM/Pod env) | — | numeric fallback (criteria 5 only blocker) |
| RunPod GPU Pod | criteria 5 E2E only | ⚠ ephemeral (recreate per STATE) | RTX PRO 4500 sm_120 last | code+unit tests run without Pod |
| pytest | all unit tests | ✓ | >=8,<9 | — |
| nlm (NotebookLM CLI) | D-06 research | ✓ used | 0.7.1 | — (research already done) |

**Missing dependencies with no fallback for criteria 5:** Cerebras API key in SSM + Pod env + running Pod. All other criteria (1-4, 6-8) have no Pod/key dependency.

## State of the Art
| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cerebras `llama3.1-8b` | `gpt-oss-120b` (Apache 2.0, 한국어 OK) | 2026-06-06 (404 deprecation) | coach_writer model already updated; use as-is |
| Exercise library as Firestore | committed fixture | this research | no seed/ADC step |

**Deprecated/outdated:** `llama3.1-8b` (Cerebras 404) — already replaced in `coach_writer.py:93`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A single committed JSON fixture is preferred over Firestore for the exercise library | Plan A Storage Decision | Low — Claude's discretion per CONTEXT; reversible. |
| A2 | `ipsfCode` should live in a separate derived `motion_ipsf_map.json` rather than absorbed into aka-mapping load path | Plan B ipsfCode Source | Low — both work; planner may absorb into studio-term data. |
| A3 | Cerebras key SSM path `/sunity/motion/cerebras-key` (name is illustrative) | Plan B activation | None — belle/Claude sets actual name; only `CEREBRAS_KEY_PARAM` must match. |
| A4 | NotebookLM IPSF angle numbers (e.g. Ayesha top shoulder 110°) are accurate for the fixture | NotebookLM A | Medium — these are LLM-synthesized from CoP sources; planner should have belle/NotebookLM re-confirm exact degrees per move before locking the criteria-7 fixture for registered moves. Branch-2 angles come from on-disk 정은지 measurements (already validated), lower risk. |
| A5 | `recommendedExercises` added as optional `AnalysisResult` field (backward compatible) | contract | Low — matches every prior phase's additive pattern. |

## Open Questions

1. **Exact per-move IPSF angle thresholds for registered moves (criteria 7 fixture lock).**
   - What we know: NotebookLM returned concrete degrees (§A) with CoP citations.
   - What's unclear: a few values are LLM-synthesized ranges (e.g. "top shoulder 110°"); the official CoP per-element criteria text may phrase them as descriptive (extended/flexed) not numeric.
   - Recommendation: planner adds a `checkpoint:human-verify` (belle / NotebookLM re-lookup) for the registered-move angle fixture before locking criteria 7; branch-2 정은지 measured angles need no re-verify.

2. **Which 3~5 동작군 ship in v1 exercise library.**
   - What we know: ROADMAP scope = 초기 3~5 동작군; reference library = 11 motions (STATE).
   - Recommendation: scope to the registered set with criteria yamls (ref-climb, ref-foxtop(+split), ref-invert, ref-sideway-spin) + AKA-mapped strength/flex moves (Ayesha, Iron X, Jade, Scorpio). Defect-keyed exercises are motion-agnostic, so coverage is by defect not by move — 5 defect groups cover all moves.

## Sources

### Primary (HIGH confidence)
- NotebookLM `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` — per-move IPSF hold angles + safety gates (queried 2026-06-16)
- NotebookLM `e688fb4e-a4fb-4e83-a168-9c4726a98e09` — defect/painArea exercises + LTAD (queried 2026-06-16)
- Codebase (read): `coach_writer.py`, `assemble.py`, `technique.py`, `force_pattern.py` (fields), `functions/pipeline/app.py` (coach + force_pattern wiring), `models.py` (BodyProfile/painAreas), `analysis.ts` (AnalysisResult/CoachingTip/DimensionExplanation), `result.tsx` (section order), `backend/data/aka-mapping.json`, `reference-motions-branch2.json`, `judging_data/criteria/ref-foxtop.yaml`, `docs/contract.md §4`
- PyPI registry — `cerebras-cloud-sdk` 1.67.0 (verified)

### Secondary (MEDIUM confidence)
- STATE.md / ROADMAP.md / 13-CONTEXT.md — locked decisions, Pod state, prior close-outs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; all paths grepped/read.
- Architecture: HIGH — attaches to existing, production-exercised structures.
- Exercise content: HIGH (sourced from NotebookLM, cited).
- Registered-move angle numbers: MEDIUM — re-verify before locking criteria-7 fixture (A4/Open Q1).

**Research date:** 2026-06-16
**Valid until:** ~2026-07-16 (stable; Cerebras model string + RunPod Pod URL are the only volatile inputs)

## RESEARCH COMPLETE
