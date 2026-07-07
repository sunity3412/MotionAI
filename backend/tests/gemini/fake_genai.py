"""Phase 27 SPD-01 — D-04 업로드/삭제 카운트 + D-03 fan-out 순서 결정론 검증용 공용 stub.

test_client.py:38-100 의 `_FakeFile`/`_FakeFiles`/`_FakeModels`/`_patch_genai` 패턴을
재사용 가능한 모듈로 확장한다 (test_client.py 본체는 무수정). 후속 wave 가 import 만으로
재사용:
  · 27-03 세션 누수 0 — `FakeFiles.delete_calls` / `deleted_names` 로 File API 삭제 검증.
  · 27-05 fan-out 결정론 — `FakeModels.delay_by_index` 로 늦게 끝나는 호출을 주입해도
    집계 순서가 call_plan 인덱스 순인지 검증.

외부 네트워크 호출 0 — genai.Client / files / models / time.sleep 를 전부 stub.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any


class FakeFile:
    """Files API 파일 핸들 stub.

    `.name` = `files/fake-N` 형식 (client.files.delete(name=...) 대상).
    `.state` = `SimpleNamespace(name=<STATE>)` — client 폴링이 `file.state.name` 을 읽는
    관례(test_client.py `_FakeFile`) 정합.
    """

    def __init__(self, name: str = "files/fake-1", state: str = "ACTIVE") -> None:
        self.name = name
        self.state = SimpleNamespace(name=state)


class FakeFiles:
    """Files API stub — upload / get / delete + 카운터 + 이름 기록.

    upload_state: upload() 가 반환하는 파일의 초기 state.
    get_sequence: get() 호출마다 pop 되는 state 시퀀스 (PROCESSING → ACTIVE 폴링 박제).
      소진되면 'ACTIVE' 로 고정.
    """

    def __init__(
        self,
        *,
        upload_state: str = "ACTIVE",
        get_sequence: list[str] | None = None,
    ) -> None:
        self.upload_state = upload_state
        self.get_sequence = list(get_sequence) if get_sequence else []
        # 카운터 (D-04 업로드/삭제 회계).
        self.upload_calls = 0
        self.get_calls = 0
        self.delete_calls = 0
        # 이름 기록 — upload 된 파일이 전부 delete 됐는지 대조 (누수 0 검증).
        self.uploaded_names: list[str] = []
        self.deleted_names: list[str] = []

    def upload(self, *, file: Any, config: Any = None) -> FakeFile:
        # config kwarg 허용 — client.py:210-219 의 UploadFileConfig 경로 대응
        # (일부 stub 환경 TypeError 폴백 전에 config 포함 호출을 먼저 시도).
        self.upload_calls += 1
        name = f"files/fake-{self.upload_calls}"
        self.uploaded_names.append(name)
        return FakeFile(name=name, state=self.upload_state)

    def get(self, *, name: str) -> FakeFile:
        self.get_calls += 1
        state = self.get_sequence.pop(0) if self.get_sequence else "ACTIVE"
        return FakeFile(name=name, state=state)

    def delete(self, *, name: str) -> None:
        self.delete_calls += 1
        self.deleted_names.append(name)


class FakeModels:
    """generate_content stub — 호출 인덱스별 응답 반환 + fan-out 순서 결정론 지원.

    responses: 호출 인덱스별 응답(또는 raise 할 BaseException). None/소진 시 None 반환.
    delay_by_index: {call_index: seconds} — 해당 인덱스 호출에서 time.sleep(delay).
      wave 5 fan-out 순서 결정론 테스트용 — 늦게 끝나는 future 가 있어도 집계 순서가
      call_plan 인덱스 순인지 검증. (patch_genai 가 time.sleep 을 박제하지 않은
      경우에만 실제 지연; 기본 patch_genai 는 sleep no-op 이라 결정론적.)
    calls: 각 호출의 kwargs 기록 (model/contents/config 인자 대조).
    """

    def __init__(
        self,
        responses: list[Any] | None = None,
        *,
        delay_by_index: dict[int, float] | None = None,
    ) -> None:
        self.responses = list(responses) if responses else []
        self.delay_by_index = dict(delay_by_index) if delay_by_index else {}
        self.calls: list[dict] = []

    def generate_content(self, **kwargs: Any) -> Any:
        idx = len(self.calls)
        self.calls.append(kwargs)
        delay = self.delay_by_index.get(idx)
        if delay:
            time.sleep(delay)
        if idx < len(self.responses):
            item = self.responses[idx]
            if isinstance(item, BaseException):
                raise item
            return item
        return None


class FakeClient:
    """genai.Client stub — files / models 를 노출."""

    def __init__(self, files: FakeFiles, models: FakeModels) -> None:
        self.files = files
        self.models = models


def patch_genai(
    monkeypatch,
    target_module: Any,
    *,
    files: FakeFiles | None = None,
    models: FakeModels | None = None,
) -> FakeClient:
    """target_module.genai.Client 를 fake ctor 로 교체 + time.sleep 박제.

    test_client.py `_patch_genai` 시그니처 관례 준수 (monkeypatch 우선). target_module
    이 `genai` 를 심볼로 갖고 있어야 한다 (`from ... import genai as genai` 또는 모듈
    참조). `target_module.time` 이 있으면 sleep 을 no-op 으로 박제 — 폴링/지연 테스트
    속도 박제.
    """
    fake = FakeClient(files or FakeFiles(), models or FakeModels())

    def _fake_client_ctor(*, api_key: str) -> FakeClient:  # noqa: ARG001 - 시그니처 박제
        return fake

    monkeypatch.setattr(target_module.genai, "Client", _fake_client_ctor)
    if hasattr(target_module, "time"):
        monkeypatch.setattr(target_module.time, "sleep", lambda _s: None)
    return fake
