"""기준 크롭의 4/3 배율은 하드코딩이 아니라 **거짓 라벨을 보상한 데이터 유도값**이다.

`fault_zoom.ref_display_frame_index` 는
    rep9_n = ref_rep_frames × frames_fps / ref_rep_fps
    scale  = ref_video_n / rep9_n
로 배율을 유도한다. 독스트링 자신이 "rep 과 비디오가 정합이면 rep9_n == ref_video_n →
배율 1.0 → identity" 라고 적어 놓았다. 그런데 두 입력이 다 거짓이었다:

  · `ref_rep_fps` = 기준 doc 라벨 **18.0** (실제 ~14.94)
  · `frames_fps` = app.py 에 **리터럴 9.0** (실제 = src_fps/step ≈ 9.96)

그래서 배율이 1.0 이 아니라 4/3 로 나왔고, 그 4/3 이 "정은지 쪽은 아예 다른 장면"의
경험적 보정으로 박제됐다. **진실을 먹이면 스스로 1.0 이 되는가**를 여기서 확인한다.

관찰 전용 — 코드 무접촉.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis.frame_extractor import (  # noqa: E402
    decimation_step, effective_fps,
)

RENDER_TARGET_FPS = 9.0     # 렌더 시 기준 영상 재추출 target (app.py frames_fps 자리)
REPROCESS_TARGET_FPS = 18.0  # 기준 재처리 때 요청한 target (= 저장 라벨)

# (motionId, 기준영상 src_fps, 총 프레임, anglesFrames) — ffprobe·Firestore 실측
REFS = [
    ("ref-pdshape", 29.8734, 472, 237),
    ("ref-peter-pan", 29.7683, 256, 130),
    ("ref-power-spin", 30.0, 316, 159),
    ("ref-elbow-twist-sister", 29.9087, 654, 329),
    ("ref-kip-up", 30.0, 234, 118),
]


def extracted_n(src_frames: int, step: int) -> int:
    """extract() 의 실제 산출 프레임 수 (강제 마지막 프레임 규칙 포함)."""
    idx = list(range(0, src_frames, step))
    return len(idx) + (1 if (src_frames - 1) > idx[-1] else 0)


print(f"{'motionId':<24}{'rep':>5}{'video':>7}"
      f"{'현행 배율':>10}{'진실 배율':>10}{'중간 인덱스 오차':>16}")
worst = 0.0
for mid, src_fps, src_frames, rep_frames in REFS:
    step = decimation_step(src_fps, RENDER_TARGET_FPS)
    video_n = extracted_n(src_frames, step)
    render_eff = effective_fps(src_fps, RENDER_TARGET_FPS)
    rep_real = effective_fps(src_fps, REPROCESS_TARGET_FPS)

    # 현행 = 라벨 18.0 + 리터럴 9.0
    rep9_now = rep_frames * RENDER_TARGET_FPS / REPROCESS_TARGET_FPS
    scale_now = video_n / rep9_now
    # 진실 = 실측 rate 두 개
    rep9_true = rep_frames * render_eff / rep_real
    scale_true = video_n / rep9_true

    mid_idx = video_n // 2
    err_frames = mid_idx * (scale_now - scale_true)
    err_sec = err_frames / render_eff
    worst = max(worst, abs(err_sec))
    print(f"{mid:<24}{rep_frames:>5}{video_n:>7}{scale_now:>10.4f}{scale_true:>10.4f}"
          f"{err_frames:>+9.1f}f {err_sec:>+5.2f}s")

print(f"\n최대 오차 {worst:.2f}초 — 기준 크롭이 그만큼 **늦은 순간**을 보여준다.")
print("진실 배율이 1.0 에 수렴하면, 4/3 은 코드가 아니라 라벨이 만든 값이었다는 뜻이고,")
print("입력을 고치는 것이 보정을 지우는 것보다 안전하다(이중 보정 위험 없음).")
