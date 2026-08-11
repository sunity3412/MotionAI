# 사전 박제 — 로컬 검증 실행 전 내 판정 (frames-before-numbers 규율)

기록 시각: 2026-08-11 (verify_local --check 실행 전, 카드 PNG 미생성·미열람 상태)

## 예측 (fresh doc p34fresh1786363530, 5 record)

| record | 축 | freeze (예상 src) | 예측 판정 | 근거 |
|---|---|---|---|---|
| r00 | left_elbow | 5.30s (align 계열) | **상속 생존** — 카드 5.30s 근방, attribution=pole_proximity 성립 여부는 pair 폴거리 실측에 달림 (approved r00 poleDiff 0.19 ≥ 0.15 였으므로 성립 예상) | ii0 fresh: hold PASS 59(경계) + eye bent 일치 0.95 |
| r01 | right_elbow | 6.10s | 상속 FAIL (hold 112) → 재정박 — 후보 유무 미지 (정답표 무구속) | ii0 fresh hold FAIL |
| r02 | right_shoulder | 13.80s | 상속 FAIL (hold 98) → 재정박 — 후보 유무 미지 | ii0 fresh hold FAIL |
| r03 | left_hip | **align-peak ~16.7s** (probe 실측) | **카드 미방출** — 각도-주장 record 라 peak 비구속 대상 아님 → 게이트 FAIL (16.7s 는 스핀 이탈 국면, pose 원거리 예상) → 재정박 0 후보 (홀드 순간에 힙 편차≥20 성립 짝 없음 예상, 있어도 eye 가 차단 예상) | 정답표: belle "결함 부분이 아니야" + ii0 이중 기각 |
| r04 | left_knee | 10.50s | 상속 FAIL (hold 221) → **재정박 성립** — 포즈거리 최소 후보는 u≈3.667s/r≈2.4s 계열 (d=0.224, k=12) 예상. 다른 홀드 짝이면 양 패널 육안 국면 대조로 판정 | ii0 r03inherit 전건 PASS + 육안 동일 국면 박제 |

## 승인 무회귀 예측

- joint-scope 9/9 생존 (ii0 최종 임계 이식 등가성 — 수치까지 SWEEP 표와 일치해야 함)
- align-peak 3건 (elbow r02 / kipup r00 / powerspin r00) 비구속 — 게이트 미적용 정보 행

## 미지 항목 (정직 박제)

- r01/r02 재정박 후보 존재 여부 — ii0 가 탐색하지 않은 축. 어느 쪽이든 정답표 위반 아님.
- 로컬 align 재구성(P35 트랙 리플레이)은 Pod 실분석 align 과 반올림 오차(kp 4자리/score 3자리)
  수준의 차이가 있을 수 있음 — freeze 초는 소수 둘째 자리까지 일치 예상, 최종 판정은 Task 3 Pod.
- left_elbow attribution: pair 폴거리 차가 0.15 미만으로 나오면 미부착 — 그 경우 정답표
  3항(귀속 확인) 미달로 박제하고 원인(폴거리 실측값)을 기록한다 (임계 조정 금지).
