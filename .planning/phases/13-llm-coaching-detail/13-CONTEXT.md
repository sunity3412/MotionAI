# Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성 - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

분석 결과(Phase 9 실패 원인 후보 + 체형 정규화 finding + BodyProfile 통증부위)에 맞는 **보완 운동·스트레칭을 자동 매핑**해 결과 화면에 표시하고, **실 Cerebras LLM**이 `tip.detail2`(causes/injuryRisk/coachNote)를 동적 생성하며, 동작의 **IPSF 등재 여부(`ipsfCode`)로 차원 자세히 모달 카피가 분기**(분기1 세계 심사기준 / 분기2 정은지 선수 기준)되는 것.

ROADMAP success criteria 1-8 이 scope 앵커. 신규 능력(연령·성별 맞춤 등)은 다른 phase.
</domain>

<decisions>
## Implementation Decisions

### 규준 맞춤 범위 (belle 2026-06-16)
- **D-01:** 연령·성별 입력 + 국민체력100 규준 맞춤은 **v2 연기**. 지금은 예약만 — REQUIREMENTS.md `PERS-04` 신설 완료 + 아래 Deferred 박제. 근거: (1) PROJECT.md 가 "체형 입력+맞춤 피드백"·"부상 위험 경고"를 이미 v2 연기, (2) NotebookLM 리서치 — 연령·성별 의학적 차이/성장기 과신전 위험에 **학술 근거 부재**(과신전은 IPSF 심사규정 맥락만, 성장판 자극은 학원 홍보 멘트). 의학근거 없는 맞춤은 "일반적 답변" 리스크 → 핵심가치(위양성 없음) 위배.
- **D-02:** fixture `backend/judging_data/fitness_norms_kspo.yaml`(커밋 3c937d9)은 v1 에서 **커밋된 채 대기**. v2 wiring 시 즉시 사용. v1 Phase 13 은 이 fixture 를 소비하지 않는다.

### 보완운동 매핑 (Q2 — belle 추천 채택)
- **D-03:** 매핑 입력 = **Phase 9 실패 원인 후보 + BodyProfile `painAreas`(기존 필드)**. 국민체력100 규준은 v1 매핑 입력에서 제외(D-01 정합). 체력은 영상 측정 불가라 자동 등급배치 금지.
- **D-04:** 보완운동 라이브러리는 **greenfield**(기존 스캐폴딩 없음). NotebookLM 리서치가 결함별 구체 운동을 다 제공 → 그대로 큐레이션(아래 Specifics). 초기 3~5 동작군 + 결함당 운동 5~10개(ROADMAP scope 제약 정합).

### 플랜 분할 (Q3 — belle 추천 채택)
- **D-05:** Phase 13 = **플랜 2개 분리**.
  - **Plan A** = 보완운동 라이브러리 + 매핑 로직 + 결과 화면 표시 + "다른 운동 보기"(criteria 1-4). GPU/Pod 불필요, fixture 단위테스트.
  - **Plan B** = 실 Cerebras LLM 활성화 + `ipsfCode` 분기 카피 + coach_writer 프롬프트 주입(criteria 5-8). 분기/프롬프트 로직은 순수, **단 criteria 5(실 영상→실 LLM tip.detail2 E2E) 검증은 Pod 필요**(아래 Integration Points).

### 리서치 비중 (belle 지시)
- **D-06:** 리서치 비중 상향 + **NotebookLM 필수**. plan-phase 의 gsd-phase-researcher 는 아래 canonical NotebookLM 노트북을 1차 소스로 쓸 것. 이미 수행한 2개 쿼리 결과는 Specifics 에 박제 — 보완운동 라이브러리 초안의 근거.

### Claude's Discretion
- 보완운동 라이브러리 저장 형태(JSON fixture vs Firestore)는 planner 재량. 단 contract-first 정합(앱↔백엔드 타입 동시 갱신).
- IPSF Code 매핑 테이블을 `studio-term-3branch` 데이터로 흡수할지 별도 둘지는 planner 재량.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 로드맵·요건
- `.planning/ROADMAP.md` §"Phase 13" — Goal + Success Criteria 1-8 + Scope 제약(3~5 동작군, 분기1·2 만 v1)
- `.planning/REQUIREMENTS.md` — `PERS-03`(v1, 보완운동), `SCORE-05`(5트랙), `PERS-04`(v2 예약 — 규준 맞춤), `TERM-*`
- `.planning/PROJECT.md` — 핵심가치(분석 정확도, 수치는 보조 원인이 핵심) + v2 연기 목록("체형 입력+맞춤 피드백")

### 데이터·fixture
- `backend/judging_data/fitness_norms_kspo.yaml` — 국민체력100 규준(v2 PERS-04 용, v1 미소비). 헤더에 용도 제약 박제.
- `backend/judging_data/criteria/` + `backend/judging_data/README.md` — IPSF GeometricCriterion(JUDGE-DATA-01), `ipsfCode` 분기 카피 근거
- `backend/data/aka-mapping.json`, `backend/data/reference-motions-branch2.json` — 학원 용어 3분기(`studio-term-3branch`)

### 코드 통합 지점
- `backend/shared/python/sunity_shared/analysis/assemble.py` (`build_dimension_explanation` L63) — `ipsfCode` 분기 추가 대상(현재 mode-aware baseline 만)
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` (`tip.detail2` 구조 L50-78) — 실 LLM + 프롬프트 주입 대상
- `backend/shared/python/sunity_shared/models.py` L37-126 — BodyProfile(painAreas 등), D-05 자가입력 scoring 유입 금지
- `app/src/types/analysis.ts` — 3-way 계약 미러(보완운동·tip 타입 추가 시 동시 갱신)

### NotebookLM (D-06 — researcher 1차 소스)
- 노트북 `96b061e8-bb7c-41c5-8606-8ceef2ce1aa3` "IPSF Rules and Advanced Strength Pole Moves Guide"(70소스) — 결함별 보완운동 + 기술별 요구능력 + IPSF Code 매핑
- 노트북 `e688fb4e-a4fb-4e83-a168-9c4726a98e09` "폴스포츠에 대한 지식"(40소스) — 통증부위별 보강 + LTAD progression
- memory: `notebook-lm-pole-sports`(query 먼저), `gemini-vision-active-use`

### 메모리
- `kspo-fitness-norms-report-context`, `scoring-dimensions-ipsf`, `studio-term-3branch-system`, `mode3-progress-not-similarity`, `analysis-objectivity-no-human-scores`, `judging-baseline-ipsf-code-of-points`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_dimension_explanation`(assemble.py:63): mode-aware baseline 이미 존재 → `ipsfCode` 분기만 추가(criteria 6).
- `coach_writer` `tip.detail2`(causes/injuryRisk/coachNote) 스키마 + 시스템 프롬프트 이미 존재(12.5) → 실 Cerebras 호출 활성화 + 동작명/분기/IPSF 각도 fixture 주입(criteria 5·7).
- BodyProfile `painAreas`(self-input, Phase 3) → 보완운동 매핑 입력(criteria 3). 단 D-05: scoring 유입 금지, 매핑/코칭 레이어만.

### Established Patterns
- 보완운동 라이브러리 스캐폴딩 **없음(greenfield)** — 자유롭게 설계.
- contract-first: analysis.ts ↔ models.py ↔ contract.md 동시 갱신.
- coach_writer 키 없으면 graceful no-op(lazy import).

### Integration Points
- **Pod 의존(criteria 5 검증 한정):** 실 영상 → RTMW/NLF 포즈 → `_process` → coach_writer 실 Cerebras → Firestore `tip.detail2`. 코드 작성·단위테스트는 Pod 불필요(fixture). E2E 검증 시점에만 Pod 기동 + Cerebras 키 Pod env 주입 + uvicorn 재시작 필요. memory `pod-ops-claude-runs`, `runpod-gpu-env`, `next-pod-use-network-storage`.
</code_context>

<specifics>
## Specific Ideas

**NotebookLM 리서치 결과 — 보완운동 라이브러리 초안 근거(출처 인용 노트북에):**

결함별 운동:
- 그립/악력 부족 → cup grip 버티기, 전완근 매달리기, farmer's walk, hand grippers
- 어깨 불안정·전인 → break the bar 3×8, single-arm down dog 3×10, incline rows 3×8, push-up(수직당기기 편중 상쇄)
- 코어 약함(anti-rotation) → elbow plank taps 2×20, hanging leg raise, russian twist, superman
- 다리 안 펴짐 → 고관절굴곡근+코어 근력 + 햄스트링 유연성, fan kick(stepping stone)
- 고관절/햄 유연성 → lunge, lunge(뒷다리 잡기), pigeon, half split, forward fold, lying hamstring
- 통증부위별: 어깨=push/pull 균형+arm circle / 손목=grip+farmer's walk / 허리=plank·side plank·russian twist / 무릎=squat·lunge·quad·hip flexor 스트레칭

기술별 요구능력(criteria 7 각도 fixture + 보완운동 게이트 근거):
- Ayesha(아이샤): 어깨 굴곡 180° + supine IR 60° + forearm pronation 80° + 코어 anti-rotation
- Iron X(아이언엑스): spine neutral/lateral + obliques + split/cup grip
- Invert: 강한 코어 + 고관절 굴곡근(없으면 straight-leg invert 불가)
- 안전 게이트: 핸드스프링/데드리프트 = Ayesha "strong & consistent" 이후에만(부상 경고)

progression: 입문(fan kick·기초 그립) → 초중급(chopper/invert·leg hang·유연성) → 전문가(shoulder mount·ayesha → 핸드스프링)

**IPSF Code 매핑(criteria 6·8 + studio-term):** Ayesha=아이샤=F101/S102, Iron X=아이언엑스=S201/S202, Shoulder Mount=숄더마운트=S103/S104, Inside Leg Hang=인사이드레그행/스콜피오=F303/F304, Jade Split=제이드스플릿=F201/F202, Deadlift=데드리프트=T101/T102 등(노트북 96b061e8 표 전체).
</specifics>

<deferred>
## Deferred Ideas

- **연령·성별 입력 + 국민체력100 규준 맞춤 리포트 맥락** → **v2 PERS-04**(REQUIREMENTS.md 신설 완료). BodyProfile age band + gender 입력(미성년 동의), 규준 join("또래 1등급 상대악력 ~45% 참고"), 연령·성별 맞춤 코칭 톤. fixture 는 이미 커밋(3c937d9)되어 v2 는 wiring 만. v1 미포함(D-01).
- **부상 위험 경고(SAFE)** 의 본격 UI — PROJECT.md 상 v2. Phase 13 의 `injuryRisk`(tip.detail2 한 줄)는 LLM 출력 수준으로만 유지.
- 회차별 성장 그래프, 영상 인앱 다운로드 등 — PROJECT.md v2 목록.

### Reviewed Todos (not folded)
None — todo 매칭 없음.
</deferred>

---

## 13-C: 섹션형 듀얼 coach 보고서 (belle 2026-06-16, 추가 plan — Wave 3)

> 13-A·13-B 완료 후 belle 가 추가. coaching detail = 본 phase 도메인이라 phase 19 신설 X, 13-C 로 처리. 머지(섞기) 아님 — **출처별 라벨 섹션 분리**.

<decisions_13c>
- **섹션 역할 배분 (locked):** 원인(왜 안 되는지)=**Gemini** / 교정 처방(무엇이 필요한지)=**Cerebras** / 부상 위험=**Cerebras** / 강사 확인=**Gemini**. belle 핵심가치 "왜 + 무엇" 직접 매핑. [[section-dual-coach-report]]
- **레이아웃:** 자세히 모달 안 **세로 스택(스크롤)**, 순서 원인→처방→부상위험→강사확인. Phase 12.5 modal 패턴 재사용. (탭/아코디언 기각 — 원인+처방 동시 비교가 핵심)
- **출처 라벨:** **기능 라벨만** 노출("원인 / 교정 처방 / 부상 위험 / 강사 확인"). AI/벤더명(Gemini/Cerebras) 숨김 — 수강생은 내용이 중요.
- **실패 처리 = 계층형:** (1) 두 writer 동시 호출 + **재시도 1회 + 짧은 타임아웃** → 평상시 항상 이상적 페어링. (2) 재시도 후 한쪽 실패 → **다른 LLM이 그 섹션 대신 채움**(빈 섹션 금지). (3) 둘 다 실패 → 기존 수치/단일 폴백(최후 바닥). 편차(B)는 실제 provider 장애 구간으로만 한정. 실패 확률은 낮음(파일럿 규모 rate-limit≈0, 소프트 파싱실패는 `_normalize_entry`가 흡수).
- **보완운동(13-A) 관계:** **별도 유지.** 화면 하단 보완운동 카드(13-A) = 큐레이션 라이브러리 / Cerebras 처방 섹션 = 동적 LLM 텍스트 — 성격·출처 다름, 통합 X(중복 아니라 보강).
- **검증:** coach **성공/폴백률 로깅** 추가(추정→파일럿 실측 전환). "실증 시 둘 중 하나 drop 여부" = **Phase 15** 검증 기준(13-C 빌드 ≠ drop 결정).
- **파일럿 기본값:** 현재 단일 Gemini(`GEMINI_COACH_ENABLED=1`). 13-C 가 섹션용으로 양쪽 활성 — toggle("택1")을 "둘 다 호출 + 섹션 조립"으로 확장.
</decisions_13c>

<code_context_13c>
- **dual-track 이미 존재:** `pipeline/app.py` `_coach_enabled()`/`_GEMINI_COACH_WRITER` + `_COACH_WRITER`(Cerebras). 13-C = toggle 분기를 "둘 다 호출 후 섹션별 조립"으로 확장. 양쪽 writer 가 단일 `_build_coach_context` 공유(기존).
- **detail2 계약:** `{causes[], injuryRisk, coachNote}` (`coach_writer.py` `_build_prompt` / `assemble.py` `_normalize_*` / `app/src/types/analysis.ts` 3-way lockstep). 출처 태깅 방식(source 필드 추가 vs 섹션 구조) = planner 결정.
- **UI:** `app/src/app/analysis/result.tsx` 자세히 모달 + `RecommendedExerciseModal.tsx`(13-A) + Phase 12.5 modal 패턴. 라이트 테마 / brand #FF4B33 토큰.
- **검증 코드:** `coach_writer.py` graceful 폴백 기존 — 재시도/타임아웃/섹션 조립 신규.
</code_context_13c>

<canonical_refs_13c>
- `.claude/projects/.../memory/section-dual-coach-report.md` (13-C 결정 박제 — MUST read)
- `backend/shared/python/sunity_shared/analysis/coach_writer.py` (CerebrasCoachWriter + _build_prompt)
- `backend/functions/pipeline/app.py` (_coach_enabled dual-track + GeminiCoachWriter)
- `backend/shared/python/sunity_shared/analysis/assemble.py` (build_result / detail2 normalize / branch)
- `app/src/types/analysis.ts` (detail2 계약 — 3-way lockstep)
- `app/src/app/analysis/result.tsx` + `app/src/components/RecommendedExerciseModal.tsx` (UI)
</canonical_refs_13c>

---

*Phase: 13-llm-coaching-detail*
*Context gathered: 2026-06-16 (13-A/13-B) · 13-C 추가: 2026-06-16*
