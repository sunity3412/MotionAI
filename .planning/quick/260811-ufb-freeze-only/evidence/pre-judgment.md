# 사전 판정 (frames-before-numbers — 카드 생성·열람 전 박제)

작성 시각: 2026-08-11T13:0x UTC (Task 1 수술 커밋 4d1b1b49 직후, verify_local
첫 실행 전). 예측 근거 = kpo 실측 (260811-kpo-SUMMARY + evidence) + 플랜
"예상 결과" 절. **정답표 아님** — 기계 실패 조건은 freeze 불일치 / 2회 비결정 /
승인 회귀 / pytest 이탈 만. 관절별 방출은 예측과 달라도 그대로 박제.

## freeze 예상 (kpo 로컬 실측 freeze 5건 기준)

| rid | joint | kpo freeze | kpo 경로 | ufb 예측 |
|---|---|---|---|---|
| r00 | left_elbow | u≈5.30s (joint-scope) | inherit PASS | **상속 방출** (hold+pair 는 kpo 에서 통과. 눈 = user 측 동일 프레임 — kpo 통과였으므로 방출 예상) |
| r01 | right_elbow | joint-scope | 로컬 기각(재정박 경계) | **미방출** 예측 — kpo 로컬에서 freeze 자리 게이트 FAIL 이었고 이번엔 재정박이 없다. (Pod 는 kpo 에서 재정박 생존이었으나 그 경로가 소멸 — 미방출이 스펙 충족) |
| r02 | right_shoulder | joint-scope | 로컬 기각 | **미방출** 예측 (같은 논리) |
| r03 | left_hip | align-peak 16.7s (각도-주장) | 절정 재배치 → 측정 짝 게이트 → 기각 | **freeze 16.7s 그 자리에서 게이트** — kpo 실측은 16.7s 에서 hold+pair 통과 (그래서 재배치를 넣었던 것). 눈 판정 미지: 통과 시 **16.7s 확대 카드 방출**(영상이 보여준 그 장면 — 스펙 충족), 눈 기각 시 미방출. **양쪽 다 스펙 충족** — 실측 그대로 보고 |
| r04 | left_knee | joint-scope (freeze FAIL) | 재정박 12.8s 방출 | **미방출** 예측 (LD-6 — freeze 자리 FAIL 이었고 재정박 소멸. 그대로 보고, 되살리기 금지) |

## 구조 불변식 예측 (이것이 정답표)

1. FREEZE-MATCH ALL — 방출 전건의 @u/r == freezes[] 값 (변형 연산 0 이므로 등호).
2. DETERMINISM PASS — 순간 비결정은 구조 소멸. 남은 비결정 후보 = 기계 눈 flip
   (같은 프레임 같은 크롭 재판정) 뿐 — flip 시 원장 박제 후 FAIL 보고.
3. approved 9/9 — 수술은 판정 함수(card_gates) 무접촉이므로 동일해야 함.
4. pytest 기준선 59 동일.

## 0장 거동 예측 (LD-5 — --zero-card 실험)

hold 전부 FAIL → confirmed 생존 0 → `update_analysis_fault_zoom` 이
confirmed 빈 목록 + advisory 만으로 호출돼 **선착 confirmed 카드가 대체
소거**될 것 (플랜 실물 좌표 절의 현 코드 해석). 이 semantics 는 kpo 승인
배선 그대로 (변경 금지) — "남아야 하는가"는 belle 결정 항목.

## 크롭 예측

카드 방출 시 fault_zoom_crop 로그의 shared_frac / side_px 는 ms2 밴드
(부위/패널 34~65%) 안일 것으로 예측 — freeze 복귀로 순간이 바뀌어도 크롭
알고리즘은 무접촉이므로 부위 크기 기반 목표 0.50 · 밴드 0.40~0.55 로직 그대로.
"멀어 보임" 잔여는 수치만 기록 (수리 범위 밖).

## 눈 호출 예측

탐색 소멸로 freeze 게이트 건수만: inherit 후보 프레임 user 측 ≤5회/실행
(kpo 40~46회 대비 급감 — T-ufb-03).

---

# 승인 5동작 스윕 사전 판정 (belle 추가 지시 — 스윕 실행 전 박제)

작성 시각: fresh --check PASS 직후, --sweep 첫 실행 전. 근거 = approved()
게이트 실측(hold/pair per freeze) + 각 doc 의 criterion 종류. **예측이 정답표가
아니다** — 승인 정지가 게이트에서 떨어지면 임계 조정 없이 그대로 박제 (그 자체가
중요 발견).

| motion | rid | joint | src | criterion 종류 | 예측 |
|---|---|---|---|---|---|
| elbow | r00 | right_elbow | align(joint) | 각도-주장 | hold 19d/s+pair PASS → 눈 통과 시 **방출** |
| elbow | r01 | right_shoulder | align(joint) | 각도-주장 | hold 2d/s+pair PASS → **방출** (어깨 중간각이면 눈 비구속) |
| elbow | r02 | left_hip | align-peak | **각도-주장** | ufb 규칙상 pairSrc 무관 게이트 — approved() 실측 **pair=False** → **미방출 예측**. ii0 스윕에선 비구속(peak 집계)이던 정지가 ufb 에서 죽는 첫 사례 — 승인 영상 카드 1장이 침묵으로 바뀐다. 중요 발견으로 박제 예정 |
| elbow | r03 | right_knee | align(joint) | 각도-주장 | hold 13d/s+pair PASS → 눈 통과 시 **방출** |
| kipup | r00 | split_angle | align-peak | 절정 축 | **peak pass-through 방출** (비구속) |
| pdshapefault | r00~r03 | l_elbow/r_elbow/l_shoulder/l_knee | joint | 각도-주장 | 4건 전부 hold+pair PASS → 눈 통과 시 **4장 방출** (상한 4) |
| peterpan | r00 | left_shoulder | joint | 각도-주장 | hold 53d/s(상한 60 근접)+pair PASS → **방출** |
| powerspin | r00 | leg_extension | align-peak | 절정 축 | **peak pass-through 방출** |
| powerspin | r01 | split_angle | (freeze 없음) | 절정 축 | **no_freeze 미방출** (probes 에 정지 없음 — 상속 바닥 부재) |
| powerspin | r02 | left_shoulder | joint | 각도-주장 | hold 8d/s+pair PASS → **방출** |

구조 불변식 (스윕에서도 이것이 정답표): 방출 전건 @u/r == 그 동작 probes freeze
초 그대로 (FREEZE-MATCH). 눈이 승인 정지를 기각하면 해당 관절 침묵 — 조정 금지,
실측 그대로. 벤치 슬롯 2건(pdshape correct/realupload)은 구버전 포맷(refKp 부재)
— helper 의 refKp 스킵 가드 대상이라 스윕 범위 밖 (활성 5슬롯 = 승인 5동작).
