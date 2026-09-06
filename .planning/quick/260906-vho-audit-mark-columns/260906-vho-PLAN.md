---
quick_id: 260906-vho
slug: audit-mark-columns
date: 2026-09-06
status: planned
phase: quick-260906-vho
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/tests/test_fault_zoom.py
  - backend/tests/test_fault_zoom_advisory_user_marked.py
  - docs/contract.md
  - backend/scripts/audit_card_photos.py
  - backend/shared/python/sunity_shared/analysis/card_photo_audit.py
  - backend/tests/test_audit_card_photos_script.py
  - backend/tests/test_card_photo_audit.py
  - .planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py
autonomous: true
requirements: [QUICK-260906-vho]

must_haves:
  truths:
    - "advisory/legacy 카드 item 에 userMarked 가 실린다 — 평시 True, 앵커 게이트가 학생 측을 억제하면 False. refMarked 는 종전대로 criterion 카드만"
    - "감사(marked_flags)는 userMarked 키가 있는 카드에서 표시 유무를 추정하지 않는다. 키가 없는 옛 doc 은 종전 폴백(학생 True, 기준 = criterion 유무) 그대로"
    - "억제된 advisory 학생 패널은 mark_disagreement(판정 불가)가 아니라 no_mark_and_center_elsewhere(확정)로 판정되어 카드가 mismatch 로 센다. 2단(mark_part) 질의는 그 패널에 나가지 않는다"
    - "마지막 줄이 `card_photo_audit total=N mismatched=M unresolved=U mark_errors=A center_errors=B` — 기존 세 필드 뒤에 두 열을 덧붙인다. --replay 도 같은 줄을 낸다"
    - "라이브 JSON(audit_live_n2j.json) --replay 결과 = total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5 (판정 문자열·허용 집합 무변경의 실물 증거)"
    - "프로덕션 표시 문법·_CROP_FRAC(0.42)·마커 반지름(int(_OUT * 0.16)) byte-unchanged"
    - "백엔드 pytest failed 0 / skipped 20 / passed >= 4717 + 신규"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "userMarked 를 criterion 무관하게 방출하는 방출부"
      contains: "item[\"userMarked\"]"
    - path: "backend/tests/test_fault_zoom_advisory_user_marked.py"
      provides: "advisory 형상 카드의 userMarked 방출·억제·refMarked 부재 고정"
      min_lines: 60
    - path: "backend/shared/python/sunity_shared/analysis/card_photo_audit.py"
      provides: "panel_error_kind — 패널 사유를 mark/center 로 가르는 순수 함수"
      exports: ["panel_error_kind", "PANEL_ERROR_KINDS"]
    - path: "backend/scripts/audit_card_photos.py"
      provides: "per-key marked_flags + mark_errors/center_errors 집계"
      contains: "mark_errors="
    - path: "docs/contract.md"
      provides: "§11.11 userMarked 방출 범위 개정 (quick-260906-vho)"
      contains: "quick-260906-vho"
    - path: ".planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py"
      provides: "배달 패널 정중앙 계측기 v2 (커밋 편입)"
  key_links:
    - from: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      to: "backend/functions/pipeline/app.py::_fault_zoom_upload_items"
      via: "advisory batch item 의 userMarked bool 이 매퍼의 isinstance(bool) 게이트를 지나 doc 에 실린다"
      pattern: "isinstance\\(c\\.get\\(\"userMarked\"\\), bool\\)"
    - from: "backend/scripts/audit_card_photos.py::marked_flags"
      to: "sunity_shared.analysis.card_photo_audit::needs_mark_query / adjudicate"
      via: "marked=user_marked 인자 — 키가 있으면 doc 값, 없으면 폴백"
      pattern: "marked=user_marked"
    - from: "backend/scripts/audit_card_photos.py::_report"
      to: "sunity_shared.analysis.card_photo_audit::panel_error_kind"
      via: "userAdj/refAdj 마다 kind 를 세어 마지막 줄에 덧붙인다"
      pattern: "cpa\\.panel_error_kind"
---

<objective>
09-06 n2j 라이브 실증(6동작, uid NdVZrpbmUbPMNMjASFwUgy8Fj9p1)에서 확정된 감사 계기 결함 2건을 닫는다.

결함 1 — 감사가 advisory 카드의 표시 유무를 알 수 없다. `fault_zoom.py` 방출부가
`if unit.criterion is not None:` 안에서만 `userMarked`/`refMarked` 를 싣고, advisory 배치는
`criterion_units` 미전달이라 두 키가 없다. n2j(105fa15e)가 advisory 경로에도 앵커 억제 게이트를
걸어 학생 표시가 실제로 지워질 수 있게 됐는데, 감사 `marked_flags` 는 키 부재를 "학생 측 표시
있음"으로 추정한다. 그러면 1단 탈락 패널에 2단(mark_part) 질의가 나가고 눈이 `no_mark` 를 답해
`mark_disagreement`(판정 불가)가 된다 — 라이브 실물 `ref-peter-pan [1] advisory right_elbow
user=back_waist→no_mark None/mark:mark_disagreement`. 그 카드는 기준 패널도 틀려 mismatch 로
남았지만, 기준 패널이 멀쩡한 카드였다면 결말이 `unresolved` 로 갔다.

결함 2 — 집계가 "표시 오류"와 "중심 오류"를 구분하지 않는다. 앵커 게이트(j8g/n2j)가 하는 일은
틀린 표시를 지우는 것이지 틀린 사진을 고치는 것이 아니라서, 게이트가 일하면 패널 사유가
`mark_elsewhere` → `no_mark_and_center_elsewhere` 로 옮겨갈 뿐 둘 다 mismatch 로 세어져 게이트
효과가 마지막 줄에 안 잡힌다. `# mismatch cards` 블록은 이미 사유를 인쇄한다 — 없는 것은 집계다.

Purpose: 감사가 n2j 게이트를 재는 계기가 되게 한다 (SUMMARY "남은 것" 2번째 항목).
Output: userMarked 전 카드 방출(refMarked 는 criterion 유지) + 감사 per-key 플래그 + `panel_error_kind`
순수 함수 + 마지막 줄 `mark_errors=/center_errors=` 두 열 + 테스트 + contract §11.11 개정 +
계측기 v2 스크립트 커밋 편입.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/kimtaesung/Dev/SunityMotion/CLAUDE.md
@/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260906-n2j-stage-1-advisory/260906-n2j-SUMMARY.md
@/Users/kimtaesung/Dev/SunityMotion/backend/shared/python/sunity_shared/analysis/fault_zoom.py (방출부 3945-3985 만)
@/Users/kimtaesung/Dev/SunityMotion/backend/shared/python/sunity_shared/analysis/card_photo_audit.py
@/Users/kimtaesung/Dev/SunityMotion/backend/scripts/audit_card_photos.py
@/Users/kimtaesung/Dev/SunityMotion/backend/tests/test_fault_zoom_anchor_check.py (fixture 헬퍼 55-116 — 새 테스트가 복제한다)
@/Users/kimtaesung/Dev/SunityMotion/backend/tests/test_fault_zoom.py (1690-1697 `_brand_px_left_panel`, 1767-1775 `test_user_marked_absent_on_legacy_cards`)
@/Users/kimtaesung/Dev/SunityMotion/backend/tests/test_audit_card_photos_script.py (180-225)
@/Users/kimtaesung/Dev/SunityMotion/docs/contract.md (§11.9 1968-1982, §11.11 1983-1998)

## 09-06 실측 전제 (재조사 금지)

- 방출부의 `if unit.criterion is not None:` 이 refMarked/userMarked 를 criterion 카드로 한정한다.
  advisory 배치(pipeline/app.py:3612, 주석 "criterion_units 미전달")는 두 키가 없다.
- 학생 원 마커는 criterion 무관하게 `u_kind == 'valid'` 면 그려진다. 계획 시점 재현(anchor_check
  fixture, `criterion_units` 미전달, `draw_arrows=False`, `split_angle_present=False`):
  plain = 왼쪽 패널 브랜드색 1356px, `anchor_check -> {"user"}` = 0px, `-> {"ref"}` = 1356px,
  세 경우 모두 item 에 `userMarked`/`refMarked` 키 없음. legacy 경로(test_fault_zoom 1767 형상,
  conf 0.9)도 1356px — 즉 갱신될 테스트가 `userMarked is True` 를 단정할 수 있다.
- 기준 측은 게이트 B(quick-260705-wbs)로 legacy/advisory 무마킹이 **정책** — contract §11.9 가
  "false 를 실으면 앱이 없는 이유를 말한다"고 방출을 금한다. refMarked 방출 범위는 건드리지 않는다.
- 앱: `userMarked === false` 한 줄은 `sheetPrimaryZoom`(result.tsx:1595, `records.map(matchZoomForDeductionRecord)`
  = record 기준 매칭)에만 걸린다. `analysis.ts` 의 userMarked 주석은 "criterion 카드만"을 주장하지
  않아 TS 변경 0. 매퍼 `_fault_zoom_upload_items`(app.py:3761)는 tier 무관하게 bool 을 pass-through.
- 감사 `marked_flags` 현행: 두 키 중 하나라도 있으면 `card.get(k, True)`, 둘 다 없으면
  `(True, criterion is not None)`. 새 방출(advisory 에 userMarked 만)이 오면 refMarked 가 True 로
  기본값 처리돼 **거꾸로** 기준 측을 표시 있음으로 추정한다 — per-key 로 바꿔야 한다.
- 라이브 JSON `.planning/quick/260906-n2j-stage-1-advisory/evidence/audit_live_n2j.json`
  (미커밋, 로컬 존재): 18카드, advisory 전부 `userMarkedRaw/refMarkedRaw = "<absent>"`, 결말
  mismatch 6 / unresolved 0. 패널 사유 실측: `mark_elsewhere` 1(climb[2] ref),
  `no_mark_and_center_elsewhere` 5(pdshape[1] user, elbow-twist[1] ref, power-spin[1] user,
  power-spin[2] ref, peter-pan[1] ref). per-key 폴백은 이 JSON 의 결말을 바꾸지 않는다
  (advisory Raw 가 전부 부재 → 종전 폴백).
- `adjudicate` 가 `ok False` 를 내는 사유는 정확히 두 개: `mark_elsewhere`, `no_mark_and_center_elsewhere`.
- 회귀 기준선 4717 passed / 0 failed / 20 skipped. 실행: `cd backend && .venv/bin/python -m pytest -q`.
- 프로덕션 표시 문법·`_CROP_FRAC = 0.42`(fault_zoom.py:50)·`r = int(_OUT * 0.16)`(:1761) 은
  belle 판정 대기 항목 — 절대 무접촉.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: fault_zoom — userMarked 를 모든 카드에 방출 (refMarked 는 criterion 유지) + 테스트 + contract §11.11</name>
  <files>backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom_advisory_user_marked.py, backend/tests/test_fault_zoom.py, docs/contract.md</files>
  <behavior>
    - advisory 형상 build(criterion_units 미전달, joint_kinds deficit, draw_arrows False, split_angle_present False): 각 item 에 `criterion` 없음, `userMarked is True`, `refMarked` 키 없음, 왼쪽 패널 브랜드색 픽셀 > 0
    - 같은 build + `anchor_check=lambda ctx: frozenset({"user"})`: 각 item `userMarked is False`, `refMarked` 키 없음, 왼쪽 패널 브랜드색 픽셀 == 0 (플래그가 그림과 일치)
    - 같은 build + `anchor_check=lambda ctx: frozenset({"ref"})`: `userMarked is True` (반대측 무접촉), `refMarked` 키 없음
    - legacy 경로(test_fault_zoom 1767 형상): `userMarked is True`, `refMarked` 키 없음 — 기존 `test_user_marked_absent_on_legacy_cards` 의 기대값 교체
    - 기존 criterion 카드 테스트(test_fault_zoom (b')(c)(d), test_fault_zoom_ref_marked, test_fault_zoom_anchor_check, phase33/test_zoom_join_joint_exact) 전부 무변경 통과
  </behavior>
  <action>
    RED 먼저: `backend/tests/test_fault_zoom_advisory_user_marked.py` 신규. 모듈 docstring 에 quick-260906-vho 와
    잠그는 것 3줄(① advisory 카드도 userMarked 를 방출한다 ② 값은 그리는 코드가 인증한다 — 억제 시 False 이고
    픽셀도 0 ③ refMarked 는 §11.9 정책대로 키 부재)을 적는다. fixture 는 `test_fault_zoom_anchor_check.py` 55-116 의
    `_KP`/`_Match`/`_identity`/`_report`/`_frames`(`_FPS=12.0`, `_N=24`, `_SIZE=96`)를 그대로 복제하고,
    `_brand_px_left_panel` 은 `test_fault_zoom.py` 1690-1697 을 복제한다(테스트 모듈 간 import 금지 — 기존 관행).
    `_build_advisory(**kw)` 헬퍼는 pipeline/app.py:3612 advisory 배치 형상을 미러: `fault_joints=["left_shoulder","right_knee"]`,
    `joint_deltas` 20.0, `frames_fps=_FPS`, `joint_kinds={j: "deficit"}`, `dtw_match=_identity()`,
    `user_frame_candidates=[8,9,10,11,12]`, `ref_frame_candidates` 동일, `draw_arrows=False`,
    `split_angle_present=False`, `analysis_id="t"`, **criterion_units 를 넘기지 않는다**. behavior 의 첫 세 항목을
    테스트 3개로 쓴다. 실행해 3개 모두 FAIL(KeyError userMarked) 확인.

    GREEN: `fault_zoom.py` 방출부(3955-3980 부근)에서 `item["userMarked"] = bool(u_drew_legs or u_drew_angle or u_drew_circle)`
    한 줄을 `if unit.criterion is not None:` 블록 **밖**으로 옮겨 모든 item 에 실리게 한다. `item["refMarked"]` 는 블록 안에
    그대로 둔다. 주석 갱신: userMarked 항목의 "criterion 카드만 (legacy/advisory 는 키 부재 — refMarked 선례)" 문장을 지우고,
    (a) 학생 원 마커는 criterion 과 무관하게 `u_kind == 'valid'` 면 그려지므로 기준 측과 달리 정책 무마킹이 없다 — 값이 사실이다,
    (b) quick-260906-n2j 앵커 게이트가 advisory 학생 표시를 지울 수 있게 되어 감사(scripts/audit_card_photos.py marked_flags)가
    추정 대신 이 값을 읽는다 (quick-260906-vho), (c) refMarked 는 §11.9 정책대로 criterion 카드만 — 세 줄로 바꾼다.
    드로잉 코드·`_CROP_FRAC`·`int(_OUT * 0.16)`·`_supp`/`_u_plain` 경로는 한 글자도 만지지 않는다.

    `backend/tests/test_fault_zoom.py` 1767 `test_user_marked_absent_on_legacy_cards` 를
    `test_legacy_cards_emit_user_marked_but_not_ref_marked` 로 개명하고 docstring 을 "legacy(criterion 부재) 카드도
    userMarked 는 방출(학생 측은 정책 무마킹이 없다 — quick-260906-vho), refMarked 는 §11.9 정책대로 키 부재" 로,
    단정을 `comps[0]["userMarked"] is True and "refMarked" not in comps[0]` 로 바꾼다.

    `docs/contract.md` §11.11 (1983-1998): 표 아래 bullet 에 "**방출 범위 (quick-260906-vho):** `userMarked` 는 criterion
    유무·tier 와 무관하게 모든 카드에 방출 — 학생 측 원 마커는 criterion 과 무관하게 그려지므로(게이트 B 는 기준 측 정책)
    값이 사실이다. n2j 앵커 게이트가 advisory 학생 표시를 생략할 수 있어 감사가 추정 대신 이 값을 읽는다. `refMarked` 는
    §11.9 그대로 criterion 카드만. 앱 동작 불변 — 시트 한 줄은 record 기준 매칭 카드(`sheetPrimaryZoom`)에만 걸린다." 를
    추가한다. 3-way lockstep 줄의 TS 타입은 변경 없음(`userMarked?: boolean` 그대로).

    커밋 메시지 예: `fix(vho): advisory·legacy 카드도 userMarked 를 방출한다 — 감사가 표시 유무를 추정하지 않는다`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest -q tests/test_fault_zoom_advisory_user_marked.py tests/test_fault_zoom.py tests/test_fault_zoom_ref_marked.py tests/test_fault_zoom_anchor_check.py tests/test_pipeline_card_anchor_check.py tests/phase33/test_zoom_join_joint_exact.py && grep -c "^_CROP_FRAC = 0.42$" shared/python/sunity_shared/analysis/fault_zoom.py | xargs test 1 -eq && grep -c "r = int(_OUT \* 0.16)$" shared/python/sunity_shared/analysis/fault_zoom.py | xargs test 1 -eq && test "$(git diff -U0 -- shared/python/sunity_shared/analysis/fault_zoom.py | grep '^[-+]' | grep -v '^[-+][-+]' | grep -v '^[-+][[:space:]]*#' | wc -l | tr -d ' ')" -le 4 && grep -c "quick-260906-vho" ../docs/contract.md | xargs test 1 -le</automated>
  </verify>
  <done>advisory 형상 카드 3케이스(평시 True/억제 False/반대측 억제 True)와 legacy 카드가 userMarked 를 내고 refMarked 는 내지 않는다. fault_zoom.py 의 비주석 변경 줄 ≤ 4 (옮긴 한 줄뿐), 두 보호 상수 byte-unchanged. 기존 확대 카드 테스트 전부 통과. contract §11.11 에 방출 범위 개정 bullet.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 감사 marked_flags per-key — 새 방출이 있으면 추정하지 않는다 (옛 doc 폴백 유지)</name>
  <files>backend/scripts/audit_card_photos.py, backend/tests/test_audit_card_photos_script.py</files>
  <behavior>
    - `marked_flags({"criterion": None, "tier": "advisory", "userMarked": False})` == (False, False) — 새 방출: 학생 False 는 doc 값, 기준은 refMarked 부재 → 정책 폴백 False
    - `marked_flags({"criterion": None, "userMarked": True})` == (True, False)
    - `marked_flags({"criterion": "split_angle", "userMarked": True})` == (True, True) — criterion 카드에서 refMarked 만 없는 옛 형상은 종전대로 True
    - 기존 `test_marked_flags_absent_means_gate_b_for_advisory` 의 6개 단정 전부 그대로 통과
    - `replay_rows` 에 peter-pan [1] 형상 행(criterion None, tier advisory, joint right_elbow, expected elbow/hand/shoulder, user.observed back_waist, ref.observed elbow, userMark.observed no_mark, refMark None, userMarkedRaw False, refMarkedRaw "<absent>") → `userAdj == {"ok": False, "by": "none", "reason": "no_mark_and_center_elsewhere"}`, `verdict == "mismatch"`
    - 같은 행에서 `userMarkedRaw: "<absent>"`(옛 doc) → `userAdj.reason == "mark_disagreement"`, `verdict == "unresolved"` — 방출이 없으면 생기는 왜곡을 박제
    - `cpa.needs_mark_query(frozenset({"elbow","hand","shoulder"}), "back_waist", marked=False) is False` — 억제 패널에 2단 질의 0
  </behavior>
  <action>
    RED: `backend/tests/test_audit_card_photos_script.py` 에 `test_marked_flags_reads_each_key_independently` 와
    `test_replay_suppressed_advisory_is_mismatch_not_unresolved` 두 테스트를 behavior 대로 추가 (기존 180-190 테스트 옆).
    두 번째 테스트의 docstring 에 라이브 실물 한 줄(`ref-peter-pan [1] advisory right_elbow user=back_waist→no_mark
    None/mark:mark_disagreement`, 09-06 n2j)을 인용한다. 실행해 첫 테스트가 FAIL(현행은 (False, True) 반환) 확인.

    GREEN: `marked_flags` 를 per-key 로 바꾼다 — `user = bool(card["userMarked"]) if "userMarked" in card else True`,
    `ref = bool(card["refMarked"]) if "refMarked" in card else (card.get("criterion") is not None)`, 반환 `(user, ref)`.
    docstring 을 갱신: "키가 있는 측은 doc(렌더가 인증한 값)을 믿고, 없는 측만 정책으로 보정한다 — quick-260906-vho 부터
    advisory/legacy 카드에 userMarked 가 실리는데(refMarked 는 §11.9 정책대로 부재) 종전 규칙은 한 키만 있어도 나머지를
    True 로 기본값 처리해 기준 측을 거꾸로 표시 있음으로 읽었다. 옛 doc(둘 다 부재)은 종전 (True, criterion 유무)".
    `replay_rows` 는 손대지 않는다 — Raw 복원 뒤 같은 `marked_flags` 를 지나므로 per-key 가 자동 적용된다
    (테스트가 그것을 증명한다). 모듈 docstring 22-23줄 "표시 유무 = doc userMarked/refMarked" 문장 뒤에
    "(advisory 학생 측은 vho 부터 doc 값, 기준 측은 부재 = 정책 무마킹)" 을 덧붙인다.

    커밋 메시지 예: `fix(vho): 감사 marked_flags per-key — 방출된 userMarked 를 읽고 없는 측만 정책 폴백`.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest -q tests/test_audit_card_photos_script.py tests/test_card_photo_audit.py && .venv/bin/python scripts/audit_card_photos.py --replay ../.planning/quick/260906-n2j-stage-1-advisory/evidence/audit_live_n2j.json | tail -1 | grep -q "^card_photo_audit total=18 mismatched=6 unresolved=0"</automated>
  </verify>
  <done>per-key 폴백이 새 방출을 읽고 옛 doc 결말을 바꾸지 않는다(라이브 JSON replay 18/6/0 불변). 억제된 advisory 학생 패널이 확정 불일치로 판정되고 2단 질의가 나가지 않는다.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: 집계 — panel_error_kind 순수 함수 + 마지막 줄 mark_errors/center_errors 두 열 + 계측기 v2 커밋 편입</name>
  <files>backend/shared/python/sunity_shared/analysis/card_photo_audit.py, backend/scripts/audit_card_photos.py, backend/tests/test_card_photo_audit.py, backend/tests/test_audit_card_photos_script.py, .planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py</files>
  <behavior>
    - `panel_error_kind(adjudicate(exp, "back_waist", "thigh", marked=True))` == "mark" (mark_elsewhere)
    - `panel_error_kind(adjudicate(exp, "back_waist", None, marked=False))` == "center" (no_mark_and_center_elsewhere)
    - center_in_expected / mark_in_expected / mark_disagreement / unreadable / mark_unobserved / no_expectation → None
    - 완전성: adjudicate 가 `ok False` 를 내는 두 결말 모두 kind 가 None 이 아니고, `set(PANEL_ERROR_KINDS) == {"mark", "center"}`
    - `_report` capsys: 행 5개(mismatch: userAdj mark_elsewhere + refAdj center_in_expected / mismatch: 양측 no_mark_and_center_elsewhere / unresolved: userAdj mark_disagreement + refAdj center_in_expected / ok: 양측 center_in_expected / fetch 실패 행: verdict 키 없음) → 마지막 줄 정확히 `card_photo_audit total=5 mismatched=2 unresolved=1 mark_errors=1 center_errors=2`, 그 앞줄은 `card_photo_audit unaudited=1 tier2_panels=...` 로 시작
    - 라이브 JSON --replay 마지막 줄 == `card_photo_audit total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5`
  </behavior>
  <action>
    RED: `backend/tests/test_card_photo_audit.py` 에 `test_panel_error_kind_splits_mark_and_center` (behavior 1-4),
    `backend/tests/test_audit_card_photos_script.py` 에 `test_report_appends_mark_and_center_error_columns(capsys)` (behavior 5)
    추가. `_report(rows, model="m", rounds=3, out_path=None)` 를 직접 부른다 — 행에는 인쇄에 필요한 키
    (`reference`, `index`, `tier`, `joint`, `criterion`, `user`, `ref`, `userMark`, `refMark`, `userAdj`, `refAdj`, `verdict`)를
    넣고, fetch 실패 행은 `{"error": "...", "audit": {...}}` 만 둔다. 실행해 두 테스트 FAIL 확인.

    GREEN (card_photo_audit.py): `card_verdict` 아래에 `PANEL_ERROR_KINDS = ("mark", "center")` 와
    `panel_error_kind(adj: dict) -> str | None` 을 추가한다 — `adj.get("ok") is not False` 면 None, 그 외
    `{"mark_elsewhere": "mark", "no_mark_and_center_elsewhere": "center"}.get(reason)`. docstring 에 왜(게이트는 틀린
    표시를 지우지 틀린 사진을 고치지 않는다 — 게이트가 일하면 사유가 mark → center 로 옮겨갈 뿐 둘 다 mismatch 라 마지막
    줄에 효과가 안 잡혔다, quick-260906-vho)와 결말 표 인용을 적고 `__all__` 에 두 이름을 넣는다. numpy/card_gates import 0 유지.

    GREEN (audit_card_photos.py `_report`): `mark_errors`/`center_errors` 를 `rows` 의 `userAdj`/`refAdj` 마다
    `cpa.panel_error_kind` 로 세고(키 없는 fetch 실패 행은 건너뜀), 마지막 줄을
    `card_photo_audit total={total} mismatched={mismatched} unresolved={unresolved} mark_errors={mark_errors} center_errors={center_errors}`
    로 바꾼다 — 기존 세 필드는 순서·이름 그대로, 뒤에 덧붙이기만. 앞줄 `unaudited=/tier2_panels=` 도 무변경.
    모듈 docstring 42-46줄의 불변식 설명을 새 줄 형식으로 갱신하고 "mark_errors = 표시가 딴 부위에 놓인 패널(mark_elsewhere),
    center_errors = 표시 없이 사진 중심이 딴 부위인 패널(no_mark_and_center_elsewhere). 앵커 게이트가 일하면 전자가 후자로
    옮겨간다 — mismatched 는 그대로여도 이 두 열이 게이트 효과를 보인다" 를 적는다. `--replay` 는 같은 `_report` 를 타므로
    분기 0. `expected_parts`·판정 문자열·`card_verdict` 무접촉.

    계측기 v2: `.planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py` 를 **내용 수정 없이**
    이 태스크의 커밋 파일 목록에 포함한다(`git add` 만). 삭제·재작성 금지. 다른 미커밋 evidence 파일은 이 단위 범위 밖 —
    건드리지 않는다.

    커밋 메시지 예: `feat(vho): 감사 집계에 mark_errors/center_errors 두 열 — 앵커 게이트 효과가 마지막 줄에 보인다`
    (본문에 계측기 v2 편입 한 줄).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest -q tests/test_card_photo_audit.py tests/test_audit_card_photos_script.py tests/test_anchor_part_check.py tests/test_card_gates.py && test "$(.venv/bin/python scripts/audit_card_photos.py --replay ../.planning/quick/260906-n2j-stage-1-advisory/evidence/audit_live_n2j.json | tail -1)" = "card_photo_audit total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5" && grep -v '^\s*#' shared/python/sunity_shared/analysis/card_photo_audit.py | grep -c "^import numpy\|^from numpy\|card_gates" | xargs test 0 -eq && cd /Users/kimtaesung/Dev/SunityMotion && git ls-files --error-unmatch .planning/quick/260906-n2j-stage-1-advisory/evidence/panel_center_eye_measure_v2.py >/dev/null</automated>
  </verify>
  <done>마지막 줄이 기존 세 필드 뒤에 두 열을 덧붙이고, 라이브 JSON replay 가 1/5 로 갈라 센다. panel_error_kind 가 adjudicate 의 ok False 두 결말을 남김없이 분류한다. 계측기 v2 가 git 추적 대상이다. (git ls-files 게이트는 커밋 후 실행 — 커밋 전이면 `git add` 뒤 재실행.)</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 감사 스크립트 | `userMarked`/`refMarked` 필드 타입은 외부 데이터 — bool 강제 |
| presigned URL / S3 → 감사 스크립트 | 카드 PNG 다운로드 (기존 경로, 무변경) |
| fault_zoom 방출 → Firestore doc | 새로 advisory 카드에 bool 한 개 추가 — 매퍼의 `isinstance(bool)` 게이트 통과 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-vho-01 | Tampering | `marked_flags` 입력(doc 필드) | mitigate | `bool()` 강제 + 키 부재 정책 폴백; 매퍼 `isinstance(c.get("userMarked"), bool)` 가 비-bool 을 걸러 doc 에 안 싣는다 (기존) |
| T-vho-02 | Information disclosure | `--out` JSON / evidence 로그의 uid·analysisId | accept | 리포 내부 evidence 관행(j8g/n2j 동일), PII 없음(익명 uid) |
| T-vho-03 | Denial of service | 감사 눈 호출 비용 | mitigate | per-key 플래그로 억제 패널의 2단 질의가 0 이 된다 — 호출 수 감소 방향만 |
| T-vho-SC | Tampering | 패키지 설치 | n/a | 이 단위에 npm/pip/cargo 설치 0 — 레거시 게이트 대상 없음 |
</threat_model>

<verification>
전체 회귀 (rtk 없이, 커밋 전 마지막 게이트):
`cd /Users/kimtaesung/Dev/SunityMotion/backend && .venv/bin/python -m pytest -q 2>&1 | tail -3`
→ `failed` 0, `skipped` 20, `passed` ≥ 4717 + 신규(T1 3 + T1 개명 0 + T2 2 + T3 2 = 최소 4724).

실물 확인 (눈 호출 0):
`cd backend && .venv/bin/python scripts/audit_card_photos.py --replay ../.planning/quick/260906-n2j-stage-1-advisory/evidence/audit_live_n2j.json | tail -1`
→ `card_photo_audit total=18 mismatched=6 unresolved=0 mark_errors=1 center_errors=5`

무접촉 확인: `git log -1 --stat` 에 fault_zoom.py 변경이 방출부 한 줄 이동 + 주석뿐 — `_CROP_FRAC`·`int(_OUT * 0.16)`·드로잉 코드 diff 0.

라이브 재검증(다음 Pod)은 이 단위 범위 밖 — SUMMARY "남은 것"에 "배포 후 advisory 카드 doc 에 userMarked 가 실리는지 + 억제 시 감사 결말이 mismatch 인지 확인" 을 적는다.
</verification>

<success_criteria>
- advisory/legacy 카드 item 에 `userMarked` 방출(평시 True, 억제 False), `refMarked` 는 criterion 카드만 (contract §11.9 정책 유지, §11.11 개정)
- 감사가 방출된 `userMarked` 를 읽고 없는 측만 정책 폴백 — 억제된 advisory 학생 패널이 `no_mark_and_center_elsewhere`/mismatch 로 판정, 2단 질의 0
- 마지막 줄 `... mark_errors=A center_errors=B` 덧붙임, 기존 필드·`--replay`·허용 집합·판정 문자열 불변; 라이브 JSON replay 18/6/0 + 1/5
- 프로덕션 표시 문법·`_CROP_FRAC`·마커 반지름 byte-unchanged (grep 게이트 + diff 줄 수 게이트)
- 계측기 v2 스크립트 git 추적
- 백엔드 전체 failed 0 / skipped 20 / passed ≥ 4724
</success_criteria>

<output>
Create `.planning/quick/260906-vho-audit-mark-columns/260906-vho-SUMMARY.md` when done — 한 일(커밋 3건 표), 왜(라이브 실물 한 줄 + replay 1/5), 남은 것(다음 Pod 라이브 재검증), 게이트(pytest 수치).
</output>
