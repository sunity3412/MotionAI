# Phase 5: Gemini 기술 인식기 (분류 한정) — Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 18 (5 yaml + 6 new module + 4 modify + 3 test)
**Analogs found:** 17 / 18 (TechniqueCache 만 부분 합성)

박제 정합:
- [[gsd-pod-work-push-first.md]] — Pod 작업 단위 = commit + push 후 belle Pod 동기화
- [[analysis-objectivity-no-human-scores.md]] — Gemini = 라벨러만, reject patterns 3종 (좌표/점수/판단)
- [[notebook-lm-pole-sports.md]] — 정은지 reference 측정값 (분기 2 path) 박제 source
- [[studio-term-3branch-system.md]] — 분기 2 정은지 reference 측정값 = yaml source_ref 정정 source
- 박제 D-16 lazy import — `google-genai` + `boto3` 모듈 로드 시점 0 import 유지

---

## File Classification

| New/Modified File | Plan | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `backend/research/spikes/measure_eunji_reference.py` | 5-00 | new spike (data acquisition) | batch / file-I/O | `backend/research/spikes/spike_rtmpose.py` | role-match (frame extract + RTMW 측정) |
| `backend/judging_data/criteria/ref-climb.yaml` | 5-00 | config / data (rewrite) | static | `backend/judging_data/criteria/ref-climb.yaml` 현재 (의도된 빈 list 유지) | self (메타 source_ref 갱신) |
| `backend/judging_data/criteria/ref-foxtop.yaml` | 5-00 | config / data (rewrite) | static | `backend/judging_data/criteria/ref-foxtop.yaml` 현재 + 정은지 측정값 | self (수치 정정 + source_ref 변경) |
| `backend/judging_data/criteria/ref-foxtop-split.yaml` | 5-00 | config / data (rewrite) | static | `backend/judging_data/criteria/ref-foxtop-split.yaml` 현재 + 정은지 측정값 | self |
| `backend/judging_data/criteria/ref-invert.yaml` | 5-00 | config / data (rewrite) | static | `backend/judging_data/criteria/ref-invert.yaml` 현재 + 정은지 측정값 | self (5/5 중 IPSF body position 단독 표시) |
| `backend/judging_data/criteria/ref-sideway-spin.yaml` | 5-00 | config / data (rewrite) | static | `backend/judging_data/criteria/ref-sideway-spin.yaml` 현재 + 정은지 측정값 | self |
| `backend/shared/python/sunity_shared/analysis/technique.py` (extend) | 5-01 | new class in existing module | request-response (adapter) | `technique.py::FallbackRecognizer` (lines 57-87) | exact (Protocol 구현 sibling) |
| `backend/shared/python/sunity_shared/analysis/technique_cache.py` (new) | 5-02 | new module | CRUD (read-through cache) | `firestore_admin.py::complete_analysis` + `firestore_admin._db` (singleton) | role-match (Firestore singleton + flat-list 박제 정신) |
| `backend/functions/pipeline/app.py` (modify line 120 + _process 흐름) | 5-03 | extend (1-line + env switch) | request-response | `pipeline/app.py::_RECOGNIZER` (line 120) + `_ensure_adapters` (123-135) | self (RECOGNIZER 교체 패턴) |
| `backend/runpod_inference/server.py` (no edit / 우회 import) | 5-03 | extend (reuse) | request-response | `runpod_inference/server.py::_load_pipeline_module` (63-80) | self (pipeline 모듈 import 후 _RECOGNIZER 보장) |
| `backend/runpod_inference/requirements.txt` (1줄 추가) | 5-04 | config | static | 본 파일 자체 | self (`google-genai` append) |
| `backend/runpod_inference/setup.sh` (env block append) | 5-04 | config | static | 본 파일 자체 (line 117-122) | self (`GEMINI_API_KEY` SSM fetch block) |
| `backend/research/evaluations/compare_rtmw_vs_ipsf.py` (`--recognizer gemini` flag) | 5-05 | extend (CLI flag + recognizer 주입) | batch | `compare_rtmw_vs_ipsf.py::compute_line_angle_gates` (line 323-346) | exact (FallbackRecognizer 주입처 단일) |
| `backend/tests/test_gemini_technique_recognizer.py` (new) | 5-01 | new test | unit | `backend/tests/test_gemini_moment_extractor.py` | exact (좌표/점수/판단 reject + cache + lazy import 패턴) |
| `backend/tests/test_technique_cache.py` (new) | 5-02 | new test | unit | `backend/tests/test_gemini_moment_extractor.py::TestExtractKeyMomentsCache` 부분 + `test_technique.py` | role-match |
| `backend/tests/test_pipeline_recognizer_switch.py` (new) | 5-03 | new test | unit | `backend/tests/test_pipeline_dispatch.py` | role-match (env switch 검증 패턴) |

---

## Pattern Assignments

### Plan 5-00 — yaml source 정정 + 정은지 reference 측정 spike

#### `backend/research/spikes/measure_eunji_reference.py` (new spike, batch / file-I/O)

**Analog:** `backend/research/spikes/spike_rtmpose.py` (823 lines)

**Imports + S3 download pattern** (lines 50-110):
```python
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# S3 기준 모션 영상 키 경로 (Plan 07/08 spike 와 동일)
_REFERENCE_VIDEO_PREFIX = "reference"


def _download_s3(s3_key: str, bucket: str, dest: Path) -> None:
    """S3 → 로컬 경로 다운로드 (Plan 07 spike_motionbert 동일)."""
    import boto3  # Pod 환경에서 제공

    s3 = boto3.client("s3")
    log.info("downloading s3://%s/%s -> %s", bucket, s3_key, dest)
    s3.download_file(bucket, s3_key, str(dest))


def _resolve_video(video_path, motion, bucket, tmp_dir):
    if video_path is not None:
        return video_path
    s3_key = f"{_REFERENCE_VIDEO_PREFIX}/{motion}.mp4"
    local_path = tmp_dir / f"{motion}.mp4"
    _download_s3(s3_key, bucket, local_path)
    return str(local_path)
```

**Frame extraction pattern** (lines 116-130):
```python
def _extract_frames(video_path: str) -> np.ndarray:
    """영상 → (T, H, W, 3) RGB uint8. FfmpegFrameExtractor (9fps / 640px).
    Plan 07/08 spike 와 동일 — sunity_shared.analysis.frame_extractor.
    """
    from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor

    extractor = FfmpegFrameExtractor()
    frames = extractor.extract(video_path)
    return np.asarray(frames, dtype=np.uint8)
```

**RTMW pose 산출 + angles 변환 + hold_window 측정 pattern** (compare_rtmw_vs_ipsf.py 의 pose engine 사용 + dimensions.hold_window):
```python
# Plan 5-00: 정은지 reference 영상 5개 → RTMW pose → (T, 8) angles → hold_window
# 측정값 추출 → yaml angle_target / tolerance / minimum 갱신용 JSON 출력.
# tolerance = 측정값 ±15° / minimum = 측정값 - 25° (D-18 박제 룰).
```

**박제 정신 정합** (D-17 / D-18):
- lazy import (`boto3`, `mmpose`, `torch`) 유지 — 로컬 단위 테스트는 stub-frames mode
- 정은지 reference 영상은 belle 가 식별한 hold timestamp 박제 후 측정 (D-18 step 2 = belle 직접 또는 수동)
- 출력 = JSON 박제 (5영상 × 6관절 × {target, tolerance, minimum} 측정값) → planner 가 yaml 5개에 수동 박제

---

#### `backend/judging_data/criteria/ref-{climb,foxtop,foxtop-split,invert,sideway-spin}.yaml` (rewrite)

**Analog:** `backend/judging_data/criteria/ref-invert.yaml` 현재 구조 (line 1-52)

**현재 박제 (변경 전, source_ref = "IPSF Code of Points 2024-2025")**:
```yaml
# Plan 01-15 (a) path 1차 박제 (2026-06-01). reference-motions.md §5 ref-invert
# checkpoints + §8 IPSF Code of Points (tolerance 20° + Fully Extended 규정) 기반.
motion: ref-invert
source: "reference-motions.md §5 ref-invert (intermediate, 인버트 스플릿 peak 7s) + IPSF Aerial Pole Sports Code of Points 2024-2025 (NotebookLM lookup 2026-06-01, 정확 element code §TBD)"
criteria:
  setup_moment: []
  hold_moment:
    - joint: left_shoulder
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 160.0
      source_ref: "reference-motions.md §5 ref-invert checkpoints (left_shoulder w=0.20 주 지지 팔 견갑 안정성) + IPSF Aerial Pole Sports Code of Points 2024-2025 (Body position ±20° tolerance, Fully Extended Criteria — fail < 160°)"
    # ... 6 joints 동일 패턴
```

**갱신 후 박제 (D-17 + IPSF-LOOKUP.md (가+다) 옵션)**:
- `source:` 헤더 = `"정은지 reference 측정값 (분기 2 path) — NotebookLM IPSF lookup 2026-06-04 결과 IPSF source 박제 X"`
- `angle_target` = Plan 5-00 spike 측정값
- `tolerance_full` = 측정값 ±15° (D-18 룰, belle 승인 시 변경 가능)
- `minimum_requirement` = 측정값 - 25° (D-18 룰)
- `source_ref` 마다 `"정은지 reference 측정값 (분기 2) — IPSF source 박제 X"` 명시 (D-19/D-20: ref-invert Body Position + ref-climb 이동 횟수 차원은 별 phase 책임 박제만 주석)

**ref-climb 특이 박제** (의도된 빈 list 유지, NotebookLM lookup 결과 IPSF Climbs = angle 차원 X):
```yaml
# 현재 박제 그대로 유지 (line 23-29):
motion: ref-climb
source: "reference-motions.md §5 ref-climb (basic, 양 무릎 X자 hook peak 5s) + IPSF Aerial Pole Sports Code of Points 2024-2025 Transitions & Climbs category (각도 임계 X — MVP scope 외)"
criteria:
  setup_moment: []
  hold_moment: []   # IPSF Climbs 카테고리 = 해부학적 각도 임계 X (의도된 빈 list)
  peak_moment: []
  release_moment: []
```
주석으로 D-20 ("이동 횟수 차원 = 별 phase") 추가만.

---

### Plan 5-01 — `GeminiTechniqueRecognizer` 어댑터 신설

#### `backend/shared/python/sunity_shared/analysis/technique.py` (extend, add new class)

**Primary Analog:** `backend/shared/python/sunity_shared/analysis/technique.py::FallbackRecognizer` (lines 57-87) — sibling Protocol 구현

**Secondary Analog:** `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py::GeminiMomentExtractor` (lines 244-355) — wrapping 대상 spike code

**Protocol 박제 (현재 박제, 무수정)** (technique.py lines 51-54):
```python
class TechniqueRecognizer(Protocol):
    """영상/관절각 → TechniqueProfile. 구현체는 swappable (Fallback/Gemini/Pole-arina)."""

    def recognize(self, angles, frames=None) -> TechniqueProfile: ...
```

**FallbackRecognizer 어댑터 박제 패턴** (technique.py lines 57-87) — Gemini 어댑터가 그대로 따라야 할 형식:
```python
class FallbackRecognizer:
    """인식 모델 없이 보수적으로 프로파일을 만든다.

    철학: **모르면 깎지 않는다(위양성 방지).** 홀딩 대표 포즈에서 명백히 신전
    영역(≥150°)에 든 팔꿈치/무릎만 EXTEND 로 보고, 굽은 사지는 BENT_OK(의도일 수
    있음). 대칭 가정 안 함(폴 동작은 비대칭이 정상).
    """

    def recognize(self, angles, frames=None) -> TechniqueProfile:
        a = np.asarray(angles, dtype=float)
        if a.ndim == 2 and a.shape[0] > 0:
            rep = np.mean(a, axis=0)
        else:
            rep = np.zeros(len(JOINT_KEYS))
        expectations: dict[str, str] = {}
        for i, key in enumerate(JOINT_KEYS):
            if key in _EXTENSION_JOINTS and i < rep.shape[0]:
                expectations[key] = (
                    JOINT_EXTEND if float(rep[i]) >= _EXTENSION_ZONE_DEG else JOINT_BENT_OK
                )
            else:
                expectations[key] = JOINT_BENT_OK
        return TechniqueProfile(
            name="미상",
            category="unknown",
            joint_expectations=expectations,
            ...
        )
```

**Lazy import + reject patterns 박제 패턴** (gemini_moment_extractor.py lines 26-73):
```python
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

# AWS SSM Parameter Store 경로 — STATE.md 2026-06-01 박제됨.
GEMINI_API_KEY_PARAM_NAME = "/sunity/motion/gemini-api-key"
DEFAULT_GEMINI_MODEL = "gemini-2.5-pro"  # D-13 박제 = gemini-3.1-pro 로 갱신

# Gemini 응답이 좌표·점수·판단을 출력하지 못하도록 거부할 패턴.
_COORDINATE_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bx\s*[:=]\s*-?\d", re.IGNORECASE),
    re.compile(r"\by\s*[:=]\s*-?\d", re.IGNORECASE),
    ...
)
_SCORE_REJECT_PATTERNS = (...)
_JUDGMENT_REJECT_PATTERNS = (...)
```

**Lazy SDK import 패턴** (gemini_moment_extractor.py lines 291-309):
```python
def _call_gemini(self, video_uri: str, motion: str) -> str:
    """Gemini 실 호출. SDK 는 lazy import — 단위 테스트는 본 메서드 override.
    2026-06-01: legacy `google-generativeai` (0.8.x) 는 새 AI Studio 키 포맷
    (`AQ.` prefix, 2025-말 갱신) 인식 못 함. 신 SDK `google-genai` 사용.
    """
    try:
        from google import genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "google-genai 미설치 — Pod 에 `pip install google-genai` 필요. "
            "(2026-06-01 박제: legacy `google-generativeai` 는 새 AI Studio "
            "`AQ.` 키 포맷 미지원). 로컬 단위 테스트에서는 `_call_gemini` "
            "를 override 하세요."
        ) from exc

    api_key = self.api_key_loader()
    client = genai.Client(api_key=api_key)
```

**Boto3 SSM lazy fetch 패턴** (gemini_moment_extractor.py lines 166-208):
```python
def _load_api_key() -> str:
    """Gemini API 키 로드. 우선순위:
      1. env `GEMINI_API_KEY` — Pod / 로컬 dev 편의용 (CLI export).
      2. AWS SSM Parameter Store `/sunity/motion/gemini-api-key` (SecureString) — Lambda 기본.
    둘 다 없으면 RuntimeError. `.env` 하드코딩 금지 (CLAUDE.md §3).
    boto3 는 lazy import — 1번 경로 사용 시 AWS 의존성 없이 동작.
    """
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        return inline

    param_name = os.environ.get("GEMINI_API_KEY_PARAM_NAME", GEMINI_API_KEY_PARAM_NAME)
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(...) from exc

    ssm = boto3.client("ssm")
    resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return resp["Parameter"]["Value"]
```

**GeminiTechniqueRecognizer 신설 박제 정신 (D-04 ~ D-09, D-13, D-16)**:
- `model_name="gemini-3.1-pro"` 박제 (D-13, STATE.md 갱신)
- `__init__(extractor=None, cache=None, low_confidence_threshold=0.5, fallback=None)` — 의존성 주입으로 테스트 가능
- `recognize(angles, frames=video_path) -> TechniqueProfile`:
  1. cache hit → `TechniqueProfile` 즉시 반환 (D-14)
  2. cache miss → `extractor.extract_key_moments(frames, motion)` 호출 (KeyMoment list 반환)
  3. hold moment 라벨 → `joint_expectations` dict 변환 (D-05 v1 활성)
  4. setup/peak/release 라벨 → Firestore 박제 layer 로 전달 (D-05 v1 dead, D-06 v2 자동활성)
  5. confidence < threshold → FallbackRecognizer 위임 (D-09 case 2)
  6. "scope 밖" 응답 → FallbackRecognizer + Firestore `scope_status="unregistered"` 박제 (D-09 case 3)
  7. API/네트워크 실패 → FallbackRecognizer 위임 (D-09 case 1)

---

#### `backend/tests/test_gemini_technique_recognizer.py` (new test)

**Analog:** `backend/tests/test_gemini_moment_extractor.py` (lines 1-117 + cache + parse 섹션)

**테스트 박제 패턴** (test_gemini_moment_extractor.py lines 14-67):
```python
from __future__ import annotations

import json

import pytest

from sunity_shared.judging import (
    GeminiMomentExtractor,
    KeyMoment,
    assign_frame_indices,
)
from sunity_shared.judging.gemini_moment_extractor import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_API_KEY_PARAM_NAME,
    _enforce_no_coordinate_or_score,
    _load_api_key,
    _parse_gemini_response,
    _strip_markdown_fence,
)
from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS


class TestKeyMomentValidate:
    def test_valid_passes(self) -> None:
        _valid_moment().validate()  # no raise

    def test_invalid_moment_key_rejected(self) -> None:
        m = KeyMoment(...)
        with pytest.raises(ValueError) as exc:
            m.validate()
        for k in VALID_MOMENT_KEYS:
            assert k in str(exc.value)
```

**테스트 박제 정신 (D-09 + D-16)**:
- mock `GeminiMomentExtractor` 주입 (실 SDK 호출 X)
- fallback 위임 3 case 검증: timeout / low confidence / unregistered
- `joint_expectations` dict 형식 정합 (FallbackRecognizer 와 동일 contract)
- lazy import 검증: 모듈 import 시 `google.genai` 미import (sys.modules grep)
- stdlib + pytest 만 사용 (mmpose / torch / google.generativeai / boto3 미import) — test_gemini_moment_extractor.py 박제 정신 그대로

---

### Plan 5-02 — `TechniqueCache` 신설 (Firestore hash 캡싱)

#### `backend/shared/python/sunity_shared/analysis/technique_cache.py` (new module)

**Primary Analog:** `backend/shared/python/sunity_shared/firestore_admin.py` (lines 18-94) — Firestore Admin singleton + flat-list 박제 패턴

**Firestore singleton 박제 패턴** (firestore_admin.py lines 18-31):
```python
_client = None


def _db():
    """firestore 클라이언트 1회 생성 (firebase-admin 초기화 재사용)."""
    global _client
    if _client is not None:
        return _client
    _auth._ensure_firebase()  # firebase_admin app 보장
    from firebase_admin import firestore

    _client = firestore.client()
    return _client


def _doc(path: str):
    return _db().document(path)
```

**박제 / lookup 박제 패턴** (firestore_admin.py lines 37-70):
```python
def update_analysis_status(uid: str, analysis_id: str, status: str) -> None:
    """진행 단계 갱신. status 는 models.PIPELINE_SEQUENCE 중 하나."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {"status": status, "updatedAt": int(time.time() * 1000)},
        merge=True,
    )


def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
) -> None:
    """status='done' + result (contract.md §4 AnalysisResult).
    Firestore 는 nested-array 금지라 flat list + anglesJointKeys(길이 J) + anglesFrames(T) 로
    저장하고 읽는 쪽에서 reshape ([[firestore-nested-array-flat]]).
    """
    payload: dict = {
        "status": models.STATUS_DONE,
        "result": result,
        "updatedAt": int(time.time() * 1000),
    }
    if angles is not None:
        payload["angles"] = angles
        payload["anglesJointKeys"] = angles_joint_keys
        payload["anglesFrames"] = angles_frames
    _doc(models.analysis_doc_path(uid, analysis_id)).set(payload, merge=True)
```

**Secondary Analog (in-memory cache 박제):** `gemini_moment_extractor.py::GeminiMomentExtractor._cache` (lines 260-289):
```python
@dataclass
class GeminiMomentExtractor:
    model_name: str = DEFAULT_GEMINI_MODEL
    api_key_loader: callable = field(default=_load_api_key)
    _cache: dict[tuple[str, str, str], list[KeyMoment]] = field(
        default_factory=dict, init=False, repr=False
    )

    def extract_key_moments(self, video_uri, motion):
        cache_key = (video_uri, motion, self.model_name)
        if cache_key in self._cache:
            log.debug("KeyMoment 캐시 hit: %s", cache_key)
            return list(self._cache[cache_key])

        raw_response = self._call_gemini(video_uri, motion)
        moments = _parse_gemini_response(motion, raw_response)
        self._cache[cache_key] = list(moments)
        return moments
```

**TechniqueCache 신설 박제 정신 (D-14)**:
- 영상 hash 계산 = SHA256 (S3 ETag 우선, fallback = 파일 streaming SHA256)
- Firestore path = `gemini_cache/{hash}` (top-level collection, uid 비의존)
- 저장 필드 = `{motion, key_moments_json, joint_expectations, confidence, model_version, scope_status, created_at}`
- nested-array 금지 → KeyMoment list = JSON 문자열로 박제 또는 flat dict array
- in-memory `_cache` layer + Firestore layer 2단계 (Pod 재시작 시 in-memory 손실 → Firestore 가 source of truth)
- lazy boto3 / firebase-admin import — 단위 테스트는 mock injection

---

#### `backend/tests/test_technique_cache.py` (new test)

**Analog:** `test_gemini_moment_extractor.py::TestExtractKeyMomentsCache` 섹션 + `test_technique.py` (lines 13-49)

**테스트 박제 패턴** (test_technique.py):
```python
import numpy as np

from sunity_shared.analysis import technique
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS


def _pose(straight: list[str], t: int = 20) -> np.ndarray:
    base = np.full(NUM_JOINTS, 100.0)
    for k in straight:
        base[JOINT_KEYS.index(k)] = 175.0
    return np.tile(base, (t, 1))


def test_straight_limbs_marked_extend():
    p = technique.FallbackRecognizer().recognize(_pose(["left_knee", "right_knee"]))
    assert p.expects_extension("left_knee")
```

**박제 정신**: hash collision 0, cache hit/miss 분기, Firestore mock, in-memory + persistent 2단 검증.

---

### Plan 5-03 — pipeline `_RECOGNIZER` swap + Pod 재사용

#### `backend/functions/pipeline/app.py` (modify line 120 + env switch)

**Analog (self):** `backend/functions/pipeline/app.py::_RECOGNIZER` (line 120) 박제 현재:

**현재 박제 (변경 대상)** (pipeline/app.py lines 117-120):
```python
# 기술 인식 어댑터 — swappable (technique.TechniqueRecognizer 프로토콜).
# 지금은 보수적 Fallback(모르면 안 깎음). Gemini/Pole-arina 어댑터로 교체 예정.
# technique 모듈은 numpy+skeleton 만 의존(가벼움) → 모듈 로드 시 즉시 생성 OK.
_RECOGNIZER: technique.TechniqueRecognizer = technique.FallbackRecognizer()
```

**Env switch 박제 패턴** (pipeline/app.py lines 71-78 — RunPod toggle 동일 패턴):
```python
# RunPod 위임 환경 — 운영에서만 set. 미설정 시 폴백(_process) 이라 개발은 그대로.
_RUNPOD_URL = os.environ.get("RUNPOD_ANALYZE_URL", "").strip()
_RUNPOD_TOKEN = os.environ.get("RUNPOD_AUTH_TOKEN", "").strip()
_RUNPOD_TIMEOUT_S = 10


def _runpod_enabled() -> bool:
    return bool(_RUNPOD_URL and _RUNPOD_TOKEN)
```

**Lazy adapter 박제 패턴** (pipeline/app.py lines 123-135):
```python
def _ensure_adapters() -> None:
    """폴백 처리(_process) 진입 시 1회 어댑터 생성 + lazy import.
    RunPod 모드에선 이 함수가 호출되지 않아 imageio·torch 도 import 안 됨."""
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    if _POSE_ESTIMATOR is None:
        from sunity_shared.analysis.pose_estimator import NlfPoseEstimator
        _POSE_ESTIMATOR = NlfPoseEstimator()
    if _COACH_WRITER is None:
        from sunity_shared.analysis.coach_writer import CerebrasCoachWriter
        _COACH_WRITER = CerebrasCoachWriter()
```

**_RECOGNIZER swap 박제 정신 (D-12, D-15, D-16)**:
- env `RECOGNIZER_BACKEND` (`gemini` | `fallback`, default `fallback`) — Pod env override
- `_RECOGNIZER` 초기화는 lazy (모듈 로드 시 X, `_process` 첫 호출 시 1회)
- Gemini 선택 시 `GeminiTechniqueRecognizer(extractor=GeminiMomentExtractor(), cache=TechniqueCache())` 합성
- API 키 / cache Firestore 의존성은 `recognize()` 첫 호출 시 lazy fetch
- `_process` 안에서 `profile = _RECOGNIZER.recognize(angles, frames=tmp_video_path)` — video path 주입 (현재 `recognize(angles)` 만 호출 line 230, frames 인자 추가)

**현재 호출처** (pipeline/app.py line 230):
```python
# 기술 인식(swappable) → 절대 차원(라인/안정성)은 기준 영상 없이 항상 산출.
profile = _RECOGNIZER.recognize(angles)
abs_dims = dimensions.absolute_dimension_scores(angles, profile)
```

**변경 후 박제 (D-12 Pod 안 1pass)**:
```python
# Plan 5-03: video path 도 recognize() 에 전달 — Gemini 어댑터가 영상 소비.
# FallbackRecognizer 는 frames=None 그대로 ignore (Protocol 호환).
profile = _RECOGNIZER.recognize(angles, frames=local_video_path)
```

→ `_angles_from_video` (line 146-153) 가 현재 tempfile 안에서 영상 처리 후 닫음 → tempfile 컨텍스트 확장 필요 (recognize 호출 시점까지 영상 path 살림).

---

#### `backend/runpod_inference/server.py` (no direct edit / pipeline 모듈 재사용)

**Analog (self):** `backend/runpod_inference/server.py::_load_pipeline_module` (lines 63-80)

**Pipeline 모듈 동적 import 박제 패턴** (server.py lines 59-80):
```python
_pipeline_lock = threading.Lock()
_pipeline_module: Any = None


def _load_pipeline_module() -> Any:
    """functions/pipeline/app.py 를 동적 임포트. 모듈 최상위에서 NLF 어댑터를
    초기화하므로(현재 코드 line 48~50), 이 함수가 처음 호출될 때 모델이 GPU 에 올라간다."""
    global _pipeline_module
    if _pipeline_module is not None:
        return _pipeline_module
    with _pipeline_lock:
        if _pipeline_module is not None:
            return _pipeline_module
        pipeline_path = _BACKEND / "functions" / "pipeline" / "app.py"
        spec = importlib.util.spec_from_file_location("sunity_pipeline_app", pipeline_path)
        ...
        spec.loader.exec_module(module)
        _pipeline_module = module
        log.info("pipeline 모듈 로드 + NLF 어댑터 워밍업 완료")
        return module
```

**Startup warmup 박제 패턴** (server.py lines 139-150):
```python
@app.on_event("startup")
def _warmup() -> None:
    """모델/어댑터 미리 GPU 메모리 로드. 실패해도 첫 /analyze 에서 재시도.
    pipeline 모듈은 어댑터 import 를 lazy 로 미루므로 _ensure_adapters() 까지
    명시적으로 호출 — startup 비용을 첫 요청이 아닌 부팅 시점에 지불."""
    log.info("RunPod 분석 서버 startup — auth=%s", "ON" if _AUTH_TOKEN else "OFF")
    try:
        mod = _load_pipeline_module()
        mod._ensure_adapters()
        log.info("어댑터 워밍업 완료 (NLF/ffmpeg/coach)")
    except Exception:
        log.exception("워밍업 실패 — 첫 요청 처리 시 재시도")
```

**박제 정신**: server.py 자체는 무수정. pipeline 모듈 import 만으로 `_RECOGNIZER` 가 env 에 따라 Gemini 어댑터로 자동 초기화 → "분기 0, 코드 1벌" 원칙 (Lambda fallback 경로와 RunPod GPU 경로 동일 코드).

---

#### `backend/tests/test_pipeline_recognizer_switch.py` (new test)

**Analog:** `backend/tests/test_pipeline_dispatch.py` (env switch 검증 패턴)

**박제 정신**:
- env `RECOGNIZER_BACKEND=gemini` → `_RECOGNIZER` instance type 검증
- env 미설정 → `FallbackRecognizer` 유지
- `_process` 호출 시 `profile.joint_expectations` 가 EXTEND/BENT_OK 라벨링 (mock Gemini 응답)
- 3 case fallback 검증 (timeout / low conf / unregistered) → FallbackRecognizer 위임 결과 동일

---

### Plan 5-04 — Pod env / requirements / setup.sh

#### `backend/runpod_inference/requirements.txt` (1줄 추가)

**Analog (self):** 본 파일 line 1-36

**현재 박제 (변경 대상)** (requirements.txt full file):
```
# RunPod Pod 위에서 server.py 가 의존하는 패키지.
# Pod base image 는 PyTorch + CUDA 가 이미 깔린 것을 가정 (RunPod PyTorch 2.4 등).

fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
pydantic>=2.5,<3.0

# S3 다운로드
boto3>=1.34,<2.0

# Firestore Admin (서비스 계정 JSON 으로 직접 초기화)
firebase-admin>=6.5,<7.0

# 영상 프레임 추출 (FfmpegFrameExtractor)
imageio>=2.34
imageio-ffmpeg>=0.5.1
```

**추가 박제 (Phase 5 D-13 + D-16)**:
```
# Phase 5 — Gemini 기술 인식기 (분류 한정).
# 신 SDK (google-genai) 만 사용 — legacy `google-generativeai` 는 새 AI Studio
# `AQ.` 키 포맷 미지원 (2026-06-01 박제, gemini_moment_extractor.py 주석 참조).
google-genai>=1.0,<2.0
```

---

#### `backend/runpod_inference/setup.sh` (env block 추가)

**Analog (self):** 본 파일 lines 113-125 (기존 환경변수 안내 block)

**현재 박제 (확장 대상)** (setup.sh lines 113-126):
```bash
echo "setup.sh 완료. 다음 명령으로 서버 기동:"
echo ""
echo "  cd $BACKEND"
echo "  export RUNPOD_AUTH_TOKEN=<생성>"
echo "  export AWS_ACCESS_KEY_ID=<...>"
echo "  export AWS_SECRET_ACCESS_KEY=<...>"
echo "  export AWS_DEFAULT_REGION=ap-northeast-2"
echo "  export FIREBASE_SA_PATH=/workspace/firebase-sa.json"
echo "  export CUDA_VISIBLE_DEVICES=0"
echo "  export MOTIONBERT_ROOT=$MOTIONBERT_ROOT"
echo "  uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1"
```

**추가 박제 (D-15 SSM lazy fetch path)**:
```bash
echo "  # Phase 5 Gemini 어댑터 — env or SSM Parameter Store fetch"
echo "  export RECOGNIZER_BACKEND=gemini  # 또는 'fallback' (기본)"
echo "  export GEMINI_API_KEY=\$(aws ssm get-parameter \\"
echo "    --name /sunity/motion/gemini-api-key \\"
echo "    --with-decryption \\"
echo "    --query 'Parameter.Value' --output text \\"
echo "    --region ap-northeast-2)"
```

**박제 정신**: setup.sh 안에서 SSM fetch 직접 실행 X (Pod 재기동 시 IAM 만료 위험). belle 가 server 기동 시점에 수동 export — gemini_moment_extractor.py 의 `_load_api_key` 가 env 우선 → SSM fallback 박제 path 와 동일 패턴.

---

### Plan 5-05 — sweep `--recognizer gemini` flag

#### `backend/research/evaluations/compare_rtmw_vs_ipsf.py` (modify)

**Analog (self):** `backend/research/evaluations/compare_rtmw_vs_ipsf.py::compute_line_angle_gates` (lines 323-346)

**현재 박제 (변경 대상)** (compare_rtmw_vs_ipsf.py lines 323-346):
```python
def compute_line_angle_gates(
    joint_angles: np.ndarray,
    pole_axis: PoleAxis,
) -> tuple[bool, bool]:
    """line_score + stability_score (angle proxy) 에서 5/5 PASS 여부 계산.

    T-23-03: line_score / angle_score = None 이면 False (N/A 를 PASS 로 카운트 금지).

    Returns:
        (line_pass, angle_pass) — bool. None 반환 시 False.
    """
    recognizer = FallbackRecognizer()
    profile = recognizer.recognize(joint_angles)

    ls = line_score(joint_angles, profile)
    line_pass = (ls is not None) and (ls >= 50)

    ss = stability_score(joint_angles)
    angle_pass = ss >= 50

    return line_pass, angle_pass
```

**Import 박제 (현재)** (line 58):
```python
from sunity_shared.analysis.technique import FallbackRecognizer
```

**변경 박제 정신 (D-12 sweep 재실행 게이트)**:
- CLI flag `--recognizer {fallback,gemini}` (default `fallback`)
- `gemini` 선택 시 `GeminiTechniqueRecognizer(extractor=GeminiMomentExtractor(), cache=TechniqueCache())` 합성
- `compute_line_angle_gates` 시그니처 확장: `(joint_angles, pole_axis, recognizer)` — DI
- video_path 가 sweep loop 안에서 살아있어야 함 (현재 코드 — frame extractor 단계에서 tempfile 닫지 않음)
- 5영상 sweep 결과 → JSON 보고서 (`phase1_ready_to_swap` 박제 위치 동일)
- 박제 [[gap-and-line-angle-mandatory-gates.md]] "강등/우회 금지" → ref-climb (의도된 빈 list) 는 within_tolerance_all=True 박제 (compare_rtmw_vs_ipsf.py:121 박제 이미 적용)

---

## Shared Patterns

### Lazy Import Boundary (D-16)

**Source:** `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` (lines 166-208, 291-309)
**Apply to:** All Plan 5-01 / 5-02 / 5-03 신설 / 수정 파일

**Excerpt:**
```python
def _call_gemini(self, video_uri: str, motion: str) -> str:
    try:
        from google import genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("google-genai 미설치 — Pod 에 `pip install google-genai` 필요.") from exc
    # ...

def _load_api_key() -> str:
    inline = os.environ.get("GEMINI_API_KEY")
    if inline:
        return inline
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(...) from exc
```

**박제 정신**: 모듈 로드 시점에 `google-genai`, `boto3`, `firebase-admin` import X — 로컬 단위 테스트 + Lambda 콜드스타트 보호.

---

### Reject Patterns (D-08 + analysis-objectivity-no-human-scores)

**Source:** `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` (lines 47-73, 129-163)
**Apply to:** GeminiTechniqueRecognizer 응답 처리 — 좌표/점수/판단 출력 감지 시 ValueError 즉시 발생

**Excerpt:**
```python
_COORDINATE_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bx\s*[:=]\s*-?\d", re.IGNORECASE),
    re.compile(r"keypoint", re.IGNORECASE),
    re.compile(r"좌표"),
    ...
)
_SCORE_REJECT_PATTERNS = (re.compile(r"\bscore\s*[:=]\s*\d", re.IGNORECASE), ...)
_JUDGMENT_REJECT_PATTERNS = (re.compile(r"심사"), re.compile(r"\bverdict\b", re.IGNORECASE), ...)


def _enforce_no_coordinate_or_score(text: str, *, context: str) -> None:
    if not text:
        return
    for pat in _COORDINATE_REJECT_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 좌표 출력이 포함됨 ({context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"Gemini 역할은 시점 분류 + 자연어 번역만 — 좌표 출력 금지 "
                f"(REQUIREMENTS.md SCORE-01, memory analysis-objectivity-no-human-scores)."
            )
    # ... same for score and judgment
```

**박제 정신**: GeminiTechniqueRecognizer 가 `extract_key_moments()` 결과를 받자마자 응답 텍스트 재검증 (extractor 가 이미 1차 가드했지만 어댑터 layer 가 2차 가드). joint_expectations 에 점수/좌표 들어오면 즉시 ValueError.

---

### Singleton Module-Level State (D-12 Pod 1pass + D-14 cache)

**Source:** `backend/shared/python/sunity_shared/firestore_admin.py` (lines 18-31) + `backend/functions/pipeline/app.py` (lines 110-135)
**Apply to:** TechniqueCache, GeminiTechniqueRecognizer instance, Firestore client

**Excerpt:**
```python
# firestore_admin.py
_client = None


def _db():
    global _client
    if _client is not None:
        return _client
    _auth._ensure_firebase()
    from firebase_admin import firestore
    _client = firestore.client()
    return _client


# pipeline/app.py — adapter lazy init pattern
_FRAME_EXTRACTOR = None
_POSE_ESTIMATOR = None
_COACH_WRITER = None
_RECOGNIZER: technique.TechniqueRecognizer = technique.FallbackRecognizer()


def _ensure_adapters() -> None:
    global _FRAME_EXTRACTOR, _POSE_ESTIMATOR, _COACH_WRITER
    if _FRAME_EXTRACTOR is None:
        from sunity_shared.analysis.frame_extractor import FfmpegFrameExtractor
        _FRAME_EXTRACTOR = FfmpegFrameExtractor()
    # ...
```

**박제 정신**: Pod 단일 worker (`uvicorn --workers 1`) + Lambda 단일 invocation → 모듈 글로벌 caching 안전. RunPod 재기동 시 in-memory 손실 → Firestore `gemini_cache/{hash}` 가 source of truth.

---

### Firestore Flat-List Persistence ([[firestore-nested-array-flat]])

**Source:** `backend/shared/python/sunity_shared/firestore_admin.py::complete_analysis` (lines 45-70)
**Apply to:** TechniqueCache 박제 — Firestore 는 nested array 금지

**Excerpt:**
```python
if angles is not None:
    payload["angles"] = angles                     # flat list (T*J)
    payload["anglesJointKeys"] = angles_joint_keys  # list[str], 길이 J
    payload["anglesFrames"] = angles_frames        # int T
```

**박제 정신**: KeyMoment list → JSON string OR flat dict list (`[{motion, moment_key, ts, frame, conf}]`) 박제. joint_expectations dict 는 nested array 없음 (str → str map) → 그대로 박제 OK.

---

### Korean Error Messages + Spec Citations

**Source:** `backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py` (lines 140-163) + 모든 모듈 docstring 박제 패턴
**Apply to:** 모든 Phase 5 신설 / 수정 파일

**Excerpt:**
```python
raise ValueError(
    f"Gemini 응답에 좌표 출력이 포함됨 ({context}): "
    f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
    f"Gemini 역할은 시점 분류 + 자연어 번역만 — 좌표 출력 금지 "
    f"(REQUIREMENTS.md SCORE-01, memory analysis-objectivity-no-human-scores)."
)
```

**박제 정신**: 모든 에러 메시지 = 한국어 + 박제 spec 인용 (REQUIREMENTS.md / memory / D-* / 박제 파일 경로). 모듈 docstring = 박제 도입 plan (예: `Plan 01-13 T-1`) + 박제 정신 인용. CLAUDE.md "이모지 금지·슬롭 코드 금지" + cross-cutting "Cite the spec in comments" 정합.

---

## No Analog Found

| File | Role | Data Flow | Reason / Synthesis Source |
|------|------|-----------|---------------------------|
| (없음 — TechniqueCache 도 `firestore_admin.py` + `GeminiMomentExtractor._cache` 합성으로 박제 가능) | — | — | — |

5영상 yaml 정정 작업의 정은지 reference 측정값 추출 룰 (D-18: tolerance = ±15° / minimum = -25°) 은 본 phase 안에서 belle 승인 영역이며 codebase 박제 source 없음. → Plan 5-00 안에서 룰 박제 + belle 승인 후 수치 박제.

---

## Metadata

**Analog search scope:**
- `backend/shared/python/sunity_shared/{analysis,judging}/`
- `backend/functions/pipeline/`
- `backend/runpod_inference/`
- `backend/research/{spikes,evaluations}/`
- `backend/tests/`
- `backend/judging_data/criteria/`

**Files scanned:** 27 (analog candidates) + 6 (auxiliary: skeleton, models, dimensions, loader, README, judging __init__)

**Files read in full for pattern extraction (8):**
- `gemini_moment_extractor.py` (513 lines, primary spike base)
- `technique.py` (88 lines, Protocol + FallbackRecognizer)
- `firestore_admin.py` (133 lines, singleton + flat-list)
- `pipeline/app.py` (367 lines, _RECOGNIZER swap point)
- `runpod_inference/server.py` (187 lines, pipeline 모듈 import 박제)
- `runpod_inference/requirements.txt` + `setup.sh` (config 박제)
- `ref-{climb, foxtop, foxtop-split, invert, sideway-spin}.yaml` (yaml source 박제)
- `test_gemini_moment_extractor.py` + `test_technique.py` (test 박제 패턴)

**Pattern extraction date:** 2026-06-04

**박제 정신 정합 확인:**
- D-16 lazy import — `gemini_moment_extractor.py` 박제 패턴 그대로 GeminiTechniqueRecognizer 에 박제
- D-08 reject patterns — 3종 정규식 가드 어댑터 layer 에서 2차 박제
- D-12 Pod 1pass — `pipeline._process` 안 `_RECOGNIZER.recognize(angles, frames=video_path)` 단일 흐름
- D-14 Firestore hash cache — firestore_admin singleton + flat-list 박제 패턴 재사용
- D-15 SSM lazy fetch — gemini_moment_extractor.py `_load_api_key` 박제 그대로
- D-17 yaml source 정정 — Plan 5-00 측정 spike + yaml 5개 rewrite (정은지 reference 분기 2 path)
- [[gsd-pod-work-push-first.md]] — 각 Plan = commit + push 단위. Pod 동기화 후 검증
- IPSF-LOOKUP.md (가+다) 옵션 — scope 5영상 유지 + yaml source 정은지 reference 박제
