"""T1-b 하네스 — extract_reference_keypoint_reports.py 를 Pod 에서 S3 우회로 구동.

왜 필요했나 (2026-07-31 실측):
  boto3 `s3.download_file` (TransferManager, 멀티스레드) 가 서울 리전 GET 에서 행에 걸렸다.
  ref-climb 에서 4분 넘게 0 바이트. 반면 **단일 스레드 ranged GET 은 정상**이었다
  (ref-climb 566 KB/s, ref-combo 1494 KB/s 실측). 즉 회선이 아니라 TransferManager 문제.

무엇을 하나 (프로덕션 스크립트 코드는 변경 0 — CLI 인자만 --target-fps 18.0):
  1. `/workspace/_s3stage/reference/{id}.mp4` 가 있고 **크기가 S3 head_object.ContentLength 와
     정확히 일치**하면 그 파일을 쓴다. 크기가 다르면 스테이지를 신뢰하지 않고 재다운로드한다
     (가정 금지 — 확인하고 쓴다).
  2. 없거나 불일치면 `TransferConfig(use_threads=False)` 로 단일 스레드 다운로드한다.
  3. 그 외 동작(프레임 추출·RTMW·build_keypoint_report·출력 형식)은 프로덕션 그대로.

Usage (Pod):
  python /workspace/pod_extract_wrapper.py --target-fps 18.0 --out /workspace/reference-kp-18fps.json
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig

_BACKEND = Path("/workspace/SunityMotion/backend")
_SCRIPT = _BACKEND / "scripts" / "extract_reference_keypoint_reports.py"
_STAGE = Path("/workspace/_s3stage")

_SINGLE = TransferConfig(use_threads=False, multipart_threshold=1024 * 1024 * 1024)


class _StagedS3:
    """download_file 만 가로채는 얇은 shim. 나머지 호출은 실 클라이언트로 위임."""

    def __init__(self) -> None:
        self._real = boto3.client("s3")

    def __getattr__(self, name):
        return getattr(self._real, name)

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:  # noqa: N803
        remote_size = int(
            self._real.head_object(Bucket=Bucket, Key=Key)["ContentLength"]
        )
        staged = _STAGE / Key
        if staged.is_file() and staged.stat().st_size == remote_size:
            print(
                f"    [stage] {Key} 크기 일치({remote_size}) → 로컬 스테이지 사용",
                flush=True,
            )
            shutil.copyfile(staged, Filename)
            return
        if staged.is_file():
            print(
                f"    [stage] {Key} 크기 불일치(stage={staged.stat().st_size} "
                f"s3={remote_size}) → 스테이지 무시하고 재다운로드",
                flush=True,
            )
        print(f"    [s3] {Key} 단일 스레드 다운로드 ({remote_size} bytes)", flush=True)
        self._real.download_file(Bucket, Key, Filename, Config=_SINGLE)
        got = Path(Filename).stat().st_size
        if got != remote_size:
            raise RuntimeError(f"{Key} 다운로드 크기 불일치: {got} != {remote_size}")


def main() -> int:
    spec = importlib.util.spec_from_file_location("_extract_refkp", str(_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    # main() 안의 boto3.client("s3") 만 shim 으로 대체.
    class _B:
        def __getattr__(self, name):
            return getattr(boto3, name)

        @staticmethod
        def client(service: str, *a, **kw):
            if service == "s3":
                return _StagedS3()
            return boto3.client(service, *a, **kw)

    mod.boto3 = _B()
    sys.argv = ["extract_reference_keypoint_reports.py"] + sys.argv[1:]
    return mod.main()


if __name__ == "__main__":
    sys.exit(main())
