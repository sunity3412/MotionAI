# Phase 31: api-visual-correction - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning (엔진 확정은 GEN3C 판정 대기 — D-02 참조)

<domain>
## Phase Boundary

"어떻게 고쳐야 하는지"를 눈으로 보여주는 시각 출력 phase. 두 층:
(1단) 기하 오버레이 — 목표 각도 화살표를 원본 영상/줌 카드 위에 렌더 (보유 데이터만, 비용 0)
(2단) 생성 시각물 — 교정 실루엣 이미지 + 카메라앵글 회전 참고코너 (spike 004/006/008 검증 완료 엔진 사용)
부산물 = `[틀린 폼→고쳐진 폼]` 페어 적재 → phase 22 재도전(플라이휠 옵션 C) 원료.
**phase 22 실패와 무관하게 성립** — 31은 22의 소비자가 아니라 공급자 (2026-07-17 belle 확인).

</domain>

<decisions>
## Implementation Decisions

### 스코프 구성
- **D-01:** 1단+2단 풀통합 — 오버레이 + 교정 실루엣(이미지) + 회전 참고코너 전부 이번 phase.
- **D-02:** 생성 엔진은 **GEN3C(007b) 판정 후 확정** — plan은 엔진 스왑 가능하게 추상화(PoseEngine 추상화 선례 준용, VisualGenEngine 류). 잠정 1순위 = Wan2.7-VideoEdit (spike 008 승자, MAE 중앙 9.9°). plan-phase 착수는 GEN3C 판정 이후.
- **D-03:** 교정 실루엣 = **정지 이미지 1장 먼저** (결함 top-1 부위의 순간 프레임 → 고친 폼). 영상 승격은 후속 phase. 이미지 생성 모델 사용 (수초~수십초, 수백원 내외 — Wan2.7-Image-Pro/Qwen-Image 등은 research 에서 선정).
- **D-04:** 회전 참고코너 = **하이브리드** — 기본 R3F 수학 3D 뷰어(환각 0·비용 0·즉시·인터랙티브, Spike 005 아키텍처) + Wan2.7 합성 영상은 옵션.

### 생성 시점·비용 정책
- **D-05:** 교정 실루엣(이미지) = **분석 완료 시 자동 생성** (top-1 결함 부위만) — 첫 분석의 "전문가 수준" 인상(core value) 정합.
- **D-06:** 회전 합성 영상(건당 ~6-7분·과금) = **온디맨드 + 완료 알림** — 버튼 → 백그라운드 생성 → 카드 갱신. R3F 뷰어가 대기 중 즉시 대체재.
- **D-07:** 비용 가드 = **사용자당 일일 생성 한도** (구체 수치는 planner 재량, 파일럿 규모에서 사실상 무제한이되 남용 방지).
- **D-08:** 모더레이션 차단(실측 ~10%) 시 = **조용한 폴백** — 실패 미강조, R3F 뷰어/오버레이만 표시. "기능이 불안하다" 인상 방지.

### 참고코너 UX
- **D-09:** 배치 = 결과 화면 **점수 내역 아래 "참고하세요" 섹션** — 채점과 시각적으로 분리 (점수 비반영 원칙이 레이아웃으로 드러나야 함).
- **D-10:** R3F 3D 뷰어 기본 표시 = **내 자세(실측 스켈레톤) + 목표 자세 반투명 중첩**, 손가락 드래그 회전.

### 1단 오버레이
- **D-11:** **목표 각도 화살표부터** ("여기까지 올려야 함" 화살표 + 목표선) — 이상 궤적 선·힘 벡터는 후속.
- **D-12:** 적용 위치 = **기존 결함 줌 카드 위** — 기존 동선/컴포넌트 재사용, 신규 화면 0.

### Claude's Discretion
- 일일 한도 수치, 화살표/중첩 시각 스타일(단 theme 토큰·design.md 준수), R3F 씬 구성 상세, 이미지 생성 모델 선정(research 비교), 실루엣 프롬프트 설계.
- UI 작업 전 [[ux-propose-user-centric-screens-first]] — 최악 데이터 케이스 목업 선제시.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/spikes/004-gemini-omni-view-editing/README.md` — **spike 004/006/008 전체 결과** (Omni PARTIAL·MAE 22.8° / PR 인버전 한정 −58% / Wan2.7 WINNER·MAE 9.9°·차단 10%·watermark off·SDK 사용법·journal 멱등 패턴). 엔진 코드 `wan_gate_batch.py` 재사용 가능.
- `.planning/spikes/MANIFEST.md` — Requirements 섹션 (라이선스 게이트, 단일 카메라 UX 불변, IPSF 기준, belle 제품 방향 박제).
- `.planning/spikes/005-frontend-3d-viewer/README.md` — R3F+expo-three 아키텍처 (MIT×4 상업 OK), Decoupling 4-stage.
- 메모리 `camera-angle-scoring-stretch-reference-corner` — **점수 비반영 invariant**: 참고코너는 비채점, 점수 반영은 게이트 통과 시만.
- 메모리 `learning-consent-pilot-mandatory` + phase 22 `22-04` learningOptIn 게이트 — **페어 적재는 학습 동의 사용자만**.
- Wan2.7 키 = SSM `/sunity/motion/dashscope-api-key` (SecureString, belle 계정). 시크릿 하드코딩 금지.
- `docs/contract.md` + `app/src/types/analysis.ts` + `backend/.../models.py` — 계약 3면 동시 수정 원칙 (실루엣 URL/참고코너 필드 방출 시).

</canonical_refs>

<constraints>
## 제약 (invariant)

- 카메라 앵글/실루엣 산출물은 **점수에 반영 금지** (stretch goal 게이트 미통과 상태 — spike 008 outlier 존재).
- 단일 카메라 UX 불변 — 다각도 촬영 요구 노출 절대 금지.
- 모더레이션 차단은 사용자에게 에러로 노출하지 않음 (D-08).
- Firestore nested-array 금지, 시크릿 Parameter Store, 브랜드 #FF4B33/Pretendard/라이트 전용.
- 페어 적재 = learningOptIn=true 사용자만, PII 정책 준수.

</constraints>

<deferred>
## Deferred Ideas

- 교정 실루엣 **영상** 버전 (D-03 후속 승격)
- 이상 궤적 선·힘 방향 벡터 오버레이 (D-11 후속)
- GEN3C 오픈 모델 자체 호스팅 전환 (판정 후 별도 결정)
- 카메라앵글 재렌더의 측정(점수) 투입 — phase 22 자체 학습 트랙과 동행 재도전

</deferred>
