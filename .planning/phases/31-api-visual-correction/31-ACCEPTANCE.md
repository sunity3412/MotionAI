# Phase 31 — 시각 교정물 수용 기준 (ACCEPTANCE)

> **상태: PARTIAL.** "## Privacy Release Gate" 와 "## Hard Rejection" 은 확정본이다.
> "## 라벨 pair 셋" 은 **미작성(BLOCKED)** — 31-01 Task 3 재개 필요.
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

## 라벨 pair 셋

**미작성 (BLOCKED).** `smoke/fixtures_manifest.json` 이 아직 없다.

요구 계약 (B4-04 / H4-10) — 재개 시 충족 대상:

- 최소 12 pair, **PASS ≥ 4 / FAIL ≥ 8**
- category 커버: 관절 2종 이상 × 좌/우 × 직립/도립 + 가림 1+ + 모션블러 1+
- FAIL 8 은 failure axis 를 각각 포함: pole 붕괴 / identity·clothing 변형 / background 변형 /
  extra limbs·person / correction invisible / pose tolerance failure
- 항목 키 10종: `id`, `beforePath`, `beforeSha256`, `afterPath`, `afterSha256`, `label`,
  `jointKey`, `targetDeg`, `afterKeypointSource`(`path` + per-fixture `modelVersion`), `failureAxes`, `category`

**차단 사유:** pair 후보 원본(spike `wan_out/*.png`, `kpts*/`)이 **git 미추적 파일**이라
worktree 에 존재하지 않는다. 상세 = `31-01-SUMMARY.md` Blocker 2.

---

## Calibration 결과표

**placeholder — 31-13 이 기입.**
