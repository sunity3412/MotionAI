"""Full batch 증류 러너 — selectable 전 행(129) 재개 가능 순차 실행 (22-04 Task 4 배선).

run_trial_batch(시험 배치)의 행별 규율을 그대로 재사용한다: S3 다운로드 →
distill_video(File API 업로드→교사→즉시 삭제 finally) → judge → evaluate_filters.
밤새 6시간급 프로세스를 위한 추가 규율:

  · resumable — 행별 결과 파일(out_dir/reports/<s3_key slug>.json)이 터미널 사유
    (accepted / rejected_*)면 skip(과금 재발 0). "error"/"ABORT_429" 는 재시도 대상.
    좌표는 pod_coords video_hash/slug 캐시와 정합 — 재실행 시 RTMW 재추출 0.
  · accepted 영속화 — 수락 행을 out_dir/accepted/<slug>.json 에 즉시 기록(메모리
    반환 의존 금지). build_jsonl distill_loader 계약 필드(video_hash / s3_key /
    motion / thought / report / joint_keys / coords_by_frame) 포함.
  · 429/RESOURCE_EXHAUSTED 즉시 중단([[gemini-credits-depleted-2026-06-20]]) +
    진행 로그 [N/total].

build_jsonl 연결(assemble_jsonl): accepted 디렉토리 → distill_loader + manifest
video_hash 주입(manifest 행은 video_hash 부재라 s3_key 로 join 보강) → train/val
JSONL. S3 업로드는 uploader 주입 시에만(gated — 기본은 로컬 기록만).

실행은 PHASE22_BELLE_GREENLIGHT=1 필요(DR-05). 순수 로직(skip/영속화/조립)은
fake client 로 네트워크 0 테스트(test_full_batch.py). 파이프라인은 동시성 비안전
— 반드시 순차 실행([[pipeline-not-concurrency-safe-eval-serial]]).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from distill import gemini_teacher as gt

log = logging.getLogger("full_batch")
if not log.handlers:
    log.setLevel(logging.INFO)

_BACKEND = Path(__file__).resolve().parents[2]
_DEFAULT_BUCKET = "sunity-motion-pilot-videos"

# 터미널 사유 — 재실행 시 skip(과금 0). "error"(일시 오류)/"ABORT_429" 는 재시도.
TERMINAL_RESULTS = frozenset({
    "accepted",
    "rejected_parse",
    "rejected_judge",
    "rejected_repetition",
    "rejected_physics",
    "rejected_bone",
    "rejected_contract",
})


# ---------------------------------------------------------------------------
# 행별 결과/수락 파일 — gemini_teacher slug 규칙 재사용(경로 충돌 0).
# ---------------------------------------------------------------------------
def load_row_result(reports_dir: str, s3_key: str):
    """행별 결과 파일 로드 — 부재/손상이면 None(재처리 대상)."""
    path = gt._trial_report_path(reports_dir, s3_key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except (json.JSONDecodeError, OSError):
        log.warning("행 결과 파일 손상 — 재처리: %s", path)
        return None


def is_terminal(payload) -> bool:
    """결과가 터미널 사유(accepted/rejected_*)면 True — 재실행 skip 판정."""
    return bool(payload) and payload.get("result") in TERMINAL_RESULTS


def _accepted_path(accepted_dir: str, s3_key: str) -> str:
    return gt._trial_report_path(accepted_dir, s3_key)


def save_accepted(accepted_dir: str, s3_key: str, sample: dict) -> str:
    """수락 샘플 행별 즉시 영속화 — build_jsonl distill_loader 계약 필드 포함."""
    os.makedirs(accepted_dir, exist_ok=True)
    path = _accepted_path(accepted_dir, s3_key)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(sample, fp, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def _accepted_sample(row: dict, video_hash, thought, report, joint_keys, coords_by_frame) -> dict:
    return {
        "video_hash": video_hash,
        "s3_key": row.get("s3_key"),
        "motion": row.get("motion"),
        "thought": thought,
        "report": report,
        "joint_keys": list(joint_keys),
        "coords_by_frame": coords_by_frame or [],
    }


def _ensure_accepted_file(accepted_dir, row, payload, coords_provider, joint_keys) -> None:
    """skip 경로에서 accepted 파일이 유실됐으면 결과 파일 + 좌표 캐시로 재구성.

    Gemini 재호출 0 — parsed(thought/report)는 결과 파일에, 좌표는 pod_coords 캐시에
    이미 있다(캐시 miss 시 빈 좌표로 재구성하고 경고 — 재과금 대신 진단 로그).
    """
    path = _accepted_path(accepted_dir, row.get("s3_key") or "")
    if os.path.exists(path):
        return
    parsed = payload.get("parsed") or {}
    coords = coords_provider(row) if coords_provider else []
    if not coords:
        log.warning("accepted 재구성: 좌표 캐시 miss — 빈 좌표로 기록 s3=%s", row.get("s3_key"))
    save_accepted(accepted_dir, row.get("s3_key") or "unknown", _accepted_sample(
        row, payload.get("video_hash"), parsed.get("thought"), parsed.get("report"),
        joint_keys, coords,
    ))


# ---------------------------------------------------------------------------
# 통계 집계 — 결과 파일이 진실(메모리 아님). 재개 run 도 전 행 기준 집계.
# ---------------------------------------------------------------------------
def aggregate_stats(reports_dir: str, rows) -> dict:
    """selectable 전 행 기준 결과 파일 집계 — {사유: count} + error/pending/ABORT_429."""
    stats = {k: 0 for k in sorted(TERMINAL_RESULTS)}
    stats.update({"error": 0, "ABORT_429": 0, "pending": 0})
    for row in rows:
        payload = load_row_result(reports_dir, row.get("s3_key") or "")
        if payload is None:
            stats["pending"] += 1
            continue
        result = payload.get("result")
        stats[result if result in stats else "error"] += 1
    return stats


def _video_hash(local_path: str):
    try:
        from sunity_shared.analysis.technique_cache import compute_video_hash

        return compute_video_hash(local_path)
    except Exception:  # noqa: BLE001 - hash 실패는 배치를 막지 않는다.
        return None


# ---------------------------------------------------------------------------
# full batch 러너.
# ---------------------------------------------------------------------------
def run_full_batch(
    manifest: dict,
    out_dir: str,
    scratch_dir: str,
    *,
    bucket: str = _DEFAULT_BUCKET,
    joint_keys=gt.DEFAULT_TASK_JOINTS,
    coords_provider=None,
    client=None,
    max_rows: int | None = None,
    probe: bool = True,
) -> dict:
    """selectable 전 행 순차 증류 — 재개 가능 + 행별 영속화 + 429 즉시 중단.

    행당: (터미널 결과 존재 → skip) → S3 다운로드 → coords_provider(row)(캐시 hit
    재사용, miss 는 scratch 다운로드본으로 RTMW 추출·캐시) → distill_video(즉시 삭제
    finally) → judge → evaluate_filters → 결과/수락 파일 즉시 기록 → 다운로드본 삭제.

    반환은 요약만(accepted 는 디스크가 진실): {stats, aborted, n_total, n_skipped,
    n_processed, residue_before/after, elapsed_s, reports_dir, accepted_dir, probe}.
    """
    client = client or gt._ensure_client()
    reports_dir = os.path.join(out_dir, "reports")
    accepted_dir = os.path.join(out_dir, "accepted")
    for d in (reports_dir, accepted_dir, scratch_dir):
        os.makedirs(d, exist_ok=True)

    rows = gt.selectable_rows(manifest)
    if max_rows is not None:
        rows = rows[: max(0, int(max_rows))]
    total = len(rows)

    probe_result = None
    if probe:
        probe_result = gt.probe_quota(client)
        if not probe_result["ok"]:
            log.warning("quota probe 실패 — 배치 시작 전 중단: %s", probe_result["error"])
            return {
                "stats": aggregate_stats(reports_dir, rows),
                "aborted": f"probe:{probe_result['error']}",
                "n_total": total, "n_skipped": 0, "n_processed": 0,
                "residue_before": probe_result.get("residue"), "residue_after": None,
                "elapsed_s": 0.0, "reports_dir": reports_dir, "accepted_dir": accepted_dir,
                "probe": probe_result,
            }

    residue_before = gt.list_file_residue(client)
    aborted = None
    n_skipped = 0
    n_processed = 0
    start = time.monotonic()

    for i, row in enumerate(rows, 1):
        s3_key = row["s3_key"]
        existing = load_row_result(reports_dir, s3_key)
        if is_terminal(existing):
            n_skipped += 1
            if existing.get("result") == "accepted":
                _ensure_accepted_file(accepted_dir, row, existing, coords_provider, joint_keys)
            log.info("[%d/%d] skip(%s) %s", i, total, existing.get("result"), s3_key)
            continue

        local = os.path.join(scratch_dir, os.path.basename(s3_key))
        parsed = None
        vh = None
        coords = []
        try:
            gt._download_s3(bucket, s3_key, local)
            vh = _video_hash(local)
            coords = coords_provider(row) if coords_provider else []
            parsed = gt.distill_video(
                client, local, coords, joint_keys, motion=row.get("motion")
            )
            judge_score = 0
            if parsed and parsed.get("report"):
                judge_score = gt.judge_report(
                    client, parsed["report"], motion=row.get("motion")
                )
            accepted, reason = gt.evaluate_filters(parsed, judge_score)
        except Exception as exc:  # noqa: BLE001 - 429 즉시 중단 / 기타는 error 재시도 대상.
            if gt._is_quota_error(exc):
                aborted = f"quota_exhausted at {s3_key}: {str(exc)[:160]}"
                gt._save_trial_report(reports_dir, s3_key, {
                    "s3_key": s3_key, "result": "ABORT_429", "error": str(exc)[:200],
                    "raw_text": (parsed or {}).get("raw_text"),
                })
                log.warning("[%d/%d] ABORT_429 %s — 배치 즉시 중단", i, total, s3_key)
                break
            gt._save_trial_report(reports_dir, s3_key, {
                "s3_key": s3_key, "result": "error", "error": str(exc)[:200],
                "raw_text": (parsed or {}).get("raw_text"),
            })
            log.warning("[%d/%d] error %s: %s", i, total, s3_key, str(exc)[:160])
            continue
        finally:
            try:
                os.remove(local)
            except OSError:
                pass

        n_processed += 1
        gt._save_trial_report(reports_dir, s3_key, {
            "s3_key": s3_key,
            "motion": row.get("motion"),
            "video_hash": vh,
            "raw_text": (parsed or {}).get("raw_text"),
            "parsed": {
                "thought": (parsed or {}).get("thought"),
                "report": (parsed or {}).get("report"),
            },
            "judge": judge_score,
            "result": reason,
        })
        if accepted and parsed:
            save_accepted(accepted_dir, s3_key, _accepted_sample(
                row, vh, parsed.get("thought"), parsed.get("report"), joint_keys, coords,
            ))
        log.info("[%d/%d] %s → %s (judge=%s)", i, total, s3_key, reason, judge_score)

    elapsed = time.monotonic() - start
    residue_after = gt.list_file_residue(client)
    return {
        "stats": aggregate_stats(reports_dir, rows),
        "aborted": aborted,
        "n_total": total,
        "n_skipped": n_skipped,
        "n_processed": n_processed,
        "residue_before": residue_before,
        "residue_after": residue_after,
        "elapsed_s": round(elapsed, 2),
        "reports_dir": reports_dir,
        "accepted_dir": accepted_dir,
        "probe": probe_result,
    }


# ---------------------------------------------------------------------------
# build_jsonl 연결 — accepted 디렉토리 → distill_loader + manifest hash 주입.
# ---------------------------------------------------------------------------
def make_distill_loader(accepted_dir):
    """accepted/<slug>.json 전부를 distill 레코드로 로드하는 loader(build_jsonl 계약)."""
    def loader():
        recs = []
        for p in sorted(Path(accepted_dir).glob("*.json")):
            try:
                recs.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                log.warning("accepted 파일 손상 — 제외: %s", p)
        return recs

    return loader


def manifest_with_hashes(manifest: dict, accepted_dir) -> dict:
    """accepted 레코드의 s3_key→video_hash 를 manifest 행 사본에 주입.

    manifest 행은 video_hash 필드가 없어(22-02 산출) build_jsonl distill join
    (video_hash 기준)이 그대로는 0건이 된다 — 배치가 계산한 hash 로 보강한다.
    manifest 파일 자체는 수정하지 않는다(사본 반환).
    """
    import copy

    by_key = {}
    for rec in make_distill_loader(accepted_dir)():
        if rec.get("s3_key") and rec.get("video_hash"):
            by_key[rec["s3_key"]] = rec["video_hash"]
    m = copy.deepcopy(manifest)
    for row in m.get("rows", []):
        vh = by_key.get(row.get("s3_key"))
        if vh and not row.get("video_hash"):
            row["video_hash"] = vh
    return m


def make_perturb_loader(cache_dir):
    """RTMW 좌표 캐시 → build_jsonl perturb_loader 계약 (D-10a, GPU·과금 0).

    22-07 게이트 FAIL 처방 A(belle 2026-07-12): v1 학습셋은 perturb 트랙 0행이라
    좌표 보정 감독이 없었다 — 캐시 좌표(pod_coords, 22-04 배치가 적재)를 역변환해
    perturb 트랙을 주입한다. 캐시 miss 행은 None(트랙에서 자연 제외)."""
    from distill import pod_coords  # lazy — numpy 외 의존 없음(캐시 파일 I/O).

    def loader(row):
        rows = pod_coords.load_cached_coords(cache_dir, pod_coords.coords_cache_key(row))
        if not rows:
            # 캐시는 배치 시점(video_hash 부재)의 s3 슬러그 키로 적재됐다 —
            # manifest_with_hashes 가 hash 를 주입한 뒤에는 슬러그로 폴백해야 hit.
            rows = pod_coords.load_cached_coords(
                cache_dir, pod_coords.coords_cache_key({"s3_key": (row or {}).get("s3_key")})
            )
        if not rows:
            return None
        arr = pod_coords.rows_to_task_array(rows)
        if arr.shape[0] == 0:
            return None
        return {
            "coords": arr,
            "joint_keys": list(pod_coords.DEFAULT_TASK_JOINTS),
            "width": 1.0,   # 캐시 좌표는 정규화 [0,1] — discretize 계약 (pod_coords).
            "height": 1.0,
        }

    return loader


def make_s3_uploader(bucket: str = _DEFAULT_BUCKET):
    """S3 업로더 factory — assemble_jsonl(uploader=...) 주입용. 기본 경로는 미사용(gated)."""
    import boto3  # lazy

    s3 = boto3.client("s3", region_name="ap-northeast-2")

    def upload(local_path: str, key: str) -> None:
        s3.upload_file(local_path, bucket, key)

    return upload


def assemble_jsonl(
    manifest: dict,
    accepted_dir,
    out_dir,
    *,
    validation_owner: str = "explicit_val_jsonl",
    partial: bool = False,
    perturb_loader=None,
    shadow_loader=None,
    reference_loader=None,
    mix_ratios=None,
    seed: int = 0,
    uploader=None,
) -> dict:
    """accepted 디렉토리 → train/val JSONL 조립(build_jsonl 재사용) + gated 업로드.

    uploader=None(기본)이면 로컬 기록만 — S3 업로드는 uploader 주입 시에만 수행한다
    (prefix 는 build_jsonl.resolve_upload_prefix 가 소유: partial 은 canonical 금지).
    perturb/shadow 트랙 loader 는 주입식 — 미주입 시 distill 트랙만 조립된다.
    """
    from datagen import build_jsonl

    m = manifest_with_hashes(manifest, accepted_dir)
    data = build_jsonl.build_dataset(
        manifest=m,
        perturb_loader=perturb_loader,
        # C1 (belle 2026-07-15): build_dataset 기본 include_perturb=False. 이 orchestrator
        # 층의 계약은 loader 주입=의도(--with-perturb) 이므로 loader 유무로 include 를
        # 유도한다 — 미주입 시 distill 트랙만(기존 동작 불변), 주입 시 perturb 부활(가역).
        include_perturb=perturb_loader is not None,
        distill_loader=make_distill_loader(accepted_dir),
        shadow_loader=shadow_loader,
        reference_loader=reference_loader,
        mix_ratios=mix_ratios,
        validation_owner=validation_owner,
        partial=partial,
        seed=seed,
    )
    paths = build_jsonl.write_dataset(data, Path(out_dir))
    uploaded: list[str] = []
    if uploader is not None:
        prefix = build_jsonl.resolve_upload_prefix(partial)
        name_map = {"train": "train.jsonl", "val": "val.jsonl", "meta": "_meta.json"}
        for kind, local in paths.items():
            key = prefix + name_map.get(kind, os.path.basename(local))
            uploader(local, key)
            uploaded.append(key)
    return {"paths": paths, "uploaded": uploaded, "meta": data["_meta"]}


if __name__ == "__main__":  # pragma: no cover - 실 실행은 메인 세션(Pod, belle-gated).
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="Phase 22 full batch 증류 러너 (재개 가능)")
    ap.add_argument("--manifest", default=str(_BACKEND / "training" / "data" / "manifest.json"))
    ap.add_argument("--out-dir", default="/workspace/phase22_distill_out")
    ap.add_argument("--scratch-dir", default="/workspace/phase22_distill_scratch")
    ap.add_argument("--cache-dir", default="/workspace/phase22_coords_cache")
    ap.add_argument("--bucket", default=_DEFAULT_BUCKET)
    ap.add_argument("--max-rows", type=int, default=None)
    ap.add_argument("--assemble", action="store_true",
                    help="배치 대신 accepted → train/val JSONL 조립(과금 0)")
    ap.add_argument("--with-perturb", action="store_true",
                    help="--assemble 시 perturb 트랙 주입(좌표 캐시 필요 — 22-07 처방 A)")
    ap.add_argument("--upload", action="store_true",
                    help="--assemble 시 S3 업로드(gated — greenlight 필수)")
    ap.add_argument("--validation-owner", default="explicit_val_jsonl",
                    choices=("explicit_val_jsonl", "phase22_eval_gate"))
    ap.add_argument("--partial", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    if args.assemble:
        if args.upload and not gt._greenlight_ready():
            raise SystemExit(
                f"{gt._GREENLIGHT_ENV}=1 미설정 — S3 업로드는 belle 승인(DR-05) 후."
            )
        result = assemble_jsonl(
            manifest,
            os.path.join(args.out_dir, "accepted"),
            os.path.join(args.out_dir, "jsonl"),
            validation_owner=args.validation_owner,
            partial=args.partial,
            perturb_loader=make_perturb_loader(args.cache_dir) if args.with_perturb else None,
            uploader=make_s3_uploader(args.bucket) if args.upload else None,
        )
        print(json.dumps(
            {"paths": result["paths"], "uploaded": result["uploaded"], "meta": result["meta"]},
            ensure_ascii=False, indent=2,
        ))
        raise SystemExit(0)

    if not gt._greenlight_ready():
        raise SystemExit(
            f"{gt._GREENLIGHT_ENV}=1 미설정 — 과금 배치는 belle 승인(DR-05) 후 실행."
        )
    from distill import pod_coords  # lazy — GPU/Pod 의존은 배치 실행 시에만.

    provider = pod_coords.make_coords_provider(args.cache_dir, args.scratch_dir)
    result = run_full_batch(
        manifest, args.out_dir, args.scratch_dir,
        bucket=args.bucket, coords_provider=provider, max_rows=args.max_rows,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
