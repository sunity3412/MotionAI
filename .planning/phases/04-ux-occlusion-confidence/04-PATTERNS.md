# Phase 4: Camera Angle AI — Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 14 (신규 생성 8 + 수정 6)
**Analogs found:** 13 / 14

> ⚠ SUPERSEDED CONTRACT NOTE (2026-06-13, 2차 리뷰 HIGH-3): 본 문서의 adapter 예시 중 tuple/None 반환 패턴 + `reshapeJoints3d(angles...)` 는 **폐기**. 최신 계약 = `SynthesisResult(status=applied|partial|skipped|failed)` (04-01) + `reshapePose3dData(result.joints3d...)` (04-02) + `identify_occlusion_targets` + joints3d 저장 위치 `result.joints3d` + joints3d source `keypoints_4ch[:,:,:3]`. 충돌 시 **04-DIRECT-REVIEW-RESPONSE.md + 04-01 PLAN 이 우선**한다. (executor 는 PATTERNS 의 옛 tuple/None 예시를 따르지 말 것.)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py` | interface/protocol | request-response | `backend/shared/python/sunity_shared/analysis/interfaces.py` | exact |
| `backend/shared/python/sunity_shared/analysis/synthesis/gemini_view_reasoner.py` | adapter/service | request-response | `backend/shared/python/sunity_shared/gemini/scene_finder.py` | exact |
| `backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py` | utility | transform | `backend/shared/python/sunity_shared/analysis/interfaces.py` (Protocol 경계) | role-match |
| `backend/shared/python/sunity_shared/analysis/synthesis/virtual_renderer.py` | utility | transform | `backend/shared/python/sunity_shared/gemini/scene_finder.py` (graceful degrade 패턴) | partial |
| `backend/shared/python/sunity_shared/models.py` (수정) | model/config | CRUD | 자기 자신 | exact |
| `backend/functions/pipeline/app.py` (수정) | service/controller | event-driven | 자기 자신 (`_call_wave1_scene_finder` wiring 패턴) | exact |
| `backend/runpod_inference/server.py` (수정) | service | event-driven | 자기 자신 (`_process_in_background` BackgroundTask 패턴) | exact |
| `backend/shared/python/sunity_shared/firestore_admin.py` (수정) | service | CRUD | 자기 자신 (`complete_analysis` flat 저장 패턴) | exact |
| `backend/tests/phase04/` (신규 6파일) | test | batch | `backend/tests/` 기존 pytest 패턴 | role-match |
| `app/src/components/PoseViewer3D.tsx` | component | request-response | `app/src/components/VideoCompare.tsx` | role-match |
| `app/src/components/AccuracyLimitBadge.tsx` | component | request-response | `app/src/app/analysis/result.tsx` occlusionBadge 패턴 | exact |
| `app/src/lib/joints.ts` | utility | transform | `app/src/lib/userAnalyses.ts` normalize 패턴 | role-match |
| `app/src/types/analysis.ts` (수정) | model/config | CRUD | 자기 자신 | exact |
| `app/src/theme/colors.ts` (수정) | config | CRUD | 자기 자신 (Phase 12 alias 추가 패턴) | exact |

---

## Pattern Assignments

### `backend/shared/python/sunity_shared/analysis/synthesis/interfaces.py` (interface/protocol, request-response)

**Analog:** `backend/shared/python/sunity_shared/analysis/interfaces.py`

**Imports pattern** (lines 1-27):
```python
"""무거운 합성 API 경계 (프로토콜 + 어댑터 위치).

Phase 4 변경:
  SynthesisAdapter : joint 시퀀스 → 합성 좌표 (Gemini / Cylindrical / Omni)
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
```

**Core Protocol pattern** (lines 42-85):
```python
class PoseEngine(Protocol):
    """프레임 시퀀스 → PoseFrame 리스트. 미감지 시 NoHumanError.

    PoseEstimator(구버전, DEPRECATED) 를 대체하는 신규 Protocol.
    ...
    D-24: 본 모듈은 어떤 백본 구현체도 직접 import 하지 않는다.
    """

    def estimate(
        self,
        frames: np.ndarray,       # (T,H,W,3) RGB uint8
        pole_axis: "PoleAxis",    # PoleDetector 산출
    ) -> "list[PoseFrame]":
        ...
```

**SynthesisAdapter 신규 선언 — 위 PoseEngine 패턴을 그대로 복사해 작성:**
```python
class SynthesisAdapter(Protocol):
    """AI 합성 어댑터 인터페이스 — Gemini / Cylindrical / Omni 동일 계약.

    D-18 PRIMARY: GeminiViewReasoner
    D-18 SECONDARY: CylindricalMeshAdapter
    D-27 Wave 4 stub: OmniVertexAdapter (인터페이스만, Vertex GA 후 활성화)

    중요 제약 (RESEARCH Anti-Patterns):
      - coco_array (DTW/kismam 입력) mutate 0 — 시각화 + KeypointReport 만 영향.
      - is_reference=True 시 합성 호출 0 (G4 가드).
      - Gemini 에 픽셀 좌표 생성 요청 0 — 좌표 추정(reasoning)만.
    """

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,        # (T, 17, 3) RTMW output
        confidence_sequence: np.ndarray,    # (T, 17) rtmw_score
        occluded_mask: np.ndarray,         # (T, 17) bool — 합성 대상
        scene_findings: dict,              # scene_finder.FindingFlags
    ) -> "SynthesisResult":  # ⚠ SUPERSEDED (BLOCKER-1) — 구 tuple 반환 폐기. 04-01 SynthesisResult(status=applied|partial|skipped|failed) 계약 사용. 이 예시 복사 금지.
        ...
```

---

### `backend/shared/python/sunity_shared/analysis/synthesis/gemini_view_reasoner.py` (adapter/service, request-response)

**Analog:** `backend/shared/python/sunity_shared/gemini/scene_finder.py`

**Imports pattern** (lines 1-60):
```python
"""Phase 17 Wave 1 — 영역 C Finding 장면 인식 (Gemini Flash).

박제 정신:
  · Graceful 폴백: `GeminiVisionCall.call()` 가 None 반환 시 빈 flag dict 반환 — 분석 흐름 차단 0.
  · Model 결정: `resolve_model("C", env_override=...)` 단일 source.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from .client import GeminiVisionCall
from .config import resolve_model
from .schemas import FindingFlags
```

**G4 가드 패턴** (lines 7-11 of docstring):
```python
"""
· G4 정은지 영상 가드: `is_reference=True + occlusion_severe=True` 동시 시 4 flag
  전체 폐기 (False) + `guardrail_triggered="G4_reference_occlusion_fp"` 박힘.
"""
```

**Graceful degrade 패턴** (lines 341-348 of pipeline/app.py):
```python
try:
    from sunity_shared.gemini.scene_finder import find_scene_flags
    return find_scene_flags(local_video_path, is_reference=is_reference)
except Exception as exc:  # noqa: BLE001 - 분석 흐름 차단 0 박제
    log.warning(
        "find_scene_flags raise — graceful skip (is_reference=%s): %s",
        is_reference,
        exc,
    )
    return None
```

**GeminiViewReasoner 구현 시 복사 원본 — scene_finder.py 의 `find_scene_flags` 함수 전체 구조:**
- `is_reference=True` → G4 가드 먼저 실행 (G5 확장: 합성 호출 0)
- `GeminiVisionCall.call()` None 반환 시 빈 추정 dict + `error="api_or_schema_fail"` 반환
- `log = logging.getLogger(__name__)` 모듈 레벨 logger
- 모델 string = `resolve_model("C", env_override="GEMINI_C_MODEL_OVERRIDE")` 패턴 재사용

**Gemini 프롬프트 구조** (Spike 003 박제 — RESEARCH.md Code Examples):
```python
# Source: .planning/spikes/003-gemini-vision-view-reasoning/run_spike.py
OCCLUDED_JOINT_REASONING_PROMPT = """
폴스포츠 동작 분석 전문가로서 RTMW 포즈 추정기가 신뢰도 미달로 추정하지 못한
관절 좌표를 영상과 주변 맥락으로 추정해 주세요.

분석 맥락:
- 기술: {motion_category}
- occlusion_severe: {occlusion_severe}
- camera_angle: {camera_angle}
- 폴 축 x 픽셀: {pole_axis_pixel_x}
- 고신뢰 anchor joints: {visible_anchors}
- 이전 프레임 포즈: {prev_frame_pose}
- 추정 필요 관절: {occluded_joints}

중요 제약:
- 픽셀 이미지 생성 금지. 좌표만 출력.
- 불확실한 경우 "indeterminate" 출력 (추정 거짓말 금지).
- 사람 점수/판단 라벨링 금지.

출력 형식 (JSON):
{{"joints": [{{"name": "lShoulder", "x": 0.45, "y": 0.23, "z_rel": -0.1, "confidence": 0.65}}, ...], "reasoning": "..."}}
"""
```

---

### `backend/shared/python/sunity_shared/analysis/synthesis/cylindrical_mesh.py` (utility, transform)

**Analog:** `backend/shared/python/sunity_shared/analysis/interfaces.py` Protocol 경계 + Spike 002b mesh_builder.py

**파일 헤더 패턴** (interfaces.py lines 1-17 복사):
```python
"""Spike 002b cylindrical humanoid mesh builder (trimesh MIT).

RTMW (T, 17, 3) joints → cylindrical mesh → pyrender 12 virtual camera view
→ RTMW 재추론 입력 이미지 생성.

라이선스: trimesh MIT, pyrender MIT, RTMW Apache-2.0 — 100% 상업 허용.
GPU 환경 전용 (pyrender EGL headless = RunPod CUDA). Mac local 개발 시
dummy render 반환 fallback 포함.

Spike 002b VALIDATED-SKELETON (2026-06-13).
"""

from __future__ import annotations
import os
import numpy as np

# EGL 초기화 순서 필수 — import pyrender 보다 먼저 (RESEARCH Pitfall 3).
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
```

**pyrender EGL 패턴** (RESEARCH.md Pattern 5):
```python
# Source: Spike 002b render.py
import os
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")  # import pyrender 보다 먼저
import pyrender

renderer = pyrender.OffscreenRenderer(viewport_width=256, viewport_height=256)
# ... render 12 views ...
renderer.delete()  # 반드시 명시적 해제 (GPU 메모리 관리)
```

---

### `backend/shared/python/sunity_shared/models.py` (수정 — 신규 warning code 추가)

**Analog:** 자기 자신 (lines 233-248)

**Warning code 카탈로그 위치 및 추가 패턴** (lines 233-248):
```python
# 20 warning code enum (docs/contract.md §9.8 mirror):
#   기존 13: occlusion_high_in_phase / layer2_unavailable / layer_disagreement_minor /
#           layer_disagreement_major / layer2_call_failed / motion_unrecognized /
#           motion_unrecognized_layer1_only / abnormal_release_during_hold /
#           partial_motion_video / video_too_short / heavy_occlusion /
#           entry_not_detected / all_frames_unreliable.
#   Cycle 1 신설 5: pole_line_missing / scale_unavailable /
#           preflight_label_gate_failed / fps_normalization_applied /
#           contact_evidence_only.
#   ...
#   Phase 4 신설 2: ai_synthesis_failed / ai_synthesis_partial
```

**body_normalizer.py 의 BODY_COMPARISON_WARNING_CODES frozenset 패턴** (lines 164-176):
```python
# R2 fix — 8 warning enum frozen (reference_source_pose_missing 포함).
BODY_COMPARISON_WARNING_CODES: frozenset[str] = frozenset({
    "low_confidence_normalization_off",
    "foreshortening_off",
    "shoulder_hip_ratio_off",
    "temporal_variance_high",
    "spatial_dispersion_high",
    "reference_profile_missing",
    "fallback_reference_not_found",
    "reference_source_pose_missing",  # R2 fix — 신규 8번째
    "target_torso_px_missing",        # WR-02 fix — 신규 9번째
})
```

**Phase 4 신규 warning frozenset 위치:** `models.py` 에 `SYNTHESIS_WARNING_CODES: frozenset[str]` 별도 선언 또는 기존 전역 frozenset 에 병합. `docs/contract.md §9.8` + `analysis.ts AnalysisErrorCode` 3-way 동시 갱신 필수.

---

### `backend/functions/pipeline/app.py` (수정 — synthesis wiring)

**Analog:** 자기 자신 (`_call_wave1_scene_finder` + `_call_wave2_keypoint_augmenter` 패턴, lines 320-370)

**Wave-gate 패턴** (lines 320-348):
```python
def _call_wave1_scene_finder(
    local_video_path: str | None,
    *,
    is_reference: bool = False,
) -> dict | None:
    """Wave 1 영역 C Finding 호출 진입점 — graceful 폴백 + skip 조건 박제.

    Skip 조건 (return None):
      · `GEMINI_FINDING_ENABLED` env = "0"/"false"/"" → 운영자 박제 차단 path.
      · `local_video_path` = None
      · find_scene_flags 예외 (객관성 가드 ValueError 등) → 흡수 + None.
    """
    if local_video_path is None:
        return None
    if not _finding_enabled():
        log.info("GEMINI_FINDING_ENABLED OFF — wave 1 skip")
        return None
    try:
        from sunity_shared.gemini.scene_finder import find_scene_flags
        return find_scene_flags(local_video_path, is_reference=is_reference)
    except Exception as exc:  # noqa: BLE001 - 분석 흐름 차단 0 박제
        log.warning(
            "find_scene_flags raise — graceful skip (is_reference=%s): %s",
            is_reference,
            exc,
        )
        return None
```

**D wave-gate 패턴** (lines 351-370):
```python
# Phase 17-03 Wave 2 — 영역 D Keypoint 보강 wiring
#
# 박제 정신:
#   · `_d_enabled()` — GEMINI_D_ENABLED env truthy (default OFF)
#   · occlusion_severe=True (wave 1 결과) → skip + None (게이트 1).
#   · GEMINI_D_ENABLED=0 → skip + None (게이트 2).
#   · **3D coco_array 행렬은 본 wave 입력/출력 모두 격리** (B2 hard gate).
```

**Phase 4 신규 wiring 패턴 — 위 `_call_wave1_scene_finder` 를 그대로 복사해 작성:**
```python
def _call_synthesis_adapter(
    joint_sequence: np.ndarray,        # (T, 17, 3)
    confidence_sequence: np.ndarray,   # (T, 17)
    scene_findings: dict | None,
    *,
    is_reference: bool = False,        # G4 가드 — True 시 호출 0
) -> tuple[np.ndarray, np.ndarray] | None:
    """⚠ SUPERSEDED (BLOCKER-1/BLOCKER-3) — 이 예시는 구 None/tuple 계약. 최신 = 04-01 SynthesisResult(status) 반환 + warning 은 ai_synthesis_meta["warnings"] (profile.extra_warnings 아님). 아래 코드 복사 금지 — 04-01 PLAN 우선.

    Phase 4 합성 어댑터 호출 — graceful 폴백 + skip 조건 박제.

    Skip 조건 (구 예시 — 최신은 SynthesisResult(status="skipped")):
      · is_reference=True → G4 가드 (D-10 박제).
      · SYNTHESIS_ENABLED env = "0" → 운영자 차단.
      · adapter 예외 → 흡수 + None + ai_synthesis_failed warning 주입.
    """
    if is_reference:
        log.info("synthesis skip — is_reference=True (G4 가드)")
        return None
    if not _synthesis_enabled():
        return None
    try:
        mask = identify_occlusion_targets(joint_sequence, confidence_sequence, scene_findings)
        if not mask.any():
            return None  # 합성 필요 target 없음 — 비용 0
        adapter = _get_synthesis_adapter()  # lazy singleton
        return adapter.synthesize_occluded_joints(
            joint_sequence, confidence_sequence, mask, scene_findings or {}
        )
    except Exception:  # noqa: BLE001
        log.exception("synthesis adapter 실패 — graceful degrade")
        return None
```

**⚠ SUPERSEDED (BLOCKER-1/BLOCKER-3)** — 아래 None/tuple/extra_warnings 패턴 폐기. 최신 = SynthesisResult.status 분기 + warning 은 `ai_synthesis_meta["warnings"]` (profile.extra_warnings 아님, 04-01 우선). 복사 금지:
```python
# R8 fix: extra_warnings injection (dataclasses.replace 우회 금지).
import dataclasses

extra_warnings: list[str] = []
synth_result = _call_synthesis_adapter(...)
if synth_result is None:
    extra_warnings.append("ai_synthesis_failed")  # models.py frozenset 에 추가 필수
else:
    merged_joints, merged_conf = synth_result

profile = dataclasses.replace(profile, extra_warnings=tuple(extra_warnings))
```

---

### `backend/runpod_inference/server.py` (수정 — BackgroundTask 내 synthesis 호출)

**Analog:** 자기 자신 (lines 105-130)

**BackgroundTask 패턴** (lines 105-130):
```python
def _process_in_background(bucket: str, key: str, uid: str, analysis_id: str) -> None:
    """pipeline.lambda_handler 의 try/except 와 동일 매핑.
    NoHumanError → ERR_NO_HUMAN, NotPoleMotionError → ERR_NOT_POLE_MOTION,
    그 외 → ERR_SERVER_ERROR."""
    try:
        pipeline_app = _load_pipeline_module()
        pipeline_app._process(bucket, key, uid, analysis_id)
        log.info("분석 완료 uid=%s analysisId=%s", uid, analysis_id)
    except NoHumanError:
        log.info("인체 미감지 uid=%s analysisId=%s", uid, analysis_id)
        firestore_admin.fail_analysis(
            uid,
            analysis_id,
            models.ERR_NO_HUMAN,
            models.ERROR_MESSAGE[models.ERR_NO_HUMAN],
        )
    except NotPoleMotionError:
        ...
    except Exception:  # noqa: BLE001
        ...
```

Phase 4 수정 없음 — `_process_in_background` 는 `pipeline_app._process` 를 그대로 호출하므로, synthesis wiring 이 `pipeline/app.py::_process` 안에 들어가면 자동 상속.

**requirements.txt 추가 필요:**
```
trimesh>=4.12.2
pyrender>=0.1.45
pyopengl
```

---

### `backend/shared/python/sunity_shared/firestore_admin.py` (수정 — aiSynthesisMeta flat 저장)

**Analog:** 자기 자신 (`complete_analysis` lines 601-660)

**complete_analysis flat 저장 패턴** (lines 601-660):
```python
def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
    body_comparison_report: dict | None = None,
    ...
    keypoint_report: dict | None = None,
) -> None:
    """status='done' + result (contract.md §4 AnalysisResult).

    angles 가 주어지면 추출된 관절각을 doc top-level 에 flat 저장한다 —
    Firestore 는 nested-array 금지라 flat list + anglesJointKeys(길이 J) +
    anglesFrames(T) 로 저장하고 읽는 쪽에서 reshape.
    """
    payload: dict = {
        "status": models.STATUS_DONE,
        "result": dict(result) if result else {},
        "updatedAt": int(time.time() * 1000),
    }
    if angles is not None:
        payload["angles"] = angles
        payload["anglesJointKeys"] = angles_joint_keys
        payload["anglesFrames"] = angles_frames
    if body_comparison_report is not None:
        _validate_flat_dict_no_nested_array(
            body_comparison_report, path="bodyComparisonReport"
        )
        payload["result"]["bodyComparisonReport"] = body_comparison_report
```

**Phase 4 aiSynthesisMeta 추가 패턴 — 위 `keypoint_report` 파라미터 추가 방식 그대로 복사:**
```python
# Phase 4 신규 파라미터 추가 위치 (complete_analysis 시그니처 확장)
    ai_synthesis_meta: dict | None = None,     # Phase 4 신규
) -> None:
    ...
    if ai_synthesis_meta is not None:
        # Firestore flat 저장 — nested-array 금지 (CLAUDE.md 박제)
        # 금지: {"synthesizedJoints": [[j1, j2], [j1, j2]]}  nested
        # 허용: {"synthesizedJoints": [j1, j2, j1, j2], "synthesizedJointsFrames": 30, ...}
        _validate_flat_dict_no_nested_array(ai_synthesis_meta, path="aiSynthesisMeta")
        payload["result"]["aiSynthesisMeta"] = ai_synthesis_meta
```

**_validate_flat_dict_no_nested_array 검증 패턴** (lines 45-101):
```python
def _validate_flat_dict_no_nested_array(payload: dict, *, path: str = "") -> None:
    """W5 (2026-06-08). Firestore nested-array 금지 보장.
    list[list] / list[dict-with-nested-list] reject.
    위반 시 TypeError + path 정보.
    """
```

---

### `app/src/types/analysis.ts` (수정 — aiSynthesisMeta 신규 필드)

**Analog:** 자기 자신 (lines 1-59)

**파일 헤더 + 수정 규칙** (lines 1-5):
```typescript
// 분析 데이터 계약 (앱 ↔ 백엔드 단일 소스). 사람용 명세: /docs/contract.md
// ...
// 이 파일이 바뀌면 docs/contract.md 와 백엔드도 같이 맞춰야 함.
```

**AnalysisResult 확장 패턴** — 기존 `ScoreDimension`, `AnalysisStatus` 와 동일한 string-literal union 스타일:
```typescript
// Phase 4 신규 warning code (models.py frozenset 3-way lockstep)
export type SynthesisWarningCode = 'ai_synthesis_failed' | 'ai_synthesis_partial';

// Phase 4 신규 — aiSynthesisMeta (contract.md §4 추가 필수)
export interface AiSynthesisMeta {
  synthesizedFrameCount: number;           // 합성 적용된 frame 수
  synthesizedJointKeys: string[];          // 합성 적용된 joint key 목록
  synthesisPath: 'gemini_view' | 'cylindrical_mesh' | 'none';
  degraded: boolean;                       // true = ai_synthesis_failed (graceful degrade)
}
```

---

### `app/src/lib/joints.ts` (신규 — flat → reshape 로더)

**Analog:** `app/src/lib/userAnalyses.ts` normalize 패턴 (lines 27-51)

**Imports 패턴** (userAnalyses.ts lines 8-20):
```typescript
import {
  collection,
  doc,
  onSnapshot,
  query,
  orderBy,
  type FirestoreError,
} from 'firebase/firestore';
import { useEffect, useState } from 'react';
import { auth, db } from './firebase';
import type { AnalysisDoc, AnalysisStatus } from '../types/analysis';
```

**normalize 방어 패턴** (userAnalyses.ts lines 27-51):
```typescript
function normalize(id: string, raw: Record<string, unknown>): AnalysisDoc | null {
  const mode = raw.mode === 'mode1' || raw.mode === 'mode3' ? raw.mode : null;
  // ...
  if (!mode || !status || fileName === null || createdAt == null)
    return null;
```

**joints.ts 신규 파일 핵심 패턴 — normalize 방어 스타일 동일하게:**
```typescript
// Firestore flat → (T, 17, 3) reshape 로더
// [[firestore-nested-array-flat]] — angles flat list + anglesJointKeys + anglesFrames
// 읽는 쪽에서 reshape (firestore_admin.complete_analysis 계약 정합).

/**
 * Firestore doc 에서 3D joint sequence 를 reshape 한다.
 * @param angles flat number[] (T * 17 * 3)
 * @param jointKeys string[] 길이 17
 * @param frames number (T)
 * @returns number[][][] (T, 17, 3) 또는 null (필드 없음 / 형식 불일치 — graceful)
 */
// ⚠ SUPERSEDED (BLOCKER-1) — reshapeJoints3d → reshapePose3dData (04-02), angles 파라미터 → (joints3d, joints3dKeys, joints3dFrames). result.angles 입력 금지. 이 예시 복사 금지.
export function reshapeJoints3d(
  angles: unknown,
  jointKeys: unknown,
  frames: unknown,
): number[][][] | null {
  if (!Array.isArray(angles) || !Array.isArray(jointKeys) || typeof frames !== 'number')
    return null;
  const T = frames;
  const J = jointKeys.length;  // 17
  if (angles.length !== T * J * 3) return null;
  // reshape (T, J, 3)
  const out: number[][][] = [];
  for (let t = 0; t < T; t++) {
    const frame: number[][] = [];
    for (let j = 0; j < J; j++) {
      const base = (t * J + j) * 3;
      frame.push([angles[base], angles[base + 1], angles[base + 2]]);
    }
    out.push(frame);
  }
  return out;
}
```

---

### `app/src/components/AccuracyLimitBadge.tsx` (신규 — D-08 정확도 제한 배지)

**Analog:** `app/src/app/analysis/result.tsx` occlusionBadge 패턴 (lines 723-730, 941-953)

**Imports 패턴** (result.tsx lines 1-51):
```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
// ...
import { colors, layout, radius, spacing, typography } from '../../theme';
```

**occlusionBadge JSX 패턴** (result.tsx lines 723-730):
```typescript
{showOcclusionBadge && (
  <View style={styles.occlusionBadge}>
    <Ionicons name="warning" size={12} color={colors.warnAmber} />
    <Text style={styles.occlusionBadgeText}>
      {`가림 ${occlusionPercent}%`}
    </Text>
  </View>
)}
```

**occlusionBadge StyleSheet 패턴** (result.tsx lines 941-953):
```typescript
occlusionBadge: {
  flexDirection: 'row',
  alignItems: 'center',
  gap: 4,
  paddingHorizontal: 8,
  paddingVertical: 3,
  borderRadius: 9,
  backgroundColor: colors.softBg,
},
occlusionBadgeText: {
  ...typography.captionSmall,
  color: colors.warnAmber,
  fontWeight: '600',
},
```

**AccuracyLimitBadge.tsx 신규 파일 — 위 occlusionBadge 스타일을 확장해 작성 (UI-SPEC Surface 2 정합):**
```typescript
// Phase 4 D-08 — "정확도 제한적" 배지 컴포넌트.
// 트리거: result.aiSynthesisMeta.warnings 배열에 'ai_synthesis_failed' 포함 시 (BLOCKER-3 — top-level warnings 아님).
// 블랙박스 원칙 (D-05): "AI 보완 실패" 문구 금지. "가림 구간 정확도가 제한적이에요" 만 허용.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

interface AccuracyLimitBadgeProps {
  visible: boolean;  // result.aiSynthesisMeta.warnings.includes('ai_synthesis_failed') (BLOCKER-3)
}

export function AccuracyLimitBadge({ visible }: AccuracyLimitBadgeProps) {
  if (!visible) return null;
  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Ionicons name="warning" size={14} color={colors.warnAmber} />
        <Text style={styles.title}>가림 구간 정확도가 제한적이에요</Text>
      </View>
      <Text style={styles.description}>측면 관절 추정 오차가 포함될 수 있어요.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.softBg,       // #F5F5F5 (accuracyLimitBg alias)
    borderWidth: 1,
    borderColor: colors.warnAmber,         // #E6A300
    borderRadius: radius.card,             // 15pt
    paddingVertical: 12,
    paddingHorizontal: spacing.screenX,    // 16pt
    marginTop: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    ...typography.boxLabel,               // 15pt 700
    color: colors.warnAmber,
  },
  description: {
    ...typography.caption,                // 12pt 400
    color: colors.textSecondary,
    marginTop: 4,
  },
});
```

---

### `app/src/components/PoseViewer3D.tsx` (신규 — Stage 3 R3F 3D viewer)

**Analog:** `app/src/components/VideoCompare.tsx` (레이아웃 구조 + theme 토큰 사용 패턴)

**VideoCompare 헤더 + imports 패턴** (VideoCompare.tsx lines 1-22):
```typescript
// 분析 결과 동작 비교 — 좌(내 영상) / 우(기준) 나란히 + 동기 재생.
//
// 영상 URL 이 비어 있을 때도 같은 레이아웃의 자리표시를 보여줘서, #7-follow 에서
// 실 영상이 들어오면 그대로 슬롯에 들어간다 ([[sim-scaffold-not-decorate]]).

import { Ionicons } from '@expo/vector-icons';
import { useVideoPlayer, VideoView, type VideoPlayer } from 'expo-video';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  type LayoutChangeEvent,
  PanResponder,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';
```

**PanResponder scrubber 패턴** (VideoCompare.tsx — timeline):
```typescript
// Phase 12 후속 B — currentTime 은 0.1s 정밀 표시.
function fmtTimeDecimal(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00.0';
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, '0')}`;
}
```

**overlay prop 패턴** (VideoCompare.tsx lines 32-35):
```typescript
/**
 * Phase 12 신설 (Plan 12-02 T4 / R7 render prop).
 * 영상 위 absolute overlay layer. pointerEvents 'none'.
 */
overlay?: (player: VideoPlayer | null) => React.ReactNode;
```

**PoseViewer3D.tsx 신규 파일 핵심 패턴 (RESEARCH.md Pattern 4 + UI-SPEC Surface 1):**
```typescript
// Phase 4 Wave 2 — Stage 3 사용자 3D 뷰어 (react-three-fiber + expo-three).
// Spike 005 VALIDATED-ARCHITECTURE (2026-06-13).
//
// 중요: /native import 경로 필수 — web path 사용 시 "window is not defined" 에러.
// expo-gl 은 Expo SDK 54 포함 — expo install expo-gl 로 버전 자동 맞춤.
//
// 배경 색: #F5F5F5 (colors.softBg) — 다크 배경 금지 (CLAUDE.md §4 / design.md §10).
// Three.js scene.background: 0xF5F5F5 (hex int, colors.softBg 정합).

import { Canvas } from '@react-three/fiber/native';  // /native 필수
import React, { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

interface PoseViewer3DProps {
  joints: number[][][] | null;      // (T, 17, 3) — reshapeJoints3d 결과
  referenceJoints?: number[][][] | null;  // mode1 전용
  ipsfViolationFrames?: number[];   // IPSF 위반 frame index → brand highlight
  currentFrame: number;
  onFrameChange: (frame: number) => void;
}

export function PoseViewer3D({
  joints,
  referenceJoints,
  ipsfViolationFrames,
  currentFrame,
  onFrameChange,
}: PoseViewer3DProps) {
  // joints null = Phase 4 이전 분석 doc — 섹션 자체 렌더 생략 (graceful)
  if (!joints) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.sectionTitle}>3D 자세 뷰어</Text>
        <Text style={styles.hint}>손가락으로 돌려보세요</Text>
      </View>
      {/* Canvas height 280pt (UI-SPEC) */}
      <View
        style={styles.canvas}
        accessibilityRole="image"
        accessibilityLabel="3D 자세 뷰어, 손가락으로 회전 가능"
      >
        {/* R3F Canvas — expo-three bridge via expo-gl GLView */}
        <Canvas gl={{ powerPreference: 'high-performance' }}>
          {/* scene.background = 0xF5F5F5 Three.js scene 초기화 시 설정 */}
          <ambientLight intensity={0.5} />
          {/* OrbitControls: drei/native 경로 확인 필요 (RESEARCH Open Q3) */}
          {/* fallback: react-native-gesture-handler PanResponder */}
          <SkeletonMesh
            joints={joints[currentFrame]}
            isIpsfViolation={ipsfViolationFrames?.includes(currentFrame) ?? false}
          />
          {referenceJoints && (
            <SkeletonMesh
              joints={referenceJoints[currentFrame]}
              isReference
            />
          )}
        </Canvas>
      </View>
      {/* 카메라 preset 버튼 4개 */}
      <CameraPresetBar />
      {/* 시간축 scrubber */}
      <TimelineScrubber
        totalFrames={joints.length}
        currentFrame={currentFrame}
        onFrameChange={onFrameChange}
      />
    </View>
  );
}
```

**StyleSheet 패턴 — VideoCompare 의 styles 구조 그대로 복사:**
```typescript
const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.bg,
    borderRadius: radius.card,   // 15pt
    borderWidth: 1,
    borderColor: colors.divider,
    overflow: 'hidden',
    marginTop: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.screenX,
    paddingVertical: 12,
  },
  sectionTitle: {
    ...typography.sectionTitle,  // 20pt 700
    color: colors.textPrimary,
  },
  hint: {
    ...typography.captionSmall,  // 10pt 400
    color: colors.textSecondary,
  },
  canvas: {
    height: 280,                 // UI-SPEC 고정값
    backgroundColor: colors.softBg,  // #F5F5F5 — 다크 배경 금지
  },
});
```

---

### `app/src/app/analysis/result.tsx` (수정 — PoseViewer3D 섹션 + AccuracyLimitBadge 삽입)

**Analog:** 자기 자신 (기존 VideoCompare 섹션 삽입 패턴 + occlusionBadge 패턴)

**섹션 삽입 패턴** (result.tsx lines 717-731 — occlusionBadge 사례):
```typescript
{/* ── 영역 X: Phase 4 신규 영역 설명 ─ */}
<View style={styles.sectionHeader}>
  <Text style={styles.sectionTitle}>세부 점수</Text>
  {showOcclusionBadge && (
    <View style={styles.occlusionBadge}>
      <Ionicons name="warning" size={12} color={colors.warnAmber} />
      <Text style={styles.occlusionBadgeText}>
        {`가림 ${occlusionPercent}%`}
      </Text>
    </View>
  )}
</View>
```

**Phase 4 result.tsx 수정 위치 (UI-SPEC 배치 순서):**
```typescript
{/* [헤더 하단] AccuracyLimitBadge — ai_synthesis_failed warning 있을 때 */}
<AccuracyLimitBadge
  visible={hasSynthesisWarning(result, 'ai_synthesis_failed')}  /* BLOCKER-3: = result.aiSynthesisMeta.warnings.includes(...), top-level result.warnings 아님 */
/>

{/* [VideoCompare 바로 아래] PoseViewer3D — joints3d 있을 때만 (Wave 2) */}
{joints3d && (
  <PoseViewer3D
    joints={joints3d}
    referenceJoints={refMotion?.joints3d ?? null}
    ipsfViolationFrames={ipsfViolationFrames}
    currentFrame={currentFrame}
    onFrameChange={setCurrentFrame}
  />
)}
```

---

### `app/src/theme/colors.ts` (수정 — Phase 4 alias 토큰 추가)

**Analog:** 자기 자신 (lines 37-53 — Phase 12 신설 토큰 패턴)

**Phase 12 alias 추가 패턴** (colors.ts lines 37-53):
```typescript
// ── Phase 12 신설 토큰 (UI-SPEC §1) ──────────────────────────────────
// 기존 brand #FF4B33 는 변경 0 (CLAUDE.md §4 / D-12-U5). 신규 키만 추가.
brandSoft: '#FFD9D2', // Phase 9 작은 카드 chip 배경
brandBg: '#FFE5E0',  // 옥타곤 outer ring 톤
softBg: '#F5F5F5',   // jointHint chip 배경
estimateGray: '#B0B0B0', // 저신뢰 "추정 N°" 컬러
...
warnAmber: '#E6A300', // ⚠ occlusion badge
```

**Phase 4 신규 alias 추가 (UI-SPEC Color 섹션):**
```typescript
// ── Phase 4 신설 토큰 ─────────────────────────────────────────────────
// alias 방식 — 기존 토큰 hex 복사 금지, softBg / neutralDark / brand / textSecondary alias.
viewer3dBg: '#F5F5F5',         // 3D 캔버스 배경 (softBg alias)
viewer3dBone: '#1F2024',       // stick figure 뼈대 (neutralDark alias)
viewer3dJoint: '#FF4B33',      // IPSF 위반 관절 highlight (brand alias)
viewer3dJointNormal: '#ACACAC', // 정상 관절 점 (textSecondary alias)
accuracyLimitBg: '#F5F5F5',    // "정확도 제한적" 배지 배경 (softBg alias)
accuracyLimitText: '#E6A300',  // "정확도 제한적" 배지 텍스트 (warnAmber alias)
```

---

## Shared Patterns

### Graceful Degrade + Warning Injection
**Source:** `backend/functions/pipeline/app.py` lines 320-348 (`_call_wave1_scene_finder`) + `backend/shared/python/sunity_shared/analysis/body_normalizer.py` lines 164-176 (BODY_COMPARISON_WARNING_CODES)
**Apply to:** `synthesis/gemini_view_reasoner.py`, `synthesis/cylindrical_mesh.py`, `pipeline/app.py` synthesis wiring
```python
try:
    result = adapter.synthesize_occluded_joints(...)
except Exception:  # noqa: BLE001 - 분析 흐름 차단 0 박제
    log.exception("synthesis adapter 실패 — graceful degrade")
    extra_warnings = ["ai_synthesis_failed"]
    # dataclasses.replace 로 profile 에 주입 (R8 fix 패턴)
    profile = dataclasses.replace(profile, extra_warnings=tuple(extra_warnings))
```

### Protocol 기반 Adapter 격리
**Source:** `backend/shared/python/sunity_shared/analysis/interfaces.py` lines 42-85 (PoseEngine Protocol)
**Apply to:** `synthesis/interfaces.py` SynthesisAdapter, Wave 4 OmniVertexAdapter stub
```python
from __future__ import annotations
from typing import Protocol
import numpy as np

class SynthesisAdapter(Protocol):
    def synthesize_occluded_joints(self, ...) -> tuple[np.ndarray, np.ndarray]:
        ...
```

### G4 is_reference 가드
**Source:** `backend/shared/python/sunity_shared/gemini/scene_finder.py` lines 7-11 (docstring)
**Apply to:** `pipeline/app.py` `_call_synthesis_adapter`, `synthesis/gemini_view_reasoner.py`
```python
# G4 guard: is_reference=True 시 합성 호출 0
if is_reference:
    log.info("synthesis skip — is_reference=True (G4 가드)")
    return None
```

### Firestore Flat 저장 + _validate_flat_dict_no_nested_array
**Source:** `backend/shared/python/sunity_shared/firestore_admin.py` lines 45-101, 601-660
**Apply to:** `firestore_admin.complete_analysis` aiSynthesisMeta 파라미터 추가
```python
# 금지: {"synthesizedJoints": [[j1, j2], [j1, j2]]}  ← nested
# 허용: {"synthesizedJoints": [j1, j2, j1, j2], "synthesizedJointsFrames": 30}
if ai_synthesis_meta is not None:
    _validate_flat_dict_no_nested_array(ai_synthesis_meta, path="aiSynthesisMeta")
    payload["result"]["aiSynthesisMeta"] = ai_synthesis_meta
```

### Theme 토큰 전용 (하드코딩 금지)
**Source:** `app/src/theme/colors.ts` + `app/src/app/analysis/result.tsx` styles
**Apply to:** `PoseViewer3D.tsx`, `AccuracyLimitBadge.tsx`
```typescript
// 모든 색/간격/typography 은 토큰만 사용
import { colors, radius, spacing, typography } from '../theme';
// 직접 hex 하드코딩 금지 (CLAUDE.md §5)
```

### Korean 에러 문구 + 인라인 상태
**Source:** `app/src/app/analysis/result.tsx` occlusionBadge + estimateGray 패턴
**Apply to:** `AccuracyLimitBadge.tsx`, `result.tsx` 수정
```typescript
// 블랙박스 원칙 (D-05): "AI 보완 실패" 금지, "가림 구간 정확도가 제한적이에요" 허용
// Phase 12.5 "추정" 톤 유지
```

### 3-way Lockstep (contract.md + models.py + analysis.ts)
**Source:** `app/src/types/analysis.ts` lines 1-5 주석
**Apply to:** `aiSynthesisMeta` 신규 필드 추가 시
```typescript
// 이 파일이 바뀌면 docs/contract.md 와 백엔드도 같이 맞춰야 함.
// models.py warning frozenset + analysis.ts SynthesisWarningCode + contract.md §9.8
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/src/components/PoseViewer3D/SkeletonMesh.tsx` | component | transform | Three.js stick figure 렌더 로직 — 프로젝트에 Three.js 컴포넌트 선례 없음. RESEARCH.md Pattern 4 (SkeletonMesh 구조) + Three.js 공식 docs 참조 필요. |

---

## Metadata

**Analog search scope:**
- `backend/shared/python/sunity_shared/` (interfaces.py, temporal.py, force_signals.py, body_normalizer.py, firestore_admin.py, models.py, gemini/scene_finder.py, analysis/gemini_technique_recognizer.py)
- `backend/functions/pipeline/app.py`
- `backend/runpod_inference/server.py`
- `app/src/components/VideoCompare.tsx`, `app/src/app/analysis/result.tsx`
- `app/src/lib/userAnalyses.ts`, `app/src/types/analysis.ts`, `app/src/theme/colors.ts`

**Files scanned:** 15
**Pattern extraction date:** 2026-06-13
