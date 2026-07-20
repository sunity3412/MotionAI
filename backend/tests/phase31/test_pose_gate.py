"""생성 실루엣의 결정론 pose 게이트 (환각 산출물 차단) — 담당 플랜 31-06.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. urlopen 은 전부 monkeypatch 로 대체하고
호출 payload 를 캡처해 "무엇을 실제로 전송했는가"까지 검증한다.

검증 축 5개:
  1. 각도 정확성 — 정규화 좌표를 등방 px 로 되돌린 뒤 재는가 (비정사각 회귀 포함)
  2. 허용오차 경계 — 인자 주입값 기준 ±0.1도에서 판정이 뒤집히는가
  3. fail-closed — 연결 실패/미검출/저신뢰/불확실이 전부 불통과인가
  4. payload 계약 (H3-04/H4-06) — 20MB 급 정규화 / bomb 은 서버 미호출 거부
  5. provenance (B2-01) — 각도 산출을 fault_zoom 단일 출처에서 가져오는가
"""

from __future__ import annotations

import ast
import base64
import binascii
import inspect
import io
import json
import re
import struct
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from sunity_shared import models
from sunity_shared.analysis import fault_zoom, pose_gate

_URL = "https://pod-1234-8000.proxy.runpod.net/pose-image"
_TOKEN = "test-token"


# ─────────────────────── 헬퍼 ───────────────────────


def _png(width: int, height: int, *, noise: bool = False) -> bytes:
    """실제 PNG 바이트. noise=True 면 비압축성 데이터(용량 큰 산출물 모사)."""
    if noise:
        rng = np.random.default_rng(3106)
        arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    else:
        arr = np.zeros((height, width, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _bomb_png(width: int = 20000, height: int = 20000) -> bytes:
    """IHDR 만 거대한 PNG — 압축 크기는 작지만 decode 시 픽셀이 폭발한다.

    실제로 20000x20000 배열을 만들면 테스트가 1.2GB 를 먹으므로 헤더만 손으로 조립한다.
    PIL 은 open() 시점에 IHDR 로 크기를 읽고 bomb 검사를 하므로 이것으로 충분하다.
    """
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(ihdr))
        + chunk
        + struct.pack(">I", binascii.crc32(chunk) & 0xFFFFFFFF)
    )


def _kp(x: float, y: float, vis: float = 0.9) -> list[float]:
    return [x, y, vis]


def _knee_payload(
    *,
    hip: tuple[float, float],
    knee: tuple[float, float],
    ankle: tuple[float, float],
    width: int,
    height: int,
    vis: float = 0.9,
    extra: dict | None = None,
) -> dict:
    keypoints = {
        "left_hip": _kp(*hip, vis),
        "left_knee": _kp(*knee, vis),
        "left_ankle": _kp(*ankle, vis),
    }
    keypoints.update(extra or {})
    return {"ok": True, "width": width, "height": height, "keypoints": keypoints}


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.status = status
        self._body = body

    def read(self, _n: int = -1) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc) -> bool:
        return False


class _Server:
    """urlopen 대체 + 요청 캡처."""

    def __init__(self) -> None:
        self.payload: dict | None = None
        self.raw_body: bytes | None = None
        self.status = 200
        self.raise_exc: Exception | None = None
        self.calls: list[dict] = []

    def __call__(self, req, timeout=None):  # noqa: ANN001
        self.calls.append(
            {
                "url": req.full_url,
                "headers": dict(req.headers),
                "body": json.loads(req.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        if self.raise_exc is not None:
            raise self.raise_exc
        body = (
            self.raw_body
            if self.raw_body is not None
            else json.dumps(self.payload or {"ok": False}).encode("utf-8")
        )
        return _FakeResponse(body, self.status)


@pytest.fixture
def pose_server(monkeypatch):
    server = _Server()
    monkeypatch.setattr(urllib.request, "urlopen", server)
    return server


def _measure(image: bytes, **kwargs):
    defaults = dict(
        joint_key="left_knee",
        target_deg=90.0,
        tolerance_deg=5.0,
        pose_url=_URL,
        token=_TOKEN,
    )
    defaults.update(kwargs)
    return pose_gate.measure_generated_pose(image, **defaults)


# ─────────────────────── 1. 각도 정확성 ───────────────────────


def test_measures_right_angle(pose_server):
    """정사각 프레임 90도 — 재측정값이 목표와 일치하면 통과."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=600, height=600
    )
    res = _measure(_png(64, 64), target_deg=90.0)
    assert res.passed is True
    assert res.reason is None
    assert res.measured_deg == pytest.approx(90.0, abs=0.5)
    assert res.error_deg == pytest.approx(0.0, abs=0.5)


def test_measures_straight_angle(pose_server):
    """완전 신전 180도 — 사지 신전 판정의 기준선."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.5, 0.7), width=600, height=600
    )
    res = _measure(_png(64, 64), target_deg=180.0)
    assert res.passed is True
    assert res.measured_deg == pytest.approx(180.0, abs=0.5)


def test_denormalizes_with_frame_shape_not_raw_normalized(pose_server):
    """비정사각 회귀 — 정규화 좌표를 그대로 재면 종횡비만큼 각도가 틀어진다.

    같은 3점이 등방 px 에서는 110.56도, 정규화 좌표 직입력이면 126.87도다.
    이 테스트가 후자를 잡지 못하면 게이트가 잘못된 각도로 자신을 통과시킨다
    (31-03 ref_frame_shape 필수화와 같은 실패 모드).
    """
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.2), knee=(0.5, 0.6), ankle=(0.9, 0.9), width=1000, height=500
    )
    res = _measure(_png(64, 64), target_deg=110.556, tolerance_deg=0.5)
    assert res.measured_deg == pytest.approx(110.556, abs=0.05)
    assert abs(res.measured_deg - 126.87) > 1.0
    assert res.passed is True


# ─────────────────────── 2. 허용오차 경계 ───────────────────────


@pytest.mark.parametrize(("tolerance", "expected"), [(9.9, False), (10.1, True)])
def test_tolerance_boundary_is_caller_injected(pose_server, tolerance, expected):
    """오차 10.0도 고정 + 허용오차 ±0.1 로 판정이 뒤집힌다.

    허용오차는 이 모듈이 정하지 않는다 — 31-13 calibration 채택값을 31-09 가 env 로
    주입한다 (H3-02). 하드코딩 임계값이 생기면 calibration 이 무력화된다.
    """
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=600, height=600
    )
    res = _measure(_png(64, 64), target_deg=80.0, tolerance_deg=tolerance)
    assert res.error_deg == pytest.approx(10.0, abs=0.05)
    assert res.passed is expected
    assert res.reason == (None if expected else pose_gate.REASON_FAILED)


def test_negative_tolerance_rejected(pose_server):
    """음수 허용오차는 설정 오류 — 통과시키지 않는다."""
    res = _measure(_png(64, 64), tolerance_deg=-1.0)
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


# ─────────────────────── 3. fail-closed ───────────────────────


def test_connection_failure_is_unavailable(pose_server):
    """Pod 미가용 = 불통과 + 'pose_gate_unavailable' (D-08 미노출).

    게이트를 못 돌린 것과 통과한 것은 절대 같지 않다.
    """
    pose_server.raise_exc = urllib.error.URLError("connection refused")
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_UNAVAILABLE
    assert res.measured_deg is None


def test_timeout_is_unavailable(pose_server):
    pose_server.raise_exc = TimeoutError("read timed out")
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_UNAVAILABLE


def test_http_error_is_unavailable(pose_server):
    pose_server.raise_exc = urllib.error.HTTPError(_URL, 503, "unavailable", {}, None)
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_UNAVAILABLE


def test_malformed_response_body_is_unavailable(pose_server):
    """JSON 이 아닌 응답 = 서버 계층 이상 → unavailable (역시 불통과)."""
    pose_server.raw_body = b"<html>502 bad gateway</html>"
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_UNAVAILABLE


def test_no_person_is_typed_and_not_passed(pose_server):
    """생성물에 사람이 없음 — 정상 판정이지만 통과는 아니다."""
    pose_server.payload = {"ok": False, "error": "no_person", "width": 600, "height": 600}
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_NO_PERSON


def test_low_confidence_keypoint_fails(pose_server):
    """저신뢰 관절로 잰 각도는 측정이 아니라 추측 — 통과시키지 않는다."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=600, height=600, vis=0.1
    )
    res = _measure(_png(64, 64), target_deg=90.0)
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert res.measured_deg is None


def test_missing_keypoint_fails(pose_server):
    payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=600, height=600
    )
    del payload["keypoints"]["left_ankle"]
    pose_server.payload = payload
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED


def test_missing_frame_shape_fails(pose_server):
    """width/height 미상 = 종횡비 미상 = 각도 신뢰 불가 → 불통과."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=0, height=0
    )
    res = _measure(_png(64, 64))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED


def test_unmapped_joint_fails_without_network(pose_server):
    """잴 수 없는 관절은 네트워크를 태우기 전에 거른다."""
    res = _measure(_png(64, 64), joint_key="left_shoulder")
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


# ─────────── 4. payload 계약 (3차 H3-04 / 4차 H4-06) ───────────


def test_oversized_source_is_normalized_under_endpoint_caps(pose_server):
    """8MB 초과 벤더 산출물이 전송 시점에는 endpoint 상한 이하가 된다.

    원본 자체를 8MB 로 자르면 안 된다 — 정규화가 존재하는 이유가 "큰 산출물을 줄여
    보내는 것"이라, 미리 거부하면 정상 이미지가 측정도 못 해보고 불통과한다.
    """
    big = _png(2000, 1500, noise=True)
    assert len(big) > pose_gate.POSE_IMG_MAX_DECODED_BYTES, "픽스처가 상한을 넘어야 의미"
    assert len(big) <= pose_gate.POSE_SOURCE_MAX_BYTES

    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=1024, height=768
    )
    res = _measure(big, target_deg=90.0)
    assert res.passed is True

    sent = pose_server.calls[0]["body"]["imageB64"]
    assert len(sent) <= pose_gate.POSE_IMG_MAX_B64_CHARS
    assert len(base64.b64decode(sent)) <= pose_gate.POSE_IMG_MAX_DECODED_BYTES


def test_normalized_payload_respects_max_edge(pose_server):
    """전송 이미지의 최대 변이 1024 이하 + 종횡비 유지."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=1024, height=512
    )
    _measure(_png(2048, 1024))
    sent = base64.b64decode(pose_server.calls[0]["body"]["imageB64"])
    img = Image.open(io.BytesIO(sent))
    assert max(img.size) <= pose_gate.POSE_NORMALIZE_MAX_EDGE
    assert img.size == (1024, 512)  # 종횡비 2:1 유지
    assert img.format == "PNG"


def test_decompression_bomb_rejected_without_server_call(pose_server):
    """대해상도 소용량 bomb 은 decode 단계에서 거부 — 서버 미호출 (H4-06).

    judge(31-05)와 같은 계약이다. 한쪽만 방어하면 bomb 이 얇은 쪽으로 흘러간다.
    """
    res = _measure(_bomb_png())
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == [], "bomb 은 서버에 도달하면 안 된다"


def test_oversized_dimensions_rejected_without_server_call(pose_server):
    """변 상한(4096) 초과도 decode 직후 거부 — bomb 예외에 걸리지 않는 구간."""
    res = _measure(_bomb_png(width=5000, height=1000))
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


def test_source_over_worker_allowance_rejected(pose_server):
    """워커 보관 허용치(20MB) 초과는 우리 산출물이 아니다 — 서버 미호출."""
    res = _measure(b"\x89PNG\r\n\x1a\n" + b"\x00" * pose_gate.POSE_SOURCE_MAX_BYTES)
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


def test_non_allowlisted_format_rejected(pose_server):
    """포맷은 확장자가 아니라 실제 컨테이너로 판정 — GIF 는 거부."""
    buf = io.BytesIO()
    Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(buf, format="GIF")
    res = _measure(buf.getvalue())
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


def test_garbage_bytes_rejected(pose_server):
    res = _measure(b"not an image at all")
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


def test_request_carries_auth_header(pose_server):
    """기존 X-RunPod-Token 인증 재사용 — 신규 인증 체계 0."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3), knee=(0.5, 0.5), ankle=(0.7, 0.5), width=600, height=600
    )
    _measure(_png(64, 64), timeout_s=12.0)
    call = pose_server.calls[0]
    headers = {k.lower(): v for k, v in call["headers"].items()}
    assert headers["x-runpod-token"] == _TOKEN
    assert call["url"] == _URL
    assert call["timeout"] == 12.0


# ─────────── 5. 전체 포즈 재생성 차단 + provenance ───────────


def test_whole_pose_regeneration_fails_even_when_target_joint_correct(pose_server):
    """목표 관절만 맞추고 나머지를 새로 그린 산출물은 불통과.

    실측 스모크의 지배적 실패 모드다 — 모델이 포즈를 통째로 다시 그리면서 목표 관절만
    우연히 맞는다. 목표 관절만 보는 게이트는 이걸 통과시킨다(교정이 아니라 다른 사진인데도).
    """
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3),
        knee=(0.5, 0.5),
        ankle=(0.7, 0.5),
        width=600,
        height=600,
        extra={
            # 원본에서 180도였던 오른 무릎이 90도로 바뀌었다.
            "right_hip": _kp(0.3, 0.3),
            "right_knee": _kp(0.3, 0.5),
            "right_ankle": _kp(0.1, 0.5),
        },
    )
    res = _measure(
        _png(64, 64),
        target_deg=90.0,
        preserved_targets={"right_knee": 180.0},
        preserve_tolerance_deg=8.0,
    )
    assert res.measured_deg == pytest.approx(90.0, abs=0.5), "목표 관절 자체는 맞다"
    assert res.passed is False, "그래도 통과시키면 안 된다"
    assert res.preserved_violation == "right_knee"


def test_preserved_joints_within_tolerance_still_passes(pose_server):
    """나머지 포즈가 보존됐으면 정상 통과 — 게이트가 과하게 막지 않는다."""
    pose_server.payload = _knee_payload(
        hip=(0.5, 0.3),
        knee=(0.5, 0.5),
        ankle=(0.7, 0.5),
        width=600,
        height=600,
        extra={
            "right_hip": _kp(0.3, 0.3),
            "right_knee": _kp(0.3, 0.5),
            "right_ankle": _kp(0.3, 0.7),
        },
    )
    res = _measure(
        _png(64, 64),
        target_deg=90.0,
        preserved_targets={"right_knee": 180.0},
        preserve_tolerance_deg=8.0,
    )
    assert res.passed is True
    assert res.preserved_violation is None


def test_preserved_targets_without_tolerance_rejected(pose_server):
    """기준 없는 검사는 검사가 아니다 — 통과시키지 않는다."""
    res = _measure(_png(64, 64), preserved_targets={"right_knee": 180.0})
    assert res.passed is False
    assert res.reason == pose_gate.REASON_FAILED
    assert pose_server.calls == []


def test_angle_math_is_single_source(pose_server):
    """B2-01 — 각도 산출을 fault_zoom 에서 import 하고 자체 재구현하지 않는다.

    이원화되면 생성 지시(target_deg)와 검증 기준(measured_deg)이 갈라져, 잘못된 목표에
    정확히 맞춘 이미지가 게이트를 통과한다.
    """
    assert pose_gate.joint_inner_angle_deg is fault_zoom.joint_inner_angle_deg
    assert pose_gate.ARROW_JOINT_MAP is fault_zoom.ARROW_JOINT_MAP

    # 문자열 검색이 아니라 AST 로 **실제 호출**만 본다 — docstring 이 arccos 를
    # 설명한다는 이유로 걸리면 테스트가 주석 검열기가 되고, 정작 진짜 재구현은
    # 변수명만 바꿔도 빠져나간다.
    tree = ast.parse(inspect.getsource(pose_gate))
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute):
                called.add(fn.attr)
            elif isinstance(fn, ast.Name):
                called.add(fn.id)
    for banned in ("acos", "arccos", "atan2", "arctan2"):
        assert banned not in called, f"자체 각도 재구현 금지: {banned}() 호출"
    assert "joint_inner_angle_deg" in called, "단일 출처 함수를 실제로 호출해야 한다"


def test_no_scoring_module_imports():
    """게이트는 display 전용 — 채점 모듈에 손대지 않는다 (점수 반영 금지 invariant)."""
    src = inspect.getsource(pose_gate)
    for banned in ("dimensions", "kismam", "assemble", "firestore_admin"):
        assert banned not in src, f"채점/저장 모듈 참조 금지: {banned}"


def test_reasons_are_lockstep_with_models():
    """typed reason 이 31-02 계약과 어긋나면 워커가 저장 못 하는 사유를 만든다."""
    assert pose_gate.REASON_FAILED in models.VISUAL_FAILURE_REASONS
    assert pose_gate.REASON_UNAVAILABLE in models.VISUAL_FAILURE_REASONS


def test_caps_match_pod_endpoint_contract():
    """측정측 상한이 server.py 의 _POSE_IMG_* 와 값이 같아야 한다.

    갈라지면 "보냈는데 413" 이 조용한 unavailable 로 둔갑한다.
    """
    src = (
        Path(__file__).resolve().parents[2] / "runpod_inference" / "server.py"
    ).read_text(encoding="utf-8")

    def const(name: str) -> int:
        m = re.search(rf"^{name} = ([\d_]+)$", src, re.MULTILINE)
        assert m, f"{name} 선언을 server.py 에서 찾지 못함"
        return int(m.group(1).replace("_", ""))

    assert const("_POSE_IMG_MAX_B64_CHARS") == pose_gate.POSE_IMG_MAX_B64_CHARS
    assert const("_POSE_IMG_MAX_DECODED_BYTES") == pose_gate.POSE_IMG_MAX_DECODED_BYTES
    assert const("_POSE_IMG_MAX_PIXELS") == pose_gate.POSE_IMG_MAX_PIXELS
    assert const("_POSE_IMG_MAX_EDGE") == pose_gate.POSE_IMG_MAX_EDGE


# ─────────────────────── derive_pose_url ───────────────────────


@pytest.mark.parametrize(
    ("analyze_url", "expected"),
    [
        (
            "https://pod-1234-8000.proxy.runpod.net/analyze",
            "https://pod-1234-8000.proxy.runpod.net/pose-image",
        ),
        ("http://localhost:8000/analyze", "http://localhost:8000/pose-image"),
        # query/fragment 는 버린다 — 다른 엔드포인트 파라미터가 따라오면 안 된다.
        ("https://h.example/analyze?x=1#f", "https://h.example/pose-image"),
    ],
)
def test_derive_pose_url(analyze_url, expected):
    assert pose_gate.derive_pose_url(analyze_url) == expected


def test_derive_pose_url_rejects_malformed():
    """env 오설정은 조용히 넘기지 않는다 — 기동 시점에 크게 실패하는 편이 낫다."""
    with pytest.raises(ValueError):
        pose_gate.derive_pose_url("")
    with pytest.raises(ValueError):
        pose_gate.derive_pose_url("/analyze")


def test_scaffold_fake_clock_alive(fake_clock):
    """공용 스캐폴드 생존 확인 (31-02 conftest 계약)."""
    start = fake_clock()
    assert fake_clock.advance(1000) == start + 1000
