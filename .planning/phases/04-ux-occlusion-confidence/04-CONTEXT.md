# Phase 4: 다중 시점 촬영 UX + occlusion confidence 게이트 - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning (spike 선행 필수)

> ⚠ **ROADMAP supersede 박제** — 본 CONTEXT.md 는 ROADMAP.md Phase 4 의 "정면+측면 2시점 업로드 UX" scope 를 belle 2026-06-10 pivot ([[camera-angle-ai-single-view-synth]]) 정합으로 **Camera Angle AI (single-view → AI 가상 다각도 합성)** 으로 재정의함. ROADMAP.md 의 success criteria 4개 중 #2 ("다중 영상 업로드 시 동일 analysisId 아래 시점별 저장") 는 폐기. plan-phase 진입 시 ROADMAP.md 갱신 필요.

<domain>
## Phase Boundary

**Phase 4 = Camera Angle AI (single-view 가상 다각도 합성) + occlusion confidence 게이트.**

사용자는 1 영상만 업로드한다. 백엔드는 RTMW 1차 분석 후 신뢰도 낮은 phase / 가려진 관절을 식별해 **해당 구간 / 관절만 핀포인트로 AI 가상 다각도 뷰를 합성**해서 재추론 → 두 결과 병합 → confidence 향상. 사용자에게 "여러 각도 촬영" UX 는 영구 제거.

**In scope (Phase 4):**
- 1차 RTMW 분석의 confidence 게이트 강화 (Phase 1 D-22 위에 적용)
- 신뢰도 미달 phase / 가려진 관절 식별 로직 (기존 `occlusion_high_in_phase`, `low_confidence_normalization_off`, scene_finder `occlusion_severe` / `camera_angle_problematic` 와 통합)
- AI 가상 뷰 합성 호출 (조건부 + 부분 합성 — 비용 효율 우선)
- 합성 뷰로 RTMW 재추론 + 두 결과 병합
- Fallback (합성 실패 → 단일 카메라 결과로 graceful degrade + 결과 화면에 정확도 제한 표기)
- 정은지 5영상 재처리 (파이프라인 완성 후 자동)
- 결과 화면 "이 구간은 가림 — 추정" 표기 (기존 Phase 12.5 자세히 모달 정합)

**Out of scope (Phase 4):**
- 다중 시점 직접 업로드 UX (영구 제거 — belle pivot)
- 합성 결과를 사용자에게 직접 보여주는 UI (deferred — v2)
- 스피닝 폴 (v1.5, Phase 1 D-10 정합)
- 사선/뒤 시점 v2 (메모리 박제 유지)

</domain>

<decisions>
## Implementation Decisions

### Phase 4 방향 (most foundational)
- **D-01:** Phase 4 = **Camera Angle AI redesign**. 사용자에게 다중 시점 직접 업로드 요구 **영구 제거**. ROADMAP.md Phase 4 의 SC #2 ("다중 영상 업로드 시 시점별 저장") 폐기. 메모리 [[camera-angle-ai-single-view-synth]] + [[single-camera-first-multi-view-last]] 정합.
- **D-02:** 사용자 UX = 1 영상 업로드 → 결과 화면 받음. AI 합성은 백엔드에서 사용자 무관하게 일어남.

### 합성 트리거 정책
- **D-03:** **조건부 + 부분 합성**. 영상 전체 AI 합성 X. 1차 RTMW 분석 후 confidence 미달 phase / 가려진 관절만 핀포인트 보완. belle 의 비용 효율 직관 정합 ("자주 돌린다고 했을 때 비용 절감").
- **D-04:** 트리거 후보 (구체 임계값/조건은 plan-phase 에서 spike 결과로 확정):
  - (a) RTMW 키포인트 score 임계값 미달 phase (Phase 1 D-22 `confidence = rtmw_score` 정합)
  - (b) `force_signals.py` 의 `occlusion_high_in_phase` warning 발동 phase
  - (c) Gemini scene_finder 의 `occlusion_severe` / `camera_angle_problematic` Finding (Phase 17 정합)
  - (d) 도메인 후보: 회전(spin) / 거꾸로 매달림 / 측면 자세 (RTMW 3D 정확도 약점 — `three_d_path_decision.md` 박제)

### 사용자 노출 정책
- **D-05:** MVP = **완전 블랙박스**. 사용자는 AI 보완이 일어났는지 모름. 점수와 설명만 노출. (Phase 12.5 자세히 모달의 confidence / 추정 표기는 유지 — "이 구간은 가림 — 추정" 같은 일반 카피.)
- **D-06:** "AI 가 보완했어요" 식 명시적 transparency 는 v2 후속 — Phase 4 MVP 에서는 X.

### Fallback / 실패 처리
- **D-07:** 합성 API 실패 / 시간초과 / 비용 손절 시 = **graceful degrade**. 1차 RTMW 결과로 분석 계속 진행. 분석 자체 중단 X. (belle 의 "분석 정확도 최우선" 메모리 [[feedback-analysis-first]] 와 "전혀 못 받는 것보단 부정확하게 받는 게 나음" 의 균형.)
- **D-08:** 단, 합성 실패 시 결과 화면에 **명확한 정확도 제한 표기** 필수 ("AI 보완 적용 실패 — 가림 구간 정확도 제한적"). confidence warning code 신규 (`ai_synthesis_failed` 또는 유사 — plan-phase 박제).

### 정은지 5영상 재처리
- **D-09:** Phase 4 파이프라인 완성 후 **자동 재처리**. mode 1 비교의 양쪽 원터필 — 신규 사용자 영상은 새 파이프라인, reference 는 옛 파이프라인이면 비교 무의미.
- **D-10:** belle 가 지적한 "5영상 중 분석 이상한 거 많음" (Phase 17 G4 occlusion FP, Phase 8.1 axis severity 등) 이 AI 합성으로 해결되는지 **동시 검증**. 해결되면 Phase 4 의 부가 가치 박제, 안 되면 별도 추적 (Phase 17 G4 가드 + 도메인 root cause 후속).

### Spike 선행
- **D-11:** Phase 4 본격 plan-phase 진입 **전에 `/gsd:spike` 로 PoC** 필수. 메모리 [[gemini-vision-active-use]] 정합.
- **D-12:** Spike **기준선 = Gemini Vision** (이미 Phase 17 통합 완료, 추가 도입 비용 0). 비교 후보 = Higgsfield Change Camera, Magnific, 기타 single-view → multi-view synth API.
- **D-13:** 비교 API 평가 항목 (3가지 모두 PASS 해야 Gemini Vision 교체):
  - (a) 가상 카메라 앵글 변환 정확도 (폴스포츠 회전 동작 핸들링)
  - (b) AI 가상 뷰 합성 품질 (occlusion 부위 재구성)
  - (c) 합성 뷰로 RTMW 재추론 시 pose 정확도 향상 효과 (실측 비교 — 정은지 5영상 등 기존 부정확 케이스 기준)

### 비용 절감 전략 (D-03 보강, plan-phase 디테일)
- **D-14:** 조건부 트리거 (D-03), 부분 합성 (D-03) 외 추가 전략:
  - **캐싱** — 같은 영상 재분석 시 합성 결과 재사용 (deferred 박제 — plan-phase)
  - **해상도/프레임 다운샘플** — 합성 입력 자체 가볍게 (plan-phase)
  - belle 의 "자주 돌린다고 했을 때" 운영 가정 — 비용 dashboard / 예산 알람은 별도 plan (deferred)

### Claude's Discretion
- 구체 confidence 임계값 (RTMW score N % cutoff), 부분 합성 윈도우 길이 (몇 프레임), 캐싱 키 전략, 비용 dashboard 구체화 — 모두 spike + plan-phase researcher 의 영역.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (planner, researcher, executor) MUST read these before planning or implementing.**

### Phase 4 pivot 박제 (memory)
- `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/camera-angle-ai-single-view-synth.md` — 2026-06-10 belle 박제: single-view AI 가상 다각도 합성, Phase 4 redesign 직접 지시
- `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/single-camera-first-multi-view-last.md` — 2026-06-01 belle 박제: 다각도 최후 수단, 신기술 single-view 우선
- `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/gemini-vision-active-use.md` — Gemini Vision 적극 활용 (Phase 4 spike 기준선)
- `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/feedback-analysis-first.md` — 분석 정확도 최우선 (fallback 박제 근거)
- `~/.claude/projects/-Users-kimtaesung-Dev-SunityMotion/memory/mvp-simple-pilot-quality.md` — 구조 열어두기 + 시연 화면 마감 (Phase 4 scope 제약 기준)

### Requirements / Roadmap
- `.planning/REQUIREMENTS.md` POSE-03 — 키포인트 confidence 임계 미달 프레임 "추정" 표기 + occlusion 경고. (Phase 4 본 결정으로 multi-view 부분은 supersede — confidence 게이트 + AI 합성으로 등가 충족.)
- `.planning/ROADMAP.md` Phase 4 — 현 scope 와 본 CONTEXT 가 모순. plan-phase 진입 시 ROADMAP 동기화 필요 (SC #2 폐기 + 신규 SC 추가).

### Prior phase context
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` §D-04, §D-22 — RTMW 키포인트 score → `confidence = rtmw_score`, `uncertainty_proxy = 1 - confidence`. 본 phase 의 1차 신뢰도 산출 표준
- `.planning/phases/01-poseengine-mediapipe-nlf-r-d/01-CONTEXT.md` §D-11 — 폴 축 검출 실패 폴백 카피 ("카메라 기울어져 세부 각도 해석에 주의") — Phase 4 합성 실패 카피 톤 참조
- `.planning/phases/17-gemini-vision-integration-4/17-CONTEXT.md` — Gemini Vision 통합 박제 (Finding 출력, G4 정은지 occlusion FP 가드 진행 예정)
- `.planning/phases/17-gemini-vision-integration-4/17-AI-SPEC.md` — Gemini Vision 분석 평가 박제
- `.planning/phases/08.1-axis-metric-redesign/` — 정은지 5영상 axis severity 정합 (5영상 재처리 시 회귀 검증 기준)
- `.planning/phases/12_5-ui-transparency/12_5-CONTEXT.md` — 자세히 모달 / "추정" 카피 톤 (Phase 4 confidence 표기 일관성)

### Code (재사용 / 통합 지점)
- `backend/shared/python/sunity_shared/analysis/temporal.py` — confidence 가중 시간 보간 (1차 분석 → 합성 결과 병합 시 재사용)
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:1416` — `low_confidence_normalization_off` warning (게이트 자산)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1274` — `occlusion_high_in_phase` warning (트리거 후보 D-04.b)
- `backend/shared/python/sunity_shared/gemini/scene_finder.py` — `occlusion_severe`, `camera_angle_problematic` Finding (트리거 후보 D-04.c, G4 가드와 연동)
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py:99-181` — `low_confidence` category 처리 패턴 (참조 패턴)
- `backend/shared/python/sunity_shared/models.py:234-237` — 기존 13 warning code 카탈로그 (신규 `ai_synthesis_failed` 등 추가 위치)
- `backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/three_d_path_decision.md:110` — "occlusion / 거꾸로 매달림 자세" lifter 약점 박제 (D-04.d 도메인 후보 근거)

### 도메인 / 시스템
- `docs/research/02_힘방향_힘조절_엔진_FINAL.md` §0.7 — occlusion 리스크 / 다중 시점 권장 (원안 다중 시점 박제 — 본 phase 가 supersede)
- `docs/research/00_시스템_아키텍처_FINAL.md` — 두 엔진 (체형 보정 + 힘 패턴) 입력은 PoseEngine 의 confidence 보장 위에서 동작

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`temporal.py`** — confidence 가중 시간 보간 로직. AI 합성 결과 ↔ 1차 결과 병합 시 그대로 적용 가능 (인터페이스 무수정 가능성 높음).
- **`body_normalizer.py`** `low_confidence_normalization_off` warning + `extra_warnings` 파라미터 — 신규 warning code (`ai_synthesis_*`) 주입 통로 이미 존재. R8 fix 패턴 정합.
- **`force_signals.py`** `occlusion_high_in_phase` warning — 트리거 시그널로 직접 사용 가능. phase 단위 게이트 박제 자산.
- **`gemini/scene_finder.py`** — `occlusion_severe`, `camera_angle_problematic` Finding 이미 Phase 17 에서 산출 중. Phase 4 트리거 입력 0 추가 비용으로 활용.
- **`gemini_technique_recognizer.py`** `low_confidence` category 처리 — Phase 4 의 "합성 후에도 confidence 안 오르면 어떻게?" 케이스 정합 패턴.

### Established Patterns
- **PoseEngine 인터페이스 추상화** (Phase 1) — Phase 4 의 "합성 뷰 재추론" 도 동일 인터페이스 위에서 동작해야 함. 다운스트림 분석 레이어 무수정 박제 유지.
- **Flat 저장 정합** (CLAUDE.md, Firestore nested-array 금지) — 합성 결과 메타데이터 (어떤 phase / 어떤 joint 합성됐는지) 도 flat 저장 강제.
- **Adapter 경계** (interfaces.py) — AI 합성 API (Gemini Vision / Higgsfield 등) 도 `Protocol` 기반 adapter 로 격리. 모델 교체 시 1개 구현체 + config flag 만.
- **Warning code 카탈로그** (models.py:234) — 신규 warning code 는 frozenset validate 통과 후 추가.
- **G4 occlusion FP 가드** (Phase 17 Plan 17-02) — `is_reference=True + occlusion_severe=True` 동시 시 4 flag. Phase 4 의 reference (정은지 5영상) 재처리 시 동일 가드 적용 필수.

### Integration Points
- **`pipeline/app.py::_process`** — Phase 4 의 합성 트리거 호출 / 결과 병합이 여기에 wiring (Phase 6 Plan 06-02 의 `_extract_video_analysis_inputs` helper 정합).
- **RunPod inference server** — 합성 API 호출은 Pod 에서 (CPU Lambda 에서 호출 시 timeout 위험). `runpod_inference/server.py` 의 BackgroundTask 패턴 정합.
- **Firestore `users/{uid}/analyses/{id}` 문서** — confidence / warnings / aiSynthesis 메타데이터 저장 (Phase 4 신규 스키마, contract.md / models.py / userAnalyses.ts 동시 갱신 필요 — single source of truth 박제).

</code_context>

<specifics>
## Specific Ideas

- **belle 의 비용 효율 직관** ("자주 돌린다고 했을 때 비용 절감 방법") — Phase 4 의 핀포인트 합성 전략 = 영상 전체 합성 대비 비용 1/N 수준 (N = 영상 중 합성 필요 구간 비율). Plan-phase 의 cost model 수립 시 belle 직관을 정량 검증.
- **belle 의 "구글맵 뷰" 비유** (Q1 답) — 사용자 본인이 평소 못 보는 각도 (위쪽 / 반대쪽) 보고 싶어할 수 있다는 흥미. Phase 4 MVP 에서는 블랙박스 (D-05) 지만 v2 deferred 후보로 박제. 합성 결과를 "스트리트뷰 식" 인터랙티브 뷰어로 제공 가능성.
- **Phase 17 (Gemini Vision) 와의 자연스러운 통합** — scene_finder 가 이미 occlusion_severe / camera_angle_problematic 출력 중. Phase 4 의 트리거 시그널을 Phase 17 출력에 얹는 게 가장 자연스러운 통합 path (별도 detector 신설 X).

</specifics>

<deferred>
## Deferred Ideas

### v2 (Phase 4 외)
- **다각도 뷰 사용자 노출 (구글맵 스트리트뷰 식)** — 합성 결과를 사용자가 직접 회전/측면/뒤 인터랙티브 뷰어로 볼 수 있게 하는 UX. belle 의 "본인 평소 못 보는 각도 보고 싶을 수도" 흥미 정합. v2 후속 — 별도 phase 박제 (UX + 합성 결과 캐싱 + 뷰어 인터랙션).
- **사선/뒤 시점 합성** — Phase 4 는 측면 + 회전 동작 우선. 사선/뒤 시점은 occlusion 빈도 낮으므로 v2 — 메모리 박제 유지.
- **스피닝 폴 핸들링** — Phase 1 D-10 정합. v1.5 별도 phase.
- **합성 결과 캐싱 + 재사용** — 같은 영상 재분석 시 합성 호출 0 비용. 사용량 데이터 확보 후 정책 박제 (deferred).
- **비용 dashboard / 예산 알람** — belle 의 "자주 돌린다고 했을 때" 운영 가정에서 도출. 별도 운영 phase.
- **transparency 모달 — "AI 가 보완했어요" 명시 노출** — D-06 정합. v2 사용자 신뢰 환기용. v1 에서는 confidence 표기만 (Phase 12.5 정합).

### Phase 5 (이미 close-out) / Phase 17 와 협업
- **G4 정은지 occlusion FP 가드** — Phase 17 Plan 17-02 에서 진행 중. Phase 4 재처리 시 동시 적용 검증 (별도 plan X, Phase 17 가 처리).

</deferred>

---

*Phase: 4-ux-occlusion-confidence (재정의: Camera Angle AI)*
*Context gathered: 2026-06-13*
