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


def get_previous_analysis(
    uid: str, current_id: str, mode: str | None = None
) -> dict | None:
    """Mode3 비교용: 가장 최근 완료(done) 분석 1건 (현재 건 제외).

    박제 (2026-06-07 belle): mode 인자 박제. mode3 first 판정 시 mode1 (정은지)
    분석을 prev 로 잡는 함정 fix — belle 의 mode3 첫 시도가 직전 mode1 분석을
    prev 로 잡아 second+ 처리됨. mode 박제 = "같은 mode" 박제 안에서만 prev 검색.
    """
    from firebase_admin import firestore

    col = _db().collection(f"users/{uid}/analyses")
    q = col.where("status", "==", models.STATUS_DONE)
    if mode is not None:
        q = q.where("mode", "==", mode)
    q = q.order_by("createdAt", direction=firestore.Query.DESCENDING).limit(5)
    for snap in q.stream():
        if snap.id == current_id:
            continue
        data = snap.to_dict() or {}
        data.setdefault("analysisId", snap.id)
        return data
    return None


# ─────────────────── Plan 5-02 (2026-06-04) Gemini 캡싱 helper ───────────────────
#
# D-14 박제 — 영상 hash 캡싱 (gemini_cache/{hash} top-level 전역 공유).
# D-09 case 3 박제 — TERM-DATA-01 분기 3 자동 수집 (term_collection/{keyword}).
# [[firestore-nested-array-flat]] 정합 — moments[i] flat dict array 강제.
# D-16 lazy import — firebase_admin.firestore 는 record_unregistered_keyword
# 안에서만 import (Increment / ArrayUnion 만 필요).

_GEMINI_CACHE_COLLECTION = "gemini_cache"  # top-level, uid 비의존 전역 공유
_TERM_COLLECTION = "term_collection"  # TERM-DATA-01 분기 3 자동 수집 (D-09 case 3)


def get_gemini_cache(video_hash: str) -> dict | None:
    """gemini_cache/{hash} document → dict 또는 None.

    Plan 5-02 박제. TechniqueCache.lookup 가 호출.
    """
    snap = _doc(f"{_GEMINI_CACHE_COLLECTION}/{video_hash}").get()
    if not snap.exists:
        return None
    return snap.to_dict() or None


def store_gemini_cache(video_hash: str, payload: dict) -> None:
    """gemini_cache/{hash} document 박제. video_hash + timestamps 자동 추가.

    Plan 5-02 박제. TechniqueCache.store 가 호출.

    [[firestore-nested-array-flat]] 정합 — moments entry 가 flat dict 아니거나
    value 가 list/tuple 이면 TypeError raise (Firestore crash 1차 차단선).

    timestamps 박제:
      · created_at — payload 에 이미 있으면 보존 (재박제 시 첫 박제 시각 유지)
      · updated_at — 항상 현재 시각 박제

    Raises:
      TypeError: moments entry 가 flat dict 아님 또는 value 가 list/tuple.
    """
    # nested-array 정합 검증 ([[firestore-nested-array-flat]])
    if "moments" in payload and payload["moments"]:
        for i, m in enumerate(payload["moments"]):
            if not isinstance(m, dict):
                raise TypeError(
                    f"moments[{i}] must be flat dict "
                    f"(firestore-nested-array-flat): got {type(m).__name__}"
                )
            for k, v in m.items():
                if isinstance(v, (list, tuple)):
                    raise TypeError(
                        f"moments[{i}][{k}] must be scalar "
                        f"(firestore nested array 금지): got {type(v).__name__}"
                    )

    now_ms = int(time.time() * 1000)
    doc = {
        **payload,
        "video_hash": video_hash,
        "created_at": payload.get("created_at", now_ms),
        "updated_at": now_ms,
    }
    _doc(f"{_GEMINI_CACHE_COLLECTION}/{video_hash}").set(doc)


def record_unregistered_keyword(keyword: str, *, uid: str, video_hash: str) -> None:
    """TERM-DATA-01 분기 3 자동 수집 트리거 (D-09 case 3 — Plan 5-02 박제).

    Phase 16 TERM-DATA-01 schema 정합 (uid 익명 + 누적 카운트):
      · keyword: 박제 keyword string
      · count: Increment(1) — 호출마다 +1
      · unique_users: ArrayUnion([uid]) — set 정합 (같은 uid 멱등)
      · last_video_hash: 마지막 박제 영상 hash
      · promotion_status: "pending" (Phase 16 16-AUTOCOLLECT-SCHEMA 박제 워크플로:
        pending → reviewing → approved)
      · created_at / updated_at: ms timestamps

    UI 카피 TERM-COPY-01 = Phase 12 책임 (본 helper = 데이터 트리거만).

    멱등: 같은 (keyword, uid) 재호출 시 unique_users set 박제 = 1 (중복 무시).
    """
    from firebase_admin import firestore as _firestore  # lazy import (D-16)

    ref = _doc(f"{_TERM_COLLECTION}/{keyword}")
    now_ms = int(time.time() * 1000)
    ref.set(
        {
            "keyword": keyword,
            "count": _firestore.Increment(1),
            "unique_users": _firestore.ArrayUnion([uid]),
            "last_video_hash": video_hash,
            "updated_at": now_ms,
            "created_at": now_ms,  # set merge=True 가 첫 박제만 사용
            "promotion_status": "pending",  # Phase 16 schema 박제 정합
        },
        merge=True,
    )
