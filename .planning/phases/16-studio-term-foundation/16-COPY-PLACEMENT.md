# 16-COPY-PLACEMENT.md — 분기 3 UX 카피 박제 위치

**Phase**: 16 (Studio Terminology Foundation)
**Plan**: 16-01 (T-5 산출물)
**Mode**: spec / copy placement decision (코드 변경 0)
**Created**: 2026-06-02
**Authority**: belle 작성 카피 원문 + 노출 위치 후보 박제. 실제 화면 통합은 Phase 14/15 진입 시.

---

## 1. 카피 원문 (CRITICAL — 변경/요약/재가공 금지)

belle 2026-06-02 직접 작성 ([[studio-term-3branch-system]] 박제 그대로):

> **공식 등재되어 있지 않은 기술명입니다. 서니티는 국제 대회 기준 명칭을 기준으로 평가하며 추가로 학원에서 등록된 명칭을 사용합니다. 귀하께서 입력한 기술 키워드는 지금 바로 '자동 수집' 되었으며 하나의 학원 이상에서 사용하는 기술임이 확인되면 업데이트 예정입니다.**

**불변 원칙**:
- 변경 금지 (단어/순서/마침표 모두 포함)
- 요약 금지 (짧은 버전 만들기 X)
- 재가공 금지 (다른 톤/존댓말 수준 변경 X)
- 다른 UI 위치에 노출 시 동일 문구 그대로 사용

---

## 2. 노출 위치 후보 (Phase 14/15 통합 시 belle 검토)

분기 3 처리가 발동하는 user-facing path 에서 다음 후보 위치에 노출. 어느 위치를 채택할지는 Phase 14/15 진입 시 Figma 디자인 + belle 결정.

### 후보 A — 결과 화면 헤더 (Result Screen Header)

**위치**: `app/src/app/analysis/result.tsx` 상단 헤더 영역.
**장점**: 사용자가 채점 결과를 가장 집중해서 보는 화면 → 카피가 채점 컨텍스트 (왜 IPSF 정밀 채점이 아닌지) 와 정합.
**단점**: 결과 화면 정보 밀도 높음 → 카피가 묻힐 위험.

### 후보 B — 분석 시작 직후 confirm 다이얼로그 (Pre-Analysis Confirm Dialog)

**위치**: `app/src/app/analysis/loading.tsx` 또는 새 confirm 단계.
**장점**: 사용자가 분석 의도를 변경할 수 있는 단계 (취소 / 다른 동작명 입력 / 정은지 reference 선택). 카피의 "자동 수집" 동의 의미가 명확.
**단점**: 단계 추가 = MVP 마찰. 분기 1/2 케이스에서는 다이얼로그 미노출 → 분기 3 만 노출.

### 후보 C — Mypage "이전 분석" 항목 옆 배지 (Mypage Badge)

**위치**: `app/src/app/(tabs)/mypage.tsx` 또는 동등.
**장점**: 사후 확인 — 사용자가 자신의 분석 이력에서 어떤 게 분기 3 처리됐는지 박제.
**단점**: 처음 분석 시 카피를 못 봄 → 분기 3 처리 사실 인지 늦음. 후보 A 또는 B 와 병행 권장.

### 권장 조합 (MVP)

belle 검토 시 다음 조합 권장:
- **후보 A (결과 화면 헤더)** 단독 노출 — 가장 단순. 사용자가 결과 보는 시점에 분기 3 처리 사실 + 자동 수집 동의 인지.
- 후보 B (confirm 다이얼로그) 는 단계 추가 마찰 → MVP 보류, v2 검토.
- 후보 C (mypage 배지) 는 분기 3 entry 가 많아진 후 (실증 데이터) 도입.

단, **결정권은 belle + Figma 디자인** — 본 plan 에서는 후보 박제만.

---

## 3. Figma 디자인 위치 (확인 필요)

**Motion AI Figma fileKey**: `jrdI7kp245HkPfLB0nclsz` ([[motion-ai-figma-file]])

UI 우선 원칙 ([[ui-figma-first]]) 적용:
- 분기 3 UX 카피 노출 위치가 Figma 에 이미 디자인됐는지 belle 확인 필요.
- 디자인 없으면 belle 에게 작업 요청 → 디자인 받은 후 코드 통합 (Phase 14/15).
- 디자인 있으면 디자인 위치 + 본 문서 후보 cross-reference 후 채택.

**TODO (후속 plan)**:
- [ ] Figma 에서 분기 3 카피 노출 위치 검색 (Phase 14/15 진입 시)
- [ ] 디자인 없으면 belle 에 작업 요청
- [ ] 디자인 받은 후 본 문서 갱신

---

## 4. 코드 통합 위치 (후속 plan)

본 plan 은 카피/위치 박제만. 실제 코드 통합은 다음 phase 진입 시:

| Phase | 통합 항목 |
|---|---|
| Phase 5 (Gemini 기술 인식기) | 분기 3 판정 로직 (AKA miss + reference miss → 분기 3) — 카피 노출 trigger |
| Phase 14 (정은지 reference 등록) | 분기 2 케이스 정리 → 분기 3 케이스 명확화 |
| Phase 15 (Mode 1/3 실영상 + TestFlight) | 후보 A/B/C 중 belle 결정 채택 + 화면 통합 |

---

## 5. Cross-Reference

| Source | 정합 항목 |
|---|---|
| memory [[studio-term-3branch-system]] | 카피 원문 박제 원본 |
| memory [[ui-figma-first]] | Figma 디자인 우선 원칙 |
| memory [[motion-ai-figma-file]] | fileKey `jrdI7kp245HkPfLB0nclsz` |
| REQUIREMENTS.md TERM-COPY-01 | "belle 작성 그대로 박제되어 노출, 변경/요약/재가공 금지" |
| `.planning/phases/16-studio-term-foundation/16-AUTOCOLLECT-SCHEMA.md` (T-4) | 자동 수집 흐름 — 카피 노출 trigger 와 동기 |
| `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` (T-2) | 분기 3 = Page 9 트랙 단독 채점 → 카피의 "공식 등재 X" 근거 |

---

*Created 2026-06-02 (Plan 16-01 T-5 산출물 — 분기 3 UX 카피 박제 위치 결정)*
