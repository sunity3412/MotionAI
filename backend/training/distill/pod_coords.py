"""Pod RTMW 좌표 추출 — 학습 JSONL 과 동일한 서브샘플 좌표 행 생성 (22-04 Task 3 선행).

시험 배치(run_trial_batch)에 주입할 RTMW 좌표를 Pod(GPU)에서 미리 추출·캐시한다.
Gemini 무접촉 — 좌표 추출만(과금 0). 이 모듈은 라벨/판정을 만들지 않는다.

── 좌표 표현 계약 (build_jsonl.py + schema.py 정합, 최우선 불변식) ──
학습 JSONL 의 좌표 행은 `_coords_to_frames` 가 discretize(상대좌표 ×1000 = 000~999)로
조립한다(schema §Pattern 2). 시험 좌표가 이와 다르면 시험의 대표성이 무너지므로
(22-04 Task 3), 본 모듈은 build_jsonl._coords_to_frames 를 그대로 재사용해 표현을 고정한다.

좌표 소스 = PoseFrame.keypoints_2d(정규화 [0,1] 이미지 좌표 + visibility). schema 가
요구하는 '상대좌표'는 정규화 이미지 좌표뿐이고, to_coco17_array 출력은 pole_aligned 3D
(x,y,z,uncertainty)라 discretize 계약과 불일치한다 — 그래서 to_coco17_array 가 아니라
keypoints_2d 를 쓴다(rtmw_133_to_coco17 §normalization: image px → 0..1). 추론 자체는
프로덕션 경로(FfmpegFrameExtractor + RTMWPoseEngine)를 재사용하고 새 추론 코드는 없다.

순수 조립/서브샘플/캐시 로직은 GPU 없이 단위테스트된다(test_pod_coords.py). GPU 추론은
extract_coords_for_video 배선에만 격리한다.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import numpy as np

# 좌표 표현 단일 owner 재사용 — discretize/서브샘플 규칙을 복제하지 않고 그대로 쓴다.
from datagen import schema
from datagen.build_jsonl import _coords_to_frames
from distill.gemini_teacher import DEFAULT_TASK_JOINTS

log = logging.getLogger("pod_coords")
if not log.handlers:
    log.setLevel(logging.INFO)

_BACKEND = Path(__file__).resolve().parents[2]

# keypoints_2d 는 이미 정규화 [0,1] 이므로 discretize 의 width/height = 1.0
# (dx = round(clamp01(x) * 999)). schema '상대좌표 ×1000' 계약과 정확히 일치.
_NORM_W = 1.0
_NORM_H = 1.0

# 서브샘플 예산 — build_jsonl perturb 트랙(schema.select_frame_indices 기본값)과 동일.
DEFAULT_FRAME_BUDGET = 64

_ENGINE = None  # RTMWPoseEngine 싱글톤(가중치 재로드 회피 — 순차 3행에서 1회만).
_EXTRACTOR = None  # FfmpegFrameExtractor 싱글톤.


# ---------------------------------------------------------------------------
# 순수 조립 — (T, J, 3) 정규화 배열 → 서브샘플 좌표 행 (GPU 무의존, 테스트 대상).
# ---------------------------------------------------------------------------
def task_array_from_pose_frames(pose_frames, joint_keys=DEFAULT_TASK_JOINTS) -> np.ndarray:
    """list[PoseFrame] → (T, len(joint_keys), 3) 정규화 배열 [x, y, conf].

    PoseFrame.keypoints_2d(정규화 [0,1] + visibility)에서 대상 관절만 뽑는다. 미감지/
    결측 관절은 NaN 으로 남겨 _coords_to_frames 가 Null 로 바인딩한다(D-11 철칙 1, 키
    삭제 금지). 좌표 소스로 to_coco17_array(pole_aligned 3D)를 쓰지 않는 이유는 모듈
    docstring 참조. duck-typed — keypoints_2d dict 와 .x/.y/.visibility 만 요구(테스트가
    fake frame 으로 검증).
    """
    frames = list(pose_frames or [])
    n = len(frames)
    j = len(joint_keys)
    arr = np.full((n, j, 3), np.nan, dtype=float)
    for t, pf in enumerate(frames):
        kp2d = getattr(pf, "keypoints_2d", None) or {}
        for k, name in enumerate(joint_keys):
            kp = kp2d.get(name)
            if kp is None:
                continue
            x = getattr(kp, "x", None)
            y = getattr(kp, "y", None)
            if x is None or y is None:
                continue
            arr[t, k, 0] = float(x)
            arr[t, k, 1] = float(y)
            arr[t, k, 2] = float(getattr(kp, "visibility", 1.0))
    return arr


def frames_to_coords_rows(
    task_coords, joint_keys=DEFAULT_TASK_JOINTS, budget: int = DEFAULT_FRAME_BUDGET
) -> list[dict]:
    """(T, J, 3) 정규화 배열 → 서브샘플 좌표 행 (build_jsonl 좌표 표현 재사용).

    schema.select_frame_indices 로 9fps 인덱스 서브샘플(Pattern 1, 원 영상 재추출 0) 후
    _coords_to_frames 로 discretize(width=height=1.0). 반환 행은 build_rtmw_text 계약과
    일치: [{'frame': int, '<joint>': [dx, dy, conf], ...}, ...] (결측 관절 = None).
    """
    arr = np.asarray(task_coords, dtype=float)
    if arr.ndim != 3 or arr.shape[0] == 0:
        return []
    idxs = schema.select_frame_indices(arr.shape[0], budget)
    return _coords_to_frames(arr, list(joint_keys), idxs, _NORM_W, _NORM_H)


def coords_health(rows, joint_keys=DEFAULT_TASK_JOINTS) -> dict:
    """좌표 행 집합의 관절 채움/Null 비율 — Task 3 검증 보고 (b) 항목.

    반환: joints_filled_ratio(채워진 [관절×행] 비율), null_ratio, all_joints_present
    (12개 관절이 최소 1회 채워졌는지), joints_present(채워진 관절명 정렬).
    """
    keys = list(joint_keys)
    total = len(rows) * len(keys)
    filled = 0
    seen: set[str] = set()
    for r in rows:
        for name in keys:
            if r.get(name) is not None:
                filled += 1
                seen.add(name)
    return {
        "joints_filled_ratio": round(filled / total, 4) if total else 0.0,
        "null_ratio": round(1 - filled / total, 4) if total else 1.0,
        "all_joints_present": len(seen) == len(keys),
        "joints_present": sorted(seen),
    }


# ---------------------------------------------------------------------------
# 캐시 — video_hash 우선, manifest rows 는 video_hash 부재이므로 s3_key slug 폴백.
# ---------------------------------------------------------------------------
def coords_cache_key(row) -> str:
    """캐시 키 — row.video_hash 우선, 없으면 s3_key slug(경로 안전, 충돌 회피).

    manifest rows 는 video_hash 필드가 없어(s3_key 만) 기본이 slug 다. '/' → '__' 로
    치환해 prefix 다른 동명 파일 충돌을 막는다(plan 'video_hash 또는 s3 basename' 정합).
    """
    vh = (row or {}).get("video_hash")
    if vh:
        return str(vh)
    s3_key = (row or {}).get("s3_key") or ""
    slug = s3_key.replace("/", "__")
    if slug.endswith(".mp4") or slug.endswith(".mov"):
        slug = slug.rsplit(".", 1)[0]
    return slug or "unknown"


def _cache_path(cache_dir, key) -> Path:
    return Path(cache_dir) / f"{key}.json"


def load_cached_coords(cache_dir, key):
    """캐시 hit 이면 좌표 행 반환, miss/손상이면 None."""
    p = _cache_path(cache_dir, key)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        log.warning("좌표 캐시 손상 — 무시: %s", p)
        return None


def save_coords(cache_dir, key, rows) -> str:
    """좌표 행을 캐시에 기록(sort_keys 결정적). 경로 문자열 반환."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    p = _cache_path(cache_dir, key)
    p.write_text(json.dumps(rows, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# GPU 배선 — 프로덕션 추론 경로 재사용(FfmpegFrameExtractor + RTMWPoseEngine).
# ---------------------------------------------------------------------------
def _get_extractor():
    global _EXTRACTOR
    if _EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

        _EXTRACTOR = FfmpegFrameExtractor(target_fps=9.0, max_side=640)
    return _EXTRACTOR


def _get_engine():
    global _ENGINE
    if _ENGINE is None:
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine

        _ENGINE = RTMWPoseEngine()
    return _ENGINE


def _vertical_pole():
    """검출 실패 폴백 = 수직 폴 축(pipeline _RTMWNlfCompat 기본값 재사용, D-11)."""
    from sunity_shared.analysis.pose_frame import PoleAxis

    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def extract_coords_for_video(
    local_video_path: str, joint_keys=DEFAULT_TASK_JOINTS, budget: int = DEFAULT_FRAME_BUDGET
) -> list[dict]:
    """9fps 프레임 추출 → RTMW 추정 → keypoints_2d → 서브샘플 좌표 행 (GPU/CUDA 필요).

    프로덕션 추론 경로만 재사용(새 추론 코드 없음). 순수 조립은 task_array_from_pose_frames
    /frames_to_coords_rows 로 분리 — 본 함수는 배선만. 반환 = build_rtmw_text 계약 행.
    """
    frames = _get_extractor().extract(local_video_path)
    pose_frames = _get_engine().estimate(frames, _vertical_pole())
    task_coords = task_array_from_pose_frames(pose_frames, joint_keys)
    return frames_to_coords_rows(task_coords, joint_keys, budget)


def make_coords_provider(
    cache_dir, scratch_dir=None, joint_keys=DEFAULT_TASK_JOINTS, budget: int = DEFAULT_FRAME_BUDGET
):
    """run_trial_batch(coords_provider=...) 에 넘길 provider(row) -> coords_by_frame.

    캐시 hit 재사용(과금·GPU 0). miss 이고 scratch_dir 의 다운로드본이 있으면 추출·캐시.
    scratch_dir 미지정 + miss → [](안전 폴백 — 재추출 시도 안 함). run_trial_batch 는
    영상을 scratch_dir/basename(s3_key) 로 내려받으므로 그 규약을 재사용한다.
    """
    def provider(row):
        key = coords_cache_key(row)
        cached = load_cached_coords(cache_dir, key)
        if cached is not None:
            return cached
        if scratch_dir:
            s3_key = (row or {}).get("s3_key") or ""
            local = os.path.join(scratch_dir, os.path.basename(s3_key))
            if s3_key and os.path.exists(local):
                rows = extract_coords_for_video(local, joint_keys, budget)
                save_coords(cache_dir, key, rows)
                return rows
        return []

    return provider


# ---------------------------------------------------------------------------
# Pod 배치 러너 — selectable_rows 앞 N 행 다운로드→추출→캐시 (순차, Gemini 무접촉).
# ---------------------------------------------------------------------------
def _download_s3(bucket: str, key: str, dest_path: str) -> None:
    """S3 객체 → 로컬 (boto3, ap-northeast-2). Pod 는 aws CLI 없음 → boto3."""
    import boto3  # lazy

    boto3.client("s3", region_name="ap-northeast-2").download_file(bucket, key, dest_path)


def extract_and_cache(
    local_video_path: str,
    cache_dir,
    key,
    joint_keys=DEFAULT_TASK_JOINTS,
    budget: int = DEFAULT_FRAME_BUDGET,
) -> dict:
    """단일 영상 추출 → 캐시 저장 + 검증 요약(프레임 수/관절 채움/소요) 반환."""
    t0 = time.monotonic()
    rows = extract_coords_for_video(local_video_path, joint_keys, budget)
    path = save_coords(cache_dir, key, rows)
    summary = {"cache_path": path, "n_frames": len(rows), "elapsed_s": round(time.monotonic() - t0, 2)}
    summary.update(coords_health(rows, joint_keys))
    return summary


def run_extract_batch(
    manifest: dict,
    cache_dir,
    scratch_dir,
    *,
    n_rows: int = 3,
    bucket: str = "sunity-motion-pilot-videos",
    joint_keys=DEFAULT_TASK_JOINTS,
    budget: int = DEFAULT_FRAME_BUDGET,
) -> list[dict]:
    """selectable_rows 앞 n_rows S3 다운로드 → 좌표 추출 → 캐시 (순차, 다운로드본 삭제).

    Gemini 무접촉(과금 0). 파이프라인은 동시성 비안전이라 반드시 순차 실행한다
    ([[pipeline-not-concurrency-safe-eval-serial]]). 반환 = 행별 검증 리포트.
    """
    from distill.gemini_teacher import selectable_rows

    os.makedirs(scratch_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    rows = selectable_rows(manifest)[: max(0, int(n_rows))]
    reports: list[dict] = []
    for row in rows:
        s3_key = row["s3_key"]
        local = os.path.join(scratch_dir, os.path.basename(s3_key))
        key = coords_cache_key(row)
        report = {"s3_key": s3_key, "motion": row.get("motion"), "cache_key": key}
        try:
            _download_s3(bucket, s3_key, local)
            report.update(extract_and_cache(local, cache_dir, key, joint_keys, budget))
        except Exception as exc:  # noqa: BLE001 - 행 오류는 배치를 막지 않고 리포트에 집계.
            report["error"] = str(exc)[:200]
            log.warning("좌표 추출 실패 s3=%s err=%s", s3_key, str(exc)[:160])
        finally:
            try:
                os.remove(local)  # 다운로드본 즉시 삭제(디스크 절약).
            except OSError:
                pass
        reports.append(report)
        log.info("추출 완료 s3=%s frames=%s", s3_key, report.get("n_frames"))
    return reports


if __name__ == "__main__":  # pragma: no cover - 실행은 Pod(GPU) 세션.
    import argparse

    ap = argparse.ArgumentParser(description="Pod RTMW 좌표 추출 (Gemini 무접촉, 과금 0)")
    ap.add_argument("--manifest", default=str(_BACKEND / "training" / "data" / "manifest.json"))
    ap.add_argument("--cache-dir", default="/workspace/phase22_coords_cache")
    ap.add_argument("--scratch-dir", default="/workspace/phase22_coords_scratch")
    ap.add_argument("--n-rows", type=int, default=3)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    reports = run_extract_batch(manifest, args.cache_dir, args.scratch_dir, n_rows=args.n_rows)
    print(json.dumps(reports, ensure_ascii=False, indent=2))
