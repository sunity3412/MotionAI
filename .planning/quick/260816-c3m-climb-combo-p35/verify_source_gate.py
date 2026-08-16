#!/usr/bin/env python3
"""discover_sweep.py::source_gate() 를 climb/combo 에 재사용해 실증 (quick-260816-c3m).

discover_sweep.py(quick-260814-ehz-5) 원본은 절대 편집하지 않는다 — importlib 로
읽기만 하고, 로드한 모듈 객체의 SWEEP_JOBS 딕셔너리를 런타임 in-memory 로만
확장한다(디스크 파일 변경 0). source_gate() 함수만 재사용 — scan/eye/render 는
호출하지 않는다(발굴 실행은 다음 사이클의 몫).

climbfault 는 여기 없다 — p35_new_motion_docs.py 의 _process() 가
NotPoleMotionError(angle 0 < 25)로 실패해(2회 재현, 결정론) doc.json/align.json
자체가 생성되지 않았다. source_gate() 는 P35 data/ 아래 doc.json 실물 존재를
전제하므로(README.md 참조) climbfault 는 게이트 대상에서 애초에 제외된다.

Pod 없이 로컬에서 실행 (S3 read-only download + AWS_PROFILE=sunity-motion):
    backend/.venv/bin/python \
      .planning/quick/260816-c3m-climb-combo-p35/verify_source_gate.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# repo root = HERE(.../260816-c3m-climb-combo-p35) -> quick -> .planning -> repo root.
REPO_ROOT = HERE.parents[2]
DISCOVER_SWEEP_PATH = REPO_ROOT / ".planning" / "quick" / "260814-ehz-5" / "discover_sweep.py"

# 원본 SWEEP_JOBS 스키마(3-tuple: userKey, refKey, motionId) — p35_extract_align.py
# 의 2-tuple JOBS 와 혼동하지 말 것.
NEW_SLOTS: dict[str, tuple[str, str, str]] = {
    "climb": ("fixtures/phase15/climb/correct.mp4", "reference/ref-climb.mp4", "ref-climb"),
    "combo": ("fixtures/phase15/combo/correct.mp4", "reference/ref-combo.mp4", "ref-combo"),
}


def _load_discover_sweep_module():
    """discover_sweep.py 를 경로 import — 원본 파일은 읽기 전용, 무편집."""
    if not DISCOVER_SWEEP_PATH.is_file():
        raise SystemExit(f"discover_sweep.py 부재: {DISCOVER_SWEEP_PATH}")
    spec = importlib.util.spec_from_file_location(
        "discover_sweep_c3m_verify", DISCOVER_SWEEP_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _load_discover_sweep_module()

    # SWEEP_JOBS 는 로드된 모듈 객체의 dict — 원본 discover_sweep.py 파일은
    # 절대 건드리지 않는다(메모리상 dict 객체만 확장).
    mod.SWEEP_JOBS.update(NEW_SLOTS)

    # _cr_root() 가드가 요구하는 캐시 루트 — .cache/ 는 커밋 대상 아님.
    cache_root = HERE / ".cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    mod._CACHE_ROOT = cache_root

    results: dict[str, dict] = {}
    all_passed = True
    for slot in NEW_SLOTS:
        gate = mod.source_gate(slot, download=True)
        results[slot] = gate
        status = "PASS" if gate["passed"] else "FAIL"
        print(f"[{slot}] source_gate {status} reasons={gate.get('reasons') or []}")
        if not gate["passed"]:
            all_passed = False

    out_path = HERE / "source_gate_result.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=1, default=str)
    )
    print(f"결과 저장: {out_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
