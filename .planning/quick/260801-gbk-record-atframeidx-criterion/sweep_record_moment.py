#!/usr/bin/env python3
"""등재 10동작 일반화 스위프 — 감점별 측정 순간이 카드 프레임을 가른다 (quick-260801-gbk).

`sweep_leg_angle.py`(f5h) 구조 계승: 합성 keypoint report + 등재 10동작 축 +
**프로덕션 함수 직접 호출**. GPU 0, 네트워크 0, Pod 0.

이 스위프가 답하는 질문은 하나다 — **record 마다 측정 순간이 다르면 카드도 다른
프레임을 쓰는가.** 종전엔 모든 카드가 `worst_seconds` 한 시각에서 잘렸다.

게이트 (a)~(e):
  (a) record 2건 이상이 서로 다른 `atFrameIdx` 를 가지면 카드 `userFrameIdx` 도
      서로 다르다 — 10/10 동작에서.
  (b) `atFrameIdx` 를 전부 제거한 대조군의 PNG sha256 이 `--compare-before` 파일과
      **byte-동일** (fail-closed 무회귀). 대조군이 구현 전에 캡처돼 있어야 성립한다.
  (c) 앵커 프레임의 keypoint confidence 를 0 으로 눌러도 창 안의 다른 프레임이
      채택되고, 그 카드에는 `atMatched` 가 **없다**.
  (d) 앵커가 채택된 카드는 `atMatched=true` 이고 표시 학생 프레임이 `atFrameIdx` 와
      정확히 일치한다.
  (e) override 경로(`ref_frame_idx` 지정) 스모크 — UnboundLocalError 0.

사용:
    python3 sweep_record_moment.py --out sweep_out.before.json          # 구현 전 캡처
    python3 sweep_record_moment.py --out sweep_out.json \\
        --compare-before sweep_out.before.json                          # 구현 후 대조

프로덕션 코드 아님 — quick 디렉터리 로컬 하네스.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
from PIL import Image

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

_CRITERIA_DIR = _REPO / "backend" / "judging_data" / "criteria"
_ASSETS = (
    _REPO / ".planning" / "phases" / "33-result-trust-recovery" / "mockups" / "assets"
)

_FPS = 9.0
_N_FRAMES = 24

# 앱/백엔드 공유 매핑 미러 (pipeline._KISMAM_TO_KEYPOINT).
_ANGLE_MAP = {
    "left_elbow": "left_elbow", "right_elbow": "right_elbow",
    "left_shoulder": "left_shoulder", "right_shoulder": "right_shoulder",
    "left_hip": "left_hip", "right_hip": "right_hip",
    "left_knee": "left_knee", "right_knee": "right_knee",
}

# 학생 = 12관절(32-14). 기준 = phase4_v1 legacy 8관절 (ankle/elbow 부재가 실제 형상).
_USER_KP = {
    "left_shoulder": (0.564, 0.397), "right_shoulder": (0.612, 0.372),
    "left_hip": (0.505, 0.475), "right_hip": (0.548, 0.462),
    "left_knee": (0.402, 0.628), "right_knee": (0.612, 0.652),
    "left_hand": (0.470, 0.196), "right_hand": (0.628, 0.184),
    "left_ankle": (0.336, 0.828), "right_ankle": (0.680, 0.848),
    "left_elbow": (0.516, 0.336), "right_elbow": (0.640, 0.288),
}
_REF_KP = {
    "left_shoulder": (0.520, 0.352), "right_shoulder": (0.586, 0.336),
    "left_hip": (0.488, 0.492), "right_hip": (0.540, 0.480),
    "left_knee": (0.430, 0.664), "right_knee": (0.600, 0.680),
    "left_hand": (0.446, 0.164), "right_hand": (0.604, 0.152),
}


class _Match:
    def __init__(self, start: int, path: list) -> None:
        self.start = start
        self.path = path


def _identity(n: int) -> _Match:
    return _Match(start=0, path=[(i, i) for i in range(n)])


def _report(n: int, fps: float, xy: dict, low_conf_frames=()) -> dict:
    """합성 keypointReport. low_conf_frames 의 프레임만 confidence 0."""
    joints = list(xy)
    data: list[float] = []
    conf: list[float] = []
    low = set(low_conf_frames)
    for f in range(n):
        for j in joints:
            data += list(xy[j])
            conf.append(0.0 if f in low else 0.9)
    return {
        "joints": joints, "frames": n, "fps": fps,
        "data": data, "confidence": conf,
    }


def _load_frames(path: pathlib.Path, n: int) -> np.ndarray:
    """같은 스틸을 n장으로 복제하되 프레임마다 1px 값을 흔들어 **프레임 구분 가능**하게.

    전부 동일하면 "카드가 다른 프레임을 골랐다"를 PNG 로 확인할 수 없다 — 프레임
    선택이 실제로 갈렸는지 픽셀로 보이게 하기 위한 최소 표식이다.
    """
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    stack = np.repeat(a[None, ...], n, axis=0)
    for f in range(n):
        stack[f, 0, 0, :] = np.uint8((f * 7) % 256)
    return stack


def _registered_motions() -> list[str]:
    """등재 동작 = criteria glob 파생 (동작명 하드코딩 0)."""
    return sorted(p.stem for p in _CRITERIA_DIR.glob("*.yaml"))


def _criteria_joints(motion: str) -> list[str]:
    import yaml

    data = yaml.safe_load((_CRITERIA_DIR / f"{motion}.yaml").read_text("utf-8")) or {}
    block = data.get("criteria") or {}
    out: list[str] = []
    for entries in block.values():
        for e in entries or []:
            j = (e or {}).get("joint")
            if isinstance(j, str) and j and j not in out:
                out.append(j)
    return out


def _records_for(motion: str, n_units: int = 3) -> list[dict]:
    """그 동작의 감점 record 목록 — criterion 은 데이터 파생, 순간은 서로 다르게.

    production 이 방출하는 두 갈래를 모두 덮는다:
      (a) criteria yaml 의 관절 (동작별로 다름)
      (b) reference_relative per-joint — 편차 있는 모든 kismam angle key

    **양쪽 report 에 다 있는 관절로 한정한다.** 합성 기준 report 에 없는 관절
    (팔꿈치 — phase4_v1 legacy 8관절 형상)로 만든 카드는 crop 단계에서 통째로
    떨어져 나가고, 그러면 이 스위프가 재려는 것(프레임 선택)이 아니라 관절 커버리지를
    재게 된다. 동작명 분기가 아니라 **report 관절 집합 파생** 규칙이다.
    """
    crits: list[str] = []
    for jk in [*_criteria_joints(motion), *_ANGLE_MAP]:
        kp = _ANGLE_MAP.get(jk)
        if kp is None or kp not in _REF_KP or kp not in _USER_KP:
            continue
        crit = f"{fz.ANGLE_VS_REFERENCE_PREFIX}{jk}"
        if crit not in crits:
            crits.append(crit)
    crits = crits[:n_units]
    # 순간을 **서로 다르게** 준다 — 이것이 스위프의 독립변수다.
    out = []
    for i, crit in enumerate(crits):
        frame = 4 + i * 5  # 4, 9, 14 ... 전부 _N_FRAMES 안
        out.append({
            "criterion": crit,
            "atFrameIdx": frame,
            "atVideoSec": frame / _FPS,
            "unit": "deg",
            "source": "geometry",
        })
    return out


def _frame_sources() -> list[tuple[pathlib.Path, pathlib.Path]]:
    stills = sorted(_ASSETS.glob("belle_still_f0*.png"))
    if not stills:
        raise SystemExit(f"스틸 자산 없음: {_ASSETS}")
    return [(stills[i], stills[(i + 3) % len(stills)]) for i in range(len(stills))]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _build(user_frames, ref_frames, user_rep, ref_rep, units, **kw):
    joints: list[str] = []
    for u in units:
        for j in u["joints"]:
            if j not in joints:
                joints.append(j)
    return fz.build_fault_zoom_comparisons(
        user_frames, ref_frames, user_rep, ref_rep,
        worst_seconds=1.0,
        fault_joints=joints,
        joint_deltas={j: 24.0 + i for i, j in enumerate(joints)},
        frames_fps=_FPS,
        joint_kinds={j: "deficit" for j in joints},
        dtw_match=_identity(_N_FRAMES),
        criterion_units=units,
        **kw,
    )


def _units(records):
    """record → crop unit (프로덕션 함수 직접 호출 — 규칙 복제 0)."""
    return fz.criterion_units_from_records(
        list(records), list(_ANGLE_MAP.values()), dict(_ANGLE_MAP), max_units=4
    )


def _strip_moments(records):
    out = []
    for r in records:
        c = dict(r)
        c.pop("atFrameIdx", None)
        c.pop("atVideoSec", None)
        out.append(c)
    return out


def run(out_path: pathlib.Path, before_path: pathlib.Path | None) -> int:
    motions = _registered_motions()
    pairs = _frame_sources()
    before = None
    if before_path is not None and before_path.exists():
        before = json.loads(before_path.read_text("utf-8"))

    rows: list[dict] = []
    fail: list[str] = []

    for mi, motion in enumerate(motions):
        u_path, r_path = pairs[mi % len(pairs)]
        u_frames = _load_frames(u_path, _N_FRAMES)
        r_frames = _load_frames(r_path, _N_FRAMES)
        user_rep = _report(_N_FRAMES, _FPS, _USER_KP)
        ref_rep = _report(_N_FRAMES, _FPS, _REF_KP)
        records = _records_for(motion)
        units = _units(records)
        # window 후보 = worst_seconds 주변 (프로덕션이 주는 sourceFrameIndices 형상).
        u_cands = [8, 9, 10, 11, 12]
        r_cands = [8, 9, 10, 11, 12]

        # ── (a)(d) 앵커 경로 ────────────────────────────────────────────────
        comps = _build(
            u_frames, r_frames, user_rep, ref_rep, units,
            user_frame_candidates=u_cands, ref_frame_candidates=r_cands,
            analysis_id=f"sweep-{motion}",
        )
        by_crit = {c.get("criterion"): c for c in comps}
        at_by_crit = {r["criterion"]: r["atFrameIdx"] for r in records}
        user_frames_seen = [c.get("userFrameIdx") for c in comps]
        distinct = len(set(user_frames_seen)) == len(user_frames_seen)
        expected_distinct = len({at_by_crit[c.get("criterion")] for c in comps}) == len(comps)
        if len(comps) >= 2 and expected_distinct and not distinct:
            fail.append(
                f"(a) {motion}: record 순간이 다른데 카드 프레임이 같다 "
                f"{user_frames_seen}"
            )
        matched_ok = []
        for c in comps:
            crit = c.get("criterion")
            want = at_by_crit.get(crit)
            if c.get("atMatched") is True:
                matched_ok.append(crit)
                if c.get("userFrameIdx") != want:
                    fail.append(
                        f"(d) {motion}/{crit}: atMatched=true 인데 표시 프레임 "
                        f"{c.get('userFrameIdx')} != atFrameIdx {want}"
                    )
        if len(comps) >= 2 and not matched_ok:
            fail.append(f"(d) {motion}: atMatched=true 카드가 하나도 없다")

        # ── (b) fail-closed 대조군 — atFrameIdx 전부 제거 ────────────────────
        legacy_units = _units(_strip_moments(records))
        legacy = _build(
            u_frames, r_frames, user_rep, ref_rep, legacy_units,
            user_frame_candidates=u_cands, ref_frame_candidates=r_cands,
            analysis_id=f"sweep-{motion}",
        )
        legacy_hashes = [_sha(c["png"]) for c in legacy]
        legacy_frames = [c.get("userFrameIdx") for c in legacy]
        if any(c.get("atMatched") is not None for c in legacy):
            fail.append(f"(b) {motion}: 앵커 없는 카드에 atMatched 가 붙었다")

        # ── (c) 앵커 프레임 keypoint 붕괴 → 창 안 다른 프레임 채택 ───────────
        anchor_frames = sorted({r["atFrameIdx"] for r in records})
        crushed_rep = _report(_N_FRAMES, _FPS, _USER_KP, low_conf_frames=anchor_frames)
        crushed = _build(
            u_frames, r_frames, crushed_rep, ref_rep, units,
            user_frame_candidates=u_cands, ref_frame_candidates=r_cands,
            analysis_id=f"sweep-{motion}",
        )
        crushed_rows = []
        for c in crushed:
            crit = c.get("criterion")
            crushed_rows.append({
                "criterion": crit,
                "userFrameIdx": c.get("userFrameIdx"),
                "atMatched": c.get("atMatched"),
            })
            if c.get("atMatched") is True and c.get("userFrameIdx") in anchor_frames:
                # 앵커 프레임 keypoint 가 붕괴했는데 그대로 채택했다면 confidence
                # 선택이 죽은 것이다.
                fail.append(
                    f"(c) {motion}/{crit}: 앵커 붕괴에도 앵커 프레임을 그대로 채택"
                )

        # ── (e) override 경로 스모크 — UnboundLocalError 0 ───────────────────
        override_err = None
        try:
            ov = _build(
                u_frames, r_frames, user_rep, ref_rep, units,
                user_frame_candidates=u_cands, ref_frame_candidates=r_cands,
                ref_frame_idx=6, analysis_id=f"sweep-{motion}",
            )
            override_n = len(ov)
        except Exception as exc:  # noqa: BLE001 — 게이트가 잡아야 할 대상
            override_err = f"{type(exc).__name__}: {exc}"
            override_n = 0
            fail.append(f"(e) {motion}: override 경로 예외 {override_err}")

        row = {
            "motion": motion,
            "records": [
                {"criterion": r["criterion"], "atFrameIdx": r["atFrameIdx"]}
                for r in records
            ],
            "cards": [
                {
                    "criterion": c.get("criterion"),
                    "userFrameIdx": c.get("userFrameIdx"),
                    "refFrameIdx": c.get("refFrameIdx"),
                    "atMatched": c.get("atMatched"),
                    "userVideoSec": c.get("userVideoSec"),
                    "png_sha256": _sha(c["png"]),
                }
                for c in comps
            ],
            "distinct_user_frames": distinct,
            "legacy_control": {
                "png_sha256": legacy_hashes,
                "userFrameIdx": legacy_frames,
            },
            "anchor_crushed": crushed_rows,
            "override_cards": override_n,
            "override_error": override_err,
        }
        rows.append(row)

        # (b) 대조 — before 캡처와 byte-동일해야 한다.
        if before is not None:
            prev = next(
                (r for r in before["rows"] if r["motion"] == motion), None
            )
            if prev is None:
                fail.append(f"(b) {motion}: before 캡처에 없는 동작")
            elif prev["legacy_control"]["png_sha256"] != legacy_hashes:
                fail.append(
                    f"(b) {motion}: fail-closed 대조군 PNG 해시가 변했다\n"
                    f"      before={prev['legacy_control']['png_sha256']}\n"
                    f"      after ={legacy_hashes}"
                )

    payload = {
        "motions": motions,
        "rows": rows,
        "gates": {
            "a_distinct_frames": sum(1 for r in rows if r["distinct_user_frames"]),
            "b_compared_against": str(before_path) if before is not None else None,
            "total_motions": len(rows),
        },
        "failures": fail,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")

    print(f"동작 {len(rows)}개 · 산출 {out_path}")
    print(f"(a) 카드 프레임 상이: {payload['gates']['a_distinct_frames']}/{len(rows)}")
    if before is not None:
        print(f"(b) fail-closed 대조군: {before_path.name} 과 대조 완료")
    else:
        print("(b) 대조군 캡처 모드 (--compare-before 미지정)")
    if fail:
        print(f"\nFAIL {len(fail)}건:")
        for f in fail:
            print(f"  - {f}")
        return 1
    print("\nPASS — 게이트 (a)~(e) 전부 통과")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare-before", default=None)
    a = ap.parse_args()
    before = pathlib.Path(a.compare_before) if a.compare_before else None
    return run(pathlib.Path(a.out), before)


if __name__ == "__main__":
    raise SystemExit(main())
