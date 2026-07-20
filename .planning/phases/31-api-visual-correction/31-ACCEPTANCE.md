# Phase 31 — 시각 교정물 수용 기준 (ACCEPTANCE)

> **상태: PARTIAL.** "## Privacy Release Gate", "## Hard Rejection", "## 모델 선정 실측" 은 확정본이다.
> "## 라벨 pair 셋" 은 **작성됐으나 H4-10 하한 미달** — 추가 생성 예산 승인 필요.
> "## Display 게이트" / "## Training 적재 게이트" 임계값과 "## Calibration 결과표" 는
> 설계상 placeholder 이며 **31-13 harness 가 기입**한다 (H3-02 — 선언값 금지).

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

**임계값: `31-13` harness 산출 — `CALIBRATION.json` 참조.**
(이 문서는 임계값 숫자를 선언하지 않는다 — H3-02.)

## Training 적재 게이트

Display 게이트 전부 + 추가 임계값.

**임계값: `31-13` harness 산출 — `CALIBRATION.json` 참조.**

**규칙(선기록): training 게이트는 display 게이트보다 항상 엄격하다.**
즉 training 통과 집합 ⊆ display 통과 집합. 역전은 calibration 결과와 무관하게 금지.

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

**작성됨 — `smoke/fixtures_manifest.json`. 단 H4-10 하한 미달.**

| 항목 | 요구 (H4-10) | 실제 | 판정 |
|------|--------------|------|------|
| PASS | ≥ 4 | **2** | 미달 |
| FAIL | ≥ 8 | **6** | 미달 |
| 총 pair | ≥ 12 | **8** | 미달 |
| category 커버 | 좌/우 × 직립/도립 + 가림 + 모션블러 | 전부 충족 | 충족 |
| failure axis 커버 | 6축 | `correction_invisible`, `pose_tolerance`, `clothing` (3축) | 미달 |

누락 축: `pole`, `background`, `extra_limbs`, `identity`.

**미달 사유 (라벨을 지어내지 않은 결과):**

1. 승인된 생성 8콜을 **전량 소진**해 실제 교정 pair 8건만 확보했다. 추가 pair 는 추가 예산이 필요하다.
2. spike 004 산출물(`wan_out/pair_chair_*.png`, `smoke_out/frames/*.png`)은 **제외**했다 —
   (a) 좌우 2분할 **합성 이미지**라 before/after 를 분리 경로로 참조할 수 없고,
   (b) **카메라 회전** 산출물이라 `jointKey`/`targetDeg` 교정 의미가 없다.
   pair 로 넣으면 31-13 임계값이 그대로 오염된다.
3. 누락 축은 8표본에서 **실제로 발생하지 않았다** — 두 모델 모두 폴·배경·사지 보존은 잘 지켰다는
   실측 결과다. 해당 축 FAIL 표본은 표본 수를 늘리거나 적대적 프롬프트를 별도 설계해야 얻을 수 있다.

**모든 라벨은 Claude 가 산출 이미지 8건을 전부 시각 확인하고 부여했다 — 미확인 추정 0건.**

> 이미지는 git 에 저장하지 않는다 (T-31-02). manifest 는 경로 + sha256 만 참조하며
> 실물은 `/Users/Shared/sunity-fixtures/31-01-visual-correction/` 에 있다(어떤 git 저장소에도 미포함).
> **미결정:** 31-13 을 다른 머신/Pod 에서 실행하려면 공유 저장 위치와 그 보존기간을 belle 이 승인해야 한다.

---

## Calibration 결과표

**placeholder — 31-13 이 기입.**
