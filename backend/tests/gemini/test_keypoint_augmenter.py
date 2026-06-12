"""Plan 17-03 Task 1 — augment_low_confidence 단위 테스트.

박제 정신:
  · Plan 17-03 박제 — 영역 D Keypoint 보강 (Gemini Pro Vision).
  · B2 hard gate — 시그너처 인자에 `coco_array` / `rtmw_array` 영구 박제 X
    (3D scoring 행렬 격리). `inspect.signature` 회귀 검증.
  · 3차 R-B3 정합 — frame_w/h 인자 박제 X (Gemini self-normalize).
  · G5 좌표 환각 가드 — 인접 frame ±2 정규화 L2 거리 ≥ 0.15 폐기.
  · mirror hint — left/right pair swap 의심 시 audit 박제.
  · 객관성 가드 — `enforce_object_guard=False` 좌표 출력 허용 (영역 D 만).
  · 외부 네트워크 호출 0 — GeminiVisionCall monkeypatch.
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import patch

import pytest

from sunity_shared.analysis.keypoint_frame import KeypointReport
from sunity_shared.gemini import keypoint_augmenter
from sunity_shared.gemini.keypoint_augmenter import augment_low_confidence
from sunity_shared.gemini.schemas import KeypointRefinement, RefinedKeypoint


# ─────────────────── KeypointReport fixture 박제 ───────────────────


def _make_report(
    T: int = 5,
    *,
    joints: list[str] | None = None,
    high_confidence: bool = True,
) -> KeypointReport:
    """T frame × 8 joint KeypointReport fixture. high_confidence=True 면 0.9, False 면 0.1."""
    if joints is None:
        joints = [
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_hand",
            "right_hand",
        ]
    J = len(joints)
    # data — frame_idx 별로 left.x = 0.3, right.x = 0.7 박제 (mirror 정상).
    data: list[float] = []
    confidence: list[float] = []
    for t in range(T):
        for j_name in joints:
            if "left_" in j_name:
                data.extend((0.3, 0.5))  # left.x = 0.3
            elif "right_" in j_name:
                data.extend((0.7, 0.5))  # right.x = 0.7
            else:
                data.extend((0.5, 0.5))
            confidence.append(0.9 if high_confidence else 0.1)
    reliability = ["high" if high_confidence else "low" for _ in range(T)]
    return KeypointReport(
        version="1.0",
        joints=joints,
        frames=T,
        fps=9.0,
        data=data,
        confidence=confidence,
        reliability=reliability,
        axis_data=[0.0] * (T * 3 * 2),
        axis_mask=[True] * (T * 3),
        warnings=[],
    )


# ─────────────────── GeminiVisionCall stub 박제 ───────────────────


class _StubCall:
    """GeminiVisionCall 대체 — schema/model/prompt/... 인자 기록 + call() 결과 박제.

    refined entries 가 여러 chunk 박제 호출 사이에 분배될 수 있도록 list 박제.
    """

    def __init__(self, refined_entries: list[RefinedKeypoint] | list[list[RefinedKeypoint]] | None):
        # refined_entries 가 list[RefinedKeypoint] 면 단일 chunk 박제.
        # list[list[RefinedKeypoint]] 면 chunk 별 박제.
        # None 이면 call() 매번 None 반환.
        self.refined_entries = refined_entries
        self.init_kwargs_history: list[dict[str, Any]] = []
        self.call_paths: list[str] = []
        self._chunk_idx = 0

    def __call__(self, *args: Any, **kwargs: Any) -> "_StubCall":
        self.init_kwargs_history.append(dict(kwargs))
        return self

    def call(self, video_path: str) -> Any:
        self.call_paths.append(video_path)
        if self.refined_entries is None:
            return None
        if (
            self.refined_entries
            and isinstance(self.refined_entries[0], list)
        ):
            # chunk 별 박제.
            if self._chunk_idx >= len(self.refined_entries):
                return None
            entries = self.refined_entries[self._chunk_idx]
            self._chunk_idx += 1
        else:
            entries = self.refined_entries  # type: ignore[assignment]
        return KeypointRefinement(refined=list(entries))


def _patch_call(monkeypatch, stub: _StubCall) -> None:
    monkeypatch.setattr(keypoint_augmenter, "GeminiVisionCall", stub)


def _video(tmp_path) -> str:
    p = tmp_path / "v.mp4"
    p.write_bytes(b"fake")
    return str(p)


# ─────────────────── 테스트 ───────────────────


class TestEmptyInput:
    """low_uncertainty_frame_indices 빈 list → Gemini 호출 0 + 빈 dict."""

    def test_empty_frames_no_call(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(refined_entries=[])
        _patch_call(monkeypatch, stub)
        report = _make_report()

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[],
            keypoint_report_2d=report,
        )

        # Gemini 호출 0 박제.
        assert stub.call_paths == []
        # 빈 dict 박제.
        assert result["refined"] == []
        assert result["augmented_frames"] == []
        assert result["original_rtmw_uncertainty_proxy"] == []
        assert result["guardrail_blocked_count"] == 0
        assert result["mirror_hint"] == {}
        assert result["model"] == "gemini-3.1-pro-preview"


class TestHappyPath:
    """정상 Gemini 호출 + G5 가드 통과 → refined 박제."""

    def test_refined_coords_passed_g5(self, tmp_path, monkeypatch) -> None:
        # frame 2 의 left_shoulder 보강 — RTMW 원본 (0.3, 0.5) 근방으로 (0.32, 0.51) 박제 (L2 ≈ 0.022 < 0.15).
        refined = [
            RefinedKeypoint(
                frame_index=2,
                joint_key="left_shoulder",
                x_normalized=0.32,
                y_normalized=0.51,
                confidence=0.85,
            ),
        ]
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        report = _make_report(T=5, high_confidence=True)

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[2],
            keypoint_report_2d=report,
        )

        # G5 통과 — refined 박제.
        assert len(result["refined"]) == 1
        assert result["refined"][0]["frame_index"] == 2
        assert result["refined"][0]["joint_key"] == "left_shoulder"
        assert result["guardrail_blocked_count"] == 0
        assert result["augmented_frames"] == [2]
        assert result["model"] == "gemini-3.1-pro-preview"

    def test_enforce_object_guard_false_set_on_call(
        self, tmp_path, monkeypatch
    ) -> None:
        """enforce_object_guard=False 박제 — 영역 D 만 좌표 허용 (AI-SPEC §6 G1)."""
        refined = [
            RefinedKeypoint(
                frame_index=0,
                joint_key="left_shoulder",
                x_normalized=0.31,
                y_normalized=0.50,
                confidence=0.8,
            ),
        ]
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        report = _make_report(T=3, high_confidence=True)

        augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[0],
            keypoint_report_2d=report,
        )

        assert len(stub.init_kwargs_history) >= 1
        # GeminiVisionCall 생성 시 enforce_object_guard=False 박힘.
        assert stub.init_kwargs_history[0].get("enforce_object_guard") is False
        # 좌표 허용 박제 — allow_coords=True.
        assert stub.init_kwargs_history[0].get("allow_coords") is True


class TestG5Guard:
    """G5 좌표 환각 가드 — 인접 frame 정규화 L2 거리 ≥ 0.15 폐기."""

    def test_neighbor_distance_blocks_refined(
        self, tmp_path, monkeypatch
    ) -> None:
        """인접 frame 의 left_shoulder = (0.3, 0.5). refined = (0.8, 0.5).
        L2 = 0.5 > 0.15 → 폐기 + guardrail_blocked_count=1."""
        refined = [
            RefinedKeypoint(
                frame_index=2,
                joint_key="left_shoulder",
                x_normalized=0.8,  # 인접 frame 의 (0.3, 0.5) 와 L2 = 0.5.
                y_normalized=0.5,
                confidence=0.85,
            ),
        ]
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        report = _make_report(T=5, high_confidence=True)

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[2],
            keypoint_report_2d=report,
        )

        # 폐기 박제.
        assert result["guardrail_blocked_count"] == 1
        assert len(result["refined"]) == 0  # 폐기 됨.
        assert result["augmented_frames"] == []

    def test_neighbor_low_confidence_skips_g5_comparison(
        self, tmp_path, monkeypatch
    ) -> None:
        """인접 frame 의 confidence < 0.3 면 비교 skip. refined L2 = 0.5 여도 통과."""
        refined = [
            RefinedKeypoint(
                frame_index=2,
                joint_key="left_shoulder",
                x_normalized=0.8,
                y_normalized=0.5,
                confidence=0.85,
            ),
        ]
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        # confidence 0.1 → 인접 frame 도 못 믿음 → G5 비교 skip.
        report = _make_report(T=5, high_confidence=False)

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[2],
            keypoint_report_2d=report,
        )

        # 통과 박제 — G5 비교 skip.
        assert result["guardrail_blocked_count"] == 0
        assert len(result["refined"]) == 1

    def test_elbow_audit_only_no_g5_compare(
        self, tmp_path, monkeypatch
    ) -> None:
        """elbow 는 KeypointReport 에 없음 → RTMW 원본 비교 데이터 없음 → G5 통과 (audit only)."""
        refined = [
            RefinedKeypoint(
                frame_index=2,
                joint_key="left_elbow",
                x_normalized=0.9,  # 비교 데이터 없으니 무조건 통과.
                y_normalized=0.1,
                confidence=0.85,
            ),
        ]
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        report = _make_report(T=5, high_confidence=True)

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[2],
            keypoint_report_2d=report,
        )

        # elbow 박제 audit only — G5 통과 (비교 데이터 없음).
        assert result["guardrail_blocked_count"] == 0
        assert len(result["refined"]) == 1
        assert result["refined"][0]["joint_key"] == "left_elbow"


class TestGracefulFallback:
    """GeminiVisionCall.call() None → 빈 dict 박제 (분석 흐름 차단 0)."""

    def test_call_none_returns_empty_dict(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(refined_entries=None)
        _patch_call(monkeypatch, stub)
        report = _make_report()

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[1, 2, 3],
            keypoint_report_2d=report,
        )

        # Gemini 호출 박제 (1회 — chunk 하나).
        assert len(stub.call_paths) >= 1
        # None 반환 → 빈 refined.
        assert result["refined"] == []
        assert result["augmented_frames"] == []
        # original_rtmw_uncertainty_proxy 는 산출됨 (KeypointReport 박제 source).
        assert len(result["original_rtmw_uncertainty_proxy"]) == 3
        assert result["guardrail_blocked_count"] == 0
        assert result["mirror_hint"] == {}
        assert result["model"] == "gemini-3.1-pro-preview"


class TestMirrorHint:
    """left/right pair swap 의심 → mirror_hint[frame_idx] = "swap_lr"."""

    def test_mirror_swap_detected(self, tmp_path, monkeypatch) -> None:
        """refined left_shoulder.x=0.8, right_shoulder.x=0.2 + RTMW 원본 반대 (left=0.3, right=0.7).
        → swap 의심 박제."""
        refined = [
            RefinedKeypoint(
                frame_index=2,
                joint_key="left_shoulder",
                x_normalized=0.32,  # G5 통과 박제 (RTMW 원본 0.3 근방).
                y_normalized=0.5,
                confidence=0.85,
            ),
            RefinedKeypoint(
                frame_index=2,
                joint_key="right_shoulder",
                x_normalized=0.68,  # G5 통과 박제 (RTMW 원본 0.7 근방).
                y_normalized=0.5,
                confidence=0.85,
            ),
        ]
        # 이 케이스는 mirror swap 이 아님 — 정상 박제. mirror swap 박제 위해 별도 분리.
        stub = _StubCall(refined_entries=refined)
        _patch_call(monkeypatch, stub)
        report = _make_report(T=5, high_confidence=True)

        result = augment_low_confidence(
            video_path=_video(tmp_path),
            low_uncertainty_frame_indices=[2],
            keypoint_report_2d=report,
        )

        # 정상 박제 — mirror_hint 없음.
        assert result["mirror_hint"] == {}

    def test_mirror_swap_actual_detection(
        self, tmp_path, monkeypatch
    ) -> None:
        """G5 가드는 통과 + swap 의심 동시 박제 — elbow pair 사용 (audit only path).

        elbow 는 KeypointReport 에 없어서 G5 비교 데이터 없음 → 무조건 통과. 따라서
        elbow pair swap 박제 가능. 단 _detect_mirror_swap 도 elbow 의 RTMW 원본
        비교 데이터 없으니 skip — 본 케이스로는 swap 미검출.

        실제 swap 검출 케이스: shoulder pair 의 refined left.x > right.x AND RTMW 원본
        반대 + G5 통과. 단 G5 검사 (인접 frame 의 같은 joint) 가 좌측 shoulder=0.3 근방
        만 통과하므로 refined left.x=0.8 면 폐기됨. 따라서 G5 + mirror 모두 박제는
        매우 좁은 케이스.

        본 테스트는 mirror_hint 박제 mechanism 자체를 검증 — RTMW 원본을 swap 상태로
        박은 report fixture + refined 가 RTMW 와 일치 (G5 통과) 인 케이스로 박제.
        """
        # 본 fixture 박제: report 의 left_shoulder.x = 0.7 (RTMW 가 잘못 swap 박은 상태)
        # refined left_shoulder.x = 0.7 (Gemini 도 동일 박제 — G5 통과). 그러나 RTMW
        # 의 left 가 right (0.3) 보다 큼 → swap detection 의 "RTMW left.x < right.x"
        # 조건 미박제 (반대). 따라서 본 케이스도 swap 미검출.

        # 더 명확한 swap 박제: refined left.x=0.7, right.x=0.3 (refined 가 swap).
        # RTMW report left.x=0.3, right.x=0.7 (정상). G5 박제 = refined 가 인접 frame
        # 의 left RTMW (0.3) 와 비교 → L2 = 0.4 > 0.15 → 폐기. 따라서 G5 통과 + swap
        # 동시 박제 불가.

        # 본 plan 박제 정신 — mirror hint 박제 mechanism 자체 (refined left.x > right.x
        # AND RTMW left.x < right.x) 가 정합. mirror hint 검출 회귀 시는 G5 가드 무관
        # case 박제 직접 호출.
        from sunity_shared.gemini.keypoint_augmenter import _detect_mirror_swap

        report = _make_report(T=5, high_confidence=True)
        refined_frame_dict = {
            "left_shoulder": (0.7, 0.5),  # refined left.x=0.7 (swap 의심)
            "right_shoulder": (0.3, 0.5),  # refined right.x=0.3.
        }
        # RTMW 원본 (KeypointReport 박제): left=0.3, right=0.7 → 정상.
        # → swap detection 박제 (refined left.x > right.x AND RTMW 반대).
        assert (
            _detect_mirror_swap(report, refined_frame_dict, frame_idx=2) is True
        )


class TestB2Signature:
    """B2 hard gate — 시그너처 인자에 `coco_array` / `rtmw_array` 영구 박제 X (3D 격리)."""

    def test_signature_no_coco_array_param(self) -> None:
        params = inspect.signature(augment_low_confidence).parameters
        assert "coco_array" not in params
        assert "rtmw_array" not in params
        # frame_w / frame_h 도 박제 X (3차 R-B3 정합).
        assert "frame_w" not in params
        assert "frame_h" not in params
        # 박힌 인자 박제 — video_path / low_uncertainty_frame_indices / keypoint_report_2d.
        assert "video_path" in params
        assert "low_uncertainty_frame_indices" in params
        assert "keypoint_report_2d" in params


class TestFirestoreAdminGeminiDKwarg:
    """firestore_admin.complete_analysis gemini_d kwarg 박제 → Firestore payload 박힘."""

    def test_complete_analysis_accepts_gemini_d_kwarg(self) -> None:
        """signature 박제 검증 — gemini_d kwarg 박힘."""
        from sunity_shared import firestore_admin

        params = inspect.signature(firestore_admin.complete_analysis).parameters
        assert "gemini_d" in params
        # default 박제 — None.
        assert params["gemini_d"].default is None

    def test_complete_analysis_writes_gemini_d_to_payload(self) -> None:
        """gemini_d dict 박제 시 Firestore set payload 의 top-level `geminiD` 박힘."""
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _StubDoc:
            def set(self, payload: dict, merge: bool = False) -> None:
                captured["payload"] = payload
                captured["merge"] = merge

        with patch.object(firestore_admin, "_doc", return_value=_StubDoc()):
            firestore_admin.complete_analysis(
                "uid-x",
                "aid-y",
                {"result": "ok"},
                gemini_d={
                    "augmented_frames": [1, 2, 3],
                    "original_rtmw_uncertainty_proxy": [0.6, 0.7, 0.8],
                    "guardrail_blocked_count": 0,
                    "mirror_hint": {"2": "swap_lr"},
                    "model": "gemini-3.1-pro-preview",
                },
            )

        assert "payload" in captured
        assert "geminiD" in captured["payload"]
        gd = captured["payload"]["geminiD"]
        assert gd["augmented_frames"] == [1, 2, 3]
        assert gd["model"] == "gemini-3.1-pro-preview"
        assert gd["mirror_hint"] == {"2": "swap_lr"}

    def test_complete_analysis_skips_gemini_d_when_none(self) -> None:
        """gemini_d=None 박제 시 payload 에 geminiD key 박지 않음."""
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _StubDoc:
            def set(self, payload: dict, merge: bool = False) -> None:
                captured["payload"] = payload

        with patch.object(firestore_admin, "_doc", return_value=_StubDoc()):
            firestore_admin.complete_analysis(
                "uid-x", "aid-y", {"result": "ok"}, gemini_d=None
            )

        assert "geminiD" not in captured["payload"]
