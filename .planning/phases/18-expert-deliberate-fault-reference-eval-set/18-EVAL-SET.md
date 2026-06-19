# Phase 18 — Expert deliberate-fault reference eval set (정식화)

**상태(2026-06-19):** eval baseline + fault 라벨 fixture **박제 완료(pod-free)**. 실 Pod 재실행
대조(채점기 live 출력 vs baseline)는 **Pod 재개 후**로 이연. self-check 하니스 PASS.

**ROADMAP:** Phase 18 — "정은지 '일부러-실수' reference 영상을 영구 regression/eval 세트로". Phase 15 의존.

---

## 무엇을 박제했나 (이번 세션, pod 불필요)

Phase 15 의 수동 실증을 **영구 regression/eval fixture** 로 승격. `backend/evals/phase18/`:

| 산출물 | 경로 | 내용 |
|---|---|---|
| 페어 매니페스트 | `backend/evals/phase18/dataset/pairs.yaml` | 6 페어 — S3 키 + reference id + **비전-파생 fault 라벨**(D-05) + expected verdict |
| baseline 스냅샷 | `backend/evals/phase18/baseline/eval18_serial_baseline.json` | 확정 serial 점수(채점기 출력 — regression 기준) |
| self-check 하니스 | `backend/evals/phase18/assert_baseline.py` | 스냅샷 ↔ 게이트 의미론 정합 검사(pod-free, **PASS**) |
| README | `backend/evals/phase18/README.md` | 목적·실행·게이트·객관성·일반화 경계 |
| 러너(재사용) | `backend/scripts/sweep_phase15.py` | 실 Pod 재실행 하니스(중복 0). `--pair-sequential` |

데이터는 전부 **재사용**(재업로드/재처리 0): S3 영상 + id = `backend/scripts/phase15_keys.json`(15-01),
fault 라벨 = Phase 19 D-05 vision grounding spike, baseline 점수 = 2026-06-18 belle 실증 serial run.

---

## 확정 EVAL baseline (Mode 1, vs 정은지 reference, Phase 19 감점식, serial)

| 동작 | fault | success | margin | 판정 |
|------|------|---------|--------|------|
| power-spin | 72 | 100 | 28 | ✅ 변별 |
| peter-pan | 79 | 100 | 21 | ✅ 변별 |
| elbow-twist-sister | 59 | 100 | 41 | ✅ 변별 |
| pdshape | 58 | 100 | 42 | ✅ 변별 |
| kip-up | 100 | 100 | 0 | ✗ 위양성 (known) |
| climb | not_pole | not_pole | — | ✗ 게이트차단 (known) |

- **4/4 변별**(climb/kip-up 제외) — angle 채널이 28~42° 결함 검출. 재설계 작동 중.
- **결정론 확정**: 같은 영상 재실행 → byte-identical (pdshape-correct 100×3, power-spin-fault 72×2).
- **kip-up 위양성**: 비-각도형 실패를 DTW 가 흡수 → angle 채널 맹점. **Phase 20(v2 Gemini 시각 거부권)** 해소 대상.
- **climb 게이트차단**: correct-climb 조차 ref-climb 유사도 <25 → not_pole. **ref-climb reference 품질/촬영각 문제**(코드 fix 아님). reference 재검토 필요.

---

## 게이트 의미론 (eval PASS 조건)

1. **변별** — 검출 가능 4 페어는 `fault < success` (margin > 0).
2. **결정론** — 같은 입력 → 같은 점수. 동시 실행 금지(순차만 — [[pipeline-not-concurrency-safe-eval-serial]]).
3. **known-issue 명시 추적(silent 금지)** — kip-up 위양성·climb 게이트는 `expected` 에 박제.
   - 새 run 에서 이 둘이 **변별로 바뀌면 개선**(fixture 갱신).
   - 변별 페어가 **위양성으로 퇴행하면 FAIL**.

`assert_baseline.py` 가 위 1·3 을 스냅샷에 대해 pod 없이 검증(현재 PASS). 2(결정론)는
Pod 재실행 시 동일 점수 재현으로 확정.

---

## 객관성 하드가드 (D-06 / [[analysis-objectivity-no-human-scores]])

- fault 라벨 = **영상-파생 입력 라벨**(어떤 결함 시연인지) — OK.
- baseline 점수 = **채점기 자신의 결정론적 출력 스냅샷**(regression 기준) — 사람 라벨 아님.
- **금지:** 사람이 매긴 "이 영상 N점" ground-truth 점수 라벨. 임계값 수치 라벨링은 OK.
- `approx_deviation_deg` = Gemini 시각 추정(±). 앵커일 뿐 임계값 직접 대입 금지.

---

## Pod 재개 후 남은 일 (정량 대조)

1. Pod 기동 + Lambda URL 동기화(HANDOFF 절차 + `pod_bootstrap_full.sh`).
2. `sweep_phase15.py --mode mode1 --pair-sequential` 로 6 페어 **순차** 재실행.
3. live 출력 ↔ `baseline/eval18_serial_baseline.json` 대조 — drift 0 면 baseline 재확정,
   변동 시 원인 박제(채점기 변경/모델 변동).

---

## Deferred (별도 셋 필요)

- **sensitivity 게이트** — 6 페어 전부 정은지 단일 선수 + fault(elite-low). curve-fit 타깃 아님
  ([[scoring-redesign-must-generalize-no-overfit]]). 미보유 동작 + above-cutoff(고득점이어야 정상)
  케이스로 일반화/sensitivity 검증 ([[sensitivity-gate-not-just-elite-low]]) — Phase 20 또는 후속.
- **combo** — fault 영상 없음(correct 만) → 페어 제외.

---

## 후속 phase 연결

- **Phase 20 (v2 비전 점수):** 이 baseline 표가 v2 known-answer gate. kip-up 위양성 + climb +
  상단 변별을 belle 스펙(같은 정은지 95~100 / 잘못된 동작 ≤50 / Gemini 시각 점수)로 해소.
  v2 작업 후 이 fixture 로 회귀 게이트.
