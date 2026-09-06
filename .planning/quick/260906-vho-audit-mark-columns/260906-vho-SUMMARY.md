---
quick_id: 260906-vho
slug: audit-mark-columns
date: 2026-09-06
status: complete
phase: quick-260906-vho
plan: 01
subsystem: backend/analysis (fault_zoom 방출부 · card_photo_audit · scripts/audit_card_photos)
tags: [fault-zoom, card-audit, userMarked, anchor-gate, n2j]
requires: [quick-260906-n2j]
provides:
  - advisory/legacy 카드 userMarked 방출 (refMarked 는 §11.9 정책 유지)
  - 감사 marked_flags per-key (방출값 우선, 부재 측만 정책 폴백)
  - card_photo_audit.panel_error_kind / PANEL_ERROR_KINDS
  - 감사 마지막 줄 mark_errors= / center_errors= 두 열
affects: [scripts/audit_card_photos.py 출력 형식, Firestore faultZoomComparisons advisory item 필드 1개 추가]
tech-stack:
  added: []
  patterns: [순수 함수 분류 + 스크립트 집계, TDD RED/GREEN 커밋 쌍]
key-files:
  created:
    - backend/tests/test_fault_zoom_advisory_user_marked.py
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/tests/test_fault_zoom.py
    - docs/contract.md
    - backend/scripts/audit_card_photos.py
    - backend/shared/python/sunity_shared/analysis/card_photo_audit.py
    - backend/tests/test_card_photo_audit.py
    - backend/tests/test_audit_card_photos_script.py
  tracked:
    - .planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py
decisions:
  - userMarked 는 모든 카드에 방출, refMarked 는 criterion 카드만 (게이트 B 는 기준 측 정책 — 학생 측은 값이 사실)
  - marked_flags 는 per-key — 키가 있는 측은 doc, 없는 측만 정책 폴백 (옛 doc 결말 불변)
  - 집계 두 열은 기존 세 필드 뒤에 덧붙이기만 — mismatched·판정 문자열·허용 집합 무변경
metrics:
  duration: 7m (2026-09-06T13:52:52Z → 14:00:42Z)
  completed: 2026-09-06
  tasks: 3
  commits: 6 (test/fix·feat 쌍 3)
  pytest: 4724 passed / 0 failed / 20 skipped (기준선 4717 + 신규 7)
---

# quick-260906-vho: 감사 계기 결함 2건 — userMarked 전 카드 방출 + mark/center 열 분리 — 완료

**한 줄:** advisory 카드도 `userMarked` 를 방출하게 해 감사가 표시 유무를 추정하지 않고, 감사 마지막 줄에
`mark_errors=/center_errors=` 두 열을 덧붙여 앵커 게이트(j8g/n2j)가 한 일이 숫자로 보이게 했다.
라이브 JSON replay = `total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5`.

## 한 일

| 커밋 | 종류 | 내용 |
|---|---|---|
| `60fbfe1c` | test | advisory 카드 userMarked 방출 실패 테스트 3건 (평시 True / 억제 False+픽셀 0 / 반대측 억제 True), RED 확인 (KeyError userMarked) |
| `47ec24e6` | fix | `fault_zoom.py` 방출부 `item["userMarked"]` 한 줄을 `if unit.criterion is not None:` 블록 밖으로. `refMarked` 는 블록 안 그대로. `test_fault_zoom` legacy 테스트 개명·단정 교체, contract §11.11 방출 범위 bullet |
| `fce2d78b` | test | `marked_flags` per-key 실패 테스트 + 09-06 실물(peter-pan [1]) replay 박제 — 현행 `(False, True)` 확인 |
| `ff7d0374` | fix | `marked_flags` per-key: user = doc 값 or True, ref = doc 값 or criterion 유무. `replay_rows` 무접촉 |
| `b73cac16` | test | `panel_error_kind` 분류 + `_report` capsys 두 열 실패 테스트 |
| `7583e7ca` | feat | `card_photo_audit.panel_error_kind`/`PANEL_ERROR_KINDS` (순수, `__all__` 등재) + `_report` 마지막 줄 두 열 + 계측기 v2 `panel_center_eye_measure_v2.py` 커밋 편입 (내용 무수정) |

## 왜 (측정)

09-06 n2j 라이브(6동작, uid NdVZrpbmUbPMNMjASFwUgy8Fj9p1) 감사 실물 한 줄:

```
ref-peter-pan [1] advisory right_elbow user=back_waist→no_mark None/mark:mark_disagreement
```

앵커 게이트가 advisory 학생 표시를 실제로 지웠는데 doc 에 `userMarked` 가 없어(방출부가 criterion 카드에만
실었다) 감사가 "표시 있음"으로 추정 → 2단(mark_part) 질의 → 눈 `no_mark` → 판정 불가. 그 카드는 기준 패널도
틀려 mismatch 로 남았지만, 기준 패널이 멀쩡했다면 `unresolved` 로 갔다 — 게이트가 일할수록 감사가 판정을
못 하는 구조였다. 테스트 `test_replay_suppressed_advisory_is_mismatch_not_unresolved` 가 두 결말(방출 False →
mismatch / 부재 → unresolved)을 박제한다.

집계 열 분리의 근거는 같은 라이브 JSON 을 새 코드로 `--replay` 한 결과 (눈 호출 0, 키 불필요 — 저장 토큰 재판정):

```
card_photo_audit total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5
```

- `mark_errors=1` = climb [2] ref (`mark_elsewhere`)
- `center_errors=5` = pdshape [1] user · elbow-twist [1] ref · power-spin [1] user · power-spin [2] ref · peter-pan [1] ref
  (`no_mark_and_center_elsewhere`)
- `total/mismatched/unresolved` 18/6/0 은 종전과 동일 — 판정 문자열·허용 집합·카드 결말 무변경의 실물 증거.
  `# mismatch cards` 블록 6행도 바이트 동일.

## 무접촉 확인

- `_CROP_FRAC = 0.42` (fault_zoom.py:50) · `r = int(_OUT * 0.16)` (:1761) grep 각 1건 — byte-unchanged.
- `fault_zoom.py` 비주석 diff (pre-plan `1eef14e7` 대비) = 정확히 2줄 (`-`/`+` 한 줄 이동). 드로잉 코드·`_supp`/`_u_plain` 경로 무접촉.
- 앱 TS 변경 0 (`userMarked?: boolean` 그대로). 매퍼 `_fault_zoom_upload_items` 는 tier 무관 `isinstance(bool)` pass-through 라 advisory item 의 새 bool 이 doc 에 실린다.
- `card_photo_audit.py` import 는 `from __future__ import annotations` 하나뿐 (numpy/boto3/card_gates 0). `test_module_is_pure_no_numpy_import` 통과.

## 게이트 (실측)

| 게이트 | 결과 |
|---|---|
| 백엔드 전체 `pytest -q` (착수 전 기준선) | 4717 passed / 0 failed / 20 skipped (51.39s) |
| 백엔드 전체 `pytest -q` (완료 후) | **4724 passed / 0 failed / 20 skipped** (49.31s) — 기준선 + 신규 7 (T1 3 · T2 2 · T3 2) |
| Task 1 묶음 (advisory_user_marked·fault_zoom·ref_marked·anchor_check·pipeline_card_anchor_check·phase33 zoom_join) | 113 passed |
| Task 2 묶음 (audit_card_photos_script·card_photo_audit) | 44 passed |
| Task 3 묶음 (+anchor_part_check·card_gates) | 125 passed |
| 라이브 JSON `--replay` 마지막 줄 | `card_photo_audit total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5` (일치) |
| 계측기 v2 `git ls-files --error-unmatch` | 추적됨 (`7583e7ca`) |

## Deviations from Plan

### Verify 게이트 표기 오류 (코드 변경 0)

**1. Task 3 자동 검증의 purity grep 이 원본 파일에서도 실패한다**
- **Found during:** Task 3 verify
- **Issue:** `grep -v '^\s*#' card_photo_audit.py | grep -c "^import numpy\|^from numpy\|card_gates"` 는 `#` 주석만
  걸러 **docstring** 의 `card_gates` 언급 7행(12·40·41·51·163·188·195 — 전부 pre-plan HEAD 에도 있는 줄)을 센다.
  게이트 작성 오류이지 회귀가 아니다.
- **Fix:** 코드는 손대지 않았다. 의도(import 0)는 import 전용 grep
  `grep -c "^import numpy\|^from numpy\|^import .*card_gates\|^from .*card_gates"` = 0 과 기존 테스트
  `test_module_is_pure_no_numpy_import` 통과로 확인했다.
- **Files modified:** 없음

**2. 커밋 시 시크릿 패턴 가드가 첫 시도에 실행되지 않았다**
- **Found during:** Task 3 커밋 (계측기 v2 `git add` 직전)
- **Issue:** 이 셸의 `grep` 이 ugrep 이라 `(RSA |)` 빈 대안을 거부, 가드가 오류 종료하며 `else` 로 빠졌다.
- **Fix:** 커밋 직후 `/usr/bin/grep -E` 로 커밋된 사본을 다시 검사 — 매치 0. v2 스크립트는 키를
  `judging.gemini_moment_extractor._load_api_key()`(env/SSM)로 얻고 리터럴은 없다.
- **Files modified:** 없음

그 외 계획대로 실행 — 판정 문자열·허용 집합·`replay_rows`·`expected_parts`·`card_verdict` 무접촉.

## Auth gates

없음 — `--replay` 는 저장 JSON 재판정이라 GEMINI/Firebase/AWS 키 없이 돌았다 (env 를 비우고 실행해 확인).

## Known Stubs

없음.

## Threat Flags

없음 — 새 네트워크/인증/파일 경로 0. 새 doc 필드는 기존 매퍼 `isinstance(bool)` 게이트를 지난다 (T-vho-01 대로).

## 남은 것

- **라이브 재검증 (다음 Pod, 이 단위 범위 밖):** 배포 후 advisory 카드 doc 에 `userMarked` 가 실리는지 +
  앵커 게이트가 학생 측을 억제한 카드에서 감사 결말이 `unresolved` 가 아니라 `mismatch`
  (`no_mark_and_center_elsewhere`) 인지, 그리고 그 패널에 2단 질의가 나가지 않는지(눈 호출 수 감소) 확인.
  같은 6동작 재감사 마지막 줄이 `mark_errors`/`center_errors` 를 내는지 — 게이트가 일하면 전자가 후자로 옮겨간다.
- n2j SUMMARY "남은 것" 1번(게이트가 통과시킨 불일치 3, 원인 단정 금지)은 그대로 열려 있다.
- `_CROP_FRAC`·마커 반지름은 belle 판정 대기 — 이 단위는 손대지 않았다.

## Self-Check: PASSED

- 산출물 10개 존재, 커밋 6개 존재, 계측기 v2 git 추적, must_have contains 3건 충족, 신규 테스트 파일 146줄.
