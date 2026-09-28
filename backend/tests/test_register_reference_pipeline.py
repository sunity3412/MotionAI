"""`pipeline._register_reference` — 등록 서비스 합성 강제 (Phase 38-07 Task 2, REQ-38-2 · D-05 · D-09 · D-10).

Pod · S3 · Firestore · GPU 0. 가짜: `_s3`(객체 저장소 — ETag 조건부 복사), `_FRAME_EXTRACTOR`(probe/extract/fps),
`_POSE_ESTIMATOR`(실제 `RTMWPoseEngine.create_with_inferencer` + 프레임별 mock 추론), `firestore_admin` writer(기록).
판정(`registration_checks.check_registration`) · 각도(`compute_joint_angles` · `temporal_fill`) · `max_split` ·
`build_keypoint_report` · `_dataclass_to_camel_case_dict` 는 **실제 함수**다 — 리뷰 R1 / plan-checker 차단 1 을
mock 으로 우회하지 않는다.

잠그는 것:
  · R9 크기·길이가 다운로드/디코딩 **전**에 거른다(too_large · too_short · too_long, probe None 이면 extract end_s 캡).
  · R5 upload → v1 `copy_object(CopySourceIfMatch=ETag)` — angles·재생·자기 재현성 전부 v1, 처리 중 교체는 server_error.
  · 실패 7코드가 각각 `set_registration_failed(error={code,message[,joints]})` 로 남는다(순서는 38-05 소유).
  · 차단 1: `check_registration` 과 `set_reference_angles` 가 받는 keypointReport 는 **같은 camelCase dict**.
  · R8 자기 재현성 = begin_self_check → create_analysis_doc → copy_object(v1 → uploads/).
  · stale job 은 쓰기 0 · 활성화 뒤 재PUT 은 스킵되고 v1·angles 불변.
"""

from __future__ import annotations

import importlib
import logging
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from botocore.exceptions import ClientError

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "shared" / "python" / "sunity_shared" / "analysis" / "pose_engines" / "rtmw" / "weights_manifest.json"
)

UID = "u1"
REF_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
JOB = "A"
BUCKET = "b"
UPLOAD_KEY = f"reference/{UID}/{REF_ID}/upload.mp4"
V1_KEY = f"reference/{UID}/{REF_ID}/v1.mp4"
ETAG = '"e1"'
FPS = 10.0
W = H = 100
_HEX32 = re.compile(r"^[0-9a-f]{32}$")

# COCO-17 인덱스 in RTMW 133 wholebody layout (wholebody_keypoints.RTMW_KEYPOINT_INDICES 와 같은 값).
_L_SHO, _R_SHO, _L_ELB, _R_ELB, _L_WRI, _R_WRI = 5, 6, 7, 8, 9, 10
_L_HIP, _R_HIP, _L_KNE, _R_KNE, _L_ANK, _R_ANK = 11, 12, 13, 14, 15, 16


def _frames_133(
    T: int,
    *,
    n_people: int = 1,
    stand: int = 10,
    ankle_stand_y: float = 0.8,
    ankle_window_y: float = 0.7,
    ankle_conf: float = 0.9,
    conf: float = 0.9,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """프레임별 rtmlib 반환 `((N,133,2) px, (N,133) score)` — 앞 `stand` 프레임은 서 있는 자세(어깨 0.5 · 발목
    `ankle_stand_y` → 몸길이 0.3), 이후는 봉에 매달린 창 자세(발목 `ankle_window_y`). 좌표는 정규화 × 100px."""
    out = []
    for t in range(T):
        standing = t < stand
        if standing:
            pts = {
                _L_SHO: (0.45, 0.50), _R_SHO: (0.55, 0.50),
                _L_ELB: (0.40, 0.58), _R_ELB: (0.60, 0.58),
                _L_WRI: (0.38, 0.66), _R_WRI: (0.62, 0.66),
                _L_HIP: (0.46, 0.65), _R_HIP: (0.54, 0.65),
                _L_KNE: (0.46, 0.72), _R_KNE: (0.54, 0.72),
                _L_ANK: (0.46, ankle_stand_y), _R_ANK: (0.54, ankle_stand_y),
            }
        else:
            pts = {
                _L_SHO: (0.45, 0.35), _R_SHO: (0.55, 0.35),
                _L_ELB: (0.42, 0.28), _R_ELB: (0.58, 0.28),
                _L_WRI: (0.45, 0.20), _R_WRI: (0.55, 0.20),
                _L_HIP: (0.46, 0.50), _R_HIP: (0.54, 0.50),
                _L_KNE: (0.40, 0.60), _R_KNE: (0.60, 0.60),
                _L_ANK: (0.36, ankle_window_y), _R_ANK: (0.64, ankle_window_y),
            }
        kps = np.zeros((n_people, 133, 2), dtype=np.float32)
        scores = np.full((n_people, 133), conf, dtype=np.float32)
        for p in range(n_people):
            for idx, (x, y) in pts.items():
                kps[p, idx] = ((x + 0.05 * p) * W, y * H)
            scores[p, _L_ANK] = ankle_conf
            scores[p, _R_ANK] = ankle_conf
        out.append((kps, scores))
    return out


class _FakeS3:
    """객체 저장소 흉내 — head/copy(CopySourceIfMatch)/download. 호출은 `events` 에 순서대로."""

    def __init__(self, events: list) -> None:
        self.objects: dict[str, dict] = {UPLOAD_KEY: {"ETag": ETAG, "ContentLength": 5_000_000}}
        self.events = events
        self.calls: list[tuple[str, dict]] = []
        self.downloads: list[tuple[str, str]] = []
        self.on_head = None  # callable(key) — 처리 중 원본 교체 재현용
        self.deny_copy_prefix: str | None = None

    def head_object(self, *, Bucket, Key):
        self.calls.append(("head_object", {"Bucket": Bucket, "Key": Key}))
        self.events.append(("head_object", Key))
        if self.on_head is not None:
            self.on_head(Key)
        obj = self.objects.get(Key)
        if obj is None:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return {"ETag": obj["ETag"], "ContentLength": obj["ContentLength"]}

    def copy_object(self, *, Bucket, CopySource, Key, **kw):
        self.calls.append(("copy_object", {"Bucket": Bucket, "CopySource": CopySource, "Key": Key, **kw}))
        self.events.append(("copy_object", Key))
        if self.deny_copy_prefix and Key.startswith(self.deny_copy_prefix):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "CopyObject")
        src = self.objects[CopySource["Key"]]
        if "CopySourceIfMatch" in kw and kw["CopySourceIfMatch"] != src["ETag"]:
            raise ClientError(
                {"Error": {"Code": "PreconditionFailed", "Message": "pre-condition did not hold"}},
                "CopyObject",
            )
        self.objects[Key] = dict(src)
        return {"CopyObjectResult": {"ETag": src["ETag"]}}

    def download_file(self, bucket, key, dest):
        self.calls.append(("download_file", {"Bucket": bucket, "Key": key}))
        self.events.append(("download_file", key))
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "GetObject")
        Path(dest).write_bytes(b"")
        self.downloads.append((key, dest))


class _FakeExtractor:
    target_fps = 9.0

    def __init__(self) -> None:
        self.T = 60
        self.duration: float | None = 6.0
        self.fps: float | None = FPS
        self.extract_calls: list = []

    def probe_duration_sec(self, path):
        return self.duration

    def extract(self, path, start_s=None, end_s=None):
        self.extract_calls.append(end_s)
        return np.zeros((self.T, H, W, 3), dtype=np.uint8)

    def effective_fps_for(self, path):
        return self.fps

    def probe_effective_fps(self, path):
        return self.fps


class _FakePose:
    """`_RTMWNlfCompat` 흉내 — 실제 엔진(DI factory) + 프레임별 mock 추론(1차 추론 T회 정확히)."""

    def __init__(self, outputs) -> None:
        from sunity_shared.analysis.pose_engines.rtmw.rtmw_engine import RTMWPoseEngine
        from sunity_shared.analysis.pose_frame import PoleAxis

        self.inferencer = MagicMock(side_effect=list(outputs))
        self._engine = RTMWPoseEngine.create_with_inferencer(self.inferencer, _MANIFEST)
        self._default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0), confidence_level="low", source="vertical_fallback", frame_index=None
        )


class _Harness:
    def __init__(self, app) -> None:
        self.app = app
        self.events: list = []
        self.s3 = _FakeS3(self.events)
        self.ext = _FakeExtractor()
        self.doc: dict | None = {
            "motionId": REF_ID, "registrationStatus": "processing", "supplierUid": UID,
            "jobId": JOB, "uploadKey": UPLOAD_KEY,
        }
        self.priv: dict | None = {"isCombo": False, "consent": {"training": False, "version": "2026-09-26"}}
        self.calls: dict[str, list] = {
            "angles": [], "active": [], "failed": [], "begin": [], "create_doc": [], "self_check": [], "check": [],
        }
        self.angles_ok = True
        self.active_ok = True
        self.begin_ok = True
        self.create_exc: Exception | None = None
        self.outputs = _frames_133(60)

    def run(self, *, key: str = UPLOAD_KEY, uid: str = UID, ref_id: str = REF_ID, job_id: str = JOB) -> None:
        self.app._POSE_ESTIMATOR = _FakePose(self.outputs)
        self.app._register_reference(BUCKET, key, uid, ref_id, job_id)

    # 편의 접근자
    @property
    def failed_codes(self) -> list[str]:
        return [c[2]["code"] for c in self.calls["failed"]]

    def failed_error(self) -> dict:
        assert len(self.calls["failed"]) == 1, self.calls["failed"]
        return self.calls["failed"][0][2]


@pytest.fixture
def app(monkeypatch):
    for k in ("ROT180_INVERSION_ENABLED", "PR_INVERSION_ENABLED", "S3_USE_ACCELERATE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RUNPOD_ANALYZE_URL", "https://pod.example/analyze")
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "tok")
    sys.modules.pop("app", None)
    import app as mod  # noqa: WPS433

    importlib.reload(mod)
    return mod


@pytest.fixture
def h(app, monkeypatch) -> _Harness:
    h = _Harness(app)
    fa = app.firestore_admin
    monkeypatch.setattr(app, "_ensure_adapters", lambda: None)
    monkeypatch.setattr(app, "_s3", h.s3)
    monkeypatch.setattr(app, "_FRAME_EXTRACTOR", h.ext)
    monkeypatch.setattr(fa, "get_reference_registration", lambda ref_id: h.doc)
    monkeypatch.setattr(fa, "get_reference_registration_private", lambda ref_id: h.priv)

    def set_angles(ref_id, *, job_id, angles_flat, joint_keys, frames, real_fps, keypoint_report, split_angle=None):
        h.calls["angles"].append(
            dict(ref_id=ref_id, job_id=job_id, angles_flat=angles_flat, joint_keys=joint_keys, frames=frames,
                 real_fps=real_fps, keypoint_report=keypoint_report, split_angle=split_angle)
        )
        h.events.append(("set_reference_angles", ref_id))
        return h.angles_ok

    def set_active(ref_id, job_id, *, video_s3_key, video_etag):
        h.calls["active"].append((ref_id, job_id, video_s3_key, video_etag))
        h.events.append(("set_registration_active", ref_id))
        return h.active_ok

    def set_failed(ref_id, job_id, *, error):
        h.calls["failed"].append((ref_id, job_id, error))
        h.events.append(("set_registration_failed", error.get("code")))
        return True

    def begin(ref_id, *, job_id, analysis_id):
        h.calls["begin"].append((ref_id, job_id, analysis_id))
        h.events.append(("begin_self_check", analysis_id))
        return h.begin_ok

    def create_doc(uid, analysis_id, payload):
        h.calls["create_doc"].append((uid, analysis_id, payload))
        h.events.append(("create_analysis_doc", analysis_id))
        if h.create_exc is not None:
            raise h.create_exc

    def set_self(ref_id, *, status, uid, analysis_id, job_id, score=None):
        h.calls["self_check"].append((ref_id, status, uid, analysis_id, job_id, score))
        h.events.append(("set_reference_self_check", status))
        return True

    monkeypatch.setattr(fa, "set_reference_angles", set_angles)
    monkeypatch.setattr(fa, "set_registration_active", set_active)
    monkeypatch.setattr(fa, "set_registration_failed", set_failed)
    monkeypatch.setattr(fa, "begin_self_check", begin)
    monkeypatch.setattr(fa, "create_analysis_doc", create_doc)
    monkeypatch.setattr(fa, "set_reference_self_check", set_self)

    real_check = app.registration_checks.check_registration

    def spy(person_counts, report, *, n_stand):
        counts = list(person_counts)
        h.calls["check"].append((counts, report, n_stand))
        return real_check(counts, report, n_stand=n_stand)

    monkeypatch.setattr(app.registration_checks, "check_registration", spy)
    return h


def _ops(h: _Harness, name: str) -> list[dict]:
    return [kw for op, kw in h.s3.calls if op == name]


# ── R9 크기 · R5 복사 · 길이 (디코딩 전) ─────────────────────────────────────────────────


def test_too_large_is_rejected_before_download(h, app):
    h.s3.objects[UPLOAD_KEY]["ContentLength"] = 101 * 1024 * 1024
    h.run()
    err = h.failed_error()
    assert err == {"code": "too_large", "message": app.models.REGISTRATION_ERROR_MESSAGE["too_large"]}
    assert _ops(h, "download_file") == [] and _ops(h, "copy_object") == []
    assert h.calls["angles"] == [] and h.calls["active"] == []


def test_copy_to_v1_with_etag_then_download_from_v1(h):
    """R5 — head(upload) → copy(upload → v1, CopySourceIfMatch) → head(v1, ETag 동일) → download(v1, upload 아님)."""
    h.run()
    s3_events = [e for e in h.events if e[0] in ("head_object", "copy_object", "download_file")]
    assert s3_events[:4] == [
        ("head_object", UPLOAD_KEY),
        ("copy_object", V1_KEY),
        ("head_object", V1_KEY),
        ("download_file", V1_KEY),
    ]
    copy = _ops(h, "copy_object")[0]
    assert copy["CopySource"] == {"Bucket": BUCKET, "Key": UPLOAD_KEY}
    assert copy["CopySourceIfMatch"] == ETAG
    assert copy["MetadataDirective"] == "COPY"
    assert h.s3.downloads[0][0] == V1_KEY
    assert h.failed_codes == []


def test_source_replaced_during_processing_is_server_error(h, app):
    """copy_object PreconditionFailed(처리 중 원본 교체) → server_error, angles 0."""
    def swap(key):
        if key == UPLOAD_KEY:
            h.s3.objects[UPLOAD_KEY]["ETag"] = '"e2"'

    h.s3.on_head = swap
    h.run()
    assert h.failed_codes == ["server_error"]
    assert h.failed_error()["message"] == app.models.REGISTRATION_ERROR_MESSAGE["server_error"]
    assert V1_KEY not in h.s3.objects
    assert _ops(h, "download_file") == []
    assert h.calls["angles"] == [] and h.calls["active"] == []


def test_v1_copy_access_denied_is_server_error(h):
    """T-38-07-7 — Pod 자격증명이 reference/* PutObject 를 거부하면 등록은 server_error 로 남는다."""
    h.s3.deny_copy_prefix = "reference/"
    h.run()
    assert h.failed_codes == ["server_error"]
    assert _ops(h, "download_file") == [] and h.calls["angles"] == []


@pytest.mark.parametrize("duration, code", [(35.0, "too_long"), (3.0, "too_short")])
def test_duration_rejected_before_extract(h, app, duration, code):
    h.ext.duration = duration
    h.run()
    assert h.failed_error() == {"code": code, "message": app.models.REGISTRATION_ERROR_MESSAGE[code]}
    assert h.ext.extract_calls == []
    assert h.calls["angles"] == []


def test_combo_limit_is_60(h):
    h.priv = {"isCombo": True, "consent": {"training": True}}
    h.ext.duration = 35.0
    h.ext.T = 350
    h.outputs = _frames_133(350)
    h.run()
    assert h.failed_codes == [] and len(h.calls["active"]) == 1
    # 65초는 콤보도 초과.
    h2_ext = h.ext
    h2_ext.duration = 65.0
    h.calls["failed"].clear()
    h.outputs = _frames_133(350)
    h.run()
    assert h.failed_codes == ["too_long"]


def test_probe_none_caps_extract_and_rechecks_length(h):
    """메타를 못 읽으면 extract(end_s=상한+1.0) 캡 뒤 len(frames)/real_fps 로 다시 검사(R9 2차 방어)."""
    h.ext.duration = None
    h.ext.T = 350
    h.outputs = _frames_133(350)
    h.run()
    assert h.ext.extract_calls == [31.0]
    assert h.failed_codes == ["too_long"]
    assert h.calls["angles"] == []


def test_probe_none_combo_cap_is_61(h):
    h.priv = {"isCombo": True, "consent": {"training": False}}
    h.ext.duration = None
    h.run()
    assert h.ext.extract_calls == [61.0]
    assert h.failed_codes == []


def test_zero_frames_is_server_error_not_no_human(h):
    """Pitfall 7 — T == 0 은 NoHumanError 가 아니다."""
    h.ext.T = 0
    h.outputs = []
    h.run()
    assert h.failed_codes == ["server_error"]
    assert h.calls["check"] == []


# ── 실패 4형 (합성 입력, 순서는 38-05 소유 · no_human 만 앞) ─────────────────────────────


def test_no_human_maps_engine_error(h, app):
    h.outputs = _frames_133(60, n_people=0)
    h.run()
    assert h.failed_error() == {
        "code": "no_human",
        "message": app.models.ERROR_MESSAGE[app.models.ERR_NO_HUMAN],
    }
    assert h.calls["check"] == [] and h.calls["angles"] == []


def test_low_confidence_ankles_with_korean_labels_beats_floor_violation(h, app):
    """R6 — 발목 conf 0.2 면 바닥 위반 형상이어도 low_confidence 이고 joints 는 한국어 라벨."""
    h.outputs = _frames_133(60, ankle_conf=0.2, ankle_stand_y=0.6, ankle_window_y=0.85)
    h.run()
    err = h.failed_error()
    assert err["code"] == "low_confidence"
    assert err["joints"] == ["왼쪽 발목", "오른쪽 발목"]
    assert "잘 안 보인 부위: 왼쪽 발목 · 오른쪽 발목" in err["message"]
    assert "{joints}" not in err["message"]
    assert h.calls["angles"] == [] and h.calls["active"] == []


def test_multiple_people(h, app):
    h.outputs = _frames_133(60, n_people=2)
    h.run()
    assert h.failed_error() == {
        "code": "multiple_people",
        "message": app.models.REGISTRATION_ERROR_MESSAGE["multiple_people"],
    }
    assert h.calls["check"][0][0] == [2] * 60


def test_no_standing_start_floor_violation(h, app):
    """서 있는 10프레임 발목이 창 발목보다 위(바닥이 공중에서 잡힘) → no_standing_start."""
    h.outputs = _frames_133(60, ankle_stand_y=0.6, ankle_window_y=0.85)
    h.run()
    assert h.failed_error() == {
        "code": "no_standing_start",
        "message": app.models.REGISTRATION_ERROR_MESSAGE["no_standing_start"],
    }
    assert h.calls["angles"] == []


# ── happy path — R1 · 차단 1 · 순서 · 자기 재현성 R8 ─────────────────────────────────────


def test_max_split_unpacking_contract():
    from sunity_shared.analysis.features import max_split

    assert max_split(np.array([20.0, 90.0, 70.0])) == (90.0, 1)


def test_happy_path_writes_angles_active_and_triggers_self_check(h, app):
    from sunity_shared.analysis import skeleton
    from sunity_shared.s3keys import build_upload_key

    h.run()
    assert h.failed_codes == []

    # 판정 입력 — 사람 수 T개 · keypointReport 는 camelCase dict · n_stand = 1.0초 × 10fps.
    assert len(h.calls["check"]) == 1
    counts, report, n_stand = h.calls["check"][0]
    assert counts == [1] * 60 and n_stand == 10
    assert isinstance(report, dict)
    assert len(report["joints"]) == 12
    assert report["frames"] == 60
    assert "axisData" in report and "axisMask" in report
    assert "axis_data" not in report

    # angles — 기준 11개와 같은 함수 순서의 산출, 소수 2자리, NaN 0.
    assert len(h.calls["angles"]) == 1
    a = h.calls["angles"][0]
    assert a["ref_id"] == REF_ID and a["job_id"] == JOB
    assert a["joint_keys"] == list(skeleton.JOINT_KEYS)
    assert a["frames"] == 60 and len(a["angles_flat"]) == 60 * len(skeleton.JOINT_KEYS)
    assert a["real_fps"] == 10.0
    assert all(np.isfinite(a["angles_flat"]))
    assert all(round(v, 2) == v for v in a["angles_flat"])
    assert a["split_angle"] is None or isinstance(a["split_angle"], float)
    # 차단 1 — check_registration 이 본 것과 같은 객체가 doc 의 referenceKeypointReport 가 된다.
    assert a["keypoint_report"] is report

    # active — v1 키 + upload ETag.
    assert h.calls["active"] == [(REF_ID, JOB, V1_KEY, ETAG)]

    # 자기 재현성 R8 — 선기록 → 분석 doc → v1 에서 uploads/ 로 복사.
    assert len(h.calls["begin"]) == 1
    _, begin_job, new_id = h.calls["begin"][0]
    assert begin_job == JOB and _HEX32.match(new_id)
    assert len(h.calls["create_doc"]) == 1
    uid, doc_id, payload = h.calls["create_doc"][0]
    assert uid == UID and doc_id == new_id
    assert payload["analysisId"] == new_id
    assert payload["mode"] == "mode1"
    assert payload["referenceMotionId"] == REF_ID
    assert payload["status"] == "uploading"
    assert isinstance(payload["fileName"], str) and payload["fileName"]
    assert isinstance(payload["createdAt"], int) and payload["updatedAt"] == payload["createdAt"]
    assert payload["learningOptIn"] is False
    assert payload["selfCheckForReference"] == REF_ID
    assert payload["selfCheckJobId"] == JOB
    copies = _ops(h, "copy_object")
    assert copies[-1]["CopySource"] == {"Bucket": BUCKET, "Key": V1_KEY}
    assert copies[-1]["Key"] == build_upload_key(UID, new_id, "mp4") == f"uploads/{UID}/{new_id}.mp4"

    names = [e[0] for e in h.events]
    order = [
        "set_reference_angles", "set_registration_active", "begin_self_check", "create_analysis_doc",
    ]
    idx = [names.index(n) for n in order]
    assert idx == sorted(idx)
    assert names.index("create_analysis_doc") < len(names) - 1
    assert h.events[-1] == ("copy_object", f"uploads/{UID}/{new_id}.mp4")
    assert h.calls["self_check"] == []


def test_training_consent_flows_to_learning_opt_in(h):
    h.priv = {"isCombo": False, "consent": {"training": True}}
    h.run()
    assert h.calls["create_doc"][0][2]["learningOptIn"] is True


def test_keypoint_report_none_is_server_error_without_verdict(h, app, monkeypatch):
    """차단 1 — build_keypoint_report 가 None 이면 판정을 부르지 않고 server_error."""
    monkeypatch.setattr(app, "build_keypoint_report", lambda *a, **k: None)
    h.run()
    assert h.failed_error() == {
        "code": "server_error",
        "message": app.models.REGISTRATION_ERROR_MESSAGE["server_error"],
    }
    assert h.calls["check"] == []
    assert h.calls["angles"] == [] and h.calls["active"] == []


def test_begin_self_check_false_skips_doc_and_copy(h, caplog):
    caplog.set_level(logging.WARNING)
    h.begin_ok = False
    h.run()
    assert h.calls["active"] == [(REF_ID, JOB, V1_KEY, ETAG)]
    assert h.calls["create_doc"] == []
    assert [c for c in _ops(h, "copy_object") if c["Key"].startswith("uploads/")] == []
    assert h.calls["self_check"] == []
    assert any(r.levelno >= logging.WARNING for r in caplog.records)


def test_uploads_copy_failure_marks_self_check_failed(h):
    h.s3.deny_copy_prefix = "uploads/"
    h.run()
    assert h.calls["active"] == [(REF_ID, JOB, V1_KEY, ETAG)]
    assert len(h.calls["create_doc"]) == 1
    new_id = h.calls["create_doc"][0][1]
    assert h.calls["self_check"] == [(REF_ID, "failed", UID, new_id, JOB, None)]
    assert h.failed_codes == []  # 등록 자체는 active 그대로


def test_analysis_doc_create_failure_marks_self_check_failed(h):
    h.create_exc = RuntimeError("AlreadyExists")
    h.run()
    new_id = h.calls["begin"][0][2]
    assert h.calls["self_check"] == [(REF_ID, "failed", UID, new_id, JOB, None)]
    assert [c for c in _ops(h, "copy_object") if c["Key"].startswith("uploads/")] == []
    assert h.failed_codes == []


def test_stale_job_writes_nothing(h, caplog):
    caplog.set_level(logging.WARNING)
    h.doc = dict(h.doc, jobId="B")
    h.run(job_id=JOB)
    assert h.s3.calls == []
    for name in ("angles", "active", "failed", "begin", "create_doc", "self_check", "check"):
        assert h.calls[name] == [], name
    assert any("stale" in r.getMessage().lower() for r in caplog.records)


def test_missing_doc_raises(h):
    h.doc = None
    with pytest.raises(RuntimeError):
        h.run()
    assert h.s3.calls == []


def test_reput_after_active_is_skipped_and_v1_immutable(h, app, monkeypatch):
    """R5 — 활성화 뒤 같은 URL 로 두 번째 PUT: 파이프라인 입구가 스킵하고 v1 ETag·angles 호출 수 불변."""
    from sunity_shared.s3keys import parse_reference_key

    h.run()
    assert h.s3.objects[V1_KEY]["ETag"] == ETAG and len(h.calls["angles"]) == 1
    # 두 번째 PUT — 새 ETag.
    h.s3.objects[UPLOAD_KEY] = {"ETag": '"e2"', "ContentLength": 7_000_000}
    h.doc = dict(h.doc, registrationStatus="active")
    monkeypatch.setattr(app, "_pod_available", lambda: pytest.fail("스킵 전에 Pod 을 보면 안 된다"))
    monkeypatch.setattr(app.firestore_admin, "set_registration_queued", lambda *a, **k: pytest.fail("writer 0"))
    monkeypatch.setattr(app.firestore_admin, "claim_registration", lambda *a, **k: pytest.fail("writer 0"))
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, parse_reference_key(UPLOAD_KEY)) == "skipped"
    assert h.s3.objects[V1_KEY]["ETag"] == ETAG
    assert len(h.calls["angles"]) == 1


def test_tmp_file_removed_on_success_and_failure(h):
    h.run()
    assert len(h.s3.downloads) == 1
    assert not Path(h.s3.downloads[0][1]).exists()
    # 실패(추출 뒤 too_short) 경로에서도 삭제.
    h.ext.duration = None
    h.ext.T = 30  # 3.0s @10fps
    h.outputs = _frames_133(30)
    h.run()
    assert h.failed_codes == ["too_short"]
    assert len(h.s3.downloads) == 2
    assert not Path(h.s3.downloads[1][1]).exists()


def test_no_scoring_path_called(h, app, monkeypatch):
    """채점 경로(_process · recognizer · build_mode1) 무접촉 — 등록은 어댑터만 빌린다(RESEARCH 안티패턴 1)."""
    monkeypatch.setattr(app, "_process", lambda *a, **k: pytest.fail("_process 호출 금지"))
    monkeypatch.setattr(app.assemble, "build_mode1", lambda *a, **k: pytest.fail("build_mode1 호출 금지"))
    h.run()
    assert h.calls["active"] == [(REF_ID, JOB, V1_KEY, ETAG)]
