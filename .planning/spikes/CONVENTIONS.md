# Spike Conventions

Phase 4 Camera Angle AI spike 세션 (2026-06-13) 에서 박제된 패턴.

## Stack

- **Python 3.12+** (운영 Lambda 정합)
- **numpy** (BSD) — joint sequence / metric 산출
- **trimesh** (MIT) — humanoid mesh (002b)
- **pyrender** (MIT) — virtual camera render (002b, RunPod GPU 위임)
- **dataclasses** — PathOutput / EvalReport / IPSFCriterion 박제
- venv = `python3 -m venv .venv` (Mac PEP 668 정합)

## Structure

각 spike 디렉토리 표준:
```
NNN-name/
  README.md            # frontmatter + What/Research/Trail/Results
  run_spike.py         # smoke test entry (`python3 run_spike.py`)
  *.py                 # 기능별 모듈 (mesh_builder.py / metrics.py / dataset.py)
  spike_report.json    # 박제 + CI 결과 산출
  humanoid.obj, etc.   # 박제 fixture (RunPod 위임 input)
```

Spike 001 의 `metrics.py` 는 다른 spike 가 `sys.path.insert` 로 재사용 — 공통 평가 harness 패턴.

## Patterns

### License-clear stack 우선
- belle 박제 [`rtmw-clean-weight-release-gate`] + [`license-blocklist-pose`] 정합
- 의존성 추가 시 license check 필수 (transitive 까지)
- Research-only weight (SMPL-X / MagicMan / NLF / WHAM / SPEC) 는 **완전 최후의 보류** (belle 명시 2026-06-13)

### NotebookLM IPSF lookup 우선
- belle 박제 [`notebook-lm-pole-sports`] — `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3`
- 폴스포츠 도메인 / IPSF 임계값 질문은 belle 한테 묻지 말고 NLM query (citation 포함 반환)
- 결과는 `ipsf_criteria.py` (Spike 001) 에 `source_ref` 필드로 박제

### Phase 17 Gemini Vision 통합 위에 build
- belle 박제 [`gemini-vision-active-use`] + [`gemini-latest-model-versions`]
- `gemini-3.1-pro-preview` (Pro) / `gemini-3.5-flash` (Flash, 2.5 영구 금지)
- Spike 003 의 multimodal view reasoning = Phase 17 통합 위에 신규 호출 path

### 평가 metric = IPSF GeometricCriterion
- belle 박제 [`analysis-objectivity-no-human-scores`] — 사람 점수 라벨링 영구 금지
- 모든 metric 에 `source_ref` 박제 (IPSF page citation)
- Phase 4 axis (a)(b)(c) ↔ IPSF criterion 매핑 = `PHASE4_EVAL_AXIS_MAPPING`

### RunPod GPU 위임 패턴
- belle 박제 [`pod-ops-claude-runs`] — Pod SSH / Lambda env / mock E2E 는 Claude 가 실행
- local spike 단계 = skeleton + smoke test
- 실 추론은 RunPod 위임 (별도 task)
- 의존성: pyrender / pyopengl-egl 은 RunPod 에서 설치

## Tools & Libraries

| Package | Version | License | Purpose |
|---|---|---|---|
| numpy | 2.4+ | BSD | joint / metric |
| trimesh | 4.12+ | MIT | humanoid mesh (002b) |
| pyrender | (latest) | MIT | virtual render (002b RunPod) |
| pyopengl-egl | (latest) | BSD | headless render (002b RunPod) |
| google-generativeai | (latest) | Apache-2.0 | Gemini Vision (003) |

**Avoid:**
- SMPL-X / SMPLify-X / SMPL — Max-Planck research-only (belle 정정 박제: 완전 최후의 보류, 880만원/yr)
- MagicMan / CameraHMR / WHAM / SPEC — transitive 비상업 (rtmw-clean-weight-release-gate 함정)
- Higgsfield API — public API 미존재 + ToS §5.1(iii) 차단
- AGORA / 3DPW / EMDB / BEDLAM / THuman / 2K2K — 모두 research-only

## belle 박제 핵심 (이 세션)

| 박제 | 출처 | 영향 |
|---|---|---|
| SMPL-X = 완전 최후의 보류 | 2026-06-13 belle 명시 | 모든 spike scope SMPL-X 의존 제거 |
| Higgsfield = closed wrapper, ToS 차단 | Spike 002a | 외부 API 단일 의존 production 금지 |
| Gemini = PRIMARY PATH | belle "Gemini 최대한 활용" | Phase 17 통합 위에 Spike 003 신규 |
| IPSF Page 19 split = Camera Angle AI 의 IPSF 근거 | NLM lookup | 모든 metric 의 ground truth |
| Cylindrical mesh = license-clear 자체 path | belle 옵션 A 선택 | Spike 002b scope 재정의 |
