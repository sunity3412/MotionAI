# 33-A4-FIX-NOTE — recognizer 캐시 히트 경로 hold_window 소실 수리

- 근거 문서: `33-A4-PHASE-EVIDENCE.md` §5 (끊긴 지점 1)
- 작업 성격: A/B 결정에 따른 A 트랙 삽입 quick fix (넘버드 플랜 아님 — SUMMARY 없음)
- 커밋: `b5cce33` (fix) + `69b03cb` (test), 브랜치 `worktree-agent-ac067349411b72f27`

---

## 1. 결함 요약

yaml `hold_moment:` 스코프(감점을 "완성 국면에서 잰다")를 시간축에 구현하는 유일한
장치는 `TechniqueProfile.hold_window`다. 신선 경로(`_build_profile`)는 Gemini
KeyMoments[hold] timestamp 로 이 창을 계산하지만, 캐시 히트 경로
(`gemini_technique_recognizer.py::_profile_from_cache`)는 `hold_window=` 를
복원하지 않았다(필드 자체 부재). 결과:

- 캐시 히트 시 `dimensions._select_window` 가 **국면 무관 분산 최소 자동 창**으로 폴백.
- 같은 영상이라도 캐시 히트/미스에 따라 감점 측정 창이 달라짐 (경로 비결정성).
- 33-A4 실증 doc(power-spin 51점)은 캐시 히트 + 자동 창이 **우연히** 옳은 국면에
  앉아 국면 정합이 보장 없이 성립했었다.

## 2. 수정 diff 요지

파일: `backend/shared/python/sunity_shared/analysis/gemini_technique_recognizer.py`

1. **`_hold_window_from_moments(moments)` 공통 함수 신설** — hold moment 필터 →
   timestamp 정렬 → 2개 이상 = 첫/마지막, 1개 = ±2초 창, 0개 = None, fps 9.0.
   종전 `_build_profile` 인라인 로직과 의미 동일 (순수 추출, 산식 변경 0).
2. **`_build_profile` 이 공통 함수 호출** — 인라인 창 계산 제거.
3. **`_profile_from_cache` 가 동일 함수로 `hold_window=` 복원** — `cached["moments"]`
   raw dict 에서 직접 산출. KeyMoment dataclass 복원(Layer 2) 실패와 독립적으로
   국면 게이트가 살아남도록 결합 차단.
4. `_moment_field` accessor — KeyMoment 객체(신선)와 cache dict(캐시)를 같은 코드로
   읽음. 비수치 timestamp 는 warning + None(자동 창 폴백) graceful.

수리 원칙 준수: 특정 동작(motion) 이름 분기 0 — 전 동작 공통 구조 수정.
신선/캐시 profile 구성의 창 계산이 "분기 0, 코드 1벌"로 합쳐짐.

## 3. 로컬 테스트 결과 (2026-07-29)

- 신규 회귀 테스트 4건 (`backend/tests/test_gemini_technique_recognizer.py::TestCacheHoldWindowRestore`):
  - 캐시 히트 시 hold_window 복원 (단일 hold 7.0s → 창 (45, 81))
  - 신선 경로 store payload round-trip → 캐시 profile 과 hold_window 동일 (핵심 불변식)
  - hold moment 부재 시 None 유지 (가짜 창 생성 금지)
  - KeyMoment 복원 실패(Layer 2 비활성) 시에도 hold_window 는 복원 (독립성)
- **RED 실증**: 수정 전(HEAD) 소스로 실행 시 4건 중 3건 실패(None 유지 테스트만 통과)
  — 테스트가 실제 결함을 잡음을 확인 후 수정 적용 → 4건 전부 GREEN.
- backend 전체 (`PYTHONPATH=backend/tests python3 -m pytest backend/tests -q`):
  **3688 passed, 58 failed, 27 skipped.** 실패 58건은 수정 전/후 **집합 diff 0**
  (전부 사전 존재, 로컬 환경 의존 — 예: `GEMINI_MODEL` env 미설정으로
  `DEFAULT_GEMINI_MODEL` 상수 불일치, yaml/judging_data 로컬 경로 의존,
  vision scorer 캐시 결정성 테스트의 env 의존 등). 본 수정이 새로 깨뜨린 테스트 0건.

## 4. 행동 변화 예고 (Pod 검증 세션 필독)

이 수정으로 캐시 히트 경로가 신선 경로와 **동일하게 Gemini hold 창을 존중**한다.
33-A4 실증이 보인 대로 Gemini hold timestamp 자체가 부정확한 영상
(power-spin 실증 doc: hold=2.1s, 실제 완성 국면은 6.3~8.2s — 4초 이상 오차)에서는:

- 종전 캐시 히트: 자동 분산최소 창(우연히 6.31~8.18s) → left_knee 평균 141°, r00 −20
- 수정 후 캐시 히트: Gemini hold 창 (2.1±2)s = frames [1,37) → right_knee 평균 약 78°
  (33-A4 §5-1 반증 계산) — **tuck 한복판을 "무릎 안 폈음"으로 재는 값**

즉 본 수정은 끊긴 지점 1(경로 비결정성)만 고친다. 끊긴 지점 2(Gemini hold
timestamp 불신뢰)와 지점 3(자동 창의 국면 무관성)은 **별도 플랜 소관**이며, 이
수정으로 지점 2의 영향이 캐시 경로에도 일관되게 드러난다. 점수 이동이 관찰되면
그것은 회귀가 아니라 결함 노출이다 — 판정은 fixture 기대치 기준으로 하되, 지점 2
수리 필요성의 증거로 기록할 것.

## 5. Pod 재검증 대기 체크리스트

로컬은 순수 함수 단위 검증까지. 실분석 검증은 Pod(RTX 4090, 8hrks3hrxmtgw6)에서
별도 세션으로 수행한다. **상태: Pod 재검증 대기.**

- [ ] 6 fixture 전체 (phase25 success+fault 페어, 산식 `final=max(25,100−min(40,Σ실행)−Σ치명)` 기대치 기준):
  - [ ] ref-kip-up
  - [ ] ref-peter-pan
  - [ ] ref-power-spin (33-A4 실증 동작 — §4 행동 변화 관찰 포함)
  - [ ] ref-pdshape (2-run stability 포함, R-6)
  - [ ] ref-elbow-twist-sister
  - [ ] ref-climb (comparison-gate 전용, 점수 없음 — 게이트 오동작 여부만)
- [ ] 비-fixture 4종 대체 검증 (`verify_self_comparison.py`):
  - [ ] ref-foxtop
  - [ ] ref-foxtop-split
  - [ ] ref-invert
  - [ ] ref-sideway-spin
- [ ] 캐시 경로 동일성 실증: 동일 영상 2회 분석(1회차 캐시 미스 → 2회차 히트)에서
  hold_window 와 r00 계열 measuredValue 가 두 회차 동일한지 확인
- [ ] 점수 이동 발생 시: fixture 기대치 위반 여부 판정 + 끊긴 지점 2(Gemini hold
  timestamp) 수리 플랜 입력으로 기록
