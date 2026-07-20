"""RunPod GPU 분석 서버 (FastAPI).

흐름:
  Lambda(SQS 트리거) → POST /analyze {bucket, key}        # X-RunPod-Token 헤더
  → 202 즉시 응답 (background task 시작)
  → Pod 내부: pipeline._process(bucket, key, uid, analysis_id)
       · S3 다운로드 → NLF GPU 추출 → reference 비교 → Firestore Admin 갱신
  → 앱은 onSnapshot 으로 결과 화면 자동 표시 (변경 없음)

설계 결정:
  - 키만 받음(parse_upload_key 가 uid/analysisId 복원) — Lambda 와 동일 계약.
  - functions/pipeline/app.py 의 `_process` 를 그대로 재사용 — 분기 0, 코드 1벌.
  - NLF 모델은 startup hook 에서 미리 로드 (콜드스타트 비용 절감).
  - 인증: shared secret 헤더(RUNPOD_AUTH_TOKEN). 토큰 미설정이면 503 (외부 공개 방지).
  - POST /pose-image (Phase 31 / 31-06): 생성 교정 이미지 1장의 keypoint 를 같은
    estimator 로 재측정하는 동기 엔드포인트. display 게이트 전용 — 채점 무접촉.

환경변수:
  RUNPOD_AUTH_TOKEN          # Lambda 와 공유. 필수 (미설정 시 모든 요청 503).
  AWS_ACCESS_KEY_ID          # S3 read 권한
  AWS_SECRET_ACCESS_KEY
  AWS_DEFAULT_REGION         # 예: ap-northeast-2
  FIREBASE_SA_JSON           # Firestore 서비스 계정 JSON 원문 (또는 FIREBASE_SA_PATH)
  CUDA_VISIBLE_DEVICES=0     # NLF GPU 강제 (runpod-gpu-env 메모)

기동(권장):
  uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1
  → 워커 1개 고정. NLF 모델이 GPU VRAM 점유라 worker 늘려도 이득 없음.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
# shared 레이어 경로 추가 (Lambda 와 동일한 sunity_shared 임포트 가능)
sys.path.insert(0, str(_BACKEND / "shared" / "python"))

from sunity_shared import firestore_admin, models  # noqa: E402
from sunity_shared.analysis.interfaces import NoHumanError, NotPoleMotionError  # noqa: E402
from sunity_shared.s3keys import parse_upload_key  # noqa: E402

log = logging.getLogger("runpod_inference")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Sunity Motion · RunPod Inference")

_AUTH_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN", "")

# pipeline/app.py 를 모듈로 1회 로드. Lambda 와 동일 코드라 분기 0.
_pipeline_lock = threading.Lock()
_pipeline_module: Any = None


def _load_pipeline_module() -> Any:
    """functions/pipeline/app.py 를 동적 임포트. 모듈 최상위에서 NLF 어댑터를
    초기화하므로(현재 코드 line 48~50), 이 함수가 처음 호출될 때 모델이 GPU 에 올라간다."""
    global _pipeline_module
    if _pipeline_module is not None:
        return _pipeline_module
    with _pipeline_lock:
        if _pipeline_module is not None:
            return _pipeline_module
        pipeline_path = _BACKEND / "functions" / "pipeline" / "app.py"
        spec = importlib.util.spec_from_file_location("sunity_pipeline_app", pipeline_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"pipeline/app.py 임포트 실패: {pipeline_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _pipeline_module = module
        log.info("pipeline 모듈 로드 + NLF 어댑터 워밍업 완료")
        return module


# ── /pose-image payload 상한 (3차 리뷰 H3-04 — 전부 명시 상수) ──────────────
#
# base64 "문자열 길이" 하나로 상한을 잡으면 실제 decode 비용이 모호해진다(인코딩
# 오버헤드 ~33%, 압축률 무관). 그래서 3중으로 나눠 명시한다:
#   1) 전송 방어  — b64 문자열 길이 (요청 본문이 커지는 것 자체를 막음)
#   2) decode 방어 — base64 decode 직후 실제 바이트
#   3) 픽셀 방어  — PIL open 직후 (w,h) 로 decompression bomb 차단
#
# 3번이 별도로 필요한 이유: 압축률이 극단적인 PNG 는 1MB 로도 20000x20000 을 담을 수
# 있어 1)2) 를 전부 통과한다. 픽셀 상한 없이는 decode 시점에 워커 메모리가 터진다.
#
# PIL 의 자체 방어(Image.MAX_IMAGE_PIXELS)는 pixels > 2*MAX 에서만 예외를 던지고
# MAX~2*MAX 구간은 경고만 낸다. 그래서 MAX_IMAGE_PIXELS 설정과 **명시적 w*h 검사**를
# 둘 다 둔다 — 어느 한쪽만으로는 구간이 샌다.
_POSE_IMG_MAX_B64_CHARS = 12_000_000
_POSE_IMG_MAX_DECODED_BYTES = 8_000_000
_POSE_IMG_MAX_PIXELS = 16_000_000
_POSE_IMG_MAX_EDGE = 4096
_POSE_IMG_FORMATS = ("PNG", "JPEG")


class AnalyzeRequest(BaseModel):
    bucket: str = Field(..., description="S3 버킷명")
    key: str = Field(..., description="S3 객체 키 (uploads/{uid}/{analysisId}.{ext})")


class PoseImageRequest(BaseModel):
    imageB64: str = Field(..., description="PNG/JPEG base64 (상한은 _POSE_IMG_* 상수)")


class PoseImageResponse(BaseModel):
    """단일 이미지 keypoint 추정 결과.

    keypoints 는 **정규화 [0,1] 좌표** (x 는 width, y 는 height 로 각각 나눈 값)이므로
    각도를 내려면 반드시 width/height 를 곱해 등방(px) 좌표로 되돌려야 한다. 정규화
    좌표를 그대로 내각에 넣으면 종횡비만큼 각도가 왜곡된다(fault_zoom.joint_inner_angle_deg
    docstring 과 동일 계약). width/height 를 응답에 함께 싣는 이유가 이것이다.
    """

    ok: bool
    width: int | None = None
    height: int | None = None
    keypoints: dict[str, list[float]] | None = None  # name → [x, y, visibility]
    error: str | None = None


class AnalyzeResponse(BaseModel):
    status: str
    uid: str
    analysisId: str


def _verify_token(x_runpod_token: str = Header(default="", alias="X-RunPod-Token")) -> None:
    """shared secret 검증. 토큰 미설정 환경은 외부 공개 위험이라 503."""
    if not _AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RUNPOD_AUTH_TOKEN 미설정 — 서버가 비공개 모드로 동작 중.",
        )
    if x_runpod_token != _AUTH_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


def _process_in_background(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    """pipeline.lambda_handler 의 try/except 와 동일 매핑.
    NoHumanError → ERR_NO_HUMAN, NotPoleMotionError → ERR_NOT_POLE_MOTION,
    그 외 → ERR_SERVER_ERROR."""
    try:
        pipeline_app = _load_pipeline_module()
        pipeline_app._process(bucket, key, uid, analysis_id)
        log.info("분석 완료 uid=%s analysisId=%s", uid, analysis_id)
    except NoHumanError:
        log.info("인체 미감지 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_NO_HUMAN,
            models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
        )
    except NotPoleMotionError:
        log.info("비폴 영상 차단 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_NOT_POLE_MOTION,
            models.ERROR_MESSAGE[models.ERR_NOT_POLE_MOTION],
        )
    except Exception:  # noqa: BLE001
        log.exception("분석 실패 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_SERVER_ERROR,
            models.ERROR_MESSAGE[models.ERR_SERVER_ERROR],
        )


@app.on_event("startup")
def _warmup() -> None:
    """모델/어댑터 미리 GPU 메모리 로드. 실패해도 첫 /analyze 에서 재시도.
    pipeline 모듈은 어댑터 import 를 lazy 로 미루므로 _ensure_adapters() +
    _ensure_recognizer() 까지 명시적으로 호출 — startup 비용을 첫 요청이 아닌
    부팅 시점에 지불.

    Phase 5 (Plan 5-04, 2026-06-04) — Gemini fail-loud 박제:
      env RECOGNIZER_BACKEND=gemini + GEMINI_API_KEY 누락 시 startup 시점에
      log.error + RuntimeError 발생. outer except 가 흡수 → FastAPI server 자체는
      살아있음, 첫 /analyze 호출에서 503/실패 (Common Pitfall 4 박제 정신).
      박제 정신 = "갑작스러운 미스터리 X — log 로 원인 명시 + 첫 분석 시점 명시 실패".
    """
    log.info("RunPod 분석 서버 startup — auth=%s", "ON" if _AUTH_TOKEN else "OFF")
    try:
        mod = _load_pipeline_module()
        mod._ensure_adapters()
        log.info("어댑터 워밍업 완료 (NLF/ffmpeg/coach)")

        # Plan 5-04 박제 — recognizer 워밍업 (lazy creation + env switch).
        # env 미설정 시 FallbackRecognizer 박제 (회귀 0).
        recognizer = mod._ensure_recognizer()
        log.info("Recognizer 워밍업 완료 — type=%s", type(recognizer).__name__)

        # Gemini 선택 시 API 키 명시 검증 — _load_api_key() 호출 시 키 없으면
        # RuntimeError 발생 (fail-loud 박제). recognize() 첫 호출 시점에서
        # 갑작스러운 에러 발생 회피 (Common Pitfall 4 박제 정신).
        if mod._gemini_enabled():
            try:
                # D-16 lazy import — Gemini 모드 진입 시점에만 import.
                from sunity_shared.judging.gemini_moment_extractor import (
                    _load_api_key,
                )
                _load_api_key()  # 키 값 자체는 버림 (검증만 — 로그에 키 노출 X).
                log.info("Gemini API 키 검증 완료")
            except RuntimeError as exc:
                log.error(
                    "Gemini API 키 검증 실패 — Pod env GEMINI_API_KEY 또는 SSM "
                    "Parameter Store /sunity/motion/gemini-api-key 박제 누락: %s",
                    exc,
                )
                raise  # fail-loud — outer except 가 흡수 (server 는 살아있음).
    except Exception:  # noqa: BLE001
        log.exception("워밍업 실패 — 첫 요청 처리 시 재시도")


@app.get("/health")
def health() -> dict:
    """liveness probe. 인증 불필요(외부 모니터링 도구가 호출). 무거운 검사 없음."""
    return {
        "status": "ok",
        "auth_configured": bool(_AUTH_TOKEN),
        "pipeline_loaded": _pipeline_module is not None,
    }


def _decode_pose_image(image_b64: str) -> tuple[Any, int, int]:
    """base64 → (1,H,W,3) uint8 RGB 배열 + (width, height). 상한 위반 시 HTTPException.

    검사 순서가 곧 방어다 — **decode 하기 전에** 거를 수 있는 것을 먼저 거른다:
      b64 길이(413) → base64 decode(400) → 바이트 수(413) → PIL open(400) →
      format allowlist(400) → 픽셀/변 상한(400) → 그제서야 실제 decode(load).

    numpy/PIL 은 함수 안에서 import — Pod 전용 경로라 모듈 import 비용을 미룬다
    (analysis 어댑터의 lazy import 관례와 동일).
    """
    import base64
    import io

    import numpy as np
    from PIL import Image, UnidentifiedImageError

    if len(image_b64) > _POSE_IMG_MAX_B64_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"imageB64 length > {_POSE_IMG_MAX_B64_CHARS}",
        )
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except Exception as exc:  # noqa: BLE001 - 잘못된 base64 는 클라이언트 오류
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid base64: {exc}"
        ) from exc
    if len(raw) > _POSE_IMG_MAX_DECODED_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"decoded bytes > {_POSE_IMG_MAX_DECODED_BYTES}",
        )

    # bomb 차단 — open 전에 전역 상한을 걸어 둔다 (pixels > 2*MAX 에서 PIL 이 예외).
    Image.MAX_IMAGE_PIXELS = _POSE_IMG_MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(raw))
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="decompression bomb rejected"
        ) from exc
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="unidentified image"
        ) from exc

    fmt = (img.format or "").upper()
    if fmt not in _POSE_IMG_FORMATS:
        # 확장자/Content-Type 이 아니라 실제 컨테이너 포맷으로 판정 — 위장 방어.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"format not allowed: {fmt or 'unknown'}",
        )
    width, height = int(img.width), int(img.height)
    # PIL 이 경고만 내는 MAX~2*MAX 구간을 여기서 명시적으로 닫는다.
    if max(width, height) > _POSE_IMG_MAX_EDGE or width * height > _POSE_IMG_MAX_PIXELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"dimensions too large: {width}x{height}",
        )

    arr = np.asarray(img.convert("RGB"), dtype=np.uint8)
    return arr[None, ...], width, height


@app.post("/pose-image", response_model=PoseImageResponse)
def pose_image(
    req: PoseImageRequest,
    _: None = Depends(_verify_token),
) -> PoseImageResponse:
    """생성 이미지 1장 → COCO-17 정규화 keypoint (31-06 결정론 pose 게이트 백엔드).

    **display 게이트 전용 — 점수 반영 금지 (invariant).** 본 엔드포인트는 채점 모듈
    (dimensions/kismam/assemble)을 호출하지 않으며 Firestore 도 만지지 않는다. 생성
    이미지에서 뽑은 좌표가 채점에 유입되면 "AI 가 만든 그림이 점수를 움직이는" 경로가
    열린다. estimator 재사용이 전부이고 신규 모델/패키지는 0.

    인체 미검출·추정 실패는 500 이 아니라 ok:false 다 — 게이트 입장에서 "사람이 없다"는
    정상적인 판정 결과(불통과)이지 서버 장애가 아니다. 장애(5xx)와 섞으면 호출측이
    'pose_gate_unavailable'(재시도 대상)과 'no_person'(종결)을 구분하지 못한다.
    """
    frames, width, height = _decode_pose_image(req.imageB64)

    try:
        mod = _load_pipeline_module()
        mod._ensure_adapters()
        engine = mod._RTMW_ENGINE
        pole_axis = mod._POSE_ESTIMATOR._default_pole  # vertical fallback 단일 출처
        pose_frames = engine.estimate(frames, pole_axis)
    except NoHumanError:
        log.info("/pose-image no_person w=%d h=%d", width, height)
        return PoseImageResponse(ok=False, width=width, height=height, error="no_person")
    except Exception as exc:  # noqa: BLE001 - 추정 실패도 게이트에는 '불통과' 신호
        log.exception("/pose-image estimate 실패 w=%d h=%d", width, height)
        return PoseImageResponse(
            ok=False, width=width, height=height, error=f"estimate_failed: {type(exc).__name__}"
        )

    kp2d = pose_frames[0].keypoints_2d if pose_frames else None
    if not kp2d:
        log.info("/pose-image keypoints_2d 부재 w=%d h=%d", width, height)
        return PoseImageResponse(ok=False, width=width, height=height, error="no_keypoints")

    keypoints = {
        name: [float(k.x), float(k.y), float(k.visibility)] for name, k in kp2d.items()
    }
    log.info("/pose-image ok w=%d h=%d joints=%d", width, height, len(keypoints))
    return PoseImageResponse(ok=True, width=width, height=height, keypoints=keypoints)


@app.post("/analyze", status_code=202, response_model=AnalyzeResponse)
def analyze(
    req: AnalyzeRequest,
    background: BackgroundTasks,
    _: None = Depends(_verify_token),
) -> AnalyzeResponse:
    parsed = parse_upload_key(req.key)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid key format: {req.key}",
        )
    log.info(
        "/analyze accepted bucket=%s uid=%s analysisId=%s",
        req.bucket,
        parsed.uid,
        parsed.analysis_id,
    )
    background.add_task(
        _process_in_background, req.bucket, req.key, parsed.uid, parsed.analysis_id
    )
    return AnalyzeResponse(
        status="accepted", uid=parsed.uid, analysisId=parsed.analysis_id
    )
