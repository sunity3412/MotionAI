---
id: 260919-mhl
title: 확대 비교 카드 짝 품질 — 시간 정렬 이탈 방출 (관측 전용)
date: 2026-09-19
status: planned
---

# 확대 비교 카드의 짝 품질을 시간 정렬 이탈로 방출한다

**이번 단위는 계기 하나를 다는 일이다.** 게이트를 바꾸지 않고, 점수에 닿지 않고,
카드 장수·사진·기존 필드를 그대로 둔 채 **카드마다 관측값 2개**
(`pairDeviationSec` + 그 값을 만든 `pairDeviationTier`)를 doc 에 싣는다.

## 왜 (belle 2026-09-19 판정)

현행 짝 품질 지표는 **자세 거리**(`card_gates.PAIR_POSE_MAX = 0.85`)다. belle 이 이 설계를
무너뜨렸다 — 카드의 존재 이유가 "자세가 다르다"를 보여주는 것이라, 자세로 짝을 재면
**"같은 순간인데 자세가 다르다"(정상)** 와 **"다른 순간이라 자세가 다르다"(결함)** 를
원리적으로 구분할 수 없다. 감점이 클수록 지표가 커진다.

대체 지표 = **시간 정렬 이탈**. belle 눈 4/4 순서 일치로 검증됐다(인계서 §6):

| 카드 | 이탈 | belle 판정 |
|---|---|---|
| 팔꿈치 8.1초 | −4.28초 | 확실히 다르다 |
| 오른무릎 5.7초 | +0.67초 | 살짝 비슷한데 같진 않음 |
| 왼골반 16.7초 | −0.13초 | 거의 같은 순간 · 구간 확실 |
| 오른어깨 3.4초 | −0.20초 | 거의 같은 순간 · 구간 확실 |

belle 기준은 **"동작의 구간(phase)이 같은가"** 이고, 회전량 차이는 구간을 안 바꾼다.
그래서 회전을 벌점으로 세는 자세 지표가 틀렸다.

**지금은 짝 품질을 사후에 알 방법이 아예 없다.** 그 구멍을 메우는 것이 이번 단위다.
라이브 실측이 이를 뒷받침한다 — **카드 192장 전수에서 `refMatch='failed'` 0장,
`refMatched=False` 0장**(True 163장 / 필드 도입 전 legacy 부재 29장). 인계서 §5 가
"원리적으로 발화 불가"라 한 정직 장치가 **실측으로도 한 번도 안 울렸다.** 짝이 틀려도
doc 에는 아무 흔적이 없다.

## ★ 라이브 실측이 바꾼 것 — 읽지 않고 구현하면 새 거짓 라벨을 만든다

doc 47건 / 카드 192장 실측(2026-09-19):

```
motionAlignment tier   : trim_only 35 · disabled 1 · warped 0      (36 doc)
reason                 : 전부 "low_global_confidence"
distance 실측          : 52.8 ~ 72.0   (motion_alignment.DISTANCE_T2 = 25.0 의 2~3배)
anchors                : 15~42쌍, 비선형 (예: u=12.44 → r=21.60)
```

**앵커 곡선은 풍부한데 tier 가 `trim_only` 라 `warpTime` 이 그 곡선을 통째로 버린다** —
`trim_only` 분기는 `t - us[0] + rs[0]` 뿐이고, 거의 모든 doc 에서 `us[0]=0, rs[0]=0` 이라
**warp 는 사실상 항등함수**다.

→ **즉 지금 라이브에서 이 필드의 값은 사실상 "생짜 시간차"다.** 그 값 자체는 틀리지 않다.
하지만 **"시간 정렬 이탈"이라는 이름만 붙이고 tier 를 숨기면, 우리가 지금 고치려는 결함
(`refMatched=true` 거짓 보증)과 정확히 같은 종류의 거짓 라벨을 새로 만드는 것이다.**

그래서 이번 단위의 규칙 2개:

1. **값과 tier 를 항상 함께 싣는다** (`pairDeviationSec` ⟺ `pairDeviationTier`,
   both-or-neither). 소비처가 doc 레벨 `motionAlignment` 를 조인하지 않아도 카드 한 장만
   보고 "이 값은 항등 warp 산출이다"를 알 수 있어야 한다.
2. **tier 를 무시하고 앵커를 보간하는 구현 금지.** 계약(`alignmentWarp.ts`) 위반이고,
   파이프라인이 스스로 저신뢰(`low_global_confidence`)로 표시한 데이터를 신뢰하는 것이 된다.
   `warp_time` 은 TS 정본의 tier 분기를 **그대로** 미러한다.

> tier 사다리·`DISTANCE_T2` 임계는 **이번 단위에서 건드리지 않는다.** distance 52~72 가
> 임계의 2~3배라는 사실은 별건(정렬 품질 자체의 문제)이고 belle 판정 대기다.
> 여기서 임계를 손대면 재생 경로(`VideoCompare` warp)의 거동이 바뀐다 — 관측 단위의 범위 밖.

## 이번 단위의 경계 — 넘지 말 것

한다:
- 이탈값 + tier 를 산출해 카드 dict 에 싣고, 화이트리스트 매퍼를 통과시켜 doc 까지 보낸다.
- 3-way lockstep 등재(analysis.ts / models.py / contract.md).

하지 않는다 (**전부 belle 판정 대기 또는 범위 밖**):
- 통과선(threshold) 적용, 카드 드롭/채택 판정 변경.
- `card_gates.PAIR_POSE_MAX` 제거·변경, `pair_gate`/`pairState` 동작 변경.
- `motion_alignment` 의 tier 사다리·`DISTANCE_T1/T2`·`build_motion_alignment` 본체 변경.
- `refMatched`/`refMatch` 값 변경 (인계서 §7 고칠 것 2번 — **별도 단위**).
- 앱 UI 변경. 앱은 이 두 필드를 **아직 한 줄도 읽지 않는다**.
- 채점·감점 경로 수정. **점수에 닿는 코드 무접촉.**

즉 **순수 additive 관측 필드 2개**다. 기존 카드 산출(사진·기존 키·장수)은 무변경이어야 한다.

## 어떻게 — 새 추론 0

카드 조립 시점에 필요한 재료가 **이미 메모리에 다 있다**:

- `result["motionAlignment"]` — `_attach_motion_alignment` 가 `complete_analysis` **직전**
  에 붙인다(`backend/functions/pipeline/app.py:8926`). 카드 두 경로는 전부 그 **뒤**의
  사후 스테이지다(fault_zoom stage `app.py:9052`, compare_render `app.py:9112`).
  두 경로 모두 **같은 `result` 객체**를 인자로 받는다 — 재조회 0.
- 카드에는 이미 `userVideoSec` / `refVideoSec`(실영상 초, float)이 실려 있다
  (`fault_zoom.py:4004-4013`).

이탈 = `refVideoSec` − `warpTime(alignment, userVideoSec)` (타임베이스 보정 후 — 아래 §타임베이스).

### warp 함수는 Python 에 없다 — TS 정본을 미러한다

`sunity_shared/analysis/motion_alignment.py` 에는 `build_motion_alignment` 뿐이고 warp 가 없다.
정본은 `app/src/lib/alignmentWarp.ts::warpTime`(49~72행)이다. 로직 원문:

```
tier 'disabled'      → return tStudent (identity)
앵커 0개             → return tStudent
tier 'trim_only'     → return tStudent - us[0] + rs[0]      ← 라이브 35/36 이 여기
tier 'warped':
  t <= us[0]         → rs[0] - (us[0] - t)         (기울기 1.0 연장)
  t >= us[n-1]       → rs[n-1] + (t - us[n-1])     (기울기 1.0 연장)
  그 외              → rs[k] + (t - us[k]) * (rs[k+1]-rs[k])/(us[k+1]-us[k])
```

`anchors` 는 flat `[u0,r0,u1,r1,...]` 초 단위 float(nested-array 금지 규약).

### ★ 타임베이스 — 그냥 빼면 틀린다

**카드의 초와 anchors 의 초는 분모가 다르다.**

- 카드: `u_video_sec = u_idx / u_label_fps`, `r_video_sec = r_display_idx / r_label_fps`
  (`fault_zoom.py:3913-3914`). `*_label_fps` = **측별 실효 rate**(`probe_effective_fps`,
  예: 30fps 원본 → 10.0). 판정 불가 시 `frames_fps`(9.0) 폴백(`fault_zoom.py:3085-3092`).
- anchors: `uSec = user_frame / user_fps`, `rSec = ref_idx / ref_fps` 에서
  `user_fps = _pipeline_frame_fps()` = **라벨 9.0**(`app.py:8925-8941`).
  ref 측은 `ref_idx`(rep 18fps 공간) / `ref_fps`(18.0 라벨)인데,
  `_to_rep_idx = round(idx / frames_fps * rep_fps)`(`fault_zoom.py:373-381`)로
  `rep_idx ≈ ref9_idx × rep_fps/9.0` 이므로 **`rSec = ref9_idx / 9.0`** 로 수렴한다.
  → **양쪽 anchors 축은 공통적으로 "비디오 배열 인덱스 / 9.0(라벨 초)"** 이다.

라벨 9.0 과 실효 ~10.0 은 약 11% 어긋난다([[fps-label-vs-actual-decimation-rate]]).
변환 없이 빼면 warp 절편(트림 오프셋)의 약 10%가 그대로 오차로 남는다.

**환산 (양방향 1줄씩):**

```
anchor_fps = _pipeline_frame_fps()                     # 9.0 — anchors 분모 단일 출처, 리터럴 금지
u_anchor   = userVideoSec * (u_label_fps / anchor_fps)
r_anchor   = refVideoSec  * (r_label_fps / anchor_fps)
dev_anchor = r_anchor - warp_time(alignment, u_anchor)
pairDeviationSec = dev_anchor * (anchor_fps / r_label_fps)   # 다시 기준 패널 실초로
```

라벨 드리프트가 없으면(`label == anchor == 9.0`) 배율이 1.0 이라 `ref - warp(user)` 로
자연 축약된다 — 회귀 위험 0.

> ⚠️ **인계서 §6 표와의 차이**: §6 의 −4.28/+0.67/−0.13/−0.20 은 세션 중 임시 스크립트
> 산출이고 그 스크립트에는 이 라벨→실효 환산이 **없었다**(스크립트는 scratchpad 와 함께
> 사라졌다). 이 필드의 값은 §6 과 **약간 다를 수 있다** — 오차가 전 카드에 공통 절편으로
> 들어가므로 **순서(belle 4/4 검증)는 보존된다**. 나중에 누가 "표와 다르다"며 환산을
> 되돌리지 않도록 SUMMARY 에 이 문단을 옮겨 적을 것.

> ⚠️ 위 ref 축 수렴(`rSec = ref9_idx / 9.0`)은 코드에서 유도한 것이다. Task 1 에서
> 테스트로 박제하되, 읽어보니 **유도가 성립하지 않으면 멈추고 물을 것**(CLAUDE.md §7
> "막히면 Do not work yet"). 추측으로 채우지 말 것.

### 부호 규약

**`pairDeviationSec = 표시된 기준 초 − 정렬이 가리키는 기준 초`** (displayed − expected).

- 양수 = 기준 패널이 정렬보다 **늦은** 순간을 보여준다.
- 음수 = 기준 패널이 정렬보다 **이른** 순간을 보여준다.

절대값만 실으면 "기준이 앞서냐 뒤서냐"를 잃는다(belle 표가 부호로 방향을 담고 있었다).
판정은 나중에 `|값|` 으로 하면 된다. **규약을 contract.md 에 박아 두고 뒤집지 말 것.**

### 동반 필드 `pairDeviationTier`

`pairDeviationSec` 을 만든 alignment 의 tier 를 그대로 싣는다 —
`'warped'` | `'trim_only'`. (`disabled` 는 값 자체를 안 내므로 여기 안 나타난다.)

- **both-or-neither 불변식**: 두 키는 항상 같이 있거나 같이 없다.
- 용도: `'trim_only'` 는 **곡선을 버린 오프셋만의 warp** 이고, 라이브에서는 오프셋마저
  0 이라 사실상 생짜 시간차라는 사실을 소비처가 카드 한 장만 보고 알 수 있게 한다.
- 이 값으로 **분기·게이트·문구를 만들지 말 것** — 지금은 읽는 코드가 0건이어야 한다.

### 값이 없을 때 (fail-closed, 조용히)

아래 중 하나라도 해당하면 **두 키를 모두 생략**한다 — 0.0 이나 추정치로 채우지 않는다:

- `motionAlignment` 부재 (legacy doc / mode3 첫 분석 / 방출 실패)
- `tier == 'disabled'` (정렬 정보 없음 — identity warp 로 뺀 값은 근거가 없다. 라이브 1/36)
- `anchors` 0개
- `userVideoSec` 또는 `refVideoSec` 부재 (기준 대응 실패 카드는 `refVideoSec` 을 애초에 안 싣는다)
- 비유한(NaN/Inf) 입력, `label_fps <= 0`

필드 부재는 **정상**이다. 소비처는 아직 없다(앱 무접촉).

---

## Task 1 — 순수 계층: warp 미러 + 이탈 산출 + 테스트

**파일**
- `backend/shared/python/sunity_shared/analysis/motion_alignment.py` (추가만)
- `backend/tests/test_pair_time_deviation.py` (신규)

**작업**

1. `motion_alignment.py` 에 순수 함수 2개를 **추가**한다 (기존 `build_motion_alignment`
   본체·`DISTANCE_T1/T2`·tier 사다리 **무접촉** — additive only).

   - `warp_time(alignment: dict, t_student: float) -> float`
     `app/src/lib/alignmentWarp.ts::warpTime`(49~72행)의 **정확한 미러**.
     TS 와 같은 분기 순서·같은 식(위 §warp 블록). **tier 분기를 그대로 지킨다** —
     `trim_only` 에서 앵커 곡선을 보간하는 "개선"은 계약 위반이므로 금지.
     `anchors` flat 읽기는 TS `readPairs` 와 동형 — `anchorCount` 를 신뢰하지 말고
     `len(anchors)` 에서 직접 쌍을 도출한다(TS 주석 "단일 출처 — 방어적 소비" 그대로).

   - `pair_time_deviation_sec(alignment, *, user_video_sec, ref_video_sec, user_label_fps, ref_label_fps, anchor_fps) -> tuple[float, str] | None`
     위 §타임베이스 공식 그대로. 반환은 **(이탈초, tier) 쌍** — 값과 tier 를 분리해 낼 수
     없게 만들어 both-or-neither 를 타입으로 강제한다. §"값이 없을 때" 조건 전부 `None`.
     `anchor_fps` 는 **인자**로 받는다 — 순수 모듈에 `_pipeline_frame_fps` 를 끌어오지
     않는다(모듈 상단 "채점 경로 import 0 / 순수" 규율 승계).

   두 함수 docstring 에 **왜**를 적는다: belle 09-19 판정(자세 지표 기각 → 시간 정렬
   이탈), 부호 규약, 타임베이스 환산 근거 라인(`fault_zoom.py:3913-3914`, `app.py:8926`),
   **라이브 실측(trim_only 35 / warped 0 / distance 52.8~72.0 → 현재 warp 는 사실상 항등)**,
   `contract.md §11.12` 인용, TS 정본 경로(`app/src/lib/alignmentWarp.ts`) lockstep 명시.

2. `backend/tests/test_pair_time_deviation.py` — 의미 있는 시험만:

   - **warp 분기 4종 동치**: disabled(identity) · 앵커 0개(identity) · trim_only(오프셋) ·
     warped(범위 이전/구간 보간/범위 이후). 손으로 계산 가능한 앵커로.
   - **★ 라이브 형상 박제**: `tier='trim_only'` + `us[0]=rs[0]=0` + **비선형 앵커 곡선**
     (실측 형상: u=12.44 → r=21.60 같은 쌍 포함)에서 `warp_time` 이 **항등**이고,
     따라서 이탈이 (타임베이스 환산 후) 생짜 시간차와 같음을 단언한다.
     이 시험이 "trim_only 인데 곡선을 보간하는" 구현 변경을 즉시 깨뜨린다.
   - **TS 정본 drift 감지 (텍스트 lockstep)**: `app/src/lib/alignmentWarp.ts` 소스에
     네 식(`tStudent - us[0] + rs[0]`, `rs[0] - (us[0] - tStudent)`,
     `rs[n - 1] + (tStudent - us[n - 1])`, `(rs[k + 1] - rs[k]) / (us[k + 1] - us[k])`)이
     그대로 있는지 단언. 선례 = `backend/tests/test_motion_alignment_contract.py`
     (`_TS_WARP` 상수 + `test_rate_clamp_lockstep_alignmentwarp`).
   - **타임베이스 환산이 실제로 값을 바꾼다**: 라벨 9.0 / 실효 10.0 조합에서
     환산 없는 순진한 뺄셈과 결과가 다름을 단언하고, **정렬과 정확히 일치하는 짝**은
     환산 후 0.0 이 나오는 것을 단언(이 시험 하나가 §타임베이스 유도 전체를 박제한다).
   - **라벨 드리프트 0(9.0/9.0)이면 `ref - warp(user)` 로 축약**됨을 단언(회귀 가드).
   - **부호 방향**: 기준이 정렬보다 늦은 짝 → 양수, 이른 짝 → 음수.
   - **tier 동반 반환**: `trim_only` 입력 → 반환 tier 가 `'trim_only'`,
     `warped` 입력 → `'warped'`.
   - **None 반환**: alignment None / `disabled` / anchors 0개 / `user_video_sec` None /
     `ref_video_sec` None / `label_fps <= 0`.

**검증**
```
cd backend && .venv/bin/python -m pytest tests/test_pair_time_deviation.py -q
```
(서브에이전트 게이트 수치를 믿지 말 것 — worktree venv 함정.
[[dont-trust-subagent-gate-numbers]] 대로 **backend/.venv 인터프리터로 직접** 돌린다.)

**완료 기준**
- 두 함수가 순수(외부 I/O 0)하고 `build_motion_alignment` 산출·임계는 무변경.
- 신규 테스트 전부 통과. 기존 `tests/test_motion_alignment*.py` 회귀 0.

---

## Task 2 — 배선: 두 카드 경로 + 화이트리스트 매퍼

**파일**
- `backend/functions/pipeline/app.py`
- `backend/tests/test_pair_time_deviation.py` (배선 단언 추가)

**작업**

1. `_fault_zoom_upload_items`(`app.py:3829`) **바로 앞**에 헬퍼를 신설한다:

   ```
   def _attach_pair_time_deviation(cards, *, alignment, user_label_fps, ref_label_fps) -> None
   ```
   - `anchor_fps = _pipeline_frame_fps()` (리터럴 9.0 금지 — I1 단일 출처 규율).
   - `user_label_fps`/`ref_label_fps` 가 None 이면 `anchor_fps` 로 폴백
     (`fault_zoom.py:3085-3092` 의 `frames_fps` 폴백과 **같은 값**이어야 한다).
   - 카드마다 `motion_alignment.pair_time_deviation_sec(...)` 호출 →
     **None 이 아닐 때만** `c["pairDeviationSec"] = float(dev)` **와**
     `c["pairDeviationTier"] = tier` 를 **함께** 쓴다(둘을 나눠 쓰는 분기 금지).
   - 전체를 `try/except Exception` 으로 감싸 **어떤 실패도 카드를 죽이지 않게** 한다
     (사후 스테이지 graceful 규율 — `_attach_motion_alignment` 선례). 실패는
     `log.exception` 1줄.

2. **호출 지점 2곳** (둘 다 `_fault_zoom_upload_items` 호출 **직전**):

   - stage-1 + advisory: `_render_fault_zoom` 의 `out: list[dict] = []` 직전
     (`app.py:3815` 부근). `result` 는 이 함수 1번 인자다.
     라벨 = `_label_eff["user"] / _label_eff["ref"]`.
     `comps` 와 `adv_comps` **둘 다** 대상 — advisory 카드도 doc 에 남는다.
   - 게이트-상속: `items = _fault_zoom_upload_items(gated_raw, ...)`
     (`app.py:5941`) 직전. 라벨 = `eff["user"] / eff["ref"]`
     (이 경로는 판정 불가 시 이미 early return 이라 항상 유효).

   두 경로 모두 `alignment=result.get("motionAlignment")`.

   > 왜 두 경로인가: 최종 doc 은 `items + stage1_keep + advisory_keep` 의 합집합이다
   > (`app.py:5952-5958`). 게이트 경로만 실으면 살아남은 stage-1 카드에 구멍이 생겨
   > "왜 어떤 카드만 값이 없나"를 설명할 수 없다.

3. **★ 화이트리스트 매퍼에 복사 절 추가** — `_fault_zoom_upload_items` 안,
   `userVideoSec/refVideoSec` 절(`app.py:3948-3956` 부근) 바로 뒤:

   ```
   # quick-260919-mhl — 짝 시간 정렬 이탈 + 그 값을 만든 tier pass-through.
   # 이 매퍼는 화이트리스트라 여기 없으면 앱·감사가 이 값을 영영 못 본다.
   # 값만 싣고 tier 를 빠뜨리면 소비처가 항등 warp(trim_only) 산출을 정렬 산출로
   # 오독한다 — 둘을 **같은 절에서** 복사해 both-or-neither 를 유지한다.
   # bool 은 int 서브클래스라 명시 배제.
   _dev = c.get("pairDeviationSec")
   _dev_tier = c.get("pairDeviationTier")
   if (isinstance(_dev, (int, float)) and not isinstance(_dev, bool)
           and isinstance(_dev_tier, str) and _dev_tier):
       item["pairDeviationSec"] = float(_dev)
       item["pairDeviationTier"] = _dev_tier
   ```
   `userVideoSec` 절의 `isinstance` 형식을 따른다.

4. 테스트 추가 (`app.py` 는 env 의존이라 import 금지 — **소스 텍스트 단언**.
   선례 `backend/tests/test_anchor_part_check.py:334-357`, `test_gated_frame_skips_collapse.py`):

   - 매퍼 본문에 `item["pairDeviationSec"]` / `item["pairDeviationTier"]` 복사가 있고
     **같은 `if` 블록 안**이다(both-or-neither 가드).
   - `_render_fault_zoom` 본문과 `_run_gated_card_inherit` 본문 **각각**에
     `_attach_pair_time_deviation(` 호출이 있고, 그 호출이 그 함수의
     `_fault_zoom_upload_items(` 호출보다 **앞선다**(문자열 인덱스 비교).
   - `app.py` 어디에도 `pairDeviationSec`/`pairDeviationTier` 로 카드를 **버리거나
     게이트하거나 분기하는** 코드가 없다. 함께 `PAIR_POSE_MAX` 언급 수와
     `pair_state`/`pairState` 대입 라인이 종전 그대로인지 단언(= 게이트 무접촉 가드).
     주석 자체 무효화 방지를 위해 카운트 단언은 주석 줄을 걸러낸 뒤 센다
     (`grep -v '^#'` 에 해당하는 필터를 파이썬 쪽에서도 적용).

**검증**
```
cd backend && .venv/bin/python -m pytest tests/test_pair_time_deviation.py -q
cd backend && .venv/bin/python -m pytest -q          # 전량 — 회귀 0 (기준선 4835 passed / 0 failed)
```

**완료 기준**
- 두 경로 모두 헬퍼를 통과하고, 매퍼가 두 값을 doc item 까지 흘린다.
- `card_gates.PAIR_POSE_MAX`·`pair_gate`·`refMatched`·`refMatch`·점수 경로 **diff 0**.
- 전량 게이트 회귀 0.

---

## Task 3 — 3-way lockstep 등재

**파일**
- `app/src/types/analysis.ts`
- `backend/shared/python/sunity_shared/models.py`
- `docs/contract.md`
- `backend/tests/test_pair_time_deviation.py` (lockstep 단언 추가)

**작업**

1. `app/src/types/analysis.ts` — `FaultZoomComparison` 의 `eyeState?` 다음
   (`analysis.ts:605` 부근, 인터페이스 닫기 직전)에 추가:

   ```ts
   pairDeviationSec?: number;
   pairDeviationTier?: 'warped' | 'trim_only';
   ```
   위에 **산문 주석**(이 파일 관례)으로: 무엇인지 · 부호 규약 · both-or-neither ·
   **앱은 아직 읽지 않는다** · 부재 조건 · **"라이브는 전부 `trim_only` 라 현재 warp 는
   사실상 항등 — 이 값을 `pairDeviationTier` 없이 해석하지 말 것"** ·
   "통과선은 belle 판정 대기라 이 값으로 카드를 숨기거나 문구를 내지 말 것" ·
   lockstep 목록(`motion_alignment.pair_time_deviation_sec` +
   `pipeline _attach_pair_time_deviation` + `_fault_zoom_upload_items` 매퍼 +
   `contract.md §11.12`).
   ⚠️ `userVideoSec` 주석의 경고와 같은 급으로 **"앱이 두 초를 빼서 추정하지 말 것"**
   을 넣을 것 — rep/video 축 혼동이 §11.8 F-3 을 만든 전력이 있다.

2. `backend/shared/python/sunity_shared/models.py` — `FAULT_ZOOM_STATUS_*` 위 주석 블록
   (`models.py:659-677`)의 끝에 한 줄 추가. 선례 문장 형식 그대로:
   *"quick-260919-mhl: item 에 `pairDeviationSec`(float) + `pairDeviationTier`(str)
   조건부 추가(both-or-neither) — 짝 시간 정렬 이탈, 관측 전용·게이트 미적용.
   lockstep = analysis.ts + contract.md §11.12."*
   (본 모듈은 status enum 만 소유 — §11.6 선례. **코드 변경 0, 주석만.**)

3. `docs/contract.md` — **`### §11.12 FaultZoomComparison.pairDeviationSec / pairDeviationTier (quick-260919-mhl)`**
   신설. §11.8/§11.9 절 형식(표 + 불릿)을 따르고 다음을 담는다:
   - 정의 + 부호 규약(displayed − expected) + both-or-neither 불변식
   - **타임베이스 환산**(라벨 9.0 ↔ 측별 실효 rate) — 이 절이 정본이 된다
   - **라이브 실측 박제**: tier `trim_only` 35 / `disabled` 1 / `warped` 0,
     reason 전부 `low_global_confidence`, distance 52.8~72.0 (`DISTANCE_T2=25.0` 의 2~3배),
     `us[0]=rs[0]=0` → **현재 warp 는 사실상 항등, 값은 사실상 생짜 시간차**.
     그래서 tier 를 같이 싣는다.
   - 값 없음 조건 = 키 생략 (fail-closed)
   - **"게이트 아님"** 명시: 통과선 belle 판정 대기, 앱 미소비,
     `pairState`/`PAIR_POSE_MAX` 와 **별개 축**
   - belle 09-19 근거 4행 표(인계서 §6) + §6 표와 값이 다를 수 있는 이유(위 ⚠️ 문단)
   - 3-way lockstep 목록

   > ⚠️ **번호 주의**: 현재 `contract.md` 에 `### §11.11` 이 **두 개** 있다
   > (userMarked/holdState 절 2053행, imageUrlPlain 절 2084행). 새 절은 `§11.12` 로
   > 달아 세 번째 충돌을 만들지 말 것. 기존 두 §11.11 의 번호는 **건드리지 않는다**
   > (다른 문서·주석이 그 번호를 인용 중 — 이번 단위 범위 밖).

4. lockstep 테스트 추가 (`test_motion_alignment_contract.py:158-176` 형식):
   - `app/src/types/analysis.ts` 소스에 `pairDeviationSec?: number;` 와
     `pairDeviationTier?:` 가 있다.
   - `docs/contract.md` 에 `§11.12` 절 제목과 두 키 이름이 있다.
   - `models.py` 주석 블록에 두 키 언급이 있다.

**검증**
```
cd app && npx tsc --noEmit
cd backend && .venv/bin/python -m pytest tests/test_pair_time_deviation.py -q
```

**완료 기준**
- 앱 `tsc --noEmit` clean (앱 런타임 코드 변경 0 — 타입 추가만).
- contract.md 에 §11.12 존재, §11.11 중복 번호 그대로(추가 훼손 0).

---

## 성공 판정 (이 단위 전체)

1. `backend/.venv` 인터프리터로 전량 pytest — **회귀 0**(기준선 4835 passed / 0 failed).
2. 앱 `tsc --noEmit` clean.
3. `git diff` 에서 다음이 **한 줄도 안 바뀐 것**을 눈으로 확인:
   `card_gates.py` · `motion_alignment.py` 의 `DISTANCE_T1/T2`·`build_motion_alignment`
   본체 · 점수/감점 경로(`dimensions.py`/`kismam.py`/`assemble.py`/`deduction*`) ·
   `refMatched`/`refMatch` 방출부 · 앱 런타임 `.tsx`/`.ts`(타입 선언 제외).
4. 새 두 필드를 **읽는** 코드가 리포에 0건이다(관측 전용 — 소비처는 다음 단위).

## 이 단위가 증명하지 못하는 것 (정직하게)

- **라이브 doc 에서 이 코드가 낸 값은 못 봤다.** Pod 이 내려가 있고 실증은 10월 중순으로
  밀렸다([[pilot-postponed-to-mid-october]]). 이 단위는 **합성 입력 단위 시험까지**다.
  [[wiring-claims-need-log-evidence]] — "배선했다"를 "값이 맞다"로 말하지 말 것.
- **통과선은 여전히 없고, 오히려 더 멀어졌다.** 라이브 confirmed 카드 114장 기준
  계약 warp 이탈은 **중앙값 1.11초 / p75 3.56초**이고 **0.7초 이하가 46%뿐**이다.
  belle 표본 4개(0.2 통과 / 0.7 경계 / 4.3 실패)로 여기에 선을 그으면 카드 절반이
  날아간다. **이번 단위는 방출까지만** — 경계를 지킬 것.
- **현재 warp 가 사실상 항등이라는 사실은 이 단위가 고치지 않는다.** distance 가
  임계의 2~3배라 전 doc 이 `trim_only` 로 떨어진 것은 **정렬 품질 자체의 문제**이고
  별건이다(belle 판정 대기). 그래서 값에 tier 를 붙여 내보낸다.
- **`refMatched=true` 거짓 보증도 그대로 살아 있다**(카드 192장 전수 False 0장).
  이 필드는 그 거짓말을 고치지 않는다 — 사후에 짝 품질을 알 수단을 하나 만들 뿐이다.

## 다음 단위 후보 (이번엔 하지 않는다)

1. `refMatched` 거짓 보증 제거 — 형제 규칙(`atMatched`, `fault_zoom.py:3967`) 적용.
2. 정렬 tier 가 전부 `trim_only` 로 떨어지는 원인(distance 52~72 vs `DISTANCE_T2=25`)
   조사 → belle 판정 요청. **warp 가 살아나야 이 필드가 제 이름값을 한다.**
3. 라이브 doc 으로 `pairDeviationSec` ↔ belle 표 대조 → 통과선 판정 요청.
4. 통과선 확정 후 게이트 축 교체(`PAIR_POSE_MAX` → 시간 이탈).
