---
phase: 29-mode3-result-screen-completion
verified: 2026-07-17T00:00:00Z
status: passed
score: 18/18 must-haves verified
overrides_applied: 0
human_verification_note: >
  실기기 확인 10항목은 batch-UAT 원칙에 따라 29-HUMAN-UAT.md 에 기적립됨
  (즉시 belle 호출 금지, /gsd-audit-uat 일괄). 본 검증의 human_needed 사유가
  전부 그 문서에 있으므로 규칙에 따라 status=passed.
---

# Phase 29: 결과·비교 화면 완성 Verification Report

**Phase Goal:** 결과 화면의 남은 파일럿 gap 일괄 해소 (시나리오 3/6/9). (a) ⑨ 부상 대응법 노출 (b) ③ Mode3 점수 내역 (c) ⑥ Mode3 확대비교 배선 + D1 비교영상 (d) D4 진짜 가로 방향 + F1 동승 새 EAS 빌드.
**Verified:** 2026-07-17
**Status:** passed (실기기 항목은 29-HUMAN-UAT.md 10건 배치 적립)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths — ROADMAP 서브 골 4종

| # | Truth | Status | Evidence (코드 실측 — SUMMARY 주장 아님) |
|---|-------|--------|------|
| a | ⑨ 부상 대응법: InjuryRiskSection recommendation 행 | ✓ VERIFIED | `InjuryRiskSection.tsx:39` FLAG_COPY 타입 `{title, why, recommendation}` + 4종(asymmetry/trunk_hyperextension/joint_hyperextension/level_mismatch) 전부 실카피 :44/:50/:56/:62 + 렌더 `copy.recommendation` :86 + a11y :77. 클라이언트 카피맵이라 legacy doc 자동 커버 |
| b | ③ Mode3 점수 내역: 백엔드 deductionBreakdown 방출 + 앱 게이트 확장 | ✓ VERIFIED | 백엔드: `pipeline/app.py:2580-2614` mode3_held+md → `deduction_engine.tally` → `overallScore: breakdown.final` + `deductionBreakdown` + status 'mode3_held' 유지. 앱: `result.tsx` 게이트 3곳 mode 무관화 — cleanPass :801, hasBreakdown :844, showBreakdownSection :937 전부 `result.deductionBreakdown` 단독 판정. 테스트 7/7 PASS 로컬 실행 |
| c | ⑥ Mode3 확대비교 배선 + D1 비교영상 | ✓ VERIFIED | zoom: `app.py:3017-3078` `_MODE3_ZOOM_CRITERION_REGION` criterion→region 소스 + `"improved"` 파일 전체 0건 + `_joint_scores` 제거 확인. 테스트 9/9 PASS. D1: `playback-url/app.py` referenceMotionId 변형 + 가드 4종(:66-94) + `api.ts:74` `requestReferencePlaybackUrl` + `result.tsx:724` freshRefUrl 훅 배선 + `template.yaml:174/217` reference/* GetObject. 테스트 11/11 PASS. **배포 실증: CFN PlaybackUrlFunction 갱신 2026-07-16T16:26Z(= a55a817 ImportError fix 01:24 KST 직후 재배포)** |
| d | D4 진짜 가로 + F1 동승 새 EAS 빌드 | ✓ VERIFIED | `package.json` expo-screen-orientation ~9.0.9 + `app.json:57` plugin. `VideoCompare.tsx:213` `requireOptionalNativeModule('ExpoScreenOrientation')` 감지 + :303/:312 함수 스코프 lazy require + lockAsync(LANDSCAPE/PORTRAIT). **정적 import: app/src 전체 grep 0건 (OTA 크래시 게이트)**. 회전 핵 폴백(fsRotated) 보존, FULLSCREEN_ZOOM=1.35 유지. 빌드: iOS 28 aaa54678 FINISHED+제출, Android 04dc0e96 FINISHED, OTA prod 4d079a4b/preview df164e4d (known-verified context) |

### Observable Truths — 29-CONTEXT 결정 D-01~D-14 전수 대조

| # | 결정 | Status | Evidence |
|---|------|--------|----------|
| D-01 | 감점 소스 = ipsf_absolute 측정 전용, Gemini 0 | ✓ VERIFIED | `app.py:2580` `status == "mode3_held" and measured_deviations` 분기, Gemini 호출 0 (테스트 케이스 5: assess_fault_severity raise sentinel 설치 후 통과) |
| D-02 | overallScore = tally(breakdown.final) 전환 + sweep 게이트 조건 | ✓ VERIFIED | `app.py:2611` in-place 교체 항등. sweep 게이트: `backend/evals/phase29/` 4파일 실존(run_sweep 349줄/assert_gates 388줄). PASS·정지조건 발동·belle 결정 A(2026-07-17)는 29-05 SUMMARY 대조표 + MEMORY 교차 확증("잘못된 동작 ≤50 일괄 상한 belle 철회 — 결함 80 승인"). E2E 실측 1건(overallScore 80==final 80, records leg_extension) 기록 |
| D-03 | 미등록 동작 = 현행 점수 + 행동 유도 안내 | ✓ VERIFIED | `result.tsx:655-658` suppressedHeaderCopy — "코치님(정은지) 영상과 비교하거나, 같은 동작을 새 영상으로 올려 이전 연습과 비교해보세요" (통보→유도 전환). md 빈 dict passthrough 는 테스트 케이스 3/6 고정 |
| D-04 | legacy doc 재분석 유도 배너 (28 배너 통합) | ✓ VERIFIED | `result.tsx:1537-1541` motionAlignment===undefined → alignUpsellBanner "다시 분석하면 자동 구간 맞춤 등 최신 분석이 적용돼요" (전용 배너 신설 없이 통합 — Claude 재량 범위) |
| D-05 | 한계 고지 1줄 + 금지어 "각도" 0 | ✓ VERIFIED | `result.tsx:88` MODE3_LIMIT_NOTICE = belle 승인 뼈대 문자열 그대로. breakdown 有→footnote(:1384) / 無→독립 1줄(:1342) 정확히 1곳. 금지어: phase 29 added-lines "각도" 0건 실측(3ecb6cc diff, 기존 7건은 전부 2026-06/07 선행 커밋 소유) |
| D-06 | 비교 라벨 지난/이번 영상 | ✓ VERIFIED | `result.tsx:1433` '이번 영상' / :1442·:1919 '지난 영상' (mode1 `${athleteName} 선수` 불변) |
| D-07 | 첫 분석 비교 숨김 + 안내 1줄 | ✓ VERIFIED | `result.tsx:1420` `!(cmp.mode==='mode3' && cmp.isFirst)` 섹션 게이트 + :1557-1561 "다음 분석부터 이전 영상과 비교해 발전을 확인해 드려요." (정은지 폴백 없음) |
| D-08 | zoom = 결함 부위만, improved deferred | ✓ VERIFIED | `app.py:3070` record criterion→region 파생, kinds 전부 "deficit"(:3079), `"improved"` 0건. cross-side 매핑 완전 일치 실측: backend `_MODE3_ZOOM_CRITERION_REGION`/`_MODE3_ZOOM_REGION_MEMBERS`(:3017-3032) == 앱 `CRITERION_REGION_KEYPOINTS`/`REGION_MEMBER_KEYPOINTS`(deductionLabels.ts:90-114) 항목·멤버 동일 |
| D-09 | D1 진단 태스크 (재현→규명→fix) | ✓ VERIFIED | 29-06 SUMMARY 에 실측 증거표(403 "Request has expired" + 신규 서명 206 대조군 + 11 doc 전수). fix 코드·테스트·배포 전부 실증 (위 (c)) — TTL 7일 유지(`_PLAYBACK_EXPIRES` diff 0) |
| D-10 | mode3 비교영상 Phase 28 워핑 동일 적용 | ✓ VERIFIED | `result.tsx:1440` `alignment={videoAlignment}` mode 무조건 전달 + "mode 조건 추가 금지" 주석. 신규 워핑 코드 0 (백엔드 방출은 28-04 완료분) |
| D-11 | 전체화면 뷰어만 가로 전환 | ✓ VERIFIED | `VideoCompare.tsx:303-313` openFullscreen/closeFullscreen lockAsync LANDSCAPE_RIGHT/PORTRAIT_UP + Modal supportedOrientations(:1012). 앱 전체 세로 고정(app.json orientation 무변경) |
| D-12 | 구빌드 90도 회전 핵 폴백 + 런타임 감지 | ✓ VERIFIED | `:213` requireOptionalNativeModule 감지, 정적 import 0, fsRotated/rotate 코드 보존(4건). version/runtimeVersion 무변경 → OTA 채널 공유 |
| D-13 | phase 마감 시 새 EAS 빌드·제출 + HUMAN-UAT 적립 | ✓ VERIFIED | iOS build 28 FINISHED+무인 제출, Android APK FINISHED, OTA 2채널 발행 (29-08 SUMMARY + known-verified context). 29-HUMAN-UAT.md 10항목 적립 실존 (frontmatter 에 빌드/OTA ID 박제) |
| D-14 | recommendation 카드 내 표시 + 점검 캡션 | ✓ VERIFIED | 위 (a) + EXPERT_REFERRAL "강사와 점검" 캡션 유지, 부상 확정 단정 카피 0 |

**Score:** 18/18 truths verified (서브 골 4 + 결정 14)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/components/InjuryRiskSection.tsx` | recommendation 4종 + 렌더 | ✓ VERIFIED | 타입+4종+렌더 2곳, 실카피 (stub 아님) |
| `backend/functions/pipeline/app.py` | mode3 tally seam + zoom criterion→region | ✓ VERIFIED | :2557-2618 seam, :3017-3078 zoom. mode1 TALLY-ELIGIBLE tuple 불변 |
| `backend/tests/test_mode3_tally_seam.py` | D-01/02/03 매트릭스 | ✓ VERIFIED | 존재(9.9KB) + **7/7 PASS 로컬 재실행** |
| `backend/tests/test_mode3_fault_zoom_selection.py` | D-08 회귀 | ✓ VERIFIED | 존재(9.4KB) + **9/9 PASS 로컬 재실행** |
| `backend/tests/test_playback_url_reference.py` | 가드 4종 + EoP 케이스 | ✓ VERIFIED | 존재(7.3KB) + **11/11 PASS 로컬 재실행** |
| `docs/contract.md` | §10.7 mode3 방출 조건 + §2 playback-url | ✓ VERIFIED | :1558 §10.7 신설 + :73-88 POST /playback-url 두 변형·가드 4종 |
| `app/src/lib/deductionLabels.ts` | projectDeductionRecordKeypoints + 매핑 | ✓ VERIFIED | :217 helper + :110 CRITERION_REGION_KEYPOINTS. result.tsx 로컬 사본 0 (규칙 1벌) |
| `app/src/app/analysis/result.tsx` | 게이트 3곳 + D-03~07 카피 + freshRefUrl | ✓ VERIFIED | 전 항목 라인 단위 실측 (위 표) |
| `app/src/components/ScoreBreakdownSection.tsx` | limitNotice optional prop | ✓ VERIFIED | :48 prop + :162 footnote 렌더, 미전달 시 diff 0 |
| `backend/evals/phase29/` 4파일 | D-02 sweep 하네스 | ✓ VERIFIED | run_sweep 349줄 / assert_gates 388줄 / eval_keys / README (min_lines 충족) |
| `backend/functions/playback-url/app.py` | referenceMotionId 재서명 + 가드 | ✓ VERIFIED | 가드 4종 + 동일 404 + `_REF_ID_RE` 형식 화이트리스트 + TTL 불변 |
| `backend/functions/playback-url/requirements.txt` | firebase-admin+pyyaml (배포 500 fix) | ✓ VERIFIED | a55a817 — CFN 재배포 타임스탬프(16:26Z)가 fix 커밋(16:24Z) 직후임을 실측 |
| `backend/template.yaml` | reference/* GetObject | ✓ VERIFIED | :174, :217 두 곳 |
| `app/package.json` + `app/app.json` | expo-screen-orientation ~9.0.9 + plugin | ✓ VERIFIED | 양쪽 존재 |
| `app/src/components/VideoCompare.tsx` | 런타임 감지 + 가로/핵 분기 | ✓ VERIFIED | 감지+lazy require+lockAsync+폴백 보존 |
| `29-HUMAN-UAT.md` | 10항목 적립 | ✓ VERIFIED | 10항목 + 빌드/OTA ID frontmatter + batch UAT 원칙 명시 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| pipeline `_apply_vision_veto_from_context` | deduction_engine.tally | mode3_held + measured_deviations 분기 | ✓ WIRED | app.py:2595 실호출 + 방출 :2609-2614 |
| pipeline mode3 zoom 빌더 | deductionBreakdown records | criterion→region 파생 | ✓ WIRED | :3070 `_MODE3_ZOOM_CRITERION_REGION.get(rec.criterion)` |
| result.tsx showBreakdownSection | result.deductionBreakdown | mode 무관 게이트 | ✓ WIRED | :937 `!= null` 단독 |
| result.tsx selectedZoom·actionPhrase | projectDeductionRecordKeypoints | 공용 helper import | ✓ WIRED | :41 import, :306/:996 소비, 로컬 사본 grep 0 |
| result.tsx | ScoreBreakdownSection limitNotice | mode3 분기 전달 | ✓ WIRED | :1384 |
| result.tsx | POST /playback-url (reference 변형) | requestReferencePlaybackUrl | ✓ WIRED | :724 훅 → api.ts:74-77 → 실 endpoint (배포 확인) |
| playback-url Lambda | Firestore reference doc videoS3Key | get_reference_motion 화이트리스트 | ✓ WIRED | 리터럴 컬렉션 문자열 0, canonical 헬퍼 경유 |
| VideoCompare | expo-screen-orientation | 함수 스코프 lazy require | ✓ WIRED | :303/:312, 정적 import 0 |
| eas build → TestFlight | eas submit --latest | 무인 제출 | ✓ WIRED | build 28 FINISHED + 제출 실행 기록 (Apple 측 처리 확인은 ASC 콘솔 — belle 이월) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Real Data | Status |
|----------|---------------|--------|-----------|--------|
| result.tsx 점수 내역 섹션 | result.deductionBreakdown | Firestore doc ← pipeline tally 방출 | E2E 실측 1건 (records leg_extension −20, final 80) production Firestore 도달 | ✓ FLOWING |
| result.tsx freshRefUrl | POST /playback-url 응답 | 배포된 Lambda (CFN 16:26Z) + reference/* IAM | 재발급 URL 서명 role 권한 실존 | ✓ FLOWING |
| InjuryRiskSection recommendation | FLAG_COPY (클라이언트 정적 카피맵) | 설계상 정적 — 데이터 소스 불필요 | 4종 실카피 | ✓ FLOWING |
| VideoCompare 가로 분기 | hasNativeOrientation | requireOptionalNativeModule 런타임 | 실기기 판정 — UAT 항목 7/8 | ? UAT 배치 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| phase 29 백엔드 테스트 3파일 | `pytest test_mode3_tally_seam.py test_mode3_fault_zoom_selection.py test_playback_url_reference.py -q` | **27 passed in 0.39s** | ✓ PASS |
| improved kind 폐기 | `grep '"improved"' pipeline/app.py` | 0건 | ✓ PASS |
| OTA 크래시 게이트 | `grep "from 'expo-screen-orientation'" app/src -r` | 0건 | ✓ PASS |
| 금지어 게이트 | 3ecb6cc added-lines `sed 심각도 제거 후 grep 각도` | 0건 | ✓ PASS |
| production 배포 실증 | `aws cloudformation describe-stack-resources` | PlaybackUrlFunction 갱신 2026-07-16T16:26Z (ImportError fix 직후) | ✓ PASS |
| 커밋 실존 | 19개 클레임 해시 `git cat-file -t` | 전부 commit | ✓ PASS |
| app typecheck | known-verified context (2026-07-17) | exit 0 | ✓ PASS (재실행 생략) |

### Probe Execution

SKIPPED — `scripts/*/tests/probe-*.sh` 0건, PLAN/SUMMARY probe 선언 0건 (이 phase 는 probe 규약 미사용, 검증 수단 = pytest + sweep 게이트).

### Requirements Coverage

신규 REQ ID 없음 (phase 선언). 커버리지 = 29-CONTEXT D-01~D-14 → **14/14 전수 VERIFIED** (위 표). ORPHANED 0.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (phase 29 변경 파일 전체) | - | TBD/FIXME/XXX | 없음 | grep 0건 — 디버트 마커 게이트 통과 |
| app/src/app/analysis/result.tsx | 1888 | `TODO: Firebase displayName 박제×4` | ℹ️ Info | **phase 29 소유 아님** — git log -S 실측: e968074 (2026-06-07, phase 12.5) 도입. 29-REVIEW IN-06 으로 기등재 |

**29-REVIEW.md 5 Warning 처분 확인 (advisory, phase goal 비차단):** WR-01(재생바 틱 도메인 불일치)=quick-260705 선행 코드 클래스, mode1 veto-applied 한정 / WR-02(prev 재발급 mov ext)=선행 freshPrevUrl 훅 소유, mov+6일 코너 / WR-03(좌측 영상 TTL)=D-09 범위(우측 reference) 밖 동일 클래스 / WR-04(임시파일 누수)=28-05 선행 다운로드 코드, 29-03 은 대상 선택만 변경 / WR-05(LogGroup 누락)=선행 함수 소유. 전부 phase 29 must-have 실패 아님 — 후속 quick/phase 처리 권장 대상.

### Human Verification Required

**신규 생성 0건** — 실기기 확인 10항목 전부 `29-HUMAN-UAT.md` 에 기적립 (batch-uat-after-phase-31 원칙, /gsd-audit-uat 일괄). 항목: D-14 권고 행 / D-01~05 내역·게이트 / D-06·07 라벨·첫분석 / D-08 드릴다운 e2e / D-10 워핑 / D-09 D1 재발 / D-11 진짜 가로(새 빌드) / D-12 구빌드 무크래시 / F1 메일 컴포저 / iPad 관찰. 추가 1건(ASC 콘솔 TestFlight Apple 처리 확인)은 29-08 SUMMARY 에 belle 이월로 기록됨.

### Gaps Summary

없음. SUMMARY 주장 대비 코드 실측 불일치 0. 특기:
- 29-06 이 이관했던 sam deploy 는 실제 수행됨 — CFN 타임스탬프 + a55a817 ImportError fix + 직후 재배포로 실증.
- D-02 production 전환(sweep PASS → belle 결정 A → Pod 재기동 → E2E)은 SUMMARY·MEMORY 교차 확증. 단 **운영 노트: Pod olnrvtj0f80pl4 는 2026-07-17 terminate 됨(volume 생존)** — 새 Pod 생성 시 SSM+Lambda 재동기화 필요(RESUME-phase29-closeout 체크리스트). 이는 Pod 생명주기 수동 정책의 인프라 운영 사안이지 phase 29 코드 gap 아님.

---

_Verified: 2026-07-17_
_Verifier: Claude (gsd-verifier)_
