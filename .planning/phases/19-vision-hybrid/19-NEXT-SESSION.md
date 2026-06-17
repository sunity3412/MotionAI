# Phase 19 — 다음 세션 시작점 (2026-06-18 작성)

**내일 시작 루트: 비전 그라운딩 스파이크 (Phase 19 D-05) 먼저.**

## 무엇을 하나
보유 fault/correct 페어(정은지)를 **Gemini Vision으로 비교 분석** →
1. "이 동작에서 정은지가 어디를 틀렸나" **정성 ground-truth** (점수 아님, fault 위치/종류)
2. 대략적 **예상 점수/각도/뻗기-갭 범위** (sanity 앵커)
→ 정답을 *알고* 재설계 채점기를 테스트(known-answer) + 비전-추론 접근 우리 도메인 de-risk + Phase 18 eval 라벨 생성.

**절대 경계 (belle):** 이 ground-truth/예상범위는 **앵커·일반화 검증용**이지 **임계값 curve-fit 타깃 아님.** 정답을 *아는 것* ≠ 거기에 *맞추는 것*. 보유셋 overfit 금지 ([[scoring-redesign-must-generalize-no-overfit]]).

## ★ Pod 없이 가능 (중요)
- **RunPod Pod 01emvodj1pdooe 는 RunPod 크레딧 소진으로 자동 종료됨(2026-06-17~18).** SSM `/sunity/motion/runpod-analyze-url` + Lambda `RUNPOD_ANALYZE_URL` 은 죽은 Pod 를 가리킴 → 실 RTMW GPU E2E(Wave 2/3 류)는 belle 가 **크레딧 충전 + 새 Pod 생성**해야 재개 가능.
- **그러나 비전 그라운딩 스파이크는 Pod 불필요** — Gemini 는 외부 API(Google AI Studio 키)고, fault/correct 영상은 로컬(`~/Downloads/정은지 선수 추가 영상/`)에 있음. RTMW GPU 안 씀.
- 필요한 것: **Gemini API 키 접근 경로 확정** — (a) SSM `/sunity/motion/gemini-api-key` 에서 fetch(값 비노출) 또는 (b) belle 가 로컬에 키 제공. 키 소유 = sunity3412 계정([[firebase-project-account]]).

## 시작 시 첫 행동
1. Gemini 키 경로 확정 (SSM vs 로컬).
2. fault/correct 페어 1~2개(예: climb, kip-up — IPSF 등재 + 페어 존재)에 대해 Gemini Vision 비교 스파이크 1회 — 두 영상 비교 → fault 위치/종류 + 대략 각도/갭.
3. 결과를 보고 belle 와 "예상 범위 vs 현재 채점기 출력" 대조 → plan 방향 확정.
4. 그 후 `/gsd-plan-phase 19` (또는 스파이크 결과를 CONTEXT 보강 후 plan).

## 컨텍스트
- 결정/근거: `.planning/phases/19-vision-hybrid/19-CONTEXT.md` (D-01~D-05)
- 근본원인 상세: `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md`
- Phase 15 = "통과" 아님. 점수 신뢰도(정은지 실패영상 94점) 미해결 → Phase 19 가 해결.
