---
phase: 33-result-trust-recovery
plan: 08
subsystem: presentation-substrate
tags: [a-track, motion-standards, domain-facts, d-09, candidate-substrate]
requires:
  - "33-20 (33-COVERAGE-MATRIX.md — canonical 11-motion 인벤토리)"
  - "33-03/04/05/17 staged candidate substrate (phase33-cm3-run1, shadow resolver 경로)"
provides:
  - ".planning/phases/33-result-trust-recovery/33-A1-MOTION-STANDARDS.md — 동작 x 4질의 표 (등재 10동작 전수, 방향 claim 전수 ref-frame 대조)"
affects:
  - "33-09 (A-2 코칭 문구 — ①③열 소비)"
  - "33-10 (A-3 크롭 설계 — ④열 소비)"
  - "33-14 (A-7 일러스트 — ②열 소비)"
tech-stack:
  added: []
  patterns:
    - "candidate 버전 read-only 대조 (reference/{id}/versions/phase33-cm3-run1 직접 열람, top-level 무접촉)"
key-files:
  created:
    - ".planning/phases/33-result-trust-recovery/33-A1-MOTION-STANDARDS.md"
  modified: []
decisions:
  - "power-spin 사실층 확정: 실측(candidate f71~f92 + 원본 영상 8s/9s 육안) = 폴 축 상하 수직 스플릿 — '천장' 단일 큐도 '옆(스트래들) 벌림'도 오답으로 기각 (D-18 대조가 계획 문면의 example claim 을 정정)"
  - "peter-pan 스태그 좌우 = 오른무릎 hook / 왼다리 신전 (candidate + techniqueProfile 합치, seed 문서 반대 기재 → 정정 기록)"
  - "ref-combo = A-1 명시적 제외 (미등재, COVERAGE-MATRIX consumer contract — 조용한 스킵 아님)"
  - "강사 교정 어휘(③열)는 기존 문서 어휘 재조합임을 UNVERIFIED 로 박제 — 강사 인터뷰 원문 미보유"
metrics:
  duration: "23m"
  tasks: 2
  files: 1
completed: 2026-07-28
---

# Phase 33 Plan 08: A-1 동작별 기준 자세 조사 표 Summary

**한줄 요약:** 등재 10동작 전수의 동작x4질의 표를 candidate substrate(phase33-cm3-run1)
프레임 전수 대조로 작성 — power-spin 은 "천장/옆" 둘 다 아닌 **폴 축 상하 수직 스플릿**으로
사실층에서 정정했고, 모든 방향 claim 에 열어본 프레임 번호 또는 UNVERIFIED 태그를 달았다.

## 수행 내용

### Task 1 — fixture 6동작 (commit b80770f)

- power-spin / peter-pan / elbow-twist-sister / pdshape / kip-up / climb 의 4질의 행 작성.
- criteria scope = phase25 sweep report 의 fault 멤버 activatedCriteria 인용 (climb 은
  status=comparison, 스코어리스 비교 게이트 — COVERAGE-MATRIX (a) 항 그대로).
- **전 방향 claim 을 candidate 문서 joints3d 로 대조:** Firestore
  `reference/{id}/versions/phase33-cm3-run1` 을 읽기 전용으로 열어 (F,17,2) 재구성, peak
  window 프레임별 다리 방향각·인버전 비율·관절각 산출 (결측 프레임 span<30px 제외).
- **power-spin 은 원본 영상까지 열람:** S3 ref-power-spin.mp4 8s/9s 프레임 2장 추출·육안 —
  수치와 동일하게 "한 다리 폴 따라 위, 반대 다리 아래" 수직 스플릿 확인
  ([[open-the-artifact-before-claiming-done]]).

### Task 2 — 등재 10동작으로 확장 + fixture-less 대체 증거 (commit b641b86)

- foxtop / foxtop-split / invert / sideway-spin 4행 추가. 각 행에
  "no fixture mp4 — verified against reprocessed reference doc
  `reference/{id}/versions/phase33-cm3-run1`" + S4 self-comparison(100점/maxDev≈0.003) +
  M8 크롭 PNG 열람을 명시 (D-23 무언 스킵 금지).
- ref-combo 는 미등재 → A-1 제외를 문서에 명시(행 부재가 곧 명시).
- 커버리지 산술 체크: 표1(6) + 표2(4) = 등재 10 = REGISTERED_MOTIONS(10).

## 도메인 소싱 (D-09: 질의 고정, IPSF 전체 읽기 금지)

- **NotebookLM 폴스포츠 노트북(96b061e8) CLI query 2건** (MCP 도구는 이 에이전트 컨텍스트에
  미노출 → `nlm notebook query` CLI 로 대체, 인용 포함 정상 응답):
  1. 스트래들/수직 스플릿 계열 완성 기준 + 흔한 실행 감점 (Aerial Hoop CoP p.15 3D
     perspective rule, F-코드 Criteria, micro-bent 0점 무효 등)
  2. 인버트/레그행/엘보그립/스핀 모멘텀/클라임 계열 (접촉 부위 Criteria, re-grip −0.5,
     모멘텀 상실 −2.0, climb 2회 반복 요건)
- repo-local: criteria yaml 10종(정은지 측정 박제), reference-motions.md v6(선수 확정),
  seed 스크립트 CROSS-CHECK 노트, 폴스포츠-지식.md 보고서 4-6, 현장 설문(강사 철학).

## Deviations from Plan

### 1. [계획 문면 정정 — D-18 작동] power-spin "legs to the SIDE" 는 실측과 모순 → 기각

- **발견:** Task 1 cross-check. 계획 acceptance 는 "legs-to-the-SIDE 를 기록하라" 였으나,
  열어본 reprocessed 프레임(f71~f92)과 원본 영상 프레임 2장 모두 **폴 축 상하 수직
  스플릿**(한 다리 위 155~180°, 반대 다리 아래 0~33°, 무릎 165~176° 신전)을 보였다.
- **처리:** 계획 본문의 상위 규칙("a claim that contradicts the ref frame is corrected or
  dropped, not shipped" / threat T-33-39 mitigate)을 우선 적용 — 행에는 정정된 사실을
  기록하고, belle "천장" 모순은 사실층에서 해결("천장 단일 큐 오답 — 위로 가는 다리는
  하나, 반대 다리는 아래로"). "옆으로" 표현의 기각도 표에 명시.
- **후속 소비자 영향:** A-2(33-09) 코칭 문구는 "옆으로 뻗으세요" 가 아니라 위·아래 다리를
  구분한 큐를 써야 한다.

### 2. [정정 발견] peter-pan 스태그 좌우가 seed 문서와 반대

- candidate 실측(36프레임 일관: 왼 무릎 176~178° 신전 / 오른 무릎 40~107° hook 굽힘)과
  techniqueProfile(left_knee=extend)이 합치, seed 스크립트 checkpoints(왼쪽=hook)와 모순.
  표에 정정 기록. 좌우 라벨 계열 이슈(회전 중 키포인트 좌우 혼동 한계)는 power-spin 위
  다리 좌우와 함께 UNVERIFIED 절에 박제.

### 3. [Stale 참조] 33-07-SUMMARY.md 부재 — belle A-트랙 우선 결정 반영

- 계획 context 의 `33-07-SUMMARY.md` 는 존재하지 않음(flip 이연, belle 2026-07-28 결정).
  계획 상단 수정 노트가 지시한 대로 cross-check 은 candidate 를 직접 읽었다(33-17 shadow
  경로와 동일한 versions/ 서브컬렉션, top-level 무접촉·write 0). 의존성은 33-20 으로 충족.

### 4. [Scope 정합] "11 registered" → 등재 10 + combo 제외

- 계획 objective 의 "11 registered" 는 canonical COVERAGE-MATRIX 가 이미 정정한 수치
  (등재 10 + 미등재 combo 1). 매트릭스의 33-08 consumer contract 를 그대로 따랐다.

### 5. [도구 대체] NotebookLM MCP → nlm CLI

- MCP 도구가 이 실행 컨텍스트에 미노출 → `nlm notebook query` CLI 로 동일 노트북 질의
  (인용 포함 정상 동작). 기능 손실 없음.

## Known Limits (표 안의 UNVERIFIED 로 노출)

- power-spin 위 다리의 좌우 라벨 (candidate=왼쪽 vs seed=오른쪽 — 좌우 혼동 가능성)
- ③열 강사 교정 어휘 전체 (인터뷰 원문 미보유 — 기존 문서 어휘 재조합)
- sideway-spin 척추 아치 곡률 (spine_mid 키포인트 부재 — 각도 데이터 없음)
- fixture-less 4동작의 ②열 근거 등급 (fault 실측 아님 — 노트+IPSF 감점 언어)

## Self-Check: PASSED

- [x] `.planning/phases/33-result-trust-recovery/33-A1-MOTION-STANDARDS.md` 존재
- [x] `grep -c "완성 기준"` = 2 (Task 1 verify), `ref-foxtop|ref-invert|ref-sideway-spin` 매치 (Task 2 verify)
- [x] commit b80770f (Task 1) / b641b86 (Task 2) 존재
- [x] STATE.md / ROADMAP.md 무접촉 (worktree 모드 — 오케스트레이터 소관)
