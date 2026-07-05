---
status: complete
---

# quick-260705-ftn — fault-zoom reference crop 정합 fix SUMMARY

> 원본 SUMMARY 는 worktree 정리 사고로 유실 — executor 최종 보고를 orchestrator 가 재작성 (2026-07-05).

## 배경

belle 실기기 (2026-07-05, kip-up fault 76점): 문제 부위 확대 비교 카드 2장 모두 "내 영상"쪽은 부위 확대인데 "정은지 선수"쪽이 전신 와이드샷. pod 재현으로 원인 2겹 확정: (1) 표시 프레임(측정 window median=37)에서 reference keypoint 전부 저신뢰 → relaxed 경로, (2) relaxed crop 이 floor(_CROP_FRAC)에도 _RELAXED_MARGIN 을 곱해 side 가 프레임 전폭(360)으로 클램프 → 전신처럼 보임.

## 변경 (TDD, 커밋 4개 — rebase 후 f3c4db4/68daf41/278438b/74689eb)

1. `_side_crop._box_for`: margin 을 bbox 파생분에만 적용 — floor 크기가 relaxed crop 의 하한으로 보존돼 밀집/단일 저신뢰 좌표도 부위 crop 유지. valid 경로 산출 byte-동일.
2. `select_confident_frame` 순수 helper 신설 + `_to_rep_idx` 모듈 레벨 추출. pipeline `_attach_fault_zoom_comparisons` 가 sourceFrameIndices median 대신 user/ref 독립으로 confidence 최대 프레임 선택. legacy(confidence 부재) doc 은 median 폴백 — 산출 diff 0.

## 검증

- 대상 테스트 37 passed (test_fault_zoom.py + test_fault_zoom_relaxed_crop.py), RED→GREEN TDD.
- diff 스코프 = 계획된 4개 파일만. 채점 경로 0 diff (deductionBreakdown/visionVeto 불변 — display 전용).
- 로컬 전체 suite 의 51개 실패는 전부 pre-existing (base 대비 diff 는 본 plan 4개 파일뿐, 실패 테스트 어느 것도 fault_zoom 미참조).

## PENDING

- 실기기 PNG 재생성 검증: pod 재분석(kip-up fault 페어) 필요 — 저장된 PNG 는 재생성되지 않으므로 새 분석에서만 새 crop 확인 가능.
