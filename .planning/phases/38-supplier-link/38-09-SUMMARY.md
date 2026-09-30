---
phase: 38-supplier-link
plan: 09
subsystem: infra
tags: [sam, cloudformation, lambda, http-api, s3-notification, s3-lifecycle, ssm, firestore-rules]

requires:
  - phase: 38-supplier-link (38-06)
    provides: functions/reference-upload-url · firestore.rules(reference 좁힘 · private 본인만 · 표식 거부) · deploy_firestore_rules.py
  - phase: 38-supplier-link (38-07)
    provides: pipeline POD_EXPECTED_PARAM 읽기 · reference/ 키 분기
  - phase: 38-supplier-link (38-08)
    provides: Pod /register-reference(이 플랜에선 배포 안 함)
provides:
  - "라이브 POST /reference/upload-url (무토큰 401 + CORS) — ReferenceUploadUrlFunction · 역할 · 로그그룹 30일"
  - "pipeline env POD_EXPECTED_PARAM + ssm:GetParameter(runpod-pod-expected)"
  - "SSM /sunity/motion/supplier-uids = belle uid:BELLE (정은지 추가 = SSM put 만)"
  - "버킷 알림 2항목(uploads/ + reference/ → 같은 큐) · 수명주기 없음(uploads/ 영구 보관, D-17)"
  - "Firestore 규칙 38-06 판 라이브(belle 콘솔 게시) + 라이브 probe 6/6"
  - "snapshot_reference_baseline.py (--out / --diff / --offline) — 38-14 T2 가 소비"
  - "롤백 원본: lambda-before.json + /Users/Shared/sunity-motion-rollback/38-09/ zip 7개 · notification-before · lifecycle-before · firestore-rules-before"
affects: [38-13 (배포된 라우트로 폼 실물 검증), 38-14 (Pod 배포 · requeue · --offline diff · Pod 자격 대조)]

tech-stack:
  added: []
  patterns:
    - "라이브 스택 = 32-16 브리지 템플릿 + 델타(template-38-09-deploy.yaml) — Phase 31 Visual 리소스를 같이 올리지 않기 위해. 정본 template.yaml 에도 같은 델타"
    - "교체-전체 S3 설정(put-bucket-notification) = 원본 저장 → 전 항목을 한 번에 put → get 검증"

key-files:
  created:
    - backend/scripts/snapshot_reference_baseline.py
    - backend/tests/test_snapshot_reference_baseline.py
    - backend/template-38-09-deploy.yaml
    - .planning/phases/38-supplier-link/38-09-CHANGESET.md
    - .planning/phases/38-supplier-link/infra/legacy-reference-baseline.json
    - .planning/phases/38-supplier-link/infra/lambda-before.json
    - .planning/phases/38-supplier-link/infra/lambda-after.json
    - .planning/phases/38-supplier-link/infra/firestore-rules-before.rules
    - .planning/phases/38-supplier-link/infra/firestore-rules-live.rules
    - .planning/phases/38-supplier-link/infra/notification-before.json
    - .planning/phases/38-supplier-link/infra/notification-after.json
    - .planning/phases/38-supplier-link/infra/lifecycle-before.json
  modified:
    - backend/template.yaml
    - backend/README.md
    - backend/scripts/intake_clips.py

key-decisions:
  - "38-09: 정본 template.yaml 대신 32-16 브리지 + Phase 38 델타(template-38-09-deploy.yaml)로 배포 — 정본으로 가면 Phase 31 Visual 스택(Default 없는 파라미터 5개)이 같이 올라간다"
  - "38-09: layer 를 옛 ARN 으로 고정하지 않음 — 5함수 전부 :21 로 재바인딩, 대신 배포 뒤 회귀 + 함수 단위 롤백(zip 보존)으로 반경을 닫음. :16 은 CFN 이 지웠고 zip 으로 재발행 가능"
  - "38-09: Firestore 규칙은 belle 선택 (B) 콘솔 게시 — Admin SA 에 Rules Admin IAM 을 주지 않음. 사전 시험(projects:test 12)은 못 돌렸고 라이브 probe 6/6 이 유일한 검증"
  - "38-09: GET /reference 500(10초 타임아웃)은 배포 전(08-31)부터 있던 것 · 앱 미사용 → 롤백 안 함, 미결로 남김"

requirements-completed: [REQ-38-1, REQ-38-7, REQ-38-2]

duration: ~2h20m (07:42 → 10:01 KST, belle 체크포인트 대기 2회 포함)
completed: 2026-09-30
---

# Phase 38 Plan 09: 인프라 배포 — 공급자 업로드 라우트 · 버킷 알림/수명주기 · 규칙 Summary

**라이브에 `POST /reference/upload-url`(401+CORS)과 pipeline 의 pod-expected 읽기를 CFN changeset(belle 승인)으로 올리고, 버킷 알림을 `uploads/`+`reference/` 2항목으로, `uploads/` 를 영구 보관으로 바꿨으며, belle 이 콘솔로 게시한 38-06 규칙이 라이브 = 리포 바이트 동일 · probe 6/6 통과다.**

## 관측 (승계 가능)

### 배포 전 보존 — 커밋 `61a255e2` (어떤 쓰기보다 앞) [확인]
- legacy `ref-*` 11 doc raw 필드 + `reference/_release` 포인터 + S3 ETag 11 + 저장 분석 표본 3건 → `infra/legacy-reference-baseline.json`.
- 5함수 설정(env 키 이름만) → `infra/lambda-before.json`, 코드 zip 5 + layer zip 2 → `/Users/Shared/sunity-motion-rollback/38-09/`.
- 배포 전 라이브 규칙 = `debb86bf` 판(diff 0) → `infra/firestore-rules-before.rules`.
- `test_snapshot_reference_baseline.py` 10 passed (이 세션 재실행).

### CFN (belle "승인 — 배포 진행") [확인]
- 스택 `sunity-motion-pilot` `UPDATE_COMPLETE`, 실패 이벤트 0. 라우트 5개(새 `POST /reference/upload-url` 포함).
- 6함수 모두 layer `:21`. `:16` 은 CFN 정리 단계에서 삭제(예고한 대로).
- 설정 diff: layer · CodeSha256 · pipeline env `POD_EXPECTED_PARAM` 만. Memory·Timeout·Runtime·Handler·Role·다른 env 키 변화 0.
- 무토큰 401 × 4 (`/reference/upload-url` · `/upload-url` · `/reference` · `/playback-url`). `Origin` 헤더 POST → 401 + `access-control-allow-origin: *`, preflight 204.
- 토큰 회귀: `POST /upload-url` 200 · `POST /playback-url` 200 · **`GET /reference` 500** (아래 미결).
- baseline 재diff `differences: 0`, exit 0.

### 버킷 [확인]
- 알림 `QueueConfigurations` 2개 — `uploads/`(원본 Id 그대로) · `reference-supplier-link` `reference/`, 같은 큐.
- 수명주기 `NoSuchLifecycleConfiguration`. README · intake_clips 의 '30일' 0건.

### IAM simulate [확인 — 로컬 `sunity-motion` 사용자 기준]
- PutObject/GetObject × `uploads/*` · `reference/*/v1` · `reference/*/upload` 전부 allowed. Pod 자격이 같은 사용자인지는 [미확인 — 38-14 T2 3-b].

### Firestore 규칙 (belle 선택 B — 콘솔 게시) [확인]
- belle: "게시했어". `--current` → release `rulesets/18587bf6-155f-43ae-aded-fdafdd7eabda`, updateTime 2026-09-30T00:58:37Z.
- 라이브 규칙 = 리포 `firestore.rules` **바이트 동일**(sha256 `b5b63131…48b8` 양쪽 같음, 공백 차이도 없음).
- 라이브 probe 6/6: A 본인 private get 200 · B 가 A 의 private get **403 PERMISSION_DENIED** · B 공개 doc get 200 · B 가 `selfCheckForReference` 넣은 create **403 PERMISSION_DENIED** · 표식 없는 create 200 · 본인 delete 200.
- 임시 doc 3개 전후 모두 없음 확인. 임시 Auth 유저 `regress38` · `regress38A` · `regress38B` 삭제.

## 미결

1. **`GET /reference` 500 (10초 타임아웃)** — 배포 전 08-31 호출 3건도 같은 10초 타임아웃 [확인 CloudWatch]. 인증 통과한 호출만 10초를 채운다(무토큰 401 은 2 ms) [확인]. 앱은 이 경로를 부르지 않는다(기준 목록 = Firestore `onSnapshot`) [확인 grep]. 이 플랜에서 고치지 않았다 — 오케스트레이터가 belle 에게 이미 보고. 플랜 A-2 의 "토큰 3 × 200" 중 이 한 줄은 미충족.
2. **Pod 코드(38-08 `/register-reference`) 미배포** — Pod 꺼짐(`runpod-pod-expected = down`). 그 사이 등록 영상은 pipeline 이 `queued` 로 두는 설계 [추정 — 라이브 미관측]. 38-14 에서 배포 + requeue.
3. **`reference/` 알림 라이브 도착 관측 없음** — 첫 공급자 업로드(38-13) 때 확인 [미확인].

## 진단 (승계 전 재검증 대상)

- `GET /reference` 500 원인: `list_reference_motions()` 가 `reference` 컬렉션 전체를 큰 필드째 읽어 256 MB·10초 안에 못 끝나는 것으로 보인다 [추정 — 컬렉션 크기·응답 크기는 안 쟀다].

## 공급자 페이지 Figma 시안 (2026-09-30, 이 플랜 밖 기록)

- belle 이 공급자 화면 디자인을 요청했고, 오케스트레이터가 Figma 에 직접 그렸다: fileKey `jrdI7kp245HkPfLB0nclsz`, 섹션 `282:506` "Phase 38 - 공급자 페이지 시안 (Claude, 2026-09-30)" — 화면 11개 + 컴포넌트 5개 + UI-SPEC 과 다른 점 8개를 적은 노트 프레임.
- 글꼴은 Noto Sans KR 로 그렸다 — Figma MCP 환경에 Pretendard 가 없다.
- `/supplier` 코드를 38-13 전에 이 시안에 맞출지는 **belle 결정 대기**.

## Deviations from Plan

1. **[Rule 3 - Blocking] 배포 템플릿을 32-16 브리지 + 델타로** — 정본 `template.yaml` 로 changeset 을 만들면 Phase 31 Visual 스택이 Default 없는 파라미터 5개와 함께 올라간다. 라이브 원본 템플릿 = 32-16 브리지(구조 차이 0)를 확인하고 `backend/template-38-09-deploy.yaml` 로 배포. 정본에도 같은 델타. 커밋 `d50cf39f`.
2. **[Rule 3] `sam build --use-container --skip-pull-image --no-cached`** — 이미지 pull 에서 20분 멈춰 로컬 이미지로 빌드. 네이티브 빌드는 하지 않았다.
3. **규칙 배포 경로 (B) 콘솔** — 플랜 F 의 `--test`/`--release` 대신 belle 선택. 사전 12 케이스 시험 없음.
4. **라이브 probe 를 웹 SDK(node) 대신 Firestore REST + ID 토큰으로** — 규칙 평가는 같다. probe 에 6번째 줄(본인 delete)을 더했다.
5. **임시 Auth 유저 삭제에 A-2 의 `regress38` 도 포함** — 이전 실행기가 만든 일회용 유저.

## Commits

| 단계 | 커밋 |
|---|---|
| T1 배포 전 보존 | `61a255e2` |
| T1 template · 브리지 · changeset 문서 | `d50cf39f` |
| T3 A~E 배포·검증·버킷·문서·IAM | `c8f6607f` (STATE `f34fbbca`) |
| T3 F 규칙 라이브 대조 + probe | `6989f64a` |

## Self-Check: PASSED
- 파일: CHANGESET · infra 8개 · snapshot 스크립트/테스트 · template-38-09-deploy.yaml 존재 확인.
- 커밋 `61a255e2` · `d50cf39f` · `c8f6607f` · `f34fbbca` · `6989f64a` git log 에 있음.
