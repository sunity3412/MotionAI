"""수리 전 코드(HEAD 72b4ee2e)에서 동시 분석 오염을 재현한다.

왜 이 스크립트가 남아 있나
  수리 후에는 이 결함을 리포 안에서 재현할 방법이 없다 — 오염을 만들던 속성이 사라졌고
  대입하면 AttributeError 다. 그래서 "정말 있던 결함인가"를 나중에 다시 물을 수 있도록,
  **수리 전 소스를 git 에서 꺼내** 같은 시나리오를 돌리는 절차를 박제한다.

무엇을 보여주나
  분석 A 가 ref-power-spin 을 요청했는데 ref-climb 으로 확정된다. 두 동작은 채점 기준이
  다르다 — ref-power-spin 은 criteria yaml 에 EXTEND 관절(무릎 2개)이 있어 line 차원이
  산출되고, ref-climb 은 EXTEND 가 0이라 line 차원 자체가 없다. dimensions.CORE_DIMENSIONS
  = (angle, line) 이고 종합은 core 의 min 이므로, 오염되면 **종합 점수의 근거가 통째로**
  바뀐다. 예외도 로그도 남지 않는다.

실행
  cd <repo>
  SP=$(mktemp -d)
  cp -R backend/shared/python/sunity_shared "$SP/"
  for f in analysis/gemini_technique_recognizer.py analysis/technique.py \
           judging/gemini_moment_extractor.py; do
    git show "72b4ee2e:backend/shared/python/sunity_shared/$f" > "$SP/sunity_shared/$f"
  done
  ln -sfn "$PWD/backend/judging_data" "$(dirname "$SP")/judging_data"
  PYTHONPATH="$SP" backend/.venv/bin/python \
    .planning/quick/260920-cac-concurrency-contamination-fix/evidence/reproduce_contamination_pre_fix.py

2026-09-20 실행 결과
  분석 A: 요청= ref-power-spin → 확정='ref-climb'  EXTEND관절=[]
  분석 B: 요청=      ref-climb → 확정='ref-climb'  EXTEND관절=[]
  판정: 오염 — 분석 A 가 B 의 동작 기준으로 채점됐다
"""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass

import numpy as np

from sunity_shared.analysis.gemini_technique_recognizer import (
    GeminiTechniqueRecognizer,
)

_mod = sys.modules["sunity_shared.analysis.gemini_technique_recognizer"]
if "motion_query_hint" not in _mod.__file__ and not hasattr(
    GeminiTechniqueRecognizer, "motion_query_hint"
):
    # 수리 후 소스로 돌리면 의미가 없다. PYTHONPATH 를 확인하라.
    print(f"경고: 수리 후 소스를 로드했다 ({_mod.__file__}) — docstring 의 절차를 따르라.")


@dataclass
class _Moment:
    moment_key: str
    timestamp_seconds: float
    confidence: float
    frame_index: int = 0


_CALL_BARRIER = threading.Barrier(2)   # Gemini 왕복 / 포즈 추론 구간
_WRITE_BARRIER = threading.Barrier(2)  # 두 분석의 '쓰기'가 소비 전에 모두 일어나게


class _PreFixExtractor:
    """수리 전 계약 — 사이드카 속성에 쓰고, 호출자가 왕복 뒤 getattr 로 되읽는다."""

    def __init__(self) -> None:
        self._last_raw_response = ""
        self._last_motion_name = ""

    def extract_key_moments(self, video_uri, motion, *, preuploaded_handle=None):
        self._last_motion_name = motion
        _CALL_BARRIER.wait(timeout=10)
        self._last_raw_response = '{"moments": []}'
        return [_Moment("hold", 1.0, 0.9)]


def main() -> int:
    recognizer = GeminiTechniqueRecognizer(extractor=_PreFixExtractor(), cache=None)
    angles = np.full((12, 8), 165.0)
    requested = {"A": "ref-power-spin", "B": "ref-climb"}
    got: dict[str, object] = {}

    def _worker(tag: str) -> None:
        # 수리 전 pipeline/app.py 가 하던 그대로: 전역 싱글턴 속성에 쓰고,
        # 프레임추출 + RTMW 추론(실측 51~177초) 뒤에 recognize 가 읽는다.
        recognizer.motion_query_hint = requested[tag]
        _WRITE_BARRIER.wait(timeout=10)
        got[tag] = recognizer.recognize(angles, frames=f"/tmp/evidence-{tag}.mp4")

    threads = [
        threading.Thread(target=_worker, args=(t,), name=f"analysis-{t}")
        for t in ("A", "B")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(15)

    print("=== 수리 전 코드 · 동시 분석 2건 (전역 recognizer 1개 공유) ===")
    for tag in ("A", "B"):
        profile = got[tag]
        extend = sorted(
            k for k, v in profile.joint_expectations.items() if v == "extend"
        )
        print(
            f"  분석 {tag}: 요청={requested[tag]:>15} → "
            f"확정={profile.motion_id!r:>18}  EXTEND관절={extend}"
        )

    clean = all(got[t].motion_id == requested[t] for t in ("A", "B"))
    print("\n판정:", "오염 없음" if clean else "오염 — 한쪽이 남의 동작 기준으로 채점됐다")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
