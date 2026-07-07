---
phase: 26
slug: onboarding-upload-guide
status: verified
threats_open: 0
threats_closed: 17
asvs_level: 1
created: 2026-07-08
---

# Phase 26 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> 검증 방식: 문서 주장 불인정 — 전 항목 코드/커밋 grep 실증 (gsd-security-auditor, adversarial stance).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| 앱 로컬 저장(AsyncStorage) | 튜토리얼 1회 노출 플래그 — 기기 로컬, 서버 무접촉 | `@sunity:tutorial_seen` boolean (비민감) |
| 라우터 param 체인 (analyze → reference → loading) | 학습활용 동의값 전달 경로 — 유실/오염 시 동의 오기록 위험 | `learningOptIn: '1'` / 미포함 |
| 앱 → Firestore (users/{uid}/analyses/{id}) | 클라이언트가 쓰는 동의값 boolean — rules 로 본인 문서만 write | `learningOptIn: boolean` (동의 증거) |
| 앱 → Firestore (users/{uid}.bodyProfile.painAreaNote) | 자유입력 통증 메모 — 민감 건강 정보, 본인 문서 한정 | 자유 텍스트 (민감) |
| 사용자 파일명 → 앱 감지 로직 | `_talkv_` 파일명은 사용자 제어 입력 — advisory 경고, 보안 게이트 아님 | 파일명 문자열 |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-26-01 | Tampering | AsyncStorage tutorial_seen 플래그 | accept | 기기 소유자 본인만 변조 가능, 영향 = 튜토리얼 재노출/미노출뿐 → Accepted Risks R-26-01 | closed |
| T-26-02 | DoS | index.tsx 라우팅 (AsyncStorage 읽기 실패) | mitigate | `onboarding.ts:22-24` catch → `return true` ("본 것으로 간주" 방향 실패). 소비처 `index.tsx:26-28` 단일 라우팅점. 진입 차단/재노출 루프 불가 | closed |
| T-26-03 | Info Disclosure | FAQ 보관·삭제 정책 카피 | mitigate | `help.tsx:55-56` "올려주신 영상은 분석에만 사용하고 안전하게 보관해요. 언제든 삭제를 요청하실 수 있어요." — D-08 고지(`analyze.tsx:524-526`)와 동일 취지, 과장/허위 없음 | closed |
| T-26-04 | DoS | 시뮬 lib 삭제 잔존 참조 + result.tsx 훅 순서 | mitigate | grep `simulationWriter\|simulatedResult` app/src = 0건, grep `analysis/samples` app/src = 0건, samples.tsx/simulationWriter.ts/simulatedResult.ts 파일 부재 확인. `result.tsx:544` wrapper(AnalysisResult) / `result.tsx:618` child(AnalysisResultContent) 분리 — non-null result 로만 자식 마운트(훅 순서 안정, 리뷰 HIGH-1) | closed |
| T-26-05 | Tampering | learningOptIn 동의값 무결성 (D-09) | mitigate | `loading.tsx:337` `learningOptIn === '1'` 엄격 비교(param 유실/오염 → false = 미동의 fail-safe), `loading.tsx:98` 항상-boolean 타입, `loading.tsx:147` 무조건 boolean 기록(조건부 spread 아님), `analyze.tsx:76-84` buildOptInRouteParams 순수 헬퍼 단일점, `reference.tsx:36→104` pass-through. **opt-out 반전 검증**: UI 초기값만 true(`analyze.tsx:127`, 커밋 a64c769 1줄 반전) — 기록 경로·fail-safe 방향(유실→false) 불변 확인 | closed |
| T-26-06 | Repudiation | 동의 증거 | mitigate | `loading.tsx:130-148` 분석 문서 생성 시 업로드 시점 boolean 명시 기록. 3-way lockstep: `analysis.ts:619` + `models.py:236-250`(주석 미러) + `contract.md:97-112`. 읽기 경로 `userAnalyses.ts:352-353`(IN-03 fix, 커밋 83780f5/9519687). Phase 22 manifest 게이트 true-필터는 후속(아래 Unregistered/Follow-up 플래그로 추적) — 이 phase 검증 범위 = 기록 존재 | closed |
| T-26-07 | Spoofing | 타 사용자 동의값 위조 | accept | `firestore.rules:9-11` `users/{uid}/{document=**}` = `request.auth.uid == uid` 본인 한정, deny-by-default(:20-22). phase 26 무변경(마지막 수정 커밋 63f4f0c, phase 26 이전) → Accepted Risks R-26-07 | closed |
| T-26-08 | Info Disclosure | 프라이버시 고지 우회(미노출) | mitigate | `analyze.tsx:524-526` D-08 1줄 고지 — pick 직전 소스 선택 단계(pickFromCamera/pickFromLibrary 카드와 동일 화면) 고정 배치, 26-06 재배치안 A "이동 금지" 주석(:522-523). 실기기 노출 확인은 26-HUMAN-UAT 배치 세션 | closed |
| T-26-09 | Spoofing | _talkv_ 감지 우회 (파일명 변경) | accept | `analyze.tsx:350` 감지는 advisory 경고만 — 우회해도 기존 `validate()`(:333, 포맷/용량) + 서버측 not_pole 게이트 그대로 적용, 하드 차단 아님 → Accepted Risks R-26-09 | closed |
| T-26-10 | Tampering | D-07 분기 회귀 (화질 우선 안내 파손) | mitigate | `analyze.tsx:382-387` continueTalkv 가 기존 `lowQuality: true` 플래그 재사용(신규 분기 0). `loading.tsx:414` `isLowQualityNotPole = isNotPole && lowQuality === '1'` — git log -S 로 도입 커밋 eb8c294(quick-260704-fwb) 이후 무변경(diff 0) 확인. 감지는 `isKakaoCompressedVideoName` 순수 헬퍼 단일점(:91-93), 인라인 includes 중복 0(전 코드베이스 grep) | closed |
| T-26-11 | DoS | 게이트 체인 데드락 (모달 이중 노출/보류 유실) | mitigate | `analyze.tsx:347-360` 직렬 체인(talkv → return 으로 화질 검사 스킵 → lowQuality → bodyProfile), `:309-315` continuePendingRoute 단일 수렴(입력완료/건너뛰기/백드롭/native back 4-경로), `:407-409` dismissTalkv native back = 영상 버림. 리뷰 WR-01 fix 실재: promptTimer 지연 present(`:152, :294-298`, 커밋 054ef71≡26094f9). WR-02 fix 실재: repickTimer 핸들 + busyRef 가드 + cleanup effect(`:116-119, :156-163, :399-401`, 커밋 7ec3ebe≡218ce57) | closed |
| T-26-12 | Tampering | painAreaNote 자유 텍스트 주입 | accept | 앱-로컬 표시 전용 — `normalizeBodyProfile` 이 키 미독취(`bodyProfile.ts:110-114`, raw 별도 읽기 `:153-156`), 분석 snapshot(`getBodyProfileOnce`) 자동 배제, backend grep `painAreaNote` = 0건. 렌더는 RN `<Text>` 만(`profile.tsx:57`, injection-safe) → Accepted Risks R-26-12 | closed |
| T-26-13 | Info Disclosure | 통증 메모 = 민감 건강 정보 | mitigate | 저장 위치 `bodyProfile.ts:238-242` `users/{uid}.bodyProfile.painAreaNote` — painAreas 와 동일 map·동일 rules(`firestore.rules:9-11` 본인 한정) 보호. 노출 경로 전수 grep: 표시 = `profile.tsx`(본인 마이페이지)뿐, 백엔드/분석 문서/LLM 프롬프트 소비 0건 — 새 노출 경로 0 | closed |
| T-26-14 | Tampering | dirty-guard 부재 시 메모 소실 | mitigate | `BodyProfileForm.tsx:178-182` `trimmedNote !== baseNote(initialPainAreaNote 기준)` 일 때만 savePainAreaNote 호출. prefill 없는 호출부(analyze.tsx 폼: initialPainAreaNote 미전달 → baseNote='' == trimmedNote='')에서 기존 메모 덮어쓰기 불가. prefill 호출부 `profile.tsx:165` initialPainAreaNote 전달 확인 | closed |
| T-26-15 | Tampering | 재배치 중 동의/게이트 로직 회귀 | mitigate | 감사 시점 grep 3종 재실행 전부 PASS: (1) `_talkv_` = analyze.tsx 상수/헬퍼 단일점만, (2) `learningOptIn` 체인 = analyze(:76-84,127,219) → reference(:36,104) → loading(:337,147) + 계약 3-미러 + userAnalyses 정합, (3) `hasSeenTutorial/markTutorialSeen` = onboarding.ts 단일 lib + index.tsx/tutorial.tsx 소비만. 재배치(커밋 54a6513)는 ScrollView/캡션 병합만 — 게이트/동의 로직 diff 0. Firestore 양방향 실기기 실증은 26-HUMAN-UAT (e)(f) 배치 세션 | closed |
| T-26-16 | EoP | 승인 범위 밖 변경 | mitigate | phase 26 커밋(25533ad~83780f5, 17건) 변경 파일 = app/src + docs/contract.md + models.py 주석 미러 + planning 산출물 + 튜토리얼 이미지 자산(79dca59, belle 승인) — 범위 밖 0. `git status` 구현 경로(app/backend/docs/firestore.rules) 클린 | closed |
| T-26-SC | Tampering | npm/pip 패키지 설치 | n/a | phase 26 전 커밋 17건 대상 `git show --name-only` 전수 확인 — package.json/package-lock/requirements* 접촉 0건 (Package Legitimacy Gate 해당 없음) | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-26-01 | T-26-01 | AsyncStorage tutorial_seen 은 기기 소유자 본인만 변조 가능. 최악 영향 = 튜토리얼 재노출/미노출 (보안 자산 아님, 서버 무접촉) | 26-01-PLAN threat_model (belle 승인 플랜) | 2026-07-07 |
| R-26-07 | T-26-07 | Firestore rules `users/{uid}` 본인 한정 + deny-by-default 가 타 사용자 동의값 위조 차단. 잔여 위험 = 기기 소유자 본인의 자기 동의값 변조뿐 (자기 데이터) | 26-03-PLAN threat_model (belle 승인 플랜) | 2026-07-07 |
| R-26-09 | T-26-09 | _talkv_ 감지는 advisory 경고 — 파일명 변경으로 우회해도 기존 validate/서버 게이트가 그대로 적용, 하드 차단이 아니라 우회 이득 없음 (D-06 설계 의도) | 26-04-PLAN threat_model (belle 승인 플랜) | 2026-07-07 |
| R-26-12 | T-26-12 | painAreaNote 는 앱-로컬 표시 전용 (normalizeBodyProfile 밖 → 분석 snapshot/백엔드/LLM 자동 배제, RN Text injection-safe). 주입 페이로드가 도달할 sink 없음 | 26-05-PLAN threat_model (belle 승인 플랜) | 2026-07-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered / Follow-up Flags

- **없음 (unregistered_flag 0건).** 26-01/26-02 SUMMARY `## Threat Flags` = None. 26-03~06 SUMMARY 의 Threat Model Coverage 항목은 전부 기존 T-26-* 매핑.
- **Follow-up (informational, T-26-06 매핑):** Phase 22 D-12 학습 플라이휠 manifest 게이트가 `learningOptIn === true` 필터를 아직 미집행 — 현재 게이트는 anonymized/등록 여부만 필터. Phase 26 은 동의 기록만 담당(계약 주석 3곳에 소비 계약 명시). Phase 22 반영 전까지 학습 후보 추출 시 이 필터 필수.
- **Deferred evidence (26-HUMAN-UAT 배치 세션):** T-26-08 실기기 고지 노출 확인, T-26-15 Firestore 동의값 양방향(ON→true / OFF→false) 실증 — 코드 레벨 mitigation 은 본 감사에서 확인 완료, 실기기 실증만 이월 (belle 승인).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-08 | 17 | 17 | 0 | gsd-security-auditor (fable) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer / n/a)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-08 (실기기 실증 2건은 26-HUMAN-UAT 이월 — 코드 레벨 전 항목 CLOSED)
