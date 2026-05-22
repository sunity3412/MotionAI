"""프레임 → 3D keypoints (PoseEstimator 구현, #7-follow 하이브리드 파이프라인).

2D 백본(YOLO11→ViTPose)은 폴 폐색·접힌 인버트 자세에서 keypoint 가 엉켜
천장이 확인됐다(plan.md #7-follow). 3D 백본 NLF(Neural Localizer Fields,
NeurIPS'24)로 전환한다 — 인체 prior 가 있어 가려진 관절도 해부학적으로
일관된 3D 좌표로 복원한다.

흐름(top-down):
  YOLO11n 으로 인체 bbox 탐지 → NLF estimate_poses_batched 로 박스마다
  17 COCO joint 의 3D 좌표 + 관절별 불확실도를 얻는다.
  bbox 미감지 프레임은 인접 성공 프레임의 박스로 폴백한다(시간적 보완).

COCO-17 질의:
  NLF 는 임의의 canonical 점을 질의할 수 있다(get_weights_for_canonical_points).
  COCO-17 순서가 필요하므로 SMPL rest-pose joint 템플릿(body_models.smpl.
  J_template, 24점)에서 사지 12관절을 뽑아 COCO-17 배치로 재배열해 질의한다.
  얼굴 5점(코·눈·귀)은 관절각(skeleton.JOINT_ANGLES)에 안 쓰여 SMPL head 로
  대체한다 — 배열 자리는 채우되 값은 사용되지 않는다.

출력 (T,17,4) = COCO-17 순서(skeleton.KEYPOINT_NAMES) · (x, y, z, uncertainty):
  x,y,z       NLF 3D 좌표(mm). 관절각은 스케일 불변이라 단위는 무관.
  uncertainty NLF per-joint 불확실도(클수록 불신). 시간축 보간(temporal)이
              상대 임계로 폐색·접힘 프레임을 가려내는 데 쓴다.
영상 전체에서 사람을 한 번도 못 찾으면 NoHumanError.

NLF 내장 인체 탐지기(detector)는 CUDA 가 하드코딩돼 박스를 직접 주입한다.
NLF 는 GPU 전제 모델 — CPU 에서는 수치가 NaN 으로 발산한다(검증됨). 운영
GPU 추론 분리는 #7-follow 인프라 단계(plan.md). 무거운 import(torch/
ultralytics)는 __init__ 에서 지연 로드 — 코어/테스트가 영향받지 않게.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from .interfaces import NoHumanError

# COCO-17(skeleton.KEYPOINT_NAMES) index → SMPL-24 joint index.
# 사지 12관절만 관절각에 쓰인다. 얼굴 5점(코·눈·귀=0~4)은 SMPL head(15)로
# 대체 — 배열 자리만 채우고 값은 미사용.
#   SMPL-24: 1 L_hip 2 R_hip 4 L_knee 5 R_knee 7 L_ankle 8 R_ankle
#            15 head 16 L_shoulder 17 R_shoulder 18 L_elbow 19 R_elbow
#            20 L_wrist 21 R_wrist
_COCO17_FROM_SMPL = (15, 15, 15, 15, 15, 16, 17, 18, 19, 20, 21, 1, 2, 4, 5, 7, 8)

# backend/ 기준 기본 경로 (parents: 0 analysis · 1 sunity_shared · 2 python ·
# 3 shared · 4 backend). 배포 시엔 환경변수로 컨테이너 내 경로를 주입.
_BACKEND = Path(__file__).resolve().parents[4]
_DEFAULT_NLF_PATH = _BACKEND / "scripts" / "nlf_l_multi.torchscript"
_DEFAULT_YOLO_PATH = _BACKEND / "yolo11n.pt"


def _fill_missing_boxes(boxes: list[np.ndarray | None]) -> list[np.ndarray]:
    """미감지(None) 박스를 가장 가까운 성공 프레임 박스로 채운다(시간적 보완)."""
    known = [(i, b) for i, b in enumerate(boxes) if b is not None]
    if not known:
        raise NoHumanError("영상 전체에서 사람을 찾지 못했습니다.")
    return [
        b if b is not None
        else min(known, key=lambda kb: abs(kb[0] - i))[1]
        for i, b in enumerate(boxes)
    ]


class NlfPoseEstimator:
    """NLF 3D HMR 어댑터. interfaces.PoseEstimator 프로토콜 구현."""

    def __init__(
        self,
        nlf_model_path: str | None = None,
        yolo_weights: str | None = None,
        person_conf: float = 0.3,
        batch_size: int = 8,
    ) -> None:
        import torch
        import torchvision  # noqa: F401 — TorchScript 모델의 연산 등록에 필요
        from ultralytics import YOLO

        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self.person_conf = person_conf
        self.batch_size = batch_size

        nlf_path = (
            nlf_model_path or os.environ.get("NLF_MODEL_PATH") or str(_DEFAULT_NLF_PATH)
        )
        yolo_path = (
            yolo_weights or os.environ.get("YOLO_WEIGHTS_PATH") or str(_DEFAULT_YOLO_PATH)
        )
        self._model = torch.jit.load(nlf_path, map_location=self._device).eval()
        self._yolo = YOLO(yolo_path)

        # COCO-17 질의점 = SMPL rest-pose joint 템플릿을 COCO 배치로 재배열.
        # weights 는 모델 device 에서 1회 계산 후 모든 프레임에 재사용.
        j_template = self._model.body_models.smpl.J_template  # (24,3) model device
        canonical = j_template[list(_COCO17_FROM_SMPL)]        # (17,3)
        self._weights = self._model.get_weights_for_canonical_points(canonical)

    def _detect_boxes(self, frames: np.ndarray) -> list[np.ndarray | None]:
        """각 프레임의 인체 박스(LTWH float32). 미감지 프레임은 None."""
        from PIL import Image

        out: list[np.ndarray | None] = []
        for f in frames:
            det = self._yolo.predict(
                Image.fromarray(f), classes=[0], conf=self.person_conf, verbose=False
            )
            boxes = det[0].boxes
            if boxes is None or len(boxes) == 0:
                out.append(None)
                continue
            best = int(boxes.conf.argmax())  # 단독 동작 — 최고 신뢰 1인
            x1, y1, x2, y2 = boxes.xyxy[best].cpu().numpy().tolist()
            out.append(np.array([x1, y1, x2 - x1, y2 - y1], dtype=np.float32))
        return out

    def estimate(self, frames: np.ndarray) -> np.ndarray:
        """(T,H,W,3) RGB uint8 → (T,17,4) = COCO-17 · (x,y,z,uncertainty).

        NLF 가 한 프레임에서 포즈를 못 내면 그 프레임은 좌표 NaN·불확실도 inf
        로 남긴다 — 시간축 보간(temporal)이 인접 프레임에서 메운다.
        """
        torch = self._torch
        T = len(frames)
        boxes = _fill_missing_boxes(self._detect_boxes(frames))  # NoHumanError 가능

        out = np.full((T, 17, 4), np.nan, dtype=float)
        with torch.inference_mode():
            for s in range(0, T, self.batch_size):
                e = min(s + self.batch_size, T)
                imgs = (
                    torch.from_numpy(np.ascontiguousarray(frames[s:e]))
                    .permute(0, 3, 1, 2)
                    .contiguous()
                    .to(self._device)
                )
                box_list = [
                    torch.from_numpy(boxes[t]).unsqueeze(0).to(self._device)
                    for t in range(s, e)
                ]
                pred = self._model.estimate_poses_batched(
                    imgs, box_list, self._weights
                )
                for k, t in enumerate(range(s, e)):
                    people = pred["poses3d"][k]
                    if people.shape[0] == 0:
                        out[t, :, 3] = np.inf  # 포즈 미산출 → 보간 위임
                        continue
                    out[t, :, :3] = people[0].cpu().numpy()
                    out[t, :, 3] = pred["uncertainties"][k][0].cpu().numpy()
        return out
