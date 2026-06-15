"""유닛 테스트가 AWS/배포 없이 sunity_shared 를 import 할 수 있도록 경로 주입.

배포 시에는 Lambda Layer 가 /opt/python 에 올려주므로 이 파일은 테스트 전용.
"""

import sys
from pathlib import Path

_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

# Plan 14-02 — backfill_reference_downstream 등 backend/scripts 의 orchestrator 를
# bare import (test_reference_backfill.py 의 R4-1 parity helper) 가능하도록 주입.
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
