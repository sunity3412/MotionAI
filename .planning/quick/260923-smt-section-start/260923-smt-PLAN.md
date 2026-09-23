---
quick_id: 260923-smt
slug: section-start
date: 2026-09-23
mode: quick (inline — 서브에이전트 미사용, 아래 사유)
---

# Quick 260923-smt — 섹션 착수 정리 + kip-up 수치 정정

새 섹션 착수 규율([[section-start-housekeeping]], belle 2026-08-30)을 한 바퀴 돈다.
코드 변경 0. 문서만.

**인라인 실행 사유:** `init.quick` 이 `agents_installed: false` 를 보고했고, 이 리포는
최근 quick 들(260922-gnj · 260923-k02 · 260923-m49)을 전부 인라인으로 수행했다.
worktree 서브에이전트는 `backend/.venv` 가 없어 다른 인터프리터로 돈다
([[dont-trust-subagent-gate-numbers]]).

## Task 1 — 착수점을 하나로

- `CLAUDE.md` 의 착수점 경로 3곳(3·85·105행)이 **260920-cac** 를 가리킨다. 그 뒤 착수점이
  세 번(k4p → gnj → m49) 바뀌었는데 CLAUDE.md 만 안 따라갔다. 같은 어긋남 3회째라
  경로를 박지 않고 **STATE.md `stopped_at` 간접참조**로 바꾼다 — `stopped_at` 은 매 세션
  실제로 갱신돼 왔다.
- `.planning/CONTINUE-2026-09-07.md` → `.planning/archive/` (이미 "이력" 배너 부착 상태).
- `.planning/phases/37-/` (빈 `.gitkeep` 만) 제거. **실제 고장이다** —
  `gsd-sdk query find-phase 37` 이 이 빈 디렉터리를 돌려준다. 이대로 `/gsd-plan-phase 37`
  을 돌리면 plan 이 DATA-SPEC·리뷰 문서가 있는 `37-continuous-learning/` 이 아니라
  빈 디렉터리에 떨어진다.
- `.planning/WAITING.json` (2026-06-10, question=null, gitignored) — 3.5개월 방치된 결정
  대기 신호. `gsd-sdk query state signal-resume` 으로 해제.

**done:** `grep 260920-cac CLAUDE.md` 0건 · `find-phase 37` → `37-continuous-learning` ·
루트 `.planning/*.md` 가 살아있는 문서만.

## Task 2 — STATE Current Position 실측

`.planning/phases/` PLAN vs SUMMARY 개수로 센다(규율 그대로):
39 페이즈 — 완료 30 / 진행중 4(22·31·33·36) / 미착수 5(18·21·34·35·37).
plan 205 / SUMMARY 대응 195. `Current focus` 가 "Phase 33" 으로 낡아 있다 — 갱신.
frontmatter `progress`(38/25/118/108)는 GSD 가 관리하는 값이라 손대지 않고, 본문에 실측을 적는다.

## Task 3 — kip-up 수치 정정 (저장된 감점 기록 대조)

quick-260923-k02 의 표(어깨 20.1도 · "0.12점 → 반올림 100")는 **운영 계산이 아니었다.**
k02 는 원시 각도 행렬로 `motion_dtw` 를 직접 불렀고 ref-경계 마스크(`ref_fps`)를 안 줬다.
운영은 `feature_vector` 로 정렬하고 마스크를 적용한다(`app._deviation_against`).

소비처(저장된 doc `e83811d3…` 의 `deductionBreakdown`) 실독:
```
records = []   final = 100
suppressedRecords = angle_vs_reference__left_shoulder  measuredValue 20.62
                    wouldBePoints -0.7   구간 15.89~24.33   tolerance 20.0
                    ruleId deviation_within_measurement_error
```
→ 100점의 기전은 반올림이 아니라 **측정오차 구간 억제**다. 이 값은 09-20 기록(20.6도,
−0.7점, 신뢰구간 억제)과 같다. **"배선 고장 아님" 결론은 그대로다.**

정정 대상: k02 SUMMARY(배너) · m49 HANDOFF §3(배너) · TRAINING-DUE 2행 · STATE stopped_at ·
MEMORY.md m49 줄. 허용오차 축을 **다시 잰 것이 아니다** — 저장된 기록을 읽었을 뿐이다
(m49 §1 "죽은 축" 규율 준수).

## Task 4 — 재학습 게이트 표 갱신 + 메모리 인덱스 정리

- TRAINING-DUE 6행: 잔액 $5.29 → **$4.26** (2026-09-23 밤 RunPod API 실측, Pod 0대,
  지출 $0.015/시간 = 볼륨 보관료).
- MEMORY.md 착수점 블록: 착수점 줄은 1개만. 낡은 착수점·이력 줄은 지우고, 이력 문서를 읽을 때
  필요한 경고만 한 줄로 합친다. 지운 줄 수를 센다.
