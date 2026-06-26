"""Phase 24 (B) kip-up Gemini still-pair probe — POD 전용 (24-06 §3 진단 #2).

pod 전용 — GPU(RTMW)/Gemini 가 로컬에 부재하므로 로컬 실행 금지. 이 스크립트는 24-06
DIRECTION §3 이 옵션 선택(B1/B2/B3)의 선결 조건으로 지목한 두 미지수 중 두 번째를 확정한다:
**선택된 still-pair 에서 Gemini 가 kip-up 결함을 실제로 짚을 수 있나** (support 게이트 통과 여부).

low_alignment_confidence collect-side bail 은 production 에서 Gemini 를 한 번도 안 돌린다
(app.py:1829-1833). 이 probe 는 그 bail 을 **우회**해 동일 시그니처로 assess_fault_context 를
직접 호출하고, alignment dict 전체(왜 bail 하는지) + Gemini 가 결함을 보는지를 출력한다.

객관성 ([[analysis-objectivity-no-human-scores]]): 점수/사람 라벨 0. Gemini 는 측정대상(결함
부위)만 짚고, fabrication 은 support 게이트가 차단한다. 이 probe 는 진단 출력만 — 채점 경로에
주입하지 않는다(24-06 §3, §5). fault 라벨=영상 파생(OK).

실행 (Pod, RTMW GPU + Gemini env 필요 — run_sweep.py 와 동일 스타일):
    source /workspace/aws_env.sh && \
    export CEREBRAS_KEY_PARAM=/sunity/motion/cerebras-api-key GEMINI_COACH_ENABLED=1 \
           RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
           YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx RTMW_DEVICE=cuda \
           FIREBASE_SA_PATH=/workspace/firebase-sa.json RECOGNIZER_BACKEND=gemini && \
    export GEMINI_API_KEY=$(python3 -c "import boto3;print(boto3.client('ssm',region_name='ap-northeast-2').get_parameter(Name='/sunity/motion/gemini-api-key',WithDecryption=True)['Parameter']['Value'])") && \
    cd /workspace/SunityMotion/backend && PYTHONPATH=shared/python:. python3 evals/phase24/probe_kip_up_gemini.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent  # backend/
sys.path.insert(0, str(BACKEND / "shared" / "python"))
sys.path.insert(0, str(BACKEND))

BUCKET = "sunity-motion-pilot-videos"
UID = "phase24kipprobe"
RUNID = str(int(time.time()))
MOTION = "kip-up"

# 현재 _process 가 트리거한 멤버 라벨 (wrapper 가 probe 출력에 부착). main 이 멤버마다 설정.
_CURRENT_LABEL = "?"


def _load_pipeline():
    """run_sweep.py 의 importlib 패턴 — pipeline 모듈 로드 + GPU 어댑터 준비."""
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _aid(role: str) -> str:
    # s3keys analysisId 는 영숫자만 — 하이픈 슬러그 금지.
    return MOTION.replace("-", "") + role + RUNID


def _do_probe(pipeline, vision_veto, gemini_vision_scorer, label: str, **kwargs) -> None:
    """app.py:1806-1850 의 selection→pair→alignment 를 **bail 없이** 재현 + Gemini 직접 호출.

    inline 으로 도는 이유: _process 는 return 후 다운로드 영상 임시 파일을 unlink 하므로
    유효한 local path 가 살아있는 wrapper 내부에서 probe 를 끝내야 한다(24-06 §3).
    """
    local_video_path = kwargs.get("local_video_path")
    reference_video_path = kwargs.get("reference_video_path")
    reference_dtw_match = kwargs.get("reference_dtw_match")
    profile = kwargs.get("profile")
    pose_frames = kwargs.get("pose_frames")
    reference_pose_frames = kwargs.get("reference_pose_frames")

    print(f"\n=== PROBE kip-up [{label}] (alignment bail 우회) ===", flush=True)

    # (1) 부위별 worst 후보 + worst timestamp → 9fps 정합 user_frame_idx.
    selection = vision_veto.select_worst_frame_candidates(profile)
    at = vision_veto.worst_pose_timestamp(profile)
    user_frame_idx = int(round((at or 0.0) * 9.0))

    # (2) still-pair 추출 (bail 전 단계와 동일 helper).
    pair = pipeline._build_selected_frame_pair(
        user_video_path=local_video_path,
        reference_video_path=reference_video_path,
        reference_dtw_match=reference_dtw_match,
        user_frame_idx=user_frame_idx,
        pose_frames=pose_frames,
        reference_pose_frames=reference_pose_frames,
    )
    if pair is None or reference_dtw_match is None:
        print(
            f"  SKIP [{label}] — pair={pair is not None} "
            f"reference_dtw_match={reference_dtw_match is not None} (probe 불가)",
            flush=True,
        )
        return

    # (3) alignment 평가 (production 이 **왜** bail 하는지 확정 — distance/visibility/path).
    visibility = float(pair.student_confidence) if pair.student_confidence is not None else 0.0
    alignment = vision_veto.assess_alignment_confidence(
        match=reference_dtw_match,
        selected_user_frame=user_frame_idx,
        keypoint_visibility=visibility,
    )
    # (a) alignment dict 전체.
    print(f"  (a) alignment = {json.dumps(alignment, ensure_ascii=False)}", flush=True)

    try:
        # (4/5) Gemini 직접 호출 (bail 우회) — app.py:1842 와 동일 시그니처.
        rich = gemini_vision_scorer.assess_fault_context(
            pair.student_frame_path,
            pair.reference_frame_path,
            at_seconds=at,
            part_scopes=list(gemini_vision_scorer.VETO_PART_SCOPES),
            frame_indices=[pair.user_frame_idx],
            reference_frame_indices=[pair.ref_frame_idx],
            selector_version=selection.get("selector_version"),
        )
        rich = rich or {}
        status = rich.get("status")
        verdict = rich.get("verdict")
        # (b) Gemini differences 반환 여부.
        print(
            f"  (b) gemini status={status} verdict_present={verdict is not None}",
            flush=True,
        )
        # (c) support 게이트 통과 여부.
        supported = rich.get("supported_differences") or []
        print(
            f"  (c) supported_differences count={len(supported)} "
            f"(support 게이트 통과={'yes' if supported else 'no'})",
            flush=True,
        )
        # (d) 각 difference 의 body_part / fault_state.
        fault_states = []
        for d in supported:
            d = d or {}
            bp = d.get("body_part")
            fs = d.get("fault_state") or d.get("severity")
            fault_states.append(fs)
            print(f"      supported: body_part={bp!r} fault_state={fs!r}", flush=True)
        for d in (getattr(verdict, "differences", None) or ()):
            bp = getattr(d, "body_part", None)
            fs = getattr(d, "fault_state", None) or getattr(d, "severity", None)
            print(f"      verdict.diff: body_part={bp!r} fault_state={fs!r}", flush=True)
        # (e) 명시 verdict 라인.
        is_fault = any(
            str(fs) not in ("none", "None", "", "correct") for fs in fault_states
        )
        if supported and is_fault:
            print("  (e) Gemini CAN see kip-up fault from still-pair", flush=True)
        else:
            print("  (e) Gemini CANNOT see kip-up fault from still-pair", flush=True)
    finally:
        # probe pair 는 원본 collect pair 와 별개 임시 파일 — 이중 정리 없음.
        for p in pair.cleanup_paths:
            pipeline._safe_unlink_local_video(p)


def main() -> int:
    from sunity_shared.analysis import vision_veto, gemini_vision_scorer  # noqa: E402
    from sunity_shared import firestore_admin as fa, models  # noqa: E402

    print(f"[setup] runId={RUNID} uid={UID} motion={MOTION} (pod-only probe)", flush=True)
    pipeline = _load_pipeline()

    # collect 를 capturing wrapper 로 monkeypatch — kwargs 캡처 후 inline probe, 그 다음
    # 원본 collect 호출로 _process 정상 종료(다운로드 영상 unlink 전에 probe 완료).
    _orig_collect = pipeline._collect_vision_fault_context

    def _wrapper(**kwargs):
        try:
            _do_probe(pipeline, vision_veto, gemini_vision_scorer, _CURRENT_LABEL, **kwargs)
        except Exception as exc:  # noqa: BLE001 — probe 진단은 분석 흐름 차단 0
            print(f"  PROBE ERROR [{_CURRENT_LABEL}]: {type(exc).__name__}: {exc}", flush=True)
        return _orig_collect(**kwargs)

    pipeline._collect_vision_fault_context = _wrapper

    global _CURRENT_LABEL
    for label, fixture, role in (("fault", "fault", "Fault"), ("correct", "correct", "Correct")):
        _CURRENT_LABEL = label
        analysis_id = _aid(role)
        key = f"fixtures/phase15/{MOTION}/{fixture}.mp4"
        fa._doc(models.analysis_doc_path(UID, analysis_id)).set({
            "mode": models.MODE_EXPERT,          # mode1 = 정은지 reference 비교
            "referenceMotionId": f"ref-{MOTION}",
            "status": "uploading",
            "createdAt": int(time.time() * 1000),
            "fileName": analysis_id + ".mp4",
            "videoKey": key,
            "sourceLabel": f"phase24_kipprobe:{MOTION}:{label}",
        })
        print(f"\n[member] {MOTION} {label} aid={analysis_id}", flush=True)
        try:
            pipeline._process(BUCKET, key, UID, analysis_id)
        except Exception as exc:  # noqa: BLE001 — not_pole 등은 doc 에 failed 로 기록됨
            print(f"  _process raised: {type(exc).__name__}: {exc}", flush=True)

    print("\nALLDONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
