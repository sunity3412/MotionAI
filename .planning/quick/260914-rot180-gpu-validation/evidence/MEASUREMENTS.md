# 실측 — rot180 회전 GPU 실경로 검증 (2026-09-14)

**전부 운영 GPU 경로.** RunPod Pod `jhm4vvmv0z1yon` (RTX PRO 4500 Blackwell 32GB,
EU-RO-1, 네트워크 볼륨 `a5z753defc`), 커밋 `e3936dfb`(번들 반입), onnxruntime-gpu
1.19.2 CUDAExecutionProvider, `RTMW_DETERMINISTIC=1`.

기동 검증 전 항목 통과 — `/health`: `status=ok` · `pipeline_loaded=true` ·
`commitSha=e3936dfb…` · `poseEngine=RTMWPoseEngine` · `recognizer=GeminiTechniqueRecognizer`
· `start_server.sh` md5 = 리포 정본과 동일 · `pod_doctor.sh` **onnxruntime CUDA EP [OK]**.

영상 = belle pdshape(`user.mp4`, 93.8MB) · mode1 · `ref-pdshape` · 182프레임.
09-13 로컬 CPU 실측과 **같은 영상**이다.

---

## 0. 결론 세 줄

1. **재현됐다.** 붕괴 6→**0**, 뼈위반 p90 1.502→**0.763**(−49%). 로컬 CPU 예측치
   (rot180 붕괴 0 / 뼈위반 0.753)와 **1.3% 이내**로 일치.
2. **못 본 관절 1→0.** 09-10 부터 문제였던 `right_elbow` 가 관측되기 시작했고,
   **가장 큰 감점(−16.2)** 을 내놓았다.
3. **점수는 60 → 60, 안 움직였다.** 이유는 회전이 무력해서가 아니라
   **감점 상한(40) 이 이미 포화**라서다. 원감점은 −40.3 → **−58.8** 로 커졌는데
   상한이 전부 흡수했다.

---

## 1. A/B 설계와 잡음 바닥

같은 영상을 같은 Pod 에서 **3회** 돌렸다. 런1·런2 는 플래그 off, 런3 은 on.

| 런 | 플래그 | analysisId | 키포인트 |
|---|---|---|---|
| 런1 | off | `09ae90ad…` | 기준 |
| 런2 | off | `62eac2bb…` | **런1 과 byte 동일** (max abs diff 0.0) |
| 런3 | on | `6888d5cc…` | — |

**잡음 바닥 = 0.** 독립 업로드·독립 분석인데 런1·런2 의 `joints3d` 가 완전히
같았고 점수·차원점수·unjudgedJoints 도 전부 같았다. 즉 런3 의 차이는 **전부
플래그 탓**이다. (`RTMW_DETERMINISTIC=1` 이 Blackwell CUDA EP 에서 실제로 동작한다는
첫 실증이기도 하다.)

> ★ off 기준선은 `prod_orig` 가 아니다. 운영은 `PR_INVERSION_ENABLED=1` 이라
> off 런에서도 PR 원근 워프가 **실제로 돌았다** —
> `pr_inversion applied=true replaced=182/182`. 그러니 아래 대조는
> **"지금 운영(PR 워프) vs 회전"** 이다. 09-13 MEASUREMENTS §4 와 같은 축.

---

## 2. 세 숫자

| 지표 | off (PR 워프 = 현행 운영) | on (rot180) | 09-13 로컬 CPU 예측 |
|---|---|---|---|
| 붕괴 프레임 | 6 | **0** | 0 ✅ |
| 뼈위반 p90 평균 | 1.502 | **0.763** (−49%) | 0.753 ✅ |
| 못 본 관절 | **1** (`right_elbow`, reason=collapse) | **0** | 미측정 |
| overallScore | 60 | **60** | 미측정 |
| angle | 45 | 38 | — |
| stability | 72 | 91 | — |
| 원감점 합(executionRawTotal) | −40.3 | **−58.8** | — |
| 상한 적용 후(executionCappedTotal) | −40.0 | −40.0 | — |

뼈별 p90:

```
off : [1.404, 1.889, 1.118, 2.007, 0.962, 1.538, 1.483, 1.618]
on  : [0.772, 1.011, 0.693, 0.866, 0.553, 0.873, 0.490, 0.844]
```

8개 뼈 **전부** 개선. 악화된 뼈 0개.

측정 정의는 09-13 `evidence/decompose.py:71-83` 그대로 —
붕괴 = 17키포인트 0.1px 반올림 후 고유좌표 ≤ 8, 뼈위반 = (길이/torso)의 클립중앙값
대비 |log 비율| p90 을 8뼈 평균. 재계산 스크립트 = `evidence/joints3d_metrics.py`.

> 좌표 출처 = `result.joints3d`. z 가 전 프레임 정확히 0 이고
> `pole/aligner.apply_alignment` 는 **순수 회전행렬**이라 길이·구별성이 보존된다.
> torso 중앙값도 66.9px(off)/67.5px(on) 로 로컬 CPU 의 67.2px 와 맞는다 —
> 두 계기가 같은 스케일을 재고 있다는 교차 확인.

---

## 3. 계기 재현 — 로그가 예측치를 그대로 냈다

```
rot180_inversion both_flags_on pr_warp_skipped=true
rot180_inversion detect is_inverted=True ratio=0.705 run=15 valid=149/182
rot180_inversion disagreement valid_pairs=3094 p50=0.109 p90=1.608 max=4.764 torso_px=67.5
rot180_inversion applied=true replaced=182/182 adopted=182
    first_missing=0 second_missing=0 second_nonfinite=0 second_out_of_bounds=0
    second_pass_ms=8467
```

| 항목 | 모듈 docstring 예측 | GPU 실측 |
|---|---|---|
| 불일치 p50 (clip-median torso) | 0.110 | **0.109** |
| 불일치 p90 | 1.618 | **1.608** |
| torso | 67.2px | **67.5px** |

- **채택률 100%** (182/182), fail-safe 기각 0건 — 혼합 패스 이음매 걱정은 이 클립에선 없다.
- **`pr_warp_skipped=true`** — `start_server.sh:24` 주석의 우선순위 주장이 실경로에서 확인됐다.
  3패스는 돌지 않는다.
- 회전 2패스가 PR 워프보다 **더 싸다**: 8,467ms vs 10,918ms. rtmw 단계 전체도
  20.7s(on) vs 22.3s(off).

---

## 4. 점수가 안 움직인 이유 — 감점 상한 포화

```
off : executionRawTotal −40.3  → executionCappedTotal −40.0 → final 60
on  : executionRawTotal −58.8  → executionCappedTotal −40.0 → final 60
       (executionCap = 40.0, scoreFloor = 25.0, baseline = 100)
```

감점 내역:

| 항목 | off | on |
|---|---|---|
| `left_elbow` | −15.1 | −9.3 |
| **`right_elbow`** | **없음 (못 봄)** | **−16.2 ← 최대 감점** |
| `left_shoulder` | 억제됨(−2.8, 측정오차 내) | **−12.0 (억제 해제)** |
| `right_shoulder` | −6.7 | 없음 |
| `left_hip` | −4.0 | −4.1 |
| `left_knee` | −7.8 | −10.0 |
| `right_knee` | −6.7 | −7.2 |
| 기록 수 | 5 | 6 |

두 가지가 같이 일어났다:

1. **못 보던 관절이 보였다** — `right_elbow` 가 감점 목록에 처음 등장했고 최대값이다.
2. **측정오차 억제가 풀렸다** — off 에서 `left_shoulder` 는 측정값 22.35°, 신뢰구간
   [19.92, 26.26] 이 허용치 20° 를 걸쳐 "오차 범위 내"로 **억제**됐다. 좌표가 좋아지자
   구간이 좁아지며 실제 감점 −12.0 으로 방출됐다.

**그런데 최종 점수는 그대로다.** off 가 이미 원감점 −40.3 으로 상한 40 을 막
넘긴 상태였기 때문이다. 즉 이 클립에서 **점수는 이 개선을 담을 해상도가 없다.**

> ★ belle 09-13 확정("명백히 틀린 영상이 100점이 되는 건 말이 안 된다")과의 관계:
> 회전은 **그 반대 방향**으로 작동한다. 못 본 관절의 감점을 지워 점수를 올리는 게
> 아니라, 관절을 **보이게 만들어 감점을 추가**한다. 방향은 belle 기준과 맞는다.
> 다만 이 클립에선 상한이 포화라 점수로는 안 보인다.
>
> ★ 따로 봐야 할 것: 원감점 −40.3 짜리와 −58.8 짜리가 **둘 다 60점**이다.
> 상한이 포화된 구간에서는 점수가 결함량을 구분하지 못한다. 이건 회전과 무관한
> 별개 사안이고, 상한을 건드리는 것은 belle 판단 영역이다 — 오늘 아무것도 안 바꿨다.

---

## 5. 미해결 / 이 실측이 답하지 않는 것

- **한 클립·한 동작(pdshape)뿐이다.** 09-13 로컬은 정은지 기준 모션에서도 재현했지만
  GPU 실경로로는 안 재봤다. 일반화 주장은 아직 이르다.
- **렌더 정렬은 회전을 못 받는다.** `compare_align.build_model`(`compare_align.py:102`)은
  자기 Wholebody 를 따로 만든다 — 채점 좌표와 렌더 좌표가 더 벌어진다. 이번 런에서
  렌더 산출물은 눈으로 확인하지 않았다. **미검증.**
- **기준 모션 각도는 회전 전 산출**이다. mode1 은 Firestore 에 저장된 기준 각도와
  비교하므로, 학생만 교정된 비대칭 비교다. 위 감점 변화에는 그 성분이 섞여 있다.
- **`rtmw_error_profile.json` 재측정은 안 했다** (회전 전 분포 그대로).
- 점수가 실제로 움직이는지는 **상한 미포화 클립**에서 재야 한다.

---

## 6. 비용·운영 기록

- Pod 총 과금 **$0.41** (잔액 6.914 → 6.501). 생성~종료 약 35분, $0.72/hr.
- **Blackwell cold JIT = 약 125초** (rtmw 첫 런 147.6s, 두 번째 22.3s). 메모리
  `rtmw-blackwell-lean-bootstrap` 의 "~127s PTX→SASS" 와 일치. 컨테이너당 1회.
- 종료 즉시 Terminate + SSM `pod-expected=down` 기록 완료. 잔여 Pod 0대 확인.
- ★ **`start_server.sh:51` 의 `> /tmp/runpod_server.log` 는 재기동 때 로그를 truncate 한다.**
  플래그를 켜려 재기동하면서 런1·런2 로그를 잃었다. 전사본 = `run12_log_lines.md`.
  **로그는 종료 전이 아니라 재기동 전에 내려받아야 한다.**

## 7. 산출물

```
evidence/
  MEASUREMENTS.md          이 문서
  joints3d_metrics.py      붕괴·뼈위반 재계산 (정의는 09-13 decompose.py 승계)
  upload_only.py           앱 순서 업로드만 (Lambda 무접촉 위임용)
  poll_doc.py              종결 폴링 + doc 전문 저장
  run12_log_lines.md       런1·2 로그 전사본 (원본 유실)
  runpod_server_run3.log   런3 서버 로그 원본
  docs/run1_off.json  docs/run2_off.json  docs/run3_on.json
```
