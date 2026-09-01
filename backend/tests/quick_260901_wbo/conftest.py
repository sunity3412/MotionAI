"""quick-260901-wbo 테스트 공용 스캐폴드 — sys.path 주입 (LOCAL ONLY, AWS/Pod 무접촉).

backend/tests/conftest.py 가 shared/python 을 주입하지만, 본 디렉터리는
functions/pipeline (app.py) 을 직접 import 하는 사후 스테이지 테스트가 있어
test_fault_zoom_deferred.py 선례대로 여기서 함께 보장한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
_PIPELINE = _BACKEND / "functions" / "pipeline"
_SHARED = _BACKEND / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
