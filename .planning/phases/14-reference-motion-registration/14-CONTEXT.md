# Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드) - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

정은지 기준 모션이 Mode 1 비교에 **바로 쓰일 수 있도록**, 각 reference 가
`meanAngles · EXTEND 프로파일 · BodyNormalizationProfile · ForceDirectionPattern`
을 모두 갖추게 만든다. 등록 경로(촬영 조건/앵글)는 비교 분석 정확도가 최대화되는
방식으로 설계·문서화한다. (REQUIREMENTS REF-01)

이 phase 가 **하는 일**: 이미 phase4_v1 RTMW 3D pose 를 가진 reference 11개에
부족한 downstream 엔진 출력(Phase 5 EXTEND / Phase 6 정규화 / Phase 9 force)을
백필 + 다각도 캡처 가이드 문서화 + 단일시점 graceful 처리.

이 phase 가 **하지 않는 일** (다른 phase / 후속): Mode 1 end-to-end 실분석 검증
(Phase 15), 선수·학원 셀프 업로드 UI 와 동작 신청 플로우(기술 실증 후 후속),
신규 정은지 영상 촬영.
</domain>

<decisions>
## Implementation Decisions

### 데이터 소스 — reference 엔진 출력 채우기 (Q1)
- **D-01:** **저장된 phase4_v1 `joints3d` 재사용 + research 게이트 하이브리드.**
  오늘(2026-06-15) 전체 11개 reference 가 RTMW 로 재처리되어 `joints3d`/`angles`/
  `keypointReport` 가 `reference/{id}/versions/phase4_v1` active 로 저장됨. Phase 14 는
  이 **검증된 pose 를 그대로 재사용**하고, 그 위에 EXTEND / BodyNormalizationProfile /
  ForceDirectionPattern 을 **학생 분석과 100% 동일한 _process 함수**로 계산한다 (분기 0,
  코드 1벌 — 위양성 방지의 본질은 reference 와 학생이 동일 계산 경로를 거치는 것).
- **D-02 (research 게이트 — planner 필수 검증):** 영상 전체 재추론(옵션2)은 채택하지
  않는다. 이유: 같은 RTMW + 같은 영상 = 같은 pose 라 **정확도가 더 높아지지 않으며**
  (독립 재검증이 아님), 오늘 belle 이 시각검증 PASS 한 pose 를 새 추론으로 대체하면
  재검증 부담만 생긴다. **단** 옵션1 의 유일한 리스크 = "저장된 reference 문서가
  downstream 함수(특히 Phase 9 force)의 입력 요구를 충족하지 못할 가능성". 따라서
  research/plan 단계에서 **"Phase 6/9/EXTEND 함수가 소비하는 입력 ⊆ phase4_v1 에
  저장된 데이터"** 를 검증한다 → 충족 시 stored 재사용, **부족한 필드에 한해서만**
  Pod 재추론(하이브리드). 전역 재추론 금지.

### 다각도 vs 단일시점 정합 (Q2)
- **D-03:** **단일시점으로 통일.** reference 도 학생과 동일하게 단일시점 기준으로
  계산한다. ROADMAP SC#3 의 "다각도 캡처 프로토콜" 은 **촬영 가이드 문서로만** 남기고
  (정은지 세션의 권장 촬영 조건·앵글), 단일시점 입력도 graceful 하게 처리하며 다각도
  부재 시 confidence 를 낮게 표기한다. Phase 4 pivot(단일시점 + AI 가상 다각도 합성,
  다중 시점 직접 업로드 영구 제거)과 정합 — [[camera-angle-ai-single-view-synth]] /
  [[single-camera-first-multi-view-last]].

### 등록 주체 / 경로 (Q3)
- **D-04:** **admin CLI 스크립트.** 운영자(belle)가 CLI 로 reference 를 등록/백필한다.
  Phase 6 의 `extract_reference_body_profiles.py` + `seed-reference-body-profile.mjs`
  패턴을 확장한다. reference 는 수강생용 입력이 아니므로 앱 내 등록 UI 불필요 — MVP 충분.

### 대상 동작 세트 (Q4)
- **D-05:** **기존 11개 reference 백필, 신규 촬영 0.** 이미 phase4_v1 active 인 11개
  reference 에 EXTEND/정규화/force 를 채워 완결한다. Mode 1 v1 비교 대상 = 이 11개.

### Claude's Discretion
- 백필 스크립트의 정확한 entrypoint 구조(기존 reprocess/extract 스크립트 확장 vs 신규
  단일 스크립트), 버전 쓰기 전략(phase4_v1 in-place merge vs 신 versioned write),
  atomic write/rollback 메커니즘은 planner 재량 — 단 D-01 의 "동일 함수 재사용" 과
  Firestore flat-array 규약([[firestore-nested-array-flat]] / [[firestore-index-entry-limit]])
  을 지킬 것.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 정의 / 요구사항
- `.planning/ROADMAP.md` — Phase 14 섹션 (Goal/Depends on/Success Criteria, line ~402)
- `.planning/REQUIREMENTS.md` — REF-01 (등록 경로 정확도 최대화 요건)
- `.planning/phases/06-coaching/06-CONTEXT.md` — Phase 6 reference 백필 선례 컨텍스트

### 재사용할 백필 인프라 (D-04 확장 대상)
- `backend/scripts/extract_reference_body_profiles.py` — Phase 6: Pod 에서 reference
  bodyNormalizationProfile + bodyComparisonSourcePose 산출. Phase 14 는 EXTEND/force 추가 확장.
- `app/scripts/seed-reference-body-profile.mjs` — Firebase Admin SDK 로 reference 필드
  atomic merge seed (--dry-run 패턴 포함).
- `backend/shared/python/sunity_shared/firestore_admin.py` — `update_reference_body_data`
  (line 850, 두 필드 atomic merge) / `complete_analysis` (line 682, 분석 문서 쓰기 형식)
- `backend/scripts/reprocess_reference_motions_phase4.py` — Phase 4 versioned write +
  active flip 패턴 (MOTION_IDS default=5 → 신규는 --motions 명시 필요, [[reference-library-phase4-all11]])
- `backend/scripts/rollback_reference_motions_phase4.py` — `--to-version pre_phase4` rollback

### 동일 계산 경로 (D-01 — 학생 분석과 1벌)
- `backend/functions/pipeline/app.py` — `_process` (line 1510) + `_extract_video_analysis_inputs`
  (line 1135, RTMW 1회 실행 + downstream 입력 산출). reference 백필이 호출/재사용해야 할 함수.
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py` — Phase 6 정규화
- `backend/shared/python/sunity_shared/analysis/force_signals.py` — Phase 9 ForceDirectionPattern
  (research D-02: 이 함수가 소비하는 입력이 phase4_v1 저장 데이터에 있는지 검증)
- `backend/shared/python/sunity_shared/analysis/technique.py` — EXTEND 프로파일(기술 인식 조건부)

### 데이터 계약 / reference 문서 형식
- `docs/contract.md` §`reference/{motionId}` (line ~83, ReferenceMotion 형식) + §8 (BodyComparison)
- `backend/functions/reference-api/app.py` — GET /reference (Mode 1 목록 노출)
- `app/src/lib/referenceMotions.ts` — 앱 reference 소비 (Mode 1 목록)

### 도메인 / 채점 근거
- 메모리 [[ipsf-5-track-scoring]] / [[judging-baseline-ipsf-code-of-points]] — reference 측정값 채점 분기
- 메모리 [[studio-term-3branch-system]] — 분기 1(IPSF 등재) vs 분기 2(정은지 reference) 구분

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 6 reference 백필 3종(`extract_reference_body_profiles.py` /
  `seed-reference-body-profile.mjs` / `firestore_admin.update_reference_body_data`):
  이미 "Pod 산출 → atomic merge → seed → revert/dry-run" 전 사이클이 있음. Phase 14 는
  여기에 EXTEND + ForceDirectionPattern 필드를 추가하는 확장으로 설계 가능.
- `reprocess_reference_motions_phase4.py`: versioned write + active flip + pre_phase4 백업
  패턴 보유 — 백필 결과를 새 버전/필드로 안전하게 쓰는 데 재사용.
- `_extract_video_analysis_inputs` / `_process`: 학생 분석의 단일 코드 경로. D-01 의
  "동일 함수 재사용" 은 이 경로의 downstream 부분을 reference 입력(stored joints3d)에
  적용하는 형태.

### Established Patterns
- **Firestore flat-array 규약**: (T,J) 행렬은 nested array 금지 → flat 저장 + 읽는 쪽
  reshape. reference 의 joints3d/angles 도 동일 ([[firestore-nested-array-flat]]).
- **Firestore 40k index-entry 한도**: 대형 flat 배열(joints3d 등) field index 면제 필요
  ([[firestore-index-entry-limit]]) — 신규 필드가 대형 배열이면 동일 면제 적용.
- **Pod ops = Claude 실행**: 백필 Pod 실행/검증은 내 몫, belle 는 production 승인만
  ([[pod-ops-claude-runs]]). Pod 작업 전 로컬 commit→push ([[gsd-pod-work-push-first]]).

### Integration Points
- 백필 결과 → `reference/{motionId}` 문서 (GET /reference → 앱 Mode 1 목록).
- reference 의 EXTEND/정규화/force → Phase 15 Mode 1 비교 입력(학생 분석과 대조).

### 운영 환경 (이미 준비됨, 2026-06-15)
- RunPod Pod `qcf38vvsmub1y4` (RTX PRO 4500 Blackwell) UP, /health ok,
  Lambda `RUNPOD_ANALYZE_URL` 동기화 완료. 하이브리드 재추론 필요 시 즉시 사용 가능.
  셋업 재현 레시피 = [[runpod-gpu-env]] 2026-06-15(2차) 항목.
</code_context>

<specifics>
## Specific Ideas

- 위양성 방지의 본질을 belle 이 명시: reference 와 학생이 **동일 계산 경로**를 거치는 것이
  핵심이지, reference 를 "다시 추론"하는 게 정확도를 높이는 게 아니다 (같은 모델+같은 영상
  = 같은 숫자, 독립 재검증 아님). → D-01/D-02 의 근거.
- 단일시점 통일은 학생 입력 조건과 reference 조건을 맞추기 위함 (비대칭 회피).
</specifics>

<deferred>
## Deferred Ideas

- **선수·학원 셀프 업로드 + 동작 신청 플로우** — belle: "나중엔 선수와 학원에서 업로드
  가능하게, 동작 신청도 할 수 있어야 함. MVP 범위 아니고 기술 실증 후 생각할 일." →
  reference 등록을 운영자 CLI 너머 셀프서비스화하는 별도 후속 phase 후보.
- **실제 다각도 촬영 기반 reference** — D-03 에서 단일시점 통일로 결정. 다각도 직접 캡처는
  단일시점/AI 합성 path 가 정확도 한계에 부딪힐 때의 최후 수단([[single-camera-first-multi-view-last]]).
- **신규 정은지 영상 촬영 등록** — Phase 14 는 기존 11개 백필로 한정(D-05).

### Reviewed Todos (not folded)
None — cross-reference 결과 매칭 todo 0.

</deferred>

---

*Phase: 14-reference-motion-registration*
*Context gathered: 2026-06-15*
