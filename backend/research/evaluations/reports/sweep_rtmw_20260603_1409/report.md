# RTMW vs IPSF 회귀 검증 보고서 (Plan 01-23)

생성 시각: 2026-06-03T14:09:44.124939+00:00

**phase1_ready_to_swap: False**  (Wave 3 plan 25 atomic swap 진입 게이트)

## 요약
| 항목 | 값 |
| --- | --- |
| phase1_ready_to_swap | False |
| 전체 모션 수 | 5 |
| IPSF within_tolerance PASS | 1/5 |
| line PASS | 3/5 |
| angle PASS | 0/5 |

## 모션별 결과
| 모션 | pole_axis (vec) | pole 신뢰도 | IPSF within_tolerance | line PASS | angle PASS | ms/frame | rtmw_mean_score | swap_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ref-climb | [0.000, 1.000, 0.000] | low | PASS | PASS | FAIL | 2201.4 | 95.4 | 0.5625 |
| ref-foxtop-split | [0.000, 1.000, 0.000] | low | FAIL | FAIL | FAIL | 2164.3 | 93.0 | 0.5402892561983471 |
| ref-foxtop | [0.000, 1.000, 0.000] | low | FAIL | FAIL | FAIL | 2082.7 | 93.3 | 0.5053003533568905 |
| ref-invert | [0.000, 1.000, 0.000] | low | FAIL | PASS | FAIL | 2116.3 | 93.6 | 0.5957446808510638 |
| ref-sideway-spin | [0.000, 1.000, 0.000] | low | FAIL | PASS | FAIL | 2008.9 | 94.8 | 0.4974704890387858 |

## IPSF 갭 상세

### ref-climb — IPSF angle criteria 없음 (MVP scope 외 카테고리)

### ref-foxtop-split
| joint | moment | target (°) | measured (°) | gap (°) | within_tolerance |
| --- | --- | --- | --- | --- | --- |
| left_shoulder | hold | 180.0 | 21.0 | 159.0 | False |
| right_shoulder | hold | 180.0 | 34.0 | 146.0 | False |
| left_hip | hold | 180.0 | 80.1 | 99.9 | False |
| right_hip | hold | 180.0 | 137.0 | 43.0 | False |
| left_knee | hold | 180.0 | 105.5 | 74.5 | False |
| right_knee | hold | 180.0 | 162.9 | 17.1 | True |

### ref-foxtop
| joint | moment | target (°) | measured (°) | gap (°) | within_tolerance |
| --- | --- | --- | --- | --- | --- |
| left_shoulder | hold | 180.0 | 107.9 | 72.1 | False |
| right_shoulder | hold | 180.0 | 76.7 | 103.3 | False |
| left_hip | hold | 180.0 | 74.6 | 105.4 | False |
| right_hip | hold | 180.0 | 88.8 | 91.2 | False |
| left_knee | hold | 180.0 | 170.0 | 10.0 | True |
| right_knee | hold | 180.0 | 154.3 | 25.7 | False |

### ref-invert
| joint | moment | target (°) | measured (°) | gap (°) | within_tolerance |
| --- | --- | --- | --- | --- | --- |
| left_shoulder | hold | 180.0 | 32.4 | 147.6 | False |
| right_shoulder | hold | 180.0 | 34.9 | 145.1 | False |
| left_hip | hold | 180.0 | 29.6 | 150.4 | False |
| right_hip | hold | 180.0 | 94.6 | 85.4 | False |
| right_knee | hold | 180.0 | 162.8 | 17.2 | True |

### ref-sideway-spin
| joint | moment | target (°) | measured (°) | gap (°) | within_tolerance |
| --- | --- | --- | --- | --- | --- |
| right_shoulder | hold | 180.0 | 137.3 | 42.7 | False |
| left_hip | hold | 180.0 | 137.2 | 42.8 | False |
| left_knee | hold | 180.0 | 174.7 | 5.3 | True |
