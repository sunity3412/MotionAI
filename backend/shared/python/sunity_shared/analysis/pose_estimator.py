"""프레임 → keypoints (PoseEstimator 구현, #7-follow Phase 1/2).

top-down 2단계: YOLO11n 으로 인체 bbox 탐지 → ViTPose 로 17 keypoint.
출력 (T, 17, 3) = COCO 17 순서(skeleton.KEYPOINT_NAMES 와 동일) · (x, y, score).
영상 전체에서 사람을 한 번도 못 찾으면 NoHumanError.

방향 보정 (#7-follow Phase 2 — overlay 검증에서 발견):
  ViTPose 는 COCO(직립 인체) 학습이라 인버트 자세에서 keypoint 가 엉킨다.
  폴스포츠는 인버트 비중이 크므로, 인물 crop 을 0°/180° 두 방향으로 추정해
  keypoint 신뢰도 평균이 높은 쪽을 채택한다(rotate-and-pick). 채택된 방향의
  keypoint 는 원본 프레임 좌표로 되돌려 반환한다.

무거운 모델 라이브러리(torch/ultralytics/transformers)는 __init__ 에서 지연
import — 코어 모듈/테스트가 이 파일을 import 해도 로딩되지 않게.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from .interfaces import NoHumanError

# 인물 crop 을 이 각도들로 추정해보고 신뢰도가 가장 높은 방향을 채택.
# 폴스포츠는 직립·인버트가 지배적 — 90/270 은 비용 대비 이득이 적어 제외.
_TRY_ANGLES = (0, 180)
# bbox 주변 여유 비율 (keypoint 가 bbox 를 살짝 벗어나는 경우 대비).
_CROP_PAD = 0.12


class YoloVitPoseEstimator:
    def __init__(
        self,
        yolo_weights: str = "yolo11n.pt",
        vitpose_model: str = "usyd-community/vitpose-base-simple",
        person_conf: float = 0.3,
    ) -> None:
        import torch
        from transformers import AutoProcessor, VitPoseForPoseEstimation
        from ultralytics import YOLO

        self._torch = torch
        self._yolo = YOLO(yolo_weights)
        self._processor = AutoProcessor.from_pretrained(vitpose_model)
        self._model = VitPoseForPoseEstimation.from_pretrained(vitpose_model)
        self._model.eval()
        self.person_conf = person_conf
        # ViTPose+ 는 데이터셋별 expert(MoE) — forward 에 dataset_index 필요.
        # 0 = COCO 17 keypoint (skeleton.KEYPOINT_NAMES 와 동일).
        self._is_moe = "plus" in vitpose_model.lower()

    def _vitpose(self, crop: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        """인물 crop(이미지 전체가 인물) → (17,2) keypoints(crop 좌표), (17,) scores."""
        w, h = crop.size
        box = np.array([[0.0, 0.0, float(w), float(h)]], dtype=float)
        inputs = self._processor(crop, boxes=[box], return_tensors="pt")
        with self._torch.no_grad():
            if self._is_moe:
                outputs = self._model(
                    **inputs, dataset_index=self._torch.tensor([0])
                )
            else:
                outputs = self._model(**inputs)
        pose = self._processor.post_process_pose_estimation(
            outputs, boxes=[box]
        )[0][0]
        return (
            pose["keypoints"].cpu().numpy(),
            pose["scores"].cpu().numpy(),
        )

    def _estimate_frame(
        self, img: Image.Image, box_xyxy: tuple[float, float, float, float]
    ) -> np.ndarray:
        """단일 프레임의 인물 bbox → (17,3) keypoints(원본 프레임 좌표).

        crop 을 _TRY_ANGLES 방향들로 추정해 keypoint 신뢰도 평균이 가장 높은
        방향을 채택하고, 해당 keypoint 를 원본 프레임 좌표로 환산한다.
        """
        fw, fh = img.size
        x1, y1, x2, y2 = box_xyxy
        pad_x = (x2 - x1) * _CROP_PAD
        pad_y = (y2 - y1) * _CROP_PAD
        cx1 = max(0, int(x1 - pad_x))
        cy1 = max(0, int(y1 - pad_y))
        cx2 = min(fw, int(x2 + pad_x))
        cy2 = min(fh, int(y2 + pad_y))
        crop = img.crop((cx1, cy1, cx2, cy2))
        cw, ch = crop.size

        best_kp: np.ndarray | None = None
        best_score = -1.0
        for angle in _TRY_ANGLES:
            rotated = (
                crop.transpose(Image.Transpose.ROTATE_180)
                if angle == 180
                else crop
            )
            kp, scores = self._vitpose(rotated)
            mean_score = float(np.mean(scores))
            if mean_score <= best_score:
                continue
            # 회전 좌표 → crop 좌표 (180° 는 양축 반전).
            if angle == 180:
                kp_crop = np.column_stack(
                    [cw - 1 - kp[:, 0], ch - 1 - kp[:, 1]]
                )
            else:
                kp_crop = kp
            best_kp = np.column_stack([kp_crop, scores])
            best_score = mean_score

        assert best_kp is not None  # _TRY_ANGLES 는 비어있지 않음
        # crop 좌표 → 원본 프레임 좌표.
        best_kp[:, 0] += cx1
        best_kp[:, 1] += cy1
        return best_kp

    def estimate(self, frames: np.ndarray) -> np.ndarray:
        """(T,H,W,3) RGB → (T,17,3) keypoints. 미감지 프레임은 score 0으로 남김."""
        out = np.zeros((len(frames), 17, 3), dtype=float)
        detected = 0
        for t in range(len(frames)):
            img = Image.fromarray(frames[t])
            det = self._yolo.predict(
                img, classes=[0], conf=self.person_conf, verbose=False
            )
            boxes = det[0].boxes
            if boxes is None or len(boxes) == 0:
                continue  # 이 프레임에 사람 없음 → keypoint 0 (score 0)
            # 최고 confidence 1인만 채점 (폴스포츠는 단독 동작).
            best = int(boxes.conf.argmax())
            x1, y1, x2, y2 = boxes.xyxy[best].cpu().numpy().tolist()
            out[t] = self._estimate_frame(img, (x1, y1, x2, y2))
            detected += 1

        if detected == 0:
            raise NoHumanError("영상 전체에서 사람을 찾지 못했습니다.")
        return out
