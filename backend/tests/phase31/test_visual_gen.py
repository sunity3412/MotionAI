"""Wan2.7 VisualGenEngine 어댑터 (create/폴링/모더레이션 폴백/redirect·oversized 방어) — 담당 플랜 31-05.

실 Firestore/네트워크/Pod 미접촉 — LOCAL ONLY. 공용 스캐폴드(_FakeTransaction 경쟁
transaction·주입 시계·DashScope urllib mock)는 backend/tests/phase31/conftest.py 소유.

본 파일은 31-02 가 만든 **골격**이다. 실제 검증은 31-05 이 채운다 — 그때까지
대상 모듈이 없으므로 `_require()` 가드로 skip 하고, 여기서는 공용 fixture 가
살아 있는지만 확인한다(스캐폴드가 조용히 썩는 것을 막는 최소 계약).
"""

from __future__ import annotations

import pytest

_TARGET = "visual_gen"


def _require():
    """대상 모듈 미존재 시 skip. 31-05 구현 후 자동으로 활성화된다."""
    return pytest.importorskip(
        _TARGET, reason=f"{_TARGET} 은 플랜 31-05 산출물 — 아직 미구현"
    )


def test_scaffold_dashscope_mock_alive(dashscope_urlopen_mock):
    """공용 DashScope mock 이 create → 폴링 형상을 그대로 돌려주는지."""
    import json
    import urllib.request

    dashscope_urlopen_mock.succeed(video_url="https://vendor.example/x.mp4")
    req = urllib.request.Request("https://dashscope-intl.aliyuncs.com/create", data=b"{}")
    with urllib.request.urlopen(req) as r:
        created = json.loads(r.read())
    assert created["output"]["task_id"] == "task-1"
    with urllib.request.urlopen("https://dashscope-intl.aliyuncs.com/tasks/task-1") as r:
        polled = json.loads(r.read())
    assert polled["output"]["task_status"] == "RUNNING"

