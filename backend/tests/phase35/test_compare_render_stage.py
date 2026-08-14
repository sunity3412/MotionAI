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
  6. 발굴 discovery 조달 + discover mp3 회수 (quick-260814-ghs). **대상 층 = 운영
     스테이지**(`_run_deferred_compare_render`)가 렌더러에 무엇을 넘기는가 —
     build_timeline 주입 레이어 자체는 test_discovery_freeze 소유(같은 층 재작성
     금지). 결함 요지: `result.discovery` 는 Firestore 단일 field-path 부분 갱신
     이라 in-memory result 에 없고, 스테이지가 그대로 doc_like 를 조립하면 발굴
     정지가 **freeze 도 excluded 행도 안 남기고 조용히 소실**된다(coachAudio 가
     이미 당한 계열 결함). 이 섹션은 조달·회수·회계 + 네 실패 경로의 흔적을 못박는다.

pipeline app.py 는 파일 경로 spec 로드(고유 모듈명) — tests/pipeline 'app' 충돌 회피.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

from sunity_shared import firestore_admin, models
from sunity_shared.analysis import compare_align, compare_render, compare_verify
from sunity_shared.s3keys import build_discover_audio_key, build_rendered_compare_key

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


# ══════ 운영 경로 진품 조인 (Phase 34 Pod 스윕 실측 수리 — H4 전건 FAIL) ══════


def test_doc_like_carries_coach_audio_so_rig_h4_joins(
    papp, rc_updates, stage_env, monkeypatch
):
    """스테이지가 render 에 넘기는 doc 에 **이 분석의 coachAudio** 가 실린다.

    회귀 근거(실측): `_run_deferred_coach_audio` 는 Firestore `result.coachAudio`
    단일 field-path 만 부분 갱신하고 in-memory result 에는 싣지 않는다. 스테이지가
    result 를 그대로 조립하면 리그 H4(음성 진품 조인)가 **운영 경로에서만** 전건
    FAIL 한다 — Pod 신선 분석 p34fresh1786192156 에서 r00~r04 5건 "외부 mp3 의심".
    드라이버(rerun_compare_stage)는 Firestore doc 을 읽어 넘기므로 이 결함을
    드러내지 못했다 (승인은 생산 경로에 붙어야 한다는 원칙의 실사례).

    이 테스트는 mock verify 를 우회해 **실 authenticity_checks 로 H4 를 직접 판정**한다.
    """
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    captured: dict = {}

    def _capturing_render(doc, user_video, ref_video, audio_dir, workdir, out, **kwargs):
        captured["doc"] = doc
        Path(out).write_bytes(b"\x00fake-mp4")
        return {"outDurationS": 9.0, "expectedFreezes": 1,
                "freezes": [{"rid": "r00", "userSec": 1.0, "refSec": 2.0,
                             "pairSrc": "align", "freezeS": 5.0,
                             "voiceStartOutS": 1.0, "text": "t"}]}

    monkeypatch.setattr(compare_render, "render", _capturing_render)

    papp._run_deferred_compare_render(**stage_env["kwargs"])

    doc = captured["doc"]
    items = ((doc["result"].get("coachAudio") or {}).get("items")) or []
    assert [it.get("recordId") for it in items] == [RECORD_ID], (
        "스테이지가 받은 coach_audio_items 가 doc.result.coachAudio 로 실려야 한다"
    )

    # 실 리그 H4 로 판정 — mock verify 가 가리던 축을 직접 연다.
    h4 = [
        (name, ok, detail)
        for name, ok, detail in compare_verify.authenticity_checks(
            {"outDurationS": 9.0, "expectedFreezes": 1,
             "freezes": [{"rid": "r00", "userSec": 1.0, "refSec": 2.0,
                          "pairSrc": "align", "freezeS": 5.0,
                          "voiceStartOutS": 1.0, "text": "t"}]},
            doc,
        )
        if name.startswith("H4")
    ]
    assert h4 and all(ok for _n, ok, _d in h4), f"H4 FAIL: {h4}"


def test_doc_like_keeps_existing_coach_audio_when_present(
    papp, rc_updates, stage_env, monkeypatch
):
    """result 에 이미 coachAudio 가 있으면(드라이버 경로 등) 덮어쓰지 않는다."""
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    captured: dict = {}

    def _capturing_render(doc, user_video, ref_video, audio_dir, workdir, out, **kwargs):
        captured["doc"] = doc
        Path(out).write_bytes(b"\x00fake-mp4")
        return {"outDurationS": 9.0, "expectedFreezes": 0, "freezes": []}

    monkeypatch.setattr(compare_render, "render", _capturing_render)
    existing = {"items": [{"recordId": RECORD_ID, "key": "results/x/y/z.mp3"}],
                "status": "done"}
    kwargs = {**stage_env["kwargs"],
              "result": {**stage_env["kwargs"]["result"], "coachAudio": existing}}

    papp._run_deferred_compare_render(**kwargs)

    assert captured["doc"]["result"]["coachAudio"] == existing


# ═══ 6. 발굴 discovery 조달 + mp3 회수 (quick-260814-ghs) ═══
#
# 전부 합성 값 — 실좌표/동작명/실 분석 ID 리터럴 0 (di7 규율 승계).
# 조달 소스는 `firestore_admin.get_analysis` monkeypatch 로 심는다: 발굴은 분석
# **사후** belle 채택물이라 in-memory 근거가 원리적으로 없고 Firestore 가 유일
# 진실이다 (coachAudio 처방과 갈리는 지점 — 그쪽은 "방금 합성한" 목록이 있다).

DISC_RID = "r07"  # records 에 없는 신규 rid — 마커 경로 회피 + 신규 발굴 케이스
DISC_JOINT = "left_elbow"  # knee 의 _body_line_viz 는 di7 이 build_timeline 층에서 핀함
DISC_TEXT = "합성 발굴 문장 — 팔꿈치를 곧게 편 채로 버텨 보세요."
DISC_CUE = "목표는 기준 자세예요. 팔꿈치를 곧게 펴 보세요"
DISC_STATUS = "팔꿈치 각도가 기준 자세와 차이가 있어요"

_SILENCE_MP3: bytes | None = None


def _silence_mp3_bytes() -> bytes:
    """실 무음 mp3 1s (ffmpeg anullsrc) — 모듈 레벨 lazy 캐시.

    `compare_render.mp3_duration_s` 는 ffmpeg 출력 파싱이라 가짜 바이트
    (FakeS3 기본값 b"ID3fake")면 RuntimeError 다. 스테이지 층 테스트도 실
    mp3 를 요구한다 (di7 `_silence_mp3` 미러 — 같은 굽기 명령).
    """
    global _SILENCE_MP3
    if _SILENCE_MP3 is None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "silence.mp3"
            subprocess.run(
                [compare_render.FF, "-y", "-loglevel", "error", "-f", "lavfi",
                 "-i", "anullsrc", "-t", "1", str(p)],
                check=True,
            )
            _SILENCE_MP3 = p.read_bytes()
    return _SILENCE_MP3


def _disc_item(**over) -> dict:
    base = {
        "rid": DISC_RID, "joint": DISC_JOINT, "userSec": 3.2, "refSec": 2.9,
        "pairSrc": models.DISCOVERY_PAIR_SRC, "text": DISC_TEXT,
        "mp3Key": build_discover_audio_key(UID, ANALYSIS_ID, DISC_RID, DISC_JOINT),
        "adoptedAt": "2026-01-01",
    }
    base.update(over)
    return base


def _install_discovery_doc(monkeypatch, items: list[dict]) -> None:
    """Firestore 조달 소스 — 수리 구현이 `get_analysis` 위에 얹히는 계약."""

    def _get_analysis(uid, analysis_id):
        return {"result": {"discovery": {"items": [dict(it) for it in items]}}}

    monkeypatch.setattr(firestore_admin, "get_analysis", _get_analysis)


@pytest.fixture
def disc_env(papp, stage_env, monkeypatch):
    """stage_env 위 4겹 — 실 mp3 / 긴 align / cueLine 보강 / 실 build_timeline 계측.

    render 스텁이 **실 build_timeline** 을 호출하므로 이 fixture 는 "운영
    스테이지가 렌더러에 무엇을 넘겼는가"를 재는 계측기다 (mock 이 가리던 층을 연다).
    """
    monkeypatch.delenv("RENDERED_COMPARE_ENABLED", raising=False)
    captured: dict = {}

    # (1) 실 무음 mp3 바이트 — 다운로드 산출물이 mp3_duration_s 를 통과해야 한다.
    fake_s3 = FakeS3(mp3_bytes=_silence_mp3_bytes())
    monkeypatch.setattr(papp, "_s3", fake_s3)

    # (2) align 길이 확장 (90/90 @15fps = 6.0s) — 발굴 item(u3.2/r2.9)이 G 경계
    #     핀(REF_BOUNDARY_PIN_S=0.5s) 안쪽에 들도록. 기본 stage_env align 은
    #     ref 2.67s 라 발굴 rt 가 경계 제외로 떨어져 조달 축을 못 잰다.
    monkeypatch.setattr(
        compare_align, "build_align", lambda *a, **k: _quality_align(tu=90, tr=90)
    )

    # (3) record 에 cueLine/statusLine 보강 — 실 build_timeline 이
    #     coach_audio_speech_text 를 부른다 (없으면 KeyError). 원본 fixture 무접촉.
    kwargs = {**stage_env["kwargs"]}
    result = {**kwargs["result"]}
    breakdown = {**result["deductionBreakdown"]}
    breakdown["records"] = [
        {**rec, "cueLine": DISC_CUE, "statusLine": DISC_STATUS}
        for rec in result["deductionBreakdown"]["records"]
    ]
    result["deductionBreakdown"] = breakdown
    kwargs["result"] = result

    # (4) render → 실 build_timeline 계측 스텁.
    def _timeline_render(doc, user_video, ref_video, audio_dir, workdir, out, **kw):
        align_json = kw.get("align_json")
        captured["doc"] = doc
        captured["align"] = align_json
        _warp, freezes, excluded = compare_render.build_timeline(
            doc, Path(audio_dir), None, align_json, None
        )
        captured["freezes"] = freezes
        captured["excluded"] = excluded
        Path(out).write_bytes(b"\x00fake-mp4")
        report = {
            "outDurationS": 9.0,
            "userDurationS": 9.0,
            "expectedFreezes": len(freezes),
            "freezes": [
                {"rid": f["rid"], "userSec": f["ut"], "refSec": f["rt"],
                 "pairSrc": f["pair_src"], "freezeS": f["dur"],
                 "voiceStartOutS": 1.0, "text": f["text"]}
                for f in freezes
            ],
            "excludedFreezes": excluded,
        }
        captured["report"] = report
        return report

    monkeypatch.setattr(compare_render, "render", _timeline_render)

    def _capturing_verify(mp4, report, workdir, **kw):
        captured["verify_doc"] = kw.get("doc")
        return (True, ["  [PASS] all"])

    monkeypatch.setattr(compare_verify, "verify", _capturing_verify)

    return {"captured": captured, "s3": fake_s3, "kwargs": kwargs,
            "render": _timeline_render}


def _warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_stage_procures_discovery_and_renders_discover_freeze(
    papp, rc_updates, disc_env, monkeypatch
):
    """갭 A+B — 운영 스테이지가 doc discovery 를 조달해 렌더러에 싣고 mp3 를 회수한다."""
    item = _disc_item()
    _install_discovery_doc(monkeypatch, [item])

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    captured = disc_env["captured"]
    # 갭 A — 운영 조립 doc 에 discovery 가 실렸는가 (산출물 직접 확인).
    assert captured["doc"]["result"]["discovery"]["items"] == [item]
    disc = [f for f in captured["freezes"]
            if f["pair_src"] == models.DISCOVERY_PAIR_SRC]
    assert len(disc) == 1
    fz = disc[0]
    assert fz["rid"] == DISC_RID
    assert fz["ut"] == pytest.approx(item["userSec"])
    assert fz["rt"] == pytest.approx(item["refSec"])
    assert fz["text"] == DISC_TEXT
    assert captured["excluded"] == []
    # 갭 B — discover mp3 가 basename 조인 규약대로 audio_dir 로 회수됐는가.
    downloaded = dict(disc_env["s3"].downloads)
    assert item["mp3Key"] in downloaded
    assert Path(downloaded[item["mp3Key"]]).name == (
        f"discover_audio_{DISC_RID}_{DISC_JOINT}.mp3"
    )
    # doc 부착 — 정지 틱에 발굴 rid 가 실린다.
    assert rc_updates and rc_updates[-1]["status"] == "done"
    assert DISC_RID in {f["rid"] for f in rc_updates[-1]["freezes"]}
    # fail-closed 리그(di7 H2/H3/H4 discover 분기)가 운영 조립 doc 를 받아들이는가.
    # record 축은 align 형상 의존이라 대상 밖 — [discover] 항목만 판정.
    disc_checks = [
        (name, ok, detail)
        for name, ok, detail in compare_verify.authenticity_checks(
            captured["report"], captured["doc"], captured["align"]
        )
        if "[discover]" in name
    ]
    assert disc_checks and all(ok for _n, ok, _d in disc_checks), f"{disc_checks}"


def test_stage_without_discovery_no_regression(
    papp, rc_updates, disc_env, monkeypatch
):
    """발굴 없는 절대다수 = 완전 무회귀 (RED 에서도 PASS 여야 판정이 성립한다)."""
    monkeypatch.setattr(
        firestore_admin, "get_analysis", lambda uid, analysis_id: {"result": {}}
    )

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    captured = disc_env["captured"]
    assert {f["rid"] for f in captured["freezes"]} == {"r00"}
    assert captured["excluded"] == []
    assert "discovery" not in captured["doc"]["result"]
    # 여분 S3 GET 0 — coach mp3 1건 정확.
    assert {k for k, _dst in disc_env["s3"].downloads} == {
        disc_env["kwargs"]["coach_audio_items"][0]["key"]
    }
    assert rc_updates and rc_updates[-1]["status"] == "done"


def test_stage_discovery_read_failure_is_fail_open_with_warning(
    papp, rc_updates, disc_env, monkeypatch, caplog
):
    """조달 읽기 실패 = fail-open(렌더 진행) + WARNING 흔적 (침묵 금지)."""

    def _raise(uid, analysis_id):
        raise RuntimeError("firestore read failure (injected)")

    monkeypatch.setattr(firestore_admin, "get_analysis", _raise)
    caplog.set_level(logging.WARNING)

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    assert rc_updates and rc_updates[-1]["status"] == "done"
    warned = _warnings(caplog)
    assert any("discovery" in m for m in warned), warned


def test_stage_malformed_discovery_never_reaches_renderer(
    papp, rc_updates, disc_env, monkeypatch, caplog
):
    """형상 위반 = validator raise → fail-open + WARNING + **렌더러 미도달**(T-ghs-01).

    읽기 실패 축(위)과 같은 except 로 수렴하지만 판정 대상이 다르다 — 이 축은
    오염 payload 가 doc_like 로 새지 않는다(= validator 가 실제로 경유된다)를 잰다.
    """
    bad = _disc_item(pairSrc="align")  # enum 위반 — 사칭 라벨 차단
    _install_discovery_doc(monkeypatch, [bad])
    caplog.set_level(logging.WARNING)

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    captured = disc_env["captured"]
    assert "discovery" not in captured["doc"]["result"]
    assert [f for f in captured["freezes"]
            if f["pair_src"] == models.DISCOVERY_PAIR_SRC] == []
    assert rc_updates and rc_updates[-1]["status"] == "done"
    warned = _warnings(caplog)
    assert any("discovery" in m for m in warned), warned
    # 형상 위반은 S3 GET 도 유발하지 않는다 (검증 통과분만 회수).
    assert {k for k, _dst in disc_env["s3"].downloads} == {
        disc_env["kwargs"]["coach_audio_items"][0]["key"]
    }


def test_stage_discover_mp3_missing_leaves_excluded_row_and_warning(
    papp, rc_updates, disc_env, monkeypatch, caplog
):
    """mp3 회수 실패 = 그 항목만 discover_no_mp3 excluded + WARNING, 전체 렌더 비차단."""
    item = _disc_item()
    _install_discovery_doc(monkeypatch, [item])
    s3 = disc_env["s3"]
    orig_download = s3.download_file

    def _download(bucket, key, dst):
        if "discover_audio" in key:
            raise RuntimeError("S3 404 (injected)")
        return orig_download(bucket, key, dst)

    monkeypatch.setattr(s3, "download_file", _download)
    caplog.set_level(logging.WARNING)

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    captured = disc_env["captured"]
    assert {"rid": DISC_RID, "reason": "discover_no_mp3"} in captured["excluded"]
    assert [f for f in captured["freezes"]
            if f["pair_src"] == models.DISCOVERY_PAIR_SRC] == []
    assert {f["rid"] for f in captured["freezes"]} == {"r00"}  # record freeze 생존
    assert rc_updates and rc_updates[-1]["status"] == "done"
    warned = _warnings(caplog)
    assert any(item["mp3Key"] in m or DISC_RID in m for m in warned), warned


def test_stage_warns_when_procured_discovery_not_rendered(
    papp, rc_updates, disc_env, monkeypatch, caplog
):
    """조달-반영 대조 회계 — 조달분이 렌더에 안 들어가면 반드시 한 줄이 남는다."""
    item = _disc_item()
    _install_discovery_doc(monkeypatch, [item])

    def _dropping_render(doc, user_video, ref_video, audio_dir, workdir, out, **kw):
        report = disc_env["render"](
            doc, user_video, ref_video, audio_dir, workdir, out, **kw
        )
        report["freezes"] = [
            fz for fz in report["freezes"]
            if fz["pairSrc"] != models.DISCOVERY_PAIR_SRC
        ]
        report["expectedFreezes"] = len(report["freezes"])
        return report

    monkeypatch.setattr(compare_render, "render", _dropping_render)
    caplog.set_level(logging.WARNING)

    papp._run_deferred_compare_render(**disc_env["kwargs"])

    warned = _warnings(caplog)
    assert any("discovery" in m and DISC_RID in m for m in warned), warned
    # 회계는 관측이지 차단이 아니다 — 스테이지는 계속 진행해 done.
    assert rc_updates and rc_updates[-1]["status"] == "done"
