# Phase 6 — Pod Sweep Validation (deferred from Plan 06-03)

> C6 fix (2026-06-08 reviews MEDIUM) — deferred but tracked. 본 문서는 사양만.
> 실 실행은 별도 (belle 의 운영 sweep 일정에 따라).

## 목적

NotebookLM §1.4 의 "PA-MPJPE 가 raw MPJPE 대비 60% 감소" 주장을 belle Pod 실
영상으로 검증. Phase 6 의 normalization (체형 보정) 이 production 점수에 실제로
의미 있는 reduction 을 만드는지 정량 확인.

## 입력

- 5 reference videos (정은지) — Plan 06-03 Task 5 에서 백필한 5 motion 의 원본
  영상 (두 필드 모두 백필 완료 상태). bucket: `s3://sunity-motion-pilot-videos/reference/{motionId}.mp4`.
- 5 student videos — belle 또는 학원 수강생 (다양한 체형 — 키 140cm~170cm,
  팔/다리 비율 다양). belle 이 별도 수집/촬영.

## 실행 단계

1. Pod SSH + git pull (latest Plan 06-02 wiring 반영)
2. 10 videos 모두 S3 업로드 (reference 5 + student 5)
3. `_process` 를 normalization ON (Phase 6 wiring) 으로 5 × 5 = 25 조합 분석
4. `_process` 를 normalization OFF 강제 (compare_body_profiles 의
   `reference_profile=None` + `source_keypoints=None` 강제) 로 동일 25 조합 분석
5. 각 조합의 `BodyComparisonReport.findings[].deductionScore` 합산 추출

## 출력 — Reduction % Table

| Student    | Reference        | normalization OFF (총 deduction) | normalization ON (총 deduction) | Reduction % |
| ---------- | ---------------- | -------------------------------- | -------------------------------- | ----------- |
| S1 (140cm) | ref-climb        | x                                | y                                | (1 - y/x) × 100 |
| S1 (140cm) | ref-foxtop       | ...                              | ...                              | ...         |
| S1 (140cm) | ref-foxtop-split | ...                              | ...                              | ...         |
| S1 (140cm) | ref-invert       | ...                              | ...                              | ...         |
| S1 (140cm) | ref-sideway-spin | ...                              | ...                              | ...         |
| S2 ...     | ...              | ...                              | ...                              | ...         |
| ...        | ...              | ...                              | ...                              | ...         |

평균 reduction % 산출 (25 조합).

## 검증 기준

- 평균 reduction >= 50% → NotebookLM §1.4 60% 주장 검증 (10% 허용 오차 내) — PASS
- 평균 reduction 30% ~ 50% → partial validation. NotebookLM 주장의 일부 회복.
- 평균 reduction < 30% → 원인 분석 (foreshortening 비율, RTMW confidence 분포,
  reference 측 source_pose confidence 분포, fixture 의 합성 vs 실 영상 차이)
- **R9 정합 카피**: deduction 합산은 5 IPSF deficits + Sunity pose_reliability_low
  (poor_transitions 제외 — Phase 8 jerk/jitter 와 통합 deferred). '7 deficits'
  옛 표현 금지.
- 결과는 `.planning/phases/06-coaching/06-03-POD-SWEEP-RESULTS.md` 에 박제 (별도
  commit). raw deductionScore + per-deficit breakdown + Reduction %.

## 실행 시점

- belle 의 운영 sweep 일정에 따라.
- 우선순위: Phase 6 → Phase 7 진입 전 권장. Phase 7 이 본 sweep 결과를 hard-block
  하지는 않음 — observational.
- 관련 메모리: [[feedback-analysis-first]], [[mvp-simple-pilot-quality]].

## 본 Plan 06-03 에서 본 Task 의 의미

본 Task 는 **사양만 박제**. 실 실행 deferred. Plan 06-03 의 Task 5 (수동
checkpoint) 가 완료되면 Plan 06-03 은 closed; 본 Task 6 은 백로그로 tracked.

## 관련 메모리

- [[feedback-analysis-first]] — 분석 정확도가 최우선. sweep 결과가 검증의 1차
  근거.
- [[mvp-simple-pilot-quality]] — 시연 화면 최소 요건과 별개로, 분석 품질의
  정량 게이트.
- [[runpod-gpu-env]] — Pod 환경 + 함정 박제.
