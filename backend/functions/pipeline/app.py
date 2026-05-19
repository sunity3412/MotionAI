"""분석 파이프라인 — S3 업로드 이벤트 → SQS → 이 함수 (비동기).

현재 상태: STUB. 트리거 파싱과 상태 머신 전이만 실제이고, ML 분석
(YOLO11 → ViTPose-S → MotionDTW → KISMAM → Cerebras)은 #7 에서 채운다.

설계 원칙(CLAUDE.md §7): 수치 채우기 금지 — 가짜 점수/결과를 만들지 않는다.
그래서 stub 는 'queued' 까지만 정직하게 전이하고, 분석부는 NotImplementedError
로 명확히 멈춘다(SQS 재시도→DLQ). #7 에서 done/result 까지 구현.

계약: 상태/오류는 docs/contract.md §3·§5, 단계 순서는
models.PIPELINE_SEQUENCE. 갱신은 백엔드 Admin SDK 만 가능(보안 규칙 우회).
"""

from __future__ import annotations

import logging

from sunity_shared import firestore_admin, models
from sunity_shared.events import iter_s3_keys_from_sqs
from sunity_shared.s3keys import parse_upload_key

log = logging.getLogger()
log.setLevel(logging.INFO)


def lambda_handler(event: dict, _context) -> dict:
    processed = 0
    for _bucket, key in iter_s3_keys_from_sqs(event):
        parsed = parse_upload_key(key)
        if parsed is None:
            # uploads/{uid}/{analysisId}.{mp4|mov} 형식이 아니면 우리 대상 아님
            log.warning("스킵: 인식 불가 S3 키 %s", key)
            continue

        uid, analysis_id = parsed.uid, parsed.analysis_id
        log.info("파이프라인 진입 uid=%s analysis_id=%s", uid, analysis_id)

        # 실제 전이: 앱이 만든 문서를 'queued' 로 (S3 트리거됨, 대기)
        firestore_admin.update_analysis_status(uid, analysis_id, models.STATUS_QUEUED)
        processed += 1

        # ── #7 에서 구현 ─────────────────────────────────────────────
        # frame_extraction → pose_analysis → comparison 전이 + 각 단계 ML,
        # 성공 시 firestore_admin.complete_analysis(uid, id, result),
        # 인체 미감지 등 실패 시 firestore_admin.fail_analysis(uid, id, code, msg).
        raise NotImplementedError(
            f"분석 파이프라인 미구현(#7). analysis_id={analysis_id} 는 'queued' "
            f"까지만 전이됨. ML 단계 연결 필요."
        )

    return {"processed": processed}
