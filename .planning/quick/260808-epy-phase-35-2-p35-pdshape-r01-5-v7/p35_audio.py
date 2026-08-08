"""Phase 35 미세조정 2차 — 코칭 mp3 회수(fetch) + 오버라이드 재합성(synth).

fetch: 렌더 5슬롯의 doc.json coachAudio 키를 S3 GET → {audio_root}/{motion}/{rid}.mp3.
  assert: 다운로드 수 == 그 doc 에서 **렌더될** record 수 (atVideoSec 보유 —
  align pairs / moments 주입분 포함, build_timeline enrichment 미러).
  mp3 누락 record 는 renderer 가 조용히 freeze 를 떨궈 A2 리그가 못 잡는다 —
  여기서 fail-fast (260808-epy Task 1-4).

synth: 오버라이드 테이블(rid→문장 JSON — 렌더 자막과 공용 단일 파일)을 읽어
  해당 rid 만 Polly 재합성 → 같은 이름 mp3 덮어쓰기 (다른 rid 무접촉).
  Polly 파라미터 = pipeline `_synthesize_coach_audio_items` 미러:
  VoiceId Seoyeon / Engine neural / LanguageCode ko-KR / OutputFormat mp3.

실행:
    backend/.venv/bin/python p35_audio.py fetch --data <DATA> --audio-root <SP>/p35
    backend/.venv/bin/python p35_audio.py synth --overrides elbow_text_overrides.json \
        --audio-dir <SP>/p35/elbow/audio
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import boto3

BUCKET = "sunity-motion-pilot-videos"
RENDER_SLOTS = ("elbow", "powerspin", "kipup", "pdshapefault", "peterpan")


def _session() -> boto3.session.Session:
    return boto3.session.Session(profile_name="sunity-motion")


def _renderable_rids(mdir: Path) -> set[str]:
    """렌더될 rid 집합 — render_compare_prototype.build_timeline enrichment 미러.

    align pairs 우선 → moments 주입 → 원본 atVideoSec. 셋 다 없으면 정지 안 됨
    (powerspin r01 실측: atVideoSec None + pairs 밖 → 렌더 제외가 정상).
    """
    doc = json.load(open(mdir / "doc.json"))
    align_path = mdir / "align.json"
    apairs = {}
    if align_path.exists():
        apairs = json.load(open(align_path)).get("pairs", {})
    moments_path = mdir / "moments.json"
    moments = json.load(open(moments_path)) if moments_path.exists() else {}

    rids: set[str] = set()
    for rec in doc["result"].get("deductionBreakdown", {}).get("records", []):
        rid = rec["recordId"].split(":")[0]
        if rid in apairs:
            rids.add(rid)
        elif rec.get("atVideoSec") is None and rid in moments:
            rids.add(rid)
        elif rec.get("atVideoSec") is not None:
            rids.add(rid)
    return rids


def cmd_fetch(args: argparse.Namespace) -> None:
    s3 = _session().client("s3")
    total = 0
    for m in RENDER_SLOTS:
        mdir = args.data / m
        doc = json.load(open(mdir / "doc.json"))
        items = {it["recordId"].split(":")[0]: it["key"]
                 for it in doc["result"].get("coachAudio", {}).get("items", [])}
        need = _renderable_rids(mdir)
        # 렌더될 record 인데 coachAudio 키가 없으면 즉시 실패 — 조용한 freeze 탈락 차단.
        missing = need - set(items)
        assert not missing, f"[{m}] coachAudio 키 없는 렌더 대상 record: {sorted(missing)}"
        outdir = args.audio_root / m / "audio"
        outdir.mkdir(parents=True, exist_ok=True)
        got = 0
        for rid in sorted(need):
            dst = outdir / f"{rid}.mp3"
            s3.download_file(BUCKET, items[rid], str(dst))
            got += 1
            print(f"[{m}] {rid} <- {items[rid]} ({dst.stat().st_size}B)")
        assert got == len(need), f"[{m}] 다운로드 {got} != 렌더될 record {len(need)}"
        print(f"[{m}] OK — 렌더될 record {len(need)}건 전수 회수")
        total += got
    print(f"FETCH DONE — {total} mp3")


def cmd_synth(args: argparse.Namespace) -> None:
    overrides: dict[str, str] = json.load(open(args.overrides))
    polly = _session().client("polly")
    for rid, text in overrides.items():
        resp = polly.synthesize_speech(
            Text=text,
            VoiceId="Seoyeon",
            Engine="neural",
            LanguageCode="ko-KR",
            OutputFormat="mp3",
        )
        body = resp["AudioStream"].read()
        dst = args.audio_dir / f"{rid}.mp3"
        dst.write_bytes(body)
        print(f"[synth] {rid} <- {args.overrides.name} ({len(body)}B) -> {dst}")
    print("SYNTH DONE")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--data", required=True, type=Path)
    f.add_argument("--audio-root", required=True, type=Path)
    f.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("synth")
    s.add_argument("--overrides", required=True, type=Path)
    s.add_argument("--audio-dir", required=True, type=Path)
    s.set_defaults(fn=cmd_synth)
    args = ap.parse_args()
    try:
        args.fn(args)
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
