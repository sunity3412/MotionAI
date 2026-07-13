"""고객 영상 얼굴 가명처리 — 얼굴 검출 + Gaussian blur (D-12, 22-02 Task 2).

D-12 (동의 3겹): 모델은 포즈/모션만 학습, 얼굴 픽셀 불필요. 가명정보의 과학적 연구
목적 활용 구조로 동의 의존을 최소화한다. **고객 영상 트랙 전용** — 유튜브 공개 영상은
D-12 범위 밖(provenance 만). **적재 후 소급 불가이므로 적재 전 강제**가 생명이다
(22-04 build_jsonl 은 anonymized=true 또는 internal=true 행만 소비).

구조 (analysis core 순수성 규율 — 순수 blur 함수와 I/O 껍데기 분리):
  · 순수: blur_bbox_regions(frame, bboxes, kernel) — numpy/PIL Gaussian blur.
    top_third_fallback_bbox(w, h) — 검출 실패 시 보수적 상단 1/3 폴백.
  · I/O 껍데기: anonymize_video(in_path, out_path) — ultralytics 얼굴 검출(기존
    인프라 재사용, 신규 pip 없이 얼굴 가중치 멱등 다운로드) + ffmpeg 재인코딩.
    torch/ultralytics/ffmpeg 는 lazy-import(코어/테스트 무영향, pose_estimator 전례).

numpy 외 서드파티 의존은 I/O 껍데기 안에서만. 순수 함수는 numpy 만 사용.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

# 검출 실패 프레임 보수적 폴백 = 상단 1/3 블러(얼굴 위치 사전확률 최대 영역).
FALLBACK_TOP_FRACTION = 1.0 / 3.0
# Gaussian blur 커널(홀수). 얼굴 식별 불가 수준으로 충분히 강하게.
DEFAULT_KERNEL = 31


def top_third_fallback_bbox(width: int, height: int) -> tuple[int, int, int, int]:
    """검출 실패 시 상단 1/3 영역 bbox (x0, y0, x1, y1). 순수.

    얼굴 미검출이 곧 얼굴 부재는 아니므로(폐색·모션블러) 식별 위험 영역을 보수적으로
    블러한다. 상단 1/3 = 직립/인버트 모두에서 머리 위치 사전확률이 높은 밴드.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height must be > 0: {width!r},{height!r}")
    y1 = int(round(height * FALLBACK_TOP_FRACTION))
    return (0, 0, int(width), max(1, y1))


def _box_blur_region(region: np.ndarray, kernel: int) -> np.ndarray:
    """단일 bbox 영역 → 반복 박스필터로 Gaussian 근사 블러. 순수(numpy만).

    OpenCV 의존 없이 separable 박스필터를 2회 적용(중심극한 → Gaussian 근사).
    region shape = (h, w, c). kernel 은 홀수로 강제.
    """
    if region.size == 0:
        return region
    k = max(3, int(kernel) | 1)  # 홀수 강제, 최소 3.
    pad = k // 2
    out = region.astype(np.float32)
    for _ in range(2):  # 2회 반복 = Gaussian 근사(중심극한정리).
        out = _separable_box(out, pad)
    return np.clip(out, 0, 255).astype(region.dtype)


def _separable_box(img: np.ndarray, pad: int) -> np.ndarray:
    """수평→수직 박스필터(separable). 경계는 edge padding. 순수."""
    h, w = img.shape[:2]
    k = 2 * pad + 1
    # 수평.
    padded = np.pad(img, ((0, 0), (pad, pad), (0, 0)), mode="edge")
    cum = np.cumsum(padded, axis=1)
    cum = np.concatenate([np.zeros_like(cum[:, :1, :]), cum], axis=1)
    horiz = (cum[:, k:, :] - cum[:, :w, :]) / k
    # 수직.
    padded = np.pad(horiz, ((pad, pad), (0, 0), (0, 0)), mode="edge")
    cum = np.cumsum(padded, axis=0)
    cum = np.concatenate([np.zeros_like(cum[:1, :, :]), cum], axis=0)
    vert = (cum[k:, :, :] - cum[:h, :, :]) / k
    return vert


def blur_bbox_regions(
    frame: np.ndarray,
    bboxes: list[tuple[int, int, int, int]],
    kernel: int = DEFAULT_KERNEL,
) -> np.ndarray:
    """프레임의 각 bbox 영역을 블러한 새 프레임 반환. 순수 — 입력 미변형.

    frame shape = (H, W, C). bboxes = [(x0,y0,x1,y1), ...] 픽셀 좌표.
    bbox 밖 픽셀은 그대로 보존(포즈 학습에 필요). 얼굴 없으면 빈 리스트로 무변형.
    """
    if frame.ndim != 3:
        raise ValueError(f"frame must be (H,W,C): got shape {frame.shape}")
    out = frame.copy()
    h, w = frame.shape[:2]
    for (x0, y0, x1, y1) in bboxes:
        x0 = max(0, min(int(x0), w))
        x1 = max(0, min(int(x1), w))
        y0 = max(0, min(int(y0), h))
        y1 = max(0, min(int(y1), h))
        if x1 <= x0 or y1 <= y0:
            continue
        out[y0:y1, x0:x1] = _box_blur_region(out[y0:y1, x0:x1], kernel)
    return out


# RTMW-133 (COCO-WholeBody) 머리 키포인트 인덱스 — 몸통 머리(코·눈·귀 0~4) + 얼굴
# 68 랜드마크(23~90). 폴 영상은 얼굴이 화면 어디든(역자세 시 하단) 오므로 일반 얼굴
# 검출기는 프레임의 ~40%만 잡는다(2026-07-13 실측). RTMW 는 사람만 검출되면(yolox,
# 큰 폴 선수 = 사실상 100%) 얼굴 랜드마크를 전부 회귀하므로 recall 이 훨씬 높다.
_WHOLEBODY_HEAD_IDX: tuple[int, ...] = (0, 1, 2, 3, 4) + tuple(range(23, 91))

# 머리 bbox 신뢰 임계 + 패딩 비율(머리 크기 대비). 머리카락/이마 커버를 위해 상단은
# 추가 패딩. 얼굴 식별 불가가 목표이므로 관대하게 — 단, 몸통 포즈 학습 신호는 보존.
_HEAD_KP_CONF = 0.3
_HEAD_PAD_RATIO = 0.6
# 머리 크기 하한(프레임 높이 대비) — 코·눈만 잡혀 bbox 가 작아도 최소 커버 보장.
_HEAD_MIN_SPAN_FRAC = 0.06


def head_bbox_from_wholebody(
    kps: np.ndarray,
    scores: np.ndarray,
    width: int,
    height: int,
    *,
    conf: float = _HEAD_KP_CONF,
    pad_ratio: float = _HEAD_PAD_RATIO,
) -> tuple[int, int, int, int] | None:
    """RTMW-133 키포인트 → 머리 blur bbox (x0,y0,x1,y1) 또는 None. 순수(numpy만).

    머리 키포인트(_WHOLEBODY_HEAD_IDX) 중 score>=conf 인 점들의 최소 포함 사각형에
    관대한 패딩(상단은 머리카락/이마 커버 위해 추가)을 적용해 클립한다. 유효점 2개
    미만이면 None(호출자가 폴백). 몸통/사지는 블러하지 않아 포즈 학습 신호를 보존한다.
    """
    n = min(len(kps), len(scores))
    xs: list[float] = []
    ys: list[float] = []
    for i in _WHOLEBODY_HEAD_IDX:
        if i >= n or float(scores[i]) < conf:
            continue
        xs.append(float(kps[i][0]))
        ys.append(float(kps[i][1]))
    if len(xs) < 2:
        return None
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    # 머리 크기 = span 최대값(작은 bbox 방어를 위해 프레임 대비 하한 적용).
    span = max(x1 - x0, y1 - y0, _HEAD_MIN_SPAN_FRAC * float(height))
    pad = span * pad_ratio
    bx0 = int(round(x0 - pad))
    bx1 = int(round(x1 + pad))
    by0 = int(round(y0 - pad - span * 0.5))  # 상단 추가 패딩(머리카락/이마).
    by1 = int(round(y1 + pad))
    bx0 = max(0, min(bx0, width))
    bx1 = max(0, min(bx1, width))
    by0 = max(0, min(by0, height))
    by1 = max(0, min(by1, height))
    if bx1 <= bx0 or by1 <= by0:
        return None
    return (bx0, by0, bx1, by1)


# ---------------------------------------------------------------------------
# I/O 껍데기 (Task 3/22-04 실행 경로 — lazy-import, 테스트 무영향).
# ---------------------------------------------------------------------------
def _load_face_detector(weights: str | None = None):
    """ultralytics 로 얼굴 검출 모델 로드(기존 인프라 재사용, 멱등 다운로드).

    신규 pip 없이 ultralytics 로 얼굴 가중치를 로드한다(pose_estimator YOLO 전례).
    torch/ultralytics 는 여기서만 lazy-import.
    """
    import os

    from ultralytics import YOLO

    path = weights or os.environ.get("FACE_WEIGHTS_PATH") or "yolov8n-face.pt"
    return YOLO(path)


def _detect_faces_no_fallback(detector, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """단일 프레임 → 얼굴 bbox 리스트(폴백 없음). 검출 0 이면 빈 리스트."""
    try:
        results = detector(frame, verbose=False)
    except Exception:  # noqa: BLE001 — 검출 실패는 빈 리스트(호출자가 폴백 결정).
        log.exception("얼굴 검출 실패")
        return []
    bboxes: list[tuple[int, int, int, int]] = []
    for r in results:
        boxes = getattr(r, "boxes", None)
        if boxes is None:
            continue
        for xyxy in boxes.xyxy.tolist():
            x0, y0, x1, y1 = (int(round(v)) for v in xyxy[:4])
            bboxes.append((x0, y0, x1, y1))
    return bboxes


def detect_face_bboxes(detector, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """단일 프레임 → 얼굴 bbox 리스트. 검출 0 → 상단 1/3 폴백 1개(하위호환)."""
    bboxes = _detect_faces_no_fallback(detector, frame)
    if bboxes:
        return bboxes
    h, w = frame.shape[:2]
    return [top_third_fallback_bbox(w, h)]


def _load_pose_detector():
    """rtmlib Wholebody 로드 — RTMW-133 키포인트(얼굴 랜드마크 포함) 추출용.

    RTMWPoseEngine 와 동일한 env 계약(RTMW_ONNX_PATH/YOLOX_ONNX_PATH/RTMW_DEVICE).
    rtmlib/onnxruntime 는 여기서만 lazy-import — Pod 전용(로컬 테스트 무영향).
    반환 detector 는 detector(frame) → ((N,133,2/3),(N,133)).
    """
    import os

    from rtmlib import Wholebody

    pose = os.environ.get("RTMW_ONNX_PATH")
    if not pose:
        raise RuntimeError("RTMW_ONNX_PATH 미설정 — 포즈기반 머리 블러 불가(D-12).")
    det = os.environ.get("YOLOX_ONNX_PATH")
    device = os.environ.get("RTMW_DEVICE", "cpu")
    return Wholebody(
        det=det, det_input_size=(640, 640), pose=pose,
        to_openpose=False, backend="onnxruntime", device=device,
    )


def head_bboxes_from_pose(pose_detector, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """단일 프레임 → 사람별 머리 bbox 리스트(포즈기반). 검출 0 이면 빈 리스트.

    RTMW 는 사람만 검출되면 얼굴 랜드마크를 회귀하므로 폴 동작(역자세·회전)에서도
    머리를 안정적으로 잡는다 — 일반 얼굴 검출기의 저 recall(프레임 40%)을 대체한다.
    """
    try:
        kps_batch, scores_batch = pose_detector(frame)
    except Exception:  # noqa: BLE001 — 추론 실패는 빈 리스트(호출자가 폴백 결정).
        log.exception("포즈 추론 실패 — 머리 bbox 0")
        return []
    if kps_batch is None or len(kps_batch) == 0:
        return []
    h, w = frame.shape[:2]
    out: list[tuple[int, int, int, int]] = []
    for kps, scores in zip(kps_batch, scores_batch):
        bb = head_bbox_from_wholebody(np.asarray(kps), np.asarray(scores), w, h)
        if bb is not None:
            out.append(bb)
    return out


def anonymize_video(in_path: str, out_path: str, weights: str | None = None) -> str:
    """고객 영상 → 머리 블러 재인코딩(D-12 적재 전 강제). Task 3/22-04 실행 경로.

    프레임별: 포즈기반 머리 bbox(RTMW, 주검출) ∪ 얼굴검출 bbox(보조) 를 블러. 둘 다
    0 이면 상단 1/3 폴백. 포즈기반이 폴 동작에서 얼굴 노출(일반 검출기 recall 40%)을
    해소한다(2026-07-13 belle 결정). 몸통/사지는 보존(포즈 학습 신호). imageio/ffmpeg/
    ultralytics/rtmlib lazy-import. 반환 = out_path.
    """
    import imageio.v3 as iio  # lazy — 코어/테스트 무영향.

    pose_detector = _load_pose_detector()
    face_detector = _load_face_detector(weights)
    frames = iio.imread(in_path, index=None)  # (T, H, W, C)
    blurred = []
    for frame in frames:
        arr = np.asarray(frame)
        bboxes = head_bboxes_from_pose(pose_detector, arr)
        bboxes += _detect_faces_no_fallback(face_detector, arr)  # 보조 union.
        if not bboxes:
            h, w = arr.shape[:2]
            bboxes = [top_third_fallback_bbox(w, h)]  # 둘 다 0 — 보수적 폴백.
        blurred.append(blur_bbox_regions(arr, bboxes))
    out = np.stack(blurred, axis=0)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    iio.imwrite(out_path, out, fps=30)
    log.info("anonymize_video 완료 (D-12): %s -> %s (%d frames)", in_path, out_path, len(blurred))
    return out_path
