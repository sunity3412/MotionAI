---
id: 260815-fzi
slug: causesubject
date: 2026-08-15
status: complete
commit: 9a8f6fdc
---

# SUMMARY — 캡션 원인 절 학생 서술 제거 + causeSubject 구조 차단

## belle 판정 (2026-08-15)

| # | 판정 | 원문 |
|---|---|---|
| a 문면 | 승인 | "캡션 좋다" |
| b 일반화 | **반려** | "아니b는 이게 논의할 일인가? 다른 사람이 분석했느데 전에 학생거를 말하는게 정상이냐...." |
| c 폴백 | 원 마커 | "c는 지운다면 원마커야. 캡션이 좋으니까 그냥 놔도도 무방" |
| d 임계 | 보류(되물음) | "임계가 어떤 임계인지, 지정방식이 뭔 방식을 말하는건지 잘 모르겠으" |

## 무엇이 잘못이었나

quick-260814-rcz 는 원인 절을 `(동작 × criterion)` 키에 고정했다. 그 키는 **분석
1건에 묶이지 않는다** — belle 이 한 학생의 영상을 보고 읽어낸 진단이 같은 결함을
낸 이후 모든 유저의 카드·자막·음성에 그대로 나간다. 실행자는 이것을 "전형 설명으로
일반화해도 되는가"라는 **판정 질문으로 냈고**, belle 은 판정할 일이 아니라고 했다.

## 갈리는 축 = 원인 문장의 주어

| 주어 | 사람이 바뀌면 | 처분 |
|---|---|---|
| 기준(정은지) 서술 — 기준 영상 v1 pinned, 전 유저 공통 | 그대로 성립 | 유지 |
| 학생 서술 — 그 학생 그 영상의 읽기 | 남의 진단이 됨 | 제거 |

두 시드가 정확히 이 축으로 갈렸다. powerspin 왼어깨는 문장 자체가 "**기준은** …"
으로 시작하고, pdshape 왼팔꿈치는 학생의 동작을 서술한다.

## 한 것

| # | 산출 | 실체 |
|---|---|---|
| T1 | 데이터 | `ref-pdshape.…__left_elbow` causeLine 제거 · `ref-power-spin.…__left_shoulder` 에 `causeSubject: "reference"` · `_meta.causeLineProvenance.unadopted` 에 문면+사유+복원조건 보존 |
| T2 | 코드 | `phrasebook.cause_line_admissible()` 순수 함수 + `_entry_slots` fail-closed 드롭. 방출 슬롯 tuple(`_ENTRY_SLOTS` == `models.DEDUCTION_PHRASE_KEYS`)은 불변 — `causeSubject` 는 입력 메타 |
| T3 | 테스트 | 전 entry(67) 스윕 · 드롭 실증(student/선언누락/원인없음 3경로) · 미채택 문면 보존 |
| T4 | 기록 | `260814-rcz/CAPTION-SHEET.md` §4 belle 원문 기입 + §4-1 처분 + §4-2 미확정 고지 |

## 게이트 (실행 로그가 증인)

- `pytest backend/tests`: **변경 전 59 failed / 4347 passed → 변경 후 59 failed / 4348 passed**
  (기준선 동일. 남은 59 는 gemini 스파이크·wiring 계열로 이번 변경과 무관 —
  `git stash` 로 변경분만 빼고 재실행해 대조함)
- `test_caption_cause_layer.py`: 28 passed
- 무회귀: causeLine 없는 66 entry 캡션은 `_legacy_compose` 동결 사본과 문자 동일
- 커밋: `9a8f6fdc`

## 안 한 것 (범위 밖 — 명시)

1. **powerspin 왼어깨는 확정 아님.** 기준 영상은 고정이지만 **카드가 잡는 순간은
   학생마다 다르다.** 그 구간 내내 기준 왼어깨가 "굽혀 더 올린" 상태인지 안 쟀다.
   안 재고 남기면 이번 반려의 반대편 실수다 → 기준 클립 전 구간 왼어깨 각 실측 후
   별건 판정. **미측정 상태로 운영에 남아 있음을 숨기지 않는다.**
2. 각도 표기 임계(§4 d) — belle 되물음 중, 무변경.
3. 영상 재렌더·S3 반영 — 별건(chd 선례).

## 남는 사실 (다음 사람이 알아야 할 것)

- 원인 절 커버리지는 **67 entry 중 1건**이다. 새 유저가 다른 동작·다른 관절에서
  결함을 내면 원인 없는 오늘의 2문장이 나간다. 넓히는 유일한 경로는 belle 의
  코칭 지식을 **기준 서술 형태로** 받는 것이다 (LLM 생성 경로는 D-11 로 닫혀 있음).
- 학생 서술 원인을 되살리는 조건은 문구집이 아니라 **측정**이다.
