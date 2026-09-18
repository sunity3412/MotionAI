---
phase: quick-260918-qm2
plan: 01
subsystem: docs
tags: [doc-truth, ledger, belle-judgment, pose-engine, reference-motions, pod-ops]
requires: [260918-qm2-FINDINGS.md, 260918-qm2-CONTEXT.md]
provides:
  - "CLAUDE.md·PROJECT·STACK·ARCHITECTURE·analysis.ts·ml_CLAUDE·contract 의 운영 백본 표기 = YOLOX-m + RTMW-x 133"
  - "docs/reference-motions.md v7 — camelCase 11편 + ROT180 env 가 박힌 §6 잠정 절차"
  - "Pod 종료 절차 3곳의 Lambda 자리표시자 복귀 문구"
  - ".planning/STATE.md 미종결 트랙 판정 원장 (24행)"
  - ".planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-BELLE-JUDGMENT.md (belle 판정 대기 5건)"
affects: [ROADMAP.md, REQUIREMENTS.md, design.md, app/CLAUDE.md, .claude/commands/start.md]
tech-stack:
  added: []
  patterns: ["정정은 삭제가 아니라 배너/정정 주석"]
key-files:
  created:
    - .planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-BELLE-JUDGMENT.md
  modified:
    - CLAUDE.md
    - .planning/PROJECT.md
    - .planning/codebase/STACK.md
    - .planning/codebase/ARCHITECTURE.md
    - app/src/types/analysis.ts
    - ml/ml_CLAUDE.md
    - docs/contract.md
    - backend/shared/python/sunity_shared/analysis/pose_engines/__init__.py
    - docs/reference-motions.md
    - .planning/quick/260918-gpx-gate-false-suppress/DEMO-CARD.md
    - .claude/commands/start.md
    - .planning/quick/260906-n2j-stage-1-advisory/evidence/POD-RUNBOOK-2026-09-06.md
    - backend/runpod_inference/README.md
    - docs/runpod-fast-restart.md
    - design.md
    - app/CLAUDE.md
    - .planning/STATE.md
    - .planning/debug/*.md (6건)
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
    - .planning/quick/260918-day-closeout/HANDOFF.md
decisions:
  - "ROADMAP 체크박스는 고정 목록이 아니라 실측 규칙(SUMMARY 가 디스크에 실재하면 [x])으로 적용 — 결과 16건"
  - "Pod 종료 자리표시자 = https://pod-down.invalid/analyze (RFC 2606 예약 TLD — DNS 즉시 실패 + 이름만 봐도 내려감을 안다)"
  - "22-06·36-01 은 '완료(원장 표기만 누락)' — 사문/죽었다로 적지 않는다"
metrics:
  duration: "약 1시간"
  completed: 2026-09-18
---

# Quick 260918-qm2: 문서 진실 수리 + 미종결 트랙 판정 원장 Summary

문서 18곳을 코드와 일치시키고(A-4·A-9 는 반려 반영 문구로), 미종결 트랙 판정을
STATE/ROADMAP/REQUIREMENTS 원장에 박고, belle 판정 대기 5건을 한 파일로 모아 인계서에서
가리켰다 — 소스 diff 는 주석/docstring 뿐, `backend/template.yaml` 무접촉.

## 커밋 6개 (BASE `78989c58`)

| # | 해시 | 무엇 |
|---|---|---|
| 1 | `12c59896` | 포즈 엔진 표기 전수 정정 — NLF/ViTPose/YOLO11 → YOLOX-m + RTMW-x 133 |
| 2 | `1ed93ea7` | reference-motions.md 수리 — camelCase·§4 실측·11편·§6 잠정 절차 |
| 3 | `e5a71144` | 운영 문서 — DEMO-CARD 빈칸화 · Pod 종료 3곳 · runpod README · 배너 2건 · design.md · 차트 |
| 4 | `1fe7f228` | 판정 원장 — debug 6건 정정 블록 (STATE.md 본문은 수정만, 커밋은 오케스트레이터 몫) |
| 5 | `689d7866` | ROADMAP 체크박스 16건 + 미종결 11줄 판정 + Phase 18/21/35/36 · REQUIREMENTS |
| 6 | `421e25f0` | BELLE-JUDGMENT.md 신설 + 인계서 연결 |

## ★ SUMMARY 에 반드시 적으라고 지시된 관측 3건 + 1

**(1) ROADMAP 의 "SUMMARY 실재 미체크"는 14 가 아니라 16이다.**
고정 목록 대신 실측 규칙(`ls .planning/phases/*/NN-MM-SUMMARY.md`)으로 돌렸더니 CONTEXT 의
14건에 **25-02 · 25-03** 이 추가됐다. 실행 출력:

```
flipped(16): 01-23, 01-24, 01-25, 05-03, 05-04, 05-05, 12-01, 12-02, 12-03,
             23-03, 24-03, 25-01, 25-02, 25-03, 25-04, 32-15
```

**(2) REQUIREMENTS 의 Pending 행은 17 이 아니라 19다.**
`grep -c '| Pending |' .planning/REQUIREMENTS.md` → `19`. 그중 SCORE-10(→Complete)과
SCORE-09(→belle 지시로 열림)를 따로 처리하고 **나머지 17행**에 "재판정 대상" 표시를 붙였다.
스크립트 출력: `Pending 재판정 표시: 17`.

**(3) FINDINGS 에 `죽은코드` 절이 없다.**
BELLE-JUDGMENT 5번 건의 수치(앱 고아 16파일 3,707줄 / 즉시 제거 후보 2,991줄 / 3D 스택 제거는
네이티브 재빌드)는 **CONTEXT §묶음 C-5 에서 옮긴 것**이고 파일별 목록은 리포 안에 없다.
FINDINGS 에 있는 파일별 항목은 `app/src/lib/resultSections.ts`(+ 테스트 348줄) 1건뿐이다.
그 사실을 BELLE-JUDGMENT §5 에 **관측으로 명시**했다 — 파일별 목록은 메인 세션이 첨부해야
판정이 가능하다.

**(4) §6 의 스크립트 플래그가 FINDINGS 와 달랐다 — 코드 쪽 이름을 썼다.**
`grep -n add_argument` 실측 결과 두 가지가 플랜 원안과 달랐고, §6 본문에 주석으로 박았다:

- `reprocess_reference_motions_phase4.py --motions` 는 `nargs="+"` (공백 분리)인데
  `backfill_reference_downstream.py --motions` 는 **쉼표 분리 목록**이다(도움말 원문:
  "쉼표 분리 motion id list"). 두 스크립트가 서로 다르다.
- `backfill_reference_downstream.py` 는 `--bucket` 이 **candidate 백필에 필요**하다
  (도움말 원문: "S3 bucket (예: sunity-motion-pilot-videos). candidate 백필에 필요."). 
  그래서 [5] 명령줄에 `--bucket sunity-motion-pilot-videos` 를 넣었다.

## 반려 반영 확인 (A-4 · A-9 · A-6 · A-16)

- **A-4** — §6 [4] 단계가 `ROT180_INVERSION_ENABLED=1 python backend/scripts/reprocess_reference_motions_phase4.py --version <활성버전> --no-flip --motions {motionId}` 이고,
  바로 아래에 "코드 기본 off(rtmw_engine.py:62-66) · 안 켜면 기질 혼합 · 실측 정은지 자기비교
  100 -> 60" 주석이 붙었다. `POST /reference/auto-register` 의 한계(name·athleteName·level
  미기록 + angles 미생성)와 "Phase 21 이 자동화 대상 — 정본으로 고착시키지 말 것" 배너도 들어갔다.
- **A-9** — 3곳(`start.md`, `POD-RUNBOOK-2026-09-06.md`, `DEMO-CARD.md`) 모두
  "**자리표시자 `https://pod-down.invalid/analyze` 로 되돌린다** / 값 삭제·SSM 삭제 금지
  (Type=String + `{{resolve:ssm:}}` → 삭제 시 다음 sam deploy 파손) / **Pod 없으면 분석은 어차피
  실패** — CPU 폴백은 ImportError 로 차단(pipeline/requirements.txt:1-4)". `.invalid` 선택 이유는
  `start.md` 에 괄호로 적었다. **AWS 는 호출하지 않았다 — 문서만.**
- **A-6** — §4 규칙 1 을 삭제하지 않고 "clipRange 의 실제 소비처는 공유 베이스 경계 한 곳
  (`pipeline/app.py:7989-7993` segments.ref_boundary_frame + `referenceMotions.ts:178` +
  `analysis.ts:1217`)"으로 정정했다. 실측으로 재확인: `extract_reference_angles.py` ·
  `reprocess_reference_motions_phase4.py` 에 clipRange 참조 0건.
- **A-16** — README 에 "기본 ON" 이라는 표현을 쓰지 않았다. "코드 기본이 off 이고 켜는 곳은
  `start_server.sh:24` 한 곳뿐 / 2026-09-17 belle 승인 이후 **운영 Pod 에서는 ON**" 으로 적었다.

## "완료"는 "사문"이 아니다 (묶음 B)

STATE 판정 원장·ROADMAP 양쪽에서 22-06 과 36-01 을 정확히 `완료(원장 표기만 누락)` 로 적었다.
검사: `grep -c '22-06[^|]*죽었\|36-01[^|]*죽었\|22-06[^|]*사문\|36-01[^|]*사문' .planning/STATE.md` → `0`.
사문 4건(31-12 · 33-07 · 33-16 · 33-21)은 ROADMAP 에서 `- [x] ~~NN-MM-PLAN.md~~` 취소선 +
"사문" 라벨로 완료와 구분했다(완료 줄에는 취소선 없음).

## 검증 — 명령과 출력

각 태스크의 `verify` 게이트를 실제로 실행했다. 아래는 최종 실행 결과.

**Task 1**
```
$ test ... && (cd app && rtk npm run typecheck) && echo TASK1-OK
> tsc --noEmit
TASK1-OK
```

**Task 2**
```
$ F=docs/reference-motions.md && test "$(grep -c '^### ref-' $F)" -eq 11 && ... && echo TASK2-OK
TASK2-OK
```

**Task 3** (아래 "게이트 정정" 참조)
```
$ D=.planning/quick/260918-gpx-gate-false-suppress/DEMO-CARD.md && ... && echo TASK3-OK
TASK3-OK
```

**Task 4**
```
$ S=.planning/STATE.md && test "$(grep -c '^### 미종결 트랙 판정 원장 ...')" -eq 1 && ... && echo TASK4-OK
TASK4-OK
```
중간 실측: 판정 표 행 수 `25` (요구 ≥23), `22-06 ok` / `36-01 ok` / `bad label: 0` /
`cp-banner ok` / debug 6건 전부 `banner=1 fmdel=0`.

**Task 5**
```
$ R=.planning/ROADMAP.md && ... && echo TASK5-OK
TASK5-OK
```
(zsh 가 `ls .planning/phases/*/22-08-SUMMARY.md` 에 대해 "no matches found" 를 stderr 로 뱉지만
그건 "SUMMARY 없음"이라는 기대 결과 자체다 — 게이트는 통과.)

**Task 6**
```
$ B=.planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-BELLE-JUDGMENT.md && ... && echo TASK6-OK
TASK6-OK
```

**전체 마감 (`78989c58..HEAD`)**
```
$ git diff 78989c58..HEAD --stat -- app backend
 app/CLAUDE.md                                             | 11 ++++-------
 app/src/types/analysis.ts                                 |  8 ++++----
 backend/runpod_inference/README.md                        | 15 +++++++++++----
 .../sunity_shared/analysis/pose_engines/__init__.py       |  4 +++-
 4 files changed, 22 insertions(+), 16 deletions(-)

$ git diff 78989c58..HEAD --quiet -- backend/template.yaml && echo UNTOUCHED
UNTOUCHED

$ git diff 78989c58..HEAD -U0 | grep '^+' | python3 -c "... 이모지 정규식 ..."
0

$ git diff --diff-filter=D --name-only 78989c58..HEAD
(출력 없음 — 삭제된 추적 파일 0)
```

**게이트 무회귀**
```
$ cd app && rtk npm run typecheck
> tsc --noEmit                      (에러 0)

$ cd backend && .venv/bin/python -m pytest tests -x -q
4835 passed, 20 skipped, 42 warnings in 53.70s
```
기준선 4835 passed / 0 failed 와 동일. (메모리 `dont-trust-subagent-gate-numbers` 대로
`backend/.venv` 인터프리터로 돌렸다.)

## Deviations from Plan

### [Rule 3 - 차단 이슈] Task 3 의 소스 범위 게이트가 자기 태스크와 모순

- **Found during:** Task 3
- **Issue:** verify 가 `test "$(git diff --stat -- app backend | grep -c '|')" -eq 1` 로
  "app/backend 변경은 `runpod_inference/README.md` 1파일" 을 요구하는데, **같은 Task 3 의
  action 6 이 `app/CLAUDE.md` 를 고치라고 지시**한다(플랜 frontmatter `files_modified` 에도
  명시). 게이트를 문자 그대로 만족시키는 방법이 없다.
- **Fix:** 게이트의 의도(= 소스/로직 diff 0)를 보존한 채 문서 파일만 제외해 실행했다:
  `git diff --stat -- app backend ':!app/CLAUDE.md'` → 1파일(`runpod_inference/README.md`). 통과.
- **확인:** `git diff -- app/CLAUDE.md` 는 `## 차트 라이브러리` 코드블록 한 곳(-7/+4줄)뿐이고
  `.ts`/`.py` 변경 0. 최종 범위 검사에서도 소스는 `analysis.ts`(주석 4줄) ·
  `pose_engines/__init__.py`(docstring) · `runpod_inference/README.md` 뿐이다.
- **Commit:** `e5a71144`

### [Rule 3 - 차단 이슈] Task 2 의 이력-줄 예외가 줄바꿈된 항목을 못 덮는다

- **Found during:** Task 2
- **Issue:** verify 의 이력 예외는 `grep -v '^\*v'` 인데, 이력 항목 중 **v5 와 v4.3 은 두 줄로
  줄바꿈**돼 있고 그 이어지는 줄(공백 들여쓰기로 시작)에 `shared_base_motion_id` · `ViTPose` ·
  `clip_range` 가 들어 있다. 예외가 적용되지 않아 게이트가 실패한다.
- **Fix:** 그 두 항목의 **텍스트를 한 글자도 바꾸지 않고 줄만 합쳤다**(래핑 해제). 이력 삭제 0,
  내용 변경 0. 나머지 이력 항목(v4.2 · v6)은 손대지 않았다.
- **Commit:** `1ed93ea7`

### [Rule 3 - 차단 이슈] 이미 있던 경고 글리프(U+26A0)가 camelCase 치환 줄에 실려 이모지 게이트를 건드림

- **Found during:** Task 2
- **Issue:** `ref-sideway-spin` 의 `exec_peak_s: 9  # <U+26A0> 기본값 …` 줄은 키 이름을 바꿔야
  하는 줄이라, 치환 결과가 `+` 라인이 되면서 **기존** 글리프가 "추가된 이모지"로 집계됐다(1건).
- **Fix:** 그 줄 하나에서만 `# <U+26A0> 기본값 (…)` → `# 주의 — 기본값 (…)` 으로 뜻을 유지한 채
  글리프를 텍스트로 바꿨다. 문서의 다른 경고 표식(자유 다리 좌우 추정 등)은 손대지 않았다.
- **근거:** CLAUDE.md §7 이모지 금지 + 게이트 요구. 손대지 않은 줄은 그대로다.
- **Commit:** `1ed93ea7`

### [Rule 1 - 오타] STACK/CLAUDE 치환 문구 오타 즉시 수정

- **Found during:** Task 1
- **Issue:** `onnxruntime-gpu 로 돌다` 로 잘못 썼다.
- **Fix:** 커밋 전에 `돈다` 로 고쳤다. 두 파일(CLAUDE.md·STACK.md) 동일 반영.
- **Commit:** `12c59896`

## 지시대로 하지 않은 것 (의도적)

- **STATE.md 를 커밋하지 않았다.** Task 4 가 STATE.md 본문(Current Position 정정 + 판정 원장
  신설)을 고쳤지만, 오케스트레이터 지시(`docs 아티팩트는 커밋하지 마라`)에 따라 작업 트리에
  수정 상태로 남겼다. `git status --short .planning/STATE.md` → ` M .planning/STATE.md`.
  Task 4 커밋(`1fe7f228`)에는 debug 6파일만 들어갔다. ROADMAP·REQUIREMENTS 는 docs 아티팩트가
  아니므로 `689d7866` 에 포함했다.
- **죽은 코드를 제거하지 않았다** (belle "목록만"). BELLE-JUDGMENT §5 에 기록만.
- **`backend/template.yaml` 무접촉** (belle 판정 대기).
- **AWS 를 호출하지 않았다.** Pod 종료 절차는 문서 문구만 고쳤고 Lambda env/SSM 은 그대로다.
- **메모리 디렉터리(리포 밖)는 건드리지 않았다.**

## Known Stubs

없음 — 이번 작업은 문서·주석뿐이고 UI 데이터 경로를 만들지 않았다.

## Threat Flags

없음 — 새 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경 0. BELLE-JUDGMENT.md 에는
파라미터 이름·Pod ID·URL 만 적었고 토큰/키 값은 적지 않았다(T-qm2-03 완화).

## Self-Check: PASSED

```
FOUND: .planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-BELLE-JUDGMENT.md
FOUND: docs/reference-motions.md
FOUND: .planning/STATE.md
FOUND: backend/runpod_inference/README.md
FOUND: CLAUDE.md
FOUND: 12c59896  FOUND: 1ed93ea7  FOUND: e5a71144
FOUND: 1fe7f228  FOUND: 689d7866  FOUND: 421e25f0
```
