"""kip-up recognizer probe (P1 A track, 2026-06-27).

목적: 왜 recognizer가 kip-up을 ref-kip-up으로 분류 못 하나 (sweep activatedCriteria=[]).
- Gemini가 반환하는 raw motion name
- classify_motion_name 매핑 결과 (canonical, scope_status)
- 최종 profile.category / motion_id / joint_expectations

env(run_sweep_24.sh 동일): RECOGNIZER_BACKEND=gemini, GEMINI_API_KEY, FIREBASE_SA_PATH,
RTMW_ONNX_PATH, YOLOX_ONNX_PATH, RTMW_DEVICE=cuda. PYTHONPATH=shared/python:.
실행: backend/ 에서 python3 research/spikes/probe_kipup_recognizer.py
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("probe")

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

BUCKET = "sunity-motion-pilot-videos"


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def main() -> int:
    import boto3

    from sunity_shared.analysis import gemini_motion_classifier as gmc
    from sunity_shared.analysis.pose_frame import PoleAxis

    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    # Instrument classify_motion_name to capture the RAW name Gemini returns.
    _orig_classify = gmc.classify_motion_name
    captured: list = []

    def _wrapped(raw_name):
        result = _orig_classify(raw_name)
        captured.append((raw_name, result))
        print(f"  [classify] raw={raw_name!r} -> {result}")
        return result

    gmc.classify_motion_name = _wrapped
    # patch the symbol the recognizer module imported, too
    try:
        from sunity_shared.analysis import gemini_technique_recognizer as gtr
        if hasattr(gtr, "classify_motion_name"):
            gtr.classify_motion_name = _wrapped
    except Exception:  # noqa: BLE001
        pass

    pipeline = _load_pipeline()
    recognizer = pipeline._ensure_recognizer()
    print("recognizer class:", type(recognizer).__name__)

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    for role in ("fault", "correct"):
        key = f"fixtures/phase15/kip-up/{role}.mp4"
        # pipeline extraction (RTMW angles + frames path)
        inputs = pipeline._extract_video_analysis_inputs(
            BUCKET, key, default_pole, keep_local_video=True
        )
        angles = inputs.angles
        video_path = str(inputs.local_video_path) if inputs.local_video_path else None

        # raw Gemini classification (instrument the internal classify step)
        raw_name = None
        try:
            # GeminiTechniqueRecognizer._classify_motion → (raw_name?) ; fall back to recognize()
            if hasattr(recognizer, "_classify_motion"):
                # _classify_motion typically returns (canonical, scope) using gmc; to see raw,
                # call the underlying Gemini name extraction if exposed.
                pass
        except Exception as exc:  # noqa: BLE001
            log.warning("classify probe failed: %s", exc)

        # knee angle diagnostics — is the bent-knee fault anywhere in the raw angles
        # but absent from the hold window?
        import numpy as np
        from sunity_shared.analysis import dimensions
        from sunity_shared.analysis.skeleton import JOINT_KEYS

        a = np.asarray(angles, dtype=float)
        for knee in ("left_knee", "right_knee"):
            ci = JOINT_KEYS.index(knee)
            col = a[:, ci]
            finite = col[np.isfinite(col)]
            if finite.size:
                print(
                    f"  [angle] {role} {knee}: frames={finite.size} "
                    f"min={finite.min():.1f} max={finite.max():.1f} mean={finite.mean():.1f} "
                    f"median={np.median(finite):.1f} p10={np.percentile(finite,10):.1f}"
                )
        # hold-window mean (what leg_extension actually scores)
        prof_tmp = recognizer.recognize(angles, frames=video_path)
        sliced, win = dimensions._select_window(a, prof_tmp)
        for knee in ("left_knee", "right_knee"):
            ci = JOINT_KEYS.index(knee)
            wcol = np.asarray(sliced)[:, ci]
            wfin = wcol[np.isfinite(wcol)]
            if wfin.size:
                print(f"  [holdwin {win}] {role} {knee}: mean={wfin.mean():.1f}")

        profile = recognizer.recognize(angles, frames=video_path)
        print(f"\n=== kip-up {role} ===")
        print("  profile.name:", getattr(profile, "name", None))
        print("  profile.category:", getattr(profile, "category", None))
        print("  profile.motion_id:", getattr(profile, "motion_id", None))
        je = getattr(profile, "joint_expectations", {}) or {}
        extend = [k for k, v in je.items() if v == "JOINT_EXTEND" or v == "EXTEND"]
        print("  joint_expectations EXTEND:", extend)
        print("  joint_expectations:", je)

    # sanity: what does classify_motion_name do with likely kip-up names?
    print("\n=== classify_motion_name sanity ===")
    for n in ["kip up", "kip-up", "킵업", "kipup", "mount", "floor mount", "kick up",
              "dynamic kip", "shoulder mount", "deadlift", "ayesha"]:
        print(f"  {n!r} -> {gmc.classify_motion_name(n)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
