# Phase 31 — 시각 교정물 수용 기준 (ACCEPTANCE)

> **상태: PARTIAL — calibration BLOCKED.** "## Privacy Release Gate", "## Hard Rejection",
> "## 모델 선정 실측" 은 확정본이다.
> "## Calibration 결과표" 는 31-13 harness 실측으로 **기입 완료**됐고, 그 결과는
> **`blocked = true` (임계값 4값 미채택)** 이다 — 사유 3종은 해당 절 참조.
> "## Display 게이트" / "## Training 적재 게이트" 의 임계값은 따라서 **여전히 숫자 0개**이며,
> 이는 placeholder 가 아니라 **측정된 결론**이다 (H3-02 — 선언값·보간값 금지).

---

## Privacy Release Gate

**확정: 2026-07-20, belle.** machine-readable 원본 = `smoke/privacy_decision.json`
(downstream 은 이 JSON 과 build-time 상수를 대조한다 — 런타임 `.planning` 읽기 금지, M3-02).

| 항목 | 확정값 |
|------|--------|
| privacy option | **option-a (블러 없음)** — Pod frame 원본을 그대로 외부 전송. **downstream 의 option B(blur) 분기는 제거 대상** |
| consentVersion | `pilot-optout-v1` (+ `capturedAtMs` 기록) |
| retentionDays | **180** |
| retentionDays 의미 | **Sunity 학습 페어 삭제 SLA.** 벤더 보존 기간이 **아니다** |
| pair 가명화 | HMAC-SHA256, versioned key set — SSM `/sunity/motion/pair-id-hmac-keys` (`{"active","keys"}`), retired key 삭제 가능 (H2-06) |
| 페어 적재 대상 | `learningOptIn=true` 사용자만 |
| 지출 상한 | 스모크 생성 8콜 + 31-13 calibration judge 24콜 = **총 32콜**. 초과 시 STOP + belle 보고 |

### 벤더(외부 처리자) 사실관계

호출 대상은 **국제망 `https://dashscope-intl.aliyuncs.com`** — 중국 본토 엔드포인트가 아니다
(spike 004 `wan_gate_batch.py:24`).

| 항목 | 확인 내용 | 출처 |
|------|-----------|------|
| 모델 학습 이용 | **사용하지 않음** (벤더 명시) | `help.aliyun.com/zh/model-studio/data-security`, 2026-07-20 조회 |
| 암호화 | AES-256 | 동일 |
| 인증 | SOC 2 (unqualified opinion) | 동일 |
| 벤더 보존 일수 | **미공개 — 숫자 확정 불가** | 동일 ("법령 요구에 따라 호출 시 생성 데이터를 저장"으로만 기술) |

> 국제망 전용 영문 data-security 문서 URL 4종은 조회 시 전부 404 였다.
> **벤더 보존 일수를 추정하거나 지어내지 않는다** — 고지 문구는 "일정 기간 보관(일수 미공개)"으로 기술한다.

### 고지 문구 방향 (belle 승인)

"분석 시 **얼굴이 포함된 프레임이 제3자(Alibaba Cloud Model Studio, 싱가포르)로 전송**됩니다.
벤더는 이 데이터를 모델 학습에 사용하지 않는다고 명시하며, 벤더 정책상 일정 기간 보관됩니다.
학습 동의 사용자의 교정 페어는 Sunity 저장소에 가명화되어 보관되며 180일 후 삭제됩니다."

**필수:** 얼굴 프레임의 제3자 전송 사실을 반드시 명시할 것 (belle 지시 — 생략 금지).

---

## Hard Rejection

아래 중 하나라도 해당하면 judge 점수와 무관하게 **무조건 FAIL** (display·training 공통):

- 인물 부재
- 추가 인물 또는 추가 사지(extra limbs/person) 발생
- 폴(pole) 기하 붕괴
- 판정 불능 (프레임 손상, 과도한 블러 등으로 관절 식별 불가)

---

## Display 게이트

judge 7축 전부 true + 임계값 조건.

**임계값: 미채택 (`CALIBRATION.blocked = true`).** 31-13 harness 를 실제로 돌렸고,
**측정된 근거가 임계값을 고르기에 부족하다는 것이 측정 결과**다. 아래 "Calibration 결과표" 참조.

- `DISPLAY_JUDGE_CONFIDENCE` — **미채택** (confidence 축이 이 표본에서 판별력 0 — 아래 §판별력)
- `DISPLAY_POSE_TOL_DEG` — **미측정** (pose 측정 12/12 `pose_gate_unavailable` — Pod 부재)

이 문서는 임계값 숫자를 선언하지 않는다 (H3-02). **보간·추정으로 채우지도 않는다.**

## Training 적재 게이트

Display 게이트 전부 + 추가 임계값.

**임계값: 미채택 (`CALIBRATION.blocked = true`).** display 가 미채택이므로 그보다
엄격한 값을 정의할 기준선 자체가 없다.

**규칙(선기록): training 게이트는 display 게이트보다 항상 엄격하다.**
즉 training 통과 집합 ⊆ display 통과 집합. 역전은 calibration 결과와 무관하게 금지.

**build gate (31-10 강제 — B4-05).** env 주입 시 아래 부등식을 빌드 타임에 검사하고,
위반이면 빌드 실패로 종결한다:

```
TRAINING_JUDGE_CONFIDENCE > DISPLAY_JUDGE_CONFIDENCE
TRAINING_POSE_TOL_DEG     < DISPLAY_POSE_TOL_DEG
```

4값 중 하나라도 부재하면 `VISUAL_CORRECTION_ENABLED` 는 OFF 로 고정된다 — 현재 상태가 그것이다.

---

## 모델 선정 실측 (D-03 확정)

**실측: 2026-07-20, 생성 8콜.** 원본 = `smoke/RESULTS.json`.

| 항목 | `wan2.7-image-pro` | `qwen-image-edit-plus` |
|------|--------------------|------------------------|
| 엔드포인트 | `/api/v1/services/aigc/image-generation/generation` | `/api/v1/services/aigc/multimodal-generation/generation` |
| 호출 방식 | **async (task_id 반환)** | **sync 전용** |
| HTTP 200 | 4/4 | 4/4 |
| 이미지 반환 | 4/4 | 4/4 |
| 지연 | 16.4 ~ 21.6s | 11.6 ~ 13.8s |
| 모더레이션 차단 | 0/4 | 0/4 |
| 시각 판정 PASS | **2/4** | **0/4** |

**chosen = `wan2.7-image-pro`. `blocked = false`.**

- B4-02 async-only 게이트: chosen 이 async task_id 를 반환하므로 통과.
- `qwen-image-edit-plus` 는 **동기 전용이라 v1 후보에서 구조적으로 탈락**한다 (품질과 무관).
- 모더레이션 차단 0/8 — spike 008 **영상** 편집의 첫시도 30%/영구 10%와 대비된다.
  표본 8건은 차단률 확정에 부족하므로 **D-08 조용한 폴백은 유지**한다.

> **주의: `blocked=false` 는 품질 통과가 아니다.** 임계값 산출과 calibration 미달 판정은
> 31-13 harness 몫이며 31-13 이 `RESULTS.json` 을 갱신할 수 있다 (H3-02).

### 실측이 드러낸 실패 유형 (31-05/31-06 프롬프트 설계 입력)

두 모델 모두 "지정 관절만 교정하고 나머지는 보존하라"는 지시를 자주 어기고 **자세를 전면 재생성**했다.
8건 중 목표 관절만 교정하고 나머지를 보존한 사례는 **2건(둘 다 wan)** 이다.
`pose_tolerance` 가 지배적 실패 축이므로 31-13 임계값 설계가 이 유형을 반드시 다뤄야 한다.

---

## 라벨 pair 셋

**`smoke/fixtures_manifest.json` — 31-13 에서 8건 보충 (총 16건, wan scope 12건). PASS 하한만 미달.**

| 항목 | 요구 (H4-10) | 31-01 | **31-13 보충 후 (wan scope)** | 판정 |
|------|--------------|-------|------------------------------|------|
| PASS | ≥ 4 | 2 | **3** | **미달 (1건 부족)** |
| FAIL | ≥ 8 | 6 | **9** | 충족 |
| 총 pair | ≥ 12 | 8 | **12** | 충족 |
| category 커버 | 좌/우 × 직립/도립 + 가림 + 모션블러 | 충족 | 충족 | 충족 |
| failure axis 커버 | 6축 | 3축 | **7축 전부** | 충족 |

31-13 이 belle 승인 추가 예산 **8콜을 전량 집행**(누적 생성 16콜 = 31-01 8 + 31-13 8)해
faithful 4 + adversarial 4 를 생성했다. 누락 4축(`pole`/`background`/`extra_limbs`/`identity`)은
**적대적 프롬프트로 전부 유도 성공**했다.

**PASS 미달을 패딩하지 않은 이유:** faithful 4콜 중 실제 PASS 는 chair-spin 1건뿐이었고,
나머지 3건은 강화된 보존 지시에도 자세를 전면 재생성했다(`pose_tolerance`).
**하한을 맞추려고 FAIL 을 PASS 로 재라벨하지 않았다.**

**적대적 표본의 한계 (명시):** adversarial 4건은 실패를 **인위적으로 유도**한 표본이라
production 실패 분포가 아니다. judge 축 검출력 검증에는 유효하지만 FA/FR 격자에서는
true_fail 을 과대계상한다 — manifest 의 `sampleKind` 필드로 구분해 두었다.

spike 004 산출물은 계속 **전량 제외**한다 — (a) 좌우 2분할 합성 이미지, (b) 카메라 회전
산출물이라 `jointKey`/`targetDeg` 교정 의미가 없다. pair 로 넣으면 임계값이 오염된다.

**모든 라벨은 Claude 가 산출 이미지 16건을 전부 시각 확인하고 부여했다 — 미확인 추정 0건.**

> 이미지는 git 에 저장하지 않는다 (T-31-02). manifest 는 경로 + sha256 만 참조하며
> 실물은 `/Users/Shared/sunity-fixtures/31-01-visual-correction/` 에 있다(어떤 git 저장소에도 미포함).
> **미결정:** 31-13 을 다른 머신/Pod 에서 실행하려면 공유 저장 위치와 그 보존기간을 belle 이 승인해야 한다.

---

## Calibration 결과표

**실측: 2026-07-20, 31-13 harness. 원본 = `smoke/CALIBRATION.json`.**
**판정: `blocked = true` — 임계값 4값 전부 미채택.**

재현 커맨드:

```bash
export GEMINI_API_KEY=$(AWS_PROFILE=sunity-motion aws ssm get-parameter \
    --name /sunity/motion/gemini-api-key --with-decryption \
    --query Parameter.Value --output text)
export RUNPOD_AUTH_TOKEN=$(AWS_PROFILE=sunity-motion aws ssm get-parameter \
    --name /sunity/motion/runpod-auth-token --with-decryption \
    --query Parameter.Value --output text)
PYTHONPATH=backend/shared/python python3 backend/scripts/calibrate_visual_gates.py \
    --pose-url https://<pod>-8000.proxy.runpod.net/pose-image
```

harness 는 측정 로직을 갖지 않는다 — `visual_gen.judge_corrected_pose` /
`judge_display_pass` / `fault_zoom.joint_inner_angle_deg` / `pose_gate.measure_generated_pose`
를 그대로 호출한다 (H3-02 · B4-05 재구현 0).

### 표본 (scope = `wan2.7-image-pro`)

scope 를 chosen 모델로 한정한 이유: `qwen-image-edit-plus` 는 B4-02 async-only 게이트에서
**구조적으로 탈락**했으므로, 그 산출물로 고른 임계값은 결코 실행되지 않을 코드에 대한 근거가 된다.

| 항목 | 요구 (H4-10) | 실제 | 판정 |
|------|--------------|------|------|
| PASS | ≥ 4 | **3** | **미달 (1건 부족)** |
| FAIL | ≥ 8 | 9 | 충족 |
| 총 pair | ≥ 12 | 12 | 충족 |
| failure axis | 6축 | **7축 전부** | 충족 |
| judge 판정 성공 | — | 12/12 | — |
| pose 측정 성공 | — | **0/12** | **불가** |

failure axis 7종: `pose_tolerance`, `clothing`, `correction_invisible`, `pole`,
`background`, `extra_limbs`, `identity`. 누락 4축은 31-13 에서 **적대적 프롬프트로 유도해
전부 확보**했다(승인 추가 예산 8콜 집행, 누적 생성 16콜).

**라벨 전건 시각 확인.** 신규 8건 모두 before/after 이미지를 실제로 열어 판정했다 — 추정 라벨 0건.

### blocked 사유 3종 (전부 측정 결과)

| # | reason | 내용 |
|---|--------|------|
| 1 | `insufficient_pass_samples:3<4` | faithful 4콜 중 PASS 는 1건(chair-spin)뿐. **하한을 맞추려 FAIL 을 PASS 로 재라벨하지 않았다** |
| 2 | `pose_unmeasured_fraction:12/12` | RunPod Pod 부재 → `/pose-image` 호출 12건 전부 `pose_gate_unavailable`. **실제로 호출해서 얻은 결과**이며 "시도 안 함"이 아니다 |
| 3 | `confidence_axis_non_discriminating` | confidence 격자 4값 전부 FA/FR 동률 — 아래 §판별력 |

### 격자표 (pose tol × confidence, 16조합)

**16조합 전부 `evaluable = 0` / `undeterminable = 12`.** pose 축을 한 건도 재지 못해
격자가 성립하지 않는다. FA/FR 숫자를 적을 수 있는 칸이 없다 — 표를 채우려면 Pod 가 필요하다.

### judge 단독 confidence 스윕 (측정 가능한 유일한 축)

production 게이트가 아니다. pose 게이트는 통과 집합을 **줄이기만** 하므로
`judge 단독 FA ≥ production FA`(상한), `judge 단독 FR ≤ production FR`(하한)이다.

| confidence | FA (상한) | FR (하한) | true_pass | true_fail |
|-----------|-----------|-----------|-----------|-----------|
| 0.60 | 4 | 1 | 2 | 5 |
| 0.70 | 4 | 1 | 2 | 5 |
| 0.80 | 4 | 1 | 2 | 5 |
| 0.85 | 4 | 1 | 2 | 5 |

<a id="판별력"></a>**판별력 0 — 이것이 이 phase 의 핵심 실측이다.**
격자 전 구간에서 값이 완전히 동일하다. 원인: **4건의 false accept 가 모두 judge confidence
0.95 ~ 1.00 에서 발생**했다. 격자 상단(0.85)보다 높으므로 **어떤 confidence 임계값으로도
제거되지 않는다.** 이 상태에서 "FA 최소" 규칙을 적용하면 전 조합 동률이라 사실상 무작위
선택이 되고, 그것이 M4-03 이 금지한 arbitrary fallback 이다. 그래서 채택하지 않았다.

### confusion table — judge 축별 검출율

| failure axis | 표본 | 검출 | 비고 |
|--------------|------|------|------|
| `pole` | 1 | 1 | 폴 제거를 `pole_ok=false` 로 정확히 검출 |
| `background` | 1 | 1 | 배경 교체 검출 |
| `extra_limbs` | 1 | 1 | 팔 4개 산출물을 `no_extra_limbs=false` 로 검출 |
| `identity` | 1 | 1 | 인물 교체 검출 (`clothing_ok` 동시 false) |
| `clothing` | 1 | 1 | 상동 |
| `correction_invisible` | 2 | 1 | |
| **`pose_tolerance`** | **6** | **2** | **지배적 실패 유형에서 6건 중 4건 미검출** |

**가장 중요한 실측: judge 는 보존 축(폴/배경/사지/인물)은 잘 잡지만, production 의 지배적
실패 유형인 `pose_tolerance`(자세 전면 재생성)를 6건 중 4건 놓쳤다.** 그 4건은 7축이 전부
true 이고 confidence 0.95~1.00 이었다 — 즉 judge 는 **확신을 갖고 틀렸다.**

이는 31-06 pose gate 설계 근거(H-03 백스톱: "생성형 judge 는 그럴듯한가만 판정할 뿐
기하가 맞는가를 판정하지 못한다")를 실측으로 확인한 것이다. **결과적으로 display 게이트의
안전성은 사실상 전적으로 pose gate 에 달려 있으며, 그 pose gate 가 지금 측정 불가한 축이다.**

### 결론 — downstream 영향

- **31-09 / 31-10:** 주입할 env 4값 없음 → `VISUAL_CORRECTION_ENABLED` OFF 고정.
- **31-12:** `CALIBRATION.blocked == true` 이므로 H4-09 배포 게이트에서 라이브 롤아웃 차단.
  인프라는 진행 가능하나 flag 는 OFF 유지.
- **`RESULTS.json` 은 수정하지 않았다.** 그 파일의 `blocked` 는 B4-02 **async-only 릴리스
  게이트** 전용 의미이고(`visual_gen.derive_engine_blocked` 및 전사 상수
  `_RESULTS_BLOCKED` 와 lockstep), calibration 미달과는 다른 사건이다. 31-12 는 두 파일을
  **각각** 읽으므로 `CALIBRATION.blocked=true` 만으로 flag OFF 목적은 이미 달성된다.
  두 의미를 한 필드에 겹치면 shipped 상수와 드리프트가 생긴다.

### 해소 조건 (blocked 3종 각각)

1. **PASS +1 이상** — 추가 생성 예산 필요. faithful 프롬프트의 실측 PASS 율은 4콜 중 1건이다.
2. **Pod 기동** — `/pose-image` 가 살아 있어야 pose 축 12건 측정 가능. 그 뒤 16조합 격자가 성립한다.
3. **confidence 격자 재설계** — 현행 상단 0.85 는 무의미하다. FA 가 0.95~1.00 에 몰려 있으므로
   격자를 상향(예: 0.9/0.95/0.98/0.99)하거나, **confidence 를 게이트 축에서 제외하고 pose 축에
   의존**하는 설계 결정이 필요하다. 이건 측정이 아니라 **belle 의 설계 판단** 영역이다.
