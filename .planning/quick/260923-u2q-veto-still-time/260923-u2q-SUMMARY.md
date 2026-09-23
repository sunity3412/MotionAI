---
quick_id: 260923-u2q
slug: veto-still-time
date: 2026-09-23
status: complete
---

# Quick 260923-u2q — Gemini 에 보내는 정은지 still 이 다른 순간이던 결함 수리

## 판정

**고쳤다 — 코드·실영상 대조까지. Pod(Gemini) 재분석은 아직이다.**
Mode 1 에서 Gemini 에게 [학생 still | 정은지 still] 한 쌍을 보여주는데, 정은지 쪽이 **다른 순간**
이었다. 학생 영상만의 문제가 아니라 **모든 Mode 1 분석**에서다. 수리 후 실제 kip-up 영상으로
10번 중 9번 같은 순간(나머지 1번은 끝 장면 1프레임 차이).

## 관측

### 1. 코드 사실 `[확인]`
- 기준 쪽 인덱스 공간이 둘이다: 기준 **각도**(기준 doc, ~15fps — kip-up 118행/7.9초)와 veto 가
  새로 뽑는 기준 **영상 프레임**(9fps 목표 → 실효 10fps — 79장).
- `fault_zoom._matched_ref_frame` 은 각도 공간 번호를 준다. 그 독스트링이 이미 "호출측이
  9fps frames 로 변환할 책임 — 그대로 넣으면 시간 2배 오독"이라 경고한다.
- 확대 카드 경로는 **28-05(2026-07-08)** 에 그 변환을 넣었다(`_to_rep_idx`).
  veto still 경로 `_build_selected_frame_pair`(**23-01, 2026-06-23**)는 변환 없이 영상 프레임
  배열에 그대로 꽂았고, 영상 프레임 수로 clamp 했다. 같은 결함을 한 곳만 고친 모양 —
  오늘 오전 감점 seed(quick-260923-sqt)와 같다.
- 번호 하나(`ref_frame_idx`)를 소비처 셋이 서로 다른 공간으로 읽는다:
  Gemini still 이미지 = 영상 프레임 공간 · 정량화(window median) = 각도 공간 ·
  확대 카드 stage-1 override(`sourceFrameIndices`) = 영상 프레임 공간.
- 여기에 window-local 문제도 겹친다 — `_matched_ref_frame` 이 `ref_start` 를 안 더했다(sqt 와 같은 결함군).

### 2. 수리 전 실측 — 같은 테이크 픽셀 대조 `[확인]`
kip-up 정타 fixture 와 정은지 기준 사본은 **같은 테이크**다(학생 프레임 u 와 가장 닮은 기준 프레임이
10/10 전부 u — 픽셀차 0.3). 운영이 고른 기준 still:
```
학생 2.0초 → 정은지 3.0초 · 학생 4.4초 → 6.6초 · 학생 5.2초 이후 → 전부 마지막 프레임(7.8초)
같은 순간 0/10 (픽셀차 5.7~12.9)
```
정량화도 영상 프레임 수(79)로 clamp 돼 **후반 1/3 은 기준 각도 78행(5.2초)에 눌렸다.**

### 3. 운영 기록 `[확인: 저장 인덱스로 계산]`
2026-09-22 운영 11건 중 Gemini 판정이 실행된 실수 영상 4건의 정량화 창 기준 인덱스
(`visionVeto.windowMedianAngleDeltas.sourceFrameIndices.reference`) 중앙값과 그 번호로 뽑힌 still:
```
power-spin  학생 4.5초 ↔ 기준 각도 82(5.5초)  → Gemini 가 본 정은지 still 8.2초  (2.7초 어긋남)
pdshape     학생 7.2초 ↔ 기준 각도 95(6.4초)  → still 9.5초                     (3.1초)
peter-pan   학생 2.0초 ↔ 기준 각도 34(2.3초)  → still 3.4초                     (1.1초)
climb       학생 1.4초 ↔ 기준 각도 13(0.9초)  → still 1.3초                     (0.4초)
```
이 4건은 정량화 쪽 clamp 에는 안 걸렸다(기준 번호가 영상 프레임 수보다 작았다).

## 진단 — 승계 전 재검증 대상

- `[미확인]` **점수에 얼마나 영향이 있었나.** Gemini 는 두 영상 전체 + still 한 쌍을 같이 받는다.
  still 이 판정을 얼마나 좌우하는지는 모른다. 2026-07-05 기록은 "위상이 어긋난 still 쌍이면
  Gemini 가 '편차 없음'을 낸다(0/6 vs 6/6)"였다 — 그 당시 "맞은 쌍"도 이 결함이 있었을 수 있어
  그 기록 자체가 재검증 대상이다.
- `[미확인]` kip-up 실수 영상에 Gemini 가 "차이 거의 없음"을 낸 것과의 관계 — 가설일 뿐이다.

## 수리

| 자리 | 변경 |
|---|---|
| `fault_zoom._matched_ref_frame` | `ref_start` 를 더해 **전체** 기준 각도 인덱스로. 창이 [0,…)면 byte-동일 |
| `vision_veto.SelectedFramePair` | `ref_image_idx` 필드 추가(끝, 기본 None — 구 생성부 비파괴) |
| `app._build_selected_frame_pair` | 각도 길이·fps 를 받으면 두 공간을 가른다: 각도 공간으로 대응을 찾고(clamp 도 각도 길이), still 이미지는 `_to_rep_idx`(28-05 와 같은 식)로 같은 시각 영상 프레임. 못 받으면 종전 동작 |
| `app._collect_vision_fault_context` | 기준 각도 길이 산출 + `reference_angles_fps` 전달. **Gemini 캐시 키(still_frame_indices)는 보낸 이미지 번호** — 각도 번호로 두면 이미지가 바뀌어도 키가 같아 어긋난 still 의 예전 판정이 캐시에서 되살아난다 |
| mode1 호출부 | `reference_angles_fps=reference_kp_fps` (점수 경로와 같은 값) |

채점 산식·허용오차·감점 기울기 무접촉. 확대 카드 표시 경로 무접촉(아래).

## 검증

- 새 테스트 8건(수정 전 8 failed): 합성 영상(프레임 i 의 red = i)으로 "기준 still 이 학생과 같은 시각의
  프레임인가" · 정량화 번호가 각도 공간인가 · 창 오프셋 가산 · 캐시 키가 이미지 번호인가.
- 실영상·실추출기 대조(`verify_after.py`): 수리 후 같은 순간 **9/10**(픽셀차 0.3), 수리 전 0/10.
- 전체 게이트 **5007 passed / 20 skipped / 0 failed** (backend/.venv 직접). 직전 4999 + 8.

## 안 한 것 / 범위 밖

- **확대 카드 stage-1 override**(`sourceFrameIndices.reference` 를 9fps 영상 프레임으로 읽음)도 같은
  공간 혼용이다. 그러나 앱에 나가는 확정 카드는 비교 영상 정지 순간을 상속하는 게이트 경로라
  ([[zoom-compare-canonical-do-not-reinvestigate]], belle 5차 승인 문법) 이번에 건드리지 않았다.
  `[미확인]` stage-1 카드가 최종 화면에 남는 경우가 있는지.
- **Pod 재분석 안 함** — Gemini 판정·점수가 실제로 얼마나 바뀌는지는 Pod 에서 fixture 를 다시 돌려야 안다.
  비교 기준 = 2026-09-22 운영 11건(`analysis_runs.jsonl`). 방법 = 다음 Pod 에서
  `intake_clips.py analyze --hash <fixture 해시들>` 후 `measure_reference_axis.py --pairs`.
