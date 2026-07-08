# Phase 29: 결과·비교 화면 완성 — Mode3 내역·줌, 비교영상, 가로 방향, 부상 대응법 - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

결과 화면의 남은 파일럿 gap 일괄 해소 (시나리오 3/6/9). (a) ⑨ 부상 대응법 노출 — `SafetyFlag.recommendation` 데이터가 있는데 `InjuryRiskSection`이 안 그림 (title/why copy map만 렌더, 실측 확인). (b) ③ Mode3 점수 내역 — 백엔드 Mode3 deductionBreakdown 방출 + 앱 mode1 게이트 3곳(내역 섹션·마커·isCleanPass) 확장. (c) ⑥ Mode3 확대비교 배선 + D1 비교영상(Mode1 회귀 진단 + Mode3 비교영상). (d) D4 진짜 가로 방향 — expo-screen-orientation 전환, **새 EAS 빌드 필요, F1 expo-mail-composer(package.json엔 있으나 TestFlight 빌드 27에 네이티브 부재 = 문의하기 안 눌림의 원인)와 같은 빌드에 동승**. Phase 28 의존 — 비교영상·줌이 동작 정렬(motionAlignment) 결과물 소비.

**불변 경계:** mode1 채점·vision veto 경로 무접촉. mode3_held(vision 보류) 유지 — Gemini를 Mode3에 넣지 않는다 (belle 재확인 2026-07-09: 기준 영상 없는 진공 판정 위험 + 속도·비용 역행).

</domain>

<decisions>
## Implementation Decisions

### Mode3 점수 내역 (감점 소스)
- **D-01:** 감점 소스 = **ipsf_absolute 측정 전용** — 등록 동작(kip-up/power-spin/peter-pan/elbow-twist-sister/pdshape, P1 step4 criteria yaml)이면 RTMW 측정값을 객관 IPSF 기준(무릎 신전 180° 등)과 대조해 `deduction_engine.tally` 실행. **Gemini 호출 없음** — mode3_held 불변. 비용·시간 증가 0.
- **D-02:** **Mode3 overallScore = tally(breakdown.final)로 전환** (표시 전용 아님 — 100−Σ감점=점수 항등식 유지, 투명 감점 invariant 준수). 단 **정은지 페어셋 mode3 sweep 검증 게이트(Pod 1회) 통과가 전환 조건**: success=고득점 / fault=감점 변별, cold=warm 결정성. Mode3 첫 분석에도 적용 가능(절대 기준이라 이전 영상 불필요). 성장 델타도 tally 점수 기준으로 일관.
- **D-03:** **미등록 동작 = 현행 절대차원 점수 유지 + 행동 유도 안내.** tally 미실행(기준 없는 감점 0=100 위양성 차단, motion-routing-generalize 정합). 안내는 "제공 불가" 통보가 아니라 **"코치님(정은지) 영상이나 본인 이전 연습 영상과 비교해보세요" 식 행동 유도 메시지** (belle 원문: "친절 메시지가 짜여져야 할 듯").
- **D-04:** **legacy Mode3 doc(내역 없음) = 재분석 유도 배너** — Phase 28 D-05 패턴 재사용. 28 배너와 중복 노출 시 통합은 Claude 재량.
- **D-05:** **한계 고지 1줄 필수** — 내역 아래에 측정 범위 + 다음 행동 유도 결합. 뼈대(belle 승인): "카메라로 잰 자세 형태 기준이에요. 같은 동작을 새 영상으로 다시 올리면 이전 영상과 비교한 발전 분석이 본격 시작돼요. 그립·디테일 점검은 코치님 비교 분석을 이용해보세요." **금지어: "각도"** — (i) 사용자가 못 알아들음(belle 실측, 260705-k8y에서 행동구 라벨로 전환한 이유), (ii) mode3 세부점수 "angle" 차원(=이전영상 유사도)과 용어 충돌, (iii) 각도 수치 전면화는 강사 철학 충돌(현장 리서치).

### Mode3 비교영상·확대비교
- **D-06:** 비교 대상 = **본인 이전 영상 vs 이번 영상** (라벨 "지난 영상/이번 영상" 계열 — 정은지 아님).
- **D-07:** **Mode3 첫 분석(이전 영상 없음) = 비교 섹션 숨김 + 안내 1줄** ("다음 분석부터 이전 영상과 비교해 드려요" 늬낌, D-05 문구와 톤 통일). 정은지 폴백 기각 — mode1과 혼동 + 미보유 동작 reference 부재.
- **D-08:** 확대비교(zoom) 카드 = **결함 부위만** — 이번 분석 감점 부위를 이전 영상 같은 구간과 나란히 확대 (mode1 줌과 동일 개념). 개선 부위 축하 카드는 deferred.
- **D-09:** **D1(Mode1 비교영상 안 뜸, 파일럿 신고) = 진단 태스크로 플랜에 정식 포함** — 재현→원인 규명→fix. Phase 28 변경 연관 가능성 점검.
- **D-10:** Mode3 비교영상도 **Phase 28 워핑 동일 적용** — 이전 영상을 이번 영상 타임라인에 워핑, 신뢰도 사다리(28 D-02)·배속 클램프 0.5~2배 동일. 백엔드 방출(mode3 second+)은 Phase 28 완료분 — 앱 소비만 확장.

### 가로 방향 + EAS 빌드
- **D-11:** expo-screen-orientation 적용 범위 = **전체화면 비교 뷰어만** — 진입 시 가로 전환, 닫으면 세로 복귀. 앱 전체 세로 고정 유지. D4(비율 이상)는 회전 핵 치수 계산 소멸로 근본 해소.
- **D-12:** **구빌드 호환: 90도 회전 핵 폴백 유지** — 런타임에 네이티브 모듈 가용성 감지해 분기 (새 빌드=진짜 가로 / 구빌드=현행 핵). runtimeVersion bump 없이 OTA를 구빌드에도 계속 배포 가능. 핵 코드 제거는 파일럿 이후.
- **D-13:** **새 EAS 빌드·제출 = Phase 29 마감 시** — iOS TestFlight 무인 제출(ASC 자동화 OK) + Android APK 함께. F1(문의하기) 동승 해소. 실기기 확인은 HUMAN-UAT.md 적립(batch UAT 원칙 — 즉시 belle 호출 금지).

### 부상 대응법 노출
- **D-14:** `SafetyFlag.recommendation`을 **카드 내 바로 표시** — 기존 카드(제목+이유) 아래 "이렇게 해보세요" 행 + "정확한 진단은 강사님과 점검하세요" 톤 캡션 (시나리오 불변원칙: 부상 경고 = "강사와 점검", 위험 확정 아님).

### Claude's Discretion
- D-03/D-05/D-07 안내·고지 카피 세부 (뼈대·금지어는 위 결정 준수, 기존 "~해요" 체).
- D-04 배너 문구·위치, Phase 28 배너와 통합 여부.
- mode3 tally의 앱 게이트 확장 구현 방식 (result.tsx mode1 게이트 3곳 — 내역 섹션·마커·isCleanPass — 의 mode 분기 설계).
- 전체화면 뷰어 가로 전환의 상태 처리(진입/이탈 시퀀스), 네이티브 모듈 가용성 감지 방법.
- 계약 필드 설계 — 단 3-way lockstep(analysis.ts + models.py + docs/contract.md) + Firestore flat 규칙 준수.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 근거 (이 phase의 존재 이유)
- `.planning/SCENARIO.md` — 확정 시나리오 v1.0. 단계 3(점수 근거)·6(확대 비교)·9(부상 대응법) + 파일럿 gap 우선순위 #1/#4/#5 + 불변 원칙("강사와 점검" 톤, mode3=발전).
- `.planning/PILOT-FEEDBACK-2026-07-06.md` §D — D1(비교영상 안 뜸)/D4(가로 비율) 원문. §F F1(문의하기 안 눌림)=mail-composer 네이티브 부재.
- `.planning/ROADMAP.md` Phase 29 섹션 — 4개 서브 골 (a)~(d) + F1 동승 빌드 명시.

### Phase 28 산출물 (의존 — 비교·줌이 소비)
- `.planning/phases/28-dtw-motion-based-alignment/28-CONTEXT.md` — D-01(워핑)/D-02(신뢰도 사다리)/D-04(fault_zoom 전신 폴백)/D-05(legacy 재분석 배너) — 본 phase가 그대로 상속·재사용하는 결정들.
- `app/src/components/VideoCompare.tsx` — Phase 28 워핑 소비 완료본 (targetRefTime 단일 경유+rate feedforward+tier 배지). mode3 확장의 삽입 지점.
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — mode3 fps 경로(prev angles 9fps) 이미 존재. Mode3 zoom 배선 지점.

### 채점 (D-01/D-02 대상)
- `backend/functions/pipeline/app.py` — `_process` 채점 seam: mode3_held 게이트(:2462 부근), deduction_engine.tally 호출부, MODE_SELF 분기(:3832). 단일 채점 seam(분기 0, 코드 1벌) 원칙 유지.
- `backend/shared/python/sunity_shared/analysis/deduction_engine.py` + ipsf_absolute criteria yaml (260627-afq: 등록 5동작 무릎 EXTEND 180°) — tally 재사용 대상.
- `backend/evals/` phase 24 계열 — sweep 게이트 패턴 (SERIAL, cold=warm 결정성). D-02 검증 게이트가 이 계보.

### 앱 (수정 대상)
- `app/src/app/analysis/result.tsx` — mode1 게이트 3곳(내역 :906, 마커 :814, isCleanPass :768 부근) + 이전 분석 doc 구독(:678). D-02/D-06/D-07 확장 지점.
- `app/src/components/InjuryRiskSection.tsx` — FLAG_COPY {title, why}만 렌더 — D-14가 recommendation 행 추가.
- `app/src/components/ScoreBreakdownSection.tsx` — mode1 내역 렌더 정본. mode3 재사용 대상.
- `app/src/types/analysis.ts` + `backend/shared/python/sunity_shared/models.py` + `docs/contract.md` — 3-way lockstep.

### 빌드 (D-11~13)
- `app/package.json` — expo-mail-composer ~15.0.8 있음 / expo-screen-orientation 없음(설치 필요, 네이티브).
- `app/eas.json` + `app/app.json` — 빌드 프로필·submit 설정 (appVersionSource=remote, ASC 6772934567 무인 제출).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 28 motionAlignment 방출 — **mode1+mode3 second+ 둘 다 이미 방출됨** (28-04). Mode3 비교영상 워핑은 앱 소비 확장만.
- fault_zoom mode3 fps 하위호환 경로(28-05) — Mode3 zoom 배선의 절반이 이미 깔림.
- `previousAnalysisId` 구독(result.tsx:678) — 이전 영상 URL·점수 이미 확보. 비교영상 소스로 재사용.
- deduction_engine.tally + ipsf_absolute criteria(등록 5동작) — D-01이 새 엔진 없이 기존 것 재사용.
- ScoreBreakdownSection·buildDeductionMarkers·composeScoringBasisKo — mode1 내역 렌더 체계 전체를 mode3에 재사용.
- Phase 28 D-05 재분석 배너 — D-04가 패턴 재사용.

### Established Patterns
- 채점 seam 단일 경로(분기 0, 코드 1벌) — mode3 tally도 같은 seam에서, mode별 criteria 소스만 분기.
- 계약 optional 필드 + legacy 폴백 (faultZoomStatus/tier 선례) — mode3 breakdown 필드도 optional, 없으면 현행 렌더.
- Firestore nested-array 금지 → flat 저장.
- 파일럿 검증 게이트 = Pod sweep SERIAL + cold=warm 결정성 + calibration-source-hard-gate(자기 sweep 재보정 금지).
- OTA(JS-only) vs 네이티브 빌드 분리 — 이번 phase는 둘 다 있음: Mode3 내역·줌·부상은 OTA 가능, 가로·F1은 네이티브 빌드 필요. 플랜에서 분리 배치 권장.

### Integration Points
- 파이프라인 `_process` MODE_SELF 분기 → complete_analysis (breakdown 필드 방출).
- result.tsx mode 분기 3곳 + VideoCompare props + InjuryRiskSection.
- EAS 빌드 체인: expo-screen-orientation 설치 → eas build(iOS+Android) → eas submit --id 무인 → HUMAN-UAT 적립.

</code_context>

<specifics>
## Specific Ideas

- belle 확답 요구 사항(2026-07-09): Mode3 = "Gemini 눈 없이 RTMW 자만" 구조를 이해하고 승인. 단 **사용자에게도 이 구조가 설명돼야 함** — D-05 고지가 그 답. "설명을 해줘야 이해된 기준이 생기겠지".
- belle 카피 방향: "더 연습하고 새로운 영상으로 같은 자세를 비교하면 본격 분석이 시작된다" — 첫 분석·미등록 안내 모두 이 전진형 유도 톤.
- "각도" 단어 회피 — belle이 기존 화면들에서 "각도" 표현 남발을 직접 지적. 행동·부위 중심 표현으로.

</specifics>

<deferred>
## Deferred Ideas

- **Mode3 개선 부위 축하 카드** — 시나리오 +α "성공 순간 축하"와 연결. improved/worsened 판정 로직 별도 phase.
- **90도 회전 핵 코드 제거** — 파일럿 이후 구빌드 소멸 시.
- **vision veto Mode3 확장** — 기각 아닌 보류 유지. Phase 22 자체 VLM이 저비용 판정 가능해지면 재검토.
- **미등록 동작 criteria 등록 확대** — 도메인 기준 수립(belle/정은지) 필요, 별도 트랙. deferred-selfservice-reference-registration과 연결 후보.

</deferred>

---

*Phase: 29-mode3-result-screen-completion*
*Context gathered: 2026-07-09*
