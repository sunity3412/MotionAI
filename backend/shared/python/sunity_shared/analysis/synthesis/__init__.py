"""Phase 4 Wave 1 — Occlusion 합성 어댑터 패키지 (POSE-03).

D-04 트리거(confidence/scene/phase) → SynthesisAdapter Protocol →
SynthesisResult(status=applied|partial|skipped|failed) 의 단방향 데이터 흐름.

R1 non-scoring 하드월:
  본 패키지의 어느 결과물도 DTW/kismam/IPSF coco_array 에 절대 mutate 되지 않는다.
  합성 output 은 KeypointReport / aiSynthesisMeta / joints3d (사용자 시각화 + 메타
  + 3D viewer) 에만 흐른다. promotion 은 별도 후속 phase 의 별도 결정.

R6 fix:
  identify_occlusion_targets 는 (T,17,3)/(T,17) 형상의 keypoint confidence 를
  직접 소비. temporal.occluded_mask 는 (T,J) 2D 전용이라 재사용 금지.
"""

from __future__ import annotations
