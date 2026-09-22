# Phase 37 — 데이터 수집·누적 규격 (intake spec)

**작성 2026-09-22.** belle: *"앞으로 학습에 써먹을 데이터가 들어오면 너가 누적시켜놔야 할 거 아냐."*

이 문서는 **데이터가 들어오기 전에** 정해야 하는 것만 담는다. 학습 알고리즘·층 설계는
여기 없다(그건 kip-up 침묵 원인 규명 뒤). **이 규격은 그것과 독립이라 지금 정한다.**

---

## 0. 왜 지금 — 지금 상태로는 belle 이 모아준 걸 넣을 칸이 없다

현행 `backend/training/data/manifest.json` (548행) 필드:
```
anonymized · channel · collected · collected_at_ms · holdout · label_bucket
license_evidence · motion · s3_key · source · source_url · tier · usage
vision_verdict · yt_dlp_version
```
출처 분포: **youtube 414 · instagram 92** / internal 17 · internal_pilot 2 · internal_pilot_user 23.

즉 **506/548 이 모르는 사람 스크랩이고 라벨은 전부 `vision_verdict`(Gemini)** 다.
Phase 37 이 필요로 하는 네 가지가 들어갈 자리가 없다:

| 필요한 것 | 현행 | 왜 필요 |
|---|---|---|
| 정타/실수 **짝** | 없음 (fixture 디렉터리 관례뿐) | 판정 지점을 찾는 신호가 짝에서 나온다 |
| **강사 판정** | 없음 | Gemini 천장을 뚫는 유일한 재료 |
| **누가** 한 동작인가 | `channel`(스크랩용)뿐 | "동작의 본질" vs "그 사람 버릇" 분리 |
| 판정의 **출처**(사람/모델) | 구분 없음 | 섞이면 몇 년 뒤 천장이 다시 생긴다 |

---

## 1. 불변 규칙 (이걸 어기면 몇 년 뒤 못 쓴다)

1. **조인 키는 불변 id.** 표시 문자열로 잇지 않는다 — 이름을 바꾸면 과거 데이터가 끊긴다
   ([[display-string-is-not-a-join-key]]). 영상은 `video_hash`(SHA256 내용 해시)가 정본 키다.
   S3 경로가 바뀌어도 살아남는다.
2. **판정에는 출처를 반드시 적는다.** `source_kind: human | model`, 모델이면 모델명·버전까지.
   ★섞이면 "강사가 짚은 것"과 "Gemini가 짚은 것"을 나중에 못 가른다 = 증류 천장이 되돌아온다.
3. **점수 필드를 두지 않는다.** 스키마 수준에서 없앤다 — 규율이 아니라 구조로 막는다
   ([[analysis-objectivity-no-human-scores]]). 사람이 주는 건 **어디가 틀렸나**이지 몇 점이 아니다.
4. **부위·국면은 통제 어휘.** 자유 서술은 `note` 한 줄에만. 자유 서술만 쌓이면 학습에 못 쓴다.
5. **중첩 배열 금지** (Firestore 저장 시) — flat 으로 ([[firestore-nested-array-flat]]).
6. **동의·라이선스를 같이 받는다.** 우리가 찍은 사람 영상은 스크랩과 취급이 다르다.
   `consent` 없는 사람 영상은 학습에 넣지 않는다.

---

## 2. 레코드 4종

기존 `manifest.json` 을 **대체하지 않고 확장**한다. 신규 3종은 별 파일로 두어
스크랩 수집(harvest)과 사람 데이터가 섞이지 않게 한다.

### 2-1. `subject` — 누가 (신규: `backend/training/data/subjects.jsonl`)

```json
{"subject_id": "sub_je",  "role": "champion",   "display_name": "정은지",
 "consent": {"granted": true, "scope": "training+demo", "at": "2026-06-xx"}}
{"subject_id": "sub_i01", "role": "instructor", "display_name": "강사 A",
 "consent": {"granted": true, "scope": "training", "at": "2026-09-xx"}}
{"subject_id": "sub_s01", "role": "student",    "display_name": null,
 "consent": {"granted": true, "scope": "training", "at": "2026-09-xx"}}
```
- `role`: `champion | instructor | student`
- 학생은 `display_name` 을 두지 않는다(PII). 식별은 `subject_id` 로만.
- ★이게 없으면 **모든 기준이 정은지 한 사람**이라 "동작의 본질"과 "정은지 버릇"이 안 갈린다.

### 2-2. `clip` — 영상 1편 (기존 manifest 확장)

기존 행에 **추가**할 필드(스크랩 행은 비워 둔다):
```json
{"s3_key": "...", "motion": "kip-up",
 "video_hash": "8a6f9f8f...",        // ★정본 키. 내용 해시
 "subject_id": "sub_je",             // 누가 (스크랩은 null)
 "capture": {"view": "side", "device": "iphone", "fps_label": 30},
 "intent": "correct"                  // correct | fault | unlabeled
}
```
- `intent` 는 **촬영 의도**다. "잘한 것/일부러 틀린 것"을 찍을 때 사람이 안다.
  판정 결과가 아니라 **의도**임에 주의 — 판정은 2-4 가 따로 담는다.

### 2-3. `pair` — 짝 (신규: `backend/training/data/pairs.jsonl`)

```json
{"pair_id": "pr_kipup_je_001", "motion": "kip-up", "subject_id": "sub_je",
 "correct_hash": "…", "fault_hash": "…",
 "fault_intent": ["left_arm_underbent"],     // 통제 어휘. 여러 개 가능
 "captured_at": "2026-09-xx"}
```
- ★**같은 동작 · 같은 사람**의 짝만 `pair` 다. 사람이 다르면 짝이 아니라 별개 clip 이다
  (체형 차이가 결함으로 잡힌다).
- **동작당 짝이 여러 개여야 한다.** 지금 1개씩이라 판정 지점이 그 한 편에 과적합된다
  (2026-09-22 kip-up 실측이 그 증거).

### 2-4. `judgment` — 강사 판정 (신규: `backend/training/data/judgments.jsonl`)

```json
{"judgment_id": "jd_0001",
 "target": {"video_hash": "…"},        // 또는 {"pair_id": "…"}
 "judged_by": "sub_i01",               // 누가 판정했나
 "source_kind": "human",               // ★human | model
 "body_part": "left_elbow",            // 통제 어휘 (아래 §3)
 "phase": "hold",                      // 통제 어휘 (아래 §3)
 "verdict": "fault",                   // fault | ok
 "note": "팔이 덜 굽어 힘을 덜 받는다",   // 자유 한 줄 (선택)
 "at": "2026-09-22"}
```
- ★**점수 필드 없음.** 의도적이다.
- `source_kind: model` 이면 `model: {"name": "gemini-3.8-flash"}` 를 같이 적는다.
  → 사람 판정만 뽑아 쓰는 질의가 가능해야 한다.
- 한 영상에 판정이 여러 줄일 수 있다(부위별 1줄).

---

## 3. 통제 어휘 (v1 — 늘어나되 지우지 않는다)

**body_part** — 채점 관절과 정합. 정본 = `sunity_shared.analysis.skeleton.JOINT_KEYS`
```
left_elbow · right_elbow · left_shoulder · right_shoulder
left_hip · right_hip · left_knee · right_knee
```
★ 여기 없는 것을 강사가 짚으면 **그건 버리지 말고 `body_part: "other"` + `note` 로 받는다.**
2026-09-22 에 belle 이 짚은 **"다리가 뜬 높이"** 가 정확히 그 경우다 — 관절각 8개에 표현이
없다. 이런 행이 쌓이는 것이 **표현을 넓혀야 한다는 증거**가 된다.

**phase** — `entry | setup | hold | peak | release | exit | unknown`

**fault_intent** (짝 기록용, v1 시드 — 늘려간다)
```
left_arm_underbent · shoulder_shrug · knee_bent · hip_drop
timing_early · timing_late · asymmetry · other
```
★어휘는 **몸 언어로** 짓는다. `power_spin_bad_leg` 같은 종목 종속 이름 금지 —
Phase 37 의 1층(몸)이 다음 종목으로 넘어가려면 어휘부터 종목 무관이어야 한다.

---

## 4. belle 이 영상을 줄 때 같이 받을 것 (최소)

영상 파일만 오면 위 칸을 못 채운다. **파일당 이 네 가지**만 있으면 된다:

```
1. 동작 이름        (kip-up / power-spin / …)
2. 누가             (정은지 / 강사 A / 학생)
3. 잘한 것인가 일부러 틀린 것인가   (+ 틀린 것이면 "무엇을" 틀리게 했는지 한 줄)
4. 촬영 방향        (옆 / 앞 / 뒤)
```
강사 판정이 있으면 **부위 + 언제 + 한 줄**. 점수는 받지 않는다.

파일명에 넣어도 되고 메모로 따로 줘도 된다 — 내가 위 형식으로 옮겨 적는다.

---

## 5. 지금 있는 것을 이 규격으로 소급 (첫 작업)

`fixtures/phase15/<motion>/{correct,fault}.mp4` 6동작이 **이미 짝**인데 기록이 없다.
디렉터리 관례로만 존재한다. 첫 작업 = 이 6쌍을 `pairs.jsonl` 로 박제 + `subject_id: sub_je`.
그러면 오늘 손으로 한 비교(정타 vs 실수 8관절)를 **코드가 짝 목록을 읽어 반복**할 수 있다.

---

## 6. 이 규격이 안 정하는 것 (일부러)

- 판정 지점을 **어떻게** 찾을지 (알고리즘) — kip-up 침묵 원인 규명 뒤
- 1층(몸) 모델의 입출력 — Phase 37 본체
- 승격 모델을 앱에 꽂는 배선 — 22-08/09/10

**이 규격은 위 셋이 무엇으로 결정되든 바뀌지 않는다.** 그래서 지금 정한다.
