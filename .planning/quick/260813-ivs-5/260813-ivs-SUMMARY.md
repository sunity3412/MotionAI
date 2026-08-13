---
phase: quick-260813-ivs
plan: "01"
subsystem: fault-zoom-display
tags: [sweep-render, mark-grammar, display-anchor, approved-corpus, frames-before-numbers]
requires: [quick-260813-fxx, quick-260811-ufb, quick-260811-xa1, quick-260811-ii0]
provides:
  - 승인 5동작 새 선 문법 스윕 카드 실물 8장 + 침묵 5건 사유 실측
  - 동작 x 관절 전수 현황표 (STATUS.md) + 육안 판정 사전 박제 (EYE-VERDICT.md)
  - /Users/Shared/sunity-sweep-260813 한글 사본 + 보드 게시 재료
affects: [마크 미세조정 라운드 (belle 판정 후)]
key-files:
  created:
    - .planning/quick/260813-ivs-5/sweep_render.py
    - .planning/quick/260813-ivs-5/evidence/sweep_verdict.json
    - .planning/quick/260813-ivs-5/evidence/measure.json
    - .planning/quick/260813-ivs-5/evidence/sweep_cards/ (카드 8 + 눈 스텁 산출물)
    - .planning/quick/260813-ivs-5/STATUS.md
    - .planning/quick/260813-ivs-5/EYE-VERDICT.md
  modified: []
decisions:
  - "verify 의 displayAnchorDrops=0 가정은 코퍼스 실측으로 반증 — drop 1건(정직한 침묵)을 정합성 검증으로 대체 박제"
metrics:
  duration: ~35min
  completed: 2026-08-13
---

# quick-260813-ivs: 승인 5동작 새 문법 스윕 렌더 Summary

**한 줄**: 무패치 운영 헬퍼로 승인 5동작 전체 스윕 — 카드 8장 방출(freeze 정본 전건 일치)
/침묵 5건 사유 실측, 단 **새 V 문법 실물은 2장뿐이고 둘 다 실눈 기각 이력 record**,
골반 P3 하이브리드 실물 0 (hip 카드 방출 0) — 미세조정 라운드의 실제 의제는 마크 길이가
아니라 rep12 스펙 게이트가 V 를 죽이는 빈도임이 드러남.

## 방출/침묵 집계 (sweep_verdict.json)

| 동작 | 생존 | 방출 카드 | 침묵 (사유) |
|---|---|---|---|
| elbow | 3 | 1 (오른팔꿈치, 원) | 2 — display_anchor drop(r01 user conf 미달) + rep12 양측 신뢰 0(r03) / dropped 1 (r02 pair=pose_far) |
| kipup | 1 | 1 (다리사이각, legs) | 0 |
| pdshapefault | 4 | 4 (V 1 + 원 3) | 0 |
| peterpan | 1 | 1 (왼어깨, V) | 0 |
| powerspin | 2 | 1 (다리뻗기, 원) | 1 — rep12 양측 신뢰 0(r02) / dropped 1 (r01 no_freeze) |

freeze-match: **위반 0** (survivors @u/r == ii0 probes.log 정본, 순간 발명 0).
침묵 = 전부 정직한 침묵 (방출 0 은 결함 아님 — 사유 문자열 그대로 STATUS.md).

## 보드 게시 재료 (게시는 오케스트레이터 몫 — 캡션에 각도 수치 없음)

| 이미지 절대경로 | 캡션 |
|---|---|
| /Users/Shared/sunity-sweep-260813/엘보트위스트_오른팔꿈치_u11.1s.png | 엘보트위스트 오른팔꿈치 — freeze u11.1/r12.1s, 원 앵커 양패널 (V 미베이크: user 스펙 게이트), 크롭 중심 = align freeze 좌표 실적용 |
| /Users/Shared/sunity-sweep-260813/킵업_다리사이각_u1.5s.png | 킵업 다리 벌림 — freeze u1.5/r2.0s, legs 문법 (골반 꼭짓점 + 양다리 선 + 호), 8장 중 즉시 읽힘 최상 |
| /Users/Shared/sunity-sweep-260813/피디쉐입_오른팔꿈치_u1.2s.png | 피디쉐입 오른팔꿈치 — freeze u1.2/r0.8s, 새 V 양패널 실물. 단 저사이각 + 폴 축과 겹쳐 선 하나로 읽힘 (사전 박제), 08-11 실눈 기각 이력 record |
| /Users/Shared/sunity-sweep-260813/피디쉐입_왼어깨_u3.2s.png | 피디쉐입 왼어깨 — freeze u3.2/r2.0s, 원 앵커 양패널, 국면 정합 양호 |
| /Users/Shared/sunity-sweep-260813/피디쉐입_왼무릎_u3.7s.png | 피디쉐입 왼무릎 — freeze u3.7/r2.4s, user 원만 (ref relaxed 무마크), 짝 화면감 상이 사전 박제 |
| /Users/Shared/sunity-sweep-260813/피디쉐입_왼팔꿈치_u8.6s.png | 피디쉐입 왼팔꿈치 — freeze u8.6/r9.4s, user 원만 (ref relaxed 무마크), 원이 역립 얼굴을 둘러쌈 (가림 계열 사전 박제) |
| /Users/Shared/sunity-sweep-260813/피터팬_왼어깨_u6.4s.png | 피터팬 왼어깨 — freeze u6.4/r7.6s, 새 V 양패널 실물. user 원본 저해상(부위/패널 71%)으로 흐림, 위 가닥 머리카락 통과는 fxx 기결론(V 유지) 인용, 08-11 실눈 기각 이력 record |
| /Users/Shared/sunity-sweep-260813/파워스핀_다리뻗기_u5.7s.png | 파워스핀 다리 뻗기 — freeze u5.7/r8.7s, 원 앵커 양패널, legs 카드 크롭 비대칭 (user 42 vs ref 68% — shared_frac 적용 범위 밖) 사전 박제 |

## STATUS / EYE-VERDICT 요지

- **align 단일 출처 좌표 실적용 = 8장 중 3장** (elbow 오른팔꿈치, 피디쉐입 오른팔꿈치,
  피터팬 왼어깨 — shift 관측 실측). 나머지 angle 카드 3장은 ref rep12 게이트(relaxed/
  ref_gate)로 vertex 경로 미성립 -> 종전 좌표 경로. legs 2장은 적용 범위 밖 (L-10).
- **V 미베이크 5/8** — user_gate 1, ref_gate 1, ref_crop_relaxed 2, unmapped/legs 2.
  새 문법이 "정상적으로" 보이는 승인 코퍼스 카드는 사실상 없음.
- **내가 사전 박제한 어색 케이스**: ① 피디쉐입 오른팔꿈치 V 저사이각·폴 겹침 (선 하나로
  읽힘 1순위) ② 피디쉐입 왼팔꿈치 원이 역립 얼굴 둘러쌈 ③ ref 무마크 2장 (relaxed 앵커
  생략 규칙 — 비교 카드에서 기준측 무표시) ④ 피터팬 user 저해상 + 부위 배율 체감차
  ⑤ 파워스핀 legs 크롭 비대칭 ⑥ 카드 초 표기가 freeze 실초보다 ~10% 큼 (÷9.0 잔존,
  kpo 유보 — 무접촉).
- 침묵 2건(elbow 오른무릎, 파워스핀 왼어깨)은 **display_anchor 는 성립했는데 rep12 양측
  신뢰 좌표 0** 으로 build 안에서 무로그 skip — 로그 없는 침묵 경로가 있다는 실측
  (memberPts 래퍼로 판별).

## Deviations from Plan

**1. [검증식 전제 반증] Task 1 verify 의 `displayAnchorDrops == 0` 가정**
- **발견**: elbow r01 오른어깨 — display_anchor drop 1건 (user 측 align conf 게이트 미달).
- **실증**: 독립 재계산 (P35 align 재로드 + cg.kp conf 게이트) 으로 좌표는 존재하나
  신뢰 미달임을 확인 — fxx fail-closed 설계가 스펙대로 동작한 것. ufb(구 문법) 렌더에선
  존재했던 카드가 새 배선에서 죽는 **실제 코퍼스 발견**이며 드라이버 결함 아님.
- **처리**: 플랜 자체 원칙("dropped 사유가 기록된 정직한 침묵 = 결함 아님")에 따라 측정을
  유지하고, 검증을 "drop 0" 대신 **drop 정합성**(drop 로그 <-> 해당 카드 미방출 <-> 게이트
  생존) 으로 대체해 PASS 박제. 마크/코드 튜닝 0.
- **커밋**: c1e5ef6f

**2. [관찰 보강] 스윕 3회 실행 (렌더 결과는 3회 모두 동일)**
- 무로그 침묵 2건의 사유 판별을 위해 관찰 래퍼를 2회 보강 (crops 의 full/box-None 기록,
  memberPts 판별자, 패널 판별을 인덱스 -> anchor 좌표 대조로 교정). 산출물 무변경 —
  survivors/dropped/freeze-match/카드 파일 3회 동일 (결정론은 fxx 2회 증명 위임).

## LLM 학습 영향 (필수 절)

- **Gemini 실호출 0** — grammar_round machine_eye 스텁 상속 (eyeStubCalls=6 기계 기록),
  더미 키로 SSM 키 주입 경로 미진입. 학습 전송 0.
- **눈 원장 신규 적재 0** — 스텁 산출물(마킹 크롭 6장 + ledger.json)은 evidence 한정,
  원장 아님 (xa1 JUDGMENT 명기 계열). Phase 22 씨앗 코퍼스 무변경.

## 한계 박제

- **마크 튜닝·코드 수정 0** (belle 08-13 방침 locked — 전체 반영 실물까지만, 미세조정은
  belle 판정 후 다음 라운드).
- **눈 스텁 방출 2장**: 피디쉐입 오른팔꿈치·피터팬 왼어깨는 08-11 실눈이 기각했던 record —
  실운영이면 안 나갔을 카드. 문법 판정 재료로만.
- **P3 하이브리드 실물 0**: 승인 코퍼스에 hip 카드 방출이 없어 이 스윕만으로 하이브리드
  판정 불가 — 유일 실물은 fxx fresh doc 왼골반 카드.
- **Pod 실증은 범위 밖** (로컬 무패치 운영 헬퍼 — Pod 은 hlv 에서 배선 실증 완료).
- 침묵 동작 = 정직한 침묵 (사유 전부 STATUS.md).

## 커밋

- c1e5ef6f `feat(quick-260813-ivs)`: 스윕 드라이버 + 렌더 실행 + 관측 박제 (21 files)
- c1afb188 `docs(quick-260813-ivs)`: STATUS.md + EYE-VERDICT.md
- SUMMARY 는 오케스트레이터 docs 커밋 몫 (실행자 미커밋 — 지시 사항).

## Self-Check: PASSED

- sweep_render.py / sweep_verdict.json / measure.json / STATUS.md / EYE-VERDICT.md 존재 확인
- /Users/Shared/sunity-sweep-260813/ 한글 사본 8 == 방출 카드 8
- 커밋 c1e5ef6f, c1afb188 존재 확인
- backend/ + 하네스 원본 3파일 diff 0
