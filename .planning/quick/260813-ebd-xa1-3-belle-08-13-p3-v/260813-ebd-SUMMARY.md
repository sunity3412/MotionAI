---
quick_id: 260813-ebd
slug: xa1-3-belle-08-13-p3-v
completed: 2026-08-13
commits:
  - 2631fde7 docs(quick-260813-ebd) JUDGMENT.md 라운드 3 절 — belle 08-13 번복 판정 박제
  - 5063a1aa feat(quick-260813-ebd) 라운드 3 하네스 + P3r1/EV1-EV3 렌더 — 베이스라인 게이트 PASS
  - 6a57d478 feat(quick-260813-ebd) EV4/EV5 오프셋 V 추가 — EV1~EV3 제자리 클리핑 붕괴 실측 수리
  - a239ccb4 docs(quick-260813-ebd) 라운드 3 육안 판정 + 사전 박제 — 추천 EV5
---

# 260813-ebd Summary — xa1 라운드 3 (belle 08-13 번복 판정 + P3r1/EV 변형안)

**한 줄**: belle 08-13 번복 판정(D-01 스포트라이트 철회 / D-02 골반 P3 채택 /
D-03 팔꿈치 V+얼굴회피)을 장부에 박제하고, 반려 freeze 실물(베이스라인 md5
게이트 PASS)에서 P3r1 좌표 수리 재렌더 + 팔꿈치 변형안 5안을 산출 — 제자리
계열(EV1~EV3)은 원반 클리핑으로 전부 붕괴함을 실측 박제하고, belle 원문
"위치 보정" 직해인 오프셋 V(EV4/EV5)가 성립, 추천 = EV5. 운영 코드 diff 0,
Gemini 실호출 0.

## 기계 판정

- **베이스라인 게이트 PASS** (실행 로그 증명): 무패치 렌더 md5 2/2 == ufb
  인증값 (left_elbow `9891d281…`, left_hip `8e147209…`) + survivors
  `['r03:inherit@u16.667/r15.20', 'r00:inherit@u5.302/r5.13']` 일치 — 캐시
  재수화(`verify_local.py --fetch`, 읽기 전용) 후에도 반려 실물과 동일 경로.
- **후보 6/6 방출 (CANDIDATES-R3 PASS)**: P3r1 + EV1~EV5, 후보별 비대상 카드
  md5 == 인증값(무누출) + survivors 불변 —
  `out/candidates/render_summary_round3.json` 박제 (좌표 px·이동량·노트 포함).
- **좌표 단일 출처**: 전 후보 vertex = `refine_round._R2Patch._gate_moment_px`
  상속 (align 17-kp @ round(freeze_sec x align_fps), conf >= 0.5, fail-closed).
  방향점 = bake spec 평행이동 (V 사이각·방향 보존). fps 라벨 사슬(`_to_rep_idx`)
  경유 0.
- **P3r1 앵커 이동 실측 = user 1.6px / ref 8.7px** — 라운드 2 진단 예측
  (user ~1.6 / ref ~8.7) 적중.
- **무접촉**: `git status --porcelain -- backend/` 빈 출력. xa1 디렉터리는
  JUDGMENT.md append 만 (기존 절 byte 무변경, out/baseline 재실행 산출물
  byte-동일 = git 무변화).

## 육안 판정 (frames-before-numbers — 개별 원본 + 확대 크롭, 몽타주 금지)

크롭 실물 = `out/crops/` (EV1~EV3 팔꿈치 확대, EV4/EV5 얼굴 영역 확대).

| 안 | ① 얼굴·머리 관통 | ② 마크가 관절 위 | ③ V(2가닥+사이각) 읽힘 |
|---|---|---|---|
| P3r1 | 해당 없음 (뒷모습, 마크 = 골반·등 영역) | 예 (양 패널 왼골반 위) | 예 (채택 하이브리드 문법 그대로) |
| EV1 | 0 | 예 (링) | **아니오** — user 마이크로 스텁 1개, ref 링만 |
| EV2 | 0 | 예 (링) | **아니오** — EV1 과 사실상 동일 |
| EV3 | 0 | 예 (링) | **아니오** — EV2 와 md5 동일 (byte-identical) |
| EV4 | 0 (얼굴 크롭 확인 + 기계 검증) | 예 (링+리더) | 예 — 단 글리프가 작아 호·벌어짐 약함 |
| EV5 | 0 (얼굴 크롭 확인 + 기계 검증) | 예 (링+리더) | **예 — 가장 명확** (두 가닥+호 뚜렷) |

관통 실물 0 — 수리·재렌더 필요 케이스 없음. EV1~EV3 은 관통이 아니라 **V 문법
소멸**로 미성립 박제 (아래 자평).

## 변형안별 자평 (belle 제시 전 사전 박제 재료)

- **P3r1** — 강점: D-02 채택 문법을 바이트 하나 안 바꾸고 앵커만 align 단일
  출처로 수리 (운영 이식 시 좌표 계약이 이것). 한계: 이동이 작아(특히 user
  1.6px) 승인 실물과의 차이는 belle 육안에서 미세하게 보일 것 — 재확인 대상.
- **EV1 (관절 도달 선)** — 강점: "선이 관절에 닿지 않는다" 진단의 정공법.
  한계: 이 freeze 에선 vertex 가 원반 가장자리 ~5px 밖이라 도달 경로 전체가
  원반 통과 — 클리핑 후 V 소멸. **미성립, 한계 증거로만 제시.**
- **EV2 (팔길이 비례)** — 강점: 스텁이 허공에서 끝나는 병의 직접 수리. 한계:
  같은 이유로 붕괴, EV1 과 사실상 동일 픽셀. **미성립, 제시 제외.**
- **EV3 (E1 연장)** — 강점: belle 가 본 E1 의 최소 변경 연장. 한계: 연장분이
  전부 원반 안이라 EV2 와 byte-identical. **미성립, 제시 제외.**
- **EV4 (오프셋 V 기본)** — 강점: 관통 0 이 기계 검증되면서 V 사이각·방향이
  온전히 남는 첫 성립안. 한계: 기본 길이 글리프가 작아 호가 거의 안 보임 —
  "굽음"의 양이 약하게 읽힌다.
- **EV5 (오프셋 V x1.6) — 추천**: 두 가닥과 호가 명확히 갈라져 채택 문법의
  정보가 실물에서 즉시 읽힘, belle "E1보다 길어도 됨"과 정합. 한계 (공통
  박제): user 패널 limb 가닥이 원반 밖 흘러내린 머리카락 끝단 위를 일부 지남
  (E2 선례) + 오프셋 글리프는 직접 표시보다 한 단계 간접적 — 최종 부위 확정은
  링·리더·캡션이 진다.

추천 근거는 이 freeze 실물 1건 관찰 — 비역립 국면의 제자리/오프셋 전환 규칙은
미측정, 운영 이식 시 결정 사항 (JUDGMENT 라운드 3 절 명기).

## 보드 라운드 3 게시 재료 (게시 = 오케스트레이터 몫)

이미지 절대경로 + 캡션 (각도 수치 미노출·이모지 금지·신뢰 표기 관례):

1. `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/P3r1/zoom_angle_vs_reference__left_hip.png`
   — **골반 P3r1 (채택본 좌표 수리, 재확인 요청)**: "실선 두 가닥이 지금 자세,
   점선이 기준 자세의 허벅지 방향이에요. 부채꼴만큼 골반을 열어 상체와의
   정렬을 기준에 맞춰 주세요 · 신뢰 높음" (채택 P3 캡션 그대로 — 바뀐 것은
   앵커 좌표뿐)
2. `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/EV1/zoom_angle_vs_reference__left_elbow.png`
   — **팔꿈치 EV1 (판정 대상 아님 — 한계 증거)**: 제자리 V 는 이 장면에서
   얼굴 회피 규칙과 양립하지 않습니다 — 관절 방향 선이 전부 얼굴 원반에 즉시
   진입해 클리핑 후 링만 남습니다 (EV2·EV3 도 동일 픽셀로 붕괴).
3. `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/EV4/zoom_angle_vs_reference__left_elbow.png`
   — **팔꿈치 EV4 (오프셋 V, 기본 길이)**: "링이 왼팔꿈치이고, 점선으로
   이어진 V 가 그 팔꿈치가 굽은 모양이에요. 왼팔꿈치가 폴에서 떨어져 있어요 —
   폴 쪽으로 당겨 붙여 주세요 · 신뢰 높음"
4. `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-ebd-xa1-3-belle-08-13-p3-v/out/candidates/EV5/zoom_angle_vs_reference__left_elbow.png`
   — **팔꿈치 EV5 (오프셋 V, 연장 — 추천)**: 캡션은 EV4 와 동일. 차이는 V
   글리프 길이뿐 — 두 가닥과 호가 더 명확히 읽힙니다.

/Users/Shared 한글 사본 (belle 로컬 확인용): `/Users/Shared/sunity-mark-candidates-260813/`
— `골반-P3r1-기존V자-좌표수리.png` · `팔꿈치-EV1-관절도달선-클리핑붕괴-한계증거.png`
· `팔꿈치-EV4-오프셋V-기본길이.png` · `팔꿈치-EV5-오프셋V-연장1.6배-추천.png`

## Deviations

- **[Rule 3] fetch 에 FIREBASE_SA_PATH 주입**: `verify_local.py --fetch` 가
  Firestore Admin 자격 부재로 실패 → 리포 실물 `firebase-sa.json` 을
  `FIREBASE_SA_PATH` env 로 주입해 해소 (읽기 전용, 코드 변경 0).
- **[Rule 1] EV4/EV5 오프셋 V 추가 (플랜 ①②③ 밖 설계)**: 플랜의 제자리
  계열 3안이 렌더 실측에서 전부 동일 픽셀로 붕괴 (EV2==EV3 md5 동일 — vertex
  가 원반 가장자리 ~5px 밖이라 모든 관절 방향 선이 즉시 클리핑, V 미성립).
  동일 붕괴 카드 3장은 판정 재료가 성립하지 않아, belle D-03 원문 "위치
  보정"의 직해(V 글리프 오프셋 배치 + 링 + 리더)로 2안을 추가 — 좌표 출처·
  원반 규칙은 전 안 공통 유지, 글리프 전 샘플의 원반 밖을 기계 검증.
  EV1~EV3 은 폐기하지 않고 미성립 박제 (커밋 6a57d478).

## LLM 학습 영향

**없음.** 이번 라운드 Gemini 실호출 0 — `machine_eye` 드라이버 프로세스 한정
스텁 (env 더미 키로 SSM 미조회, 최종 실행 스텁 카운트 14회 = 전부 스텁), 학습
전송 0, 기계 눈 원장 신규 적재 0 (스텁 산출물은 xa1 out/_ev 비커밋 영역 한정).

## Self-Check: PASSED

- 산출물 존재: round3.py / .gitignore / out/candidates/{P3r1,EV1..EV5} PNG 6장
  + render_summary_round3.json / out/crops 10장 / JUDGMENT.md 라운드 3 절
  (번복 박제 + 육안 + 사전 박제 추천) / /Users/Shared 한글 사본 4장
- 커밋 존재: 2631fde7 / 5063a1aa / 6a57d478 / a239ccb4 — 파일 삭제 0
- 게이트: BASELINE GATE PASS + CANDIDATES-R3 PASS (6/6) 실행 로그로 증명,
  backend/ diff 0, 미추적 잔여 = PLAN/SUMMARY 만 (오케스트레이터 docs 커밋 몫)

## 다음 (이 라운드 완료 정의 아님)

- belle 판정: P3r1 재확인 + 팔꿈치 EV4/EV5 (추천 EV5). 통과 시 운영 배선
  사이클 별도 (표시 좌표 단일 출처 근본 수리 + 오프셋/제자리 전환 규칙 결정 +
  승인 5동작 무회귀 + 새 Pod 실증).
