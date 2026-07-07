# Phase 26: 온보딩·기대설정 + 원본 업로드 가이드 - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

분석 이전 구간(시나리오 0 / 0.5 / 1 / 1.5)의 파일럿 gap 해소 — 수강생이 학원에서 혼자 앱을 켜고 업로드까지 도달하게 만드는 구간. 구성: (a) 기대설정 온보딩(Figma 튜토리얼 + samples.tsx 여정 편입 + 샘플→이용방법/FAQ 교체 F2), (b) 프라이버시 1줄 + 학습활용 고지(Phase 22 D-12 연동), (c) 원본 업로드 가이드(카톡 압축본 `_talkv_` 감지 경고 + 촬영 거리 안내), (d) 잡 UI(F3 기타 자유입력, F4 공지 간격). **앱만, 낮은 난이도.** 백엔드/채점 로직 무접촉 (not_pole 게이트 불변 — D-01).

</domain>

<decisions>
## Implementation Decisions

### not_pole 게이트 (belle 2026-07-07 확정)
- **D-01:** 게이트/임계 **불변**. 대응은 안내만 — (i) 업로드 전 촬영 거리·구도 안내, (ii) not_pole 실패 화면에 "촬영 구도/거리" 원인 안내 + 재촬영 가이드 노출. 위양성 리스크 0, "앱만" 스코프 유지.
- **D-02 [informational]:** 게이트 임계 완화는 파일럿에서 안내 효과 측정 후 별도 결정. torso ratio 스케일 정규화(근본 보정)는 채점 트랙 별도 phase 후보로 deferred. (이번 phase 구현 대상 아님 — Deferred Ideas 참조)

### 온보딩 진입
- **D-03:** Figma 튜토리얼은 **첫 실행 1회 + 스킵 가능**. 이후 이용방법/FAQ에서 재접근 가능해야 함.
- **D-04:** 온보딩 내용 = 기대설정("무엇을 측정하고 무엇은 못 하는지") 중심. UI는 Figma 튜토리얼 디자인(belle 승인 2026-07-05, fileKey jrdI7kp245HkPfLB0nclsz) 사용 — 자체 디자인 금지, Figma 우선.
- **D-05:** `analysis/samples.tsx`(샘플 결과 미리보기)를 이용방법/FAQ로 교체(F2)하고 온보딩 여정에 편입.

### 카톡 압축본 감지
- **D-06:** `_talkv_` 파일명 감지 시 **경고 + 진행 허용** (하드 차단 금지). 경고 문구 = "카톡 전달본은 화질 손상으로 분석 실패 확률 높음" 취지 + 원본 사용 안내.
- **D-07:** 진행 선택 시 기존 저화질 경고 플로우(260704-fwb: 저화질 승인 후 not_pole 실패 시 화질 원인 우선 안내 분기)와 연동 — 압축본 승인 후 실패하면 화질 원인 안내가 우선.

### 프라이버시·학습활용 고지
- **D-08:** 업로드 직전 **1줄 고지**("영상은 분석 후 안전 보관·삭제 요청 가능" 취지) + **학습활용 opt-in 체크 별도**("AI 개선에 활용 동의"). 포괄 동의 금지.
- **D-09:** opt-in 기본값 = **off**. 동의값은 Phase 22 D-12(고객 영상→학습 플라이휠)의 동의 근거로 저장돼야 함 — 동의한 영상만 학습 후보. 저장 위치/필드는 플래너 재량이되 Phase 22 쪽 manifest 게이트가 읽을 수 있는 형태여야 함.

### Claude's Discretion
- UI 화면 순서 재배치(belle 요청): 실행 중 **목업 선제시**(AskUserQuestion preview, 최악 데이터 케이스 포함 — belle 기존 지시) 후 확정. 플랜에는 "재배치 제안 + 목업 checkpoint"로 태스크화.
- 이용방법/FAQ의 위치(탭/마이페이지 등), FAQ 항목 구성, 경고·고지 문구 세부 카피, F3(기타 자유입력)·F4(공지 간격) 구현 세부.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 여정/시나리오 (이 phase의 존재 이유)
- `.planning/SCENARIO.md` — 확정 시나리오 v1.0. 단계 0/0.5/1/1.5 정의 + 파일럿 gap 우선순위 + 스코프 제외 근거(라이브 앵글 가이드/3초 검증 제외, 전신/폴 미포함 비고려). **모든 작업은 시나리오 단계로 태깅.**
- `.planning/PILOT-FEEDBACK-2026-07-06.md` — 실증 피드백 원문. A1(not_pole 오반려 실측), F2/F3/F4 항목 출처.

### 디자인
- Figma fileKey `jrdI7kp245HkPfLB0nclsz` — 튜토리얼 디자인(belle 승인). Figma MCP로 조회. design.md는 보조.
- `design.md` — 브랜드 컬러 #FF4B33, 라이트 전용, 배경 규칙 §5-1.

### 앱 컨벤션/연동 지점
- `app/CLAUDE.md` — 테마 토큰 강제(하드코딩 금지), 컨벤션.
- `docs/ia.md` — 화면 스펙. 단 1.5 관련 라이브 앵글 가이드/3초 검증은 실측 근거 없음으로 스코프 제외(SCENARIO.md 우선).

### Phase 22 연동 (D-12 동의 근거)
- `.planning/phases/22-custom-vlm-finetune/22-04-PLAN.md` — 학습 JSONL manifest 게이트(anonymized/registration). opt-in 동의값이 이 게이트가 소비 가능한 형태여야 함.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/src/app/analysis/samples.tsx` — 기존 샘플 미리보기 화면. F2로 이용방법/FAQ 교체 대상 (여정 편입).
- `app/src/app/(tabs)/analyze.tsx` — 업로드 UX 완비. 파일 pick 시점이 `_talkv_` 감지 + 프라이버시 1줄 + 촬영 거리 안내의 자연 삽입 지점.
- 저화질 경고 분기(260704-fwb) — 압축본 경고 승인 후 not_pole 실패 시 화질 원인 우선 안내. D-07 연동 대상.
- `app/src/app/analysis/loading.tsx` / result 에러 표시 계층 — not_pole 실패 화면 원인 안내(D-01-ii) 삽입 지점.

### Established Patterns
- 에러/안내는 한국어 인라인 문자열 + 테마 토큰. 이모지 금지.
- 계약 변경 시 3-way lockstep(`app/src/types/analysis.ts` + `models.py` + `docs/contract.md`) — opt-in 동의 필드가 계약을 건드리면 준수.

### Integration Points
- 게스트(익명 Firebase) 첫 실행 감지 → 튜토리얼 1회 노출 (AsyncStorage 플래그 등 로컬 저장 재량).
- opt-in 동의값 → Firestore 사용자/분석 문서 (Phase 22 manifest 게이트가 읽는 경로).

</code_context>

<specifics>
## Specific Ideas

- 온보딩 튜토리얼 = Figma 디자인 그대로 (belle: "UI는 Figma 우선" 원칙).
- UI 화면 순서 재배치는 belle이 직접 보고 결정하고 싶어함 → 목업 checkpoint 필수.
- 경고/고지 문구 톤 = 기존 앱의 친근한 한국어체 ("~해요" 체, `analyze.tsx` 기존 에러 문구 참조).

</specifics>

<deferred>
## Deferred Ideas

- **torso ratio 스케일 정규화(구도 보정)** — not_pole 오반려의 근본 해법이지만 채점 트랙(백엔드). 별도 phase 후보로 백로그. (D-02)
- **게이트 임계 완화** — 파일럿에서 안내 효과 측정 후 재결정.
- 촬영 방법(삼각대 등) 심화 가이드 — 시나리오 1단계 "셀프촬영 방법 안내"는 이번엔 촬영 거리 안내 수준까지만.

</deferred>

---

*Phase: 26-onboarding-upload-guide*
*Context gathered: 2026-07-07*
