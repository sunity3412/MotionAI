"""reference 11개 doc 의 angles fps 실측 — Phase 28 Wave 0 1회성 (28-RESEARCH A1).

목적 (28-RESEARCH Pitfall 1 / Assumption A1 해소):
  학생 angles 는 9fps(`FfmpegFrameExtractor` 기본)인데 활성 reference 11개의 angles 는
  phase4_v1 재처리 때 `--target-fps 18.0` 으로 생성됐다고 코드/주석이 시사한다
  (reprocess_reference_motions_phase4.py:427 default 18.0,
  backfill_reference_downstream.py:131 주석). dtw path 의 ref 인덱스가 어느 fps 공간인지에
  따라 정렬 맵 계약(초 단위 방출, 28-CONTEXT D-01)의 전제가 좌우되므로 **live doc 로
  실측**한다. 정렬 맵은 프레임 인덱스가 아닌 초로 방출하고 fps 는 doc 메타에서 읽는
  설계라 fps 실측값이 18.0 이 아니어도 계약 설계는 방어된다 — 여기서는 판정 (a)(b) 만 본다.

판정 (doc 별):
  (a) anglesFrames == keypointReport.frames — angles 와 keypointReport 가 같은 재처리
      산출(같은 frame 축)이라는 fault_zoom 표시 경로 fix 의 clamp 도메인 전제.
  (b) keypointReport.fps > 0 — fps 를 doc 메타에서 읽는 설계의 최소 요건.

출력 (doc 별): id, activeVersion, keypointReport.fps, keypointReport.frames,
  anglesFrames, anglesFrames / keypointReport.fps (= angles 재생 길이 초).
  판정 실패 doc 이 하나라도 있으면 exit 1 (실패 id 출력). 전부 통과면
  "A1 RESOLVED: N docs, fps set={...}" 출력 후 exit 0.

읽기 전용 — get 만 사용. 어떤 write 연산(set/update/delete)도 없음 (T-28-01, read-only 강제).
credential = auth._ensure_firebase (FIREBASE_SA_PATH=firebase-sa.json 로컬 SA — Pod 아님):
  cd backend && PYTHONPATH=shared/python:. FIREBASE_SA_PATH=../firebase-sa.json \\
      python3 scripts/measure_reference_fps.py

재사용 가능 — 향후 reference 재처리 후 fps 도메인 재확인 시 재실행.
[per [[reference-library-phase4-all11]], 28-RESEARCH Pitfall 1 / A1]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# sys.path 주입 — shared/python layer (backfill_reference_downstream.py:69 패턴, `-m` 미사용).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared" / "python"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("measure_reference_fps")


# ── 11-id 전체 motion 상수 ([[reference-library-phase4-all11]], backfill ALL_MOTION_IDS 정합) ──
# 절대 5-subset default 금지 — 전 active doc 실측이 A1 해소 조건.
ALL_MOTION_IDS: tuple[str, ...] = (
    # 원본 5
    "ref-climb",
    "ref-foxtop",
    "ref-foxtop-split",
    "ref-invert",
    "ref-sideway-spin",
    # 후속 6
    "ref-combo",
    "ref-elbow-twist-sister",
    "ref-kip-up",
    "ref-pdshape",
    "ref-peter-pan",
    "ref-power-spin",
)


def _measure() -> int:
    # lazy import — 의존성 부재 시 fail-fast 는 실행 시점 (Mac `--help` exit 0 관례).
    try:
        from sunity_shared import auth as _auth
        from sunity_shared import firestore_admin
    except ImportError as e:  # pragma: no cover
        log.error("sunity_shared import 실패: %s", e)
        return 2

    # credential gate — SA 소스 = FIREBASE_SA_* (hand-rolled Certificate 금지, backfill 관례).
    try:
        _auth._ensure_firebase()
    except Exception as e:  # noqa: BLE001 — credential 실패는 actionable 메시지로.
        log.error(
            "Firebase SA 미마운트/미설정 — FIREBASE_SA_PATH=firebase-sa.json (로컬 SA) 필요. (%s)",
            e,
        )
        return 2

    failed: list[str] = []
    fps_set: set[float] = set()
    ok_count = 0

    for mid in ALL_MOTION_IDS:
        try:
            doc = firestore_admin.get_reference_motion(mid)  # read-only get
        except Exception as e:  # noqa: BLE001
            log.error("[%s] FAIL — read error: %s", mid, e)
            failed.append(mid)
            continue
        if doc is None:
            log.error("[%s] FAIL — reference doc 없음", mid)
            failed.append(mid)
            continue

        active_version = doc.get("activeVersion")
        angles_frames = doc.get("anglesFrames")
        kr = doc.get("keypointReport") or {}
        kr_fps = kr.get("fps") if isinstance(kr, dict) else None
        kr_frames = kr.get("frames") if isinstance(kr, dict) else None

        # (b) keypointReport.fps > 0 (판정 + 타입 방어).
        try:
            fps_val = float(kr_fps) if kr_fps is not None else 0.0
        except (TypeError, ValueError):
            fps_val = 0.0
        fps_ok = fps_val > 0.0

        # angles 재생 길이 초 = anglesFrames / fps (fps>0 일 때만 의미).
        try:
            n_angles_frames = int(angles_frames) if angles_frames is not None else -1
        except (TypeError, ValueError):
            n_angles_frames = -1
        seconds = (n_angles_frames / fps_val) if (fps_ok and n_angles_frames >= 0) else None

        # (a) anglesFrames == keypointReport.frames.
        try:
            n_kr_frames = int(kr_frames) if kr_frames is not None else -1
        except (TypeError, ValueError):
            n_kr_frames = -1
        frames_match = n_angles_frames >= 0 and n_angles_frames == n_kr_frames

        log.info(
            "[%s] activeVersion=%s keypointReport.fps=%s keypointReport.frames=%s "
            "anglesFrames=%s seconds=%s",
            mid,
            active_version,
            kr_fps,
            kr_frames,
            angles_frames,
            f"{seconds:.2f}" if seconds is not None else "n/a",
        )

        if not fps_ok:
            log.error("[%s] FAIL (b) — keypointReport.fps 미양수: %r", mid, kr_fps)
            failed.append(mid)
            continue
        if not frames_match:
            log.error(
                "[%s] FAIL (a) — anglesFrames(%d) != keypointReport.frames(%d)",
                mid,
                n_angles_frames,
                n_kr_frames,
            )
            failed.append(mid)
            continue

        fps_set.add(fps_val)
        ok_count += 1

    if failed:
        log.error(
            "A1 UNRESOLVED — 판정 실패 docs: %s (총 %d/%d 실패)",
            failed,
            len(failed),
            len(ALL_MOTION_IDS),
        )
        return 1

    log.info(
        "A1 RESOLVED: %d docs, fps set=%s",
        ok_count,
        sorted(fps_set),
    )
    return 0


if __name__ == "__main__":
    sys.exit(_measure())
