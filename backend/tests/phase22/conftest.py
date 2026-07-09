"""Phase 22 datagen 테스트 — shared layer + training 패키지 sys.path 주입.

backend/tests/conftest.py 가 이미 shared/python 을 주입하지만, D-16 Wave 0 데이터
엔진(schema/perturb)은 backend/training/datagen 아래 신설되므로 별도 주입이 필요하다.
vision_veto.FAULT_CATEGORIES 단일 owner 재사용을 위해 shared layer 도 함께 보장한다
(schema.py 는 스스로도 shared layer 를 주입하지만, 테스트가 datagen 을 직접 import
할 수 있도록 여기서 training 루트를 path 에 얹는다).
"""

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
_TRAINING = _BACKEND / "training"
_SCRIPTS = _BACKEND / "scripts"  # collect_phase22_youtube 순수 필터 import (22-02).
for _p in (_LAYER, _TRAINING, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
