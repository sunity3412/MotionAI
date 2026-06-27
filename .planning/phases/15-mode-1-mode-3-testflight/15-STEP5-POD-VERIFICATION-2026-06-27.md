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

## 다음 (belle 결정 + 후속)
1. **peter-pan/elbow-twist/pdshape knee EXTEND 제거** 여부 = belle 도메인 확인(굽힘 form 맞는지). 확인 시 yaml 수정 → 재-sweep → clean-residual GREEN 기대.
2. **kip-up** = 별 트랙: recognizer 분류 보강(alias/Gemini) + vision-veto alignment 게이트(24-B). EXTEND와 독립.
3. power-spin = 유지(검증 완료).
4. pod 비용: 재-sweep 필요 → belle가 (1) 결정 후 pod 유지 시 즉시 재검증, 아니면 Stop.
