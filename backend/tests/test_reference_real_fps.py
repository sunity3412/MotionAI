"""기준 트랙의 실제 rate 를 쓴다 (quick-260810-e4v U3).

기준 doc 의 `keypointReport.fps` 는 재처리 때 **요청한** target_fps(18.0)이고, 실제
산출 rate 가 아니다. `frame_extractor` 가 정수 step 으로 솎으므로 30fps 원본에 target 18
을 주면 step 2 → **~14.93fps** 가 나온다(quick-260810-cbt 실측, 기준 5건 전부 15.0x).

이 라벨은 `ref_boundary_step_mask` 의 마진 `ceil(0.5초 × ref_fps)` 에 들어가므로
9 프레임을 제외해 왔는데, 실제로는 8 프레임이 0.5초다 — 즉 **0.6초를 제외**하고 있었다.
belle 승인분(08-10): 이 교정으로 점수가 움직여도 정당하면 괜찮다.

여기서는 **읽기 경로만** 만든다. 필드가 없으면 종전 라벨로 fail-open 하므로 백필 전까지
산출은 byte-동일이다 — 점수가 움직이는 시점은 백필이고, 그 전에 점수표를 belle 께 낸다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared.analysis import motiondtw as md  # noqa: E402


def test_prefers_measured_real_fps_when_present() -> None:
    ref = {"keypointReport": {"fps": 18.0}, "anglesRealFps": 15.03}
    assert app._reference_angles_fps(ref) == pytest.approx(15.03)


def test_falls_back_to_stored_label_when_absent() -> None:
    """백필 전 = 종전 라벨 → 산출 byte-동일 (점수 이동 시점은 백필)."""
    ref = {"keypointReport": {"fps": 18.0}}
    assert app._reference_angles_fps(ref) == pytest.approx(18.0)


@pytest.mark.parametrize("bad", [0, -1, None, "15.0", float("nan"), True])
def test_rejects_bad_real_fps_and_falls_back(bad) -> None:
    """깨진 값으로 마진을 옮기면 조용한 오채점 — fail-closed 로 라벨 유지."""
    ref = {"keypointReport": {"fps": 18.0}, "anglesRealFps": bad}
    assert app._reference_angles_fps(ref) == pytest.approx(18.0)


def test_zero_when_nothing_known() -> None:
    """둘 다 없으면 0.0 → 호출측이 None 으로 바꿔 경계 제외 미적용(종전 fail-open)."""
    assert app._reference_angles_fps({}) == 0.0
    assert app._reference_angles_fps(None) == 0.0


def test_margin_moves_by_exactly_one_frame() -> None:
    """이 교정이 실제로 바꾸는 것 = 마진 9 → 8 프레임. 그것 말고는 없다."""
    import math
    lab = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * 18.0)
    real = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * 15.03)
    assert (lab, real) == (9, 8)


def test_mode3_margin_unchanged_by_user_side_fix() -> None:
    """사용자 축(9.0 → 9.997)은 마진이 안 바뀐다 — mode3 점수 무접촉의 근거."""
    import math
    assert math.ceil(md.REF_BOUNDARY_EXCLUDE_S * 9.0) == 5
    assert math.ceil(md.REF_BOUNDARY_EXCLUDE_S * 9.997) == 5
