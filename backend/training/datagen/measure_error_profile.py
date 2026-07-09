"""실 RTMW 오류 분포 측정 → rtmw_error_profile.json (22-01 Task 2, A3 해소).

이 스크립트는 합성 교란(perturb.py)의 유일한 수치 근거를 실측으로 박제한다. NLM 이
제안한 교란 수치(3~5프레임 Null, 5% 지터 등)는 소스 직접 근거가 없음이 자인됐다
(22-RESEARCH Pitfall 4, A3). 그래서 여기서는 **교란 수치를 만들지 않고**, 우리
파이프라인이 실제로 낸 RTMW 오류의 '분포'만 측정한다. perturb.py 가 이 분포에서
샘플한다.

[[scoring-redesign-must-generalize-no-overfit]] 정신: 보유 영상 점수에 curve-fit 하는
것이 아니라 오류 '분포'를 측정하는 것이다 — 특정 영상이 아니라 전체 히스토그램이
교란 설계의 기준이다.

측정 3종 (전부 집계 히스토그램 — 개별 식별자 미포함, T-22-01):
  1. confidence_drop_run_length — 연속 저신뢰 프레임 구간 길이 분포
     (keypointReport.confidence 를 (frames, J)로 reshape, 저신뢰 run-length).
  2. per_joint_jump_deg — 관절별 프레임간 각도 점프 크기 분포
     (top-level angles (T,J) flat 시계열의 프레임간 절대차, anglesJointKeys 별).
  3. low_confidence_joint_rank — 저신뢰 관절 빈도 순위.

데이터 소스: Firestore `users/{uid}/analyses` 실사용 문서(collection_group) — angles +
anglesJointKeys + anglesFrames 재구성 + result.keypointReport(confidence 채널). 읽기
전용, firestore_admin 기존 클라이언트 재사용. reference/{id}/versions/phase4_v1 은
선택적 보강.

T-22-01 (Info Disclosure 방어): 산출 artifact 에 uid·영상 URL·문서 식별자를 절대
포함하지 않는다 — 히스토그램 집계값 + `_meta`(문서 수만) 만 저장. 쓰기 직전
_assert_no_identifiers 로 화이트리스트 검증.

CLI:
  FIREBASE_SA_PATH=$(pwd)/firebase-sa.json python3 backend/training/datagen/measure_error_profile.py --dry-run
  FIREBASE_SA_PATH=$(pwd)/firebase-sa.json python3 backend/training/datagen/measure_error_profile.py --limit 400
  (AWS SSM 환경은 FIREBASE_SA_PARAM 자동 — auth._load_service_account 3경로)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[2]
_SHARED = _BACKEND / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

SCRIPT_VERSION = "measure-error-profile-v1.0"
OUT_PATH = _HERE.parent / "rtmw_error_profile.json"

# ── 측정 정의 (교란 수치가 아니라 '관측 기준') ──
# 저신뢰 임계 = RTMW 키포인트가 신뢰 불가로 간주되는 confidence 하한. 이는 오류를
# 어떻게 '관측'하는지의 정의일 뿐 교란 강도가 아니다 (_meta.measurement 로 투명 노출).
LOW_CONFIDENCE_THRESHOLD = 0.3
# 히스토그램 bin edges (관측 격자 — perturb 는 이 분포에서 샘플).
JUMP_DEG_BIN_EDGES = [float(e) for e in np.arange(0.0, 92.5, 2.5)]  # 0~90도, 2.5도 격자.
RUN_LENGTH_MAX = 30  # run-length 히스토그램 상한(초과는 마지막 bin overflow).


def _iter_analyses(db, limit: int):
    """collection_group('analyses') 스트림 (읽기 전용). 문서 id/uid 를 밖으로 내보내지
    않는다 — 호출자는 to_dict() 페이로드만 소비한다 (T-22-01)."""
    q = db.collection_group("analyses")
    if limit:
        q = q.limit(limit)
    for snap in q.stream():
        yield snap.to_dict() or {}


def _reshape_angles(data: dict):
    """top-level angles(flat) → (T, J) + joint_keys. 형상 불량이면 None."""
    angles = data.get("angles")
    joint_keys = data.get("anglesJointKeys")
    frames = data.get("anglesFrames")
    if not angles or not joint_keys or not frames:
        return None
    j = len(joint_keys)
    t = int(frames)
    if j <= 0 or t <= 0 or len(angles) != t * j:
        return None
    try:
        arr = np.asarray(angles, dtype=float).reshape(t, j)
    except (ValueError, TypeError):
        return None
    return arr, list(joint_keys)


def _reshape_confidence(data: dict):
    """result.keypointReport.confidence(flat) → (frames, J) + joint names. 불량이면 None."""
    kp = (data.get("result") or {}).get("keypointReport") or {}
    conf = kp.get("confidence")
    joints = kp.get("joints")
    frames = kp.get("frames")
    if not conf or not joints or not frames:
        return None
    j = len(joints)
    t = int(frames)
    if j <= 0 or t <= 0 or len(conf) != t * j:
        return None
    try:
        arr = np.asarray(conf, dtype=float).reshape(t, j)
    except (ValueError, TypeError):
        return None
    return arr, list(joints)


def _low_conf_runs(conf_col: np.ndarray) -> list[int]:
    """단일 관절 confidence 시계열 → 연속 저신뢰 run-length 리스트."""
    runs: list[int] = []
    cur = 0
    for v in conf_col:
        if np.isfinite(v) and v < LOW_CONFIDENCE_THRESHOLD:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    return runs


class _Accumulator:
    """분포 누적기 — 문서를 순회하며 히스토그램 substrate 만 모은다 (식별자 미보유)."""

    def __init__(self) -> None:
        self.run_lengths: list[int] = []
        self.per_joint_jumps: dict[str, list[float]] = {}
        self.low_conf_frames: dict[str, int] = {}
        self.total_frames: dict[str, int] = {}
        self.angle_doc_count = 0
        self.conf_doc_count = 0

    def add_angles(self, arr: np.ndarray, joint_keys: list[str]) -> None:
        if arr.shape[0] < 2:
            return
        jumps = np.abs(np.diff(arr, axis=0))  # (T-1, J) 프레임간 절대차(도).
        for j, key in enumerate(joint_keys):
            col = jumps[:, j]
            finite = col[np.isfinite(col)]
            if finite.size:
                self.per_joint_jumps.setdefault(key, []).extend(finite.tolist())
        self.angle_doc_count += 1

    def add_confidence(self, arr: np.ndarray, joints: list[str]) -> None:
        for j, name in enumerate(joints):
            col = arr[:, j]
            self.run_lengths.extend(_low_conf_runs(col))
            low = int(np.sum(np.isfinite(col) & (col < LOW_CONFIDENCE_THRESHOLD)))
            self.low_conf_frames[name] = self.low_conf_frames.get(name, 0) + low
            self.total_frames[name] = self.total_frames.get(name, 0) + int(col.size)
        self.conf_doc_count += 1


def _histogram(values, bin_edges) -> dict:
    counts, edges = np.histogram(np.asarray(values, dtype=float), bins=bin_edges)
    return {
        "bin_edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
        "count": int(len(values)),
    }


def _run_length_histogram(run_lengths: list[int]) -> dict:
    edges = list(range(1, RUN_LENGTH_MAX + 2))  # 1..30 정수 bin + overflow edge.
    clipped = [min(r, RUN_LENGTH_MAX) for r in run_lengths]
    counts, _ = np.histogram(np.asarray(clipped, dtype=float), bins=edges)
    return {
        "bin_edges": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
        "count": int(len(run_lengths)),
    }


def build_profile(acc: _Accumulator, source_doc_count: int) -> dict:
    """누적기 → rtmw_error_profile.json 페이로드 (집계 히스토그램만)."""
    per_joint = {
        key: _histogram(vals, JUMP_DEG_BIN_EDGES)
        for key, vals in sorted(acc.per_joint_jumps.items())
    }
    rank = sorted(
        (
            {
                "joint": name,
                "low_conf_frames": acc.low_conf_frames.get(name, 0),
                "total_frames": acc.total_frames.get(name, 0),
                "low_conf_fraction": round(
                    acc.low_conf_frames.get(name, 0)
                    / max(1, acc.total_frames.get(name, 0)),
                    6,
                ),
            }
            for name in acc.total_frames
        ),
        key=lambda r: r["low_conf_fraction"],
        reverse=True,
    )
    return {
        "_meta": {
            "script_version": SCRIPT_VERSION,
            "captured_epoch": int(time.time()),
            "source_doc_count": int(source_doc_count),
            "angle_doc_count": int(acc.angle_doc_count),
            "confidence_doc_count": int(acc.conf_doc_count),
            "measurement": {
                "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
                "jump_deg_bin_step": 2.5,
                "run_length_max": RUN_LENGTH_MAX,
            },
            "note": (
                "aggregate histograms only — no uid/video/identifier (T-22-01). "
                "measures RTMW error DISTRIBUTION, not per-video curve-fit."
            ),
        },
        "confidence_drop_run_length": _run_length_histogram(acc.run_lengths),
        "per_joint_jump_deg": per_joint,
        "low_confidence_joint_rank": rank,
    }


# ── T-22-01: 식별자 누출 방어 (쓰기 직전 화이트리스트 검증) ──
_META_ALLOWED = {
    "script_version",
    "captured_epoch",
    "source_doc_count",
    "angle_doc_count",
    "confidence_doc_count",
    "measurement",
    "note",
}
_TOP_ALLOWED = {
    "_meta",
    "confidence_drop_run_length",
    "per_joint_jump_deg",
    "low_confidence_joint_rank",
}


def _assert_no_identifiers(profile: dict) -> None:
    """artifact 키 화이트리스트 + _meta 에 문서 수 외 값 부재 검증 (T-22-01)."""
    extra_top = set(profile) - _TOP_ALLOWED
    if extra_top:
        raise ValueError(f"artifact top-level 화이트리스트 위반: {sorted(extra_top)}")
    extra_meta = set(profile.get("_meta", {})) - _META_ALLOWED
    if extra_meta:
        raise ValueError(f"_meta 화이트리스트 위반(식별자 누출 위험): {sorted(extra_meta)}")


def measure(limit: int) -> dict:
    from sunity_shared import firestore_admin as fa

    db = fa._db()
    acc = _Accumulator()
    source_doc_count = 0
    for data in _iter_analyses(db, limit):
        used = False
        angles = _reshape_angles(data)
        if angles is not None:
            acc.add_angles(*angles)
            used = True
        conf = _reshape_confidence(data)
        if conf is not None:
            acc.add_confidence(*conf)
            used = True
        if used:
            source_doc_count += 1
    return build_profile(acc, source_doc_count)


def dry_run(limit: int) -> dict:
    """소스 카운트만 — 실측 없이 유효 문서 수를 센다."""
    from sunity_shared import firestore_admin as fa

    db = fa._db()
    angle_ok = conf_ok = either = 0
    for data in _iter_analyses(db, limit):
        a = _reshape_angles(data) is not None
        c = _reshape_confidence(data) is not None
        angle_ok += int(a)
        conf_ok += int(c)
        either += int(a or c)
    return {"angle_docs": angle_ok, "confidence_docs": conf_ok, "usable_docs": either}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="실 RTMW 오류 분포 측정 (A3 해소)")
    parser.add_argument("--dry-run", action="store_true", help="소스 카운트만 출력")
    parser.add_argument("--limit", type=int, default=0, help="문서 상한 (0=전체)")
    args = parser.parse_args(argv)

    if args.dry_run:
        counts = dry_run(args.limit)
        print("[dry-run]", json.dumps(counts, ensure_ascii=False))
        return 0

    profile = measure(args.limit)
    _assert_no_identifiers(profile)
    n = profile["_meta"]["source_doc_count"]
    OUT_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[ok] wrote {OUT_PATH.name} source_doc_count={n}")
    if n < 30:
        print(
            f"[warn] source_doc_count={n} < 30 — reference 데이터 보강 후 재측정 필요 "
            "(P2-2201: print-only 통과 금지)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
