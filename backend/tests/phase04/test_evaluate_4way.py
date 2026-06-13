"""POSE-03-g — Spike 001 evaluate_4way 4-way 비교 게이트 (Phase 4 04-03 신규 작성).

[파일 박제 정신 / 04-03 plan 정합]

이 파일은 04-03 plan 소유. Wave 3a smoke + license 게이트 (unit, RunPod 불필요)
+ Wave 3b @integration skeleton (실 RunPod RTMW 재추론, RunPod 필요) 둘로
구성된다. 04-05 는 본 파일 하단에 RunPod 통합 테스트 (예: test_evaluate_4way_
reprocess_vs_baseline) 를 append 한다 — 04-05 는 이 파일을 재신설하지 않는다.

Wave 3a (현재 — unit, 정확도 주장 0):
  · test_axis_b_smoke_synthetic_boost — +0.15 synthetic boost 가 evaluate_4way
    계산에서 NaN 없이 동작함을 검증. 산출된 rate_reduction_pct 는 scoring promote
    근거 아님 (calibration-source-hard-gate).
  · test_axis_a_split_angle_consistency — 3-way path NaN-free 계산 확인.
  · test_cylindrical_mesh_no_smplx_import — D-20 license gate (소스 grep).
  · test_cylindrical_mesh_license_stack — trimesh / pyrender importorskip +
    __file__ slopcheck.
  · test_mesh_adapter_excluded_without_env_flag — MEDIUM-1 hard gate: B4
    invariant 박제. SYNTHESIS_MESH_ENABLED unset/0 일 때 04-01 의
    `_get_synthesis_adapter()` 가 CylindricalMeshAdapter 를 반환하지 않음을 단언.
    Wave 3b GREEN 전까지 mesh path 가 점수/UI 에 새지 않음을 보장.

Wave 3b skeleton (@pytest.mark.integration, RunPod 필요 — pytest -m "not integration"
실행 시 자동 제외):
  · test_axis_b_real_rtmw_integration — pytest.skip 박제. 12-view render →
    실 RTMW 재추론 → evaluate_4way axis_b rate_reduction_pct > 0 검증.
    완료 기준 + 산출물 명세 docstring 박제.

phase blocker 비차단 원칙:
  Wave 3b @integration skip 상태이어도 Wave 2 (UI) / Wave 5 (reference 재처리)
  진행 가능 — 04-05 depends_on 은 04-03 Wave 3a smoke 까지만 요구한다 (반박#2).

3-way path:
  rtmw_mirror (baseline) / gemini_view (PRIMARY) / cylindrical_mesh (SECONDARY,
  D-18). Higgsfield / MagicMan 제외 (D-19 INVALIDATED).
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

# spike 001 metrics 모듈 path 박제 — conftest 에 spike path 없으므로 본 테스트가 직접 주입.
_SPIKE_DIR = pathlib.Path(__file__).parents[3] / ".planning/spikes/001-dataset-eval-harness"
sys.path.insert(0, str(_SPIKE_DIR))

from metrics import PathOutput, evaluate_4way  # noqa: E402 — sys.path 주입 후 import


# ── 로컬 헬퍼 박제 ─────────────────────────────────────────────────────────────
# spike 001 harness.py 의 make_synthetic_path 패턴을 dataset / JEONGEUNJI_5
# 의존성 제거하여 로컬 복사 (T=60, RTMW COCO-17 17 joint).


def _make_path_output(
    *,
    path_name: str,
    base_joints: np.ndarray,
    confidence: np.ndarray,
    video_id: str = "phase4-04-03-smoke",
    motion_category: str = "split",
    fps: float = 30.0,
    notes: list[str] | None = None,
) -> PathOutput:
    """conftest joint_seq_60f / conf_seq_60f 를 PathOutput 으로 wrap."""
    return PathOutput(
        path_name=path_name,
        joint_sequence=base_joints,
        confidence_sequence=confidence,
        fps=fps,
        video_id=video_id,
        motion_category=motion_category,
        notes=notes or [],
    )


def _build_split_joints(base_joints: np.ndarray) -> np.ndarray:
    """split 자세 박제 — hip/knee/ankle 위치를 deterministic 으로 설정."""
    arr = base_joints.copy()
    n = arr.shape[0]
    # COCO-17: hip_l=11, hip_r=12, knee_l=13, knee_r=14, ank_l=15, ank_r=16
    arr[:, 11] = np.tile(np.array([-0.15, 0.0, 0.0], dtype=arr.dtype), (n, 1))
    arr[:, 12] = np.tile(np.array([+0.15, 0.0, 0.0], dtype=arr.dtype), (n, 1))
    arr[:, 13] = np.tile(np.array([-0.55, -0.3, 0.0], dtype=arr.dtype), (n, 1))
    arr[:, 14] = np.tile(np.array([+0.55, -0.3, 0.0], dtype=arr.dtype), (n, 1))
    arr[:, 15] = np.tile(np.array([-0.95, -0.6, 0.0], dtype=arr.dtype), (n, 1))
    arr[:, 16] = np.tile(np.array([+0.95, -0.6, 0.0], dtype=arr.dtype), (n, 1))
    return arr


# ── [Wave 3a unit] test_axis_b_smoke_synthetic_boost ──────────────────────────


def test_axis_b_smoke_synthetic_boost(
    joint_seq_60f: np.ndarray, conf_seq_60f: np.ndarray
) -> None:
    """POSE-03-g Wave 3a axis_b smoke — +0.15 synthetic boost NaN-free 계산.

    이 테스트는 +0.15 synthetic boost 가 evaluate_4way 계산에서 NaN 없이 동작함을
    검증하는 smoke test 임. 실 RunPod RTMW 재추론 없이 산출된 rate_reduction_pct
    는 scoring promote 근거가 아님 (calibration-source-hard-gate). 실 accuracy
    gate 는 test_axis_b_real_rtmw_integration (@integration) 에서 수행.

    3-way path:
      rtmw_mirror (baseline) / gemini_view (PRIMARY) / cylindrical_mesh (SECONDARY).
    """
    split_joints = _build_split_joints(joint_seq_60f)

    # cylindrical_mesh boost: +0.15 clipped at 1.0 (scoring promote 근거 아님,
    # calibration-source-hard-gate).
    cylindrical_boost_conf = np.clip(conf_seq_60f + 0.15, 0.0, 1.0)

    outputs = {
        "rtmw_mirror": _make_path_output(
            path_name="rtmw_mirror",
            base_joints=split_joints,
            confidence=conf_seq_60f,
        ),
        "gemini_view": _make_path_output(
            path_name="gemini_view",
            base_joints=split_joints,
            confidence=np.clip(conf_seq_60f + 0.10, 0.0, 1.0),
        ),
        "cylindrical_mesh": _make_path_output(
            path_name="cylindrical_mesh",
            base_joints=split_joints,
            confidence=cylindrical_boost_conf,
            notes=[
                "Wave 3a placeholder boost (+0.15) — scoring promote 근거 아님 "
                "(calibration-source-hard-gate). Wave 3b @integration 실 검증.",
            ],
        ),
    }

    split_frames = [0, 5, 10, 15, 20]
    criterion_frames = {
        "fully_extended": list(range(0, 60, 5)),
        "twist_alignment": list(range(10, 30)),
    }

    report = evaluate_4way(
        outputs=outputs,
        split_frame_indices=split_frames,
        criterion_frames=criterion_frames,
        baseline_path_name="rtmw_mirror",
        occlusion_threshold=0.3,
    )

    # NaN-free 계산 확인. baseline 대비 rate_reduction_pct >= 0.0 박제
    # (cylindrical_mesh boost 가 occlusion frame rate 를 감소시키므로).
    assert "cylindrical_mesh" in report.axis_b
    cm = report.axis_b["cylindrical_mesh"]
    assert cm["rate_reduction_pct"] >= 0.0, (
        f"rate_reduction_pct = {cm['rate_reduction_pct']} — synthetic boost 가 "
        "occlusion frame rate 를 감소시켜야 함 (NaN/음수 아님). "
        "주의: 이 값은 scoring promote 근거 아님 — Wave 3b accuracy gate 별도."
    )
    # NaN guard
    assert not np.isnan(cm["rate_reduction_pct"]), "axis_b rate_reduction_pct NaN"
    assert not np.isnan(cm["occlusion_frame_rate"]), "axis_b occlusion_frame_rate NaN"


# ── [Wave 3a unit] test_axis_a_split_angle_consistency ────────────────────────


def test_axis_a_split_angle_consistency(
    joint_seq_60f: np.ndarray, conf_seq_60f: np.ndarray
) -> None:
    """POSE-03-g Wave 3a axis_a — 3-way path split angle pass rate NaN-free.

    IPSF Page 19: split angle 은 어떤 perspective 에서도 동일해야 함. smoke 단계
    에서는 산출 자체가 NaN 없이 동작함을 확인 (실 IPSF tolerance 정합은 Wave 3b
    @integration 에서 실 RunPod 재추론 후 검증).
    """
    split_joints = _build_split_joints(joint_seq_60f)
    outputs = {
        "rtmw_mirror": _make_path_output(
            path_name="rtmw_mirror",
            base_joints=split_joints,
            confidence=conf_seq_60f,
        ),
        "gemini_view": _make_path_output(
            path_name="gemini_view",
            base_joints=split_joints,
            confidence=np.clip(conf_seq_60f + 0.10, 0.0, 1.0),
        ),
        "cylindrical_mesh": _make_path_output(
            path_name="cylindrical_mesh",
            base_joints=split_joints,
            confidence=np.clip(conf_seq_60f + 0.15, 0.0, 1.0),
        ),
    }
    split_frames = [0, 5, 10, 15, 20]
    criterion_frames = {
        "fully_extended": list(range(0, 60, 5)),
        "twist_alignment": list(range(10, 30)),
    }
    report = evaluate_4way(
        outputs=outputs,
        split_frame_indices=split_frames,
        criterion_frames=criterion_frames,
        baseline_path_name="rtmw_mirror",
    )
    for path in ("rtmw_mirror", "gemini_view", "cylindrical_mesh"):
        rate = report.axis_a[path]
        assert not np.isnan(rate), f"axis_a {path} NaN — split_frame_indices 가용성 확인"
        assert rate >= 0.0, f"axis_a {path} rate < 0 — 계산 오류 ({rate})"


# ── [Wave 3a unit] test_cylindrical_mesh_no_smplx_import ──────────────────────


def test_cylindrical_mesh_no_smplx_import() -> None:
    """POSE-03-g Wave 3a license gate — cylindrical_mesh.py 소스에 "smplx" 미포함.

    D-20 박제 (SMPL-X 의존 0). 본 테스트는 소스 text grep 으로 license 통과
    검증.
    """
    src_path = (
        pathlib.Path(__file__).parents[3]
        / "backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py"
    )
    assert src_path.exists(), f"cylindrical_mesh.py 부재: {src_path}"
    src = src_path.read_text(encoding="utf-8").lower()
    assert "smplx" not in src, (
        "cylindrical_mesh.py 에 'smplx' literal 발견 — D-20 박제 위반"
    )


# ── [Wave 3a unit] test_cylindrical_mesh_license_stack ────────────────────────


def test_cylindrical_mesh_license_stack() -> None:
    """POSE-03-g Wave 3a license stack — trimesh + pyrender 모듈 경로 slopcheck.

    pytest.importorskip 으로 모듈 미설치 환경 (Mac local) 은 SKIP 처리. 설치
    환경에서는 __file__ 경로 print 로 수동 slopcheck 가능.
    """
    trimesh = pytest.importorskip("trimesh")
    pyrender = pytest.importorskip("pyrender")
    print(f"\n[license slopcheck] trimesh : {trimesh.__file__}")
    print(f"[license slopcheck] pyrender: {pyrender.__file__}")


# ── [Wave 3a unit] test_mesh_adapter_excluded_without_env_flag ────────────────


def test_mesh_adapter_excluded_without_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """POSE-03-g Wave 3a MEDIUM-1 hard gate — SYNTHESIS_MESH_ENABLED unset/0
    일 때 _get_synthesis_adapter() 가 CylindricalMeshAdapter 를 반환하지 않음.

    B4 invariant 박제:
      Wave 3b @integration (실 RTMW 재추론) GREEN 전까지 mesh path 는 pipeline
      운영 경로(점수/UI)에 새지 않아야 한다. placeholder boosted confidence
      (+0.15) 가 scoring 에 흘러가는 것을 차단 (R1 non-scoring 하드월 +
      calibration-source-hard-gate).

      04-01 의 `_get_synthesis_adapter()` 는 module-level lazy singleton 으로
      GeminiViewReasoner 만 반환한다. 본 테스트는 SYNTHESIS_MESH_ENABLED env 가
      unset/0 인 상태에서 해당 helper 가 CylindricalMeshAdapter 인스턴스를
      반환하지 않음을 단언한다.
    """
    # SYNTHESIS_MESH_ENABLED 명시적으로 제거 (혹은 0) — 본 테스트 invariant.
    monkeypatch.delenv("SYNTHESIS_MESH_ENABLED", raising=False)

    # 04-01 pipeline 의 _get_synthesis_adapter 단일 source 박제.
    # backend/functions/pipeline 은 SAM Lambda function 폴더이지만 본 테스트 의도는
    # "pipeline 의 lazy singleton 이 CylindricalMeshAdapter 를 노출하지 않음" 이라
    # backend/functions/pipeline/app.py 의 helper 를 직접 호출한다.
    sys.path.insert(
        0,
        str(pathlib.Path(__file__).parents[2] / "functions/pipeline"),
    )
    # 모듈 캐시 정리 — 첫 import 가 module-level singleton 을 None 으로 초기화.
    sys.modules.pop("app", None)

    import app as pipeline_app  # type: ignore[import-not-found]

    # 명시적으로 singleton 을 비우고 새로 가져온다.
    pipeline_app._SYNTHESIS_ADAPTER = None  # type: ignore[attr-defined]

    adapter = pipeline_app._get_synthesis_adapter()

    # CylindricalMeshAdapter 클래스를 import 해서 isinstance 비교.
    from sunity_shared.analysis.synthesis.cylindrical_mesh import CylindricalMeshAdapter

    assert not isinstance(adapter, CylindricalMeshAdapter), (
        "SYNTHESIS_MESH_ENABLED unset/0 인데 _get_synthesis_adapter() 가 "
        f"CylindricalMeshAdapter 를 반환함 — B4 hard gate 위반. got={type(adapter)}"
    )

    # 또한 synthesis 패키지 __init__ 이 default 로 CylindricalMeshAdapter 를
    # export 하지 않음을 보조 확인 (env-flag 도달 전에도 export 자체가 없으면
    # 추가 안전).
    import sunity_shared.analysis.synthesis as synth_pkg

    default_exports = getattr(synth_pkg, "__all__", None)
    if default_exports is not None:
        assert "CylindricalMeshAdapter" not in default_exports, (
            "synthesis/__init__.py __all__ 에 CylindricalMeshAdapter 가 노출됨 — "
            "Wave 3b GREEN 전까지 default export 금지 (B4 hard gate)."
        )


# ── [Wave 3b skeleton — @pytest.mark.integration, RunPod 필요] ───────────────


@pytest.mark.integration
def test_axis_b_real_rtmw_integration() -> None:
    """POSE-03-g Wave 3b accuracy gate — 실 RunPod RTMW 재추론 + evaluate_4way
    axis_b baseline 대비 실 비교.

    완료 기준 (Wave 3b 실 구현 시):
      RunPod 에서 12-view 렌더 이미지 → 실 RTMW 재추론 → PathOutput wrapping →
      evaluate_4way axis_b rate_reduction_pct 실 검증. 산출물(렌더 이미지/배열)
      persisted artifact 필수. baseline evaluate_4way 와 실 비교. acceptance:
      rate_reduction_pct > 0 (baseline 대비 실 개선 확인) — calibration-source-
      hard-gate 통과 게이트.

    Wave 3a 시점 위치:
      04-05 는 본 skeleton 아래에 RunPod 통합 테스트 (예:
      test_evaluate_4way_reprocess_vs_baseline) 를 append 한다. 04-05 는 본
      파일을 재신설하지 않는다.

    Wave 3b @integration skip = Wave 2/5 진행 차단 아님 (04-05 depends_on 은
    04-03 3a smoke 까지).
    """
    pytest.skip(
        "Wave 3b 실 RunPod RTMW 재추론 미구현 — _rerun_rtmw_on_views 연결 후 "
        "skip 제거"
    )
