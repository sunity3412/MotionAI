"""Phase 22 인스타그램 릴스 수집 어댑터 (Task 3, belle greenlight 2026-07-09).

YouTube 와 흐름이 반대다: Gemini 가 IG URL 을 네이티브로 못 읽으므로
  gallery-dl 로 릴스를 임시 다운로드 → Gemini File API 로 curate(선별) → keep 만 S3 적재.
공개 릴스는 /reels/ 경로로 로그인 없이 접근된다(2026-07 확인). ToS 회색 —
usage=training-only-no-redistribution, 재배포 없음. 얼굴 픽셀 학습 불필요(포즈/모션만).

collect_phase22_youtube 의 키 스킴/매니페스트/curate 게이트를 재사용한다(계약 1벌).
belle greenlight(PHASE22_BELLE_GREENLIGHT=1) 없이는 --collect 차단.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(BACKEND / "training"))

import collect_phase22_youtube as yt  # 키 스킴·매니페스트·레지스트리 재사용.
from datagen import curate_vision

BELLE_GREENLIGHT_ENV = "PHASE22_BELLE_GREENLIGHT"


def _gallery_dl_bin() -> str:
    """venv 우선 gallery-dl 경로. 미발견 시 PATH 폴백."""
    cand = Path(sys.executable).parent / "gallery-dl"
    return str(cand) if cand.exists() else "gallery-dl"


def _ig_accounts(registry: dict, only: str | None) -> list[dict]:
    """platform=instagram 계정. IG 어댑터 실행 자체가 belle IG greenlight 이므로
    enabled=false(유튜브 curate 격리용) 여부와 무관하게 IG 트랙에서 처리한다."""
    out = [c for c in registry["channels"] if c.get("platform") == "instagram"]
    if only:
        out = [c for c in out if only.lower() in c["name"].lower()]
    return out


def _reels_url(channel_url: str) -> str:
    base = channel_url.rstrip("/")
    return base if base.endswith("/reels") else base + "/reels/"


def account_cap(account_cfg: dict, default_cap: int) -> int:
    """계정별 수집 cap 해석 (순수, quick-260714-js2).

    레지스트리 cap_per_account 가 있으면 CLI 기본값을 오버라이드 — eunji.poledancer
    상향(20→60, 본인 동의 확보 2026-07-14)처럼 계정 단위 정책을 코드 수정 없이 반영.
    """
    return int(account_cfg.get("cap_per_account", default_cap))


def _download_reels(account_url: str, cap: int, dest: Path) -> list[Path]:
    """gallery-dl 로 릴스 임시 다운로드 → mp4 경로 목록. 실패는 빈 목록."""
    cmd = [_gallery_dl_bin(), "-d", str(dest), "--range", f"1-{cap}", _reels_url(account_url)]
    try:
        subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=600)
    except Exception as exc:  # noqa: BLE001 — 로그인월/rate-limit/타임아웃은 계정 skip.
        print(f"  [IG-FAIL] {account_url}: {exc}", file=sys.stderr, flush=True)
        return []
    return sorted(p for p in dest.rglob("*.mp4") if p.is_file())


def _ig_manifest_row(*, motion, video_id, bucket, source_url, account, tier, verdict, notes):
    """IG provenance 행 — source=instagram, ToS 회색 명시. 사람 점수 라벨 없음(버킷만)."""
    if bucket not in yt.VALID_BUCKETS:
        raise ValueError(f"label_bucket {bucket!r} 는 {yt.VALID_BUCKETS} 밖 (숫자 점수 금지)")
    s3_key = yt.build_s3_key(motion, video_id)
    yt.assert_non_notified(s3_key)
    return {
        "s3_key": s3_key,
        "motion": motion,
        "label_bucket": bucket,
        "source": "instagram",
        "source_url": source_url,
        "channel": account,
        "tier": tier,
        "license_evidence": f"gallery-dl metadata + IG ToS 회색(학습전용·비재배포). {notes or ''}".strip(),
        "usage": "training-only-no-redistribution",
        "collected_at_ms": int(time.time() * 1000),
        "vision_verdict": verdict,
        "anonymized": False,  # 공개 릴스 provenance만(포즈/모션 학습, 얼굴 픽셀 불필요).
        "holdout": None,
        "collected": True,
    }


def _require_greenlight() -> None:
    if os.environ.get(BELLE_GREENLIGHT_ENV) != "1":
        print(
            f"[collect] belle greenlight 필요 — IG 다운로드는 외부·비가역. "
            f"승인 후 {BELLE_GREENLIGHT_ENV}=1 로 재실행.",
            file=sys.stderr, flush=True,
        )
        raise SystemExit(2)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 22 인스타 릴스 수집 (download→Gemini curate→keep만 S3). belle 게이트"
    )
    parser.add_argument("--sources", default=str(yt.SOURCES_YAML))
    parser.add_argument("--only", default=None, help="계정명 부분일치 (파일럿)")
    parser.add_argument("--cap-per-account", type=int, default=20, dest="cap")
    parser.add_argument("--max-candidates", type=int, default=None, dest="max_candidates")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="계정 목록 + reels URL 확인 (기본, 안전)")
    mode.add_argument("--collect", action="store_true", help="다운로드→curate→S3 (belle 게이트)")
    args = parser.parse_args(argv)

    registry = yt.load_registry(Path(args.sources))
    accounts = _ig_accounts(registry, args.only)

    if not args.collect:  # --dry-run 기본.
        print(f"[dry-run] IG 계정 {len(accounts)} (다운로드 0):", flush=True)
        for c in accounts:
            print(f"  {c['name']:<24} {_reels_url(c['channel_url'])} "
                  f"[{c.get('bucket','?')}] {c.get('notes','')[:40]}", flush=True)
        return 0

    _require_greenlight()
    gate = curate_vision.VisionGate()
    if not gate.ready:
        print("[collect] Gemini 미초기화 — GEMINI_KEY_PARAM/AWS_PROFILE 확인.", file=sys.stderr, flush=True)
        return 2
    import boto3

    s3 = boto3.client("s3")
    manifest = yt._load_manifest()
    existing = {r.get("s3_key") for r in manifest.get("rows", [])}

    downloaded = skipped = rejected = failed = 0
    for c in accounts:
        if args.max_candidates and downloaded >= args.max_candidates:
            break
        # 계정별 cap 오버라이드 + 큐레이션 프로필 (quick-260714-js2, YT 와 동일 계약).
        cap = account_cap(c, args.cap)
        profile = c.get("curation_profile", "default")
        with tempfile.TemporaryDirectory() as td:
            mp4s = _download_reels(c["channel_url"], cap, Path(td))
            for mp4 in mp4s:
                if args.max_candidates and downloaded >= args.max_candidates:
                    break
                vid = yt._ascii_safe(mp4.stem)
                verdict = gate.gate(vid, str(mp4), profile=profile)  # File API 선별(캐시).
                dec = curate_vision.decide(verdict, profile=profile)
                if dec.status != "keep":
                    rejected += 1
                    continue
                motion = yt._motion_slug(verdict, c["name"])
                s3_key = yt.build_s3_key(motion, vid)
                if s3_key in existing:
                    skipped += 1
                    continue
                try:
                    s3.upload_file(str(mp4), yt.BUCKET, s3_key,
                                   ExtraArgs={"ContentType": yt.CONTENT_TYPE})
                    row = _ig_manifest_row(
                        motion=motion, video_id=vid, bucket=dec.bucket,
                        source_url=f"https://www.instagram.com/{c['name']}/",
                        account=c["name"], tier=c.get("tier", "2_studio"),
                        verdict=verdict, notes=c.get("notes", ""),
                    )
                    manifest.setdefault("rows", []).append(row)
                    existing.add(s3_key)
                    yt.MANIFEST_PATH.write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    downloaded += 1
                    print(f"  [OK] {c['name']:<24} {vid} → {s3_key} ({dec.bucket}/{motion})", flush=True)
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(f"  [FAIL] {vid}: {exc}", file=sys.stderr, flush=True)

    print(f"\n[collect-ig] 적재 {downloaded} | reject(품질) {rejected} | skip(기존) {skipped} | "
          f"fail {failed} | manifest rows {len(manifest.get('rows', []))}.", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
