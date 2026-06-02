# 16-01-SUMMARY.md — Studio Terminology + 5-Track Scoring Foundation (Data/Spec/Copy 박제)

**Phase**: 16 (Studio Terminology Foundation)
**Plan**: 16-01
**Mode**: mvp (data/spec/copy lockstep, code change 0)
**Status**: ✓ Complete
**Created**: 2026-06-02
**Completed**: 2026-06-02

---

## One-liner

학원 용어 3분기 시스템 (분기 1 AKA 매핑 13개 + 분기 2 정은지 reference 폭스탑 + 분기 3 자동 수집 스키마) + IPSF 5트랙 채점 v1 scope ((a) + (c) + Page 9 절대 트랙) 의 데이터/스펙/UX 카피를 박제. 코드 변경 0, 후속 plan (Phase 5/14/15) 진입 위치 명시.

---

## 박제 산출물 위치

| Task | 산출물 | 위치 |
|---|---|---|
| T-1 | 분기 1 AKA 매핑 13개 | `backend/data/aka-mapping.json` |
| T-2 | 5트랙 채점 v1 architectural decision | `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` |
| T-3 | 분기 2 정은지 reference (폭스탑) | `backend/data/reference-motions-branch2.json` |
| T-4 | 분기 3 자동 수집 Firestore 스키마 | `.planning/phases/16-studio-term-foundation/16-AUTOCOLLECT-SCHEMA.md` |
| T-5 | 분기 3 UX 카피 박제 위치 | `.planning/phases/16-studio-term-foundation/16-COPY-PLACEMENT.md` |
| T-6 | 실증 게이트 threshold belle 결정 | `.planning/ROADMAP.md` Phase 16 Success #7 + `.planning/STATE.md` decision |
| T-7 | 본 SUMMARY | `.planning/phases/16-studio-term-foundation/16-01-SUMMARY.md` |

---

## belle 협의 결과 (T-3 + T-6)

### T-3 — 정은지 폭스탑 영상

- **보유 여부**: ✓ 보유 (belle 2026-06-02 확인 — 정은지 영상 폴더에 존재)
- **명명 갈등 박제**: 정은지 선수 본인은 폭스탑 동작을 **"버터플라이 콤보"** 라고 호칭. 학원/IPSF/reference 인물 명칭 모두 다른 케이스.
- **신규 필드**: `championPersonalAlias` 박제 — `studioNameAliases` (학원 측 다른 표기) 와 별개. memory [[studio-term-3branch-system]] How to apply 에 박제.

### T-6 — 실증 검증 게이트 threshold

belle 2026-06-02 결정:

| Q | 결정 | 근거 |
|---|---|---|
| (a) 분기 1 매핑률 X% | **deferred** | belle: "분석만 잘되면 돼, 정은지같은 프로 점수가 이상하게 안나오게". 매핑률 자체가 v1 게이트 아님 — 진짜 게이트 = 분석 정확도 + 고수 위양성 방지. [[feedback-analysis-first]] + Core Value 정합. |
| (b) 분기 3 "둘 이상" 정의 | **둘 이상 anon userId** (`uniqueUserCount >= 2`) | belle: "mvp에 맞게 가고, 조정하자". 학원 ID 트래킹은 v2. |
| (c) 분기 2 사용률 측정 | **v1 게이트 아님** | belle: "분석 후 판단에 따라야할 것 같은데". 사용률보다 분석 정확도 작동 여부가 진짜 검증. 운영 metric only. |

---

## Success Criteria (Plan 16-01) 충족 여부

1. ✓ AKA 매핑 13개 data file 박제 (T-1) — 모든 entry 필드 완전성 + NotebookLM citation
2. ✓ 5트랙 채점 v1 spec architectural decision 박제 (T-2) — PROJECT.md/REQUIREMENTS.md/memory cross-ref
3. ✓ 분기 2 정은지 reference 1개 박제 (T-3) — 폭스탑 + `championPersonalAlias` 신규 필드
4. ✓ 분기 3 자동 수집 데이터 스키마 정의 (T-4) — Firestore `pending_terms` + 익명성 요건 박제
5. ✓ 분기 3 UX 카피 박제 위치 후보 박제 (T-5) — 후보 3개 + Figma 위치 검토 TODO
6. ✓ 실증 게이트 threshold belle 협의 완료 + ROADMAP 박제 (T-6)
7. ✓ SUMMARY 박제 완료 (T-7)

---

## Phase 5/14/15 진입 시 통합 위치 (Cross-Reference)

| Phase | 통합 항목 | 참조 위치 |
|---|---|---|
| Phase 5 (Gemini 기술 인식기) | 분기 1 AKA 매핑 lookup → IPSF Code + Criteria 정밀 채점 | `backend/data/aka-mapping.json` |
| Phase 5 | 분기 3 자동 수집 wiring + Firestore 컬렉션 생성 + 보안 규칙 박제 | `16-AUTOCOLLECT-SCHEMA.md` |
| Phase 5 | (a) Compulsory Criteria 정밀 채점 코드 path | `16-SCORING-SPEC.md` v1 진입 위치 표 |
| Phase 14 (정은지 reference 등록) | 폭스탑 영상 ID + S3 경로 확정 + 측정값 자동 추출 wiring | `backend/data/reference-motions-branch2.json` `championReferenceVideoId` placeholder 갱신 |
| Phase 14 | 분기 2 reference 5~10개 확장 (실증 데이터 후) | `backend/data/reference-motions-branch2.json` entries 추가 |
| Phase 15 (Mode 1/3 실영상 + TestFlight) | 분기 3 UX 카피 화면 통합 (후보 A/B/C 중 belle 결정) | `16-COPY-PLACEMENT.md` 노출 위치 후보 |
| Phase 15 | 5트랙 통합 점수 합성 + 신뢰도 게이트 (고수 위양성 방지) | `16-SCORING-SPEC.md` 동작 인식 케이스별 활성 트랙 매트릭스 |

---

## 다음 단계 (후속 plan 후보)

### v1 진행 (Phase 5/14/15)

- Phase 5 — Gemini 기술 인식기 + 분기 1/2/3 코드 wiring + 분기 3 자동 수집 Firestore 통합
- Phase 14 — 정은지 폭스탑 영상 ID 확정 + 측정값 자동 추출 wiring + 분기 2 reference 5~10개 확장 검토
- Phase 15 — 분기 3 UX 카피 화면 통합 (후보 A 단독 권장 — belle 검토 필요) + Figma 디자인 위치 확인

### 실증 검증 후 확장 plan 후보 (별 milestone)

belle 결정으로 다음은 실증 데이터 수집 후 한 번에 진행:
- 분기 2 reference 5~10개 추가 (실증 데이터 본 후 우선순위 결정)
- 분기 3 → 분기 1/2 승격 알고리즘 (`promotionThresholdMet` trigger + belle 검토 UI)
- 분기 1 NotebookLM batch lookup 자동화 (`notebookLookupResult` 필드 활용)
- 학원 ID 트래킹 도입 (v2 — `studioIds` 필드 활성화)
- (b) Technical Bonus + (d) Artistic 트랙 v2 (별 milestone)

### v1.5 진입 시 (judging 모드)

- JUDGE-DATA-01 GeometricCriterion 라벨링 → (a) Compulsory Criteria 정밀 채점 데이터 확장. 본 plan 산출물 (`aka-mapping.json`) 와 데이터 형식 동일 (judging 모드 진입 시 추가 박제만).

---

## 박제 정합성 (Cross-Reference Summary)

본 plan 산출물이 정합해야 하는 source:

| Source | 정합 항목 |
|---|---|
| PROJECT.md Active Requirements "점수 신뢰도" | "IPSF 5트랙 채점 시스템 v1 박제" 항목 ✓ (T-2) |
| REQUIREMENTS.md SCORE-05 | (a) + (c) + Page 9 트랙 ✓ (T-2) |
| REQUIREMENTS.md TERM-01 | 학원 용어 3분기 시스템 ✓ (T-1/T-3/T-4) |
| REQUIREMENTS.md TERM-DATA-01 | AKA 매핑 13개 + 분기 2 reference + 분기 3 스키마 ✓ (T-1/T-3/T-4) |
| REQUIREMENTS.md TERM-COPY-01 | belle 작성 카피 그대로 박제 ✓ (T-5) |
| memory [[ipsf-5-track-scoring]] | 5트랙 구조 + v1/v2 scope ✓ (T-2) |
| memory [[studio-term-3branch-system]] | 3분기 시스템 + UX 카피 + T-3/T-6 belle 결정 박제 ✓ |
| memory [[judging-baseline-ipsf-code-of-points]] | IPSF 단일 기준 ✓ (T-1/T-2) |
| memory [[analysis-objectivity-no-human-scores]] | 사람 점수 라벨링 영구 금지 ✓ (T-3/T-4) |
| memory [[mode3-progress-not-similarity]] | mode3 reference 없는 채점 IPSF 공식 근거 ✓ (T-2 — Page 9 트랙) |
| memory [[notebook-lm-pole-sports]] | NotebookLM lookup 자동화 path ✓ (T-1 — 13개 매핑 출처) |

---

## 코드 변경 횟수

**0** (의도된 0 — MVP 가볍게 박제만, 코드 통합은 후속 plan)

### 신규 파일 (data/spec/doc)

- `backend/data/aka-mapping.json` (data — T-1)
- `backend/data/reference-motions-branch2.json` (data — T-3)
- `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` (spec — T-2)
- `.planning/phases/16-studio-term-foundation/16-AUTOCOLLECT-SCHEMA.md` (spec — T-4)
- `.planning/phases/16-studio-term-foundation/16-COPY-PLACEMENT.md` (doc — T-5)
- `.planning/phases/16-studio-term-foundation/16-01-SUMMARY.md` (본 문서 — T-7)

### 갱신

- `.planning/ROADMAP.md` (Phase 16 Success #7 belle 결정 박제 — T-6)
- `.planning/STATE.md` (decision 추가 — T-6)
- `~/.claude/.../memory/studio-term-3branch-system.md` (How to apply T-6/T-3 박제)

---

## 주요 인사이트 (memory 박제 후보)

### championPersonalAlias 필드 신설 (T-3 결과)

학원/IPSF/reference 인물 본인이 사용하는 명칭이 모두 다른 케이스가 존재 (예: 학원 = 폭스탑, IPSF = 비등재, 정은지 본인 = 버터플라이 콤보). 분기 2 reference 의 정확한 채점 컨텍스트를 위해 reference 인물 본인 호칭을 별도 필드로 박제 필요. 이미 [[studio-term-3branch-system]] 에 박제됨.

### 실증 게이트 = 분석 정확도 > 매핑률 (T-6 결과)

belle 의 의도가 명확해짐: "매핑률" 같은 메트릭은 v1 게이트 아님. 진짜 게이트는 **분석 정확도 + 고수 위양성 방지** (이미 SCORE-04 + Phase 15 신뢰도 게이트로 박제). Phase 16 의 v1 박제는 분석 정확도 게이트의 데이터 인프라일 뿐. [[feedback-analysis-first]] 정합 — "분석 망하면 다 망함".

---

*Plan 16-01 완료 2026-06-02. Phase 16 (MVP scope) 의 모든 박제 완료 — 후속 plan (Phase 5/14/15) 진입 가능.*
