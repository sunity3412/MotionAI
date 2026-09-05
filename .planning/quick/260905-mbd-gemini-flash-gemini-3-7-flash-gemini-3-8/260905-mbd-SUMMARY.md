---
phase: quick-260905-mbd
plan: "01"
subsystem: gemini-model-pin
tags: [gemini, model-version, vision-gate, whitelist]
requires: []
provides:
  - "gemini/config.py DEFAULT_C_MODEL = gemini-3.8-flash, ALLOWED_MODELS = {3.1-pro-preview, 3.8-flash} (3.7 은 resolve_model 에서 ValueError)"
  - "evals/phase25·phase29 run_sweep 의 GEMINI_MOMENT_MODEL 기본값이 config 를 읽는다 (raw 문자열 0, start_server.sh 와 같은 방식)"
  - "테스트의 Flash 모델 단언이 DEFAULT_C_MODEL 기준 — 다음 갱신은 config.py + test_config.py 두 곳"
affects: [gemini-region-C(scene_finder·machine-eye·view_reasoner), gemini_teacher-judge, curate_vision-gate, visual_gen-judge, llm_judge, moment-extractor-fallback]
tech-stack:
  added: []
  patterns: ["모델 문자열 owner = gemini/config.py 한 곳 — 소비처(스크립트·테스트)는 import 로 승계, 리터럴은 config 와 그 테스트에만"]
key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/gemini/config.py
    - backend/evals/phase25/run_sweep.py
    - backend/evals/phase29/run_sweep.py
    - backend/research/spikes/spike_judge_sees_video.py
    - backend/training/distill/gemini_teacher.py
    - backend/training/datagen/curate_vision.py
    - backend/evals/phase22/run_bakeoff.py
    - backend/shared/python/sunity_shared/analysis/synthesis/gemini_view_reasoner.py
    - backend/shared/python/sunity_shared/eval/llm_judge.py
    - backend/tests/gemini/test_config.py
    - backend/tests/gemini/test_scene_finder.py
    - backend/tests/gemini/test_reference_extractor.py
    - backend/tests/phase22/test_gemini_teacher.py
    - backend/tests/phase22/test_shadow_wiring.py
    - backend/tests/test_technique_cache.py
    - backend/tests/eval/test_llm_judge.py
    - backend/tests/phase08/test_gemini_model_env_driven.py
    - backend/tests/phase31/test_visual_gen.py
    - backend/tests/test_pipeline_geminic_wiring.py
decisions:
  - "sweep env 기본값과 spike TEXT_JUDGE_MODEL 은 3.8 리터럴로 바꾸지 않고 config import 로 — 08-18 주석이 경고한 '놓친 하드코딩이 옛 모델로 도는' 모양을 구조적으로 없앤다"
  - "테스트 단언은 DEFAULT_C_MODEL 과 비교 (test_config.py 만 리터럴) — 의도('정본이 Flash 최신 / 2.5 계열 0')는 유지, 숫자 고정은 정본 테스트 한 곳"
  - "gemini_moment_extractor.py 56·58행의 3.7 언급은 08-18/08-28 날짜 박힌 사실 기록이라 그대로 둠 — 코드 경로 아님"
  - ".planning/ 아래 3.7 hit(증거 JSON·옛 PLAN·260816 스크립트)은 당시 기록 — 손대지 않음"
requirements-completed: []
metrics:
  duration: "12분"
  completed: "2026-09-05"
  tasks: "3/3"
  pytest: "4602 passed / 0 failed / 20 skipped (기준선 4601/0 + parametrize 1)"
---

# Quick 260905-mbd: Gemini Flash 정본 3.7 → 3.8 Summary

**One-liner:** Flash 정본을 `gemini-3.8-flash` 로 옮기고 3.7 을 화이트리스트에서 빼서(resolve_model ValueError) 하드코딩 우회로를 닫았다 — 소비처 2곳(eval sweep env 기본값)은 문자열 대신 config 를 읽게 바꿔 다음 갱신 때 같은 누락이 재발하지 않는다. backend 4602/0.

## 판정: 된다

- **정본 1곳:** `DEFAULT_C_MODEL == "gemini-3.8-flash"`, `"gemini-3.7-flash" not in ALLOWED_MODELS` (plan verify 명령 실행, PASS).
- **3.7 거부:** `resolve_model("C", env_override="gemini-3.7-flash")` → ValueError (test_config parametrize 3.5/3.7 둘 다 PASS).
- **env 기본값:** phase25·phase29 run_sweep 을 GEMINI_MOMENT_MODEL 없는 env 에서 import → `GEMINI_MOMENT_MODEL=gemini-3.8-flash` (실측). 화이트리스트 밖 모델을 가리키던 상태 해소.
- **pytest:** `cd backend && .venv/bin/python -m pytest -q` → **4602 passed / 0 failed / 20 skipped** (44s). 편집 전 대조군 4601 passed / 0 failed / 20 skipped (49s). +1 = 은퇴 모델 거부 테스트의 3.7 케이스.
- **정본 단일 출처:** config.py 밖 실행 코드에 `gemini-3.8-flash` 리터럴 0. 남은 리터럴은 주석·docstring(표기)과 test_config.py(정본 자체의 테스트)뿐.

## Performance

- **Duration:** 12분
- **Started:** 2026-09-05T07:08:08Z
- **Completed:** 2026-09-05T07:20:18Z
- **Tasks:** 3/3
- **Files modified:** 19 (config 1 + 소비처 8 + 테스트 10)

## Task Commits

1. **Task 1: 정본 갱신 + 화이트리스트에서 3.7 제거** — `85105aca` (feat)
2. **Task 2: 3.7 문자열 소비처 정리** — `d53d1b0b` (fix)
3. **Task 3: 문자열 단언 테스트 갱신** — `cd765baf` (test)

## 한 일

### Task 1 — config.py (`85105aca`)
- `DEFAULT_C_MODEL` 3.7 → 3.8, `ALLOWED_MODELS` 에서 3.7 제거, 모듈 docstring 표기 3.8/2026-09-05.
- 08-18 선례 주석 바로 아래에 같은 형식으로 09-05 주석: 근거(3장 x 5회 세 모델 비교, 3.8 반복 안정성 최고, omni 는 흔들리고 최고가에 호출 형태 다름), belle 승인, 3.7 이 이제 터진다는 것, start_server.sh 가 이 값을 읽어 Pod 재기동 시 자동 승계된다는 것.

### Task 2 — 소비처 (`d53d1b0b`)
- `evals/phase25/run_sweep.py`, `evals/phase29/run_sweep.py`: `os.environ.setdefault("GEMINI_MOMENT_MODEL", "gemini-3.7-flash")` → `from sunity_shared.gemini.config import DEFAULT_C_MODEL as _MOMENT_MODEL_DEFAULT` 후 그 값. sys.path 주입(shared/python)이 이미 그 위에 있어 순수 import. 인접 주석의 A/B 예시 `GEMINI_MOMENT_MODEL=gemini-2.5-pro` 는 2.5 영구 금지와 모순이라 `gemini-3.1-pro-preview` 로.
- `research/spikes/spike_judge_sees_video.py`: `TEXT_JUDGE_MODEL = DEFAULT_C_MODEL` (현행 gemini_teacher.JUDGE_MODEL 과 같은 정본). 35행(현 39행) EAP `gemini-3.7-flash-video-understanding-eap` 는 그대로. import 스모크: TEXT=gemini-3.8-flash / VIDEO=EAP 유지.
- 주석·docstring 표기만: `gemini_teacher.py` 11·371행, `curate_vision.py` 52행, `run_bakeoff.py` 16행, 그리고 plan 목록 밖 2건 `gemini_view_reasoner.py` 18행, `eval/llm_judge.py` 125행(현행 동작 서술이라 정정).
- run_sweep 를 import 하는 테스트 3파일(test_eval_out_dir · test_phase25_eval_gates · test_sweep_rtmpose_smoke) 50 passed.

### Task 3 — 테스트 (`cd765baf`)
- `test_config.py`: 3.8 리터럴, `test_c_override_rejects_retired_flash` 를 `["gemini-3.5-flash", "gemini-3.7-flash"]` parametrize + `match="ALLOWED_MODELS"`, docstring 에 09-05 한 줄.
- `test_scene_finder` (6곳) · `test_reference_extractor` (4곳) · `test_gemini_teacher` (6곳, `"flash" in JUDGE_MODEL` 1줄 추가로 "judge = Flash 축" 의도 명시) · `test_shadow_wiring` (2곳) · `test_technique_cache` (1곳): `"gemini-3.7-flash"` → `DEFAULT_C_MODEL` import.
- plan 목록 밖 4파일: `eval/test_llm_judge.py:54`(갱신 후 실제로 깨짐 — `_JUDGE_MODEL = DEFAULT_C_MODEL`), `phase31/test_visual_gen.py:636`(갱신 후 깨짐 — endpoint URL 이 DEFAULT_C_MODEL 로 조립), `phase08/test_gemini_model_env_driven.py:111·115`(은퇴 문자열을 env 예시로 사용 — DEFAULT_C_MODEL 로, 공유 키가 Pro 라 우선순위 판별력 유지), `test_pipeline_geminic_wiring.py:250·322`(stub payload).

## 계획과 다르게 한 것

**1. [Rule 1 - 누락] plan 의 grep 목록이 불완전 — 6건 추가 처리**
- **발견:** Task 2 착수 grep. plan 은 `.planning`·tests 일부만 나열했으나 실제로는 `tests/eval/test_llm_judge.py`, `tests/phase31/test_visual_gen.py` 가 정본 갱신 뒤 **실제로 깨지는 단언**이었고, `tests/phase08/test_gemini_model_env_driven.py`, `tests/test_pipeline_geminic_wiring.py` 는 은퇴 문자열을 데이터로 들고 있었다. 코드 쪽 docstring 2건(`gemini_view_reasoner.py`, `eval/llm_judge.py`)도 현행 서술이라 정정.
- **처리:** Task 2/3 커밋에 포함. 전체 스위트 0 failed 로 확인.

**2. [정본 단일 출처] 소비처의 리터럴을 3.8 로 바꾸지 않고 config import 로**
- run_sweep 2곳, spike 1곳. 오케스트레이터 제약("config.py 밖 새 raw 문자열 금지")과 08-18 주석의 실패 모드에 맞춘 선택. start_server.sh 는 이미 같은 방식(config 에서 읽음)이라 "production mirror" 의미가 정확해졌다.

**3. [의도 유지] 테스트 단언은 `DEFAULT_C_MODEL` 비교로**
- plan 의 "단언의 의도를 유지 — 특정 숫자 고정이 목적이 아니다" 를 이렇게 읽었다. 숫자는 `test_config.py` 한 곳에서만 고정. 각 단언은 여전히 판별력이 있다(예: reference_extractor 의 A 영역 기본은 Pro 라 Flash override 가 구분되고, env_driven 은 공유 키가 Pro 라 전용 키 우선이 구분된다).

**4. [의도적 잔여] `gemini_moment_extractor.py` 56·58행은 손대지 않음**
- "08-18 갱신으로 ALLOWED_MODELS 가 {…3.7} 로 좁혀지며 / 08-28 Pod 실측에서 3.7 이 정상 처리" — 날짜 박힌 사실 기록. 코드 체인(`GEMINI_MOMENT_MODEL → GEMINI_MODEL → _config.DEFAULT_C_MODEL`)은 이미 config 승계라 변경 불필요.

**5. [게이트 실행 방식] `rtk pytest` 는 "No tests collected"**
- rtk 가 `/opt/homebrew/bin/pytest`(시스템 3.14) 를 불러 venv 의존 테스트 수집 단계에서 ImportError. 게이트는 제약에 적힌 그대로 `cd backend && .venv/bin/python -m pytest -q` 로 실행(출력은 파일로 받아 tally 만 읽음).

## 잔여 grep (Task 2·3 verify 대응)

`gemini-3.7-flash` — backend 전체(.aws-sam·.venv 제외):
```
research/spikes/spike_judge_sees_video.py:39   VIDEO_JUDGE_MODEL = "...-video-understanding-eap"   ← EAP 별개 모델, 지시대로 유지
tests/gemini/test_config.py:77                 parametrize ["gemini-3.5-flash", "gemini-3.7-flash"]  ← 거부 회귀
judging/gemini_moment_extractor.py:56, 58      08-18 / 08-28 날짜 박힌 사실 기록                      ← 위 4번
```
`.planning/` 아래 hit(260818-lik PLAN, 260816 regenerate_gated.py, 0901/0903 eye 증거 JSON, 35 phase doc.json)은 당시 실행 기록이라 손대지 않았다. `docs/contract.md:1525` 의 예시 `gemini-3.5-flash` 는 08-18 부터 낡은 것 — 이번 범위 밖, 아래 Deferred.

## Deferred

- `docs/contract.md:1525` `modelId` 예시가 `gemini-3.5-flash` — 계약 문서 예시(동작 무영향). 예시를 "config.py 정본 참조" 로 바꾸는 편이 낡지 않는다.
- `tests/phase08/test_gemini_model_env_driven.py` 파일 머리 docstring 의 "default 'gemini-2.5-flash'" 는 Plan 08-03 당시 기록 — 그대로 둠.

## 운영 메모

- **Pod:** `start_server.sh` 가 `GEMINI_MOMENT_MODEL` 을 config 에서 읽으므로 이 커밋을 반입한 다음 기동부터 3.8. 분석 Pod 는 시연 때만 켜는 운영이라(08-28) 지금 도는 Pod 는 없다고 보지만, 켜져 있다면 HEAD 반입·재기동 전까지는 3.7 그대로다.
- **모델 id 실재:** plan 의 09-05 측정(3장 x 5회, 3.8 이 5/5 응답)이 곧 실재 증거. 이번 태스크에서 ListModels 재조회는 하지 않았다.
- **LLM 학습 영향:** 영역 C(scene_finder·기계 눈·view_reasoner), gemini_teacher 증류 judge 필터, curate_vision 게이트, visual_gen 판정이 다음 호출부터 3.8. 학습셋 자체는 안 바뀌고 재학습도 촉발되지 않는다 — 다음 증류 사이클의 judge 통과 분포가 달라질 수 있으니 그 사이클 보고에 모델 변경을 한 줄 남길 것.

## Known Stubs

없음.

## Threat Flags

없음 — 새 네트워크 표면·인증 경로·스키마 변경 없음(모델 id 문자열과 그 소비 경로만).

## Self-Check: PASSED

- SUMMARY 파일 존재, 태스크 커밋 3건(85105aca · d53d1b0b · cd765baf) git log 에 존재, 핵심 파일 4건 존재 확인.
