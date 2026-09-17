---
title: 인수인계서 — 2026-09-17 세션
date: 2026-09-17
next_section: ★ 내일 첫 일 = Omni 영상 합성 spike (belle 승인 "1~2편만")
status: 회전 묶음 배포 완료 · 앱 E2E 60→87 · 강사 교정 v2 개시 · 재학습 게이트 수리
---

# 인수인계서 — 2026-09-17

**§0 → §2 를 먼저 읽어라.** §2 가 내일 첫 일이다.
★ 오늘 **내가 틀렸다가 고친 것 4건**은 §6 에 모아뒀다.

---

## 0. 30초 요약

- ★ **회전 묶음을 배포했다.** 기준 11편 `rot180_v1` 승격 + 엔진 플래그 ON.
  **belle 영상 60점 → 87점 · 정은지 자기비교 60점 → 100점.**
  PROJECT.md 핵심 우려("정은지 41점 위양성") 해소.
- ★ **앱 전 경로 E2E 로 확인했다** — 채점 코드 직접 호출이 아니라 앱→Lambda→Pod 실경로.
  로컬 예측 87 을 실제 파이프라인이 그대로 냈다.
- **전수 측정이 09-14 서술 2건을 정정했다** — 기준 라이브러리는 낡지 않았고,
  "허용오차 2.6배"는 pdshape 1편의 성질이었다.
- **강사 교정 수집 v2 개시** — 결과 화면에서 받는다. 시뮬 왕복 확인. **OTA 미발행**.
- **재학습 승격 게이트 수리** — 승격이 구조적으로 불가하던 것을 풀었다.
  정책이 아니라 구현이 자기 독트린을 어긴 것이었다.
- 게이트 **4831 passed / 0 failed** · HEAD `222e9c87` · Pod 0대 · RunPod **$2.79**

---

## 1. 지금 상태 (실측)

```
브랜치   main   HEAD 222e9c87   (origin/main 보다 앞섬 — 미푸시)
게이트   pytest 4831 passed / 20 skipped / 0 failed   (기준선 4827 + 신규 4)
앱       tsc CLEAN · node --test 268 passed / 0 failed
회전     ROT180_INVERSION_ENABLED=1        ← 켜져 있다 (start_server.sh:24)
기준     reference/_release.activeCandidate = rot180_v1   (11/11 verify PASS)
Pod      0대 · SSM pod-expected=down · RunPod 잔액 $2.79 (오늘 $1.19 씀)
Lambda   RUNPOD_ANALYZE_URL = 죽은 주소 (E2E 후 Pod 종료 — 종전과 같은 상태)
Firestore Blaze
```

★ **롤백은 반드시 한 묶음이다** — 포인터(`_release.activeCandidate`)와
플래그(`start_server.sh:24`) **둘 다**. 한쪽만 되돌리면 학생·기준 중 한쪽만 교정된
비대칭 비교가 되어 **승격 전보다 나빠진다**(실측: 회전만 켜면 원감점 −55.3 → −62.4).
top-level 원본은 `reference/{id}/versions/pre_phase4` 에 11/11 백업돼 있다.

---

## 2. ★ 내일 첫 일 — Omni 영상 합성 spike

**belle 승인(2026-09-17): "1~2편만 해봐"** ($17.50~35).

### 2-1. 무엇을 위한 것인가

belle 2026-06-10 박제: 촬영 UX 는 **"스마트폰 한 대, 한 자리, 한 번"** 이고
사용자에게 다각도 촬영을 요구하는 것은 **영구 금지**다. 가림·측면·회전 동작에서
관절을 못 보는 문제는 **AI 가상 카메라 앵글 합성**으로 푼다
([[camera-angle-ai-single-view-synth]]). Omni 가 그 물건이다.

### 2-2. 착수 전에 반드시 읽을 것 — 두 번 밟은 함정

메모리 `gemini-omni-1-1-flash-released-interactions-api` 가 답을 적어뒀는데도
09-05 세션이 `generateContent` 만 5가지로 두드리고 "못 쓴다"고 보고했다.
belle 이 모델 카드를 다시 들이밀어서야 엔드포인트를 바꿨다.

```
v1beta/models/gemini-omni-1.1-flash:generateContent → HTTP 400
    "This model only supports Interactions API."
v1beta/interactions  {model, input}                 → 동작 (status: completed)
```

★ `ListModels` 는 `supportedGenerationMethods: [generateContent, countTokens]` 라고
**광고하지만 실제 호출은 거부한다.** 메타데이터를 믿지 말 것.

### 2-3. 지금 어디까지 돼 있나 (실측, 2026-09-17)

`video_gen_adapter.py:6-12` 의 활성 조건 4개 — **코드에 그대로 살아 있다**:

| # | 조건 | 상태 |
|---|---|---|
| 1 | `SYNTHESIS_VIDEO_GEN_ENABLED=1` | **미설정** (리포에 설정처 0) |
| 2 | endpoint 명세 확정 | **부분** — Interactions 도달은 실증, **영상 IO shape 미확인** |
| 3 | 10-video pose consistency 게이트 | **미착수** |
| 4 | belle 비용 sign-off | **오늘 받음** (1~2편 한정) |

★ **어댑터 주석이 낡았다** — `video_gen_adapter.py:3` 이 아직
*"Omni Vertex endpoint 공식 등록 미완 (mid-to-late June 2026 윈도우)"* 라고 적어뒀다.
그 차단은 **2026-08-28 에 해소**됐다. spike 하면서 이 줄부터 고칠 것.

### 2-4. ★ 내일 바로 막힐 지점

**리포에 Interactions API probe 스크립트가 없다.** 08-28·09-05 실증은 **즉석 호출**이라
자산으로 안 남았다(`grep -rl "v1beta/interactions" backend` → `gemini/config.py` 주석뿐).
→ **첫 30분은 probe 를 스크립트로 박는 데 쓸 것.** 그래야 세 번째로 같은 함정을 안 밟는다.

### 2-5. spike 가 대답해야 할 것 (미측정 — 전부)

메모리 원문: *"영상 생성은 **실제로 안 돌려봤다**(유료라 텍스트 probe 만 했다).
품질·실제 단가·RTMW 재추론 정확도는 전부 미측정."*

1. **영상이 실제로 나오나** — Interactions API 로 영상 출력까지 (IO shape 확정)
2. **실제 단가** — 카드 표시가는 Video output $17.50 인데 **실측 청구액**을 볼 것
3. ★ **RTMW 가 합성 영상에서 일관된 pose 를 뽑나** — 이게 핵심이다.
   앵글이 예뻐도 관절을 못 뽑으면 **우리에겐 쓸모가 없다**. 조건 3번의 실체다.
4. 입력은 **오늘 회전 묶음으로 좌표가 좋아진 영상**을 쓸 것 — 기준선이 달라졌다.

### 2-6. 비용 규율

belle 승인은 **1~2편**이다. 3편째부터는 다시 물을 것.
$17.50 은 RunPod 한 달치보다 크다(현재 잔액 $2.79).

---

## 3. 오늘 한 일 — 근거 위치

| 커밋 | 내용 |
|---|---|
| `35cd652d` | 기준 11편 회전 드리프트 **전수 측정** — 09-14 서술 2건 정정 |
| `564efbb5` | 묶음 적용 시 점수 실측 (수강생 60→86~88, 자기비교 60→100) |
| `ec9c9ef4` | candidate 스테이징 + **Firestore 1MB 중복 저장 결함 수리** |
| `02b1155a` | **묶음 승격** — rot180_v1 active + 회전 플래그 ON |
| `acfd1ed7` | **앱 전 경로 E2E** — 60 → 87 실경로 확인 |
| `c177488f` | **강사 교정 수집 v2 개시** (앱) |
| `222e9c87` | **재학습 승격 게이트 수리** |

근거 전문:
- `.planning/quick/260917-hjy-reference-drift-all11/evidence/`
  — `REFERENCE-DRIFT-ALL11.md` · `SCORE-IF-BUNDLED.md` · `BUNDLE-STAGED.md`
  · `E2E-REAL-PATH.md` · `e2e/` (확대카드 4장 + 서버 로그 + doc 요약)
- `.planning/quick/260918-0q8-coach-review/` — 강사 교정 (시뮬 스크린샷 3장)
- `.planning/quick/260918-gate-semantics/SUMMARY.md` — 게이트 수리

---

## 4. belle 판정 대기 — 2건

| # | 판정 | 상태 |
|---|---|---|
| **1** | **확대 카드 `zoom_adv_left_shoulder` 원 위치** | **눈 판정 필요** ↓ |
| **2** | 강사 교정 OTA 발행 | 실기기 확인 후 |

### 4-1. 확대 카드 — 게이트가 판독 실패를 통과시킨다

E2E 산출 카드 2장 중 하나는 **확실히 좋아졌다**(`zoom_angle_vs_reference__left_elbow`
— 두 패널이 같은 역립 자세, 표식이 양쪽 다 실제 팔꿈치, 감점 사유가 그림으로 읽힘).

다른 하나(`zoom_adv_left_shoulder`)는 **한쪽에만 동그라미**다. 게이트 로그:

```
side=user  action=pass       trail=unclear/unreadable   ← 눈이 "못 읽겠다"인데 통과
side=ref   action=suppressed trail=head/mismatch
요약: sides=4 eye_calls=9 pass=3 suppressed=1 unbound=0
```

**게이트가 fail-open 이다.** 원 위치가 틀렸다고는 **단정하지 않았다** — 처음엔
화분 위로 보였으나 `__plain` 원본과 대조하니 등/견갑 쪽일 수 있고, 게이트 허용 부위
목록에 `back_waist` 가 있다. 좁은 크롭에선 좌표 오류와 크롭 폭을 못 가른다
([[tight-crop-cannot-separate-coord-from-crop]]).

사진 = `.planning/quick/260917-hjy-reference-drift-all11/evidence/e2e/`

---

## 5. 내가 먼저 할 것 (판정 불필요)

- **Omni spike** (§2) ← 내일 첫 일
- `video_gen_adapter.py:3` 낡은 차단 사유 주석 정정
- `.planning/TRAINING-DUE.md` 기준선 정정 — "직전 판 v29" 는 낡았다.
  실제 직전은 **v38**(2026-08-28)이고 v28/v29/v35/v36/v38 **전부 promoted=false**.
  **승격 이력 0건**이다.
- 09-14 인계서 §6 잔여: 가시성 조항 배선 설계 · 코드 출처 태그 정정 2건

---

## 6. ★ 오늘 내가 틀렸다가 고친 것 4건 — 같은 함정 반복 금지

1. **"저장 angles 와 joints3d 가 불일치한다" — 유령 결함이었다**
   11편 전부 어긋나길래 결함인 줄 알았는데, **갭필 + 5프레임 스무딩을 걸면 전부
   0.00 으로 닫힌다**(`temporal_fill` 단계 차이, 불확실도 채널 미저장).
   → **보고 직전에 한 번 더 재서 살았다.**

2. **"뼈위반으로 각도 드리프트를 예측한다" — 교정에서 떨어졌다**
   pdshape 정답에 맞춰보니 뼈위반 **최대** 관절의 드리프트가 8.7°(최소),
   **최소** 관절이 43.2°(최대)였다. → **새 계기는 정답 있는 표본에 먼저 교정하라.**

3. **"S3 다운로드가 멈췄다" — 느린 것이었다**
   임시파일이 12분째 0바이트라 멈춘 줄 알았는데, boto3 는 **별도 임시파일**
   (`*.mp4.<suffix>`)에 받는다. 89MB / EU↔서울 교차 리전 = 752초.
   → **0바이트를 보고 단정하지 말 것.**

4. **"advisory 카드 원이 화분 위에 있다" — 성급했다**
   표시 없는 `__plain` 원본과 대조하니 등/견갑일 수 있었다. 판정을 철회하고
   belle 눈 판정으로 넘겼다. → **좁은 크롭에서 위치를 단정하지 말 것.**

---

## 7. 함정 (밟으면 시간을 태운다)

1. ★ **Omni 는 `generateContent` 가 아니라 `v1beta/interactions` 다.**
   두 세션이 이걸로 시간을 태웠다. probe 스크립트부터 만들 것(§2-4).
2. ★ **기준 doc 이 Firestore 1MB 한도에 닿아 있다** — 라이브 `ref-combo` 1013KB(99%).
   콤보보다 긴 기준 모션을 넣으면 다시 걸린다. 오늘은 같은 보고서 중복 저장을
   지워서 통과시켰다([[reference-doc-hits-firestore-1mb-limit]]).
3. ★ **승격(flip)이 터지면 부분 상태가 생긴다** — doc 단위 루프다.
   오늘 실제로 ref-climb 한 편만 미러된 상태가 생겼다(포인터는 루프 뒤라 해석 경로는
   불변). **터지면 반드시 실물로 어디까지 갔는지 확인할 것.**
4. **분석 시간의 2/3 이 S3 다운로드다** (89MB 752초). 시연 때 "왜 이렇게 느리지"
   하게 될 지점이다. Pod 이 유럽이고 버킷이 서울이라 그렇다.
5. **Pod 은 분석 완료 후 3~5분 더 돌려라** — 확대카드·음성이 그때 만들어진다.
   (09-14 에 이걸로 "회전이 렌더를 깬다"고 오진했다. 오늘은 기다려서 정상 확인.)
6. **`--motions` 기본값이 5개로 낡았다** (`extract_reference_angles.py`).
   기준 작업은 11개를 명시할 것.
7. **Pod `git pull` 이 실패할 수 있다**(`bad object refs/heads/local-0903b`).
   추출·분석 경로가 안 바뀌었으면 pull 없이 진행해도 된다 — `git diff --name-only`
   로 먼저 확인하면 10분을 아낀다.
8. **시뮬 키보드가 한글 IME 라 ASCII 입력이 자모로 들어간다.** 입력 모드 문제이지
   버그가 아니다.
9. 09-14 인계서 §8 함정 1~9 는 그대로 유효하다.

---

## 8. 오늘 배포한 것의 성질 — 다음 세션이 알아야 할 것

**회전은 11편 중 6편만 바꾼다.** 5편(climb·kip-up·peter-pan·power-spin·sideway-spin)은
전 프레임·전 관절 차이가 **0.000000** 이다. 20° 초과 9/88 중 **5개가 pdshape 하나**다.

그래서 **pdshape 이외 동작의 점수 변화는 아직 안 쟀다** — E2E 도 pdshape 1편이다.
특히 **kip-up 은 위양성 재발 이력**이 있다([[kipup-fp-RESOLVED-phase24A]] 는
08-31 에 재발 관측됐다 — RESOLVED 를 믿지 말 것). 회전이 kip-up 을 안 건드리긴 하지만,
기준이 재추출됐으므로 한 번은 돌려볼 가치가 있다.
