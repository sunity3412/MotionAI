# Spike Manifest

## Idea

**Phase 4 Camera Angle AI 4-way 비교 spike.** Sunity AI Coach (폴스포츠 단일 카메라 영상 → 자세 분석 모바일 앱) 의 Phase 4 = single-view → AI 가상 다각도 합성 + occlusion confidence 게이트. belle 우려: Higgsfield Change Camera 가 closed wrapper 일 가능성 + production 단일 의존 risk. 자체 path (SMPL-X virtual camera render, MagicMan, RTMW mirror) 와 4-way 비교 검증 후 Phase 4 plan-phase 진입. 부산물로 Phase 4.5 (Perspective Correction — tilt + 줌인/줌아웃 + off-center 통합) 잔여 gap 정량화.

**연결 박제:**
- `.planning/phases/04-ux-occlusion-confidence/04-CONTEXT.md` D-11/D-12/D-13/D-17/D-18/D-19/D-20
- 메모리: `camera-angle-ai-single-view-synth`, `single-camera-first-multi-view-last`, `notebook-lm-pole-sports`, `feedback-analysis-first`, `judging-baseline-ipsf-code-of-points`
- 운영 stack: RTMW 133 wholebody (Apache-2.0) + MotionBERT lifter (MIT) + RunPod GPU pod

## Requirements

belle 박제 (변경 금지). spike 진행 중 새 requirement 발생 시 즉시 추가.

- **NotebookLM MCP 우선 활용** — IPSF Code of Points / 폴스포츠 도메인 lookup 은 belle 한테 묻지 말고 노트북 `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` 자동 query (메모리 [`notebook-lm-pole-sports`] 정합)
- **상업 라이선스 정합 필수** — research-only 모델은 production 진입 차단. 메모리 [`rtmw-clean-weight-release-gate`] 동일 함정 회피
- **자체 path 강력 우선** — Higgsfield API 단일 의존 production 금지. spike 단계 비교 baseline 으로만
- **사용자 UX 영구 불변** — "스마트폰 한 대, 한 자리, 한 번". 다각도 직접 촬영 요구 절대 노출 X (메모리 [`single-camera-first-multi-view-last`], [`camera-angle-ai-single-view-synth`])
- **평가 기준 = IPSF GeometricCriterion** — 사람 점수 라벨링 영구 금지. 임계값 수치 라벨링은 OK (메모리 [`analysis-objectivity-no-human-scores`])
- **MVP 단순 우선** — 비용/제어권/license 가 우선, 광택 X (메모리 [`mvp-simple-pilot-quality`])
- **🎯 Spike 001 발견 (2026-06-13):** IPSF Page 19 "split angle must remain the same from all angles/perspectives" = **Camera Angle AI 의 raison d'être 가 IPSF 규정으로 직접 박제됨**. 모든 평가 metric 의 ground truth.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | dataset-eval-harness | foundation | 정은지 5영상 + IPSF rubric (NLM lookup) 위에 4-way 비교용 평가 harness 셋업 | ✓ VALIDATED | foundation, ipsf, nlm, eval |
| 002a | higgsfield-angles-api | comparison | Higgsfield Angles API 의 license/cost/약관 박제 + 실제 호출 검증 | ✗ INVALIDATED | external-api, closed-wrapper, novel-view, license-block |
| 002c | magicman-zero-shot | comparison | MagicMan license 검증 + 인체 NVS zero-shot 추론 품질 | ✗ INVALIDATED | human-nvs, license-gate, smplx, blocked |
| 002b | cylindrical-mesh-virtual-render | comparison | RTMW 3D → cylindrical humanoid mesh → 12 virtual camera render (SMPL-X 제거, license clear) | ✓ VALIDATED-SKELETON | self-path, cylindrical-mesh, license-clear, virtual-render |
| 002d | rtmw-mirror-baseline | comparison | 보정 없는 현 운영 stack 상한 정확도 박제 | PENDING | baseline, rtmw, mirror |

## Risk Order Rationale

1. **001 foundation** — 다른 spike 가 호출할 공통 평가 harness. 0순위.
2. **002a Higgsfield API** — 외부 의존성 가장 큰 가설. license/약관 차단 시 즉시 kill switch → 자체 path 비교 set 축소.
3. **002c MagicMan license** — research-only 추정. 일찍 검증해서 production 가능성 판정.
4. **002b SMPL-X virtual render** — belle 자체 path 강력 후보. 가장 검증 가치 큼.
5. **002d RTMW mirror baseline** — 현 운영 stack 상한. 비교 기준점.
