---
status: awaiting_human_verify
trigger: "역립 동작(elbow-twist/pdshape)에서 7~8관절이 균일하게 ~30°씩 감점되는 근본원인 — 포즈추정 저신뢰 vs DTW/좌표 전역오프셋. 33-NEXT-JOINT-ATTRIBUTION-SEED.md 참조"
created: 2026-07-24
updated: 2026-07-24
root_cause_confirmed: true
crux_answer: "H1 (역립 저신뢰 포즈추정) — H2 반증. 균일 ~30° 는 절대median 채점 metric 아티팩트."
checkpoint: "belle DECISION 1=approach A(magnitude-neutral marker) / DECISION 2=GPU deferred(request-when-ready). 로컬 5-fixture 변별 검증 후 STOP+report."
---

# Debug: 역립 관절 귀속 정밀도 (균일 다관절 편차 근본원인)

> 출처 SEED: `.planning/phases/33-result-trust-recovery/33-NEXT-JOINT-ATTRIBUTION-SEED.md`
> 근거 문서: `33-SCORING-REVERIFY.md` "영상 전수 검증", 33-23 sweep (shadow candidate `phase33-cm3-run1`, 2트랙 엔진)

## Symptoms

**Expected behavior:**
채점이 "어느 관절이/왜 문제인지"를 신뢰성 있게 귀속해야 함. 역립 자세에서 특정 결함 관절만 짚어야 함 (belle A-0: "분석이 엉뚱한 데를 짚으면 안 됨").

**Actual behavior:**
- elbow-twist-sister(점수 60): 8관절 전부 26~36° **균일** 감점 (Σ−111.4 → −40 캡 → 바닥 60)
- pdshape(점수 60): 7관절 25~30° **균일** 감점 (Σ−57.1 → 캡 → 60)
- 균일 다관절 편차 = 개별 진짜 결함이 아니라 "거꾸로 자세에서 포즈추정/DTW정렬이 통째 틀어진" 아티팩트 냄새.
- **점수 크기(magnitude)는 정당** — Wave R로 검증됨. 문제는 오직 **귀속(attribution)**.

**Error messages / signals:**
- vision severity=none (5/5): Gemini가 특정 결함을 하나도 못 짚음 → 점수가 순수 기하 per-joint 편차에만 의존. 의미 레이어 비어있음.
- seedObservation.pointed=[] (전부): vision 침묵 → `angle_vs_reference__{joint}` fallback 경로가 전 관절 편차를 감점. window_joints도 비어있음.
- power-spin worst-window 70° = 정렬 아티팩트 (클립 위상 어긋남). 점수엔 DTW-median이 옳게 쓰였지만, 측정 시스템 간 불일치가 큼을 보여줌.

**Timeline:**
33-23 재검증(Wave R) 후 belle 요청 영상 전수 검증에서 도출. 채점 재설계(33-22 2트랙 엔진)는 magnitude만 고쳤고 attribution은 A-0 잔존 형태로 남음.

**Reproduction:**
역립(inversion) 성격 fixture — elbow-twist-sister, pdshape — 분석 시 균일 다관절 편차 재현. 33-23 sweep 산출물에 breakdown 존재.

## Hypotheses (조사 대상 — curve-fit 금지, 일반화)

1. **역립 포즈 추정 신뢰도 저하** — RTMW가 거꾸로/폐색 자세에서 관절을 통째 오프셋. → 관절별 confidence 게이트로 저신뢰 관절을 귀속에서 제외?
2. **DTW/좌표프레임 전역 오프셋** — 정은지 대비 학생 몸 전체가 회전/정렬 어긋나 모든 관절이 균일하게 X° 밀림. → 전역 오프셋 제거 후 잔차로 귀속?
3. **vision 의미 레이어 미발화** — Gemini severity=none이라 "무슨 결함"이 없음. → vision이 짚은 관절에만 window 측정 적용하는 원칙([[window-median-silent-seed-fp-reverted]] 교훈)을 역으로 적용: vision 침묵 시 특정 관절 단정 회피?
4. **fixture 성격** — 그로스 폴트가 아니라 "덜 깨끗한" 데모. 귀속 애매함이 결함 자체가 미세·분산돼서일 수도. → belle와 fixture 의도 확인 필요.

## Scope boundaries

- **채점 크기(엔진/임계) 재변경 아님** — Wave R로 검증됨. 이 작업은 "귀속/표현"이지 "점수값"이 아님 (D-20/D-29 정신).
- flip(33-07) 전에도 가능한 seed/측정 정밀도 조사. 표현 트랙(33-08~16)과 연결되나 분리 가능.
- curve-fit 금지: 특정 fixture를 맞추려 관절 규칙 조작 금지 ([[judgment-must-not-fixate-on-recent-fixture]]).
- **crux = 가설 1/2** (역립 균일-다관절-편차가 포즈추정 저신뢰인지 전역정렬 오프셋인지). 원인 규명 후 귀속 설계(가설 3)로.

## Evidence

- timestamp: 2026-07-24 (E1)
  checked: 로컬 phase25 baseline breakdowns (`backend/evals/phase25/baseline/phase25_breakdowns.json`) — 33-23 shadow(final 60)과 구조·크기 동일한 baseline(final 61/54). 역립 2개 fault records per-joint 덤프.
  found: |
    per-joint measuredValue (= 정은지 대비 절대 각도편차, tol=20° 위만 record):
    elbow-twist-sister fault (7 joints): 22.3~26.9°, mean 24.6°, spread 4.7°.
    pdshape fault (8 joints): 20.4~28.4°, mean 24.8°, spread 8.0°.
    편차 크기가 팔꿈치·어깨·엉덩·무릎(해부학적으로 무관한 관절) 전반에 걸쳐 거의 동일(~24°).
    deviation = measuredValue − 20 (tol=20° 확인: 24.12−4.12=20.0 등). points 는 deviation 기반 선형.
  implication: 개별 진짜 결함이면 관절별 편차 크기가 크게 분산돼야 함(예: 5°~50°). 대신 무관한 관절들이 균일 ~24° = 전역 오프셋(H2) 신호. H1(저신뢰 jitter)이면 크기·부호가 독립·noisy 해야 함 → 불일치.

- timestamp: 2026-07-24 (E2)
  checked: 전 fault fixture per-joint measured 스프레드/카운트 대조.
  found: |
    inversion:     elbow-twist n=7 joints over-tol,  pdshape n=8.
    non-inversion: power-spin n=3, peter-pan n=3, kip-up n=2.
    비역립은 2~3관절만 tol 초과(진짜 결함 관절), 역립은 거의 전 관절(7~8) tol 초과.
  implication: 역립에서만 "전 관절 동시 tol 초과" = 전역 효과가 모든 관절을 20° 임계 위로 밀어올림(H2). 결정적 crux 신호. 남은 질문: angle_vs_reference 가 굴곡각(flexion, 전역회전 불변) 인지 방향각(orientation, 전역회전 민감) 인지 — 굴곡각이면 단순 전역회전으론 설명 안 됨 → 메커니즘 코드 확인 필요.

- timestamp: 2026-07-24 (E3)
  checked: features.py `compute_joint_angles` — 각도 정의.
  found: 모든 관절각 = 3점 subtended angle(_angle_deg, vertex b 에서 arccos). 굴곡각이며 전역 회전·평행이동 불변.
  implication: H2 의 "좌표프레임 전역 회전" 은 굴곡각을 이동시킬 수 없음 → H2 의 "coordinate rotation" 형태는 원리상 배제. 남은 후보 = 측정/정렬 품질 저하.

- timestamp: 2026-07-24 (E4 — 결정적)
  checked: phase25 sweep_report visionVeto.windowMedianAngleDeltas (부호 있는 per-joint delta) + alignment(visibility/distance) 전 fixture 대조.
  found: |
    per_joint_deviation(채점 경로, |Δ| median): 역립 전 관절 균일 ~24° (부호 제거).
    그러나 부호 있는 window delta 는 균일 아님 — 부호·크기 전부 분산:
      elbow-twist: −20.3/−8.3/−36.9/+54.7/+13.8/−5.7/+7.3/+34.9 (범위 −37~+55, 부호 혼재)
      pdshape:     +14.6/−20.4/−44.4/−77.6/+66.8/+57.2/−28.0/+6.1 (범위 −78~+67, 부호 혼재)
    visibility(신뢰도 proxy): 역립 0.686/0.448 << 비역립 0.708/0.815/0.806.
    DTW distance: 역립 62.9/64.3 = 최고(비역립 26.9~60.1). localPathCount 역립 7~8(적음).
  implication: |
    crux 판정 → **H1(역립 저신뢰 포즈추정) 이 root, H2(coherent 전역오프셋) 는 반증**.
    - H2 서명(동일 부호·동일 크기, 정상 confidence): 부호 혼재(−78~+67) + 낮은 visibility 로 **반증**.
    - H1 서명(역립 프레임 저신뢰, 독립·noisy 부호·크기, confidence↔deviation 상관): window delta 부호·크기 분산 + visibility 문제 fixture 에서만 저하 = **일치**.
    "균일 ~30°" 는 오직 채점 metric(per_joint_deviation = |Δ| median)에서만 나타나는 **아티팩트**: 절대값 + 저품질 DTW 정렬(높은 distance)이 결합해 모든 관절 median|Δ| 를 ~20-24° 로 바닥 상승시킴 → 전 관절 tol(20°) 초과 → fallback record 8개. 실제 per-joint 신호는 분산돼 있음(진짜 결함 귀속 근거 아님).

- timestamp: 2026-07-24 (E5 — approach A 구현 + 로컬 변별 검증)
  checked: attribution_unreliable 마커 배선(pipeline/app.py + assemble.py) 후, phase25 baseline
    sweep_report.json 실측값(over_tol=record수 / visibility·distance=visionVeto.alignment /
    silent=seedObservation.pointed 공집합)을 _assess_attribution_reliability 에 그대로 통과.
  found: |
    마커 발화 결과(실측 재생, 추론 아님):
      power-spin fault    over=3 vis=0.708 dist=60.1 silent=T -> False
      peter-pan  fault    over=3 vis=0.815 dist=51.4 silent=T -> False
      elbow-twist fault   over=7 vis=0.686 dist=62.9 silent=T -> True   ✓ suppress
      pdshape    fault    over=8 vis=0.448 dist=64.3 silent=T -> True   ✓ suppress
      kip-up     fault    over=2 vis=0.806 dist=26.9 silent=F -> False
      전 success(over=0) -> False.
    DISCRIMINATION HOLDS: 정확히 {elbow-twist-sister/fault, pdshape/fault} 에만 발화.
  implication: |
    belle DECISION 1(approach A) 요건 충족 — 역립 2 fixture 만 저신뢰 귀속으로 판정,
    비역립 3 fixture per-joint 귀속 무접촉. 3-조건 AND 게이트(silent∧over≥5∧저정렬)에서
    power-spin(over=3)/peter-pan(over=3)은 count 게이트로, kip-up 은 pointed=4(비-silent)로
    차단 — 각 게이트가 독립적으로 필요(단위테스트 test_each_gate_is_necessary 확인).
    ⚠ 임계(≥5/vis0.70/dist60)는 5-fixture 로컬 유도 — 6-fixture serial GPU sweep 로
    일반화·비역립 무오발 재검증 필요(curve-fit 금지, belle DECISION 2 greenlight 대기).

## Specialist Review

reviewer: Python specialist (33-NEXT approach A 리뷰, 2026-07-24)
invariants_verified_held:
  - magnitude-neutral (md 무mutate, 마커는 side-channel top-level key)
  - no curve-fit fixture-name branching (3 module-level 상수)
  - side-channel 이 per-joint CLAIM 만 억제
  - pure/type-hinted assessment fn
findings_addressed:
  - id: WR-01
    severity: WARNING
    problem: |
      gemini_silent = (len(pointed)==0) 이 "Gemini 가 결함 못 찾음"과 "Gemini 부재/오류"를
      혼동. pointed 는 skipped_error/resource_limited 에서도 공집합 → Gemini FAILURE + broad
      deviation + dtw>60 시 마커가 잘못된 근거(vision 오류)로 발화.
    fix: |
      pointed=∅ 를 affirmative vision 상태(no_fault/candidate_verdict/low_alignment_confidence)
      에서만 silent 로 승격. skipped_error/resource_limited/disabled/mode3_held/missing_* 는
      signal-absent → 발화 금지. _ATTR_AFFIRMATIVE_VISION_STATUSES frozenset + builder 에
      vision_status kwarg 배선(production = ctx.collection_status).
    verification: |
      실측 재생 — 동일 강신호(over=7 vis=0.686 dist=62.9)에서 no_fault/candidate_verdict/
      low_alignment_confidence → FIRE, skipped_error/resource_limited/disabled → geminiSilent=False
      → NO FIRE. phase25 baseline 전 fault fixture 의 실제 collectionStatus 확인: elbow-twist/
      pdshape/power/peter = no_fault, kip-up = candidate_verdict — 전부 affirmative → 5-fixture
      변별 불변(fix 는 미테스트 error-status 경로만 교정).
  - id: WR-02
    severity: WARNING
    problem: |
      assess_alignment_confidence 가 missing keypoint confidence 를 0.0 으로 collapse(never None)
      → 마커의 None-guard 가 프로덕션에서 dead. frame-pair 선택 실패(미측정 → 0.0)를 genuine
      worst visibility 로 오인해 발화에 기여.
    fix: |
      "0.0=측정-최악" vs "미측정"을 명시 bool 로 구분. 정렬 계산 site 에서 visibility_measured
      추적(pair·student_confidence 존재 시만 True) → alignment["visibility_measured"] 방출.
      builder 에 alignment_visibility_measured kwarg 추가, 미측정이면 None 으로 강등 후 마커에
      전달(None-guard 활성). production 은 ctx.alignment.visibility_measured 주입.
    verification: |
      실측 — vis=0.0 measured=True(dist=50, vis 만 저정렬 후보) → visibility=0.0 → FIRE;
      measured=False → visibility=None → NO FIRE. 역립 fixture 는 genuine 측정값(0.686/0.448)
      이라 measured=True → 정상 발화 유지(fix 는 프레임선택 실패 error-case 만 교정).
  - id: WR-03
    severity: WARNING (TRACKED — honor, do NOT fix)
    action: |
      razor-thin margins(power-spin vis=0.708 vs 0.70, dtw=60.13 vs 60.0, over_tol 3<5 로만 차단)
      은 6-fixture serial GPU sweep 가 닫을 overfit 리스크. 임계 무변경(5/0.70/60.0 그대로).
      로컬 pass 를 validated 로 간주하지 않음.
  - id: NOTE
    action: |
      over_tol_count 는 angle_vs_reference__{jk} record 만 카운트 — 등록 프로파일은 ipsf_absolute
      방출로 과소집계. 역립(미등록) 타깃엔 benign 하나 발화가 "미등록 프로파일" 가정에 커플링됨.
      builder 마커 블록에 coupling 문서화 주석 추가.
  - id: IN-02
    severity: INFO (optional)
    action: |
      SKIP — public alias(ANGLE_TOLERANCE_DEG)는 scoring-core(ipsf_criteria.py) 파일 접촉이라
      magnitude-neutral 스코프 규율상 보류. from ...ipsf_criteria import _ANGLE_TOLERANCE_DEG
      (단일 진실) 유지. 향후 정리 후보로만 기록.

- timestamp: 2026-07-24 (E6 — specialist review WR-01/WR-02 반영 + 재검증)
  checked: |
    Python specialist 리뷰 2 WARNING(WR-01 gemini_silent 오류상태 혼동 / WR-02 미측정
    0.0 sentinel) 수정 후, 실측 재생 + 단위테스트 + phase25 baseline collectionStatus 확인.
  found: |
    WR-01 (동일 강신호 over=7 vis=0.686 dist=62.9, vision status 변주):
      no_fault -> FIRE / candidate_verdict -> FIRE / low_alignment_confidence -> FIRE
      skipped_error -> geminiSilent=False NO-FIRE / resource_limited -> NO-FIRE / disabled -> NO-FIRE
    phase25 baseline 실제 collectionStatus: elbow-twist/pdshape/power-spin/peter-pan = no_fault,
      kip-up = candidate_verdict — 전 5 fixture affirmative → WR-01 gate 는 변별 무영향.
    WR-02 (vis=0.0, dist=50 저정렬 아님 → visibility 만 후보):
      measured=True -> marker.visibility=0.0 -> FIRE (genuine worst)
      measured=False -> marker.visibility=None -> NO-FIRE (미측정 sentinel 발화 미기여)
    5-fixture 변별 재확인(pure fn 실측): elbow-twist(True)/pdshape(True) 만 발화,
      power-spin/peter-pan/kip-up(F). 임계 5/0.70/60.0 무변경(WR-03 honor).
    단위테스트: test_attribution_reliability_marker 19 pass(신규 5: error-status×2 NO-FIRE,
      affirmative no_fault FIRE, unmeasured NO-FIRE, measured-terrible FIRE).
    회귀: 명명 스위트 248 pass. test_p1_objective_knee_decontamination 4 failed 는
      pre-existing(stash 전후 동일 — 등록 프로파일 YAML 미활성 환경 이슈, 무관).
  implication: |
    두 WARNING 이 magnitude-neutral·변별 불변을 유지한 채 교정됨. WR-01 은 vision 오류를
    저신뢰-역립으로 오인하던 오발 경로를 닫고, WR-02 는 frame-pair 선택 실패의 0.0 을
    genuine worst 로 오인하던 경로를 닫음. 실측 5-fixture 변별은 두 fix 모두에 대해 불변
    (fix 는 미테스트 error-case 만 교정). WR-03 razor-thin margin 은 GPU sweep 몫으로 유지.

## Resolution

root_cause: |
  역립(self-occluded inverted) 자세에서 RTMW keypoint 신뢰도(visibility)가 급락(0.45~0.69 vs 정상 0.71~0.82)해 관절각이 noisy·독립적으로 틀어지고 DTW 정렬 품질이 저하(distance 최고)됨. 채점 경로의 `per_joint_deviation`(motiondtw)은 정렬 path 전체의 **절대값 median |Δ|** 를 쓰는데, 정렬이 나쁘면 모든 관절의 median|Δ| 가 tol(20°) 위로 균일하게 부양된다. 결과: 7~8관절 전부가 `angle_vs_reference__{joint}` fallback 감점 record 를 생성하고, vision severity=none 이라 이 fallback 이 그대로 사용자 귀속(seedObservation.fallback_joints=8관절)이 된다. "균일 다관절 ~30°" 는 개별 진짜 결함이 아니라 **저신뢰 측정 × 절대median metric 의 아티팩트**. (H1 root, H2 반증 — E3/E4.)
fix: |
  approach A (belle DECISION 1 — magnitude-neutral marker) 구현 완료. 점수 record/final 무접촉.
  --- 배선 ---
  1) pipeline/app.py: 순수 함수 _assess_attribution_reliability(gemini_silent, over_tol_count,
     visibility, dtw_distance) + 명명 상수(_ATTR_MIN_OVER_TOL_JOINTS=5 / _ATTR_MAX_VISIBILITY=0.70
     / _ATTR_MAX_DTW_DISTANCE=60.0 / _ATTR_AGGREGATE_STATEMENT). 3-조건 AND → unreliable + 발화 시
     aggregateStatement("전체 자세가 정은지 선수보다 덜 정돈된 편이에요.") 방출.
  2) _build_deduction_measured_deviations: alignment_visibility kwarg 추가. seed 루프 후 md 를
     읽기만(over_tol = angle_vs_reference__{jk} 중 tol 20° 초과 수, 단일진실 ipsf_criteria.
     _ANGLE_TOLERANCE_DEG 재사용) + dtw_distance = reference_dtw_match.distance. 마커를
     seed_audit_out["attributionReliability"] 에만 기록 — md(점수 substrate)는 절대 mutate 안 함.
  3) 프로덕션 call site: seed_audit={} 전달 + ctx.alignment.visibility 주입. veto apply 후
     unreliable=True 일 때만 result["attributionReliability"] 부착(reliable/부재 시 result byte-동일).
  4) assemble.rebuild_tips_for_vision_fault: unreliable 이면 per-joint 팁 재조립 skip(early return)
     → 8관절 단정이 사용자 tips 로 새지 않음. 앱 표현은 aggregateStatement 로 clean aggregate 렌더.
  --- specialist review WR-01/WR-02 반영(E6) ---
  5) WR-01: _ATTR_AFFIRMATIVE_VISION_STATUSES frozenset(no_fault/candidate_verdict/
     low_alignment_confidence). builder 에 vision_status kwarg → gemini_silent = (pointed=∅) AND
     status affirmative. skipped_error/resource_limited 등 signal-absent 는 발화 금지(vision 오류
     오인 차단). production = ctx.collection_status 주입.
  6) WR-02: 정렬 계산 site 에서 visibility_measured 추적(pair·student_confidence 존재 시만 True)
     → alignment["visibility_measured"]. builder 에 alignment_visibility_measured kwarg →
     미측정이면 None 강등(marker None-guard 활성). 0.0 sentinel(프레임선택 실패)을 genuine
     worst 로 오인하던 경로 차단. production = ctx.alignment.visibility_measured 주입.
  7) NOTE 주석: over_tol_count 가 angle_vs_reference record 만 카운트(등록 프로파일 ipsf_absolute
     과소집계) → 발화가 "미등록 프로파일" 가정에 커플링됨을 builder 마커 블록에 문서화.
  8) WR-03(honor): 임계 5/0.70/60.0 무변경 — razor-thin margin 은 GPU sweep 이 검증. IN-02 SKIP
     (scoring-core 접촉 회피).
  --- 스코프 준수 ---
  magnitude(record/overallScore/deductionBreakdown.final) byte-불변(md 무접촉 — 단위테스트
  test_marker_does_not_mutate_score_substrate 로 md 동등성 단언). reliability.py "단정형 금지"
  설계 의도 정합(seed-stage 상위 게이트).
verification: |
  로컬 검증 통과(GPU 미의존, phase25 baseline recorded 실값 재생 — E6 갱신):
    · 변별: 마커가 정확히 {elbow-twist-sister/fault, pdshape/fault} 에만 발화. power-spin/
      peter-pan(over=3)·kip-up(pointed=4)·전 success 미발화. (WR-01/WR-02 fix 후 불변 재확인.)
    · WR-01 재검증: 동일 강신호에서 no_fault/candidate_verdict/low_alignment_confidence → FIRE,
      skipped_error/resource_limited/disabled → geminiSilent=False → NO-FIRE. phase25 실제
      collectionStatus 전 5 fixture affirmative(no_fault×4, kip-up=candidate_verdict) → 변별 무영향.
    · WR-02 재검증: vis=0.0/dist=50 에서 measured=True → visibility=0.0 → FIRE(genuine worst),
      measured=False → visibility=None → NO-FIRE(미측정 sentinel 발화 미기여).
    · 단위테스트 신규 17개(test_attribution_reliability_marker.py, 파라메트라이즈 19 실행) 전부
      PASS — 실측 5-fixture 변별, 각 게이트 필요성, distance-단독 OR, None-신호 미발화, md
      byte-불변, builder 통합, +WR-01 error-status×2 NO-FIRE·affirmative FIRE, +WR-02 unmeasured
      NO-FIRE·measured-terrible FIRE.
    · 회귀: 명명 스위트 248 pass(test_attribution_reliability_marker/test_deduction_seed_pointed_merge/
      test_pipeline_deduction_seam/test_deduction_engine/test_deduction_two_track/test_vision_veto/
      test_phase25_eval_gates/test_pipeline_vision_gate). test_p1_objective_knee_decontamination
      4 failed 는 pre-existing(git stash 전후 동일 — 등록 프로파일 YAML 미활성 환경 이슈, 무관).
  미완(belle DECISION 2 greenlight 대기): 6-fixture serial GPU sweep(shadow phase33-cm3-run1,
  RTX 4090 EU-RO-1) 로 임계 일반화·비역립 무오발·WR-03 razor-thin margin 재검증. 파이프라인
  비-동시성 → serial 필수.
files_changed:
  - backend/functions/pipeline/app.py (marker 함수+상수, WR-01 affirmative-status frozenset+
    vision_status gate, WR-02 visibility_measured 추적+강등, NOTE coupling 주석, builder+call site 배선)
  - backend/shared/python/sunity_shared/analysis/assemble.py (rebuild_tips unreliable skip 가드)
  - backend/tests/test_attribution_reliability_marker.py (단위테스트 17 — WR-01/WR-02 신규 5 포함)

reasoning_checkpoint:
  hypothesis: "역립 self-occluded 자세에서 RTMW keypoint 신뢰도(visibility) 급락이 관절각을 noisy·독립적으로 틀고 DTW 정렬을 저하시켜, 채점 경로 per_joint_deviation 의 절대median|Δ| 가 전 관절을 tol(20°) 위로 균일 부양 → 8관절 fallback record. 균일 ~30° 는 저신뢰 측정×절대median 아티팩트이지 개별 진짜 결함 아님 (H1 root, H2 반증)."
  confirming_evidence:
    - "부호 있는 window delta 는 균일 아님: elbow-twist −37~+55, pdshape −78~+67, 부호 혼재 (H2 coherent-offset 서명 반증)"
    - "관절각 = 3점 subtended flexion angle (features._angle_deg) = 전역회전 불변 → H2 coordinate rotation 원리상 불가"
    - "visibility 역립만 저하(0.686/0.448 vs 0.71~0.82) + DTW distance 역립 최고(62.9/64.3) = confidence↔문제 상관 (H1 서명)"
    - "채점 metric(per_joint_deviation |Δ| median)에서만 균일 ~24°; 역립은 7~8관절 tol초과 vs 비역립 2~3관절 = 정렬품질 저하가 전 관절을 균일 부양"
  falsification_test: "GPU 재분석으로 역립 프레임 per-keypoint confidence 를 직접 덤프했을 때 정상(≥medium) 이고 부호정렬된 잔차가 동일부호 오프셋으로 collapse 되면 H1 반증·H2 성립. (로컬 aggregate visibility+signed window delta 는 그 반대를 가리킴.)"
  fix_rationale: "record(magnitude)는 보존하고 seedObservation 에 attribution_unreliable 마커만 추가 → 점수 불변(스코프 준수), 저신뢰 시 특정 관절 단정만 억제. root(저신뢰 측정→잘못된 다관절 귀속)를 표현 레이어에서 차단하되 채점 magnitude 는 무접촉."
  blind_spots: "①per-keypoint(관절별) confidence 원본은 종료된 Pod 에만 존재 — 로컬은 aggregate visibility 만. ②게이트 임계(≥5/vis0.70/dist60)가 5 fixture overfit 아닌지 미검증. ③비역립·미등록 동작에서 오발(정당 다관절 결함 억제) 가능성 미검증. ④'전체 자세 덜 정돈' 표현이 belle 제품의도와 맞는지 미확인(=대표방식은 제품 결정). ①~③ 모두 6-fixture serial GPU sweep 필요."

## Current Focus

- hypothesis: (확정) H1 root — 역립 저신뢰 포즈추정 → DTW 정렬 저하 → per_joint_deviation 절대median 이 전 관절을 tol 위로 균일 부양 → 잘못된 다관절 귀속. magnitude(60) 정당(Wave R), 문제는 귀속.
- test: approach A(magnitude-neutral 마커) + specialist review WR-01/WR-02 반영 후 로컬 재검증 — 5-fixture 변별 불변 + error-status NO-FIRE + 미측정 visibility NO-FIRE.
- expecting: (충족) 마커가 정확히 2 역립 fixture 에만 발화, WR-01/WR-02 오발 경로 차단, 임계 무변경, 점수 byte-불변. 단위 19 + 명명 스위트 248 pass.
- next_action: (완료 — checkpoint) belle greenlight 대기 = 6-fixture serial GPU sweep(shadow phase33-cm3-run1, RTX 4090 EU-RO-1) 로 WR-03 razor-thin margin 일반화·비역립 무오발 재검증. 변경 staged/uncommitted 유지(belle 워크플로 지시 대기).
