"""프레임 → keypoints (PoseEstimator 구현, #7-follow Phase 1).

top-down 2단계: YOLO11n 으로 인체 bbox 탐지 → ViTPose 로 17 keypoint.
출력 (T, 17, 3) = COCO 17 순서(skeleton.KEYPOINT_NAMES 와 동일) · (x, y, score).
영상 전체에서 사람을 한 번도 못 찾으면 NoHumanError.

무거운 모델 라이브러리(torch/ultralytics/transformers)는 __init__ 에서 지연
import — 코어 모듈/테스트가 이 파일을 import 해도 로딩되지 않게.

⚠ ViTPose 출력 keypoint 순서가 COCO 17(skeleton.KEYPOINT_NAMES)과 일치하는지
   reference overlay 검증 스크립트로 반드시 육안 확인할 것.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from .interfaces import NoHumanError


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
            # 최고 confidence 1인만 채점 (폴스포츠는 단독 동작)
            best = int(boxes.conf.argmax())
            x1, y1, x2, y2 = boxes.xyxy[best].cpu().numpy().tolist()
            # ViTPose 는 COCO bbox (x, y, w, h) 를 기대
            box_coco = np.array([[x1, y1, x2 - x1, y2 - y1]], dtype=float)

            inputs = self._processor(img, boxes=[box_coco], return_tensors="pt")
            with self._torch.no_grad():
                outputs = self._model(**inputs)
            pose = self._processor.post_process_pose_estimation(
                outputs, boxes=[box_coco]
            )[0][0]
            out[t, :, :2] = pose["keypoints"].cpu().numpy()
            out[t, :, 2] = pose["scores"].cpu().numpy()
            detected += 1

        if detected == 0:
            raise NoHumanError("영상 전체에서 사람을 찾지 못했습니다.")
        return out
