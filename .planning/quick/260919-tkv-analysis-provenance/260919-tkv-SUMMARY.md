---
unit: quick-260919-tkv
title: 분석 출처 기록 (result.analysisVersion)
date: 2026-09-19
status: done
scope: 기록 추가만 — 채점 무접촉
commits:
  - 796932fb feat(quick-260919-tkv): result.analysisVersion 계약 + provenance 공통 모듈
  - 23f0b6d6 feat(quick-260919-tkv): pipeline 배선 + 채점 무접촉 박제 테스트
gates:
  backend: 4945 passed / 20 skipped / 0 failed (기준선 4896 + 신규 49, 회귀 0)
  app: npx tsc --noEmit clean
---

# quick-260919-tkv — 분석 출처 기록

## 한 줄

분석 결과에 **어느 코드·어느 기준으로 나왔는지** 를 같이 적는다 (`result.analysisVersion`). 숫자는 1도 안 바뀐다.

## 왜 (belle 2026-09-19)

> "분석이 할 때마다 다르니까 문제 아냐. 언제는 3장이라 보고하고 6장이라 보고하고 5장이라 보고하고 ... 몇 일은 이렇게 몇 일은 이렇게 해서 꼬이는 거 아냐."

라이브 전 이력을 실측해 원인을 갈랐다 (같은 pdshape 영상, belle 계정 실 doc):

| 언제 | 점수 | 감점 | 결과 지문 | 버전 기록 |
|---|---|---|---|---|
| 3판 (9/02~9/03) | 60 | 5 | `389f9b31` | 없음 |
| 3판 (9/09) | 60 | 6 | `3ac37f2f` | 없음 |
| 오늘 | 80 | 1 | `c162916` | 없음 |

1. **비결정성은 아니다.** 같은 코드에서 3번 돌려 3번 다 지문이 같다 (두 묶음 모두 3/3).
2. **어느 판이 어느 코드/기준에서 나왔는지 기록이 doc 어디에도 없다.** 답이 바뀌면 **분석이 바뀐 건지 우리가 바꾼 건지** 구분할 수단이 없다 — 이것이 "꼬임"의 기계적 원인이다.

이번 단위 = 그 기록을 남긴다.

## 무엇을 했나

`result.analysisVersion` (flat scalar dict) 을 `complete_analysis` **직전** 에 1회 붙인다.

| 키 | 뜻 | 출처 |
|---|---|---|
| `commitSha` | 코드 판 | `SUNITY_COMMIT_SHA` env → `git rev-parse HEAD` |
| `referenceRelease` | 기준 라이브러리 판 (`rot180_v1` 등) | `reference/_release.activeCandidate` |
| `poseEngine` | 포즈 엔진 클래스명 | `/health` canary 와 같은 출처 (`_RTMW_ENGINE`) |
| `rot180InversionEnabled` / `prInversionEnabled` / `rtmwDeterministic` | 켜져 있던 플래그 | 각 env |

**값을 못 구하면 키를 생략한다** (fail-closed). 빈 문자열·`'unknown'`·추측값으로 채우지 않는다.

### 파일

- `backend/shared/python/sunity_shared/provenance.py` (신설) — `resolve_commit_sha` · `PROVENANCE_FLAGS` · `build_analysis_version`
- `backend/runpod_inference/server.py` — `_resolve_commit_sha` **제거**, 공통 모듈 호출로 전환 (중복 구현 0). `/health` 의 기존 계약(항상 문자열, 못 구하면 `'unknown'`)은 그 자리에서만 유지
- `backend/shared/python/sunity_shared/firestore_admin.py` — `_resolve_reference_version_pointer` 분리 · `get_active_reference_release` 신설 · `_validate_analysis_version` scoped validator + `complete_analysis` 배선
- `backend/functions/pipeline/app.py` — `_attach_analysis_version` + mode1 경로의 `reference_release` 포착
- 3-way lockstep: `backend/.../models.py ANALYSIS_VERSION_KEYS` ↔ `app/src/types/analysis.ts AnalysisVersion` ↔ `docs/contract.md §11.13`
- `backend/tests/test_analysis_provenance.py` (신설, 49건)

### 설계 판단 2건 (왜 그렇게 했는지)

**(1) `referenceRelease` 는 포인터 값이 아니라 "실제로 overlay 된 판" 이다.**
`_release.activeCandidate` 를 그대로 적으면 틀릴 수 있다 — 포인터가 가리키는 `reference/{id}/versions/{v}` 문서가 없으면 `get_reference_motion` 은 top-level 로 **폴백** 하기 때문이다. 그래서 `get_active_reference_release` 는 `get_reference_motion` 과 **같은 포인터 판정**(`_resolve_reference_version_pointer`)을 쓰고 버전 문서 실재까지 확인한 뒤에만 값을 돌려준다. 폴백이면 키 생략. 두 함수가 갈리면 doc 에 박제되는 기록이 거짓말이 된다.

**(2) `get_reference_motion` 의 반환 dict 에 키를 심지 않았다.**
그게 가장 짧은 길이었지만, 그 dict 는 `backend/scripts/backup_reference_docs.py` 가 **그대로 백업 JSON 에 쓴다**. 합성 키가 백업에 섞이면 복원 때 Firestore 로 흘러든다. 시그니처 변경도 기각했다 — 기존 테스트 더블이 `lambda mid: {...}` 라 kwarg 하나에 깨진다(회귀 0 제약). 남은 길이 별도 accessor 였다.

## 채점 무접촉을 어떻게 박제했나

`test_attach_analysis_version_touches_nothing_else` — 점수·감점 내역·카드가 들어 있는 대표 `result` 에 helper 를 돌린 뒤

- 늘어난 키가 정확히 `{analysisVersion}` 하나임을 확인
- 호출 전 모든 키의 값이 **완전히 동일** 함을 확인
- `overallScore` / `deductionBreakdown.final` / `records` 수 / `faultZoomComparisons` 수를 명시적으로 다시 확인 (회귀 시 무엇이 깨졌는지 즉시 보이도록)

추가로 `_process` 를 실제로 완주시켜 `complete_analysis` 로 넘어간 result 에 필드가 실렸는지 본다 (mode1 / mode3 / 조회 실패 3경로). helper 단위 테스트만으로는 "만들었다" 만 증명되기 때문 ([[wiring-claims-need-log-evidence]]).

## 실측하다 발견한 것 — env 플래그 판정 규칙이 소비처마다 다르다

이번 작업의 부산물이고, **이번 단위에서 고치지 않았다.**

| doc 키 | env | True 조건 | 규칙 소유자 |
|---|---|---|---|
| `rot180InversionEnabled` | `ROT180_INVERSION_ENABLED` | `strip().lower() in ("1","true")` | `rtmw_engine._env_on` |
| `prInversionEnabled` | `PR_INVERSION_ENABLED` | 같음 | 같음 |
| `rtmwDeterministic` | `RTMW_DETERMINISTIC` | **정확히 `"1"`** (`"true"` 는 OFF) | `ort_determinism.deterministic_enabled` |

그런데 `runpod_inference/server.py::_env_flag`(= `/health` 의 `envFlags`)는 `("1","true","on","yes")` 로 **셋 모두보다 느슨하다.**

→ `RTMW_DETERMINISTIC=true` 면 **`/health` 는 `true`, 엔진은 OFF.** provenance 는 "실제로 켜졌던 것"을 적어야 하므로 **엔진 쪽 규칙** 을 따랐고, 그 결과 `/health` 와 doc 의 `analysisVersion` 이 다를 수 있다. **그건 버그가 아니라 이 불일치다** — server.py 주석 · contract.md §11.13 · `test_deterministic_rule_is_stricter_than_rot180` 세 곳에 박아 두었다. `/health` 를 고치면 기존 계약이 바뀌므로 별도 단위로 남긴다.

지금 운영 영향은 없다: `start_server.sh` 는 세 플래그를 전부 `=1` / `=0` 숫자로 export 한다(`"true"` 를 쓰는 경로 0건).

## 이 단위가 하지 않는 것

- **과거 doc 을 소급해 채우지 않는다.** 위 표의 3묶음을 포함해 기존 doc 은 하나도 고치지 않는다 (migration 0). **앞으로 나오는 분석부터** 실린다.
- **점수가 왜 60→80 으로 움직였는지 설명하지 않는다.** 이 필드는 "다음에 또 움직이면 무엇이 달랐는지 알 수 있게" 할 뿐이다.
- **앱은 한 줄도 읽지 않는다.** TS 타입은 기록의 모양을 박제할 뿐 UI 소비 금지.

## ★ 남은 절반 — 고정 영상 묶음 회귀 대조 (다음 단위)

이번 것은 **앞으로의 판을 구분할 수 있게** 만든 것이다. 나머지 절반은 **판끼리 실제로 대보는 것** 이다:

- 고정 영상 묶음(정은지 기준 + 학생 대표 N편)을 판이 바뀔 때마다 돌려 산출 지문을 비교
- 위 표의 "결과 지문"(`389f9b31` / `3ac37f2f` / `c162916`)이 바로 그 지문의 수동판이다 — 자동화가 없어 사람이 매번 다시 세고 있었다
- 그래야 "3장 → 6장 → 5장" 이 났을 때 **어느 커밋이 카드 수를 바꿨는지** 를 사람 기억이 아니라 대조표로 짚는다

Pod 가동이 필요하다 (현재 `pod-expected=down`, 실증은 2026-10 중순).

## 게이트 (직접 실측)

```
backend/.venv/bin/python -m pytest backend/tests -q
  기준선  4896 passed / 20 skipped / 0 failed
  이후    4945 passed / 20 skipped / 0 failed      (신규 49, 회귀 0)

cd app && npx tsc --noEmit                          clean (exit 0)

python -c "from runpod_inference import server; server.health()"
  commitSha 54a4f5de2532 · envFlags 3키 · 기존 /health 키 6개 그대로
```

## belle 판정 요청 — 0건

이번 단위는 판정이 이미 끝난 범위였다. 다만 **위의 "env 플래그 규칙 3종 불일치"** 는 belle 판정이 아니라 **다음 세션이 `/health` 를 정리할 때 봐야 할 기록** 이다.
