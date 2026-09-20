---
title: 동시 분석 오염 수리 — 분석별 값을 전역 싱글턴에서 떼어냈다
date: 2026-09-20
scope: 인계서 260919-cls §3-② (분석 결함 3건 중 1건)
status: 수리 완료 · 게이트 4958 passed / 0 failed (직접 실측) · 앱 tsc clean
---

# 동시 분석 오염 수리 (260920-cac)

## 0. 판정

**됐다.** 인계서 §3-② 의 오염 경로를 닫았다. 커브핏 없음 — 임계값·상수·분포를 하나도
건드리지 않은 순수 구조 수리다. 직렬 분석의 산출은 한 톨도 바뀌지 않는다.

같이 닫힌 것 2건, 종결한 미확인 1건, **새로 열린 미결 1건**이 있다 (§5, §6).

### ★ 어제(260919-cls) 는 허무해지지 않았다 — 살아남은 것부터

| 어제 규명한 결함 | 오늘 검증 결과 |
|---|---|
| **② 동시 분석 오염** | **주장 9개가 줄 번호까지 전부 맞았다. 정정 0건.** 오늘 수리는 그 조사를 그대로 들고 간 것이다 |
| ① 정렬 축이 틀렸다 | **핵심 맞았다** — distance 는 정렬 품질이 아니라 학생을 잰다. 곁가지 설명 3건이 틀렸다(§4) |
| ③ 허용오차가 얼었다 | **핵심 맞았다** — wobble 8.70→5.72, tol 은 잡음 기반. 틀린 건 **어느 점수에 닿느냐**(§4) |

정정된 것은 전부 **곁가지 인과 설명**이고, 전부 **같은 실수 하나**다 —
"X가 움직였다"에서 **"그래서 점수가 움직였다"로 한 칸 건너뛰었다**.
규칙으로 박았다: CLAUDE.md §7 "보고 규칙 — 관측과 진단을 섞지 말 것".

### 이 문서의 표기 규칙

`[확인]` = 코드/실측으로 소비처까지 따라간 것. **다음 세션이 승계해도 된다.**
`[미확인]` = 그럴듯하지만 끝까지 안 이은 것. **승계 전에 다시 재라. 인용 금지.**

---

## 1. 결함이 실재했다는 증거

수리 전 코드(`72b4ee2e`)를 git 에서 꺼내 같은 시나리오를 돌렸다.
재현 절차와 스크립트 = `evidence/reproduce_contamination_pre_fix.py`.

```
=== 수리 전 코드 · 동시 분석 2건 (전역 recognizer 1개 공유) ===
  분석 A: 요청= ref-power-spin → 확정=       'ref-climb'  EXTEND관절=[]
  분석 B: 요청=      ref-climb → 확정=       'ref-climb'  EXTEND관절=[]

판정: 오염 — 분석 A 가 B 의 동작 기준으로 채점됐다
```

**이것이 왜 채점 사고인가**: `ref-power-spin` 은 criteria yaml 에 EXTEND 관절(무릎 2개)이
있어 `line` 차원이 산출되고, `ref-climb` 은 EXTEND 가 0이라 `line` 차원 자체가 없다.
`dimensions.CORE_DIMENSIONS = (angle, line)` 이고 종합은 core 의 min 이므로
(`dimensions.py:548,563`), 오염되면 **종합 점수의 근거가 통째로** 바뀐다.
예외 0, 로그 0, 화면상 정상.

**도달성** (전부 코드/설정 실측):
- Pod: `/analyze` 가 동기 `def` + `BackgroundTasks` → Starlette 스레드풀
  (`server.py:433-456`). 직렬화 락 0. anyio 기본 한도 40.
- Lambda: `template.yaml:327` PipelineFunction 에 `ReservedConcurrentExecutions` **없음**
  (있는 건 visual-worker=2, visual-dispatch=1). `BatchSize: 1` 은 동시성 제한이 아니다.
- 학원은 정의상 동시 업로드.

---

## 2. 무엇을 고쳤나

원칙 하나: **분석마다 달라지는 값은 인스턴스 속성이 아니라 호출 인자다.**
값이 호출 스택을 벗어나지 않으면 직렬 leak 도 동시 오염도 구조적으로 불가능하다.
새 패턴이 아니다 — `preuploaded_handle`(27-04), `timings_ms`, `GeminiFileSession`
분석-로컬 관례를 그대로 따랐다.

| 오염 지점 | 전 | 후 |
|---|---|---|
| `recognizer.motion_query_hint` | 싱글턴 속성 (app.py:7847 쓰기 → 51~177초 → 301 읽기) | `recognize(motion_hint=...)` |
| `recognizer.unregistered_hook` | 싱글턴 속성 (app.py:7986 쓰기) | `recognize(unregistered_hook=...)`. 생성 시점 기본값은 유지(상수라 정당) |
| `extractor._last_raw_response` | 사이드카 속성, Gemini 왕복 뒤 getattr | `extract_key_moments_with_response()` **반환값** |
| `extractor._last_motion_name` | 사이드카 속성 | 폐기 (원래 질의 문자열의 왕복이었다 — §4) |
| `recognizer.extractor` lazy init | 락 없음 (인스턴스 쪼개짐) | double-checked locking |
| `_ensure_adapters()` | 락 없음 (RTMW 엔진 2벌 + ort monkeypatch 창 노출) | `_ADAPTERS_LOCK` |

**조용한 no-op 방지**: 비-frozen dataclass 는 선언되지 않은 이름에도 대입이 조용히
성공한다. 필드를 그냥 지우면 옛 호출자가 말없이 아무 일도 안 하게 되는데, 그건 이 수리가
없앤 고장과 **같은 종류**다. 그래서 `__setattr__` 이 생성 이후 대입을 `AttributeError` 로
막고, 메시지가 대체 경로를 알려준다.

수정 파일 (소스 5 + 테스트 7):
```
backend/functions/pipeline/app.py
backend/shared/python/sunity_shared/analysis/technique.py                 (Protocol + Fallback)
backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py
backend/shared/python/sunity_shared/judging/gemini_moment_extractor.py
backend/research/evaluations/compare_rtmw_vs_ipsf.py                      (sweep CLI)
backend/tests/test_analysis_local_state_concurrency.py                    ← 신규
backend/tests/{test_gemini_technique_recognizer,test_pipeline_gemini_integration,test_stage_timing}.py
backend/tests/phase06/{test_motion_query_hint_leak,test_gemini_recognizer_populates_motion_id,test_unregistered_hook_uid_threading}.py
```

---

## 3. 회귀를 어떻게 막는가

수리 시점에 리포에는 **"분석 2건이 같은 전역 객체를 동시에 만진다"를 태우는 테스트가
0건**이었다. 이름이 비슷한 `test_pipeline_body_profile_injection.py` 조차 두 worker 가
각자 별개 인스턴스를 만들어서, 사이드카가 되살아나도 통과한다. 그래서 다음 세션이
"방어선 있음"으로 오독했다.

신규 `test_analysis_local_state_concurrency.py` (8건):
- **살아 있는 동시성 3건** — 인스턴스 **하나**를 두 스레드가 공유하고, extractor 안의
  barrier 가 두 분석을 창 한가운데서 반드시 겹치게 한다. 겹치지 못하면 통과가 아니라
  timeout 실패다(조용한 위음성 차단). motion hint / unregistered hook / raw 응답 각각.
- **구조 가드 5건** — 그 중 하나가 `pipeline/app.py` 를 AST 로 훑어 `<이름>.<속성> = ...`
  (self 제외) 대입이 **0건**임을 강제한다. 2026-09-20 에 없앤 두 줄이 정확히 그 모양이다.
  같은 모양이 다시 들어오면 즉시 깨진다.

WR-07 회귀(`test_motion_query_hint_leak.py`)는 의도를 유지한 채 더 강해졌다 — 예전엔 속성을
미리 세팅하고 `_process` 1회를 돌렸는데, 이제 **mode1 분석을 실제로 돌려 오염원을 만든 뒤**
같은 싱글턴으로 mode3 를 돌린다. 대역도 `spec_set` 이라 속성 rebind 로 회귀하면 통과 불가다.

**게이트**: `4958 passed / 20 skipped / 0 failed` — `backend/.venv` 로 직접 실측
(baseline 4945). 앱 `tsc --noEmit` clean.

**변이 검증 (mutation testing)** — "통과한다"가 아니라 "고장을 잡는다"를 확인했다.
소스를 일부러 망가뜨리고 잡히는지 봤다(검증 후 md5 대조로 원복 완료):

| 변이 | 잡혔나 |
|---|---|
| `motion_hint=` 인자를 `None` 으로 | ✅ leak 테스트 2/2 |
| `unregistered_hook=` 인자 제거 | ✅ 3건 |
| **직렬 leak 재현** (모듈 전역으로 앞 분석 hint 상속) | ✅ WR-07 회귀가 잡는다 |
| 호출 인자 hook 이 인스턴스 기본값에 짐 | ✅ 3건 |
| `motion_hint` 무시하고 항상 `"auto"` | ✅ 13건 |
| **읽기측 사이드카 부활** (`getattr(extractor, "_last_motion_name")`) | ❌ → 가드 추가 후 ✅ |

마지막 항목이 실제 구멍이었다. 쓰기측 부활과 pipeline 속성 대입은 막혀 있었지만
**읽기측**은 스텁에 그 속성이 없어 폴백이 먹어서 전부 통과했다. `gemini_technique_recognizer.py`
와 `gemini_moment_extractor.py` 를 AST 로 훑어 폐기 속성 접근 0건을 강제하는 가드를 추가했고
(주석·docstring 의 언급은 허용 — 왜 없앴는지는 남아야 한다), 같은 변이로 잡히는 것을 확인했다.

---

## 4. 인계서가 틀렸던 것 (belle 전제 정정)

belle 지시 ③ — 내 보고가 belle 의 전제가 된다. 아래는 어제 인계서에 **사실과 다르게**
적힌 것들이다. 인용 전에 여기를 보라.

### ★ §6 "80 중 stability 절반은 얼어붙은 허용오차로 기계적으로 설명된다" — 성립하지 않는다

코드로 확인한 사실:
- `dimensions.py:548` `CORE_DIMENSIONS = (DIM_ANGLE, DIM_LINE)` — **stability 는 종합 입력에서
  명시적으로 제외**돼 있다(Phase 19 D-01, docstring 이 이유까지 적어놨다).
- `ref-pdshape.yaml:13-17` 의 criteria 는 4개 moment 전부 빈 리스트다 → EXTEND 관절 0 →
  `line` 차원 자체가 없다. (리포 전체에서 `extension_class: EXTEND` 는 `ref-power-spin.yaml`
  두 줄이 전부다.)
- 화면 점수는 차원 종합도 아니다 — `app.py:3186,3371` `"overallScore": breakdown.final`,
  즉 `deduction_engine` 산출이고 `ipsf_criteria.py` 의 13개 criterion 에 stability 는 **0건**이다.

→ **pdshape mode1 의 80 점에 stability 기여는 0이다.** 어제 내가 belle 에게 올린 판정은
틀렸다. 그 80 의 이동은 활성 criterion 개수(6→1)가 설명한다(실행 캡 −40 → 60 / 단건 −20 → 80).

**③ 이 죽은 건 아니다 — 소비처를 잘못 짚었다.**
`[확인]` `app.py:7046`(mode3 첫 분석)·`:7117`(second+) 둘 다
`overall_from_dimensions(abs_dims)` 를 쓰고 `abs_dims` 는 line/stability 뿐이다.
mode3 는 파일럿 성공기준 1번이다.
`[미확인]` **"그래서 mode3 종합 = stability 단독"** — mode3 도 `_apply_vision_veto` 를
타므로(`app.py:8636,8673` 이 `mode=mode` 를 넘긴다) deduction 경로가 낄 수 있다.
**끝까지 안 이었다. 이 문장을 인용하지 말고 재라** — 어제 §6 이 틀린 것과 정확히 같은
모양의 주장이다.

### §3-② "`_last_motion_name` = Gemini 가 응답한 동작 이름" — 아니다

그 필드의 **유일한 쓰기**가 `self._last_motion_name = motion` (호출자가 넘긴 질의 문자열)
이다. Gemini 프롬프트 스키마에 동작명 필드가 없어 자체 분류명은 그 필드에 들어온 적이 없다.
즉 A-1 과 A-2 는 서로 다른 값이 아니라 **같은 값을 다른 창에서 읽던 것**이다.
(부수: 그래서 mode3 는 정상 동작에서도 항상 `"auto"` → `unregistered` → `joint_expectations={}`
로 채점된다. 이건 오염과 무관한 기존 동작이고 이번 수리로 바뀌지 않는다.)

### §3-② "과거 race fix 는 직렬 누수만 고쳤다" — 과일반화

`0d1e0cdf`(HIGH-1 v4)는 진짜 동시성을 겨냥한 수리였다(사이드카 폐기 → 로컬 튜플 반환).
다만 그 회귀 테스트는 두 worker 가 **별개 인스턴스**를 써서 자기가 지킨다는 것을 안 지킨다.
recognizer 자리에 한정하면 인계서 서술이 맞다.

### §3-① 관련 (이번 수리 범위 밖, 다음 세션용)

- **"`RATE_MIN/MAX` 클램프가 있다, 거기가 옳은 자리"** — 클램프가 아니라 **위반 검출기**다
  (`motion_alignment.py:157-170`). 그리고 라이브 전건이 타는 `else` 분기(`:183-203`)가
  `slopes_ok`/`length_extreme` 을 **읽지 않고** `low_global_confidence` 를 무조건 박는다.
  → 수리는 새 축을 발명하는 일이 아니라 **이미 계산돼 있는 구조 축을 사다리의 주축으로
  승격**하는 일에 가깝다. (실제 클램프는 앱 `alignmentWarp.ts:28-30` 뿐이고
  `:79 if (a.tier !== 'warped') return 1.0;` 이라 라이브 발화 0.)
- **"짝이 시간정렬 없이 뽑힌다"** — 카드의 짝은 `motionAlignment`/`warpTime` 을 입력으로
  쓰지 않는다. `MotionMatch.path` 직접 사용 + `fault_zoom.py:588 _POSE_SEARCH_SECONDS = 4.0`
  의 **±4초 자세 재탐색**이 덮어쓴다(tier 와 무관하게 항상 작동).
  → belle 이 본 8.1초 어긋남의 실질 용의자는 tier 가 아니라 그 ±4초일 수 있다.
  tier 를 warped 로 만들어도 그 카드는 그대로일 수 있다.
- **"라이브 39건 / distance 27.0~72.0"** — 리포에 박제된 실측 셋 중 어느 것과도 표본·범위가
  안 맞는다(`motion_alignment.py:276-280` 36건 52.8~72.0 / `app.py:8656` 186건 max 63.6 /
  `app.py:2401` fixture 62.9·64.3). **0% 통과라는 결론은 셋 모두와 정합**하지만 그 수치는
  출처가 없다. 인용하지 말 것.
- **`DISTANCE_T1/T2` 는 lockstep 테스트로 `vision_veto._ALIGN_GLOBAL_T1/T2` 에 묶여 있다**
  (`test_motion_alignment.py:294-295`). vision_veto 쪽 25 는 `app.py:2199-2201 → :3241` 로
  **채점에 닿는다**. 그 상수를 직접 움직이는 수리는 "정렬=표현 전용" 계약을 깬다.

---

## 5. 같이 닫힌 것 / 종결한 미확인

**① 캐시 히트가 남의 raw 응답을 객관성 가드에 흘리던 것** (인계서에 없던 결함).
`extract_key_moments` 는 캐시 히트 시 `_call_gemini` 를 건너뛰어 `_last_raw_response` 를
갱신하지 않았다. 그래서 히트한 분석의 가드가 **직전 다른 영상의 응답**을 검사했다.
캐시가 이제 `(moments, raw_response)` 를 함께 보관해 자동으로 닫혔다.

**② rtmlib 내부 상태 — 종결(무해).** 직전 조사가 "확인 불가, Pod 필요"로 남긴 항목인데
로컬 uv 캐시에 소스가 있어 AST 로 전수 확인했다(rtmlib 0.0.13).
`Wholebody.__call__` / `YOLOX.__call__` / `BaseTool` 의 `self` 쓰기 **0건**.
유일한 호출-중 쓰기는 `RTMPose.preprocess` 의 `self.mean`/`self.std` 인데 정규화 상수를
`np.array()` 로 바꾸는 **멱등** 대입이라 영상 데이터를 담지 않는다. 상태를 가진
`PoseTracker` 는 우리 리포에서 참조 0.
→ **동시 분석이 keypoint 를 섞지는 않는다.** 오염은 동작 이름 층에 한정된다.

---

## 6. 남은 것

**★ `gemini_cache` 는 uid 스코프도 motion 키도 없다 — 오염이 영상에 영구 박제될 수 있다.**
`technique_cache.py:335` 의 키는 `{video_hash}:{model}:{yaml_version}` 이고, Firestore
`gemini_cache/{video_hash}` 는 top-level 컬렉션이다. 즉 (a) 같은 영상을 다른 hint 로
재분석하면 앞 판정을 물려받고, (b) 그 doc 은 전 사용자가 공유한다.
이번 수리는 **앞으로 생길** 오염을 막지만, 수리 이전에 캐시에 박힌 판정이 있다면 계속
재생된다. 이건 별건이고, 착수 전에 라이브 doc 로 실재 여부를 먼저 재야 한다
(Firestore 는 무료 플랜 읽기 5만/일 — 전수 스캔 금지).

**★ 새로 잰 것 — 학원 용어 수집 원장에 쓰레기 항목이 1등으로 앉아 있다.**
mode3 분석은 `motion_hint=None` → 질의 `"auto"` → `classify_motion_name("auto")` =
`("auto", "unregistered")` → **매 분석마다 `record_unregistered_keyword("auto", ...)`** 를
부른다. 라이브 Firestore 를 읽어 확인했다(읽기 8건):

```
term_collection/auto : count=52 · unique_users=25 · promotion_status="pending"
(같은 컬렉션의 다른 항목: ref-kip-up 52 · ref-pdshape 43 · ref-elbow-twist-sister 39 …)
```

`"auto"` 는 학원 용어가 아니라 **우리가 만든 내부 placeholder** 다. 그게 TERM-DATA-01
promotion 큐(pending → reviewing → approved)에 최다 tie 로 올라 있고, unique_users=25 는
바로 승격 임계를 정하는 신호다. 즉 학원 용어 학습 경로의 입력이 오염돼 있다.

**이번 수리가 만든 게 아니다** — 수리 전에도 `_last_motion_name` 의 유일한 쓰기가 질의
문자열이었으므로 동작은 같았다. 이번 변경이 그 사실을 **눈에 보이게** 만들었을 뿐이다.
수리 방향은 명확하다(질의가 `"auto"` 면 수집하지 않는다 — 아무도 말한 적 없는 단어다).
다만 이 수리에 섞지 않았다: 이번 커밋의 가장 강한 성질인 "직렬 산출 무변동"을 깨기 때문이고,
기존 52건을 어떻게 할지(삭제 / 방치)와 승격 임계 재계산은 별도 판정이 필요하다.

**분석 결함 ①(정렬 축)과 ③(얼어붙은 허용오차)은 미착수.** §4 의 정정을 반영해 다시 읽어야
한다 — 특히 ③ 은 소비처가 pdshape mode1 이 아니라 **mode3 종합점수**다.

**프로세스**: 이 작업은 GSD 커맨드(`/gsd-quick`)를 거치지 않고 직접 편집으로 진행했다.
산출물(quick 디렉터리 · SUMMARY · STATE 갱신 · 원자 커밋)은 같은 모양으로 남긴다.


---

## 7. ★★★★ `[확인]` Mode 3 종합점수는 **자세를 안 본다 — 떨림만 본다**

§4 에서 내가 `[미확인]` 으로 남긴 문장("mode3 종합 = stability 단독")을 닫았다.
**추론이 아니라 실행했다.** 결론은 더 셌다.

### 사슬 — 전부 `[확인]`, 각 칸을 실행하거나 코드로 읽었다

```
mode3 는 기준 동작이 없다        → motion_hint = None                 (app.py:7862, 실행)
  → Gemini 질의 = "auto"                                              (recognizer.py:265, 실행)
  → classify_motion_name("auto") = ("auto", "unregistered")           (실행)
  → joint_expectations = {}                                           (실행)
  → line 차원이 **생성되지 않는다**                                    (실행)
  → md(measured_deviations) = {}                                      (실행)
  → deduction tally 분기가 `and measured_deviations` 에서 걸러진다     (app.py:3272)
  → overallScore = overall_from_dimensions({stability}) = stability 단독
  → 앱 옥타곤에 그대로 표시                                            (result.tsx:1661)
```

같은 각도(전 관절 150°, 신전 30° 부족)를 두 경로에 넣은 실행 결과:

| | dimensionScores | md | 종합 |
|---|---|---|---|
| **mode3** (unregistered) | `{'stability': 100}` | `{}` | **100** |
| mode1 (ref-power-spin) | `{'line': 0, 'stability': 100}` | `{'leg_extension': 30.0, 'line': 30.0}` | 0 |

**같은 자세를 mode3 는 100 점, mode1 은 0 점으로 채점한다.** mode3 에서 차이를 만든 것은
자세가 아니라 "그 동작이 뭔지 모른다"는 사실 하나뿐이다.

### 그래서 ③ 은 내가 어제 말한 것보다 **더 중요하고, 이유가 다르다**

`_STABILITY_TOL_DEG = 15.0` 은 pdshape mode1 의 80 점에 기여가 **0** 이었지만(§4),
**mode3 점수의 100%** 다 — `round(100·exp(−½·(wobble/15)²))` 이 식 전부가 점수다.
그리고 mode3 는 **파일럿 성공기준 1번**(수강생이 본인 영상 2개 비교 → 성장 확인)이다.

즉 어제의 ③("잡음으로 잡은 허용오차가 얼었다")은 살아 있다. 다만 그게 닿는 화면은
belle 이 본 pdshape 80 점이 아니라 **Mode 3 화면 전체**다.

### `[확인]` 시스템은 이 사실을 절반만 고백한다

`_mode3_scoring_basis`(app.py:6908)가 `reference_free_absolute` 라벨을 방출한다 —
"기준 동작 없음"은 정직하게 밝힌다. 그런데 그 라벨이 뜻하는 **절대 트랙 = line + stability**
인데, 실제로는 line 이 구조적으로 절대 안 생겨서 **stability 하나**다.
라벨은 맞고 구성은 더 좁다.

### `[미확인]` — 다음에 재야 할 것

- **왜 mode3 에 동작 인식이 없나.** Gemini 프롬프트 스키마에 동작명 필드가 없어서
  분류 결과가 돌아올 구조가 아니다(`_last_motion_name` 의 유일한 쓰기가 질의 문자열이었던
  것과 같은 뿌리). **의도된 보류인지 빠진 배선인지 문서를 더 봐야 한다.** 단정하지 말 것.
- **캐시가 이 구멍을 가끔 메운다.** 같은 영상을 mode1 로 먼저 돌리면 `gemini_cache` 가
  video_hash 로만 키잉돼 있어 mode3 가 그 profile 을 상속한다 → 그 영상만 line 이 생긴다.
  즉 **mode3 점수 구성이 영상마다 달라질 수 있다.** §6 의 캐시 미결과 같은 뿌리다.
- 어제 ③ 표의 `wobble 8.70/5.72` 와 `stability 72/91` 은 **같은 계산에서 나올 수 없다**
  (산식으로 8.70→85, 5.72→93). 72/91 을 내려면 wobble 이 12.16/6.51 이어야 한다.
  그 표를 만든 스크립트가 리포에 없다 — **인용 금지, 다시 재라.**


---

## 8. ★★★★ `[확인]` 캐시 키에 동작 질의가 없다 — 같은 영상이 이력에 따라 다르게 분석된다

§7 의 `[미확인]` 두 번째를 닫았다. **실행했고, 라이브 지문도 찾았다.**

### 실행 — 같은 영상, 같은 mode3 호출, 결과가 갈린다

```
A. 이 영상을 mode3 로 먼저 (신규 학생 영상)
   mode3(hint=None)  category=unregistered  motion_id=None   dims={'stability':100}  종합=100

B. 같은 영상을 mode1 으로 먼저 → 그 다음 mode3
   mode1(hint=ref-power-spin)   recognized  ref-power-spin   dims={'line':0,'stability':100}  종합=0
   mode3(hint=None) ← 같은 영상  recognized  ref-power-spin   dims={'line':0,'stability':100}  종합=0
```

**같은 영상의 같은 mode3 분석이 100 점이 되기도 0 점이 되기도 한다** — 그 영상이 전에
mode1 으로 분석된 적 있느냐에 따라. 코드도 영상도 그대로다.

### 원인 — 캐시가 잡지 않는 입력에 결과가 의존한다

```
캐시 키 = {video_hash}:{model}:{yaml_version}    (technique_cache.py:335, 실행 출력으로 확인)
         ↑ motion 질의 없음 · mode 없음 · uid 없음
```
Gemini 호출 결과는 `(video, motion_query)` 에 의존한다 — `motion_query` 가 프롬프트에
들어가고 거기서 profile 이 나온다. **키가 입력을 다 안 담는다.** 무효화 조건도
`yaml_version`/`model` 둘뿐이라(`technique_cache.py:273,280`) 질의가 달라도 안 깨진다.

### `[확인]` 이 캐시는 전역이고 재기동을 넘어 산다

코드가 스스로 적는다 — `firestore_admin.py:2652`
`_GEMINI_CACHE_COLLECTION = "gemini_cache"  # top-level, uid 비의존 전역 공유`,
`:2646` `D-14 박제 — 영상 hash 캡싱 (gemini_cache/{hash} top-level 전역 공유)`.
Firestore 히트 시 in-memory 를 다시 채운다(`technique_cache.py:289`).
→ 프로세스 안 quirk 가 아니라 **Pod 재기동을 넘어 살아남고 사용자를 넘는다.**

### `[확인]` 라이브에 지문이 있다 (읽기 40건)

지문 = **mode3 분석인데 `recognizedMotionId` 가 있다**. mode3 는 자력으로 그 값을 만들 수
없다(hint=None → "auto" → unregistered → motion_id=None, §7).

```
표본 40건 (collection_group analyses)  →  mode1 35 · mode3 5
★ mode3 인데 recognizedMotionId 보유 = 1 / 5
   예: 53a3601...  recognizedMotionId='ref-peter-pan'  dims=['stability']  overall=98
```

### `[미확인]` — 정직하게: 그 라이브 1건은 **점수가 안 바뀌었다**

상속된 `ref-peter-pan` 은 criteria yaml 에 EXTEND 관절이 없어 line 이 여전히 안 생겼다
(리포 전체에서 EXTEND 보유는 `ref-power-spin.yaml` 하나뿐). 즉 **기전은 실재하고 실행으로
확인됐지만, 점수 구성이 실제로 뒤집힌 라이브 사례는 아직 못 찾았다.** 뒤집히려면 상속
동작이 `ref-power-spin` 이어야 한다 — 표본 40건에는 없었다.

단 motion_id 상속 자체는 점수 말고도 `_match_reference_by_motion_id`(기준 체형 조회) ·
md 키 · 코칭 · 카드 criterion 에 닿는다 — 그 파급은 아직 안 쟀다.

### `[확인]` 부수 관측 — 라이브 mode3 점수는 전부 높다

표본에서 본 mode3 3건: **98 · 98 · 93**. §7 대로 떨림만 재면 나올 값이다.
`dimensionScores` 키도 `['stability']` 또는 `['angle','stability']` — **line 없음**이
라이브에서 확인된다.

### 수리 방향 (미착수)

**캐시 키에 동작 질의를 넣는다.** 커브핏이 아니다 — 임계값·분포를 안 건드리고, 캐시가
잡지 않던 입력을 키에 넣을 뿐이다. 비용은 같은 영상을 두 모드로 분석할 때 Gemini 호출이
1회 늘어나는 것인데 **다른 질문을 하고 있으니 맞는 동작**이다.
기존에 박힌 doc 처리(무효화/방치)는 별도 판정.


---

## 9. ★ §7 정정 + 왜 mode3 에 동작 인식이 없나 (결정 이력 발굴)

### 9-1. `[정정]` 내가 §7 에서 "line 이 **구조적으로 절대** 안 생긴다"고 한 것은 과장이다

뒷문이 둘 있었다. 실행으로 확인:

```
Gemini 성공 (정상 mode3)   category=unregistered  line차원=없음  dims={'stability':100}       종합=100
Gemini 실패 (api_failure)  category=api_failure   line차원=있음  dims={'line':75,'stability':100} 종합=75
```

**Gemini 가 실패하면 자세를 채점하고, 성공하면 안 한다.** `FallbackRecognizer` 가 ≥150° 관절을
EXTEND 로 채우기 때문이다(`technique.py:129-136`). 역전이다.

두 번째 뒷문은 **캐시 상속**인데 §8 수리로 닫혔다. 문서 증거도 있다 —
`29-05-SUMMARY.md:70-71` 의 2026-07-16 Pod sweep 에서 power-spin 2키가 `md={leg_extension,line}`
였다(나머지 10키는 md 빈 dict). 그 표에서 line 이 뜬 것이 하필 **EXTEND yaml 을 가진 유일한
동작**(`ref-power-spin`)뿐인 것이 캐시 유래(=yaml 파생 profile)의 증거다 — FallbackRecognizer
였다면 기하 기준이라 12키 전부 떴어야 한다.

**정확한 문장**: mode3 는 **정상 경로에서** line 차원을 얻지 못한다. 얻는 경우는 (a) Gemini
실패 (b) 다른 분석의 profile 상속 — 둘 다 "제대로 인식해서"가 아니다.

### 9-2. `[확인]` 의도된 보류가 아니다 — **빠진 배선**이고, 한 번 식별됐다가 잊혔다

**belle 결정 D-07 (2026-06-19, `20-CONTEXT.md:34`)**:
> **판정 주체 = Gemini 인식기 3분기.** … (1) IPSF 공식 등재 → … (2) IPSF없음·정은지 보유 → …
> (3) 둘 다 미보유 → 유효성 게이트.

미보유는 **3분기 중 1개**지 정상 경로가 아니다. 그런데 지금 코드는 mode3 가 분기 1·2 에
도달할 정상 경로가 없어 **3분기가 1분기로 붕괴**해 있다.

**그리고 이건 2026-06-05 에 이미 식별됐다** — `05-05-SUMMARY.md:271-299` "박제 함정 19".
production 수리안이 표로 적혀 있다: `Path B` = "Gemini prompt 에 motion 분류 응답 추가",
`Path C` = "extractor `_last_motion_name` 가 caller query 아닌 Gemini 응답 반영".
채택된 것은 **sweep 한정 우회(Path A)뿐**이고 B/C 는 *"production 시점 별 plan"* 으로 이월됐다.
**그 후속 plan 이 `.planning` 전체에 0건이다.** 취소 기록도 0건 — 잊힌 것으로 보인다.

**그 뒤 문서 2건이 반대 사실을 적었다** (고쳐진 줄 알았던 이유):
- `deferred-items.md`(2026-06-17): *"recognizer classification is driven by Gemini's OWN visual
  read … not the hint"* → **사실과 반대**.
- `30-CONTEXT.md:26` D-04(2026-07-09): *"인식기는 이미 mode3 에서 동작 인식 중 — 저장만 안 되던 것"*
  → **사실과 반대**.

운영 프롬프트는 Gemini 에게 **동작 이름을 묻지 않는다** — `_GEMINI_PROMPT_TEMPLATE` 의 출력
스키마가 `moments` 뿐이고 파서에 그 키를 읽는 줄이 없다. 있다가 빠진 게 아니라 처음부터 없었다.

### 9-3. `[확인]` belle 의 D-08 결정이 앱에서 사라졌다

**belle 결정 D-08 (`20-CONTEXT.md:35`)**:
> **미보유(분기 3) 표시 = confident 점수 억제 + "기준 없음".** … **confident 97 금지**

백엔드는 지금도 `scoreSuppressed` 를 방출한다(`app.py:8720`). 그런데 **결과화면에는
`scoreSuppressed` 참조가 0건**이고 `result.tsx:1661` 이 점수를 무조건 그린다. 2026-09-09
재디자인에서 제거됐고(`aadf0375`·`a5089955`, `--noUnusedLocals` 죽은 코드 판정) **철회 결정
기록은 못 찾았다.** 라이브 mode3 점수가 98·98·93 인데 화면은 그걸 그대로 confident 하게 띄운다.

남은 소비처는 홈뿐이다 — `growthSelectors.ts:74` · `(tabs)/index.tsx:81` 이 억제된 분석을
성장 지표에서 뺀다. **한 분석이 화면마다 다른 대접을 받는다.**

### 9-4. ★ `[확인]` §8 수리의 부작용 — 정직하게

`_score_suppression_reason`(app.py:6954)은 `category == "unregistered"` 면 무조건 억제한다.
§8 캐시 수리가 mode3 를 `recognized` 로 만들던 **유일한 뒷문**을 닫았으므로:

```
수리 전 : mode3 는 대개 억제(성장 그래프 제외), 가끔 캐시 상속으로 통과(단 남의 동작 기준)
수리 후 : mode3 는 항상 억제 → 홈 성장 그래프에서 항상 제외
```

**mode3 는 파일럿 성공기준 1번이다.** 그러니 이렇게 적어야 한다 —
**"mode3 가 고쳐졌다"고 보고하면 거짓말이다.** 간헐적으로 틀리던 분석이 일관되게 얄팍한
분석으로 바뀐 것이다. 캐시 수리는 옳고 되돌리면 안 되지만, **짝이 따라와야 한다.**

### 9-5. `[미확인]` — 수리 착수 전에 반드시 잴 것

**Gemini 가 폴 동작 이름을 맞히는가 — 측정 0회.** 이게 Path B 의 유일한 전제다.
05-05 의 "분류 정확도" 수치들은 전부 **묻지도 않은 프롬프트**에서 나온 것이라 능력의 증거가
아니다. 현 프롬프트에 `motion_name` 출력만 더한 판으로 정은지 ref 10편 + 학생 영상 몇 편을
돌려 응답을 박제하는 spike(운영 코드 무접촉)가 선행해야 한다. **못 맞히면 Path B 는 폐기하고
다른 축을 찾는다.** [[recommend-only-after-measuring-the-deciding-fact]]

그 밖에 못 닫은 것: 09-09 억제 UI 제거가 belle 승인 범위였는지(문서로 못 가린다) ·
캐시 상속이 점수를 실제로 뒤집은 라이브 사례(아직 0건) · hold_window/key_moments 상속의 2차 파급.


---

## 10. belle 의 도메인 지적이 측정 설계를 바꿨다 + 실측 4건

### 10-0. `[확인]` belle 지적이 맞고, belle 이 이미 결정해 둔 것이다

> belle 2026-09-20: "폴 동작 이름이 애초에 학원이랑 대회랑 좀 다르고 학원마다도 살짝 다른데 괜찮나?"

맞다. 그리고 belle 이 **2026-06-01 에 이미 결정**했다 — *"이걸 하나로 통일하기엔 사실 문제가
한두가지가 아니야… 코치가 원한다면 코치 용어를, 대회를 원한다면 대회 기준 용어를"*.
명칭 체계가 최소 5개(학원 통상명 / IPSF / KPSA / 코치별 / 대회별)다.

→ **내가 §9-5 에서 제안한 측정("Gemini 가 동작 이름을 맞히는가")은 정답지가 없는 질문이다.
폐기한다.** 채점이 실제로 쓰는 것은 이름이 아니라 **어떤 기준을 걸 것인가**이고, 이름은
그 기준을 찾는 중간 키일 뿐이다.

### 10-1. `[확인·실행]` 객관 criteria yaml 은 10개 중 1개뿐이다

```
yaml                          EXTEND  BENT_OK
ref-power-spin                     2        0   ←★ 유일
나머지 9개                          0    0 또는 6
```

우연이 아니라 결정이다 — `ref-pdshape.yaml:6-8` 이 적는다: *"pdshape 는 IPSF element
미등재(학원 명칭) + **곧아야 할 객관 관절 부재** → 객관 angle criteria 없음. 결함(자유 다리
무릎 굽음)은 **reference_relative(정은지 대비)** 가 처리."*
(belle 2026-06-27 결정으로 knee EXTEND 를 명시적으로 **제거**했다 — 굽힘 form 에 신전기준
강요 금지, anti-curve-fit.)

### 10-2. `[확인·실행]` 그래서 동작을 **완벽히** 인식해도 점수는 9/10 에서 안 바뀐다

등록 동작 10개 전부를 인식 성공으로 가정해 돌렸다(같은 자세, 전 관절 150°):

```
동작                     line차원   종합    억제사유    홈 성장그래프
ref-power-spin            있음        0     None        포함     ←★ 유일
나머지 9개                 없음      100     None        포함
현행 mode3(미인식)          없음      100     unheld      제외
```

**인식이 고치는 것은 점수가 아니라 억제**다. 9/10 은 종합이 100(떨림 단독) 그대로인데
억제만 풀려 **자신 있게 100 점을 띄운다** — belle D-08 *"confident 97 금지"* 가 막으려던 바로 그것.
→ 인식만 고치면 **더 나빠진다.**

### 10-3. ★ `[확인]` 그런데 채점 기준은 yaml 만이 아니다 — 재료가 이미 손에 있다

`ref-pdshape.yaml` 이 말한 그 **reference_relative** 경로가 코드에 실재한다:
`app.py:2861` `md[f"angle_vs_reference__{jk}"] = v` — 정은지 대비 per-joint 각도 편차.

그 경로의 관문은 `app.py:2906`:
```python
if reference_dtw_match is not None and reference_angles is not None and angles is not None:
```
**mode 게이트가 아니라 데이터 게이트다.** mode3 가 그 둘을 넣어주면 같은 코드가 그대로 돈다.

그리고 재료가 이미 있다 — 라이브 Firestore 실측(읽기 12건):
```
reference 컬렉션 12건 → 각도 시계열 보유 11 / 11 (ref-combo 931프레임 … ref-kip-up 118프레임)
```
게다가 **mode3 는 이미 그 doc 을 가져온다** — `app.py:8371 _match_reference_by_motion_id(motion_id)`.
다만 지금은 **체형 비교(bodyNormalizationProfile)에만** 쓰고 `angles` 는 안 쓴다.

→ 수리는 새 채점 로직도 새 임계값도 아니다. **이미 있는 관문에 이미 있는 재료를 먹이는 것**이다.

### 10-4. `[미확인]` — 아직 안 쟀다. 단정 금지

- **인식이 얼마나 맞는가.** 이름이 아니라 **"우리 기준 동작 11개 중 어느 것인가"** 를 맞히는
  정확도다(정답지 = 정은지 라이브러리 하나 → 학원 명칭 문제 통과). 측정 0회.
- **틀린 매칭의 대가.** 엉뚱한 기준과 비교하면 감점이 통째로 틀린다. 현행(떨림만 100점)보다
  나쁜가 아닌가는 매칭 정확도에 달렸다 — **재기 전에는 권장하지 않는다.**
- DTW distance 로 매칭하는 대안은 위험하다 — distance 가 "학생이 얼마나 다른가"를 재므로
  (§4) 못하는 학생일수록 엉뚱한 동작에 붙을 수 있다.
