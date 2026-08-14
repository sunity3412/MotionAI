"""phase22 v6 재라벨 러너 — 새 thorough-Gemini 프롬프트로 distill 영상 재라벨.

기존 train_v5.jsonl 의 distill 행에서 {s3 영상경로, RTMW 좌표(재사용), motion} 를 뽑아
gemini_teacher.distill_video(새 프롬프트 반영됨)로 재호출 → 기존 vs 새 fault 개수 비교.
RTMW 재추출 0(좌표는 안 변함). 좌표는 user 턴 RTMW_Data 에서 역파싱.

env: AWS_PROFILE=sunity-motion (S3+SSM), Gemini 키 = SSM /sunity/motion/gemini-api-key.
사용: relabel_venv/bin/python relabel_faults.py <train.jsonl> <out.jsonl> [max_rows]
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.getcwd(), "backend", "training"))
from distill import gemini_teacher as gt  # noqa: E402


def parse_row(row):
    """distill 행 → (s3_uri, coords_by_frame, motion, old_report) 또는 None."""
    msgs = row.get("messages", [])
    user = next((m for m in msgs if m.get("role") == "user"), None)
    asst = next((m for m in msgs if m.get("role") == "assistant"), None)
    if not user or not asst:
        return None
    s3_uri = None
    coords = None
    for part in (user.get("content") or []):
        if not isinstance(part, dict):
            continue
        if part.get("type") == "video":
            s3_uri = part.get("video")
        elif part.get("type") == "text":
            t = part.get("text", "")
            if t.startswith("RTMW_Data:"):
                # 좌표 배열 뒤에 _TASK_INSTRUCTION 텍스트가 붙어있으므로 raw_decode 로
                # 앞의 JSON 배열만 추출(trailing 텍스트 무시).
                coords, _ = json.JSONDecoder().raw_decode(t[len("RTMW_Data:"):].strip())
    if not s3_uri or coords is None:
        return None
    try:
        old_report = json.loads(asst.get("content", ""))
    except Exception:
        old_report = {}
    return s3_uri, coords, row.get("_motion"), old_report


def s3_download(uri, dest):
    import boto3

    assert uri.startswith("s3://")
    bucket, key = uri[len("s3://"):].split("/", 1)
    boto3.client("s3", region_name="ap-northeast-2").download_file(bucket, key, dest)


def main():
    train_path = sys.argv[1]
    out_path = sys.argv[2]
    max_rows = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9

    rows = [json.loads(l) for l in open(train_path)]
    distill = [r for r in rows if r.get("_track") == "distill"]
    print(f"[setup] 총 {len(rows)}행 중 distill={len(distill)} (재라벨 대상), max_rows={max_rows}",
          flush=True)

    client = gt._ensure_client()
    joint_keys = gt.DEFAULT_TASK_JOINTS
    stats = {"accepted": 0, "rejected": 0, "denser": 0, "same": 0, "sparser": 0, "error": 0}
    out = open(out_path, "w", encoding="utf-8")
    processed = 0

    for row in distill:
        if processed >= max_rows:
            break
        parsed_row = parse_row(row)
        if not parsed_row:
            continue
        s3_uri, coords, motion, old_report = parsed_row
        old_nf = len(old_report.get("faults") or [])
        vh = row.get("_video_hash")
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        try:
            s3_download(s3_uri, tmp.name)
            result = gt.distill_video(client, tmp.name, coords, joint_keys, motion=motion)
            report = (result or {}).get("report")
            if not report:
                stats["error"] += 1
                print(f"  [err] {s3_uri} parse실패", flush=True)
                continue
            judge = gt.judge_report(client, report, motion=motion)
            accepted, reason = gt.evaluate_filters(result, judge)
            new_nf = len(report.get("faults") or [])
            delta = "==" if new_nf == old_nf else ("↑" if new_nf > old_nf else "↓")
            if new_nf > old_nf:
                stats["denser"] += 1
            elif new_nf == old_nf:
                stats["same"] += 1
            else:
                stats["sparser"] += 1
            print(f"  {s3_uri.split('/')[-2]}/{s3_uri.split('/')[-1]} "
                  f"motion={motion} fault {old_nf}->{new_nf} {delta} judge={judge} {reason}",
                  flush=True)
            if accepted:
                stats["accepted"] += 1
                out.write(json.dumps({
                    "_video_hash": vh, "_track": "distill", "_motion": motion,
                    "s3_uri": s3_uri, "old_fault_count": old_nf, "new_fault_count": new_nf,
                    "thought": result.get("thought"), "report": report,
                }, ensure_ascii=False) + "\n")
                out.flush()
            else:
                stats["rejected"] += 1
        except Exception as exc:
            stats["error"] += 1
            if gt._is_quota_error(exc):
                print(f"  [ABORT] quota 429 at {s3_uri}: {str(exc)[:120]}", flush=True)
                break
            print(f"  [err] {s3_uri}: {str(exc)[:140]}", flush=True)
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
            processed += 1
        time.sleep(0.5)

    out.close()
    tot_old = None
    print(f"\n[done] processed={processed} accepted={stats['accepted']} "
          f"rejected={stats['rejected']} error={stats['error']}", flush=True)
    print(f"[density] 더촘촘={stats['denser']} 동일={stats['same']} 성김={stats['sparser']}",
          flush=True)


if __name__ == "__main__":
    main()
