---
quick_id: 260923-sqt
slug: seed-ref-window
date: 2026-09-23
status: complete
---

# Quick 260923-sqt — 감점 재료가 기준의 엉뚱한 구간과 비교되던 결함 수리

## 판정

**고쳤다.** 학생 영상이 기준 영상보다 1.2~1.5배 길 때, 감점 계산이 정은지 기준 영상의
엉뚱한 구간과 비교되고 있었다. 완벽한 수행에 감점이 붙고, 진짜 결함은 줄어들거나 부풀었다.
지금까지의 측정(정은지 fixture)은 전부 이 길이대 밖이라 **한 번도 안 걸렸다** — 학생 영상에서
처음 터질 결함이었다.

## 관측

### 1. 코드 사실 `[확인]`

| 자리 | 기준 배열 |
|---|---|
| 점수 경로 `_deviation_against` (`app.py:7044`) | `a_ref[ref_start:ref_end]` 로 자름 ✓ |
| 표시 `_angles_to_dtw_median_dicts` (`app.py:2055`) | 자름 ✓ |
| segment 채점 (`app.py:8494-8501`) | 자름 ✓ |
| **감점 builder DTW fallback** (`app.py:3058` 부근) | **전체 배열 그대로** ✗ — 이번 수리 |

`MotionMatch.path` 의 기준 인덱스는 window-local 이다(`motiondtw.py:130-136`).
33-M3-SPEC 이 이 계약을 도입할 때 builder 만 빠졌고, 기존 builder 테스트는 전부 `ref_start=0` 이었다.

### 2. 운영 기록 11건 — 전부 이 결함 밖 `[확인]`

2026-09-22 gnj 런 11건(지난 세션 대화 기록에서 doc id 복원)을 운영 함수로 재계산:
**11/11 이 기준 창 `[0, nr)`** — 학생 프레임/기준 프레임 = 0.52~0.77(자르기 문턱 0.80 미만).
이때는 수리 전후 byte-동일이다. 저장된 감점 measuredValue 4건(power-spin 31.88 · climb 22.57/26.95 ·
peter-pan 32.68 · pdshape 31.13)이 재계산과 소수 첫째 자리까지 일치 = 재계산이 운영과 같은 경로.
→ **과거 저장 점수는 이 수리로 바뀌지 않는다.**

### 3. 재현 — 운영 함수 + 실제 기준 doc `[확인]`

학생 = 정은지 기준 영상 자신의 뒷부분(앞 15% 절단). 같은 영상이라 올바르면 편차 0.
운영과 같은 호출 순서(`_deviation_against` → 전체 `a_ref` → builder → `deduction_engine.tally`):

| 기준 | 기준 창 | 점수 경로 편차 | 수리 전 감점 seed 최대 | 수리 전 최종 | 수리 후 최종 |
|---|---|---|---|---|---|
| kip-up | [17,118) | 0.0도 | 29.3도 | **89** | 100 |
| power-spin | [23,159) | 0.0도 | 32.6도 | **85** | 100 |
| climb | [18,120) | 0.0도 | 29.5도 | **84** | 100 |

합성 테스트에서는 **반대 방향도** 나왔다 — 진짜 25도 차이가 19.7도로 읽혀(허용오차 20도 아래)
감점이 사라지는 경우(cut=8). 즉 위양성·위음성 둘 다 만든다.

재현 스크립트: `repro_real_reference.py` · 운영 11건 대조: `check_stored_runs.py` (이 디렉터리).

### 4. 영향 길이대 `[확인: 산식]` / 실제 빈도 `[미확인]`

학생 분석 ~10fps(30fps 촬영 기준, kip-up 정타 실측 79프레임/7.9초) · 기준 ~15fps(`anglesRealFps`).
창이 미끄러지는 조건 = 학생/기준 프레임 0.80~1.00 = **학생 영상 길이가 기준의 1.2~1.5배.**
```
kip-up 9.4~11.8초 · climb 9.6~12.0초 · peter-pan 10.4~13.0초 · power-spin 12.7~15.9초
pdshape 19.0~23.7초 · invert 20.8~26.0초 · sideway-spin 23.8~29.8초 · elbow-twist 26.3~32.9초
foxtop 34.1~42.6초 · foxtop-split 38.8~48.5초 · combo 74.5~93.1초
```
이 안에서도 DTW 창이 모호하면 전체 기준으로 떨어져(fail-closed) 결함이 안 걸린다.
**학생 영상이 아직 0편이라 실제로 몇 %가 걸리는지는 모른다.** 수강생이 촬영 앞뒤를 안 자르고
올리면 이 길이대가 흔할 수 있다 — 추정이다.

## 수리

`_build_deduction_measured_deviations` 안에서 `reference_angles[ref_start:ref_end]` 로 한 번 잘라
`per_joint_deviation` · `per_joint_median_ci` · `per_joint_representative_frames` 세 호출에 쓴다.
- 채점 산식 · 허용오차 20도 · 도당 1.2점 · 상한 · 측정오차 억제 규칙 **무접촉**.
- `per_joint_deviation` 본체(SHA-256 핀) 무접촉.
- 창이 기준 전체면 byte-동일. mode3 기준 축(플래그 OFF)도 같은 builder 라 함께 고쳐진다.

## 검증

- 새 테스트 `backend/tests/test_deduction_seed_ref_window.py` 3건: **수정 전 3 failed → 수정 후 통과.**
  수정 전 실패 메시지가 결함 그대로다 — "완벽한 수행에 감점 재료가 생겼다: 8관절 15~49도".
- 전체 게이트 **4992 passed / 20 skipped / 0 failed** (backend/.venv 직접 실행, 56초).
  직전 기록 4989 + 새 테스트 3.
- 실제 기준 doc 재현: 수리 후 세 동작 모두 100 / 감점 0 / 억제 0.

## 배포

RunPod 서버는 기동 때 origin/main 을 당긴다 — **push 해야 다음 Pod 부터 적용된다.**
Lambda 쪽 사본은 분석에 안 쓰인다(CPU 폴백은 배포에서 막혀 있다).

## 안 한 것

- 과거 저장 분석 재채점 없음(11/11 이 영향 밖).
- 허용오차·감점 기울기 변경 없음. m49 §1 "죽은 축" 규율 그대로.
- 창이 미끄러지는 조건 자체(`COVERAGE_FLOOR=0.80`, 10fps vs 15fps 비대칭)는 건드리지 않았다.
  그 설계가 맞는지는 별개 질문이다.
