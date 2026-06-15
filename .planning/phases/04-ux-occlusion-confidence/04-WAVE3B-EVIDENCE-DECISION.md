# Phase 04 Wave 3b — Evidence-First 결과 + 경로 보류 결정 (2026-06-15)

> 작성: belle 위임("어제 추천 순서대로") → 증거-먼저 단계 실행 → belle 결정 "이 경로 보류".
> 관련: [[calibration-source-hard-gate]] · [[single-camera-first-multi-view-last]] · [[camera-angle-ai-single-view-synth]] · D-18 / D-10 / D-22.

## 1. 무엇을 했나 (증거-먼저 단계)

RunPod 재가동 후, parked 였던 Wave 3b "axis_b RunPod 증거" 를 **새 GPU 추론 없이** 이미 존재하는 Wave 5 재처리 데이터로 계산.

- 소스: Firestore `reference/{id}/versions/{pre_phase4 | phase4_v1}` 5 motion.
- metric: `axis_b.occlusion_frame_rate = mean(confidence < 0.3)` (spike 001 `metrics.axis_b_synthesis_quality`).
- baseline = `pre_phase4.referenceKeypointReport.confidence`, candidate = `phase4_v1.keypointReport.confidence`.
- 양쪽 모두 **8 core joint (shoulder/hip/knee/hand) × 동일 프레임수** → shape 동일 (17관절 RTMW 는 별도 `joints3d` top-level, axis_b confidence 는 양쪽 8관절). 즉 비교는 apples-to-apples (joint-set artifact 아님 — 검증 완료).

## 2. 실측 결과

| motion | base occ_rate | phase4_v1 occ_rate | rate_reduction | mean_conf base→cand |
|---|---|---|---|---|
| ref-sideway-spin | 0.0520 | 0.0440 | **+15.3%** (개선) | 0.712 → 0.693 |
| ref-climb | 0.0253 | 0.0525 | −107.7% (악화) | 0.698 → 0.670 |
| ref-invert | 0.1760 | 0.1856 | −5.5% (악화) | 0.583 → 0.573 |
| ref-foxtop | 0.1373 | 0.1728 | −25.9% (악화) | 0.550 → 0.524 |
| ref-foxtop-split | 0.1044 | 0.1503 | −44.0% (악화) | 0.571 → 0.543 |

mean rate_reduction = **−33.5%**, 개선 1/5, **G4 악화 0 (D-10) = False**.

## 3. 정직한 해석 — 이 비교는 유효 게이트가 아니다

`occlusion_frame_rate` 는 **모델의 self-reported confidence** 에 임계값 0.3 을 건 비율이다. 그런데
- baseline = **구 파이프라인 모델** confidence
- candidate = **RTMW** confidence

→ **서로 다른 두 모델의 confidence 스케일을 비교**하는 것이라, RTMW occ_rate 가 높게 나온 것은 "pose 정확도 하락" 이 아니라 "RTMW 가 다른(더 보수적) confidence 분포를 갖는다" 일 가능성이 크다. mean_conf 차이도 motion 당 0.02~0.03 수준으로 거의 동일하다. belle 의 Wave 5 시각검증(관절각 Δ 0~6°, NaN 0, 프레임 1.5x 촘촘)이 reprocess 품질을 이미 확인했다.

**결론:** reprocess-vs-baseline (구 파이프라인 vs RTMW) 로는 axis_b 합성-정확도 게이트를 대체할 수 없다. 유효한 axis_b 게이트는 **동일 모델(RTMW) 의 합성 유무 비교 — RTMW-baseline vs RTMW+mesh-synthesis** 여야 하며, 그것은 `_rerun_rtmw_on_views` 풀 구현(12-view 합성 렌더 → 실 RTMW 재추론 → camera 역투영 aggregate)이 있어야 가능하다.

## 4. 결정 — mesh-synthesis SECONDARY 경로 보류 (belle 2026-06-15)

- `_rerun_rtmw_on_views` 풀 구현 **보류** (별도 phase 후보). 텍스처 없는 cylindrical mesh 렌더에 RTMW(실인간 학습) 재추론이 baseline 을 실제로 개선하는지 미검증 + SECONDARY 경로(PRIMARY = Gemini Vision occlusion 처리) + Phase 04 는 6/6 complete (phase blocker 아님).
- `SYNTHESIS_MESH_ENABLED` 는 B4 hard gate 로 이미 OFF default — **코드 변경 0**. `test_mesh_adapter_excluded_without_env_flag` 회귀 게이트가 운영 경로 사고적 활성 차단 유지.
- `test_evaluate_4way_reprocess_vs_baseline` (synthetic placeholder, XFAIL/SKIP) + `test_axis_b_real_rtmw_integration` (skip skeleton) 는 현 상태 유지 — 본 문서가 "왜 보류인지" 의 single source.

## 5. 재개 조건 (재방문 시)

PRIMARY Gemini Vision 이 occlusion 을 충분히 못 잡는다는 실증이 나오거나, mesh-synthesis 경로를 다시 평가할 때:
1. 동일 RTMW 모델로 occluded 영상에 합성 유무 두 경로 생성.
2. ground-truth (또는 비-occluded 동일 동작) 대비 실 pose 정확도 비교 — confidence proxy 아님.
3. acceptance = RTMW+synthesis 가 RTMW-baseline 대비 실 개선 (calibration-source-hard-gate).
