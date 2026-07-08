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
