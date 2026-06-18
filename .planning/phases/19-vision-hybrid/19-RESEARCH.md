# Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid 채점) - Research

**Researched:** 2026-06-18
**Domain:** 채점 집계 알고리즘 (감점식 IPSF 정합) · 표시-점수 정합 · Mode3 유효성 게이트 · 3D 골격 좌표 정규화 · known-answer 검증 아키텍처
**Confidence:** HIGH (코드 직접 확인 + IPSF 도메인 baseline + Phase 15 근본원인 + D-05 앵커 모두 in-repo)

---

<user_constraints>
## User Constraints (from 19-CONTEXT.md)

### Locked Decisions
- **D-01:** IPSF **감점식(엄격)** 으로 전환. 현재 이중 단순평균(관절→각도 평균, 차원→종합 평균)이 결함을 다수 정상 관절/차원에 희석 → 실패 영상 94점. 재설계 = 100에서 시작 → 결함마다 감점, **단일 major fault가 점수를 크게 지배**. 차원 한 개(안정성)에 휘둘리지 않는 합성. IPSF Code of Points = 감점식 baseline.
- **D-02 (v2, 본 phase에서는 비-차단 설계만):** 기하학 주도 + 비전 거부권(veto)/교차검증. 기하학이 점수 산출, 비전이 "타당한가·놓친 결함 없나" 교차검증 + 위양성 거부권. 비전이 헤드라인 점수 직접 부여 금지. 객관성·감사가능성 유지.
- **D-03:** IPSF Page 9 절대 공통 트랙 + 비전 품질 판정 + 근거 명시. 기준 동작 데이터 없어도 reference-free 절대 트랙으로 점수 주되 "**기준 동작 없음 — 절대 자세 기준 평가**" 화면 명시. "정은지와 89% 일치" 거짓 프레이밍 금지. Mode3(MODE_SELF)에 유효성/근거 게이트 신설 (not_pole 게이트는 Mode1 전용).
- **D-04:** v1/v2 분할. **v1** = 기하학 감점식 전환(D-01) + 확정 버그 수정(3D 골격 좌표 정규화 / 어깨 '안정성' 라벨 / 표시 각도값을 점수 산출값과 정합) + Mode3 게이트·근거표시(D-03). **v2** = 비전 거부권(D-02). Phase 18 eval set으로 v1 일반화 검증 후 v2 진입.
- **D-05:** 보유 fault/correct 페어를 Gemini로 비교 분석해 known-answer 검증 앵커 확보 (`19-D05-VISION-GROUNDING-SPIKE.md`). 자동 판정("94가 틀렸다")의 기준.

### Claude's Discretion
- 감점 임계값(major fault 정의) 구체 수치, 비전 거부권 발동 조건, 표시값 정합 구현 방식, 골격 좌표 정규화 위치(reshape vs viewer group) = research/plan 단계 확정. **단 D-05 경계 준수 — 보유 sweep 재calibrate 금지.**

### Deferred Ideas (OUT OF SCOPE)
- **운동 명칭 직관화** 카피 (엘보 트위스트 시스터/폭스탑/콤보 + Farmer's Walk 영문명) — 별도 phase.
- **입문/중급/고급 레벨 UI** 개선 (폴리시) — v1 폴리시 또는 별도.
- **촬영 가이드 UX** (전문가 영상 먼저 보고 비슷한 시작점 촬영) — DTW 정렬은 이미 됨, 순수 UX. 별도 검토.
- **v2 비전 거부권/교차검증** 본체 구현 — 본 phase는 v1만. v2를 막지 않는 hook/경계만 남긴다 (RQ8).
</user_constraints>

<phase_requirements>
## Phase Requirements (제안 — REQUIREMENTS.md 신설)

> 본 phase는 신규 SCORE-*/TRUST-* 요건을 제안한다. 형식은 REQUIREMENTS.md v1 섹션 "점수 신뢰도 (Scoring)" 정합 (체크박스 + ID 볼드 + 출처 인용).

| ID | Description | Research Support |
|----|-------------|------------------|
| **SCORE-06** | 종합·차원 점수가 **감점식(deduction)** 으로 집계되어 단일 major fault가 종합을 지배한다 — 이중 단순평균(`overall_score` 가중평균 + `overall_from_dimensions` 단순평균) 폐기. 100에서 시작 → IPSF 트랙(요소 0점 + 누적 실행 감점) 비율 매핑으로 감점. D-05 6 앵커(모두 fault 영상)가 채점기에서 낮은 종합점수를 받고, above-cutoff 케이스는 높게 유지된다. (출처: 19-IPSF-DEDUCTION-NOTES.md §A) | RQ1, RQ2 / kismam.overall_score, dimensions.overall_from_dimensions 교체 |
| **SCORE-07** | "Fully Extended" 요소의 micro-bent 0점 트랙 — 신전 요구 관절이 IPSF 임계(스플릿 160°=목표 180°−20° tol) 미달이면 해당 요소 무효(비례감점 아님). 임계는 IPSF 근거에서만, 보유 sweep 재calibrate 금지. (출처: §A 트랙1) | RQ2 / dimensions.line_score 임계 분기 |
| **TRUST-01** | 결과 화면 표시 각도값(현재/기준)이 점수를 산출한 DTW-정렬 median 값과 정합한다 — `_angles_to_mean_dict`(whole-clip nanmean) → DTW-정렬 source 로 교체, user matched-window vs ref full-clip 비대칭 제거. (출처: deferred-items.md §E) | RQ3 / app.py 1515-1538, 1800-1801 |
| **TRUST-02** | 어깨 차원 라벨이 'STATIC POSE ANGLE'을 'stability(떨림)'로 오인 표기하지 않으며(COACHING_FOCUS 어깨→'안정성' 정정), DIM_STABILITY(떨림)가 종합점수를 인플레하지 않는다(매끄러운 fault가 99점으로 평균 끌어올림 차단). (출처: deferred-items.md §E, CRITICAL C) | RQ4 / kismam.COACHING_FOCUS, 종합 합성식 |
| **TRUST-03** | Mode3(MODE_SELF)에 미보유동작 유효성 게이트 + 점수근거 표시 — 동작분류(IPSF등재/정은지reference/미보유) 분기 후, 미보유 시 "기준 동작 없음 — 절대 자세 기준 평가" 근거를 헤드라인에 명시. not_pole 안전망을 reference-free 절대 트랙으로도 적용. (출처: deferred-items.md "Mode 3 scoring-basis", D-03) | RQ5 / app.py MODE_SELF 분기, assemble.build_mode3 |
| **TRUST-04** | 3D 골격이 실기기에서 렌더된다 — joints3d RTMW 픽셀좌표를 골반중심 recenter + 몸통길이 정규화하여 viewer frustum 안에 들어온다. Firestore flat 저장·nested-array 금지 준수. (출처: deferred-items.md §H) | RQ6 / app.py 2327-2337 또는 joints.ts reshapePose3dData |
| **TRUST-05** (v2 hook, 비-차단) | 감점식 schema가 v2 비전 거부권 투입 지점(adapter Protocol + audit 필드)을 막지 않는다 — score 산출 후 veto/cross-check hook 자리 + dimensionScores 에 vision-flag 확장 여지. v2에서 채울 schema 슬롯만 남긴다. | RQ8 / 기존 Gemini 어댑터 패턴 |
</phase_requirements>

## Summary

Phase 15 실기기 검증에서 정은지 **fault** 영상이 Mode1 **94점/89% "거의 다 왔어요"** 로 나온 것이 본 phase의 출발점이다. 3-갈래 심층조사(deferred-items.md)가 근본원인을 **코드에서 확정**했다: 채점 철학이 **평균식(결함 희석)** 이라 프로젝트의 채점 baseline인 **IPSF Code of Points(감점식)** 와 정면으로 반대다. 구체적으로 (1) `dimensions.overall_from_dimensions` = 차원 단순평균, (2) `kismam.overall_score` = 관절 동일가중 평균(`DEFAULT_WEIGHT` 전부 1.0), (3) `score_from_deviation` = tol 20° 가우시안(느슨), (4) `DIM_STABILITY`(떨림=매끄러움)가 종합을 인플레, (5) 표시 각도값은 점수가 쓰는 DTW-정렬 median 대신 비정렬 whole-clip nanmean(게다가 user는 matched-window·ref는 full-clip 비대칭).

**v1 작업은 측정가능·결정론적**이다: 감점식 집계로 교체(D-01), 확정 버그 3건(표시-점수 정합 / 어깨 라벨·안정성 분리 / 3D 좌표 정규화), Mode3 유효성 게이트+근거(D-03). IPSF 도메인 baseline(`19-IPSF-DEDUCTION-NOTES.md`)이 임계값 출처이고, D-05 6 앵커(전부 fault, 6/6 major fault 보유)가 known-answer 검증 타깃이다 — **단 curve-fit 타깃이 아니라 sanity 앵커**다. v2 비전 거부권은 본 phase에서 **schema/hook 자리만 남기고** 구현은 Phase 18 일반화 검증 후로 미룬다.

**Primary recommendation:** `kismam.overall_score` + `dimensions.overall_from_dimensions` 두 평균 함수를 **감점식 집계**로 교체하되 — 기존 `score_from_deviation`/`assess`/`top_issues`/`motiondtw` 정렬 인프라는 재사용 — 단일 major fault 지배를 보장하는 합성식(권장: **worst-fault-anchored = 100 − Σdeductions, deduction은 per-joint 편차 임계 초과분 + line 미달 0점 트랙**)을 도입하고, 3중 계약(analysis.ts ↔ models.py ↔ contract.md)을 차원 schema 변경 시 함께 수정한다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 감점식 집계(D-01) | ML analysis core (`kismam`, `dimensions`) | pipeline `_process` 분기 | 순수 함수 — AWS/네트워크 무관, 단위테스트 가능 (CLAUDE.md "순수 함수" 원칙) |
| micro-bent 0점 트랙(SCORE-07) | ML core (`dimensions.line_score`) | technique profile(expects_extension) | 신전 요구 관절은 profile이 정함 — 기술 조건부 |
| 표시-점수 정합(TRUST-01) | pipeline (`_angles_to_mean_dict` 호출부) | — | DTW 정렬 결과(user_seg/match)는 pipeline에만 있음 |
| 어깨 라벨/안정성 분리(TRUST-02) | ML core (`kismam.COACHING_FOCUS`) + 집계 합성식 | 3중 계약 | 라벨은 상수, 인플레는 집계식 |
| Mode3 게이트+근거(TRUST-03) | pipeline (MODE_SELF 분기) | `assemble.build_mode3` 카피 + 3중 계약 | 게이트는 분석 흐름, 근거는 표시 카피 |
| 3D 골격 정규화(TRUST-04) | App (`joints.ts` reshape) **또는** backend 저장부 | viewer `<group>` | 좌표 변환 — 저장 schema vs 읽는 쪽 결정 (RQ6) |
| v2 비전 hook(TRUST-05) | adapter Protocol 경계 | pipeline 점수 산출 직후 | 기존 Gemini 어댑터 lazy-import 패턴 재사용 |

## Standard Stack

본 phase는 **신규 외부 패키지 설치 없음** — 전부 in-repo 알고리즘 수정 + 기존 의존(numpy, react-three-fiber, 기존 Gemini 어댑터) 재사용. 따라서 Package Legitimacy Audit / Standard Stack 외부 라이브러리 표는 해당 없음.

### Core (수정 대상 모듈 — 전부 기존)
| 모듈 | 역할 | 변경 |
|------|------|------|
| `backend/shared/python/sunity_shared/analysis/kismam.py` | 관절 편차→점수, 집계, 코칭 라벨 | `overall_score` 감점식 교체, `COACHING_FOCUS` 어깨 라벨 정정, `score_from_deviation` tol 재검토 |
| `backend/shared/python/sunity_shared/analysis/dimensions.py` | 차원 점수(angle/line/stability) | `overall_from_dimensions` 감점식 교체, `line_score` micro-bent 0점 트랙, stability 종합 분리 |
| `backend/functions/pipeline/app.py` | MODE_EXPERT/MODE_SELF 분기, 표시값/저장 | `_angles_to_mean_dict` 정합, MODE_SELF 게이트, joints3d 저장 정규화 결정 |
| `backend/shared/python/sunity_shared/analysis/assemble.py` | 점수근거·표시 카피 조립 | `build_mode3`/`build_dimension_explanation` 근거 카피 |
| `app/src/lib/joints.ts` | joints3d reshape | recenter+normalize (TRUST-04 선택지 A) |
| `app/src/components/PoseViewer3D.tsx` | 3D 렌더 | `<group>` transform (TRUST-04 선택지 B) |
| `app/src/types/analysis.ts` + `models.py` + `docs/contract.md` | 3중 계약 | 차원 schema/근거 필드 변경 시 동시 수정 |

### 재사용 자산 (교체 금지 — 이미 올바름)
| 자산 | 왜 재사용 |
|------|-----------|
| `kismam.score_from_deviation` / `assess` / `top_issues` | 관절별 편차→점수 인프라 — 감점식은 **집계만** 교체, 관절 편차 산출은 그대로 |
| `motiondtw.find_action_segment` + `dtw` + `per_joint_deviation`(median) | DTW 정렬 **이미 올바름** (deferred-items.md §F 확인). 표시값을 이 정렬로 바꾸면 TRUST-01 해결. **잔여 편향은 belle 우려의 반대 — DTW over-eager 정렬이 유사도를 INFLATE** (fault-high 기여) |
| `dimensions._select_window` / `line_deficits_by_joint` / `stability_wobble_by_joint` | deficit summary source — 점수 산식과 동일 window (drift 방지) |
| 기존 Gemini 어댑터 (`gemini_technique_recognizer`, `synthesis/gemini_view_reasoner`, `gemini/scene_finder`, `force_signals`, `coach_writer`) | v2 거부권 호출 패턴 재사용 (TRUST-05) |

## Architecture Patterns

### System Architecture Diagram (점수 산출 데이터 흐름 — 현재 vs 재설계)

```
영상 → frame_extract → RTMW 3D pose → angles (T, J)
                                          │
        ┌─────────────────────────────────┴──────────────────────────┐
        │ MODE_EXPERT (Mode1)                   MODE_SELF (Mode3)      │
        │  ref angles ─┐                         prev angles? ─┐       │
        │              ▼                                       ▼       │
        │   _deviation_against (DTW 정렬)         _mode3_comparison    │
        │     → deviation(J,) [점수용 median]         abs_dims         │
        │     → user_seg / a_ref [표시용]          + (prev면 angle)    │
        │              │                                       │       │
        │   ╔══════════▼═══════════╗  ← 재설계 진입 ←  ╔════════▼═════╗ │
        │   ║ 감점식 집계 (NEW)     ║              ║ 미보유 게이트 ║ │
        │   ║ 100 − Σdeductions    ║              ║ +근거 카피    ║ │
        │   ║ + line micro-bent 0  ║              ╚════════╤═════╝ │
        │   ║ + stability 분리     ║                       │       │
        │   ╚══════════╤═══════════╝                       │       │
        │              │  not_pole 게이트(Mode1)    절대트랙 게이트   │
        │              ▼                                   ▼         │
        │      ┌───────────────[ v2 hook: vision veto/cross-check ]──┐│
        │      │ (TRUST-05 자리만 — v1은 pass-through)              ││
        │      └───────────────────────┬───────────────────────────┘│
        └──────────────────────────────┼────────────────────────────┘
                                        ▼
              assemble.build_result (점수 + 근거 + joints + tips)
                                        │
                            표시값 = DTW-정렬 source (TRUST-01)
                                        ▼
              Firestore complete_analysis (flat: angles + joints3d)
                                        │   joints3d = recenter+normalize? (TRUST-04)
                                        ▼
              App result.tsx → reshapePose3dData → PoseViewer3D
```

### Pattern 1: 감점식 집계 (deduction aggregation) — D-01 핵심

**What:** 평균 대신 100에서 시작해 결함마다 빼는 누적 감점 + 요소 무효(0점) 트랙.

**IPSF 2-트랙 (19-IPSF-DEDUCTION-NOTES.md §A):**
- **트랙 1 (요소 무효 0점):** "Fully Extended" 요건 관절이 micro-bent → 비례감점 아니라 **득점 전체 0점**. 스플릿 ±20° tol → 160° 미만 = 요소 fail. → `dimensions.line_score`에 임계 분기 (현재는 부족분→가우시안 비례, 0점 트랙 없음).
- **트랙 2 (누적 실행 감점, 회당):** Clean lines/Extension/Posture −0.1~−0.2, Loss of balance −0.5, Slip −1.0, Fall −3.0, Missing element −3.0. 기술 감점 총 한도 −25.0. **평균 희석 없음.**

**0~100 매핑 (Claude's Discretion — 후보 + 트레이드오프):**

| 합성식 후보 | 단일 major 지배? | 트레이드오프 |
|-------------|------------------|--------------|
| **A. 감점합 (100 − Σ penalty)** | 부분 — 누적이라 여러 minor가 합쳐도 큰 감점 | IPSF 트랙2 직접 정합. major fault에 큰 penalty 배정 필요. **권장 baseline** |
| **B. min-of-dimension** | 강함 — 가장 나쁜 차원이 종합 | 차원이 3개뿐이라 거칠다(angle 41 → 종합 41). stability 매끄러운 fault에 약점은 해결 |
| **C. 가중 페널티 (worst-joint-weighted)** | 강함 — worst joint에 큰 가중 | tuning 위험(보유 sweep 유혹) — D-05 경계 충돌 가능 |
| **권장 조합** | — | **A(트랙2 누적 감점) + line 0점 트랙(트랙1) + stability를 종합에서 분리**. min-clamp로 단일 major가 종합을 끌어내리되 minor 누적도 반영 |

**권장 구현:**
1. `kismam.overall_score`(angle 차원): 평균 대신 **편차 임계 초과분의 누적 감점**. 예: 각 관절 `penalty_i = max(0, dev_i − tol) × k`, `angle_score = max(0, 100 − Σ penalty_i)`. 단일 큰 dev가 종합을 끌어내림(평균 희석 제거).
2. `dimensions.line_score`: 신전 요구 관절이 임계(목표−20°tol) 미달이면 그 요소 0점 처리(트랙1) → line 차원이 major fault 시 급락.
3. `dimensions.overall_from_dimensions`: 단순평균 폐기 → **감점합 또는 min-clamp** (stability 제외하고 angle/line만 종합에 직접 반영, stability는 보조 표시).

**When to use:** 모든 점수 산출 경로 (Mode1 종합, Mode3 절대 트랙).

**Anchor 검증 (curve-fit 아님):** D-05 climb(등 말림 line ~25°), kip-up(무릎 ~35° angle) → line/angle 차원이 지배해 종합이 낮아야 정상. 6/6 fault가 낮은 점수면 PASS, above-cutoff(미보유 고득점)도 별도 검증.

### Pattern 2: 표시-점수 정합 (TRUST-01)

**What:** 표시 각도(현재/기준)를 점수가 쓰는 DTW-정렬 median으로 통일.

**근본원인 (deferred-items.md §E 확정):**
- 표시값 = `_angles_to_mean_dict`(app.py:1515-1538) = **whole-clip np.nanmean** (점수는 `motiondtw` per-joint **median**).
- 게다가 비대칭: user 측 = DTW-matched sub-window(`user_seg`) mean, ref 측 = **전체 ref clip**(`a_ref`) mean (app.py:1800-1801). 시간 범위 불일치 + mean의 jitter/occlusion 민감성 → "시각적으로 동일한데 19° 차이".

**구현 위치:** pipeline `_process` MODE_EXPERT 분기. `_angles_to_mean_dict(user_seg)` / `_angles_to_mean_dict(a_ref)` 를 **DTW path-정렬된 동일 구간**의 median으로 교체. `match.path`가 정렬 대응을 가지므로 user_seg와 a_ref를 path로 매핑한 후 median (점수 경로 `per_joint_deviation`가 이미 하는 방식 재사용). Mode3 progress 경로(`_mode3_comparison`의 `ref_mean = _angles_to_mean_dict(prev_seg)`)도 동일.

### Pattern 3: Mode3 미보유동작 게이트 + 근거 (TRUST-03 / D-03)

**What:** MODE_SELF에 유효성 게이트 + "기준 동작 없음 — 절대 자세 기준 평가" 근거 표시.

**현황 (deferred-items.md 확정):** `not_pole_motion` 게이트(app.py:1812)는 **MODE_EXPERT 안에만** 있다 — 정은지 ref 유사도 기반이라 reference-independent MODE_SELF에는 적용 불가. 그래서 Mode3는 **어떤 영상이든**(비폴 포함) confident 97점 출력.

**belle 타깃 설계 (3분기, deferred-items.md):**
1. IPSF 등재 동작 → IPSF 기준 판정 + 근거 설명 + 발전 비교.
2. IPSF 비등재지만 정은지 reference 보유 → 정은지 비교 + 근거 + 발전.
3. 둘 다 아님(미보유) → **유효성 게이트/불확실 플래그** — confident 점수 금지(현재는 1/2처럼 97 출력).

**기존 인프라 재사용:** `assemble.lookup_motion_branch(motion_id)` → `MotionBranchInfo`(copyBranch=branch1_ipsf_registered / branch2_eunji_reference / 안전기본). 이미 카피 분기 라우팅 존재 — **현재는 카피/프롬프트 분기 전용, 채점 미진입**. TRUST-03은 이 branch를 MODE_SELF **게이트**에 연결 + `build_mode3`에 근거 카피 추가. 안전기본(`_SAFE_DEFAULT_BRANCH`)이 fail-closed 아님 정신([[motion-routing-generalize-principle]]) 준수 — 미지 동작에 raise 금지, 절대 트랙으로 점수 주되 근거 명시.

**reference-free 절대 트랙 (IPSF-DEDUCTION-NOTES §B):** 기술 감점 트랙은 특정 요소 성공과 무관하게 모든 움직임에 적용 → 기준 없어도 자세 품질 절대 평가. line(신전 완성도) + stability + posture가 절대 트랙. 미보유 동작은 이 절대 감점표로 채점 + 화면 근거 명시.

### Pattern 4: 3D 골격 좌표 정규화 (TRUST-04)

**What:** joints3d를 골반중심 recenter + 몸통길이 정규화하여 viewer frustum 안으로.

**근본원인 (deferred-items.md §H 확정):** joints3d는 **RAW RTMW 픽셀좌표**(x,y ~0-640 uncentered, z MotionBert-scale) — pole_aligned 회전만 하고 recenter/rescale 안 함(app.py:2327-2337). Viewer는 distance 3, fov 50, sphere r=0.04 — **normalized origin-centered** 기대(PoseViewer3D.tsx). 실제 골격 중심 ~(320,240,z), 수백 단위 spread → frustum 밖 → GL이 #F5F5F5로 clear = 빈 회색. smoke 화면은 hand-authored normalized 좌표라 "동작"했음.

**구현 선택지 (Claude's Discretion):**
| 위치 | 장점 | 단점 |
|------|------|------|
| **A. 저장 시 정규화 (app.py:2327-2337)** | 한 번만 계산, Firestore 작게, 읽는 쪽 단순 | 기존 doc 재계산 불가(과거 분석 영향), space enum 변경 시 3중 계약 |
| **B. 읽는 쪽 (joints.ts reshapePose3dData)** | 과거 doc도 즉시 고침, backend 불변 | 매 렌더 계산(미미), reshape 함수에 normalize 책임 추가 |
| **C. viewer `<group>` transform** | 렌더 레이어 격리 | per-frame hip 중심이 달라 group 단일 transform 부족 — frame별 recenter 필요 |

**권장:** **B (joints.ts)** — 과거 분석 doc도 즉시 렌더되고 backend·계약 불변(가장 안전). recenter = 각 frame의 hip midpoint(left_hip+right_hip)/2 빼기, normalize = torso length(shoulder_mid↔hip_mid 거리)로 나누기. Firestore flat 저장·nested-array 금지 제약은 reshape 단계에서 처리(이미 flat→3D reshape하는 함수라 정규화 추가가 자연스러움).

### Anti-Patterns to Avoid
- **보유 sweep 재calibrate:** D-05 경계 — 6 페어 실제 출력에 임계값을 맞추는 것 금지. 임계는 IPSF 근거에서만([[calibration-source-hard-gate]] [[scoring-redesign-must-generalize-no-overfit]]).
- **사람 점수 라벨 ground-truth:** belle/강사/심사자 점수 라벨 영구 금지([[analysis-objectivity-no-human-scores]]). 임계값/감점 수치 라벨링은 OK.
- **3중 계약 한쪽만 수정:** 차원/근거 schema 변경 시 analysis.ts + models.py + contract.md 동시.
- **stability를 종합 인플레:** 매끄러운 fault가 99점 → 종합 끌어올림. stability는 보조 표시, 종합 직접 반영 금지(TRUST-02).
- **DTW 정렬을 "버그"로 오인:** 정렬은 이미 올바름. 잔여 편향은 over-eager 정렬이 유사도 INFLATE — fault-high 기여(채점기 보수성으로 상쇄).
- **미보유 동작 fail-closed/raise:** 안전기본은 점수 주되 근거 명시([[motion-routing-generalize-principle]]).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 시간 정렬 | 새 DTW/정렬 | `motiondtw` (find_action_segment + banded dtw + global fallback) | 이미 올바름, 검증됨 (deferred §F) |
| 관절 편차→점수 | 새 매핑 | `kismam.score_from_deviation` / `assess` | 감점식은 **집계만** 교체 |
| deficit summary source | 별도 window 계산 | `dimensions._select_window` 공유 helper | drift 방지 (Codex v3 HIGH-2) |
| 동작 분기 라우팅 | 새 boolean | `assemble.lookup_motion_branch` → MotionBranchInfo | copyBranch 라우팅 이미 존재 |
| weightPercent 합 100 | 반올림 직접 | `assemble._largest_remainder_pct` | 33×3=99 버그 방지 |
| Gemini 호출(v2) | 새 클라이언트 | 기존 어댑터 lazy-import 패턴 | adapter Protocol 경계 정합 |

**Key insight:** 본 phase는 **새 인프라가 아니라 집계 철학 교체**다. 편차 산출·정렬·deficit source는 전부 정확 — 평균이 결함을 희석하는 **집계 단계**만 감점식으로 바꾼다.

## Runtime State Inventory

> rename/refactor 아님 (알고리즘 + schema 변경). 단 **schema 변경이 기존 Firestore doc에 미치는 영향**이 runtime state에 해당하므로 명시.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 기존 `users/{uid}/analyses/{id}.result.dimensionScores` / `overallScore` = 평균식으로 산출된 과거 점수. joints3d = raw 픽셀좌표(정규화 안 됨). | **데이터 마이그레이션 불필요** — 과거 doc 재분석 강제 안 함(파일럿). joints3d 정규화를 **읽는 쪽(joints.ts)** 에 두면 과거 doc도 즉시 렌더(권장 B). 저장 쪽 정규화(A) 선택 시 과거 doc은 여전히 raw → 읽는 쪽 fallback 필요. |
| Live service config | 없음 — Lambda env(RUNPOD_ANALYZE_URL 등) 변경 없음. | None — 검증: 본 phase는 알고리즘/앱 코드만. |
| OS-registered state | 없음. | None. |
| Secrets/env vars | v2 비전(deferred)은 Gemini 키 필요 — 이미 Parameter Store/Pod env 주입됨. v1은 신규 secret 없음. | None for v1. |
| Build artifacts | 3중 계약(analysis.ts/models.py/contract.md) 변경 시 앱 EAS 재빌드 + Lambda SAM 재배포 필요(차원 schema 바뀌면). | schema 변경 task에 재빌드/재배포 명시. `sam build --use-container` 필수. |

**핵심 질문 답:** schema 미변경 시(집계식만 교체) 과거 doc은 그대로 읽힌다(점수 필드 동일). 차원 추가/근거 필드 추가 시 옵셔널로 선언(이전 빌드 doc 호환 — dimensionExplanation 패턴 정합).

## Common Pitfalls

### Pitfall 1: 보유 셋 overfit (curve-fit)
**What goes wrong:** 6 페어 실제 점수를 보고 "94→낮게" 나오도록 임계값을 맞춤 → 미보유 동작에서 깨짐.
**Why:** D-05 앵커가 너무 구체적이라 타깃화 유혹.
**How to avoid:** 임계는 IPSF 근거(160° 스플릿, ±20° tol, 감점표)에서만 도출. 6 페어는 **방향 검증**(fault가 낮은가)이지 수치 타깃 아님. above-cutoff/미보유 케이스 동시 검증([[sensitivity-gate-not-just-elite-low]]).
**Warning signs:** 임계값이 IPSF 문서가 아니라 sweep 결과에서 나옴; 6 페어만 통과하고 합성 above-cutoff 실패.

### Pitfall 2: stability 분리하다 contract 깨짐
**What goes wrong:** DIM_STABILITY를 종합에서 빼면 dimensionScores 키/순서/delta 계약이 어긋남.
**Why:** 3중 계약 + Mode3 deltaFromPrevious가 절대 차원(line/stability)에 의존.
**How to avoid:** stability를 **표시는 유지하되 종합 합성식 입력에서만 제외**. dimensionScores 키는 보존, `overall_from_dimensions` 입력만 변경. Mode3 delta는 절대 차원 유지([[mode3-progress-not-similarity]]).

### Pitfall 3: 3D 정규화 위치 혼란 (저장 vs 읽기)
**What goes wrong:** 저장 쪽 정규화(A)하면 과거 doc은 여전히 raw → 일부 blank 유지.
**How to avoid:** 읽는 쪽(B) 권장 — 모든 doc 일관. 저장 쪽 선택 시 reshape에 raw-detect fallback.
**Warning signs:** 새 분석은 보이는데 과거 기록 화면 골격 blank.

### Pitfall 4: micro-bent 0점 트랙이 정상 동작 위양성
**What goes wrong:** 모든 굽은 무릎을 0점 처리 → 의도적 굽힘(chair pose) 위양성 → 41점 재현.
**Why:** line 차원이 기술 조건부인데 0점 트랙을 무조건 적용.
**How to avoid:** `profile.expects_extension(joint)` True인 관절만 0점 트랙(이미 line_score가 expects_extension로 필터). 의도적 굽힘은 평가 제외 유지.

### Pitfall 5: Mode3 게이트가 정은지 reference를 prev로 오인
**What goes wrong:** MODE_SELF가 mode1 분석을 prev로 잡음.
**Why:** 과거 함정(2026-06-07 belle fix). `get_previous_analysis(mode=MODE_SELF)`로 같은 mode만 검색 — 유지.

## Code Examples

### 감점식 집계 (권장 baseline — angle 차원, kismam.overall_score 교체)
```python
# Source: 설계 (IPSF-DEDUCTION-NOTES §A 트랙2 누적 감점 + 단일 major 지배)
# 현재: num = sum(a.score * w[a.key]); return num/den  ← 평균(희석)
def overall_score_deductive(
    assessments: list[JointAssessment],
    tol_deg: float = _IPSF_TOLERANCE_DEG,
    penalty_per_deg: float = 2.0,  # IPSF 근거 매핑 — 보유 sweep 아님
) -> int:
    """100에서 시작 → 관절별 (편차 − tol) 초과분 누적 감점. 단일 큰 편차가 지배."""
    total_penalty = 0.0
    for a in assessments:
        over = max(0.0, a.deviation_deg - tol_deg)
        total_penalty += over * penalty_per_deg
    return max(0, min(100, int(round(100.0 - total_penalty))))
```

### micro-bent 0점 트랙 (dimensions.line_score 분기 추가)
```python
# Source: 설계 (IPSF-DEDUCTION-NOTES §A 트랙1 — 비례감점 아닌 요소 0점)
_SPLIT_FAIL_THRESHOLD_DEG = 160.0  # 180° 목표 − 20° tol (IPSF), curve-fit 아님
# line_score 안: 신전 요구 관절이 임계 미달이면 그 요소 0점 (현재는 부족분→가우시안)
for k in extend_joints:
    rep_angle = float(rep[JOINT_KEYS.index(k)])
    if rep_angle < _SPLIT_FAIL_THRESHOLD_DEG:
        return 0  # 요소 무효 — 비례감점 아님 (트랙1)
```

### 종합 = stability 분리 (dimensions.overall_from_dimensions 교체)
```python
# Source: 설계 (TRUST-02 — 매끄러운 fault stability 99 인플레 차단)
def overall_from_dimensions_deductive(dimension_scores: dict[str, int]) -> int:
    """angle/line 만 종합 산출 입력. stability 는 표시만(인플레 차단).
    min-clamp 로 단일 major 차원이 종합을 끌어내림."""
    core = [v for k, v in dimension_scores.items() if k in (DIM_ANGLE, DIM_LINE)]
    if not core:
        return dimension_scores.get(DIM_STABILITY, 0)  # 절대트랙 단독 fallback
    return min(core)  # 또는 100 − Σ(100−v) clamp — major 지배
```
> 합성식(min vs 감점합)은 plan에서 6 앵커 방향검증 + above-cutoff로 확정. min은 단일 major 강하게 지배(거칠), 감점합은 누적 minor도 반영(부드러움). **권장: angle은 감점합(관절 다수), 종합은 min-of-core(차원 소수)** 하이브리드.

### v2 비전 hook 자리 (TRUST-05 — 비-차단)
```python
# Source: 설계 — v1은 pass-through, v2가 채울 슬롯만
# pipeline _process: 감점식 점수 산출 직후
score_result = {"overall": overall, "dims": dimension_scores}
# v2 hook (Phase 19 v2 / 후속): vision veto/cross-check. v1 = identity.
score_result = _apply_vision_veto(score_result, local_video_path, angles)  # v1 no-op
# _apply_vision_veto 는 adapter Protocol — _gemini_vision_enabled() OFF 시 입력 그대로 반환
```

## State of the Art

| Old Approach | Current Approach (재설계) | When Changed | Impact |
|--------------|---------------------------|--------------|--------|
| 차원 단순평균 종합 | 감점식 + min-of-core(stability 분리) | Phase 19 v1 | fault가 낮은 점수 — 신뢰 회복 |
| 관절 동일가중 평균 | 편차 임계 초과분 누적 감점 | Phase 19 v1 | 단일 major 지배(IPSF 정합) |
| line = 부족분 가우시안 비례 | micro-bent 0점 트랙(트랙1) + 부족분(트랙2) | Phase 19 v1 | 신전 미달 요소 무효 |
| 표시값 whole-clip nanmean(비대칭) | DTW-정렬 median(점수와 동일 source) | Phase 19 v1 | 표시-점수 모순 제거 |
| Mode3 게이트 없음(어떤 영상도 97) | 미보유 게이트 + 절대트랙 근거 | Phase 19 v1 | 미보유 동작 거짓 점수 차단 |
| joints3d raw 픽셀(blank) | hip-center recenter + torso normalize | Phase 19 v1 | 실기기 골격 렌더 |

**Deprecated/outdated:**
- `kismam.DEFAULT_WEIGHT` 전부 1.0 동일가중 평균 — 감점식으로 대체(weight는 checkpoint 중요도로 재해석 가능).
- "거의 다 왔어요" 헤드라인(`build_result` angle≥95) — fault에서 발화 금지(deferred CRITICAL D).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `penalty_per_deg=2.0` 등 구체 감점 계수 | Code Examples | [ASSUMED] 예시값 — IPSF 비율 매핑은 plan에서 6 앵커 방향검증으로 확정. curve-fit 금지. 계수가 너무 크면 정상 동작 위양성, 너무 작으면 fault 안 잡힘 |
| A2 | min-of-core 종합 합성식이 감점합보다 단일 major 지배에 적합 | Pattern1/Code | [ASSUMED] — min은 거칠고 감점합은 부드러움. plan에서 above-cutoff 케이스로 비교 확정 |
| A3 | joints3d 정규화는 읽는 쪽(B, joints.ts)이 최선 | Pattern4 | [ASSUMED] 권장 — 저장 쪽(A)도 유효. 과거 doc 호환이 결정 요인 |
| A4 | torso length = shoulder_mid↔hip_mid 거리로 normalize | Pattern4 | [ASSUMED] — 표준 정규화. occlusion으로 hip 누락 시 fallback 필요 |
| A5 | stability를 종합에서 빼도 Mode3 delta 계약 안 깨짐 | Pitfall2 | [ASSUMED] — delta는 절대차원 유지하므로 OK로 판단, plan에서 계약 재확인 |
| A6 | SCORE-07 스플릿 임계 160° = 180°−20° tol 매핑 | SCORE-07 | [CITED: 19-IPSF-DEDUCTION-NOTES.md §A] — IPSF 근거. RTMW 측정 각도가 IPSF 정의(발목뼈→골반뼈 일직선)와 정합하는지는 측정 검증 필요 |

**확인 필요:** A1/A2 감점 계수·합성식은 plan/discuss에서 user 확인 또는 6 앵커 방향검증으로 잠가야 함 — curve-fit 경계 때문에 특히 민감.

## Open Questions

1. **감점 계수·합성식 구체값 (A1/A2)**
   - 알고 있음: IPSF 트랙2 감점 구조 + 6 앵커 fault 방향 + 단일 major 지배 요구.
   - 불확실: 0~100 정확한 매핑 계수, min vs 감점합, line 0점 트랙 임계의 RTMW 측정 정합.
   - 권장: plan에서 IPSF 근거로 초기값 → 6 앵커 **방향**(fault<정상) + 합성 above-cutoff(정상 동작 고득점 유지)로 검증. **보유 sweep 재calibrate 금지** — 방향만 본다.

2. **RTMW 측정 각도 vs IPSF 정의 정합 (A6, deferred §E)**
   - 알고 있음: 어깨각 = 3D 벡터각(geometrically valid, camera-invariant). belle가 "시각적으로 정은지와 동일한데 19° flag" 봄 — 근본은 표시 artifact(TRUST-01)지 측정 버그 아님.
   - 불확실: line 0점 트랙의 160° 임계가 RTMW 측정 스케일과 정합하는가(IPSF는 발목뼈→골반뼈 일직선=180°, RTMW 무릎각 측정이 동일 의미?).
   - 권장: plan에서 D-05 앵커의 ~각도(무릎 ~35° 굽음 등)와 RTMW 실측을 Pod 재개 후 대조(현재 GPU 없음 — JSON 앵커는 그때 자동판정 기준).

3. **Pod/GPU 가용성 (정량 검증 차단 요인)**
   - 알고 있음: D-05 앵커는 정성 ground-truth(점수 라벨 없음). 채점기 실제 출력 정량 대조는 RTMW GPU 필요.
   - 불확실: belle 크레딧 충전 + 새 Pod 시점.
   - 권장: v1 알고리즘 + 단위테스트(synthetic angles)는 GPU 없이 진행. 실영상 정량 검증은 Pod 재개 후 게이트.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| numpy | 감점식 알고리즘 | ✓ (in-repo) | >=1.26 | — |
| pytest | 검증 (단위) | ✓ | >=8,<9 | — |
| RTMW GPU (RunPod Pod) | 실영상 정량 검증 | ✗ (크레딧/Pod 없음) | — | synthetic angles 단위테스트로 알고리즘 검증, 실영상은 Pod 재개 후 |
| Gemini API (gemini-3.1-pro-preview) | v2 비전 거부권 (deferred) | ✓ (키 주입됨) | — | v1 미사용 |
| react-three-fiber / drei / expo-gl | 3D 골격 렌더 (앱) | ✓ (in-repo) | — | — |

**Missing dependencies with no fallback:** 없음 (v1 핵심은 GPU 불필요 — synthetic angles로 결정론적 검증).
**Missing dependencies with fallback:** RTMW GPU — synthetic 단위테스트로 알고리즘 검증, 실영상 정량 대조는 Pod 재개 게이트.

## Validation Architecture

> nyquist_validation 기본 enabled (config 미확인 시 enabled 취급).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config file | `backend/tests/conftest.py` (존재). pytest.ini 없음 — conftest + sys.path 패턴 |
| Quick run command | `cd backend && python -m pytest tests/test_kismam.py tests/test_dimensions.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |
| App typecheck | `cd app && npm run typecheck` (tsc --noEmit — 유일한 정적 게이트) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-06 | 감점식 — 단일 major fault가 종합 지배 (한 관절 큰 편차 → 종합 급락, 평균 희석 안 됨) | unit | `pytest backend/tests/test_kismam.py::test_single_major_fault_dominates -x` | ❌ Wave 0 |
| SCORE-06 | above-cutoff: 모든 관절 정상(편차<tol) → 종합 high (위양성 없음) | unit | `pytest backend/tests/test_kismam.py::test_clean_pose_high_score -x` | ❌ Wave 0 |
| SCORE-07 | 신전 요구 관절 160° 미달 → line 차원 0점(요소 무효, 비례감점 아님) | unit | `pytest backend/tests/test_dimensions.py::test_micro_bent_zero_track -x` | ❌ Wave 0 |
| SCORE-07 | 의도적 굽힘(expects_extension False) 관절은 0점 트랙 미적용(위양성 차단) | unit | `pytest backend/tests/test_dimensions.py::test_intentional_bend_not_penalized -x` | ❌ Wave 0 |
| TRUST-01 | 표시 각도 = 점수 산출 source(DTW-정렬 median), user/ref 동일 구간 | unit | `pytest backend/tests/test_pipeline_mode3.py::test_display_matches_score_source -x` | ✅(파일) ❌(케이스) |
| TRUST-02 | DIM_STABILITY 높아도 angle/line 낮으면 종합 낮음(stability 인플레 안 됨) | unit | `pytest backend/tests/test_dimensions.py::test_stability_does_not_inflate -x` | ❌ Wave 0 |
| TRUST-02 | 어깨 COACHING_FOCUS 라벨이 'STATIC POSE' 의미로 정정(‘안정성’ 오인 제거) | unit | `pytest backend/tests/test_kismam.py::test_shoulder_focus_label -x` | ❌ Wave 0 |
| TRUST-03 | MODE_SELF 미보유 동작 → confident 점수 대신 근거 플래그 + 절대트랙 | unit | `pytest backend/tests/test_pipeline_mode3.py::test_unknown_move_gate -x` | ✅(파일) ❌(케이스) |
| TRUST-04 | reshapePose3dData가 hip-center recenter + torso normalize → origin-centered 좌표 반환 | unit(앱) | `cd app && npm run typecheck` + jest 없음 → reshapePose3dData 순수함수 수동검증/RN 부재 | ⚠ 앱 JS 테스트 러너 없음 |
| TRUST-05 | v1 vision hook이 pass-through(점수 불변), OFF 시 입력 그대로 | unit | `pytest backend/tests/test_pipeline_*.py::test_vision_hook_passthrough -x` | ❌ Wave 0 |

### Known-Answer Anchor Validation (D-05 — Pod 재개 후 게이트)
| Anchor | Expected (방향, curve-fit 아님) | Test |
|--------|-------------------------------|------|
| climb (등 말림 line ~25°) | line 차원 지배 → 종합 낮음. fault < correct | Pod 재개 후 `pytest backend/tests/test_anchor_known_answer.py::test_climb_fault_lower` (GPU 필요 — skip marker) |
| kip-up (무릎 ~35° angle) | angle 차원 지배 → 종합 낮음 | 동상 |
| 6/6 fault | 모두 종합 낮음(94 같은 위양성 0건) | 6 페어 parametrize |
| above-cutoff (미보유 고득점) | 정상 동작 high 유지(sensitivity gate) | synthetic above-cutoff angles |

> 앵커는 **방향 판정**(fault<정상 + major 차원 지배)이지 점수 수치 타깃 아님([[calibration-source-hard-gate]]).

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_kismam.py tests/test_dimensions.py -x` (+ `npm run typecheck` for 앱 task)
- **Per wave merge:** `pytest backend/tests/ -q` (full backend suite)
- **Phase gate:** Full suite green + D-05 앵커 방향검증(Pod 재개 시) 전 `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_kismam.py` — SCORE-06(single_major_fault_dominates, clean_pose_high_score) + TRUST-02(stability_does_not_inflate, shoulder_focus_label) 케이스 추가
- [ ] `backend/tests/test_dimensions.py` — SCORE-07(micro_bent_zero_track, intentional_bend_not_penalized) + TRUST-02 케이스 추가
- [ ] `backend/tests/test_pipeline_mode3.py` — TRUST-01(display_matches_score_source) + TRUST-03(unknown_move_gate) 케이스 추가
- [ ] `backend/tests/test_anchor_known_answer.py` — D-05 6 앵커 방향검증 (GPU skip marker — Pod 재개 후 활성)
- [ ] 앱 JS 테스트 러너 부재: reshapePose3dData(TRUST-04) 단위테스트 인프라 없음 → 순수함수라 jest 도입 검토 또는 typecheck + 수동 device 검증. **Pre-existing**: `app/`에 JS test runner 미설정(CLAUDE.md: "no JS test runner configured")
- [ ] **Pre-existing 실패 격리** (deferred-items.md): test_pole_detector(fixtures ImportError), test_pipeline_geminid_wiring, test_spike_gemini_moment_smoke — 본 phase 무관, 회귀 판정에서 제외(isolation 실행)

## Security Domain

> 본 phase는 점수 알고리즘 + 앱 렌더 — 인증/세션/네트워크 신규 표면 없음. 기존 Firebase 토큰 auth + Firestore 규칙 불변.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 기존 Firebase anonymous + ID token (불변) |
| V3 Session Management | no | 불변 |
| V4 Access Control | no | Firestore 규칙 불변 (점수 schema만 변경) |
| V5 Input Validation | yes | RTMW angles → `_as_tj` shape 검증(이미 있음), joints3d finite-only(nan_to_num, 이미 있음), normalize 시 0-div 가드 추가 |
| V6 Cryptography | no | 해당 없음 |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| NaN/Inf 좌표 → viewer crash | DoS(렌더) | nan_to_num(이미) + normalize 0-div 가드(torso=0 fallback) |
| 미보유 동작 거짓 confident 점수 | (신뢰성/Information) | TRUST-03 유효성 게이트 + 근거 명시 |

## Sources

### Primary (HIGH confidence — in-repo, 직접 확인)
- `.planning/phases/19-vision-hybrid/19-CONTEXT.md` — D-01~D-05 locked decisions, scope, canonical refs
- `.planning/phases/19-vision-hybrid/19-IPSF-DEDUCTION-NOTES.md` — IPSF 2트랙 감점식, 160° 스플릿, 감점표, 미보유 절대트랙
- `.planning/phases/19-vision-hybrid/19-D05-VISION-GROUNDING-SPIKE.md` — 6 페어 known-answer 앵커(전부 major fault, 라인/신전 붕괴)
- `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md` — 근본원인 확정(평균식 vs IPSF 감점식 / 표시 artifact / DTW 이미 OK / joints3d 좌표 버그 / Mode3 게이트 부재)
- `backend/shared/python/sunity_shared/analysis/kismam.py` — overall_score 평균, score_from_deviation tol 20°, COACHING_FOCUS 어깨 라벨
- `backend/shared/python/sunity_shared/analysis/dimensions.py` — overall_from_dimensions 단순평균, line_score 비례 부족분(0점 트랙 없음), DIM_STABILITY
- `backend/functions/pipeline/app.py` — MODE_EXPERT(1740-1838, not_pole 1812), MODE_SELF(1839), _angles_to_mean_dict(1515-1538), _deviation_against(1557-1569), 비대칭(1800-1801), joints3d 저장(2318-2342)
- `backend/shared/python/sunity_shared/analysis/assemble.py` — build_mode1/mode3/dimension_explanation, lookup_motion_branch, _SAFE_DEFAULT_BRANCH
- `app/src/lib/joints.ts` — reshapePose3dData (정규화 추가 후보 위치)
- `app/src/types/analysis.ts` + `models.py` — AnalysisResult/dimensionScores 3중 계약
- `.planning/REQUIREMENTS.md` — SCORE-04/05 형식, v1 점수 신뢰도 섹션

### Secondary (MEDIUM — 메모/도메인)
- MEMORY: [[judging-baseline-ipsf-code-of-points]], [[scoring-redesign-must-generalize-no-overfit]], [[calibration-source-hard-gate]], [[sensitivity-gate-not-just-elite-low]], [[mode3-progress-not-similarity]], [[motion-routing-generalize-principle]], [[analysis-objectivity-no-human-scores]], [[mode3-scoring-basis-unknown-move-gate]]

## Metadata

**Confidence breakdown:**
- 감점식 설계(집계 교체 위치/구조): HIGH — 코드에서 정확한 함수·라인 확인, IPSF baseline in-repo
- 구체 감점 계수/합성식: MEDIUM — 예시값(ASSUMED), curve-fit 경계로 plan 확정 필요
- 표시-점수 정합/3D 정규화/Mode3 게이트(버그 3건+게이트): HIGH — deferred-items.md가 근본원인을 코드에서 확정
- 검증 아키텍처: HIGH(단위) / MEDIUM(실영상 — GPU 차단)

**Research date:** 2026-06-18
**Valid until:** 2026-07-18 (in-repo 알고리즘 안정 — 단 Pod 재개 시 실영상 정량 검증으로 보강)
