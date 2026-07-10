"""Full batch 러너 단위 테스트 — resumable skip / 행별 영속화 / 조립 배선 (22-04 Task 4).

핵심 불변식:
  · resumable — 터미널 결과(accepted/rejected_*) 행은 재실행 시 Gemini 호출 0(과금 재발 0).
    "error"/"ABORT_429" 행은 재시도 대상.
  · 영속화 — 수락 행이 accepted/<slug>.json 에 즉시 기록(메모리 반환 의존 금지),
    build_jsonl distill_loader 계약 필드 포함.
  · 429 즉시 중단 + 기존 필터 회귀 없음(evaluate_filters 재사용).
  · assemble_jsonl — accepted 디렉토리 → train/val JSONL, 업로드는 uploader 주입 시에만.

네트워크 0 — fake Gemini client(모델별 응답 라우팅) + fake S3 다운로드.
"""

from __future__ import annotations

import json
from pathlib import Path

from distill import full_batch as fb
from distill import gemini_teacher as gt


# ---------------------------------------------------------------------------
# fake Gemini client — 교사/judge 모델별 응답 라우팅 + 호출 기록.
# ---------------------------------------------------------------------------
_TEACHER_TEXT = '{"coaching": "골반을 폴에 붙이세요", "faults": []}'


class _FakeHandle:
    def __init__(self, name: str, state: str = "ACTIVE"):
        self.name = name

        class _S:
            pass

        s = _S()
        s.name = state
        self.state = s


class _FakeFiles:
    def __init__(self):
        self.uploaded = []
        self.deleted = []

    def upload(self, file):  # noqa: A002 - genai SDK 시그니처 미러.
        self.uploaded.append(file)
        return _FakeHandle(name=f"files/{len(self.uploaded)}")

    def get(self, name):
        return _FakeHandle(name=name)

    def delete(self, name):
        self.deleted.append(name)

    def list(self):
        return []


class _RoutedModels:
    """모델 string 으로 교사/judge 응답을 라우팅 — full batch 는 두 모델을 다 부른다."""

    def __init__(self, teacher_text=_TEACHER_TEXT, judge_text="9", raises=None):
        self.calls = []
        self._teacher_text = teacher_text
        self._judge_text = judge_text
        self._raises = raises

    def generate_content(self, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self._raises is not None:
            raise self._raises

        class _R:
            pass

        r = _R()
        r.text = self._judge_text if model == gt.JUDGE_MODEL else self._teacher_text
        return r


class _FakeClient:
    def __init__(self, **kw):
        self.files = _FakeFiles()
        self.models = _RoutedModels(**kw)


def _fake_download(monkeypatch):
    def _dl(bucket, key, dest):
        with open(dest, "wb") as fp:
            fp.write(b"fake video bytes for " + key.encode())

    monkeypatch.setattr(gt, "_download_s3", _dl)


def _manifest(n=2):
    rows = [
        {"s3_key": f"fixtures/phase22/climb/v{i}.mp4", "motion": "climb",
         "label_bucket": "정타", "source": "youtube", "usage": "training-only",
         "holdout": None, "anonymized": False}
        for i in range(n)
    ]
    return {"_meta": {"collection_complete": True}, "rows": rows}


def _coords_provider(row):
    return [{"frame": 0, "left_knee": [500, 500, 0.9]}]


def _run(tmp_path, client, manifest=None, provider=_coords_provider, **kw):
    return fb.run_full_batch(
        manifest or _manifest(),
        str(tmp_path / "out"),
        str(tmp_path / "scratch"),
        coords_provider=provider,
        client=client,
        probe=False,
        **kw,
    )


# ---------------------------------------------------------------------------
# 영속화 — 행별 결과 + accepted 즉시 기록.
# ---------------------------------------------------------------------------
def test_full_batch_persists_reports_and_accepted(tmp_path, monkeypatch):
    _fake_download(monkeypatch)
    client = _FakeClient()
    result = _run(tmp_path, client)

    assert result["aborted"] is None
    assert result["n_processed"] == 2 and result["n_skipped"] == 0
    assert result["stats"]["accepted"] == 2 and result["stats"]["pending"] == 0
    # 행별 결과 파일 + accepted 파일이 디스크에 존재(메모리 반환 의존 금지).
    reports = sorted(Path(result["reports_dir"]).glob("*.json"))
    accepted = sorted(Path(result["accepted_dir"]).glob("*.json"))
    assert len(reports) == 2 and len(accepted) == 2
    sample = json.loads(accepted[0].read_text(encoding="utf-8"))
    # build_jsonl distill_loader 계약 필드.
    for key in ("video_hash", "s3_key", "motion", "thought", "report",
                "joint_keys", "coords_by_frame"):
        assert key in sample, f"accepted 계약 필드 {key} 부재"
    assert sample["coords_by_frame"] == _coords_provider(None)
    assert sample["report"]["coaching"] == "골반을 폴에 붙이세요"
    # File API 누수 0 — 업로드 수 == 삭제 수.
    assert len(client.files.deleted) == len(client.files.uploaded) == 2


def test_full_batch_rejected_row_not_in_accepted(tmp_path, monkeypatch):
    """기존 필터 회귀 없음 — judge<7 이면 rejected_judge, accepted 파일 0."""
    _fake_download(monkeypatch)
    client = _FakeClient(judge_text="5")
    result = _run(tmp_path, client)
    assert result["stats"]["rejected_judge"] == 2
    assert list(Path(result["accepted_dir"]).glob("*.json")) == []
    # 결과 파일에는 raw/judge/사유가 남는다(진단 가능).
    payload = json.loads(next(Path(result["reports_dir"]).glob("*.json")).read_text(encoding="utf-8"))
    assert payload["result"] == "rejected_judge" and payload["judge"] == 5
    assert payload["raw_text"] == _TEACHER_TEXT


# ---------------------------------------------------------------------------
# resumable — 터미널 결과 skip(Gemini 호출 0) / error·429 는 재시도.
# ---------------------------------------------------------------------------
def test_full_batch_resumable_skips_terminal_rows(tmp_path, monkeypatch):
    _fake_download(monkeypatch)
    _run(tmp_path, _FakeClient())  # 1차 run — 2행 accepted.

    fresh = _FakeClient()
    result = fb.run_full_batch(
        _manifest(), str(tmp_path / "out"), str(tmp_path / "scratch"),
        coords_provider=_coords_provider, client=fresh, probe=False,
    )
    assert result["n_skipped"] == 2 and result["n_processed"] == 0
    # 재실행에서 Gemini 호출/업로드 0 (과금 재발 0).
    assert fresh.models.calls == [] and fresh.files.uploaded == []
    assert result["stats"]["accepted"] == 2


def test_full_batch_retries_error_rows(tmp_path, monkeypatch):
    _fake_download(monkeypatch)
    boom = _FakeClient(raises=RuntimeError("일시 오류"))
    r1 = _run(tmp_path, boom)
    assert r1["stats"]["error"] == 2 and r1["aborted"] is None

    r2 = _run(tmp_path, _FakeClient())  # error 는 터미널 아님 — 재시도.
    assert r2["n_processed"] == 2 and r2["stats"]["accepted"] == 2


def test_full_batch_quota_abort_stops_and_is_retryable(tmp_path, monkeypatch):
    _fake_download(monkeypatch)
    quota = _FakeClient(raises=RuntimeError("429 RESOURCE_EXHAUSTED"))
    r1 = _run(tmp_path, quota)
    assert r1["aborted"] is not None and "quota_exhausted" in r1["aborted"]
    # 첫 행에서 즉시 중단 — 두 번째 행은 결과 파일조차 없다(pending).
    assert r1["stats"]["ABORT_429"] == 1 and r1["stats"]["pending"] == 1

    r2 = _run(tmp_path, _FakeClient())  # ABORT_429 는 터미널 아님 — 재시도.
    assert r2["aborted"] is None and r2["stats"]["accepted"] == 2


def test_full_batch_reconstructs_missing_accepted_on_skip(tmp_path, monkeypatch):
    """accepted 파일 유실 시 skip 경로가 결과 파일 + 좌표 캐시로 재구성(재과금 0)."""
    _fake_download(monkeypatch)
    r1 = _run(tmp_path, _FakeClient())
    for p in Path(r1["accepted_dir"]).glob("*.json"):
        p.unlink()

    fresh = _FakeClient()
    r2 = _run(tmp_path, fresh)
    assert fresh.models.calls == []  # Gemini 재호출 0.
    accepted = sorted(Path(r2["accepted_dir"]).glob("*.json"))
    assert len(accepted) == 2
    sample = json.loads(accepted[0].read_text(encoding="utf-8"))
    assert sample["report"]["coaching"] == "골반을 폴에 붙이세요"
    assert sample["coords_by_frame"] == _coords_provider(None)


# ---------------------------------------------------------------------------
# build_jsonl 연결 — accepted → distill_loader + manifest hash 주입 + gated 업로드.
# ---------------------------------------------------------------------------
def _accepted_fixture(tmp_path) -> Path:
    accepted_dir = tmp_path / "out" / "accepted"
    accepted_dir.mkdir(parents=True)
    sample = {
        "video_hash": "vh-climb-0",
        "s3_key": "fixtures/phase22/climb/v0.mp4",
        "motion": "climb",
        "thought": "가려짐 보정",
        "report": {
            "coaching": "골반을 폴에 붙이세요",
            "faults": [
                {"student_angle_deg": 120.0, "reference_angle_deg": 178.0,
                 "measurement_basis": "왼무릎 관절각", "fault_category": "limb_extension",
                 "body_part": "왼무릎"}
            ],
        },
        "joint_keys": ["left_knee"],
        "coords_by_frame": [{"frame": 0, "left_knee": [500, 500, 0.9]}],
    }
    (accepted_dir / "fixtures__phase22__climb__v0.mp4.json").write_text(
        json.dumps(sample, ensure_ascii=False), encoding="utf-8"
    )
    return accepted_dir


def test_manifest_with_hashes_injects_video_hash(tmp_path):
    accepted_dir = _accepted_fixture(tmp_path)
    manifest = _manifest()  # 행에 video_hash 없음(22-02 실제 상태).
    m2 = fb.manifest_with_hashes(manifest, accepted_dir)
    assert m2["rows"][0]["video_hash"] == "vh-climb-0"
    assert "video_hash" not in m2["rows"][1]  # accepted 에 없는 행은 미주입.
    assert "video_hash" not in manifest["rows"][0]  # 원본 불변(사본 반환).


def test_assemble_jsonl_builds_distill_track_without_upload(tmp_path):
    accepted_dir = _accepted_fixture(tmp_path)
    out = fb.assemble_jsonl(_manifest(), accepted_dir, tmp_path / "jsonl")
    assert out["uploaded"] == []  # uploader 미주입 — 업로드 0(gated).
    train = Path(out["paths"]["train"])
    assert train.exists()
    lines = [json.loads(l) for l in train.read_text(encoding="utf-8").splitlines()]
    distill = [s for s in lines if s.get("_track") == "distill"]
    assert len(distill) == 1  # video_hash 주입으로 join 성립.
    assert out["meta"]["track_counts"]["distill"] == 1
    assert out["meta"]["validation_owner"] == "explicit_val_jsonl"


def test_assemble_jsonl_uploads_only_with_injected_uploader(tmp_path):
    accepted_dir = _accepted_fixture(tmp_path)
    calls = []

    def uploader(local, key):
        calls.append((local, key))

    out = fb.assemble_jsonl(_manifest(), accepted_dir, tmp_path / "jsonl", uploader=uploader)
    keys = sorted(k for _, k in calls)
    assert keys == sorted(out["uploaded"])
    assert all(k.startswith("training/phase22/jsonl/") for k in keys)  # canonical.
    assert any(k.endswith("train.jsonl") for k in keys)

    # partial run 은 canonical prefix 금지(DR-06).
    calls.clear()
    fb.assemble_jsonl(_manifest(), accepted_dir, tmp_path / "jsonl_p",
                      partial=True, uploader=uploader)
    assert calls and all(k.startswith("training/phase22/jsonl_partial/") for _, k in calls)


def test_terminal_results_match_filter_reasons():
    """터미널 집합이 evaluate_filters 사유와 정합 — 필터 사유 추가 시 여기서 잡힌다."""
    stats_keys = set(gt.FilterStats().as_dict().keys())
    assert fb.TERMINAL_RESULTS == stats_keys
