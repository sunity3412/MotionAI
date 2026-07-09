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
