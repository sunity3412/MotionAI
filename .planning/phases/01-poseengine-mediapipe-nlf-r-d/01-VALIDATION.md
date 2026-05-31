---
phase: 1
slug: poseengine-mediapipe-nlf-r-d
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: RESEARCH.md §Validation Architecture (line 968).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8 (이미 설치 — `backend/requirements-dev.txt`) |
| **Config file** | 없음 (pytest 기본). `backend/tests/conftest.py` 존재 |
| **Quick run command** | `cd backend && pytest tests/ -x` |
| **Full suite command** | `cd backend && pytest tests/` |
| **Estimated runtime** | ~10-30s (현재 ~20 tests; +5-10 unit tests 추가 예정) |

MediaPipe·OpenCV·scipy는 무거우니 단위 테스트에서는 **mock**으로 대체. 실 모델 추론은 `compare_engines.py`(수동 + RunPod) 또는 RunPod Pod에서.

---

## Sampling Rate

- **After every task commit:** `cd backend && pytest tests/ -x` (~10-30s)
- **After every plan wave:** 같은 전체 suite + Wave 종료 시 통합 smoke
- **Before `/gsd-verify-work`:** 전체 suite 통과 + `compare_engines.py` 실행 + `summary.phase1_ready_to_swap == true` (D-13~D-16)
- **Max feedback latency:** 30s

---

## Per-Task Verification Map

| Req ID | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|--------|----------|------------|-----------|-------------------|-------------|--------|
| POSE-01 | `PoseEngine` Protocol 정의 + `MediaPipePoseEngine.estimate()` 반환 shape/타입 | — | unit | `pytest backend/tests/test_pose_engine_interface.py -x` | ❌ W0 | ⬜ pending |
| POSE-01 | `MediaPipe33ToCOCO17Adapter` 17 키포인트 + 폴 확장 (toe/heel/grip) 정확 추출 | — | unit | `pytest backend/tests/test_adapter_mediapipe_to_coco17.py -x` | ❌ W0 | ⬜ pending |
| POSE-01 | `NoHumanError` 발생 (전 프레임 미감지 mock) | — | unit | `pytest backend/tests/test_pose_engine_interface.py::test_no_human -x` | ❌ W0 | ⬜ pending |
| POSE-01 | NLF 격리 — `from sunity_shared.analysis.pose_engines.nlf import ...` ImportError | T-1-01 | unit (구조 검증) | `pytest backend/tests/test_nlf_isolation.py -x` | ❌ W0 | ⬜ pending |
| POSE-01 | `pipeline._process` MediaPipe 경로로 동작 (mock PoseEngine) | — | integration | `pytest backend/tests/test_pipeline_dispatch.py -x` | ✅ 존재 (mock case 추가) | ⬜ pending |
| POSE-02 | `HoughPoleDetector.detect()` 수직 폴 영상에서 `PoleAxis` 반환 | — | unit | `pytest backend/tests/test_pole_detector.py -x` | ❌ W0 | ⬜ pending |
| POSE-02 | 검출 실패 시 `PoleAxis(source='vertical_fallback', confidence='low')` 반환 | — | unit | `pytest backend/tests/test_pole_detector.py::test_fallback -x` | ❌ W0 | ⬜ pending |
| POSE-02 | `PoleAxisAligner.align()` 회전행렬 적용 + 항등성 (이미 Z 축이면 변경 없음) | — | unit | `pytest backend/tests/test_pole_aligner.py -x` | ❌ W0 | ⬜ pending |
| POSE-02 | `confidence = visibility × presence` 변환식 정확 + 임계값 미만 프레임 표기 | — | unit | `pytest backend/tests/test_pose_engine_interface.py::test_confidence_conversion -x` | ❌ W0 | ⬜ pending |
| Success #5 (회귀) | `compare_engines.py` 5영상 처리 + JSON 출력 + `summary.phase1_ready_to_swap` 계산 | — | manual + script | `python -m backend.research.evaluations.compare_engines --motions ...` (NLF 측은 RunPod, 또는 mock smoke) | ❌ W0 | ⬜ pending |
| Success #6 (lockstep) | TS `PoseFrame` ↔ Python `PoseFrame` 필드 일치 | — | manual | `grep "interface PoseFrame" app/src/types/analysis.ts && grep "class PoseFrame\\|PoseFrame =" backend/shared/python/sunity_shared/models.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_pose_engine_interface.py` — PoseEngine Protocol + MediaPipePoseEngine 단위 (mock mediapipe library)
- [ ] `backend/tests/test_adapter_mediapipe_to_coco17.py` — 33→17 + 폴 확장 변환 정확성 (fixture)
- [ ] `backend/tests/test_pole_detector.py` — HoughPoleDetector 정상·실패 케이스 (synthetic 영상 fixture)
- [ ] `backend/tests/test_pole_aligner.py` — 회전행렬 적용 (numerical 테스트)
- [ ] `backend/tests/test_nlf_isolation.py` — `import` 시 ImportError 검증
- [ ] `backend/tests/fixtures/` — 작은 synthetic frames (~3 frames, 64x64) — 어댑터/변환 테스트용 (MediaPipe 호출 없이)
- [ ] `backend/research/evaluations/compare_engines.py` (RESEARCH.md Code Example 4 기반)
- [ ] 기존 `backend/tests/test_pipeline_dispatch.py`에 MediaPipe mock case 추가

Framework install: 이미 설치됨. MediaPipe·OpenCV·scipy는 `backend/runpod_inference/requirements.txt`에 추가 (Pod용). 로컬 단위 테스트는 mediapipe import를 mock으로 대체.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MediaPipe Heavy 추론 속도 frame당 ms 측정 (Lambda CPU SLA 적합성) | D-15 ④ | 실 환경 추론 필요, Lambda·Pod 모두 측정 | RunPod Pod에서 `compare_engines.py` 실행 후 `inference_ms_per_frame` 필드 확인. Lambda는 ARM64 wheel 부재로 측정 불가 (Pitfall 1 참조) |
| 정은지 영상 5개 회귀 검증 — MediaPipe vs NLF 점수 갭 ±5점, 정은지 ≥70점, Top-3 원인 ≥2/3 겹침 | D-13~D-15 ① ② | belle가 영상 제공 + 결과 검토 필요 | `compare_engines.py` 실행 → `01-COMPARE-REPORT.md` 생성 → belle 검토 후 atomic swap 승인 |
| 폴 확장 landmark (toe/heel/grip) MediaPipe 33 인덱스 매핑 정확성 (A1) | POSE-01 | mediapipe 공식 매핑 테이블 미발견 — visual 검증 필요 | mediapipe samples GitHub 또는 정은지 영상 1개에 33 landmark overlay 렌더링 → toe/heel/grip 위치 시각 확인 |
| `pose_landmarker_heavy.task` 모델 파일 배포 후 RunPod 콜드스타트 영향 | Claude Discretion (Q2) | 콜드스타트는 실측 필요 | RunPod Pod 재시작 → 첫 요청까지 시간 측정 (S3 다운로드 + 모델 로드) |

---

## Validation Sign-Off

- [ ] 모든 task가 `<automated>` verify 또는 Wave 0 의존성 보유
- [ ] Sampling 연속성: 3 task 연속으로 자동 verify 없는 경우 없음
- [ ] Wave 0가 모든 MISSING 참조 커버
- [ ] watch-mode 플래그 없음
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` frontmatter에 설정
- [ ] belle 확정 필요 사항 (A1 폴 확장 매핑·A9 confidence 임계값) 합의 후 테스트 임계값 확정

**Approval:** pending
