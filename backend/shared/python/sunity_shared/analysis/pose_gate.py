"""생성 교정 이미지의 결정론 pose 재측정 게이트 — 리뷰 H-03 백스톱.

왜 필요한가: 생성형 judge 는 "그럴듯한가"를 판정할 뿐 "기하가 맞는가"를 판정하지
못한다. judge 단독으로 통과시키면 목표 각도를 전혀 반영하지 않은 이미지가 노출·적재된다.
그래서 생성물의 목표 관절을 **실제 pose 추정으로 다시 재고** 허용오차와 대조한다.

각도 산출은 `fault_zoom.joint_inner_angle_deg` 단일 출처를 import 한다 (2차 리뷰 B2-01).
자체 arccos 를 재구현하면 "생성 지시(target_deg)"와 "검증 기준(measured_deg)"이 서로 다른
공식을 쓰게 되고, 잘못된 목표에 정확히 맞춘 이미지가 게이트를 통과한다 — 게이트가 스스로를
통과시키는 실패 모드다. 관절 트리플(proximal/vertex/distal)도 `ARROW_JOINT_MAP` 재사용.

좌표계 계약 (31-03 과 동일): pose 응답의 keypoint 는 정규화 [0,1] 이고 x 는 width, y 는
height 로 **각각** 나뉘어 있다. 비정사각 이미지에서 정규화 좌표를 그대로 내각에 넣으면
종횡비만큼 각도가 왜곡되므로, 서버가 돌려준 width/height 를 곱해 등방(px) 좌표로 되돌린
뒤에만 `joint_inner_angle_deg` 에 넣는다. width/height 가 없으면 측정을 신뢰할 수 없으므로
통과시키지 않는다.

허용오차 값은 여기서 정하지 않는다 — 호출측(31-09)이 31-13 calibration 채택값을 env 로
주입한다 (3차 H3-02). 이 모듈은 "무엇을 어떻게 재는가"만 고정한다.

decode 방어 (3차 H3-04 + 4차 H4-06): 전송 전 정규화가 31-05 `safe_decode_image` 와 **동일
계약**(format allowlist + MAX_IMAGE_PIXELS + width/height/pixel cap, decode 전/직후 검사)을
따른다. judge 와 pose 중 한쪽만 방어하면 bomb 입력이 방어가 얇은 쪽으로 흘러간다.

fail-closed 원칙 (D-08): 측정이 불가능하거나 불확실한 모든 경우는 **불통과**다. 게이트를
못 돌린 것과 게이트를 통과한 것은 절대 같은 결과가 아니다.
"""

from __future__ import annotations

import base64
import io
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass

from .fault_zoom import ARROW_JOINT_MAP, joint_inner_angle_deg

# ── payload 상한 — runpod_inference/server.py 의 _POSE_IMG_* 와 동일 값 ────────
#
# 서버가 거절할 payload 를 애초에 만들지 않기 위해 측정측이 같은 상한을 안다.
# 값이 갈라지면 "클라이언트는 보냈는데 서버가 413" 이 조용한 unavailable 로 둔갑한다.
POSE_IMG_MAX_B64_CHARS = 12_000_000
POSE_IMG_MAX_DECODED_BYTES = 8_000_000
POSE_IMG_MAX_PIXELS = 16_000_000
POSE_IMG_MAX_EDGE = 4096
POSE_IMG_FORMATS = ("PNG", "JPEG")

# 전송 전 정규화 목표 — 워커가 받은 20MB 급 이미지도 항상 상한 이하로 줄인다.
# pose 추정에 1024px 이상은 이득이 없고, 결정론(LANCZOS 고정)이어야 같은 입력이
# 같은 판정을 낸다.
POSE_NORMALIZE_MAX_EDGE = 1024

# 원본(정규화 전) 바이트 상한. 워커가 벤더에서 받아 보관하는 이미지 허용치(20MB)와
# 같다. 여기에 endpoint 상한(8MB)을 걸면 안 된다 — 정규화가 존재하는 이유가 바로
# "8MB 를 넘는 벤더 산출물을 줄여서 보내는 것"이라, 미리 거부하면 정상 20MB 이미지가
# 측정도 못 해보고 불통과한다. 8MB 는 **재인코딩 후** 만족해야 하는 값이다.
POSE_SOURCE_MAX_BYTES = 20_000_000

# keypoint 신뢰도 하한. 이보다 낮은 관절로 잰 각도는 측정이 아니라 추측이다.
MIN_KEYPOINT_VISIBILITY = 0.3

# 응답 본문 상한 — 악의적/고장난 서버가 무한 스트림을 흘려도 워커가 버티게.
_MAX_RESPONSE_BYTES = 4_000_000

# ── typed reason (models.VISUAL_FAILURE_REASONS 와 lockstep — 테스트가 검증) ──
REASON_UNAVAILABLE = "pose_gate_unavailable"  # 게이트를 돌리지 못함 (전송/서버 계층)
REASON_FAILED = "pose_gate_failed"  # 게이트는 돌았으나 신뢰할 측정이 안 나옴
REASON_NO_PERSON = "no_person"  # 생성물에 사람이 없음 (정상 판정, 종결)


class _NormalizeError(Exception):
    """전송 전 정규화 실패. 서버를 호출하지 않고 즉시 fail-closed 종결한다."""


@dataclass(frozen=True)
class PoseGateResult:
    """게이트 판정 (immutable).

    `passed=True` 는 오직 "정상 측정이 나왔고 허용오차 안이다" 하나뿐이다. 그 외
    모든 경로(불가/실패/미검출)는 `passed=False` + typed `reason` 이다.
    """

    passed: bool
    measured_deg: float | None
    error_deg: float | None
    reason: str | None
    preserved_violation: str | None = None


def derive_pose_url(analyze_url: str) -> str:
    """RUNPOD_ANALYZE_URL → 같은 Pod 의 /pose-image URL.

    Pod proxy 호스트는 재생성마다 바뀌므로 별도 env 를 하나 더 두면 두 값이 어긋난 채
    운영된다(한쪽만 갱신). analyze URL 에서 파생시켜 출처를 하나로 묶는다.
    query/fragment 는 버린다 — 다른 엔드포인트의 파라미터가 따라오면 안 된다.
    """
    parts = urllib.parse.urlsplit(analyze_url)
    if not parts.scheme or not parts.netloc:
        raise ValueError(f"analyze_url 형식 오류 (scheme/host 없음): {analyze_url!r}")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/pose-image", "", ""))


def _normalize_for_pose(image_bytes: bytes) -> str:
    """생성물 bytes → 서버 상한을 항상 만족하는 PNG base64.

    31-05 `safe_decode_image` 와 동일 계약: format allowlist + MAX_IMAGE_PIXELS +
    width/height/pixel cap 을 **decode 전/직후** 검사한다. bomb 형 입력(압축은 작지만
    픽셀이 거대한 PNG)은 여기서 거부되므로 서버를 아예 호출하지 않는다.

    Raises:
        _NormalizeError: 상한 위반 / 미식별 포맷 / bomb.
    """
    from PIL import Image, UnidentifiedImageError

    if not image_bytes:
        raise _NormalizeError("빈 이미지")
    # decode 전 1차 — 워커 보관 허용치를 넘는 것은 애초에 우리 산출물이 아니다.
    if len(image_bytes) > POSE_SOURCE_MAX_BYTES:
        raise _NormalizeError(f"원본 {len(image_bytes)}B > 상한 {POSE_SOURCE_MAX_BYTES}B")

    Image.MAX_IMAGE_PIXELS = POSE_IMG_MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Image.DecompressionBombError as exc:
        raise _NormalizeError(f"decompression bomb: {exc}") from exc
    except UnidentifiedImageError as exc:
        raise _NormalizeError(f"미식별 이미지: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - 손상 파일도 전부 fail-closed
        raise _NormalizeError(f"open 실패: {exc}") from exc

    # decode 직후 2차 — PIL 이 경고만 내는 MAX~2*MAX 픽셀 구간을 명시적으로 닫는다.
    fmt = (img.format or "").upper()
    if fmt not in POSE_IMG_FORMATS:
        raise _NormalizeError(f"허용 포맷 아님: {fmt or 'unknown'}")
    width, height = int(img.width), int(img.height)
    if width <= 0 or height <= 0:
        raise _NormalizeError(f"잘못된 크기: {width}x{height}")
    if max(width, height) > POSE_IMG_MAX_EDGE or width * height > POSE_IMG_MAX_PIXELS:
        raise _NormalizeError(f"픽셀 상한 초과: {width}x{height}")

    try:
        img = img.convert("RGB")
        longest = max(width, height)
        if longest > POSE_NORMALIZE_MAX_EDGE:
            # 종횡비 유지 — W/H 를 같은 배율로 줄여야 서버가 돌려준 좌표를 px 로
            # 되돌렸을 때 등방성이 유지된다.
            scale = POSE_NORMALIZE_MAX_EDGE / float(longest)
            img = img.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
    except Exception as exc:  # noqa: BLE001 - 재인코딩 실패도 fail-closed
        raise _NormalizeError(f"정규화 실패: {exc}") from exc

    payload = buf.getvalue()
    encoded = base64.b64encode(payload).decode("ascii")
    # 서버 계약을 실제로 만족하는지 전송 직전 assert — 정규화가 회귀하면 여기서 걸린다.
    if len(payload) > POSE_IMG_MAX_DECODED_BYTES:
        raise _NormalizeError(f"정규화 후에도 {len(payload)}B — 상한 초과")
    if len(encoded) > POSE_IMG_MAX_B64_CHARS:
        raise _NormalizeError(f"정규화 후에도 b64 {len(encoded)}자 — 상한 초과")
    return encoded


def _post_pose_image(
    pose_url: str, image_b64: str, token: str, timeout_s: float
) -> dict | None:
    """/pose-image 호출. 전송/서버 계층 실패는 None (→ unavailable)."""
    body = json.dumps({"imageB64": image_b64}).encode("utf-8")
    req = urllib.request.Request(
        pose_url,
        data=body,
        headers={"Content-Type": "application/json", "X-RunPod-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            if int(getattr(resp, "status", 200)) != 200:
                return None
            raw = resp.read(_MAX_RESPONSE_BYTES)
    except Exception:  # noqa: BLE001 - HTTPError/URLError/timeout/socket 전부 동일 처리
        return None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return parsed if isinstance(parsed, dict) else None


def _angle_from_payload(
    payload: dict, joint_key: str, width: float, height: float
) -> float | None:
    """응답 keypoint 3점 → 등방 px 내각. 미매핑/결측/저신뢰 시 None."""
    triple = ARROW_JOINT_MAP.get(joint_key)
    if triple is None:
        return None
    keypoints = payload.get("keypoints")
    if not isinstance(keypoints, dict):
        return None

    pts: list[tuple[float, float]] = []
    for name in triple:
        kp = keypoints.get(name)
        if not isinstance(kp, (list, tuple)) or len(kp) < 3:
            return None
        try:
            x, y, vis = float(kp[0]), float(kp[1]), float(kp[2])
        except (TypeError, ValueError):
            return None
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(vis)):
            return None
        if vis < MIN_KEYPOINT_VISIBILITY:
            return None
        # 정규화 → 등방 px (joint_inner_angle_deg 의 입력 계약).
        pts.append((x * width, y * height))

    measured = joint_inner_angle_deg(pts[0], pts[1], pts[2])
    return None if not math.isfinite(measured) else measured


def measure_generated_pose(
    image_bytes: bytes,
    *,
    joint_key: str,
    target_deg: float,
    tolerance_deg: float,
    pose_url: str,
    token: str,
    timeout_s: float = 60.0,
    preserved_targets: Mapping[str, float] | None = None,
    preserve_tolerance_deg: float | None = None,
) -> PoseGateResult:
    """생성 이미지의 목표 관절각을 재측정해 허용오차와 대조한다 (fail-closed).

    Args:
        image_bytes: 생성물 원본 bytes (정규화는 내부에서).
        joint_key: ARROW_JOINT_MAP 의 관절 키.
        target_deg: 31-03 CorrectedPoseTarget.target_deg (생성 지시와 동일 값).
        tolerance_deg: 호출측이 env 로 주입 (display/training 이 서로 다름).
        preserved_targets: 목표 관절 **외** 관절의 원본 각도 (joint_key → deg).
            주면 각 관절이 `preserve_tolerance_deg` 안에 남아 있는지도 검사한다.
            이유: 실측 스모크에서 지배적 실패 모드가 "목표 관절은 맞췄는데 나머지
            포즈를 통째로 새로 그린" 산출물이었다. 목표 관절만 보는 게이트는 이걸
            통과시킨다 — 교정이 아니라 다른 사람 사진이 되는데도.
        preserve_tolerance_deg: 위 검사의 허용오차. preserved_targets 를 줬는데
            이 값이 없으면 검사 기준이 없는 것이므로 통과시키지 않는다.

    Returns:
        PoseGateResult. `passed=True` 는 정상 측정 + 허용오차 내에서만.
    """
    if joint_key not in ARROW_JOINT_MAP:
        # 네트워크를 태우기 전에 거른다 — 잴 수 없는 관절이다.
        return PoseGateResult(False, None, None, REASON_FAILED)
    if not math.isfinite(target_deg) or not math.isfinite(tolerance_deg) or tolerance_deg < 0:
        return PoseGateResult(False, None, None, REASON_FAILED)
    if preserved_targets and preserve_tolerance_deg is None:
        return PoseGateResult(False, None, None, REASON_FAILED)

    try:
        image_b64 = _normalize_for_pose(image_bytes)
    except _NormalizeError:
        return PoseGateResult(False, None, None, REASON_FAILED)

    payload = _post_pose_image(pose_url, image_b64, token, timeout_s)
    if payload is None:
        # 게이트를 못 돌렸다 = 통과가 아니다 (D-08 미노출).
        return PoseGateResult(False, None, None, REASON_UNAVAILABLE)
    if not payload.get("ok"):
        return PoseGateResult(False, None, None, REASON_NO_PERSON)

    try:
        width = float(payload.get("width") or 0.0)
        height = float(payload.get("height") or 0.0)
    except (TypeError, ValueError):
        return PoseGateResult(False, None, None, REASON_FAILED)
    if width <= 0 or height <= 0:
        # 종횡비를 모르면 각도를 신뢰할 수 없다 (31-03 ref_frame_shape 와 같은 규칙).
        return PoseGateResult(False, None, None, REASON_FAILED)

    measured = _angle_from_payload(payload, joint_key, width, height)
    if measured is None:
        return PoseGateResult(False, None, None, REASON_FAILED)

    error_deg = abs(measured - target_deg)

    for other_key, other_deg in (preserved_targets or {}).items():
        if other_key == joint_key:
            continue
        if not math.isfinite(other_deg):
            return PoseGateResult(False, measured, error_deg, REASON_FAILED, other_key)
        other_measured = _angle_from_payload(payload, other_key, width, height)
        if other_measured is None:
            return PoseGateResult(False, measured, error_deg, REASON_FAILED, other_key)
        if abs(other_measured - other_deg) > float(preserve_tolerance_deg):
            # 목표 외 관절이 흔들렸다 = 교정이 아니라 재생성.
            return PoseGateResult(False, measured, error_deg, REASON_FAILED, other_key)

    passed = error_deg <= tolerance_deg
    return PoseGateResult(passed, measured, error_deg, None if passed else REASON_FAILED)
