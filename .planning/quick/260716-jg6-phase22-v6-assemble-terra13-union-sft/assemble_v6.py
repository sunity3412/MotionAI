"""phase22 v6 학습셋 조립 스크립트 — 복원 + terra13 union + assemble (quick-260716-jg6).

배경(사전 조사, PLAN.md):
  현재 S3 `training/phase22/jsonl/` = pre-v6 (perturb 166 + distill 152 + text 48,
  B/C1 미적용, terra 미반영). distill full_batch 가 산출한 accepted/ 라벨은 종료된
  Pod 볼륨과 함께 소실됐다. 단 현재 train.jsonl/val.jsonl 의 distill 152행이 accepted
  라벨을 무손실로 담고 있어(system=joint_keys, user=s3_key+RTMW_Data, assistant=report)
  여기서 accepted 레코드를 역복원할 수 있다.

이 스크립트는:
  1. 현재 S3 jsonl/ 다운로드 → distill 152행에서 accepted 레코드 복원.
  2. terra_collect(149행)에서 terra_fault_count > gemini_fault_count 인 13영상 선별,
     각 video_hash 의 report.faults 에 terra faults 를 union(계약 안전장치 + dedup).
  3. 복원 accepted 를 tmp accepted_dir 에 기록 → full_batch.assemble_jsonl 을 무변형
     호출(manifest_with_hashes + build_dataset). perturb_loader 미주입 → include_perturb
     =False(C1), B cap 자동, video_hash split(leakage 0), _meta 방출.
  4. 검증 게이트 산출(SUMMARY 기재). --upload 시에만(전 게이트 PASS 후) S3 백업→교체.

프로덕션 코드 0 수정 — backend/ 는 전부 import 재사용. 이 파일만 신규.

규율:
  · terra union 후 schema.normalize_report + build_jsonl._faults_satisfy_contract 로
    각 terra fault 를 개별 검증 — 계약 위반 terra fault 만 드롭(gemini fault·행 보존).
    F1 계약 필터(_build_distill_samples)는 미충족 행을 통째 폐기하므로 선제 방어.
  · manifest_with_hashes + build_dataset 은 무변형 호출(split/cap/balance 재구현 금지).
  · 네트워크(S3) 필요 — AWS_PROFILE=sunity-motion, region ap-northeast-2.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ── 경로 배선: backend/training + backend/shared/python 을 sys.path 에 주입 ──
_REPO = Path(__file__).resolve().parents[3]
_BACKEND = _REPO / "backend"
_TRAINING = _BACKEND / "training"
_SHARED = _BACKEND / "shared" / "python"
for p in (str(_TRAINING), str(_SHARED)):
    if p not in sys.path:
        sys.path.insert(0, p)

from datagen import build_jsonl, schema  # noqa: E402  (경로 주입 후 import)
from distill import full_batch  # noqa: E402

log = logging.getLogger("assemble_v6")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

# ── 상수 ──
_BUCKET = "sunity-motion-pilot-videos"
_REGION = "ap-northeast-2"
_CANONICAL_PREFIX = "training/phase22/jsonl/"
_BACKUP_PREFIX = "training/phase22/jsonl_v5_backup/"
_S3_URI_PREFIX = f"s3://{_BUCKET}/"
_MANIFEST_PATH = _BACKEND / "training" / "data" / "manifest.json"
_TERRA_PATH = (
    _REPO
    / ".planning/quick/260715-wq9-phase22-v6-gemini-teacher-build-jsonl-de"
    / "overnight-artifacts/terra_collect.jsonl"
)

_RTMW_MARKER = "RTMW_Data: "


# ---------------------------------------------------------------------------
# S3 helpers (boto3 — AWS_PROFILE=sunity-motion 환경 가정).
# ---------------------------------------------------------------------------
def _s3_client():
    import boto3

    return boto3.client("s3", region_name=_REGION)


def download_current_jsonl(dest_dir: Path) -> dict:
    """현재 S3 jsonl/ 의 train/val/_meta 다운로드 → 로컬 경로 dict."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    s3 = _s3_client()
    paths = {}
    for name in ("train.jsonl", "val.jsonl", "_meta.json"):
        local = dest_dir / name
        s3.download_file(_BUCKET, _CANONICAL_PREFIX + name, str(local))
        paths[name] = local
    return paths


# ---------------------------------------------------------------------------
# 복원 — distill 행 → accepted 레코드.
# ---------------------------------------------------------------------------
def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).open(encoding="utf-8") if line.strip()]


def _s3_key_from_sample(sample: dict) -> str | None:
    try:
        content = sample["messages"][1]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, list):
        return None
    for c in content:
        if isinstance(c, dict) and c.get("type") == "video":
            uri = c.get("video") or ""
            return uri[len(_S3_URI_PREFIX):] if uri.startswith(_S3_URI_PREFIX) else uri
    return None


def _user_text(sample: dict) -> str | None:
    try:
        content = sample["messages"][1]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(content, list):
        return None
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            return c.get("text")
    return None


def _parse_coords_by_frame(user_text: str) -> list[dict]:
    """user 텍스트의 'RTMW_Data: [...]' 를 raw_decode 로 파싱(뒤 _TASK_INSTRUCTION 무시)."""
    if not user_text:
        return []
    idx = user_text.find(_RTMW_MARKER)
    if idx == -1:
        return []
    start = idx + len(_RTMW_MARKER)
    decoder = json.JSONDecoder()
    try:
        frames, _end = decoder.raw_decode(user_text, start)
    except (json.JSONDecodeError, ValueError):
        return []
    return frames if isinstance(frames, list) else []


def _joint_keys_from_system(sample: dict) -> list[str]:
    """system 메시지 bind_key_prompt 의 대괄호 리스트에서 joint_keys 파싱."""
    try:
        content = sample["messages"][0]["content"]
    except (KeyError, IndexError, TypeError):
        return []
    if not isinstance(content, str):
        return []
    lb = content.find("[")
    rb = content.find("]", lb + 1)
    if lb == -1 or rb == -1:
        return []
    inner = content[lb + 1:rb]
    return [tok.strip() for tok in inner.split(",") if tok.strip()]


def _joint_keys_from_frames(frames: list[dict]) -> list[str]:
    if not frames or not isinstance(frames[0], dict):
        return []
    return sorted(k for k in frames[0] if k != "frame")


def reconstruct_accepted(distill_samples: list[dict]) -> tuple[list[dict], int]:
    """distill 행 → accepted 레코드 리스트. 반환 (records, normalize_parse_failures).

    normalize_parse_failures = assistant JSON 파싱 실패 건수(게이트 5, 기대 0).
    """
    records: list[dict] = []
    parse_failures = 0
    for s in distill_samples:
        report = build_jsonl.assistant_report(s)  # </thought> 뒤 JSON 파싱(공유 로직).
        if report is None:
            parse_failures += 1
            log.warning("assistant report 파싱 실패 — vh=%s", s.get("_video_hash"))
            continue
        content = s["messages"][2]["content"]
        thought = None
        if isinstance(content, str) and "<thought>" in content:
            a = content.find("<thought>") + len("<thought>")
            b = content.find("</thought>")
            if b != -1:
                thought = content[a:b].strip()
        user_text = _user_text(s)
        coords_by_frame = _parse_coords_by_frame(user_text or "")
        joint_keys = _joint_keys_from_system(s) or _joint_keys_from_frames(coords_by_frame)
        records.append({
            "video_hash": s.get("_video_hash"),
            "s3_key": _s3_key_from_sample(s),
            "motion": s.get("_motion"),
            "thought": thought,
            "report": report,
            "joint_keys": joint_keys,
            "coords_by_frame": coords_by_frame,
        })
    return records, parse_failures


# ---------------------------------------------------------------------------
# terra13 union.
# ---------------------------------------------------------------------------
def load_terra_union_candidates() -> list[dict]:
    """terra_collect 에서 terra_fault_count > gemini_fault_count 인 행(비교로 재도출)."""
    rows = _load_jsonl(_TERRA_PATH)
    return [
        r for r in rows
        if int(r.get("terra_fault_count", 0)) > int(r.get("gemini_fault_count", 0))
    ]


def _fault_dedup_key(fault: dict) -> tuple[str, str]:
    return (
        str(fault.get("fault_category") or "").strip().lower(),
        str(fault.get("body_part") or "").strip().lower(),
    )


def union_terra_faults(records: list[dict], terra_candidates: list[dict]) -> dict:
    """각 candidate video_hash 의 report.faults 에 terra faults 를 union.

    계약 안전장치: gemini faults 를 고정한 채 terra fault 를 하나씩 추가하며 매번
    schema.normalize_report → build_jsonl._faults_satisfy_contract 검사. 통과분만 채택
    (개별 검증이라 중간 위반 fault 만 드롭, 뒤 유효 fault 보존). dedup: 동일
    (fault_category, body_part) 는 gemini 우선으로 append 금지.

    반환: 검증표 dict {video_hash: {motion, before, after, delta, recovered,
    terra_offered, terra_dropped}}.
    """
    by_hash: dict[str, dict] = {}
    for rec in records:
        vh = rec.get("video_hash")
        if vh:
            by_hash.setdefault(vh, rec)  # 첫 매칭 사용(동일 vh 중복 없음 가정).

    table: dict[str, dict] = {}
    for cand in terra_candidates:
        vh = cand.get("_video_hash")
        rec = by_hash.get(vh)
        if rec is None:
            log.warning("terra candidate 미매칭(distill 부재) — vh=%s", vh)
            table[vh] = {
                "motion": cand.get("_motion"),
                "before": None, "after": None, "delta": None,
                "recovered": False, "terra_offered": None, "terra_dropped": None,
                "note": "distill 부재 — union skip",
            }
            continue

        gemini_faults = list((rec.get("report") or {}).get("faults") or [])
        before = len(gemini_faults)
        existing_keys = {_fault_dedup_key(f) for f in gemini_faults}
        terra_faults = list((cand.get("terra_report") or {}).get("faults") or [])
        terra_offered = len(terra_faults)

        kept_terra: list[dict] = []
        dropped = 0
        for tf in terra_faults:
            if not isinstance(tf, dict):
                dropped += 1
                log.info("terra fault 드롭(비-dict) vh=%s", vh)
                continue
            key = _fault_dedup_key(tf)
            if key in existing_keys:
                dropped += 1
                log.info(
                    "terra fault dedup 드롭 vh=%s (%s / %s)",
                    vh, tf.get("fault_category"), tf.get("body_part"),
                )
                continue
            # 계약 안전장치 — gemini + 기채택 terra + 이 terra 로 test 리포트 구성.
            test_report = dict(rec.get("report") or {})
            test_report["faults"] = gemini_faults + kept_terra + [tf]
            norm = schema.normalize_report(test_report)
            if build_jsonl._faults_satisfy_contract(norm):
                kept_terra.append(tf)
                existing_keys.add(key)
            else:
                dropped += 1
                log.info(
                    "terra fault 계약위반 드롭 vh=%s (%s / %s)",
                    vh, tf.get("fault_category"), tf.get("body_part"),
                )

        rec["report"]["faults"] = gemini_faults + kept_terra
        after = len(rec["report"]["faults"])
        table[vh] = {
            "motion": cand.get("_motion"),
            "before": before,
            "after": after,
            "delta": after - before,
            "recovered": before == 0 and after > 0,
            "terra_offered": terra_offered,
            "terra_dropped": dropped,
        }
        log.info(
            "terra union vh=%s motion=%s before=%d after=%d delta=%d (offered=%d dropped=%d)",
            vh, cand.get("_motion"), before, after, after - before, terra_offered, dropped,
        )
    return table


# ---------------------------------------------------------------------------
# accepted 물리 기록.
# ---------------------------------------------------------------------------
def write_accepted(records: list[dict], accepted_dir: Path) -> int:
    """full_batch.save_accepted 규약으로 accepted/<slug>.json 기록. 반환 기록 건수."""
    accepted_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for rec in records:
        s3_key = rec.get("s3_key")
        if not s3_key:
            log.warning("s3_key 부재 accepted 레코드 skip — vh=%s", rec.get("video_hash"))
            continue
        full_batch.save_accepted(str(accepted_dir), s3_key, rec)
        n += 1
    return n


# ---------------------------------------------------------------------------
# 검증 게이트 산출.
# ---------------------------------------------------------------------------
def compute_gates(out_dir: Path, meta: dict, terra_table: dict, parse_failures: int) -> dict:
    """산출 train/val/_meta 로 검증 지표 계산."""
    train = _load_jsonl(out_dir / "train.jsonl")
    val_path = out_dir / "val.jsonl"
    val = _load_jsonl(val_path) if val_path.exists() else []

    train_hashes = {s.get("_video_hash") for s in train if s.get("_video_hash")}
    val_hashes = {s.get("_video_hash") for s in val if s.get("_video_hash")}
    leakage = sorted(train_hashes & val_hashes)

    tc = meta.get("track_counts", {})
    recoveries = sum(1 for v in terra_table.values() if v.get("recovered"))
    delta_all_positive = all(
        (v.get("delta") or 0) > 0 for v in terra_table.values() if v.get("before") is not None
    )

    return {
        "track_counts": tc,
        "perturb_zero": tc.get("perturb") == 0,
        "fault_bearing_count": meta.get("fault_bearing_count"),
        "fault_free_count": meta.get("fault_free_count"),
        "fault_free_cap_ratio": meta.get("fault_free_cap_ratio"),
        "terra_recoveries": recoveries,
        "terra_delta_all_positive": delta_all_positive,
        "leakage_hashes": leakage,
        "leakage_zero": len(leakage) == 0,
        "normalize_parse_failures": parse_failures,
        "normalize_pass_100": parse_failures == 0,
        "train_rows": len(train),
        "val_rows": len(val),
        "distill_rows": tc.get("distill"),
        "text_rows": tc.get("text"),
    }


# ---------------------------------------------------------------------------
# S3 백업 + 교체 (전 게이트 PASS 후에만 — --upload).
# ---------------------------------------------------------------------------
def _gates_pass(gates: dict, terra_table: dict) -> tuple[bool, list[str]]:
    fails = []
    if not gates["perturb_zero"]:
        fails.append(f"perturb != 0 ({gates['track_counts'].get('perturb')})")
    if not gates["leakage_zero"]:
        fails.append(f"leakage != 0 ({gates['leakage_hashes']})")
    if not gates["normalize_pass_100"]:
        fails.append(f"normalize parse failures {gates['normalize_parse_failures']}")
    if gates["fault_bearing_count"] is None or gates["fault_free_count"] is None:
        fails.append("fault_bearing/free count 미방출")
    present = [v for v in terra_table.values() if v.get("before") is not None]
    if len(present) != 13:
        fails.append(f"terra present {len(present)} != 13")
    # delta==0 은 offered terra 가 전량 정당 드롭(dedup/계약위반)된 경우만 허용 —
    # 조립 버그로 인한 무음 손실을 차단한다. General-pole-movements 처럼 유일한 terra
    # fault 가 계약 부적합(각도·편차 전무)이면 delta==0 이 정상(belle 2026-07-16 수용).
    for vh, v in terra_table.items():
        if v.get("before") is None:
            continue
        if (v.get("delta") or 0) > 0:
            continue
        offered = v.get("terra_offered") or 0
        dropped = v.get("terra_dropped") or 0
        if offered != dropped:
            fails.append(
                f"terra delta==0 미설명 vh={vh} (offered={offered} dropped={dropped})"
            )
    # recoveries(gemini=0→>0 승격) 상한은 데이터·계약에 종속 — 계약상 상한 7 을 하한으로
    # 단언(belle 수용 상태 고정, 회귀 시 <7 이면 차단). "8" 은 계약필터 미계산 추정치였음.
    if gates["terra_recoveries"] < 7:
        fails.append(f"terra recoveries {gates['terra_recoveries']} < 7")
    return (len(fails) == 0, fails)


def backup_and_upload(out_dir: Path) -> dict:
    """전 게이트 PASS 후: jsonl/ → jsonl_v5_backup/ 백업(검증) → v6 업로드 → 왕복 검증."""
    s3 = _s3_client()

    # 1. 백업 — 현 canonical 3파일 copy_object.
    backed_up = []
    for name in ("train.jsonl", "val.jsonl", "_meta.json"):
        src = _CANONICAL_PREFIX + name
        dst = _BACKUP_PREFIX + name
        s3.copy_object(
            Bucket=_BUCKET,
            CopySource={"Bucket": _BUCKET, "Key": src},
            Key=dst,
        )
        backed_up.append(dst)

    # 2. 백업 존재 검증(교체 전 필수).
    resp = s3.list_objects_v2(Bucket=_BUCKET, Prefix=_BACKUP_PREFIX)
    backup_keys = {o["Key"] for o in resp.get("Contents", [])}
    missing = [k for k in backed_up if k not in backup_keys]
    if missing:
        raise RuntimeError(f"백업 검증 실패 — 누락: {missing}. 교체 중단.")
    log.info("백업 검증 OK — %s", sorted(backup_keys))

    # 3. v6 업로드(백업 확인 후에만).
    uploaded = []
    for name in ("train.jsonl", "val.jsonl", "_meta.json"):
        local = out_dir / name
        key = _CANONICAL_PREFIX + name
        s3.upload_file(str(local), _BUCKET, key)
        uploaded.append(key)

    # 4. 왕복 검증 — _meta.json 재다운로드.
    with tempfile.TemporaryDirectory() as td:
        rt = Path(td) / "_meta.json"
        s3.download_file(_BUCKET, _CANONICAL_PREFIX + "_meta.json", str(rt))
        roundtrip_meta = json.loads(rt.read_text(encoding="utf-8"))

    return {
        "backed_up": backed_up,
        "uploaded": uploaded,
        "roundtrip_meta": roundtrip_meta,
    }


# ---------------------------------------------------------------------------
# 메인.
# ---------------------------------------------------------------------------
def run(work_dir: Path, do_upload: bool) -> dict:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    # 1. 현재 S3 jsonl 다운로드.
    cur_dir = work_dir / "current_jsonl"
    download_current_jsonl(cur_dir)
    train = _load_jsonl(cur_dir / "train.jsonl")
    val_path = cur_dir / "val.jsonl"
    val = _load_jsonl(val_path) if val_path.exists() else []
    distill_samples = [s for s in train + val if s.get("_track") == "distill"]
    log.info("현재 distill 행 복원 대상: %d", len(distill_samples))

    # 2. 복원.
    records, parse_failures = reconstruct_accepted(distill_samples)
    log.info("복원 accepted 레코드: %d (parse 실패 %d)", len(records), parse_failures)

    # 3. terra union.
    terra_candidates = load_terra_union_candidates()
    log.info("terra union candidates: %d", len(terra_candidates))
    terra_table = union_terra_faults(records, terra_candidates)

    # 4. accepted 물리 기록.
    accepted_dir = work_dir / "accepted"
    if accepted_dir.exists():
        shutil.rmtree(accepted_dir)
    n_written = write_accepted(records, accepted_dir)
    log.info("accepted 기록: %d", n_written)

    # 5. assemble (무변형 호출) — perturb_loader 미주입 → include_perturb=False(C1).
    out_dir = work_dir / "jsonl"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    result = full_batch.assemble_jsonl(
        manifest,
        str(accepted_dir),
        str(out_dir),
        validation_owner="explicit_val_jsonl",
        uploader=None,  # S3 업로드는 이 스크립트가 게이트 후 직접 수행.
    )
    meta = result["meta"]

    # 6. 검증 게이트.
    gates = compute_gates(out_dir, meta, terra_table, parse_failures)
    passed, fails = _gates_pass(gates, terra_table)

    upload_result = None
    if do_upload:
        if not passed:
            raise SystemExit(
                "게이트 미통과 — S3 교체 차단. 실패: " + "; ".join(fails)
            )
        upload_result = backup_and_upload(out_dir)

    return {
        "out_dir": str(out_dir),
        "meta": meta,
        "gates": gates,
        "gates_passed": passed,
        "gate_failures": fails,
        "terra_table": terra_table,
        "upload_result": upload_result,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="phase22 v6 assemble + terra13 union")
    ap.add_argument(
        "--emit", action="store_true",
        help="로컬 v6 산출 확정(기본 dry-run 도 로컬 산출은 동일; S3 무접촉).",
    )
    ap.add_argument(
        "--upload", action="store_true",
        help="전 게이트 PASS 후 S3 백업(jsonl_v5_backup/)→canonical 교체→왕복 검증.",
    )
    ap.add_argument(
        "--work-dir", default=None,
        help="작업 디렉토리(기본 tmp). 재사용 시 accepted/jsonl 재생성.",
    )
    args = ap.parse_args()

    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        work_dir = Path(tempfile.mkdtemp(prefix="assemble_v6_"))
    log.info("work_dir=%s emit=%s upload=%s", work_dir, args.emit, args.upload)

    out = run(work_dir, do_upload=args.upload)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
