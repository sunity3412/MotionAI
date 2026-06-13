---
spike: 002d
name: rtmw-mirror-baseline
type: comparison
validates: "Given 현 운영 stack (RTMW + 좌우 mirror + temporal.py), when 정은지 영상 시뮬 baseline 평가, then occlusion-prone phase 의 IPSF 추정 감점 baseline 박제"
verdict: VALIDATED-BASELINE
related: [001, 002a, 002b, 002c]
tags: [baseline, rtmw, mirror, operational-stack, ipsf-penalty]
---

# Spike 002d: RTMW Mirror Baseline

## What This Validates

**Given** 현 운영 stack (RTMW 133 wholebody + 좌우 mirror + temporal.py confidence 가중 보간),
**when** 정은지 je-04 (페어 스핀) 시뮬 + Spike 001 eval harness 호출,
**then** spin phase 의 occlusion baseline (frame rate + IPSF 추정 감점) 박제.

## Results

### Verdict: **VALIDATED-BASELINE ✓**

**핵심 정량화:**
- **Spin phase (frame 20~40) hip/knee occlusion: 73.8%**
- Wrist occlusion (frame 10~25): 56.7%
- Overall confidence < 0.3 frame rate: 7.5%
- **IPSF Page 10/94/106 추정 감점 = -7.60 pts/video**

**Impact:** 002b cylindrical mesh virtual render 가 이 occlusion 을 보완하면 절감 가능한 IPSF 감점 = **7.60 pts**. belle 의 "분석 99% 정확도" 정합 검증의 baseline.

### Carry-forward
- Spike 001 PathOutput 형식 재사용 검증 ✓ (eval harness 호환)
- 002b + 002d 2-way 비교 시 axis_b reduction_pct = (7.5% - 002b 결과) / 7.5% × 100
- RunPod 실 4-way 비교 task 박제 = `evaluate_4way({rtmw_mirror: baseline, cylindrical_mesh: 002b_output, gemini_vision: 003_output})`

## Files

- `run_spike.py` — baseline 시뮬 + Spike 001 eval harness 호출
- `spike_report.json` — baseline 정량화 박제
