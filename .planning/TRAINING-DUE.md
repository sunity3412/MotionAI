# 재학습 — 건수는 도달, **아직 돌리면 안 됨** (2026-10-02 갱신: 잔액·누수 재측정, v38 성적 찾음)

<!-- flywheel:counts --> 플라이휠 최신 판정 2026-09-28 10:07 — 수집 579 / 임계 400 · admit 336 / 임계 60 (건수만. 학습 가능 여부는 게이트 표)

플라이휠이 **건수 조건**을 자동 판정했다(2026-09-21). 그러나 2026-09-23 외부리뷰 판정으로
**건수만으로는 시작하지 않는다.** 아래 게이트가 다 켜져야 "학습 가능"이고, 그때
**belle 에게 즉시 알린다** (belle 2026-09-23: *"학습 가능할 때 알려줘야 해"*).

## 학습 가능 게이트 — 세션 시작 때 이 표를 채워서 belle 에게 보고할 것

| # | 조건 | 2026-10-02 상태 | 확인 방법 |
|---|---|---|---|
| 1 | 수집 건수 | ✅ **충족** 579 / 임계 400 · admit 336 / 60 (09-28 플라이휠, 다음 10-05 — 맨 위 마커 줄이 매주 갱신) | `backend/training/data/manifest.json` |
| 2 | **실패 원인이 실측으로 확정됐나** | 🔶 **부분** — kip-up 은 기준/감점 단계 확정: 저장된 감점 기록 = 어깨 편차 **20.62도** vs 허용오차 20.0도 → **−0.7점이 측정오차 구간(15.9~24.3도)에 걸려 억제**(quick-260923-smt 정정 — k02 의 "20.1도 · 0.12점 반올림"은 운영 계산이 아니었다). **국면 정렬 단계 미확인**(운영 DTW distance 정타 6.51 vs 실수 26.94) | Phase 37 Success 1 |
| 3 | **이번 학습이 무엇을 개선할 가설이 있나** | ❌ 없음. v35·v36 은 같은 데이터로 두 번 돌렸다 | 가설 1문장 + 대상 실패유형 |
| 4 | **인물·세션 분리 평가셋이 있나** | 🔶 **틀 있음 · 정책 코드 반영(10-02, `179d1392`)** — 평가 항목 = `sealed_tests.jsonl` 에서 안 닫힌 시험(status ≠ closed)의 시험 영상 + 짝 + 같은 인물·세션 클립. 닫힌 시험의 영상과 practice 는 연습 영상 → 학습 후보(belle 09-26 "시험 영상은 배우지 않는다, 나머지는 전부 배운다"; 시험 영상 = 처음 채점하는 영상만). 점검 = `backend/scripts/eval_split_check.py`(L1 같은 파일 · L2 같은 세션 = 오류, L3 같은 인물 = 경고). **10-02 재실행 [확인]: exit 2 평가셋 없음** — 유일한 시험 260925-mvh 가 closed 라 평가 영상 0편, 정은지 실수 fixtures 6편 = 연습 영상 → 학습 후보(L1 0). `sealed_tests.jsonl` 은 이력이라 그대로 두고 status 로 처리한다, `--mark-holdout` 은 안 돌렸다(누수 0이라 필요 없음). **게이트 4 는 다음 시험 영상이 봉인될 때 켜진다** — 다음 후보 = 정은지 중급콤보 영상(belle 09-30: Phase 38 뒤). 인물이 1명뿐이라 **인물 분리는 여전히 불가** | `eval_split_check.py` exit 0 (exit 2 = 평가셋 없음 = 통과 아님) |
| 5 | **비학습 기준선(E1·E2)이 측정됐나** | ❌ 미측정. E3 가 E2 를 넘는지 볼 수가 없다 | Phase 37 Success 3 |
| 6 | 예산 | ❌ 잔액 **$16.93** (10-02 실측 · Motion·타 프로젝트 Pod 0대 · pod-expected=down) / 사이클 **$33~38** — 아직 못 미침. 09-23 $23.12 에서 38-14 분석 Pod 등으로 줄었다 | RunPod `clientBalance` |
| 7 | GPU | ❌ A100급 필요(5090 OOM 실측). 미확보 — 10-02 재고는 안 봤다 [미확인] | RunPod 재고 |

★**2~5 는 학습 없이 하는 일이다.** 돈이 생겨도 그것부터다 —
안 하면 또 "돌렸는데 떨어졌다"로 끝난다(현재 5사이클 0승격).

## 왜 건수 조건만으로는 부족한가 (2026-09-23 외부리뷰)

- **v35 · v36 은 학습 데이터가 229개로 완전히 동일**했다. 같은 실험을 두 번 돌린 셈이다.
- 현재 학습은 좌표 보정·결함·구간·렌더·코칭을 **한 출력에 전부** 담는다.
  적은 정답으로 너무 많은 것을 동시에 가르치고 있는지 먼저 점검해야 한다.
- 승격해도 **그 모델을 앱에 꽂는 배선이 0건**이다(22-08/09/10 미실행).
  즉 지금 성공해도 수강생 화면은 안 바뀐다.

## 돌리는 법 (게이트 다 켜진 뒤)

1. belle 이 A100급 Pod 추가 (EU-RO-1, 기존 볼륨 `a5z753defc`)
2. `bash backend/scripts/pod_doctor.sh` — 결손 복구
3. train_venv312 없으면: `TRAIN_VENV_ISOLATED=1 bash backend/training/sft/setup_train_venv.sh`
4. **`backend/scripts/eval_split_check.py` 가 exit 0 이어야 한다**(평가셋 있음 + 누수 0. exit 1 = 누수, exit 2 = 평가셋 없음 = 통과 아님 — 다음 시험 영상 봉인 전) → 전 사이클: preflight → label → assemble → train → gates → promote
5. ★**학습 범위를 좁혀서 시작** — 좌표 생성·그림 명세·긴 코칭 문장은 같은 학습의 필수 출력에서
   분리(외부리뷰 §9.1). 한 번에 여러 조건을 바꾸지 않는다.

## 넘어야 할 선

`[정정 2026-09-23]` 종전에 "직전 판 성적"이라 적었던 **빈 골격 9/29 · 4동작 중 1동작**은
**v29 성적**이다. 직전 사이클은 **v38**이다.

**v38 성적 [확인 2026-10-02]** — 원본 = `.planning/quick/260828-v34-targeted-data/gates_v38.log`
(체크포인트 `v38-20260828-024523/checkpoint-76`, 원장 `promotion_ledger.json` 의 v38 행과 같은 경로),
요약 = 같은 폴더 `SUMMARY.md`. 학습 재료 distill 210 · text 34.

```
eval18 결함 짚기  : 겨냥한 4동작(power-spin · peter-pan · elbow-twist-sister · pdshape) 전부 fault 쪽 결함 0건
                    (kip-up · climb 은 SKIPPED 추적만 — kip-up fault 1 < correct 2, climb fault 3 > correct 2)
결정론            : real-kipup-correct 두 번 돌린 verdict 가 다름
svg_spec          : 결함 리포트 8건 중 형식 맞는 것 0건 (target_angle_deg = None)
JSON 형식·시간축  : json_parse 1.0 · temporal_acc 1.0
판정              : gates FAIL, 승격 없음 (promotion_ledger.current = null, 5사이클 0승격)
```

넘어야 할 선 = 겨냥한 4동작에서 fault 쪽 결함을 짚는 것(v38 은 0/4).
v29 의 "4동작 중 1동작"이 이 4동작과 같은 묶음인지는 [미확인] — 그래서 v29 → v38 을 "줄었다"로 잇지 않는다.
재료를 늘려도(distill 171 → 210) 겨냥한 4동작이 안 움직였다는 게 SUMMARY 의 판정이고("데이터를 넣는 것만으로는"),
게이트 3(가설)이 비어 있는 이유다.

## 정본
- 설계·성공기준 = `.planning/ROADMAP.md` Phase 37
- 데이터 규격 = `.planning/phases/37-continuous-learning/37-DATA-SPEC.md`
- 리뷰 판정 = `.planning/phases/37-continuous-learning/37-REVIEW-VERDICT.md`
