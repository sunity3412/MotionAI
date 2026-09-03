---
phase: quick-260903-upx
plan: 01
type: execute
wave: 1
depends_on: [quick-260903-lpl]
files_modified:
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/functions/pipeline/app.py
  - backend/tests/test_card_gates.py
  - backend/tests/test_fault_zoom.py
  - backend/shared/python/sunity_shared/models.py
  - docs/contract.md
  - app/src/types/analysis.ts
  - app/src/components/DeductionDetailSheet.tsx
autonomous: true
requirements: [quick-260903-upx]
must_haves:
  truths:
    - "감점 record 마다(criterion unit 이 있는 것 전부) 확정 확대 사진이 1장 있다 — 카드 상한·기준 대응 실패·좌표 부재·게이트(멈춤·짝·눈) 결과·표시 좌표 부재 어느 것도 사진을 없애지 않는다"
    - "게이트는 표시만 정한다: 눈이 불일치(observed≠claim 또는 arm↔leg 상충)면 학생 패널 표시(선·원·호)를 그리지 않고 userMarked=false. 멈춤/짝 결과는 holdState/pairState 로 doc 에 남긴다"
    - "비교 영상이 멈추는 순간(freeze)이 있는 record 는 그 순간에서 사진을 만들고(inherit), freeze 가 없는 record 는 1단계 카드가 그대로 남는다 — 최종 부착이 1단계 카드를 없애지 않는다"
    - "카드 수 불변식이 로그로 증언된다: `card_gates 대체 부착 완료 … expected_units=N emitted=N` (N = criterion_units_from_records 상한 없이 낸 unit 수). 부족하면 WARNING"
    - "advisory 카드·채점·원장 기존 필드·응답 스키마 무접촉. pytest 4589/0 → 신규 포함 전부 pass, 앱 tsc 0 · node --test 219/0"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      provides: "decide_card(hold_reason, pair_reason, eye_match, eye_why) → CardDecision(emit=True, draw_user_marks, holdState, pairState, eyeState) 순수 함수"
      contains: "def decide_card"
    - path: "backend/functions/pipeline/app.py"
      provides: "_run_gated_card_inherit 무삭제 + 1단계 카드 보존 병합 + expected/emitted 로그"
      contains: "expected_units="
    - path: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      provides: "criterion 카드 ref 대응 실패·양측 좌표 부재 시에도 방출(전신 폴백, 표시 생략) + suppress_user_marks 렌더 옵션 + userMarked 방출"
      contains: "userMarked"
---

<objective>
멈춤 구간마다 확대 사진 1장 보장 — 모든 동작에서, 검사는 표시만 조정.

**belle 09-03 (원문):** "확대사진을 그 멈추는 구간은 다 보여줘야하고, 그걸 모든 동작에서 통과시켜야한다. 지금처럼 짜맞추는게
아니라 매번 사용자가 올렸을 때 그 동작을 캐치해서 확대사진을 넣어줘야하는데" / "pdshape 는 5개잖아 멈추는 동작(음성나오는
구간)이 근데 왜 또 4개야". 실측: pdshape 감점 5 = 비교 영상 정지 5(r00~r04) 인데 사진은 08-09 에 4장(상한 4), 09-03 에 2장
(게이트가 2장 삭제). 클라임은 눈 오판으로 0장이었던 이력.

**사진이 사라지는 지점 5곳(코드로 확인) → 전부 "사진은 남기고 표시만" 으로:**

| # | 위치 | 지금 | 바꿈 |
|---|---|---|---|
| 1 | `fault_zoom.criterion_units_from_records(max_units=4)` — 1단계·게이트 양쪽 호출 | 5번째 record 부터 카드 없음 | 상한 = record 수(호출측이 `max_units=len(records)` 전달) |
| 2 | `fault_zoom.build_fault_zoom_comparisons` ~3308 `if unit.criterion is not None and ref_match_failed_unit: continue` | 기준 대응 실패 시 criterion 카드 미방출 | 방출 — ref 전신 폴백 + `refMatch='failed'`(legacy 경로와 동일 처리), 학생 측은 그대로 |
| 3 | 같은 함수 ~3338 `if not u_valid and not r_valid: continue` | 양측 좌표 없음 시 미방출 | 방출 — 양측 전신 폴백, 표시 없음(`userMarked=false`, `refMarked=false`) |
| 4 | `app.py _run_gated_card_inherit` 게이트 루프 (~5075-5120): hold/pair/eye FAIL → `dropped`, `freeze_sec_invalid`, `no_freeze` | 카드 삭제 | 삭제 0. hold/pair 결과는 플래그로만. 눈 불일치 = 학생 표시 생략. `no_freeze`·`freeze_sec_invalid` record 는 1단계 카드 보존 |
| 5 | 같은 함수 ~5290 `display_anchor drop … continue` (align 좌표 게이트 미달) | 카드 미방출 | 방출 — 그 측 표시 생략(anchor 없는 측만), 카드는 남김 |
| 6 | 최종 부착 ~5340 `final = items + advisory_keep` | 1단계 카드 전부 대체 | `final = 게이트 카드 + (게이트가 못 낸 record 의 1단계 카드) + advisory` — record(criterion) 기준 병합, 중복 0 |

**손대지 않는 것:** 채점, advisory 선별, 눈 질문·다수결·몸통 관절 제외(jka/jxn/lpl), 원장 기존 필드, 게이트 순서, 앱 문구(아래 1문장 제외), 계약의 기존 필드 의미.
</objective>

<context>
읽을 것(순서대로):
- `backend/functions/pipeline/app.py` 4827-5400 `_run_gated_card_inherit` 전체 (게이트 루프 5075-5120, verdict 로그 5122-5135, units 5150, 렌더 루프 5210-5330, 부착 5335-5365, 원장 5367-5395)
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` 169-215 `criterion_units_from_records`, 2814-2990 `build_fault_zoom_comparisons` docstring, 3100-3140(ref_match_failed_unit), 3300-3345(두 skip), 3580-3630(angle_bake user_gate/ref_gate 침묵 — 표시 생략 선례), 3775-3845(refMatched/refMarked/refMatch 방출부), `_side_crop` 1532~
- `backend/shared/python/sunity_shared/analysis/card_gates.py` 220-410 (HoldResult/PairResult/hold_gate/pair_gate), 이번 세션 추가분(_eye_check 호출부 app.py 4978-5050)
- `backend/tests/test_fault_zoom.py` 에서 `ref_match`·`skip` 관련 테스트(D-12 ① 미방출을 assert 하는 것이 있으면 새 규칙으로 갱신 — 삭제가 아니라 기대값 변경, 사유 주석)
- 계약: `app/src/types/analysis.ts` FaultZoomComparison(refMarked 선례 439-530), `backend/shared/python/sunity_shared/models.py` 630-640, `docs/contract.md` 560-600 (§11.9 refMarked)
- `app/src/components/DeductionDetailSheet.tsx` REF_UNMARKED_NOTE(120 부근)·refUnmarked 렌더부, `app/src/app/analysis/result.tsx` 3650-3665 시트 배선(`refUnmarked={sheetPrimaryZoom?.refMarked === false}`)

규율: 한국어 docstring/주석에 belle 원문 요지 + quick-260903-upx. 동작명·영상 ID 분기 0(일반화). pytest = `backend/.venv/bin/python -m pytest backend/tests -q`(기준선 4589/0). 앱 = `cd app && npx tsc --noEmit`·`node --test "src/lib/__tests__/*.test.*"`(219/0). Gemini 호출·키 조회 금지. Pod 검증은 오케스트레이터.
</context>

<tasks>

<task id="1" name="card_gates.decide_card 순수 함수 + 테스트">
files: backend/shared/python/sunity_shared/analysis/card_gates.py, backend/tests/test_card_gates.py
action:
- `@dataclass(frozen=True) class CardDecision: emit: bool; draw_user_marks: bool; hold_state: str; pair_state: str; eye_state: str` + `def decide_card(hold_reason: str | None, pair_reason: str | None, eye_ok: bool | None, eye_why: str) -> CardDecision`:
  · emit 은 항상 True (belle 규칙 — 게이트는 삭제 권한 없음). docstring 에 원문.
  · draw_user_marks = False ⇔ eye_ok is False 이고 eye_why 가 실제 불일치(`->` 포함 판정 문자열, 즉 observed≠claim 또는 arm↔leg 상충) — `frame_missing`/`no_api_key`/`midrange`/`skip:torso_joint`/None 은 True(표시 유지: 눈이 못 본 것은 틀린 게 아니다).
  · hold_state = hold_reason or "unmeasured"("hold"|"moving"|"unmeasurable"|"peak"), pair_state = pair_reason or "unmeasured"("match"|"pose_far"|"pole_mismatch"), eye_state ∈ {"match","mismatch","skip","none"}.
- 테스트 6건: 전 조합에서 emit True / 눈 불일치만 draw False / skip·midrange·frame_missing 은 draw True / peak 경로 / 상태 문자열 매핑.
verify: `backend/.venv/bin/python -m pytest backend/tests/test_card_gates.py -q` pass
done: 결정 규칙이 한 함수에 있고 테스트가 박제
</task>

<task id="2" name="fault_zoom: 상한 해제·대응 실패/좌표 부재 방출·표시 생략 옵션·userMarked">
files: backend/shared/python/sunity_shared/analysis/fault_zoom.py, backend/tests/test_fault_zoom.py
action:
- `criterion_units_from_records(..., max_units=4)` 기본값은 두되(하위호환) 호출측이 넘길 수 있게 유지 — 변경은 app.py 에서(task 3). 여기서는 무접촉.
- `build_fault_zoom_comparisons`: (2) `if unit.criterion is not None and ref_match_failed_unit: continue` → continue 제거, legacy 와 같은 D-04 폴백 경로로 진행(r_valid=[] 전신 폴백, `refMatch='failed'`, `refMatched=False`). (3) `if not u_valid and not r_valid: continue` → continue 제거, 양측 전신 폴백(`_side_crop` 3단 강하의 전신 단계)로 진행 — 표시 0.
- 신규 kwarg `suppress_marks: set[str] | frozenset[str] = frozenset()` ("user"/"ref"): 해당 측 crop 에 원·선·호·화살표를 그리지 않는다(전신 폴백이 아니라 크롭은 그대로, 표시만 생략 — angle_bake `omitted:*` 침묵 선례 재사용). docstring: quick-260903-upx "게이트는 표시만 정한다".
- 방출 dict 에 `userMarked: bool`(학생 패널에 표시가 하나라도 그려졌는가 — refMarked 3808 선례 미러). 기존 필드 무변경.
- 테스트: (a) criterion 카드 + ref 대응 실패 → 방출 1 + refMatch='failed' + refMatched False (종전 미방출 assert 는 새 규칙으로 갱신, 사유 주석) (b) 양측 좌표 없음 → 방출 1 + userMarked False + refMarked False (c) suppress_marks={'user'} → userMarked False, ref 는 그대로 (d) 정상 경로 userMarked True.
verify: `backend/.venv/bin/python -m pytest backend/tests/test_fault_zoom.py -q` pass
done: 1단계가 record 당 카드를 반드시 낸다
</task>

<task id="3" name="pipeline: 게이트 무삭제 + 표시 조정 + 1단계 보존 병합 + 불변식 로그">
files: backend/functions/pipeline/app.py
action:
- 1단계 호출부와 게이트 호출부의 `criterion_units_from_records(...)` 에 `max_units=max(4, len(records))` 전달(grep `criterion_units_from_records(` 전부).
- 게이트 루프: hold/pair/eye 결과를 `cg.decide_card(...)` 로 넘겨 **항상 emitted** 에 넣는다(`dropped` 는 `freeze_sec_invalid` 만 남고, 그 record 는 1단계 카드 보존 대상). emitted 튜플에 decision 을 실어 렌더 루프로 전달. `survivor_eye`/verdict 로그는 `eye=` 사유 + `hold=`/`pair=`/`marks=user|none` 를 함께 남긴다(정보 손실 0).
- 렌더 루프: `display_anchor` 가 한 측이라도 None 이면 `continue` 대신 그 측을 `suppress_marks` 에 넣고 진행(anchor 없는 측 표시 생략 — 로그 문구 "카드 미방출" → "표시 생략"). decision.draw_user_marks False 면 `"user"` 를 suppress_marks 에 추가. `build_fault_zoom_comparisons(..., suppress_marks=...)` 전달. 방출 dict 에 `holdState`/`pairState`/`eyeState` 추가(scalar).
- 최종 부착: `gated_by_crit = {c['criterion']: c}`; `stage1_keep = [it for it in existing_comparisons if it.tier != 'advisory' and it.criterion not in gated_by_crit]` (criterion 없는 legacy 카드는 joint 키로 동일 규칙); `final = items(게이트) + stage1_keep + advisory_keep`. 순서 = record 순서.
- 불변식 로그: `expected_units = len(_fz.criterion_units_from_records(records, fault_joints, _KISMAM_TO_KEYPOINT, max_units=max(4, len(records))))`; `log.info("card_gates 대체 부착 완료 analysis_id=%s expected_units=%d emitted=%d confirmed=%d advisory=%d", ...)`; emitted < expected 면 `log.warning("card_gates 사진 부족 …")`. 원장 업로드 조건·필드 무접촉.
verify: `backend/.venv/bin/python -m pytest backend/tests -q` → 4589 + 신규 전부 pass, fail 0 (수치 보고)
done: 게이트가 카드를 삭제하지 않고, 1단계 카드가 보존되며, 불변식이 로그에 남는다
</task>

<task id="4" name="계약 3중 미러 + 시트 '왼쪽 표시 없음' 한 줄">
files: backend/shared/python/sunity_shared/models.py, docs/contract.md, app/src/types/analysis.ts, app/src/components/DeductionDetailSheet.tsx, app/src/app/analysis/result.tsx
action:
- 계약(optional, additive, legacy 부재 = 종전): `userMarked?: boolean`, `holdState?: 'hold'|'moving'|'unmeasurable'|'peak'|'unmeasured'`, `pairState?: 'match'|'pose_far'|'pole_mismatch'|'unmeasured'`, `eyeState?: 'match'|'mismatch'|'skip'|'none'`. TS 주석(refMarked 선례 문형) + models.py 주석 + contract.md §11.9 옆 §11.11 절.
- 앱: `DeductionDetailSheet` 에 `userUnmarked?: boolean` prop — true 면 REF_UNMARKED_NOTE 와 같은 자리에 `USER_UNMARKED_NOTE = '왼쪽 사진에는 관절 위치를 확인하지 못해 표시를 넣지 않았어요'`(승인 문장 REF_UNMARKED_NOTE 에서 "오른쪽"→"왼쪽"만 바꾼 것 — 신규 문형 0). result.tsx 시트 배선에 `userUnmarked={sheetPrimaryZoom?.userMarked === false}`. 그 외 앱 무접촉(카드 인라인은 PNG 그대로).
verify: `cd app && npx tsc --noEmit` 0; `node --test "src/lib/__tests__/*.test.*"` 219/0
done: 3중 미러 + 시트 한 줄
</task>

</tasks>

<verification>
- pytest fail 0, 앱 게이트 green.
- 오케스트레이터(Pod, 켜져 있음): 6동작 E2E(pdshape·클라임·파워스핀·엘보 트위스트·킵업·피터팬) → 각 doc 에서 `expected_units == confirmed 카드 수` 기계 판정 + 서버 로그 `대체 부착 완료 expected_units=N emitted=N`. pdshape 는 5장.
</verification>

<success_criteria>
- 커밋 4개(태스크당 1개). docs 커밋은 오케스트레이터. 동작명 분기 0.
</success_criteria>
