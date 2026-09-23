---
quick_id: 260923-smt
slug: section-start
date: 2026-09-23
status: complete
---

# Quick 260923-smt — 섹션 착수 정리 + kip-up 수치 정정

코드 변경 0. 문서·설정만.

## 한 것

| # | 항목 | 결과 |
|---|---|---|
| 1 | CLAUDE.md 착수점 경로 3곳 | 260920-cac 를 가리키고 있었다(그 뒤 3번 바뀜). **경로 대신 STATE `stopped_at` 간접참조**로 바꿨다 — 같은 어긋남 3회째라 구조로 막는다. `grep 260920-cac CLAUDE.md` = 0 |
| 2 | `.planning/CONTINUE-2026-09-07.md` | `archive/` 로 이동. 루트 `.md` = 살아있는 문서 7개만 |
| 3 | `.planning/phases/37-/` (빈 `.gitkeep`) | 제거. **실제 고장이었다** — `find-phase 37` 이 이 빈 디렉터리를 돌려줬다. 제거 후 `37-continuous-learning` |
| 4 | `.planning/WAITING.json` (06-10, question=null, gitignored) | `state signal-resume` 으로 해제 |
| 5 | STATE Current Position | 서로 다른 착수점을 적은 09-18·09-20 노트 2개 삭제 → 현행 1개. 페이즈 **실측**: 39 · 완료 30 · 진행중 4 · 미착수 5(37 추가) · plan 205/195. `Current focus` 갱신 |
| 6 | TRAINING-DUE | 6행 잔액 $5.29 → **$4.26**(RunPod API 실측). 1행 건수 548 재확인(manifest 548행, 플라이휠 09-21, launchd 등록 유지). 2행 kip-up 수치 정정 |
| 7 | kip-up 수치 정정 | 아래 |
| 8 | MEMORY.md 착수점 블록 | 착수점·이력 항목 5개(23줄) 삭제 → 인용 경고 1항목(5줄)으로 합침. 착수점 표시는 1개만 남음 |

## kip-up 수치 정정 — 관측

**`[확인]` k02 의 표는 운영 계산이 아니었다.** 지난 세션 대화 기록에서 k02 가 쓴 코드를 복원했다:
원시 각도 행렬로 `motiondtw.motion_dtw(S, R)` 를 직접 부르고 `per_joint_deviation` 에 `ref_fps` 를
안 줬다. 운영(`app._deviation_against`)은 `feature_vector` 로 정렬하고 ref-경계 마스크를 적용한다.

**`[확인]` 소비처 실독** — doc `users/KAi6p4ubcfVMvo8TfvytTkzNp0j2/analyses/e83811d3cc484887b0aef315346f8aae`
(commit 208dc500, rot180_v1):
```
deductionBreakdown.final = 100 · records = []
suppressedRecords[0] = angle_vs_reference__left_shoulder
    measuredValue 20.62 · wouldBePoints -0.7 · interval 15.89~24.33 · tolerance 20.0
    ruleId deviation_within_measurement_error · sampleSize 118
```
운영 경로 재계산값(같은 함수 호출)이 저장값과 일치한다 — 어깨 20.6 · 다른 동작 저장 감점 4건
(power-spin 31.88 · climb 22.57/26.95 · peter-pan 32.68 · pdshape 31.13)도 소수 첫째 자리까지 일치.

| 관절 | 운영 정타 | 운영 실수 | k02 가 적은 실수 |
|---|---|---|---|
| left_shoulder | 3.5 | **20.62** | 20.1 |
| left_elbow | 4.1 | 13.8 | 15.1 |
| right_shoulder | 3.3 | 12.7 | 14.9 |
| right_hip | 2.4 | 9.6 | 8.3 |
| DTW distance | 6.51 | 26.94 | 6.50 / 26.92 |

→ 100점의 기전 = 반올림(0.12점)이 아니라 **−0.7점이 측정오차 구간 억제로 빠졌다.**
2026-09-20 기록(20.6도 · −0.7점 · 신뢰구간 억제)과 같다.

**허용오차 축을 다시 잰 것이 아니다.** 저장된 감점 기록을 읽었다. m49 §1 "죽은 축" 규율 그대로.
판정 "배선 고장 아님"은 유지된다. 틀린 것은 숫자와 기전 설명이다 — CLAUDE.md 보고 규칙
"숫자는 소비처까지 따라가라"의 다섯 번째 사례.

정정 반영: k02 SUMMARY 머리 배너 · m49 HANDOFF 머리 배너 · TRAINING-DUE 2행 · STATE stopped_at ·
MEMORY.md m49 줄.

## 이 작업 중 발견 — 다음 quick 으로 넘긴다

운영 채점 코드의 **감점 재료 계산이 기준 영상의 엉뚱한 구간과 비교할 수 있다**
(`_build_deduction_measured_deviations` 의 DTW fallback). 별도 quick 에서 재현·수리한다.

## 인라인 실행

`init.quick` = `agents_installed: false`. 최근 quick 관례(인라인)와
[[dont-trust-subagent-gate-numbers]] 에 따라 planner/executor 서브에이전트 없이 수행했다.
