# Phase 18 — Expert deliberate-fault reference eval set

정은지 선수가 같은 동작을 **일부러 틀리게(fault)** / **제대로(correct)** 시연한 6 페어를
영구 regression/eval fixture 로 박제한다. Phase 15 의 수동 실증을 정식 자동 게이트로 승격.

## 왜 별도 셋인가 (Phase 15 와의 차이)

- Phase 15 = 이 영상들을 **수동 실행 + 1회성 assert** (실증 검증).
- Phase 18 = 같은 영상에 **fault 라벨**(어디를 틀렸나)을 영구히 달고, 채점기가 그 결함을
  **독립적으로** 잡아 fault < success 로 변별하는지 **반복 가능한 게이트**로 만든다.
  점수 재설계(Phase 19/20)가 회귀하지 않았는지 매번 같은 셋으로 확인한다.

## 구성

| 파일 | 내용 |
|---|---|
| `dataset/pairs.yaml` | 6 페어 매니페스트 — S3 키 + reference id + **비전-파생 fault 라벨**(D-05) + expected verdict |
| `baseline/eval18_serial_baseline.json` | 확정 serial 점수 스냅샷(채점기 출력 — regression drift 기준) |
| `assert_baseline.py` | 스냅샷이 게이트 의미론을 만족하는지 검사(pod-free — 스냅샷 검증) |
| (러너) `backend/scripts/sweep_phase15.py` | 실제 Pod 재실행 하니스(재사용 — 중복 0). `--pair-sequential` |

## 데이터 출처 (재사용 — 재업로드/재처리 0)

- S3 영상 + motionId + referenceMotionId: `backend/scripts/phase15_keys.json` (15-01 산출).
- fault 라벨: Phase 19 D-05 Gemini Vision grounding spike
  (`.planning/phases/19-vision-hybrid/19-D05-VISION-GROUNDING-SPIKE.md`).
- baseline 점수: 2026-06-18 belle 실증 serial run.

## 게이트 의미론 (PASS 조건)

1. **변별(discriminate)** — angle/line 검출 가능 4 페어(power-spin/peter-pan/elbow-twist-sister/pdshape)는
   `fault_overall < success_overall` (margin > 0). 현재 margin 28/21/41/42.
2. **결정론** — 같은 영상 재실행 → 같은 점수(byte-identical). 동시 실행 금지(순차만).
3. **known-issue 명시 추적(silent 금지)** — kip-up 위양성(100/100), climb not_pole 게이트는
   `expected` 에 박제. 새 run 에서 이 둘이 **변별로 바뀌면 개선**, 변별 페어가 위양성으로
   **퇴행하면 FAIL**. 둘 다 silent 통과 불가.

## 실행 (Pod 재개 후)

```bash
# 1) Pod 기동 + Lambda URL 동기화 (HANDOFF 절차)
# 2) 순차 sweep (동시 금지 — pipeline-not-concurrency-safe-eval-serial)
python backend/scripts/sweep_phase15.py --mode mode1 --pair-sequential ...
# 3) 결과를 baseline 스냅샷과 대조
python backend/evals/phase18/assert_baseline.py
```

`assert_baseline.py` 는 **pod 없이도** 현재 박제된 스냅샷이 게이트 의미론을 만족하는지
검사한다(스냅샷 self-consistency). 실 Pod 재실행 대조는 Pod 재개 후.

## 객관성 하드가드 (D-06 / [[analysis-objectivity-no-human-scores]])

- fault 라벨 = **영상-파생 입력 라벨**(어떤 결함을 시연하는지) — OK.
- baseline 점수 = **채점기 자신의 결정론적 출력 스냅샷**(regression 기준) — 라벨 아님.
- **금지:** 사람이 매긴 "이 영상 N점" ground-truth 점수 라벨. 임계값 수치 라벨링은 OK.
- `approx_deviation_deg` = Gemini 시각 추정(±). 앵커일 뿐 임계값 직접 대입 금지.

## 일반화 경계 (Deferred)

6 페어 전부 정은지 단일 선수 + fault(elite-low). curve-fit 타깃 아님
([[scoring-redesign-must-generalize-no-overfit]]). **sensitivity 검증**(미보유 동작 +
above-cutoff 고득점이어야 정상)은 별도 셋 필요 ([[sensitivity-gate-not-just-elite-low]]) — Deferred.
