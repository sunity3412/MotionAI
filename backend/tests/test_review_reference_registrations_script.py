"""quick-261001-thx Task 2 — 검수 운영 CLI review_reference_registrations.py (실 Firestore · S3 · ffmpeg 0).

잠그는 계약:
  · list — review 상태만 조회(단일 등가 쿼리), 건마다 비공개 진단을 읽어 요약. 0건이면 "검수 대기 0건".
  · show — 썸네일 · v1 을 --out 폴더(권한 700)에 받고 anglesFrames/anglesRealFps 길이의 10·50·90% 프레임 3장.
    썸네일 키가 없으면 그 줄만 '없음', 나머지는 계속.
  · approve / reject — firestore_admin writer 결과를 그대로 출력, ValueError 는 stderr + 종료 1.
    ref-* · 형식 밖 id · 빈 사유 · 200자 초과 사유는 Firestore 호출 전 종료 2. --dry-run 은 writer 0.
  · --help — 자격 초기화 없이 네 서브커맨드.
"""

from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path

import pytest

from sunity_shared import firestore_admin as fa
from sunity_shared import models
from tests.phase31.conftest import fake_firestore  # noqa: F401 — 픽스처 재등록(디렉터리 밖)

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_reference_registrations.py"
REF = "0123456789abcdef0123456789abcdef"
REF2 = "fedcba9876543210fedcba9876543210"
T0 = 1_700_000_000_000


@pytest.fixture
def script(monkeypatch):
    spec = importlib.util.spec_from_file_location("review_reference_registrations_script", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["review_reference_registrations_script"] = mod
    spec.loader.exec_module(mod)
    init_calls: list[str] = []
    monkeypatch.setattr(mod, "_ensure_credentials", lambda: init_calls.append("init"))
    mod._init_calls = init_calls
    yield mod
    sys.modules.pop("review_reference_registrations_script", None)


class _Rec:
    def __init__(self, result=None):
        self.result = result
        self.calls: list[tuple] = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _seed_review(db, ref_id=REF, **extra):
    doc = {
        "motionId": ref_id, "registrationStatus": "review", "isActive": False, "supplierUid": "u1",
        "supplierCode": "EUNJI", "name": "아이샤", "athleteName": "정은지", "level": "advanced",
        "selfScore": 94.26, "selfCheckStatus": "done", "createdAt": T0,
        "videoS3Key": f"reference/u1/{ref_id}/v1.mp4", "thumbnailS3Key": f"reference/u1/{ref_id}/thumb.jpg",
        "anglesFrames": 100, "anglesRealFps": 10.0,
    }
    doc.update(extra)
    db._apply("set", f"reference/{ref_id}", doc, False)
    db._apply(
        "set", f"reference/{ref_id}/private/registration",
        {"supplierUid": "u1", "registrationDiagnostics": {
            "personRatio": 0.538, "lowConfidenceJoints": ["left_ankle"], "standMaterialUnreadable": [],
            "standingStart": "floor_violation", "nStand": 9}},
        False,
    )


# ─────────────────────── list ───────────────────────


def test_list_empty_prints_zero(script, fake_firestore, capsys):
    assert script.main(["list"]) == 0
    assert "검수 대기 0건" in capsys.readouterr().out
    assert fake_firestore.query_log == [("reference", "registrationStatus", "==", "review")]


def test_list_shows_review_rows_with_diagnosis_summary_and_full_ids(script, fake_firestore, capsys):
    _seed_review(fake_firestore)
    _seed_review(fake_firestore, REF2, selfScore=None, selfCheckStatus="pending", createdAt=T0 + 1)
    fake_firestore._apply("set", "reference/aaaa", {"registrationStatus": "active", "name": "숨김"}, False)
    assert script.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "검수 대기 2건" in out
    assert "숨김" not in out  # review 만
    line = next(ln for ln in out.splitlines() if ln.startswith(REF[:8]))
    for part in ("EUNJI", "아이샤", "정은지", "advanced", "94.3", "여러명=0.54", "저신뢰=1(왼쪽 발목)",
                 "서있는시작=floor_violation"):
        assert part in line, (part, line)
    line2 = next(ln for ln in out.splitlines() if ln.startswith(REF2[:8]))
    assert "pending" in line2
    assert f"{REF[:8]} = {REF}" in out and f"{REF2[:8]} = {REF2}" in out
    assert script._init_calls == ["init"]


# ─────────────────────── show ───────────────────────


class _FakeS3:
    def __init__(self, fail_keys=()):
        self.downloads: list[tuple[str, str, str]] = []
        self.fail_keys = set(fail_keys)

    def download_file(self, bucket, key, dest):
        self.downloads.append((bucket, key, dest))
        if key in self.fail_keys:
            raise RuntimeError("denied")
        Path(dest).write_bytes(b"x")


@pytest.fixture
def show_env(script, fake_firestore, monkeypatch):
    s3 = _FakeS3()
    monkeypatch.setattr(script, "_s3_client", lambda: s3)
    frames: list[tuple[str, float, str, int]] = []

    def fake_extract(src, t_sec, dst, width=360):
        frames.append((src, t_sec, dst, width))
        Path(dst).write_bytes(b"jpg")

    monkeypatch.setattr(script.reference_media, "extract_thumbnail", fake_extract)
    return s3, frames


def test_show_downloads_thumb_video_and_three_frames(script, fake_firestore, show_env, tmp_path, capsys):
    s3, frames = show_env
    _seed_review(fake_firestore)
    out_dir = tmp_path / "rv"
    assert script.main(["show", REF, "--out", str(out_dir), "--bucket", "bkt"]) == 0
    out = capsys.readouterr().out
    assert [(b, k) for b, k, _ in s3.downloads] == [
        ("bkt", f"reference/u1/{REF}/thumb.jpg"),
        ("bkt", f"reference/u1/{REF}/v1.mp4"),
    ]
    # 길이 = 100 / 10 = 10초 → 1.0 · 5.0 · 9.0 초
    assert [round(t, 3) for _, t, _, _ in frames] == [1.0, 5.0, 9.0]
    assert all(src == str(out_dir / "v1.mp4") for src, _, _, _ in frames)
    lines = [ln for ln in out.splitlines() if ln.split(" ")[0] in ("thumb", "video", "frame10", "frame50", "frame90")]
    assert len(lines) == 5
    assert str(out_dir / "thumb.jpg") in out and str(out_dir / "frame90.jpg") in out
    assert stat.S_IMODE(os.stat(out_dir).st_mode) == 0o700


def test_show_without_thumbnail_key_prints_none_and_continues(script, fake_firestore, show_env, tmp_path, capsys):
    s3, frames = show_env
    _seed_review(fake_firestore, thumbnailS3Key=None)
    assert script.main(["show", REF, "--out", str(tmp_path / "o")]) == 0
    out = capsys.readouterr().out
    assert next(ln for ln in out.splitlines() if ln.startswith("thumb")).endswith("없음")
    assert [k for _, k, _ in s3.downloads] == [f"reference/u1/{REF}/v1.mp4"]
    assert len(frames) == 3


def test_show_without_fps_skips_frames(script, fake_firestore, show_env, tmp_path, capsys):
    _s3, frames = show_env
    _seed_review(fake_firestore, anglesRealFps=None)
    assert script.main(["show", REF, "--out", str(tmp_path / "o")]) == 0
    assert frames == []
    assert capsys.readouterr().out.count("없음") == 3


def test_show_missing_doc_exit_1(script, fake_firestore, show_env, tmp_path):
    assert script.main(["show", REF, "--out", str(tmp_path / "o")]) == 1


@pytest.mark.parametrize("bad", ["ref-kip-up", "XYZ", REF.upper(), REF[:8]])
def test_show_bad_ref_id_exit_2_without_firestore(script, fake_firestore, show_env, bad):
    assert script.main(["show", bad]) == 2
    assert script._init_calls == []
    assert show_env[0].downloads == []


def test_default_review_root_is_outside_home():
    spec = importlib.util.spec_from_file_location("rr_root_probe", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert str(mod.REVIEW_ROOT) == "/Users/Shared/sunity-motion-review"
    assert not str(mod.REVIEW_ROOT).startswith(str(Path.home()))


# ─────────────────────── approve / reject ───────────────────────


@pytest.mark.parametrize("result", ["approved", "already_approved"])
def test_approve_prints_writer_result(script, monkeypatch, capsys, result):
    rec = _Rec(result)
    monkeypatch.setattr(fa, "approve_reference_registration", rec)
    assert script.main(["approve", REF, "--by", "ops:belle"]) == 0
    assert rec.calls == [((REF,), {"by": "ops:belle"})]
    assert capsys.readouterr().out.startswith(f"{result} ref={REF}")


def test_approve_default_by_is_ops_user(script, monkeypatch):
    rec = _Rec("approved")
    monkeypatch.setattr(fa, "approve_reference_registration", rec)
    monkeypatch.setattr(script.getpass, "getuser", lambda: "kim")
    assert script.main(["approve", REF]) == 0
    assert rec.calls[0][1]["by"] == "ops:kim"


def test_approve_value_error_exit_1_stderr(script, monkeypatch, capsys):
    monkeypatch.setattr(fa, "approve_reference_registration", _Rec(ValueError("approve needs review")))
    assert script.main(["approve", REF]) == 1
    assert "approve needs review" in capsys.readouterr().err


@pytest.mark.parametrize("cmd", [["approve", "ref-kip-up"], ["reject", "ref-kip-up", "--reason", "x"],
                                 ["approve", "not-hex"], ["approve", REF, "--by", "  "]])
def test_input_rule_violations_exit_2_without_firestore(script, monkeypatch, cmd):
    a, r = _Rec("approved"), _Rec("rejected")
    monkeypatch.setattr(fa, "approve_reference_registration", a)
    monkeypatch.setattr(fa, "reject_reference_registration", r)
    assert script.main(cmd) == 2
    assert a.calls == [] and r.calls == []
    assert script._init_calls == []


@pytest.mark.parametrize("reason", ["", "   ", ".", "가" * 201])
def test_reject_bad_reason_exit_2(script, monkeypatch, reason):
    r = _Rec("rejected")
    monkeypatch.setattr(fa, "reject_reference_registration", r)
    assert script.main(["reject", REF, "--reason", reason]) == 2
    assert r.calls == []


def test_reject_strips_spaces_and_trailing_period(script, monkeypatch, capsys):
    r = _Rec("rejected")
    monkeypatch.setattr(fa, "reject_reference_registration", r)
    assert script.main(["reject", REF, "--reason", "  화면이 어두워요. ", "--by", "ops:belle"]) == 0
    assert r.calls == [((REF,), {"reason": "화면이 어두워요", "by": "ops:belle"})]
    assert capsys.readouterr().out.startswith(f"rejected ref={REF}")


def test_reject_already_rejected_is_ok(script, monkeypatch, capsys):
    monkeypatch.setattr(fa, "reject_reference_registration", _Rec("already_rejected"))
    assert script.main(["reject", REF, "--reason", "사유"]) == 0
    assert "already_rejected" in capsys.readouterr().out


@pytest.mark.parametrize("cmd", [["approve", REF, "--dry-run"], ["reject", REF, "--reason", "어두워요", "--dry-run"]])
def test_dry_run_calls_no_writer(script, fake_firestore, monkeypatch, capsys, cmd):
    _seed_review(fake_firestore)
    a, r = _Rec("approved"), _Rec("rejected")
    monkeypatch.setattr(fa, "approve_reference_registration", a)
    monkeypatch.setattr(fa, "reject_reference_registration", r)
    before = dict(fake_firestore.store[f"reference/{REF}"])
    commits = fake_firestore.commit_count
    assert script.main(cmd) == 0
    assert a.calls == [] and r.calls == []
    assert fake_firestore.store[f"reference/{REF}"] == before
    assert fake_firestore.commit_count == commits
    out = capsys.readouterr().out
    assert "현재=review" in out and "쓰기 없음" in out


def test_dry_run_missing_doc_exit_1(script, fake_firestore):
    assert script.main(["approve", REF, "--dry-run"]) == 1


def test_end_to_end_with_real_writers_on_fake_firestore(script, fake_firestore, monkeypatch, capsys):
    """CLI → 실제 firestore_admin writer → FakeFirestore. 두 번 돌려도 두 번째는 쓰기 0."""
    monkeypatch.setattr(fa, "_now_ms", lambda: T0)
    _seed_review(fake_firestore)
    assert script.main(["approve", REF, "--by", "ops:belle"]) == 0
    assert fake_firestore.store[f"reference/{REF}"]["isActive"] is True
    assert fake_firestore.store[f"reference/{REF}"]["registrationStatus"] == models.REGISTRATION_STATUS_ACTIVE
    assert script.main(["approve", REF, "--by", "ops:belle"]) == 0
    assert "already_approved" in capsys.readouterr().out.splitlines()[-1]


# ─────────────────────── --help ───────────────────────


def test_help_needs_no_credentials(script, capsys):
    with pytest.raises(SystemExit) as ei:
        script.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("list", "show", "approve", "reject"):
        assert cmd in out
    assert script._init_calls == []
