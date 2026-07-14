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
    parser.add_argument("--only", default=None, help="채널명 부분일치 필터 (파일럿용)")
    parser.add_argument("--limit-per-channel", type=int, default=None, dest="limit_per_channel",
                        help="채널당 후보 상한 (미지정 시 per_channel_cap)")
    parser.add_argument("--max-candidates", type=int, default=None, dest="max_candidates",
                        help="전체 gate 호출 상한 (과금 안전장치, 파일럿용)")
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


def build_enumeration_url(channel_cfg: dict, limit: int | None) -> str:
    """열거 URL 순수 빌더 (yt-dlp 미호출 — 테스트 대상, quick-260714-js2).

    3분기:
      · channel_url 부재 + search 존재 → ytsearch{limit}:{search} 스킴
        (fault 타겟 검색쿼리 엔트리 — 채널이 아닌 검색어 단위 열거).
      · search_query 존재 → 채널 내 검색 URL (시리즈가 채널 전반에 흩어진 경우).
      · 그 외 → /videos 탭 (기존 계약 무변경).
    """
    search = channel_cfg.get("search")
    if not channel_cfg.get("channel_url") and search:
        n = int(limit) if limit else 40
        return f"ytsearch{n}:{search}"
    base = channel_cfg["channel_url"].rstrip("/")
    search_q = channel_cfg.get("search_query")
    if search_q:
        from urllib.parse import quote
        return f"{base}/search?query={quote(str(search_q))}"
    if "youtube.com" in base and not base.endswith(("/videos", "/shorts", "/streams")):
        return base + "/videos"
    return base


def _enumerate_channel(channel_cfg: dict, limit: int | None) -> list[dict]:
    """yt-dlp flat-playlist 열거 → [{id,title,duration}]. 다운로드 0.

    URL 은 build_enumeration_url(순수) — 채널 /videos, 채널 내 검색, ytsearch 스킴.
    """
    from yt_dlp import YoutubeDL

    opts = {
        "extract_flat": True,
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "no_warnings": True,
    }
    if limit:
        opts["playlistend"] = int(limit)
    url = build_enumeration_url(channel_cfg, limit)
    out: list[dict] = []
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    for e in ((info or {}).get("entries") or []):
        if not e:
            continue
        out.append({
            "id": e.get("id"),
            "title": e.get("title", ""),
            "duration": e.get("duration"),
        })
    return out


def _run_curate(registry: dict, args) -> int:
    """Vision 선별(다운로드 0, Gemini 과금). Task 3 belle greenlight 후에만.

    각 활성 유튜브 채널: yt-dlp 열거 → passes_filters → per-channel cap →
    curate_vision.gate → keep/reject/unknown 집계. verdict 는 캐시(재호출 0).
    다운로드·S3 적재는 하지 않는다(그건 --collect).
    """
    sys.path.insert(0, str(BACKEND / "training"))
    from datagen import curate_vision

    defaults = registry["defaults"]
    active = [c for c in _active_channels(registry) if c.get("platform") == "youtube"]
    if args.only:
        active = [c for c in active if args.only.lower() in c["name"].lower()]
    if not active:
        print("[curate] 대상 채널 0 (--only 필터 확인).", file=sys.stderr, flush=True)
        return 1

    gate = curate_vision.VisionGate()
    if not gate.ready:
        print(
            "[curate] Gemini 클라이언트 미초기화 (키 미설정/크레딧/SDK) — verdict 전부 unknown. "
            f"GEMINI_KEY_PARAM/{curate_vision.GEMINI_KEY_ENV} 및 AWS_PROFILE 확인 후 재실행.",
            file=sys.stderr, flush=True,
        )
        return 2

    per_cap = args.limit_per_channel or defaults.get("per_channel_cap", 40)
    total_gated = 0
    print(f"[curate] 활성 유튜브 채널 {len(active)} | per_channel_cap={per_cap} "
          f"| max_candidates={args.max_candidates or '무제한'} | 다운로드 0", flush=True)
    for ch in active:
        if args.max_candidates and total_gated >= args.max_candidates:
            break
        # 채널별 큐레이션 프로필 (quick-260714-js2) — fault_demo 는 편집/자막 수용
        # + 프로필 스코프 캐시 키(22-02 default reject 박제와 분리). 미지정 = default.
        profile = ch.get("curation_profile", "default")
        enum = _enumerate_channel(ch, per_cap * 4)  # 필터 전 여유 열거.
        passed = [e for e in enum if e.get("id") and passes_filters(e, ch, defaults)][:per_cap]
        kept = rejected = unknown = 0
        moves: dict[str, int] = {}
        for e in passed:
            if args.max_candidates and total_gated >= args.max_candidates:
                break
            url = f"https://www.youtube.com/watch?v={e['id']}"
            verdict = gate.gate(e["id"], url, profile=profile)
            dec = curate_vision.decide(verdict, profile=profile)
            total_gated += 1
            if dec.status == "keep":
                kept += 1
                moves[dec.move_guess or "?"] = moves.get(dec.move_guess or "?", 0) + 1
            elif dec.status == "reject":
                rejected += 1
            else:
                unknown += 1
        print(
            f"  {ch['name']:<30} [{ch.get('bucket','?'):<4}] 열거 {len(enum):>4} 필터통과 {len(passed):>3} "
            f"| gated {kept+rejected+unknown:>3} keep {kept:>3} reject {rejected:>3} unknown {unknown:>3}"
            + (f" moves={moves}" if moves else ""),
            flush=True,
        )
    print(
        f"\n[curate] gated {total_gated} (verdict 캐시 = "
        f"{curate_vision.VERDICT_CACHE_PATH}). 다운로드 0. belle 확인 후 --collect.",
        flush=True,
    )
    return 0


def _motion_slug(verdict: dict, channel_name: str) -> str:
    """S3 키의 {motion} 세그먼트 — 영문 동작명은 슬러그, 한글/미상은 채널명 폴백."""
    slug = _ascii_safe((verdict.get("move_guess") or "").strip())
    if not slug or slug == "unknown":
        return _ascii_safe(channel_name)
    return slug[:40]


def _load_manifest() -> dict:
    import json as _json

    try:
        return _json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"rows": [], "_meta": {}}


def _run_collect(registry: dict, args) -> int:
    """통과분(캐시 keep verdict) 다운로드 + S3 적재 + manifest 갱신. belle greenlight 후.

    멱등: manifest 에 이미 있는 s3_key 는 skip. verdict 캐시에 keep 인 후보만 받는다
    (재-curate 없이 curate 결과 재사용, 재과금 0). ffmpeg 불필요한 단일파일 포맷.
    """
    import json as _json
    import tempfile

    import boto3
    from yt_dlp import YoutubeDL

    sys.path.insert(0, str(BACKEND / "training"))
    from datagen import curate_vision

    defaults = registry["defaults"]
    active = [c for c in _active_channels(registry) if c.get("platform") == "youtube"]
    if args.only:
        active = [c for c in active if args.only.lower() in c["name"].lower()]

    gate = curate_vision.VisionGate()  # 캐시 로드용(네트워크 0, keep 조회만).
    manifest = _load_manifest()
    existing = {r.get("s3_key") for r in manifest.get("rows", [])}
    s3 = boto3.client("s3")
    per_cap = args.limit_per_channel or defaults.get("per_channel_cap", 40)

    downloaded = skipped = failed = unavailable = 0
    for ch in active:
        if args.max_candidates and downloaded >= args.max_candidates:
            break
        profile = ch.get("curation_profile", "default")
        enum = _enumerate_channel(ch, per_cap * 4)
        passed = [e for e in enum if e.get("id") and passes_filters(e, ch, defaults)][:per_cap]
        for e in passed:
            if args.max_candidates and downloaded >= args.max_candidates:
                break
            vid = e["id"]
            # curate 캐시 조회(재호출 0) — 프로필 스코프 키는 cache_key 헬퍼 경유
            # (계약 1벌, 직접 f-string 재작성 금지 — T-js2-02).
            verdict = gate._cache.get(curate_vision.cache_key(vid, profile))
            dec = curate_vision.decide(verdict, profile=profile)
            if dec.status != "keep":
                continue
            motion = _motion_slug(verdict, ch["name"])
            s3_key = build_s3_key(motion, vid)
            if s3_key in existing:
                skipped += 1
                continue
            assert_non_notified(s3_key)
            url = f"https://www.youtube.com/watch?v={vid}"
            try:
                with tempfile.TemporaryDirectory() as td:
                    opts = {
                        # bv+ba → ffmpeg mp4 병합(webm 복구), 없으면 progressive 폴백.
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
                    if not mp4:  # merge 실패 시 any 비디오 파일 폴백.
                        mp4 = next((f for f in files
                                    if f.suffix.lower() in (".webm", ".mkv", ".m4v")), None)
                    info = next((f for f in files if f.name.endswith(".info.json")), None)
                    if not mp4:
                        unavailable += 1  # 삭제·지역차단 등 = fail 아님(skip).
                        print(f"  [UNAVAIL] {vid} 비디오 파일 없음(삭제/차단 추정)", flush=True)
                        continue
                    s3.upload_file(str(mp4), BUCKET, s3_key,
                                   ExtraArgs={"ContentType": CONTENT_TYPE})
                    if info:
                        s3.upload_file(str(info), BUCKET, build_info_key(motion, vid),
                                       ExtraArgs={"ContentType": "application/json"})
                row = build_manifest_row(
                    motion=motion, video_id=vid, label_bucket=dec.bucket,
                    source_url=url, channel=ch["name"], tier=ch.get("tier", "?"),
                    yt_dlp_version=_ytdlp_version(), vision_verdict=verdict,
                    collected_at_ms=int(time.time() * 1000),
                )
                manifest.setdefault("rows", []).append(row)
                existing.add(s3_key)
                MANIFEST_PATH.write_text(
                    _json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                downloaded += 1
                print(f"  [OK] {ch['name']:<24} {vid} → {s3_key} ({dec.bucket}/{motion})", flush=True)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  [FAIL] {vid}: {exc}", file=sys.stderr, flush=True)

    print(f"\n[collect] 다운로드 {downloaded} | skip(기존) {skipped} | unavailable {unavailable} "
          f"| fail {failed} | manifest rows {len(manifest.get('rows', []))}. "
          f"_meta.collection_complete 미설정(부분 배치 — 균등게이트는 22-04 진입 assert).",
          flush=True)
    return 0 if failed == 0 else 1  # unavailable(삭제/차단)은 정상, 실 예외만 exit 1.


def _ytdlp_version() -> str:
    try:
        import yt_dlp
        return getattr(yt_dlp.version, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
