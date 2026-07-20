"""visual worker — action 단위 state machine (SQS consumer). 담당 플랜 31-09.

불변식 (6~11차 리뷰 §7 실행 허용 조건):

  1. **외부 side-effect 당 invocation 1개.** 어떤 유료/파괴적 호출이 이미 나갔는지
     job.state 하나만 보고 판정할 수 있어야 한다 (B2-02).
  2. **claim 통과분(claimed)의 반환 snapshot 만 사용한다** (6차 B6-01). claim 이전
     inbound 메시지로 job 을 재구성해 action 이나 후속 CAS 에 쓰는 경로는 없다 —
     acceptance 가 grep 으로 강제한다.
  3. **모든 전이는 transaction 원자 outbox + snapshot 반환**을 거친다 (B3-01/B4-01).
     SQS send 는 best-effort 이고, 유실 복구 주체는 dispatcher(visual-dispatch)다.
  4. **owner/lease CAS** — lease 를 잃었거나 만료된 늦은 worker 의 결과 write 는
     새 owner 의 진행을 덮지 못한다 (5차 B5-01 + 6차 H6-07).
  5. **correctedPose 의 terminal 은 성공/실패 전부 postprocessing 을 경유한다**
     (H4-01 + H5-05 + 6차 B6-03). 진입 transition 이 inputSealed=True 를 기록하고,
     postprocess 가 비-버저닝 단일 delete cleanup 을 durable 수행해 remainingObject==0
     을 확인한 뒤에야 한 번 finalize 한다. 실패 경로도 cleanup 을 우회하지 않는다.
  6. **URL 을 문서에 저장하지 않는다** (H3-01). taskId 만 남기고 fetch 가 재-poll 로
     fresh URL 을 얻어 같은 invocation 에서 즉시 다운로드한다.
  7. **임계값 리터럴 금지 (D-08 fail-closed).** display/training 판정 임계값과 pose
     허용오차는 31-13 calibration 채택값을 env 로 주입받는다. env 가 없거나 파싱
     불가면 **추측하지 않고 typed 실패로 종결**한다 — 교정 카드가 노출되지 않는다.

금지 (acceptance grep): requests / 키 리터럴 / fail_analysis / update_analysis_visual /
google.genai / 시간 폴링 루프 / outputUrl 기록 / list_object_versions.
"""

from __future__ import annotations

import json
import logging
import os
import random

import boto3

from sunity_shared import firestore_admin, models

log = logging.getLogger()
log.setLevel(logging.INFO)

# ── 상수 ────────────────────────────────────────────────────────────────

ACTION_IAM_PROBE = "iam_probe"  # 31-12 IAM canary 전용 — 외부 side-effect 0 (H4-02).

MAX_POLLS = 20
POLL_DELAY_S = 60
CLEANUP_ATTEMPT_MAX = 5
CLEANUP_BLOCKED_BACKOFF_S = 3600

_BUSY_JITTER_S = 30
_BUSY_MIN_VISIBILITY_S = 5

_METRIC_NAMESPACE = "SunityVisual"

_ALLOWED_ACTIONS = tuple(models.VISUAL_NEXT_ACTIONS) + (ACTION_IAM_PROBE,)


class _MalformedMessage(Exception):
    """스키마 위반 메시지 — 재시도해도 같으므로 DLQ 로 보낸다 (M2-02)."""


class _CalibrationMissing(Exception):
    """31-13 채택 임계값 env 부재/파싱 불가.

    **추측 금지** (D-08): CALIBRATION.json 은 현재 blocked 이고 임계값을 방출하지
    않는다. 값이 없으면 판정 기준이 없는 것이므로 통과시키지 않고 fail-closed 로
    종결한다 — 근거 없는 교정 이미지를 사용자에게 보여주는 것보다 안 보여주는 쪽이
    항상 낫다.
    """

    def __init__(self, env_name: str) -> None:
        super().__init__(env_name)
        self.env_name = env_name


# ── seam (테스트가 monkeypatch 하는 경계) ────────────────────────────────

_S3 = None
_SQS = None


def _s3():
    global _S3
    if _S3 is None:
        _S3 = boto3.client("s3")
    return _S3


def _sqs():
    global _SQS
    if _SQS is None:
        _SQS = boto3.client("sqs")
    return _SQS


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value else default


def _required_float_env(name: str) -> float:
    """31-13 채택 임계값 1개. 부재/파싱 불가 → _CalibrationMissing (추측 금지)."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        raise _CalibrationMissing(name)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise _CalibrationMissing(name) from None
    if value != value:  # NaN
        raise _CalibrationMissing(name)
    return value


def _put_metric(metric_name: str, value: float = 1.0) -> None:
    """운영 가시성 metric. 실패는 삼킨다 — metric 때문에 job 이 죽으면 안 된다."""
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace=_METRIC_NAMESPACE,
            MetricData=[{"MetricName": metric_name, "Value": float(value)}],
        )
    except Exception:  # noqa: BLE001 - 관측 실패는 작업 실패가 아니다
        log.warning("metric put failed metric=%s", metric_name)


# ── 메시지 파싱 ──────────────────────────────────────────────────────────


def _parse_message(record: dict) -> dict:
    try:
        body = json.loads(record.get("body") or "")
    except (TypeError, ValueError):
        raise _MalformedMessage("body_not_json") from None
    if not isinstance(body, dict):
        raise _MalformedMessage("body_not_object")

    job_id = body.get("jobId")
    action = body.get("action")
    if not isinstance(job_id, str) or not job_id:
        raise _MalformedMessage("jobId")
    if action not in _ALLOWED_ACTIONS:
        raise _MalformedMessage("action")
    try:
        generation = int(body.get("generation"))
        outbox_seq = int(body.get("outboxSeq"))
    except (TypeError, ValueError):
        raise _MalformedMessage("generation_or_outboxSeq") from None
    return {
        "jobId": job_id,
        "generation": generation,
        "action": action,
        "outboxSeq": outbox_seq,
    }


def _request_id(context) -> str:
    """claim owner. Lambda 요청 ID 는 invocation 마다 고유해 owner 로 정확하다."""
    rid = getattr(context, "aws_request_id", None)
    return str(rid) if rid else f"local-{random.getrandbits(48):012x}"


# ── entrypoint ──────────────────────────────────────────────────────────


def lambda_handler(event, context=None):
    failures: list[dict] = []
    for record in (event or {}).get("Records") or []:
        message_id = record.get("messageId")
        try:
            msg = _parse_message(record)
        except _MalformedMessage as exc:
            # 스키마 위반은 재시도해도 같다 — DLQ 로 보낸다 (M2-02).
            log.error("visual-worker malformed message_id=%s reason=%s", message_id, exc)
            failures.append({"itemIdentifier": message_id})
            continue

        if msg["action"] == ACTION_IAM_PROBE:
            # 31-12 canary: send 권한만 확인한다. 외부 호출 0, 정상 소비 (H4-02).
            log.info("visual-worker iam_probe job_id=%s", msg["jobId"])
            continue

        try:
            outcome = _handle_job(msg, owner=_request_id(context))
        except Exception:  # noqa: BLE001 - 개별 레코드 실패가 배치를 죽이면 안 된다
            log.exception(
                "visual-worker action failed job_id=%s action=%s", msg["jobId"], msg["action"]
            )
            failures.append({"itemIdentifier": message_id})
            continue

        if outcome.get("status") == "busy":
            # **정상 ACK 금지** (B5-01): ACK 하면 이 action 의 유일한 재전달 기회가
            # 사라져 claim 을 쥔 worker 가 죽었을 때 복구가 dispatcher lease 만료까지
            # 지연된다. lease 만료 직후에 다시 오도록 visibility 를 맞춰 반납한다.
            _defer_busy(record, outcome.get("job") or {})
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}


def _defer_busy(record: dict, job: dict) -> None:
    """남은 claim lease + jitter 만큼 visibility 를 늘려 재전달 시점을 맞춘다 (M6-03).

    jitter 가 없으면 중복 전달들이 동시에 깨어나 같은 job 을 두들긴다(thundering herd).
    """
    remaining_ms = int(job.get("claimLeaseExpiresAt") or 0) - _now_ms()
    seconds = max(_BUSY_MIN_VISIBILITY_S, remaining_ms // 1000) + random.randint(
        1, _BUSY_JITTER_S
    )
    queue_url = _env("VISUAL_QUEUE_URL")
    receipt = record.get("receiptHandle")
    if not queue_url or not receipt:
        return
    try:
        _sqs().change_message_visibility(
            QueueUrl=queue_url, ReceiptHandle=receipt, VisibilityTimeout=int(seconds)
        )
    except Exception:  # noqa: BLE001 - 실패해도 batchItemFailures 로 재전달은 보장된다
        log.warning("change_message_visibility failed")


# ── claim 규율 ──────────────────────────────────────────────────────────


def _handle_job(msg: dict, *, owner: str) -> dict:
    action = msg["action"]
    job_id = msg["jobId"]

    if action == "create":
        # create 는 claim 을 쓰지 않는다 — begin_visual_job_create 의 creating lease 특례.
        return _action_create(job_id, msg, owner=owner)

    res = firestore_admin.claim_visual_job_action(
        job_id,
        generation=msg["generation"],
        action=action,
        outbox_seq=msg["outboxSeq"],
        owner=owner,
        lease_ms=models.VISUAL_CLAIM_LEASE_MS,
        now_ms=_now_ms(),
    )
    status = res.get("status")
    if status == "busy":
        return {"status": "busy", "job": res.get("job") or {}}
    if status != "claimed":
        # stale/completed — 외부 0 + 정상 ACK. 재발행은 불필요하다(이미 진행했거나 끝났다).
        log.info("visual-worker claim %s job_id=%s action=%s", status, job_id, action)
        return {"status": status}

    # B6-01: 여기서부터 job 은 **claim 이 반환한 snapshot** 이다. msg 값을 action 이나
    # 후속 CAS 에 재사용하지 않는다.
    job = res["job"]
    handler = _ACTION_HANDLERS.get(_handler_key(action, job.get("kind")))
    if handler is None:
        raise _MalformedMessage(f"no handler for {action}/{job.get('kind')}")
    handler(job_id, job, owner=owner)
    return {"status": "ok"}


def _handler_key(action: str, kind: str | None) -> str:
    if action == "fetch":
        return f"fetch:{kind}"
    return action


# ── 공통 전이 헬퍼 ───────────────────────────────────────────────────────


def _advance(
    job_id: str,
    job: dict,
    *,
    next_state: str,
    updates: dict,
    next_action: str | None,
    owner: str | None,
    delay_s: int = 0,
) -> dict | None:
    """전이 1회 + best-effort 발행. 성공 시 **갱신 snapshot**, CAS 실패 시 None.

    반환 snapshot 이 계약의 핵심이다 (H5-04): 한 invocation 이 2번 전이할 때
    두 번째 호출은 반드시 첫 번째가 돌려준 snapshot 을 job 으로 써야 한다. msg 나
    claim snapshot 을 재사용하면 이미 한 칸 진행한 job 을 옛 seq 로 다시 건드린다.
    """
    now = _now_ms()
    payload = dict(updates)
    payload["state"] = next_state
    snap = firestore_admin.transition_visual_job(
        job_id,
        expect_states=(job.get("state"),),
        updates=payload,
        next_action=next_action,
        expect_outbox_seq=int(job.get("outboxSeq") or 0),
        expect_generation=int(job.get("generation") or 0),
        expect_claim_owner=owner,
        now_ms=now,
        next_dispatch_at_ms=(now + int(delay_s) * 1000) if next_action else None,
    )
    if snap is None:
        # CAS 실패 = lease 상실/만료/구세대. 재발행하지 않는다 — 이미 남이 쥐었다.
        log.warning("visual-worker transition CAS failed job_id=%s state=%s", job_id, next_state)
        return None

    if next_action is None:
        # H7-01: creating 내부 전이는 SQS 로 나가지 않는다. action=None 메시지는
        # 스키마 위반이라 DLQ 만 오염시키고, 같은 invocation 이 이어서 create 한다.
        assert snap.get("nextAction") is None and snap.get("dispatchState") is None
        return snap

    _emit(job_id, snap, next_action)
    return snap


def _emit(job_id: str, snap: dict, next_action: str) -> None:
    """best-effort 발행. 실패는 삼킨다 — durable outbox 를 dispatcher 가 복구한다."""
    queue_url = _env("VISUAL_QUEUE_URL")
    if not queue_url:
        log.warning("VISUAL_QUEUE_URL 미설정 — dispatcher 복구에 위임")
        return
    delay = max(0, int(snap.get("nextDispatchAtMs") or 0) - _now_ms()) // 1000
    try:
        _sqs().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(
                {
                    "jobId": job_id,
                    "generation": int(snap.get("generation") or 0),
                    "action": next_action,
                    "outboxSeq": int(snap.get("outboxSeq") or 0),
                }
            ),
            DelaySeconds=min(900, delay),
        )
        firestore_admin.mark_visual_job_dispatched(
            job_id,
            expect_action=next_action,
            expect_outbox_seq=int(snap.get("outboxSeq") or 0),
            expect_generation=int(snap.get("generation") or 0),
        )
    except Exception:  # noqa: BLE001 - outbox 가 pending 으로 남고 dispatcher 가 집는다
        log.warning("visual-worker dispatch best-effort failed job_id=%s", job_id)


# ── 종결 헬퍼 ───────────────────────────────────────────────────────────


def _finalize_correctedpose_intent(
    job_id: str,
    job: dict,
    reason: str | None,
    *,
    owner: str | None,
    meta: dict | None = None,
    terminal_state: str = "failed",
) -> dict | None:
    """correctedPose 종결 의도를 postprocessing 에 실어 durable 하게 넘긴다.

    직접 finalize 하지 않는 이유 (H5-05 + 6차 B6-03): 실패든 성공이든 임시 생체
    프레임 cleanup 은 반드시 일어나야 한다. 실패 경로만 finalize 로 빠지면 그 경로의
    입력이 영구 잔존한다. 진입 transition 이 inputSealed=True 를 기록해 producer 의
    재사용도 같이 막는다.
    """
    updates = dict(meta or {})
    updates.update(
        {
            "pendingTerminalState": terminal_state,
            "pendingFailureReason": reason,
            "inputSealed": True,
        }
    )
    if reason is not None:
        updates["failureReason"] = reason
    return _advance(
        job_id,
        job,
        next_state="postprocessing",
        updates=updates,
        next_action="postprocess",
        owner=owner,
    )


def _finalize_rotation_failure(
    job_id: str, job: dict, reason: str, *, owner: str | None
) -> None:
    """rotation 은 임시 입력·pair 가 없어 postprocessing 을 경유하지 않는다."""
    firestore_admin.finalize_visual_job(
        job_id,
        terminal_state="failed",
        failure_reason=reason,
        job_meta=None,
        display_status=models.VISUAL_STATUS_FAILED,
        expect_states=(job.get("state"),),
        expect_generation=int(job.get("generation") or 0),
        expect_outbox_seq=int(job.get("outboxSeq") or 0),
        expect_claim_owner=owner,
        now_ms=_now_ms(),
    )


def _finalize_create_failure(
    job_id: str, job: dict, reason: str, *, owner: str | None
) -> None:
    """create 계열 실패의 kind 분기 (9차 H9-09).

    correctedPose 를 rotation 처럼 direct finalize 하면 cleanup 계약을 통째로 우회한다.
    분기를 helper 한 곳에 가두어 호출부가 실수할 수 없게 한다.
    """
    if job.get("kind") == models.VISUAL_KIND_CORRECTED_POSE:
        _finalize_correctedpose_intent(job_id, job, reason, owner=owner)
    else:
        _finalize_rotation_failure(job_id, job, reason, owner=owner)


# ── action: create ──────────────────────────────────────────────────────


def _adapter(kind: str):
    """벤더 어댑터. 키는 env 에서만 읽는다 (리터럴 금지)."""
    from sunity_shared.analysis import visual_gen

    api_key = _env("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY 미설정")
    if kind == models.VISUAL_KIND_CORRECTED_POSE:
        return visual_gen.WanImageAdapter(api_key)
    return visual_gen.WanVideoEditAdapter(api_key)


def _action_create(job_id: str, msg: dict, *, owner: str) -> dict:
    """vendor create. begin_visual_job_create 의 5상태 분기 (8차 B8-01)."""
    from sunity_shared.analysis import visual_gen

    now = _now_ms()
    res = firestore_admin.begin_visual_job_create(
        job_id,
        expect_generation=msg["generation"],
        expect_outbox_seq=msg["outboxSeq"],
        now_ms=now,
        owner=owner,
        lease_ms=models.VISUAL_CLAIM_LEASE_MS,
        expect_next_action="create",
    )
    status = res.get("status")
    snap = res.get("job") or {}

    if status in ("stale", "busy"):
        # 외부 0 + 정상 ACK. busy 는 다른 유효 owner 가 이미 create 를 진행 중이다.
        log.info("visual-worker create %s job_id=%s", status, job_id)
        return {"status": status}

    if status == "unconfirmed":
        # creating lease 만료 + taskId 부재. create 가 벤더에 도달했는지 알 수 없어
        # 자동 재생성은 이중 과금이 된다 (B2-02) — 수동 판정으로 넘긴다.
        log.error("visual-worker create_unconfirmed job_id=%s", job_id)
        _finalize_create_failure(job_id, snap, "create_unconfirmed", owner=None)
        return {"status": "unconfirmed"}

    if status == "resume":
        # taskId 가 이미 있다 = create 는 나갔다. polling 으로 재개하고 재호출하지 않는다.
        if snap.get("state") == "creating":
            _advance(
                job_id,
                snap,
                next_state="polling",
                updates={"taskId": snap.get("taskId")},
                next_action="poll",
                owner=None,
                delay_s=POLL_DELAY_S,
            )
        return {"status": "resume"}

    if status != "acquired":
        raise RuntimeError(f"unexpected begin_visual_job_create status {status!r}")

    # ★ acquired — 이 snapshot 하나로 즉시 vendor create 를 1회 호출한다.
    # _advance(creating) 2차 호출 없음 (B8-01).
    kind = snap.get("kind")
    try:
        if kind == models.VISUAL_KIND_CORRECTED_POSE:
            created = _create_corrected_pose(snap)
        else:
            created = _create_rotation(snap)
    except _InvalidJobInput as exc:
        _finalize_create_failure(job_id, snap, exc.reason, owner=None)
        return {"status": "invalid_input"}

    if isinstance(created, visual_gen.VendorPollResult):
        if created.state == visual_gen.VENDOR_STATE_SUCCEEDED:
            # v1 은 async taskId 경로만 정상 처리한다 (B4-02). sync 결과를 받으면
            # taskId 없이 산출물만 있는 상태라 재개/멱등 계약이 성립하지 않는다.
            log.error("visual-worker sync succeeded 미허용 (B4-02) job_id=%s", job_id)
            _finalize_create_failure(job_id, snap, "vendor_error", owner=None)
            return {"status": "sync_rejected"}
        reason = (
            "moderation"
            if created.state == visual_gen.VENDOR_STATE_BLOCKED
            else "vendor_error"
        )
        _finalize_create_failure(job_id, snap, reason, owner=None)
        return {"status": "create_failed"}

    _advance(
        job_id,
        snap,
        next_state="polling",
        updates={"taskId": created.task_id},
        next_action="poll",
        owner=None,
        delay_s=POLL_DELAY_S,
    )
    return {"status": "ok"}


class _InvalidJobInput(Exception):
    def __init__(self, reason: str = "invalid_output") -> None:
        super().__init__(reason)
        self.reason = reason


def _create_corrected_pose(job: dict):
    """srcKey presign → Wan2.7 image edit. 프롬프트 목표각은 job payload 단일 출처."""
    bucket = _env("VISUAL_INPUT_BUCKET")
    src_key = job.get("srcKey")
    if not bucket or not src_key:
        raise _InvalidJobInput()
    url = _s3().generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": src_key}, ExpiresIn=3600
    )
    return _adapter(models.VISUAL_KIND_CORRECTED_POSE).create_task(
        url, _corrected_pose_prompt(job)
    )


def _corrected_pose_prompt(job: dict) -> str:
    """생성 지시. joint/targetDeg 는 job payload(CorrectedPoseTarget.to_payload) 에서만.

    pose gate 의 검증 기준(target_deg)과 **같은 출처**를 쓰는 것이 B2-01 계약이다.
    """
    joint = str(job.get("jointKey") or "")
    target = float(job.get("targetDeg") or 0.0)
    return (
        "Edit this photo so that the athlete's "
        f"{joint.replace('_', ' ')} inner angle becomes approximately {target:.0f} degrees. "
        "Keep the same person, same clothing, same pole, same camera angle and same "
        "background. Change nothing except that single joint angle. "
        "Do not add or remove limbs. Do not add other people."
    )


ROTATION_PROMPT = (
    "Orbit the camera smoothly around the athlete while keeping the athlete, the pole "
    "and the lighting unchanged. The athlete's pose must stay frozen exactly as it is; "
    "only the camera viewpoint moves. No new people, no extra limbs, no scene changes."
)


def _create_rotation(job: dict):
    """myVideoKey 를 canonical upload key 후보와 대조한 뒤에만 presign (H-05)."""
    from sunity_shared import s3keys

    bucket = _env("VIDEO_BUCKET")
    video_key = job.get("myVideoKey")
    uid = job.get("uid")
    analysis_id = job.get("analysisId")
    if not bucket or not video_key or not uid or not analysis_id:
        raise _InvalidJobInput()

    # 남의 객체를 벤더로 보내는 경로를 원천 차단한다 — key 를 신뢰하지 않고
    # 이 job 의 신원으로 만들 수 있는 후보와의 equality 로만 통과시킨다.
    candidates = {
        s3keys.build_upload_key(uid, analysis_id, fmt) for fmt in ("mp4", "mov")
    }
    if video_key not in candidates:
        raise _InvalidJobInput()

    url = _s3().generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": video_key}, ExpiresIn=3600
    )
    return _adapter(models.VISUAL_KIND_ROTATION).create_task(url, ROTATION_PROMPT)


# ── action: poll ────────────────────────────────────────────────────────


def _action_poll(job_id: str, job: dict, *, owner: str) -> None:
    from sunity_shared.analysis import visual_gen

    if job.get("state") != "polling":
        log.info("visual-worker poll unexpected state=%s job_id=%s", job.get("state"), job_id)
        return

    result = _adapter(job.get("kind")).poll(job.get("taskId"))

    if result.state == visual_gen.VENDOR_STATE_SUCCEEDED:
        # ★ URL 을 기록하지 않는다 (H3-01). fetch 가 taskId 로 재-poll 해 fresh URL 을
        # 얻고 같은 invocation 에서 즉시 다운로드한다.
        _advance(
            job_id,
            job,
            next_state="fetching",
            updates={},
            next_action="fetch",
            owner=owner,
        )
        return

    if result.state == visual_gen.VENDOR_STATE_PENDING:
        attempt = int(job.get("attempt") or 0) + 1
        if attempt >= MAX_POLLS:
            _terminal_intent(job_id, job, "timeout", owner=owner)
            return
        _advance(
            job_id,
            job,
            next_state="polling",
            updates={"attempt": attempt, "taskId": job.get("taskId")},
            next_action="poll",
            owner=owner,
            delay_s=POLL_DELAY_S,
        )
        return

    if result.state == visual_gen.VENDOR_STATE_BLOCKED:
        retry_count = int(job.get("retryCount") or 0)
        if retry_count < visual_gen.MODERATION_RETRY_MAX:
            # retry_ready 는 taskId=None 강제 + nextAction='create' (B4-03). 다음
            # retry_ready→creating 전이가 generation+1 로 승격하며 requestKey 를
            # 그 새 generation 으로 transaction 안에서 만든다 (H5-03).
            _advance(
                job_id,
                job,
                next_state="retry_ready",
                updates={"taskId": None, "attempt": 0, "retryCount": retry_count + 1},
                next_action="create",
                owner=owner,
            )
            return
        _terminal_intent(job_id, job, "moderation", owner=owner)
        return

    _terminal_intent(job_id, job, "vendor_error", owner=owner)


def _terminal_intent(job_id: str, job: dict, reason: str, *, owner: str | None) -> None:
    """kind 분기 종결 — correctedPose 는 postprocessing 경유, rotation 은 direct."""
    if job.get("kind") == models.VISUAL_KIND_CORRECTED_POSE:
        _finalize_correctedpose_intent(job_id, job, reason, owner=owner)
    else:
        _finalize_rotation_failure(job_id, job, reason, owner=owner)


# ── action 디스패치 테이블 ───────────────────────────────────────────────
# Task 2/3 에서 fetch/judge/pose_check/postprocess 가 채워진다.

_ACTION_HANDLERS: dict = {
    "poll": _action_poll,
}
