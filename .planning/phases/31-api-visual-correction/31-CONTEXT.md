# Phase 31: api-visual-correction - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning — **D-02 해소됨 (2026-07-18): 생성 엔진 = Wan2.7-VideoEdit 확정.** GEN3C(007b) 판정 완료 = 중앙 MAE 41.1°(Wan2.7 9.9°의 4배)·이봉분포·인체 붕괴 → 부적격, Wan2.7 유지. 상세 = spike 004 README §007b.

<domain>
## Phase Boundary

"어떻게 고쳐야 하는지"를 눈으로 보여주는 시각 출력 phase. 두 층:
(1단) 기하 오버레이 — 목표 각도 화살표를 원본 영상/줌 카드 위에 렌더 (보유 데이터만, 비용 0)
(2단) 생성 시각물 — 교정 실루엣 이미지 + 카메라앵글 회전 참고코너 (spike 004/006/008 검증 완료 엔진 사용)
부산물 = `[틀린 폼→고쳐진 폼]` 페어 적재 → phase 22 재도전(플라이휠 옵션 C) 원료.
**phase 22 실패와 무관하게 성립** — 31은 22의 소비자가 아니라 공급자 (2026-07-17 belle 확인).
**[AMENDED 2026-07-20, 9차 B9-04 — belle 위임 후 planner 결정]:** pair 는 부산물이므로 **사용자 표시·cleanup·finalize 의 critical path 를 막지 않는다** — pair store 는 cleanup 직전 단일 시도(source 존재 구간)이고, 네트워크 일시장애(network/5xx) 시 `pairStoreStatus='failed'` 로 진행하며 durable 재시도를 하지 않는다. **해당 pair 는 유실을 수용한다**(플라이휠은 대량 볼륨 목적이라 개별 pair 손실 영향 미미). 손실이 누적되면 운영 재처리로 보강. durable pair outbox 는 파일럿 범위 밖(후속 phase 후보).

</domain>

<decisions>
## ★ SETTLED AXES — 리뷰어 재개 금지 (belle 2026-07-20, Q1 응답)

아래 축은 belle 지시로 **확정**됐다. 후속 리뷰는 이 축의 *설계 선택*을 재논의하지 말고, 선택된 설계의 *closure(계약·fault test)* 만 검증한다.

- **임시 생체 프레임 privacy SLA = "즉시 삭제(하드 크래시에도 보장)" — 현행 유지 확정.** 24h-lifecycle-only 로의 단순화는 belle 가 배제했다. 따라서 per-invocation reservation + key-level ownership(`visualInputObjects/{hash}`) + crash-recoverable janitor(claim lease/owner) machinery 는 **의도된 설계**이며, "복잡하니 없애자"는 리뷰 금지. B9-01/02/03 은 이 설계 *안에서* 닫는다(janitor lease 복구·cross-reservation same-key ownership·multi-object expected∪created).
- **비-버저닝 전용 VisualInputBucket 아키텍처(6차)** — 확정, 재논의 금지.
- **pair 네트워크 실패 = 단일 시도 + 손실 수용(9차 B9-04 amended, 위 D-01 각주)** — durable outbox 재제안 금지.
- **D-06 완료 알림 실체** = **확정(2026-07-20, belle — 31-11 Task1c: option B)**. 아래 D-06 [AMENDED] 참조. 열린 축 0.

## Implementation Decisions

### 스코프 구성
- **D-01:** 1단+2단 풀통합 — 오버레이 + 교정 실루엣(이미지) + 회전 참고코너 전부 이번 phase.
- **D-02:** 생성 엔진 = **Wan2.7-VideoEdit 확정** (2026-07-18 GEN3C 판정 완료). GEN3C(007b, 오픈)는 중앙 MAE 41.1°·이봉분포·역위/급격모션 인체붕괴로 부적격 — Wan2.7(spike 008 승자, MAE 중앙 9.9°) 유지. plan은 여전히 엔진 스왑 가능하게 추상화(VisualGenEngine 류) — GEN3C 는 depth 파이프라인 개선 후 재평가 후보(deferred). 키 = SSM `/sunity/motion/dashscope-api-key`.
- **D-03:** 교정 실루엣 = **정지 이미지 1장 먼저** (결함 top-1 부위의 순간 프레임 → 고친 폼). 영상 승격은 후속 phase. 이미지 생성 모델 사용 (수초~수십초, 수백원 내외 — Wan2.7-Image-Pro/Qwen-Image 등은 research 에서 선정).
- **D-04:** 회전 참고코너 = **하이브리드** — 기본 R3F 수학 3D 뷰어(환각 0·비용 0·즉시·인터랙티브, Spike 005 아키텍처) + Wan2.7 합성 영상은 옵션.
  - **[AMENDED 2026-07-19, belle — 31-PLAN-REVIEW B-01]:** "R3F 3D 뷰어" 표기는 성립 불가로 재결정 — 사용자·reference 좌표 **모두 RTMW = depth 부재**(`result.tsx:1191` 2026-06-21 제거 결정과 동일 근거, reference 도 `reprocess_reference_motions_phase4.py` RTMW 처리). **회전은 Wan2.7 합성 영상이 전담**(옵션 아닌 유일 회전 수단). 즉시·비용0 대체재는 D-10 의 2D 비교 뷰어.

### 생성 시점·비용 정책
- **D-05:** 교정 실루엣(이미지) = **분석 완료 시 자동 생성** (top-1 결함 부위만) — 첫 분석의 "전문가 수준" 인상(core value) 정합.
- **D-06:** 회전 합성 영상(건당 ~6-7분·과금) = **온디맨드 + 완료 알림** — 버튼 → 백그라운드 생성 → 카드 갱신. R3F 뷰어가 대기 중 즉시 대체재.
  - **[AMENDED 2026-07-20, belle — 31-11 Task1c option B]:** "완료 알림"의 실체는 **결과 화면이 열려 있는 동안의 실시간 갱신(Firestore `onSnapshot`)** 으로 축소 확정. **푸시/로컬 알림은 이번 phase 에서 구현하지 않는다** — `expo-notifications` 미설치 유지.
    - **사유:** 회전 영상은 **비채점 참고코너** 기능이다. 푸시 알림을 넣으려면 알림 권한 UX + 푸시 토큰 등록/저장 + 백엔드 발송 인프라를 새로 들여와야 하고, 이는 파일럿 범위를 넓힌다. 비용 대비 우선순위가 낮아 **별도 작업으로 분리**한다.
    - **사용자 경험(정직한 기술):** 6-7분 대기 중 화면을 닫으면 완료를 즉시 인지할 수 없다. 사용자는 **결과 화면을 다시 열어** 완료를 확인한다. 이 축소는 의도된 것이며 침묵 축소가 아니다.
    - **범위 경계:** 알림은 회전 영상만의 문제가 아니다. Figma 에 이미 `알림` 프레임과 "분석 결과를 알림으로 알려드려요" 카피가 존재하므로, **분석 완료 알림까지 아우르는 독립 기능**으로 다뤄야 한다. belle 도 이를 인지한 상태에서 B 를 선택했다. 후속 작업자는 이 범위를 31 안에서 넓히지 말 것.
- **D-07:** 비용 가드 = **사용자당 일일 생성 한도** (구체 수치는 planner 재량, 파일럿 규모에서 사실상 무제한이되 남용 방지).
- **D-08:** 모더레이션 차단(실측 ~10%) 시 = **조용한 폴백** — 실패 미강조, R3F 뷰어/오버레이만 표시. "기능이 불안하다" 인상 방지.

### 참고코너 UX
- **D-09:** 배치 = 결과 화면 **점수 내역 아래 "참고하세요" 섹션** — 채점과 시각적으로 분리 (점수 비반영 원칙이 레이아웃으로 드러나야 함).
- **D-10:** R3F 3D 뷰어 기본 표시 = **내 자세(실측 스켈레톤) + 목표 자세 반투명 중첩**, 손가락 드래그 회전.
  - **[AMENDED 2026-07-19, belle — 31-PLAN-REVIEW B-01 재결정]:** **2D 비교 뷰어로 확정** — 회전 없음(RTMW depth 부재로 정직한 회전 불가), 카메라 평면 고정, 내 자세+목표 자세 반투명 중첩으로 "어디가 다른지"만 표시. 팬/줌/프레임 스크럽 허용. "3D"/"회전" 문구 사용 금지. 프레임 대응 = DTW 매칭 결함 프레임(v1 = 피크 프레임 1장). 회전 니즈는 D-04 Wan2.7 영상 전담. 진짜 3D 는 자체학습 트랙(Phase 22 계열) 이후 재검토 — belle: "더 학습하는 모델 필요, phase 22 에서 나눴던 것처럼".

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
- GEN3C 오픈 모델 재평가 — 2026-07-18 판정 = 현 monocular depth(MoGe) 파이프라인에서 부적격(중앙 41.1°). **재도전 조건 = depth 소스 개선**(멀티프레임/실카메라궤적/foreground masking). 잘 맞는 클립은 <6°로 Wan2.7 상회 → 개선 시 잠재력 있음. 구동 스텁은 볼륨 박제(재현 가능)
- 카메라앵글 재렌더의 측정(점수) 투입 — phase 22 자체 학습 트랙과 동행 재도전

</deferred>
