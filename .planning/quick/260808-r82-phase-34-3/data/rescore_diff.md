# Phase 34 수술 ② 재채점 회계 표 (quick-260808-r82)

측정창 ref-경계 마진 제외(REF_BOUNDARY_EXCLUDE_S=0.5s) 전/후의 관절별
DTW-median 편차와 대표 프레임(측정 순간) 이동. `over` = max(0, dev-20°)
(tol 20° 초과분 — 감점으로 흐르는 성분의 환산 표시, 산식 무접촉).

## elbow (ref=ref-elbow-twist-sister, ref_fps=18.0)

- n_path=330 margin=9f n_excluded=18 n_used=312 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 19.31 | 19.31 | 0.00 | 0.00 | 0.00 | 47 -> 47 | 5.22 -> 5.22 |
| right_elbow | 28.91 | 28.60 | -0.31 | 8.91 | 8.60 | 100 -> 137 <- 이동 | 11.11 -> 15.22 |
| left_shoulder | 20.56 | 20.72 | 0.16 | 0.56 | 0.72 | 23 -> 23 | 2.56 -> 2.56 |
| right_shoulder | 28.30 | 27.98 | -0.32 | 8.30 | 7.98 | 67 -> 26 <- 이동 | 7.44 -> 2.89 |
| left_hip | 22.18 | 22.31 | 0.13 | 2.18 | 2.31 | 27 -> 27 | 3.00 -> 3.00 |
| right_hip | 17.05 | 17.42 | 0.38 | 0.00 | 0.00 | 22 -> 27 <- 이동 | 2.44 -> 3.00 |
| left_knee | 22.18 | 22.18 | 0.00 | 2.18 | 2.18 | 97 -> 97 | 10.78 -> 10.78 |
| right_knee | 23.66 | 25.10 | 1.44 | 3.66 | 5.10 | 65 -> 46 <- 이동 | 7.22 -> 5.11 |

기존 doc records (대조용):
- r00:angle_vs_reference__right_elbow atVideoSec=11.11111111111111
- r01:angle_vs_reference__right_shoulder atVideoSec=7.444444444444445
- r02:angle_vs_reference__left_hip atVideoSec=4.888888888888889
- r03:angle_vs_reference__right_knee atVideoSec=10.11111111111111

## powerspin (ref=ref-power-spin, ref_fps=18.0)

- n_path=161 margin=9f n_excluded=20 n_used=141 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 18.79 | 17.85 | -0.95 | 0.00 | 0.00 | 30 -> 55 <- 이동 | 3.33 -> 6.11 |
| right_elbow | 15.83 | 16.65 | 0.83 | 0.00 | 0.00 | 30 -> 30 | 3.33 -> 3.33 |
| left_shoulder | 29.05 | 25.48 | -3.56 | 9.05 | 5.48 | 29 -> 30 <- 이동 | 3.22 -> 3.33 |
| right_shoulder | 18.04 | 17.51 | -0.53 | 0.00 | 0.00 | 80 -> 40 <- 이동 | 8.89 -> 4.44 |
| left_hip | 22.50 | 22.99 | 0.49 | 2.50 | 2.99 | 6 -> 6 | 0.67 -> 0.67 |
| right_hip | 21.57 | 20.04 | -1.53 | 1.57 | 0.04 | 11 -> 15 <- 이동 | 1.22 -> 1.67 |
| left_knee | 19.47 | 19.47 | 0.00 | 0.00 | 0.00 | 23 -> 23 | 2.56 -> 2.56 |
| right_knee | 27.74 | 30.84 | 3.10 | 7.74 | 10.84 | 7 -> 43 <- 이동 | 0.78 -> 4.78 |

기존 doc records (대조용):
- r00:leg_extension atVideoSec=3.3333333333333335
- r01:split_angle atVideoSec=None
- r02:angle_vs_reference__left_shoulder atVideoSec=3.2222222222222223

## kipup (ref=ref-kip-up, ref_fps=18.0)

- n_path=118 margin=9f n_excluded=18 n_used=100 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 15.96 | 14.78 | -1.19 | 0.00 | 0.00 | 43 -> 6 <- 이동 | 4.78 -> 0.67 |
| right_elbow | 2.64 | 2.51 | -0.14 | 0.00 | 0.00 | 33 -> 39 <- 이동 | 3.67 -> 4.33 |
| left_shoulder | 18.98 | 20.09 | 1.10 | 0.00 | 0.09 | 0 -> 31 <- 이동 | 0.00 -> 3.44 |
| right_shoulder | 13.83 | 12.29 | -1.55 | 0.00 | 0.00 | 13 -> 40 <- 이동 | 1.44 -> 4.44 |
| left_hip | 7.81 | 7.99 | 0.18 | 0.00 | 0.00 | 25 -> 25 | 2.78 -> 2.78 |
| right_hip | 7.58 | 9.66 | 2.08 | 0.00 | 0.00 | 28 -> 18 <- 이동 | 3.11 -> 2.00 |
| left_knee | 1.87 | 1.64 | -0.24 | 0.00 | 0.00 | 1 -> 23 <- 이동 | 0.11 -> 2.56 |
| right_knee | 1.93 | 1.72 | -0.21 | 0.00 | 0.00 | 7 -> 9 <- 이동 | 0.78 -> 1.00 |

기존 doc records (대조용):
- r00:split_angle atVideoSec=None

## pdshapefault (ref=ref-pdshape, ref_fps=18.0)

- n_path=251 margin=9f n_excluded=29 n_used=222 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 32.72 | 32.49 | -0.23 | 12.72 | 12.49 | 77 -> 112 <- 이동 | 8.56 -> 12.44 |
| right_elbow | 24.32 | 23.75 | -0.57 | 4.32 | 3.75 | 11 -> 86 <- 이동 | 1.22 -> 9.56 |
| left_shoulder | 26.79 | 26.98 | 0.18 | 6.79 | 6.98 | 29 -> 106 <- 이동 | 3.22 -> 11.78 |
| right_shoulder | 21.97 | 23.95 | 1.98 | 1.97 | 3.95 | 54 -> 94 <- 이동 | 6.00 -> 10.44 |
| left_hip | 21.84 | 21.65 | -0.19 | 1.84 | 1.65 | 64 -> 40 <- 이동 | 7.11 -> 4.44 |
| right_hip | 21.71 | 24.18 | 2.47 | 1.71 | 4.18 | 106 -> 14 <- 이동 | 11.78 -> 1.56 |
| left_knee | 27.57 | 26.87 | -0.70 | 7.57 | 6.87 | 33 -> 46 <- 이동 | 3.67 -> 5.11 |
| right_knee | 22.49 | 22.62 | 0.13 | 2.49 | 2.62 | 116 -> 37 <- 이동 | 12.89 -> 4.11 |

기존 doc records (대조용):
- r00:angle_vs_reference__left_elbow atVideoSec=8.555555555555555
- r01:angle_vs_reference__right_elbow atVideoSec=1.2222222222222223
- r02:angle_vs_reference__left_shoulder atVideoSec=3.2222222222222223
- r03:angle_vs_reference__left_knee atVideoSec=3.6666666666666665

## peterpan (ref=ref-peter-pan, ref_fps=18.0)

- n_path=130 margin=9f n_excluded=18 n_used=112 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 5.18 | 5.00 | -0.18 | 0.00 | 0.00 | 51 -> 23 <- 이동 | 5.67 -> 2.56 |
| right_elbow | 23.25 | 17.41 | -5.84 | 3.25 | 0.00 | 5 -> 33 <- 이동 | 0.56 -> 3.67 |
| left_shoulder | 33.90 | 36.97 | 3.07 | 13.90 | 16.97 | 58 -> 34 <- 이동 | 6.44 -> 3.78 |
| right_shoulder | 10.70 | 9.70 | -1.00 | 0.00 | 0.00 | 0 -> 6 <- 이동 | 0.00 -> 0.67 |
| left_hip | 10.36 | 12.14 | 1.77 | 0.00 | 0.00 | 23 -> 6 <- 이동 | 2.56 -> 0.67 |
| right_hip | 20.42 | 20.42 | 0.00 | 0.42 | 0.42 | 4 -> 4 | 0.44 -> 0.44 |
| left_knee | 2.01 | 1.86 | -0.15 | 0.00 | 0.00 | 15 -> 48 <- 이동 | 1.67 -> 5.33 |
| right_knee | 16.90 | 16.93 | 0.03 | 0.00 | 0.00 | 0 -> 50 <- 이동 | 0.00 -> 5.56 |

기존 doc records (대조용):
- r00:angle_vs_reference__left_shoulder atVideoSec=6.444444444444445

## pdshape (ref=ref-pdshape, ref_fps=18.0)

- n_path=237 margin=9f n_excluded=18 n_used=219 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 9.11 | 8.74 | -0.36 | 0.00 | 0.00 | 98 -> 8 <- 이동 | 10.89 -> 0.89 |
| right_elbow | 20.01 | 20.68 | 0.66 | 0.01 | 0.68 | 3 -> 45 <- 이동 | 0.33 -> 5.00 |
| left_shoulder | 12.90 | 12.90 | 0.00 | 0.00 | 0.00 | 75 -> 75 | 8.33 -> 8.33 |
| right_shoulder | 14.24 | 15.57 | 1.33 | 0.00 | 0.00 | 53 -> 72 <- 이동 | 5.89 -> 8.00 |
| left_hip | 16.26 | 17.66 | 1.40 | 0.00 | 0.00 | 154 -> 110 <- 이동 | 17.11 -> 12.22 |
| right_hip | 12.98 | 13.47 | 0.49 | 0.00 | 0.00 | 137 -> 140 <- 이동 | 15.22 -> 15.56 |
| left_knee | 16.85 | 17.97 | 1.12 | 0.00 | 0.00 | 62 -> 134 <- 이동 | 6.89 -> 14.89 |
| right_knee | 16.98 | 18.70 | 1.72 | 0.00 | 0.00 | 84 -> 98 <- 이동 | 9.33 -> 10.89 |

## realupload (ref=ref-power-spin, ref_fps=18.0)

- n_path=161 margin=9f n_excluded=20 n_used=141 fail_open=False

| joint | dev_before | dev_after | delta | over_before | over_after | rep_frame before -> after | rep_sec before -> after |
|---|---|---|---|---|---|---|---|
| left_elbow | 18.79 | 17.85 | -0.95 | 0.00 | 0.00 | 30 -> 55 <- 이동 | 3.33 -> 6.11 |
| right_elbow | 15.83 | 16.65 | 0.83 | 0.00 | 0.00 | 30 -> 30 | 3.33 -> 3.33 |
| left_shoulder | 29.05 | 25.48 | -3.56 | 9.05 | 5.48 | 29 -> 30 <- 이동 | 3.22 -> 3.33 |
| right_shoulder | 18.02 | 17.51 | -0.51 | 0.00 | 0.00 | 80 -> 40 <- 이동 | 8.89 -> 4.44 |
| left_hip | 22.44 | 22.93 | 0.49 | 2.44 | 2.93 | 6 -> 6 | 0.67 -> 0.67 |
| right_hip | 21.48 | 20.02 | -1.47 | 1.48 | 0.02 | 11 -> 15 <- 이동 | 1.22 -> 1.67 |
| left_knee | 19.15 | 19.15 | 0.00 | 0.00 | 0.00 | 13 -> 13 | 1.44 -> 1.44 |
| right_knee | 27.62 | 31.00 | 3.38 | 7.62 | 11.00 | 36 -> 6 <- 이동 | 4.00 -> 0.67 |

기존 doc records (대조용):
- r00:leg_extension atVideoSec=3.3333333333333335
- r01:split_angle atVideoSec=None
- r02:angle_vs_reference__left_shoulder atVideoSec=3.2222222222222223

---

회계 단위 주석: 이 표는 md(관절별 편차, DTW-fallback 경로 `angle_vs_reference__*` seed) 레벨의 1차 회계다. deduction_engine.tally 재실행(record/final 레벨)은 입력 재구성(profile/recognizer/vision 컨텍스트/quantification 전체)이 순수 계층 범위를 넘어 생략하고, 편차→over(tol 20° 초과분) 환산 열로 갈음했다. vision-pointed 관절의 window-median(wm) 경로는 이번 수술 무접촉이라 이 표의 delta 가 그 관절의 최종 record 에 그대로 반영되지 않을 수 있다.

## 불변식 1 전건 검사: PASS (after 대표 프레임 전건이 제외-전용 스텝 프레임 집합 밖)
