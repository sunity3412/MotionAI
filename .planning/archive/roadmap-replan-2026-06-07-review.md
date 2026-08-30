# 로드맵 재정렬 검토 — 2026-06-07

> 본 문서는 `.planning/roadmap-replan-2026-06-07.md` 에 대한 narrow gate 검토.
>
> **외부 AI (Codex) 실패** — `codex exec` 가 ChatGPT 계정에서 gpt-5 / gpt-5.5 / gpt-5-codex 모두 사용 불가 (HTTP 400 invalid_request_error). 4회 시도 모두 응답 미시작. 결과: **Claude self-review** 로 대체. belle 가 별도 path (Cursor Opus, Claude.ai 등) 로 외부 검토 추가 권장.
>
> Self-review 는 외부 비교군 결여 — narrow gate 식별 의도는 동일하나 "확증 편향" 위험. belle 가 가장 비판적 항목부터 검증 권장.

---

## 1. Verdict

**APPROVE-WITH-CHANGES** — A+B+C 선정 자체는 파일럿 목표에 맞음. 그러나 **B → A → C 시퀀싱은 위험**: A (Phase 12) 가 큰 scope 인데 시연 가능 상태 (빌드 11) 를 깨뜨릴 가능성이 있고, C (학원 용어) 가 학원 파일럿 직전에 가장 필요. **권장 시퀀싱 = B → C → A**.

---

## 2. Q1~Q10 답변

### Q1 — A+B+C 시퀀싱이 파일럿 목표에 정합?

**부분 정합**. A (실측 각도 + 오버레이) + C (학원 용어) 는 직접적인 파일럿 가치. B (UI transparency) 는 belle 의문 "94 vs 95% 갭" 을 해소 = 사용자/시연자 신뢰. 그러나 보류한 Phase 11 (CoachCommentHook + "AI = 강사 보조 도구" 포지셔닝) 은 실증 단계 실패 1순위 후보 — 메모리 [[field-research-stakeholders]] = "강사/운영자는 도입 결정권자이자 가장 큰 저항 세력. 1순위 우려 = AI 가 강사를 대체할까". **B scope 안에 "강사 보조 도구" 카피 박제 추가 권장** (`result.tsx` 헤더 + footer 한 줄씩). 본격 CoachCommentHook 데이터 구조는 v1.5 유지 OK.

### Q2 — A 큰 scope (2주~) 가 시연 직전 시간에 정합?

**아니다**. 메모리 [[feedback-no-demo-urgency]] 정합으로 시연 임박을 가정하지는 않지만, A 의 위험은 시간 외에도: (a) Plan 12-01 backend payload 1MB 검증 미완 시 path 재설계 필요, (b) Plan 12-03 SVG 오버레이 + 영상 동기화 = `react-native-svg` + `expo-video` currentTime ↔ frame index 정합 검증 필요 (9fps 분석 frame vs 60fps 재생). **B (3~5일, Q7 보정 후) 먼저** 가 안전 — 사용자 신뢰 카피만으로 빌드 12 ship 가능, 시연 가능 상태 유지하며 A 본격 진행.

### Q3 — C 분기 3 자동 수집 vs "MVP 단순"?

**MVP 단순 정합 = 스키마 + UX 노출만, 승급 알고리즘은 v2**. 메모리 [[studio-term-3branch-system]] = "분기 3 = 자동 수집 + UX 카피 노출이 핵심". 타협 = (a) Firestore `pending_terms` 컬렉션 스키마 박제, (b) belle 작성 UX 카피 (변경/요약 X) 분석 시작 화면 한 줄 노출, (c) `uniqueUserCount >= 2 → reviewing` 자동 승급 = v2 보류.

### Q4 — ROADMAP.md 갱신 vs 본 문서 supersede?

**둘 다 필요**. 본 문서 = 2026-06-07 결정 박제. ROADMAP.md = single source of truth (gsd workflow 가 참조). 갱신 항목 = Phase 1 close-out 마킹 (Plan 23 SUPERSEDED, Plan 01-24/25 → 통합 박제 필요), Phase 5 close-out (12차 sweep PASS), Phase 12.5 (B) 신설, Phase 16 코드 통합 Plan 16-02~04 추가.

### Q5 — Plan 01-24 (NLF R&D 격리) 우선?

**우선이지만 작은 unit, B 와 parallel 진행 가능**. 메모리 [[license-blocklist-pose.md]] = "NLF/AlphaPose/SMPL-X 상업 불가". `.samignore` 명시 + import 차단 단위 테스트 = 약 0.5~1일. Lambda layer 가 commit 2a8aa72 (atomic swap) 후 NLF 의존 없는지 grep 검증 필수 — 만약 NLF 모듈이 layer 안에 잔존하면 라이선스 게이트 위반. B 진행과 별도 PR 로 분리.

### Q6 — playbackKeypoints Firestore 1MB 제한?

**무난, 그러나 압축 권장**. 추정: 60s × 9fps × 17 keypoint × 2D × float = 약 200KB. 1MB 무난. 위험 = (a) 120s+ 영상 가능성, (b) confidence/3D 박제 시 +50%. **권장 = 5fps + 8 핵심 keypoint (어깨/골반/무릎/손) 만 저장** = 30s 약 24KB, 60s 약 48KB. Plan 12-01 acceptance 에 "60s 영상에서 < 200KB" 게이트 박제.

### Q7 — B 가 backend 변경 필요?

**필수, 원 문서는 의존성 누락**. `assemble.py:105-157` 의 `build_result` = `dimensionScores: dict[str, int]` 만 출력, 차원별 deficit 박제 없음. 현재 `joints[i].deltaDeg` (관절별) 만 있음. B 박제 시 backend 추가 = `assemble.py:build_result` 가 `dimensionExplanation: dict[ScoreDimension, { weight: float; baseline: string; deficitSummary: string }]` 출력. weight 는 산식 인용 (현재 `_compute_overall` 가중치 grep 필요), baseline 은 상수, deficitSummary 는 `kismam.top_issues` 재사용. **B scope = backend 약 50 line + contract 양쪽 + frontend 약 30 line**. 작업량 = 1 plan / **3~5일** (원 문서 1~3일은 과소 추정).

### Q8 — C 의 5트랙 채점 v1 vs mode3 second+ 산식 정합?

**충돌 위험**. `assemble.py:build_mode3` = `deltaFromPrevious = cur_dimension_scores - prev_dimension_scores` (현재 angle/line/stability 3차원). 5트랙 v1 (a)+(c)+Page 9 박제 시 차원 변경:
- (a) Compulsory = 관절각 + 라인 통합
- (c) Technical Deduction = 안정성 + 갑작스러운 떨림
- Page 9 = 절대 공통 트랙 (단독 채점)

mode3 박제 정신 [[mode3-progress-not-similarity]] = "절대 지표 세션 간 델타" — 5트랙도 절대 지표이므로 박제 정신 정합. 그러나 contract 변경 필요: `dimensionScores: { angle, line, stability }` → `dimensionScores + tracks: { compulsory, technicalDeduction, page9Absolute }` 병행. **권장 = Plan 16-03 안에 contract migration 박제 = legacy 보존 + 새 `tracks` 필드 추가 (parallel), frontend 토글로 점진 전환**. 한 번에 바꾸면 mode3 second+ 비교 깨짐.

### Q9 — A+B+C "분석 정확도" 정합?

**정합**. 메모리 [[feedback-analysis-first]] = "분석이 최우선". A = "어디" 시각화, B = "왜" 텍스트, C = "용어 + 5트랙" 정확도 통합. 보류 Phase 2~11 = "분석 정확도" 차세대 진화 (체형 정규화 = 위양성 감점 방지, 두 엔진 = 원인 추론 깊이). 현재 IPSF (a)+(c)+Page 9 가 5/5 PASS 박제 = 박제 정신 정합 검증 완료. v1.5 진입 시점은 파일럿 실증 데이터 보고 결정.

### Q10 — B 의 mode3 분기 카피 정합?

**정합, 단 분기 카피 명시 필요**. 메모리 [[mode3-progress-not-similarity]] = "절대 지표 세션 간 델타로 성장 표시, %일치 헤드라인 금지". B 의 차원별 카피 박제 시:
- mode1: "각도 정확도 = IPSF 기준 + 정은지 측정값 = 70점"
- mode3 first: "각도 일관성 = 70점 (이번이 첫 분석)"
- mode3 second+: "각도 일관성 = +5점 (지난 분석 대비)"

이미 `result.tsx` 가 mode 별 다른 박제 보임 — B scope 안에서 mode 분기 카피 박제 작성 + DIMENSION_LABEL_KO 확장.

---

## 3. HIGH concerns

### H1: A 의 시간 위험 + 시연 가능 상태 유지

A 가 큰 scope (5 plan, 2주~) + Plan 12-03 영상 동기화 = expo-video currentTime (60fps × 16ms 정밀도) ↔ 9fps 분석 frame 매핑 = "현재 보이는 frame ≠ 분석 frame" 위험. A 진행 중 시연 요청 발생 시 빌드 11 ship 가능 상태 유지 필수. **권장 = (a) feature flag (`EXPO_PUBLIC_KEYPOINT_OVERLAY=1`) 으로 toggle, (b) git branch `pilot-demo-stable` = 빌드 11 박제 보존**. 메모리 [[eas-build-gotchas]] 정합.

### H2: C 의 contract migration 위험

5트랙 채점 v1 박제 시 `dimensionScores` 변경 = mode3 second+ delta 비교 깨짐 위험. **권장 = parallel field 박제** (legacy `dimensionScores` 보존 + 새 `tracks` 필드 추가). frontend 가 두 필드 모두 읽고 점진 전환. 메모리 [[firestore-nested-array-flat]] 정합 — tracks 도 flat 저장.

### H3: B 의 backend 변경 의존성

원 문서 = "B 의존성 = 없음 (contract 위에 확장)". **실제 = backend `assemble.py` 변경 필수** (Q7 답변). 작업량 보정 = "1 plan, 1~3일" → "1 plan, 3~5일". scope = backend 약 50 line + contract 양쪽 + frontend 약 30 line.

### H4: 학원 도입 게이트 — "AI = 강사 보조" 카피 누락

메모리 [[field-research-stakeholders]] = "강사/운영자 = 도입 결정권자 + 가장 큰 저항 세력. 1순위 우려 = AI 가 강사 대체할까". 보류 Phase 11 본체는 v1.5 OK. 그러나 **B scope 안에 "AI = 강사 보조 도구" 카피 박제 필수** — `result.tsx` 헤더 한 줄 ("이 분석은 강사 수업을 대체하지 않아요") + footer 한 줄 ("강사와 함께 보세요"). 코드 5~10줄로 H4 해소.

---

## 4. Scope 수정 권장

### 4-1. A (Phase 12)

- **추가 Plan 12-00 (선행)**: feature flag `EXPO_PUBLIC_KEYPOINT_OVERLAY` + git branch `pilot-demo-stable` 박제 (H1).
- **수정 Plan 12-01 acceptance**: "60s 영상 playbackKeypoints < 200KB" 게이트 박제 (Q6).
- **재검토 Plan 12-04**: 영상 currentTime ↔ frame index 동기화 = 9fps 분석 한계로 정밀 sync 어려움. 대안 = (a) hold moment 1차 frame 만 정적 오버레이 (사용자 박제 = "수치는 보조" 정신 정합), (b) 또는 분석 fps 늘리기 (Lambda timeout / GPU 부하 검토).

### 4-2. B (UI transparency)

- **추가**: backend `assemble.py:build_result` = `dimensionExplanation` 출력 (weight + baseline + deficitSummary). 메모리 [[ipsf-5-track-scoring]] 참조.
- **추가**: "AI = 강사 보조 도구" 카피 박제 (H4).
- **추가**: mode 분기 카피 박제 (Q10).
- **작업량 수정**: 1 plan / **3~5일** (원 1~3일 → 보정).

### 4-3. C (Phase 16 코드 통합)

- **Plan 16-02 (AKA 매핑 13개)**: backend `gemini_motion_classifier.py` 가 이미 부분 구현 (한국어/영어/IPSF code alias). 13개 매핑 전체 박제 + Gemini prompt motion_query 통합 + 5영상 + 학원 통용 한국어 추가 영상 검증.
- **Plan 16-03 (5트랙 채점 v1)**: contract migration parallel field 박제 (H2) — legacy `dimensionScores` 보존 + 새 `tracks: { compulsory, technicalDeduction, page9Absolute }` 추가. backend `assemble.py` + contract 양쪽 + frontend 토글.
- **Plan 16-04 (분기 3 자동 수집)**: Firestore 스키마 + UX 카피 노출만 (Q3) — 자동 승급 알고리즘 v2.

---

## 5. 권장 시퀀싱 = B → C → A

**원 문서 추천 = B → A → C** 였으나 본 검토 결과 = **B → C → A**.

| 단계 | 작업 | 작업량 | 효과 |
|---|---|---|---|
| 0 | Plan 01-24 (R&D 격리) parallel | 0.5~1일 | 라이선스 게이트 |
| 1 | B (UI transparency + 강사 보조 카피) | 3~5일 | 사용자 신뢰 + H4 해소 + 시연 가능 상태 박제 |
| 2 | C (Phase 16 코드 통합) | 1~2주 | 학원 용어 + 5트랙 = 학원 파일럿 직전 가치 최대 |
| 3 | A (Phase 12) | 2주~ | 시연 임팩트 (실측 시각화). feature flag 박제로 시연 가능 상태 유지하며 진행 |

**B → C → A 가 B → A → C 보다 나은 이유**:
1. C 가 학원 파일럿 직전에 가장 필요 (학원 용어 = 학원 사용자 1차 진입 게이트). A 가 C 전에 들어가면 학원 파일럿 진입 지연.
2. A 가 큰 scope 라서 마지막에 두는 게 안전 — feature flag + branch 박제로 빌드 11 stable 유지하며 점진 진행.
3. B + C 만 ship 되어도 파일럿 실증 가능 — A 는 시연 임팩트 강화 layer.

---

## 6. 문서가 놓친 항목

1. **TestFlight 빌드 12 ship 시점 의문** — B 박제 후 빌드 12 ship 인지 vs A+C 다 완료 후 ship 인지 미명시. 권장 = B 박제 후 빌드 12 ship → C 박제 후 빌드 13 → A 박제 후 빌드 14.
2. **Phase 5 close-out 마킹 별도 작업** — Phase 1 Plan 01-24 만 언급, Phase 5 의 ROADMAP close-out 마킹은 누락. STATE.md "Phase 5 사실상 완료" 박제와 정합 필요.
3. **Pod 새 ID (ub242i85kkmh3f) → Lambda env 동기화** — 본 세션 외 작업이지만 후속 작업 항목 미포함. server.py 살아나면 sunity-motion AWS 키로 갱신.
4. **Plan 01-23 (RTMW vs IPSF sweep) SUPERSEDED 마킹** — Phase 5 sweep 12차로 사실상 대체. ROADMAP 갱신 시 명시.
5. **belle Pod 1ablelgbtrzcgb (어제 죽은 Pod) S3/Firestore artifact cleanup** — 후속 cleanup 후보 미명시.

---

*Self-review 작성: 2026-06-07 (Claude Code)*
*외부 비교군 결여 — belle 가 Cursor Opus 또는 Claude.ai 등 별도 path 로 narrow gate 추가 검증 권장*
