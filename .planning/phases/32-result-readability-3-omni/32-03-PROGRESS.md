# 32-03 진행 상태 (전 Task 완료 — 최종 상태는 32-03-SUMMARY.md 참조)

**작성:** 2026-07-21 18:40 KST (Task 3 완결 반영 19:05 KST) · **실행 커밋 기준:** `c45eb95` (wave-1 포함, origin push 완료)

## Task 상태

| Task | 상태 | 커밋 |
|---|---|---|
| 1. Pod 배포 + 6동작 전수 스윕 (D-23) | **완료** — 게이트 PASS (증거: `32-03-SWEEP.md`) | `08b8d10` |
| 2. wave-1 앱 OTA 발행 | **완료** — production+preview 발행 | `4a0c668` |
| 3. belle 실기기 리뷰 (D-17 3건 + D-23 매핑) | **완료** — `32-GATE-DECISIONS.md` 적재 | `b76361d` |

## Task 2 — OTA 발행 기록

**발행 (2026-07-21 18:37 KST, runtime 1.0.0, android+ios, 커밋 08b8d10 = wave-1 c45eb95 포함 트리):**

| 채널 | 신규 group id |
|---|---|
| production | `2cf7b6af-e583-487a-bdb4-8c1cce4a51f6` |
| preview | `13f4cccd-7c46-42a8-81c5-d3654c28b226` |

**롤백 (1분 절차 — 직전 정상 group):**

```bash
cd app && npx eas update:republish --group c153e0ec-c0db-471a-861b-87264c60b6f3 --non-interactive   # production (31 최종 정상본)
cd app && npx eas update:republish --group 853915f7-dca7-465b-b15f-3275701af4b8 --non-interactive   # preview (30-REVIEW-FIX 정상본)
```

**빌드 경로 청결 검증:** 메인 리포 `app/` 직접 발행 — `node_modules` 실디렉터리(심볼릭 링크 아님) 확인, 임시 worktree 미사용, `npm run typecheck` clean, `eas update:list` 최신 항목 = 본 발행 확인.

**발행 전 시뮬레이터 확인 ([[verify-ui-on-simulator-before-ota]]):** iPhone 16 Pro 시뮬레이터 + Expo Go 54.0.7 로 wave-1 트리 부팅 → 온보딩 첫 화면 정상 렌더(크래시 0, 스크린샷 확인). **한계 정직 기록:** 결과 화면(참고 지표 카드·VideoCompare 슬라이더) 픽셀 확인은 실분석 Firestore doc 필요(phase 26이 시뮬 폴백 제거) + 시뮬 세션에 doc 없음 → 32-02 SUMMARY가 명시 이월한 대로 **Task 3 belle 실기기 리뷰가 최종 픽셀 게이트** (롤백 1분 경로 준비 완료 상태로 진행).

## Task 3 진입 정보 (checkpoint:human-verify — blocking)

- belle 안내 절차 = `32-03-PLAN.md` Task 3 `<how-to-verify>` (실기기 완전 종료 2회 재실행 → 참고 지표 겹침 확인 → 동작 비교 "대략 맞춤" 배지+슬라이더 → 새 분석 1건 확대비교 배율 → D-17 3건 확정 → D-23 매핑 확인).
- 확정 결과 적재 위치: `32-GATE-DECISIONS.md` — "## 실물 게이트 (D-17)" + "## D-23 스윕 매핑" 섹션 (결정·일자·belle 원문 요지).
- 참고: 기존 doc(스윕 이전 분석)은 legacy 폴백(faultZoomComparisons median 오프셋) 경로, **새 분석부터** trim_only 자동 시작 오프셋 + 크롭 parity 적용.

## 운영 노트 (다음 세션/에이전트용)

- Pod `6seluxc43awmqi` (RTX 4090): 서버 PID 14740, wave-1 `c45eb95` 서빙 중, `/health` 200. SSM v16 + Lambda 재동기화 완료 — **sam deploy 시 URL 되돌림 함정 없음** (SSM 최신).
- 스윕 잔여물: Firestore `users/phase25eval/*` (기준선 runId 1784618645 / 배포후 1784623086), `users/pode2e32/*` E2E 1건 — eval 관례상 보존(과거 run들과 동일).
- STATE.md/ROADMAP.md 는 이 플랜 executor 가 건드리지 않음 (mixed worktree wave — orchestrator 소관).
