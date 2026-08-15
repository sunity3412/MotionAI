---
id: 260815-fzi
slug: causesubject
date: 2026-08-15
status: in-progress
---

# 캡션 원인 절 — 학생 서술 제거 + causeSubject 구조 차단

## 왜 (belle 2026-08-15 판정)

> "아니b는 이게 논의할 일인가? 다른 사람이 분석했느데 전에 학생거를 말하는게 정상이냐...."

quick-260814-rcz 가 원인 절(`causeLine`)을 `(동작 × criterion)` 키에 고정했다.
그 키는 **분석 1건에 묶이지 않으므로**, 앞 학생의 영상을 보고 belle 이 읽어낸
진단이 이후 모든 유저의 카드·자막·음성에 그대로 나간다. §4 b 반려.

## 갈리는 축 = 원인 문장의 주어

| 주어 | 사람이 바뀌면 | 판정 |
|---|---|---|
| **기준(정은지) 서술** — 기준 영상은 전 유저 공통(v1 pinned) | 그대로 성립 | 고정 가능 |
| **학생 서술** — 그 학생 그 영상의 읽기 | 남의 진단이 됨 | 고정 불가 |

`ref-power-spin.…__left_shoulder` = "**기준은** … 팔을 굽혀 더 올린 것으로 보여요" (기준 서술)
`ref-pdshape.…__left_elbow` = "회전이 덜 된 채 손을 먼저 뻗어 잡은 것일 수 있어요" (학생 서술)

## 작업

### T1 — 학생 서술 원인 절 제거 (데이터)
- `backend/data/phrasebook.json`
  - `ref-pdshape.angle_vs_reference__left_elbow` 의 `causeLine` 제거
  - `ref-power-spin.angle_vs_reference__left_shoulder` 에 `causeSubject: "reference"` 선언
  - `_meta.causeLineProvenance` 에 belle 판정 원문 + 미채택 사유 + 되살릴 조건 기록.
    **원문 전사는 지우지 않는다** — 측정이 생기면 그 문면으로 돌아온다.

### T2 — 구조적 차단 (코드)
- `backend/shared/python/sunity_shared/analysis/phrasebook.py`
  - `causeSubject` 슬롯 추가, 허용값 `{"reference"}` 화이트리스트
  - `cause_line_admissible(entry) -> (bool, reason)` 순수 함수
  - `_entry_slots` 에서 부적격 causeLine 은 **드롭**(fail-closed). 텍스트 휴리스틱 0 —
    선언 필드만 본다
- **주의**: `models.DEDUCTION_PHRASE_KEYS == phrasebook._ENTRY_SLOTS` 계약이 있으므로
  `causeSubject` 는 방출 슬롯이 아니라 **입력 메타**로 둔다(방출 슬롯 tuple 불변)

### T3 — 테스트 (전 entry 스윕)
- `backend/tests/test_caption_cause_layer.py`
  - `SEED_KEYS` 1건으로 갱신, `test_seed_count_is_exactly_two…` → 이름·수 갱신
  - 신규: 전 entry 스윕 — causeLine 보유 시 `causeSubject == "reference"` 필수, 아니면 FAIL
  - 신규: 학생 서술 entry 는 조립 결과에서 causeLine 이 빠진다(fail-closed 실증)
  - 합성 fixture 문자열 유지 + "문구집에 넣으면 안 된다" 주석

### T4 — 판정 기록
- `.planning/quick/260814-rcz-caption-cause-layer/CAPTION-SHEET.md` §4 belle 원문 기입

## 무회귀 게이트
- causeLine 없는 65 entry 캡션 문자 단위 동일 (`_legacy_compose` 대조 유지)
- `PYTHONPATH=backend/tests backend/.venv/bin/python -m pytest -q backend/tests` 전건 통과 (기준선 59+)
- powerspin 왼어깨 문면 무변경 — 기준 클립 전 구간 실측은 별건

## 범위 밖
- 기준 클립 왼어깨 각 전 구간 실측 (별건, 실측 후 판정)
- 영상 재렌더·S3 반영
- 각도 표기 임계(§4 d) — belle 보류
