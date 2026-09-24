---
quick_id: 260924-ig3
slug: window-constant
date: 2026-09-24
status: complete
---

# Quick 260924-ig3 — reference_relative seed 에 "유지 구간 상수" 경로 배선 (kip-up 수리 2단계)

> belle 09-24 *"응 진행해"*. 설계 정본 = `260924-i38-SUMMARY.md` §4. 코드 커밋 `1d9a41e9`(push).

## 0. 판정 (belle 에게)

**된다.** kip-up 실수가 **100 → 83**(왼어깨 33.9도, −16.6점, 억제 없음). 정타 5편은 **5/5 = 100 그대로**(차원 점수까지 동일).
다른 실수 3편은 내려갔다(climb 86→60 · peter-pan 80→60 · pdshape 87→80). **예외 1건**: power-spin 실수 73→**80**(↑7).
원인을 열어 보니 새 경로의 신뢰구간이 **관절이 창 안에서 움직이는 폭**을 측정오차로 읽어 어깨 감점 2건(26.4·23.9도)을 억제한 것이었다
(같은 이유로 peter-pan 무릎 33.8도, climb 팔꿈치 22.4도 억제). → 상수 경로는 **신뢰구간을 남기지 않는다**로 고쳤다(Gemini window 경로와 같은 규율:
추정량이 다르면 구간 없음 = 종전대로 감점). 저장된 감점 기록(wouldBePoints)으로 운영 산식을 그대로 다시 돌리면 power-spin 실수 **68**, 나머지 불변
`[확인: 산식]` — 이 수리는 Pod 재검증 전이다 `[미확인: Pod]`. 코드 커밋 `1d9a41e9`(배선) + 이 커밋(구간 제거).

## 1. 바뀐 코드 (`backend/functions/pipeline/app.py`, 테스트 `backend/tests/test_deduction_seed_window_constant.py`)
- 순수 헬퍼: `_reference_exec_window`(기준 doc clipRange → 기준 각도 프레임 창) · `_student_window_from_match`(운영 DTW 로 창 가장자리만 학생 축으로) ·
  `_window_constant_samples`(창 안 짝 없는 표본 = 학생 각도 − 기준 창 median) · `_abs_median_interval`(signed CI → |·| 구간).
- 빌더 `ref_exec_window=None` 인자: 관절 선택 순서 **pointed(window) > constant > DTW-fallback**. 값 = |학생 창 median − 기준 창 median|,
  순간 = 창 안 학생 median 최근접 프레임(동점만 신뢰도), measurement_error = 같은 표본 순서통계 CI, `seed_audit["constant_joints"]`.
  관절별 fail-closed(창·표본 부족·NaN → 그 관절만 DTW). 방출 규칙(expects_extension·붕괴 게이트)은 공통.
- 호출측 `_process`: `REFERENCE_CONSTANT_WINDOW_ENABLED`(default 1) → mode1 기준 doc 의 clipRange 로 창. 로그 `constant window reference=… window=…`.
- 무접촉: 허용 20 · slope 1.2 · record 문법 · 표시층 · Gemini window 경로 · mode3(clipRange 없음 → 종전).

## 2. 관측 — 오프라인 게이트
- 테스트: 신규 10 통과 · 기존 4603+417 통과(backend/.venv 직접).
- 실데이터 재현(빌더 직접 호출, 기준 rot180_v1): kip-up 실수 왼어깨 **20.6(DTW, 억제) → 34.0**(CI 24.4~38.3, n=55, 억제 안 걸림) · 정타 1.7 · 다른 GPU 판 33.9. i38 표(33.9)와 일치.
- 짝수 표본 부동소수 잔차(1e-14)가 정타에 "0 아닌 값"으로 방출되던 것을 잡았다 — 값은 두 median 의 차를 직접 쓴다.

## 3. 관측 — Pod 검증 (L4 `eqmfk0nwgaxset`, 서버 commit 1d9a41e9, 09-23 밤 판(L4)과 비교)

경로 = 앱과 같은 경로(`intake_clips.py analyze` → upload-url → Firestore → S3 → SQS → Lambda → Pod). 10편 직렬, 편당 60~121초.
Pod 로그 `[확인]`: 10건 전부 `constant window reference=… window=(…)` + `angle_vs_reference seed … constant=5~8 fallback=0` — 창은 i38 표와 동일.
전문 = `score_compare_0923_vs_ig3.txt`(records/suppressed 원문) · `pairs_after_ig3.txt`(`--pairs` 출력).

| 동작 | 정타 09-23 → 오늘 | 실수 09-23 → 오늘 | 오늘 실수 records (measured, points) | 오늘 억제(wouldBe) |
|---|---|---|---|---|
| kip-up | 100 → 100 | **100 → 83** | ref:left_shoulder 33.9 −16.6 | 없음 |
| power-spin | 100 → 100 | 73 → **80** | leg_extension 140.9 −20 | ref:left_shoulder 26.4 −7.7 · right_shoulder 23.9 −4.7 |
| climb | 100 → 100 | 86 → 60 | right_hip 40.3 / left_knee 36.8 / right_knee 37.9 각 −20 | right_elbow 22.4 −2.8 |
| peter-pan | 100 → 100 | 80 → 60 | left_shoulder 39.2 −20 · right_elbow 38.7 −20 | right_knee 33.8 −16.6 |
| pdshape | 100 → 100 | 87 → 80 | left_elbow 43.7 −20 | 없음 |

- 정타 5편의 dims(angle/line/stability)와 records 는 09-23 과 **동일** — 이 경로는 정타에 아무것도 안 냈다.
- 60 = 관절당 −20 캡 × 2~3 + 실행 합산 캡 −40 → 바닥 60(IPSF 캡, 0점 뭉침 방지). 실수 크기 차이가 60 에서 뭉친다 `[관측]`.
- 억제 해제(구간 제거) 산식 재계산: kip-up 83 · power-spin **68** · climb 60 · peter-pan 60 · pdshape 80 (저장 final 5/5 재현 뒤 wouldBePoints 합산, `_two_track_final` 산식).

## 4. 진단 / 미확인

- `[확인]` 상수 경로의 순서통계 구간은 측정 잡음이 아니라 관절의 움직임 폭이었다(합성 테스트에서도 ±25 사인이 그대로 구간이 됐다). i38 의 판 간 잡음 ≤5도가 이 추정량의 실측 잡음이고 허용 20 이 그 몫을 한다 → 구간 제거.
- `[미확인: Pod]` 구간 제거 판의 Pod 재검증은 안 했다. 효과는 억제 record 의 wouldBePoints 합산뿐이라 산식으로 닫았다. 다음 Pod 기동 때(belle 영상 절차) 같은 10편을 한 번 더 돌리면 닫힌다.
- `[관측]` kip-up 실수의 확대 카드가 이제 왼어깨 record 로 생긴다 — 순간 = 창 안 학생 median 최근접 프레임. 카드 사진이 맞는 순간인지는 belle 눈(`kipup_fault_zoom_card_ig3.png`).
- `[미확인]` power-spin 정타 왼팔꿈치 −10 / 오른무릎 −16, peter-pan 정타 왼어깨 +13(i38, 판 간 불변) — 허용 안이지만 여유가 4~10도뿐인 관절이 있다. 정타 테이크가 기준과 실제로 다른 자세인지, 창 가장자리 문제인지.
- `[관측]` 4동작에서 상수가 DTW 편차보다 크게 나와 캡에 닿는다 — "실수의 크기"는 60 바닥에서 안 갈린다. 표시층·캡은 무접촉(belle 원칙), 판단은 belle.

## 5. 인프라·비용

- Pod: L4 `eqmfk0nwgaxset` (SECURE, 볼륨 a5z753defc) 04:27~04:50 UTC ≈ 23분, **$0.16**. 잔액 $22.90 → **$22.74**. `pod_teardown.py eqmfk0nwgaxset` 로 종료 + Lambda/SSM 자리표시자 + pod-expected=down `[확인]`.
- ★ssh 기동은 `RUNPOD_POD_ID` 가 없어 주소 자동 동기가 **SKIP** 됐다 → Pod 에서 sync 블록을 직접 실행해 맞췄다(메모리 갱신: ssh 기동은 `export RUNPOD_POD_ID=<id>` 먼저).
- 다운로드는 가속 엔드포인트로 3.6초(55MB). 기동~health 100초(부트스트랩 포함 약 5분).
- 새 Firestore doc 10건(오늘 uid/analysisId 는 `backend/training/data/analysis_runs.jsonl` 에 추가). 사람 영상은 manifest 밖(규율 유지).
