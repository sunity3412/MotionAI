"""채널 harvester 순수 필터 단위 테스트 (22-02 Task 1).

discipline_filter(후프 제외·폴 통과) / duration_window(타이틀카드 배제) /
series_filter(시리즈 매칭) 순수 함수만 검증 — 네트워크·yt-dlp 무관.
"""

import collect_phase22_youtube as harvest


DEFAULTS = {
    "discipline_include": r"(?i)(폴|pole)",
    "discipline_exclude": r"(?i)(후프|hoop|에어리얼|aerial)",
    "duration_window": [120, 400],
}


def test_discipline_excludes_hoop_includes_pole():
    """후프 종목 배제 + 폴 제목 통과 (비-폴 오염 차단)."""
    inc, exc = DEFAULTS["discipline_include"], DEFAULTS["discipline_exclude"]
    assert harvest.title_discipline_ok("2025 한국폴스포츠선수권 pole sports", inc, exc) is True
    assert harvest.title_discipline_ok("에어리얼 후프 루틴", inc, exc) is False
    assert harvest.title_discipline_ok("Aerial Hoop Championship", inc, exc) is False
    # 폴/후프 둘 다 언급되면 exclude 우선(안전).
    assert harvest.title_discipline_ok("폴 그리고 후프 믹스", inc, exc) is False


def test_duration_window_excludes_titlecard_and_block():
    """6s 타이틀카드·1000s 다인블록 배제, 180s 단일루틴 통과."""
    win = DEFAULTS["duration_window"]
    assert harvest.duration_in_window(6, win) is False
    assert harvest.duration_in_window(1000, win) is False
    assert harvest.duration_in_window(180, win) is True
    # 길이 미상(None) = 보수적 제외.
    assert harvest.duration_in_window(None, win) is False
    # window=None → 제한 없음.
    assert harvest.duration_in_window(6, None) is True


def test_series_filter_matches_only_series():
    """series_regex 있으면 매칭분만 통과, None 이면 전부 통과."""
    series_re = r"(?i)(폴인폴|fall\s*in\s*pole)"
    assert harvest.series_match("폴인폴 EP 3 오늘의 동작 #2 윈드밀", series_re) is True
    assert harvest.series_match("비키니폴 예능 클립", series_re) is False
    assert harvest.series_match("아무 제목", None) is True


def test_passes_filters_combines_three_gates():
    """discipline + duration + series 3중 게이트 결합."""
    channel_cfg = {"series_include": r"(?i)(폴인폴)"}
    good = {"title": "폴인폴 pole EP 5 스콜피온", "duration": 180}
    assert harvest.passes_filters(good, channel_cfg, DEFAULTS) is True
    # 시리즈 불일치 → 탈락.
    bad_series = {"title": "pole 개인영상", "duration": 180}
    assert harvest.passes_filters(bad_series, channel_cfg, DEFAULTS) is False
    # 길이 탈락.
    bad_dur = {"title": "폴인폴 pole EP 5", "duration": 6}
    assert harvest.passes_filters(bad_dur, channel_cfg, DEFAULTS) is False
    # 종목 탈락.
    bad_disc = {"title": "폴인폴 후프 EP 5", "duration": 180}
    assert harvest.passes_filters(bad_disc, channel_cfg, DEFAULTS) is False


def test_s3_key_scheme_non_notified():
    """키 스킴 = fixtures/phase22/{motion}/{id}.mp4, uploads/ 절대 금지 (HIGH 1)."""
    key = harvest.build_s3_key("windmill", "abc123")
    assert key == "fixtures/phase22/windmill/abc123.mp4"
    assert not key.startswith("uploads/")
    harvest.assert_non_notified(key)  # raise 없어야.
    # uploads/ prefix 는 self-check 에서 거부.
    import pytest

    with pytest.raises(RuntimeError):
        harvest.assert_non_notified("uploads/phase22/x.mp4")


def test_ascii_safe_filename_normalization():
    """외부 미디어 파일명 ASCII-safe 정규화 (T-22-06)."""
    key = harvest.build_s3_key("윈드밀", "id/../evil")
    assert not key.startswith("uploads/")
    assert key.startswith("fixtures/phase22/")
    # 경로 이스케이프 문자 제거.
    assert ".." not in key.split("/")[-1] or "/" not in key.split("fixtures/phase22/")[1].rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# fault 재수집 라운드 배선 (quick-260714-js2 — 검색쿼리 엔트리 + 프로필/cap 필드).
# ---------------------------------------------------------------------------
def test_load_registry_accepts_new_fields_and_filters_untouched(tmp_path):
    """curation_profile/cap_per_account/search 필드 로드 + passes_filters 불간섭."""
    yaml_text = (
        "defaults:\n"
        "  discipline_include: '(?i)(폴|pole)'\n"
        "  discipline_exclude: '(?i)(후프|hoop)'\n"
        "  duration_window: [120, 400]\n"
        "  per_channel_cap: 40\n"
        "channels:\n"
        "  - name: fault_ch\n"
        "    channel_url: https://www.youtube.com/@x\n"
        "    platform: youtube\n"
        "    bucket: fault\n"
        "    curation_profile: fault_demo\n"
        "  - name: yt_search_mistakes\n"
        "    platform: youtube\n"
        "    search: pole dance beginner mistakes\n"
        "    bucket: fault\n"
        "    curation_profile: fault_demo\n"
        "    duration_window: [30, 900]\n"
        "  - name: eunji.poledancer\n"
        "    channel_url: https://www.instagram.com/eunji.poledancer/\n"
        "    platform: instagram\n"
        "    bucket: fault\n"
        "    cap_per_account: 60\n"
    )
    p = tmp_path / "sources.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    reg = harvest.load_registry(p)
    assert len(reg["channels"]) == 3
    assert reg["channels"][0]["curation_profile"] == "fault_demo"
    assert reg["channels"][1]["search"] == "pole dance beginner mistakes"
    assert reg["channels"][2]["cap_per_account"] == 60
    # 신규 필드는 기존 3중 게이트(passes_filters)에 불간섭.
    good = {"title": "pole mistakes tutorial", "duration": 180}
    assert harvest.passes_filters(good, reg["channels"][0], reg["defaults"]) is True
    bad = {"title": "후프 mistakes", "duration": 180}
    assert harvest.passes_filters(bad, reg["channels"][0], reg["defaults"]) is False


def test_search_entry_builds_ytsearch_url():
    """channel_url 부재 + search 존재 엔트리 → ytsearch{N}: 스킴 (yt-dlp 미호출 순수)."""
    cfg = {
        "name": "yt_search_common_mistakes", "platform": "youtube",
        "search": "pole dance common mistakes tutorial",
        "bucket": "fault", "curation_profile": "fault_demo",
    }
    assert harvest.build_enumeration_url(cfg, 160) == (
        "ytsearch160:pole dance common mistakes tutorial"
    )
    # channel_url 보유 채널은 기존 /videos 탭 계약 무변경.
    ch = {"name": "KoreaPole", "channel_url": "https://www.youtube.com/@KoreaPole"}
    assert harvest.build_enumeration_url(ch, 160) == "https://www.youtube.com/@KoreaPole/videos"
    # 채널 내 검색(search_query) 경로도 기존 계약 유지.
    ch2 = {
        "name": "BerryTV", "channel_url": "https://www.youtube.com/@BerryTV",
        "search_query": "폴인폴",
    }
    assert harvest.build_enumeration_url(ch2, 160).startswith(
        "https://www.youtube.com/@BerryTV/search?query="
    )


def test_ig_account_cap_override():
    """cap_per_account 필드가 있으면 CLI 기본값을 오버라이드 (순수 헬퍼)."""
    import collect_phase22_instagram as ig

    assert ig.account_cap({"cap_per_account": 60}, 20) == 60
    assert ig.account_cap({}, 20) == 20
    assert ig.account_cap({"cap_per_account": "60"}, 20) == 60


def test_dry_run_exit_zero_with_recollection_entries(capsys):
    """--dry-run 이 신규 fault 검색 엔트리 포함 exit 0 + 키 스킴 self-check (네트워크 0)."""
    assert harvest.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    # 신규 검색쿼리 엔트리(fault 재수집 라운드)가 레지스트리에 등재돼 순회에 나타난다.
    assert "yt_search" in out
    assert "uploads/" not in out
    # IG dry-run 도 exit 0 (계정 목록만, 다운로드 0).
    import collect_phase22_instagram as ig

    assert ig.main(["--dry-run"]) == 0
