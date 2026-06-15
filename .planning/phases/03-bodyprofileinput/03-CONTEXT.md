# Phase 3: 자가입력 BodyProfileInput - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

게스트(익명 uid)가 **키·몸무게·경력·통증부위·우세손**을 앱에서 1회 선택 입력하고, 그 값이 Firestore 에 저장되어 분석 요청 시 보조 정보로 전달된다. 영상으로 단정 불가한 항목을 보완하는 것이 목적 — Phase 2 의 `BodyNormalizationProfile`(영상 측정 비율)과 **상호보완**.

**범위 고정 (ROADMAP):**
- 받는 항목 = 키·몸무게·경력·통증부위·우세손 **5개만**.
- 유연성·근력 자가입력은 **받지 않음** (부정확).
- 회원가입 게이트 **없음** — 파일럿은 게스트 우선·회원가입 강제 없음 (CLAUDE.md §2). 익명 uid 기준 저장.
- 미입력 사용자도 분석이 graceful (BodyNormalizationProfile 만으로 진행).
</domain>

<decisions>
## Implementation Decisions

### 입력 진입점 / 시점
- **D-01:** 입력 진입점 = **마이페이지 상시 편집 + 첫 분석 직전 1회 가벼운 권유** (둘 다). 게스트가 자연스럽게 입력하되 강제 아님. belle 가 떠올린 "회원가입 후 큐레이션 때 받나" 는 파일럿의 게스트 우선 원칙과 충돌 → **지금, 선택 입력**으로 확정 (회원가입 뒤로 미루지 않음). 정식 출시의 큐레이션 온보딩은 후속(deferred).
- **D-02:** 마이페이지(`app/src/app/(tabs)/profile.tsx`)는 현재 정적 게스트 정보 카드 — Phase 3 가 여기에 BodyProfile 편집 카드/화면을 추가.

### 필드 입력 방식 (빠른 선택형)
- **D-03:** 입력 부담 최소화 — **빠른 선택형**. 탭 몇 번으로 끝.
  - 경력 = **초급/중급/고급 구간 선택** (연차 숫자 아님).
  - 통증부위 = **신체부위 칩 다중선택** (자유텍스트 아님). 부위 목록은 폴스포츠 맥락 상 의미있는 단위(예: 어깨/손목/허리/무릎/발목 등 — 정확 목록은 plan 에서 확정).
  - 우세손 = 좌 / 우 / 양손.
  - 키 = 숫자(cm), 몸무게 = 숫자(kg).

### 분석 활용 방식
- **D-04:** **저장 + 결과화면 표기 + coach_writer LLM 컨텍스트 훅**. 입력값을 결과화면에 표기하고, `coach_writer` 코칭 생성 시 컨텍스트로 주입할 수 있는 **훅(전달 경로)을 박제**한다 (통증부위 회피 언급·경력별 톤 분기 근거). **실 LLM 활성 검증은 Phase 13** (실 LLM 코칭 활성화 phase) — Phase 3 는 데이터가 coach_writer 까지 흐르는 경로만 확보, Phase 13 이 실제로 소비.
- **D-05:** 키·몸무게(`weightKg`/`heightCm`)는 **보조 정보로만** 사용 — 분석 단정 근거로 쓰지 않음 (ROADMAP SC#3). 코드 주석 + 사용처 제한으로 박제. 통증부위·경력은 coach 컨텍스트(D-04)로만, 점수 산출에 직접 가중 X.

### 미입력 / 건너뛰기 처리
- **D-06:** **명확한 "건너뛰기" + 부분 입력 허용 + 재권유 안 함**. 일부 필드만 채워도 OK, 미입력이어도 분석 graceful (SC#4). 첫 분석 권유에서 건너뛰면 다시 강요하지 않고 마이페이지에서 언제든 입력/수정 가능.

### Claude's Discretion
- 통증부위 칩의 정확한 부위 목록 (폴스포츠 맥락) — plan/research 에서 IPSF·도메인 참조로 확정.
- BodyProfile Firestore 저장 위치 (예: `users/{uid}` doc 또는 `users/{uid}/profile`) + 분석 요청 전달 메커니즘(upload 요청 body vs pipeline 이 user doc read) — planner 가 기존 contract 패턴에 맞춰 결정. 단, **3-way contract lockstep** (TS `analysis.ts` ↔ Python `models.py`/`validation.py` ↔ `docs/contract.md`) 준수 필수.
- 결과화면 BodyProfile 표기 위치/형식 — design.md + Figma 우선.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 요구사항 / 로드맵
- `.planning/ROADMAP.md` §"Phase 3: 자가입력 BodyProfileInput" — Goal, Scope 제약, Success Criteria 4개, BODY-02.
- `.planning/REQUIREMENTS.md` — BODY-02 요구사항 원문.

### 데이터 계약 (3-way lockstep — 함께 수정 필수)
- `app/src/types/analysis.ts` — TS 계약 (`UploadUrlRequest` 등). BodyProfile 타입 신설 위치.
- `backend/shared/python/sunity_shared/models.py` — Python 계약 mirror.
- `backend/shared/python/sunity_shared/validation.py` — 입력 검증 (순수 함수).
- `docs/contract.md` — API 계약 단일 소스.

### Phase 2 결합 대상 (보조 입력이 합쳐지는 곳)
- `backend/shared/python/sunity_shared/analysis/body_normalization.py` — `BodyNormalizationProfile` (영상 측정 scale). 자가입력은 이것과 상호보완.

### 분석 활용 (D-04 훅)
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` (+ Gemini `coach_writer_v2.py`) — LLM 코칭 생성. BodyProfile 컨텍스트 주입 지점.

### 설계 / UI
- `design.md` (브랜드 #FF4B33, Pretendard, 라이트 전용) + Figma fileKey `jrdI7kp245HkPfLB0nclsz` (UI 우선 — [[ui-figma-first]]).
- `app/src/app/(tabs)/profile.tsx` — 마이페이지 (입력 진입점 D-01/D-02).
- `app/src/app/(tabs)/analyze.tsx` — 첫 분석 직전 권유 진입점.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/app/(tabs)/profile.tsx` — 현재 게스트 정보 카드(StatBox/InfoRow 헬퍼). BodyProfile 편집 카드 추가 지점.
- `app/src/theme/` 토큰 (colors/spacing/radius) — 입력 폼 스타일은 하드코딩 금지, 토큰 사용 (app/CLAUDE.md).
- `app/src/lib/` 데이터소스 패턴 (`userAnalyses.ts` 의 `normalize()` 방어적 정규화) — BodyProfile Firestore 읽기/쓰기 hook 동일 패턴.
- `app/src/lib/api.ts` (`requestUploadUrl`) — 분석 요청에 BodyProfile 싣는 경로 후보.

### Established Patterns
- **3-way contract lockstep** — 새 BodyProfile 타입은 TS/Python/contract.md 동시 수정 (Cross-cutting 규칙).
- **Firestore 익명 uid 저장** — 게스트도 익명 Firebase Auth uid 보유 (`firebase.ts`, `index.tsx` anonymous sign-in). 기기별 영속.
- **데이터소스 격리** — 화면은 Firestore 직접 모름, `useXxx()` hook 경유.
- **String-literal union** — 경력(초/중/고급)·우세손(좌/우/양) 같은 닫힌 집합은 union 타입 (`type AnalysisMode` 패턴).

### Integration Points
- Firestore `users/{uid}` 영역 (BodyProfile 저장) → 분석 요청/파이프라인이 read → `coach_writer` 컨텍스트 주입(D-04 훅).
- 미입력 graceful: 파이프라인이 BodyProfile 없으면 `BodyNormalizationProfile` 만으로 진행 (SC#4).
</code_context>

<specifics>
## Specific Ideas

- belle 의 원래 고민("지금 받나 vs 회원가입 후 큐레이션") → "게스트 우선 선택입력"으로 정리. 두 직감(지금/큐레이션)이 충돌 안 함 — 파일럿은 "지금·선택", 큐레이션 온보딩은 정식 출시 후속.
- 빠른 선택형 = "탭 몇 번으로 끝나는" 가벼운 입력 (belle 선호 — 입력 부담 최소).
- 입력을 실제 분석 가치로 연결하되(D-04), 실 LLM 소비는 Phase 13 이 담당 — Phase 3 는 경로/훅까지.
</specifics>

<deferred>
## Deferred Ideas

- **회원가입 후 큐레이션 온보딩** — 정식 출시 단계의 가입 플로우에서 BodyProfile + 목표/관심사 큐레이션 수집. 파일럿 범위 밖 (게스트 우선). 후속 마일스톤.
- **유연성·근력 자가입력** — ROADMAP 명시 제외 (부정확). 향후 측정 기반으로 대체 검토.
- **통증부위 → 부상 위험 신호 연동** — Phase 10 (SAFE-01) 에서 통증부위를 injuryRisk 신호와 결합. Phase 3 는 저장+coach 컨텍스트까지만.
- **실 LLM 코칭에서 BodyProfile 소비** — Phase 13 (실 LLM 활성화) 가 D-04 훅을 실제로 검증·활용.

### Reviewed Todos (not folded)
None — todo 교차참조 단계 미실행 (해당 todo 없음).
</deferred>

---

*Phase: 3-bodyprofileinput*
*Context gathered: 2026-06-15*
