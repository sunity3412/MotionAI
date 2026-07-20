---
phase: 31-api-visual-correction
plan: 01
subsystem: privacy-release-gate + image-model-smoke
status: BLOCKED
tags: [privacy, dashscope, s3, release-gate, smoke]
requires:
  - "환경 권한: 라이브 AWS mutation 실행 허용 (현재 classifier 차단 — Task 1b)"
  - "데이터: spike 004 pair 후보 이미지 접근 경로 (Task 3)"
provides:
  - "smoke/privacy_decision.json — consentVersion/blurOption/retentionDays (M2-05)"
  - "31-ACCEPTANCE.md — Privacy Release Gate + Hard Rejection 확정본"
  - "infra/visual_input_bucket.json — bucket name 단일 출처 (H8-07)"
affects:
  - "31-07 (CONSENT_VERSION/BLUR_OPTION 배포 상수 대조 대상 확보)"
  - "31-10 / 31-12 (bucket name 단일 출처 확보, 단 버킷 실물 미생성)"
  - "31-13 (fixtures_manifest 미생성 — calibration 입력 부재)"
tech-stack:
  added: []
  patterns:
    - "privacy 결정의 machine-readable 방출 (런타임 .planning 읽기 금지, build-time 대조)"
key-files:
  created:
    - .planning/phases/31-api-visual-correction/smoke/privacy_decision.json
    - .planning/phases/31-api-visual-correction/31-ACCEPTANCE.md
    - .planning/phases/31-api-visual-correction/infra/visual_input_bucket.json
    - .planning/phases/31-api-visual-correction/infra/visual_input_wave0_lifecycle.json
  modified: []
decisions:
  - "privacy option-a (블러 없음) 확정 — downstream B 분기 제거 대상"
  - "retentionDays=180 은 Sunity 학습 페어 삭제 SLA이며 벤더 보존 기간이 아님을 스키마에 명시"
  - "벤더 보존 일수는 문서 확정 불가 — null 로 두고 추정 금지"
metrics:
  tasks_completed: 1
  tasks_total: 4
  duration: "약 45분"
  completed: null
---

# Phase 31 Plan 01: 외부 처리 release gate + 이미지 모델 스모크 Summary

belle 승인으로 Task 1(privacy release gate)은 확정·방출 완료. **Task 1b 이후는 환경 권한
차단으로 실행 불가** — 승인은 있으나 실행 권한이 없다. 두 개의 독립 blocker 로 정지한다.

## 작업 상태

| Task | 내용 | 상태 | 커밋 |
|------|------|------|------|
| 1 | privacy release gate | **COMPLETE** | `f17a801` |
| 1b | VisualInputBucket provision | **BLOCKED** (권한) | — |
| 2 | 이미지 모델 스모크 실호출 | **BLOCKED** (1b 의존) | — |
| 3 | RESULTS/fixtures_manifest/ACCEPTANCE | **PARTIAL** | `63f83a0` |

`smoke/RESULTS.json` 과 `smoke/fixtures_manifest.json` 은 **생성되지 않았다.**
계획서 Task 3 의 automated verify 는 이 두 파일을 요구하므로 **현재 통과하지 않는다.**

## 완료된 작업

### Task 1 — privacy release gate (COMPLETE)

belle 결정을 `smoke/privacy_decision.json` 으로 방출했다. 확정값: `blurOption="none"`(option-a),
`retentionDays=180`, `consentVersion="pilot-optout-v1"`, 지출 상한 32콜.

belle 지시에 따라 **retentionDays 의 의미를 스키마 수준에서 못박았다** — `retentionDaysScope`
= `"sunity_training_pairs_only"`, `retentionDaysMeaning` 에 "벤더 보존 기간이 아니다" 명시.
벤더 보존은 별도 `vendorRetention` 객체로 분리하고 `retentionDays: null` + 미공개 사유를 기록해
**숫자를 추정하지 않았다.**

### 벤더 정책 조사 결과

엔드포인트는 국제망 `dashscope-intl.aliyuncs.com`(싱가포르) — 본토 아님.
`help.aliyun.com/zh/model-studio/data-security`(2026-07-20 조회) 기준: 모델 학습 미사용 명시,
AES-256, SOC 2 통과. 보존 일수는 "법령상 저장"으로만 기술되고 **숫자 미공개**이며 국제망 전용
영문 data-security 문서 URL 4종은 전부 404 였다.

### Task 3 — 부분 (ACCEPTANCE 골격)

`31-ACCEPTANCE.md` 작성. "Privacy Release Gate"·"Hard Rejection" 은 확정본,
Display/Training/Calibration 은 설계대로 placeholder(임계값 선언 숫자 0 — H3-02 준수 grep 확인),
"라벨 pair 셋" 은 BLOCKED 표기. `infra/` manifest 2종은 값 정의만 완료(미적용).

## Blockers

### Blocker 1 — 라이브 AWS mutation 권한 차단 (Task 1b)

`aws s3api create-bucket` 이 Claude Code auto mode classifier 에 의해 거부됐다(2회 확인).
읽기 전용 호출(`head-bucket`, `sts get-caller-identity`, `ssm get-parameter`)은 정상 동작하므로
**AWS 자격증명 문제가 아니라 실행 환경의 쓰기 작업 차단**이다.

belle 의 승인은 제품·비용 승인이며 이 기술적 권한 게이트를 해제하지 못한다. 우회를 시도하지 않았고
샌드박스 비활성화 옵션도 쓰지 않았다. 해소 방법은 둘 중 하나다:

1. 사용자가 `aws s3api` / `aws ssm put-parameter` 에 대한 Bash 권한 규칙 추가
2. 사용자가 직접 provision 실행 (아래 명령 그대로 사용 가능)

미실행 mutation 목록 (승인 완료, 실행만 남음):

```
BUCKET=sunity-motion-pilot-visual-input   REGION=ap-northeast-2   AWS_PROFILE=sunity-motion

aws s3api create-bucket --bucket $BUCKET --region $REGION \
  --create-bucket-configuration LocationConstraint=$REGION
aws s3api put-public-access-block --bucket $BUCKET --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-ownership-controls --bucket $BUCKET \
  --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
aws s3api put-bucket-encryption --bucket $BUCKET --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-policy --bucket $BUCKET --policy <SecureTransport deny>
aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET \
  --lifecycle-configuration file://infra/visual_input_wave0_lifecycle.json
aws ssm put-parameter --name /sunity/motion/pair-id-hmac-keys --type SecureString \
  --value '{"active":"v1","keys":{"v1":"<random>"}}'
```

**`put-bucket-versioning` 은 호출하지 않는다** (Never-versioned — B7-02).
검증(`get-bucket-versioning` Status key 부재 / PublicAccessBlock / SSE / ownership / no Object Lock /
policy Sid / lifecycle 1일 rule)은 provision 후 재개 시 수행해 SUMMARY 에 기록해야 한다.

### Blocker 2 — pair 후보 원본 이미지가 worktree 에 없음 (Task 3)

`fixtures_manifest.json` 은 spike 004 의 `wan_out/*.png` 와 `kpts*/` 를 입력으로
beforeSha256/afterSha256 계산 + 시각 라벨(PASS/FAIL) + afterKeypointSource 를 채워야 한다.
그런데 이 파일들은 **git 미추적(untracked)** 이라 main 체크아웃에만 존재하고 worktree 에는 없다.
worktree 의 `wan_out/` 에는 `journal.json`·`metrics.json` 만 있고 이미지는 **0건**이다.

AWS 권한과 무관한 별도 문제이므로, **권한이 풀려도 Task 3 는 이 상태로는 완료 불가**다.
이미지를 커밋하는 것은 T-31-02(인물 이미지 git 저장 금지)와 정면 충돌하므로,
worktree 가 아닌 main 체크아웃에서 실행하거나 이미지를 별도 경로로 전달하는 방식이 필요하다.
**임의로 판단해 진행하지 않았다** — 판정 대상 이미지를 못 본 채 라벨을 채우면 manifest 가 허구가 되고,
그 manifest 는 31-13 calibration 의 유일한 입력이라 오염이 그대로 임계값으로 전파된다.

## Deviations from Plan

**1. [Rule 3 - 계획 가정과 실측 불일치] SSM `/sunity/motion/pair-id-hmac-keys` 미존재**

- **발견 시점:** Task 1b 사전 실측
- **내용:** 계획서(Task 1 context (c), H2-06)는 versioned HMAC key set 파라미터를 기존 존재로
  가정하지만, `aws ssm get-parameter` 결과 `ParameterNotFound` 였다.
- **조치:** belle 승인을 받아 **신규 생성 분기로 정정**. 생성 자체는 Blocker 1 로 미실행.
- **영향:** 31-07 의 pair 가명화 경로는 이 파라미터 생성 전까지 동작 불가.

**2. [실측에 따른 분기 확정] VisualInputBucket 신규 생성 분기**

- 버킷 미존재(404) 확인 → 기존 policy/lifecycle merge·rollback 경로는 타지 않는다.
- `visual_input_policy_before.json` 은 생성하지 않았다(기존 정책 없음).
- lifecycle before manifest 는 `{"Rules":[]}` 로 기록 예정이나, 실제 put 이 미실행이므로
  **before 파일도 생성하지 않았다** — 미적용 상태에서 before 를 남기면 적용된 것으로 오독될 수 있다.

**3. [계획 대비 축소] Task 3 부분 실행**

- `RESULTS.json` / `fixtures_manifest.json` 미생성 (Blocker 1·2).
- `31-ACCEPTANCE.md` 는 확정 가능한 절만 채우고 나머지는 BLOCKED/placeholder 로 명시.

## Known Stubs

| 항목 | 위치 | 사유 |
|------|------|------|
| 라벨 pair 셋 절 | `31-ACCEPTANCE.md` | Blocker 2 — 원본 이미지 부재. Task 3 재개 시 해소 |
| Display/Training 임계값 | `31-ACCEPTANCE.md` | **의도된 placeholder** — 31-13 harness 산출 (H3-02) |
| Calibration 결과표 | `31-ACCEPTANCE.md` | **의도된 placeholder** — 31-13 기입 |

`infra/visual_input_wave0_lifecycle.json` 은 stub 이 아니라 **정의 완료·미적용** 상태다.

## 재개 조건

1. AWS mutation 권한 부여 또는 사용자 직접 provision → Task 1b 검증 기록
2. pair 후보 이미지 접근 경로 확정 → Task 3 manifest
3. 이후 Task 2 스모크(8콜 상한) → RESULTS.json → 31-ACCEPTANCE 갱신

**phase 진행 판정: 31-01 은 미완료다.** `RESULTS.json` 부재이므로 31-12 배포 게이트의
`blocked` 판정 입력 자체가 없다 — 후속 wave 는 이 상태로 출발하면 안 된다.

## Self-Check: PASSED

- `smoke/privacy_decision.json` — 존재, 스키마 assert 통과 (3키 + 값 검증)
- `31-ACCEPTANCE.md` — 존재, "Training" grep 통과, 임계값 선언 숫자 0 확인
- `infra/visual_input_bucket.json`, `infra/visual_input_wave0_lifecycle.json` — 존재
- 커밋 `d15fb53`, `f17a801`, `63f83a0` — git log 확인
- AWS mutation 0건 / 외부 과금 호출 0건 — 승인 상한 32콜 중 **0콜 사용**
- `.planning` 하위 인물 이미지 0건
- STATE.md / ROADMAP.md 무수정
