# Phase 25 Sweep Evidence — 2회 실측 (2026-07-04, pod lsx9kedqsdk1e3, GPU CUDA EP)

## 판정: FAIL (2회) — Wave 1 코드는 main 유지, 프로덕션 미반영 (pod repo 0d11835 고정)

## Run 1 (HEAD 7a598df, cold 1783148579 + warm)

- success: 6/6 == 100 (climb 차단 포함) — **위양성 0, 260702-o0c 재발 없음**
- fault: power-spin 54 / peter-pan 79 / elbow-twist 64 / pdshape 55 / kip-up **100 (FAIL — split 감점 유실)**
- 원인: CR-01 멤버 라우팅에서 vision 측정 payload 미승계 → 87978fe 로 승계 fix

## Run 2 (HEAD 87978fe, cold 1783154115 + warm)

- success: 6/6 == 100 유지
- kip-up fault: cold 99 (crit=left_shoulder silent) / warm 100 (crit=[]) — **split 여전히 유실 + 비결정**
- cold != warm: power-spin 52/54, peter-pan 83/79 (criteria 구성도 상이), elbow-twist 69/66, kip-up 99/100
- [kipup_upper] (c): left_shoulder record 가 pointed 밖 (silent seed 출처) — vision 상체 짚기 미발화

## 확정 근본원인 4건 (다음 세션 작업 목록)

1. **split_angle 주입 유실 잔존**: 승계 fix(87978fe) 후에도 실 파이프라인에서 미회복. 유닛(실형상 왕복)은 GREEN — 실 경로와 테스트 형상 사이에 아직 갭. 25-04 재진단 필요 (collect 는 살아있음: supportCount 3).
2. **cold/warm 비결정**: GPU RTMW 미세 변동이 tol 20 degree 경계 관절을 flip — angle_vs_reference 활성 criterion 이 늘며 처음 노출. 결정론 전략 결정 필요 (eval 고정 시드/EP, 경계 히스테리시스 등 — belle 논의 대상).
3. **upper-body vision 짚기 미발화**: 프롬프트 v10.1 로도 kip-up 에서 어깨 faultKey 미산출 (텍스트 언급 -> faultKey 변환 갭 잔존). 프롬프트/파싱 재설계 필요.
4. **Pod baseline artifact 오염**: pod network volume 의 evals/phase24/baseline/*.json 이 2026-07-02 FAIL sweep 값(kip-up 50, peter-pan 0)으로 덮여 있었음 — git 커밋본(kip-up 88, peter-pan 79, elbow 62, pdshape 58)과 상이. **게이트 일부가 오염 기준으로 판정됨.** fix: run_sweep 출력 경로를 repo 밖으로 분리 + pod repo clean 절차.

## 올바른 baseline(git 커밋본) 기준 재판정 (Run 2)

| fault | cold/warm | baseline | 판정 |
|---|---|---|---|
| power-spin | 52/54 | 60 | PASS (개선) |
| peter-pan | 83/79 | 79 | cold +4 마일드 퇴행 (비결정 영향) |
| elbow-twist | 69/66 | 62 | +4~7 마일드 퇴행 |
| pdshape | 58/? | 58 | PASS (동일) |
| kip-up | 99/100 | 88 | **FAIL (split 유실)** |

## 안전 상태

- 프로덕션 서버: 구 코드(0d11835)로 계속 가동 — 사용자 영향 0. pod repo 를 0d11835 로 고정 (재시작해도 안전).
- main 브랜치: Wave 1 + 리뷰 fix 유지 (revert 안 함 — success 100 유지 등 검증된 부분이 많고 프로덕션 미반영이므로).
- 다음 세션 재진입: pod repo `git checkout main && git pull` 후 위 4건 순서대로.


---

## Run 3 (HEAD 5a48d31 — fix 3건 + rtmw_deterministic=1, cold 1783162451 + warm)

### 게이트 결과: FAIL (잔여 = 측정/짚기 품질 한 갈래)

**해결 확인 (3/4 근본원인):**
- **#2 결정론 PASS**: cold/warm 불일치 0건 (직전 run 4건 → 0). ORT 결정론 모드 실증.
- **#4 eval 격리 PASS**: baseline 이 git 커밋본(kip-up 88/peter-pan 79/elbow 62)으로 정확히 판정. 산출물 EVAL_OUT_DIR 분리 동작.
- **#1 split 라우팅 회복**: power-spin fault(49)·elbow-twist fault(68) 에 split_angle record 재등장. 어휘 위치 fix(3399fd7) 실경로 검증.
- **성공 6/6 == 100 (3회 연속) + 짚기-FP 0/5** — vision 이 clean 영상을 전혀 안 짚음 (아키텍처의 위양성 방어 완전 실증).

**잔여 FAIL (전부 근본원인 #3 = vision 측정/짚기 품질):**
- kip-up fault 100 (< 88 미달): 캐시된 vision split 측정 20° == tol 경계 → 감점 0 (규칙상 정당). production 시절 측정은 30°. **측정값 변동(20 vs 30)이 tol 경계를 넘나듦** = 측정 강건화 필요.
- kipup_upper (c): 어깨 감점이 silent seed 출처 (vision 짚기 아님) — v10.1 로도 상체 faultKey 미산출.
- peter-pan 83(>79)/elbow-twist 68(>62) 마일드 무퇴행 위반: distinct-call support 강화(WR-01)로 일부 vision 결함이 지지 미달 drop 된 영향으로 추정 — #3 라운드에서 짚기 커버리지와 함께 재검.

### 다음 라운드 (#3) 스코프
프롬프트 v11 + 캐시 bump (cold ~36 pro call): (a) 상체 faultKey 산출 구조화 강제 보강, (b) split 측정 강건화 (N-sample 측정 median 또는 명시 측정 rubric), (c) WR-01 지지 기준과 짚기 커버리지 균형 재점검. 아티팩트 = runs/run3-5a48d31/.

---

## #3 라운드 코드 반영 (2026-07-04, v11.0/v8.0/agg4 — pod 미실측, 다음 sweep 대기)

### 구현 (3 커밋)

- **(a) 측정 강건화** — 편차 "한 방 추정" 구조 제거. SCHEMA v8.0 이 differences[] 에 `student_angle_deg`/`reference_angle_deg`(각도쌍) + `measurement_basis`(잰 방법 서술) 추가, PROMPT v11.0 이 학생/기준 각도를 **각각** 추정하게 지시 — 편차는 코드가 산술(`vision_veto.explicit_measured_deviation_deg`, |ref−student|). 엔진(`_vision_measured_deviation`)은 각도쌍 산술 우선/approx 폴백, split 주입은 first-wins → 멤버별 후보 **median(lower-middle)** 집계 (severity rank-median 짝수 규칙 재사용 — 새 튜닝 상수 0). 산술 편차 0 은 approx 로 뒤집지 않음(honest).
- **(b) 상체 방출 강제** — v10.1 실측 갭(어깨 관측이 primary_fault 서사에만 잔존): PROMPT v11.0 rule 5 + scope suffix 에 "관찰-전량 differences[] 개별 항목 방출, 서사-only = 응답 무효" 계약 추가. 정타 방어는 유지·강화("편차 없으면 항목을 만들지 말고 빈 배열이 정답" — 짚기-FP 0/5 게이트 보존).
- **(c) WR-01 지지 균형 (agg4)** — distinct-call K=2 는 불변. 단 **명시 각도쌍 측정(산술 편차>0)을 동반한 언급은 단일 call 도 지지 인정** (측정 동반 = 환각 아닌 관측 신호; scope-집중 fan-out 은 부위당 1 call 이라 정당한 단일-scope 관측이 구조적으로 K 미달이던 커버리지 손실 복원). approx 어림 단독은 예외 비대상. `_measurementBacked` marker 가 rich 캐시 왕복 보존(결정론).

### (c) run3 vs phase24 baseline 대조 — "drop 된 faultKey" 확정

**지지(post-gate) faultKey 수준에서는 drop 0 — R3 ⊇ P24 (전 멤버).** 점수 퇴행으로 보였던 것의 실체는 criteria 레벨:

| fault | P24→R3 | P24 supported | R3 supported | 점수差 실원인 |
|---|---|---|---|---|
| power-spin | 60→49 | (gemini_silent) | leg/ext(2) | R3 개선 — split −12 신규 (vision 30°) |
| peter-pan | 79→83 | leg/bent(2) | **+head_neck/ext(3)**, leg/bent(2) | vision drop 아님 — geometry drift (l_shoulder 33.9→31.75, r_elbow 23.25→22.59) + r_hip 20.47→tol 이내(미발화 −0.6) |
| elbow-twist | 62→68 | leg/ext(3) | leg/ext(2) | vision drop 아님 — split −6.0 신규 활성(vision 25°)이 HIGH-5 로 knee ref-rel(−5.1/−2.1) claim + geometry drift |
| pdshape | 58→54 | — | — | 동일 (geometry drift만) |
| kip-up | 88→100 | leg/bent(4) | leg/bent(3) | **측정값 변동 (30°→20°=tol 경계)** = (a) 스코프 |

**WR-01 이 실제로 무는 지점은 pre-gate**: kip-up R3 `_sourceIds` [1,2,3,**5**,6] — diff #4 가 단일-call 지지 미달로 drop (아티팩트에 잔재). 상체(어깨) 관측은 애초에 differences[] 미방출((b) 스코프)이라 게이트에 도달도 못 함 — (b)+(c) 가 한 쌍으로 필요했던 근거.

### 게이트 상태

- 로컬: 관련 스위트 GREEN (deduction/vision_veto/scorer/pipeline seam/phase24·25 gates 369 passed). baseline artifact diff 0 (evals/ 무접촉).
- 다음 pod sweep: cold = 캐시 전량 miss(의도됨, ~36 pro call). 판정 게이트 = success 6/6==100 + 짚기-FP 0/5 유지, kip-up fault < 88 방향(상체 record 포함), peter-pan/elbow-twist 무퇴행.

---

## #4 라운드 코드 반영 (2026-07-04, v11.1/v8.1 — fault_category 고정 enum, pod 미실측)

### 배경 — v11 실측이 확정한 어휘 드리프트 3연속

split 라우팅이 프롬프트 버전마다 다른 이유로 깨짐: v9 body_part "양다리 (스플릿 각도)" → v10.1 스플릿이 fault_state 로 이동 → v11 "벌림"+fault_kind=extension_or_alignment 로 drift(kip-up supported: leg/line/unknown/extension_or_alignment "양다리 벌림 각도가 기준에 비해 현저히 좁음" moderate → leg_extension 으로 새서 감점 유실. 왼팔 pole_gap_or_bent major 짚기는 성공 — belle 육안 일치). 키워드 추가는 두더지잡기 — 구조화 출력에 고정 enum 강제 + 라우터 enum 1순위 소비로 종결.

### 구현 (2 커밋: 54b20d4 스키마/프롬프트, e697364 라우터)

- **SCHEMA v8.1**: differences[] 에 `fault_category` **필수** — `vision_veto.FAULT_CATEGORIES` 고정 enum (split_angle/limb_extension/pole_gap/alignment/grip/other, 기존 criterion/FaultKey 체계 1:1 — 새 분류 발명 금지, 단일 owner = vision_veto).
- **PROMPT v11.1**: 단일/비교 프롬프트 공통 정의 rule 1줄씩 — 스플릿 = "벌림"/"스플릿"/"다리 사이 각도" 전부 split_angle (drift 봉인).
- **라우터**(criteria_for_fault): ① enum split_angle → 무조건 split 분기 (1순위). ② split 키워드 폴백 유지 + **"벌림" 추가**(구 캐시 하위호환 + enum 오분류 방어 — 재발 축이 split 유실이라 split 어휘 방어를 비-split enum 위에 둠). ③ alignment→line / grip→gap 단독-결정 enum. ④ limb_extension/pole_gap/other/부재 → 기존 키워드 체인(하위호환, 결과 불변).
- 캐시 bump: PROMPT/SCHEMA_VERSION 키 포함 = 자동 무효화. AGGREGATION agg4 불변(집계 로직 무접촉). 신규 튜닝 상수 0.

### 게이트 상태

- 로컬: 관련 스위트 GREEN (deduction/vision_veto/scorer/pipeline seam/phase24·25 gates/eval_out_dir **278 passed**, 신규 15 테스트 포함 — v11 실측 형상 enum 라우팅/enum 부재 폴백/오분류 방어/clean 방어 불변/rich 캐시 왕복). baseline artifact diff 0 (evals/ 무접촉). 전체 backend 스위트 실패 집합 = 변경 전과 byte-identical (회귀 0, worktree 대조 실측).
- 다음 pod sweep 기대치: kip-up split 관측이 fault_category=split_angle 로 산출 → 라우팅 확정(어휘 무관). 판정 게이트는 #3 라운드와 동일.
