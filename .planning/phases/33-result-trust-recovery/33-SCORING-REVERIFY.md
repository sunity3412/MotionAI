# 33-SCORING-REVERIFY — Wave R 2-트랙 채점 재검증 (33-SPEC R5, D-38)

**Verdict: PASS** — 2-트랙 채점 엔진(33-22)이 실제 6 fixture(채점 도달 5개) 전수에서 구조 불변식 INV-1/2/4/5/6 을 **동시에** 만족. INV-3/7/8 은 33-22 합성 유닛테스트로 이미 증명(치명 트랙 DORMANT, 어떤 fixture 도 미발화, D-35). fixture별 목표 점수로 판정하지 않음([[judgment-must-not-fixate-on-recent-fixture]]). flip(33-07)은 pivot 상 belle 보류 유지 — 이 PASS 는 flip 을 "가능"하게 할 뿐 자동 flip 아님.

## 실행 조건 (재현 근거)

- **Pod:** `b9l5gt1vpc4ho1` (RTX 4090, belle greenlight 2026-07-24), code re-pin `ac59904`(2-트랙 엔진 포함), `RTMW_DETERMINISTIC=1`, `PR_INVERSION_ENABLED=1`.
- **기질:** candidate `phase33-cm3-run1` 을 **shadow** 소비(`SUNITY_SHADOW_REFERENCE_VERSION`) — active 포인터 `phase4_v1` 무변형(flip 없음). Lambda 미동기화(트래픽 격리).
- **실행:** `run_sweep.py --reference-version phase33-cm3-run1 --tag cold`, **serial**(동시 금지, [[pipeline-not-concurrency-safe-eval-serial]]), 6 PAIRS 등빈도(D-23), recognizer=Fallback(phase25 baseline 정합), vision-veto ON.
- 산출물: `phase25_breakdowns.json`(6 motion) + `phase25_sweep_report.json` (Pod `/workspace/eval_out_33_23/`, repo 밖).

## 실측 2-트랙 breakdown 덤프 (열어서 확인 — D-19)

| motion | kind | final | executionRaw | executionCapped | criticalTotal | 재구성(INV-6) |
|---|---|---:|---:|---:|---:|:---:|
| power-spin | correct | 100 | 0.0 | 0.0 | 0 | 100 OK |
| power-spin | fault | **80** | −20.2 | −20.2 | 0 | 80 OK |
| peter-pan | correct | 100 | 0.0 | 0.0 | 0 | 100 OK |
| peter-pan | fault | **86** | −14.1 | −14.1 | 0 | 86 OK |
| elbow-twist-sister | correct | 100 | 0.0 | 0.0 | 0 | 100 OK |
| elbow-twist-sister | fault | **60** | −111.4 | −40.0 | 0 | 60 OK |
| pdshape | correct | 100 | 0.0 | 0.0 | 0 | 100 OK |
| pdshape | fault | **60** | −57.1 | −40.0 | 0 | 60 OK |
| kip-up | correct | 100 | 0.0 | 0.0 | 0 | 100 OK |
| kip-up | fault | **79** | −20.6 | −20.6 | 0 | 79 OK |
| climb | correct | None | — | — | — | not_pole 게이트(미채점) |
| climb | fault | None | — | — | — | `NotPoleMotionError: angle 0 < 25`(미채점) |

재구성 공식: `final = max(25, round(100 − min(40, |executionRaw|) − |criticalTotal|))`. 전 10개 채점 breakdown 이 dict 만으로 정확히 재구성됨.

## 구조 불변식 PASS/FAIL (채점 도달 5개 fixture)

| 불변식 | 판정 | 근거 |
|---|:---:|---|
| **INV-1** elite ≥95 | ✅ PASS | correct 5/5 = 100 |
| **INV-2** 실행 바닥 ≥60 | ✅ PASS | fault 80/86/60/60/79 — 60 미만 0건. 엘보우트위스트 옛 붕괴(Σ−111.4→0) → **바닥 60** 로 복구 = 재설계 핵심 효과 |
| **INV-4** 변별 유지 (캡 위) | ✅ PASS (finding) | 아래 참조 |
| **INV-5** 단조 감점 | ✅ PASS | \|executionRaw\| 증가 시 final 비증가 (20.2→80, 20.6→79, 14.1→86; 캡 이후 평탄) |
| **INV-6** 재구성 가능 | ✅ PASS | 10/10 정확 재구성 |
| INV-3/7/8 | ✅ (33-22 합성) | 치명 강하/엘보우 앵커→60/절대바닥25 = 합성 유닛테스트 증명. 실 elbow-twist(−111.4→60)가 앵커 재현 |

### INV-4 캡 위 변별 명시 확인 (D-38 caution)

- **캡 미도달(자연 점수):** power-spin −20.2→80, peter-pan −14.1→86, kip-up −20.6→79 → 서로 변별 가능, correct(100) 대비 margin 20/14/21.
- **캡 도달(−40 → 바닥 60):** elbow-twist −111.4, pdshape −57.1 → **둘 다 정확히 60 으로 평탄화**. 두 영상은 실측 심각도가 다름(−111 vs −57)이나 −40 집계캡 위에서는 구분되지 않음.
- **판정:** 이는 재설계의 **의도된 트레이드오프**(다관절 결함이 0 으로 뭉치는 것을 막는 대가로, −40 초과 구간의 심각도 미세변별을 포기). SPEC 문서화 사항. gate2(fixture별 바닥 curve-fit) 는 폐기됐고 여기서 **바닥을 억지로 복원하지 않음**([[judgment-must-not-fixate-on-recent-fixture]]). 캡 아래 변별은 온전하므로 INV-4 = PASS + 명시 finding.

## 정직한 맥락 (belle 판단용 — 엔진과 무관한 별건)

fault 점수가 옛 baseline 대비 **크게 상승**함: power-spin 57→80, kip-up 47→79. 이는 **2-트랙 엔진 효과가 아님** — 세 fixture 모두 −40 캡 아래라 pre-33-22 와 동일하게 `100 − Σ실행` 로 계산됨. 상승 원인은 **새 candidate 기질**(`phase33-cm3-run1`, 9fps + PR 인버전 재추출 = 더 정확한 기준 → 학생 편차 감소). 즉 2-트랙 엔진이 결함을 관대하게 만든 게 아니라, 더 나은 기준 자세가 편차를 줄인 것.

- 엔진의 유일한 행동 변화: 심각한 다관절 실행결함을 0 붕괴 대신 바닥 60 으로 고정(elbow-twist/pdshape). 그 외 fixture 는 byte 동일.
- **belle 판단 필요(이 게이트와 별개):** "잘못된 시연이 80점"이 믿을 만한가? 이는 기질/임계 민감도 이슈로, 원하시면 별도로 살펴봄. 여기서는 curve-fit 하지 않음.

## climb 커버리지 예외

climb(fault/correct 모두) `not_pole_motion` 안전 게이트(`angle 0 < 25`)로 채점 이전 반려 — 33-20 커버리지 매트릭스가 예고한 "climb 은 mode1 margin/substrate 결핍"과 일치. 2-트랙 엔진 실패 아님(채점 경로 미도달). climb 기준 substrate 는 별도 트랙.

## 회귀 검증 (독립 재확인 — executor 주장 불신, 직접 대조)

- 전체 백엔드 스위트 **HEAD(ac59904) vs baseline(bdfe4a0)** 동일 커맨드 대조: 양쪽 **61 failed 동일, 33-22 로 신규 실패 0**, +16 신규 통과(test_deduction_two_track 15 + traceability 게이트 fix). 61개 실패 전부 로컬 환경 결측(Gemini SDK / RTMW mock / pipeline env) — 33-22 없이도 동일 실패.
- 채점 관련 테스트 전수 GREEN: deduction/two_track/dimension/ipsf 등 **241 passed / 0 failed**.

## 치명 트랙 DORMANT — 언제·어떻게 켜야 안전한가 (concern #3)

- **현재 상태:** 치명 트랙은 `criterion` 이 `split_fail_threshold_deg` 필드를 보유하고 `measured < fail_thr` 일 때만 발화. 그 필드를 가진 criterion 이 없어 **DORMANT**(deduction_engine.py:501-508, D-35). 어떤 fixture 도 치명 record 미생성(criticalTotal 전부 0 확인).
- **켜는 법:** 특정 criterion yaml 에 `split_fail_threshold_deg` 추가 = 유일 레버.
- **왜 지금 안 켜는가:** split 검출은 과거 kip-up 위양성을 재유발한 이력([[kipup-fp-RESOLVED-phase24A]]). 켜는 순간 그 FP 재발 위험 → **켤 때는 반드시 6 fixture 재검증 게이트를 다시 통과**해야 함(별도 gated plan, 오늘 범위 밖). 구조는 준비됐고 스위치만 꺼둔 상태.

## 결론

R5 일반화 게이트 **PASS** — curve-fit 없이 구조 불변식 동시 성립. 재설계는 "다관절 결함 0점 뭉침"을 제거하면서(elbow-twist 0→60) 고수 만점·단조·재구성·캡아래 변별을 보존. flip(33-07)은 belle 보류 유지.
