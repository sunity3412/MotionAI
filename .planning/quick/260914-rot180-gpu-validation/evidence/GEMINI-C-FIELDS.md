# belle C2 답 — `camera_angle_problematic` / `occlusion_severe` / `grip_visible`

belle 09-13 질문: *"나머지 두개는 모르겠네 왜 파이프라인에만 있었는지"*
09-13 인계서 관측: *"승인 픽스처 4개 전부 각도문제=False, 심한가림=False. 표본 4개라 단정 금지."*

**표본을 4개에서 전수로 올려 쟀다. belle 가설이 맞았고, 표본 문제가 아니었다.**

---

## 1. 판정

**세 필드 중 둘은 4개월간 단 한 번도 True 가 된 적이 없다.**
앱 계약에 안 열려 있는 것이 문제가 아니라, **열어도 보여줄 정보가 없다.**

Firestore `users/*/analyses/*` 전수 스캔 (2026-09-14 직접 실행, 읽기 전용):

```
분석 doc 총 1242건 · geminiC 있는 doc 941건
  camera_angle_problematic   True 0    / False 941      ← 0.0%
  occlusion_severe           True 0    / False 941      ← 0.0%
  grip_visible               True 922  / False 19       ← 반대로 축퇴
  backbend_present (대조군)   True 333  / False 608      ← 35.4%, 살아 있다
  error: None 922 / api_or_schema_fail 19
```

- `grip_visible` 의 False 19건 = **정확히** Gemini 호출이 실패한 19건.
  실패 시 `_empty_flag_dict`(`scene_finder.py:124-127`)가 네 플래그를 전부 False 로
  **지어낸다**. 즉 진짜 응답 922건에서는 `grip_visible` 이 100% True.
- **대조군이 결정적이다.** `backbend_present` 는 **같은 호출·같은 스키마**로
  333/922 True 를 낸다. 배선·스키마·모델은 멀쩡하다. 죽은 것은 이 두 필드다.
- 기간 2026-06-12 ~ 2026-09-14, uid 156개, 모델 3판(gemini-3.5/3.7/3.8-flash)
  **전 버전에서 0 True.**
- ★ **Gemini 자기 메모(`notes_ko`)가 역립/인버트/거꾸로를 언급한 213건에서조차
  `occlusion_severe` True 0건.**

## 2. 왜 이런가 — 판정 규칙이 아예 없다

셋 다 **Gemini 응답 원문 그대로**다. 임계값도 휴리스틱도 파생식도 없다.

```
scene_finder.py:137  find_scene_flags(...)
scene_finder.py:197  return parsed.model_dump()     ← Pydantic FindingFlags 그대로 통과
scene_finder.py:67-84 _FINDING_PROMPT               ← 유일한 '규칙' = 프롬프트 안 한국어 산문
```

호출은 **정상 경로·기본 ON** 이다 — `GEMINI_FINDING_ENABLED` 기본값 `"1"`
(`app.py:279`), `start_server.sh` 에서 덮어쓰지 않음. 모델은 `gemini-3.8-flash`
(`gemini/config.py:28` DEFAULT_C_MODEL).

즉 **모델이 이 두 질문에 한 번도 "예"라고 답한 적이 없다.** 코드 결함이 아니라
프롬프트/판정 기준의 문제다.

## 3. 왜 4개월간 아무도 몰랐나

이걸 잡으라고 만든 교정셋이 **미완성인 채로 방치돼 있었다**:

- `backend/evals/phase17/dataset/reference_dataset.yaml:202-260` —
  `occlusion_severe: true` 기대 시나리오 4개, `camera_angle_problematic: true` 3개 정의됨
- 그런데 **모든 `video_s3_key` 가 `TODO_finding_*.mp4` 플레이스홀더**,
  C 영역 라벨 전부 `label_status: "TODO"`
- 혼동행렬 산출물 **리포 어디에도 없음**

**상수를 뱉는 분류기를 검증한 적이 없으니 상수인 줄도 몰랐다.**

## 4. 계약 3벌 상태 (belle 질문의 표면)

| 위치 | 상태 |
|---|---|
| Firestore doc | `geminiC` 최상위에 **쓰이고 있다** (`firestore_admin.py:1346`) |
| `app/src/types/analysis.ts` | **없다** — `geminiCalls?: number`(호출 횟수)뿐. 세 이름 grep 0건 |
| `models.py` | **없다** — 타입은 `gemini/schemas.py` 의 `FindingFlags` 에만 있고 정본 3벌에 안 들어옴 |
| `docs/contract.md` | `geminiC` grep 0건 |

앱 `normalize()` 가 허용목록으로 최상위 `geminiC` 를 버리므로 **렌더 위험은 0**
(열어도 안 깨진다). 다만 키가 snake_case 라 나머지 camelCase 계약과 다르다.

**백엔드 소비처**(합성 오클루전 마스크 · wave-2 키포인트 게이트 · 코치 프롬프트 힌트)는
`occlusion_severe` 에 걸려 있는데 값이 항상 False 라 **사실상 사문**이다.

> 지금 세 필드를 전부 False 로 하드코딩해도 **깨지는 것이 없다.**
> 점수·감점·확대카드·화면·로그 분기 어디에도 영향이 없다.
> 살아 있는 소비처가 있는 geminiC 플래그는 `backbend_present` 하나뿐이다(코치 프롬프트 힌트).

## 5. 그래서 뭘 할 것인가 — belle 판단 필요

계약을 여는 것은 **순서가 틀렸다**. 먼저 신호를 살려야 한다.

1. **재는 것이 먼저다.** `reference_dataset.yaml` 의 C 영역 TODO 7건에 실제 영상과
   라벨을 붙여 혼동행렬을 내야 한다. 그래야 "모델이 못 맞히는가 / 프롬프트가 못 묻는가"가
   갈린다.
2. 팔이 폴에 완전히 붕괴한 영상조차 `occlusion_severe=False` 라면 **프롬프트의 기준이
   현장 기준과 다르다**는 쪽이 유력하다 (미검증 추정).
3. `grip_visible` 은 반대로 **항상 True** 라 정보량이 0이다. 같은 문제의 다른 얼굴.
4. 계약 3벌 확장은 신호가 실제로 흔들리는 걸 확인한 **뒤에** 한다. 그 전에 열면
   사용자에게 상수를 보여주는 것이다.

---

근거: 2026-09-14 Firestore 전수 스캔(읽기 전용) + 코드 판독. 스캔은 오케스트레이터가
직접 재실행해 수치를 확인했다(941/1242 — 오늘 런3 반영분 포함).
