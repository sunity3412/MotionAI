---
phase: 33-result-trust-recovery
plan: 10
subsystem: presentation-faultzoom-design
tags: [a-track, a-3, fault-zoom, d-07, d-24, seam-1, investigation-only]
requires:
  - "33-08 (33-A1-MOTION-STANDARDS.md ④열 — 도메인 강 원천)"
  - "33-09 (phrasebook 동작 전용 entry — 탭-상세 글결합의 born-matched 반쪽)"
  - ".planning/debug/resolved/faultzoom-same-frame-crops.md (벤치마크·프레이밍 실험·facing 프로브·belle 확정 3건 — 재발산 금지 입력)"
provides:
  - ".planning/phases/33-result-trust-recovery/33-A3-ZOOM-DESIGN.md (D-07 6기준 고정 + 근거 3갈래 + 옵션 채택/기각 + seam #1 결정)"
affects:
  - "33-11 (A-4 목업 — 살아남은 2안 + D-08 최악 케이스 3종만 그림)"
  - "A-5 (구현 — seam 결정·계약 갱신 지침 소비, 재결정 금지)"
tech-stack:
  added: []
  patterns:
    - "criterion-keyed crop provenance (항목↔크롭 정합을 조인이 아니라 출생에서 보장 — IPSF 심판의 criteria 1:1 대조 관용구의 직역)"
    - "data-limit-first design gate (백엔드가 못 주는 데이터를 그린 옵션은 목업 전 INVALID — D-12/D-24)"
key-files:
  created:
    - .planning/phases/33-result-trust-recovery/33-A3-ZOOM-DESIGN.md
  modified: []
decisions:
  - "seam #1 = backend criterion-keyed crops 채택 (RESEARCH Open Q2 해소). app joint-exact join 단독안 기각 — vision record 전체 투영(deductionLabels.ts:236)은 앱 단독으로 못 고치고, record별 관절 provenance 는 결국 백엔드 방출 필요. 키 일치 join 은 백엔드안의 앱측 반쪽으로 흡수"
  - "관용구 INVALID 4종: 반투명 겹침·슬라이더 와이프(정합 보장 불가 — facing 신호 부재+역립 환각), 유령 실루엣(8관절+환각으로 자신 있게 틀린 형상), 궤적선(회전 자기겹침+flicker). 나란히/마커 원 VALID, 각도호 VALID-게이트 유지"
  - "옵션 = 새로 만들지 않고 framingexp A/B/C/D 채택/기각 박제 (belle 육안 확정분): D 기본 화면 채택 / A 탭-상세 승계 / B·C 기각. 살아남은 안 2개만 A-4 목업행"
  - "A-4 목업 필수 최악 케이스 3종 지정: 역립 마커 강등 / relaxed·full 폴백 카드 / DTW refMatch='failed' 상세 (D-08)"
metrics:
  duration: "11m"
  tasks: 2
  files: 1
completed: 2026-07-28
---

# Phase 33 Plan 10: A-3 확대비교 재설계 조사 Summary

**한줄 요약:** D-07 판정 기준 6개를 옵션에 앞서 문서 고정하고, 도메인(A-1 ④열 +
NotebookLM 신규 query — IPSF 심판은 criterion-키 부위·고정 순간으로 관찰)·선행사례
(debug 벤치마크 확정분)·데이터 한계(fault_zoom.py 9개 실측 제약, INVALID 관용구 4종)
3갈래를 종합해 framingexp A/B/C/D 의 채택/기각을 D-07 로 박제했으며, seam #1 은
**backend criterion-keyed crops** 로 결정(candidate substrate 재확인: crop 출처 이원화는
substrate 무관 구조 결함)해 A-5 가 재결정 없이 구현하게 했다 — 조사 전용, 코드 변경 0.

## 수행 내용

### Task 1 — D-07 고정 + 근거 3갈래 (commit 4991abc)

- **1절**: D-07 6기준 verbatim 박제 (D-24 순서 — 기준이 옵션보다 먼저) + D-05 해법
  순서·D-08 최악 데이터 목록·D-12 카드 불변식을 보조 제약으로 명시.
- **2(a) 도메인**: A-1 ④열 10동작 "어디를·어느 순간" 표 + 학원 관용구→화면 은유 매핑
  (손짚기→마커 전부 / 나란히→탭-상세 쌍 / 시범→기준 패널+일러스트 슬롯).
  **NotebookLM 신규 query 1건**: 강사 지도 방식(거울/손짚기 등)은 출처 부재로 명시
  (숨기지 않음), 대신 IPSF 심판 관찰 방식이 상세 문서화 — Fixed Position(고정 시점부터
  측정)·신체 영역 다이어그램(해부학 경계로 잘라 봄)·**criteria 1:1 대조** = 심판의
  관찰 자체가 criterion-키 구조라는 발견이 4절 seam 결정의 도메인 근거가 됨.
- **2(b) 선행사례**: debug 벤치마크(V1/OnForm/Sportsbox/Ochy/coach.ly — 자동 관절
  타이트크롭 기본표시 선례 0) 재조사 없이 박제 + 관용구 7종 강/약 표.
- **2(c) 데이터 한계**: fault_zoom.py 를 직접 열어 (D-19 — 함수:라인 전부 인용)
  9개 제약 확정: 640px 소스/2.4× 업스케일, `_side_crop:975` 3단 강하(마커 게이트),
  fps 공간 3종의 `_to_rep_idx:196` 라우팅(+mode3 dtw_ref_fps 잔존 함정 — candidate 는
  ref 9fps 재추출로 identity), `_matched_ref_frame:715` DTW 실패 시 refMatch='failed'
  정직 폴백, facing 원리적 부재(프로브 실측 — belle A 글 흡수), 역립 환각+좌우 귀속
  불신(IN-01), 좌표 결측 실재, veto 다관절 카드 붕괴, spine_mid 부재.
  **INVALID 4종 확정** (겹침/와이프/유령/궤적) — 이 절이 D-18 "틀리면 걸리는 장치".

### Task 2 — 옵션 채택/기각 + seam #1 결정 (commit 99eb47b)

- **3절**: framingexp A/B/C/D (S3 실렌더 + belle 육안 완료분) 채택/기각을 D-07 근거로
  박제 — D 기본 화면 채택(belle verbatim), A 탭-상세 승계, B(마커 무)·C(인물 소) 기각.
  갈래 지점(나란히 vs 겹침 / 크기 기준 / 차이 표시 / 캡션) 결정 기록.
- **4절**: seam #1 = **backend criterion-keyed crops**. 근거 5개: ① candidate substrate
  재확인 — record 방출 7 criteria vs crop 3장(legs 묶음+advisory arms)으로 집합 불일치가
  substrate 복원 후에도 잔존 = 출처 이원화(`app.py:3098` vv.faultJoints vs records[])의
  구조 결함 ② 결함⑤(vision 전체 투영)는 앱 단독 수정 불가 ③ IPSF criteria 1:1 대조
  도메인 정합 ④ Ochy 탭-상세가 record 단위 born-match 요구(글은 33-09 로 이미
  criterion-키) ⑤ Pod 가동 중(8hrks3hrxmtgw6)이라 재생성 비용 조건 충족.
  기각안(app join 단독) 사유 기록 + 키 일치 join 은 백엔드안의 앱측 반쪽으로 흡수.
  A-5 구현 지침(재결정 금지 범위): criterion→관절 매핑 백엔드 미러, payload 에
  criterion scalar 추가(계약 3파일 동시 갱신), advisory tier 분리 유지, 전수 assert+
  PNG 열람 검증.
- **5절**: 살아남은 2안(D 기본/탭-상세 세트)의 D-07 6기준 사전 판정표 — 좋은 케이스
  + D-08 최악 케이스. A-4 목업 필수 포함 최악 케이스 3종 지정.

## 검증 (플랜 verify 전항)

- `33-A3-ZOOM-DESIGN.md` 존재 + "판정 기준|D-07" grep PASS + "fps|confidence" grep PASS
- "criterion-keyed|joint-exact" grep PASS + "안 ?[0-9]|Option" 7건
- INVALID 관용구 4종 (요구 "최소 1종" 초과 충족)
- seam #1 결정 = 근거 5개 + 기각안 사유 + A-5 지침으로 무모호 기록

## Deviations from Plan

### 1. [계획 문면 stale — 2026-07-28 수정 노트 준수] 재발산 금지 스코프 축소 이행

- 계획 본문 Task 1/2 는 선행사례 조사·옵션 신규 생성·같은-데이터 렌더를 지시하나,
  계획 상단 2026-07-28 수정 노트가 debug 종결분(벤치마크·프레이밍 실험·facing·belle
  확정 3건)을 재조사/재제안 금지로 못박음. 수정 노트를 따라 확정분은 **박제**(출처
  인용)하고 남은 스코프(① D-07 고정 ② 도메인 갈래 ③ seam 결정 ④ 종합)만 신규 수행.
  "2-3 options" 요건은 노트 지시대로 framingexp A/B/C/D 채택/기각 기록으로 충족.

### 2. [계획 문면 stale — flip 이연] "flipped substrate" → candidate 직접 재확인

- 계획 objective/Task 2 의 "flipped substrate (33-07)" 은 belle A-트랙 우선 결정으로
  staged candidate(phase33-cm3-run1)를 뜻함 (track_context). seam 근거 1 의 A-0 재평가는
  candidate substrate 실측(debug 2026-07-28 렌더 3장 + faultJoints 프로브)으로 수행 —
  flip 시 동일 데이터가 활성화되므로 재작업 없음.

### 3. [Rule 2 — 근거 보강] NotebookLM 신규 query 로 도메인 강 실측 추가

- 계획 read_first 는 A-1 표 소비만 명시했으나 남은 스코프 노트가 "갈래 (a) =
  33-08 표 + NotebookLM" 을 지정 — `nlm query` 1건 수행. 강사 지도 방식의 출처 부재를
  명시(조용한 재조합 방지)하고 IPSF 심판의 criterion-키 관찰 방식을 신규 확보 —
  seam 결정의 도메인 근거로 직결. 코드 변경 0, 문서 근거 강화만.

## Known Stubs

없음 — 조사 전용 문서 산출물. 코드/데이터 스텁 해당 없음.

## Threat Flags

없음 — 신규 표면 0 (문서만). T-33-42(옵션 vs 백엔드 능력)는 2(c) INVALID 게이트로
mitigate 완료.

## Self-Check: PASSED

- [x] `.planning/phases/33-result-trust-recovery/33-A3-ZOOM-DESIGN.md` 존재 (312줄)
- [x] commit 4991abc (Task 1) / 99eb47b (Task 2) 존재
- [x] 자동 검증 grep 4종 전부 PASS (위 검증 절)
- [x] 코드/채점 파일 무접촉 — git diff 스코프 = .planning 문서 2파일뿐
- [x] STATE.md / ROADMAP.md 무접촉 (worktree 모드 — 오케스트레이터 소관)
