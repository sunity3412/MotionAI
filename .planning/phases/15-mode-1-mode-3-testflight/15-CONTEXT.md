# Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

이 phase는 **새 기능 추가가 아니라 실영상 end-to-end 검증 + 전달**이다. 코드(분석 파이프라인·리포트·오버레이·보완운동·듀얼 coach·기준모션 등록)는 Phase 1~14/17에서 이미 깔려 있다. Phase 15가 하는 일:

1. **Mode 1** (정은지 기준 비교) — 사용자가 정은지 reference를 불러와 본인 영상과 비교, 전문가 기준 점수를 실영상으로 end-to-end 확인 (MODE-01)
2. **Mode 3** (자기 발전) — 동일 인물 2영상의 차원 점수 세션 간 델타 ("지난 분석보다 N점 발전" 형태)를 실영상으로 확인 (MODE-02). [2026-06-17 리뷰 정정 D-13] 현 계약(`build_mode3` + `result.tsx:192`)은 차원 점수 델타이지 관절 각도 델타가 아님 — Phase 15는 검증-only라 점수 델타로 통일.
3. **위양성 게이트** — 정은지(고수) 영상이 41점 같은 위양성 없이 자세 품질을 반영하는 점수로 산출 (SCORE-04 / SC3)
4. **TestFlight 전달** — 수강생이 익명 게스트로 회원가입 없이 Mode 1·Mode 3를 실기기에서 완주, 결과 영상 재생 (DELIV-01)

**Out of scope:** 영구 라벨 regression fixture + fault 자동 assert 하니스화 = Phase 18 (Expert deliberate-fault eval set, Phase 15 의존). 범위 밖 동작군의 false-reject 허용. 신규 기능/화면 추가 금지.
</domain>

<decisions>
## Implementation Decisions

### 위양성 게이트 증명 방법 (SC3 / SCORE-04)
- **D-01:** 실 E2E 재측정 + 기존 기준선 대조 방식으로 PASS 판정한다. Phase 15에서 정은지 영상을 **실 Pod E2E**(최신 path = RTMW + Gemini 인식 + 듀얼 coach 포함)로 다시 돌려 점수를 산출하고, 그 점수가 자세 품질을 반영하는지 + axis severity 등이 기대대로 나오는지 assert.
- **D-02:** **임계값 재calibrate 금지** ([[calibration-source-hard-gate]]). 비교 기준선은 기존 확정 evidence — 08.1 `SWEEP-EVIDENCE.md`(정은지 5영상 P100+margin tilt threshold) + Phase 1 IPSF GeometricCriterion baseline. Phase 15 sweep 결과로 threshold를 다시 맞추는 circular tuning 금지. 신규 실행은 "현 기준선 위에서 통과하는가"를 보는 용도.
- **D-03:** mock E2E만으로 게이트 충족 선언 금지 — 실 LLM/듀얼 coach 포함 최신 path 재검증이 게이트의 일부.

### 실영상 검증 데이터셋
- **D-04:** **Mode 1** 비교 대상 = 등록된 **11개 reference 전부**([[reference-library-phase4-all11]], phase4_v1 RTMW 재처리 완료). "5"는 위양성 calibration 영상 수였을 뿐 — Mode 1은 11개 기준. [2026-06-17 라운드2 리뷰 정정] 11개 전부 **필드 검증**(seed-reference-downstream.mjs --verify 11/11)되지만, **실 Mode1 E2E 비교는 정은지 학생영상이 있는 7개 모션**(climb/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin/combo)만 — ref-foxtop/foxtop-split/invert/sideway-spin 4개는 학생영상 없어 live 비교 미실시(명시적 coverage limitation, 은폐 금지).
- **D-05:** **Mode 3 + 위양성 = 정은지 6 성공/실패 페어** 활용 ([[jeongeunji-success-fail-pair-dataset]]). 위치 `~/Downloads/정은지 선수 추가 영상/`. 6 동작: pdshape · elbow-twist-sister · climb · kip-up · power-spin · peter-pan. 동일 인물·동일 동작이라 Mode 3 델타(성공 vs 실패)와 위양성 게이트(성공=높음+low severity / 실패=fault 잡고 높은 점수 안 줌)를 한 셋으로 동시 검증. "나중에 추가된 6개 = 이 영상들" (belle 확인).
- **D-06:** **objectivity 하드가드** — `분석결과/*.md`(누군가 작성한 분석 문서)는 fault가 무엇인지 **정성 참고만**. [[analysis-objectivity-no-human-scores]]에 따라 "이 영상 N점" ground-truth 점수 라벨로 영구 금지. 분석기가 독립적으로 fault를 잡아내야 검증이 의미. fault 종류 라벨(영상 입력 라벨)은 OK.
- **D-07:** belle 본인 2영상 페어(실 사용자 장비·체형 커버)는 **선택** — 있으면 보강, 없어도 정은지 페어로 진행 가능.

### TestFlight 전달
- **D-08:** **SIGABRT fix → TestFlight preview 빌드** 경로. letterSpacing SIGABRT는 release 빌드 native crash라 Expo Go에선 재현 안 될 수 있음 → 실 release 환경(EAS preview 빌드)에서 잡고 검증해야 함.
- **D-09:** **핸드오프 규칙** ([[verify-before-handoff-even-final]]) — 내가 SIGABRT fix + EAS preview 빌드 + submit까지 돌려 PASS 확인한 뒤, belle에게는 "실기기 게스트 완주(탭 흐름·결과 재생)" 사람만 할 수 있는 단계만 넘긴다. belle가 Xcode/실기기 제공. 미검증 핸드오프 금지.
- **D-10:** 회귀 체크리스트 = presigned URL 만료/Content-Type 이슈 없음([[s3-presigned-video-playback]]) + letterSpacing SIGABRT 회귀 없음.

### 듀얼 LLM coach 검증
- **D-11:** 파일럿 primary = **Gemini 유지** (belle 13-B 선택). 섹션형 듀얼 coach = 원인(왜)=Gemini / 교정 처방(무엇)=Cerebras / 부상위험=Cerebras / 강사확인=Gemini ([[section-dual-coach-report]]).
- **D-12:** 검증 기준 = 실영상에서 둘 다 채워지면 best, **한쪽 drop 시 cross-fill 폴백으로 빈 섹션 0이면 PASS**. 둘 다 필수(drop=FAIL)는 아님 — graceful degrade 허용. (단 D-03대로 실 LLM 호출이 실제로 작동함은 확인해야 함.)

### Claude's Discretion
- Pod 작업(SSH/sweep/Lambda env 동기화/mock·실 E2E 실행)은 내가 실행 ([[pod-ops-claude-runs]]). 현 Pod = xbdkj1g2ylnfwi, `RUNPOD_ANALYZE_URL` Lambda env 동기화 필요 (STATE.md).
- 검증 스크립트 구조, sweep 실행 방식, S3 업로드 경로, assert 구현 디테일은 내 판단.
- 영상 파일명 정규화(`fixtures:` prefix, 더블 확장자 오타 `pdshape-correct.mp4  .mp4`)는 업로드 시 내가 정리.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 위양성 게이트 / calibration baseline
- `.planning/phases/08.1-axis-metric-redesign/` (SWEEP-EVIDENCE.md) — 정은지 5영상 P100+margin tilt threshold (재calibrate 금지 기준선)
- `backend/judging_data/tilt_thresholds.yaml` — schema_v2 axis tilt 임계값 (frozen, sha256 c94bb8…e87c). [2026-06-17 리뷰 정정 D-13] loader = `force_signals.py:250` 가 이 경로 사용. 이전 CONTEXT 의 `analysis/tilt_thresholds.yaml` 경로는 오기 — 존재하지 않음. assert 스크립트는 force_signals.py 와 동일 경로 import.
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/` (Plan 01-15 IPSF GeometricCriterion) — IPSF 객관 baseline

### 검증 데이터셋
- `~/Downloads/정은지 선수 추가 영상/` — 6 성공/실패 페어 + combo + 분석결과 md (repo 밖, belle 로컬 자산)
- 등록된 11 reference 모션 — Firestore `reference/{motionId}` (Phase 14 등록)

### 듀얼 coach / 리포트 계약
- `backend/shared/python/sunity_shared/analysis/assemble.py` (`assemble_dual_coach_sections`) — 섹션 출처 태깅 + cross-fill 폴백
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` / `coach_hook_writer.py` — Gemini/Cerebras writer
- `app/src/types/analysis.ts` ↔ `backend/shared/python/sunity_shared/models.py` ↔ `docs/contract.md` — 3-way 계약 (변경 시 lockstep)

### 전달 / 빌드
- `app/eas.json` — EAS 빌드 프로필 (development/preview/production), iOS submit 설정 (ascAppId 6772934567)
- `app/app.json` — Expo config (bundle com.sunity.aicoach, updates URL)
- STATE.md "남은 작업" — TestFlight 튕김 fix(letterSpacing SIGABRT 후보) + belle 진짜 E2E 검증 항목

### Mode 3 표시 원칙
- `docs/` mode3 = 발전 not 일치 ([[mode3-progress-not-similarity]]) — 절대지표 세션 간 델타, %일치 헤드라인 금지
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/scripts/seed-reference-motions.mjs` — reference 영상 S3 presign + Firestore 등록 (검증 영상 업로드에 재사용 가능)
- 기존 mock E2E artifact 경로 (`uploads/mock_e2e_belle_*`) — 실 E2E 실행 패턴 참고
- `backend/functions/pipeline/app.py::_process` — Lambda/RunPod 단일 분석 path (실 E2E가 타는 경로)
- `backend/runpod_inference/server.py` — Pod `/analyze` (`_process` 재사용, 분기 0)

### Established Patterns
- 실 분석 = RunPod Pod GPU (CUDA 필수, CPU NaN). Pod 교체 시 `RUNPOD_ANALYZE_URL` Lambda env 동기화 필수.
- 앱은 폴링 X, Firestore `users/{uid}/analyses/{id}` onSnapshot 구독으로 status 전이 반응.
- Firestore nested-array 금지 — (T,J) 행렬 flat 저장 + 읽는 쪽 reshape. analyses 인덱스 면제 7개 적용됨([[analyses-index-exemption-fix]]).

### Integration Points
- Mode 1 = `referenceMotionId` lockstep (앱 선택 → 백엔드 비교).
- Mode 3 = 동일 사용자 2 analysis doc 페어링 → 절대지표 델타 계산.
- TestFlight = EAS Build (preview) + EAS Submit (ASC API Key 등록되어 무인 submit OK, [[asc-app-id-and-api-key]]).
</code_context>

<specifics>
## Specific Ideas

- belle 통찰: "정은지 성공영상 + 실패영상(같은 동작)을 활용하면 Mode 3도 함께 할 수 있는 거 아니냐" — 채택. 동일 인물 페어가 Mode 3 델타와 위양성 게이트를 한 셋으로 충족.
- Mode 3 델타 카피 형태: "지난 분석보다 N점 발전했어요!" (차원 점수 세션 간 차이 — 현 `result.tsx:192` 계약). 관절 각도 델타("무릎 신전 8°")는 계약 변경(TS↔Python↔contract.md lockstep + UI + 테스트) 필요라 Phase 15 검증-only 범위 밖 → Deferred.
- TestFlight 완주 정의: 익명 게스트 진입 → Mode 1·Mode 3 둘 다 실기기 완주 → 결과 영상 재생 (presigned/Content-Type/SIGABRT 회귀 없음).
</specifics>

<deferred>
## Deferred Ideas

- **영구 라벨 regression fixture + fault 자동 assert 하니스** — 각 실패 영상에 fault 라벨 달아 분석기가 그 fault를 잡고 위양성 안 주는지 자동 assert. = **Phase 18** (Expert deliberate-fault eval set, Phase 15 의존). Phase 15는 수동 실행 + assert까지만.
- **belle 본인 다양한 앵글/동작 크래시 테스트 영상 대량 소싱** — SC4 강건성 확장. Phase 15는 정은지 페어 + (선택) belle 2영상 페어로 최소 충족, 대량 스트레스셋은 실증 단계.
- `combo.mp4` (성공만, 페어 없음) — Mode 3 페어 미성립이라 Mode 1 단독 분석에만 사용 가능.
- **관절 각도 델타 Mode 3** ("무릎 신전 8° 개선") — result 형상에 관절 각도 델타 필드 추가(TS↔Python↔contract.md lockstep) + UI 렌더 + 테스트. 현 계약은 차원 점수 델타뿐. "수치는 보조, 원인이 핵심" 가치에 더 부합하나 검증-only Phase 15 범위 밖 → belle 결정(2026-06-17)으로 후속 phase 후보. 각도 데이터는 이미 저장됨(stored angles)이라 구현 가능.

### Reviewed Todos (not folded)
None — discussion stayed within phase scope.
</deferred>

---

*Phase: 15-mode-1-mode-3-testflight*
*Context gathered: 2026-06-17*
