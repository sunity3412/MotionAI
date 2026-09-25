# 평가셋 분리 점검 (TRAINING-DUE 게이트 4)

점검 2026-09-25T12:14:19+00:00 · 학습 후보(증류 대상) 546행

- 평가 영상(봉인 시험지 + 짝): 4편 · 평가 그룹(인물·세션): [('sub_je', '2026-06-17')] · 평가 인물: ['sub_je']
- 평가 그룹에 속한 클립: 12편

| 누수 | 건수 | 뜻 |
|---|---|---|
| L1 같은 파일 | 6 | 평가 영상 그 자체가 학습 후보 — **오류** |
| L2 같은 세션 | 0 | 평가 인물·같은 촬영 세션의 다른 클립이 학습 후보 — **오류** |
| L3 같은 인물 | 11 | 평가 인물의 다른 세션(내부 촬영·reference) — 경고 |

L1_same_file:
- fixtures/phase15/climb/fault.mp4
- fixtures/phase15/elbow-twist-sister/fault.mp4
- fixtures/phase15/kip-up/fault.mp4
- fixtures/phase15/pdshape/fault.mp4
- fixtures/phase15/peter-pan/fault.mp4
- fixtures/phase15/power-spin/fault.mp4

L3_same_subject:
- reference/ref-climb.mp4
- reference/ref-combo.mp4
- reference/ref-elbow-twist-sister.mp4
- reference/ref-foxtop.mp4
- reference/ref-foxtop-split.mp4
- reference/ref-invert.mp4
- reference/ref-kip-up.mp4
- reference/ref-pdshape.mp4
- reference/ref-peter-pan.mp4
- reference/ref-power-spin.mp4
- reference/ref-sideway-spin.mp4

**인물 분리 불가** — 평가 인물이 1명뿐이다(정은지). 다른 사람의 봉인 시험지가 생겨야 게이트 4 가 켜진다. 그 전까지 세션 분리(L1·L2 = 0)만 지킨다.

판정: **누수 — 학습 전에 `--mark-holdout` 또는 manifest 수정**
