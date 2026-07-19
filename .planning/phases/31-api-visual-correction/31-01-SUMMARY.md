---
phase: 31-api-visual-correction
plan: 01
subsystem: privacy-release-gate + image-model-smoke
status: BLOCKED_AT_CHECKPOINT
tags: [privacy, dashscope, s3, release-gate, smoke]
requires:
  - "belle 결정: privacy option-a|option-b + retentionDays 숫자 + 지출 승인 (Task 1)"
  - "belle 승인: VisualInputBucket provision (Task 1b)"
provides: []
affects:
  - "31-07 (CONSENT_VERSION/BLUR_OPTION 배포 상수)"
  - "31-10 / 31-12 (bucket name 단일 출처, blocked 게이트)"
  - "31-13 (fixtures_manifest calibration 입력)"
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified: []
decisions: []
metrics:
  tasks_completed: 0
  tasks_total: 4
  duration: "약 20분 (사전조사만)"
  completed: null
---

# Phase 31 Plan 01: 외부 처리 release gate + 이미지 모델 스모크 Summary

**상태: 미완료 — Task 1 (checkpoint:decision, gate="blocking") 에서 정지.** 산출물 4종
(privacy_decision.json / RESULTS.json / fixtures_manifest.json / 31-ACCEPTANCE.md) 은 아직 없다.
Task 1 은 belle 의 개인정보·보존기간·지출 결정이 입력이며, 계획서가 "승인 전 Task 2 착수 금지"
를 명시하므로 자동 진행하지 않았다.

## 완료된 작업

없음 (코드/산출물 커밋 0). 아래는 checkpoint 를 실행 가능하게 만들기 위한 **읽기 전용 사전조사**다.

## 사전조사 결과 (Task 1 / 1b 결정 입력)

### 1. DashScope / Alibaba Model Studio 데이터 정책

호출 대상 엔드포인트는 spike 004 코드 기준 **국제망(`dashscope-intl.aliyuncs.com`)** 이다
(`.planning/spikes/004-gemini-omni-view-editing/wan_gate_batch.py:24`) — 중국 본토 엔드포인트가 아니다.

공식 문서(`help.aliyun.com/zh/model-studio/data-security`, 2026-07-20 조회) 요약:

| 항목 | 문서 명시 내용 |
|------|----------------|
| 인증 | SOC 2 무보류 의견(unqualified opinion) 통과 |
| 학습 이용 | "귀하의 데이터를 모델 학습에 **절대 사용하지 않음**" 명시 |
| 전송/저장 암호화 | AES-256 |
| 보존 | "관련 법령 요구에 따라 **모델·애플리케이션 호출 시 생성된 데이터를 저장**한다" — **보존 일수는 이 페이지에 미명시**, 서비스 계약서(阿里云百炼服务协议)의 데이터 처리 조항 참조로 위임 |

**미해소 사항 (belle 결정 시 인지 필요):** 국제망(Model Studio International) 전용 영문
data-security 문서 URL 4종이 전부 404 였다. 따라서 **벤더측 보존 일수는 문서로 확정하지 못했다.**
"학습 미사용 + AES-256 + SOC2" 는 확인됐고, "호출 데이터는 법령상 일정 기간 저장됨"도 확인됐으나
그 기간의 숫자는 미확인이다. 이 값은 우리 쪽 `retentionDays` 와 별개(벤더 보존)이며, 고지 문구에
"제3자(Alibaba Cloud Model Studio, 싱가포르)로 전송되며 벤더 정책상 일정 기간 보관됨"으로
기술하는 것이 정직한 표현이다.

### 2. AWS 실측 (읽기 전용, mutation 0)

| 확인 | 결과 |
|------|------|
| `head-bucket sunity-motion-pilot-visual-input` | **404 Not Found — 버킷 미존재** |
| caller identity | `arn:aws:iam::976369350031:user/sunity-motion` (profile `sunity-motion`) |
| SSM `/sunity/motion/dashscope-api-key` | **존재** (SecureString, Version 1) |
| SSM `/sunity/motion/pair-id-hmac-keys` | **ParameterNotFound — 미존재** |

**함의:**
- Task 1b 는 **신규 생성 분기**로 확정된다. 즉 `visual_input_policy_before.json` 과
  `visual_input_wave0_lifecycle_before.json` 은 기존 정책 백업이 아니라 신규 기준값
  (`{"Rules":[]}`) manifest 로 기록된다. Sid merge / rollback 경로는 이번에 타지 않는다.
- option-a/b 어느 쪽이든 **versioned HMAC key set 파라미터를 새로 만들어야 한다**
  (`/sunity/motion/pair-id-hmac-keys`, `{"active":...,"keys":{...}}`). 계획서는 이 파라미터를
  기존 존재로 가정하고 있으나 실제로는 없다 — Task 1b 승인 시 함께 생성 대상에 포함해야 한다.

## Deviations from Plan

계획 대비 실행 편차 없음 (아직 실행 구간에 진입하지 않음). 단, 위 "함의" 2번은 계획서의
암묵 가정과 실측이 어긋난 지점이므로 재개 시 반영이 필요하다.

## 다음 단계

1. belle — Task 1 결정 (option-a|option-b, retentionDays 숫자, 고지 방향, 지출 승인 최대 32콜)
2. belle — Task 1b 승인 (신규 버킷 생성 + 보안 속성 + visual-input/ 1일 lifecycle)
3. Claude — Task 2 스모크 실호출 → Task 3 산출물 3종 + 31-ACCEPTANCE.md

## Self-Check: PASSED

- 생성 주장 파일 없음 (key-files.created 비어 있음) — 검증 대상 0
- AWS mutation 0 / 외부 과금 호출 0 — `git status` clean 확인
