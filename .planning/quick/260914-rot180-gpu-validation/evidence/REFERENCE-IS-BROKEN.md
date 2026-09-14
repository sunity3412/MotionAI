# 실측 — 저장된 기준 모션이 허용오차보다 크게 틀려 있다 (2026-09-14)

**오늘 가장 중요한 발견.** 회전 실증을 하러 갔다가 더 큰 것을 찾았다.

Pod `wluq3losoiqcyh` (RTX PRO 4500 Blackwell), 커밋 `e3936dfb`, ORT-gpu 1.19.2 CUDA EP,
`RTMW_DETERMINISTIC=1`. 대상 = 정은지 pdshape 기준 영상(`reference/ref-pdshape.mp4`,
15.77초)을 **학생 영상으로 올려 자기 자신과 mode1 비교**했다.

---

## 1. 관측 — 챔피언 영상이 회전을 켜자 100점에서 60점이 됐다

| | OFF (현행 운영) | ON (rot180) |
|---|---|---|
| overallScore | **100** | **60** |
| dimensionScores | angle 100 / stability 62 | angle 41 / stability 94 |
| executionRawTotal | **0** | **−49.1** |
| 감점 record | 없음 | right_elbow −20.0 · left_hip −15.0 · left_knee −14.1 |
| 억제 record | — | right_hip −4.7 · right_knee −1.2 |
| unjudgedJoints | right_hip (collapse) | left_shoulder (collapse) |

그런데 **좌표는 오히려 극적으로 좋아졌다**:

| `result.joints3d` 실측 | OFF | ON |
|---|---|---|
| 붕괴 프레임 | 2 | **0** |
| 뼈위반 p90 평균 | **7.171** | **0.774** (−89%) |
| 최악 뼈 2개 | 19.953 / 20.604 | 0.882 / 0.937 |

09-13 로컬 CPU 예측(R전완 19.9 → 0.83)과 **정확히 일치**. 회전은 제 일을 했다.

## 2. 원인 — 기준 모션도 똑같이 망가져 있다

```
저장된 reference/ref-pdshape  (reprocessedAt 2026-06-15, pipelineVersion phase4_v1)
  붕괴 4프레임 · 뼈위반 p90 평균 4.976 · 최악 뼈 20.538
  joints3d z 전부 0 · space='pole_aligned' 라벨은 거짓(항등 폴백)
```

- **OFF**: 학생(뼈 7.17) ≈ 기준(뼈 4.98) → **틀린 것끼리 일치** → 100점
- **ON**: 학생(뼈 0.77) ≠ 기준(뼈 4.98) → 불일치 → −49.1 → 60점

**OFF 의 100점은 "잘 쟀다"가 아니다.** 학생과 기준을 같은 고장난 자로 재서 나온
동어반복이다. 회전이 학생 쪽 자만 고치자 그 일치가 깨졌다.

## 3. 확증 — 감점은 기준이 가장 틀린 관절에 정확히 떨어진다

같은 영상에서 기준 각도를 회전 켜고 재추출해(`extract_reference_angles.py`,
Pod 에서 GPU) 저장본과 관절별 중앙값을 비교했다.

| 관절 | 저장본 | 재추출(ON) | 차이 | 학생이 받은 감점 |
|---|---|---|---|---|
| left_elbow | 65.0 | 65.1 | **+0.1** | **0** |
| **right_elbow** | 101.7 | 154.0 | **+52.3** | **−20.0** |
| left_shoulder | 114.5 | 154.3 | +39.7 | 0 (학생 쪽 붕괴로 제외) |
| right_shoulder | 43.4 | 39.1 | −4.3 | 0 |
| **left_hip** | 96.1 | 139.3 | **+43.2** | **−15.0** |
| right_hip | 102.1 | 128.8 | +26.7 | −4.7 (억제) |
| **left_knee** | 94.1 | 138.6 | **+44.5** | **−14.1** |
| right_knee | 115.9 | 124.5 | +8.7 | −1.2 (억제) |

**기준이 맞는 관절(+0.1°)은 감점 0, 가장 틀린 세 관절이 감점 3건 전부다.**
인과가 닫혔다.

★ **허용오차는 20°인데 저장 기준은 8관절 중 5개가 26~52° 어긋나 있다 —
최대 2.6배다.** 지금의 mode1 점수는 고장난 자로 잰 값이고, 학생을 같은 고장난
자로 재기 때문에만 그럴듯해 보인다.

## 4. 함께 드러난 기준 라이브러리 문제

- **fps 불일치**: 저장본 237프레임(≈15fps) vs 현재 파이프라인 재추출 159프레임(≈10fps).
  같은 15.77초 영상이다. 기준은 다른 샘플링으로 만들어졌다.
- **회전 없이도 재추출값이 저장본과 다르다**(OFF 재추출 대비 right_shoulder +9.8°,
  right_hip −5.2°). 즉 **회전 이전에 이미 드리프트가 있다** — 6월 추출 이후
  파이프라인이 바뀌었는데 기준은 그대로다.
- `space='pole_aligned'` 라벨이 학생·기준 양쪽에서 거짓이다(z 전부 0, 항등 폴백).

## 5. 판정에 미치는 영향

**회전 플래그를 단독으로 켜면 안 된다.** 켜는 순간 모든 mode1 점수가
"교정된 학생 vs 미교정 기준"의 비대칭 비교가 되고, 그 결과가 바로
PROJECT.md 가 핵심 우려로 박아둔 **"정은지 영상 41점 위양성"** 이다.
오늘 그것을 60점으로 재현했다 — 우리 손으로.

**회전 + 기준 11개 재추출은 한 묶음이다.**

단 재추출 자체가 별도 결정을 부른다:
- 재추출하면 **과거 분석과의 점수 연속성이 끊긴다**(같은 영상이 다른 점수를 받는다)
- 기준 11개 중 pdshape 하나만 쟀다. 나머지 10개의 드리프트 폭은 **미측정**
- [[display-string-is-not-a-join-key]] 규율상 기준 교체는 불변 id 로 버전을 나눠야 한다

## 6. 재현 방법

```
# 학생 런 (같은 영상, 플래그만 다름)
evidence/upload_only.py --video <ref-pdshape.mp4> --mode mode1 --reference ref-pdshape
# Pod 에서 /analyze 직접 위임 → docs/ref_off.json, docs/ref_on.json

# 좌표 품질
evidence/joints3d_metrics.py docs/ref_off.json docs/ref_on.json

# 기준 재추출 (Pod, GPU)
ROT180_INVERSION_ENABLED={0,1} python3 scripts/extract_reference_angles.py \
    --motions ref-pdshape --out ref_angles_{off,on}.json
```

산출물: `docs/ref_off.json` · `docs/ref_on.json` · `ref_angles_off.json` · `ref_angles_on.json`
