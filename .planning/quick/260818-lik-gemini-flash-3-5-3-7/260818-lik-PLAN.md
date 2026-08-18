---
phase: quick-260818-lik
quick_id: 260818-lik
slug: gemini-flash-3-5-3-7
date: 2026-08-18
status: planned
description: >
  belle 지시(2026-08-18, ★재지시): Gemini Flash 를 gemini-3.5-flash → gemini-3.7-flash 로 갱신.
  할인 기간이라 지금 써야 한다. ★저번에도 지시받았으나 반영되지 않았는데, 원인은 게으름이 아니라
  구조다 — 중앙 owner(`gemini/config.py` DEFAULT_C_MODEL + ALLOWED_MODELS)가 있는데도
  모듈 8곳 이상이 그걸 우회해 문자열을 직접 박아놨다. 그래서 "모델 바꿔줘"가 열 군데 수정이 되고,
  하나만 빠뜨리면 그곳만 조용히 옛 모델로 돈다. 이번엔 갱신과 함께 **우회로를 없애고**,
  화이트리스트에서 3.5 를 **제거**해 남은 하드코딩이 조용히 도는 대신 ValueError 로 터지게 한다.
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [QUICK-260818-LIK]
files_modified:
  - backend/shared/python/sunity_shared/gemini/config.py
  - backend/runpod_inference/start_server.sh
  - backend/shared/python/sunity_shared/analysis/card_gates.py
  - backend/shared/python/sunity_shared/analysis/visual_gen.py
  - backend/training/distill/gemini_teacher.py
  - backend/training/datagen/curate_vision.py
  - backend/evals/phase22/run_bakeoff.py
  - backend/evals/phase25/run_sweep.py
  - backend/evals/phase29/run_sweep.py
  - backend/research/spikes/spike_judge_sees_video.py
  - .planning/quick/260816-ill2-illustration-framing-wiring/regenerate_gated.py
must_haves:
  truths:
    - "gemini-3.7-flash 가 실재하는 모델 ID 임을 API models 목록으로 확인한 뒤에 반영했다(문자열 추정 금지)"
    - "ALLOWED_MODELS 에서 gemini-3.5-flash 가 제거되어, 남아 있는 3.5 하드코딩이 resolve_model 를 타면 ValueError 로 터진다 — 조용한 옛 모델 사용이 불가능하다"
    - "운영 분석 경로(scene_finder/moment extractor)가 실제로 3.7 을 호출하는 것이 Pod 실행 로그로 확인된다 — 코드 통과가 아니라 호출 증거로"
    - "학습 라벨 심사(gemini_teacher JUDGE_MODEL)·학습 큐레이션(curate_vision)·게이트 코칭 심사(run_bakeoff JUDGE_MODEL)·일러스트 9항목 게이트가 전부 3.7 을 쓴다"
    - "과거 산출 기록(backend/evals/realfixture/fixtures/*.json 4건)의 model 필드는 손대지 않는다 — 그 파일이 만들어질 당시 쓴 모델의 기록이고, 고치면 기록이 거짓이 된다"
    - "모델 문자열을 직접 박은 모듈은 config 를 import 하도록 바뀌어, 다음 갱신은 config.py 한 곳만 고치면 된다"
    - "pytest 기준선(failed<=59)이 유지되고, 모델 문자열을 단언하던 테스트는 3.7 로 함께 갱신된다"
  artifacts:
    - path: "backend/shared/python/sunity_shared/gemini/config.py"
      provides: "DEFAULT_C_MODEL=gemini-3.7-flash + ALLOWED_MODELS 에서 3.5 제거(fail-loud) + 제거 이유 주석"
      contains: "gemini-3.7-flash"
  key_links:
    - from: "backend/training/distill/gemini_teacher.py::JUDGE_MODEL"
      to: "backend/shared/python/sunity_shared/gemini/config.py::DEFAULT_C_MODEL"
      via: "import (하드코딩 제거)"
---

# quick-260818-lik — Gemini Flash 3.5 → 3.7

## 왜 저번에 안 됐나 (이번 작업의 진짜 대상)

중앙 owner 가 있는데 우회로가 더 많았다. `resolve_model()` 을 타는 곳은 `scene_finder` 와
`gemini_view_reasoner` 둘뿐이고, 나머지는 자기 파일에 `"gemini-3.5-flash"` 를 박아뒀다.
그래서 지시 한 번에 열 군데를 고쳐야 했고, 빠뜨린 곳은 **아무 신호 없이** 옛 모델로 돌았다.

이번엔 갱신 + 우회로 제거 + fail-loud 를 같이 한다. 다음 갱신은 `config.py` 한 줄이어야 한다.

## 위험 (belle 께 고지)

운영 분석 경로(moment extractor·카드 게이트)의 모델이 바뀌면 **사용자에게 나가는 판정이
달라질 수 있다.** 임계값들은 3.5 로 맞춰둔 것이다. 그래서 코드 반영 후 **실제 분석 1건을
운영 경로로 돌려** 이전 결과와 대조한다.
