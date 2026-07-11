# 22-BAKEOFF-RESULT — 분석 엔진 백본 3파전 판정

> **판정: PROVISIONAL — 우승 Qwen/Qwen3-VL-8B-Instruct** (belle 확정 도장 전).
> 선정 규칙 = belle 사전 위임(2026-07-11): 4축 종합 우승자, 성능만, 동률 시 시계열 축 우선.
> belle 구두 확인 2026-07-12 아침("응 이해됬어" — 축별 분업 질의 응답 후). 공식 도장은 이 문서 승인으로 갈음.

## 계측 이력

- run5 (2026-07-11 07~12 UTC, 리포트 7개) = **폐기**. 하네스 `max_tokens=2048` 고정이
  전 프레임 corrected_coords JSON을 ~3.6K자에서 중간 절단 → 3모델 전부 grounding null,
  parse ~0.36, coaching judge 기아(파싱 성공분 = 내용 없는 껍데기 리포트뿐).
  모델 무능이 아니라 계측 결함. 원본은 Pod `/workspace/eval_out/phase22_run5_truncated/` 격리.
- fix = 6e91a13 (max_tokens 미지정 → vLLM 잔여 컨텍스트 자동 상한, timeout 900→1800).
- run6 (2026-07-11 12:04 ~ 22:5x UTC) = 본 판정의 근거. 러너 backend/training/run_bakeoff_pod.sh,
  하네스 backend/evals/phase22/run_bakeoff.py, SERIAL(모델당 run1 judge 포함 + run2/3 cold re-run).
  리포트 9개 + determinism_summary.json = Pod `/workspace/eval_out/phase22/` (로컬 백업 확보).

## 4축 표 (run1, zero+few 종합)

| 축 | Qwen3-VL-8B | InternVL3.5-8B | Cosmos-Reason2-8B | 승자 |
|---|---|---|---|---|
| A. grounding L2 (합성 16항목, 낮을수록 좋음) | 0.0345 | **0.0340** | 0.0351 | InternVL (격차 0.0005 = 미미) |
| B. temporal (trap 6, CircularEval) | **0.667** | 0.000 (전패) | **0.667** | Qwen·Cosmos 공동 |
| C. JSON parse / CER | 0.707 / 0.293 | 0.886 / 0.114 | 0.690 / 0.310 | InternVL (생존자 편향 — 아래) |
| D. coaching judge (1~5, gemini-3.5-flash 블라인드) | **2.0** (n=4) | 1.22 (n=23) | 1.0 (n=3) | Qwen |
| 실행 불가 에러 | **0** | 8 (32K 초과 400) | **0** | — |
| 결정성 (run1~3 raw_sha 일치) | **64/64 완벽** | 48/50 | 63/64 | Qwen |

### 모드별 분해 (판정 뉘앙스)

| | Qwen zero | Qwen few | InternVL zero | InternVL few | Cosmos zero | Cosmos few |
|---|---|---|---|---|---|---|
| parse | **1.000** | 0.414 | 0.957 | 0.810 | **1.000** | 0.379 |
| grounding L2 | 0.0348 | 0.0342 | 0.0339 | 0.0340 | 0.0343 | 0.0359 |
| judge | — (coaching 공백) | 2.0 | 1.21 | 1.22 | — | 1.0 |

- 서빙은 프롬프트 모드를 우리가 통제한다 — 실전 관련성이 높은 zero-shot에서 **Qwen parse 100% (29/29)**.
- Qwen·Cosmos의 few-shot 붕괴 = 예시를 따라 출력이 길어져 32K 컨텍스트 끝에서 절단되는 패턴.
  SFT 설계 시사점: 학습 타겟 길이/프레임 예산 관리 필요 (22-07에서 max_length 32768 + packing).

## 판정 근거 (규칙 적용)

축 승수: InternVL 2 (A, C) vs Qwen 2 (B, D) 동률 → **시계열 축 우선 규칙 → Qwen**.

정성 근거가 동률 해소를 강하게 지지:
1. **InternVL temporal 전패 = 위치 편향 shortcut.** 6개 trap 전부에서 선택지 순서를 바꾸면
   답이 따라 바뀜(항상 1번 선택, preds=[is_trap, forward]). 좌표의 물리적 연속성을 보지 않는다는
   직접 증거 — 모션 분석 도메인에서 자격 문제.
2. **InternVL 실영상 8/21 처리 불가** (입력 32,824~33,615 tok > 32,768 한계). C축 1위는 살아남은
   항목만의 성적(생존자 편향). 같은 항목을 Qwen·Cosmos는 에러 0으로 처리(토크나이저/비주얼 패킹 효율 차).
3. A축 격차 0.0005는 SFT 한 번에 지워지는 노이즈 수준. B·D축 격차는 체질.
4. Qwen만 3런 결정성 완벽(temp0 greedy 64항목 raw_sha 전일치) — eval 재현성 자산.

Cosmos-Reason2-8B: B 공동 1위 외 전 축 최하위권. reasoning post-train이 이 태스크 포맷에서
이점을 못 보임. 탈락. (v2 생성 엔진 후보 Cosmos3-Nano와는 별개 트랙 — 유효 유지.)

## 한계 (판정에 영향 없음, 기록)

- hard_negative 2항목은 3모델 공통 skip (manifest s3_key null, relocate pending) — 트랙 미계측.
- svg_wellformed 3모델 전부 0.0 = 베이스 모델에서 예상된 결과 (선정 축 아님, F2 관측치).
  정식 svg 게이트는 SFT 후 22-07 assert_gates 담당.
- judge n이 작음 (Qwen 4 / Cosmos 3) — 베이스 모델이 coaching을 거의 비워서 채점 표본 자체가 적음.
  SFT 후 게이트에서 재계측된다.
- json_exact_match == parse_rate 는 guided JSON(키 집합 강제)의 필연 — 버그 아님.

## 다음

- 22-07 SFT: `Qwen/Qwen3-VL-8B-Instruct` + QLoRA(rank 64, 4-bit, all-linear), 학습셋
  s3://sunity-motion-pilot-videos/training/phase22/jsonl/ (train 101 / val 2,
  validation_owner=explicit_val_jsonl). 비용 알림 = 2026-07-11 채팅 갈음(belle 사전 승인).
- 뒤집기 비용 = SFT 재실행(GPU 시간)만. 백본 교체 시 이 문서 갱신 + PROVISIONAL 해제 필수.
