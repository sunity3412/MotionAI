---
task: 260808-epy
type: execute
date: 2026-08-08
commits:
  - d266cb8d (데이터: p35 정렬 데이터 리포 영구화 — 7동작 16파일 + README)
  - 7787832d (코드: 렌더러 폴 문법 + 그립 판정 + 오버라이드 + p35_audio.py)
  - 0f81316f (코드: diff_reports.py 게이트)
key-files:
  created:
    - .planning/phases/35-server-rendered-comparison-video/data/** (16 JSON + README.md)
    - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/elbow_text_overrides.json
    - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/p35_audio.py
    - .planning/quick/260808-epy-phase-35-2-p35-pdshape-r01-5-v7/diff_reports.py
  modified:
    - backend/scripts/render_compare_prototype.py
---

# 260808-epy: Phase 35 미세조정 2차 — 엘보 폴-근접 문법 + pdshape r01 그립 짝 + 데이터 영구화

## 한 줄

엘보 팔꿈치 큐가 각도 문장 대신 폴 축선·간격 브래킷·"폴에 붙여라" 문구(자막=음성 lockstep)로
말하는 v7 을 belle 기존 링크 5키에 덮어썼다. **pdshapefault r01 왼손 그립 짝은 미충족(fail-closed)** —
x-투영 간격으로는 그립 개시가 원리적으로 측정 불가함을 실측 박제.

## 게이트별 실측 수치

| 게이트 | 판정 | 실측 |
|--------|------|------|
| Task 1 STOP (baseline=v6 재현) | PASS | 5편 전부 S3 v6 실파일과 길이 **0.00s 오차** (elbow 65.80 / powerspin 31.63 / kipup 15.53 / pdshapefault 58.97 / peterpan 23.63) |
| mp3 전수 회수 assert | PASS | 12건 == 렌더 대상 record 수 (elbow 4 / powerspin 2 / kipup 1 / pdshapefault 4 / peterpan 1) |
| baseline 리그 | 5×ALL PASS | exit 0 전건 (A/A2/B/C/D/E/F) |
| v7 리그 | 5×ALL PASS | exit 0 전건. elbow 61.00s(새 mp3 반영), 나머지 길이 불변 |
| diff 게이트 (diff_reports.py) | ALL PASS (exit 0) | 의도 변경 = elbow r00 단 1건. powerspin·kipup·peterpan freeze 행 전건 불변, pdshapefault 4행 전건 불변 |
| kipup r00 피크 | PASS | userSec **1.467** (승인 피크 1.47±0.1, baseline=v7 동일) |
| 발동 프로브 (--probe) | 초과 발동 0 | 신규 발동 = 정확히 {elbow r00: align-pole}. 나머지 11 record 전부 baseline 경로 그대로 |
| S3 5키 덮어쓰기 | 완료 | 08-08 11:38 갱신. realupload_v3 무접촉(08-07 21:22 그대로). kipup/peterpan/powerspin 은 바이트 동일(결정론 재렌더 실증) |
| 증거 스틸 눈확인 | 엘보 PASS / pdshape 상태 기록 | 아래 표 |

## 임계값 실사용치 (전부 구조 유도 — 픽스처 curve-fit 0)

| 상수 | 산식 | elbow 실사용치 (u/r) | pdshapefault (u/r) |
|------|------|---------------------|--------------------|
| τ_prox | 폴반폭px/몸통px + 0.15 | 0.249 / 0.243 | 0.226 / 0.231 |
| τ_grip | 폴반폭px/몸통px + 0.20 | 0.299 / 0.293 | 0.276 / 0.281 |
| 폴 감지 | 커버리지 < 0.25 = None | user cov 0.411 / ref 0.463 | user 0.391 / ref 0.470 |
| dwell (신규 조임) | ref 접촉 run ≥ 0.5s | r00: 1.60s (통과) | r00: 0.20s (차단) / r01: 1.47s (통과) |
| 접촉 특정성 (신규 조임) | rt 에서 힙중점ratio − 팔꿈치ratio ≥ 0.15 | r00: **+0.595** (통과) | r01: **+0.074** (차단) |
| user 대비 마진 | user 창 max ≥ ref_min + 0.15 | r00: 0.458 ≥ 0.152 | — |

조임 2겹의 구조 근거 (동작명 분기 0, `grep -nE '"(elbow|kipup|...)"'` 빈 출력 확인):
- **dwell**: '붙임'(홀드)은 저간격이 지속, 회전 중 x 교차는 순간 딥 — 8배 마진(1.60 vs 0.20)으로 가름.
- **접촉 특정성**: belle 원문 "폴에 가까운 **부분**에서 차이" — 팔꿈치가 접촉 부위려면
  몸통(힙중점)보다 유의미하게 가까워야 함. 몸 전체가 폴선에 있는 진입 국면(pd r01, 마진
  +0.074)은 팔꿈치 x-교차가 부수적 → 배제. 8배 마진(+0.595 vs +0.074).

## 발동 표 (--probe 실측, 12 record 전수)

| slot | rid | criterion | baseline | v7 | 변경 |
|------|-----|-----------|----------|----|------|
| elbow | r00 | right_elbow | align (rt 12.07) | **align-pole (ut 11.60, rt 13.80)** | 의도 변경 ① |
| elbow | r01 | right_shoulder | align-w 10.2 | align-w 10.2 | 불변 |
| elbow | r02 | left_hip | align-peak 11.8 | align-peak 11.8 | 불변 (사이각 표시 유지) |
| elbow | r03 | right_knee | align 11.6 | align 11.6 | 불변 |
| powerspin | r00 | leg_extension | align-peak | align-peak | 불변 |
| powerspin | r02 | left_shoulder | align | align | 불변 (grip fail-closed 로그) |
| kipup | r00 | split_angle | align-peak 1.467 | align-peak 1.467 | 불변 |
| pdshapefault | r00 | left_elbow | align-w 9.4 | align-w 9.4 | 불변 (①=dwell 차단, ②=fail-closed) |
| pdshapefault | r01 | right_elbow | align 2.2 | align 2.2 | **미충족** (①=특정성 차단, ②=fail-closed) |
| pdshapefault | r02 | left_shoulder | align 2.0 | align 2.0 | 불변 (grip fail-closed 로그) |
| pdshapefault | r03 | left_knee | align 2.4 | align 2.4 | 불변 |
| peterpan | r00 | left_shoulder | align 7.6 | align 7.6 | 불변 (grip fail-closed 로그) |

## belle 지시 미충족: pdshapefault r01 왼손 그립 짝 (묶음 2)

**결과**: r01 기준 정지는 rt=2.2s(기존 짝) 유지. 계획 ②의 명시된 fail-closed 경로 — 조용한 생략 아님.

**사유 (전부 실측)**:
1. ref 왼손목 접촉 개시는 검출기가 깨끗이 잡음 — 후보 [0.8s, 1.33s], **0.8s 가 실제 그립 장면**
   (스틸 육안 확인: 0.6s 팔 뻗음 → 0.73s 복귀 → 0.8s 폴 도달. 계획의 "≈1.6s" 후보는 med3 그리드에서 1.33s).
2. 그러나 발동 게이트(user 측)가 성립 불가:
   - user 왼손목의 cue(1.22s) 근방 x-투영 간격이 0.23~0.27(τ_grip 0.276 이내)로 **한 번도 이탈
     임계(2τ=0.55)를 넘지 않음** — 재그립 동작이 깊이/y 축에서 일어나 x-간격에 안 보임. 개시 부재.
   - user 오른손목 개시는 0.467s — |0.467−1.222|=0.756s 로 ±0.75s 창을 0.006s 차이로 벗어남.
     설령 통과해도 **오른손**이라 belle 지시(왼손)와 다른 장면(rt=0.13s 아티팩트)이 나옴 — 게이트 실패가 오히려 보호.
3. 대안 재설계 3종(위상 앵커 ±0.75s / 지속 이탈 필터 / side 규칙 교체)을 전 record 실측으로
   검증했으나 전부 **pdshapefault r02(승인 장면, ref left 개시 1.33s 가 r02 위상 창 안)** 를
   오발동시킴 — 승인 항목 보호가 최상위라 기각.

**belle 선택지 (다음 라운드)**:
- (a) r01 기준 순간을 사람이 지정 (실측 정답 = **ref 0.8s**, 스틸 확보됨) — moments 류 명시 주입.
- (b) 깊이 신호 추가 (3D/y 축 병행) 후 그립 검출 재시도.
- (c) 현 상태(2.2s, 같은 국면대의 정착 장면) 수용.

## 사이각 긴장 판단 (Task 2-6)

**해소 구조 성립.** 엘보 doc 4건 중:
- r00(팔꿈치): 각도 문장("기준 자세와 차이" + 수치로는 179 vs 173 이 비슷해 보이던 긴장) →
  **폴-근접 문법으로 이동**. 차이가 실제로 사는 곳은 각도가 아니라 간격(몸통비 0.002 vs 0.458,
  229배)이고, 이제 그 간격을 브래킷이 모양으로 말한다. 수치 배지 없음.
- r02(가위스플릿 힙): 사이각(두 선+호+수치) **유지** — baseline=v7 legsViz 동일 실측.
- r01(어깨)/r03(무릎): 링 마커 유지.
수치 표시는 벌림 계열에만 남고 팔꿈치 차이는 간격으로 말한다 — 계획의 기대 구조 그대로.

## 증거 스틸 (직접 열어 확인 완료)

| 파일 | 확인 내용 |
|------|-----------|
| `$SP/evidence/elbow_r00_pole_freeze.jpg` | PASS — 양 패널 폴 축선(브랜드 반투명 세로선) + 팔꿈치 링 + 간격 브래킷. user(좌)=링→폴 수평 브래킷으로 벌어짐이 보임, ref(우)=링이 폴선 위(브래킷 0 수렴="붙음"). 수치 배지 없음. 자막 = 오버라이드 문장 |
| `$SP/evidence/pdshape_r01_grip_freeze.jpg` | 상태 기록 — user(좌)=1.22s 왼팔 재그립 국면, ref(우)=2.2s 그립 정착 국면(잡는 '순간' 아님, fail-closed 상태의 정직한 스틸) |

`$SP` = `/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/e6ff396b-4e73-4d48-b163-2b06d562d292/scratchpad` (세션 임시 — 재부팅 소실 가능)

## 자막=음성 lockstep (묶음 1)

- 단일 테이블 `elbow_text_overrides.json` 을 렌더러 `--text-override-json` 과
  `p35_audio.py synth`(Polly Seoyeon/neural/ko-KR/mp3 — pipeline 미러)가 공용으로 읽음.
- r00.mp3 재합성: 11.11s → **6.29s** (37772B), 타 rid 무접촉.
- 구조 증명: v7 elbow r00 freezeS 6.69 = 새 mp3 6.29 + 0.4 (diff 게이트 assert PASS),
  자막 text == 오버라이드 문장 (assert PASS) — 같은 파일에서 갈라져 나감.
- 문장: "오른쪽 팔꿈치가 폴에서 떨어져 있어요. 팔꿈치를 폴에 붙여서 몸을 고정해 보세요."
  (결함문 + 마침표 경계 + 행동문, 각도 언급 0)

## S3 (belle 기존 presigned 링크 그대로 유효)

| 키 | 크기 | 갱신 |
|----|------|------|
| proto/phase35/elbow_v3.mp4 | 11618657 (61.0s) | 08-08 11:38 |
| proto/phase35/powerspin_v3.mp4 | 5971614 (바이트 동일) | 08-08 11:38 |
| proto/phase35/pdshape_v3.mp4 | 11029938 (내용 동일) | 08-08 11:38 |
| proto/phase35/kipup_v3.mp4 | 4038006 (바이트 동일) | 08-08 11:38 |
| proto/phase35/peterpan_v3.mp4 | 6126766 (바이트 동일) | 08-08 11:38 |
| proto/phase35/realupload_v3.mp4 | 무접촉 | 08-07 21:22 유지 |

## 계획 대비 편차

1. **[실측>계획] Task 1 길이 기대치 중 peterpan 18s 는 stale** — S3 의 실제 v6 파일이 23.63s
   (재재생 꼬리 포함, 4e5737af 이후). baseline 5편 전부 S3 실파일과 0.00s 일치로 STOP 게이트의
   의도(승인 상태 재현 실증)를 계획의 ±2s 근사보다 강하게 충족 → 진행.
2. **[조임 2겹 추가] ① 폴-근접에 dwell + 접촉 특정성** — 계획 예시(pd r00)대로 초과 발동이
   실측됐고(r00·r01 둘 다), 계획이 허용한 "구조적 근거가 있는 조임"으로 해소. 상수는 기존
   마진(0.15) 재사용 + dwell 0.5s(그립 유지 0.2s 의 상위 스케일). 발동 프로브로 전 record 검증.
3. **[fail-closed] 묶음 2 미충족** — 위 섹션. 계획 ② 명문의 실패 경로.
4. **[게이트 순서] diff 게이트의 pdshapefault r01 조건을 2상태 허용으로 작성** — 계획 3-3 은
   grip 발동 전제였으나 ② fail-closed 가 계획 자신의 sanctioned 경로라 (a) align-grip 또는
   (b) 행 전체 불변 중 실상태를 판정·출력하도록 작성. 그 외 diff 1건이라도 있으면 FAIL 유지.

## 미검증 항목

| 항목 | 사유 |
|------|------|
| belle 실기기/실링크 재생 확인 | belle 심사 대기 (기계 판정은 전건 PASS) |
| 폴 감지의 타 촬영환경 일반화 | 파일럿 고정 카메라·수직 폴 가정 — 다른 각도/이동 카메라 미실측 |
| 그립 검출기의 발동 실증 | 이 데이터셋에선 전부 fail-closed — 실발동 사례 0 (코드 경로는 프로브로 검증) |

## 보드 갱신 필요

상태 보드 아티팩트(https://claude.ai/code/artifact/f8630d0f-c07f-4d82-943a-0fa272900b5f)는
이 환경에서 갱신 불가 — **v7 상태(5키 08-08 11:38 덮어씀, 엘보=폴 문법, pdshape r01 미충족)로
갱신 필요.**

## Self-Check: PASSED

- 커밋 존재 3/3: d266cb8d(데이터만, git show 로 data/ 한정 확인) / 7787832d(렌더러+quick 3파일) / 0f81316f(diff 게이트)
- 산출 파일 존재 5/5 (README·overrides·p35_audio·diff_reports·SUMMARY), data JSON 16/16
- 리그·추출 스크립트 무접촉: `git diff HEAD -- verify_render_prototype.py p35_extract_align.py` 빈 출력
- 태스크 커밋 구간 파일 삭제 0, 증거 스틸 2/2
- 동작명 리터럴 grep 0 / cv2 import 0 / ast.parse OK
