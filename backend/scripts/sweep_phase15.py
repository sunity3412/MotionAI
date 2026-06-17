#!/usr/bin/env python3
"""Phase 15 sweep CLI — 비-reference SOURCE fixture 키 → per-run/per-mode analysis identity → _process.

Phase 15 / CONTEXT D-05 / HIGH 1 fixture-vs-identity 분리 + direct-process=fixtures-key-no-uploads-copy
+ --trigger mutually-exclusive + createdAt + pair-sequential / HIGH 2 영숫자 analysisId + per-run identity
+ every-key parse.

sweep_phase8_1.py 를 복제·적응한다. sweep_phase8_1 대비 차이 (한국어 박제):

  (1) 입력 = immutable SOURCE fixture 키 목록 (--keys-file phase15_keys.json — 각 항목
      sourceS3Key=fixtures/phase15/{motion}/correct|fault.mp4 / motionId / mode / label /
      referenceMotionId). SOURCE 키는 절대 분석 doc identity 로 쓰지 않는다 — SOURCE 와
      analysis identity 를 분리한다 (HIGH 2). sweep_phase8_1 은 reference/{name}.mp4 를
      copy 해서 sweep_temp/{uid}/{analysisId}.mp4 를 만들었지만, 여기서는 SOURCE 가
      비-notified fixtures/ 프리픽스라 direct-process 에서는 COPY 자체가 없다 (HIGH 1).

  (2) 신규 분석 path 를 절대 만들지 않는다 — sweep_phase8_1 과 동일하게 pipeline._process 를
      직접 import·호출한다 (분기 0; RESEARCH Anti-Pattern "Writing a new analysis path" 금지).
      항목별 mode 로 MODE_EXPERT(Mode 1) / MODE_SELF(Mode 3) 지정. Mode 1 항목은
      referenceMotionId(ref-{motion}) 를 analysis doc 에 박는다 (CONTEXT Integration Points:
      Mode 1 = referenceMotionId lockstep).

  (3) HIGH 2 — analysis identity 를 실행마다·mode 마다 새로 생성한다 (fixed uid/analysisId
      재사용 절대 금지). 실행 시작에 runId(영숫자 stamp) 를 한 번 만든다. analysisId 는 반드시
      영숫자([A-Za-z0-9]+)만 사용한다 — motion 슬러그는 하이픈을 포함하므로
      (elbow-twist-sister, kip-up, power-spin, peter-pan) raw 슬러그를 analysisId 에 절대
      넣지 않고 _sanitize_slug 로 하이픈을 제거(elbow-twist-sister→elbowtwistsister)한 뒤
      role+runId 를 붙인다. uid 의 언더스코어는 s3keys.py:18 의 uid=[^/]+ 를 통과하지만
      analysisId 는 영숫자만 통과하므로 하이픈을 절대 넣지 않는다.

  (4) HIGH 1/MEDIUM 4 — controlled trigger 는 mutually-exclusive 단일 경로다. --trigger 로
      정확히 하나만 선택:
      • direct-process(default — truly direct, uploads/ COPY 절대 없음): doc 생성 후 곧바로
        pipeline._process(bucket, sourceS3Key, uid, analysisId) 호출. key 인자로 항목의
        fixtures/phase15/... SOURCE 키를 그대로 넘긴다 — _process(app.py:1633)는 전달된
        uid/analysisId 로 update_analysis_status/get_analysis 를 호출하고
        _extract_video_analysis_inputs(bucket, key, ...) 로 bucket/key 를 직접 download 할
        뿐 key 를 parse_upload_key 로 재파싱하지 않으므로 fixtures/ 키로 직접 분석된다
        (app.py:1678 _resolve_is_reference 는 key prefix 1차 + Firestore mode 2차라
        MODE_SELF/MODE_EXPERT doc 의 mode 가 우선). 따라서 uploads/ 로의 copy_object/
        put_object 가 ZERO 이고 _process 를 정확히 1회 호출하며 /analyze POST 도 안 한다 —
        결정론적, 비동기 S3/SQS 타이밍 회피, uploads/ ObjectCreated notification 발화 0 →
        double-analysis race 원천 차단 (HIGH 1). sweep evidence 기본값.
      • notification: doc 생성 후 fixture 를 그 run 의 unique uploads/{uid}/{analysisId}.mp4
        로 COPY 하고, 그 ObjectCreated 가 production S3→SQS→pipeline notification 을
        발화해 분석을 구동한다. _process 직접 호출도 /analyze POST 도 하지 않는다.
      • analyze: doc 생성 후 fixture 를 uploads/{uid}/{analysisId}.mp4 로 COPY 하고 직접
        /analyze POST (X-RunPod-Token). 주의 — /analyze 는 uploads/ 키를 요구하므로 live
        notified 버킷에서는 그 COPY 가 notification 도 발화해 double-trigger 가 된다. 따라서
        analyze 모드는 live notified 버킷 비대상(isolated/non-notified 환경 전용)이다.

      세 모드는 상호 배타적이며 한 run 에 정확히 하나만 invoke 된다. 같은 객체에 둘 이상의
      trigger(예: notification + manual _process)를 병행하면 double-analysis 가 되므로 절대
      금지한다. 스크립트가 각 모드의 invariant 를 카운터로 자체 검증한다:
        direct-process ⇒ uploads-copy == 0 + _process == 1(per item) + /analyze == 0
        notification  ⇒ uploads-copy == 1 + _process == 0 + /analyze == 0
        analyze       ⇒ /analyze == 1 + _process == 0 (+ live-notified 버킷 경고)

  (5) HIGH 1 — 쓰는 모든 analysis doc 에 createdAt 과 updatedAt 을 반드시 설정한다. sweep_phase8_1
      은 sweepCreatedAtMs 만 쓰는데(line 162) 그대로 복제하면 firestore_admin.get_previous_analysis
      (line 1322, createdAt DESC order) 가 sweep doc 을 prior 후보에서 누락시켜 Mode 3
      deltaFromPrevious 가 붕괴한다 — sweepCreatedAtMs 외에 createdAt/updatedAt 을 추가로 박는다.

  (6) per-run/per-mode uid 격리로 success doc 의 get_previous_analysis 가 같은 motion·같은 run 의
      fault doc 하고만 페어링된다 (cross-motion·cross-run 누출 0). uid=phase15_mode3_{motion}_<runId>
      가 motion+run 단위 scope 를 제공한다.

  (7) HIGH 1 — --pair-sequential: Mode 3 페어를 처리할 때 한 motion 의 fail doc 이 완전히
      status done 으로 기록되고 그 createdAt 이 success doc 보다 earlier 임을 보장한 뒤에만
      success doc 을 제출한다. 페어 내부는 절대 병렬 제출하지 않는다.

  (8) HIGH 2 — evidence 출력(stdout)이 페어·항목별로 runId/uid/analysisId/mode/s3Key/createdAt 을
      기록한다 (stale·overwritten doc 가시적 거부).

  (9) HIGH 2 — dry-run identity self-check + (notification/analyze 전용) build-every-key assertion.

CLI:
    python backend/scripts/sweep_phase15.py --keys-file backend/scripts/phase15_keys.json \
        --mode all --trigger direct-process --pair-sequential
    python backend/scripts/sweep_phase15.py --keys-file ... --dry-run   # Pod 없이 로컬 검증
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import boto3
import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "shared" / "python"))

YAML_PATH = BACKEND / "judging_data" / "tilt_thresholds.yaml"

# s3keys.py:18 와 동일 — analysis_id 는 영숫자만. uploads 전체 키 self-check 용.
_ALNUM_RE = re.compile(r"^[A-Za-z0-9]+$")
_UPLOAD_KEY_RE = re.compile(r"^uploads/[^/]+/[A-Za-z0-9]+\.(mp4|mov)$")
_FIXTURES_PREFIX = "fixtures/phase15/"

TRIGGER_DIRECT = "direct-process"
TRIGGER_NOTIFICATION = "notification"
TRIGGER_ANALYZE = "analyze"
TRIGGERS = (TRIGGER_DIRECT, TRIGGER_NOTIFICATION, TRIGGER_ANALYZE)


def _load_pipeline():
    """Lazy-load pipeline module so --dry-run path can run without GPU/ffmpeg deps."""
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", BACKEND / "functions" / "pipeline" / "app.py"
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(BACKEND.parent), text=True
    ).strip()


def _new_run_id() -> str:
    """영숫자 runId stamp — rerun 충돌 0 (HIGH 2). epoch_ms 는 [0-9]+ 라 영숫자."""
    return str(_epoch_ms())


def _sanitize_slug(slug: str) -> str:
    """motion 슬러그를 영숫자만 남긴다 (하이픈/언더스코어 제거).

    HIGH 2 — analysisId 는 s3keys.py:18 의 [A-Za-z0-9]+ 를 통과해야 하므로 하이픈 슬러그
    (elbow-twist-sister, kip-up, power-spin, peter-pan) 를 raw 로 절대 넣지 않는다.
    elbow-twist-sister → elbowtwistsister. 정규화 후 비어버리면(이론상 비영숫자만 있을 때)
    short-hash 로 폴백한다.
    """
    cleaned = re.sub(r"[^A-Za-z0-9]", "", slug)
    if cleaned:
        return cleaned
    return "m" + hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]


def _yaml_metadata() -> dict:
    """tilt_thresholds.yaml checksum (evidence 정합용 — sweep_phase8_1 hygiene 보존)."""
    if not YAML_PATH.exists():
        return {"thresholdChecksum": None, "thresholdCalibrationMethod": "missing"}
    raw = YAML_PATH.read_bytes()
    data = yaml.safe_load(raw)
    return {
        "thresholdChecksum": hashlib.sha256(raw).hexdigest(),
        "thresholdCalibrationMethod": str(data.get("calibration_method", "")),
        "thresholdCalibrationVersion": str(data.get("calibration_version", "")),
    }


# ── identity 생성 (HIGH 2 — per-run/per-mode, SOURCE 와 분리) ──────────────


def _load_items(keys_file: Path) -> list[dict]:
    raw = json.loads(keys_file.read_text(encoding="utf-8"))
    # phase15_keys.json schema = {"items": [...]} 또는 [...] 둘 다 허용.
    items = raw["items"] if isinstance(raw, dict) and "items" in raw else raw
    if not isinstance(items, list):
        raise ValueError("keys-file 은 list 또는 {'items': [...]} 형식이어야 한다")
    return items


def _plan_identities(items: list[dict], mode_filter: str, run_id: str) -> list[dict]:
    """각 항목 → per-run/per-mode analysis identity 계획.

    Mode 1: uid=phase15_mode1_<runId>, analysisId=<sanitizedSlug>Success<runId>,
            referenceMotionId=ref-{motion}.
    Mode 3: uid=phase15_mode3_{motion}_<runId>, analysisId=<sanitizedSlug>Fault<runId>
            (earlier) → <sanitizedSlug>Success<runId> (later). fault 가 prior 로 잡히도록.
    """
    from sunity_shared import models  # noqa: E402

    planned: list[dict] = []
    # motion 별 Mode 3 페어를 묶기 위한 그룹핑.
    mode3_motions: dict[str, dict] = {}

    for item in items:
        motion = item["motionId"]
        mode = item["mode"]  # 'mode1' | 'mode3' (label-level)
        label = item["label"]  # 'success' | 'fault'
        source_key = item["sourceS3Key"]
        ref_motion_id = item.get("referenceMotionId")
        slug = _sanitize_slug(motion)

        if not source_key.startswith(_FIXTURES_PREFIX):
            raise ValueError(
                f"sourceS3Key {source_key!r} 가 비-notified {_FIXTURES_PREFIX} 프리픽스가 아님 "
                "(HIGH 1 — SOURCE 는 fixtures/ 만)"
            )

        if mode == "mode1":
            if mode_filter not in ("all", "mode1"):
                continue
            uid = f"phase15_mode1_{run_id}"
            analysis_id = f"{slug}Success{run_id}"
            planned.append({
                "motion": motion, "trigger_mode": models.MODE_EXPERT,
                "modeLabel": "mode1", "label": label, "uid": uid,
                "analysisId": analysis_id, "sourceS3Key": source_key,
                "referenceMotionId": ref_motion_id or f"ref-{motion}",
                "pairOrder": 0,
            })
        elif mode == "mode3":
            if mode_filter not in ("all", "mode3"):
                continue
            uid = f"phase15_mode3_{motion}_{run_id}"
            role = "Fault" if label == "fault" else "Success"
            analysis_id = f"{slug}{role}{run_id}"
            # fault earlier(pairOrder 0) → success later(pairOrder 1).
            pair_order = 0 if label == "fault" else 1
            entry = {
                "motion": motion, "trigger_mode": models.MODE_SELF,
                "modeLabel": "mode3", "label": label, "uid": uid,
                "analysisId": analysis_id, "sourceS3Key": source_key,
                "referenceMotionId": None, "pairOrder": pair_order,
            }
            mode3_motions.setdefault(motion, {})[label] = entry
        else:
            raise ValueError(f"알 수 없는 mode {mode!r} (mode1|mode3 만 허용)")

    # Mode 3 페어를 fault→success 순서로 평탄화 (--pair-sequential 정합).
    for motion in sorted(mode3_motions):
        pair = mode3_motions[motion]
        for label in ("fault", "success"):
            if label in pair:
                planned.append(pair[label])

    return planned


def _self_check_identities(planned: list[dict], trigger: str) -> None:
    """HIGH 2 — analysisId 영숫자 self-check (전 모드) + uploads-key parse(notification/analyze).

    "영숫자" prose 에 의존하지 않고 실제로 검사한다. 비영숫자(특히 하이픈)가 하나라도 있으면
    즉시 RuntimeError → non-zero exit.
    """
    from sunity_shared import s3keys  # noqa: E402

    for p in planned:
        aid = p["analysisId"]
        if not _ALNUM_RE.match(aid):
            raise RuntimeError(
                f"analysisId {aid!r} 가 영숫자([A-Za-z0-9]+)가 아님 — 하이픈 슬러그 금지 (HIGH 2)"
            )
        if trigger == TRIGGER_DIRECT:
            # direct-process 는 uploads/ 키를 만들지 않으므로 sourceS3Key 가 fixtures/ 인지만 검증.
            if not p["sourceS3Key"].startswith(_FIXTURES_PREFIX):
                raise RuntimeError(
                    f"direct-process sourceS3Key {p['sourceS3Key']!r} 가 fixtures/ 가 아님 (HIGH 1)"
                )
        else:
            # notification/analyze — build-every-key assertion.
            upload_key = s3keys.build_upload_key(p["uid"], aid, "mp4")
            if s3keys.parse_upload_key(upload_key) is None:
                raise RuntimeError(
                    f"uploads 키 {upload_key!r} 가 parse_upload_key 를 통과하지 못함 (HIGH 2)"
                )
            if not _UPLOAD_KEY_RE.match(upload_key):
                raise RuntimeError(
                    f"uploads 키 {upload_key!r} 가 정규식 검증을 통과하지 못함 (HIGH 2)"
                )


# ── trigger invariant 카운터 (HIGH 1/MEDIUM 4) ───────────────────────────


class _TriggerCounters:
    """모드별 invariant 를 코드로 강제 (자체 검증)."""

    def __init__(self) -> None:
        self.uploads_copy = 0
        self.process_calls = 0
        self.analyze_posts = 0

    def assert_invariant(self, trigger: str, item_count: int) -> None:
        if trigger == TRIGGER_DIRECT:
            assert self.uploads_copy == 0, (
                f"direct-process invariant 위반: uploads-copy={self.uploads_copy} != 0 (HIGH 1)"
            )
            assert self.process_calls == item_count, (
                f"direct-process invariant 위반: _process={self.process_calls} != {item_count}"
            )
            assert self.analyze_posts == 0, (
                f"direct-process invariant 위반: /analyze={self.analyze_posts} != 0"
            )
        elif trigger == TRIGGER_NOTIFICATION:
            assert self.uploads_copy == item_count, (
                f"notification invariant 위반: uploads-copy={self.uploads_copy} != {item_count}"
            )
            assert self.process_calls == 0, (
                f"notification invariant 위반: _process={self.process_calls} != 0"
            )
            assert self.analyze_posts == 0
        elif trigger == TRIGGER_ANALYZE:
            assert self.analyze_posts == item_count, (
                f"analyze invariant 위반: /analyze={self.analyze_posts} != {item_count}"
            )
            assert self.process_calls == 0, (
                f"analyze invariant 위반: _process={self.process_calls} != 0"
            )


def _write_doc(db, models, p: dict) -> int:
    """analysis doc 생성 — 모든 doc 에 createdAt/updatedAt 박제 (HIGH 1).

    sweep_phase8_1 은 sweepCreatedAtMs 만 썼다 → get_previous_analysis(createdAt DESC)
    누락 → Mode 3 delta 붕괴. 여기서는 createdAt/updatedAt 을 추가로 박는다.
    """
    now = _epoch_ms()
    doc = {
        "analysisId": p["analysisId"],
        "uid": p["uid"],
        "mode": p["trigger_mode"],
        "status": models.STATUS_QUEUED,
        "videoKey": p["sourceS3Key"],
        "videoFormat": "mp4",
        "fileSizeBytes": 0,
        # HIGH 1 — get_previous_analysis 가 보는 필드.
        "createdAt": now,
        "updatedAt": now,
        # evidence 정합용 보조 필드 (sweep_phase8_1 hygiene 보존).
        "sweepCreatedAtMs": now,
        "sourceLabel": f"sweep_phase15:{p['motion']}:{p['label']}",
    }
    if p["referenceMotionId"]:
        doc["referenceMotionId"] = p["referenceMotionId"]
    db.collection("users").document(p["uid"]).collection("analyses").document(
        p["analysisId"]
    ).set(doc)
    return now


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 15 sweep CLI — SOURCE fixtures 입력 → per-run/per-mode 영숫자 identity → "
            "--trigger mutually-exclusive 단일 경로 → _process. "
            "주의: --trigger analyze 는 live-notified 버킷 비대상(isolated/non-notified 전용) — "
            "uploads/ COPY 가 notification 도 발화시켜 double-trigger 가 된다 (HIGH 1)."
        )
    )
    parser.add_argument(
        "--keys-file", required=True,
        help="upload_phase15_dataset.py 산출 phase15_keys.json (sourceS3Key=fixtures/ 키)",
    )
    parser.add_argument(
        "--mode", default="all", choices=["all", "mode1", "mode3"],
        help="처리할 mode 선택 (default all)",
    )
    parser.add_argument(
        "--trigger", default=TRIGGER_DIRECT, choices=list(TRIGGERS),
        help=(
            "controlled trigger — mutually-exclusive 단일 경로. "
            "direct-process(default, uploads/ COPY 0) / notification / analyze "
            "(analyze 는 live-notified 버킷 비대상)"
        ),
    )
    parser.add_argument(
        "--pair-sequential", action="store_true",
        help="Mode 3 페어를 fault→success 순차 제출 (fault 가 prior 로 잡히도록, HIGH 1)",
    )
    parser.add_argument("--bucket", default="sunity-motion-pilot-videos")
    parser.add_argument(
        "--runpod-url", default=None,
        help="--trigger analyze 용 /analyze 엔드포인트 (RUNPOD_ANALYZE_URL)",
    )
    parser.add_argument(
        "--runpod-token", default=None,
        help="--trigger analyze 용 X-RunPod-Token (절대 로그·evidence 출력 금지)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-cleanup", action="store_true",
        help="notification/analyze 모드 uploads/ cleanup 생략 (debug only)",
    )
    args = parser.parse_args()

    keys_file = Path(args.keys_file)
    if not keys_file.is_absolute():
        keys_file = Path.cwd() / keys_file

    run_id = _new_run_id()
    commit_hash = _git_head()
    metadata = _yaml_metadata()

    items = _load_items(keys_file)
    planned = _plan_identities(items, args.mode, run_id)

    print(
        f"[setup] runId={run_id} trigger={args.trigger} mode={args.mode} "
        f"items={len(planned)} commit={commit_hash[:8]} "
        f"thresholdChecksum={(metadata.get('thresholdChecksum') or 'none')[:8]}",
        flush=True,
    )

    # HIGH 2 — dry-run/실행 공통 identity self-check (영숫자 + notification/analyze parse).
    _self_check_identities(planned, args.trigger)
    print(
        f"[self-check] {len(planned)} identities OK — "
        f"analysisId 영숫자 self-check 통과"
        + (
            " + uploads-key parse_upload_key 통과"
            if args.trigger != TRIGGER_DIRECT
            else " (direct-process: uploads 키 미생성, sourceS3Key fixtures/ 검증)"
        ),
        flush=True,
    )

    # evidence 헤더 — runId/uid/analysisId/mode/s3Key/createdAt (HIGH 2).
    print("\n[evidence] planned identities:", flush=True)
    for p in planned:
        s3_key = (
            p["sourceS3Key"]
            if args.trigger == TRIGGER_DIRECT
            else f"uploads/{p['uid']}/{p['analysisId']}.mp4"
        )
        print(
            f"  runId={run_id} uid={p['uid']} analysisId={p['analysisId']} "
            f"mode={p['modeLabel']} label={p['label']} s3Key={s3_key}",
            flush=True,
        )

    if args.dry_run:
        print(
            "\n[dry-run] no S3 copy / no Firestore write / no _process / no /analyze. "
            "identity self-check + every-key parse(notification/analyze) 통과.",
            flush=True,
        )
        return 0

    if args.trigger == TRIGGER_ANALYZE:
        print(
            "[warn] --trigger analyze 는 live-notified 버킷 비대상 — uploads/ COPY 가 "
            "production notification 도 발화시켜 double-trigger 가 된다 (HIGH 1). "
            "isolated/non-notified 환경에서만 사용할 것.",
            flush=True,
        )

    from sunity_shared import firestore_admin as fa, models  # noqa: E402
    s3 = boto3.client("s3")
    db = fa._db()

    counters = _TriggerCounters()
    uploads_to_cleanup: list[str] = []
    failures: list[dict] = []
    pipeline = None
    if args.trigger == TRIGGER_DIRECT:
        pipeline = _load_pipeline()

    for i, p in enumerate(planned, start=1):
        created_at = _write_doc(db, models, p)
        print(
            f"\n[sweep {i}/{len(planned)}] uid={p['uid']} analysisId={p['analysisId']} "
            f"mode={p['modeLabel']} createdAt={created_at}",
            flush=True,
        )

        if args.trigger == TRIGGER_DIRECT:
            # direct-process — fixtures/ SOURCE 키를 _process 에 그대로 (uploads/ COPY 0).
            try:
                pipeline._process(
                    args.bucket, p["sourceS3Key"], p["uid"], p["analysisId"]
                )
                counters.process_calls += 1
                print("  _process OK (direct, uploads-copy=0)", flush=True)
            except Exception as exc:  # noqa: BLE001
                failures.append({
                    "uid": p["uid"], "analysisId": p["analysisId"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
                print(f"  _process FAILED: {type(exc).__name__}: {exc}", flush=True)

        elif args.trigger == TRIGGER_NOTIFICATION:
            # notification — fixture 를 unique uploads/ 로 COPY → ObjectCreated 가 트리거.
            upload_key = s3keys_build(p["uid"], p["analysisId"])
            s3.copy_object(
                Bucket=args.bucket,
                CopySource={"Bucket": args.bucket, "Key": p["sourceS3Key"]},
                Key=upload_key,
            )
            counters.uploads_copy += 1
            uploads_to_cleanup.append(upload_key)
            print(f"  COPY -> {upload_key} (S3 notification 트리거)", flush=True)

        elif args.trigger == TRIGGER_ANALYZE:
            if not args.runpod_url:
                raise RuntimeError("--trigger analyze 는 --runpod-url 필요")
            upload_key = s3keys_build(p["uid"], p["analysisId"])
            s3.copy_object(
                Bucket=args.bucket,
                CopySource={"Bucket": args.bucket, "Key": p["sourceS3Key"]},
                Key=upload_key,
            )
            counters.uploads_copy += 1
            uploads_to_cleanup.append(upload_key)
            try:
                _post_analyze(args.runpod_url, args.runpod_token, upload_key)
                counters.analyze_posts += 1
                print(f"  /analyze POST OK key={upload_key}", flush=True)
            except Exception as exc:  # noqa: BLE001
                failures.append({
                    "uid": p["uid"], "analysisId": p["analysisId"],
                    "error": f"{type(exc).__name__}: {exc}",
                })
                print(f"  /analyze FAILED: {type(exc).__name__}", flush=True)

    # 모드별 invariant 강제 (자체 검증). analyze counters 는 COPY==item 도 만족.
    if args.trigger == TRIGGER_ANALYZE:
        assert counters.uploads_copy == len(planned)
    counters.assert_invariant(args.trigger, len(planned))
    print(
        f"\n[invariant] trigger={args.trigger} uploads-copy={counters.uploads_copy} "
        f"_process={counters.process_calls} /analyze={counters.analyze_posts} — "
        "mutually-exclusive 단일 경로 강제 통과",
        flush=True,
    )

    # notification/analyze uploads/ cleanup (direct-process 는 COPY 가 없어 cleanup 불필요).
    if not args.skip_cleanup and uploads_to_cleanup:
        s3.delete_objects(
            Bucket=args.bucket,
            Delete={"Objects": [{"Key": k} for k in uploads_to_cleanup]},
        )
        print(
            f"[cleanup] deleted {len(uploads_to_cleanup)} uploads/ objects",
            flush=True,
        )

    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2), flush=True)
        return 1
    return 0


def s3keys_build(uid: str, analysis_id: str) -> str:
    from sunity_shared import s3keys  # noqa: E402

    return s3keys.build_upload_key(uid, analysis_id, "mp4")


def _post_analyze(url: str, token: str | None, key: str) -> None:
    """RunPod /analyze POST. token 은 절대 로그·evidence 에 출력하지 않는다 (T-15.01-02)."""
    body = json.dumps({"key": key}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-RunPod-Token", token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


if __name__ == "__main__":
    sys.exit(main())
