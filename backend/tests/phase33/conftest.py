"""Phase 33 백엔드 테스트 공용 스캐폴드 — sys.path 주입 (LOCAL ONLY, AWS/Pod 무접촉).

backend/tests/conftest.py 가 shared/python 을 주입하지만, phase33 은 backend 루트
(functions/*)와 scripts 를 직접 import 하는 후속 플랜이 있어 phase31/phase32
conftest.py 선례대로 여기서 함께 보장한다.

이 플랜(33-01)은 관찰/덤프만 수행하므로 fake_firestore/fake_clock mock 은 넣지
않는다 — 필요한 후속 플랜이 phase31/phase32 fixture 를 재사용/복제한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
_SCRIPTS = _BACKEND / "scripts"
for _p in (_BACKEND, _LAYER, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
