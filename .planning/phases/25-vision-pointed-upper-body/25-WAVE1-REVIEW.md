---
phase: 25-vision-pointed-upper-body
reviewed: 2026-07-04T00:00:00Z
rereviewed: 2026-07-04T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - backend/shared/python/sunity_shared/analysis/vision_veto.py
  - backend/functions/pipeline/app.py
  - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
  - backend/shared/python/sunity_shared/analysis/fault_zoom.py
  - backend/tests/test_vision_pointed_mapper.py
  - backend/tests/test_deduction_seed_pointed_merge.py
  - backend/tests/test_gemini_vision_scorer.py
  - backend/tests/test_fault_zoom_relaxed_crop.py
findings:
  critical: 1
  warning: 6
  info: 3
  total: 10
rereview:
  diff: 535b190..HEAD
  blockers_open: 0
  resolved: [CR-01, WR-01, WR-02, WR-03, WR-04, WR-05]
  verdict: RE-REVIEW PASSED
status: issues_found
---

# Phase 25 Wave 1: Code Review Report

**Reviewed:** 2026-07-04
**Depth:** deep (cross-module: vision_veto → gemini_vision_scorer → pipeline app → deduction_engine/ipsf_criteria → eval gate)
**Diff:** `6cd5266..HEAD` (커밋 10개, 25-01/25-02/25-03)
**Status:** issues_found — BLOCKER 1 (→ 재리뷰에서 해소, 하단 재리뷰 절 참조)

## Summary

Wave 1 의 핵심 주장 4가지를 소스에서 직접 추적 검증했다.

**검증 통과 (실증):**
- **260702-o0c 재발 경로 차단 (25-01):** window 측정은 `_build_deduction_measured_deviations` step 3 에서 `jk in pointed and jk in wm_by_joint` 일 때만 방출된다 (`app.py:2202-2206`). pointed=None/빈 → 전 관절 DTW fallback. `test_pointed_none_or_empty_is_byte_identical_to_legacy` 가 dict-동일성 단언, 코드 판독으로도 legacy emit 조건(NaN/≤0/expects_extension gate, JOINT_KEYS 순서)과 동치 확인. mode3 는 `_collect_vision_fault_context` 가 `mode3_held` ctx(supported=[]) 반환 → pointed=() → 무회귀.
- **매퍼 좁힘 (25-01):** `_POINTED_BASE_BY_KEYPOINT_SET` 4종만 등재, line/torso/head_neck/grip 은 `base is None` skip (`vision_veto.py:778-780`). JOINT_KEYS 밖 방출 0, dedup, 순서 안정 — 테스트 15개 전부 확인. 단 keyword-매핑 단계 우회 존재 (WR-03).
- **캐시 정합 (25-02):** `AGGREGATION_VERSION` 이 `build_key` 반환 문자열의 실제 component (`gemini_vision_scorer.py:455`). 구 키(13 필드) vs 신 키(14 필드) — 어떤 component 도 `:` 를 포함하지 않으므로(hex hash/모델명/버전/정책 문자열) join-string aliasing 불가, 충돌 0. 이번 배포는 PROMPT v10.0 bump 가 이중으로 전체 키 공간을 무효화하므로 rich stale-hit 구조적 불가.
- **edge 3종:** pointed∩wm 밖 관절 → DTW fallback (test 확인), wm NaN/0/형상불량 → `wm_by_joint` 미등재 → DTW 강하 (test 확인), fold 후 중복 관절 → set dedup (test 확인).
- **회귀 0 (테스트):** 전체 suite HEAD 2318 passed / 51 failed — baseline 6cd5266 워크트리 실측과 **실패 집합 byte-동일** (전부 pre-existing, Wave 1 무관). 신규 97 테스트 전부 green.

**발견된 결함:** fold(25-02)의 그룹 키를 keypoint_set 단독으로 바꾼 것이 **라우터가 명시적으로 금지해 둔 granularity** 로 대표를 붕괴시켜, kip-up split 감점 경로를 확률적으로 소실시킬 수 있다 (CR-01). 그 외 support 게이트 의미 약화, 23-03 recall 게이트 구조적 FAIL, coverage-gap 모순 등 WARNING 6건.

## Critical Issues

### CR-01: keypoint_set 단독 fold 가 split_angle 라우팅을 대표-선정 복권으로 만든다 — kip-up FP 재발 경로

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1283` (fold 키), `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py:284-303` (라우터)
**Issue:** `criteria_for_fault` 의 docstring 이 정확히 경고한다: *"keypoint_set 단독 매핑은 불가 — split/straddle/knee-reach 가 전부 keypoint_set='leg' 로 정규화됨"*. 그런데 25-02 fold 는 그룹 키를 keypoint_set 단독으로 바꾸고 **그룹당 대표 1개만** 남긴다. 엔진의 criterion 라우팅(`deduction_engine.tally` → `criteria_for_fault`)은 대표 record 의 RAW `body_part` 만 읽는다.

구체 재발 경로 (kip-up fault 페어):
1. Gemini lower-scope 가 "스플릿 각도 부족" + "무릎/다리 굽음" 을 모두 방출 (v10 프롬프트가 개별 항목화를 강제하므로 더 자주 발생).
2. 두 record 는 `_keypoint_set_for` 로 모두 `leg` → **한 그룹으로 fold**. 25-02 이전에는 fault_kind 가 갈라서("굽" = pole_gap_or_bent vs split = extension_or_alignment) 별도 그룹 → 둘 다 라우팅됐다.
3. 대표 선정 = severity rank → dev. 무릎 record 가 이기면 라우팅은 `leg_extension`(미등록 동작이라 ipsf_absolute substrate 부재 → honest 0)이 되고, **split_angle 활성 + vision-측정 편차 주입(`md["split_angle"]`, belle 결정 A)이 통째로 사라진다**.
4. kip-up 은 geometric split substrate 가 gated-off(keypoint saturate) 라 vision 주입이 유일한 split 감점 경로 — 소실 시 fault 88 → ~99 FP 재복귀 ([[kipup-fp-RESOLVED-phase24A]] 의 역행).

같은 메커니즘이 일반화된다: 같은 keypoint_set 의 서로 다른 결함(예: hand-reach vs knee-bend 둘 다 `leg`/`arm` 계열)은 fold 후 하나만 라우팅된다.
**Fix:** fold 는 support 카운트용으로 유지하되, **라우팅은 그룹 멤버 전체에 대해 수행**하라. 두 가지 방법 중 하나:
```python
# 방법 A (권장, 스코프 최소): fold 시 그룹 멤버의 라우팅-원문을 보존
groups[key]["members"] = [...]  # 각 d 의 (body_part, fault_state) 쌍 유지
rec["_memberFaults"] = tuple(...)  # 대표 rec 에 부착
# deduction_engine.tally 의 라우팅 루프에서 _memberFaults 각각을 criteria_for_fault 에 통과
```
```python
# 방법 B: 그룹 키를 (keypoint_set, routed-class) 2단으로 — split 키워드 보유 record 는
# 같은 leg 라도 별도 그룹 (라우터의 "keypoint_set 단독 불가" 불변 존중)
```
최소한 25-04 pod sweep 게이트에 "kip-up fault 페어의 deduction records 에 `split_vs_reference_over_tol_linear` rule 존재" 를 명시 assert 로 추가해, 이 경로 소실이 점수 우연 통과로 은폐되지 않게 하라.

## Warnings

### WR-01: support K=2 게이트가 단일 호출 자기-충족 가능 — v10 프롬프트가 이를 증폭

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1271-1307` (카운트), `:1516-1523` (v10 suffix)
**Issue:** support 는 call-교차 여부와 무관하게 record 발생 건수로 센다(테스트 `test_fold_no_union_inflation_same_call_counting_preserved` 가 이를 "보존" 으로 박제). 25-02 이전에는 4필드 키라 한 호출의 좌+우 언급이 서로 다른 그룹으로 갈라져 각각 K=2 미달-drop 이었는데, fold 후에는 **한 호출이 "왼쪽 어깨"+"오른쪽 어깨" 를 내면 그 즉시 shoulder support=2 통과**다. v10 프롬프트는 "좌/우를 명시해 개별 항목으로" 를 강제하므로 이 패턴의 발생 확률을 직접 올린다. H1(환각 차단)의 "N 중 K 교차 확증" 의미가 양측-서술 결함에 한해 공동(空洞)화 — 환각 1회가 pointed 게이트를 열고, window 측정 노이즈가 tol 20° 를 넘으면 success 감점(위양성)으로 이어질 수 있다. 260702-o0c 의 교훈이 "window 표집은 노이즈가 tol 을 넘을 수 있다" 였음을 상기.
**Fix:** support 를 record 건수가 아니라 **distinct call 수**로 세라: 그룹에 `calls: set[int]` (call index) 를 축적하고 `len(calls) >= min_support_k` 로 게이트. 발생-건수 의미를 유지하고 싶으면 `_supportCount` 는 그대로 두고 게이트 판정만 call-교차로 분리. 변경 시 AGGREGATION_VERSION bump (agg3).

### WR-02: 23-03 recall 게이트가 fold 후 구조적으로 FAIL — eval18-kip-up-fault 의 expected (left,arm)+(right,arm) 은 fold 산출로 영구 미충족

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1283`, `backend/research/spikes/assert_stillframe_veto_gate.py:356-376`, `backend/research/spikes/eval_stillframe_veto_manifest.json`
**Issue:** `check_recall` 은 `recall_set ⊇ expected_recall_keys` 를 canonical 4-tuple 정확 매칭으로 검사한다. manifest 의 eval18-kip-up-fault 는 `(upper_body, left, arm, pole_gap_or_bent)` 과 `(upper_body, right, arm, pole_gap_or_bent)` **둘 다**를 요구한다. fold 후 `to_trace_dict().faultKeys` 는 keypoint_set 당 대표 1개 — arm 그룹에서 left+right 혼재 시 side=unknown 단일 키만 방출되므로 이 두 expected 키는 **어떤 Gemini 출력으로도 동시 충족 불가**. 이 게이트가 pod 검증 중 실행되면 무조건 GateFail(거짓 경보), 실행 안 하면 manifest 가 조용히 stale.
**Fix:** 둘 중 하나를 Wave 1 범위에서 결정하라: (a) manifest expected 키를 fold 어휘로 갱신 (`side=unknown` 단일 arm 키), (b) `to_trace_dict` 가 fold 대표가 아닌 **그룹 멤버별 원본 FaultKey** 를 faultKeys 에 방출 (recall trace 는 표시/감점과 분리된 관측 채널이므로 fold 전 어휘 유지가 정합). (b) 가 CR-01 방법 A 와 데이터를 공유한다.

### WR-03: "허리/코어" → hip, "손" → arm keyword 매핑이 pointed 감점 게이트를 우회 — broad 금지 의도의 부분 누수

**File:** `backend/shared/python/sunity_shared/analysis/vision_veto.py:136-140` (keyword 표), `:737-742` (매퍼)
**Issue:** 매퍼는 keypoint_set 레벨에서 line/torso/grip 을 차단하지만, 그 앞단 `_KEYPOINT_SET_BY_KEYWORD` 가 torso-성 언급("허리", "코어")을 `hip` 으로, grip-성 언급("손")을 `arm` 으로 정규화한다. 결과: Gemini 가 "허리가 굽음"/"손이 폴에서 떨어짐" 을 짚으면 양쪽 hip/elbow 가 window-측정 eligible 이 된다. 25-02 이전에는 shoulder/hip 계열은 CoverageGap(감점 0) 종착이라 무해했지만, 이제 hip/elbow window 편차가 tol 20° 를 넘으면 **의미상 torso/grip 결함이 hip/elbow 각도 감점으로 둔갑**한다. tol 게이트가 1차 방어이나, 260702-o0c 가 보여줬듯 window 노이즈는 tol 을 넘을 수 있다.
**Fix:** 매퍼에서 `_faultKey` 뿐 아니라 대표 record 의 RAW body_part 재검(grip/torso 키워드 포함 시 skip)을 추가하거나 — T-25-01(재파싱 금지)과 충돌하면 — `_keypoint_set_for` 의 "허리"→hip, "손"→arm 매핑을 pointed 문맥 전용 보수 테이블로 분리하라. 25-04 sweep 의 success 7영상에서 `seed_audit_out.window_joints` 에 hip/elbow 가 뜨는 케이스를 육안 대조.

### WR-04: shoulder/hip 감점과 CoverageGap "substrate deferred" 가 같은 결함에 동시 방출 — 투명성 모순

**File:** `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py:183-189, 332-344`, `backend/functions/pipeline/app.py:2202-2206`
**Issue:** 25-01 의 대표 케이스(Gemini 가 어깨 Δ40° 짚음)에서: (1) window seed 가 `angle_vs_reference__left_shoulder` 를 방출 → 엔진이 감점 record 생성, (2) 동시에 `criteria_for_fault` 는 같은 supported diff 를 여전히 `CoverageGap("shoulder", "shoulder_alignment_substrate_deferred")` 로 라우팅 → coverage_gaps 에 "어깨는 측정 substrate 없음" 이 실린다. 최종 audit 은 **어깨를 측정해 감점했다면서 어깨를 측정 못 했다고 동시에 보고**한다. 점수는 정확하나(gap 은 0 기여) 투명 감점-합산 보고 원칙([[scoring-must-be-transparent-deduction-tally]])의 사용자-노출 서사가 자기모순이고, 25-04 eval 의 구조 게이트가 coverage_gaps 를 단언하면 오판 소지.
**Fix:** `criteria_for_fault` 의 shoulder/hip gap 분기에서 `measured_deviations` 에 해당 관절의 `angle_vs_reference__*` 키가 존재하면 gap 대신 해당 criterion id 를 반환(또는 gap 억제). 라우터는 이미 `measured_deviations` 를 인자로 받고 있어 시그니처 변경 0.

### WR-05: v10 좌/우 명시 강제 + unique-side 해소가 mirror/시점 반전에서 반대측 고정 위험

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1516-1523` (프롬프트), `:1311-1313` (side 해소)
**Issue:** 프롬프트는 "body_part 에 좌/우를 명시하세요" 만 지시하고 **카메라 기준인지 해부학 기준인지 정의하지 않는다**. Gemini 가 viewer-left 로 답하고 학생 영상이 기준과 mirror 관계(Phase 13-A 가 DTW 에서 다루는 알려진 축)면, fold 의 unique-side 해소가 반대측을 확정한다 → pointed 가 실제 결함 관절의 **반대쪽만** window-eligible → 결함측은 DTW 희석으로 tol 미만 → 결함 miss(under-detection). 25-02 이전에는 side 가 대부분 unknown → 양측 eligible 이라 이 실패 모드가 없었다. v10 이 명시를 강제하면서 새로 생긴 좁힘이다.
**Fix:** 프롬프트에 기준을 박아라: "좌/우는 **학생 본인의 신체 기준(해부학적 좌/우)** 으로 명시" + 확신 없으면 좌/우 생략 허용. 또는 보수적으로: fold 그룹에 명시 side 가 유일해도 대표 side 를 unknown 으로 두는 옵션(양측 eligible — 판정은 어차피 측정+tol). 후자는 25-01 OD-1 정신과 정합.

### WR-06: fold 가 비-대표 결함 서술을 완전 폐기 — 표시/코치/줌 충실도 손실

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:1306-1316`
**Issue:** 그룹의 `best` 외 record 는 `_sourceIds` 의 id 숫자만 남고 본문(body_part/fault_state/correct_state/root cause 재료)이 소실된다. 예: "왼팔꿈치 굽음"(moderate) + "오른손이 폴에서 떨어짐"(moderate, dev 낮음) → 사용자에게는 왼팔꿈치 서술만 노출되고, fault-zoom 카드/코치 원인 서사에서 오른손 결함이 사라진다. CR-01(라우팅)과 뿌리가 같은 정보 소실의 표시-측면이다.
**Fix:** CR-01 방법 A 의 `_memberFaults` 를 verdict.differences 직렬화에도 활용해 대표 + 부-서술을 함께 방출하거나, 최소한 25-04 sweep 에서 fault 페어별 differences[] 손실 여부를 눈으로 대조할 체크 항목을 추가.

## Info

### IN-01: wm delta 가 정확히 0.0 인 pointed 관절은 "window 가 clean 판정" 인데 DTW fallback 으로 강하

**File:** `backend/functions/pipeline/app.py:2180` (`_v > 0.0` 게이트)
**Issue:** pointed ∩ wm 관절의 window median 편차가 0.0 이면 `wm_by_joint` 미등재 → DTW full-path 값이 대신 방출된다. window 가 "결함 순간에 편차 없음" 을 측정했는데 더 노이지한 DTW 값으로 감점될 수 있는 의미상 역전. float 실측에서 정확히 0.0 은 사실상 발생하지 않아 실해는 없다.
**Fix:** 의미를 살리려면 pointed ∩ wm(finite) 관절은 값이 0 이어도 fallback 금지(미방출로 종결). 다음 리팩터에 편승.

### IN-02: AGGREGATION_VERSION bump 는 관례-강제일 뿐 구조 강제가 아님

**File:** `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py:75-82`
**Issue:** 주석 + "키에 포함" 테스트는 있으나, fold 로직 변경 시 marker bump 를 잊어도 잡아주는 장치가 없다 (90d038f 의 stale-hit 이력이 정확히 이 실수였다). 현 배포는 PROMPT bump 가 이중 방어라 무해.
**Fix:** fold 동작 스냅샷 테스트에 marker 값을 함께 박아라: `assert AGGREGATION_VERSION == "agg2"` 를 fold 의미 테스트(`test_shoulder_side_and_kind_fragments_fold_to_support_two` 등) 안에 두면, fold 를 고치는 사람이 같은 테스트 파일에서 marker 를 만나게 된다.

### IN-03: relaxed crop kind 가 방출 dict 에 미기록 — 관측성 소폭 손실

**File:** `backend/shared/python/sunity_shared/analysis/fault_zoom.py:519-546`
**Issue:** `_side_crop` 이 crop_kind("valid"/"relaxed"/"full") 를 반환하지만 `out` 항목에는 실리지 않는다. belle 실기기 검증("카드마다 동일 전신 반복 해소" 확인)이나 pod eval 에서 어느 카드가 relaxed 였는지 png 육안 외 확인 수단이 없다. 채점 무접촉이라 위험 0.
**Fix:** 항목 dict 에 `"cropKind": {"user": u_kind, "reference": _r_kind}` scalar 추가 (Firestore flat 규칙 내, 계약 소비자 없음 확인 후).

## 검증 노트 (요청 관점별)

1. **위양성 재발**: 직접 경로(전 관절 window)는 차단 확인. 잔여 리스크는 CR-01(감점 소실 방향의 FP), WR-01/WR-03(감점 과잉 방향의 FP) — 셋 다 25-04 sweep 의 success≥95 / kip-up fault 변별 assert 로 실측 커버 필요.
2. **캐시**: agg2 가 build_key component 로 실재, join-aliasing 불가(component 에 `:` 없음, 필드 수 상이), rich round-trip 시 `_faultKey` 는 dict→FaultKey 복원되고 매퍼가 양형 모두 수용. PASS.
3. **fold 정확성**: side/fault_kind fragment 접합 자체는 의도대로 동작(테스트 8개). 변질 지점은 라우팅(CR-01)과 support 의미(WR-01), recall 어휘(WR-02).
4. **하위호환**: pointed=None/빈/mode3 byte-동일 — 코드 동치 판독 + 테스트 + baseline 대비 전체 suite 실패 집합 동일(51건 전부 pre-existing)로 3중 확인. HIGH-5 이중감점 방어(expects_extension seed-gate + 엔진 claimed_joints discard)는 window 경로에도 동일 적용됨을 확인. Firestore/계약 스키마 변경 0 확인.
5. **일반**: 컴파일 clean, 삭제 helper(`_valid_kp_xy`/`_crop_zoom`) 잔존 참조 0, fault_zoom 앵커 픽셀 산식/경계 clamp 정상, seed_audit_out production 미전달 확인.

---

# 재리뷰 (fix 커밋 6개, `535b190..HEAD`)

**Re-reviewed:** 2026-07-04 · 커밋 0f89cb8 / 161c2cd / 05b44a3 / 81f8e51 / be6635b / ab1c534
**Verdict:** **RE-REVIEW PASSED** — BLOCKER 0. 6건 전부 해소 확인, 신규 결함 없음. 잔여는 스윕-관찰 항목 3건(하단, 비차단).

## 판정 근거

### CR-01 → RESOLVED (0f89cb8)

- **경로 보존 확인:** `_filter_supported_differences` 가 그룹 멤버 원문을 `_memberFaults`((body_part, fault_state) dedup, rank→dev 최선 유지) + `_memberFaultKeys`(fold 전 원본)로 대표에 부착. `deduction_engine.tally` 와 `_collect_coverage_gaps` 가 `_routing_members(diff)` 로 **멤버 각각을 라우팅** — 대표가 무릎(major)이어도 split 멤버가 `criteria_for_fault` 의 split 분기에 도달하고, `_vision_measured_deviation(member)` 가 **멤버 자신의 dev** 를 주입한다 (`_fault_key_for(member)` 도 멤버 body_part 에서 재산출 — fold 대표 키 오염 0). `test_folded_leg_group_preserves_split_routing_via_members` 가 정확히 CR-01 시나리오(스플릿 moderate + 무릎 major 동일 그룹, 대표=무릎)에서 `split_angle` record + `source="vision"` 을 단언. AGGREGATION_VERSION agg3 bump 확인(agg2/v10.0 키 공간과 component 값 상이 → 충돌 0).
- **전체 라우팅의 신규 문제 부재 (요청 확인 1):**
  - *중복 활성/감점 배가 없음:* `pointed`/`activated` 는 set — 같은 criterion 을 여러 멤버가 반환해도 union 1회. per-criterion 감점 루프는 `_ordered(activated, …)` 로 **criterion 당 정확히 1 record** 이고 감점값은 md 의 단일 값에서만 산출 → 멤버 수 비례 감점 배가 경로 구조적 부재.
  - *split 주입 단일성:* `"split_angle" not in md` 가드 유지 — 첫 매칭 멤버 1회만 주입, 기존 geometric-우선/덮어쓰기-금지 규칙 보존.
  - *HIGH-5 방어 범위:* cross-exclusion 은 전부 activated-set 이후 단계(leg/arm↔line discard, claimed_joints → `angle_vs_reference__*` discard) — 멤버 fan-out 은 같은 set 에 원소를 더할 뿐이라 방어가 동일 적용. split_angle + hip window 동시 활성 케이스도 claimed_joints(left/right_hip) discard 로 이중감점 0 확인.
  - *gap 중복:* 멤버 fan-out 의 내용-동일 gap 은 `gap not in coverage_gaps` dedup — 점수 무접촉(gap 0 기여).
  - *하위호환:* `_memberFaults` 부재(구 캐시/직접 구성 diff) → `[diff]` 폴백 (`test_routing_members_fallback_without_member_meta`). rich 캐시 왕복은 `_memberFaults`/`_memberFaultKeyDicts` flat-map 리스트로 보존(`test_rich_doc_round_trip_preserves_member_meta`), Firestore nested-array 규칙 내. `_run_part_frame_fanout` 의 verdict.differences 직렬화가 underscore 키를 strip 하므로 멤버 메타의 표시-누출 0.

### WR-01 → RESOLVED (161c2cd)

distinct-call 게이트: 그룹이 `calls: set[call_idx]` 를 축적하고 `len(calls) >= K` 로 판정. **K=2 의미 보존 확인 (요청 확인 3):** 정당한 2-call 교차 확증(좌+우 항목화 call + "어깨" 단독 call)은 통과하며 출력은 여전히 대표 1개(부풀림 0), 단일 호출의 좌+우 항목화는 drop — `test_single_call_left_right_itemization_does_not_self_satisfy_k` 가 양방향 모두 단언. `_supportCount`=distinct-call 확증 수 / `_sourceIds`=발생 건수 provenance 로 역할 분리. planned scope 3개(upper/lower/line)에서 K=2 는 여전히 도달 가능. agg3 bump 에 포함.

### WR-02 → RESOLVED (81f8e51)

`to_trace_dict` 가 `_memberFaultKeys`(fold 전 원본) + 대표 키의 superset 을 dedup 방출 — 좌+우 혼재 arm 그룹에서 (left,arm)+(right,arm)+(unknown,arm) 동시 방출을 `test_trace_dict_emits_prefold_member_fault_keys` 가 단언. manifest 무접촉으로 side/fault_kind 어휘의 구조적 미충족이 해소. (part_scope 차원은 pre-existing hint-uniform — 잔여 R-3.)

### WR-03 → RESOLVED (05b44a3)

keyword 표 보수화: "허리"/"코어" 는 어느 행에도 없음 → default `torso`(gap 종착, 감점 0), "손"/"손목" → `grip`. grip 행을 head_neck 앞으로 이동해 "손목" 의 "목" substring 오분류(pre-existing)도 함께 수정 — 순서 의존 처리 올바름. 진짜 hip("골반")/arm("팔꿈치") 매핑 유지 + pointed 매퍼 torso/grip 방출 0 을 테스트로 재확인. 라우터(`criteria_for_fault`)는 RAW body_part 자체 키워드를 쓰므로 영향 범위가 fold/pointed 어휘로 정확히 국한됨을 확인.

### WR-04 → RESOLVED (be6635b) — 채점 결과 영향 0 검증 (요청 확인 2)

gap 억제는 `criteria_for_fault` 의 shoulder/hip gap 분기 한정: md 에 `angle_vs_reference__{side}_{ks}` 가 `_finite_positive`(finite>0, NaN/Inf/비수치 거부)로 실재할 때만 gap 대신 그 criterion id 반환. **records/final 무영향을 3케이스로 확인:**
- dev > tol(20°): seed(`criteria_from_measured_deviations`)가 이미 같은 cid 활성화 — 라우터 반환은 set union no-op → record 동일.
- 0 < dev ≤ tol: 신규 활성이지만 엔진의 `over = max(0, d−tol) = 0` → `if over <= 0.0: continue` (**dead-zone, record 미방출**) → final 동일. 바뀌는 것은 gap 방출뿐.
- dev 부재/NaN: `_finite_positive` False → 기존 gap 그대로(억제 아님).
end-to-end 로 `test_tally_no_shoulder_gap_and_record_contradiction` 이 "감점 record 존재 AND shoulder gap 부재" 를 단언, 미측정 side 미활성(`test_hip_gap_suppressed_only_for_measured_side`).

### WR-05 → RESOLVED (ab1c534)

프롬프트에 "좌/우는 화면(카메라) 기준이 아니라 수행자(학생) 본인 신체 기준" + "확실하지 않으면 좌/우 생략(억지 지정 금지)" 명시 — 생략 시 side=unknown → OD-1 양측 eligible 로 안전 흡수. PROMPT_VERSION v10.1 bump(캐시 무효화) + 전 scope 프롬프트 단언 테스트 확장 확인.

### 전체 회귀 (요청 확인 4)

- 전체 suite: **2328 passed / 51 failed** — 실패 집합이 baseline 6cd5266 실측과 여전히 **byte-동일**(전부 pre-existing). fix 로 +10 테스트, 전부 green. 변경 4개 모듈 컴파일 clean.
- 캐시: PROMPT v10.1 + agg3 이중 bump — v10.0/agg2 로 잠깐 존재했을 수 있는 키 공간까지 무효화.

## 잔여 (비차단 — 25-04 sweep 관찰 항목)

- **R-1 (distinct-call 의 의도된 강화):** 단일 scope call 안에서만 2회 언급된 결함은 이제 drop (25-02 이전 4필드 키에서는 동일-키 same-call 2건도 통과했었다). 정상 결함은 lower+line 등 복수 scope 에 걸쳐 나타나므로 설계상 수용 — 단 kip-up fault 변별이 sweep 에서 유지되는지 확인할 것 (under-detection 방향).
- **R-2 (gap 항목 수 증가 가능):** 멤버 fan-out 으로 같은 그룹의 서로 다른 문구가 각각 gap 을 만들 수 있다(내용-동일만 dedup). 점수 0 기여·표시 노이즈만 — sweep report 육안 확인.
- **R-3 (recall part_scope 차원, pre-existing):** fanout 필터는 `part_scope_hint="line"` 균일이라 trace 키의 part_scope 는 "line" — manifest 의 "upper_body" 기대와의 fit 은 Wave 1 이전부터의 상태([[phase23-pod-eval-gate-fail-2026-06-24]] 의 기존 recall gap 영역). WR-02 fix 가 복원한 것은 side/fault_kind 어휘다. 23-03 게이트를 실행할 계획이면 그때 part_scope 정합을 확인.
- WR-06(표시 충실도)/IN-01~03 은 원 리뷰 판정 유지 — `_memberFaults` 가 이제 존재하므로 WR-06 의 표시-측 활용은 후속에서 저비용.

---

_Reviewed: 2026-07-04 · Re-reviewed: 2026-07-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
