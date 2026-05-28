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


class AnalyzeRequest(BaseModel):
    bucket: str = Field(..., description="S3 버킷명")
    key: str = Field(..., description="S3 객체 키 (uploads/{uid}/{analysisId}.{ext})")


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
    pipeline 모듈은 어댑터 import 를 lazy 로 미루므로 _ensure_adapters() 까지
    명시적으로 호출 — startup 비용을 첫 요청이 아닌 부팅 시점에 지불."""
    log.info("RunPod 분석 서버 startup — auth=%s", "ON" if _AUTH_TOKEN else "OFF")
    try:
        mod = _load_pipeline_module()
        mod._ensure_adapters()
        log.info("어댑터 워밍업 완료 (NLF/ffmpeg/coach)")
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
