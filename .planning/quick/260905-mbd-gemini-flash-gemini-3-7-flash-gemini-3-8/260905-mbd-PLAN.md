---
phase: quick-260905-mbd
status: planned
subsystem: gemini-model-pin
tags: [gemini, model-version, vision-gate]
created: 2026-09-05
---

# quick-260905-mbd: Gemini Flash 정본을 3.7 → 3.8 로

## 왜

확대 카드 사진이 제목의 부위를 실제로 보여주는지 기계 눈으로 검사하는 감사를 09-03 라이브 21장에
돌리고, 판정이 갈린 3장을 **5회 반복**으로 세 모델 비교했다 (2026-09-05 실측):

| 카드 | gemini-3.7-flash | gemini-3.8-flash | gemini-omni-1.1-flash |
|---|---|---|---|
| 파워스핀 왼어깨 | 표시 팔꿈치×4 무릎×1 | 표시 겨드랑이×3 무릎×2 | 4가지로 흩어짐 |
| 엘보 참고 왼어깨 | 머리×3 목×2 | **머리×5 · 목×5** | 등허리×3 가슴×1 배×1 |
| pdshape 오른팔꿈치(정답 아는 카드) | 등허리×5 | 등허리×5 | 등허리×5 |

3.8 이 반복 안정성 최고(2/3 카드 5/5). omni 는 가장 흔들리고 카드당 $0.017 로 최고가 —
게다가 `generateContent` 가 아니라 `/v1beta/interactions` 전용이라 파이프라인 호출 형태가 다르다.
belle 승인: "3.8로".

## 하는 일

### Task 1 — 정본 갱신 + 화이트리스트에서 3.7 제거

`backend/shared/python/sunity_shared/gemini/config.py`
- `DEFAULT_C_MODEL` → `"gemini-3.8-flash"`
- `ALLOWED_MODELS` → `{"gemini-3.1-pro-preview", "gemini-3.8-flash"}`
- 2026-08-18 선례 주석과 **같은 형식**으로 3.7 제거 사유를 날짜와 함께 남긴다. 남겨두면 놓친
  하드코딩이 가드를 통과해 조용히 옛 모델로 돈다 (그게 08-18 이 적어둔 실패 모드다).
- 모듈 docstring 의 `gemini-3.7-flash(2026-08-18 갱신)` 표기도 3.8/2026-09-05 로.

`verify`: `backend/.venv/bin/python -c "from sunity_shared.gemini.config import DEFAULT_C_MODEL, ALLOWED_MODELS; assert DEFAULT_C_MODEL=='gemini-3.8-flash'; assert 'gemini-3.7-flash' not in ALLOWED_MODELS"`
`done`: 정본 1곳만 바뀌고 새 raw 문자열 박제 0.

### Task 2 — 화이트리스트 밖으로 나간 3.7 문자열 소비처 정리

`rtk grep -rn "gemini-3.7-flash"` (제외: `.aws-sam`, `.claude/worktrees`, `node_modules`, `.planning/archive`)
로 전건을 훑고, **resolve_model 에 env override 로 들어가는 값**을 먼저 고친다 — 화이트리스트에서
빠진 지금 그대로 두면 `ValueError` 로 터진다:
- `backend/evals/phase25/run_sweep.py:110` `GEMINI_MOMENT_MODEL` 기본값
- `backend/evals/phase29/run_sweep.py:91` 같은 값

문자열/주석만인 곳(동작 영향 없음, 표기 정정):
- `backend/training/distill/gemini_teacher.py` — `JUDGE_MODEL = DEFAULT_C_MODEL` 이라 코드 변경
  불필요, 11·371행 주석의 모델명만
- `backend/training/datagen/curate_vision.py:52` 주석
- `backend/research/spikes/spike_judge_sees_video.py:36` `TEXT_JUDGE_MODEL`
  (35행 `gemini-3.7-flash-video-understanding-eap` 는 **EAP 별개 모델 — 건드리지 말 것**)
- `backend/evals/phase22/run_bakeoff.py:16` 주석

`verify`: 위 제외 경로 밖에서 `gemini-3.7-flash` grep 결과가 EAP 문자열 1건과 테스트 회귀 주석만 남는다.
`done`: env 기본값이 화이트리스트 안 모델만 가리킨다.

### Task 3 — 문자열 단언 테스트 갱신

- `backend/tests/gemini/test_config.py` (40·50행 + docstring)
- `backend/tests/gemini/test_scene_finder.py` (92·102·111·150·214·283행)
- `backend/tests/gemini/test_reference_extractor.py` (10·374·382·389행)
- `backend/tests/phase22/test_gemini_teacher.py` (6·105·107·201·204·221행)
- `backend/tests/phase22/test_shadow_wiring.py` (89·103행)
- `backend/tests/test_technique_cache.py` (262행)

단언의 **의도를 유지**한다 — "정본이 Flash 최신이다 / 2.5 계열 0" 이 목적이지 특정 숫자 고정이 아니다.
`test_config.py` 는 3.7 이 이제 거부되는지도 한 줄로 확인(3.5 선례와 동형).

`verify`: `cd backend && .venv/bin/python -m pytest -q`
`done`: **4601 passed / 0 failed** (직전 기준선) 유지.

## 하지 않는 일

- `gemini-3.1-pro-preview`(A/B/D 판정·코칭) 는 그대로. 이번 측정은 Flash 축만 봤다.
- omni 도입 안 함. 영상 생성 트랙([[camera-angle-ai-single-view-synth]])은 별건이고 활성 조건 3개가 남아 있다.
- 감사 자체를 게이트로 승격하는 작업은 별도 — 여기서는 모델 핀만 옮긴다.

## 게이트

- backend pytest 전체 4601/0
- 정본 단일 출처 유지 (config.py 밖 새 raw 문자열 0)
