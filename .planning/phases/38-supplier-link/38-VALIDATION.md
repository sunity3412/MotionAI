---
phase: 38
slug: supplier-link
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-26
updated: 2026-09-26
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. 채워짐: 2026-09-26 플래너(14 플랜 · 38 task). 관측/진단 분리 규칙(CLAUDE.md §7 ★)은 SUMMARY 에 적용. 리비전 1(2026-09-26, plan-checker 13건): 38-03 wave 2 · `expo export` 는 플랜 단위 · 38-14-01 REQ-38-3 · 스킵 상태 `⏭` · IAM/Pod 동의/시뮬레이터 행. **리비전 2(2026-09-26, Codex 리뷰 R1~R15 — `38-01-PLAN.md` `## Review Response`):** 38-04 wave 3 · 새 task 38-03-03(순수 규칙)·38-06-03(규칙 파일+REST 스크립트) · claim/lease·권위 가드·v1 ETag·probe 상한·max_split 튜플·판정 순서 행 갱신 · 38-09 baseline/설정 보존/회귀/규칙 probe · 38-12 생성 ESM 행동 테스트 · 38-14 두 라벨.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 (`backend/.venv`, Python 3.14.6) · tsc 5.9 (`npm run typecheck`) · `node --test` (Node 24 type stripping, 신규 의존성 0 — `pickerFailure.test.ts` 선례) |
| **Config file** | none — `backend/tests/conftest.py` 가 `shared/python`·`scripts`·리포 루트를 sys.path 에 주입 |
| **Quick run command** | `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py tests/test_validation.py tests/test_registration_contract.py tests/test_registration_checks.py tests/test_firestore_reference_writers.py tests/test_reference_upload_url_handler.py tests/test_deploy_firestore_rules.py tests/test_pipeline_reference_dispatch.py tests/test_register_reference_pipeline.py tests/test_frame_extractor_probe_duration.py tests/test_self_score_hook.py tests/test_runpod_server.py tests/test_requeue_reference_registrations.py tests/test_snapshot_reference_baseline.py -q` (+ 앱 task 는 `cd app && npm run typecheck` + `node --test <파일>`) |
| **Full suite command** | `cd backend && .venv/bin/python -m pytest tests -q` · `cd app && npm run typecheck` · `node --test app/src/lib/pickerFailure.test.ts app/src/lib/videoDuration.test.ts app/src/constants/supplierCopy.test.ts app/src/lib/supplierRules.test.ts app/src/lib/supplierForm.test.ts` (+ option-2 면 빌드 뒤 `node --test web/supplier/rules.test.mjs`) |
| **Estimated runtime** | quick ≈ 12s(14 파일, 현재 4 파일 1.5s 실측 [확인]); full pytest 소요 [미확인 — 38-08 SUMMARY 가 실측 기록]; typecheck 4.3s [확인]; 예산 38s. `CI=1 npx expo export --platform web` 은 task 게이트가 아니라 플랜 단위 verification 절(38-10/38-11) — 소요 [미확인 — 38-04 T1 이 실측해 MEASUREMENT.md 에 기록], 38s 예산에 넣지 않는다 |

**실행 위치 규칙:** 반드시 `cd backend && .venv/bin/python -m pytest`(worktree 에 .venv 가 없으면 다른 인터프리터 — 메모리 dont-trust-subagent-gate-numbers). 앱은 `cd app && npm run typecheck`.

---

## Sampling Rate

- **After every task commit:** quick run command 중 그 task 가 만진 파일의 테스트 + (앱이면) `npm run typecheck`
- **After every plan wave:** full suite command
- **Before `/gsd-verify-work`:** full suite green + 38-14 E2E(등록 1건 → picker → mode1 done → selfScore) 판정
- **Max feedback latency:** 38 seconds (pytest quick + typecheck)
- **Plan-level only (38s 예산 밖):** `CI=1 npx expo export --platform web` — 38-10/38-11 의 verification 절에서 플랜 끝 1회(소요 초를 38-04 실측값과 비교해 SUMMARY 에); task automated 게이트에는 두지 않는다

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | REQ-38-1, REQ-38-7 | T-38-01-1, T-38-01-6 | upload/v1 두 모양 라운드트립(kind) · legacy/`_archive`/옛 모양/`..` 키 → None · 헤더 게이트 = 옛 서술 0 + 영구 보관 ≥ 1(R15a) | unit | `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py -q` + grep 게이트 | ✅ 확장 | ⬜ pending |
| 38-01-02 | 01 | 1 | REQ-38-3 | T-38-01-5, T-38-01-7 | status enum 별개(+expired) · 코드(+too_large) · 잘못된 CODE → uid 유지 · `selfCheckForReference`·`selfCheckJobId` 3벌 · 비공개 서브문서 계약(R13) · lease/expires 상수 | unit + 3벌 텍스트 대조 | `cd backend && .venv/bin/python -m pytest tests/test_registration_contract.py -q && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-01-03 | 01 | 1 | REQ-38-3, REQ-38-6 | T-38-01-3, T-38-01-4 | enum/bool 위장/길이/동의 필수 거부 | unit | `cd backend && .venv/bin/python -m pytest tests/test_validation.py -q` | ✅ 확장 | ⬜ pending |
| 38-02-01 | 02 | 1 | REQ-38-6 | T-38-02-1 | `classifyDurationMs` 순수 분기(absent/0 → null · 2s tooShort · 91s tooLong) + 앱 배선; 보장 = 클라이언트 fail-open 만(R15c) | node --test ×2 + typecheck | `node --test app/src/lib/videoDuration.test.ts app/src/lib/pickerFailure.test.ts && cd app && npm run typecheck` | ❌ 생성 / ✅ 확장 | ⬜ pending |
| 38-02-02 | 02 | 1 | REQ-38-6 | T-38-02-3 | 낡은 문구 0건 | grep 게이트 | `grep -rn '측면 45°\|2~3m\|정면 우선\|정면으로 다시\|정면으로 촬영\|정면을 기준' app/src docs \| wc -l` == 0 | — | ⬜ pending |
| 38-02-03 | 02 | 1 | REQ-38-5 | T-38-02-2 | 표시만, 리터럴 0 · 시뮬레이터 실물(스크린샷 2장 + UI 트리; OTA/EAS 는 선언된 이월) | typecheck + grep + simulator | `cd app && npm run typecheck && grep -c "profileCopy.instructorCode" "src/app/(tabs)/profile.tsx" && test -s ../.planning/phases/38-supplier-link/38-02-simulator-profile.png && test -s ../.planning/phases/38-supplier-link/38-02-simulator-tips.png` | — | ⬜ pending |
| 38-03-01 | 03 | 2 | REQ-38-8 | T-38-03-1 | 7항목·고정 각도 0 · R7 "등록 정보로 보관" · R11 고지 · R6 "사람이 확인" | doc grep | `grep -c '^## ' docs/supplier-guide.md` == 7 · `2~3m\|45°` == 0 · R7/R11/R6 grep | — | ⬜ pending |
| 38-03-02 | 03 | 2 | REQ-38-8, REQ-38-4 | T-38-03-2 | md ↔ copy 글자 동일 · row.fail 7코드(too_large) = analysis.ts 조인 규칙 · R7/R11 정직 문구 · `expired`·`self.note` 행 · 크레딧/결제 0 | node --test | `node --test app/src/constants/supplierCopy.test.ts && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-03-03 | 03 | 2 | REQ-38-3, REQ-38-4, REQ-38-6 | T-38-03-3, T-38-03-4 | 호스팅 무관 순수 규칙(행 상태·자기 점수 분기·실패/만료 문구·401/403/offline 매핑·업로드 전이·폼 검증 경계·동의·요청 조립) — 공용 fixture 1벌, firebase/react import 0 (R14) | node --test ×2 + typecheck | `node --test app/src/lib/supplierRules.test.ts app/src/lib/supplierForm.test.ts && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-04-01 | 04 | 3 | REQ-38-3 | T-38-SC, T-38-04-1, T-38-04-4 | lockfile 외 변경 0, 팝업만 · 후보 (2) probe 존재(redirect/innerHTML 0) · `test_account:` 명시 | export exit + typecheck + grep | `grep -q react-native-web app/package.json && cd app && npm run typecheck && test -f ../.planning/phases/38-supplier-link/38-04-probe/probe.js` | — | ⬜ pending |
| 38-04-02 | 04 | 3 | REQ-38-3 | T-38-04-2, T-38-04-3 | localhost Authorized domain 전용 · 같은 4가지 × 2 후보 · 테스트 계정 uid = `uploads/{uid}` 대조(R15d) | **manual** (belle 8 항목) + `aws s3 ls` | — | — | ⬜ pending |
| 38-04-03 | 04 | 3 | REQ-38-3 | — | 결정 기록(후보 (2) 행은 probe 실측만, R14) → 미선택 트랙 스킵을 파일로 · `selfScoreMin` 기록(≠90 이면 supplierRules.ts 상수 한 줄) | **manual** (checkpoint:decision) + grep | `grep -q 'option-1\|option-2' 38-04-MEASUREMENT.md && grep -q selfScoreMin: 38-04-MEASUREMENT.md` + 미선택 SUMMARY 존재 | — | ⬜ pending |
| 38-05-01 | 05 | 2 | REQ-38-4 | T-38-05-1, T-38-05-4 | 순서 low_confidence → multiple_people → no_standing_start(R6) · 측정 가능성 분리 · 사람 수 2/10·3/10·4/10 순서 무관(R15b) · crouch PROXY 반례 박제 · 상수 복제 0 | unit (합성 강제) | `cd backend && .venv/bin/python -m pytest tests/test_registration_checks.py tests/test_hold_height.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-05-02 | 05 | 2 | REQ-38-4 | T-38-05-2 | 사이드카 0, estimate 무회귀 | unit (mock N=0/2) | `cd backend && .venv/bin/python -m pytest tests/test_rtmw_engine.py tests/test_rtmw_engine_rot180.py -q` | ✅ 확장 | ⬜ pending |
| 38-06-01 | 06 | 2 | REQ-38-1, REQ-38-3, REQ-38-4 | T-38-06-4, T-38-06-5, T-38-06-8, T-38-06-9, T-38-06-10 | 공개+비공개 batch `create()` · `ref-` 가드 · flat 검증 · 동의 서버 시각 · claim CAS(동시 2 = 1) · lease 만료 재claim · stale job no-op · `self_check_authorized` 4케이스 · pending 전 완료 스킵 | unit (phase31 FakeFirestore) | `cd backend && .venv/bin/python -m pytest tests/test_firestore_reference_writers.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-06-02 | 06 | 2 | REQ-38-1, REQ-38-3, REQ-38-5 | T-38-06-1, T-38-06-2, T-38-06-3, T-38-06-6 | 토큰 uid 만 · env/SSM 부재 = 403 · upload 키만 서명 → create(`uploadExpiresAt`) · create 실패 = URL 미응답(R4) | unit (monkeypatch) | `cd backend && .venv/bin/python -m pytest tests/test_reference_upload_url_handler.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-06-03 | 06 | 2 | REQ-38-4, REQ-38-3 | T-38-06-9, T-38-06-10, T-38-06-11 | 규칙: `reference/{refId}`·`versions`·`private/{doc}` 본인만 · 표식 create/update 거부 · REST `projects:test` 케이스 ≥ 12 · 스크립트 순수 빌더(토큰 미출력) · `--release` 미실행 | unit + grep (+ 선택 라이브 `--test`) | `cd backend && .venv/bin/python -m pytest tests/test_deploy_firestore_rules.py -q` + firestore.rules grep 게이트 | ❌ 생성(task 내) | ⬜ pending |
| 38-07-01 | 07 | 3 | REQ-38-1 | T-38-07-1, T-38-07-6, T-38-07-10 | kind upload 만 · registering+uid 일치만 · Pod 부재 = queued 쓰기 성공 시 정상 반환, 쓰기 실패 = raise(R4) · claim 뒤 위임 1회(동시 2 = 1, R3) · v1 이벤트 스킵 · uploads/ 무접촉 | unit | `cd backend && .venv/bin/python -m pytest tests/test_pipeline_reference_dispatch.py tests/test_pipeline_dispatch.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-07-02 | 07 | 3 | REQ-38-2, REQ-38-4 | T-38-07-2, T-38-07-3, T-38-07-4, T-38-07-7, T-38-07-8, T-38-07-9 | head_object 크기(too_large) · copy→v1 `CopySourceIfMatch` + ETag 재확인 · probe 길이 거부 추출 전 + `end_s` 캡(R9) · 7 실패 코드 합성 강제 · **실제 `max_split` 튜플**(R1) · job 가드 · begin→doc→copy(R8) · 재PUT 불변 · stale job 쓰기 0 · 상수만 | unit (mock engine, fake s3 store) | `cd backend && .venv/bin/python -m pytest tests/test_register_reference_pipeline.py tests/test_frame_extractor_probe_duration.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-08-01 | 08 | 4 | REQ-38-4, REQ-38-2 | T-38-08-1, T-38-08-2, T-38-08-3, T-38-08-6 | 훅 = 기준 doc 권위 가드(위조·타공급자·stale·pending 전 = 0회, R2/R8) · 라우트 jobId 전달/자체 claim(409) · upload 키만 · /analyze 무접촉 | unit + TestClient | `cd backend && .venv/bin/python -m pytest tests/test_self_score_hook.py tests/test_runpod_server.py -q` | ❌ 생성 / ✅ 확장 | ⬜ pending |
| 38-08-02 | 08 | 4 | REQ-38-2 | T-38-08-4, T-38-08-5, T-38-08-6, T-38-08-7 | 단일 where ×3 · claim 경유(2회 = POST 1회, R3) · `--reclaim-stale` · `--sweep-expired`(객체 있음 claim+POST / 없음 expired, R4) · 토큰 미출력 | unit | `cd backend && .venv/bin/python -m pytest tests/test_requeue_reference_registrations.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-09-01 | 09 | 5 | REQ-38-1, REQ-38-2 | T-38-09-4, T-38-09-5, T-38-09-6, T-38-09-7 | **첫 쓰기 전** legacy baseline(raw·angles 해시·ETag·표본 3, R10) + 5함수 설정/코드 zip 보존(R12) + 규칙 원본 → 최소 권한 정책 · uid 마스킹 · layer 범위 평가 | pytest + `sam validate --lint` + grep | `cd backend && .venv/bin/python -m pytest tests/test_snapshot_reference_baseline.py -q && sam validate --lint && grep -c "ReferenceUploadUrlFunction\|ReferenceUploadUrlLogGroup" template.yaml` | ❌ 생성(task 내) | ⬜ pending |
| 38-09-02 | 09 | 5 | REQ-38-1 | T-38-09-1, T-38-09-7 | changeset + 규칙 diff belle 검토(`hold-rules` 분리 가능) | **manual** (checkpoint) | — | — | ⬜ pending |
| 38-09-03 | 09 | 5 | REQ-38-1, REQ-38-7, REQ-38-2 | T-38-09-2, T-38-09-3, T-38-09-6, T-38-09-7, T-38-07-7 | 설정 diff(허용 차이 외 0) · 기존 API 회귀 401×3(+토큰 200 형상) · baseline 재diff 0 · 알림 2항목 · lifecycle 없음 · 401 스모크 · IAM(두 접두사) · 규칙 `--test` 12/12 → `--release` → 라이브 probe(타인 private DENY·위조 표식 DENY) | AWS 읽기 + curl + REST + 웹 SDK probe | 알림 length == 2 · `NoSuchLifecycleConfiguration` · `curl … /reference/upload-url → 401` · `snapshot_reference_baseline.py --diff` exit 0 · `grep -c permission-denied CHANGESET.md` ≥ 2 | — | ⬜ pending |
| 38-10-01 | 10 | 4 | REQ-38-3, REQ-38-4 | T-38-10-2 | 규칙 import 만(재정의 0, R14) · 공개 구독 단일 where · 상세용 비공개 doc 훅 1건(R13) | typecheck + grep | `cd app && npm run typecheck && grep -q "from './supplierRules'" src/lib/supplierMotions.ts && grep -q "'private', 'registration'" src/lib/supplierMotions.ts` | — | ⬜ pending |
| 38-10-02 | 10 | 4 | REQ-38-3, REQ-38-5 | T-38-10-1, T-38-10-2, T-38-10-4 | 팝업만 · 단일 where · 쓰기 0 · 리터럴 색 0 · `expired` 행 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c 'supplierCopy\.' src/app/supplier/index.tsx` ≥ 20 + hex 리터럴 0 | — | ⬜ pending |
| 38-10-03 | 10 | 4 | REQ-38-4 | T-38-10-2, T-38-10-3 | `{joints}` textContent 치환 · 실패 상세 = 비공개 doc(R13) · 만료 패널(R4) · 재분석 한 줄 + 고지(R11) | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c "FailurePanel\|DonePanel" src/app/supplier/index.tsx` ≥ 2 + `useSupplierRegistrationPrivate\|expiredCopy\|selfCheckNote` ≥ 3 | — | ⬜ pending |
| 38-11-01 | 11 | 5 | REQ-38-3, REQ-38-6 | T-38-11-1, T-38-11-2 | 38-03 폼 규칙 import 만(R14) · 길이·형식·서 있는 시작 차단, fail-open · helper = R7 정직 문구 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c PickErrorDialog src/app/supplier/upload.tsx` ≥ 1 && `grep -q "from '../../lib/supplierForm'"` | — | ⬜ pending |
| 38-11-02 | 11 | 5 | REQ-38-3 | T-38-11-3, T-38-11-5, T-38-11-6 | 필수 3 만 제출 · Firestore 쓰기 0 · `mapPresignFailure`/`uploadOutcomeNext` 소비(R14) · 재시도 = 새 refId(R4) | typecheck + grep | `cd app && npm run typecheck && grep -c "from 'firebase/firestore'" src/app/supplier/upload.tsx` == 0 && `mapPresignFailure\|uploadOutcomeNext` ≥ 2 | — | ⬜ pending |
| 38-11-03 | 11 | 5 | REQ-38-8 | — | md 동일 문구 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c 'supplierCopy.guide' …` ≥ 7 + `/supplier/guide` 링크 ≥ 2 | — | ⬜ pending |
| 38-12-01 | 12 | 4 | REQ-38-3, REQ-38-5 | T-38-12-1, T-38-12-3, T-38-12-4, T-38-12-7 | CDN 버전 고정 · 리다이렉트 0 · config gitignore · `rules.js` 생성(type-strip + specifier 재작성) + `supplier.js` 규칙 재구현 0(R14) | build + `node --check` ×2 + grep | `node app/scripts/build-supplier-web.mjs && node --check web/supplier/supplier.js && node --check web/supplier/dist/rules.js && grep -q "from './rules.js'" web/supplier/supplier.js` | — | ⬜ pending |
| 38-12-02 | 12 | 4 | REQ-38-3, REQ-38-6 | T-38-12-5, T-38-12-6 | Firestore 쓰기 0 · 즉시 검사 = rules.js `validateFile`/`buildRequest`/`mapPresignFailure`/`uploadOutcomeNext` 소비 | `node --check` + grep | `node --check web/supplier/supplier.js && grep -c 'setDoc\|addDoc\|updateDoc' …` == 0 && `buildRequest(\|mapPresignFailure(\|uploadOutcomeNext(` ≥ 3 | — | ⬜ pending |
| 38-12-03 | 12 | 4 | REQ-38-4, REQ-38-8 | T-38-12-2, T-38-12-7, T-38-12-8 | innerHTML 0 · `SELF_SCORE_OK_MIN` import 만 · 비공개 doc 상세 구독(R13) · 만료 패널(R4) · 고지(R11) · **생성 ESM 행동 테스트**(401/403/offline · 길이 경계 · 취소/재시도 · 행 매핑 7상태, R14) | build + node --test + grep | `node app/scripts/build-supplier-web.mjs && node --test web/supplier/rules.test.mjs && grep -c innerHTML …` == 0 | ❌ 생성(task 내) | ⬜ pending |
| 38-13-01 | 13 | 6 | REQ-38-3 | T-38-13-1, T-38-13-3, T-38-13-6 | public block · OAC 정책 · 읽기 먼저 멱등 · 재사용 리소스는 업데이트 전 원본 보존(복원 롤백) / 신규는 삭제 롤백 · 과금 관측값(`[미확인]` 허용, Free plan 단정 금지)(R12) | curl + AWS 읽기 | `curl -sI https://<domain>/ → 200` + before-파일 존재(재사용 시) | — | ⬜ pending |
| 38-13-02 | 13 | 6 | REQ-38-3 | T-38-13-2 | 정확한 도메인만 | **manual** (belle 콘솔) | — | — | ⬜ pending |
| 38-13-03 | 13 | 6 | REQ-38-3, REQ-38-5, REQ-38-8 | — | 실기기 E2E + Figma 대조 | **manual** (belle) | — | — | ⬜ pending |
| 38-14-01 | 14 | 7 | REQ-38-3 | — | uid 제공 · `pod:go <GPU>` 동의(단가 조회값) · 두 라벨(`structural_check_stand_in` / `success_1_independent_user`, R15e) | **manual** (정은지/belle) + grep | `grep -q 'pod_consent:' 38-14-E2E.md && grep -q 'success_1_independent_user:' 38-14-E2E.md` | — | ⬜ pending |
| 38-14-02 | 14 | 7 | REQ-38-2 | T-38-14-2, T-38-14-3, T-38-07-7 | `pod_consent` 뒤에만 기동 · GPU 한 종류 · commitSha 일치 · SSM 롤백(get-parameter-history) · IAM `uploads/`+`reference/` probe · requeue 2회(두 번째 0 POST, R3) + `--sweep-expired` · 첫 requeue 뒤 baseline 재diff 0(R10) | 명령 원문 + grep + `--diff` | `snapshot_reference_baseline.py --diff … --offline after-requeue.json` exit 0 && `grep -q 'skip(claim)' E2E.md` && git log origin/main..HEAD 비어 있음 | — | ⬜ pending |
| 38-14-03 | 14 | 7 | REQ-38-2, REQ-38-4 | T-38-14-4 | Success ① ③ 사람 판정 — ① 은 belle 아닌 사람 완주 때만, ③ 은 재분석 일관성 의미(R11/R15e) | **manual** (belle/정은지) | — | — | ⬜ pending |
| 38-14-04 | 14 | 7 | REQ-38-2, REQ-38-4 | T-38-14-1, T-38-14-6 | RuntimeError 0 · v1 키/ETag · 재PUT 불변 실물(R5) · selfCheckJobId = jobId 연결 · E2E 뒤 baseline 재diff 0 + 표본 id 비겹침(R10) · 두 라벨 · Pod down | 로그 grep + AWS 읽기 + `--diff` | `aws ssm get-parameter … runpod-pod-expected == down && test -f infra/legacy-reference-after-e2e.json && grep -q 'videoETag' E2E.md` | — | ⬜ pending |
*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⏭ skipped-by-decision(38-04 Task 3 (d) 가 미선택 트랙 행에 표시 — 38-10-01~03 · 38-11-01~03 또는 38-12-01~03)* · 리비전 2 는 38-03-03 · 38-06-03 행을 더하고 claim/가드/v1/probe/baseline 행을 갱신했다.

---

## Wave 0 Requirements

별도 Wave 0 플랜 없음 — 아래 테스트 파일은 **그 파일을 검증하는 task 안에서 RED 먼저** 만든다(`tdd="true"` task). 실행 위치 `cd backend && .venv/bin/python -m pytest`.

- [ ] `backend/tests/test_registration_contract.py` — REQ-38-3 계약 3벌 대조(+expired·too_large·private·selfCheckJobId) (38-01-02)
- [ ] `app/src/lib/videoDuration.test.ts` — REQ-38-6 duration 분기 자체(R15c) (38-02-01)
- [ ] `backend/tests/test_registration_checks.py` — REQ-38-4 합성 4형 (38-05-01)
- [ ] `backend/tests/test_firestore_reference_writers.py` — REQ-38-1/2 writer 13종 + claim CAS + 권위 가드(phase31 FakeFirestore 재사용) (38-06-01)
- [ ] `backend/tests/test_reference_upload_url_handler.py` — REQ-38-1/3 (38-06-02)
- [ ] `backend/tests/test_deploy_firestore_rules.py` + `backend/tests/firestore_rules_cases.json` — 규칙 REST 빌더 + `projects:test` 케이스 ≥ 12 (38-06-03)
- [ ] `backend/tests/test_pipeline_reference_dispatch.py` — REQ-38-1 Pod down/up (38-07-01)
- [ ] `backend/tests/test_register_reference_pipeline.py` — REQ-38-2/4 7 코드 + happy(실제 max_split) + v1 ETag + 재PUT 불변 + stale (38-07-02)
- [ ] `backend/tests/test_frame_extractor_probe_duration.py` — R9 probe (38-07-02)
- [ ] `backend/tests/test_snapshot_reference_baseline.py` — R10 해시/diff 순수 함수 (38-09-01)
- [ ] `backend/tests/test_self_score_hook.py` — REQ-38-4 (38-08-01)
- [ ] `backend/tests/test_requeue_reference_registrations.py` — REQ-38-2 (38-08-02)
- [ ] `app/src/constants/supplierCopy.test.ts` — REQ-38-8 md 동일성 (38-03-02)
- [ ] `app/src/lib/supplierRules.test.ts` · `app/src/lib/supplierForm.test.ts` · `app/src/lib/supplierFixtures.ts` — 호스팅 무관 순수 규칙 + 공용 fixture (38-03-03, R14)
- [ ] `web/supplier/rules.test.mjs` — option-2 일 때 생성 ESM 행동 테스트 (38-12-03, R14)
- [x] 확장만: `test_s3keys.py` · `test_validation.py` · `test_rtmw_engine.py` · `test_runpod_server.py` · `pickerFailure.test.ts`
- [x] 프레임워크 설치 없음(기존 pytest/tsc/node --test)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 웹 export 번들 **과 후보 (2) probe** 에서 Google 팝업 로그인 · .mov 선택 · presigned PUT · onSnapshot (같은 4가지 × 2, 테스트 계정 uid 대조) | REQ-38-3 | Google 계정 + 팝업은 사람 손; localhost 만 Authorized domain | 38-04 Task 2 (시뮬 Safari 8줄 ○/×, R14/R15d) |
| 호스팅 후보 결정 | — (Claude's Discretion → belle) | 측정값을 보고 belle 이 고른다 | 38-04 Task 3 결정표 |
| CFN changeset 검토(layer 재바인딩 5함수 + 함수 단위 롤백 + 규칙 diff) | REQ-38-1 | `sam deploy` 금지 규칙의 예외 승인; 규칙 배포도 같은 승인(`hold-rules` 분리 가능) | 38-09 Task 2 |
| Firestore 규칙 배포 폴백(REST 권한 거부 시 콘솔 붙여넣기) | REQ-38-4 | Rules REST `--release` 가 403 이면 콘솔만 남는다 | 38-09 Task 3 F |
| Firebase Authorized domains | REQ-38-3 | 콘솔 전용(CLI 없음) | 38-13 Task 2 |
| 실기기 폰 브라우저 A-1~A-6 + Figma 대조(D-22) | REQ-38-3/5/8 | 실기기 렌더·팝업·파일 선택은 사람만 | 38-13 Task 3 |
| 정은지 uid 제공(닭-달걀) | REQ-38-3 | 로그인 1회 뒤 uid 는 사람이 전달 | 38-14 Task 1 |
| Pod 기동 동의 `pod:go <4090\|L4>`(공용 유료 계정) | REQ-38-2 | 비용 결정은 belle — 실행자는 단가 조회값 × 예상 시간만 제시 | 38-14 Task 1 how-to-verify 4 |
| Success ① picker 노출 + mode1 완주(belle 아닌 사람 — 대역은 구조 검증만, R15e) · ③ selfScore 판정(재분석 일관성 의미, R11) | REQ-38-2/4 | Pod(GPU) + 앱 실기기 + belle 판정(통과선 belle) | 38-14 Task 3·4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are checkpoints (checkpoint task 는 Manual-Only 표에)
- [x] Sampling continuity: 자동 검증 없는 task 가 3개 연속으로 오지 않는다(체크포인트 사이에 자동 task 배치)
- [x] Wave 0 covers all MISSING references(각 task 내 RED 먼저)
- [x] No watch-mode flags
- [x] Feedback latency < 38s (quick pytest ≈ 12s + typecheck 4.3s; `expo export` 와 option-2 빌드+ESM 테스트는 플랜 단위라 예산 밖)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (플래너 초안 2026-09-26 · 리비전 1 반영 · 리비전 2 = Codex 리뷰 R1~R15 반영 — plan-checker 재검토 뒤 승인)
