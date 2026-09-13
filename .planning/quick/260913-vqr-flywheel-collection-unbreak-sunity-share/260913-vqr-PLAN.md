---
id: 260913-vqr
slug: flywheel-collection-unbreak
title: 플라이휠 수집 복구 — sunity_shared 경로 결손 + 실패가 조용한 것
date: 2026-09-13
status: planned
mode: quick
phase: quick-260913-vqr
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
files_modified:
  - backend/scripts/collect_phase22_instagram.py
  - backend/scripts/collect_phase22_youtube.py
  - backend/scripts/phase22_watch.py
  - backend/scripts/flywheel_cycle.sh
  - backend/tests/phase22/test_watch_import_path.py
must_haves:
  truths:
    - phase22_watch.py --dry-run 이 PYTHONPATH 없이 exit 0 으로 통과한다
    - 수집 진입점들이 backend/shared/python 을 sys.path 에 넣는다 (리포 관례와 같은 형태)
    - flywheel_cycle.sh 가 어느 단계든 rc!=0 이면 마커 파일을 남기고 알림을 띄운다
    - 마커가 있으면 다음 세션이 즉시 본다 (TRAINING-DUE.md 와 같은 기전)
    - 모든 단계가 성공하면 마커는 지워진다 (낡은 마커로 잘못 알리지 않는다)
  artifacts:
    - backend/scripts/collect_phase22_instagram.py
    - backend/scripts/flywheel_cycle.sh
    - backend/tests/phase22/test_watch_import_path.py
  key_links:
    - collect_phase22_instagram → datagen.curate_vision → sunity_shared.gemini.config (359b9de5 이후)
    - flywheel_cycle.sh rc 집계 → .planning/FLYWHEEL-BROKEN.md 마커
---

# 플라이휠 수집 복구

한 줄: **수집이 3주간 조용히 죽어 있었다. 경로를 고치고, 다음엔 조용히 죽지 않게 한다.**

## 실측 — 원인 확정

`.planning/FLYWHEEL-LOG.md` 가 스스로 증거를 남기고 있었다:

| 실행 | 수집 신규 | rc(수집/수확/반출/분석) |
|---|---|---|
| 2026-08-17 10:07 | 50 | `0/0/0/0` |
| 2026-08-24 10:08 | 0 | **`1`**/0/**`1`**/0 |
| 2026-08-31 10:07 | 0 | **`1`**/0/0/0 |
| 2026-09-07 10:15 | 0 | **`1`**/0/**`1`**/**`1`** |

**launchd 스케줄은 정상이다** (매주 월요일 10:07 실행됨). 수집 단계만 exit 1 이다.

재현:
```
$ PHASE22_BELLE_GREENLIGHT=1 backend/.venv/bin/python backend/scripts/phase22_watch.py --dry-run
  File "backend/training/datagen/curate_vision.py", line 53
    from sunity_shared.gemini.config import DEFAULT_C_MODEL
ModuleNotFoundError: No module named 'sunity_shared'
```

원인 커밋: **`359b9de5` (2026-08-18)** "Gemini Flash 3.5 → 3.7 + 하드코딩 우회로 제거"
— 모델 문자열을 `sunity_shared/gemini/config.py` 정본으로 모으면서 `curate_vision.py` 에
그 import 가 생겼다. 그런데 `collect_phase22_instagram.py` 는 `BACKEND/"scripts"` 와
`BACKEND/"training"` 만 sys.path 에 넣고 `BACKEND/"shared"/"python"` 은 안 넣는다.
**마지막 성공 08-17, 첫 실패 08-24 — 커밋 날짜와 정확히 맞는다.**

확인된 수정: `PYTHONPATH=backend/shared/python` 를 주면 `--dry-run` 이 exit 0 으로 전부 통과한다.

## 부수 관측 (이번에 고칠 것 아님 — 기록만)

- 반출 rc=1 (08-24·09-07): 지금 `--upload-media --run` 은 `pending 0` 으로 정상 종료.
  올릴 것이 없을 때 rc 가 1 로 나온 것으로 보이나 재현 못 했다. **미확정.**
- 분석 rc=1 (09-07, 원장 338/325 → 0/0): 지금 `--run` 정상, **밀린 46건을 복구**했다
  (rows 338 → 384, admit 334). 09-07 실패는 일시적이었던 것으로 보인다. **미확정.**

## 영향

- 정은지 IG (`eunji.poledancer`, cap 60) 수집 마지막 = **2026-08-14**, 이후 0건 (37건에서 멈춤)
- 전체 코퍼스 371편 — 재학습 임계 400편에서 **29편 부족**
- 레지스트리 활성 = YT 17채널 + IG 6계정. 3주간 전부 안 긁혔다

## 태스크

### Task 1 — 수집 진입점에 shared/python 경로

files: `backend/scripts/collect_phase22_instagram.py`, `backend/scripts/collect_phase22_youtube.py`, `backend/scripts/phase22_watch.py`

action:
- 각 파일의 기존 `sys.path.insert` 블록에 `BACKEND / "shared" / "python"` 을 추가한다.
  리포 관례와 같은 형태로 (`assert_falsepositive_gate.py:46` 이 본보기).
- 이미 있는 파일은 건너뛴다. 중복 insert 금지.
- 주석으로 **왜**를 적을 것: `curate_vision` 이 `sunity_shared.gemini.config` 를 쓴다(`359b9de5`),
  그리고 이 결손이 수집을 3주간 죽였다.

verify: `backend/.venv/bin/python backend/scripts/phase22_watch.py --dry-run` 이
**PYTHONPATH 없이** exit 0. `[watch dry-run] exit 0` 줄이 나와야 한다.

done: PYTHONPATH 없이 dry-run 통과.

### Task 2 — 회귀 박제

files: `backend/tests/phase22/test_watch_import_path.py` (신규)

action: 수집 진입점을 **하위 프로세스로** import 해서 `sunity_shared` 결손이 재발하면
깨지게 한다. 네트워크·AWS·Gemini 호출 0. 형태:
- `subprocess` 로 `python -c "import sys; sys.path.insert(...); import collect_phase22_instagram"`
  를 **PYTHONPATH 없이** 돌려 exit 0 을 본다.
- `curate_vision` 도 같은 방식으로.
- 왜 하위 프로세스인가: 같은 인터프리터 안에서는 pytest 가 이미 경로를 깔아둬 결손이 안 보인다.
  **이 함정을 테스트 독스트링에 적을 것.**

verify: 테스트가 통과하고, Task 1 을 되돌리면 **실패한다**(RED 를 실제로 관측할 것).

done: RED→GREEN 관측 기록.

### Task 3 — 조용히 죽지 않게

files: `backend/scripts/flywheel_cycle.sh`

action:
- 이미 있는 `TRAINING-DUE.md` 기전을 그대로 본떠 **`.planning/FLYWHEEL-BROKEN.md`** 마커를 만든다.
- 4개 rc(`watch_rc`·`harvest_rc`·`upload_rc`·`report_rc`) 중 **하나라도 0 이 아니면**:
  마커에 실행 시각·어느 단계·rc·해당 `/tmp/_fw_*.log` 의 **마지막 20줄**을 적고,
  `osascript` 알림을 띄운다 (TRAINING-DUE 와 같은 방식).
- **전부 0 이면 마커를 지운다** — 낡은 마커로 잘못 알리는 것을 막는다 (TRAINING-DUE 와 같은 규율).
- 마커 본문에 재현 커맨드를 적을 것.
- `set -uo pipefail` 이 이미 있고 `set -e` 는 없다 — 그대로 둔다(한 단계 실패가 다음을
  막으면 안 된다). rc 는 이미 수집되고 있으니 **읽기만 추가**하는 것이다.

verify: 일부러 실패하는 rc 를 넣어 마커가 생기는지, 전부 0 일 때 지워지는지 각각 확인.
실제 사이클을 돌리지는 말 것(과금).

done: 두 방향 다 확인.

## 하지 말 것

- 실제 수집(`--run`)을 돌리지 말 것 — **Gemini 선별 과금**이 붙는다. 오케스트레이터가 별도로 판단한다.
- `curate_vision.py` 의 import 를 되돌리지 말 것 — 정본 집중은 옳은 방향이다
  (메모리 `gemini-latest-model-versions`: 모델 문자열은 어디에도 박지 말 것)
- 레지스트리(채널·계정 목록) 수정 금지
- launchd plist 수정 금지 — 스케줄은 정상이다
- `backend/training/data/` 의 원장 수정 금지
