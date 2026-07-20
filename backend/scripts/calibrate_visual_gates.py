"""31-13 — Display/Training 게이트 임계값 calibration harness (3차 H3-02 + 4차 B4-04/B4-05/H4-10/M4-03/M4-05).

이 스크립트는 **측정 로직을 하나도 갖고 있지 않다.** 판정은 전부 31-05/31-06 이
출하한 구현을 그대로 호출한다:

  - judge     : `visual_gen.judge_corrected_pose` (raw 7축 + confidence)
  - 판정 규칙 : `visual_gen.judge_display_pass` / `judge_training_pass` (threshold 인자 주입)
  - 각도      : `fault_zoom.joint_inner_angle_deg` (각도 산출 단일 출처)
  - pose 게이트: `pose_gate.measure_generated_pose` (정규화·전송·좌표계 계약 포함)

재구현을 금지하는 이유(B4-05): calibration 이 자체 스코어링을 들고 있으면 "임계값을
고른 코드"와 "production 에서 도는 코드"가 갈라진다. 그러면 이 파일이 산출한 숫자는
실제로 게이트하는 코드에 대한 근거가 아니게 된다.

pair 계약 (B4-04):
  manifest 항목 = {id, beforePath, beforeSha256, afterPath, afterSha256, label,
  jointKey, targetDeg, afterKeypointSource{path, modelVersion}, failureAxes[], category[]}.
  harness 는 before/after **각각** sha256 을 재검증하고, pose error 는 **after
  keypoint 로만** 계산한다. before 로 재면 "교정 전 각도"를 재는 꼴이라 게이트가
  스스로를 통과시킨다.

fail-closed (D-08): 측정이 없으면 통과가 아니라 **blocked** 다. 재보지 못한 축의
임계값을 보간해서 채우지 않는다 — 그 숫자는 측정이 아니라 창작이다.

사용:

    # 배선만 (네트워크 0, 과금 0)
    PYTHONPATH=backend/shared/python python3 backend/scripts/calibrate_visual_gates.py --dry-run

    # 실측 (judge = Gemini, pose = 살아있는 Pod 필요)
    export GEMINI_API_KEY=$(AWS_PROFILE=sunity-motion aws ssm get-parameter \\
        --name /sunity/motion/gemini-api-key --with-decryption \\
        --query Parameter.Value --output text)
    export RUNPOD_AUTH_TOKEN=$(AWS_PROFILE=sunity-motion aws ssm get-parameter \\
        --name /sunity/motion/runpod-auth-token --with-decryption \\
        --query Parameter.Value --output text)
    PYTHONPATH=backend/shared/python python3 backend/scripts/calibrate_visual_gates.py \\
        --pose-url https://<pod>-8000.proxy.runpod.net/pose-image

키는 env 로만 받는다 — 리터럴 0, 로그 0 (T-31-15/T-31-61). 산출 JSON 에 이미지
바이트·서명 URL 을 넣지 않는다 (T-31-61).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = REPO_ROOT / ".planning" / "phases" / "31-api-visual-correction"
DEFAULT_MANIFEST = PHASE_DIR / "smoke" / "fixtures_manifest.json"
DEFAULT_OUT = PHASE_DIR / "smoke" / "CALIBRATION.json"

# ── grid (측정 코드가 아니라 **탐색 공간**) ────────────────────────────────
#
# 임계값은 여기서 정해지지 않는다 — 격자를 훑고 라벨 대비 FA/FR 이 고르는 것이다.
# CLI 로 덮어쓸 수 있게 둔 이유는 이 파일에 "채택값" 리터럴이 남지 않게 하기 위함이다.
DEFAULT_POSE_TOL_GRID = (8.0, 10.0, 15.0, 20.0)
DEFAULT_CONFIDENCE_GRID = (0.6, 0.7, 0.8, 0.85)

# H4-10 표본 하한.
FLOOR_PASS = 4
FLOOR_FAIL = 8
# 측정 불가 비율 상한 — 넘으면 격자 자체가 근거를 잃는다.
MAX_UNMEASURED_FRACTION = 0.25

# production 분포. qwen-image-edit-plus 는 B4-02 async-only 게이트에서 구조적으로
# 탈락했으므로, 그 모델의 산출물로 고른 임계값은 **절대 돌지 않을 코드**에 대한
# 근거다. 기본 scope 를 chosen 모델로 제한하고 전체 격자는 참고용으로 따로 낸다.
DEFAULT_GENERATOR_SCOPE = "wan2.7-image-pro"

# failureAxes(라벨) → judge 축(예측). 어느 축을 실제로 잡아내는지 대조표에 쓴다.
_AXIS_TO_JUDGE = {
    "identity": ("identity_ok", False),
    "clothing": ("clothing_ok", False),
    "background": ("background_ok", False),
    "pole": ("pole_ok", False),
    "extra_limbs": ("no_extra_limbs", False),
    "extra_person": ("single_person_ok", False),
    "correction_invisible": ("correction_visible", False),
}
# pose_tolerance 는 대응하는 judge 축이 하나도 없다 — "목표 관절은 맞췄는데 나머지
# 포즈를 새로 그린" 유형이라 보존 축들이 통째로 거짓이 되어야 잡힌다. 별도 처리.
_PRESERVATION_AXES = (
    "identity_ok",
    "clothing_ok",
    "background_ok",
    "pole_ok",
    "single_person_ok",
    "no_extra_limbs",
)

POSE_STATUS_MEASURED = "measured"
POSE_STATUS_UNMEASURED = "unmeasured"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── manifest 검증 (B4-04) ────────────────────────────────────────────────

_REQUIRED_KEYS = (
    "id",
    "beforePath",
    "beforeSha256",
    "afterPath",
    "afterSha256",
    "label",
    "jointKey",
    "targetDeg",
    "afterKeypointSource",
    "failureAxes",
    "category",
)


def validate_pair(entry: dict) -> str | None:
    """pair 계약 위반 사유를 반환한다 (정상이면 None).

    hash 재검증까지 여기서 한다 — manifest 가 가리키는 파일이 라벨링 당시의 그
    파일인지 확인하지 않으면, 파일이 조용히 바뀐 뒤 라벨만 남아 잘못된 근거로
    임계값이 정해진다.
    """
    missing = [k for k in _REQUIRED_KEYS if k not in entry]
    if missing:
        return f"missing_keys:{','.join(missing)}"
    if entry["label"] not in ("PASS", "FAIL"):
        return f"bad_label:{entry['label']}"

    for side in ("before", "after"):
        path = Path(entry[f"{side}Path"])
        if not path.is_file():
            return f"{side}_missing_file"
        actual = _sha256_file(path)
        if actual != entry[f"{side}Sha256"]:
            return f"{side}_hash_mismatch"
    return None


def validate_keypoint_provenance(entry: dict) -> str | None:
    """afterKeypointSource 가 **이 pair 의 after 이미지**에서 나온 것인지 확인 (B4-04).

    다른 이미지의 keypoint 로 각도를 재면 pair 가 어긋난 채로 "측정됨" 이 된다.
    keypoint JSON 은 자신이 잰 이미지의 sha256 을 `imageSha256` 으로 들고 있어야 한다.
    """
    src = entry.get("afterKeypointSource") or {}
    path = src.get("path")
    if not path or path == "manual":
        return "no_keypoint_file"
    kp_path = Path(path)
    if not kp_path.is_file():
        return "keypoint_file_missing"
    try:
        payload = json.loads(kp_path.read_text())
    except (OSError, ValueError):
        return "keypoint_unreadable"
    if payload.get("imageSha256") != entry["afterSha256"]:
        return "keypoint_pair_mismatch"
    return None


# ── 측정 (전부 shipped 코드 호출) ─────────────────────────────────────────


def measure_judge(entry: dict) -> dict:
    """31-05 `judge_corrected_pose` 실호출 → raw 7축 + confidence."""
    from sunity_shared.analysis import visual_gen

    before = Path(entry["beforePath"]).read_bytes()
    after = Path(entry["afterPath"]).read_bytes()
    hint = (
        f"목표 관절 {entry['jointKey']} 를 약 {entry['targetDeg']}도로 교정하도록 "
        "지시한 산출물이다."
    )
    try:
        verdict = visual_gen.judge_corrected_pose(
            before, after, {"correction_hint": hint}
        )
    except visual_gen.JudgeInputTooLargeError as exc:
        return {"available": False, "reason": f"judge_input_too_large:{exc}"}
    if verdict is None:
        # None 은 통과가 아니다 — 판정 불가다 (31-05 계약).
        return {"available": False, "reason": "judge_unavailable"}
    return {
        "available": True,
        "axes": {axis: getattr(verdict, axis) for axis in visual_gen.JUDGE_AXES},
        "confidence": round(float(verdict.confidence), 4),
        "reason": verdict.reason,
    }


def measure_pose_from_keypoints(entry: dict) -> dict:
    """오프라인 경로 — keypoint JSON → 31-06 이 쓰는 것과 같은 각도 함수.

    좌표는 keypoint 파일이 등방 px 로 들고 있어야 한다 (`joint_inner_angle_deg` 입력
    계약). 정규화 좌표를 그대로 넣으면 종횡비만큼 각도가 왜곡된다.
    """
    from sunity_shared.analysis.fault_zoom import ARROW_JOINT_MAP, joint_inner_angle_deg

    src = entry["afterKeypointSource"]
    payload = json.loads(Path(src["path"]).read_text())
    keypoints = payload.get("keypoints")
    triple = ARROW_JOINT_MAP.get(entry["jointKey"])
    if triple is None or not isinstance(keypoints, dict):
        return {"status": POSE_STATUS_UNMEASURED, "reason": "joint_unmappable"}

    pts = []
    for name in triple:
        kp = keypoints.get(name)
        if not isinstance(kp, (list, tuple)) or len(kp) < 2:
            return {"status": POSE_STATUS_UNMEASURED, "reason": "keypoint_missing"}
        pts.append((float(kp[0]), float(kp[1])))

    measured = joint_inner_angle_deg(pts[0], pts[1], pts[2])
    if not math.isfinite(measured):
        return {"status": POSE_STATUS_UNMEASURED, "reason": "degenerate_triple"}
    return {
        "status": POSE_STATUS_MEASURED,
        "source": "keypoint_file",
        "measured_deg": round(measured, 3),
        "error_deg": round(abs(measured - float(entry["targetDeg"])), 3),
        "model_version": src.get("modelVersion"),
    }


def measure_pose_live(entry: dict, pose_url: str, token: str, max_tol: float) -> dict:
    """라이브 경로 — 31-06 `measure_generated_pose` 실호출.

    tolerance 는 격자 최댓값을 넣는다. 여기서 필요한 것은 통과 여부가 아니라 **raw
    error_deg** 이고, 통과 판정은 격자가 나중에 각 조합에서 다시 한다. 이렇게 해야
    임계값이 측정 호출에 하드코딩되지 않는다 (H3-02).
    """
    from sunity_shared.analysis import pose_gate

    result = pose_gate.measure_generated_pose(
        Path(entry["afterPath"]).read_bytes(),
        joint_key=entry["jointKey"],
        target_deg=float(entry["targetDeg"]),
        tolerance_deg=max_tol,
        pose_url=pose_url,
        token=token,
    )
    if result.error_deg is None:
        # unavailable(전송) 과 failed(측정 불신) 를 구분해 남긴다 — 전자는 재시도
        # 가능, 후자는 산출물 문제다 (31-06 계약).
        return {"status": POSE_STATUS_UNMEASURED, "reason": result.reason or "no_error_deg"}
    return {
        "status": POSE_STATUS_MEASURED,
        "source": "pose_image_endpoint",
        "measured_deg": round(float(result.measured_deg), 3),
        "error_deg": round(float(result.error_deg), 3),
        "model_version": None,
    }


# ── 격자 (판정은 31-05 함수 재사용) ───────────────────────────────────────


def _verdict_from_raw(raw: dict):
    from sunity_shared.analysis.visual_gen import JudgeVerdict

    return JudgeVerdict(
        **raw["axes"], confidence=float(raw["confidence"]), reason=raw.get("reason", "")
    )


def evaluate_grid(pairs: list[dict], pose_tol_grid, confidence_grid) -> list[dict]:
    """격자 조합별 FA/FR. 판정은 `judge_display_pass` 재사용 — 재구현 0."""
    from sunity_shared.analysis.visual_gen import judge_display_pass

    table = []
    for tol in pose_tol_grid:
        for conf in confidence_grid:
            fa = fr = tp = tn = undeterminable = 0
            for p in pairs:
                judge = p["judge"]
                pose = p["pose"]
                if pose["status"] != POSE_STATUS_MEASURED:
                    # pose 축을 못 재면 이 조합의 판정 자체가 성립하지 않는다.
                    undeterminable += 1
                    continue
                if judge["available"]:
                    judge_pass = judge_display_pass(
                        _verdict_from_raw(judge), min_confidence=conf
                    )
                else:
                    judge_pass = False  # 판정 불가 = 불통과 (fail-closed)
                predicted = judge_pass and pose["error_deg"] <= tol
                label_pass = p["label"] == "PASS"
                if predicted and not label_pass:
                    fa += 1
                elif not predicted and label_pass:
                    fr += 1
                elif predicted:
                    tp += 1
                else:
                    tn += 1
            table.append(
                {
                    "pose_tol_deg": tol,
                    "confidence": conf,
                    "false_accept": fa,
                    "false_reject": fr,
                    "true_pass": tp,
                    "true_fail": tn,
                    "undeterminable": undeterminable,
                    "evaluable": fa + fr + tp + tn,
                }
            )
    return table


def evaluate_confidence_only(pairs: list[dict], confidence_grid) -> list[dict]:
    """pose 축을 뺀 **judge 단독** confidence 스윕.

    production 게이트가 아니다 — 실제 판정은 judge AND pose 다. 그래도 이 표에는
    엄밀한 의미가 있다: pose 게이트는 통과 집합을 줄이기만 하므로

        judge 단독 FA  >=  production FA   (상한)
        judge 단독 FR  <=  production FR   (하한)

    즉 여기서 이미 false accept 가 남는 confidence 값은, pose 게이트가 그 산출물을
    따로 잡아내지 못하는 한 production 에서도 통과시킨다. pose 를 못 잰 상태에서도
    confidence 축에 대해 말할 수 있는 것을 정확히 이만큼으로 한정한다.
    """
    from sunity_shared.analysis.visual_gen import judge_display_pass

    rows = []
    for conf in confidence_grid:
        fa = fr = tp = tn = 0
        for p in pairs:
            judge = p["judge"]
            predicted = (
                judge_display_pass(_verdict_from_raw(judge), min_confidence=conf)
                if judge["available"]
                else False
            )
            label_pass = p["label"] == "PASS"
            if predicted and not label_pass:
                fa += 1
            elif not predicted and label_pass:
                fr += 1
            elif predicted:
                tp += 1
            else:
                tn += 1
        rows.append(
            {
                "confidence": conf,
                "false_accept_upper_bound": fa,
                "false_reject_lower_bound": fr,
                "true_pass": tp,
                "true_fail": tn,
                "n": len(pairs),
            }
        )
    return rows


def choose_thresholds(table: list[dict]) -> dict:
    """display = FA 최소(동률 FR 최소). training = display 보다 **양축 모두 엄격**한
    조합 중 FA 0 우선.

    더 엄격한 조합이 없으면 blocked 다 (M4-03). display 값을 training 에 복제하면
    "학습 적재 기준이 노출 기준과 같다"는 뜻이 되는데, 그건 B4-05 가 명시적으로
    금지한 상태다 — 실패 비용이 다른 두 게이트를 같은 값으로 두면 잘못 적재된 페어가
    모델을 영구히 오염시킨다.
    """
    evaluable = [r for r in table if r["evaluable"] > 0]
    if not evaluable:
        return {"blocked": True, "reason": "no_evaluable_grid_cell"}

    display = min(evaluable, key=lambda r: (r["false_accept"], r["false_reject"]))
    stricter = [
        r
        for r in evaluable
        if r["pose_tol_deg"] < display["pose_tol_deg"]
        and r["confidence"] > display["confidence"]
    ]
    if not stricter:
        return {
            "blocked": True,
            "reason": "no_stricter_training_grid",
            "display_candidate": {
                "display_pose_tol_deg": display["pose_tol_deg"],
                "display_confidence": display["confidence"],
            },
        }
    training = min(stricter, key=lambda r: (r["false_accept"], r["false_reject"]))
    return {
        "chosen": {
            "display_pose_tol_deg": display["pose_tol_deg"],
            "display_confidence": display["confidence"],
            "training_pose_tol_deg": training["pose_tol_deg"],
            "training_confidence": training["confidence"],
        }
    }


def build_confusion(pairs: list[dict]) -> dict:
    """category × 예측, failure axis 별 judge 검출율, 표본 수 (H4-10).

    예측은 pose 축 없이 **judge 단독** 으로 낸다 — pose 를 못 잰 상태에서도 judge 가
    어느 실패 축을 잡아내는지는 독립적으로 확인할 수 있어야 하기 때문이다.
    """
    from sunity_shared.analysis.visual_gen import judge_display_pass

    by_category: dict[str, dict[str, int]] = {}
    axis_detection: dict[str, dict[str, int]] = {}
    judge_only = {"pass_labeled_pass": 0, "pass_labeled_fail": 0,
                  "fail_labeled_pass": 0, "fail_labeled_fail": 0}

    for p in pairs:
        judge = p["judge"]
        label_pass = p["label"] == "PASS"
        if judge["available"]:
            # confusion 은 confidence 최저 격자값에서 낸다 — judge 의 **축 판정**
            # 능력을 보려는 것이지 confidence 임계를 보려는 것이 아니다.
            predicted = judge_display_pass(
                _verdict_from_raw(judge), min_confidence=min(DEFAULT_CONFIDENCE_GRID)
            )
        else:
            predicted = False
        key = ("pass" if predicted else "fail") + (
            "_labeled_pass" if label_pass else "_labeled_fail"
        )
        judge_only[key] += 1

        for cat in p["category"]:
            slot = by_category.setdefault(
                cat, {"n": 0, "predicted_pass": 0, "predicted_fail": 0,
                      "labeled_pass": 0, "labeled_fail": 0}
            )
            slot["n"] += 1
            slot["predicted_pass" if predicted else "predicted_fail"] += 1
            slot["labeled_pass" if label_pass else "labeled_fail"] += 1

        for axis in p["failureAxes"]:
            slot = axis_detection.setdefault(axis, {"n": 0, "detected": 0})
            slot["n"] += 1
            if not judge["available"]:
                continue
            axes = judge["axes"]
            mapped = _AXIS_TO_JUDGE.get(axis)
            if mapped is not None:
                judge_axis, expected = mapped
                if axes[judge_axis] is expected:
                    slot["detected"] += 1
            elif axis == "pose_tolerance":
                # 대응 judge 축 없음 — 보존 축이 하나라도 거짓이면 "전면 재생성"을
                # 잡아낸 것으로 본다 (31-05 프롬프트가 지시하는 동작).
                if any(axes[a] is False for a in _PRESERVATION_AXES):
                    slot["detected"] += 1

    return {
        "sample_counts": {
            "total": len(pairs),
            "labeled_pass": sum(1 for p in pairs if p["label"] == "PASS"),
            "labeled_fail": sum(1 for p in pairs if p["label"] == "FAIL"),
            "judge_available": sum(1 for p in pairs if p["judge"]["available"]),
            "pose_measured": sum(
                1 for p in pairs if p["pose"]["status"] == POSE_STATUS_MEASURED
            ),
        },
        "judge_only_confusion": judge_only,
        "by_category": by_category,
        "failure_axis_detection": axis_detection,
        "failure_axes_present": sorted({a for p in pairs for a in p["failureAxes"]}),
    }


# ── main ─────────────────────────────────────────────────────────────────


def _parse_floats(text: str) -> tuple[float, ...]:
    return tuple(float(x) for x in text.split(","))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-judge-calls", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true", help="측정 없이 manifest 계약만 검증")
    ap.add_argument("--pose-url", default=None, help="/pose-image URL (미지정 시 오프라인 keypoint 만)")
    ap.add_argument("--pose-token-env", default="RUNPOD_AUTH_TOKEN")
    ap.add_argument(
        "--generator",
        default=DEFAULT_GENERATOR_SCOPE,
        help="calibration scope 생성 모델 ('all' = 전체)",
    )
    ap.add_argument("--pose-tol-grid", default=None)
    ap.add_argument("--confidence-grid", default=None)
    ap.add_argument("--judge-cache", default=None, help="judge raw 캐시 JSON (재실행 과금 0)")
    args = ap.parse_args()

    pose_tol_grid = (
        _parse_floats(args.pose_tol_grid) if args.pose_tol_grid else DEFAULT_POSE_TOL_GRID
    )
    confidence_grid = (
        _parse_floats(args.confidence_grid)
        if args.confidence_grid
        else DEFAULT_CONFIDENCE_GRID
    )

    manifest_path = Path(args.manifest)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    entries = manifest["fixtures"]

    scope = args.generator
    in_scope = [
        e for e in entries if scope == "all" or e.get("generatorModel") == scope
    ]

    excluded: list[dict] = []
    valid: list[dict] = []
    for entry in in_scope:
        reason = validate_pair(entry)
        if reason:
            excluded.append({"id": entry.get("id"), "reason": reason})
        else:
            valid.append(entry)

    if args.dry_run:
        print(f"manifest      : {manifest_path}")
        print(f"scope         : {scope}")
        print(f"in scope      : {len(in_scope)} / {len(entries)}")
        print(f"contract ok   : {len(valid)}")
        print(f"excluded      : {len(excluded)} {excluded if excluded else ''}")
        pass_n = sum(1 for e in valid if e["label"] == "PASS")
        fail_n = len(valid) - pass_n
        print(f"labels        : PASS={pass_n} FAIL={fail_n} (floor {FLOOR_PASS}/{FLOOR_FAIL})")
        kp = [validate_keypoint_provenance(e) for e in valid]
        print(f"keypoint src  : measurable={sum(1 for r in kp if r is None)} / {len(valid)}")
        print(f"grid cells    : {len(pose_tol_grid) * len(confidence_grid)}")
        print(f"judge calls   : would be {len(valid)} (cap {args.max_judge_calls})")
        return 0

    cache: dict[str, dict] = {}
    cache_path = Path(args.judge_cache) if args.judge_cache else None
    if cache_path and cache_path.is_file():
        cache = json.loads(cache_path.read_text())

    pose_token = os.environ.get(args.pose_token_env, "")
    max_tol = max(pose_tol_grid)

    pairs: list[dict] = []
    judge_calls = 0
    stopped_early = False
    for entry in valid:
        cache_key = entry["afterSha256"]
        if cache_key in cache:
            judge_raw = cache[cache_key]
        else:
            if judge_calls >= args.max_judge_calls:
                stopped_early = True
                break
            judge_raw = measure_judge(entry)
            judge_calls += 1
            cache[cache_key] = judge_raw

        if validate_keypoint_provenance(entry) is None:
            pose = measure_pose_from_keypoints(entry)
        elif args.pose_url and pose_token:
            pose = measure_pose_live(entry, args.pose_url, pose_token, max_tol)
        else:
            pose = {
                "status": POSE_STATUS_UNMEASURED,
                "reason": "no_keypoint_file_and_no_live_pose_endpoint",
            }

        pairs.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "jointKey": entry["jointKey"],
                "targetDeg": entry["targetDeg"],
                "beforeSha256": entry["beforeSha256"],
                "afterSha256": entry["afterSha256"],
                "generatorModel": entry.get("generatorModel"),
                "failureAxes": entry["failureAxes"],
                "category": entry["category"],
                "judge": judge_raw,
                "pose": pose,
            }
        )

    if cache_path:
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1))

    table = evaluate_grid(pairs, pose_tol_grid, confidence_grid)
    confidence_only_table = evaluate_confidence_only(pairs, confidence_grid)
    confusion = build_confusion(pairs)

    from sunity_shared.analysis import visual_gen

    pose_versions = {
        p["id"]: p["pose"].get("model_version")
        for p in pairs
        if p["pose"]["status"] == POSE_STATUS_MEASURED
    }
    meta = {
        "judge_model": "gemini-3.5-flash",
        "prompt_version": visual_gen.PROMPT_VERSION,
        "judge_axes": list(visual_gen.JUDGE_AXES),
        "pose_model_versions": pose_versions,
        # M4-05 — 단일 문자열 금지. fixture 마다 다른 pose 모델로 잰 값이 섞이면
        # 임계값이 어느 측정기의 것인지 추적 불가능해진다.
        "pose_model_version_set": sorted({str(v) for v in pose_versions.values()}),
        "ran_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "manifest_sha256": _sha256_bytes(manifest_bytes),
        "manifest_path": str(manifest_path),
        "generator_scope": scope,
        "pose_tol_grid": list(pose_tol_grid),
        "confidence_grid": list(confidence_grid),
        "judge_calls_made": judge_calls,
        "judge_call_cap": args.max_judge_calls,
        "stopped_early_on_call_cap": stopped_early,
        "excluded_pairs": excluded,
        "pose_endpoint_used": bool(args.pose_url),
        "reproduce": (
            "PYTHONPATH=backend/shared/python python3 backend/scripts/"
            f"calibrate_visual_gates.py --manifest {manifest_path.name} "
            f"--generator {scope} --pose-url <pod>/pose-image"
        ),
    }

    counts = confusion["sample_counts"]
    unmeasured = len(pairs) - counts["pose_measured"]
    blocks: list[str] = []
    if counts["labeled_pass"] < FLOOR_PASS:
        blocks.append(f"insufficient_pass_samples:{counts['labeled_pass']}<{FLOOR_PASS}")
    if counts["labeled_fail"] < FLOOR_FAIL:
        blocks.append(f"insufficient_fail_samples:{counts['labeled_fail']}<{FLOOR_FAIL}")
    if pairs and unmeasured / len(pairs) > MAX_UNMEASURED_FRACTION:
        blocks.append(
            f"pose_unmeasured_fraction:{unmeasured}/{len(pairs)}>{MAX_UNMEASURED_FRACTION}"
        )
    # confidence 축이 격자 전 구간에서 같은 FA/FR 를 내면, 그 축은 이 표본에서
    # **판별력이 없다**. 이때 "FA 최소" 규칙은 전 조합 동률이라 사실상 무작위 선택이
    # 되고, 그건 M4-03 이 금지한 arbitrary fallback 이다. 측정이 있었더라도 그 측정이
    # 임계값을 고를 근거가 되지 못한다는 사실 자체를 blocked 로 남긴다.
    distinct = {
        (r["false_accept_upper_bound"], r["false_reject_lower_bound"])
        for r in confidence_only_table
    }
    if len(confidence_only_table) > 1 and len(distinct) == 1:
        blocks.append(
            "confidence_axis_non_discriminating:"
            f"all_{len(confidence_only_table)}_grid_values_tie_at_"
            f"FA{confidence_only_table[0]['false_accept_upper_bound']}"
        )

    result: dict = {
        "table": table,
        "confidence_only_table": confidence_only_table,
        "confidence_only_note": (
            "pose 축 제외 judge 단독 스윕. production 게이트가 아니며 FA 는 상한, "
            "FR 은 하한이다 (pose 게이트는 통과 집합을 줄이기만 한다)."
        ),
        "confusion": confusion,
        "pairs": pairs,
        "meta": meta,
    }
    if blocks:
        # 하한 미달이면 chosen 을 내지 않는다 (H4-10). 부분 근거로 고른 임계값은
        # "측정된 것처럼 보이는 추정" 이고, 그게 그대로 production 게이트가 된다.
        result["blocked"] = True
        result["blocked_reasons"] = blocks
    else:
        outcome = choose_thresholds(table)
        if outcome.get("blocked"):
            result["blocked"] = True
            result["blocked_reasons"] = [outcome["reason"]]
            if "display_candidate" in outcome:
                result["display_candidate"] = outcome["display_candidate"]
        else:
            result["blocked"] = False
            result["chosen"] = outcome["chosen"]

    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"wrote {args.out}")
    print(f"pairs={len(pairs)} judge_calls={judge_calls} blocked={result.get('blocked')}")
    if result.get("blocked"):
        print("blocked_reasons: " + "; ".join(result["blocked_reasons"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
