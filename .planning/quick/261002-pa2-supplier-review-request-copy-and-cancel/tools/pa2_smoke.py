"""pa2 Docker 스모크 — /opt/python = layer, /var/task = 함수. 배포 아님(로컬 컨테이너).

MODE=new  : 새 layer + 새 함수 — import · 무토큰 401 · 상수 · writer · validator.
MODE=old-code-new-layer : 라이브 함수 + 새 layer — 배포 (2) 의 'layer 먼저' 중간 상태가 안전한지.
MODE=new-code-old-layer : 새 함수 + layer :24 — 순서를 거꾸로 하면 import 에서 죽는지(롤백 '코드 먼저' 근거).
"""
import json
import os
import sys

sys.path.insert(0, "/var/task")
os.environ.setdefault("VIDEO_BUCKET", "smoke-dummy-bucket")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")
mode = os.environ["MODE"]
HEX = "0123456789abcdef0123456789abcdef"

if mode == "new-code-old-layer":
    try:
        import app  # noqa: F401
    except ImportError as e:
        print(f"EXPECTED_IMPORT_ERROR {type(e).__name__}: {e}")
        sys.exit(0)
    print("UNEXPECTED_IMPORT_OK")
    sys.exit(1)

import app  # 가장 큰 위험 = 옛 layer 위 새 app.py 의 ImportError
from sunity_shared import firestore_admin, models, validation

r = app.lambda_handler({"headers": {}, "body": json.dumps({"cancel": True, "refId": HEX})}, None)
assert r["statusCode"] == 401, r
r2 = app.lambda_handler({"headers": {}, "body": json.dumps({"probe": True})}, None)
assert r2["statusCode"] == 401, r2
assert models.REGISTRATION_STATUS_CANCELLED == "cancelled"
assert models.REGISTRATION_STATUSES[-1] == "cancelled"
assert models.REFERENCE_CANCEL_ERR_NOT_CANCELLABLE == "not_cancellable"
assert models.REFERENCE_CANCEL_ERR_NOT_FOUND == "not_found"
assert callable(firestore_admin.cancel_reference_registration)
assert callable(firestore_admin.deactivate_reference_registration)
assert models.REGISTRATION_STATUS_CANCELLED in firestore_admin._REGISTRATION_TERMINAL
try:
    validation.validate_reference_cancel_request({"refId": "ref-kip-up"})
except validation.ValidationError as e:
    assert e.code == "bad_request" and e.http_status == 400, (e.code, e.http_status)
else:
    raise AssertionError("ref-kip-up 가 통과했다")
assert validation.validate_reference_cancel_request({"refId": HEX}) == HEX
if mode == "new":
    assert hasattr(app, "_cancel")
    print("SMOKE_OK unauth=401 probe_unauth=401 cancelled=ok writer=ok validator=bad_request(ref-kip-up)")
else:
    assert not hasattr(app, "_cancel")  # 라이브 옛 코드
    print("SMOKE_OK_OLD_CODE_NEW_LAYER unauth=401 import=ok")
