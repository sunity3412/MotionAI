# 260811-ii0 스윕 보고 — 성립 게이트 × 승인 5동작

> 기계 판정 한 줄: **승인 정지(joint-scope) 9/9 전건 생존 + pdshape 왼골반 탈락(홀드
> 111도/초 전환 + 기계 눈 불일치 이중 기각) + 왼무릎 방출 경로 = r03 상속 성립**
> (게이트 전건 PASS, 육안 동일 국면 확인). 단, 벌림 절정(align-peak) 정지 3건은
> 홀드/포즈 parity 의 판정 축이 아님을 실측으로 확인 — 아래 "게이트 적용 범위" 참조.

- 실행: 2026-08-11, 로컬 (Pod 불필요). 판정 트랙 = P35 align.json (15fps RTMW17,
  타임베이스 정본). 채점·운영 코드 무접촉 — 전부 이 디렉터리의 gates.py/sweep_gates.py.
- 승인 정지의 정본 = 렌더러 probe 실행 로그 (`run_probes.sh` → `probes.log` —
  자동 짝 판정 + pdshapefault r01 수동 오버라이드 0.8s 포함, v7 승인 영상의 실제 정지).
- 동작 목록 = `data/*/` glob (align.json+doc.json 7건) — 하드코딩 0 (D-41).

## 1. 승인 정지 전건 — 게이트 결과 (최종 임계)

임계: hold < 60도/초 · pose < 0.85 · poleDiff < 0.375 몸통. `sweep_out/approved_final.json`.

| 동작 | rid | 축 | src | hold (도/초) | pose d (k) | poleDiff | 판정 |
|---|---|---|---|---|---|---|---|
| elbow | r00 | right_elbow | align | PASS 19 | 0.15 (12) | 0.17 | 생존 |
| elbow | r01 | right_shoulder | align-w | PASS 2 | 0.74 (12) | 0.11 | 생존 |
| elbow | r03 | right_knee | align | PASS 13 | 0.29 (12) | 0.31 | 생존 |
| pdshapefault | r00 | left_elbow | align-w | PASS 26 | 0.22 (12) | 0.19 | 생존 |
| pdshapefault | r01 | right_elbow | **override 0.8s** | PASS 18 | 0.46 (12) | 0.14 | 생존 |
| pdshapefault | r02 | left_shoulder | align | PASS 2 | 0.14 (12) | 0.08 | 생존 |
| pdshapefault | r03 | left_knee | align | PASS 18 | 0.22 (12) | 0.02 | 생존 |
| peterpan | r00 | left_shoulder | align | PASS 53 | 0.16 (12) | 0.03 | 생존 (영상끝 클램프 미러) |
| powerspin | r02 | left_shoulder | align | PASS 8 | 0.45 (12) | 0.20 | 생존 |
| **joint-scope 소계** | | | | **9/9** | **9/9** | | **전건 생존** |
| elbow | r02 | left_hip | align-peak | (16) | (1.42) | 0.02 | 절정 축 — 비구속 |
| kipup | r00 | split_angle | align-peak | (35) | (0.10) | 0.15 | 절정 축 — 비구속 |
| powerspin | r00 | leg_extension | align-peak | (428) | (0.23) | 0.04 | 절정 축 — 비구속 |
| realupload | r02/r00 | (bench) | | (7 / 425) | ref_kp 없음 | | 벤치 — 정보 행 |

pdshape(correct) = 정지 0건 (records 없음) — 해당 없음.

### 게이트 적용 범위 (구조 발견 — 동작명 분기 0)

`src=align-peak` 정지(벌림 계열: split_angle / leg_extension / 가위스플릿 힙 큐)는
**절정 표시 축**이다 — 성립 근거가 "홀드"가 아니라 "벌림 최대 국면"(렌더러 argmax 가
이미 강제)이고, 짝도 "각자의 절정"이라 포즈 parity 대상이 아니다. 실측 근거:

- 파워스핀 leg_extension 절정 = 회전 중 428도/초 — 스핀의 스플릿 절정은 원리적으로
  홀드가 아니다 (CONTINUE "스핀 계열 홀드 짧음" 예고 그대로).
- 가위스플릿 힙(elbow r02) 포즈거리 1.42 — 유저 절정 vs 기준 절정은 belle 승인
  짝이지만 같은 순간 포즈가 아니다.

이 3건에 홀드/포즈 parity 를 강제하면 승인 정지가 죽는다 → 게이트는 **record 선정
경로(src) 기준**으로 적용 범위를 갈랐다 (동작명 리터럴 0 — `grep -nE '"(elbow|kipup|powerspin|peterpan|pdshape)"' gates.py sweep_gates.py` 빈 출력, 판정 경로 한정).

## 2. 튜닝 이력 (전부 박제 — 픽스처 curve-fit 0)

| 라운드 | 변경 | 근거 | 결과 (joint-scope 9정지) |
|---|---|---|---|
| t0 | 출발값 hold<60 · pose<1.30 · poleDiff<0.15, 대칭창 Theil-Sen, conf0.35 경질 포즈 기저 | PLAN 출발값 | hold 8/12 · pair 6/12 (peak 미분리 12정지 기준) — FAIL |
| t1 | **구조 수리 ①**: 홀드 = 3창(과거/대칭/미래) 최소 판정 | 승인 정지는 홀드 **경계**(자세 도달 직후)에 정당하게 잡힘 — pd r00 재그립 직후 정착: 대칭창 111 → 전방창 33도/초 실측. 전환 구간은 3창 전부 높아 판별력 유지 (fresh 왼골반 111 FAIL 유지) | hold 9/9 (임계 60 유지) |
| t1 | **구조 수리 ②**: 포즈거리 = 가중 모드 (기저 = 학생 finite∩conf>0 ∩ 기준 finite, 가중 = 학생 conf) | 운영 `select_pose_matched_ref_frame` 2026-07-27 재설계 미러 — conf 경질 게이트가 역립 기저 붕괴(elbow r01 k=3 측정불가)를 만든 실측 재현. 신규 튜닝상수 0 | pair 측정가능 9/9, d 최대 0.74 |
| t1 | 영상끝 클램프 미러 (peterpan ut 6.44s > 영상 6.07s) | 렌더러 [clamp] 와 동일 — 실제 승인 화면은 클램프된 정지 | peterpan 측정가능 (53도/초) |
| final | pose < **0.85** (1.30→0.85 조임) | 승인 최대 0.74 vs 부정 대조군 최소 0.96 사이 (양측 실측 유도, 아래 대조군 표) | 9/9 유지 + NEG 2건 기각 |
| final | poleDiff < **0.375** (0.15→0.375 완화) | 승인 최대 0.31 (elbow r03 — **차이 자체가 결함인 승인 표시**: 몸이 폴에서 떨어진 belle 승인 카드) vs NEG left_hip 0.44 사이. 0.15 는 승인 4건을 죽여 기각 | 9/9 유지 + NEG 1건 기각 |

### 임계 분리 대조군 (align 트랙 실측)

| 짝 | 성격 | pose d | poleDiff |
|---|---|---|---|
| r03 상속 3.667/2.4s | POS (승인) | 0.224 | 0.02 |
| r01 상속 1.222/0.8s | POS (승인·수동 지정) | 0.462 | 0.14 |
| r00 상속 8.556/9.4s | POS (승인) | 0.216 | 0.19 |
| left_hip 카드 짝 4.78/1.19s | **NEG** (belle 적발 다른 장면 — 철회 장부 1호) | **0.962** | **0.44** |
| knee 탐욕 짝 16.27/11.69s | **NEG** (오늘 육안 기각) | **1.520** | 0.14 |

pose 축은 POS≤0.74 / NEG≥0.96 으로 깨끗이 갈린다. poleDiff 축은 승인 0.31 이
하한이라 [0.31, 0.44] 사이 중점 0.375 — pose 축이 1차, 폴 parity 는 2차 방어선.

## 3. pdshape 목표 판정 (fresh doc p34fresh1786363530, 60점, 5 record)

판정 트랙 = pdshapefault align (fresh 영상과 동일 원본 — md5 일치 08-08 실증).
record 순간 = Firestore REST 실조회 (`sweep_out/fresh.json`, atVideoSec 9.997fps 보정 세대).

| record | 축 | 순간 | hold (3창 최소) | 기계 눈 | 판정 |
|---|---|---|---|---|---|
| r00 | left_elbow | 5.30s | PASS 59도/초 (경계) | bent→bent 일치 (conf 0.95) | 생존 (기결론 폴이탈 축) |
| r01 | right_elbow | 6.10s | **FAIL 112** | 중간각 100도 — 판정 대상 아님 | 탈락 |
| r02 | right_shoulder | 13.81s | **FAIL 98** | bent→bent 일치 | 탈락 (홀드) |
| **r03** | **left_hip** | **4.70s** | **FAIL 111 (3창 전부 >110 — 전환)** | **트랙 bent(98도) vs 눈 extended — 불일치** | **탈락 (이중 기각) — 기대 그대로** |
| r04 | left_knee | 10.50s | **FAIL 221** | 중간각 127도 — 판정 대상 아님 | 측정 순간 기각 |

### 왼무릎 방출 경로 — 성립 (r03 상속)

승인 영상 pdshapefault r03 정지(user 3.667s / ref 2.4s)가 **모든 게이트를 통과**한다:
hold 18도/초 · pose 0.22 · poleDiff 0.02 · 육안 동일 국면 (`evidence/r03inherit_u_3.667s.png`
/ `r03inherit_r_2.4s.png` — 역립 + 한 다리 걸고 자유 다리 뻗는 같은 국면, 자유 다리
라인 차이가 읽힘). 카드가 영상 정지를 상속하면 왼무릎 카드가 방출된다 — CONTINUE 의
"무릎=r03 상속으로 해결" 이 기계 게이트로도 성립. 오늘 doc 의 잘못된 측정 순간
(10.5s, 221도/초)은 홀드 게이트가 기각한다.

### 신규 발굴(탐색) 경로의 한계 — 정직 박제

홀드∩짝 탐욕 탐색이 찾은 최상 짝 (user 16.33s / ref 15.47s, d=0.81, deficit 92도)은
게이트 수치를 전부 통과했으나 **육안으로 다른 국면** (user 수평 스핀 이탈 vs ref
직립 다리 교차 — `evidence/kneepath_u_16.33s.png` / `kneepath_r_15.47s.png`):

1. pose 회색 지대 [0.74, 0.96] 실존 — 승인 상한(0.74)을 지키는 한 0.85 아래로 새는
   국면 불일치가 있을 수 있다.
2. 기계 눈의 잔여 위험 실측: user 측 트랙 왼무릎(0도)의 마크가 **팔에 얹혔는데**
   (환각 keypoint), 팔이 굽어 있어 claim=bent 가 "일치"로 통과했다
   (`evidence/eye_kneepath_user_left_knee.png`). 마크가 "다른 굽은 사지"에 떨어지면
   claim-일치 검증이 뚫린다 — bz5 부록 C 설계의 알려지지 않았던 구멍.
3. 따라서 **신규 발굴 짝은 A1~A3 수치 통과만으로 방출 불가** — 프로세스 5번(방출 전
   바닥 대조: 영상이 잡은 걸 잃으면 폴백)이 필수임의 실측 근거. 상속 경로(r03)가
   바닥이므로 엉망이 되는 경로 자체는 없다 (CONTINUE 설계 그대로).

## 4. 기계 눈 결과 전건 (gemini-3.5-flash, temp 0, 호출 9회)

| 대상 | 트랙 주장 | 눈 판정 | 일치 | 비고 |
|---|---|---|---|---|
| 캘리브레이션: 정은지 rep162 왼무릎 | extended 178.4도 (환각) | **bent** conf 0.9 | **불일치 → 차단** | 기하로 못 잡는 환각을 눈이 잡음 (부록 B/C 재현) |
| fresh r00 left_elbow | bent 74도 | bent 0.95 | 일치 | |
| fresh r02 right_shoulder | bent 76도 | bent 0.95 | 일치 | |
| fresh r03 left_hip | bent 98도 | **extended** 0.9 | **불일치 → 차단** | 전환 순간 — 홀드와 이중 기각 |
| fresh r01 / r04 | 중간각 100/127도 | — | 판정 대상 아님 | 이분 판정 불가 = 정직한 침묵 |
| kneepath user/ref | bent 0/92도 | bent 0.9 | 일치(위험 사례) | 마크가 타 사지 — §3 한계 |
| elbow r03 right_knee (타 동작 표본) | extended 174도 | extended 0.95 | 일치 | |

## 5. 증거 PNG (전부 직접 열어 확인)

- `evidence/pole_{동작}_{user|ref}.png` 14장 — 배경 중앙값 + 검출 축선 (전 동작
  x≈0.501, peterpan ref 0.522 — 육안 폴 위 확인 2장 표본: pdshapefault user,
  peterpan ref)
- `evidence/calib_ref_rep162_left_knee_marked.png` — 환각 프레임 마킹 크롭 (마크가
  폴 위, 다리는 접힘)
- `evidence/r03inherit_{u,r}_*.png` — 왼무릎 방출 경로 짝 (같은 국면 육안 확인)
- `evidence/kneepath_{u,r}_*.png` — 탐색 짝 (다른 국면 육안 기각)
- `evidence/eye_*.png` 7장 — 기계 눈 판정 크롭

## 6. 미달/유보 정직 박제

1. **fresh r00 (left_elbow) 홀드 59.3도/초 — 임계 60 바로 아래 경계 통과.** 임계
   민감 구간이다. 왼팔꿈치는 기결론(폴 이탈 원인, 각도 문구 아님) 축이라 카드
   문법은 폴 근접도로 가야 하고, 이 게이트 판정에 걸린 것이 없음을 명시.
2. **align-peak 정지의 성립 게이트는 이번 스윕 범위 밖** — "실제 절정인가"는 렌더러
   argmax 가 강제하지만 절정의 **각도값 신뢰**(발목 환각 시 절정 오검) 게이트는
   별도 설계 필요.
3. **기계 눈 마크-전위 구멍** (§3-2) — 마킹 크롭 프롬프트에 "원 안의 관절이 어느
   신체 부위인지"를 함께 묻는 2단 판정(부위 확인 → 상태 판정)이 다음 수리 후보.
4. **doc keypointReport 는 게이트 판정 트랙으로 부적합** — fps 라벨 오차(라벨 18 vs
   실효 20.1 ffprobe 실측)와 관절 12개 제약. 운영 배선 시(다음 사이클) 파이프라인
   내부 트랙의 타임베이스 보정을 전제해야 한다.
5. realupload/pdshape 벤치 슬롯은 구식 align(refKp 없음)이라 pair 측정 불가 —
   벤치라 비구속, 정보 행으로만 박제.
