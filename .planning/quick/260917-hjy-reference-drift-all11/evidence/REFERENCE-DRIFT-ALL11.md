# 실측 — 기준 11편 회전 드리프트 전수 (2026-09-17)

**09-14 `REFERENCE-IS-BROKEN.md` 는 pdshape 1편만 쟀다.** 그 인계서가 나에게 배정한
"기준 11편 드리프트 전수 측정"을 GPU 로 끝냈다. **결론이 09-14 의 서술을 정정한다.**

Pod `mkyjbo14kwlwsd` (RTX PRO 4500 Blackwell) · 리포 `e3936dfb` · ORT-gpu 1.19.2 CUDA EP ·
`RTMW_DETERMINISTIC=1` — **09-14 실측과 동일 GPU·동일 핀·동일 코드**.
(`git diff e3936dfb origin/main -- backend/shared backend/scripts/extract_reference_angles.py
backend/runpod_inference` = 빈 결과. 추출 경로에 변경 0.)

---

## 0. 계기 검증 — 이 측정을 믿어도 되는 이유

측정 전후로 pdshape 을 대조군으로 썼다. 09-14 가 남긴 GPU 산출
(`260914-.../evidence/ref_angles_{off,on}.json`)과 오늘 재추출을 비교:

| 대조 | 형상 | 최대차 | 판정 |
|---|---|---|---|
| pdshape OFF | (159,8) | **0.000000°** | byte 동일 |
| pdshape ON | (159,8) | **0.000000°** | byte 동일 |

폐색 프레임 dict 도 동일, `referenceSplitAngle` 도 동일(OFF 180.0 / ON 176.65).
**대조군이 완전 재현되므로 나머지 10편 수치를 같은 신뢰도로 읽을 수 있다.**

---

## 1. ★ 기준 라이브러리는 "낡아서 드리프트한" 것이 아니다 — 반증

저장본(2026-06-14~15 추출, 일부 08-16) vs **오늘 파이프라인 재추출(회전 OFF)**.
관절별 시간 중앙값 차이(도). 허용오차 20°.

| 기준 | 프레임(저장→재) | 최대 |Δ| | 20° 초과 |
|---|---|---|---|
| ref-climb | 120→80 | 5.3 | 0 |
| ref-combo | 931→621 | 3.3 | 0 |
| ref-elbow-twist-sister | 329→220 | 4.8 | 0 |
| ref-foxtop | 426→284 | 4.8 | 0 |
| ref-foxtop-split | 485→324 | 6.5 | 0 |
| ref-invert | 260→174 | 5.5 | 0 |
| ref-kip-up | 118→79 | 2.6 | 0 |
| ref-pdshape | 237→159 | 9.8 | 0 |
| ref-peter-pan | 130→87 | 9.3 | 0 |
| ref-power-spin | 159→106 | 15.6 | 0 |
| ref-sideway-spin | 298→199 | 7.9 | 0 |

**88개 관절-기준 쌍 중 허용오차 초과 = 0개. 최대 15.6°.**

- pdshape 의 R.shoulder 9.8° · R.hip 5.2° 는 09-14 가 적은 값과 정확히 일치한다
  (부호 규약만 반대) — 이 표가 09-14 를 재현하면서 범위만 넓힌 것이다.
- **fps 차이는 무해하다.** 저장본은 ~15fps, 재추출은 ~10fps 인데(같은 영상 길이)
  각도 중앙값 차이는 어디서도 16°를 넘지 않는다. 09-14 가 곁가지로 적은
  "237 vs 159 프레임" 은 드리프트의 증거가 아니다.

> **정정**: 09-14 §4 "회전 이전에 이미 드리프트가 있다" 는 문장은 크기를 안 밝혔다.
> 전수로 재보니 그 크기가 **허용오차 아래**다. 재추출의 근거가 되지 않는다.

### 1-1. 단서: 꼬리 분포는 다르다 (약한 신호, 채점 경로 아님)

중앙값이 아니라 p10/p90·산포로 보면 4편(elbow-twist-sister 26.3 · pdshape 30.0 ·
peter-pan 21.6 · power-spin 24.7)이 20°를 넘는다. 다만 이 통계는 프레임 샘플링
(15fps↔10fps)과 폐색 보간에 민감하고, **채점이 읽는 양이 아니다**(채점은 DTW 정렬
윈도 중앙값). 헤드라인으로 쓰지 말 것. 재현 = `evidence/dist.py` 정의.

---

## 2. ★ 재추출이 필요한 유일한 이유는 회전이다

같은 코드·같은 실행에서 플래그만 바꾼 OFF vs ON. 저장 시점 변수가 전혀 없다.

| 기준 | 회전이 바꾸나 | 프레임별 최대차 | 중앙값 20° 초과 관절 |
|---|---|---|---|
| ref-climb | **아니오** | 0.000000 | 0 |
| ref-kip-up | **아니오** | 0.000000 | 0 |
| ref-peter-pan | **아니오** | 0.000000 | 0 |
| ref-power-spin | **아니오** | 0.000000 | 0 |
| ref-sideway-spin | **아니오** | 0.000000 | 0 |
| ref-foxtop-split | 예 | 134.39 | 0 |
| ref-combo | 예 | 145.44 | 1 (L.hip 25.7) |
| ref-elbow-twist-sister | 예 | 162.95 | 1 (R.elbow 25.7) |
| ref-foxtop | 예 | 152.27 | 1 (R.hip −23.4) |
| ref-invert | 예 | 112.47 | 1 (R.knee −26.9) |
| **ref-pdshape** | 예 | 137.92 | **5** (R.elbow 55.3 · L.hip 45.7 · L.knee 42.2 · L.shoulder 35.7 · R.hip 31.9) |

- **11편 중 5편은 전 프레임·전 관절 차이가 정확히 0.000000 이다.** 회전 게이트가
  선택적으로만 발화한다는 실측 확증이다.
- 20° 초과 관절 **9/88**. **그중 5개가 pdshape 하나다.**
- 나머지 4편은 각각 **1관절만** 23~27° — 허용오차 바로 위다.
- 프레임별 최대차가 112~163° 인데 중앙값은 대부분 20° 아래다. 회전은 개별 프레임을
  크게 뒤집지만 시간 중앙값이 상당 부분 흡수한다.

> **정정**: 09-14 의 "저장 기준은 8관절 중 5개가 26~52° 어긋나 있다 — 최대 2.6배"
> 는 **pdshape 한 편의 성질**이다. 라이브러리 전체 성질이 아니다.
> 전수로는 88쌍 중 9개(10%), 5편은 아예 무변화다.

---

## 3. 회전은 "바꾼다"가 아니라 "개선한다" — 독립 신호

추출 로그의 폐색 보간 횟수(관절별 합). 폐색 = 신뢰도가 떨어져 시간축 보간으로
메운 프레임이다. 적을수록 실제로 본 관절이 많다.

| 기준 | 폐색 OFF | 폐색 ON | 변화 |
|---|---|---|---|
| ref-invert | 111 | 8 | **−93%** |
| ref-foxtop | 66 | 9 | **−86%** |
| ref-elbow-twist-sister | 146 | 27 | **−82%** |
| ref-pdshape | 98 | 20 | **−80%** |
| ref-foxtop-split | 70 | 17 | **−76%** |
| ref-combo | 228 | 56 | **−75%** |
| ref-climb / kip-up / peter-pan / power-spin / sideway-spin | 34/59/61/82/146 | 동일 | **+0** |
| **합계** | **1101** | **519** | **−53%** |

- 회전이 건드린 6편에서만 폐색이 −75~−93% 줄고, 안 건드린 5편은 **정확히 +0**.
- 09-14 의 학생측 실측(뼈위반 p90 7.171→0.774, 붕괴 2→0)과 같은 방향이다.
- 비용: 추출 시간 OFF 총 243.4s → ON 총 328.6s (**+35%**, 2패스).

---

## 4. 부수 결과 — 기각한 것 2건

### 4-1. "저장 `angles` 와 `joints3d` 가 불일치한다" → **결함 아님**

저장 `joints3d` 로 `compute_joint_angles` 를 돌리면 저장 `angles` 와 11편 전부
어긋난다(완전일치 0~1%, 중앙차 2.2~27.5°). 그런데 **갭필 + 5프레임 이동평균을 걸면
11편 전부 차이가 0.00 으로 닫힌다**(설명율 99.8~100%).

원인은 추출 경로가 `compute_joint_angles → temporal_fill` 이고 `temporal_fill` 이
폐색 보간 + `DEFAULT_SMOOTH_WINDOW=5` 가중 이동평균을 걸기 때문이다. 불확실도 채널은
저장되지 않으므로 재현이 안 될 뿐이다. **저장 두 필드는 정합한다.**
(재현 = `evidence/libcheck.py`, `evidence/smoothtest.py`)

### 4-2. "뼈위반으로 각도 드리프트를 예측한다" → **계기로 못 씀**

저장 좌표의 뼈위반 p90 으로 어느 관절각이 틀렸는지 예측하려 했으나 pdshape 정답에
교정하니 떨어졌다:

| | 뼈위반 최대 | 실제 드리프트 |
|---|---|---|
| R.knee (R정강 뼈 20.54) | **최대** | 8.7° (작음) |
| L.hip (L허벅 뼈 2.00) | **최소** | 43.2° (큼) |

뼈위반은 "길이가 떨리는" 실패는 잡지만 "통째로 틀린" 실패는 못 잡는다.
**저장 좌표만으로는 드리프트를 못 잰다 — GPU 재추출이 유일한 길이다.**
(재현 = `evidence/ref_drift_audit.py`)

---

## 5. 판정 1번(belle)에 미치는 영향

09-14 가 올린 판정 1번 = "**회전 + 기준 11편 재추출을 한 묶음으로**".
**묶음 요건 자체는 유지된다** — 회전을 켜면 기준 6편의 각도가 움직이므로
학생만 교정하면 비대칭 비교가 된다. 다만 **전제와 범위가 달라진다**:

| 09-14 서술 | 전수 실측 |
|---|---|
| "저장된 기준 모션이 허용오차의 최대 2.6배 틀려 있다" | pdshape **1편**의 성질. 라이브러리는 오늘 파이프라인과 88쌍 중 0개 초과로 일치 |
| "회전 이전에 이미 드리프트가 있다" | 있으나 **최대 15.6°, 전부 허용오차 아래** |
| 재추출 대상 11편 | 실제로 값이 바뀌는 것은 **6편**. 5편은 byte 동일 |
| "과거 분석과 점수 연속성이 끊긴다" | 끊기는 것은 **6편을 참조한 분석뿐**. 그중 크게 움직이는 것은 pdshape |

즉 belle 이 실제로 결정할 것은 "썩은 라이브러리를 갈아엎을 것인가"가 아니라
"**좌표계를 바꾸는 김에 기준 6편을 같이 다시 뽑을 것인가**"다.

---

## 6. 재현 방법

```bash
# 1) 기준 doc 1회 읽기 -> 로컬 (Firestore 읽기 11회. 에이전트별 재스캔 금지)
FIREBASE_SA_PATH=firebase-sa.json backend/.venv/bin/python evidence/pull_refs.py <outdir>

# 2) GPU 재추출 (Pod, RTX PRO 4500 Blackwell + ORT-gpu 1.19.2)
#    env = start_server.sh 와 동일 (RTMW_ONNX_PATH/YOLOX_ONNX_PATH/RTMW_DEVICE=cuda/
#          RTMW_DETERMINISTIC=1 + cudnn·cublas LD_LIBRARY_PATH)
ROT180_INVERSION_ENABLED={0,1} python3 scripts/extract_reference_angles.py \
  --motions ref-climb ref-combo ref-elbow-twist-sister ref-foxtop ref-foxtop-split \
            ref-invert ref-kip-up ref-pdshape ref-peter-pan ref-power-spin ref-sideway-spin \
  --out ref11_{off,on}.json
#    ★ --motions 기본값은 5개로 낡았다. 11개를 반드시 명시할 것.

# 3) 분석
backend/.venv/bin/python evidence/drift.py <outdir> evidence/ref11_off.json off
backend/.venv/bin/python evidence/drift.py <outdir> evidence/ref11_on.json  on
backend/.venv/bin/python evidence/offon.py evidence/ref11_off.json evidence/ref11_on.json
```

산출물: `ref11_off.json` · `ref11_on.json` · `extract_run.log`

**운영 코드 무접촉.** `ROT180_INVERSION_ENABLED` 는 여전히 `start_server.sh:24` 에서 0.
