"""line / angle 차원 N/A root cause 박제 스크립트 (Plan 01-11 T-2).

Plan 10 ref-sideway-spin 단일 영상 결과에서 line, angle 두 차원이 N/A 였다 —
production overall 점수 신뢰도의 결정적 약점 (PROJECT.md 핵심 블로커).
Plan 11 5영상 sweep 결과를 받아 각 영상별로:

  1. FallbackRecognizer (technique.FallbackRecognizer) 가 만든 TechniqueProfile
     의 expected_extend / expected_bent / applicable_joints 출력
  2. dimensions.absolute_dimension_scores 가 line_score / angle_score 에서
     None 을 반환하는 정확한 조건 trace
  3. 영상별 root cause table
  4. Phase 5 (Gemini 기술 인식기) 진입 전 임시 회복 후보 박제 (실제 변경 X)

본 스크립트는 sweep_rtmpose JSON 출력을 입력으로 받는다 — raw frames /
RTMPose keypoints / MotionBERT 3D 가 JSON 에 저장돼 있지 않으므로 deep retrace
는 제한적. JSON 에 있는 final dimension scores (line/angle None 여부) +
FallbackRecognizer 의 default behaviour (빈 입력에서 출력되는 profile) 를
조합해 N/A 원인을 분류한다.

실행 (로컬 OK — mmpose 의존 없음):

  python3 -m backend.research.spikes.debug_dimensions \\
    --report backend/research/spikes/reports/sweep_rtmpose_20260601_2200.json \\
    --out backend/research/spikes/reports/debug_dimensions_20260601_2200.md

Plan 11 T-2 scope:
  - FallbackRecognizer 코드 수정 금지 (Phase 5 Gemini 통합 진입 시 변경)
  - dimensions.py 수정 금지
  - 본 스크립트는 박제 + 가능성 평가만 — 운영 코드 0 라인 변경
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


# ── FallbackRecognizer 분석 ───────────────────────────────────────────────────


def _inspect_fallback_recognizer_default() -> dict[str, Any]:
    """FallbackRecognizer 의 default behaviour 박제 — angles 빈 입력 시 결과.

    Plan 10 / 11 ref-sideway-spin 같은 측면 자세에서 FallbackRecognizer 가
    반환하는 profile 은 영상 실제 데이터로만 정확히 확인 가능하지만,
    빈/0 angles 입력으로 default expectations 의 분포를 박제할 수 있다.

    Returns:
        - default_profile: 0 frames angles 입력 시 출력 profile dict
        - expected_extend_joints: EXTEND 로 분류된 관절 키
        - expected_bent_joints: BENT_OK 로 분류된 관절 키
        - applicable_joints: technique.py 내부 _EXTENSION_JOINTS 상수
    """
    from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: PLC0415
    from sunity_shared.analysis.technique import (  # noqa: PLC0415
        FallbackRecognizer,
        JOINT_BENT_OK,
        JOINT_EXTEND,
        _EXTENSION_JOINTS,  # type: ignore[attr-defined]
    )

    # 빈 angles (T=1, J=8 의 0 행렬) — fallback 의 default 분기 발동
    zero_angles = np.zeros((1, len(JOINT_KEYS)), dtype=float)
    profile = FallbackRecognizer().recognize(zero_angles)

    expected_extend = [
        k for k, v in profile.joint_expectations.items() if v == JOINT_EXTEND
    ]
    expected_bent = [
        k for k, v in profile.joint_expectations.items() if v == JOINT_BENT_OK
    ]

    return {
        "name": profile.name,
        "category": profile.category,
        "joint_expectations": dict(profile.joint_expectations),
        "expected_extend": expected_extend,
        "expected_bent": expected_bent,
        "applicable_joints": list(_EXTENSION_JOINTS),
        "is_symmetric": profile.is_symmetric,
        "requires_hold": profile.requires_hold,
        "default_input": "zero angles (T=1, J=8)",
        "note": (
            "0 행렬 입력에서는 모든 관절이 BENT_OK 로 분류 — "
            "150° 임계 미달 (0 < 150). 실제 영상은 holding 구간 평균 ≥ 150° "
            "인 팔꿈치/무릎만 EXTEND. 측면/굽힘 자세는 대부분 BENT_OK 로 빠짐."
        ),
    }


# ── line / angle N/A root cause 분류 ──────────────────────────────────────────


def _classify_line_na(line_score: float | None, recognizer_info: dict) -> str:
    """line 차원 N/A 원인 분류.

    line_score 가 None 반환되는 조건 (dimensions.line_score 소스):
      - profile.expects_extension(k) == False for all k → deficits empty
      → 즉, FallbackRecognizer 가 어떤 관절도 EXTEND 로 분류 못 함

    그 외 line_score 가 점수를 반환했다면 N/A 아님.
    """
    if line_score is not None:
        return "정상 (line 점수 산출됨)"

    expected_extend = recognizer_info.get("expected_extend") or []
    if not expected_extend:
        return (
            "FallbackRecognizer: expected_extend 빈 집합 (모든 관절 BENT_OK) → "
            "dimensions.line_score 가 deficits empty 로 None 반환. "
            "PROJECT.md 핵심 블로커와 일치 — 측면/굽은 자세에서 holding 구간 "
            "평균 관절각 < 150° 라 EXTEND 로 분류되지 못함."
        )
    # default 에서는 EXTEND 가 있어도 실제 영상에서는 다를 수 있음
    return (
        "default profile 에는 EXTEND 관절이 있으나 실제 영상의 holding 구간 "
        "평균이 임계 미달로 추정됨. 정확한 trace 는 raw angles 재실행 필요."
    )


def _classify_angle_na(angle_score: float | None) -> str:
    """angle 차원 N/A 원인 분류.

    angle 차원은 dimensions.absolute_dimension_scores 가 **반환하지 않는다** —
    reference (mode1=정은지, mode3=이전 영상) 가 있어야 산출 가능 (DIM_ANGLE).
    spike 는 reference 없이 호출하므로 angle 은 dict 에 키 자체가 없다.

    따라서 spike 보고서의 angle: N/A 는 dimensions 모듈의 정상 동작 — bug 아님.
    """
    if angle_score is not None:
        return "정상 (angle 점수 산출됨, reference 비교 완료)"

    return (
        "spike 는 reference (정은지/이전 영상) 없이 호출 — "
        "dimensions.absolute_dimension_scores 가 angle 키를 dict 에 포함 X. "
        "production (mode1/mode3) 에서는 kismam.overall_score(angles_user, "
        "angles_ref) 로 산출됨. spike 의 angle N/A 는 정상 동작."
    )


def trace_motion(entry: dict, recognizer_info: dict) -> dict[str, Any]:
    """단일 영상 trace — sweep JSON 의 motion entry 1개 분석.

    Returns:
        {motion, line_score, angle_score, line_cause, angle_cause, recognizer_summary}
    """
    motion = entry.get("motion", "?")
    if entry.get("error"):
        return {
            "motion": motion,
            "line_score": None,
            "angle_score": None,
            "line_cause": f"spike 실행 실패: {entry.get('error')}",
            "angle_cause": f"spike 실행 실패: {entry.get('error')}",
        }

    rmb = entry.get("rtmpose_mb") or {}
    line_score = rmb.get("line")
    angle_score = rmb.get("angle")

    line_cause = _classify_line_na(line_score, recognizer_info)
    angle_cause = _classify_angle_na(angle_score)

    return {
        "motion": motion,
        "line_score": line_score,
        "angle_score": angle_score,
        "line_cause": line_cause,
        "angle_cause": angle_cause,
    }


# ── fix 후보 박제 (Phase 5 진입 전 임시 회복) ─────────────────────────────────


def _fix_candidates() -> list[dict[str, str]]:
    """Plan 11 T-2-5: 임시 회복 가능성 박제. 실제 적용은 belle 결정 후.

    세 후보:
      1. score_threshold 0.3 → 0.2 — RTMPose keypoint 컷 완화
      2. FallbackRecognizer default profile 확장 — 모든 사지 EXTEND 가정
      3. _EXTENSION_ZONE_DEG 150° → 120° 등 완화 — holding 평균 관절각 임계 하향
    """
    return [
        {
            "id": "1",
            "title": "score_threshold 0.3 → 0.2 완화",
            "what": (
                "RTMPose keypoint score < threshold 면 NaN 처리. 0.3 → 0.2 로 "
                "낮추면 더 많은 keypoint 가 살아남아 compute_joint_angles 가 "
                "유효한 관절각을 produce 할 가능성 ↑."
            ),
            "risk": (
                "저신뢰 keypoint 가 lift 단계에 들어가 stability / line 점수 "
                "변동성 증가. 측정 신뢰도 ↓ 가능. avg_rtm_score 0.4382 "
                "(Plan 10) 컨텍스트 하에 평가 필요."
            ),
            "scope": "spike 코드만 (sweep_rtmpose CLI default 변경)",
            "decision_owner": "belle (실제 적용은 sweep 결과 분석 후)",
            "status": "박제만 — 실제 변경은 belle 결정 후",
        },
        {
            "id": "2",
            "title": "FallbackRecognizer default profile 확장",
            "what": (
                "technique.FallbackRecognizer 의 _EXTENSION_JOINTS 4개 "
                "(left/right elbow/knee) 를 모두 EXTEND 로 기본 가정 변경. "
                "굽은 자세도 EXTEND 로 분류 → dimensions.line_score 가 "
                "deficits empty 케이스에서 탈출."
            ),
            "risk": (
                "PROJECT.md 핵심 블로커의 정반대 — '의도된 굽힘'을 결함으로 "
                "깎는 위양성 발생. 정은지 측면 자세에서 점수 오히려 하락 "
                "가능. 운영 코드 수정 = Phase 5 Gemini 통합 전 결정 위험."
            ),
            "scope": "technique.py 수정 (운영 코드, 본 plan 금지)",
            "decision_owner": "belle + 도메인 검증 (Phase 5 Gemini 통합과 같이)",
            "status": "박제만 — Phase 5 진입 시 Gemini 어댑터로 대체 권장",
        },
        {
            "id": "3",
            "title": "_EXTENSION_ZONE_DEG 150° → 130° 등 완화",
            "what": (
                "FallbackRecognizer 가 EXTEND 로 분류하는 임계 (현재 150°) 를 "
                "낮추면 holding 평균 관절각이 130~150° 인 자세도 EXTEND 로 "
                "분류 → line_score 가 deficits non-empty 로 점수 산출."
            ),
            "risk": (
                "임계 낮추면 굽은 자세를 EXTEND 로 분류 → 라인 deficit 가 "
                "커져 점수 하락. 후보 2 와 동일한 위양성 함정."
            ),
            "scope": "technique.py 수정 (운영 코드, 본 plan 금지)",
            "decision_owner": "belle + 도메인 검증",
            "status": "박제만 — Phase 5 Gemini 통합이 정공법",
        },
    ]


# ── Markdown 출력 ────────────────────────────────────────────────────────────


def generate_markdown(
    report_path: Path,
    sweep_data: dict,
    traces: list[dict],
    recognizer_info: dict,
    fix_candidates: list[dict],
) -> str:
    lines = [
        "# Debug: line / angle 차원 N/A root cause (Plan 01-11 T-2)",
        "",
        f"입력 보고서: `{report_path}`",
        f"보고서 생성: {sweep_data.get('generated_at', 'N/A')}",
        f"detector: `{sweep_data.get('detector', 'N/A')}` "
        f"score_threshold: {sweep_data.get('score_threshold', 'N/A')}",
        "",
        "## 1. FallbackRecognizer default 박제",
        "",
        f"- name: `{recognizer_info.get('name')}`",
        f"- category: `{recognizer_info.get('category')}`",
        f"- applicable_joints (technique._EXTENSION_JOINTS): "
        f"`{recognizer_info.get('applicable_joints')}`",
        f"- expected_extend (0 angles 입력): "
        f"`{recognizer_info.get('expected_extend')}`",
        f"- expected_bent (0 angles 입력): "
        f"`{recognizer_info.get('expected_bent')}`",
        f"- is_symmetric: {recognizer_info.get('is_symmetric')}",
        f"- requires_hold: {recognizer_info.get('requires_hold')}",
        "",
        f"**해석**: {recognizer_info.get('note')}",
        "",
        "## 2. 영상별 root cause table",
        "",
        "| 모션 | line | line N/A 원인 | angle | angle N/A 원인 |",
        "|---|---|---|---|---|",
    ]

    for t in traces:
        line_s = t.get("line_score")
        angle_s = t.get("angle_score")
        line_s_str = "N/A" if line_s is None else f"{line_s:.1f}"
        angle_s_str = "N/A" if angle_s is None else f"{angle_s:.1f}"
        lines.append(
            f"| {t.get('motion', '?')} | {line_s_str} | {t.get('line_cause', '')} | "
            f"{angle_s_str} | {t.get('angle_cause', '')} |"
        )

    lines += [
        "",
        "## 3. FallbackRecognizer profile per video",
        "",
        "본 보고서는 sweep JSON 만 입력으로 받아 raw angles 재현 불가 — "
        "FallbackRecognizer 의 영상별 실제 profile 확인은 belle Pod 에서 spike 재실행 "
        "시 `--dump-profile` 같은 옵션 추가 후 가능 (현재 plan 범위 밖).",
        "",
        "아래는 default (zero angles) 입력 기준 박제:",
        "",
        f"- expected_extend: {recognizer_info.get('expected_extend')}",
        f"- expected_bent: {recognizer_info.get('expected_bent')}",
        "",
        "## 4. Fix candidates (Phase 5 진입 전 임시 회복 — 박제만)",
        "",
        "**중요**: 아래 후보는 본 plan 에서 적용하지 않음. Plan 11 scope_limits 명시 — "
        "FallbackRecognizer / dimensions.py 코드 수정 금지. belle 결정 + Phase 5 "
        "(Gemini 기술 인식기) 통합과 같이 평가.",
        "",
    ]

    for fc in fix_candidates:
        lines += [
            f"### 후보 {fc['id']}: {fc['title']}",
            "",
            f"- **무엇**: {fc['what']}",
            f"- **위험**: {fc['risk']}",
            f"- **범위**: {fc['scope']}",
            f"- **결정 소유**: {fc['decision_owner']}",
            f"- **상태**: {fc['status']}",
            "",
        ]

    lines += [
        "## 5. 결론",
        "",
        "- **line N/A 정공법**: Phase 5 Gemini 기술 인식기 통합. Gemini 가 영상에서 "
        "기술명 + EXTEND/BENT/CONTACT 매핑을 직접 반환 → FallbackRecognizer 한계 우회.",
        "- **angle N/A**: spike 에서는 정상 동작 (reference 없이 호출). production "
        "mode1/mode3 에서 자동 산출되므로 별도 작업 불요.",
        "- **임시 회복 (3 후보)**: 모두 위양성 위험. belle 결정 + 도메인 검증 없이 "
        "단독 적용 금지.",
        "",
    ]

    return "\n".join(lines) + "\n"


def _print_summary(traces: list[dict], recognizer_info: dict) -> None:
    print()
    print("=== debug_dimensions root cause ===")
    print(f"  applicable_joints: {recognizer_info.get('applicable_joints')}")
    print(f"  default expected_extend: {recognizer_info.get('expected_extend')}")
    print(f"  default expected_bent : {recognizer_info.get('expected_bent')}")
    print()
    print(f"  {'모션':<22}  {'line':>6}  {'angle':>6}  원인 요약")
    print(f"  {'-'*22}  {'-'*6}  {'-'*6}  {'-'*40}")
    for t in traces:
        line_s = t.get("line_score")
        angle_s = t.get("angle_score")
        line_s_str = "N/A" if line_s is None else f"{line_s:.1f}"
        angle_s_str = "N/A" if angle_s is None else f"{angle_s:.1f}"
        cause = (t.get("line_cause") or "")[:60]
        print(
            f"  {t.get('motion', '?'):<22}  {line_s_str:>6}  {angle_s_str:>6}  {cause}"
        )
    print()


# ── 메인 ──────────────────────────────────────────────────────────────────────


def run_debug(
    report_path: str | Path,
    motions: list[str] | None = None,
    out: str | Path | None = None,
) -> dict[str, Any]:
    """sweep_rtmpose JSON 보고서를 받아 line/angle N/A root cause trace.

    Args:
        report_path: sweep_rtmpose 가 dump 한 .json 경로.
        motions: 필터링 (None 이면 전체 분석).
        out: Markdown 보고서 저장 경로 (.md). None 이면 stdout 만.

    Returns:
        {recognizer_info, traces, fix_candidates} dict.
    """
    report_path = Path(report_path)
    if not report_path.exists():
        raise FileNotFoundError(f"보고서 파일 없음: {report_path}")

    with open(report_path, encoding="utf-8") as f:
        sweep_data = json.load(f)

    all_entries = sweep_data.get("motions", []) or []
    if motions is not None:
        entries = [e for e in all_entries if e.get("motion") in motions]
    else:
        entries = all_entries

    if not entries:
        raise ValueError(
            f"분석할 영상이 없습니다. report 의 motions 키: "
            f"{[e.get('motion') for e in all_entries]}"
        )

    recognizer_info = _inspect_fallback_recognizer_default()
    traces = [trace_motion(e, recognizer_info) for e in entries]
    fix_candidates = _fix_candidates()

    if out is not None:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_text = generate_markdown(
            report_path, sweep_data, traces, recognizer_info, fix_candidates
        )
        out_path.write_text(md_text, encoding="utf-8")
        log.info("Markdown 결과: %s", out_path)

    _print_summary(traces, recognizer_info)
    return {
        "recognizer_info": recognizer_info,
        "traces": traces,
        "fix_candidates": fix_candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "sweep_rtmpose 보고서의 line/angle N/A 원인 trace (Plan 01-11 T-2). "
            "FallbackRecognizer default profile + 영상별 점수 → 원인 분류."
        )
    )
    parser.add_argument(
        "--report",
        required=True,
        help="sweep_rtmpose 가 dump 한 JSON 보고서 경로",
    )
    parser.add_argument(
        "--motions",
        nargs="+",
        default=None,
        help="필터링할 motion_id 리스트 (없으면 전체)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Markdown 결과 저장 경로 (.md)",
    )

    args = parser.parse_args()

    run_debug(
        report_path=args.report,
        motions=args.motions,
        out=args.out,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    main()
