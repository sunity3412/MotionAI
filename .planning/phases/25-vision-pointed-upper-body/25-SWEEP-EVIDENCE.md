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
