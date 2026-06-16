---
phase: 13-llm-coaching-detail
plan: B
status: complete
completed: 2026-06-16
---

# 13-B: LLM 분기 카피 + 실 Cerebras 활성화 — SUMMARY

## What was built

동작의 IPSF 등재 여부(`ipsfCode`)로 차원 자세히 카피를 분기하고, 실 LLM coach 경로를 활성화했다. belle 2026-06-16 결정 2건이 반영됨: **(1) 5→11 동작 전부 커버**, **(2) unknown→분기2 안전 기본값**(fail-closed 폐기).

### Tasks (commits)
- **Task 1** (belle 2026-06-16 pre-resolved): 현재 11 동작 라우팅 명확, `ipsf_registered_fixture` 사용 0 → `registered_move_angles.json = {schemaVersion:"1.0.0", angles:{}}` (미래 등재 동작 전용 path만 유지).
- **Task 2** (`db252c9`): `motion_ipsf_map.json` 11-motion curated join + `MotionBranchInfo` frozen dataclass + `lookup_motion_branch`(unknown→`_SAFE_DEFAULT_BRANCH` 분기2) + `assemble.build_result`/`build_dimension_explanation` 분기 pass-through + 분기2 forbidden-phrase 게이트.
- **Task 3** (`79d862c`): `coach_writer` 프롬프트에 동작명/분기/정의각도 주입 + `pipeline/app.py` lookup_motion_branch wiring.
- **Task 4** (criteria 5 — 실 Cerebras Pod E2E): **완료, 라이브 검증.** (아래 검증 참조)

## Verification (criteria 5–8)

- 단위테스트: `tests/phase13` **81 passed**, app `tsc` clean, 0 regression.
- 라우팅 회귀: `test_motion_ipsf_map_coverage.py` — 11 동작 seed(단일 진실원) 전부 non-unknown resolve + unknown→분기2 + forbidden-phrase.
- **풀 파이프라인 E2E (Pod, ref-foxtop 영상, upload→/analyze→Firestore):**
  - 양쪽 coach(Gemini default / Cerebras `GEMINI_COACH_ENABLED=0`) **모두 status=done**.
  - 분기2 카피 `dimensionExplanation.angle.baseline = "정은지 선수 기준 관절 각도"` (criteria 6/8). 금지문구("세계 심사 기준"/"IPSF"/"180°") 0 (criteria 8).
  - `result.tips[].detail2`(causes/injuryRisk/coachNote) 실 LLM 채움 (criteria 5).
- **Cerebras coach 직접 호출 검증**: SSM `/sunity/motion/cerebras-api-key`(csk-) 로드 → 실 detail2 생성 + 분기2 금지문구 clean.

## 파일럿 coach 결정 (belle 2026-06-16)

양쪽 E2E 비교 후 belle 가 **Gemini** 를 파일럿 production coach 로 선택 (개념적 framing + 강사 위임 톤 = 강사 철학 충돌 회피). `GEMINI_COACH_ENABLED=1` 을 Pod `start_server.sh` 에 명시 고정. **Cerebras 는 검증된 fallback** 으로 유지(키/SDK 설치 완료).

## 인프라 (Pod / Firestore)

- 신규 Network Storage Pod(`oeihrna8xe3wbw`, RTX 4090) 부트스트랩 + 서버 의존성(`cerebras-cloud-sdk` 포함) 설치 + uvicorn 기동(auth_configured:true). Lambda `RUNPOD_ANALYZE_URL` + SSM `runpod-analyze-url` 새 Pod 동기화.
- **Firestore `analyses` 컬렉션 그룹 single-field index 면제 7개 신규 적용** (angles, result.joints3d, result.keypointReport + leaves data/confidence/axisData/axisMask). 면제가 reference/versions 엔 있었지만 analyses 엔 누락 → joints3d(2026-06-13 추가) 저장이 `INDEX_ENTRIES_COUNT_LIMIT_EXCEEDED` 로 막혀 있던 것. **production 분석 저장도 함께 복구된 것으로 추정.** 상세: [[firestore-index-entry-limit]] [[analyses-index-exemption-fix]].

## Follow-up (Phase 13 13-C)

섹션형 듀얼 coach 보고서(원인=Gemini / 처방=Cerebras 섹션 분리)는 본 phase 의 새 plan **13-C** 로 처리. "실증 시 둘 중 하나 drop 여부"는 Phase 15 검증 기준. [[section-dual-coach-report]].
