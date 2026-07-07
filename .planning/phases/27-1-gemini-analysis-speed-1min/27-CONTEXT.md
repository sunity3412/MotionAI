# Phase 27: 분석 속도 1분 — Gemini 라운드트립·후처리 축소 - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

mode1 분석 대기 경험 개선 (시나리오 2 — 대기 경험). 실측 분해(power-spin 3분17초, 2026-07-06): 포즈 ~51s + Gemini 비전 2단 ~52s(File API 업로드+폴링) + 후처리 ~49s(fault_zoom 렌더+Firestore) — 단일 범인 없음. 레버 = 겹치기(파이프라인 내 병렬) + 전송 축소 + 후처리 사후 분리 + 대기 중 체감 개선. **Phase 22 shadow 전환 시 Gemini 라운드트립 자체가 소멸하므로 중복 투자 금지 — 저비용 레버 우선.**

</domain>

<decisions>
## Implementation Decisions

### 게이트 강도 (belle 2026-07-07 확정)
- **D-01:** **정확도 무회귀가 hard gate** — 점수·verdict·faults가 EVAL18 순차 대조에서 무회귀. 시간은 "가능한 범위에서 현실적으로 최대 절감"이 목표치 (1분은 지향점, hard 아님). belle 원문: "너무 1분에 집착 안 해도 됨. 4분 넘어가는데도 아무 조치가 없어서 나온 피드백 — 빠르면 빠를수록 좋고 현실적으로."
- **D-02:** 피드백의 본질 = "오래 걸리는데 **아무 조치/변화가 없다**"는 체감. 절대 시간 단축과 대기 중 체감 개선(D-06)을 동급 레버로 취급.

### veto 처리
- **D-03:** vision veto는 **파이프라인 내 겹치기** — 포즈 추정 진행 중 비전 호출을 가능한 구간부터 병렬 시작 (단일 분석 내부 병렬 — 분석 간 동시성 오염과 별개, 분석 간 SERIAL 불변). 점수는 결과 시점에 **동기 확정** — 사후 점수 변경 금지. veto 완전 비동기(점수 사후 보정)는 기각.

### 허용 레버 범위
- **D-04:** 기본 = **모델·입력 불변** 레버만: inline 전송(File API 우회), 파일 핸들 재사용, 호출 병렬화, 캐시. 프레임 수/해상도 축소는 **금지** (정확도 영향).
- **D-05:** Pro→Flash 전환은 **조건부 허용** — EVAL18 순차 대조에서 verdict·점수 동일할 때만 채택 (과거 실측: video split 판정에서 Flash≈Pro, 레버=프롬프트). 채택/기각 근거를 SUMMARY에 기록.

### 후처리·대기 경험
- **D-06:** fault_zoom PNG 렌더는 **사후 업데이트로 분리** — 점수/verdict/감점 내역 먼저 complete(앱은 onSnapshot으로 즉시 표시), zoom PNG는 렌더 완료 후 필드 업데이트로 도착. 결과 화면의 확대카드 자리는 로딩 상태 표시. zoom은 점수가 아닌 표현물이므로 D-03의 "사후 변경 금지"와 충돌하지 않음.
- **D-07:** **로딩 대기 중 재미 요소 추가** (belle 아이디어): 분석 대기 화면에 폴스포츠 관련 콘텐츠 — v1 = 저비용 텍스트 로테이션(폴스포츠 팁/동작 소개/재미 문구), 캐릭터 애니메이션(심플한 캐릭터가 폴 동작)은 에셋 확보 시 업그레이드 옵션. 형태 세부는 Claude 재량이되 라이트 테마·이모지 금지·기존 로딩 화면(navy 예외) 규칙 준수.

### Claude's Discretion
- 병렬화 구현 방식(스레드/asyncio/BackgroundTasks), inline 전송 크기 임계 처리, 캐시 키 설계 (단, 과거 캐시 키 충돌 사고 이력 참조 — PROMPT_VERSION류 버전 키 포함 필수).
- 진행률 표시 정밀화(단계별 %)는 D-02 범위에서 재량 (85% 멈춤 오인 재발 방지 관점).
- 로딩 재미 요소의 문구/구성.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 근거/실측
- `.planning/PILOT-FEEDBACK-2026-07-06.md` §B — 속도 피드백 원문(belle 기준선 1분, mode1 2.5~5.7분 실측, 지배 요인 분해).
- `.planning/ROADMAP.md` Phase 27 섹션 — 실측 분해(포즈 51s + 비전 52s + 후처리 49s)와 레버 목록.

### 파이프라인 코드 (수정 대상)
- `backend/functions/pipeline/app.py` — `_process` 오케스트레이션 (포즈→비전→후처리 순차 구조가 겹치기 대상).
- `backend/shared/python/sunity_shared/analysis/` — vision veto/인식기/coach_writer 어댑터 (Gemini 호출부), fault_zoom 렌더.
- `backend/runpod_inference/server.py` — BackgroundTasks 실행 컨텍스트 (single worker, 분석 간 SERIAL 불변).

### 무회귀 게이트
- `backend/evals/` phase 24 계열 eval 하니스 — EVAL18 순차 대조 패턴 (EVAL_OUT_DIR 리포 밖, SERIAL, artifact-gated). Phase 22가 22-VALIDATION에서 참조하는 것과 동일 계보.

### 앱 (D-06/D-07 소폭 수정)
- `app/src/app/analysis/loading.tsx` — 진행률/대기 화면 (재미 요소 삽입 지점, navy 예외 화면).
- `app/src/app/analysis/result.tsx` — 확대카드 zoom 로딩 상태 (Phase 26의 26-02 wrapper/child 분리와 파일 겹침 주의 — 실행 순서 조율 필요).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 진행률 표시 로직(loading.tsx) — 85% 멈춤 버그 fix 이력 있음. 단계별 % 정밀화의 기반.
- Gemini 호출 캐시(PROMPT_VERSION 키 버전링) — 캐시 확장 시 동일 패턴 재사용, 키 충돌 사고 재발 방지.
- 앱 onSnapshot 구독 — zoom 사후 업데이트가 추가 앱 폴링 없이 자동 반영되는 기반.

### Established Patterns
- 파이프라인 분석 간 동시성 비안전 → eval/batch 순차 필수 (invariant). 단일 분석 내부 병렬은 신규 영역 — 공유 상태(모듈 캐시/전역) 오염 여부 검증 필요.
- vision veto 필수(VETO=1 start_server.sh 박제), GEMINI_MAX_VETO_WALL_S=300 예산.
- Gemini 모델 string: Pro=`gemini-3.1-pro-preview`, Flash=`gemini-3.5-flash` (2.5 금지).

### Integration Points
- Pod env/start_server.sh — 새 env 추가 시 박제(setdefault) 패턴 준수.
- Firestore complete/업데이트 경로(firestore_admin) — zoom 사후 업데이트 필드 추가 시 nested-array 금지/flat 규칙.

</code_context>

<specifics>
## Specific Ideas

- belle: 로딩 중 "심플한 캐릭터가 폴스포츠 동작을 하고 있다던가, 아님 텍스트로 표현한다던가" — 재미 요소로 대기 체감 개선.
- 4분 무변화 대기가 원성의 본질 — 진행이 "보이는" 것 자체가 가치.

</specifics>

<deferred>
## Deferred Ideas

- 프레임/해상도 입력 축소 — 정확도 영향 검증 부담, 이번 phase 금지 (D-04).
- veto 완전 비동기(점수 사후 보정) — 신뢰 리스크로 기각.
- 캐릭터 애니메이션 에셋 제작 — 에셋 확보 시 D-07 업그레이드 (디자인 트랙).
- 근본 해법 = Phase 22 자체 서빙(vLLM)으로 Gemini 라운드트립 소멸 — 이 phase는 그때까지의 저비용 브리지.

</deferred>

---

*Phase: 27-analysis-speed-1min*
*Context gathered: 2026-07-07*
