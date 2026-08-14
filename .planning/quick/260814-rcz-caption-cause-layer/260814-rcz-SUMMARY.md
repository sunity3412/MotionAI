---
phase: quick-260814-rcz
quick_id: 260814-rcz
slug: caption-cause-layer
date: 2026-08-14
status: complete
subsystem: 캡션 조립 · 카드 마크 표시 문법
tags: [caption, phrasebook, lockstep, fault-zoom, mark-gate, belle-judgment]

requires:
  - "belle 2026-08-14 발굴 판정 (DISCOVERY-LEDGER 판정 기입란)"
  - "quick-260814-ehz 후보 좌표·눈 원장 (cand17B / cand01E)"
  - "quick-260813-u8i 승인 카드 md5 정본 (현 HEAD 기준선)"
provides:
  - "DeductionRecord.causeLine — 원인 가설 절 (계약 4면 lockstep)"
  - "cue_text/deductionSheet 3절 조립 + 양엔진 실행 비교 프로브"
  - "fault_zoom.angle_mark_admissible — 각도 V 마크 적용 조건 게이트"
  - "MEASURE.md 마크 조건 실측표 + CAPTION-SHEET.md belle 판정 재료"
affects:
  - "합성 비교 영상 정지 자막 · Polly 음성 (문구 2건에 한해)"
  - "확대 비교 카드 마크 (cand01E 유형 1장에 한해)"

tech-stack:
  added: []
  patterns:
    - "양엔진 lockstep = 소스 눈대조가 아니라 node 로 TS 를 실제 실행해 문자 비교"
    - "임계는 판정 규칙을 표보다 먼저 커밋한 뒤 기계 적용 (curve-fit 구조 차단)"
    - "표시 억제는 기존 폴백으로 떨어뜨린다 — 새 표면 발명 0"

key-files:
  created:
    - backend/tests/test_caption_cause_layer.py
    - backend/tests/test_fault_zoom_angle_admissible.py
    - backend/tests/phase32/compose_cue_probe.mjs
    - .planning/quick/260814-rcz-caption-cause-layer/mark_gate_sweep.py
    - .planning/quick/260814-rcz-caption-cause-layer/candidate_render.py
    - .planning/quick/260814-rcz-caption-cause-layer/MEASURE.md
    - .planning/quick/260814-rcz-caption-cause-layer/CAPTION-SHEET.md
  modified:
    - backend/shared/python/sunity_shared/analysis/cue_text.py
    - backend/shared/python/sunity_shared/analysis/phrasebook.py
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/shared/python/sunity_shared/models.py
    - backend/data/phrasebook.json
    - app/src/lib/deductionSheet.ts
    - app/src/lib/userAnalyses.ts
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/tests/phase32/test_mission_contract_lockstep.py

decisions:
  - "원인 절 출처 = 승인 문구집 슬롯. LLM 생성 경로 0 (D-11 골격 소유 — 음성·자막은 하중이 가장 큰 표면이라 완화 불가)"
  - "causeLine 은 whyLine 재활용이 아니다 — whyLine 은 '왜 감점인가'(심사 언어), causeLine 은 '왜 그렇게 됐는가'(코칭 지식)"
  - "마크 조건 축 = A3(양 패널 사이각 절대차), 임계 99.6도 — 사전 규칙 기계 적용 결과"
  - "정본 정정: 승인 카드 md5 기준선은 nh4 가 아니라 u8i (nh4 는 pre-초라벨-수리)"
  - "3줄 초과 문구는 belle 원문 의미 안에서 축약 — 의미 훼손 여부는 belle 판정 항목으로 이관"

metrics:
  duration: "약 2시간 (세션 중단 1회 — 절전으로 API 끊김, Task 2 시작점에서 재개)"
  tasks_completed: 3
  commits: 6
  tests_added: 49
  completed: 2026-08-14
---

# quick-260814-rcz: 캡션 원인 절 + 각도 표기 적용 조건 Summary

belle 08-14 발굴 판정("발굴은 성립, 설명이 미달")의 처방 — 캡션에 **원인이 들어갈
자리**를 만들고 승인 문구로 채웠으며, 각도 V 마크를 그릴지 말지의 조건을 **재고
나서** 정해 배선했다.

## 무엇을 했나

### Task 1 — 캡션 원인 절 자리 신설 (TDD)

캡션은 `statusLine`(증상) + 행동절 **2문장 고정**이라 원인이 들어갈 자리가
구조적으로 없었다. 3절(증상 → 원인 → 행동)로 확장하되 **원인이 없으면 오늘과
문자 하나도 다르지 않게** 했다.

- `cue_text.coach_audio_speech_text` — 절 경계 규칙(마침표 + 공백, 중복 억제)을
  **공용 헬퍼로 승격**. 분기를 복제하지 않았으므로 belle 08-07 반려(Polly run-on
  낭독)의 방지가 새 이음매에서 뚫리지 않는다.
- `app/src/lib/deductionSheet.ts composeCueSubtitleKo` 동시 미러.
- 계약 4면 동시 갱신 — `models.DEDUCTION_PHRASE_KEYS` / `analysis.ts` /
  `contract.md §12.3` / lockstep 핀 테스트. 파이프라인
  `_attach_translation_emission` 은 이 tuple 을 돌기 때문에 **배선 코드 변경 0**
  으로 record 에 각인된다.
- `phrasebook.json` 기존 2 entry 에 `causeLine` 키만 추가(신규 entry 생성 0 —
  entry 단위 매칭이라 신규 entry 는 그 record 캡션을 통째로 날린다).

### Task 2 — 마크 조건 실측 (운영 코드 diff 0)

**판정 규칙을 표보다 먼저 커밋**(`02dfb35`)한 뒤 기계 적용했다. 커밋 순서가
curve-fit 방지의 증인이다.

승인 코퍼스에서 V 가 **실제로 그려진** 카드 8건 + belle 채택 cand17B(= P, 9건)
vs belle 반려 cand01E(= N, 1건)의 px 사이각을 운영 함수 `_spec_inner_deg_px` 로
전건 실측 → A1/A4ref/A5/A6 분리 없음, A2/A4user 마진 부족 기각,
**A3(양 패널 사이각 절대차) 채택 · 임계 99.6도**.

### Task 3 — 게이트 배선 + 무회귀 + belle 재료

- `angle_mark_admissible()` 순수 함수 + 진입점 1곳(shift 직후 = 실제로 그려질
  좌표). 하이브리드가 쓰던 사이각 계산과 공유해 **중복 계산 0**.
- 미충족이면 `angle_reason` 만 채우고 드로잉 skip → **기존 원 마커 폴백**으로
  자연히 떨어진다(분기 무변경, 새 표면 0). 못 재면 **fail-open**.
- CAPTION-SHEET.md + `/Users/Shared/sunity-caption-cause-260814/` (카드 5장 + 안내).

## 기계 증명

| 게이트 | 결과 |
|---|---|
| 원인 없는 record 캡션 | 문구집 **65 entry 전건 byte-동일** (동결 사본 대조 — 구현끼리 비교하는 동어반복 회피) |
| 음성 = 자막 | **양엔진 실행 비교** PASS. node 로 `deductionSheet.ts` 를 실제 실행한 산출과 python 산출이 fixture 전건 문자 동일 (skip 아님) |
| 승인 카드 무회귀 | 패치 전/후 **10/10 md5 동일** (u8i 정본) · survivors/dropped 전건 일치 · hold 9/9 pair 9/9 |
| belle 채택분 | cand17B md5 **동일** — 픽셀 한 점 안 바뀜 |
| 반려분만 변경 | cand01E md5 변경 + 운영 로그 `angle_bake=omitted:panel_diff_114.4` + **PNG 육안 확인**(V 소멸, 원 마커 폴백) |
| 자막 3줄 상한 | 시드 2건 3줄 이내 · 문구집 67 entry 전건 3줄 이내 (테스트 고정) |
| pytest | **59 failed 동일**(기준선) / 4298 → **4347 passed** |
| typecheck | PASS |
| 채점 산식 5파일 | diff **0** |

## 발견 (보고할 것)

### ① 정본이 nh4 가 아니라 u8i 였다 — 실측으로 정정

플랜은 nh4 `sweep_verdict_port.json` 을 "현 HEAD 정본"으로 지목했는데 실행하니
**10/10 전건 불일치**였다. 원인은 nh4(08-13) **이후** 들어온 u8i 의 카드 초 라벨
수리(÷9.0 → `label_fps` 실효 fps)다 — 카드에 구워지는 초 문자가 바뀌었으니
픽셀이 바뀌는 것이 옳다. u8i 정본과 대조하면 **10/10 일치**.

측정을 밀어붙이지 않고 원인을 먼저 실측한 것이 맞았다. 이 일치는 동시에
**관측 래퍼가 픽셀을 바꾸지 않는다**는 증거이기도 하다(래퍼를 단 채 byte-동일).

### ② 원안 캡션은 자막 3줄을 넘겼다 — 축약했고, 의미 판정은 belle 몫

플랜이 예시로 쓴 문구는 **둘 다 4줄**이었다(pdshape 134자 / powerspin 148자).
`wrap_text(...)[:3]` 이 4번째 줄을 조용히 버리므로 그대로 갔으면 **행동절이
사라져** 2026-08-01 반려가 재발했다.

belle 원문 의미 안에서 축약했다 — pdshape 62→51자, powerspin 50→34자. 덜어낸
것은 수식어이고 원인 자체는 남겼지만, **의미가 상했는지는 belle 만 판정할 수
있으므로** CAPTION-SHEET §4-a 로 올렸다.

부수 실측: powerspin 왼어깨는 **구 캡션이 이미 3줄**이었다(96자). 문구집 67
entry 중 12건이 이미 3줄이라 이들에 원인 절을 붙이려면 같은 축약 작업이 필요하다.

### ③ "한쪽 패널이 직선이다"는 억제 근거가 못 된다

직관적으로는 "한쪽이 직선이면 각도로 안 읽히니 지운다"가 맞아 보였는데, 실측이
그 축(A2 / A4user)을 **마진 1.53 < 필요 16.81** 로 기각했다. 반례가
`pdshapefault/right_elbow` 다 — user 177.4도(거의 직선)인데 ref 도 167.0도라
**양쪽이 함께 직선**이고 belle 이 통과시켰다. 갈리는 것은 **불일치**뿐이다.

## 알려진 한계 (belle 판정 재료에 그대로 게재)

1. **반려 표본 = 1건**(cand01E). 어떤 규칙이든 반례 1개에 맞춘 것이고 구조적
   과적합 위험이 남는다.
2. **임계 여유 14.77도** — 가장 가까운 통과 카드(84.85)와 임계(99.6) 사이.
   85~99 구간은 미검증 영역이다.
3. **통과집합의 다수는 belle 이 현 형태로 아직 못 본 카드**다. 08-13 스윕 판정
   때 V 가 실제로 그려진 카드는 2장뿐이었고 nh4 의 B 이식 뒤 8장이 됐다.
4. **영상 재렌더 미실행** — 캡션이 실제로 나가는 자리는 합성 영상 정지 자막과
   Polly 음성이고 그 재렌더는 별건(chd 선례)이다. 이번 사이클은 문장과 배선까지.
5. **`rootCauseHypotheses` 재활용 이월** — coach_writer 의 원인 사슬은 분석 전체
   수준이라 record 에 귀속되지 않는다. 이번 스코프 밖으로 두었다.

## 이번 사이클에 하지 않은 것 (제약 준수 실측)

| 제약 | 결과 |
|---|---|
| Pod 접촉 | **0** — 전 구간 로컬 replay (GPU 는 학습 중) |
| S3 업로드 | **0** — 읽기만, 영상은 현 세션 scratchpad 캐시 재사용 |
| Firestore 쓰기 | **0** — refmotion 은 캐시 시딩으로 조회조차 0 |
| Gemini 실호출 | **0** — 승인 스윕은 xa1 눈 스텁(6회), 후보는 ehz **실측 판정 재생**(2회). 지어낸 값 0, 원장 미보유 조회는 fail-closed |
| 앱 카드 UI | 무변경 — causeLine 은 자막 조립에서만 소비 |
| 이모지 | 0 (`★`/`⚠` 는 이 리포의 기존 표기 관례, 변경 전부터 존재) |

## LLM 학습 영향

- **추론 호출**: 이번 사이클 **0회**. Gemini(기계 눈) 실호출 0, Cerebras(코치
  문장 생성) 호출 0, Polly(TTS, 비-LLM) 0.
- **학습 전송**: **0**. 어떤 사용자 데이터·영상·판정도 외부 모델 학습에
  제공되지 않았다.
- **원인 문구의 생산 방식**: 이번에 추가한 캡션 2건은 **LLM 이 만들지 않았다**.
  belle 원문의 사람 전사이며 승인 문구집이 소유한다. 이것은 비용 문제가 아니라
  D-11 골격 소유 원칙이다 — 음성·자막은 사용자가 가장 신뢰를 거는 표면이라
  생성 경로를 열면 "무릎을 더 펴세요" 류 일반론이 그 자리로 들어온다.
- **누적 원장**: 신규 눈 원장 항목 **0건**(재생만 했으므로 새 판정 없음).
  Phase22 씨앗 코퍼스 증가분 없음.

## 다음

1. **belle 판정 4항** (CAPTION-SHEET §4) — 문면 승인 / 전형 설명 일반화 가부 /
   억제 시 폴백 형태 / 임계를 지금 넣을지 vs 선언 억제 표로 갈지.
2. 판정 통과 시 — 영상 재렌더 사이클(정지 자막·Polly 재합성)에서 새 캡션 반영.
3. 이미 3줄인 12 entry 에 원인 절을 확장하려면 같은 축약 라운드가 필요하다.

## Self-Check: PASSED

- 산출 파일 12/12 FOUND
- 커밋 6/6 FOUND (`23901b81` `5aff1263` `02dfb35` `b9610f5` `1cd55ba` `f8af2e8`)
- 스텁 0건 (신규 코드에 TODO/FIXME/placeholder 유입 없음 — 검출된 placeholder 는
  전부 이번 변경과 무관한 기존 라인)
