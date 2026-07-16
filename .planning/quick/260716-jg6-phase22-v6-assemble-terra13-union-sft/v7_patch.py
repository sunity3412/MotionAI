"""phase22 v7 조립 — v6 붕괴(collapse) 대응: 볼륨 복원 + terra union (quick-260716-jg6 후속).

진단(2026-07-16): v6(C1 perturb 제거 → 168행)가 34/37 빈출력으로 붕괴 = 데이터 반토막
과소학습. v5(369행)는 안 붕괴 → 볼륨이 원인. v7 = **pre-v6 백업(jsonl_v5_backup/,
perturb 169+distill 152+text 48 = 볼륨 온전)을 base 로 복원** + terra13 union 유지.
C1/B 롤백(붕괴 유발분 제거). 이 실험이 데이터 트랙의 마지막 — 결과로 학습가능성 판정.

방식(직접 패치, 재조립 아님):
  · jsonl_v5_backup/ train+val 다운로드(perturb/split 구조 온전).
  · 13 terra video_hash 의 distill 행 assistant 리포트에 terra faults union(계약
    안전장치 + dedup, assemble_v6 로직 재사용). 나머지 행(perturb/text/미대상 distill)
    무접촉 → 볼륨·구조·time_anchors 등 원본 포맷 보존(재정규화 안 함, 시블링 정합).
  · 현재 canonical(v6)을 jsonl_v6_backup/ 로 백업 후 v7 을 canonical 에 업로드.

프로덕션 코드 0 수정. assemble_v6.py 의 terra union 함수 재사용.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
_BACKEND = _REPO / "backend"
for p in (str(_BACKEND / "training"), str(_BACKEND / "shared" / "python")):
    if p not in sys.path:
        sys.path.insert(0, p)

# assemble_v6 의 검증된 terra union 로직 재사용.
sys.path.insert(0, str(_HERE))
import assemble_v6 as a6  # noqa: E402
from datagen import build_jsonl  # noqa: E402

log = logging.getLogger("v7_patch")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

_BUCKET = "sunity-motion-pilot-videos"
_REGION = "ap-northeast-2"
_CANONICAL = "training/phase22/jsonl/"
_V5_BACKUP = "training/phase22/jsonl_v5_backup/"   # v7 base (pre-v6, 볼륨 온전)
_V6_BACKUP = "training/phase22/jsonl_v6_backup/"   # 현 canonical(v6) 백업처


def _s3():
    import boto3
    return boto3.client("s3", region_name=_REGION)


def _download(prefix: str, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    s3 = _s3()
    out = {}
    for name in ("train.jsonl", "val.jsonl", "_meta.json"):
        local = dest / name
        s3.download_file(_BUCKET, prefix + name, str(local))
        out[name] = local
    return out


def _extract_thought(content: str) -> str | None:
    if not isinstance(content, str) or "<thought>" not in content:
        return None
    a = content.find("<thought>") + len("<thought>")
    b = content.find("</thought>")
    return content[a:b].strip() if b != -1 else None


def patch_terra(rows: list[dict], terra_cands: list[dict]) -> dict:
    """rows(train 또는 val)의 distill 행에 terra union 적용. 반환 검증표(patch된 것만)."""
    # video_hash -> (row, report, thought) 인덱스 (distill 만).
    idx: dict[str, dict] = {}
    for row in rows:
        if row.get("_track") != "distill":
            continue
        vh = row.get("_video_hash")
        rep = build_jsonl.assistant_report(row)
        if not vh or rep is None:
            continue
        thought = _extract_thought(row["messages"][2]["content"])
        idx[vh] = {"row": row, "report": rep, "thought": thought}

    # assemble_v6.union_terra_faults 는 records=[{video_hash, report,...}] 를 받아
    # report.faults 를 in-place mutate + 검증표 반환. 여기 idx 값을 records 로 넘긴다.
    records = [{"video_hash": vh, "report": e["report"]} for vh, e in idx.items()]
    table = a6.union_terra_faults(records, terra_cands)

    # mutate 된 report 를 assistant 메시지에 재직렬화(원본 키 보존 — 재정규화 안 함,
    # time_anchors 등 시블링 포맷 유지. terra faults 는 이미 FAULT_ITEM_KEYS 형태).
    patched = 0
    for vh, info in table.items():
        e = idx.get(vh)
        if e is None or info.get("before") is None:
            continue
        if (info.get("delta") or 0) <= 0:
            continue  # 실제 추가 없음(전량 드롭) — 원본 유지.
        report = e["report"]  # union_terra_faults 가 이미 faults 갱신함.
        thought = e["thought"]
        thought_block = f"<thought>\n{thought}\n</thought>\n" if thought else ""
        body = json.dumps(report, ensure_ascii=False, sort_keys=True)
        e["row"]["messages"][2]["content"] = thought_block + body
        patched += 1
    return {"table": table, "patched": patched}


def run(work_dir: Path, do_upload: bool) -> dict:
    base = work_dir / "v5_backup"
    _download(_V5_BACKUP, base)
    train = a6._load_jsonl(base / "train.jsonl")
    val = a6._load_jsonl(base / "val.jsonl") if (base / "val.jsonl").exists() else []
    meta = json.loads((base / "_meta.json").read_text(encoding="utf-8"))

    terra_cands = a6.load_terra_union_candidates()
    log.info("terra candidates: %d", len(terra_cands))

    rt = patch_terra(train, terra_cands)
    rv = patch_terra(val, terra_cands)
    total_patched = rt["patched"] + rv["patched"]

    # 검증표 합치기(train+val) — 매칭된 엔트리(before!=None) 우선. val 은 대부분
    # distill 미보유라 before=None 미매칭을 반환하는데, 단순 dict 병합 시 train 의
    # 실제 delta 를 None 으로 덮어쓰는 버그가 있어 매칭 우선 병합한다.
    table: dict = {}
    for t in (rt["table"], rv["table"]):
        for vh, v in t.items():
            cur = table.get(vh)
            if cur is None or (cur.get("before") is None and v.get("before") is not None):
                table[vh] = v
    recoveries = sum(1 for v in table.values() if v.get("recovered"))
    delta_pos = sum(1 for v in table.values() if (v.get("delta") or 0) > 0)

    # 산출 로컬 기록.
    out = work_dir / "v7"
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train) + "\n", encoding="utf-8")
    (out / "val.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in val) + "\n", encoding="utf-8")
    (out / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    gates = {
        "track_counts": meta.get("track_counts"),
        "perturb_restored": (meta.get("track_counts", {}).get("perturb", 0) > 0),
        "validation_owner": meta.get("validation_owner"),
        "terra_patched_rows": total_patched,
        "terra_recoveries": recoveries,
        "terra_delta_positive": delta_pos,
        "train_rows": len(train),
        "val_rows": len(val),
    }
    passed = (
        gates["perturb_restored"]
        and gates["validation_owner"] == "explicit_val_jsonl"
        and total_patched >= 7
        and delta_pos >= 12
    )

    upload = None
    if do_upload:
        if not passed:
            raise SystemExit(f"게이트 미통과 — 업로드 차단: {gates}")
        s3 = _s3()
        # 현 canonical(v6) 백업.
        for name in ("train.jsonl", "val.jsonl", "_meta.json"):
            s3.copy_object(Bucket=_BUCKET,
                           CopySource={"Bucket": _BUCKET, "Key": _CANONICAL + name},
                           Key=_V6_BACKUP + name)
        resp = s3.list_objects_v2(Bucket=_BUCKET, Prefix=_V6_BACKUP)
        if len({o["Key"] for o in resp.get("Contents", [])}) < 3:
            raise RuntimeError("v6 백업 검증 실패 — 업로드 중단")
        # v7 업로드.
        for name in ("train.jsonl", "val.jsonl", "_meta.json"):
            s3.upload_file(str(out / name), _BUCKET, _CANONICAL + name)
        with tempfile.TemporaryDirectory() as td:
            r = Path(td) / "_meta.json"
            s3.download_file(_BUCKET, _CANONICAL + "_meta.json", str(r))
            upload = {"roundtrip_track_counts": json.loads(r.read_text())["track_counts"]}

    return {"gates": gates, "gates_passed": passed, "table": table, "upload": upload,
            "out_dir": str(out)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--work-dir", default=None)
    args = ap.parse_args()
    wd = Path(args.work_dir) if args.work_dir else Path(tempfile.mkdtemp(prefix="v7_"))
    wd.mkdir(parents=True, exist_ok=True)
    out = run(wd, args.upload)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
