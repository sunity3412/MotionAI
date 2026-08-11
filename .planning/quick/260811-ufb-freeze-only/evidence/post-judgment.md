# 사후 판정 (카드 실물 육안 — pre-judgment.md 박제 후 실측)

판정 순서 준수: pre-judgment 박제 → --check(2회)/--sweep 실행 → 카드 PNG 전부
직접 열람 → 이 문서. 실측이 예측과 다른 곳은 다르다고 적는다 (curve-fit 0).

## A. fresh doc (p34fresh1786363530) — 예측 대비

| rid | joint | 예측 | 실측 | 판정 |
|---|---|---|---|---|
| r00 | left_elbow | 상속 방출 | **방출** inherit@u5.302/r5.13 (== freeze) | 예측 적중 |
| r01 | right_elbow | 미방출 | **미방출** hold=moving pair=match | 예측 적중 |
| r02 | right_shoulder | 미방출 | **미방출** hold=moving pair=pose_far | 예측 적중 |
| r03 | left_hip | 통과/기각 양쪽 다 스펙 | **방출** inherit@u16.667/r15.20 (== freeze). 눈 실측: track 6.9도 claim=bent, observed=bent/leg conf 0.9 → 통과 | freeze 그 장면이 카드가 됨 |
| r04 | left_knee | 미방출 (LD-6) | **미방출** hold=moving pair=match | 예측 적중 — 되살리지 않음 |

### 카드 육안 (evidence/cards/)

- `zoom_angle_vs_reference__left_hip.png` (라벨 18.6s / 실초 16.667s — ÷9.0
  잔존 기록): 좌 패널 = u30fps 프레임 00501(16.667s, 뒤태 폴 밀착 왼다리 접힘)
  **동일 장면 확대** — 영상 정지 u16.667 프레임과 대조 일치. 우 패널 = r30fps
  00457(15.20s, 후굴 다리 폴 거치) 동일 장면. **카드 = 영상 freeze 확대** 성립.
  단, 이 짝의 국면 대비(유저 수직 밀착 vs 기준 후굴)는 영상 자체의 align-peak
  짝 — 카드는 그것을 그대로 물려받는다 (영상이 승인 틀이라는 스펙 그대로).
- `zoom_angle_vs_reference__left_elbow.png` (라벨 5.9s / 실초 5.302s): 양 패널
  역립(머리 아래) 동일 국면, u30fps 00160·r30fps 00155 와 장면 일치. 성립.

### 크롭 재측정 (반려 스펙 잔여 관찰 — 수리 범위 밖, 수치만)

fresh 2카드 모두 `shared_frac=0.4000` (부위/패널 40% — ms2 밴드 0.40~0.55 하한),
user_side_px=864(원본 2160 의 40%), ref_side_px=432. vertex_centered=True.
"멀어 보임" 잔여는 밴드 하한 소진 상태 — 크롭 알고리즘 무접촉 확인.

### 0장 거동 (LD-5 실물 — --zero-card, 드라이버 한정 monkeypatch)

hold 전부 FAIL 강제 → survivors=[] → **`update_analysis_fault_zoom` 호출됨**
(confirmed=0 + advisory=1) → 기존 doc 의 confirmed 4장이 **대체 소거**, advisory
1장만 잔존. 눈 호출 0 (게이트 실패 시 눈 안 씀 — 비용 0). "선착 confirmed 를
남겨야 하는가"는 belle 결정 항목 (kpo 승인 semantics 그대로 — 이번 변경 0).

## B. 승인 5동작 스윕 (belle 추가 지시 — 어떤 영상이든)

**SWEEP FREEZE-MATCH ALL (5동작, 방출 9 / 침묵 4)** — 방출 전건 @u/r == 그 동작
승인 freeze 초 그대로. 순간 발명 0 이 5동작 전부에서 성립.

| motion | rid/joint | 예측 | 실측 | 비고 |
|---|---|---|---|---|
| elbow | r01 right_shoulder | 방출 | **방출** @u7.444/r10.20 | 눈 midrange 비구속 |
| elbow | r03 right_knee | 방출 | **방출(게이트)** @u10.111/r11.60 — 단 카드 미렌더 (아래 관찰 1) | 눈 통과 (ledger 00_user_right_knee) |
| elbow | r00 right_elbow | 방출 | **방출** @u11.111/r12.07 카드 육안: 양 패널 트위스트 동일 국면 | 눈 통과 |
| elbow | r02 left_hip | **미방출 예측 (중요 발견 후보)** | **미방출** hold=hold pair=pose_far | 예측 적중 — ii0 집계에선 비구속(peak)이던 승인 정지가 ufb 규칙(각도-주장 pairSrc 무관 게이트)에서 침묵. 임계 무조정 박제 |
| kipup | r00 split_angle | peak 방출 | **방출** peak@u1.467/r2.00 카드 육안: 양 패널 스플릿 정상 | |
| pdshapefault | r02 left_shoulder | 방출 | **방출** @u3.222/r2.00 육안 동일 역립 국면 | |
| pdshapefault | r03 left_knee | 방출 | **방출** @u3.667/r2.40 — ii0 r03inherit 좌표(3.667/2.4)와 동일 짝 | 눈 통과 (01_user_left_knee) |
| pdshapefault | r00 left_elbow | 방출 | **방출** @u8.556/r9.40 | |
| pdshapefault | r01 right_elbow | 방출 예측 (눈 미지) | **미방출 — 눈 기각** `extended->bent/arm` (u1.222s 도입부 override 짝) | **예측과 다름.** 크롭 육안(00_user_right_elbow.png): 폴을 쥔 팔이 실제 굽어 보임 — track 주장(폄)이 환각, 눈이 잡은 것. 정직한 침묵 |
| peterpan | r00 left_shoulder | 방출 예측 | **미방출 — 눈 기각** `extended->unclear/other` | **예측과 다름.** 크롭 육안(00_user_left_shoulder.png): 원이 머리카락/폴에 겹친 어깨 — 눈이 확정 불가(unclear) → fail-closed 침묵. 승인 peterpan 은 confirmed 0장이 된다 — 그대로 박제 (임계·판정 무조정) |
| powerspin | r02 left_shoulder | 방출 | **방출(게이트)** @u3.222/r5.73 — 카드 미렌더 (관찰 1) | 눈 통과 |
| powerspin | r00 leg_extension | peak 방출 | **방출** peak@u5.733/r8.67 육안 정상 | |
| powerspin | r01 split_angle | no_freeze | **no_freeze 미방출** | 예측 적중 |

### 관찰 1 — 방출 게이트 생존 ≠ 카드 보장 (kpo 무접촉 층의 기존 거동)

elbow r03(right_knee)·powerspin r02(left_shoulder)는 게이트 생존·verdict 방출
기록됐으나 카드 미렌더 — `criterion_units_from_records` 유닛 유도(fault_joints
재료 의존, fault_zoom 무접촉 층)에서 제외된 것. ufb 수술 범위 밖 (kpo 승인
배선 semantics 그대로). SUMMARY 유보 항목으로 박제.

### 관찰 2 — 기계 눈이 승인 정지 2건을 침묵시켰다 (중요 발견, 무조정)

- pdshapefault r01: 눈이 track 환각(접힌 팔 → 폄 주장)을 적중 — 침묵이 정당해
  보임 (크롭 육안 동의).
- peterpan r00: 눈 확정 불가(unclear) → fail-closed 침묵. 유일 record 라 승인
  peterpan 의 confirmed 카드가 0장이 됨. **판정 자체는 스펙(LD-1/3 정직한 침묵)
  이나, 승인 영상 카드 소멸이므로 belle 확인 요망** — "unclear 를 기각으로 볼
  것인가"는 임계가 아니라 정책 (fail-closed 유지가 현행).

### D-41 재확인 (동작명 분기 0)

- card_gates.py: 동작명 리터럴 코드 분기 0 (docstring 근거 인용 1곳뿐 — 212행
  "승인 pdshapefault" 산문).
- app.py `_run_gated_card_inherit` 함수 범위: 동작명/ref-* 리터럴 0.

## 기계 판정 종합

- FREEZE-MATCH ALL: fresh 2회 + 스윕 5동작 전부 — 방출 순간 == freeze 전건.
- DETERMINISM PASS: fresh 2회 별도 프로세스 — survivors/dropped/카드/PNG md5 동일.
- approved 9/9 (hold+pair) + peak 비구속 3 — ii0 등가 재현.
- pytest: **59 failed / 4149 passed — 기준선 동일.**
- 눈 호출: fresh 2회/실행 (kpo 40~46회 → 급감), 스윕 총 6회/5동작.
