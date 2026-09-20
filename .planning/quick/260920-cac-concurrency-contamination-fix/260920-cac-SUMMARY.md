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


---

## 11. ★★★★ 매칭은 공짜로 쟀다 + 빈 yaml 이 스스로 답을 적어놨다

### 11-1. `[확인·실측]` 매칭 정확도 — 크레딧 0, Pod 0

라벨이 공짜로 있었다: **mode1 분석의 `referenceMotionId` = 사용자가 직접 고른 기준 동작**.
학생 각도 시계열도 doc 최상위에 저장돼 있다. 라이브 78건(6동작) 확보(Firestore 120 read).

저장된 각도만으로 정은지 기준 11개와 DTW 매칭:

```
★ DTW      top-1 = 67/78 = 85.9%
  profile  top-1 = 57/78 = 73.1%   (분포 대조군)

혼동표: kip-up 22/22 · pdshape 12/12 · power-spin 12/12 ·
        elbow-twist 10/10 · peter-pan 4/4 · climb 7/18
        ★ 오분류 11건이 **전부** climb → sideway-spin 한 쌍이다
```

마진(1등 대비 2등 상대거리) 분포:
```
맞춘 67건 : 최소 0.069 · 중앙 0.881 · 최대 9.306
틀린 11건 : 최소 0.045 · 중앙 0.048 · 최대 0.056   ← 좁은 띠에 몰려 겹치지 않는다
```

★ **주의 — 이 분리로 통과선을 정하면 커브핏이다.** 관측은 "오분류가 한 쌍이고 그 쌍의
마진이 균일하게 낮다"이지 "문턱 0.10 이 옳다"가 아니다. 표본 78건·6동작이고,
나머지 5동작(foxtop·foxtop-split·invert·sideway-spin·combo)은 학생 분석이 **0건**이라
정확도가 **미측정**이다. [[chasing-the-number-is-the-tangle]]

### 11-2. ★ `[확인·실측]` 기준이 있는 동작은 아무도 안 올리고, 올리는 동작은 기준이 없다

```
동작                     학생 분석   angle_target   EXTEND
ref-kip-up                    22           0         0   ← 기준 없음
ref-climb                     18           0         0   ← 기준 없음
ref-pdshape                   12           0         0   ← 기준 없음
ref-elbow-twist-sister        10           0         0   ← 기준 없음
ref-peter-pan                  4           0         0   ← 기준 없음
ref-power-spin                12           2         2   ← 유일한 교집합
ref-foxtop / -split / invert / sideway-spin
                               0        6/6/6/6       0   ← 기준 있는데 학생 0건

★ 라이브 학생 분석 78건 중 '걸 기준이 있는 동작' = 12건 (15%)
```

### 11-3. ★★ 그런데 빈 yaml 들이 **스스로 대안을 적어놨다**

`ref-peter-pan.yaml:9-11` (belle 2026-06-27 결정문):
> "곧아야 할 객관 관절 부재 → 객관 angle criteria 없음. 다른 관절(shoulder/elbow)은
> **reference_relative(정은지 대비)** 가 처리."

`ref-pdshape.yaml` · `ref-kip-up.yaml` 도 같은 문장. 즉 **criteria 가 빈 것은 결함이 아니라
설계**이고, 그 자리를 메우도록 지정된 것이 **"정은지 대비 per-joint 비교"**다.

그 경로가 코드에 실재한다 — `app.py:2861` `md[f"angle_vs_reference__{jk}"]`.
관문은 `app.py:2906`:
```python
if reference_dtw_match is not None and reference_angles is not None and angles is not None:
```
**mode 게이트가 아니라 데이터 게이트다.**

재료도 있다 — `reference` 컬렉션 **11/11 이 각도 시계열 보유**(실측), 그리고
**mode3 는 이미 그 doc 을 가져온다**(`app.py:8371`) — 체형 비교에만 쓰고 angles 는 안 쓸 뿐이다.

### 11-4. 그래서 사슬이 이렇게 이어진다 (각 칸 `[확인]`)

```
mode3 가 어느 기준과 비교할지 안다  ← 인식. 오늘 공짜로 85.9% 측정 (11-1)
  → 이미 가져오는 reference doc 의 angles 를 쓴다        (11-3, 실측 11/11 보유)
  → motion_dtw 로 reference_dtw_match 를 만든다          (mode1 이 하는 것과 같은 함수)
  → app.py:2906 데이터 관문 통과 → angle_vs_reference__{jk} 가 md 에 실린다
  → deduction tally 가 돈다 → 점수가 **자세를 반영한다**
```

**새 채점 로직도 새 임계값도 없다.** 빈 yaml 이 "reference_relative 가 처리한다"고 적어둔
그 경로를 mode3 에도 붙이는 일이다.

### 11-5. `[미확인]` — 아직 안 쟀다. 이게 다음 측정이다

- **틀린 매칭의 대가.** climb 을 sideway-spin 으로 잘못 붙이면 감점이 통째로 틀린다.
  지금(떨림만 98점)보다 나쁜가? **오프라인으로 잴 수 있다** — 저장된 각도에 맞는 기준/틀린
  기준을 각각 걸어 `md` 와 점수를 비교하면 된다. Pod 0 · Gemini 0 · Firestore 0(캐시 보유).
- **매칭 실패를 거절로 돌릴 때 무엇을 잃나.** 거절 = 현행(떨림 단독 + 억제) 유지다.
- 학생 분석 0건인 5동작의 매칭 정확도 — 라벨이 없어 못 잰다.

### 11-6. 판정 — belle 이 D-08 로 금지한 것이 지금 화면에 떠 있다

인식만 고치면 `_score_suppression_reason`(app.py:6954)의 억제가 풀려 **떨림 단독 98 점이
홈 성장 지표로 들어간다** — belle D-08 *"confident 97 금지"* 그 자체다.
그래서 **인식 수리는 11-3 의 reference_relative 배선과 한 묶음으로만 의미가 있다.**
따로 내보내면 순수 악화다.


---

## 12. `[확인·실측]` reference_relative 를 mode3 에 걸면 어떻게 되나 — 오프라인 전량 측정

Pod 0 · Gemini 0 · Firestore 0(전부 캐시). 라이브 78건 + 정은지 11편.
방법: 저장된 학생 각도에 `motion_dtw(학생, 정은지)` 를 걸어 `reference_dtw_match` 와
`reference_angles`(T,J 배열)를 만들고, 운영 함수 `_build_deduction_measured_deviations` →
`deduction_engine.tally` 를 그대로 호출했다. **채점 코드를 재구현하지 않았다.**

### 12-1. 점수가 실제로 움직인다

```
                    현행(떨림단독)          정답 기준          DTW 선택 기준
매칭 맞은 67건   89.8 (중앙 91)      79.3 (중앙 70)      79.3 (중앙 70)
매칭 틀린 11건   93.0 (중앙 93)      60.0               60.0
```
md 항목: 현행 **0개** → reference_relative **8개**(관절 전부). 자세가 점수에 들어온다.

### 12-2. 타당성 게이트 통과 — 정은지를 학생으로 넣으면 감점 원천이 0이다

```
동작 11편 자기비교 → angle_vs_reference__ 키 수 = 0 (9/11)
   ref-power-spin 만 md 2개(leg_extension, line) = IPSF 180° 신전 기준 → 80점
```
★ 편차가 0 이면 **키를 아예 안 만드는** 계약이다(`_build_deduction_measured_deviations`
docstring: *"없으면 키 부재 → honest 0"*). 따라서 **md 가 비는 것이 통과 신호**다.
자기비교 점수가 100 이 아닌 것은 감점이 아니라 **떨림(stability) 단독 base** 때문이고,
그 값(88~98)은 정은지 본인 영상의 떨림 측정값이다.

★ 단 `ref-power-spin` 80 점은 **정은지 본인이 IPSF 180° 신전 기준으로 감점당한다**는 뜻이다.
이건 이번 축이 만든 게 아니라 mode1 의 기존 동작이다 — 별건으로 봐야 한다.

### 12-3. ★ 틀린 매칭의 대가 = **점수가 관대해진다** (위음성 방향)

정은지 대비 per-joint 편차 중앙값(도):
```
                     정답 기준   틀린 기준
매칭 맞은 67건          19.5      19.5
매칭 틀린 11건          27.4      18.1   ← 틀린 기준이 편차를 **작게** 만든다
```
DTW 가 그 기준을 고른 이유가 바로 "더 가까워서"다. 즉 climb 을 sideway-spin 으로 잘못 붙이면
**덜 틀린 것처럼 보인다.** 핵심 가치의 "고수가 낮게 나오는 위양성"과 반대 방향인
**못하는데 높게 나오는 위음성**이다. (이번 표본에서는 둘 다 실행 캡 바닥 60 에 닿아 최종
점수로는 차이가 안 드러났다 — 캡에 안 닿는 구간에서는 드러난다.)

### 12-4. 동작별 "정은지와 얼마나 다른가"(정답 기준, 중앙값)

```
ref-climb 27.4도 · ref-elbow-twist-sister 24.0 · ref-pdshape 20.8
ref-power-spin 20.2 · ref-peter-pan 13.9 · ref-kip-up 8.1
```
★ `[미확인]` 이 차이가 **학생 실력**인지, **그 동작이 원래 정렬이 어려운 것**인지
(climb 은 반복 동작이라 DTW 가 붙기 어렵다), **촬영 각도**인지 **가르지 않았다.**
결함 ①(DTW distance 가 학생을 잰다)과 같은 성질의 혼동이 여기에도 있다.
**이걸 가르기 전에는 "점수가 맞아졌다"고 말할 수 없다.**

### 12-5. 판정

**경로는 이어지고 점수는 움직인다. 그 점수가 옳은지는 아직 모른다.**
- `[확인]` 배선은 가능하다 — 새 채점 로직 0, 새 임계값 0, 운영 함수 그대로.
- `[확인]` 자기비교 게이트를 통과한다(감점 원천 0).
- `[확인]` 틀린 매칭은 점수를 **관대하게** 만든다 → 거절(매칭 포기)이 안전한 기본값이다.
- `[미확인]` 편차 19.5~27.4도가 "못했다"인지 "계기가 흔들린다"인지 **안 갈랐다.**
  → 다음은 belle 눈이다: 몇 건을 사진으로 보이고 *"이 영상이 이 점수가 맞나"* ○×.
  그 전에는 배포하지 않는다. [[belle-eye-is-the-answer-key-predict-before-asking]]


---

## 13. ★★★★ `[확인·실측]` §12-4 의 `[미확인]` 을 사람 눈 없이 닫았다 — **이 축은 학생이 아니라 동작을 잰다**

belle 2026-09-20: *"아이 이걸 또해?"* — 맞는 지적이다. 내가 §12-5 에서 belle 눈 ○× 를
다음 단계로 올렸는데, 그건 내가 스스로 적어둔 [[belle-confirmation-is-not-a-fix]]
(*"사람이 알려줘야 성립하는 해법은 답이 아니다"*)를 정면으로 어긴 것이다. 분산으로 갈랐다.

### 방법 — 사람 눈이 필요 없는 이유

계기/동작 탓이면 **학생이 누구든 같은 값**이 나오고(동작 안 분산 ≈ 0),
실력 신호면 **학생마다 흩어진다**(동작 안 분산 큼). 라이브 78건으로 분산분해.

### 결과

```
동작                      n     중앙   표준편차      최소~최대
ref-climb                18    27.4     4.88     7.2~28.0
ref-elbow-twist-sister   10    24.0     0.55    22.4~24.5   ← 사실상 상수
ref-pdshape              12    20.8     5.06     5.1~26.0
ref-power-spin           12    20.2     4.69     7.4~20.6
ref-peter-pan             4    13.9     0.59    13.8~15.2   ← 사실상 상수
ref-kip-up               22     8.1     1.57     2.7~8.7    ← 사실상 상수

★ 동작내 분산이 전체 분산을 설명하는 비율 = 21%
  → 나머지 79% 는 "어느 동작이냐"가 정한다
```

각 동작의 **최대값이 좁게 뭉쳐 있다**(climb 28.0 · elbow-twist 24.5 · pdshape 26.0 ·
power-spin 20.6 · kip-up 8.7). 동작마다 천장이 따로 있는 모양이다.

### 판정 — 지금 상태로 배포하면 안 된다

**편차 19.5~27.4도는 대체로 "학생이 못한다"가 아니라 "그 동작은 정은지와 그만큼 달라
보인다"이다.** 이대로 켜면 kip-up 한 학생은 누구든 높은 점수를, climb 한 학생은 누구든
낮은 점수를 받는다 — **사람이 아니라 동작을 채점한다.**

핵심 가치가 금지한 위양성(*"고수가 낮게 나오는"*)과 같은 모양이고, 결함 ①(DTW distance 가
학생을 잰다)과도 같은 성질이다. **점수가 움직이는 것과 맞게 움직이는 것은 다르다.**

### 남은 실력 신호 21% 와 다음 단서 `[미확인]`

동작 안 분산 2.89도가 실력일 가능성이 있다(pdshape 5.1~26.0, climb 7.2~28.0 은 실제로
넓다). 즉 **동작별 상수 오프셋을 걷어내면 그 밑에 신호가 있을 수 있다.**

단 그 오프셋을 동작별로 fit 하면 그게 커브핏이다. 물어야 할 것은 *"오프셋이 어디서 오나"* —
후보: 정은지와 학생의 **체형 차이**(리포에 `body_normalizer` 가 이미 있는데 이 축에
적용되는지 안 봤다) · 촬영 각도 · 동작별 DTW 정렬 난이도(climb 은 반복 동작).
**이걸 가르는 것이 다음 측정이고, 이것도 오프라인으로 된다.**

---

## 14. ★★★★ §13 다음 측정 — 답이 나왔고, **§13 의 판정은 무너졌다**

belle 가 고른 것 = "§13 다음 측정 실행"(동작별 상수 오프셋이 어디서 오나 — 체형 / 촬영 각도 /
DTW 정렬 난이도). 오프라인 전량: **Pod 0 · Gemini 0 · GPU 0 · 크레딧 0.** Firestore 는 읽기만
(약 3,100건, 일일 캡 5만). 측정은 전부 운영 함수 호출이고 채점 코드 재구현은 없다.

### 14-0. 판정 — 살아남은 것부터

**§13 이 물은 것은 답이 나왔다.** 후보 넷 중 셋이 실측으로 떨어졌다.
남은 것은 **포즈 추정이 같은 영상에서 스스로를 재현하지 못하는 것**이고,
그 크기를 정하는 것은 **그 동작의 역립 프레임 비율**이다(Spearman 0.891).

**그러나 §13 의 판정 — "이 축은 사람이 아니라 동작을 잰다, 배포 금지" — 은 무너진다.**
기준 버전을 맞춰 다시 재면 **정은지 본인 영상은 11동작 전부 100점**이고(예외 0건),
§13 이 "죽었다"고 지목한 pdshape·elbow-twist 가 오히려 결함을 **가장 크게** 가른다(+37·+34).

**그리고 그보다 큰 것이 나왔다 — 표본에 학생이 없다.** §11·§12·§13 이 "라이브 학생"이라 부른
것은 **정은지 fixture 영상 12편 안팎의 재분석**이다. 동작당 고유 영상 = correct 1편 + fault 1편.

**그래서 최종 판정은 "된다"가 아니라 "아직 못 말한다"다.** 축은 정은지 영상에서 옳게 동작한다.
학생 영상은 **단 한 번도 이 축에 태워진 적이 없다.**

---

### 14-1. ★ `[확인]` 표본의 정체 — 875건은 학생이 아니다

`collection_group('analyses')` 전수 스캔(1,250 문서):

```
done + referenceMotionId + angles = 875건 (전부 mode1)
  videoKey 접두 : fixtures/ 664 · 없음 164 · uploads/ 32 · reference/ 13
  동작당 고유 videoKey = 1~8개
  ★ 동작당 고유 영상 = correct 1편 + fault 1편 (나머지는 같은 파일의 재분석)
  실제 사용자 업로드 32건 중 26건이 한 uid 의 **같은 pdshape 영상 1편**
```

uid 상위: `phase25eval` 368 · `phase24eval` 162 · `phase15_mode1_*` 약 90 ·
`mock_* / genpod / verify / probe / e2e` 약 50. **평가 하네스가 같은 영상을 수십~수백 번 돌린 것**이다.

**그 fixture 의 정체도 확정했다** `[확인]` — `fixtures/phase15/{동작}/correct.mp4` 는
**기준 영상 그 자체**다. 근거 셋:
(a) 6/6 동작에서 학생 프레임 수가 기준의 **정확히 2/3** (118→79 · 130→87 · 159→106 ·
    120→80 · 329→220 · 237→159). fault 쪽은 2/3 이 아니다(비 0.48~0.77);
(b) pdshape 의 일치 프레임 78장이 Procrustes 정합에서 프레임별로 대응한다;
(c) [[jeongeunji-success-fail-pair-dataset]] 이 "추가 6개 reference = 이 페어 배치"라고 적는다.

→ **correct 행은 전부 자기비교다 — 실력차가 0 인 조건.** 이 사실이 이번 측정을 가능하게 했다.

`[미확인]` 실증이 2026-10 중순으로 밀렸으니([[pilot-postponed-to-mid-october]]) 학생 영상이
없는 것 자체는 자연스럽다. **문제는 없다는 사실이 아니라 그걸 "라이브 학생 78건"이라 부른 것이다.**

---

### 14-2. ★ `[확인]` §12-2 의 타당성 게이트는 공허했다 — 제대로 걸면 통과하되 이유가 다르다

§12-2 는 *"동작 11편 자기비교 → `angle_vs_reference__` 키 수 = 0 (9/11)"* 으로 게이트를
통과시켰다. 그건 **기준의 저장 각도 행렬을 학생 자리에 그대로 넣은 identity 비교**다.
0 이 나오는 게 당연하다 — 게이트가 아무것도 검사하지 않았다.

```
게이트를 거는 세 방법                          편차(도)
(A) §12-2 방식 — 저장 각도를 그대로 넣기        0.0000   (identity)
(B) 같은 행을 솎기만 하기                       0.000    (DTW 가 원본 행을 되찾는다)
(C) 실제 라이브 경로(같은 영상을 다시 추출)     2.3 ~ 15.8
```

★ **그래도 점수는 안 깎인다** `[확인]` — 이 축의 감점 허용오차가 `_ANGLE_TOLERANCE_DEG = 20.0`
(`ipsf_criteria.py:32,158`, kismam 차용값)이라 15.8도는 데드존 안이다. 버전을 맞춰 운영
`deduction_engine.tally` 로 재산출하면 **정은지 본인 영상 100점, 감점 record 0건** —
pdshape correct 100/100건, elbow-twist correct 54/54건, 예외 없음.

→ **§12-2 의 결론은 맞았다. 근거가 틀렸다.** 진짜 이유는 "편차가 0이라서"가 아니라
**"편차가 허용오차 20도 아래라서"**다. 그리고 §12-2 에는 **여유가 얼마인지가 없다.**

★ **여유는 2.0~2.3도다** `[확인]` — 같은 영상 재분석에서 관측된 최악값:
elbow-twist **18.00** / pdshape **17.69** (허용오차 20.0). 학생은 정은지가 아니다.

---

### 14-3. ★ `[확인]` §12·§13 이 본 점수 이동은 **기준 버전 불일치**였다

기준 11편은 **2026-09-17 에 `rot180_v1` 으로 승격**됐다
(`reference/_release.activeCandidate = "rot180_v1"`, 각 doc `reprocessedAt` 05:02~05:09,
근거 `.planning/quick/260917-hjy-reference-drift-all11/`, belle 승인,
`start_server.sh:24 ROT180_INVERSION_ENABLED=1` 과 **한 묶음**).

승격이 기준 각도를 옮긴 양 (`versions/phase4_v1` vs 현재 top-level, 중앙 |Δ각도|):

```
안 옮긴 5동작 : kip-up 0.00 · peter-pan 0.00 · power-spin 0.00 · sideway-spin 0.00 · climb 0.13
옮긴   6동작 : combo 14.55 · invert 15.99 · foxtop-split 19.15 · foxtop 20.87
                · pdshape 25.99 · elbow-twist-sister 28.54
```

저장된 875건 중 **871건이 그 승격 이전**이다(rot180 OFF 로 추출된 학생 각도).
§12·§13 은 그 학생 각도를 **승격 이후의 기준**과 비교했다 — 한쪽만 교정된 비대칭이고,
`start_server.sh:24` 주석이 이름으로 경고해 둔 바로 그 상황이다.

```
                          버전 불일치(§12·§13)   버전 일치(정본)
pdshape 자기비교                 24.3                 15.0
elbow-twist 자기비교             22.2                 15.8
   → 그 6도가 허용오차 20도 선을 넘나든다

같은 분석을 두 기준으로 운영 tally 에:
pdshape correct                  60점                100점   ← 정은지 본인 영상이 40점 깎였다
elbow-twist correct              74점                100점
```

→ §12-1 의 *"현행 89.8 → 정답 기준 79.3(중앙 70)"* 과 §13 의 *"동작을 채점한다"* 는
**상당 부분 이 불일치가 만든 것이다.** [[trace-the-number-to-its-consumer-before-reporting]]

`[미확인]` 라이브 화면 영향은 안 쟀다. 새 분석은 양쪽 다 rot180 이라 정합하고 저장된 분석은
재채점되지 않는다. 다만 **09-17 이전 점수와 이후 점수는 기준이 다르다** — 09-17 요약도
같은 말을 적어놨다("점수 연속성이 끊기는 것은 그 6편을 참조한 분석뿐").

---

### 14-4. ★ `[확인]` 바닥은 어디서 오나 — 후보 넷 중 셋을 떨어뜨렸다

바닥 = 정은지 본인 영상을 자기 기준과 비교했을 때의 편차(실력차 0). 버전 일치:

```
sideway-spin 2.3 · kip-up 2.7 · peter-pan 5.0 · climb 7.3 · power-spin 7.5
invert 9.2 · combo 9.5 · foxtop-split 12.3 · foxtop 13.4 · pdshape 15.0 · elbow-twist 15.8
```

| 후보 | 실측 | 판정 |
|---|---|---|
| **체형** | correct/self 는 같은 사람·같은 영상 | **구조적으로 배제** |
| **시간 격자** | 기준 행렬을 학생 격자로 재샘플 → **0.000도, 11/11**. 보간으로 세운 상한도 0.84~2.07도 | **0% ~ 상한 10~13%** |
| **DTW 정렬** | 같은 두 행렬에 경로만 갈아끼워 운영 `per_joint_deviation` 재호출 → **DTW 가 참 선형 대응보다 낫다**(foxtop 15.4<18.2 · pdshape 24.4<30.3, 11동작 중 9동작 경로몫 음수) | **기계는 결백하다** |
| **촬영 각도** | self 행은 카메라 불일치가 **정의상 0**인데 바닥 2.3~17.2 | **필요조건 아님** |
| **입력 키포인트** | 아래 | **남은 것** |

★ **직접 증거** `[확인]` — 기준은 원본을 step 2 로, 학생은 step 3 로 솎으므로 **학생 짝수 행은
기준과 정확히 같은 원본 프레임**이다. 그 프레임만의 잔차가 운영 편차와 같은 크기다:

```
동작              같은 원본 프레임 잔차   운영 편차
sideway-spin              2.00            2.32
invert                   15.82           15.33
combo                    15.31           13.59
foxtop                   16.99           15.37
foxtop-split             18.98           17.16
```

**시간정렬을 완전히 통제해도 바닥이 그대로 남는다.** 그리고 pdshape 의 일치 프레임 78장을
Procrustes 정합(전역 이동·회전·배율 제거 — 각도는 어차피 그것들에 불변)하면
**40~44% 프레임에서 관절 하나가 몸통 길이 이상 다른 곳에 있다**(p90 잔차 1.0~2.1 torso).
흔들림이 아니라 골격이 통째로 다르다.

★ **바닥의 크기를 정하는 것은 역립 프레임 비율이다** `[확인]` —
기준 `joints3d`(pole_aligned)에서 어깨가 골반보다 아래인 프레임 비율:

```
climb 0.8% · sideway-spin 1.3% · kip-up 1.7% · peter-pan 4.6% · power-spin 18.9%
invert 35.4% · combo 45.1% · foxtop-split 68.0% · foxtop 69.0%
elbow-twist 80.2% · pdshape 89.9%
                         바닥과 Spearman rho = 0.891  (climb 제외 0.952)
```

**한 영상 안에서도 같은 관계가 성립한다** — combo(역립·정립이 섞인 클립)의 프레임 잔차가
역립도 사분위를 따라 **5.5 → 17.6 → 24.5 → 31.2도**, 정립 프레임 11.1 vs 역립 프레임 28.4.
(같은 순서를 09-17 rot180 승격이 기준을 옮긴 양도 재현한다 — 안 옮긴 5동작 바닥 2.3~7.5,
옮긴 6동작 9.2~15.8, 겹침 0. 기준 `keypointReport` 저신뢰 프레임 비율과는 Spearman +0.891.)

**떨어진 부수 가설 3건** `[확인]`:
실행 간 비결정성(같은 videoKey 재분석 각도행렬 median|Δ| 0.00~0.10도, self 3건은 byte-동일) ·
좌우 라벨 스왑(L/R 교환하면 15.8~19.0 → 23.1~33.7도로 악화) ·
iid 프레임 잡음(추정 잡음을 주입하면 0.88~3.62도, 관측 바닥의 1/5).

★ **무작위 대조** `[확인]` — 정렬 창 안에서 기준 프레임을 무작위로 짝지으면(시간정보 0)
바닥/우연 비가 **0.14~0.53**(버전 일치, seed 5개 중앙). **우연 수준에 붙은 동작은 없다.**
(§13 계열의 "chance 의 82~86%" 는 버전 불일치 판 + 다른 chance 정의다 — 두 수를 섞지 말 것.)

`[미확인]` ★ **이건 동정이 아니라 소거다.** 어느 추출이 맞는지, 원인이 무엇인지 안 갈랐다.
로컬에서 보이는 유력 후보 둘:
- `temporal.occluded_mask` 의 **격자 의존성** — 폐색 판정이 그 시퀀스 불확실도 분포의
  `median + 3·MAD` 라는 **상대 기준**이고(`temporal.py:28-31`), 폐색 프레임 값은 이웃에서
  선형보간으로 대체된다. 10fps 격자와 15fps 격자는 이웃도 분포도 다르다.
  **불확실도 배열이 doc 에 없어 못 쟀다.**
- `temporal.DEFAULT_SMOOTH_WINDOW = 5` 가 **프레임 단위**라 기준 축 0.334초 / 학생 축 0.501초 —
  같은 영상인데 평활 구간이 다르다. 실측 기여는 ~1도로 작다.
- 그리고 **기준 doc 의 저장 `angles` 는 그 doc 자신의 `joints3d` 로 재계산되지 않는다**
  (현재 운영 `features.compute_joint_angles` 로 다시 계산하면 median|Δ| 2.21~17.43도,
  1e-6 이내 일치 프레임 0.0000). 기준 각도가 지금 코드와 다른 판에서 구워졌다는 뜻이다.

**닫으려면 GPU 가 필요하다** — 같은 프레임을 두 설정으로 다시 돌리는 일이다.

---

### 14-5. `[확인]` 버전을 맞춘 정본 표 — 이 축이 점수에 하는 일

운영 함수 그대로(`_deviation_against` → `_build_deduction_measured_deviations` →
`deduction_engine.tally`). 기준은 각 분석이 실제로 채점됐던 버전.

```
동작                     정은지 본인 영상    일부러 낸 결함    분리
ref-pdshape                   100                63          +37
ref-elbow-twist-sister        100                66          +34
ref-peter-pan                 100                80          +20
ref-power-spin                100                80          +20
ref-climb                     100                92           +8
ref-kip-up                    100               100           +0   ← 이 경로에선 못 잡는다
combo / foxtop / foxtop-split / invert / sideway-spin   100    (fault 영상 없음)

전이함수 (운영 상수, 손계산 == tally.final 698/698):
  관절 감점 = min(20, 1.2 x max(0, 편차 - 20.0))      final = max(25, 100 - min(40, 합))
```

**위양성 0** — 정은지 본인 영상 전 분석(correct 345 + self 13)이 100점, 예외 없음.
§13 이 "죽었다"고 한 두 동작이 **가장 잘 가른다.**

### 14-6. ★ `[확인]` 내 표에도 구멍이 있다 — 운영에는 분기가 하나 더 있다

적대 검증이 찾아냈다. 운영 mode1 은 `vision_pointed_joints`(Gemini 가 짚은 관절)에 대해
DTW path median 대신 **worst-window median** 을 쓴다. 내 재구성은 `quantification=None` 이라
그 분기가 꺼져 있었다. 그리고 `app.py:2808-2812` 주석이 **이 건을 이름으로 지목한다** —
*"kip-up 어깨 Δ40° 처럼 국소 결함이 전체 DTW path median 에서 tol 미만으로 희석되던
'표시는 40°인데 감점 0' 해소"*.

운영 함수 `features.window_median_angle_deltas` 를 DTW 정렬 path 전 창에 호출해 재면:

```
kip-up  correct : 전 창·전 8관절 최대 |Δ| = 19.3도 → tol 20 초과 0개 → 100점 보장
kip-up  fault   : 최대 130.5도                     → tol 초과 7개   → 포화 감점
pdshape         : correct·fault 양쪽 8/8 초과(129.6 / 141.1) → 둘 다 캡 바닥 = 무분리
```

→ **§14-5 표는 "이 축 단독"의 하한이지 운영 mode1 점수가 아니다.**
그 분기를 켜면 kip-up 은 갈리고 pdshape 은 무분리로 바뀐다.
`[미확인]` 운영이 실제로 고르는 창은 `vision_fault_context.selected_frame_pairs[0]`(Gemini 산출)
이고 그것이 DTW path 위의 쌍이라는 보장을 **코드로 못 이었다.**

---

### 14-7. `[확인]` §11-1 의 매칭 85.9% 재검 — 97.8% 다

운영 `motion_dtw` 로 875 × 11 = 9,625회:

```
집계 단위                       정확도      (우연: 균등 9.1% · 최빈 찍기 24.6%)
분석 단위 (875)                 97.8%
videoKey 중복제거 (105쌍)       96.2%
거리벡터 지문 군집 (71쌍)       94.4%
   → 중복이 정확도를 부풀린 게 아니다. 오히려 1.9~3.4%p 낮춘다.

label 별 : correct 100% · fault 100% (354/354) · self 100% · upload 100%
오분류 전량 = ref-climb → ref-sideway-spin, 19건 / 고유 2편. 그게 전부다.
```

§11-1 의 85.9% 는 **climb 을 5배 과대표집한 표본**의 값이다. 그리고 §11-5 가 걱정한
*"못하는 학생일수록 엉뚱한 동작에 붙는다"* 는 **일부러 낸 결함 354건에서 오분류 0건**이다.

`[미확인]` 그래도 **학생 매칭 정확도가 아니다.** 875건에 초보 학생 영상이 0편이다.

---

### 14-8. 부산물 `[확인]`

- **기준 트리밍 경로가 라이브에서 한 번도 발동하지 않는다** — `COVERAGE_FLOOR` 통과 0/856,
  기준 트리밍 0/875(학생 트리밍은 19/875). `motion_dtw` 의 nu<nr 신규 경로가 사문이다.
- **`ipsf_absolute`(leg/arm/line)는 이 코퍼스 875건에서 감점 record 0건** — 한 건도 tol 20 을 못 넘는다.
- **180도 천장 가설 기각** — 바닥과 "180도로부터의 거리"의 상관은 +0.40 뿐. 바닥 크기와 더 잘 맞는 것은
  각도 분포 폭(r +0.77)이고 그 위에 역립 비율(rho 0.891)이 있다.
- **학생 875건 전부 `anglesExtractedBy = None`** — 어느 추출 판이 그 각도를 구웠는지 doc 에 기록이 없다.

---

### 14-9. 남은 것

1. `[미확인]` **바닥의 동정.** 소거로 키포인트까지 왔지만 기전(폐색 보간의 격자 의존 /
   평활창 / 기준 각도의 추출 판)은 안 갈랐다. **GPU 필요.**
2. `[미확인]` **여유가 2.0~2.3도다.** 버전 일치 바닥의 최악값이 elbow-twist 18.00 ·
   pdshape 17.69 인데 허용오차는 20.0(kismam 차용값)이다. **학생은 정은지가 아니다** —
   다른 몸·다른 카메라·다른 테이크가 그 받침대 위에 얹히면 즉시 넘고, 넘으면
   **못해서가 아니라 남이라서** 감점된다. 이게 §13 이 걱정한 것의 옳은 형태다.
3. `[미확인]` **학생 영상 0편.** 1·2 를 아무리 재도 이건 안 닫힌다.
   실증 전에 **비-정은지 영상 몇 편**을 이 축에 태워보는 것이 다른 어떤 측정보다 값이 크다.

**측정은 여기서 멈춘다.** [[measure-again-treadmill-stop-at-three]] — 이 축을 세 번째 재고 있고,
남은 질문 셋 중 둘은 오프라인으로 닫히지 않는다.

**프로세스**: GSD 커맨드를 거치지 않고 직접 편집으로 이 절을 붙였다(§6 과 같은 형태).
측정 스크립트는 세션 scratchpad 라 휘발한다 — 재현이 필요하면 `evidence/` 로 옮길 것.

---

## 15. ★★★★ 운영이 저장한 점수를 읽었다 — **정은지 본인 영상의 12.8%가 100점 미만이다**

§14-6 이 남긴 `[미확인]`("내 재구성은 이 축 단독 하한이지 운영 점수가 아니다")을 닫으려고
**운영이 실제로 저장한 `result.deductionBreakdown`** 을 읽었다. 재구성이 아니라 운영 산출물이다.
읽기 전용, 172건(64 + 46 + 62). Pod 0 · GPU 0.

### 15-0. 판정

**이 축은 운영에서 무죄에 가깝다. 위양성의 주범은 다른 축이다.**
그리고 §14-5 의 재구성은 방향이 맞았다 — 운영도 정은지 본인 영상에 **감점 record 0건**을 낸다.

**그런데 항상은 아니다.** 같은 영상을 다시 돌린 358건 중 **46건(12.8%)이 100점 미만**이고
최저가 **10점**이다. 핵심 가치가 금지한 위양성(*"고수가 낮게 나오는"*)이 **저장된 운영 데이터 안에
이미 있다.**

### 15-1. `[확인]` 운영에서 실제로 감점을 내는 것은 이 축이 맞다

`deductionBreakdown.records` 표본(동작×라벨당 최신 4건):

```
ref-pdshape     / fault : angle_vs_reference__left_elbow=28.7(-10.5) · right_elbow=27.3(-8.8)
                          · left_shoulder=25.7(-6.9) ...                       → 67점
ref-peter-pan   / fault : angle_vs_reference__left_shoulder=36.7(-20.0)        → 80점
ref-elbow-twist / fault : right_elbow=24.5(-5.4) · right_shoulder=23.1(-3.7) ... → 82점
ref-climb       / fault : right_knee=26.5(-7.8)                                 → 92점
ref-power-spin  / fault : leg_extension=60.8(-20.0) · left_shoulder=31.9(-14.3) → 66점
ref-kip-up      / fault : split_angle=20.0(-20.0)                               → 80점
                          (같은 영상의 다른 분석은 record 0건 → 100점)

정은지 본인 영상(correct/self) : 대부분 **감점 record 0건 → 100점**
```

→ **§14-5 의 재구성은 방향이 맞았다.** 그리고 §14-6 이 걱정한 window 분기는 kip-up 을
`angle_vs_reference` 가 아니라 **`split_angle`** 로 가른다 — 그마저 같은 영상에서
**100점과 80점을 오간다**(fault 75건 중 33.3%가 100점).

### 15-2. ★ `[확인]` 위양성 — 정은지 본인 영상 358건 전수

```
동작                      n    중앙   <100 비율   최저
ref-climb                 4     82     50.0%      60
ref-power-spin           62    100     33.9%      72
ref-combo                 4    100     25.0%      90
ref-peter-pan            60    100      8.3%      10
ref-kip-up               62    100      8.1%      50
ref-pdshape             100    100      8.0%      10
ref-elbow-twist-sister   54    100      7.4%      50
ref-foxtop / -split / invert / sideway-spin   각 3건 전부 100
                                     전체 46/358 = 12.8%
```

**같은 영상이다.** pdshape correct 97건 중 89건이 100점이고 8건이 미만이다.
즉 이 흔들림은 실력도 촬영도 아니고 **실행마다 달라지는 것**이다.

### 15-3. ★ `[확인]` 무엇이 깎았나 — 시점순 전량

```
2026-06-27  pdshape         10점   leg_extension = 67.7  (-90.0)
2026-06-27  peter-pan       10점   leg_extension = 71.6  (-90.0)
2026-06-27  pdshape         24점   leg_extension = 96.2  (-76.5)
2026-06-27  peter-pan       47점   leg_extension = 115.8 (-53.0)
2026-06-27  elbow-twist     62점   leg_extension = 128.3 (-38.0)
2026-07-02  power-spin      74점   angle_vs_reference__left_hip 27.5(-9.0) · right_hip 34.4(-17.2)
2026-07-02  peter-pan       85점   left_shoulder 27.8(-9.4) · right_elbow 24.9(-5.9)
2026-07-02  elbow-twist     86점   right_shoulder 31.7(-14.1)
2026-07-02  pdshape         92점   right_knee 26.5(-7.9)
2026-07-08  power-spin      80점   leg_extension = 99.3  (-20.0)
2026-07-22  pdshape         99점   left_knee 21.2(-1.4)
2026-08-16  climb           60점   left_elbow 60.7(-20.0) · right_shoulder 23.2(-3.8) · split_angle 65.0(-20.0)
2026-08-31  power-spin      80점   leg_extension = 135.8 (-20.0)
```

★ **재앙급 4건(10·10·24·47점)은 전부 `leg_extension` 이고 전부 2026-06-27 이다.**
`leg_extension` 은 ipsf_absolute 축("다리는 180도로 펴져야 한다")이고,
pdshape·peter-pan 은 **belle 가 2026-06-27 에 무릎 EXTEND 를 명시적으로 제거한** 동작이다
(§10-1, `ref-pdshape.yaml:6-8`). 그 뒤로 그 형태는 **재발하지 않았다** `[확인]`.

`[미확인]` **그 EXTEND 가 어디서 왔는지는 못 닫았다.** 후보는 §9-1 의 FallbackRecognizer
(Gemini 실패 시 ≥150도 관절을 EXTEND 로 채운다)와 §8 의 캐시 상속이다. 그 분석들의
`dimensionScores` 에 `line` 키가 있어 profile 에 EXTEND 관절이 있었던 것은 확실하지만,
**분석 doc 은 `techniqueProfile` 을 저장하지 않는다** — 그래서 로컬로는 못 닫는다.
`geminiB`/`geminiC` 의 fallback 플래그는 100점 군과 차이가 없었다(46/46 vs 34/35 동일).

★ **그러나 위양성이 끝난 것은 아니다** `[확인]`:
```
2026-06 : 21.6% (n=134, 최저 10)
2026-07 :  5.4% (n=204, 최저 74)
2026-08 : 20.0% (n= 10, 최저 60)
2026-09 :  0.0% (n=  2)          ← 표본이 2건이라 닫혔다고 말할 수 없다
```
2026-08-31 에도 power-spin 이 `leg_extension=135.8(-20)` 으로 80점을 받았다.

★ **그리고 2026-08-16 climb 60점은 이 축이다** — `angle_vs_reference__left_elbow = 60.7도`.
그 동작의 자기비교 바닥이 7.3도인데 **60.7도**가 나왔다. 바닥의 8배다.
즉 **드문 큰 포즈 실패**가 median 집계를 뚫고 점수까지 닿는다. 바닥만 위험한 게 아니다.

### 15-4. `[확인]` 관측 가능성 구멍 — 왜 그 점수가 나왔는지 사후에 못 묻는다

분석 doc 에 `techniqueProfile` 이 없다. `leg_extension` 이 −90점을 냈는데 **어느 관절에
무슨 기대가 걸려 있었는지** doc 만으로는 복원 불가다. `recognizedMotionId` 는
`result.comparison` 에 있지만 그 4건은 전부 `None` 이다.
→ 이 축을 파일럿에 내보낼 거라면 **profile 을 doc 에 박는 것**이 선행돼야 한다.
같은 종류의 구멍을 §8 에서도 봤다(캐시가 자기 입력을 키에 안 담던 것).

### 15-5. 이게 belle 판정에 주는 것

- `[확인]` **이 축(reference_relative)은 운영 위양성의 주범이 아니다.** 재앙급 4건은
  `leg_extension`(ipsf_absolute)이고 belle 의 06-27 yaml 결정 이전 건이다.
- `[확인]` **그래도 이 축도 한 번 찍혔다** — 2026-08-16 climb, 바닥의 8배인 60.7도.
- `[확인]` **같은 영상이 실행마다 10점~100점을 오간다.** 파일럿에서 수강생이 같은 영상을
  두 번 올리면 다른 점수를 받을 수 있다.
- `[미확인]` **지금도 그런지는 표본이 2건이라 말할 수 없다.** 09-17 rot180 이후 분석이
  4건뿐이다. 이걸 닫는 가장 싼 길은 **Pod 을 한 번 띄워 같은 영상 10회 재분석**이다 —
  belle 판정이 필요하다(돈).
