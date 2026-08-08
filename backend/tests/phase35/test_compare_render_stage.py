"""quick-260808-jix — compare_render 사후 스테이지 테스트 (LOCAL ONLY, 실렌더 0).

고정 표면 (phase32 test_coach_audio 서식 미러 — render/verify/S3/firestore 전부 mock):
  1. 게이트 스킵 3종 — env kill-switch / 모드(mode3) / 능력 프로브. 스킵 = doc
     필드 **무접촉** (update 호출 0 — 부재 = 앱 듀얼 플레이어 폴백).
  2. align 실패 → failed 마킹 (doc 리포트 폴백 렌더 금지 — belle 반려 이력).
     Phase 34 수술 ① (quick-260808-r82): tier 프록시 게이트 삭제 → build_align
     성공 직후 align_quality(산출 자체 품질) 게이트 — FAIL = 필드 미기록 스킵,
     tier=trim_only doc 이라도 품질 PASS 면 부착 경로 생존.
  3. 리그 FAIL → S3 업로드·done 부착 0 + failed 마킹 (돌파 ② "전 항목 PASS
     아니면 없음").
  4. 렌더 예외 → failed 마킹. failed write 실패 → 재raise 0 (분석 무훼손).
  5. 성공 경로 — canonical key put_object + done 마킹 + mp3 파일명 계약(r{NN}.mp3).

pipeline app.py 는 파일 경로 spec 로드(고유 모듈명) — tests/pipeline 'app' 충돌 회피.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import compare_align, compare_render, compare_verify
from sunity_shared.s3keys import build_rendered_compare_key

_BACKEND = Path(__file__).resolve().parents[2]

UID = "u1"
ANALYSIS_ID = "a" * 32
KEY = build_rendered_compare_key(UID, ANALYSIS_ID)
RECORD_ID = "r00:angle_vs_reference__right_elbow"
FAIL_PRESERVE_DIR = Path(tempfile.gettempdir()) / f"compare_fail_{ANALYSIS_ID}"


def _pose_row() -> list[list[float]]:
    """개연성 있는 정적 17-keypoint 정규화 좌표 1행 (torso 비퇴화 — pose_feature 안전)."""
    pts = {j: [0.5, 0.5] for j in compare_align.J17}
    pts.update({
        "nose": [0.5, 0.1], "left_eye": [0.48, 0.09], "right_eye": [0.52, 0.09],
        "left_ear": [0.46, 0.1], "right_ear": [0.54, 0.1],
        "left_shoulder": [0.42, 0.25], "right_shoulder": [0.58, 0.25],
        "left_elbow": [0.38, 0.4], "right_elbow": [0.62, 0.4],
        "left_wrist": [0.36, 0.55], "right_wrist": [0.64, 0.55],
        "left_hip": [0.45, 0.55], "right_hip": [0.55, 0.55],
        "left_knee": [0.44, 0.75], "right_knee": [0.56, 0.75],
        "left_ankle": [0.44, 0.92], "right_ankle": [0.56, 0.92],
    })
    return [pts[j] for j in compare_align.J17]


def _quality_align(tu: int = 30, tr: int = 40, conf: float = 0.9) -> dict:
    """align_quality 를 **실제로 통과**하는 합성 align (신포맷 전 필드).

    user/ref 동일 정적 자세 + 고신뢰 → 커버리지 1.0, 자세거리 0 — mock 이 아니라
    실 게이트를 지나게 해 스테이지 테스트가 새 게이트와 함께 산다."""
    row = _pose_row()
    fps = 15.0
    return {
        "fps": fps,
        "userFrames": tu, "refFrames": tr,
        "userKp": [[c for pt in row for c in pt] for _ in range(tu)],
        "refKp": [[c for pt in row for c in pt] for _ in range(tr)],
        "userScore": [[conf] * 17 for _ in range(tu)],
        "refScore": [[conf] * 17 for _ in range(tr)],
        "curveRefSec": [round(min(t / fps, (tr - 1) / fps), 4) for t in range(tu)],
        "pairs": {},
        "joints17": compare_align.J17,
    }


@pytest.fixture(autouse=True)
def _clean_preserved_dir():
    """FAIL 보존 경로 정리 — 테스트 간 오염 방지 (전/후 양쪽)."""
    shutil.rmtree(FAIL_PRESERVE_DIR, ignore_errors=True)
    yield
    shutil.rmtree(FAIL_PRESERVE_DIR, ignore_errors=True)


def _load_module(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def papp():
    return _load_module(
        "pipeline_app_phase35_compare_render",
        _BACKEND / "functions" / "pipeline" / "app.py",
    )


class FakeS3:
    def __init__(self, mp3_bytes: bytes = b"ID3fake"):
        self.downloads: list[tuple[str, str]] = []
        self.puts: list[dict] = []
        self.mp3_bytes = mp3_bytes

    def download_file(self, bucket, key, dst):
        self.downloads.append((key, dst))
        Path(dst).write_bytes(self.mp3_bytes)

    def put_object(self, **kwargs):
        body = kwargs.pop("Body", None)
        if hasattr(body, "read"):
            body.read()
        self.puts.append(kwargs)
        return {}


@pytest.fixture
def rc_updates(monkeypatch):
    """update_analysis_rendered_compare 캡처 — 실 validator 경유."""
    captured: list[dict] = []

    def _update(uid, analysis_id, key, status, freezes=None):
        payload = {"status": status, "key": key}
        if freezes is not None:
            payload["freezes"] = list(freezes)
        firestore_admin._validate_rendered_compare(payload)
        captured.append({"uid": uid, "analysis_id": analysis_id, **payload})

    monkeypatch.setattr(
        firestore_admin, "update_analysis_rendered_compare", _update
    )
    return captured


@pytest.fixture
def stage_env(papp, monkeypatch, tmp_path):
    """성공 경로 기본 배선 — 능력 프로브 ON + 렌더/정렬/리그 mock + FakeS3.

    render mock 은 out 경로에 가짜 mp4 바이트를 실제로 쓴다 (성공 경로의
    put_object Body=open(out) 이 실파일을 요구)."""
    monkeypatch.setattr(papp, "_compare_render_capability", lambda: True)
    fake_s3 = FakeS3()
    monkeypatch.setattr(papp, "_s3", fake_s3)
    # 수술 ① — 스텁 align 은 실 align_quality 게이트를 **실제로 통과**하는 신포맷
    # (mock 아님). 게이트 FAIL 형상은 개별 테스트가 저품질 align 으로 덮어쓴다.
    monkeypatch.setattr(
        compare_align, "build_align", lambda *a, **k: _quality_align()
    )

    def _fake_render(doc, user_video, ref_video, audio_dir, workdir, out, **kwargs):
        Path(out).write_bytes(b"\x00fake-mp4")
        return {"outDurationS": 9.0, "expectedFreezes": 1,
                "freezes": [{"rid": "r00", "userSec": 1.0, "refSec": 2.0,
                             "pairSrc": "align", "freezeS": 5.0,
                             "voiceStartOutS": 1.0, "text": "t"}]}

    monkeypatch.setattr(compare_render, "render", _fake_render)
    monkeypatch.setattr(
        compare_verify, "verify",
        lambda mp4, report, workdir, **kw: (True, ["  [PASS] all"]),
    )

    user_mp4 = tmp_path / "user.mp4"
    ref_mp4 = tmp_path / "ref.mp4"
    user_mp4.write_bytes(b"u")
    ref_mp4.write_bytes(b"r")
    return {
        "s3": fake_s3,
        "kwargs": dict(
            result={
                "deductionBreakdown": {"records": [{"recordId": RECORD_ID,
                                                    "criterion": "angle_vs_reference__right_elbow",
                                                    "atVideoSec": 1.0}]},
                # 방어 2 (tier 게이트) — 성공 경로 기본은 warped (신뢰 정렬).
                "motionAlignment": {"tier": "warped"},
            },
            keypoint_report_dict={"joints": [], "frames": 0, "data": [],
                                  "confidence": [], "fps": 9.0},
            coach_audio_items=[{"recordId": RECORD_ID, "key": f"results/{UID}/{ANALYSIS_ID}/coach_audio_{RECORD_ID}.mp3"}],
            mode=models.MODE_EXPERT,
            uid=UID,
            analysis_id=ANALYSIS_ID,
            bucket="b",
            local_video_path=str(user_mp4),
            reference_local_video_path=str(ref_mp4),
        ),
    }


# ═══════════════════ 1. 게이트 스킵 3종 (doc 필드 무접촉) ═══════════════════


def test_gate_env_kill_switch_skips_without_touching_doc(
    papp, rc_updates, stage_env, monkeypatch
):
    monkeypatch.setenv("RENDERED_COMPARE_ENABLED", "0")
    papp._run_deferred_compare_render(**stage_env["kwargs"])
    assert rc_updates == []  # 스킵 = 필드 무접촉 (failed 마킹도 없음)
    assert stage_env["s3"].puts == []


def test_gate_mode3_skips(papp, rc_updates, stage_env, monkeypatch):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    kwargs = {**stage_env["kwargs"], "mode": models.MODE_SELF}
    papp._run_deferred_compare_render(**kwargs)
    assert rc_updates == []
    assert stage_env["s3"].puts == []


def test_gate_missing_reference_video_skips(papp, rc_updates, stage_env, monkeypatch):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    kwargs = {**stage_env["kwargs"], "reference_local_video_path": None}
    papp._run_deferred_compare_render(**kwargs)
    assert rc_updates == []


def test_gate_capability_probe_skips(papp, rc_updates, stage_env, monkeypatch):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    monkeypatch.setattr(papp, "_compare_render_capability", lambda: False)
    papp._run_deferred_compare_render(**stage_env["kwargs"])
    assert rc_updates == []
    assert stage_env["s3"].puts == []


def test_align_quality_fail_skips_without_field(
    papp, rc_updates, stage_env, monkeypatch
):
    """방어 2 교체 (Phase 34 수술 ①) — align_quality FAIL(저신뢰 스텁 align)이면
    렌더 미시도 + **필드 미기록 스킵** (failed 아님 — 부재가 앱 폴백). 실 게이트
    함수 경유 (mock 0)."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    bad = _quality_align(conf=0.0)  # 전 관절 conf 0 → 커버리지 0 < 0.88 FAIL
    monkeypatch.setattr(compare_align, "build_align", lambda *a, **k: bad)
    render_calls: list = []
    monkeypatch.setattr(
        compare_render, "render", lambda *a, **k: render_calls.append(1)
    )

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    assert render_calls == []  # 게이트가 렌더 앞 — 시도 자체 없음
    assert rc_updates == []  # 필드 무접촉 (failed 마킹도 없음)
    assert stage_env["s3"].puts == []


def test_trim_only_doc_with_quality_pass_attaches(
    papp, rc_updates, stage_env, monkeypatch
):
    """가치 복원 핵심 (수술 ①) — tier=trim_only doc(리포 7 doc 전부 = 종전 게이트
    에선 부착 0)이라도 align_quality PASS 면 부착 경로가 산다."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    kwargs = {**stage_env["kwargs"]}
    result = dict(kwargs["result"])
    result["motionAlignment"] = {"tier": "trim_only"}  # belle doc 127a2a90 실측 형상
    kwargs["result"] = result

    papp._run_deferred_compare_render(**kwargs)

    assert rc_updates and rc_updates[0]["status"] == "done"
    assert len(stage_env["s3"].puts) == 1
    assert stage_env["s3"].puts[0]["Key"] == KEY


def test_all_freezes_excluded_skips_without_field(
    papp, rc_updates, stage_env, monkeypatch
):
    """렌더 대상 freeze 전멸 (제외 회계로 0) = '표현할 것 없음' — 업로드·마킹 0,
    **필드 미기록** (failed 아님). 리그 verify 도 미도달."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    def _fake_render(doc, user_video, ref_video, audio_dir, workdir, out, **kwargs):
        Path(out).write_bytes(b"\x00fake-mp4")
        return {"outDurationS": 1.0, "expectedFreezes": 0, "freezes": [],
                "excludedFreezes": [{"rid": "r00", "reason": "no_mp3"}]}

    monkeypatch.setattr(compare_render, "render", _fake_render)
    verify_calls: list = []
    monkeypatch.setattr(
        compare_verify, "verify",
        lambda *a, **k: verify_calls.append(1) or (True, []),
    )

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    assert rc_updates == []  # 필드 미기록 (done 도 failed 도 아님)
    assert stage_env["s3"].puts == []
    assert verify_calls == []  # 리그 미도달 (표현물 없음)


def test_capability_probe_false_without_rtmlib(papp, monkeypatch):
    """rtmlib import 불가 = 능력 없음 (Lambda CPU 폴백 자동 스킵 — T-35J-04)."""
    monkeypatch.setitem(sys.modules, "rtmlib", None)  # import rtmlib → ImportError
    assert papp._compare_render_capability() is False


def test_capability_probe_requires_weight_files(papp, monkeypatch, tmp_path):
    """rtmlib 은 있어도 가중치 실파일 없으면 False / 둘 다 있으면 True."""
    monkeypatch.setitem(sys.modules, "rtmlib", types.ModuleType("rtmlib"))
    monkeypatch.setenv("YOLOX_ONNX_PATH", str(tmp_path / "absent_det.onnx"))
    monkeypatch.setenv("RTMW_ONNX_PATH", str(tmp_path / "absent_pose.onnx"))
    assert papp._compare_render_capability() is False

    det = tmp_path / "det.onnx"
    pose = tmp_path / "pose.onnx"
    det.write_bytes(b"x")
    pose.write_bytes(b"x")
    monkeypatch.setenv("YOLOX_ONNX_PATH", str(det))
    monkeypatch.setenv("RTMW_ONNX_PATH", str(pose))
    assert papp._compare_render_capability() is True


# ═══════════════════ 2. align 실패 = failed (폴백 렌더 금지) ═══════════════════


def test_align_failure_marks_failed_no_fallback_render(
    papp, rc_updates, stage_env, monkeypatch
):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    def _raise(*_a, **_k):
        raise RuntimeError("align failure (injected)")

    monkeypatch.setattr(compare_align, "build_align", _raise)
    render_calls: list = []
    monkeypatch.setattr(
        compare_render, "render",
        lambda *a, **k: render_calls.append(1),
    )

    papp._run_deferred_compare_render(**stage_env["kwargs"])  # 재raise 0

    assert render_calls == []  # doc 리포트 폴백 렌더 금지 — 렌더 자체 미시도
    assert rc_updates == [
        {"uid": UID, "analysis_id": ANALYSIS_ID, "key": "", "status": "failed"}
    ]
    assert stage_env["s3"].puts == []


# ═══════════════════ 3. 리그 FAIL = 업로드·done 부착 0 ═══════════════════


def test_rig_fail_blocks_upload_and_marks_failed(
    papp, rc_updates, stage_env, monkeypatch
):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    monkeypatch.setattr(
        compare_verify, "verify",
        lambda mp4, report, workdir, **kw: (False, ["  [FAIL] E 저더 user: 반복률=40%"]),
    )

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    assert stage_env["s3"].puts == []  # ALL PASS 아니면 S3 업로드 없음
    assert rc_updates == [
        {"uid": UID, "analysis_id": ANALYSIS_ID, "key": "", "status": "failed"}
    ]
    # 실 E2E 라운드 (2026-08-08) — FAIL 아티팩트 보존: workdir 가 고정 경로로
    # 이동돼 mp4·report·align 이 남는다 (당일 소실로 진단 불가했던 근거의 수리).
    assert FAIL_PRESERVE_DIR.is_dir()
    assert (FAIL_PRESERVE_DIR / "compare.mp4").exists()
    assert (FAIL_PRESERVE_DIR / "report.json").exists()
    assert (FAIL_PRESERVE_DIR / "align.json").exists()


# ═══════════════════ 4. 렌더 예외 / failed write 실패 ═══════════════════


def test_render_exception_marks_failed(papp, rc_updates, stage_env, monkeypatch):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    def _raise(*_a, **_k):
        raise RuntimeError("render failure (injected)")

    monkeypatch.setattr(compare_render, "render", _raise)

    papp._run_deferred_compare_render(**stage_env["kwargs"])  # 재raise 0

    assert rc_updates == [
        {"uid": UID, "analysis_id": ANALYSIS_ID, "key": "", "status": "failed"}
    ]
    assert stage_env["s3"].puts == []
    # 예외 경로도 부분 아티팩트 보존 (align.json 까지는 기록됐다).
    assert FAIL_PRESERVE_DIR.is_dir()
    assert (FAIL_PRESERVE_DIR / "align.json").exists()


def test_failed_write_failure_never_raises(papp, stage_env, monkeypatch):
    """failed 마킹 write 자체가 실패해도 재raise 0 — 분석은 이미 complete."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    def _raise_render(*_a, **_k):
        raise RuntimeError("render failure (injected)")

    monkeypatch.setattr(compare_render, "render", _raise_render)

    def _raise_update(*_a, **_k):
        raise RuntimeError("firestore write failure (injected)")

    monkeypatch.setattr(
        firestore_admin, "update_analysis_rendered_compare", _raise_update
    )

    papp._run_deferred_compare_render(**stage_env["kwargs"])  # 예외 전파 없음


# ═══════════════════ 5. 성공 경로 (canonical key + mp3 파일명 계약) ═══════════════════


def test_success_uploads_canonical_key_and_marks_done(
    papp, rc_updates, stage_env, monkeypatch
):
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    assert len(stage_env["s3"].puts) == 1
    put = stage_env["s3"].puts[0]
    assert put["Key"] == KEY  # s3keys 단일 출처 canonical
    assert put["ContentType"] == "video/mp4"
    # done 마킹 + 정지 틱 데이터 (UI 라운드 — 렌더 리포트 voiceStartOutS 각인).
    assert rc_updates == [
        {"uid": UID, "analysis_id": ANALYSIS_ID, "key": KEY, "status": "done",
         "freezes": [{"rid": "r00", "outSec": 1.0}]}
    ]
    # mp3 회수 파일명 계약 — recordId 콜론 앞 r{NN}.mp3 (build_timeline 이 읽는 이름).
    assert len(stage_env["s3"].downloads) == 1
    _, dst = stage_env["s3"].downloads[0]
    assert dst.endswith("/audio/r00.mp3")
    # done 경로는 현행대로 즉시 정리 — FAIL 보존 경로 미생성 (디스크 누적 0).
    assert not FAIL_PRESERVE_DIR.exists()


def test_success_with_zero_audio_items_still_proceeds(
    papp, rc_updates, stage_env, monkeypatch
):
    """item 0건 = freeze 0 순수 정렬 재생 편 — 스테이지는 진행한다 (리그 C 분기).
    제외 회계 없는 freeze-0 (excludedFreezes 부재) = 전멸 스킵과 구분."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)

    def _fake_render(doc, user_video, ref_video, audio_dir, workdir, out, **kwargs):
        Path(out).write_bytes(b"\x00fake-mp4")
        return {"outDurationS": 1.0, "expectedFreezes": 0, "freezes": []}

    monkeypatch.setattr(compare_render, "render", _fake_render)
    kwargs = {**stage_env["kwargs"], "coach_audio_items": []}

    papp._run_deferred_compare_render(**kwargs)

    assert rc_updates and rc_updates[0]["status"] == "done"
    assert rc_updates[0]["freezes"] == []  # 틱 데이터도 빈 배열로 정직 각인
    assert stage_env["s3"].downloads == []


def test_stage_does_not_touch_scoring_result(papp, rc_updates, stage_env, monkeypatch):
    """채점 무접촉(사후) 회귀 가드 — 스테이지 전/후 result 딥 동등."""
    import copy

    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    result = stage_env["kwargs"]["result"]
    before = copy.deepcopy(result)

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    assert result == before  # renderedCompare 는 doc 부분 갱신으로만
