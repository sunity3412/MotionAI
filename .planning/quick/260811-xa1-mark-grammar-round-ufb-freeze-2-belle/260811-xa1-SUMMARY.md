---
quick_id: 260811-xa1
slug: mark-grammar-round-ufb-freeze-2-belle
completed: 2026-08-12
commits:
  - 45e0f2c8 feat(quick-260811-xa1) 하네스 + 베이스라인 게이트 + 후보 6안 렌더
  - (Task 2 커밋) docs(quick-260811-xa1) JUDGMENT.md 판정지
---

# 260811-xa1 Summary — 마크 문법 후보 라운드 (ufb freeze 2카드)

**한 줄**: belle 반려 2카드(왼골반 16.7s 마크 반려 · 왼팔꿈치 5.3s 부위 특정 불가)의
표시 문법 후보 6안을 **반려된 그 freeze 순간의 실물**로 산출하고 (베이스라인 md5
2/2 == ufb 인증값 + survivors 일치 기계 증명), 캡션·추천을 담은 판정지
`JUDGMENT.md` 1장을 belle 께 낸다 — 운영 코드 diff 0, Gemini 호출 0.

## 기계 판정

- **베이스라인 게이트 PASS**: 무패치 렌더 md5 — left_elbow
  `9891d2811eb9dcb7925bcf229831f19b`, left_hip `8e1472097f8a7c2acf3834dfdaf2c78f`
  (ufb `run_verdict.json` 인증값과 2/2 일치) + survivors
  `['r03:inherit@u16.667/r15.20', 'r00:inherit@u5.302/r5.13']` 일치 —
  이 하네스 경로 = belle 이 반려한 실물과 동일 경로 (LD-2 순간 무변경 증명).
  `out/baseline/gate.json` 박제.
- **후보 6/6 방출**: left_hip P1/P2/P3 + left_elbow E1/E2/E3, 후보별 run 에서
  **비대상 카드 md5 == 인증값**(무누출) + survivors 불변. Task 1 automated
  verify = `GATE-PASS` (PNG 6장 + `git status --porcelain -- backend/` 빈 출력).
- **Gemini 0회**: `card_gates.machine_eye` 드라이버 프로세스 한정 스텁 (env 더미
  키로 SSM 미조회). 하네스 출력에 eye 스텁 카운트 명기 (baseline 2회 / candidates
  12회 — 전부 스텁). ufb evidence 는 `vl.EV` 리다이렉트 + assert 가드로 무접촉
  (T-xa1-02).

## 후보 6안 요약 (근거·캡션·관찰 정본 = JUDGMENT.md)

| 안 | 카드 | 문법 | 실물 관찰 요지 |
|---|---|---|---|
| P1 | 왼골반 | 단일선 + vertex 링 (양 패널) | 깨끗하나 두 패널 선 방향이 비슷해 차이는 캡션 몫 |
| P2 | 왼골반 | 단일선 + 기준각 쐐기 + 화살촉 | 쐐기·화살촉이 교정 방향을 마크로 답함 — **추천** |
| P3 | 왼골반 | bz5 하이브리드 그대로 | 반려된 V 2가닥 잔존 + 요소 최다 |
| E1 | 왼팔꿈치 | 현행 2가닥 + 머리 원반 클리핑 | 얼굴 관통 0 성립, 대신 각도 문법이 스텁으로 소멸 |
| E2 | 왼팔꿈치 | vertex 링 + 폴 축선 + 간격 브래킷 | 얼굴 관통 0, 단 브래킷이 원반 밖 머리카락과 일부 겹침 + 이 freeze 는 기준 패널 간격도 커 보여 대조가 안 갈림 |
| E3 | 왼팔꿈치 | 스포트라이트(원 밖 44% 감광) + 링 | 관통 0 구조적 성립, 부위 특정 즉시 — **추천** |

## 육안 판정 (LD-5 — 몽타주 금지, 개별 원본 8장 Read)

베이스라인 2장 + 후보 6장을 한 장씩 개별로 열어 확인 (E1/E2/E3 는 얼굴 영역
확대 크롭 추가 확인). **왼팔꿈치 후보 3안 전부 얼굴/머리 관통 0 육안 성립**:

- E1: 얼굴을 관통하던 몸통측 선이 머리 원반 경계 앞 스텁으로 잘리고 호 생략,
  팔뚝 선은 팔뚝 실물 위 — 얼굴/눈/코 위 마크 픽셀 0.
- E2: 폴 축선 점선이 머리 원반 구간에서 끊김, 브래킷은 얼굴 아래 배치 — 얼굴
  관통 0. 원반 밖으로 흘러내린 포니테일 다발 위를 브래킷이 일부 지나는 것은
  실측 그대로 판정지에 명기 (완전 비겹침은 이 국면에서 E3 계열만 가능).
- E3: 선/도형 0 — 원 밖 감광뿐이라 관통이 원리적으로 불가. 픽셀 실측으로 원 안
  원본 보존 / 원 밖 약 44% 감광 확인. 링은 팔꿈치 위 (관통 선 없음).

머리 원반 추정 = 플랜 옵션 ① (align 17-kp 트랙 nose/eyes/ears 를 카드 크롭
좌표로 투영, user r=61px / ref r=83px) — 옵션 ② (12관절 어깨/골반 연장)는 역립
freeze 프레임에서 conf 게이트 탈락으로 불성립이라 폴백으로만 유지.

## Deviations

- **[Rule 3] 인터프리터 자동 승격**: 시스템 python3 에 imageio 부재 →
  `grammar_round.py` 가 backend/.venv 로 스스로 재실행 (env 마커 루프 가드).
  신규 패키지 설치 0 (T-xa1-SC 준수). 플랜 verify 커맨드(`python3 ...`)는
  그대로 성립.
- **[Rule 1] E1 1차 머리 추정 실패 → 옵션 ① 전환**: 휴리스틱 ② 단독으로는
  역립 프레임에서 어깨/골반 conf 게이트 탈락 → E1 이 베이스라인과 동일 픽셀
  (changed=False 게이트가 잡음). 플랜이 선택지로 명기한 옵션 ①(align 17-kp
  투영)로 전환해 해소 — 순간·경로 변경 없음.

## 무접촉 증명

- 운영 코드: `git status --porcelain -- backend/` 빈 출력 (staged 포함).
- ufb/bz5 디렉터리: 읽기 전용 재사용만 (importlib 로드) — diff 0.
- 채점: 렌더 드로잉 monkeypatch 만 — records/점수 무접촉.

## LLM 학습 영향

**없음.** 이번 라운드 Gemini 호출 0 (machine_eye 스텁) — 학습 전송 0, 기계 눈
원장 신규 0 (스텁 산출물은 원장 아님, 리포 비커밋 영역 out/_ev 한정).

## 다음 (이 라운드 완료 정의 아님)

- **belle 판정 대기**: JUDGMENT.md 로 카드 2장 × 후보 3안 + 캡션 판정. 내 추천 =
  P2(왼골반) / E3(왼팔꿈치), 근거는 실물 관찰만.
- 채택 시 운영 이식 + Pod 실증은 별도 사이클 (이 라운드는 산출만, 배선 없음).
- E2 실측 특기: 이 freeze 에선 기준 패널 팔꿈치-폴 간격도 커 보임 — "엘보 = 폴
  근접도" 문법의 카드 실물 성립 여부는 belle 판정 재료로 넘김.

## Self-Check: PASSED

- 산출물 13개 파일 전부 존재 (하네스 + 판정지 + SUMMARY + 베이스라인 2 +
  gate.json + 후보 6 + render_summary.json)
- 커밋 45e0f2c8 (Task 1) / adc749c5 (Task 2) 존재, 파일 삭제 0
- 미추적 잔여 = PLAN/SUMMARY 만 (오케스트레이터 docs 커밋 몫), backend/ diff 0

---

# 라운드 2 — 정제 (2026-08-12, belle 판정 스펙 직접 실행)

**한 줄**: E3 채택 후 정제 — ref 원이 벗어난 뿌리를 실물 추적으로 **fps 라벨
사슬의 1프레임 이른 인덱스**(트랙 간 차이가 아님)로 규명하고, 원 좌표 출처를
align 17-kp **게이트 freeze 순간**(게이트/기계눈과 같은 공식)으로 교체한
E3-r1 + 같은 원칙의 골반 스포트라이트 P4 를 산출 — 픽셀 오프셋 0, 운영 코드
diff 0, Gemini 0회.

## 기계 판정

- **베이스라인 게이트 재실행 PASS**: md5 2/2 == ufb 인증값 + survivors 일치
  (라운드 1 과 동일 경로 재증명).
- **진단 렌더**: 후보 좌표 3종(12관절 rep / align 선형 인덱스 / align 게이트
  순간) 마커 오버레이 + 트랙 정합 실측 — `out/diagnose/` (survivors 불변).
  실측 요지: ref 에서 rep12 와 align17 은 같은 인덱스에서 2.5px 일치 (같은
  237프레임 시퀀스, 선형 매핑 평균 35px vs fps 라벨 매핑 191px), 어긋난 것은
  rep fps 라벨(18)이 실효(~14.9)와 다른 사슬이 고른 **인덱스**. 팔 스윕
  ~600px/s 순간이라 1프레임 = 원이 관절 밖으로.
- **후보 2/2 방출 (CANDIDATES-R2 PASS)**: E3r1/P4 — 비대상 카드 md5 == 인증값
  (무누출) + survivors 불변 (`out/candidates/render_summary_round2.json`).

## 육안 판정 (개별 원본 + 확대 크롭)

- **E3-r1 ref 원이 팔꿈치 위인가 — 예** (명시 판정). 보정 전 = 팔 실루엣 밖 흰
  벽 위 / 보정 후 = 팔꿈치 굽이 위 (첨점 대비 잔여 ~10px = 표시 프레임 skew
  몫, JUDGMENT 잔여 한계 절). user 패널 무회귀. 사전 박제 예측("굽이 가장자리
  도달 + 잔여 ~10px") 적중.
- **P4**: 두 패널 링이 골반 위, 관통 0. 중심 이동 user 1.6px / ref 8.7px —
  belle 장면 PASS 위치 유지.
- **선 앵커 진단 (수리 없음)**: 골반 앵커는 정확 (3원천 9px 클러스터) — P1~P3
  반려 원인은 앵커가 아니라 선 문법 (고정 길이 방향 스텁이 관절에 닿지 않고
  허공에서 끝남 + 이 freeze 사이각 7.3°/18.5° 로 V 가 선 하나로 읽힘).

## Deviations

- 없음 — 스펙의 "좌표 출처 교체" 원칙 그대로. 단 스펙이 가정한 "트랙 출처
  교체"가 아니라 실측이 가리킨 "인덱스 공식 교체"(같은 출처-레벨 수리)로
  귀결 — 근거는 JUDGMENT 라운드 2 절 + `out/diagnose/diagnose.json`.

## LLM 학습 영향

**없음.** Gemini 호출 0 (machine_eye 스텁 유지) — 학습 전송 0, 눈 원장 신규 0.

## 다음 (belle 판정 대기)

- E3-r1 / P4 판정 + before_after 비교 (`out/candidates/E3r1/before_after.png`).
- 다음 라운드 후보 입력 2건: ① 표시 프레임 skew (±1프레임) 근본 수리 = 표시
  프레임도 게이트 순간에서 선택 (운영 이식 시 결정), ② 선 문법을 살리려면
  관절까지 닿는 선 + 각도 시각 재료 필요 (JUDGMENT 진단 절).

## Self-Check (라운드 2): PASSED

- refine_round.py + out/diagnose/ (카드 2 + diagnose.json) + out/candidates/
  E3r1/ (카드 + before_after) + P4/ (카드) + render_summary_round2.json 존재
- 베이스라인/진단/후보 전 단계 survivors == ufb 인증값, backend/ diff 0
