# Phase 33 Discussion Log — 채점 재설계 트랙 (2026-07-24)

Human-reference record of the discuss-phase session that captured the scoring-redesign implementation decisions. Not consumed by downstream agents (they read `33-CONTEXT.md` + `33-SPEC.md`).

## Context

Entered via `/gsd-discuss-phase 33` after `/gsd-spec-phase 33` locked `33-SPEC.md`. SPEC locked WHAT (IPSF two-track cap, floor 60 execution, structural invariants); discuss covered HOW. Existing `33-CONTEXT.md` (D-01~D-32, 표현/substrate tracks) was UPDATED (not overwritten) — D-20/D-29 "채점 무접촉" superseded, D-33~D-38 added.

## Areas discussed (belle selected all three)

### Area 1 — 치명 트랙 판별 규칙
- Options: (a) 기존 0-fail 요소만 (임계 신설 0) / (b) 지금 일반화 (leg/arm에 요소-인정 임계 추가)
- **belle: (a) 기존 0-fail 요소만.** → D-35.

### Area 2 — deductionBreakdown 형상 + 앱 계약
- Options: (a) additive (track 라벨 + 집계필드) / (b) 최소 (boolean 마커만)
- **belle: (a) additive.** → D-37. 계약 3파일(analysis.ts + models.py + contract.md) 동시 갱신.

### Area 3 — 기존 캡 적용 순서 / 치명 트랙 바닥
- Q: 치명 record에 −20 관절캡 적용? Options: (a) 미적용(우회) / (b) 적용
- **belle 수정:** "0까진 좀 그렇고 2~30 정도면 어때? 완전 다른 영상은 어차피 분석조차 안 되니까" → SPEC의 "critical→0"을 **절대 바닥 25**로 대체. 확정값 = 25.
- → D-36. 치명은 −40 집계캡 + −20 관절캡 둘 다 우회, 절대 바닥 25. 3단 구조(정은지 95~100 / 실행 60~95 / 치명 25~60).

## Mid-discussion discovery (코드 실측 — 가정 정정)

Area 1 잠그기 전 `deduction_engine`/`ipsf_criteria` 확인 → **split 0-fail(160°)이 실제로는 dormant**:
- `split_fail_threshold_deg` 키를 보유한 criterion 0개 (주석: per-move expects_split flag 도입 시 후속).
- split_angle은 reference_relative 분기 → 엔진의 0-fail 체크(ipsf_absolute 분기) 미도달 (2중 dormant).
- ∴ D-35 "기존 0-fail 요소" = 지금 비어 있음 → 치명 트랙이 어느 fixture도 트리거 안 함.

belle 반응: "IPSF를 그래도 활용해야 하는 것 아닌가? 잘 모르겠" (요소-미인정 메시지가 값지다는 직관, 불확실).

**6 fixture 점검으로 데이터 기반 해소** (baseline breakdowns):
- 6동작 = power-spin, peter-pan, elbow-twist-sister, pdshape, kip-up, climb(fixture 미보유).
- fault 영상 전부 실행결함(관절 편차). 깨끗한 "요소 미수행" 케이스 0.
- 유일한 split_angle 발동 = kip-up(dev 30, 스플릿 동작 아님) = 알려진 측정 아티팩트([[split-measurement-doesnt-discriminate-kipup]], Phase24/25 해결).
- 정은지(correct) 6동작 전부 100 (INV-1 유지 확인).
- ∴ 지금 split 0-fail 배선 = kip-up FP 재유발 위험 + 검증 fixture 부재.

**belle 확정: 치명 트랙 구조만 넣고 dormant + split 0-fail 배선은 문서화 후속.** → D-35 개정, deferred에 후속 경로 기록.

## Decisions locked

D-33 (발견=채점 결함) / D-34 (2트랙 상한, final=max(25,100−min(40,Σ실행)−Σ치명)) / D-35 (치명=기존 0-fail만, 현재 dormant) / D-36 (치명 캡 우회 + 바닥 25, 3단) / D-37 (breakdown additive + 계약 3파일) / D-38 (6 fixture + INV-1~8, dormant 트랙은 합성 단위테스트, baseline은 substrate 이전값).

SPEC.md revised: critical floor 0 → 25, INV-3 dormant/unit-test, INV-8 absolute floor 25, dormant boundary + split-0-fail deferral.

## Deferred

- split 0-fail(요소 미인정) 배선 — per-move expects_split flag + 깨끗한 fixture 준비 시 활성화(D-35). belle IPSF 요소-미인정 직관의 실현 경로.

## belle touchpoints this session

belle 도메인 결정 4건(실행 바닥 60 / 치명 우회 / 치명 바닥 25 / dormant 확정) + 구현 선택 2건(track 판별·breakdown 형상). 채점은 신뢰 직결이라 belle 이 spec+discuss 양쪽에 깊이 관여(D-01 2회 원칙의 예외 — 표현 트랙이 아니라 정확성 뿌리).
