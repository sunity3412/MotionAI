---
phase: 31-api-visual-correction
plan: 01
subsystem: privacy-release-gate + image-model-smoke
status: PARTIAL
tags: [privacy, dashscope, s3, release-gate, smoke, calibration-input]
requires:
  - "추가 생성 예산 승인: fixtures_manifest H4-10 하한(PASS4/FAIL8) 미달분 확보용"
  - "공유 fixture 저장 위치 + 보존기간 결정: 31-13 을 타 머신/Pod 에서 실행할 경우"
provides:
  - "smoke/privacy_decision.json — consentVersion/blurOption/retentionDays (M2-05)"
  - "smoke/RESULTS.json — chosen_model=wan2.7-image-pro, sync=false, blocked=false (B4-02)"
  - "smoke/fixtures_manifest.json — 실측 교정 pair 8건, 라벨 전건 시각 확인 (B4-04)"
  - "smoke/image_smoke.py — 재현 가능한 스모크 하니스"
  - "infra/visual_input_bucket.json — bucket name 단일 출처 (H8-07)"
  - "VisualInputBucket 실물 provision 완료 (Never-versioned + 1일 lifecycle)"
  - "31-ACCEPTANCE.md — Privacy Release Gate + Hard Rejection + 모델 선정 실측"
affects:
  - "31-07 (CONSENT_VERSION/BLUR_OPTION 배포 상수 대조 대상 확보)"
  - "31-10 / 31-12 (bucket 실물 + name 단일 출처 확보, blocked=false 로 게이트 입력 존재)"
  - "31-13 (calibration 입력 확보, 단 표본 하한 미달)"
  - "31-05 / 31-06 (pose_tolerance 지배적 실패 유형 실측 — 프롬프트 설계 입력)"
tech-stack:
  added: []
  patterns:
    - "privacy 결정의 machine-readable 방출 (런타임 .planning 읽기 금지, build-time 대조)"
    - "인물 이미지 git 배제 — 경로 + sha256 참조만으로 pair 계약 성립 (T-31-02)"
    - "생성 모델 후보의 async/sync 여부를 릴리스 게이트로 사용 (B4-02)"
key-files:
  created:
    - .planning/phases/31-api-visual-correction/smoke/privacy_decision.json
    - .planning/phases/31-api-visual-correction/smoke/image_smoke.py
    - .planning/phases/31-api-visual-correction/smoke/RESULTS.json
    - .planning/phases/31-api-visual-correction/smoke/fixtures_manifest.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_bucket.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_wave0_lifecycle.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_wave0_lifecycle_before.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_policy_before.json
  modified:
    - .planning/phases/31-api-visual-correction/31-ACCEPTANCE.md
decisions:
  - "privacy option-a (블러 없음) 확정 — downstream B 분기 제거 대상"
  - "retentionDays=180 은 Sunity 학습 페어 삭제 SLA이며 벤더 보존 기간이 아님을 스키마에 명시"
  - "벤더 보존 일수는 문서 확정 불가 — null 로 두고 추정 금지"
  - "D-03 이미지 모델 = wan2.7-image-pro 확정. qwen-image-edit-plus 는 동기 전용이라 v1 구조적 탈락"
  - "fixtures_manifest 하한 미달을 패딩 대신 meetsFloor=false 로 박제 — 라벨 조작 거부"
  - "spike 004 회전 산출물은 pair 의미 불일치로 전량 제외"
metrics:
  tasks_completed: 4
  tasks_total: 4
  duration: "약 25분 (재개 세션)"
  completed: "2026-07-20"
---

# Phase 31 Plan 01: 외부 처리 release gate + 이미지 모델 스모크 Summary

D-03 이미지 모델을 `wan2.7-image-pro` 로 실측 확정하고, async-only 릴리스 게이트를 `blocked=false`
로 통과시켰다. **단 `fixtures_manifest.json` 이 H4-10 표본 하한에 미달한다** — 승인 예산 8콜을
전량 써서 실제 pair 8건(PASS 2/FAIL 6)만 확보했고, 부족분을 지어내지 않았다.

## 작업 상태

| Task | 내용 | 상태 | 커밋 |
|------|------|------|------|
| 1 | privacy release gate | COMPLETE | `f17a801` |
| 1b | VisualInputBucket provision | **COMPLETE** | `fe4d255` (before-manifest) |
| 2 | 이미지 모델 스모크 실호출 | **COMPLETE** | `bd405f9` |
| 3 | RESULTS + fixtures_manifest + ACCEPTANCE | **COMPLETE (하한 미달 박제)** | `63f83a0`, `7ca5b3b` |

## Task 1b — VisualInputBucket provision 검증 결과

버킷 `sunity-motion-pilot-visual-input` 생성 완료. 아래는 **재개 세션에서 읽기 전용 API 로 독립 재확인**한 값이다.

| 검증 항목 | 실측 결과 |
|-----------|-----------|
| 리전 | `ap-northeast-2` (`LocationConstraint` 일치) |
| **버저닝 (B7-02)** | **`get-bucket-versioning` 응답 본문 비어 있음 — `Status` 키 부재. versioning API 를 한 번도 호출하지 않았다 (Never-versioned)** |
| Block Public Access | `BlockPublicAcls` / `IgnorePublicAcls` / `BlockPublicPolicy` / `RestrictPublicBuckets` 전부 `true` |
| 암호화 | SSE-S3 `AES256`, `BucketKeyEnabled: true` |
| Ownership | `BucketOwnerEnforced` |
| Object Lock | `ObjectLockConfigurationNotFoundError` — 미설정 확인 |
| Bucket policy | 단일 Sid `DenyInsecureTransport` (`aws:SecureTransport=false` 일 때 `s3:*` Deny) |
| Lifecycle | ID `visual-input-1d`, `Filter.Prefix` `visual-input/`, `Status` Enabled, `Expiration.Days` 1 — put 후 get 재확인 |
| 태그 | `project=sunity-motion`, `environment=pilot` |
| SSM HMAC 키 | `/sunity/motion/pair-id-hmac-keys` SecureString v1 생성. 스키마 `{"active":"k1","keys":{"k1":"<32B base64>"}}` 확인 — **비밀값은 어떤 로그에도 출력하지 않았다** |

**신규 버킷 분기 확정** (사전 `head-bucket` 404):

- `infra/visual_input_wave0_lifecycle_before.json` = `{"Rules":[]}` (lifecycle 부재 정규화)
- `infra/visual_input_policy_before.json` = `priorPolicyExisted: false`, `mergePathTaken: false`
  — 기존 정책이 없으므로 Sid merge 경로를 타지 않고 known policy 를 그대로 put 했다.

## Task 2 — 이미지 모델 스모크 (생성 8콜, 상한 8콜)

`smoke/image_smoke.py` 로 fixture 4종 × 모델 2종 = 8콜을 실행했다.
fixture 는 `gate_in/*.mp4` 중간 프레임 4장 — 직립(Chair-spin) / 도립+모션블러(invert) /
도립+가림(power-spin) / 직립+가림(sideway-spin).

| 항목 | `wan2.7-image-pro` | `qwen-image-edit-plus` |
|------|--------------------|------------------------|
| 엔드포인트 | `/api/v1/services/aigc/image-generation/generation` | `/api/v1/services/aigc/multimodal-generation/generation` |
| 호출 방식 | **async — `X-DashScope-Async` → `task_id` 폴링** | **sync 전용** |
| HTTP 200 / 이미지 반환 | 4/4 / 4/4 | 4/4 / 4/4 |
| 지연 | 16.4 ~ 21.6s | 11.6 ~ 13.8s |
| 모더레이션 차단 | 0/4 | 0/4 |
| 시각 판정 PASS | **2/4** | **0/4** |

엔드포인트·바디 형상은 추측하지 않고 벤더 문서(2026-07-20 조회)에서 확인한 뒤 사용했다.

**위생 확인:** 임시 S3 key 4건 전부 `delete-object` 후 `head-object` 404 확인(4/4).
키는 SSM 경유만, 리터럴 0. 산출 이미지는 `.planning` 하위 0건.

### 실측이 뒤집은 가정

1. **모더레이션 차단 0/8.** spike 008 의 **영상** 편집 실측(첫 시도 30%, 영구 10%)과 대비된다.
   다만 8표본으로 차단률을 확정할 수 없으므로 **D-08 조용한 폴백은 그대로 유지**한다 —
   0건을 "차단 없음"으로 일반화하지 않았다.
2. **지배적 실패는 `pose_tolerance` 다.** 두 모델 모두 "지정 관절만 교정하고 나머지는 보존하라"를
   자주 어기고 자세를 전면 재생성했다. 8건 중 목표 관절만 교정하고 나머지를 보존한 사례는 **2건뿐**이며
   둘 다 wan 이다. 31-05/31-06 프롬프트 설계와 31-13 임계값이 이 유형을 반드시 다뤄야 한다.

## Task 3 — RESULTS.json / fixtures_manifest.json / ACCEPTANCE

### RESULTS.json — `blocked = false`

`chosen_model = wan2.7-image-pro`, `sync = false`. B4-02 async-only 게이트를 통과했다.
`qwen-image-edit-plus` 는 동기 전용이라 **품질과 무관하게 v1 후보에서 구조적으로 탈락**한다.

> `blocked=false` 는 **품질 통과가 아니다.** 임계값 산출과 calibration 미달 판정은 31-13 몫이며
> 31-13 이 이 파일을 갱신할 수 있다 (H3-02).

### fixtures_manifest.json — 계약 충족, 표본 하한 미달

10키 pair 계약은 전건 충족. **라벨 8건 전부 산출 이미지를 Read 로 시각 확인하고 부여했다 — 미확인 추정 0건.**

| 항목 | 요구 (H4-10) | 실제 | 판정 |
|------|--------------|------|------|
| PASS | ≥ 4 | 2 | 미달 |
| FAIL | ≥ 8 | 6 | 미달 |
| 총 pair | ≥ 12 | 8 | 미달 |
| category 커버 | 좌/우 × 직립/도립 + 가림 + 모션블러 | 전부 충족 | 충족 |
| failure axis | 6축 | 3축 (`correction_invisible`, `pose_tolerance`, `clothing`) | 미달 |

누락 축: `pole`, `background`, `extra_limbs`, `identity`.

**미달을 패딩하지 않은 이유 (의도적 판단):**

1. 승인 예산 8콜 전량 소진 — 추가 pair 는 추가 예산이 필요하다.
2. spike 004 산출물(`wan_out/pair_chair_*.png`, `smoke_out/frames/*.png`)을 **전량 제외**했다.
   실제로 열어 확인한 결과 (a) **좌우 2분할 합성 이미지**라 before/after 를 분리 경로로 참조할 수 없고,
   (b) **카메라 회전** 산출물이라 `jointKey`/`targetDeg` 교정 의미가 성립하지 않는다.
   pair 로 넣으면 31-13 이 채택할 임계값이 그대로 오염된다.
3. 누락 축은 8표본에서 **실제로 발생하지 않았다.** 두 모델 모두 폴·배경·사지 보존은 잘 지켰다는
   실측 결과이며, 해당 축 FAIL 표본은 표본 수를 늘리거나 **적대적 프롬프트를 별도 설계**해야 얻는다.

## Deviations from Plan

**1. [Rule 3] SSM `/sunity/motion/pair-id-hmac-keys` 미존재 → 신규 생성 분기**

계획서는 기존 존재를 가정했으나 실측 결과 `ParameterNotFound` 였다. belle 승인 후 신규 생성으로
정정했고, 재개 세션에서 SecureString v1 + 스키마(`active`/`keys`)를 재확인했다.

**2. [실측 분기 확정] VisualInputBucket 신규 생성**

사전 404 → 기존 policy/lifecycle merge·rollback 경로 미사용. before manifest 2종은
"기존 없음"을 명시적으로 기록하는 형태로 작성했다(빈 파일로 두면 미적용과 구분되지 않는다).

**3. [Rule 3] 엔드포인트 미확정 → 문서 조회 후 확정**

계획서는 `wan2.7-image-pro` 의 이미지 편집 엔드포인트를 미상으로 두었다. 추측 대신 벤더 문서를
조회해 `image-generation/generation` + `X-DashScope-Async` 를 확인한 뒤 호출했다.

**4. [T-31-02 방어] fixture 이미지 저장 위치 재배치**

pair 이미지를 처음 `~/sunity-fixtures` 에 두었으나 **홈 디렉터리 자체가 git 저장소**이고 해당 경로가
ignore 되지 않음을 발견했다(추적되진 않았으나 인물 이미지가 커밋될 위험). 즉시
`/Users/Shared/sunity-fixtures/31-01-visual-correction/` 로 이전하고 어떤 git 저장소에도 속하지
않음을 확인했다.

**5. [계획 대비 축소] fixtures_manifest 표본 하한 미달**

위 "미달을 패딩하지 않은 이유" 참조. 계획서 Task 3 의 automated verify 중 `len>=12` +
`PASS>=4` + `FAIL>=8` 절은 **통과하지 않는다.** 나머지 절(RESULTS 스키마, 10키 계약,
privacy 3키, ACCEPTANCE `Training` grep)은 통과한다.

## Known Stubs

| 항목 | 위치 | 사유 |
|------|------|------|
| `afterKeypointSource.modelVersion = null` | `fixtures_manifest.json` 전건 | RTMW 실측 미수행. 라벨은 육안 판정이며 달성 각도 측정은 31-13 몫 (M4-05). 숫자를 추정해 채우지 않았다 |
| Display/Training 임계값 | `31-ACCEPTANCE.md` | **의도된 placeholder** — 31-13 harness 산출 (H3-02) |
| Calibration 결과표 | `31-ACCEPTANCE.md` | **의도된 placeholder** — 31-13 기입 |

## 잔여 blocker (belle 결정 필요)

**1. fixtures_manifest 표본 하한 — 추가 생성 예산**

하한 충족까지 최소 PASS +2 / FAIL +2 (총 4 pair) 가 부족하고, 누락 축 4종
(`pole`/`background`/`extra_limbs`/`identity`)은 적대적 프롬프트 설계가 별도로 필요하다.
현 승인 상한은 생성 8콜(소진) + calibration judge 24콜(31-13 몫, 미사용)이다.
**추가 생성 콜 예산 없이는 31-13 이 H4-10 을 만족하는 입력을 받을 수 없다.**

**2. 공유 fixture 저장 위치 + 보존기간**

현재 pair 이미지는 로컬 단일 머신 경로에 있다. 31-13 을 다른 머신/Pod 에서 실행하려면
공유 저장 위치와 그 보존기간을 belle 이 승인해야 한다(인물 이미지이므로 privacy 결정 대상).
임의로 새 클라우드 PII 표면을 만들지 않았다.

## Self-Check: PASSED

- `smoke/privacy_decision.json`, `smoke/image_smoke.py`, `smoke/RESULTS.json`,
  `smoke/fixtures_manifest.json` — 전부 존재, JSON 파싱/스키마 assert 통과
- `infra/` manifest 4종 — 전부 존재
- `31-ACCEPTANCE.md` — 존재, `Training` grep 통과, Display/Training 임계값 선언 숫자 0
- 커밋 `fe4d255`, `bd405f9`, `7ca5b3b` — git log 확인
- 버킷 속성 8종 — 읽기 전용 API 로 독립 재확인 (versioning `Status` 키 부재 포함)
- 생성 호출 **8/8 (상한 준수, 초과 0)**. calibration judge 24콜 미사용
- `.planning/phases/31-api-visual-correction` 하위 인물 이미지 **0건**
- 스테이징된 PNG **0건** (`git diff --cached --name-only` 확인)
- STATE.md / ROADMAP.md 무수정
