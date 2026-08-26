"""표적 fault 시연 7건 외과 수확 (2026-08-26 1회용, belle 승인 표적 수집의 마감).

배경: 표적 검색(quick 표적 수집)의 게이트에서 keep + fault_demo=true 로 판정된
영상 8건 중 7건이 프로필 틈새로 미수확됐다 —
  · fault_demo 프로필 decide 는 bucket=="fault" 를 요구하는데 Gemini 가 이들에게
    net bucket "정타"(튜토리얼 전체 성격)를 매겨 1차 기각,
  · default 프로필 재판정(캐시 키가 프로필 스코프)은 편집/자막 엄격성으로 기각.
판정 실체(keep·단일인물 폴·fault_desc 존재)는 이미 성립 — 여기서는 그 캐시된
fault_demo 프로필 verdict 를 그대로 신뢰해 다운로드·적재만 수행한다. Gemini 재호출 0.

label_bucket = "fault": fault_demo=true + fault_desc 실재가 근거 (net bucket "정타"는
"영상 전체가 튜토리얼"이라는 뜻이고, 수확 목적은 실수 시연 구간이다). 사람 점수
라벨 없음 — 버킷 라벨만 (collect_phase22_youtube 계약 그대로).

실행:
  PHASE22_BELLE_GREENLIGHT=1 AWS_PROFILE=sunity-motion \
    PYTHONPATH=backend/shared/python backend/.venv/bin/python \
    backend/scripts/collect_targeted_faultdemo_260826.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))

import boto3
from yt_dlp import YoutubeDL

import collect_phase22_youtube as cy
from datagen import curate_vision

# 첫 수확 게이트(fault_demo 프로필)에서 keep&fault_demo 로 판정된 8건 중 미수확 7건.
TARGET_IDS = [
    "wBLS84LLl4g",   # climb — 팔 힘으로만 당겨 올라가는 실수
    "S-KePmByB94",   # 피터팬 — 시선/골반/손목 실수 시연 (eval18 침묵 동작)
    "cVPWWUZsLOI",   # Elbow Grip Spin — 어깨 무너짐 실수 (eval18 침묵 동작 근연)
    "OnhM20XMk8M",   # Handspring — 허리 꺾임·오금 풀림·반동 부족
    "B5CJY-8e69M",   # 큐피드 — 발바닥 랩 없이 접촉만
    "3XxdK0g0_qQ",   # 파워 스핀 — 머리 방향·허벅지 밀착 실수 (eval18 변별 동작)
    "-u5qfytLcK0",   # Tuck Spin — 골반 미밀착·다리 풀림
]

def main() -> int:
    if os.environ.get("PHASE22_BELLE_GREENLIGHT") != "1":
        raise SystemExit(2)
    gate = curate_vision.VisionGate()  # 캐시 로드 전용 — 네트워크 0.
    manifest = cy._load_manifest()
    existing = {r.get("s3_key") for r in manifest.get("rows", [])}
    s3 = boto3.client("s3")
    ok = skip = fail = 0
    for vid in TARGET_IDS:
        verdict = gate._cache.get(curate_vision.cache_key(vid, "fault_demo"))
        if not verdict or not verdict.get("keep") or not verdict.get("fault_demo"):
            print(f"  [SKIP] {vid}: 캐시 verdict 부적합 — 수확 안 함", flush=True)
            skip += 1
            continue
        motion = cy._motion_slug(verdict, "yt_targeted_faultdemo")
        s3_key = cy.build_s3_key(motion, vid)
        if s3_key in existing:
            print(f"  [SKIP] {vid}: 이미 manifest 에 있음", flush=True)
            skip += 1
            continue
        cy.assert_non_notified(s3_key)
        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            with tempfile.TemporaryDirectory() as td:
                opts = {
                    "format": "bv*[height<=720]+ba/b[height<=720]/b",
                    "merge_output_format": "mp4",
                    "outtmpl": str(Path(td) / "%(id)s.%(ext)s"),
                    "writeinfojson": True,
                    "quiet": True, "no_warnings": True, "ignoreerrors": True,
                }
                with YoutubeDL(opts) as ydl:
                    ydl.download([url])
                files = list(Path(td).iterdir())
                mp4 = next((f for f in files if f.suffix == ".mp4"), None)
                if not mp4:
                    mp4 = next((f for f in files
                                if f.suffix.lower() in (".webm", ".mkv", ".m4v")), None)
                info = next((f for f in files if f.name.endswith(".info.json")), None)
                if not mp4:
                    print(f"  [UNAVAIL] {vid}", flush=True)
                    skip += 1
                    continue
                s3.upload_file(str(mp4), cy.BUCKET, s3_key,
                               ExtraArgs={"ContentType": cy.CONTENT_TYPE})
                if info:
                    s3.upload_file(str(info), cy.BUCKET, cy.build_info_key(motion, vid),
                                   ExtraArgs={"ContentType": "application/json"})
            row = cy.build_manifest_row(
                motion=motion, video_id=vid, label_bucket="fault",
                source_url=url, channel="yt_targeted_faultdemo", tier="2_studio",
                yt_dlp_version=cy._ytdlp_version(), vision_verdict=verdict,
                collected_at_ms=int(time.time() * 1000),
            )
            manifest.setdefault("rows", []).append(row)
            existing.add(s3_key)
            cy.MANIFEST_PATH.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            ok += 1
            print(f"  [OK] {vid} → {s3_key} (fault/{motion})", flush=True)
        except Exception as exc:  # noqa: BLE001 - 개별 실패는 집계 후 exit 1
            fail += 1
            print(f"  [FAIL] {vid}: {exc}", file=sys.stderr, flush=True)
    print(f"[targeted] ok {ok} | skip {skip} | fail {fail} | rows {len(manifest.get('rows', []))}")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
