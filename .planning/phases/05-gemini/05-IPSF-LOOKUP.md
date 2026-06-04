# Phase 5: IPSF Code of Points 5영상 Lookup — NotebookLM 결과

**Generated:** 2026-06-04
**Source:** NotebookLM Notebook `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` (IPSF Code of Points 2024-2025 + 보조 자료)
**Query 기준:** 박제 [[notebook-lm-pole-sports.md]] + 박제 [[judging-baseline-ipsf-code-of-points.md]]
**박제 정신:** [[analysis-objectivity-no-human-scores.md]] — "임계 없음" 그대로 박제, belle 미루기 금지

---

## ⚠ CRITICAL FINDING — Phase 5 게이트 재검토 필요

5영상 catalog 중 **3영상 (foxtop / foxtop-split / sideway-spin) = IPSF 미등재** + **ref-climb = hold 자세 채점 영역 X (climb 흐름 채점)** + **ref-invert 만 IPSF body position 채점 가능**. 이 발견은 박제 D-01 (5영상 인버트 계열 우선) 의 게이트 정의 (angle 5/5 PASS) 가 **IPSF 룰상 4/5 영상에서 불가능** 함을 의미.

| 모션 | IPSF 등재? | angle 채점 영역? | yaml hold target=180° 박제 source |
|---|---|---|---|
| ref-climb | ✓ Transitions & Climbs | hold = 위아래 이동 2회 (각도 X) | **source X (현 yaml angle 박제는 IPSF 근거 없음)** |
| ref-foxtop | ✗ 미등재 | 임계 없음 | **source X** |
| ref-foxtop-split | ✗ 미등재 | 임계 없음 | **source X** |
| ref-invert | ✓ Body Position Inverted | body position ±20° (관절 angle X) | **source X (yaml 6관절 angle 박제 vs IPSF body position 차이)** |
| ref-sideway-spin | ✗ 미등재 | 임계 없음 | **source X** |

→ **현 5영상 yaml hold_moment 6관절 angle_target=180° = IPSF source 박제 X**. Plan 23 sweep verdict root cause 3 (AKA 매핑 vs yaml criteria 정합 미검증) 의 정확한 실증. 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" 정신은 **angle 5/5 PASS 가 IPSF 룰상 가능한 동작에 한정** 으로 재해석 필요.

**Phase 5 박제 결정 영향 (belle 판단 영역)**:
- (가) Phase 5 게이트 정의 변경 — angle 5/5 PASS 대신 "ref-invert angle 채점 + 4영상 P9 절대 트랙 채점 path PASS"
- (나) 5영상 catalog 변경 — IPSF 등재 동작 (Basic Invert Hold / Inverted Split / Inverted Thigh Hook 등 NotebookLM 인용 [4-7]) 으로 sweep 재구성
- (다) yaml 박제 source 정정 — 현 hold_moment 6관절 = 정은지 reference 측정값 (분기 2 path) 으로 source_ref 변경, IPSF source 박제 X 명시
- (라) 위 3개 조합

박제 [[feedback-analysis-first.md]] 정신 정합 → belle 판단 우선. 본 lookup 박제 후 Phase 5 plan 진행은 belle redirect 대기 가능.

---

## 1. ref-climb (폴 climb — basic ascending technique)

### (a) IPSF 분류
- **Transitions & Climbs 카테고리** (공식 등재)
- 특정 element code 없음 (기본 움직임)
- 채점 영역: **Artistic 트랙 (Flow) + Tech Deduction (실행 감점)**
- 등재 형태: Basic climb / Side climb / Caterpillar climb / Seated climb (NotebookLM citation [2, 3])

### (b) 4단계 정의
| 단계 | 정의 |
|---|---|
| setup | 폴을 잡고 이륙 (take-off) 준비 |
| hold | **신체를 위아래로 이동하며 오르내림을 2회 이상 연속 수행** (핵심 채점 구간) |
| peak | N/A |
| release | 등반 마치고 하강 또는 다음 기술 전환 |

### (c) hold moment 관절 기대 (6 joints)
| 관절 | IPSF 기대 상태 |
|---|---|
| Left/Right Shoulder | **CONTACT / BENT_OK** (풀링/푸시 + 폴 접촉) |
| Left/Right Hip | **BENT_OK** (다리 끌어올리기 굴곡 허용, 펴기 요구 X) |
| Left/Right Knee | **CONTACT / BENT_OK** (안쪽 오금/무릎 등 폴 클램핑) |

### (d) setup / peak / release 기대 상태
**IPSF 채점 영역 외** (기하학적 관절 임계 없음)

### (e) angle criteria 수치
- target / tolerance: **특정 각도 임계 없음**
- minimum requirement: **최소 2회 이상 반복 움직임** (Minimum of 2 repeated movements)
- deduction per step: **그립 재조정 (re-grips) / 가시적 덜컹거림 (visible adjustments) 건당 -0.5**

### (f) 비등재 여부
**공식 등재 (Transitions & Climbs)**

### (g) Citation
- "Biomechanical and Terminological Taxonomy of Pole Sports" Table: Taxonomic Structure of IPSF Technical Categories (Transitions & Climbs)
- "2026. 6. 1.의 모든 메모" [1]

### → 현 `backend/judging_data/criteria/ref-climb.yaml` 박제 검토 필요
hold_moment 의 angle criteria 박제 X 가 IPSF 룰상 정합. angle 채점 → **반복 횟수 + 그립 안정성** 채점으로 차원 변경 필요. Phase 5 scope 안에서 처리 불가 (dimensions.py 의 angle 차원과 별 차원).

---

## 2. ref-foxtop (Inverted butterfly / vertical split inverted hold at top)

### (a) IPSF 분류
**미등재 (Unrecognized)** [NotebookLM 인용 [1]]. 평가 시 Transitions & Climbs 카테고리 분류 (Artistic 흐름 평가).

### (b) 4단계 정의
| 단계 | 정의 |
|---|---|
| setup | 인버트 진입 후 하체 세팅 |
| hold | 위 다리 hook + 상체 열어 거꾸로 매달림 유지 |
| peak | N/A |
| release | 그립 풀고 하강 |

### (c) hold moment 관절 기대 (6 joints)
| 관절 | IPSF 기대 상태 |
|---|---|
| Left/Right Shoulder | **임계 없음 (규정에 없음)** |
| Left/Right Hip | **임계 없음 (규정에 없음)** |
| Left/Right Knee | **임계 없음 (규정에 없음)** |

### (d) setup / peak / release 기대 상태
**IPSF 채점 영역 외 (임계 없음)**

### (e) angle criteria 수치
- target / tolerance / minimum requirement: **규정에 없음 (임계 없음)**
- deduction per step: 신체 정렬 오차 시 절대 감점 -0.5 (P9 트랙)

### (f) 비등재 동작 Path
**IPSF 등재 안 됨 명시**. Transitions & Climbs 트랜지션 취급. **P9 절대 감점 트랙 (Poor presentation -0.5) 만 모든 요소 공통 적용**.

### (g) Citation
- "2026. 6. 1.의 모든 메모" [1] (폭스탑 미등재 명시)
- IPSF Pole Sports Code of Points 2021-2024 Page 9 (Poor presentation 절대 감점)

### → 현 `backend/judging_data/criteria/ref-foxtop.yaml` 박제 검토 필요
hold_moment 6관절 angle_target=180° / tolerance ±20° / minimum 160° / deduction 0.2 **= IPSF source 박제 X**. 가능한 path:
- (a) yaml source_ref = "정은지 reference 측정값 (분기 2)" 으로 변경 + IPSF 박제 X 명시
- (b) yaml 자체 폐기 + P9 절대 트랙 단독 채점
- (c) yaml 그대로 + Phase 5 출력에 "비등재 알림" 추가

---

## 3. ref-foxtop-split (Foxtop with split variation)

### (a) IPSF 분류
**미등재 (Unrecognized)**. Transitions & Climbs 카테고리.

### (b) 4단계 정의
| 단계 | 정의 |
|---|---|
| setup | 폭스탑 자세 진입 |
| hold | 두 다리 찢어 스플릿 변형 각도 유지 |
| peak | N/A |
| release | 스플릿 해제 + 탈출 |

### (c) hold moment 관절 기대 (6 joints)
| 관절 | IPSF 기대 상태 |
|---|---|
| Left/Right Shoulder | **임계 없음 (규정에 없음)** |
| Left/Right Hip | **임계 없음 (규정에 없음)** |
| Left/Right Knee | **임계 없음 (규정에 없음)** |

### (d) setup / peak / release 기대 상태
**IPSF 채점 영역 외 (임계 없음)**

### (e) angle criteria 수치
- target / tolerance / minimum requirement: **규정에 없음 (임계 없음)**
- deduction per step: P9 절대 감점 -0.5

### (f) 비등재 동작 Path
**IPSF 등재 안 됨 명시**. 필수 제출 시 0점 (Unrecognized) 처리. 자유 안무 시 Transitions & Climbs 평가 + P9 절대 감점.

### (g) Citation
- "2026. 6. 1.의 모든 메모" [1]
- IPSF Pole Sports Code of Points 2021-2024 Page 9

### → 현 `backend/judging_data/criteria/ref-foxtop-split.yaml` 박제 검토 필요
ref-foxtop 와 동일 path (정은지 reference 박제 vs 폐기 vs 비등재 알림).

---

## 4. ref-invert (Basic invert — 기본 거꾸로 매달림)

### (a) IPSF 분류
**Body Position: Inverted** (공식 등재). NotebookLM citation [4-7]:
- Basic Invert Hold
- Inverted Split
- Inverted Thigh Hook

독립 요소 제출 X 인 경우 Transitions & Climbs 카테고리.

### (b) 4단계 정의
| 단계 | 정의 |
|---|---|
| setup | 폴 잡고 다리 차올려 골반 거상 |
| hold | **골반이 머리보다 높게 위치하여 몸 180° 뒤집힌 상태 유지** |
| peak | N/A |
| release | 골반 낮추어 착지 |

### (c) hold moment 관절 기대 (6 joints)
| 관절 | IPSF 기대 상태 |
|---|---|
| Left/Right Shoulder | **CONTACT / BENT_OK** |
| Left/Right Hip | **BENT_OK** |
| Left/Right Knee | **BENT_OK / CONTACT** (다리 거치 위한 굽힘 허용, Fully Extended 강제 X) |

### (d) setup / peak / release 기대 상태
**IPSF 채점 영역 외** (자연스러운 전환 흐름 평가, 임계 없음)

### (e) angle criteria 수치
- target: **Body Position Inverted (위아래 역전 정렬)** — 6관절 각도 X
- tolerance: **±20°** (목표 정렬 기준선 허용 오차)
- minimum requirement: **엉덩이가 머리 위로 완전 역전**
- deduction per step: 전환 중 평형 상실 -0.5

### (f) 비등재 여부
**공식 기준 상태 (Official Body Position)**

### (g) Citation
- "2026. 6. 1.의 모든 메모" [1] (인버트 공식 용어 명시)
- Biomechanical and Terminological Taxonomy of Pole Sports (Tolerance: 20 degrees limit)

### → 현 `backend/judging_data/criteria/ref-invert.yaml` 박제 검토 필요
yaml hold_moment 6관절 angle_target=180° 는 **IPSF Body Position Inverted 와 다른 차원**. IPSF source 박제 X. 가능한 path:
- (a) yaml 차원 변경 — angle criteria 제거, Body Position Inverted (골반-머리 상대 위치 ±20°) 차원 추가
- (b) yaml hold_moment 6관절 박제 = 정은지 reference 측정값 (분기 2) 으로 source 변경
- (c) Body Position 차원과 6관절 angle 차원 병행 — 6관절은 BENT_OK 인정 (IPSF 룰 정합) + Body Position 차원 신규 dimensions.py 추가

→ Phase 5 scope 안에서 처리 불가. dimensions.py 의 angle 차원 외 **Body Position 차원** 신규 차원 추가는 후속 plan (Phase 8 또는 별 phase).

---

## 5. ref-sideway-spin (Lateral / side rotational spin)

### (a) IPSF 분류
**미등재 (Unrecognized)**. Transitions & Climbs 카테고리 (단순 회전 안무).

### (b) 4단계 정의
| 단계 | 정의 |
|---|---|
| setup | 폴 측면 회전 모멘텀 (원심력) + 도약 |
| hold | 공중에 뜬 상태로 측면 축 회전 유지 |
| peak | N/A |
| release | 발이 바닥에 닿으며 회전 종료 |

### (c) hold moment 관절 기대 (6 joints)
| 관절 | IPSF 기대 상태 |
|---|---|
| Left/Right Shoulder | **임계 없음 (규정에 없음)** |
| Left/Right Hip | **임계 없음 (규정에 없음)** |
| Left/Right Knee | **임계 없음 (규정에 없음)** |

### (d) setup / peak / release 기대 상태
**IPSF 채점 영역 외 (임계 없음)**

### (e) angle criteria 수치
- target / tolerance / minimum requirement: **규정에 없음 (임계 없음)**
- deduction per step: 속도 저하 / 덜컹거림 시 공통 감점

### (f) 비등재 동작 Path
**IPSF 등재 안 됨 명시**. 공식 스핀 (최소 360°/720° 지정 각도 유지) 요소 점수 불가. Transitions & Climbs 동적 연결 흐름 평가 + P9 절대 감점 (Poor transitions -0.5).

### (g) Citation
- "2026. 6. 1.의 모든 메모" [1] (사이드웨이 스핀 미등재 명시)
- IPSF Pole Sports Code of Points 2021-2024 Page 9

### → 현 `backend/judging_data/criteria/ref-sideway-spin.yaml` 박제 검토 필요
ref-foxtop / ref-foxtop-split 와 동일 path (정은지 reference 박제 vs 폐기 vs 비등재 알림).

---

## 종합 박제 — Phase 5 영향 분석

### 박제된 결정과의 정합성 검토

| Phase 5 박제 결정 (CONTEXT.md) | NotebookLM 결과 영향 |
|---|---|
| **D-01: 5영상 인버트 계열 우선** | ⚠ catalog 자체 문제 — 4영상 IPSF 미등재. 게이트 정의 재검토 |
| **D-04: Gemini 1회 호출 → 4단계 라벨 + timestamp** | ✓ 정합 — 4단계 정의 NotebookLM 도 OK |
| **D-05: v1 채점 = hold 라벨만** | ⚠ ref-invert 외 hold angle 채점 자체 IPSF 영역 X |
| **D-08: Gemini = EXTEND/BENT 라벨러, IPSF 임계는 yaml 유지** | ⚠ yaml IPSF 임계 박제 자체 X — 정은지 reference 분기 2 path 로 source 변경 필요 |
| **D-09: 3케이스 분리 (API/Low conf/미등록)** | ✓ 정합 — NotebookLM 도 미등재 = P9 절대 트랙 박제 |
| **D-12 ~ D-16: Pod 호출 + 3.1 Pro + hash 캡싱** | ✓ 정합 (IPSF lookup 과 무관) |

### Phase 5 게이트 재검토 옵션 (belle 판단)

| 옵션 | scope 변경 | 게이트 정의 |
|---|---|---|
| **(가) 게이트 정의 변경 — IPSF 룰 정합** | scope 5영상 유지 | "ref-invert Body Position 채점 PASS + 4영상 P9 절대 트랙 path PASS" — angle 5/5 PASS 게이트 폐기 |
| **(나) catalog 변경 — IPSF 등재 동작 sweep 재구성** | 5영상 → IPSF 등재 동작 (Basic Invert Hold / Inverted Split / Inverted Thigh Hook / Caterpillar climb / Seated climb 등) | angle 5/5 PASS 유지 가능 |
| **(다) yaml source 정정** | scope 5영상 유지, yaml 박제만 정은지 reference 로 source 변경 | yaml IPSF 박제 X 명시 + angle 채점 = 정은지 측정값 기준 (분기 2 path) |
| **(가+다) 조합** | scope 유지 + yaml source 정정 + 게이트 = "ref-invert IPSF Body Position + 4영상 정은지 reference" | 박제 [[studio-term-3branch-system.md]] 분기 2 path 정합 |

### 박제 정신 정합 분석

- [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" → angle 게이트는 **IPSF 룰상 가능한 동작에 한정**. 미등재 동작에서 angle 강요 = 게이트 정의 자체 오류, 우회/강등 X.
- [[analysis-objectivity-no-human-scores.md]] "사람 점수 라벨링 X, 객관 수치 라벨링 OK" → 정은지 reference 측정값 (객관 수치) 박제 = 분기 2 path OK. 단 "정은지가 좋다고 판단" (사람 점수) 박제는 금지.
- [[studio-term-3branch-system.md]] 분기 2 = "한국 학원 통용 + 정은지 reference 비등재 동작". foxtop / sideway-spin = 분기 2 정합. ref-foxtop yaml = 분기 2 박제 path 가 자연 정합.
- [[ipsf-5-track-scoring.md]] "Page 9 절대 트랙 단독 채점 가능" → 미등재 동작 P9 path 박제됨.

### 추천 path (orchestrator)

**옵션 (가+다)**: scope 5영상 유지 + yaml source 정은지 reference 박제 (분기 2 path) + Phase 5 게이트 재정의 ("ref-invert IPSF Body Position 채점 PASS + 4영상 정은지 reference 측정값 비교 PASS + 4영상 P9 절대 트랙 path 작동").

박제 정신 [[mvp-simple-pilot-quality.md]] "MVP 가볍게" 정합 — scope 그대로 유지, 박제 source 만 변경. Phase 5 게이트도 IPSF 룰 정합 + 분기 2 path 정합 + Plan 23 sweep 의 야 데이터 그대로 활용.

**belle 즉시 재검토 필요** — 본 lookup 결과 박제 commit 후 Phase 5 plan 진행 전 belle 판단 받기.

---

## 추가 Lookup 추천 (후속 plan)

- **Basic Invert Hold IPSF element code** + angle criteria (현재 ref-invert = Body Position 만, element code 단위 angle 박제 가능?)
- **Inverted Split IPSF element code** + angle criteria (ref-foxtop 가 Inverted Split 의 변형일 가능성 — element code 단위 박제 시 분기 1 AKA 매핑)
- **Inverted Thigh Hook IPSF element code** + angle criteria (또 다른 분기 1 매핑 후보)
- **Page 9 "all components" 정확 인용** (CoP 2025-2027 page) — Phase 5 D-09 케이스 2/3 의 P9 routing 박제 source
- **Element Code Matching p.138-139** (CoP 2025-2027) — Gemini 분류 → element code 매핑 path 박제

---

*Lookup completed: 2026-06-04*
*Conversation ID: 84d5c7b2-9a71-44d1-9513-5d7071279264 (NotebookLM 후속 follow-up 가능)*
