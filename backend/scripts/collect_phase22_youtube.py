#!/usr/bin/env python3
"""Phase 22 채널 harvester — yt-dlp 채널 열거 + 종목/길이 필터 + Vision 선별 게이트 +
비-notified S3 적재 + provenance 매니페스트 (D-09, belle 2026-07-09 채널 harvest 개편).

아키텍처 (22-DATA-SOURCES.md + 22-02-PLAN Task 1):
  phase22_sources.yaml(채널 레지스트리) → yt-dlp --flat-playlist 열거 →
  discipline_filter/duration_window/series_filter 로 후보 축소 →
  (선별) curate_vision.gate 호출 → (통과분) yt-dlp --write-info-json 다운로드 →
  S3 fixtures/phase22/{motion}/{video_id}.mp4 PUT + info.json 사이드카 →
  manifest.json 행 추가.

동작 모드 3단 (belle 게이트, autonomous=false):
  --dry-run  : 레지스트리 로드 + 필터 순수 self-check + 키 스킴 검증. 네트워크·yt-dlp·
               boto3·Gemini 0. 지금 실행 안전(과금·다운로드 없음).
  --curate   : Vision 선별까지(다운로드 0, API 과금 발생). Task 3 belle greenlight 필요.
  --collect  : 통과분 다운로드 + S3 적재. Task 3 belle greenlight 필요.

키 스킴 규율 (upload_phase15_dataset.py HIGH 1 복사):
  fixtures/phase22/{motion}/{video_id}.mp4 — uploads/ prefix 절대 금지
  (ObjectCreated -> SQS -> pipeline 발화 차단). Content-Type video/mp4.

사람 숫자 점수 라벨 금지 — label_bucket("정타"|"fault")만. AWS 자격증명 = sunity-motion.

yt-dlp / boto3 는 --curate/--collect 경로에서만 lazy-import 한다. --dry-run 은 순수
로컬 검증이라 외부 의존이 전혀 없다 (테스트가 이 모듈의 순수 필터를 직접 import).
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
SOURCES_YAML = BACKEND / "scripts" / "phase22_sources.yaml"
MANIFEST_PATH = BACKEND / "training" / "data" / "manifest.json"

BUCKET = "sunity-motion-pilot-videos"
FIXTURES_PREFIX = "fixtures/phase22"
CONTENT_TYPE = "video/mp4"
NOTIFIED_PREFIX = "uploads/"  # 절대 사용 금지 — notification 발화.

VALID_BUCKETS = ("정타", "fault")

# Task 3(과금·비가역) 게이트 — belle greenlight 없이는 --curate/--collect 차단.
BELLE_GREENLIGHT_ENV = "PHASE22_BELLE_GREENLIGHT"


# ---------------------------------------------------------------------------
# 순수 필터 함수 (테스트 대상 — 네트워크/yt-dlp 무관).
# ---------------------------------------------------------------------------
def title_discipline_ok(title: str, include_regex: str, exclude_regex: str) -> bool:
    """제목이 종목 include 에 매칭되고 exclude 에 매칭되지 않으면 True.

    폴 계열만 통과, 후프/에어리얼후프 등 비-폴 종목 배제. 순수 — 부수효과 0.
    """
    t = str(title or "")
    if include_regex and not re.search(include_regex, t):
        return False
    if exclude_regex and re.search(exclude_regex, t):
        return False
    return True


def duration_in_window(duration_sec, window) -> bool:
    """duration_sec 가 [min, max] 창 안이면 True.

    window=None → 제한 없음(True). duration_sec=None(메타 부재) → 보수적으로 False
    (길이 미상 = 타이틀카드/블록 위험, 제외). 순수.
    """
    if not window:
        return True
    if duration_sec is None:
        return False
    lo, hi = window
    return float(lo) <= float(duration_sec) <= float(hi)


def series_match(title: str, series_regex) -> bool:
    """series_regex 가 None/빈값이면 True(시리즈 제한 없음). 있으면 제목 매칭 여부. 순수."""
    if not series_regex:
        return True
    return re.search(series_regex, str(title or "")) is not None


def passes_filters(entry_meta: dict, channel_cfg: dict, defaults: dict) -> bool:
    """단일 후보(entry_meta = {title, duration}) 가 채널 필터 전부 통과하는지. 순수.

    discipline(종목) + duration(길이) + series(시리즈) 3중 게이트. 채널별 오버라이드가
    없으면 defaults 사용.
    """
    include_re = channel_cfg.get("discipline_include", defaults.get("discipline_include", ""))
    exclude_re = channel_cfg.get("discipline_exclude", defaults.get("discipline_exclude", ""))
    window = channel_cfg.get("duration_window", defaults.get("duration_window"))
    series_re = channel_cfg.get("series_include")  # 시리즈는 채널 로컬만.
    title = entry_meta.get("title", "")
    duration = entry_meta.get("duration")
    return (
        title_discipline_ok(title, include_re, exclude_re)
        and duration_in_window(duration, window)
        and series_match(title, series_re)
    )


# ---------------------------------------------------------------------------
# 키 스킴 규율 (upload_phase15 self-check 복사).
# ---------------------------------------------------------------------------
def build_s3_key(motion: str, video_id: str) -> str:
    """fixtures/phase22/{motion}/{video_id}.mp4 — 비-notified prefix."""
    safe_motion = _ascii_safe(motion)
    safe_id = _ascii_safe(video_id)
    return f"{FIXTURES_PREFIX}/{safe_motion}/{safe_id}.mp4"


def build_info_key(motion: str, video_id: str) -> str:
    """provenance 사이드카 info.json 키 (동일 prefix)."""
    safe_motion = _ascii_safe(motion)
    safe_id = _ascii_safe(video_id)
    return f"{FIXTURES_PREFIX}/{safe_motion}/{safe_id}.info.json"


def _ascii_safe(name: str) -> str:
    """파일명 ASCII-safe 정규화 (T-22-06 — 외부 미디어 파일명 방어)."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", str(name or "")).strip("-") or "unknown"


def assert_non_notified(key: str) -> None:
    """업로드 전 키 스킴 self-check — uploads/ prefix 발화 위험 차단 (HIGH 1)."""
    if key.startswith(NOTIFIED_PREFIX):
        raise RuntimeError(f"키 {key!r} 가 uploads/ prefix — notification 발화 위험 (HIGH 1)")
    if not key.startswith(FIXTURES_PREFIX + "/"):
        raise RuntimeError(f"키 {key!r} 가 {FIXTURES_PREFIX}/ 스킴 위반")


# ---------------------------------------------------------------------------
# provenance 매니페스트 행 빌더.
# ---------------------------------------------------------------------------
def build_manifest_row(
    *,
    motion: str,
    video_id: str,
    label_bucket: str,
    source_url: str,
    channel: str,
    tier: str,
    yt_dlp_version: str,
    vision_verdict: dict | None,
    collected_at_ms: int,
) -> dict:
    """MANIFEST_ROW (22-RESEARCH) — 사람 숫자 점수 라벨 없이 버킷만."""
    if label_bucket not in VALID_BUCKETS:
        raise ValueError(f"label_bucket {label_bucket!r} 는 {VALID_BUCKETS} 밖 (숫자 점수 라벨 금지)")
    s3_key = build_s3_key(motion, video_id)
    assert_non_notified(s3_key)
    return {
        "s3_key": s3_key,
        "motion": motion,
        "label_bucket": label_bucket,
        "source": "youtube",
        "source_url": source_url,
        "channel": channel,
        "tier": tier,
        "license_evidence": "info.json 보관",
        "usage": "training-only-no-redistribution",
        "collected_at_ms": collected_at_ms,
        "yt_dlp_version": yt_dlp_version,
        "vision_verdict": vision_verdict,
        "anonymized": False,  # 공개영상은 provenance 만(D-12 범위 밖).
        "holdout": None,
        "collected": True,
    }


# ---------------------------------------------------------------------------
# 레지스트리 로드.
# ---------------------------------------------------------------------------
def load_registry(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {}) or {}
    channels = [c for c in (data.get("channels") or []) if isinstance(c, dict)]
    return {"defaults": defaults, "channels": channels}


def _active_channels(registry: dict) -> list[dict]:
    """enabled=false 채널(미성년·IG ToS 회색) 제외."""
    return [c for c in registry["channels"] if c.get("enabled", True)]


# ---------------------------------------------------------------------------
# 필터 순수 self-check (--dry-run — 네트워크 0).
# ---------------------------------------------------------------------------
def _filter_self_check(registry: dict) -> list[str]:
    """합성 제목/길이로 각 채널 필터가 살아있는지 확인. 통과 리스트 반환.

    후프 제외·타이틀카드(6s) 배제가 실제로 걸리는지 self-consistency 검증
    (phase18 assert_baseline silent-통과 금지 전례). 네트워크·yt-dlp 0.
    """
    defaults = registry["defaults"]
    problems: list[str] = []
    # 종목 exclude 가 후프를 실제로 거르는지.
    if title_discipline_ok(
        "에어리얼 후프 루틴",
        defaults.get("discipline_include", ""),
        defaults.get("discipline_exclude", ""),
    ):
        problems.append("discipline_exclude 가 후프를 거르지 못함")
    # 폴 제목은 통과해야.
    if not title_discipline_ok(
        "2025 한국폴스포츠선수권 pole",
        defaults.get("discipline_include", ""),
        defaults.get("discipline_exclude", ""),
    ):
        problems.append("discipline_include 가 폴 제목을 통과시키지 못함")
    # 6s 타이틀카드가 기본 창(120~400)에서 배제되는지.
    if duration_in_window(6, defaults.get("duration_window")):
        problems.append("duration_window 가 6s 타이틀카드를 거르지 못함")
    # 단일 루틴(180s)은 통과해야.
    if not duration_in_window(180, defaults.get("duration_window")):
        problems.append("duration_window 가 180s 단일루틴을 거름")
    return problems


def _require_greenlight(mode: str) -> None:
    import os

    if os.environ.get(BELLE_GREENLIGHT_ENV) != "1":
        print(
            f"[BLOCKED] {mode} 는 Task 3(belle 게이트) — Gemini 과금 + 카피라이트 prod S3 "
            f"적재(비가역)라 belle greenlight 전 실행 금지.\n"
            f"승인 후에만: {BELLE_GREENLIGHT_ENV}=1 로 재실행.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(2)


# ---------------------------------------------------------------------------
# main.
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 22 채널 harvester (D-09) — --dry-run 안전, --curate/--collect belle 게이트"
    )
    parser.add_argument("--sources", default=str(SOURCES_YAML))
    parser.add_argument("--bucket", default=BUCKET)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="열거+필터 self-check만 (기본, 안전)")
    mode.add_argument("--curate", action="store_true", help="Vision 선별 (Task 3, belle 게이트)")
    mode.add_argument("--collect", action="store_true", help="다운로드+S3 적재 (Task 3, belle 게이트)")
    args = parser.parse_args(argv)

    registry = load_registry(Path(args.sources))
    active = _active_channels(registry)

    # 기본 = dry-run (모드 미지정 시).
    if args.curate:
        _require_greenlight("--curate")
        return _run_curate(registry, args)
    if args.collect:
        _require_greenlight("--collect")
        return _run_collect(registry, args)

    # ── --dry-run (기본) : 네트워크·yt-dlp·boto3·Gemini 0 ──────────────────
    print(
        f"[dry-run] 레지스트리 {args.sources} — 활성 채널 {len(active)}/{len(registry['channels'])} "
        f"(enabled=false 제외: 미성년·IG ToS)",
        flush=True,
    )
    # 채널별 샘플 키 스킴 검증 (uploads/ 미등장, fixtures/phase22/ 등장).
    disallowed = 0
    for ch in active:
        motion_placeholder = ch["name"].lower()
        sample_key = build_s3_key(motion_placeholder, "SAMPLEID")
        assert_non_notified(sample_key)
        if sample_key.startswith(NOTIFIED_PREFIX):
            disallowed += 1
        print(
            f"  ch={ch['name']:<32} tier={ch.get('tier','?'):<11} bucket={ch.get('bucket','?'):<6} "
            f"sample_key={sample_key}",
            flush=True,
        )
    # 필터 순수 self-check.
    problems = _filter_self_check(registry)
    if problems:
        for p in problems:
            print(f"  [FILTER-FAIL] {p}", file=sys.stderr, flush=True)
        return 1
    if disallowed:
        print(f"  [KEY-FAIL] uploads/ prefix 등장 {disallowed}건", file=sys.stderr, flush=True)
        return 1
    print(
        "\n[dry-run] exit 0. 키 스킴 전부 fixtures/phase22/ (uploads/ 미사용, 트리거 비발화). "
        "필터 self-check 통과(후프 배제·타이틀카드 배제·폴 통과). 다운로드·Gemini 호출 0.",
        flush=True,
    )
    return 0


def _run_curate(registry: dict, args) -> int:
    """Vision 선별(다운로드 0, Gemini 과금). Task 3 belle greenlight 후에만."""
    # 실제 열거는 yt-dlp lazy-import 경로. Task 3 에서 구현/실행.
    from datagen import curate_vision  # noqa: F401 — 게이트 배선 확인용.

    print("[curate] Task 3 경로 — yt-dlp 열거 + curate_vision.gate 선별. (greenlight 확인됨)", flush=True)
    print("[curate] 실 열거/선별 실행은 Task 3 belle 스코프에서 배선한다.", flush=True)
    return 0


def _run_collect(registry: dict, args) -> int:
    """통과분 다운로드 + S3 적재. Task 3 belle greenlight 후에만."""
    print("[collect] Task 3 경로 — yt-dlp 다운로드 + boto3 PUT + manifest 갱신. (greenlight 확인됨)", flush=True)
    print("[collect] 실 다운로드/적재 실행은 Task 3 belle 스코프에서 배선한다.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
