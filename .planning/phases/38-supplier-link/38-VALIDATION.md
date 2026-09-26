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

> Per-phase validation contract for feedback sampling during execution. 채워짐: 2026-09-26 플래너(14 플랜 · 38 task). 관측/진단 분리 규칙(CLAUDE.md §7 ★)은 SUMMARY 에 적용. 리비전 1(2026-09-26, plan-checker 13건): 38-03 wave 2 · `expo export` 는 플랜 단위 · 38-14-01 REQ-38-3 · 스킵 상태 `⏭` · IAM/Pod 동의/시뮬레이터 행.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 (`backend/.venv`, Python 3.14.6) · tsc 5.9 (`npm run typecheck`) · `node --test` (Node 24 type stripping, 신규 의존성 0 — `pickerFailure.test.ts` 선례) |
| **Config file** | none — `backend/tests/conftest.py` 가 `shared/python`·`scripts`·리포 루트를 sys.path 에 주입 |
| **Quick run command** | `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py tests/test_validation.py tests/test_registration_contract.py tests/test_registration_checks.py tests/test_firestore_reference_writers.py tests/test_reference_upload_url_handler.py tests/test_pipeline_reference_dispatch.py tests/test_register_reference_pipeline.py tests/test_self_score_hook.py tests/test_runpod_server.py tests/test_requeue_reference_registrations.py -q` (+ 앱 task 는 `cd app && npm run typecheck` + `node --test <파일>`) |
| **Full suite command** | `cd backend && .venv/bin/python -m pytest tests -q` · `cd app && npm run typecheck` · `node --test app/src/lib/pickerFailure.test.ts app/src/constants/supplierCopy.test.ts app/src/lib/supplierRules.test.ts app/src/lib/supplierForm.test.ts` |
| **Estimated runtime** | quick ≈ 10s(11 파일, 현재 4 파일 1.5s 실측 [확인]); full pytest 소요 [미확인 — 38-08 SUMMARY 가 실측 기록]; typecheck 4.3s [확인]; 예산 38s. `CI=1 npx expo export --platform web` 은 task 게이트가 아니라 플랜 단위 verification 절(38-10/38-11) — 소요 [미확인 — 38-04 T1 이 실측해 MEASUREMENT.md 에 기록], 38s 예산에 넣지 않는다 |

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
| 38-01-01 | 01 | 1 | REQ-38-1, REQ-38-7 | T-38-01-1 | legacy/`_archive`/`..` 키 → None | unit | `cd backend && .venv/bin/python -m pytest tests/test_s3keys.py -q` | ✅ 확장 | ⬜ pending |
| 38-01-02 | 01 | 1 | REQ-38-3 | T-38-01-5 | status enum 별개 · 잘못된 CODE → uid 유지 · `selfCheckForReference` 3벌 존재(D-10) · 실패 문구 조인 규칙 명시 | unit + 3벌 텍스트 대조 | `cd backend && .venv/bin/python -m pytest tests/test_registration_contract.py -q && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-01-03 | 01 | 1 | REQ-38-3, REQ-38-6 | T-38-01-3, T-38-01-4 | enum/bool 위장/길이/동의 필수 거부 | unit | `cd backend && .venv/bin/python -m pytest tests/test_validation.py -q` | ✅ 확장 | ⬜ pending |
| 38-02-01 | 02 | 1 | REQ-38-6 | T-38-02-1 | 3~90초 즉시 차단, duration 부재 통과 | node --test + typecheck | `node --test app/src/lib/pickerFailure.test.ts && cd app && npm run typecheck` | ✅ 확장 | ⬜ pending |
| 38-02-02 | 02 | 1 | REQ-38-6 | T-38-02-3 | 낡은 문구 0건 | grep 게이트 | `grep -rn '측면 45°\|2~3m\|정면 우선\|정면으로 다시\|정면으로 촬영\|정면을 기준' app/src docs \| wc -l` == 0 | — | ⬜ pending |
| 38-02-03 | 02 | 1 | REQ-38-5 | T-38-02-2 | 표시만, 리터럴 0 · 시뮬레이터 실물(스크린샷 2장 + UI 트리 "강사 코드"/"기준 영상처럼 찍으세요"; OTA/EAS 는 선언된 이월) | typecheck + grep + simulator | `cd app && npm run typecheck && grep -c "profileCopy.instructorCode" "src/app/(tabs)/profile.tsx" && test -s ../.planning/phases/38-supplier-link/38-02-simulator-profile.png && test -s ../.planning/phases/38-supplier-link/38-02-simulator-tips.png` | — | ⬜ pending |
| 38-03-01 | 03 | 2 | REQ-38-8 | T-38-03-1 | 7항목·고정 각도 0 | doc grep | `grep -c '^## ' docs/supplier-guide.md` == 7 · `grep -c '2~3m\|45°' …` == 0 | — | ⬜ pending |
| 38-03-02 | 03 | 2 | REQ-38-8, REQ-38-4 | T-38-03-2 | md ↔ copy 글자 동일 · row.fail 6코드 = analysis.ts `REGISTRATION_ERROR_MESSAGE`(title + '. ' + body; no_human 예외) · 크레딧/결제 0 | node --test | `node --test app/src/constants/supplierCopy.test.ts && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-04-01 | 04 | 1 | REQ-38-3 | T-38-SC, T-38-04-1 | lockfile 외 변경 0, 팝업만 | export exit + typecheck | `grep -q react-native-web app/package.json && cd app && npm run typecheck` | — | ⬜ pending |
| 38-04-02 | 04 | 1 | REQ-38-3 | T-38-04-3 | localhost Authorized domain 전용 | **manual** (belle 4 항목) | — | — | ⬜ pending |
| 38-04-03 | 04 | 1 | REQ-38-3 | — | 결정 기록 → 미선택 트랙 스킵을 파일로(SUMMARY skipped-by-decision · PLAN skipped · 38-13 depends_on · 아래 미선택 행 `⏭`) · `selfScoreMin` 기록 | **manual** (checkpoint:decision) + grep | `grep -q 'option-1\|option-2' 38-04-MEASUREMENT.md && grep -q selfScoreMin: 38-04-MEASUREMENT.md` + 미선택 SUMMARY 존재(38-12 또는 38-10+38-11) | — | ⬜ pending |
| 38-05-01 | 05 | 2 | REQ-38-4 | T-38-05-1 | fail-closed 판정, 상수 복제 0 | unit (합성 강제 b·c·d) | `cd backend && .venv/bin/python -m pytest tests/test_registration_checks.py tests/test_hold_height.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-05-02 | 05 | 2 | REQ-38-4 | T-38-05-2 | 사이드카 0, estimate 무회귀 | unit (mock N=0/2) | `cd backend && .venv/bin/python -m pytest tests/test_rtmw_engine.py tests/test_rtmw_engine_rot180.py -q` | ✅ 확장 | ⬜ pending |
| 38-06-01 | 06 | 2 | REQ-38-1, REQ-38-3 | T-38-06-4, T-38-06-5 | `create()` · `ref-` 가드 · flat 검증 · 동의 서버 시각 | unit (`_FakeDoc`) | `cd backend && .venv/bin/python -m pytest tests/test_firestore_reference_writers.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-06-02 | 06 | 2 | REQ-38-1, REQ-38-3, REQ-38-5 | T-38-06-1, T-38-06-2, T-38-06-3, T-38-06-6 | 토큰 uid 만 · env/SSM 부재 = 403 · doc 선작성 후 presign | unit (monkeypatch) | `cd backend && .venv/bin/python -m pytest tests/test_reference_upload_url_handler.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-07-01 | 07 | 3 | REQ-38-1 | T-38-07-1, T-38-07-6 | registering+uid 일치만 · Pod 부재 = queued 정상 반환 · uploads/ 무접촉 | unit | `cd backend && .venv/bin/python -m pytest tests/test_pipeline_reference_dispatch.py tests/test_pipeline_dispatch.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-07-02 | 07 | 3 | REQ-38-2, REQ-38-4 | T-38-07-2, T-38-07-3, T-38-07-4, T-38-07-7 | 6 실패 코드 합성 강제 · 같은 함수 순서 · doc 먼저 copy 뒤 · `ANALYSIS_FIELD_SELF_CHECK_FOR_REFERENCE` 상수만(리터럴 0) · copy_object IAM 범위 [미확인 → 38-09-03 (E) / 38-14-02 3-b] | unit (mock engine) | `cd backend && .venv/bin/python -m pytest tests/test_register_reference_pipeline.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-08-01 | 08 | 4 | REQ-38-4, REQ-38-2 | T-38-08-1, T-38-08-2, T-38-08-3 | 훅 graceful · 라우트 토큰/키 검증 · /analyze 무접촉 | unit + TestClient | `cd backend && .venv/bin/python -m pytest tests/test_self_score_hook.py tests/test_runpod_server.py -q` | ❌ 생성 / ✅ 확장 | ⬜ pending |
| 38-08-02 | 08 | 4 | REQ-38-2 | T-38-08-4, T-38-08-5 | 단일 where · 토큰 미출력 · 순차 POST | unit | `cd backend && .venv/bin/python -m pytest tests/test_requeue_reference_registrations.py -q` | ❌ 생성(task 내) | ⬜ pending |
| 38-09-01 | 09 | 5 | REQ-38-1 | T-38-09-4, T-38-09-5 | 최소 권한 정책 · uid 마스킹 | `sam validate --lint` + grep | `cd backend && sam validate --lint && grep -c "ReferenceUploadUrlFunction\|ReferenceUploadUrlLogGroup" template.yaml` | — | ⬜ pending |
| 38-09-02 | 09 | 5 | REQ-38-1 | T-38-09-1 | changeset belle 검토 | **manual** (checkpoint) | — | — | ⬜ pending |
| 38-09-03 | 09 | 5 | REQ-38-1, REQ-38-7 | T-38-09-2, T-38-09-3, T-38-07-7 | 알림 2항목 · lifecycle 없음 · 401 스모크 · IAM simulate-principal-policy(읽기 전용) 기록 | AWS 읽기 + curl | `aws s3api get-bucket-notification-configuration … length == 2` · `get-bucket-lifecycle-configuration → NoSuchLifecycleConfiguration` · `curl … /reference/upload-url → 401` | — | ⬜ pending |
| 38-10-01 | 10 | 4 | REQ-38-3, REQ-38-4 | T-38-10-3 | 순수 규칙, firebase import 0 | node --test + typecheck | `node --test app/src/lib/supplierRules.test.ts && cd app && npm run typecheck` | ❌ 생성(task 내) | ⬜ pending |
| 38-10-02 | 10 | 4 | REQ-38-3, REQ-38-5 | T-38-10-1, T-38-10-2, T-38-10-4 | 팝업만 · 단일 where · 쓰기 0 · 리터럴 색 0 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c 'supplierCopy\.' src/app/supplier/index.tsx` ≥ 20 + hex 리터럴 0 | — | ⬜ pending |
| 38-10-03 | 10 | 4 | REQ-38-4 | T-38-10-3 | `{joints}` textContent 치환 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c "FailurePanel\|DonePanel" src/app/supplier/index.tsx` ≥ 2 + `export function FailurePanel\|DonePanel` == 2 | — | ⬜ pending |
| 38-11-01 | 11 | 5 | REQ-38-3, REQ-38-6 | T-38-11-1, T-38-11-2 | 길이·형식·서 있는 시작 차단, fail-open | node --test + typecheck (export 는 플랜 단위) | `node --test app/src/lib/supplierForm.test.ts && cd app && npm run typecheck && grep -c PickErrorDialog src/app/supplier/upload.tsx` ≥ 1 | ❌ 생성(task 내) | ⬜ pending |
| 38-11-02 | 11 | 5 | REQ-38-3 | T-38-11-3, T-38-11-5 | 필수 3 만 제출 · Firestore 쓰기 0 | typecheck + grep | `cd app && npm run typecheck && grep -c "from 'firebase/firestore'" src/app/supplier/upload.tsx` == 0 | — | ⬜ pending |
| 38-11-03 | 11 | 5 | REQ-38-8 | — | md 동일 문구 | typecheck + grep (export 는 플랜 단위) | `cd app && npm run typecheck && grep -c 'supplierCopy.guide' …` ≥ 7 + `/supplier/guide` 링크 ≥ 2 | — | ⬜ pending |
| 38-12-01 | 12 | 4 | REQ-38-3, REQ-38-5 | T-38-12-1, T-38-12-3, T-38-12-4 | CDN 버전 고정 · 리다이렉트 0 · config gitignore | build + `node --check` + grep | `node app/scripts/build-supplier-web.mjs && node --check web/supplier/supplier.js && grep -q firebasejs/12.13.0 …` | — | ⬜ pending |
| 38-12-02 | 12 | 4 | REQ-38-3, REQ-38-6 | T-38-12-5, T-38-12-6 | Firestore 쓰기 0 · 즉시 검사 | `node --check` + grep | `node --check web/supplier/supplier.js && grep -c 'setDoc\|addDoc\|updateDoc' …` == 0 | — | ⬜ pending |
| 38-12-03 | 12 | 4 | REQ-38-4, REQ-38-8 | T-38-12-2 | innerHTML 0 · `SELF_SCORE_OK_MIN` 이름만(리터럴 90 0) | build + grep | `node app/scripts/build-supplier-web.mjs && grep -c innerHTML …` == 0 && `grep -c '< 90\|>= 90' …` == 0 | — | ⬜ pending |
| 38-13-01 | 13 | 6 | REQ-38-3 | T-38-13-1, T-38-13-3 | public block · OAC 정책 · 롤백 기록 · 읽기 먼저(head-bucket / list-OAC / list-distributions) 멱등 | curl + AWS 읽기 | `curl -sI https://<domain>/ → 200` | — | ⬜ pending |
| 38-13-02 | 13 | 6 | REQ-38-3 | T-38-13-2 | 정확한 도메인만 | **manual** (belle 콘솔) | — | — | ⬜ pending |
| 38-13-03 | 13 | 6 | REQ-38-3, REQ-38-5, REQ-38-8 | — | 실기기 E2E + Figma 대조 | **manual** (belle) | — | — | ⬜ pending |
| 38-14-01 | 14 | 7 | REQ-38-3 | — | uid 제공 · `pod:go <GPU>` 동의(단가 조회값 포함) | **manual** (정은지/belle) + grep | `grep -q 'pod_consent:' 38-14-E2E.md` | — | ⬜ pending |
| 38-14-02 | 14 | 7 | REQ-38-2 | T-38-14-2, T-38-14-3, T-38-07-7 | `pod_consent` 뒤에만 기동 · Pod 한 종류 · commitSha 일치 · SSM 롤백(get-parameter-history) · IAM uploads/ PutObject 확인 · baseline 스냅샷 | 명령 원문 + grep | `test -f infra/legacy-reference-baseline.json && grep -c ref- … ≥ 11 && git log origin/main..HEAD 비어 있음` | — | ⬜ pending |
| 38-14-03 | 14 | 7 | REQ-38-2, REQ-38-4 | T-38-14-4 | Success ① ③ 사람 판정 | **manual** (belle/정은지) | — | — | ⬜ pending |
| 38-14-04 | 14 | 7 | REQ-38-2, REQ-38-4 | T-38-14-1 | RuntimeError 0 · baseline diff 0 · Pod down | 로그 grep + AWS 읽기 | `aws ssm get-parameter … runpod-pod-expected == down && grep … E2E.md` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⏭ skipped-by-decision(38-04 Task 3 (d) 가 미선택 트랙 행에 표시 — 38-10-01~03 · 38-11-01~03 또는 38-12-01~03)*

---

## Wave 0 Requirements

별도 Wave 0 플랜 없음 — 아래 테스트 파일은 **그 파일을 검증하는 task 안에서 RED 먼저** 만든다(`tdd="true"` task). 실행 위치 `cd backend && .venv/bin/python -m pytest`.

- [ ] `backend/tests/test_registration_contract.py` — REQ-38-3 계약 3벌 대조 (38-01-02)
- [ ] `backend/tests/test_registration_checks.py` — REQ-38-4 합성 4형 (38-05-01)
- [ ] `backend/tests/test_firestore_reference_writers.py` — REQ-38-1/2 writer (38-06-01)
- [ ] `backend/tests/test_reference_upload_url_handler.py` — REQ-38-1/3 (38-06-02)
- [ ] `backend/tests/test_pipeline_reference_dispatch.py` — REQ-38-1 Pod down/up (38-07-01)
- [ ] `backend/tests/test_register_reference_pipeline.py` — REQ-38-2/4 6 코드 + happy (38-07-02)
- [ ] `backend/tests/test_self_score_hook.py` — REQ-38-4 (38-08-01)
- [ ] `backend/tests/test_requeue_reference_registrations.py` — REQ-38-2 (38-08-02)
- [ ] `app/src/constants/supplierCopy.test.ts` — REQ-38-8 md 동일성 (38-03-02)
- [ ] `app/src/lib/supplierRules.test.ts` · `app/src/lib/supplierForm.test.ts` — 후보 (1) 순수 규칙 (38-10-01 · 38-11-01)
- [x] 확장만: `test_s3keys.py` · `test_validation.py` · `test_rtmw_engine.py` · `test_runpod_server.py` · `pickerFailure.test.ts`
- [x] 프레임워크 설치 없음(기존 pytest/tsc/node --test)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 웹 export 번들에서 Google 팝업 로그인 · .mov 선택 · presigned PUT · onSnapshot | REQ-38-3 | Google 계정 + 팝업은 사람 손; localhost 만 Authorized domain | 38-04 Task 2 (시뮬 Safari 4줄 ○/×) |
| 호스팅 후보 결정 | — (Claude's Discretion → belle) | 측정값을 보고 belle 이 고른다 | 38-04 Task 3 결정표 |
| CFN changeset 검토(layer 재바인딩 5함수) | REQ-38-1 | `sam deploy` 금지 규칙의 예외 승인 | 38-09 Task 2 |
| Firebase Authorized domains | REQ-38-3 | 콘솔 전용(CLI 없음) | 38-13 Task 2 |
| 실기기 폰 브라우저 A-1~A-6 + Figma 대조(D-22) | REQ-38-3/5/8 | 실기기 렌더·팝업·파일 선택은 사람만 | 38-13 Task 3 |
| 정은지 uid 제공(닭-달걀) | REQ-38-3 | 로그인 1회 뒤 uid 는 사람이 전달 | 38-14 Task 1 |
| Pod 기동 동의 `pod:go <4090\|L4>`(공용 유료 계정) | REQ-38-2 | 비용 결정은 belle — 실행자는 단가 조회값 × 예상 시간만 제시 | 38-14 Task 1 how-to-verify 4 |
| Success ① picker 노출 + mode1 완주 · ③ selfScore 판정 | REQ-38-2/4 | Pod(GPU) + 앱 실기기 + belle 판정(통과선 belle) | 38-14 Task 3·4 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are checkpoints (checkpoint task 는 Manual-Only 표에)
- [x] Sampling continuity: 자동 검증 없는 task 가 3개 연속으로 오지 않는다(체크포인트 사이에 자동 task 배치)
- [x] Wave 0 covers all MISSING references(각 task 내 RED 먼저)
- [x] No watch-mode flags
- [x] Feedback latency < 38s (quick pytest ≈ 10s + typecheck 4.3s; `expo export` 는 플랜 단위라 예산 밖)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (플래너 초안 2026-09-26 · 리비전 1 반영 — plan-checker 재검토 뒤 승인)
