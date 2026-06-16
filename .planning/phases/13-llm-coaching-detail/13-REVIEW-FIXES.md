# Phase 13 Review Fixes — Supersession Ledger

> 이 문서는 두 plan(`13-A`, `13-B`)의 `<read_first>` 에서 `13-RESEARCH.md` **이전에** 읽는다.
> 충돌 시 우선순위: **본 문서 > plan `<action>` > `13-RESEARCH.md`**.
> 목적: 1차/2차 direct-review 에서 뒤집힌 RESEARCH 가이드를 실행 에이전트가 다시 도입하지 않게 한다.

작성: 2026-06-16 · 출처: `13-DIRECT-REVIEW.md`(iteration 1) + `13-DIRECT-REVIEW-ITERATION2.md`(iteration 2)

---

## 1. motion_ipsf_map 은 curated, derived 아님 (1차 BLOCKER-1)

RESEARCH §"ipsfCode Source"(L237-238) 은 `motion_ipsf_map.json` 을 aka-mapping.json + reference-motions-branch2.json 에서 **derived(자동 생성)** 하라고 권한다 — **superseded**.

- `motion_ipsf_map.json` 은 **명시 curated join table** 이다. 각 production `motion_id` 마다 사람이 검토한 라우팅 결정 + 근거(`sourceNote`)를 박제한다.
- aka-mapping.json 은 `motionId` 키가 없고 display name 만 있으므로 자동 join 은 잘못된 매핑을 만든다. derive 금지.

## 2. 라우팅 = copyBranch + angleSource + angleFixtureKey (2차 BLOCKER-1 / HIGH-1)

RESEARCH(L302-307) 과 1차 patch 의 단일 `isRegistered` boolean 은 **superseded**. 단일 boolean 으로 카피 분기와 각도 소스를 **둘 다** 라우팅할 수 없다 — 둘은 직교(orthogonal)다. 현재 production 5 동작이 실제로 이 케이스를 섞는다.

`motion_ipsf_map.json` 엔트리 스키마(per id):

| field | type | 의미 |
|-------|------|------|
| `copyBranch` | `branch1_ipsf_registered \| branch2_eunji_reference \| unknown` | 차원 자세히 카피 분기 |
| `ipsfCode` | string \| null | IPSF 코드(있으면) |
| `officialName` | string | 표시 동작명 |
| `angleSource` | `ipsf_registered_fixture \| eunji_measured_yaml \| no_angle_criterion \| unavailable` | coach 프롬프트 각도 출처 |
| `angleFixtureKey` | string \| null | 각도 lookup 키(registered_move_angles.angles[key] 또는 criteria/{key}.yaml) |
| `criteriaYaml` | string \| null | 분기2/측정값 yaml 파일명 |
| `sourceNote` | string (non-empty 필수) | 라우팅 결정 근거 |

룩업 함수: `lookup_motion_ipsf(...) -> tuple[str|None, bool|None]` 은 **superseded** →
`lookup_motion_branch(motion_id) -> MotionBranchInfo`. **MotionBranchInfo = `@dataclass(frozen=True)`** (3차 MEDIUM-2 — dict 아님, attribute 접근 `branch_info.copyBranch` 일관). 필드: `copyBranch: str, ipsfCode: str|None, officialName: str, angleSource: str, angleFixtureKey: str|None, criteriaYaml: str|None, sourceNote: str`. assemble.py(또는 인접 fixture helper)에 정의. app.py / assemble.build_result / assemble.build_dimension_explanation / coach_writer 가 모두 이 dataclass 를 소비(bare boolean 아님, dict 아님).

### Fail-closed: 현재 5 production id 는 `copyBranch:"unknown"` 으로 ship 불가

`unknown` 은 미래/신규 id 전용. 현재 5 id 중 진짜 ambiguous 한 게 있으면 Task 1 blocking human checkpoint 로 보낸다(checkpoint 없이 unknown ship 금지).

### 현재 5 production 동작 라우팅 (yaml evidence 로 확정 — Plan B Task 2 박제)

| motion_id | copyBranch | ipsfCode | officialName | angleSource | angleFixtureKey | criteriaYaml | yaml 근거 |
|-----------|-----------|----------|--------------|-------------|-----------------|--------------|-----------|
| `ref-invert` | `branch1_ipsf_registered` | `BODY_POSITION_INVERTED` | Body Position Inverted | `eunji_measured_yaml` | `ref-invert` | `ref-invert.yaml` | `ref-invert.yaml` L9,L17: "IPSF Body Position Inverted (등재)" but joint-angle 채점은 정은지 측정값(Body Position 차원 = D-19 별 phase deferred) |
| `ref-climb` | `branch1_ipsf_registered` | `TRANSITIONS_AND_CLIMBS` | Transitions & Climbs | `no_angle_criterion` | null | null | `ref-climb.yaml` L8-21: IPSF Transitions & Climbs 카테고리, hold_moment=[] 의도된 빈 list, 해부학적 각도 target 없음(Repetition/Flow 패러다임) |
| `ref-foxtop` | `branch2_eunji_reference` | null | Foxtop (정은지 reference) | `eunji_measured_yaml` | `ref-foxtop` | `ref-foxtop.yaml` | `ref-foxtop.yaml` L8: "IPSF 미등재(Unrecognized) → 분기 2 정은지 reference" |
| `ref-foxtop-split` | `branch2_eunji_reference` | null | Foxtop Split (정은지 reference) | `eunji_measured_yaml` | `ref-foxtop-split` | `ref-foxtop-split.yaml` | `ref-foxtop-split.yaml` L8: "IPSF 미등재(Unrecognized) → 분기 2" |
| `ref-sideway-spin` | `branch2_eunji_reference` | null | Sideway Spin (정은지 reference) | `eunji_measured_yaml` | `ref-sideway-spin` | `ref-sideway-spin.yaml` | `ref-sideway-spin.yaml` L8: "IPSF 미등재(Unrecognized) → 분기 2" |

핵심 함의:
- `ref-invert` 는 IPSF 등재(branch1 카피)지만 각도 소스는 정은지 측정 yaml — `copyBranch=branch1` 이라고 IPSF 각도 fixture 를 쓰는 게 아님. 둘이 직교라는 증거.
- `ref-climb` 은 branch1 카피지만 `no_angle_criterion` — coach 프롬프트는 "이 동작은 관절 각도 fixture 가 없다" 라인을 내보내고 **가짜 각도를 주입하지 않는다**.
- **현재 5 동작 중 `ipsf_registered_fixture` 로 라우팅되는 것은 0개** (전부 eunji_measured 또는 no_angle). Ayesha 류 IPSF fixture + criteria-7 human-verify checkpoint 는 **미래 등재 동작 전용** — path/test 는 유지하되 현재-5 critical path 가 아니다.

## 3. 180° 는 extension/line 전용, universal angle 아님 (1차 HIGH-3)

RESEARCH(L233, L305) 의 "세계 심사 기준 (IPSF) + 180°" / "어깨/무릎 180° 신전" 을 **모든 angle 차원 baseline** 으로 쓰는 것은 **superseded**.

- `180°` 는 **line(신전) 차원 전용** 카피 — 해당 동작에서 EXTEND 인 팔꿈치/무릎에만.
- angle 차원 baseline = **동작별 정의 각도(NON-180)**. 예: registered_move_angles fixture 의 Ayesha top shoulder ~110°, top elbow 20-30° 는 `isExtension:false`, 180° 로 덮어쓰지 않는다.
- `registered_move_angles.json` 은 joint 별 `{angle, tolerance, fault, isExtension}` — `isExtension:true` 만 180°.

## 4. registered_move_angles ↔ motion_ipsf_map 키 계약 (2차 HIGH-1)

- `registered_move_angles.json` 은 `motion_ipsf_map` 의 `angleFixtureKey` 와 **동일 키**로 keyed + `schemaVersion`.
  ```
  { "schemaVersion": "1.0.0",
    "angles": { "ipsf-ayesha": {...}, "ref-invert": {"angleSource":"eunji_measured_yaml", "criteriaYaml":"ref-invert.yaml"} } }
  ```
- 모든 motion_ipsf_map 엔트리는 `angleFixtureKey` **필드**를 가진다. 단 non-null 은 `ipsf_registered_fixture`/`eunji_measured_yaml` 에서만 — `no_angle_criterion`(ref-climb)에서는 **반드시 null**(3차 HIGH-1: 가짜 key 강제 금지). 테스트:
  - `angleSource=ipsf_registered_fixture` → `registered_move_angles.angles[angleFixtureKey]` 존재
  - `angleSource=eunji_measured_yaml` → `criteria/{angleFixtureKey}.yaml` 존재
  - `angleSource=no_angle_criterion` → 프롬프트가 "관절 각도 fixture 없음" 명시(가짜 각도 생성 0)

## 5. app mirror = JSON byte-copy + full-content lockstep (2차 HIGH-2)

1차 patch 의 manual TS object + name-set lockstep 은 **smoke test only** 로 강등 — **superseded as drift gate**.

- BEST: `app/src/data/corrective_exercises.json` 을 `backend/data/corrective_exercises.json` 의 **byte-for-byte 복사**로 두고, `correctiveExercises.ts` 는 그 JSON 을 import 하는 typed wrapper.
- lockstep test/script 는 canonical JSON 전체를 hash 또는 deep-equal 비교: schemaVersion, 모든 defect 키, 모든 painArea 키, 각 exercise `{name, setsReps, purpose, sourceRef}`, 각 painArea `avoid`, 각 trigger `sourceSignals`+`jointHints`. name-set 비교만으로는 drift 미탐지.

## 6. 빈 추천 시에도 전체 라이브러리 browse entry 유지 (2차 MEDIUM-1)

- "보완 운동" 섹션은 `recommendedExercises.length > 0` **OR** app 라이브러리(`CORRECTIVE_EXERCISES`)에 항목이 있으면 렌더.
- 빈 추천 neutral state: "이번 분석에서는 뚜렷한 보완 운동 매핑이 없어요." + "전체 보완 운동 보기" 버튼(전체 라이브러리 모달) — criteria 4 entry point 가 사라지지 않는다.
- 빈 추천 케이스 UAT 라인(또는 RN snapshot test) 추가.

---

## 변경 없이 유지(1차 closed/PASS — 계속 박제)

3-way 계약(recommendedExercises plain camelCase scalar dict + scoped validator) · D-05 painAreas-no-scoring grep gate · criteria-5 non-autonomous Pod checkpoint · branch-2 forbidden-phrase gate · criteria-8 "세계 심사 기준" branch2 미포함 · fitness_norms_kspo.yaml 미소비(v2) · branch-2 yaml 경로 double-prefix 금지(`ref-ref-foxtop.yaml` 금지) · 각 task `<read_first>` + checkable `<acceptance_criteria>` + 산문 `<action>`(fenced code 금지) · `<threat_model>` blocks · 이모지 금지 · app 라이트 테마 / brand #FF4B33 토큰 / Phase 12.5 modal 패턴 재사용.
