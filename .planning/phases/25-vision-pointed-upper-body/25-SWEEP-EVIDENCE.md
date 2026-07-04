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
