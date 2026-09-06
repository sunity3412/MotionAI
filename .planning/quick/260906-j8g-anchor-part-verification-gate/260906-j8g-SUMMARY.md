---
phase: quick-260906-j8g
plan: 01
subsystem: analysis-cards
tags: [card_gates, card_photo_audit, fault_zoom, gemini-vision, machine-eye, pipeline]

# Dependency graph
requires:
  - phase: quick-260906-f4j
    provides: "붕괴 앵커 이동(nearest_usable_frame·_frame_usable) + ROOT-CAUSE.md 36패널 실측(좌표 OK 15/틀림 14/못읽음 7)"
  - phase: quick-260905-mvm / quick-260905-ota
    provides: "card_photo_audit 순수 판정 층·expected_parts·eye_judge(claim=part) 운영 질문·감사 스크립트 modal_token"
  - phase: quick-260903-upx
    provides: "게이트는 표시만 정한다 — suppress_marks 경로, userMarked/refMarked"
provides:
  - "card_photo_audit.modal_token / anchor_verdict(ok|mismatch|unreadable|no_expectation) — 순수, numpy 0"
  - "card_gates: ANCHOR_CHECK_CROP_FRAC=0.18 / MAX_RETRY=2 / ROUNDS=3 + part_crop(무마킹) + eye_part_token(2표 조기 종료) + anchor_retry_frames(_frame_usable 공유) + verify_anchor_side 상태기계"
  - "pipeline._run_gated_card_inherit: gated 카드 양측 앵커 확인 → moved(프레임 이동)/suppressed(표시만 생략)/pass/unbound, 캐시·eye_calls 합산·S3 eye 원장 additive"
  - "로그 2종: 카드당 측별 fault_zoom_anchor_check / 문서당 fault_zoom_anchor_check_summary"
affects: [gated-card-path, fault-zoom-cards, pod-live-verification, audit_card_photos]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "판정(순수)·눈/프레임(card_gates)·처분(pipeline) 3층 — 상한(재확인 2·라운드 3)은 순수 함수가 소유"
    - "눈 확인 실패 처분 = 이동 → 표시 생략, 카드 삭제 권한 0 (belle 09-03 규칙 1 유지)"
    - "배선 단언은 app.py 텍스트 절단(_gated_body) — 흐름 제어(continue)·목록 조작 부재로 '사진 장수 불변' 증명"

key-files:
  created:
    - backend/tests/test_anchor_part_check.py
  modified:
    - backend/shared/python/sunity_shared/analysis/card_photo_audit.py
    - backend/shared/python/sunity_shared/analysis/card_gates.py
    - backend/scripts/audit_card_photos.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_gated_frame_skips_collapse.py

key-decisions:
  - "크롭 프레임 원천 = 카드와 같은 픽셀 원천(native_or_downscaled) — 측정 스크립트가 리포 밖(scratchpad 휘발)이라 원천 미기록, 카드 기준으로 정함"
  - "unreadable(못 읽음)은 pass — 축소본 폴백(640px, 크롭 ≈65px)에서 못 읽음이 늘 수 있고 그것으로 표시를 지우면 카드가 운으로 사라진다"
  - "stage-1(3488)·advisory(3531) 호출부 무접촉 — gated 경로가 belle 이 보는 감점 카드이고 f4j 실측 붕괴·이동은 전부 gated 였다"
  - "좌표 우선순위 미러는 측별 — fault_zoom 의 both-or-neither(양측 vertex 성립 시만 vertex 중심)는 카드 합성 시점 결정이라 확인 시점엔 측별 근사(단일 관절 비-어깨 각도에선 vertex==_anchor_xy 로 동일)"

patterns-established:
  - "눈 호출 상한 산식을 순수 함수 docstring + SUMMARY 에 박제: 측당 (1+MAX_RETRY)×ROUNDS"

requirements-completed: [quick-260906-j8g]

# Metrics
duration: 13min
completed: 2026-09-06
---

# Quick 260906-j8g: 앵커 부위 확인 게이트 Summary

**gated 카드마다 학생·기준 양측 앵커 좌표를 짧은 변 0.18 무마킹 크롭으로 기계 눈에 확인 — 틀리면 창 안 건전 프레임 ≤2 재확인 후 이동, 그래도 틀리면 사진은 남기고 표시만 생략. 순수 층(판정·상태기계) + 얇은 배선, 오프라인 테스트 32건, 전체 4701/0/20.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-09-06T05:07:47Z
- **Completed:** 2026-09-06T05:21:04Z
- **Tasks:** 2 (Task 1 TDD: test → feat)
- **Files modified:** 6 (created 1, modified 5)

## Accomplishments

- 09-06 실측의 결론("신뢰도로도 붕괴로도 못 거르니 보는 수밖에 없다")을 카드 생산 경로에 붙였다 — 좌표가 제목의 부위가 아니면 카드가 그대로 나가던 구조가 닫힘.
- 처분은 표시만: `verify_anchor_side` 의 action 4종(pass/moved/suppressed/unbound) 어느 것도 방출을 바꾸지 않는다. dataclass 에 emit/drop 류 필드 자체가 없고, 배선 블록에 `continue`/`gated_raw`/`units.remove` 가 없음을 source 단언이 고정.
- 비용은 순수 함수가 소유: `ANCHOR_CHECK_MAX_RETRY=2`(호출측이 후보 5개를 줘도 앵커+2), `ANCHOR_CHECK_ROUNDS=3` + 2표 조기 종료, (측,프레임,관절,좌표) 캐시, 이미 suppress 된 측 0회.
- 사후 판별 흔적: 카드당 측별 `fault_zoom_anchor_check … trail=30:elbow/mismatch,29:knee/ok …` + 문서당 `fault_zoom_anchor_check_summary … pass= moved= suppressed= unbound= recheck=` + S3 eye 원장(claim=part, expected 동반, 크롭 PNG).

## Task Commits

1. **Task 1 (RED): 순수 층 실패 테스트** - `90ea18a6` (test) — 26 failed, 전부 AttributeError(함수 부재) 확인 후 커밋
2. **Task 1 (GREEN): card_photo_audit·card_gates·스크립트 alias** - `05174665` (feat) — 4 파일 114 passed
3. **Task 2: gated 호출부 배선 + source 단언 + f4j 슬라이스 조정** - `e58a2edb` (feat) — 전체 4701 passed / 0 failed / 20 skipped

**Plan metadata:** 오케스트레이터 docs 커밋 (이 실행자는 docs 미커밋 — 제약 준수)

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/card_photo_audit.py` — `modal_token`(스크립트에서 이관) + `ANCHOR_VERDICTS`/`anchor_verdict`. import 는 `from __future__` 하나뿐(numpy/card_gates 0 — 실행 확인: `import` 후 `sys.modules` 에 sunity_shared 3개만).
- `backend/shared/python/sunity_shared/analysis/card_gates.py` — 새 절 "앵커 부위 확인": 상수 3(근거 주석·재튜닝 금지), `part_crop`(링 0, mark_crop 무접촉), `eye_part_token`(claim="part" 그대로, expected_limb/joint_kind 미전달), `anchor_retry_frames`(`fz._frame_usable` 공유, −d 먼저), `AnchorCheckOutcome`/`verify_anchor_side`. `machine_eye`·`_eye_verdict`·질문·스키마 byte 무변경.
- `backend/scripts/audit_card_photos.py` — `modal_token = cpa.modal_token` (중복 정의 0, 기존 스크립트 테스트 그대로 통과).
- `backend/functions/pipeline/app.py` — `_run_gated_card_inherit` 안만(hunk 4897/4972/5397/5672, 함수 끝 5748): `cpa` import, `anchor_stats`/`_anchor_cache`, f4j 이동 직후 확인 블록(`_xy_for_check` 좌표 우선순위 미러 → `_ask_part` 캐시·크롭·눈·원장 → 양측 루프 → 교차 재확인), 요약 로그 1행(부착 완료 로그 **앞**, 문자열 무변경).
- `backend/tests/test_anchor_part_check.py` — 32 테스트(순수 26 + 배선 source 6). 눈 호출 전부 가로채기(monkeypatch `cg.eye_judge` / 대본 `ask`), 라이브 호출 0.
- `backend/tests/test_gated_frame_skips_collapse.py` — `test_moved_side_drops_freeze_moment_payload` 슬라이스 끝을 `r9 = r9_new` 로 좁힘(f4j 블록 자체의 suppress 무접촉 단언 유지, 새 블록은 그 뒤).

## belle 보고 수치 (plan 필수 항목)

### (a) 눈 호출 수 산식 — 카드당·문서당

| | 측당 | 카드당(양측) | 문서당(카드 ≤5) |
|---|---|---|---|
| 통상 (앵커 ok, 2표 조기 종료) | 2 | **4** | **≈20** |
| 최악 (앵커 mismatch + 재확인 2 × 3라운드) | (1+2)×3 = 9 | 18 | 90 |
| 최악 + 교차 재확인(카드당 최대 1측, +3) | — | **21** | **≈105** |

- 통상 카드당 4 = 기존 `_eye_check`(학생 1측, 불일치 시만 다수결)에 **더해지는** 호출. 캐시(측,프레임,관절,좌표)로 같은 질문 반복 0, 이미 suppress 된 측 0회, `expected` 빈 집합·좌표/프레임/키 부재 0회.
- 교차 재확인이 카드당 최대 1측인 이유: display_anchor 로 통과한 측이 재확인 대상인데, 한 측이 이동하면 display_anchor 가 None 이 되어 다른 측은 처음부터 rep12 좌표로 검사(재확인 불요).

### (b) 지연 — 미실측

호출당 지연은 이번 quick 에서 **재지 않았다**(오프라인 테스트만, 라이브 0). 다음 Pod 에서 `fault_zoom_anchor_check` 행의 `eye_calls` 와 로그 타임스탬프 간격으로 잰다. 산식상 문서당 통상 ≈20 호출이 기존 `_eye_check` 위에 얹히므로 카드 부착 단계가 그만큼 길어진다 — 수치는 실측 전까지 말하지 않는다.

### (c) 크롭 프레임 원천 — 측정 스크립트 미보존

36패널 측정 스크립트는 리포 밖(scratchpad, 휘발)이라 **크롭을 원본 프레임에서 잘랐는지 640px 축소본에서 잘랐는지 기록이 없다**. 이번 구현은 "카드와 같은 픽셀 원천"(`fault_zoom.native_or_downscaled` — 원본 우선, 실패 시 축소본)으로 정했다. 축소본 폴백(640px)에서는 크롭이 ≈65px 라 못 읽음(unclear)이 늘 수 있고, 그것은 **비구속(pass)** 이다 — 못 읽음으로 표시를 지우면 카드가 운으로 사라진다(09-03 눈 비결정 교훈). 측정과 원천이 다르면 OK/틀림 비율도 다를 수 있음을 라이브에서 확인해야 한다.

### (d) stage-1(3488)·advisory(3531) 호출부를 안 건드린 이유

gated 경로가 belle 이 보는 감점 카드이고, f4j 09-06 실측에서 붕괴 14패널·이동 전부가 gated 카드였다(stage-1·advisory 붕괴 0). 09-06 36패널 좌표 실측의 불일치도 감점 카드에 몰려 있다. stage-1/advisory 는 다음 단위 — `test_stage1_and_advisory_call_sites_untouched` 가 app.py 전체 비주석 `verify_anchor_side(` == 2(둘 다 gated 본문 안)를 고정한다.

### (e) 라이브 미검증 — 다음 Pod 절차

이 quick 은 **라이브 검증 없음**(Pod 는 시연 때만, belle 08-28). 배선 성립 증거는 py_compile + source 단언 6건 + 순수 층 테스트 26건뿐 — `_run_gated_card_inherit` 자체는 env 의존이라 오프라인 실행 0. 다음 Pod 때:
1. 09-03 6영상 재분석(번들은 Pod HEAD 부터 반입) → `fault_zoom_anchor_check` / `fault_zoom_anchor_check_summary` 로그 회수(호출 수·지연 실측, action 분포).
2. `backend/scripts/audit_card_photos.py --rounds 5` 재감사 — 감점 카드 불일치 4장이 줄어드는지, 신규 불일치 0 인지.
3. S3 `results/{uid}/{aid}/eye/ledger.json` 의 claim=part 항목(크롭 PNG)으로 눈이 본 것을 사람 눈으로 대조.
완료 신호는 로그 "대체 부착 완료" 회수 뒤(faultZoomStatus=done 아님).

### 모델 문자열

`eye_part_token` 의 모델은 `DEFAULT_C_MODEL`(런타임 `gemini/config.py` 정본) — 36패널 측정 당시 모델(ROOT-CAUSE: gemini-3.8-flash)과 **다를 수 있다**. 라이브 결과가 측정과 어긋나면 모델 차이를 먼저 의심한다.

## Decisions Made

- 좌표 우선순위 미러(`_xy_for_check`)는 **측별**: ① display_anchor(안 옮긴 측) ② 단일 관절 각도 criterion 의 `criterion_vertex_xy`(rep12; 학생 `_gated_kp` / 기준 `make_reference_anchor_resolver`) ③ `_member_pts` valid(비면 align_bake seam 2 주입) 의 `_anchor_xy` ④ None=비구속. fault_zoom 의 both-or-neither(양측 vertex 성립 시만 vertex 중심)는 카드 합성 시점의 쌍 결정이라 확인 시점엔 측별 근사 — 단일 관절 비-어깨 각도에선 vertex == `_anchor_xy` 로 동일하고, 어깨(겨드랑이 근사점)만 한 측 vertex 실패 시 어긋날 수 있다. 라이브에서 어깨 카드 trail 을 따로 본다.
- 교차 재확인은 재확인 프레임 0(`retry_frames=[]`) — 이미 이동 결정이 끝난 뒤라 프레임을 다시 옮기지 않고 그릴 좌표만 한 번 더 본다.
- 원장 항목은 기존 업로드 블록의 요구(`side`/`joint`/`png`)만 맞춘 additive — `claim="part"`, `expected`, `frameSpace="video9"` 로 기존 bent/extended 항목과 구분.

## Deviations from Plan

### Verify 게이트 정밀도 (코드 변경 없음, 기록만)

**1. Task 1 grep 게이트 `card_photo_audit.py` 의 `card_gates` 문자열 0 — 문자 그대로는 성립 불가**
- **Found during:** Task 1 verify
- **Issue:** `grep -v '^\s*#' … | grep -c "^import numpy\|^from numpy\|card_gates"` 는 `#` 주석만 거르고 **docstring 산문**은 세므로, 변경 전(76be5abd)에도 이미 3(mvm 이 남긴 "card_gates.eye_judge" 등), 변경 후 7.
- **Fix:** 게이트의 의도(import 부재)를 엄격 패턴으로 검증 — `^(import numpy|from numpy|from .* card_gates|import .*card_gates)` = **0**, import 줄은 `from __future__ import annotations` 하나, 모듈 import 후 `sys.modules` 의 sunity_shared 항목 3개(card_gates/numpy 없음). 코드는 plan 대로(numpy 0, card_gates import 0).
- **Files modified:** 없음
- **Verification:** 위 명령 출력 `STRICT_IMPORT_MATCHES=0` / `PRE_EXISTING_PROSE_MATCHES=3`

나머지는 plan 대로 실행 — 새 튜닝값 0.18 하나(측정값), 모델 문자열 하드코딩 0, 이모지 0, 채점·방출 필드·hold/pair/_eye_check·stage-1·advisory·어깨 각도 문법·fault_zoom.py 무접촉(`git diff --name-only 76be5abd` = 6 파일 정확히, fault_zoom.py 작업 트리 clean).

---

**Total deviations:** 0 코드 변경 (verify 게이트 해석 1건 기록)
**Impact on plan:** 없음

## Issues Encountered

None.

## Known Stubs

None — 하드코딩 빈값/placeholder/TODO 0 (added 행 grep 결과 `none`).

## Threat Flags

없음 — 새 네트워크 경계 0(기존 Gemini generateContent 경로에 크롭 JPEG 만), 새 S3 키 규칙 0(기존 `eye/` 하위 additive), 클라이언트 입력 0. T-j8g-02(비용 상한)·T-j8g-04(흔적)는 순수 함수 상한 + 로그 2종으로 이행.

## User Setup Required

None — 기존 `GEMINI_API_KEY`(Pod env) 그대로. 키 부재 = 비구속(카드 유지).

## Next Phase Readiness

- 다음 Pod 세션 첫 일: (e) 절차 — 6영상 재분석 → 로그 회수 → `audit_card_photos.py --rounds 5` 재감사. 판정 기준: 감점 카드 불일치 4장 감소 + 신규 불일치 0 + 호출 수/지연 실측치.
- 결과가 "못 읽음 다수" 면 (c) 축소본 폴백 여부부터 확인(로그 `fault_zoom_crop` 의 프레임 해상도와 대조).
- stage-1·advisory 경로 확장은 gated 라이브 결과 뒤 별도 단위.
- STATE.md / ROADMAP.md 는 이 실행자가 건드리지 않음(quick 제약 — 오케스트레이터 docs 커밋).

---
*Phase: quick-260906-j8g*
*Completed: 2026-09-06*

## Self-Check: PASSED

- 파일 7건 존재(생성 1·수정 5·SUMMARY) / 커밋 3건(90ea18a6·05174665·e58a2edb) 이력 존재 / artifact contains 마커 3건(anchor_verdict·verify_anchor_side·cg.verify_anchor_side() 확인 — 위 명령 출력.
