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

## 2. 왜 이런가 — 프롬프트 정의의 비대칭

셋 다 **Gemini 응답 원문 그대로**다. 파생식도 임계 계산도 없다
(`scene_finder.py:197` 이 `parsed.model_dump()` 를 그대로 통과시킨다).
유일한 후처리는 **G4 기준영상 가드레일**(`scene_finder.py:204-219`) 하나인데,
`is_reference AND occlusion_severe` 일 때 전 플래그를 False 로 덮는다 —
**941건 중 0건 발동**(`guardrail_triggered` 전부 None)이라 원인이 아니다.

호출은 **정상 경로·기본 ON** 이다 — `GEMINI_FINDING_ENABLED` 기본값 `"1"`
(`app.py:279`), `start_server.sh` 에서 덮어쓰지 않음. 모델 `gemini-3.8-flash`,
`temperature=0.0`, `max_output_tokens=512`, **`thinking_budget=0`**
(`scene_finder.py:97-99` — Flash 의 thinking 을 끈 상태다).

### ★ 프롬프트 정의를 나란히 놓으면 패턴이 보인다 (`scene_finder.py:73-80`)

| flag | 정의가 요구하는 것 | 실측 |
|---|---|---|
| `grip_visible` | "식별 가능한 시점이 **1회 이상** 존재하면" — 클립 전체에 대한 **존재 한정** | True **100%** |
| `backbend_present` | "**30도 이상** 후굴이 **1초 이상** 유지" — 임계+지속, 그러나 **이름 붙은 자세** | True **35.4%** ✅ |
| `occlusion_severe` | "**신체의 50% 이상**이 가려진 상태가 **1초 이상** 지속" — **면적 정량 판단** | True **0%** |
| `camera_angle_problematic` | "좌/우 구분이 **불가능**한 각도" — **불가능성 단언** | True **0%** |

- `grip_visible` 은 "한 번이라도 보이면 참"이라 **거의 항상 참**이 된다. 정보량 0.
- `backbend_present` 는 같은 "임계+지속" 형식인데 **살아 있다.** 차이는 판단 대상이
  *알아볼 수 있는 자세*(등 후굴)라는 점이다.
- 죽은 둘은 모델에게 **"몸 면적의 50%"를 재라**거나 **"불가능하다"고 단언하라**고
  요구한다. thinking 을 끈 Flash 가 temperature 0 에서 이런 걸 긍정하기는 어렵다.

**미검증 추정**: 코드 결함이 아니라 **정의가 관측 불가능한 형태로 쓰여 있는 것**이
원인이다. 확정하려면 §5 의 혼동행렬이 필요하다.

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
| `app/src/types/analysis.ts` | **없다** — 세 이름 grep 0건. Gemini 관련 필드는 `geminiCalls?: number`(:351, 합성 비용 카운터)와 `geminiSilent: boolean`(:943, attribution 신뢰도 — 앱이 실제로 파싱한다 `userAnalyses.ts:359,364`) 둘뿐이고 **둘 다 이 세 필드와 무관하다** |
| `models.py` | **없다** — 타입은 `gemini/schemas.py` 의 `FindingFlags` 에만 있고 정본 3벌에 안 들어옴 |
| `docs/contract.md` | `geminiC` grep 0건 |

앱 `normalize()` 가 허용목록으로 최상위 `geminiC` 를 버리므로 **렌더 위험은 0**
(열어도 안 깨진다). 다만 키가 snake_case 라 나머지 camelCase 계약과 다르다.

**백엔드 소비처는 배선돼 있다** — `scene_result` 는 코치 컨텍스트로 들어가고
(`app.py:8219` → `sceneFlags` → `coach_writer_v2.py:484,494` → 프롬프트) 합성
오클루전 마스크·wave-2 키포인트 게이트에도 걸려 있다. **호출되지 않는 게 아니라,
값이 항상 False 라 그 분기들이 한 번도 참이 된 적이 없다.**

> 세 필드를 지금 False 로 하드코딩해도 **사용자가 보는 것은 하나도 안 바뀐다** —
> 이미 상수 False 이기 때문이다. 다만 "소비처가 없다"는 서술은 틀렸다:
> 소비처는 있고, 죽어 있는 것은 **신호**다.

## 5. 그래서 뭘 할 것인가 — belle 판단 필요

계약을 여는 것은 **순서가 틀렸다**. 먼저 신호를 살려야 한다.

1. **정의를 관측 가능한 형태로 다시 쓴다** (가장 싸고 가장 유력하다).
   "신체의 50% 이상" 같은 면적 정량 대신 `backbend_present` 가 통하는 방식 —
   **알아볼 수 있는 장면**으로. 예: "폴 뒤로 몸통이 지나가 **한쪽 팔 전체가 안 보이는**
   구간이 있는가", "좌/우 구분 불가" 대신 "**정면/측면/뒤** 중 무엇인가"(bool 말고 분류).
   `thinking_budget=0` 을 올려볼 가치도 있다(`scene_finder.py:99`).
2. **그 다음에 잰다.** `reference_dataset.yaml:202-260` 의 C 영역 TODO 7건에 실제
   영상·라벨을 붙여 혼동행렬을 내야 "모델이 못 맞히는가 / 정의가 못 묻는가"가 갈린다.
   지금은 어느 쪽인지 **모른다**.
3. `grip_visible` 은 반대 방향으로 축퇴했다(항상 True). "1회 이상 존재하면 참"이라는
   존재 한정을 고치지 않으면 정보량은 계속 0이다.
4. **계약 3벌 확장은 맨 마지막.** 신호가 실제로 흔들리는 걸 확인하기 전에 열면
   사용자에게 상수를 보여주는 것이다.

---

근거: 2026-09-14 Firestore 전수 스캔(읽기 전용) + 코드 판독. 스캔은 오케스트레이터가
직접 재실행해 수치를 확인했다(941/1242 — 오늘 런3 반영분 포함).
