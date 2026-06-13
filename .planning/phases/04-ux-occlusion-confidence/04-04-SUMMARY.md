---
phase: 04-ux-occlusion-confidence
plan: "04"
subsystem: ml
tags: [synthesis, video-generation, protocol, stub, vertex-ai, gemini-omni, veo, plug-in-slot, pose-03]

requires:
  - phase: 04-ux-occlusion-confidence
    provides: "SynthesisAdapter Protocol + SynthesisResult dataclass (Wave 1, 04-01)"
provides:
  - "VideoGenerationAdapter Protocol (@runtime_checkable) — Stage 4 영상 생성 plug-in slot"
  - "OmniVertexAdapter stub (Gemini Omni via Vertex AI, D-30/D-25)"
  - "VeoAdapter stub (Veo 3.1 Vertex Public Preview, D-27)"
  - "get_video_gen_adapter(adapter_type='omni') 팩토리 — SYNTHESIS_VIDEO_GEN_ENABLED env gated"
  - "4-조건 활성화 게이트 박제 (env + Vertex endpoint + 10-video gate + belle 승인)"
  - "비용 박제 (D-28): Omni $6-36/영상 vs $0.12/video PRIMARY 기준선"
affects:
  - "Phase 5+ Stage 4 활성화 plan (Vertex GA 후 OmniVertexAdapter 실 구현)"
  - "_call_synthesis_adapter SynthesisResult 래핑 wiring plan (W5 R1 하드월 유지)"

tech-stack:
  added: []
  patterns:
    - "@runtime_checkable Protocol — isinstance() 구조적 서브타입 체크 지원"
    - "env flag truthy check 팩토리 — 미설정/0/빈 문자열 모두 None 반환"
    - "Stub 클래스: __init__ raise 안 함, 호출 경로만 NotImplementedError 차단"

key-files:
  created:
    - "backend/shared/python/sunity_shared/analysis/synthesis/video_gen_adapter.py (134 lines)"
    - "backend/tests/phase04/test_video_gen_adapter.py (77 lines)"
  modified:
    - "backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py (+45 lines, VideoGenerationAdapter Protocol 추가)"

key-decisions:
  - "Stub __init__ 은 raise 하지 않는다 (팩토리 truthy check 와 분리) — generate_virtual_view 만 NotImplementedError"
  - "VideoGenerationAdapter 는 SynthesisAdapter 와 별도 Protocol (입출력 시그니처 다름: pixel 합성 vs 좌표 추정)"
  - "Wave 4 = pipeline/app.py 무수정 — 인터페이스만 박제, D-31 정합"
  - "4-조건 활성화 게이트 (env + Vertex endpoint + 10-video pose consistency + belle 승인) — 단일 env flag 불충분 (R9)"

patterns-established:
  - "Pattern 1: Stub adapter — __init__ debug log only, 호출 경로만 NotImplementedError. 인스턴스 생성 ≠ 활성화"
  - "Pattern 2: @runtime_checkable Protocol — structural subtyping 으로 isinstance 체크 지원, inheritance 없이 호환 클래스 확장 가능"
  - "Pattern 3: Plug-in slot — env flag + 4-조건 활성화 게이트. 구현체 1개 + config flag 만으로 활성화 (D-30 D-31)"

requirements-completed:
  - POSE-03

duration: 12 min
completed: 2026-06-13
---

# Phase 04 Plan 04: Stage 4 VideoGenerationAdapter Plug-in Slot Summary

**VideoGenerationAdapter Protocol (@runtime_checkable) + OmniVertexAdapter / VeoAdapter NotImplementedError stub + SYNTHESIS_VIDEO_GEN_ENABLED env-gated 팩토리 박제 (Vertex GA 후 활성화 슬롯)**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-13 (자동 측정 생략)
- **Completed:** 2026-06-13
- **Tasks:** 2 (both `tdd="true"`)
- **Files modified:** 3 (1 modified + 2 created)

## Accomplishments

- VideoGenerationAdapter Protocol (`@runtime_checkable`) 박제 — Stage 4 영상 생성 plug-in 슬롯 (D-30 D-31)
- OmniVertexAdapter / VeoAdapter stub — `__init__` 성공, `generate_virtual_view` 호출 시만 NotImplementedError (D-25 D-27)
- `get_video_gen_adapter` 팩토리 — `SYNTHESIS_VIDEO_GEN_ENABLED` env truthy gate (T-04-W4-01 mitigate)
- 4-조건 활성화 게이트 박제 (env + Vertex endpoint + 10-video pose consistency gate + belle 승인) — R9
- 비용 박제 (D-28): Omni $6-36/영상 vs $0.12/video PRIMARY 기준선
- R1 non-scoring 하드월 W5 미래 우회 방지 주석 (SynthesisResult 래핑 강제)
- 5/5 신규 단위 테스트 GREEN — phase04 31→36 passed

## Task Commits

1. **Task 1: VideoGenerationAdapter Protocol + OmniVertexAdapter / VeoAdapter stub** — `a934b06` (feat)
2. **Task 2: 비활성 단위 테스트 5개 (stub gate)** — `f962424` (test)

_TDD ordering follows plan's explicit `<action>` step order (impl→test). Plan specified per-task commit messages were used verbatim._

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py` (+45 lines) — `VideoGenerationAdapter` Protocol 추가 (`@runtime_checkable`), `runtime_checkable` import 추가, 모듈 docstring 갱신, `__all__` 에 `VideoGenerationAdapter` 추가. 기존 `SynthesisResult` / `SynthesisAdapter` / `identify_occlusion_targets` / `merge_with_temporal` 무변경.
- `backend/shared/python/sunity_shared/analysis/synthesis/video_gen_adapter.py` (134 lines, NEW) — `OmniVertexAdapter`, `VeoAdapter`, `get_video_gen_adapter` 신설. 파일 헤더에 D-28 비용 + 4-조건 활성화 게이트 + R1 W5 우회 방지 주석 박제. 클래스별 라이선스 주석 (Gemini Apache-2.0 / Veo Vertex Public Preview).
- `backend/tests/phase04/test_video_gen_adapter.py` (77 lines, NEW) — 5개 단위 테스트 (disabled_by_default / explicitly_disabled / omni raises / veo raises / protocol structural subtyping).

## Decisions Made

- **Stub `__init__` 은 raise 하지 않는다.** 팩토리 truthy check 와 호출 차단을 분리 — 인스턴스 생성은 성공, `generate_virtual_view` 만 NotImplementedError. 이유: 향후 dependency injection 으로 mock adapter 주입 가능성 + 팩토리 동작 단위 테스트 용이성.
- **VideoGenerationAdapter 는 SynthesisAdapter 와 별도 Protocol.** 입출력 시그니처가 다름 — SynthesisAdapter 는 `(T,17,3)` joints → `SynthesisResult`, VideoGenerationAdapter 는 `(T,H,W,3)` RGB frames + camera delta → `(T',H,W,3)` 합성 프레임. 같은 Protocol 로 통합 시 LSP 위반.
- **Wave 4 = pipeline/app.py 무수정.** D-31 "Wave 4 = 인터페이스만 박제" 정합. `pipeline/app.py` 마지막 수정 = `2790f57` (Wave 4 이전).
- **4-조건 활성화 게이트.** 단일 env flag 불충분 (R9). `SYNTHESIS_VIDEO_GEN_ENABLED="1"` 만으로는 활성화 X — Vertex endpoint 공식 등록 + 10-video pose consistency gate + belle 승인 4개 모두 충족 필수.

## Deviations from Plan

None — plan executed exactly as written.

5개 acceptance criteria (Task 1 + Task 2) 모두 첫 패스에 통과. plan 의 `<behavior>` 가 4개, `<action>` 이 5개 (test_video_gen_explicitly_disabled 추가) 언급한 점 — 사용자 프롬프트 지시대로 5개 모두 구현했다.

## Threat Model Dispositions Confirmed

| Threat ID | Disposition | Confirmation |
|-----------|-------------|--------------|
| T-04-W4-01 (Tampering — env flag) | mitigate | `get_video_gen_adapter` truthy check (env != "1" → None). 단위 테스트 2개 (disabled_by_default / explicitly_disabled) 회귀 게이트 GREEN. |
| T-04-W4-02 (Info Disclosure — API key) | accept | stub 단계 표면 없음 (외부 호출 코드 X). 미래 plan 항목으로 SSM Parameter Store 정책 박제 (코드 주석). |
| T-04-W4-03 (DoS — 실수 활성화) | mitigate | `generate_virtual_view` 즉시 NotImplementedError raise. 단위 테스트 2개 (omni/veo raises) GREEN. pipeline `_call_synthesis_adapter` 의 `except Exception` 블록이 graceful 흡수 (Wave 4 미연동이지만 향후 활성화 시 안전망). |
| T-04-W4-SC (Tampering — 패키지 설치) | accept | 신규 패키지 설치 없음. 표준 라이브러리 (`os`, `logging`) + 기존 `numpy` 만 의존. `pip install` 명령 실행 0회. |

## Verification Output

```
$ python3 -m pytest backend/tests/phase04/test_video_gen_adapter.py -x -q
.....                                                                    [100%]
5 passed in 0.02s

$ python3 -m pytest backend/tests/phase04/ -q
36 passed, 2 skipped, 2 warnings in 0.98s

$ python3 -m pytest backend/tests/ --ignore=backend/tests/test_pole_detector.py -q
36 failed, 1704 passed, 12 skipped, 39 warnings in 12.08s
  baseline: 36 failed, 1699 passed, 12 skipped → 신규 +5 passed, 회귀 0

$ PYTHONPATH=backend/shared/python python3 -c "from sunity_shared.analysis.synthesis.interfaces import VideoGenerationAdapter; from sunity_shared.analysis.synthesis.video_gen_adapter import OmniVertexAdapter, VeoAdapter, get_video_gen_adapter; print('OK')"
OK

$ grep -c "SYNTHESIS_VIDEO_GEN_ENABLED" backend/shared/python/sunity_shared/analysis/synthesis/video_gen_adapter.py
4

$ grep -c -E "ai_synthesis_failed|VideoGenerationAdapter|NotImplementedError" backend/shared/python/sunity_shared/analysis/synthesis/video_gen_adapter.py
7
```

**Notes on backend full-suite 36 failures:**
- All 36 failures are pre-existing (Phase 0~3 unrelated to Wave 4 scope). Major clusters: `test_pipeline_geminid_wiring.py` (`_call_wave2_helper`, `_augment_low_confidence`), `test_spike_gemini_moment_smoke.py`.
- `test_pole_detector.py` excluded from collection due to `ModuleNotFoundError: fixtures` (pre-existing, not introduced by Wave 4).
- Wave 4 changes did not add or resolve any of these — out of scope per execute-plan.md "Scope Boundary".

## Acceptance Criteria Checklist

### Task 1
- [x] `test_video_gen_disabled_by_default` GREEN
- [x] `test_omni_adapter_raises_not_implemented` GREEN
- [x] `test_veo_adapter_raises_not_implemented` GREEN
- [x] `test_protocol_structural_subtyping` GREEN
- [x] Protocol + adapter imports 성공
- [x] grep `SYNTHESIS_VIDEO_GEN_ENABLED` count = 4 (≥1)
- [x] grep `VideoGenerationAdapter|NotImplementedError|...` count = 7 (≥1)

### Task 2
- [x] 5개 테스트 모두 GREEN
- [x] phase04 전체 GREEN (36 passed, 2 skipped)
- [x] backend 전체 회귀 0 (pre-existing 36 failed 불변, +5 passed)
- [x] pipeline/app.py 수정 없음 (`git log -1 --format=%H -- backend/functions/pipeline/app.py` = `2790f57`, Wave 4 이전 커밋)

### Success Criteria (plan-level)
- [x] (1) VideoGenerationAdapter Protocol import 성공
- [x] (2) OmniVertexAdapter / VeoAdapter generate_virtual_view → NotImplementedError
- [x] (3) SYNTHESIS_VIDEO_GEN_ENABLED 미설정 → None → 파이프라인 영향 없음
- [x] (4) 단위 테스트 5개 GREEN
- [x] (5) 기존 Phase 4 suite 회귀 0 (31→36 passed 순증가, skipped 불변)
- [x] (6) 비용/라이선스 주석 박제 — D-28 정합 (Omni $6-36 / Veo Vertex Preview / Vision $0.12 기준선)

## Issues Encountered

None — 두 task 모두 첫 패스에 모든 acceptance criteria 통과.

## User Setup Required

None — 외부 서비스 구성 불필요. 모든 변경은 stub 코드 + 단위 테스트 (외부 호출 0).

## Follow-ups (Wave 4 이후 plan 후보)

1. **Vertex GA 후 OmniVertexAdapter 실 구현** (별도 plan): Vertex AI Model Garden console 에서 Omni endpoint 등록 확인 → Vertex SDK 호출 + 응답 파싱 + `(T',H,W,3)` ndarray 변환 박제. GEMINI_API_KEY → SSM Parameter Store (CLAUDE.md §3).
2. **10-video pose consistency gate spike** (별도 plan): Omni 생성 영상에서 RTMW 가 일관된 pose 를 뽑아내는지 sweep + belle 평가. 활성화 4-조건 게이트 중 핵심.
3. **`_call_synthesis_adapter` SynthesisResult 래핑 wiring** (별도 plan, W5 정합): 실 구현 후 `generate_virtual_view` raw ndarray 를 `SynthesisResult` 로 변환하여 R1 non-scoring 하드월 유지. pipeline 측에서만 wiring (어댑터는 ndarray 반환 유지).
4. **Veo 3.1 PoC spike** (D-27): Vertex Public Preview 가격 / 품질 비교. Omni 단일 활성화 vs Omni+Veo 듀얼 활성화 결정.

## Next Phase Readiness

- Phase 4 Wave 4 (Stage 4 plug-in slot 박제) 완료. Phase 4 전체 progress: Wave 1~4 박제 완료.
- Stage 4 활성화는 Vertex GA + 10-video gate + belle 승인 충족 시 별도 plan 으로 진행.
- 회귀 0 — 기존 Phase 4 suite + backend suite 영향 없음.

## Self-Check: PASSED

- `backend/shared/python/sunity_shared/analysis/synthesis/video_gen_adapter.py` exists ✓
- `backend/tests/phase04/test_video_gen_adapter.py` exists ✓
- `backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py` modified (VideoGenerationAdapter Protocol 추가) ✓
- Task 1 commit `a934b06` exists ✓
- Task 2 commit `f962424` exists ✓
- Phase04 36 passed, backend 1704 passed (+5 vs baseline, regression 0) ✓
- pipeline/app.py unchanged (last commit `2790f57`, pre-Wave 4) ✓

---
*Phase: 04-ux-occlusion-confidence*
*Completed: 2026-06-13*
