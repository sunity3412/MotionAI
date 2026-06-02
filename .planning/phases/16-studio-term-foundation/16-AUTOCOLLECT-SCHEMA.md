# 16-AUTOCOLLECT-SCHEMA.md — 분기 3 자동 수집 데이터 스키마 (Branch 3)

**Phase**: 16 (Studio Terminology Foundation)
**Plan**: 16-01 (T-4 산출물)
**Mode**: spec / schema definition (코드 변경 0)
**Created**: 2026-06-02
**Authority**: Phase 5 / Phase 14 / Phase 15 통합 시 Firestore 컬렉션 생성/wiring 의 source of truth.

---

## 1. Goal

분기 3 — IPSF 미등재 + 정은지 reference 없음 케이스에서 사용자가 입력한 동작 키워드를 **자동 수집**해 후속 표준화 path 의 입력 데이터로 누적할 Firestore 컬렉션 스키마 박제. 본 plan 에서는 **스키마/보안 규칙/익명성 요건만 박제** — 실제 수집 wiring 은 후속 plan (Phase 5).

박제 동기: KPSA 도 작성 안 한 한국어 학원 용어 표준 작성 path 는 분기 3 누적 데이터에서 시작. 스키마가 박제 안 되면 후속 plan 에서 필드 누락 / 익명성 위반 / 학원 ID 트래킹 같은 결정이 임시방편으로 굳어질 위험.

---

## 2. 컬렉션 — `pending_terms`

Firestore root-level 컬렉션. 사용자 권한 범위 밖 (read/write 모두 백엔드 전용).

### 필드 스키마

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `termId` | string | ✓ | 자동 생성 ID (Firestore auto-id 권장) |
| `inputKeyword` | string | ✓ | 사용자가 입력한 원문 키워드 (예: "사이드웨이 스핀") |
| `normalizedKeyword` | string | ✓ | 정규화 (소문자 화 / 공백 trim / 한글 NFC 정규화) → 동일 키워드 dedup key |
| `firstSubmittedAt` | timestamp | ✓ | 최초 입력 시각 (Firestore server timestamp) |
| `lastSubmittedAt` | timestamp | ✓ | 최근 입력 시각 |
| `submitCount` | number | ✓ | 누적 입력 횟수 (서로 다른 사용자가 같은 키워드 → +1) |
| `uniqueUserCount` | number | ✓ | 고유 사용자 수 (anon userId 기준 — Set 크기) |
| `associatedAnalysisIds` | string[] | ✓ | 익명 분석 ID 목록 (검증/디버그용. 사용자 식별 정보 X) |
| `promotionStatus` | enum | ✓ | `pending` \| `reviewing` \| `promoted_to_branch2` \| `promoted_to_branch1` \| `rejected` |
| `promotionThresholdMet` | boolean | ✓ | 실증 게이트 충족 여부 (T-6 박제 — MVP v1 = 둘 이상 anon userId) |
| `createdAt` | timestamp | ✓ | 문서 생성 시각 (= `firstSubmittedAt` initial) |
| `updatedAt` | timestamp | ✓ | 문서 갱신 시각 |

### 선택 필드 (v2 후속 확장 가능)

| 필드 | 타입 | 설명 |
|---|---|---|
| `studioIds` | string[] | 학원 ID 목록 (v2 — 학원 ID 트래킹 도입 시) |
| `notebookLookupResult` | object | 정기 NotebookLM batch query 결과 (분기 1 승격 후보 검토) |
| `belleReviewedAt` | timestamp | belle 검토 시각 (`promotionStatus` 변경 시 박제) |
| `belleReviewNote` | string | belle 검토 코멘트 |

---

## 3. 익명성 요건 (CRITICAL)

[[analysis-objectivity-no-human-scores]] + Firebase 익명 인증 정합:

1. **사용자 식별 정보 직접 박제 금지** — uid / email / 이름 / 학원 ID 직접 박제 X.
2. **`associatedAnalysisIds` 는 익명 분석 ID 만** — `users/{uid}/analyses/{id}` 의 `{id}` 는 무의미한 UUID 라서 식별 정보 아님.
3. **`uniqueUserCount` 계산 방식** — 백엔드에서 `pending_term_submissions/{termId}/{anonUserId}` 보조 컬렉션 (또는 동등 구조) 으로 unique set 관리. anonUserId 는 사용자 식별 가능하면 안 됨 — Firebase uid 의 hashing 또는 별도 anonymized counter 권장.
4. **사용자 직접 read 차단** — Firestore 규칙에서 root-level `pending_terms` 컬렉션은 사용자 권한 차단.

---

## 4. Firestore 보안 규칙 (예상 변경)

현 `firestore.rules` 는 `users/{uid}` 와 `reference/` 만 정의. 본 plan 진입 시 다음 규칙 추가 (실 wiring 은 후속 plan):

```javascript
// 분기 3 자동 수집 — 사용자 직접 접근 차단, 백엔드 전용
match /pending_terms/{termId} {
  allow read, write: if false;  // Lambda + Admin SDK 만
}

// 분기 3 보조 unique counter — 백엔드 전용
match /pending_term_submissions/{termId}/{anonUserId} {
  allow read, write: if false;
}
```

기존 deny-by-default 규칙으로도 차단되지만 명시적으로 박제하면 후속 plan 에서 일관성 보장.

---

## 5. 수집 흐름 (스펙만)

실 wiring 은 Phase 5 (Gemini 기술 인식기) 진입 시. 본 plan 은 흐름 박제만.

```
사용자 입력 키워드 (예: "사이드웨이 스핀")
   │
   ▼
backend AKA 매핑 lookup (backend/data/aka-mapping.json — T-1 산출물)
   │
   ├─ HIT  → 분기 1 처리 (IPSF Code + Criteria)
   │
   └─ MISS
       │
       ▼
       정은지 reference 매핑 lookup (backend/data/reference-motions-branch2.json — T-3 산출물)
       │
       ├─ HIT → 분기 2 처리 (정은지 측정값 기준)
       │
       └─ MISS
           │
           ▼
           분기 3 처리:
           (a) Page 9 절대 트랙 단독 채점 (16-SCORING-SPEC.md)
           (b) pending_terms 컬렉션에 키워드 박제 (본 스키마)
           (c) UX 카피 노출 (16-COPY-PLACEMENT.md — T-5 산출물)
```

---

## 6. 실증 검증 게이트 (T-6 belle 협의 박제)

belle 2026-06-02 결정:
- **분기 3 신규 키워드 승격 기준 = 둘 이상 anon userId** (MVP 단순. 학원 ID 트래킹은 v2).
- `promotionThresholdMet` 계산: `uniqueUserCount >= 2`.
- 승격 path:
  - `promotionThresholdMet = true` 진입 시 `promotionStatus: pending → reviewing` 자동 전환.
  - belle 검토 후 분기 1 (NotebookLM lookup 으로 IPSF Code 발견) 또는 분기 2 (정은지 영상 추가 캡처) 로 승격.
  - 분기 1/2 승격 후 `pending_terms` entry 는 보관 (이력 / 향후 분석).

---

## 7. v2 후속 확장 path

| 시점 | 확장 항목 |
|---|---|
| Phase 5 진입 | 본 스키마 기반 컬렉션 생성 + Lambda wiring + 보안 규칙 박제 |
| Phase 5 진입 | `pending_term_submissions` 보조 컬렉션으로 anonUserId set 관리 |
| 실증 데이터 후 | 학원 ID 트래킹 도입 (`studioIds` 필드 활성화) |
| 실증 데이터 후 | 정기 NotebookLM batch query (`notebookLookupResult` 필드 활성화) |
| v2 | belle 검토 UI (admin console 또는 별도 검토 path) |

---

## 8. Cross-Reference

| Source | 정합 항목 |
|---|---|
| `firestore.rules` | 본 스키마의 보안 규칙 (현 deny-by-default + 명시 박제) |
| REQUIREMENTS.md TERM-01 / TERM-DATA-01 | 분기 3 자동 수집 path + 데이터 스키마 |
| `.planning/phases/16-studio-term-foundation/16-SCORING-SPEC.md` (T-2) | 분기 3 = Page 9 트랙 단독 작동 근거 |
| `backend/data/aka-mapping.json` (T-1) | 수집 흐름의 분기 1 lookup 입력 |
| `backend/data/reference-motions-branch2.json` (T-3) | 수집 흐름의 분기 2 lookup 입력 |
| `.planning/phases/16-studio-term-foundation/16-COPY-PLACEMENT.md` (T-5) | 수집 시 사용자에게 노출되는 UX 카피 |
| memory [[studio-term-3branch-system]] | 분기 3 자동 수집 path + UX 카피 |
| memory [[analysis-objectivity-no-human-scores]] | 익명성 요건 + 사람 점수 라벨링 영구 금지 |

---

*Created 2026-06-02 (Plan 16-01 T-4 산출물 — 분기 3 자동 수집 스키마 박제)*
