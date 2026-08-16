"""backend/scripts/p35_extract_align.py 캐시 fresh-by-default 회귀 (quick-260816-k2f).

오늘(2026-08-16) 실측 근거 — ref-climb.mp4 를 새 영상(40,928,589B)으로 교체하고
P35 align 을 재생성했는데 climb 슬롯만 옛 refFrames=256(climb/rf15 mtime 06:00)
을 재사용하고 climbfault 는 같은 새 ref.mp4 로 refFrames=119(climbfault/rf15
mtime 09:13)를 정상 산출했다. 두 존재기반 캐시(s3_download() 의 dst.exists(),
compare_align.extract() 의 *.jpg 존재 체크) 중 어느 쪽도 원본 내용이 바뀌었는지
확인하지 않아서다 — `rm -rf climb/{rf15,verify}` 후 재추출하니 refFrames=119 로
정상화됐다. 이 테스트는 그 사고가 재발하지 않는다는 것을 tmp_path 합성 디렉토리로
고정한다 — S3/GPU/Firestore 실호출 0.
"""
from __future__ import annotations

from pathlib import Path

import p35_extract_align as pea


def _populate(mdir: Path) -> None:
    """process() 가 실제로 만드는 디렉토리 구조를 tmp_path 위에 최소 재현.

    CACHE_PATHS 5항목(user.mp4/ref.mp4/uf15/rf15/verify) + 화이트리스트 밖
    3항목(doc.json/moments.json/align.json)을 모두 채운다 — 삭제/생존을
    같은 디렉토리에서 동시에 검증하기 위함."""
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "user.mp4").write_bytes(b"fake-user-video-bytes")
    (mdir / "ref.mp4").write_bytes(b"fake-ref-video-bytes")
    for sub in ("uf15", "rf15", "verify"):
        subdir = mdir / sub
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "00001.jpg").write_bytes(b"fake-jpg-bytes")
    (mdir / "doc.json").write_text('{"result": {}}')
    (mdir / "moments.json").write_text("{}")
    (mdir / "align.json").write_text('{"motion": "x"}')


class TestCleanMotionCache:
    def test_removes_whitelist_preserves_inputs_and_output(self, tmp_path):
        mdir = tmp_path / "climb"
        _populate(mdir)

        removed = pea.clean_motion_cache(mdir)

        assert removed == list(pea.CACHE_PATHS)
        for name in pea.CACHE_PATHS:
            assert not (mdir / name).exists(), f"{name} 이 삭제되지 않음"
        # 화이트리스트 밖 3항목은 byte-identical 로 생존해야 한다 — 파생 캐시가
        # 아니라 사전 주입 입력(doc/moments)과 이 스크립트의 최종 산출물(align).
        assert (mdir / "doc.json").read_text() == '{"result": {}}'
        assert (mdir / "moments.json").read_text() == "{}"
        assert (mdir / "align.json").read_text() == '{"motion": "x"}'

    def test_noop_when_cache_absent(self, tmp_path):
        mdir = tmp_path / "climb"
        mdir.mkdir(parents=True)
        (mdir / "doc.json").write_text('{"result": {}}')

        assert pea.clean_motion_cache(mdir) == []
        assert (mdir / "doc.json").read_text() == '{"result": {}}'

    def test_safe_when_mdir_missing(self, tmp_path):
        mdir = tmp_path / "does-not-exist"

        assert pea.clean_motion_cache(mdir) == []


class TestMaybeCleanCache:
    def test_reuse_cache_true_skips_deletion(self, tmp_path):
        mdir = tmp_path / "climb"
        _populate(mdir)

        removed = pea.maybe_clean_cache(mdir, reuse_cache=True)

        assert removed == []
        for name in pea.CACHE_PATHS:
            assert (mdir / name).exists(), f"{name} 이 --reuse-cache 인데 삭제됨"

    def test_reuse_cache_false_delegates_to_clean(self, tmp_path):
        mdir = tmp_path / "climb"
        _populate(mdir)

        removed = pea.maybe_clean_cache(mdir, reuse_cache=False)

        assert removed == list(pea.CACHE_PATHS)
        for name in pea.CACHE_PATHS:
            assert not (mdir / name).exists()
        assert (mdir / "doc.json").read_text() == '{"result": {}}'


class TestReuseCacheFlag:
    def test_default_is_false(self, tmp_path):
        args = pea.build_arg_parser().parse_args(["--workdir", str(tmp_path)])
        assert args.reuse_cache is False

    def test_explicit_flag_sets_true(self, tmp_path):
        args = pea.build_arg_parser().parse_args(
            ["--workdir", str(tmp_path), "--reuse-cache"]
        )
        assert args.reuse_cache is True
