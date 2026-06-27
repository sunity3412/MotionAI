# P1 step 5 — pod 재-sweep 검증 (2026-06-27)

Pod wyu4kk159fv3k4 (RTX 4090, Network Volume). HEAD 245f378. `run_sweep_24.sh`(RECOGNIZER_BACKEND=gemini, RTMW cuda) → `evals/phase24/run_sweep.py` 6 페어 serial. 산출: phase24_breakdowns.json + sweep_report.json (repo 커밋).

## 검증 질문 (audit)
"정타 오염 사라지고 kip-up 잡히는지." → **부분 성공 + 정밀 진단.**

## 결과 (verdict 표)
| pair | fault | correct | 판정 |
|---|---|---|---|
| power-spin | 60 | **100** | ✅ 메커니즘 작동 — fault leg_extension(무릎 141°→-22.7), correct **clean(records 0)** |
| peter-pan | 37 | 47 | ⚠️ correct에 leg_extension(무릎 115.8°, raw 64°) = false fault |
| elbow-twist-sister | 36 | 62 | ⚠️ correct leg_extension raw 51.7° = false fault |
| pdshape | 0 | 24 | ⚠️ correct leg_extension raw 83.8° = false fault(비대칭 anchor 다리) |
| kip-up | 100 | 96 | ❌ INVERTED, records 0 — 미해결 |
| climb | None | None | not_pole 게이트(angle<25, 기존 known) |

## ✅ P1 핵심 메커니즘 PROVEN (power-spin)
- 객관 `leg_extension`(ipsf_absolute, 180°) 정상 발화: fault 무릎 141.09° → dev 18.9° → **-22.7 pts**(굽은 무릎 검출). ipsfAnchor="19-IPSF §A 트랙2".
- **de-contamination 작동**: power-spin **correct = records 0, final 100**. 정은지와 체형/각도 차이 있어도 곧은 다리면 감점 0 — reference_relative 오염 제거 확인. (step1 clean-residual 게이트도 power-spin은 통과 = clean.)
- 즉 "곧은 다리 correct form" 동작에서 오염 제거 + 결함 검출이 **둘 다 실증됨.**

## ⚠️ 과잉 EXTEND (peter-pan / elbow-twist-sister / pdshape)
- 세 동작의 **correct(정타) form이 무릎을 굽힘**(measured 96~116°). 양 무릎 EXTEND가 정타에 false fault 생성.
- 증거: peter-pan correct 무릎 115.8°가 fault 무릎 121.6°보다 **더 굽음** → 무릎 신전이 이 동작들의 fault 축이 아님. fault는 다른 관절(shoulder/elbow, reference_relative가 이미 처리).
- step1 **clean-residual 게이트가 정확히 FAIL** 발화(raw 52~84° > 20° tol) — false-close 차단 작동.
- 교란: peter-pan/kip-up에 `torso_px ratio extreme`(촬영 거리 불일치 ratio 10~35) 경고 — 절대 무릎각 측정 왜곡 가능.
- **belle 도메인 확인 필요**: 이 동작들의 correct form이 실제로 무릎 굽힘인가(→ knee EXTEND 제거) vs 촬영 왜곡인가(→ 깨끗한 reference 재촬영). 데이터는 "굽힘"을 강하게 시사(64~84° = 노이즈 아님). 권고: power-spin만 knee EXTEND 유지, 나머지 3 제거(curve-fit 아님 — 굽힘 form에 신전기준 강요 금지 정합).

## ❌ kip-up 미해결 (100, inverted) — 3중 차단 (EXTEND로 해결 불가)
sweep_report 진단:
1. **인식 실패**: kip-up fault `activatedCriteria=[]` → recognizer가 ref-kip-up으로 분류 못 함 → EXTEND 프로파일 미로드(step4 등록이 닿지 못함). power-spin은 leg_extension activated(인식됨)와 대조.
2. **non-angle-shaped**: records 0 — hold-window 평균 무릎각이 reference와 일치(굽은 무릎 fault가 순간/공중이라 윈도우에서 씻겨나감). reference_relative도 미발화.
3. **vision 경로 차단**: visionVeto `status='not_applicable'` — 비-각도 fault를 잡을 유일한 경로(vision)가 alignment 게이트에 막힘([[session-handoff-2026-06-26]] B / [[phase23-pod-eval-gate-fail-2026-06-24]]).
→ kip-up은 (a) recognizer 분류 + (b) vision-veto alignment 게이트(24-B 트랙) 필요. **EXTEND 데이터로 해결 불가 — audit 질문에 명확히 답함.**

## 게이트 최종 (step1↔step5 루프 종결)
`assert_gates.py` EXIT=1, 정밀 localize: clean-residual 3건(peter-pan/elbow-twist/pdshape correct) + generalization 4건(+kip-up false-negative). power-spin·sensitivity·traceability 등은 통과. **게이트가 false-close 막고 남은 결함을 동작·관절 단위로 지목** = step1 설계 목적 달성.

## ★ 최종 결과 (belle 결정 적용 + 재-sweep 검증, 2026-06-27)
belle 결정: peter-pan/elbow-twist/pdshape knee EXTEND 제거(굽힘 form) + 지금 고치고 재-sweep.

**적용**:
1. 3개 yaml 객관 무릎 criteria 제거(empty hold). power-spin/kip-up EXTEND 유지. 테스트 갱신(85 passed).
2. **cache invalidation 버그 발견·수정**: technique_cache `_YAML_FILENAMES`가 원본 5개만 하드코딩 → 신규 동작 yaml 변경이 yaml_version에 반영 안 돼 **stale profile cache hit**(1차 재-sweep에서 EXTEND 잔존). → 전 criteria yaml glob으로 변경(어떤 yaml 변경이든 자동 invalidation). 22 cache tests pass.

**재-sweep verdict (cache fix 후)**:
| pair | fault | correct | 판정 |
|---|---|---|---|
| power-spin | 47 | 91 | discriminate (margin 44), leg_extension 유지 |
| peter-pan | 79 | **100 clean** | ✅ false fault 제거 |
| elbow-twist-sister | 61 | **100 clean** | ✅ |
| pdshape | 60 | **100 clean** | ✅ |
| kip-up | 97 | 96 | ❌ INVERTED — 미해결(별 트랙) |
| climb | None | None | not_pole 게이트(known) |

**게이트 최종**: `assert_gates` 7 failures → **1 failure**. clean-residual 전부 GREEN(3 false fault 제거). generalization은 **kip-up만** RED(non-angle-shaped). 즉 **P1 핵심(정타 오염 제거) 완료·게이트 검증됨.** 4개 각도형 페어 전부 discriminate(margin 21~44).

**남은 1건 = kip-up (별 트랙, P1 메커니즘 실패 아님)**:
- recognizer가 ref-kip-up 분류 실패(activatedCriteria=[], 무릎 EXTEND 미로드) — Gemini alias/분류 보강 필요.
- 굽은 무릎 fault가 hold-window에서 씻겨나감(non-angle-shaped) + vision-veto alignment 게이트 차단(24-B).
- → recognizer 분류 + vision/alignment(24-B) 트랙. EXTEND 데이터로 불가.

**부수 관찰**: Cerebras 코칭 JSON 파싱 실패(coach_writer.py:229) — 수치 폴백으로 graceful, 분석/점수 무영향(별 minor 항목). torso_px ratio extreme(촬영 거리 불일치) 경고는 peter-pan/kip-up reference 영상 framing 이슈(측정 안정성 후속).

## ★ kip-up 정밀 진단 (2026-06-27, probe_kipup_recognizer.py) — 이전 가설 정정
재부팅 pod에서 kip-up recognizer/각도 직접 probe. **이전 "recognizer 분류 실패" 가설은 틀림:**
- kip-up은 **정상 분류됨**: profile.category=recognized, motion_id=ref-kip-up, joint_expectations에
  양 무릎 'extend' 로드됨(step4 yaml 정상 작동). activatedCriteria=[]는 분류 실패가 아니라
  **감점이 안 나서**(곧은 측정).
- **무릎각 신호가 INVERTED**: fault min 무릎 161°/165° vs **correct min 149°/149°(정타가 더 굽음)**.
  hold-window 평균은 양쪽 ~174~176°(곧은 순간 포착) → leg_extension 0 → 100/100.
- 어떤 window(hold/worst-pose)로도 fault>correct 변별 불가 — **무릎각으로 kip-up 채점 불가 확정**.
- 원인 후보: "공중 양 무릎 굽음" fault가 순간/공중이라 안정 윈도우서 씻겨남 + torso_px ratio
  extreme(촬영거리 불일치) 측정 왜곡 + 실제 fault가 무릎각이 아닐 가능성.
- **조치**: kip-up knee EXTEND 제거(다른 3동작과 동일 + inversion 증거). ref-kip-up.yaml empty.
  45 tests pass. (committed breakdowns는 제거 전 sweep 기준이나 kip-up verdict=generalization red는
  불변 — 재-sweep 불요.)

**kip-up 실결함 검출 = 별 트랙, 2가지 미해결 필요**:
1. **무엇이 kip-up의 진짜 fault인가** = belle 도메인 (무릎각이 아님이 데이터로 증명됨 — 타이밍/제어/
   kip 완성도/높이? belle가 정의해야 객관 채점 설계 가능).
2. **측정 신뢰** = reference 영상 framing(촬영거리 불일치) 정리 또는 vision/temporal 트랙(24-B).

## 다음
1. ✅ P1 정타 오염 제거 = 완료. power-spin이 유일하게 검증된 straight-knee 객관 채점 동작.
2. ✅ kip-up 진단 완료 — 무릎각 채점 불가 확정(inversion). EXTEND 제거.
3. **kip-up 실결함** = belle가 "진짜 fault" 정의 → vision/temporal(24-B) 트랙. EXTEND로 불가.
4. ✅ P2 Mode3 근거공개 = 이미 구현됨(Phase19/20-03, 34 tests). audit P2 stale. [[p2-mode3-disclosure-already-done]]
5. (minor) Cerebras coach JSON 파싱 견고화, reference 영상 framing.
