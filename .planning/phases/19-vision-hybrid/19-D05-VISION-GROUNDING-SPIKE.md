# Phase 19 D-05 — Vision Grounding Spike 결과 (2026-06-18)

**무엇:** 보유 정은지 fault/correct 페어를 Gemini Vision(`gemini-3.1-pro-preview`)으로
직접 비교 → "어디를 틀렸나" known-answer 앵커 확보. Pod 불필요(Gemini 외부 API).

**경계 (절대):** 아래는 **sanity 앵커 / 일반화 검증용**. 임계값 curve-fit 타깃 아님.
점수 숫자 라벨 없음(객관성 게이트 — fault 위치/종류 + 기하 각도/갭 + 정성 심각도만).
[[scoring-redesign-must-generalize-no-overfit]] [[analysis-objectivity-no-human-scores]]

**스크립트:** `backend/research/spikes/spike_vision_grounding_pair.py`
**결과 JSON:** `backend/research/spikes/reports/spike_vision_grounding_*.json` (6 페어)
**실행:** fault/correct 페어 **6개 전부** (climb, kip-up, pdshape, elbow-twist-sister,
power-spin, peter-pan). combo는 fault 영상 없음(correct만) → 제외.
모두 **confidence: high**, 점수 숫자 출력 0건.

---

## 6 페어 종합 (지배 결함 = 라인/신전 붕괴)

| 동작 | 지배 결함(major) | ~편차 | 추가 결함 |
|---|---|---|---|
| climb | 굽은 등/척추 정렬(라인) | ~25° | 목 꺾임(mod ~30°), 골반 과밀착(mod ~15°), 팔꿈치 갭 ~20° |
| kip-up | 공중 무릎 굽음 | ~35° | 발끝 포인 풀림(mod ~45°), 스트래들 좁음(mod ~30°) |
| pdshape | 자유 다리 무릎 굽음 | ~35° | 발끝 풀림(mod ~20°), 스플릿 좁음(mod ~15°) |
| elbow-twist-sister | 스플릿 각도 부족 | ~40° | 발끝(mod ~20°), 등 아치 부족(minor ~15°), 위다리 무릎 갭 ~35° |
| power-spin | **무릎×2 + 스플릿 (major 3개)** | ~45/30/40° | — (지배 결함 다중) |
| peter-pan | 뻗은 다리 무릎 굽음 | ~25° | 발끝(mod ~30°), 어깨 으쓱(minor ~15°) |

**핵심 패턴:** 6/6 fault 영상 모두 **최소 1개 major 결함** 보유. 결함이 일관되게
**신전 부족(무릎 굽음·발끝 풀림) + 라인 붕괴(스플릿/등)** 에 집중 →
IPSF 실행(Execution)·신전(Extension) 감점에 직결. 채점기의 **angle / line 차원**이
지배해야 할 케이스. 비전 6/6 high confidence + IPSF 도메인 용어 정합.

---

## 앵커 1 — climb (클라임) · confidence: high

**지배 결함(primary_fault):** 척추 정렬 불량 / 굽은 등(hunched back) — 가슴을 펴지 못하고
등이 둥글게 말려 신체 라인·자세에서 심각한 실행 감점을 유발하는 단일 지배 결함.

| 심각도 | 부위 | FAULT 상태 | ~편차 |
|---|---|---|---|
| **major** | 척추/등 | 등이 말리고 가슴 닫힘, 코어 긴장 부족 | ~25° |
| moderate | 머리/목 | 턱이 가슴쪽으로 당겨져 시선·목 꺾임 | ~30° |
| moderate | 골반/상체 각도 | 골반이 폴에 과밀착, 상체 무너짐 | ~15° |

뻗기-갭: 자유 팔 팔꿈치 ~20°.

## 앵커 2 — kip-up (킵업) · confidence: high

**지배 결함:** 공중 스트래들/V자 시 양 무릎 불완전 신전(굽음) + 발끝 포인 풀림 →
다리 라인 붕괴.

| 심각도 | 부위 | FAULT 상태 | ~편차 |
|---|---|---|---|
| **major** | 무릎 | 공중 내내 양 무릎 굽음, 다리 라인 꺾임 | ~35° |
| moderate | 발목/발끝 | 발끝 포인 풀려 flexed | ~45° |
| moderate | 고관절(스트래들) | 다리 벌림 좁아 V자 불분명 | ~30° |

뻗기-갭: 무릎 ~35°, 발목 ~45°.

---

## Known-answer 해석 (채점기 재설계 검증)

1. **두 페어 모두 명백한 single major fault 존재** (등 말림 ~25° / 무릎 굽음 ~35°).
   비전이 high confidence로 "신체 라인 붕괴 → IPSF 실행 다중 감점"을 짚음.
   → Phase 15 실증의 **94점/89% "거의 다 왔어요"는 명백히 틀린 출력**임을 자동 확증.
   (현재 이중 단순평균이 major fault를 정상 관절에 희석 — deferred-items.md 근본원인 정합.)

2. **D-01 감점식의 known-answer 타깃(앵커, 정답 아닌 curve-fit):**
   - climb: 등 말림이 **단일 major fault로 점수를 지배**해야 함. line 차원이 크게 깎여야 정상.
   - kip-up: 무릎 굽음(~35°)이 angle 차원을 지배해야 함. 발끝/스트래들은 추가 moderate 감점.
   - 둘 다 "major fault 1개가 종합점수를 끌어내린다"는 D-01 설계의 직접 테스트 케이스.

3. **비전-추론 de-risk (D-02 v2 선행 신호):** Gemini가 RTMW 수치 없이도 fault 위치/종류를
   정확·일관되게 짚음(2/2 high confidence, 도메인 IPSF 용어 정합). 비전 거부권/교차검증이
   우리 도메인에서 작동할 가능성 ↑.

4. **Phase 18 eval 라벨:** fault 영상 **6건** 영상-파생 fault 라벨 생성
   (사람 점수 아님 — 객관성 OK). deliberate-fault eval set 병합 자산.

## 한계 / 주의

- 각도는 Gemini의 **시각 추정**(±상당) — 정밀 측정 아님. 앵커로만 사용, 임계값 직접 대입 금지.
- 보유 6 페어 전부 실행. 단 모두 **정은지 단일 선수 + fault 페어**(elite-low) →
  일반화/sensitivity 검증은 **미보유 동작 + above-cutoff(고득점이어야 정상)** 케이스 별도 필요
  ([[sensitivity-gate-not-just-elite-low]]). combo는 fault 영상 없어 제외.
- 현재 채점기의 *해당 영상 실제 출력*과의 정량 대조는 RTMW GPU 필요 → Pod 재개 후
  (belle 크레딧 충전 + 새 Pod). 본 앵커는 그때 자동 판정 기준으로 사용.

## 다음

- ✅ 6 페어 확장 실행 완료 (belle 결정).
- belle 검토: 앵커(6/6 major fault 지배, 라인/신전 붕괴)가 D-01 감점식 방향과 정합 확인.
- 이후 `/gsd-plan-phase 19` (v1 = D-01 감점식 + 확정 버그, 본 6 앵커로 known-answer 검증).
