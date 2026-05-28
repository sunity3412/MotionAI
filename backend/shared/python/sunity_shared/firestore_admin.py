"""Firestore Admin 클라이언트 (백엔드 전용 — 보안 규칙 우회).

용도:
  - pipeline: users/{uid}/analyses/{id} 의 status/result/error 갱신
  - reference-api: reference 컬렉션 목록 조회

앱은 절대 Admin 권한을 갖지 않는다. 서비스 계정은 auth.py 와 동일하게
Parameter Store(FIREBASE_SA_PARAM)에서 로드 — 코드/.env 하드코딩 금지.
"""

from __future__ import annotations

import time

from . import auth as _auth
from . import models

_client = None


def _db():
    """firestore 클라이언트 1회 생성 (firebase-admin 초기화 재사용)."""
    global _client
    if _client is not None:
        return _client
    _auth._ensure_firebase()  # firebase_admin app 보장
    from firebase_admin import firestore

    _client = firestore.client()
    return _client


def _doc(path: str):
    return _db().document(path)


def update_analysis_status(uid: str, analysis_id: str, status: str) -> None:
    """진행 단계 갱신. status 는 models.PIPELINE_SEQUENCE 중 하나."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {"status": status, "updatedAt": int(time.time() * 1000)},
        merge=True,
    )


def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
) -> None:
    """status='done' + result (contract.md §4 AnalysisResult).

    angles 가 주어지면 추출된 관절각을 doc top-level 에 flat 저장한다 — mode3(자기
    성장)가 '이전 분석 영상'을 기준 시퀀스로 DTW 비교할 때 읽는다. Firestore 는
    nested-array 금지라 flat list + anglesJointKeys(길이 J) + anglesFrames(T) 로
    저장하고 읽는 쪽에서 reshape ([[firestore-nested-array-flat]]). get_previous_analysis
    는 to_dict() 로 이 필드를 자동 반환한다."""
    payload: dict = {
        "status": models.STATUS_DONE,
        "result": result,
        "updatedAt": int(time.time() * 1000),
    }
    if angles is not None:
        payload["angles"] = angles
        payload["anglesJointKeys"] = angles_joint_keys
        payload["anglesFrames"] = angles_frames
    _doc(models.analysis_doc_path(uid, analysis_id)).set(payload, merge=True)


def fail_analysis(uid: str, analysis_id: str, code: str, message: str) -> None:
    """status='failed' + error{code,message} (contract.md §5)."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {
            "status": models.STATUS_FAILED,
            "error": {"code": code, "message": message},
            "updatedAt": int(time.time() * 1000),
        },
        merge=True,
    )


def list_reference_motions() -> list[dict]:
    """reference 컬렉션 전체 (기준 모션 선택 화면 #9). 읽기 전용."""
    col = _db().collection(models.REFERENCE_MOTIONS_COLLECTION)
    out: list[dict] = []
    for snap in col.stream():
        data = snap.to_dict() or {}
        data.setdefault("motionId", snap.id)
        out.append(data)
    return out


def get_analysis(uid: str, analysis_id: str) -> dict | None:
    """앱이 만든 분석 문서 읽기 (mode, referenceMotionId, fileName 등)."""
    snap = _doc(models.analysis_doc_path(uid, analysis_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data.setdefault("analysisId", analysis_id)
    return data


def get_reference_motion(motion_id: str) -> dict | None:
    """기준 모션 1건. keyframe 각도 데이터(angles) + 메타 포함(ml_CLAUDE.md 등록)."""
    snap = _doc(models.reference_motion_path(motion_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data.setdefault("motionId", motion_id)
    return data


def get_previous_analysis(uid: str, current_id: str) -> dict | None:
    """Mode3 비교용: 가장 최근 완료(done) 분석 1건 (현재 건 제외)."""
    from firebase_admin import firestore

    col = _db().collection(f"users/{uid}/analyses")
    q = (
        col.where("status", "==", models.STATUS_DONE)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(5)
    )
    for snap in q.stream():
        if snap.id == current_id:
            continue
        data = snap.to_dict() or {}
        data.setdefault("analysisId", snap.id)
        return data
    return None
