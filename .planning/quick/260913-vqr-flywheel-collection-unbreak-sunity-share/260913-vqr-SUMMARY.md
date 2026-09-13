---
phase: quick-260913-vqr
plan: 01
subsystem: infra
tags: [flywheel, launchd, sys.path, sunity_shared, phase22, regression-test, bash]

# Dependency graph
requires:
  - phase: quick-260814-l5i
    provides: flywheel_cycle.sh 주간 사이클 + TRAINING-DUE.md 마커 기전
  - phase: 22-11
    provides: phase22_watch.py / collect_phase22_* 수집 진입점
provides:
  - 수집 진입점 3개가 backend/shared/python 을 스스로 sys.path 에 깐다 (PYTHONPATH 없이 동작)
  - 하위 프로세스 회귀 테스트 — conftest 가 가리는 경로 결손을 잡는다
  - flywheel_cycle.sh 가 단계 실패 시 .planning/FLYWHEEL-BROKEN.md 마커 + osascript 알림
affects: [flywheel, phase22-collection, launchd-cycle, session-start-housekeeping]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "진입점 sys.path 는 진입점이 스스로 — conftest 주입에 기대지 말 것(하위 프로세스 테스트로 박제)"
    - "자동 사이클의 실패는 로그 열이 아니라 마커 파일 + 알림으로(TRAINING-DUE 기전 재사용)"

key-files:
  created:
    - backend/tests/phase22/test_watch_import_path.py
  modified:
    - backend/scripts/collect_phase22_instagram.py
    - backend/scripts/collect_phase22_youtube.py
    - backend/scripts/phase22_watch.py
    - backend/scripts/flywheel_cycle.sh

key-decisions:
  - "youtube 는 training 지연 import 를 유지하고 shared/python 만 모듈 최상위에 한 번 — 경로 insert 는 비용이 없고 두 지연 지점에 중복 넣을 이유가 없다"
  - "마커 rc 는 플랜의 4개 + report_up_rc(분석반출) 1개 = 5개 — 이미 모으고 있던 rc 를 읽기만 하는 범위 안이고, 빠뜨리면 그 단계는 다시 조용히 죽는다"
  - "회귀 테스트에 대조군(깨끗한 인터프리터에 sunity_shared 없음) 포함 — .pth 등으로 전역 주입되면 진입점 테스트가 사문이 되는 것을 그 자리에서 잡는다"

patterns-established:
  - "하위 프로세스 import 테스트: PYTHONPATH 제거 + cwd 리포 루트 + sys.executable — launchd 와 같은 조건"

requirements-completed: []

# Metrics
duration: ~25min
completed: 2026-09-13
---

# Quick 260913-vqr: 플라이휠 수집 복구 Summary

**3주간 조용히 죽어 있던 주간 수집을 sys.path 한 줄(x3)로 되살리고, 하위 프로세스 테스트로 박제하고, 다음 실패는 마커+알림으로 표면화되게 했다.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-13 23:05 KST
- **Tasks:** 3/3
- **Files modified:** 5 (4 수정 + 1 신규)

## Accomplishments

- `phase22_watch.py --dry-run` 이 **PYTHONPATH 없이** `[watch dry-run] exit 0` — 359b9de5(08-18) 이후 처음
- 회귀 테스트가 진짜로 잡는다는 것을 RED 로 관측(아래 기록)
- `flywheel_cycle.sh` 가 어느 단계든 rc!=0 이면 `.planning/FLYWHEEL-BROKEN.md` 를 남기고 알림, 전부 0 이면 지운다

## Task Commits

1. **Task 1: 수집 진입점에 shared/python 경로** - `f6b56c20` (fix)
2. **Task 2: 회귀 박제** - `c9415abe` (test)
3. **Task 3: 조용히 죽지 않게** - `510abe33` (feat)

**Plan metadata:** 커밋 안 함 — 오케스트레이터 몫(지시).

## Files Created/Modified

- `backend/scripts/collect_phase22_instagram.py` - `BACKEND/shared/python` sys.path 추가 + 왜(359b9de5, 3주 사망) 주석. 실제로 죽은 자리(모듈 최상위 `from datagen import curate_vision`)
- `backend/scripts/collect_phase22_youtube.py` - 모듈 최상위에 shared/python 1회. `--curate/--collect` 의 training 지연 import 는 그대로
- `backend/scripts/phase22_watch.py` - launchd 직접 진입점이라 하위 수집기에 기대지 않고 스스로 깐다
- `backend/tests/phase22/test_watch_import_path.py` - 신규. 진입점 3개(instagram/youtube/watch)를 PYTHONPATH 없는 하위 인터프리터에서 import + 대조군 1개. 독스트링에 "왜 하위 프로세스인가" 함정 명시
- `backend/scripts/flywheel_cycle.sh` - 3-4 단계 추가(43줄). rc 5개 읽기 → 마커/알림/삭제

## 게이트 (before / after)

| | passed | skipped | failed | errors |
|---|---|---|---|---|
| 착수 전 (HEAD e3004253) | 4821 | 20 | 0 | 0 |
| 완료 후 (HEAD 510abe33) | **4825** | 20 | 0 | 0 |

+4 = 신규 테스트 4개(진입점 3 + 대조군 1). 커맨드: `backend/.venv/bin/python -m pytest backend/tests -q --continue-on-collection-errors`

## Task 2 RED → GREEN 관측 기록

```
GREEN (Task 1 적용):            4 passed in 0.26s
RED   (세 파일을 aca0f868 판으로 git checkout, 워킹트리만):
  FAILED test_watch_import_path.py::test_entrypoint_imports_without_pythonpath[instagram]
  FAILED test_watch_import_path.py::test_entrypoint_imports_without_pythonpath[watch]
  FAILED test_watch_import_path.py::test_entrypoint_imports_without_pythonpath[youtube]
  E  ModuleNotFoundError: No module named 'sunity_shared'
  3 failed, 1 passed in 0.29s        (1 passed = 대조군 — 깨끗한 인터프리터엔 원래 없음)
GREEN (HEAD 판 복원):            4 passed in 0.27s
```

첫 시도에서 zsh 가 `$FILES` 를 단어 분리하지 않아 되돌리기가 실행되지 않은 채 "4 passed" 가 나왔다 — 경로를 명시해 재실행한 것이 위 기록이다.

## Task 3 검증 기록 (실 사이클 미실행)

스크래치 루트(`SUNITY_ROOT`)에 가짜 `backend/.venv/bin/python`(argv 패턴에 따라 25줄 출력 후 exit 0/1)·가짜 `osascript`(호출을 파일에 기록)·가짜 `git`(no-op) 을 두고 `flywheel_cycle.sh` 를 그대로 실행:

| 시나리오 | 결과 |
|---|---|
| A. 수집+반출 실패(08-24 와 같은 1/0/1/0) | 마커 생성. 섹션 정확히 2개(수집·반출), 각 로그 마지막 20줄(6..25) 포함, 수확·분석 섹션 없음. osascript 1회: `단계 실패: 수집(rc=1) 반출(rc=1)` |
| B. 전부 0 (낡은 마커 미리 심어둠) | 마커 삭제됨. osascript 호출 0. LOG 행 `0/0/0/0` |
| C. 분석반출만 실패(트림 확인) | `실패: 분석반출(rc=1)` — 끝 공백 없음 |

실제 리포의 `.planning/FLYWHEEL-LOG.md`·`FLYWHEEL-BROKEN.md`·`backend/training/data/` 무접촉 확인.

## Decisions Made

- youtube: shared/python 은 모듈 최상위 1회, training 지연 import 는 유지(플랜 "기존 블록에 추가"를 지연 지점 2곳 중복 대신 최상위 1곳으로 해석)
- 마커 rc 집계에 `report_up_rc`(분석반출) 포함 — 플랜은 4개를 명시했지만 must_have 는 "어느 단계든"이고, 이 rc 는 이미 모으고 있어 읽기만 추가하는 범위
- 마커의 재현 커맨드: 수집은 `--dry-run`(같은 import 오류가 나고 과금 0), 수확은 `--dry-run --readjudicate --with-s3 <maps>`(`--help` 로 조합 파싱 확인), 반출·분석은 사이클이 실제 돌린 커맨드 그대로

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - 누락 기능] 마커 rc 에 분석반출(report_up_rc) 추가**
- **Found during:** Task 3
- **Issue:** 플랜은 rc 4개(수집/수확/반출/분석)만 들었는데 사이클엔 5번째 단계(`harvest_reports.py --upload-media`) 가 있고 그 rc 는 LOG 열에도 없다 — 거기서 죽으면 또 조용하다
- **Fix:** 5번째 rc 를 같은 방식으로 읽는다(`분석반출`)
- **Files modified:** backend/scripts/flywheel_cycle.sh
- **Verification:** 시나리오 C
- **Committed in:** 510abe33

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** 플랜 범위 안("읽기만 추가"). 스코프 확장 없음.

## Issues Encountered

- **`/tmp/_fw_*.log` 백업 실패 → 유실 없음 확인.** 하네스가 `/tmp/_fw_*.log` 를 덮어쓰기 전에 `cp` 로 백업하려 했으나 조용히 실패했다. 생성(birth) 시각이 전부 오늘 23:00 이라 **하네스 전에 파일이 없었던 것**(macOS /tmp 3일 정리, 09-07 로그는 이미 없었음)으로 확정. 하네스가 만든 가짜 4개는 삭제했다 — 지금 `/tmp/_fw_*.log` 는 없다. 다음 월요일 사이클이 새로 만든다.
- **PATH 에 가짜 `git` 을 올린 셸에서 Task 3 커밋을 시도해 무효.** 같은 호출 안에서 `export PATH="$SCR/bin:$PATH"` 뒤에 `rtk git commit` 을 해서 스텁이 잡혔다(출력 `ok` 하나, 로그 줄 없음). 새 셸에서 재커밋(`510abe33`). 작업 손실 없음.

## Next Session Note (오케스트레이터 판단 사항)

- 실제 수집 `--run` 은 돌리지 않았다(과금). 다음 launchd 사이클(월 10:07) 또는 수동 `--run` 이 첫 실증이다.
- `.planning/FLYWHEEL-BROKEN.md` 가 보이면 즉시 알릴 것 — TRAINING-DUE.md 와 같은 규칙. (착수 정리 목록에 넣을 것)
- 플랜 "부수 관측"(반출 rc=1, 분석 rc=1 의 09-07 원인)은 미확정 그대로. 로그가 이미 /tmp 정리로 사라져 이번엔 못 본다 — 다음 사이클부터는 마커가 마지막 20줄을 박제한다.

## Known Stubs

없음.

## Threat Flags

없음 — 네트워크·인증·스키마 변경 없음. 마커는 로컬 파일이고 git 에 올리지 않는다(TRAINING-DUE 와 동일).

## Self-Check: PASSED

- 생성 파일 1 + 수정 파일 4 존재, 커밋 3건(f6b56c20 / c9415abe / 510abe33) 존재
- 게이트 after 4825 passed / 0 failed
