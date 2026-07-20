---
phase: 31-api-visual-correction
plan: 05
subsystem: backend/analysis
tags: [external-api, wan2.7, gemini-judge, ssrf, decompression-bomb, async-only]
requires:
  - 31-01 (smoke RESULTS.json — chosen_model / sync / request_params)
  - 31-02 (models.VISUAL_FAILURE_REASONS — 실패 사유 단일 출처)
provides:
  - sunity_shared.analysis.interfaces.ImageEditEngine / VideoEditEngine (Protocol)
  - sunity_shared.analysis.visual_gen.WanImageAdapter / WanVideoEditAdapter
  - visual_gen.safe_decode_image (judge + 31-06 pose gate 공용 bomb 방어)
  - visual_gen.download_vendor_asset / DownloadedAsset
  - visual_gen.judge_corrected_pose / JudgeVerdict / judge_display_pass / judge_training_pass
  - visual_gen.IMAGE_ENGINE_SYNC / IMAGE_ENGINE_BLOCKED / derive_engine_blocked (릴리스 게이트 입력)
  - visual_gen.PROMPT_VERSION = "judge-v1"
affects:
  - 31-06 (pose gate — safe_decode_image import)
  - 31-09 (워커 — 이 모듈이 유일한 외부 API 경로, 임계값 env 주입)
  - 31-12 (배포 게이트 — IMAGE_ENGINE_BLOCKED 소비)
  - 31-13 (calibration — judge_*_pass 임계값 grid + PROMPT_VERSION 재현성)
tech-stack:
  added: []
  patterns:
    - stdlib urllib 전용 외부 호출 (SDK 미반입 — Lambda 250MB)
    - frozen dataclass + __post_init__ 계약 검증
    - Protocol 어댑터 경계 (구현은 형제 모듈)
    - PIL lazy import (모듈 로드는 Pillow 없이 성공)
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/visual_gen.py (837줄)
  modified:
    - backend/shared/python/sunity_shared/analysis/interfaces.py (Protocol 2종 추가)
    - backend/tests/phase31/test_visual_gen.py (스캐폴드 → 58 테스트, 762줄)
decisions:
  - "비-JSON 벤더 응답은 빈 dict 가 아니라 ValueError → vendor_error (계획 대비 강화)"
  - "RESULTS.json 은 런타임 미독 — 값 전사 + 테스트 대조로 드리프트 방어"
  - "judge 축 7종은 보존 6 + correction_visible 1 — 전면 재생성 실패 유형 차단"
metrics:
  duration: 약 50분
  tasks: 3
  commits: 3
  tests: 58 (phase31 전체 162 green)
  completed: 2026-07-20
---

# Phase 31 Plan 05: 외부 생성 API 계층 Summary

Wan2.7 이미지·영상 어댑터(create_task/poll), 공용 이미지 bomb 방어, SSRF 차단 다운로드
경계, before/after 보존 judge를 stdlib urllib만으로 구현 — 신규 패키지 0.

## 무엇을 만들었나

| 구성물 | 역할 | 계약 근거 |
|--------|------|-----------|
| `ImageEditEngine` / `VideoEditEngine` | 이미지·영상 **양쪽** create_task + poll | B2-02 |
| `VendorTaskCreated` / `VendorPollResult` | frozen typed 반환 (dict\|None 금지) | M-08 |
| `WanImageAdapter` | wan2.7-image-pro, RESULTS.json request_params 고정 | D-02 |
| `WanVideoEditAdapter` | wan2.7-videoedit 720P/watermark False/seed 42 | amended D-04 |
| `IMAGE_ENGINE_SYNC` / `IMAGE_ENGINE_BLOCKED` | async-only 릴리스 게이트 입력 | B4-02 |
| `safe_decode_image` | 3중 cap bomb 방어 (judge + 31-06 공용) | H4-06 |
| `download_vendor_asset` / `DownloadedAsset` | /tmp 스트리밍 + sha256 + 경계 7종 | H2-04/H2-05/H3-05 |
| `prepare_judge_payload` | safe_decode → EXIF 제거·2048px·JPEG → 16MB 상한 | H3-03 |
| `judge_corrected_pose` / `JudgeVerdict` | Gemini REST 7축 판정, fail-closed | H-03 |
| `judge_display_pass` / `judge_training_pass` | min_confidence **인자 주입** | H3-02/B4-05 |

## 31-01 실측이 설계를 바꾼 지점

wave 1 smoke의 지배적 실패는 `pose_tolerance`였다. 8건 중 지정 관절만 교정하고 나머지를
보존한 사례는 2건(둘 다 wan)뿐이고, 나머지는 자세를 전면 재생성했다(qwen 1건은 복장 색까지
변경). 이 실측이 두 곳에 직접 반영됐다.

1. **judge 축 구성.** `correction_visible` 단독으로 판정하면 "전면 재생성했는데 교정도
   보이는" 산출물이 그대로 통과한다. 그래서 보존 축 6종(identity/clothing/background/pole/
   single_person/no_extra_limbs)을 두고 **전부 참**이어야 통과시킨다. 이 케이스를
   `test_preservation_axis_failure_blocks_pass` 가 4개 보존 축 각각에 대해 고정한다.
2. **프롬프트·파라미터.** `prompt_extend: False` 는 벤더의 프롬프트 임의 확장이 "지정 관절만"
   지시를 희석하는 것을 막는 최소 방어다. judge 프롬프트에도 "자세가 전면적으로 다시
   그려졌다면 correction_visible 이 참이더라도 보존 축들을 거짓으로 판정하라"를 명시했다.

`hard rejection`(single_person_ok / no_extra_limbs)은 confidence와 무관하게 실패시킨다 —
사람이 여럿이거나 팔다리가 늘어난 산출물을 "확신도가 높으니 통과"시킬 수는 없다.

## 검증에서 실제로 무언가를 잡는 테스트

대부분의 보안 경계 테스트는 mock으로 짜면 구현이 비어 있어도 통과한다. 그래서 두 곳은
실제 실행으로 갔다.

- **redirect 차단 (H3-05).** openssl로 self-signed 인증서를 만들고 `ThreadingHTTPServer`를
  TLS로 감싼 뒤 https 127.0.0.1 로 **진짜** 301/302/303/307/308 응답을 받는다.
  `_test_ssl_context` 주입으로 인증서를 신뢰시킨다. `_NoRedirectHandler` 를 `build_opener` 에
  물리는 것을 빼먹으면 이 테스트에서만 잡힌다 — urlopen monkeypatch 로는 영원히 green이다.
- **RSS 상한 (H3-06).** 200MB 다운로드를 `subprocess.run([sys.executable, '-c', ...])` 로
  **새 프로세스**에서 실행하고 `ru_maxrss` 를 플랫폼 정규화(darwin bytes / linux KiB→bytes)해
  구조화 JSON으로 stdout에 실어 부모가 파싱한다.

  실측: `{"baseline_bytes": 41975808, "peak_bytes": 44040192, "delta_bytes": 2064384,
  "platform": "darwin"}` — 200MB 다운로드에 RSS 증가 **약 1.97MB**. 스트리밍이 실동작한다.

  **박제: 이 수치는 darwin 측정이다. IaC MemorySize 산정은 Linux/container 측정 기준으로
  다시 재야 한다** (ru_maxrss 단위와 allocator 거동이 다르다).

- **bomb.** PIL로 20000x20000 이미지를 실제로 만들 수는 없으므로(400M 픽셀), IHDR이
  20000x20000을 주장하는 1KB 미만 PNG를 `struct` + `zlib.crc32` 로 직접 조립했다. 압축
  크기 cap은 통과하고 `Image.MAX_IMAGE_PIXELS` 에서 걸린다 — 이게 정확히 실제 bomb의 형태다.
  `test_safe_decode_restores_global_pixel_cap` 이 실패 경로에서도 전역 cap이 복원되는지
  본다(MAX_IMAGE_PIXELS는 PIL 전역이라 되돌리지 않으면 다른 호출자에 샌다).

## Deviations from Plan

### 1. [Rule 1 - Bug] 비-JSON 벤더 응답이 pending 으로 오독되던 경로

- **발견 시점:** Task 1 테스트 작성 중
- **문제:** 계획대로 `_http_json` 이 비-JSON 응답에 빈 dict 를 반환하면, `_poll_result` 가
  `task_status` 부재를 보고 `pending` 을 돌려준다. 게이트웨이 HTML 오류 페이지를 받은
  워커가 죽은 작업을 영원히 폴링하게 된다.
- **수정:** `_http_json` 이 비-JSON/비-object 응답에 `ValueError` 를 올리고, 어댑터가
  잡아 `vendor_error` 로 수렴시킨다. 계획의 "방어적 JSON" 의도(크래시 금지)는 유지하되
  실패를 typed 로 표면화한다.
- **커밋:** 94dac98

### 2. [계획 강화] `VendorPollResult` 가 url 없는 succeeded 를 거부

계획에는 없었으나 `__post_init__` 에서 `state == succeeded and not output_url` 을
`ValueError` 로 막았다. url 없는 성공은 `invalid_output` 으로 표현되어야 하고, 그 구분이
무너지면 워커가 None URL 을 fetch 로 넘긴다.

### 3. [프로세스] 태스크별 커밋 방식

플랜의 3개 태스크가 **동일한 2개 파일**을 순차적으로 채우는 구조라, 모듈을 한 벌로 작성한
뒤 태스크 경계(공용 bomb 방어 / judge 섹션)에서 파일을 잘라 3개 커밋으로 나눴다. 각 커밋
시점에 해당 태스크 테스트가 실제로 green 임을 확인했다(14 → 35 → 58). 커밋 히스토리는
태스크 단위로 정확하지만, 작성 순서는 파일 단위였다.

## 후속 플랜이 반드시 처리해야 할 것

### BLOCKER 후보: Pillow 가 Lambda 의존성에 없다

`prepare_judge_payload` 는 PIL을 쓴다(정규화·EXIF 제거·bomb 방어). 그런데
`backend/functions/pipeline/requirements.txt` 에 Pillow가 없다 — 현재 Pillow는 RunPod
서버측 전용이다. 본 모듈은 PIL을 **lazy import** 하므로 모듈 로드와 어댑터 경로는 Lambda에서
정상 동작하지만, **judge 를 Lambda 에서 호출하면 ImportError 로 죽는다.**

31-09 는 다음 중 하나를 명시적으로 선택해야 한다:

- (a) `pipeline/requirements.txt` 에 `Pillow` 추가 (약 3–4MB, 250MB 한도에 여유 있음), 또는
- (b) judge 를 Pod 측에서 실행하고 Lambda 는 결과만 소비.

본 플랜의 `files_modified` 범위 밖이라 여기서 손대지 않았다. 플랜의 must_have
"judge 런타임은 Lambda 에서 실행 가능하다" 는 **SDK 미반입 축에서는 충족**(google-genai/
pydantic 0, stdlib urllib REST)이고, **런타임 의존성 축에서는 (a) 또는 (b) 결정이 남아 있다.**

### 인계 사항

- `judge_display_pass` / `judge_training_pass` 의 `min_confidence` 는 keyword-only **필수**
  인자다(기본값 없음). 31-09 가 `DISPLAY_JUDGE_CONFIDENCE` / `TRAINING_JUDGE_CONFIDENCE`
  env 로 각각 주입해야 하며, 값 자체는 31-13 grid 산출물이다.
- `IMAGE_ENGINE_SYNC` / `_RESULTS_BLOCKED` 는 RESULTS.json 전사값이다. 31-13 이 RESULTS.json
  을 갱신하면 `test_async_only_gate_reflects_smoke_results` 가 즉시 실패한다 — 그때 전사값을
  같이 올리라는 신호다(조용한 드리프트 방지가 목적).
- `safe_decode_image` 는 31-06 이 `_normalize_for_pose` 에서 import 해야 한다(공용 계약).
  두 벌 구현이 생기면 H4-06 방어가 한쪽에만 적용된다.
- 벤더 output URL 은 **반환값으로만** 흐른다. Firestore/로그/메시지 기록 금지(H3-01).

## 범위 밖 발견 (수정하지 않음)

`python -m pytest backend/tests -q` 는 본 플랜 이전부터 실패한다:

- 수집 오류 2건: `test_pole_detector.py`, `test_rtmw_133_to_coco17_adapter.py`
  (`fixtures.rtmw_keypoints` import 경로 — 파일은 존재하나 sys.path 가정이 깨짐)
- 실패 41건: 전부 Gemini/pose 레거시 스위트 (phase06/phase08, `test_gemini_*`,
  `test_pipeline_gemini{c,d}_wiring`, `test_spike_*`)

phase31 과 visual_gen 을 건드리는 것은 하나도 없다. 위 2개 파일 제외 시
**3073 passed / 41 failed(전부 사전 실패)**, phase31 은 **162 passed / 0 failed**.

## Threat Flags

없음 — 본 플랜이 도입한 외부 표면(DashScope create/poll, Gemini generateContent, 벤더
자산 다운로드)은 전부 플랜 `<threat_model>` 의 T-31-15~T-31-19 에 등재되어 있고, 각 항목의
mitigation 이 테스트로 고정됐다.

## Known Stubs

없음.

## Verification

```
python3 -m pytest backend/tests/phase31 -q        → 162 passed
python3 -m pytest backend/tests/phase31/test_visual_gen.py -q → 58 passed
```

- 신규 패키지 0 (`requirements*.txt` 무변경)
- `requests` / `google.genai` / `pydantic` / `import time` import 0 — 테스트가 소스 assert
- 판정 임계값 리터럴 0 — `re.search(r"(?<![\w.])0\.\d+", src)` 무매치 assert
- 실 외부 API 호출 0 (생성 콜 예산 8/8 은 31-01 에서 소진, 추가 지출 없음)
- 각도 계산 미구현 — `joint_inner_angle_deg` 재구현 0 (31-03 fault_zoom 단일 출처 유지)

## Self-Check: PASSED

- `backend/shared/python/sunity_shared/analysis/visual_gen.py` FOUND (837줄)
- `backend/shared/python/sunity_shared/analysis/interfaces.py` FOUND (ImageEditEngine/VideoEditEngine 포함)
- `backend/tests/phase31/test_visual_gen.py` FOUND (762줄)
- 커밋 94dac98 / 3e427e8 / d4a271d FOUND
- STATE.md / ROADMAP.md 미수정 확인
