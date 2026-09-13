"""수집 진입점이 PYTHONPATH 없이 import 되는지 — 하위 프로세스로 박제 (quick-260913-vqr).

함정 — 왜 하위 프로세스인가:
  pytest 안에서는 backend/tests/conftest.py 와 tests/phase22/conftest.py 가
  shared/python·training·scripts 를 이미 sys.path 에 깔아 둔다. 그래서 같은
  인터프리터에서 `import collect_phase22_instagram` 을 해 봐야 경로 결손은 절대
  드러나지 않는다. 359b9de5(2026-08-18) 로 curate_vision 이
  sunity_shared.gemini.config 를 import 하게 됐을 때 기존 테스트 4800여 개가 전부
  초록이었던 이유가 이것이다 — 그동안 launchd 가 실행하는 실제 진입점은 3주간
  ModuleNotFoundError 로 죽어 있었다(.planning/FLYWHEEL-LOG.md rc 열 1/0/1/0).

  그래서 launchd 와 같은 조건 — PYTHONPATH 없는 깨끗한 인터프리터 — 를 subprocess 로
  띄워 진입점이 스스로 경로를 까는지 본다. 네트워크·AWS·Gemini 호출 0(import 만).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_SCRIPTS = _BACKEND / "scripts"

# 진입점별 import 스니펫 — 각각 launchd/사람이 단독 실행하는 경로를 본뜬다.
#   instagram : 모듈 최상위에서 curate_vision 을 import (08-24 실제로 죽은 자리)
#   youtube   : --curate/--collect 의 지연 import 를 그대로 재현
#   watch     : launchd 가 직접 실행하는 러너 — shared layer 가 보여야 한다
_ENTRYPOINTS = {
    "instagram": "import collect_phase22_instagram",
    "youtube": (
        "import collect_phase22_youtube as yt; "
        "sys.path.insert(0, str(yt.BACKEND / 'training')); "
        "from datagen import curate_vision"
    ),
    "watch": "import phase22_watch; import sunity_shared.gemini.config",
}


def _run_in_clean_interpreter(snippet: str) -> subprocess.CompletedProcess:
    """PYTHONPATH 를 지운 하위 인터프리터에서 snippet 실행. cwd = 리포 루트(사이클과 동일)."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    code = f"import sys; sys.path.insert(0, {str(_SCRIPTS)!r}); {snippet}"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_BACKEND.parent),
        env=env, capture_output=True, text=True, timeout=60,
    )


def test_clean_interpreter_really_lacks_shared_layer():
    """계기의 시야 선언 — 깨끗한 인터프리터에는 sunity_shared 가 없어야 한다.

    누군가 .pth 등으로 shared/python 을 전역에 깔면 아래 진입점 테스트는 영원히
    초록이 되어 결손을 못 잡는다(사문). 그 순간을 여기서 잡는다.
    """
    proc = _run_in_clean_interpreter("import sunity_shared")
    assert proc.returncode != 0, (
        "깨끗한 인터프리터에서 sunity_shared 가 import 된다 — 진입점 테스트가 사문이 됐다. "
        "전역 경로 주입(.pth 등)을 확인할 것."
    )


@pytest.mark.parametrize("name", sorted(_ENTRYPOINTS))
def test_entrypoint_imports_without_pythonpath(name):
    proc = _run_in_clean_interpreter(_ENTRYPOINTS[name])
    assert proc.returncode == 0, (
        f"{name} 진입점이 PYTHONPATH 없이 import 실패 — sunity_shared 경로 결손 재발?\n"
        f"stderr:\n{proc.stderr[-1500:]}"
    )
