"""Phase 27 SPD-02 / 27-04 — 세션 핸들 소비처 배선 테스트.

이 파일은 세 wave 태스크가 공유한다:
  · Task 1 — 어댑터 핸들 주입 (scene_finder / moment extractor / coach B) + moment
    extractor self-upload 폴백 누수 fix (외부 리뷰 HIGH-2).
  · Task 2 — vision_scorer veto 핸들 kwargs + still PNG inline 전환.
  · Task 3 — _process 세션 배선 통합 (학생 영상 업로드 분석당 1회).

핵심 계약 (전 태스크 공통):
  · preuploaded_handle 주입 시 File API 업로드/폴링/delete 를 skip 한다 (핸들 소유권 = 세션).
  · 미주입 시 기존 자체 업로드 동작이 보존되고, self-upload 한 핸들은 정확히 1회 delete 된다
    (누수 0 — 20GB 적체 재발 방지).

외부 네트워크 0 — tests/gemini/fake_genai.py 의 FakeFiles/FakeModels 재사용.
"""

from __future__ import annotations

from types import SimpleNamespace

import google.genai as _google_genai
import pytest

from tests.gemini.fake_genai import FakeClient, FakeFiles, FakeModels

_VALID_MOMENT_JSON = (
    '{"moments": [{"moment_key": "hold", "timestamp_seconds": 3.2, '
    '"confidence": 0.9, "description": "홀드 구간"}]}'
)


def _patch_google_genai(
    monkeypatch: pytest.MonkeyPatch,
    *,
    files: FakeFiles | None = None,
    models: FakeModels | None = None,
) -> FakeClient:
    """moment extractor 는 `from google import genai` 를 함수-로컬 import 하므로
    실제 google.genai.Client 를 fake ctor 로 교체한다 (모듈 속성 patch)."""
    fake = FakeClient(files or FakeFiles(), models or FakeModels())

    def _ctor(*, api_key: str) -> FakeClient:  # noqa: ARG001 - 시그니처 박제
        return fake

    monkeypatch.setattr(_google_genai, "Client", _ctor)
    return fake


# ─────────────────── Task 1 — moment extractor (HIGH-2) ───────────────────


class TestMomentExtractorHandleInjection:
    """extract_key_moments / _call_gemini 의 preuploaded_handle 계약 + self-upload 누수 fix."""

    def _extractor(self):
        from sunity_shared.judging.gemini_moment_extractor import GeminiMomentExtractor

        return GeminiMomentExtractor(api_key_loader=lambda: "stub-key")

    def test_m1_injected_handle_skips_upload_poll_delete(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """M1 (HIGH-2): 핸들 공급 → upload/get/delete 전부 0 (세션 소유 핸들 미삭제)."""
        fake = _patch_google_genai(
            monkeypatch,
            models=FakeModels([SimpleNamespace(text=_VALID_MOMENT_JSON)]),
        )
        ext = self._extractor()
        handle = SimpleNamespace(name="files/session-owned-1")

        raw = ext._call_gemini(
            "/tmp/fake.mp4", "power-spin", preuploaded_handle=handle
        )

        assert raw  # generate 결과 raw text 반환
        assert fake.files.upload_calls == 0
        assert fake.files.get_calls == 0
        assert fake.files.delete_calls == 0  # 세션 소유 핸들을 extractor 가 지우지 않음

    def test_m2_self_upload_generate_error_deletes_exactly_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """M2 (HIGH-2): 핸들 미공급 + generate 예외 → 업로드 파일 정확히 1회 delete."""
        fake = _patch_google_genai(
            monkeypatch,
            models=FakeModels([RuntimeError("generate boom")]),
        )
        ext = self._extractor()

        with pytest.raises(RuntimeError):
            ext._call_gemini("/tmp/fake.mp4", "power-spin")

        assert fake.files.upload_calls == 1
        assert fake.files.delete_calls == 1
        assert fake.files.deleted_names == fake.files.uploaded_names

    def test_m2_self_upload_success_deletes_exactly_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """M2 정상 경로: 핸들 미공급 성공 시에도 self-upload 핸들 1회 delete."""
        fake = _patch_google_genai(
            monkeypatch,
            models=FakeModels([SimpleNamespace(text=_VALID_MOMENT_JSON)]),
        )
        ext = self._extractor()

        raw = ext._call_gemini("/tmp/fake.mp4", "power-spin")

        assert raw
        assert fake.files.upload_calls == 1
        assert fake.files.delete_calls == 1
        assert fake.files.deleted_names == fake.files.uploaded_names

    def test_m2_upload_raise_no_delete_and_original_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Warning 1: upload 자체가 raise → 생성된 파일 없음 → delete 미실행, 원 예외 보존."""
        fake = _patch_google_genai(monkeypatch)

        def _raising_upload(*, file, config=None):  # noqa: ARG001
            raise RuntimeError("upload boom")

        monkeypatch.setattr(fake.files, "upload", _raising_upload)
        ext = self._extractor()

        with pytest.raises(RuntimeError, match="upload boom"):
            ext._call_gemini("/tmp/fake.mp4", "power-spin")

        assert fake.files.delete_calls == 0  # 파일 미생성 → delete 대상 없음


# ─────────────────── Task 2 — vision_scorer veto 핸들 + still inline ───────────────────


_VALID_VERDICT_JSON = (
    '{"primary_fault": "없음", "dominant_severity": "none", "differences": []}'
)


def _make_video(tmp_path, name: str) -> str:
    p = tmp_path / name
    p.write_bytes(b"\x00\x01\x02" + name.encode())
    return str(p)


def _make_png(tmp_path, name: str) -> str:
    p = tmp_path / name
    # 최소 PNG signature + 더미 바이트 (inline 은 바이트만 읽으므로 유효 디코드 불필요).
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + name.encode())
    return str(p)


def _patch_vision(monkeypatch):
    """gvs._ensure_client → FakeClient + VisionVetoCache in-memory + time.sleep noop."""
    from sunity_shared.analysis import gemini_vision_scorer as gvs

    files = FakeFiles()
    models = FakeModels([SimpleNamespace(text=_VALID_VERDICT_JSON)] * 12)
    fake = FakeClient(files, models)
    monkeypatch.setattr(gvs, "_ensure_client", lambda: fake)

    store: dict = {}
    monkeypatch.setattr(
        gvs.VisionVetoCache, "_backend_get", lambda self, k: store.get(k), raising=False
    )
    monkeypatch.setattr(
        gvs.VisionVetoCache,
        "_backend_put",
        lambda self, k, v: store.__setitem__(k, v),
        raising=False,
    )
    return gvs, fake


class TestVisionScorerVetoHandles:
    """assess_fault_context_video 세션 핸들 kwargs + still PNG inline 전환."""

    def test_both_handles_skip_upload_and_not_deleted(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test 1: student+reference 핸들 둘 다 제공 → 영상 업로드 0, 주입 핸들 미삭제."""
        gvs, fake = _patch_vision(monkeypatch)
        student = _make_video(tmp_path, "student.mp4")
        reference = _make_video(tmp_path, "reference.mp4")
        h_s = SimpleNamespace(name="files/session-student")
        h_r = SimpleNamespace(name="files/session-reference")

        gvs.assess_fault_context_video(
            student,
            reference,
            part_scopes=["upper_body"],
            preuploaded_student_handle=h_s,
            preuploaded_reference_handle=h_r,
        )

        assert fake.files.upload_calls == 0  # 세션 핸들 재사용 — 영상 업로드 0
        assert fake.files.delete_calls == 0  # 주입 핸들은 세션 소유 — 여기서 미삭제
        assert "files/session-student" not in fake.files.deleted_names
        assert "files/session-reference" not in fake.files.deleted_names

    def test_only_one_handle_treated_as_not_provided(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test 2: 하나만 제공 → 미제공 취급 (기존 자체 업로드 2회 + finally delete 2회)."""
        gvs, fake = _patch_vision(monkeypatch)
        student = _make_video(tmp_path, "student.mp4")
        reference = _make_video(tmp_path, "reference.mp4")

        gvs.assess_fault_context_video(
            student,
            reference,
            part_scopes=["upper_body"],
            preuploaded_student_handle=SimpleNamespace(name="files/session-student"),
            # reference 미제공 → 미제공 취급 (계약 스타일 = 둘 다일 때만 활성).
        )

        assert fake.files.upload_calls == 2  # 자체 업로드 2 (video)
        assert fake.files.delete_calls == 2  # 자체 업로드분 finally delete
        assert fake.files.deleted_names == fake.files.uploaded_names

    def test_still_png_inline_no_image_upload(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """Test 3: still PNG 이 inline Part 로 들어가고 _upload_image 미호출 (image 업로드 0)."""
        from google.genai import types as genai_types

        gvs, fake = _patch_vision(monkeypatch)

        def _fail_upload_image(*a, **k):  # noqa: ARG001
            raise AssertionError("inline 전환 — _upload_image 는 호출되면 안 됨")

        monkeypatch.setattr(gvs, "_upload_image", _fail_upload_image)

        student = _make_video(tmp_path, "student.mp4")
        reference = _make_video(tmp_path, "reference.mp4")
        stu_png = _make_png(tmp_path, "stu.png")
        ref_png = _make_png(tmp_path, "ref.png")

        gvs.assess_fault_context_video(
            student,
            reference,
            part_scopes=["upper_body"],
            still_student_png=stu_png,
            still_reference_png=ref_png,
            still_frame_indices=[3, 5],
        )

        assert fake.files.upload_calls == 2  # video 2 만 (image 업로드 0)
        # inline Part 가 generate contents 에 존재.
        all_contents = [c for call in fake.models.calls for c in call.get("contents", [])]
        assert any(isinstance(c, genai_types.Part) for c in all_contents)


# ─────────────────── Task 3 — _process 세션 통합 (업로드 1회 + 종료 delete) ───────────────────


class TestSessionProcessIntegration:
    """GeminiFileSession 이 여러 소비처의 get_or_upload 를 1회 업로드로 dedupe 하고
    close() 가 세션 업로드분을 정확히 delete 하는지 (파이프라인 _process 배선 계약)."""

    def test_student_upload_once_and_close_deletes(self) -> None:
        from sunity_shared.gemini.file_session import GeminiFileSession

        fake = FakeClient(FakeFiles(), FakeModels())
        session = GeminiFileSession(client_factory=lambda: fake)

        # scene → recognizer → veto → coach B 순으로 같은 학생 영상 경로 get_or_upload.
        h_scene = session.get_or_upload("/tmp/student.mp4")
        h_recog = session.get_or_upload("/tmp/student.mp4")
        h_veto = session.get_or_upload("/tmp/student.mp4")
        h_coach = session.get_or_upload("/tmp/student.mp4")

        # 4 소비처가 동일 핸들 공유 + 업로드 정확히 1회.
        assert h_scene is h_recog is h_veto is h_coach
        assert fake.files.upload_calls == 1
        assert fake.files.delete_calls == 0  # close 전에는 delete 0

        session.close()
        # 종료 일괄 delete = 업로드 수.
        assert fake.files.delete_calls == fake.files.upload_calls == 1
        assert fake.files.deleted_names == fake.files.uploaded_names

    def test_student_and_reference_two_uploads_one_delete_each(self) -> None:
        """학생 ∥ 기준 = 경로별 1회 업로드, close 시 각 1회 delete (veto 학생+기준 공유)."""
        from sunity_shared.gemini.file_session import GeminiFileSession

        fake = FakeClient(FakeFiles(), FakeModels())
        session = GeminiFileSession(client_factory=lambda: fake)

        session.get_or_upload("/tmp/student.mp4")
        session.get_or_upload("/tmp/reference.mp4")
        session.get_or_upload("/tmp/student.mp4")  # 재사용

        assert fake.files.upload_calls == 2  # 학생 1 + 기준 1
        session.close()
        assert fake.files.delete_calls == 2
        assert sorted(fake.files.deleted_names) == sorted(fake.files.uploaded_names)
