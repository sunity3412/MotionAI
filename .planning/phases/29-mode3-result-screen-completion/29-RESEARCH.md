# Phase 29: 결과·비교 화면 완성 — Mode3 내역·줌, 비교영상, 가로 방향, 부상 대응법 - Research

**Researched:** 2026-07-09
**Domain:** RN/Expo 결과 화면 확장 + 파이프라인 채점 seam (mode3 tally) + EAS 네이티브 빌드
**Confidence:** HIGH (전 대상 코드 실측 — 라인 번호는 2026-07-09 main 기준)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Mode3 점수 내역 (감점 소스)
- **D-01:** 감점 소스 = **ipsf_absolute 측정 전용** — 등록 동작(kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape, P1 step4 criteria yaml)이면 RTMW 측정값을 객관 IPSF 기준(무릎 신전 180° 등)과 대조해 `deduction_engine.tally` 실행. **Gemini 호출 없음** — mode3_held 불변. 비용·시간 증가 0.
- **D-02:** **Mode3 overallScore = tally(breakdown.final)로 전환** (표시 전용 아님 — 100−Σ감점=점수 항등식 유지, 투명 감점 invariant 준수). 단 **정은지 페어셋 mode3 sweep 검증 게이트(Pod 1회) 통과가 전환 조건**: success=고득점 / fault=감점 변별, cold=warm 결정성. Mode3 첫 분석에도 적용 가능(절대 기준이라 이전 영상 불필요). 성장 델타도 tally 점수 기준으로 일관.
- **D-03:** **미등록 동작 = 현행 절대차원 점수 유지 + 행동 유도 안내.** tally 미실행(기준 없는 감점 0=100 위양성 차단, motion-routing-generalize 정합). 안내는 "제공 불가" 통보가 아니라 **"코치님(정은지) 영상이나 본인 이전 연습 영상과 비교해보세요" 식 행동 유도 메시지** (belle 원문: "친절 메시지가 짜여져야 할 듯").
- **D-04:** **legacy Mode3 doc(내역 없음) = 재분석 유도 배너** — Phase 28 D-05 패턴 재사용. 28 배너와 중복 노출 시 통합은 Claude 재량.
- **D-05:** **한계 고지 1줄 필수** — 내역 아래에 측정 범위 + 다음 행동 유도 결합. 뼈대(belle 승인): "카메라로 잰 자세 형태 기준이에요. 같은 동작을 새 영상으로 다시 올리면 이전 영상과 비교한 발전 분석이 본격 시작돼요. 그립·디테일 점검은 코치님 비교 분석을 이용해보세요." **금지어: "각도"** — (i) 사용자가 못 알아들음(belle 실측, 260705-k8y에서 행동구 라벨로 전환한 이유), (ii) mode3 세부점수 "angle" 차원(=이전영상 유사도)과 용어 충돌, (iii) 각도 수치 전면화는 강사 철학 충돌(현장 리서치).

#### Mode3 비교영상·확대비교
- **D-06:** 비교 대상 = **본인 이전 영상 vs 이번 영상** (라벨 "지난 영상/이번 영상" 계열 — 정은지 아님).
- **D-07:** **Mode3 첫 분석(이전 영상 없음) = 비교 섹션 숨김 + 안내 1줄** ("다음 분석부터 이전 영상과 비교해 드려요" 늬낌, D-05 문구와 톤 통일). 정은지 폴백 기각 — mode1과 혼동 + 미보유 동작 reference 부재.
- **D-08:** 확대비교(zoom) 카드 = **결함 부위만** — 이번 분석 감점 부위를 이전 영상 같은 구간과 나란히 확대 (mode1 줌과 동일 개념). 개선 부위 축하 카드는 deferred.
- **D-09:** **D1(Mode1 비교영상 안 뜸, 파일럿 신고) = 진단 태스크로 플랜에 정식 포함** — 재현→원인 규명→fix. Phase 28 변경 연관 가능성 점검.
- **D-10:** Mode3 비교영상도 **Phase 28 워핑 동일 적용** — 이전 영상을 이번 영상 타임라인에 워핑, 신뢰도 사다리(28 D-02)·배속 클램프 0.5~2배 동일. 백엔드 방출(mode3 second+)은 Phase 28 완료분 — 앱 소비만 확장.

#### 가로 방향 + EAS 빌드
- **D-11:** expo-screen-orientation 적용 범위 = **전체화면 비교 뷰어만** — 진입 시 가로 전환, 닫으면 세로 복귀. 앱 전체 세로 고정 유지. D4(비율 이상)는 회전 핵 치수 계산 소멸로 근본 해소.
- **D-12:** **구빌드 호환: 90도 회전 핵 폴백 유지** — 런타임에 네이티브 모듈 가용성 감지해 분기 (새 빌드=진짜 가로 / 구빌드=현행 핵). runtimeVersion bump 없이 OTA를 구빌드에도 계속 배포 가능. 핵 코드 제거는 파일럿 이후.
- **D-13:** **새 EAS 빌드·제출 = Phase 29 마감 시** — iOS TestFlight 무인 제출(ASC 자동화 OK) + Android APK 함께. F1(문의하기) 동승 해소. 실기기 확인은 HUMAN-UAT.md 적립(batch UAT 원칙 — 즉시 belle 호출 금지).

#### 부상 대응법 노출
- **D-14:** `SafetyFlag.recommendation`을 **카드 내 바로 표시** — 기존 카드(제목+이유) 아래 "이렇게 해보세요" 행 + "정확한 진단은 강사님과 점검하세요" 톤 캡션 (시나리오 불변원칙: 부상 경고 = "강사와 점검", 위험 확정 아님).

### Claude's Discretion
- D-03/D-05/D-07 안내·고지 카피 세부 (뼈대·금지어는 위 결정 준수, 기존 "~해요" 체).
- D-04 배너 문구·위치, Phase 28 배너와 통합 여부.
- mode3 tally의 앱 게이트 확장 구현 방식 (result.tsx mode1 게이트 3곳 — 내역 섹션·마커·isCleanPass — 의 mode 분기 설계).
- 전체화면 뷰어 가로 전환의 상태 처리(진입/이탈 시퀀스), 네이티브 모듈 가용성 감지 방법.
- 계약 필드 설계 — 단 3-way lockstep(analysis.ts + models.py + docs/contract.md) + Firestore flat 규칙 준수.

### Deferred Ideas (OUT OF SCOPE)
- **Mode3 개선 부위 축하 카드** — 시나리오 +α "성공 순간 축하"와 연결. improved/worsened 판정 로직 별도 phase.
- **90도 회전 핵 코드 제거** — 파일럿 이후 구빌드 소멸 시.
- **vision veto Mode3 확장** — 기각 아닌 보류 유지. Phase 22 자체 VLM이 저비용 판정 가능해지면 재검토.
- **미등록 동작 criteria 등록 확대** — 도메인 기준 수립(belle/정은지) 필요, 별도 트랙.
</user_constraints>

<phase_requirements>
## Phase Requirements

프로젝트 REQUIREMENTS.md 에 매핑된 신규 ID 없음 — 커버리지는 CONTEXT.md 결정 D-01~D-14 기준.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Mode3 등록동작 ipsf_absolute tally (Gemini 무호출) | §채점 seam 실측 — 삽입 지점 = `_apply_vision_veto_from_context` passthrough_map(app.py:2565), md 는 이미 빌드됨(:4137). 24-04 low_alignment tally-eligible 선례 재사용 |
| D-02 | Mode3 overallScore = tally.final + Pod sweep 게이트 | evals/phase24·25 harness 패턴 실측 (SERIAL, cold/warm, baseline read-only). **4/5 동작이 criteria 빈 yaml — 기대치 보정 필수(Pitfall 1)** |
| D-03 | 미등록 = 현행 점수 + 행동유도 안내 | expects_extension 전부 False → md 빈 → 엔진 fallback 이 자연 방어. 안내 hook = `scoreSuppressed`/`suppressedHeaderCopy`(result.tsx:655) |
| D-04 | legacy Mode3 doc 재분석 배너 | Phase 28 배너 선례 실측 (result.tsx:1471-1484, `motionAlignment === undefined` 판정) |
| D-05 | 한계 고지 1줄 (금지어 "각도") | ScoreBreakdownSection 구조 실측 — basisLine/footer 삽입 슬롯 존재 |
| D-06/D-07 | Mode3 비교 라벨·첫분석 안내 | result.tsx:1373-1396 실측 — 라벨 "지난 분석", 첫 분석 = 섹션 전체 미렌더(안내 0줄) |
| D-08 | Mode3 zoom = 감점 부위만 | `_build_mode3_fault_zoom_comparisons`(app.py:2970) 이미 존재 — 현행 = \|Δscore\| top-2 improved/worsened. 선택 소스 교체 + improved 억제 필요 |
| D-09 | D1 진단 태스크 | §D1 진단 체크리스트 — 최유력 = presigned 7일 TTL(재발급 경로 부재) |
| D-10 | Mode3 워핑 앱 소비 | 실측: alignment prop 은 이미 mode 무관 전달(result.tsx:1387) + 백엔드 mode3 방출 완료(28-04) — 신규 doc 은 이미 동작 가능성 높음, 검증 태스크로 |
| D-11 | 전체화면 뷰어만 가로 전환 | expo-screen-orientation ~9.0.9 API 검증 (lockAsync/unlockAsync) |
| D-12 | 구빌드 폴백 (런타임 감지) | `requireOptionalNativeModule` 패턴 검증 — **정적 import 는 구빌드 크래시(Pitfall 3)** |
| D-13 | EAS 빌드·무인 제출 + F1 동승 | eas.json/app.json 실측 — runtimeVersion policy appVersion(1.0.0) 유지 시 OTA 공유 채널 유지. mail-composer 는 plugins 등록 완료 → 새 빌드에 자동 포함 |
| D-14 | 부상 대응법 카드 행 | **`SafetyFlag.recommendation` 필드는 존재하지 않음(Pitfall 2)** — FLAG_COPY 클라이언트 카피맵 확장이 정답 (OTA-safe, legacy doc 포함) |
</phase_requirements>

## Summary

이 phase 는 4개 서브골 전부 "이미 깔린 인프라의 마지막 배선"이다. 실측 결과 CONTEXT/SCENARIO 의 전제 2곳이 코드 실체와 다르므로 플랜이 반드시 보정해야 한다:

1. **`SafetyFlag.recommendation` 은 어디에도 없다** (backend dataclass·TS interface·contract §9.13 모두 7필드, recommendation 없음). SCENARIO.md 의 "데이터가 있는데 앱이 안 그림"은 오류 — 기존 부상 카피는 전부 클라이언트 카피맵(`FLAG_COPY {title, why}`)이고 백엔드는 enum 만 보낸다. D-14 의 올바른 구현 = **FLAG_COPY 에 flagType 별 recommendation 행 추가 (앱 전용, OTA-safe, legacy doc 자동 커버, 계약 변경 0)**. 백엔드 필드 신설은 3-way lockstep + 신규 분석에만 적용되므로 열등.
2. **등록 5동작 중 objective EXTEND criteria 를 가진 것은 power-spin 하나뿐**이다. kip-up/peter-pan/elbow-twist-sister/pdshape 의 criteria yaml 은 2026-06-27 Pod 진단으로 knee EXTEND 가 제거되어 비어 있다(정타 form 이 무릎을 굽힘 — 신전기준 강요 금지). 따라서 Mode3 ipsf_absolute tally 는 4/5 동작에서 measured seed 가 비어 dimension_overall fallback(점수 불변)으로 귀결된다. D-01/D-02 는 그대로 유효하지만(무회귀가 구조적으로 보장됨), **"Mode3 내역"의 실질 콘텐츠는 power-spin 외에는 fallback 1행뿐** — UI 는 이 케이스를 정직하게 처리해야 하고 D-05 한계 고지가 UX 의 본체가 된다. sweep 게이트 기대치도 이에 맞춰야 한다.

나머지는 순방향이다: mode3 fault_zoom 백엔드는 이미 배선돼 있고(joint 선택 로직만 D-08 에 맞게 교체), motionAlignment 는 mode1/mode3 둘 다 방출·앱 소비 코드가 mode 무관이라 Mode3 워핑은 사실상 이미 흐른다. 가로 방향은 expo-screen-orientation ~9.0.9(SDK 54 번들 버전, 레지스트리 검증 완료) 설치 + `requireOptionalNativeModule` 런타임 감지 + 기존 90° 회전 핵 폴백 분기.

**Primary recommendation:** OTA-safe 작업(D-14 부상 → D-01~05 mode3 내역 → D-06~08/10 비교·줌 → D-09 D1 진단)을 먼저 완결하고, 네이티브 작업(D-11/12 가로)을 마지막 wave 로 분리한 뒤 D-13 빌드·제출로 마감한다. D-02 점수 전환은 Pod sweep 게이트 통과 전까지 표시-경로에만 두지 말고 게이트를 plan 내 checkpoint 로 명시한다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Mode3 tally 실행·breakdown 방출 (D-01/D-02) | Pipeline (RunPod GPU 서버가 실행하는 pipeline/app.py `_process` 채점 seam) | Firestore (complete_analysis 저장) | 점수는 백엔드 단일 seam 소유 — 앱은 절대 재계산 금지 |
| D-02 sweep 검증 게이트 | Pod (SERIAL in-process harness) | 로컬 assert_gates | 파이프라인 동시성 비안전 + GPU 필수 |
| Mode3 내역·마커·cleanPass 게이트 확장 | App (result.tsx) | — | 저장된 record 를 그대로 표기 (숫자 조작 금지) |
| 미등록 안내·한계 고지·첫분석 안내 카피 (D-03/05/07) | App (카피맵/컴포넌트) | — | 카피는 전부 클라이언트 소유 (부상 카피 선례) |
| Mode3 비교영상 워핑 (D-10) | App (VideoCompare 소비) | Pipeline (motionAlignment 방출 — 완료분) | 28-04 가 방출 완료, 표현/재생 전용 |
| Mode3 zoom joint 선택 (D-08) | Pipeline (`_build_mode3_fault_zoom_comparisons`) | App (진입점·kind 필터) | 렌더·S3 업로드는 백엔드 사후 태스크 |
| 부상 대응법 행 (D-14) | App (InjuryRiskSection FLAG_COPY) | — | recommendation 데이터 실체가 클라이언트 카피맵 |
| 가로 전환 (D-11/12) | App (VideoCompare 전체화면) + 네이티브 빌드 | — | expo-screen-orientation = 네이티브 모듈 |
| EAS 빌드·제출 (D-13) | 빌드 체인 (eas-cli) | — | iOS 무인 제출 + Android APK |
| D1 진단 (D-09) | App(렌더 조건) + Backend(URL 발급·TTL) 양쪽 | — | 원인 후보가 두 tier 에 걸침 (아래 진단 체크리스트) |

## Standard Stack

### Core (신규 설치는 1개뿐)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| expo-screen-orientation | **~9.0.9** (SDK 54 번들 — `expo/bundledNativeModules.json` 로컬 실측) | 전체화면 뷰어 가로 lock/unlock | Expo 공식 모듈, config plugin 동봉 [VERIFIED: npm registry + 로컬 bundledNativeModules.json + slopcheck OK] |

**주의: npm latest 는 57.0.0 (신형 SDK 정렬 버저닝)** — 절대 latest 설치 금지. 반드시 `npx expo install expo-screen-orientation` 으로 SDK 54 호환 ~9.0.9 를 받을 것. [VERIFIED: npm registry — latest=57.0.0, SDK54 bundled=~9.0.9]

### Supporting (전부 기설치 — 재사용만)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| expo-mail-composer | ~15.0.8 (package.json + app.json plugins 등록 완료) | F1 문의하기 | 코드 변경 0 — 새 빌드가 네이티브 포함 (빌드 27 부재가 F1 원인) |
| expo-modules-core | 3.0.29 | `requireOptionalNativeModule` — D-12 런타임 감지 | 신규 import 만 (기설치, `src/requireNativeModule.ts:32` 실측) |
| expo-video | ~3.0.16 | 비교영상 재생 (rate/seek 워핑) | Phase 28 소비 완료본 유지 |
| expo-updates | ~29.0.17 | OTA 배포 (channel production) | OTA-safe wave 배포 |
| deduction_engine + ipsf_criteria (backend) | in-repo | Mode3 tally (D-01) | 신규 엔진 금지 — 기존 tally 재사용 |
| evals/phase24·25 harness (backend) | in-repo | D-02 sweep 게이트 | 복제-확장 패턴 (phase25 가 phase24 게이트 import 재사용) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| expo-screen-orientation | RN `Modal supportedOrientations` (iOS) | 네이티브 모듈 불필요하나 Android 미지원 + 기기 자동회전 설정 의존 — D-11 의 "진입 시 강제 가로"를 보장 못함. 기각 (단 iOS Modal prop 은 병행 필요 — Pattern 4) |
| FLAG_COPY 확장 (D-14) | SafetyFlag 백엔드 필드 신설 | 3-way lockstep + 신규 분석에만 적용 + 파이프라인 재배포 필요. 카피맵이 우월 (OTA·legacy 커버) |

**Installation:**
```bash
cd app && npx expo install expo-screen-orientation
# app.json plugins 에 "expo-screen-orientation" 추가 (initialOrientation 은 iOS 전용 옵션 — 기본 미지정 가능)
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| expo-screen-orientation | npm | 7+ yrs (expo monorepo) | 대량 (Expo 공식) | github.com/expo/expo (packages/expo-screen-orientation) | [OK] | Approved — 단 `npx expo install` 로 ~9.0.9 고정 |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

주의 기록: `slopcheck install` 은 검증 후 **실제 npm install 을 실행**한다 (연구 세션 중 홈 디렉터리 오설치 발생 → 즉시 완전 롤백 완료, repo 무접촉). 플래너/실행자는 검증 목적이면 `slopcheck scan` 또는 ecosystem 명시(`-e npm`)와 설치 위치를 반드시 통제할 것. 또한 ecosystem 미지정 시 pypi 로 오판(cross-ecosystem 함정 실증)한다.

## Architecture Patterns

### System Architecture Diagram

```
[Mode3 영상 업로드] → S3 → SQS → pipeline Lambda → (위임) RunPod _process
                                                        │
   recognizer.recognize (Gemini 1회 — 기존, 추가 호출 0) │
        │ profile(joint_expectations ← criteria yaml)   │
        ▼                                               ▼
   _mode3_comparison → overall(절대차원 평균)      _collect_vision_fault_context
        │                                          └ mode==MODE_SELF → ctx("mode3_held") [Gemini 무호출]
        ▼                                               │
   _build_deduction_measured_deviations (:4137)  ← 이미 mode3 에서도 빌드됨 (ref 인자 None)
        │ md = {leg_extension?, arm_extension?, line?}  │ (mode3 는 이 3키만 가능)
        ▼                                               ▼
   _apply_vision_veto(vision_fault_context=ctx) → _apply_vision_veto_from_context
        │  현행: passthrough_map["mode3_held"] → md 폐기, breakdown 미방출   ← ★ D-01 삽입 지점
        │  변경: mode3_held 를 tally-eligible 로 (24-04 low_alignment 선례) — md 비면 D-03 자연 방어
        ▼
   result{overallScore(D-02: tally.final), deductionBreakdown} → _apply_score_suppression(미등록 억제 유지)
        ▼
   complete_analysis (Firestore flat) → 앱 onSnapshot
        ▼ (complete 이후 사후)
   _build_mode3_fault_zoom_comparisons (dtw_match=prev_dtw_match, D-08 joint 선택 교체 대상)
        → update_analysis_fault_zoom → faultZoomStatus pending→done

[앱 result.tsx]  mode1 게이트 4곳 확장: showBreakdownSection(:905) / cleanPass(:771)
                / actionLabels hasBreakdown(:813) / markers·legend(모두 breakdown 파생)
                + InjuryRiskSection FLAG_COPY recommendation 행 (D-14)
                + VideoCompare(alignment 이미 mode 무관 :1387) 라벨·첫분석 안내 (D-06/07)
                + 전체화면 뷰어: requireOptionalNativeModule 감지 → 진짜 가로 / 90° 핵 폴백 (D-11/12)
```

### Recommended Change Map (파일 단위)
```
backend/functions/pipeline/app.py        # D-01/D-02: from_context mode3 tally-eligible + D-08 zoom joint 선택
backend/shared/.../models.py             # (필요 시) 계약 상수 — 기본 권고는 신규 필드 0 (Pattern 2)
backend/evals/phase29/                   # D-02 sweep 게이트 (phase25 복제-확장)
docs/contract.md                         # §10 에 mode3 방출 조건 명시 (필드 추가 없이 서술 갱신)
app/src/types/analysis.ts                # (필요 시) 계약 미러 — 기본 권고는 변경 0
app/src/app/analysis/result.tsx          # 게이트 4곳 mode 분기 + D-04/05/07 카피 + D-06 라벨
app/src/components/InjuryRiskSection.tsx # D-14 FLAG_COPY recommendation 행 + 캡션
app/src/components/ScoreBreakdownSection.tsx # D-05 한계 고지 슬롯 (basisLine/footer 재사용)
app/src/components/VideoCompare.tsx      # D-11/12 가로 전환 분기 (openFullscreen/closeFullscreen :285-292)
app/package.json + app/app.json          # expo-screen-orientation 설치 + plugin
```

### Pattern 1: mode3_held → tally-eligible (D-01 의 최소 절개)
**What:** `_apply_vision_veto_from_context`(app.py:2533) 의 TALLY-ELIGIBLE status 집합 {candidate_verdict, no_fault, low_alignment_confidence} 에 mode3 경로를 추가. measured substrate 는 seam(:4137)이 이미 mode3 에서 빌드한다 (reference_dtw_match/split/pointed 전부 None → md 는 ipsf_absolute 3키만 — D-01 "ipsf_absolute 전용"이 인자 흐름으로 자동 보장됨).
**When to use:** D-01 구현 태스크.
**근거 선례:** 24-04 Option A (belle 2026-06-26) — "RTMW 측정 편차는 정렬-독립이므로 Gemini 없이도 감점해야 한다"는 논리가 mode3 에 그대로 이식된다. Gemini-located fault 는 부재 → `criteria_for_fault` 는 아무것도 안 더함(위양성 fabricate 금지) → seeded criteria 만 발화.
**Status 의미 주의:** `visionVeto.status` 는 비전 실행 여부의 진실 신호다. mode3 에서 tally 만 돌 때 'applied' 를 재사용하면 앱의 `vetoApplied`(:711) 파생들이 오염될 수 있다(현행 소비처는 mode1-gated 라 실해는 없지만 의미 왜곡). 옵션: (a) status 는 mode3_held 유지 + deductionBreakdown 만 additive 방출 (계약 §10 은 breakdown 을 visionVeto 와 독립 필드로 이미 정의 — 최소 변경, 권고), (b) 신규 status 값 추가(계약 3-way + 앱 enum 확장 비용). 플래너 재량이나 (a) 권고.
**D-03 자연 방어:** 미등록/굽힘-form 동작은 `profile.expects_extension` 전부 False → md 빈 dict → 엔진은 quant_unavailable AND activated 0 → dimension_overall fallback (final 불변). 단 이때 **fallback 1행짜리 breakdown 을 방출할지**가 설계 분기점: 방출하면 "내역" 섹션이 무의미한 1행을 보여주고, D-03 의 "tally 미실행" 문언과 어긋난다. **권고: md 가 비면(또는 fallback-only 면) mode3 에서는 deductionBreakdown 미방출** → 앱은 breakdown 부재 = 행동 유도 안내(D-03)로 라우팅. 이렇게 하면 D-02 의 overallScore 전환도 fallback 케이스에서 항등(final==dimension_overall)이라 무회귀가 산술적으로 보장된다.

### Pattern 2: 계약 변경 최소화 (3-way lockstep)
**What:** `deductionBreakdown` 은 이미 mode 무관 optional 필드다 (models.py DEDUCTION_BREAKDOWN_KEYS / analysis.ts:557 / contract.md §10). record 의 `deviationSource: 'ipsf_absolute'` 가 이미 provenance 를 나른다. faultZoomComparisons.kind 는 이미 `'deficit' | 'improved' | 'worsened'`(analysis.ts:442). motionAlignment 도 mode 무관(§11).
**결론:** 신규 계약 필드 0 으로 D-01~D-10 전부 구현 가능. contract.md 는 "mode3 방출 조건" 서술만 갱신 (§10 에 mode3 절, §11.5 는 기존 유지). Firestore flat 규칙은 기존 record dict list 가 이미 준수. legacy 폴백 = 필드 부재 시 현행 렌더 (faultZoomStatus/tier 선례 그대로).

### Pattern 3: D-12 런타임 네이티브 모듈 감지 (구빌드 크래시 차단)
**What:** expo-screen-orientation 9.0.9 의 `build/ExpoScreenOrientation.js` 는 **모듈 최상위에서** `requireNativeModule('ExpoScreenOrientation')` 를 실행한다 [VERIFIED: unpkg 9.0.9 소스]. `requireNativeModule` 은 네이티브 부재 시 throw → **정적 `import ... from 'expo-screen-orientation'` 이 포함된 OTA 번들은 TestFlight 빌드 27 에서 모듈 평가 시점에 크래시**한다.
**Safe pattern:**
```ts
// Source: expo-modules-core 3.0.29 src/requireNativeModule.ts:32 (로컬 실측)
import { requireOptionalNativeModule } from 'expo-modules-core';

const hasNativeOrientation =
  requireOptionalNativeModule('ExpoScreenOrientation') != null;

async function enterLandscape() {
  if (!hasNativeOrientation) return; // 구빌드 → 기존 90° 회전 핵 경로
  // 함수 스코프 lazy require — Metro 는 require 호출 시점에 모듈 평가
  const ScreenOrientation = require('expo-screen-orientation');
  await ScreenOrientation.lockAsync(
    ScreenOrientation.OrientationLock.LANDSCAPE_RIGHT,
  );
}
async function exitLandscape() {
  if (!hasNativeOrientation) return;
  const ScreenOrientation = require('expo-screen-orientation');
  await ScreenOrientation.lockAsync(
    ScreenOrientation.OrientationLock.PORTRAIT_UP,
  );
  // unlockAsync() 는 DEFAULT 로 풀어 기기 자동회전에 맡김 — 앱 전체 세로 고정(D-11)
  // 유지를 위해 PORTRAIT_UP lock 후 필요 시 unlock 순서는 실기기 확인 항목.
}
```
**runtimeVersion:** app.json `runtimeVersion: {policy: "appVersion"}` + version 1.0.0. **version 을 올리지 않으면** 새 빌드와 빌드 27 이 같은 runtimeVersion 을 공유 → OTA 가 양쪽에 도달 (D-12 요구 그대로). autoIncrement 는 buildNumber 만 올린다 (appVersionSource=remote). 즉 기본 설정 유지가 정답 — version bump 금지.

### Pattern 4: 가로 전환 진입/이탈 시퀀스 (전체화면 뷰어)
**What:** 현행 핵 = RN Modal 안에서 `transform: rotate('90deg')` + short/long 파생 치수 (VideoCompare.tsx:263-292, :1223-1228, FULLSCREEN_ZOOM=1.35 :202). 진짜 가로 분기에서는 회전 transform 과 축 스왑 치수 계산을 모두 생략하고 window 치수를 그대로 쓴다.
**iOS Modal 주의:** 네이티브 가로로 실제 회전하려면 표시 중인 RN `Modal` 에 `supportedOrientations={['portrait', 'landscape']}` 필요 (Modal 은 자체 orientation 허용 목록을 가짐). 순서: openFullscreen → setState → Modal 마운트 → lockAsync(LANDSCAPE_RIGHT). 닫기: lockAsync(PORTRAIT_UP) → closeFullscreen (역순이면 세로 복귀 전에 Modal 이 닫혀 화면 flicker). 정확한 시퀀스는 Claude 재량 + HUMAN-UAT 항목.
**FULLSCREEN_ZOOM 1.35:** belle 승인값 — 감으로 변경 금지 (28-CONTEXT deferred 메모). 진짜 가로에서는 회전 핵의 치수 왜곡이 사라지므로 zoom 값의 재검토가 필요할 수 있으나, 변경 시 근거 필수.

### Pattern 5: D-02 sweep 게이트 (phase25 복제-확장)
**What:** `backend/evals/phase29/` 신설 — run_sweep.py(phase25 복제: serial in-process `_process`, EVAL_OUT_DIR=/tmp/sunity_eval_out, baseline read-only, `--tag warm` 재실행) + assert_gates.py.
**Mode3 전용 조정:** eval_keys 는 phase24 의 6페어(fixtures/phase15, bucket sunity-motion-pilot-videos)를 **mode='mode3'** 로 재사용. Mode3 첫 분석(이전 영상 없음) 케이스가 D-02 의 본체 — prev 없는 단독 분석으로 돌리면 절대 기준 채점이 검증된다. 게이트: (1) success 멤버 무감점(final == 현행 절대차원 점수와 항등 또는 ≥ 기존), (2) power-spin fault 는 leg_extension 감점 발화(유일한 criteria 보유 동작 — 변별 실증), (3) 나머지 4동작 = fallback 항등(무회귀), (4) cold=warm 결정성 (recognizer TechniqueCache 재사용 — mode3 는 Gemini 가 recognizer 1회뿐), (5) climb = not_pole 게이트 유지 여부는 mode3 에 not_pole 미적용이므로 제외 판단 필요. **특정 점수 리터럴 assert 금지 + 자기 sweep 재보정 금지(calibration-source-hard-gate) + SERIAL 필수.**
**Pod 운영:** 현재 Pod s7gyvvlc6u7ktz (SSH root@213.173.102.162:26448) — push 먼저, Pod 에서 pull 후 실행 (gsd-pod-work-push-first).

### Pattern 6: 앱 게이트 mode 분기 (D-01/D-02 소비)
**What:** result.tsx 의 breakdown 파생 4곳은 전부 `cmp.mode === 'mode1'` 게이트다. 확장 = "mode1" 조건을 "breakdown 보유"로 일반화하되, mode3 전용 차이를 명시 분기:
- `showBreakdownSection`(:905): `result.deductionBreakdown != null` 로 mode 무관화 (mode3 는 D-01 방출 시에만 필드 존재 — 미등록/legacy 는 자연 숨김).
- `cleanPass`(:771): mode3 도 breakdown 전달 — 단 mode3 의 "감점 0 = 축하" 카피는 mode1 문구(정은지 유사) 재사용 금지, mode3 톤 별도.
- `actionLabels hasBreakdown`(:813): mode3 는 windowMedianAngleDeltas 없음(veto 미실행) → JointScore.deltaDeg 경로(기존 2순위)가 이미 mode3 를 커버 — 게이트만 확장.
- `markers`/`fullscreenLegend`/`timelineTicks`: markers 는 records 파생이라 자동. timelineTicks 는 visionVeto 의존(:892 "mode3 면 빈 배열") — mode3 는 window 시점이 없어 틱 생략이 정직(유지).
- `breakdownBasisLine`(:789): `composeScoringBasisKo` 가 record deviationSource 로 자동 조립 — ipsf_absolute 만 있는 mode3 에서 그대로 동작. D-05 한계 고지는 이 라인 옆/아래 신설 (금지어 "각도" — 기존 deductionLabels 카피 재사용 시 "각도" 포함 여부 grep 필수).
- 억제 상호작용: `scoreSuppressed`(mode3 미등록, :651) 시 점수카드 억제는 유지 — D-03 안내는 suppressedHeaderCopy(:655) 자리에 행동 유도 문구로 교체/보강.

### Anti-Patterns to Avoid
- **앱에서 감점 재계산/재해석:** 저장된 record 그대로 표기 (ScoreBreakdownSection 헤더 주석 — "합계 검증이 어긋나도 UI 가 숫자를 조작하지 않는다").
- **mode1 채점·vision veto 경로 접촉:** D-01 절개는 from_context 의 mode3 분기에 한정. mode1 TALLY-ELIGIBLE 3-status 로직 불변.
- **Gemini 를 mode3 에 추가 호출:** recognizer 1회(기존)만. collect 의 mode3_held 조기 bail(:1999-2000) 불변.
- **정적 import 'expo-screen-orientation':** 구빌드 OTA 크래시 (Pattern 3).
- **npm install expo-screen-orientation@latest:** 57.0.0 은 SDK 54 비호환.
- **Firestore nested array:** breakdown records 는 flat dict list (기존 준수) — 신규 필드 설계 시에도 유지.
- **eval sweep 동시 실행:** 파이프라인 동시성 비안전 — SERIAL 만.
- **mode3Summary 델타를 tally·구점수 혼합 비교로 방치:** prev doc(legacy, 절대차원 평균) vs 신규(tally) 델타는 fallback 항등 덕에 대부분 안전하지만 power-spin 만 기준 이동 가능 — D-04 재분석 배너가 완충. 플랜에서 명시 확인.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mode3 감점 산출 | mode3 전용 채점 함수 | `deduction_engine.tally` + `_build_deduction_measured_deviations` (seam 재사용) | 분기 0 코드 1벌 원칙 + 추적성/결정성 게이트 기적용 |
| 가로 전환 | 자체 회전 개선 핵 v2 | expo-screen-orientation lockAsync | OS 레벨 회전 — 치수 계산 소멸이 D4 근본 해소 |
| 네이티브 감지 | try/catch import 곡예 | `requireOptionalNativeModule('ExpoScreenOrientation')` | expo-modules-core 공식 API, null 반환 계약 |
| sweep 하네스 | 신규 eval 구조 | evals/phase25 복제-확장 (게이트 import 재사용) | cold/warm·baseline 오염 방지 규율이 이미 코드화됨 |
| 재분석 배너 | 신규 배너 컴포넌트 | Phase 28 alignUpsellBanner 패턴 (result.tsx:1471) | 판정 규칙(필드 부재=legacy)까지 검증된 선례 |
| prev 영상 URL 재발급 | 자체 서명 로직 | 기존 `requestPlaybackUrl`(POST /playback-url) | 인증·키 규칙 완비 — D1 fix 에서 확장 후보 |

## Common Pitfalls

### Pitfall 1: "등록 5동작" criteria 실체 — 4/5 가 빈 yaml
**What goes wrong:** D-01 문언("등록 동작이면 tally")대로 구현하고 sweep 을 돌리면 kip-up/peter-pan/elbow-twist-sister/pdshape 에서 감점 record 가 0 — "내역이 안 나온다"를 버그로 오판하거나, 반대로 위양성 감점을 내려고 criteria 를 임의 복원하는 사고.
**Why it happens:** 2026-06-27 Pod 진단(P1 step5)으로 knee EXTEND 가 4동작에서 제거됨 — 정타 form 이 무릎을 굽혀 신호가 inverted (`judging_data/criteria/ref-*.yaml` 헤더 주석 실측). 이 동작들의 결함 축은 reference_relative(정은지 대비)인데 D-01 은 ipsf_absolute 전용.
**How to avoid:** (i) sweep 게이트 기대치를 "power-spin 만 감점 변별, 나머지 4동작 항등"으로 설계. (ii) UI 는 breakdown 부재/무감점 mode3 를 D-05 한계 고지 중심으로 렌더. (iii) criteria 복원·신설 금지 (굽힘 form 신전기준 강요 금지 + deferred "미등록 동작 criteria 확대" 트랙).
**Warning signs:** sweep 에서 4동작 fault 가 100점 → 정상 동작임 (ipsf_absolute 기준으로 잴 것이 없음). 이를 "감점 엔진 고장"으로 보고 임계를 만지기 시작하면 calibration-source-hard-gate 위반.

### Pitfall 2: SafetyFlag.recommendation 은 존재하지 않는 필드
**What goes wrong:** D-14 를 "백엔드가 이미 보내는 필드를 앱이 안 그린다"로 착수 → 필드가 없어서 렌더가 영원히 빈다.
**Why it happens:** SCENARIO.md 단계 9 서술 오류. 실체: safety_flags.py dataclass 7필드(:86-92), analysis.ts SafetyFlag 7필드(:1138-1146), contract §9.13 — 전부 recommendation 없음. 카피는 전부 클라이언트 FLAG_COPY.
**How to avoid:** FLAG_COPY 를 `{title, why, recommendation}` 로 확장 (flagType 4종 전부) + 카드에 "이렇게 해보세요" 행 + 캡션. 10-UI-SPEC Copywriting Contract 동시 갱신 (컴포넌트 헤더 주석의 명시 규칙). "부상 확정" 단정 금지·amber 시맨틱 유지·브랜드 레드 금지.
**Warning signs:** plan 에 models.py/contract.md 수정이 D-14 태스크로 들어가 있으면 재검토 (필요 없음).

### Pitfall 3: OTA 번들의 정적 import → 구빌드 크래시
**What goes wrong:** `import * as ScreenOrientation from 'expo-screen-orientation'` 을 아무 파일에나 추가하면, 같은 runtimeVersion 으로 OTA 를 받는 빌드 27 에서 번들 평가 시점 throw → 앱 전체 크래시 (가로 기능을 안 써도).
**Why it happens:** 9.0.9 의 네이티브 바인딩이 모듈 최상위 `requireNativeModule` (Pattern 3 실측).
**How to avoid:** requireOptionalNativeModule 감지 + 함수 스코프 lazy require. OTA 발행 전 구빌드 시뮬(모듈 부재) 경로 확인을 HUMAN-UAT 에 적립.
**Warning signs:** VideoCompare 상단 import 목록에 expo-screen-orientation 이 보이면 실패.

### Pitfall 4: presigned URL 7일 TTL — D1 의 최유력 원인 (아래 진단 체크리스트)
**What goes wrong:** Mode1 비교영상(정은지)이 "안 뜸".
**Why it happens (유력 순):**
1. `result.referenceVideoUrl` 은 분석 시점 서명 (`_signed_get`, `_PLAYBACK_EXPIRES = 7*24*3600`, app.py:145/:1258/:3806). **7일 지난 doc 은 우측 영상이 확정적으로 죽는다.** 앱의 재발급 로직(result.tsx:683-706)은 mode3 prev doc 전용이며, `/playback-url` 은 본인 업로드 키만 재서명 — reference videoS3Key 재서명 경로가 전무.
2. 폴백 `refMotion?.videoUrl`(result.tsx:1394) 은 Firestore reference doc 의 서명 URL — 시드 시점 서명이라 사실상 항상 만료 (S3 presigned GET TTL 한계, 프로젝트 메모리 선례).
3. `ref.videoS3Key` 부재 시 referenceVideoUrl 자체 미방출 → rightUrl undefined → VideoCompare 빈 슬롯 UI.
4. Phase 28 워핑 회귀 가능성 (낮음): normalizeMotionAlignment malformed → null → 절대시계 폴백이라 재생 자체는 유지되어야 함. rate 제어(클램프 0.5~2x) 오작동은 "안 뜸"보다 "이상 재생"으로 발현.
5. expo-video 로드 실패는 무음 (에러 UI 없음) — 재현 시 원인 분간이 어려움.
**How to avoid (진단 태스크 설계):** (a) 신선한 mode1 분석 vs 7일+ 경과 doc 양쪽 재현 → TTL 가설 즉시 분리. (b) rightUrl 값 로깅/검사 (undefined vs 만료 URL). (c) fix 방향 후보: /playback-url 을 referenceMotionId 재서명까지 확장(백엔드) 또는 결과 화면에서 refMotion 실시간 재서명. fix 는 진단 결과 따라 — 선판단 금지 (D-09).
**Warning signs:** "재분석하면 뜨는데 옛 분석은 안 뜸" 제보 = TTL 확정.

### Pitfall 5: iOS 가로 lock 의 기기·라이브러리 함정
**What goes wrong:** lockAsync 가 resolve 되는데 실기기가 안 돈다.
**Why it happens:** (i) iPad + supportsTablet:true — split view 지원 시 orientation lock 무효 (`requireFullScreen: true` 필요; 현 app.json 미설정). (ii) react-native-screens ≥4.23 이 supportedInterfaceOrientations 전역 swizzle 로 lock 무력화 (expo/expo#43802, 2026-03) — 현 프로젝트는 ~4.16.0 이라 미해당이나 **이번 빌드에서 rns 업그레이드 금지**. (iii) RN Modal 이 landscape 를 supportedOrientations 에 안 가지면 Modal 위에서 회전 안 됨.
**How to avoid:** 파일럿 = iPhone 중심이므로 iPad 는 HUMAN-UAT 관찰 항목으로만. rns 버전 고정. Modal prop 명시.
**Warning signs:** EAS 빌드에서만 재현되는 회전 실패 → Info.plist orientation 목록 확인.

### Pitfall 6: mode3 zoom 의 현행 백엔드가 D-08 과 다른 것을 만든다
**What goes wrong:** "타입 준비됨 = 배선만" 으로 읽고 앱 진입점만 열면, 카드가 **개선 부위(improved)** 까지 보여준다 — deferred 결정 위반.
**Why it happens:** `_build_mode3_fault_zoom_comparisons`(app.py:2970) 는 이미 완전 구현체 — joint 선택이 \|Δscore\| top-2, kind=improved/worsened. D-08 은 "이번 분석 감점 부위만".
**How to avoid:** 백엔드 joint 선택 소스를 deduction records(=tally 감점 관절)로 교체하거나 최소한 improved 를 방출/렌더 억제. 앱 zoom 진입점(openRecordByNumber :946 → record keypoint ∩ faultZoomComparisons :958-974)은 breakdown 확장으로 자동 개방 — record 관절과 zoom 관절의 일치가 매칭 성립 조건이므로 **백엔드 선택 소스 교체가 정합상 필수**.
**Warning signs:** mode3 에서 record 행 탭 시 zoom 미매칭(빈 시트) = 관절 소스 불일치.

### Pitfall 7: D-10 은 "구현"이 아니라 "검증"일 수 있다
**What goes wrong:** Mode3 워핑 소비를 새로 구현하는 태스크를 잡는 것.
**Why it happens:** result.tsx:1387 은 alignment 를 mode 무관 전달, 백엔드는 mode3 second+ 방출 완료(app.py:4611-4619, 양측 9fps). VideoCompare 워핑 로직도 mode 무관.
**How to avoid:** 신규 mode3 분석(second+)으로 실동작 확인부터 — 안 되면 그때 원인 규명. 첫 분석 안내(D-07)와 라벨(D-06)은 확실한 신규 작업.
**Warning signs:** "mode3 워핑 대규모 리팩터" 류 태스크가 plan 에 있으면 과잉.

## Code Examples

### D-14: FLAG_COPY 확장 (앱 전용)
```tsx
// app/src/components/InjuryRiskSection.tsx — 기존 구조 실측 기반
const FLAG_COPY: Record<SafetyFlagType, { title: string; why: string; recommendation: string }> = {
  asymmetry: {
    title: '좌우 비대칭 신호',
    why: '…(기존 유지)…',
    recommendation: '(카피 재량 — "이렇게 해보세요" 행동 지시, "~해요" 체, 부상 단정 금지)',
  },
  // trunk_hyperextension / joint_hyperextension / level_mismatch 동일 확장
};
// 카드: why 아래 recommendation 행 + 캡션 "정확한 진단은 강사님과 점검하세요" 톤 (D-14).
// 기존 EXPERT_REFERRAL 푸터(:25)와 중복되지 않게 문구 조정은 재량.
```

### D-01: seam 삽입 스케치 (from_context)
```python
# backend/functions/pipeline/app.py _apply_vision_veto_from_context — 개념 스케치
# 현행: status not in TALLY_ELIGIBLE → passthrough_map["mode3_held"] → breakdown 미방출.
# 변경: mode3_held 이고 md(ipsf_absolute seed)가 비어있지 않으면 tally 실행.
if status == "mode3_held":
    if measured_deviations:  # 등록 동작 + expects_extension 발화분만 (D-01/D-03)
        breakdown = deduction_engine.tally(
            None, None,                     # quantification/fault_context 없음 — Gemini 무호출
            dimension_overall=score_result["overallScore"],
            measured_deviations=measured_deviations,
            dimension_scores=score_result.get("dimensionScores"),
            baseline_kind=baseline_kind,
        )
        # D-02 (sweep 게이트 통과 후): overallScore = breakdown.final
        # visionVeto.status 는 'mode3_held' 유지 권고 (비전 미실행의 진실 신호, Pattern 1)
    # md 빈 dict → 현행 passthrough 유지 (D-03: breakdown 미방출 + 점수 불변)
```

### D-02: sweep 실행 커맨드 (phase25 계보)
```bash
# Pod (SERIAL — 파이프라인 동시성 비안전)
cd backend && PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py            # cold
cd backend && PYTHONPATH=shared/python:. python3 evals/phase29/run_sweep.py --tag warm  # 결정성
cd backend && PYTHONPATH=shared/python:. python3 evals/phase29/assert_gates.py          # exit 0 = PASS
```

### D-13: 빌드·제출 체인
```bash
cd app && npx expo install expo-screen-orientation   # ~9.0.9 (SDK 54 고정)
# app.json plugins 에 "expo-screen-orientation" 추가 후:
eas build --profile production --platform ios --non-interactive       # channel production
eas submit -p ios --latest --non-interactive                           # ASC 6772934567 무인 제출
eas build --profile preview-android --platform android --non-interactive  # APK
# OTA-safe wave 는 별도: eas update --channel production (JS-only 변경분)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 90° 회전 핵 (quick-260702-t0v, OTA 전제로 네이티브 금지) | expo-screen-orientation 진짜 가로 (새 빌드 허용됨) | 이 phase (D-11) | 회전 핵 치수 계산 소멸 → D4 근본 해소. 핵은 구빌드 폴백으로 존치 |
| severity→cap 밴드 (Phase 20) | deduction_engine.tally 투명 감점-합산 (Phase 24) | 2026-06-24~ | mode3 확장도 같은 엔진 재사용 — 신규 채점 코드 0 |
| fault_zoom 시간비례 근사 | DTW 대응 프레임 정렬 + 전신 폴백 (Phase 28 D-04) | 2026-07-08 | mode3 zoom 도 prev_dtw_match 로 같은-pose 프레임 (기배선) |
| VideoCompare 절대시계 동기화 | DTW 워핑 (targetRefTime + rate feedforward, 신뢰도 사다리) | Phase 28 | mode3 는 소비 검증만 남음 (Pitfall 7) |
| expo 모듈 개별 버저닝 (9.x) | SDK 정렬 버저닝 (57.0.0 = 신형 SDK) | 2026 상반기 | latest 설치 사고 위험 — expo install 강제 |

**Deprecated/outdated:**
- `severity→고정천장 밴드`: 재도입 금지 (SCORE-10).
- Mode3 overall 에 angle(이전영상 유사도) 차원 포함: 260620-0r0 에서 제거 — invariant.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | iOS 에서 app.json `orientation: "portrait"` 이어도 expo-screen-orientation lockAsync(LANDSCAPE) 가 런타임 우선한다 ("Changes to the screen orientation will override existing settings" — 공식 문서 문언은 있으나 portrait 필드와의 상호작용을 명시하지 않음) | Pattern 3/4 | 가로 전환 자체 실패 → 실기기(HUMAN-UAT) 1순위 확인 항목. 실패 시 plugin `initialOrientation` 또는 `ios.requireFullScreen` 조정 |
| A2 | RN Modal `supportedOrientations` 가 lockAsync 와 함께 필요하다 (RN 공식 prop 이나 expo-screen-orientation 병용 케이스는 실측 전) | Pattern 4 | 회전 안 됨 → 같은 UAT 에서 판별 |
| A3 | mode3 recognizer(TechniqueCache) 캐시로 cold=warm 결정성이 성립한다 (mode1 에서 검증된 캐시 — mode3 sweep 에서의 실측은 전) | Pattern 5 | warm 게이트 FAIL → 캐시 키에 mode 관여 여부 조사 |
| A4 | D1 의 원인이 presigned 7일 TTL 일 가능성이 최유력 (코드 흐름 실측 기반 추론 — 파일럿 기기 재현 전) | Pitfall 4 | 진단 태스크가 어차피 재현부터 시작 (D-09 구조가 방어) |
| A5 | `slopcheck` 의 npm 판정 [OK] 외에 expo-screen-orientation 의 공급망 이상 없음 (expo 모노레포 공식 패키지 — postinstall 스크립트 미확인) | Package Audit | 위험 극소 (Expo 공식) — 설치 시 lockfile diff 확인으로 충분 |

## Open Questions (RESOLVED)

> 플래너 확정 (2026-07-09, phase 29 plan set 리비전): 4문항 전부 플랜에 채택-반영 완료.

1. **mode3 tally 시 visionVeto.status / breakdown 방출 신호 설계** — **RESOLVED → 29-02 (옵션 a 채택)**
   - What we know: status 'applied' 재사용은 의미 오염, 'mode3_held' 유지 + breakdown additive 가 최소 변경 (Pattern 1 옵션 a).
   - What's unclear: 앱이 "measured-only tally" 를 구분 표시할 필요가 있는지 (D-05 고지가 사실상 그 역할).
   - Resolution: 옵션 (a) 확정 — visionVeto.status 'mode3_held' 유지 + deductionBreakdown additive 방출 (29-02 Task 2), contract §10 서술 갱신 동봉. "measured-only" 별도 신호는 두지 않고 D-05 한계 고지(29-04)가 그 역할을 담당.
2. **fallback-only breakdown 의 방출 여부 (D-03 경계)** — **RESOLVED → 29-02 (미방출 확정)**
   - What we know: md 빈 dict → 엔진 fallback record 1행. 방출하면 무의미 내역 + D-03 "tally 미실행" 문언 충돌.
   - Resolution: md 빈 dict → mode3 breakdown 미방출 + overallScore byte-불변 (29-02 Task 2 명세 3항, 테스트 케이스 3 으로 고정) — 무회귀 산술 보장 겸함.
3. **D1 fix 의 형태 (진단 결과 의존)** — **RESOLVED → 29-06 (조건부 fix 구조)**
   - What we know: TTL 이면 백엔드 재서명 경로 신설(playback-url 확장) 또는 앱 실시간 재서명이 필요 — 둘 다 이 phase 범위로 감당 가능한 크기.
   - Resolution: 29-06 Task 1 진단(재현→규명)이 원인을 확정하고, Task 2 는 조건부 fix — TTL 확정 시 /playback-url referenceMotionId 재서명 확장 + 앱 mode1 재발급 훅, 다른 원인 확정 시 그 fix 로 대체(deviation 기록), 범위 초과면 blocker 보고. D-09 문언 그대로.
4. **mode3 zoom 의 감점-부위 선택과 4/5 동작 빈 record 의 교차** — **RESOLVED → 29-03 + 29-08**
   - What we know: D-08 = 감점 부위만인데 4동작은 감점 record 가 없다 → zoom 카드도 자연히 없음.
   - Resolution: "record 없으면 zoom 카드 없음 = 의도된 동작" 을 29-03 에 명시 (must_haves truth + 조기 return 주석). belle 기대("Mode3 확대비교")와 실 노출 빈도의 간극 커뮤니케이션은 29-08 담당 (D-05 고지 문맥 + HUMAN-UAT 적립 항목).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node / npm | app 작업·EAS | ✓ | v24.15.0 / 11.12.1 | — |
| eas-cli | D-13 빌드·제출 | ✓ | 20.1.0 (>=19 요건 충족) | — |
| SAM CLI | 백엔드 배포 (Lambda 갱신 필요 시) | ✓ | 1.161.0 | Pod 위임이 실행 경로라 배포 규모 작음 |
| Docker | `sam build --use-container` | ✓ (client 29.4.0) | — | 데몬 기동 확인 필요 |
| RunPod Pod | D-01/02 파이프라인 실행 + sweep | ✓ (메모리: s7gyvvlc6u7ktz, SSH root@213.173.102.162:26448, 코드 910a568) | — | Pod 재생성 시 proxy URL → Lambda env 동기화 필수 |
| AWS profile sunity-motion | S3/SSM | ✓ (프로젝트 상시) | — | — |
| Gemini 크레딧 | mode3 sweep 의 recognizer 호출 | 미확인 | — | **sweep 전 잔액 확인 (고갈 이력 2026-06-20)** |

**Missing dependencies with no fallback:** 없음.
**Missing dependencies with fallback:** Docker 데몬·Gemini 크레딧은 실행 시점 확인 항목.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (backend/requirements-dev.txt) / 앱은 tsc 만 (JS 테스트 러너 없음) |
| Config file | backend/tests/conftest.py (별도 pytest.ini 없음) |
| Quick run command | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/pipeline -q -x` |
| Full suite command | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` (기존 54 failures 알려짐 — app-module-name-collision + gemini/knee env; 게이트 = 신규 실패 0) |
| App gate | `cd app && npm run typecheck` (유일한 정적 게이트) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | mode3_held + md 보유 → tally 실행·breakdown 방출 (Gemini 0회) | unit | `pytest tests/pipeline -k mode3 -q` (신규 테스트) | ❌ Wave 0 |
| D-01/D-03 | md 빈 dict → breakdown 미방출 + 점수 불변 | unit | 위와 동일 파일 | ❌ Wave 0 |
| D-02 | overallScore == breakdown.final 항등 (mode3) | unit + Pod sweep | unit + `evals/phase29/assert_gates.py` | ❌ Wave 0 (+ Pod manual) |
| D-08 | mode3 zoom joint = 감점 record 소스, improved 미방출 | unit | `pytest tests/ -k "mode3_fault_zoom" -q` (기존 mode3 zoom 테스트 존재 여부 확인 후 확장) | 확인 필요 |
| D-04~07/14 (앱 카피·게이트) | 렌더 분기 | typecheck + manual | `npm run typecheck` + HUMAN-UAT | typecheck ✅ / UAT 적립 |
| D-11/12 | 가로 전환 + 구빌드 폴백 무크래시 | manual-only (네이티브 회전 — 자동화 불가) | HUMAN-UAT.md 적립 (batch UAT 원칙) | — |
| D-09 | D1 재현·규명 | manual 진단 태스크 (Pitfall 4 체크리스트) | — | — |
| D-13 | 빌드·제출 성공 | build 체인 자체가 검증 | `eas build/submit --non-interactive` | — |

### Sampling Rate
- **Per task commit:** 백엔드 변경 시 관련 tests/pipeline 서브셋 -x, 앱 변경 시 typecheck.
- **Per wave merge:** backend full suite (신규 실패 0 기준) + typecheck.
- **Phase gate:** full suite + Pod sweep 게이트(D-02) + HUMAN-UAT 적립 완료 확인 후 `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/pipeline/test_mode3_tally_seam.py` — D-01/D-02/D-03 (md 유/무 × 등록/미등록 × breakdown 방출/점수 항등)
- [ ] `backend/evals/phase29/` — run_sweep.py + assert_gates.py + eval_keys (phase24 6페어 mode3 변형)
- [ ] mode3 zoom joint 선택 교체분 회귀 테스트 (기존 fault_zoom 테스트 위치 확인 후)
- 앱 신규 테스트 프레임워크 도입은 하지 않음 (프로젝트 컨벤션 — typecheck + 실기기)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (신규 auth 표면 0) | 기존 Firebase ID-token 경로 불변 |
| V4 Access Control | yes (D1 fix 가 /playback-url 확장 시) | 기존 패턴 유지 — 재서명은 요청 uid 소유 리소스만. reference 재서명 신설 시 참조 무결성(임의 S3 키 서명 금지 — referenceMotionId 화이트리스트 경유) 필수 |
| V5 Input Validation | yes | 앱 normalize() 방어 파싱 선례 유지 (malformed doc → undefined, 크래시 0). 백엔드 scoped validator (firestore_admin) — breakdown 은 기존 검증 재사용 |
| V6 Cryptography | no | presigned URL = AWS SDK 서명만 (자체 구현 금지 기존 준수) |
| V14 Config/공급망 | yes | expo-screen-orientation 공식 패키지 + `npx expo install` 버전 고정 + lockfile diff 확인 |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| presigned URL 유출/과다 TTL | Information Disclosure | 7일 TTL 유지 (연장으로 D1 을 풀지 말 것 — 재발급 경로가 정답) |
| /playback-url 로 타인/임의 키 서명 | Elevation of Privilege | uid-scoped 키 조립 유지 (`uploads/{uid}/{analysisId}.{ext}`), reference 확장 시 doc 존재 검증 |
| OTA 번들로 구빌드 크래시 (가용성) | Denial of Service | Pattern 3 lazy require + 구빌드 경로 UAT |

## Sources

### Primary (HIGH confidence — 로컬 실측)
- `backend/functions/pipeline/app.py` — 채점 seam(:2409-2530, :2533-2600), md 빌더(:2225-2380), collect mode3 bail(:1996-2000), MODE_SELF 분기(:3832-), veto 호출부(:4107-4174), 억제(:3175-3230), motionAlignment(:4594-4619), zoom 게이트/사후 렌더(:4478-4491, :4658-4692), mode3 zoom(:2970-3034), `_PLAYBACK_EXPIRES`(:145)
- `backend/shared/python/sunity_shared/analysis/deduction_engine.py` — tally 시그니처(:166-201), fallback 게이트(:196-201), PER_RECORD_CAP(:43)
- `backend/shared/python/sunity_shared/analysis/safety_flags.py` — SafetyFlag 7필드(:86-92, recommendation 부재 확정)
- `backend/judging_data/criteria/ref-{kip-up,peter-pan,elbow-twist-sister,pdshape,power-spin}.yaml` — 4/5 빈 criteria 실측 (2026-06-27 진단 헤더)
- `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py` — yaml→joint_expectations(:267-325)
- `backend/evals/phase24/eval_keys.json` + `evals/phase25/{README.md,run_sweep.py}` — sweep 하네스 계보
- `app/src/app/analysis/result.tsx` — 게이트(:651-906), prev 재발급(:683-706), 비교 섹션(:1373-1486), zoom 진입점(:946-1007)
- `app/src/components/{InjuryRiskSection,ScoreBreakdownSection,VideoCompare}.tsx` — FLAG_COPY(:29-46), 회전 핵(:263-292)
- `app/src/types/analysis.ts` + `backend/shared/.../models.py` + `docs/contract.md` §9.13/§10/§11 — 계약 실측
- `app/{package.json,app.json,eas.json}` + `expo/bundledNativeModules.json` (설치본) — expo-screen-orientation ~9.0.9 / mail-composer ~15.0.8
- unpkg.com/expo-screen-orientation@9.0.9/build/*.js — 최상위 requireNativeModule 실측
- `expo-modules-core` 3.0.29 설치본 — requireOptionalNativeModule 존재 확인

### Secondary (MEDIUM confidence)
- docs.expo.dev/versions/v54.0.0/sdk/screen-orientation/ — lockAsync/unlockAsync/OrientationLock/initialOrientation/iPad split-view 주의 [CITED]
- docs.expo.dev/versions/v54.0.0/config/app/ — orientation 필드 의미 [CITED]
- expo/expo#43802 (2026-03) — react-native-screens ≥4.23 swizzle 이 iOS lock 무력화 [CITED: WebSearch — 프로젝트는 4.16 이라 미해당, 업그레이드 경고용]

### Tertiary (LOW confidence)
- expo/expo#13641, #13184 (구 SDK EAS/iPad lock 이슈) — 구버전 이슈라 현행성 낮음, iPad 주의만 채택

## Metadata

**Confidence breakdown:**
- 채점 seam / 계약 / 앱 게이트: HIGH — 전부 코드 실측 + 라인 확인
- expo-screen-orientation 버전·API: HIGH — 레지스트리 + 설치본 + unpkg 소스 실측
- iOS 런타임 가로 전환의 실기기 동작: MEDIUM — 공식 문서 + 이슈 기반 (A1/A2, HUMAN-UAT 로 판정)
- D1 원인: MEDIUM — 코드 흐름상 최유력 후보 도출 (진단 태스크가 확정)

**Research date:** 2026-07-09
**Valid until:** 2026-08-09 (안정 영역 — 단 Pod 재생성/rns 업그레이드 시 재확인)
