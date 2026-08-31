# 자세 축 신뢰성 수리 검증 (quick-260831-o63)

규율: 예측 블록은 **스크립트 실행 전** 박제. 이후 수정 금지. FAIL 시 curve-fit 금지.

## 예측 블록 (2026-08-31, 측정 전 작성)

1. **퇴화 4개 기준**(foxtop·foxtop-split·invert·sideway-spin): `uprightness_measurable`
   = False, `torso_uprightness_series` 전 프레임 NaN → 상수 90.0° 가 더 이상 안 나온다.
2. **정상 7개 기준**(climb·combo·elbow·kip-up·pdshape·peter-pan·power-spin):
   measurable = True, 상체각 중앙값이 08-31 측정치와 **동일**(24.9/63.9/111.1/8.1/151.9/
   6.4/84.1°) — 무회귀.
3. **양방향화**: 기준이 뒤집힘 계열(pdshape 151.9°)이고 학생이 덜 뒤집힌 경우
   (예: 학생 120°) → 종전에는 미발화, 이제 "덜 기울어져 있음" 라인이 발화한다.
4. **피터팬 무회귀**: 08-31 라이브 doc(학생 상체각 > 기준)에서 종전과 같은
   "더 기울어져 있음" 방향이 유지된다.

## 측정 블록 (스크립트 출력 원문 — 예측 블록 수정 없음)

### 1차 시도 = **예측 1 FAIL** (박제)

퇴화 4개가 measurable=True 로 통과. 원인 실측: 그 좌표의 y 는 **정확한 0 이 아니라
6e-14 ~ 1.2e-13**(평면 회전 연산의 부동소수 잔여, x·z 스케일 ~550). 최초 구현의
"성분이 정확히 0" 구조 판정이 실데이터에서 무력했다.
★합성 픽스처(y=0.0)가 실데이터보다 깨끗해서 단위테스트는 통과했다 — 가드가 실데이터를
못 잡는 것을 **실데이터 검증에서만** 발각. curve-fit 대신 원인을 재고 판정을 교체:
`up 축 범위 > 좌표스케일 × float64 eps` (임의 임계 아님 — 그 스케일의 표현 한계.
살아있는 축과 15자릿수 차이). 픽스처도 실데이터 형태(잔여 1e-13)로 교체.

부수: `test_torso_tilt_monotonic` 이 deg=90 에서 걸렸다 — 4관절만 설정하고 13관절을
0 으로 두는 합성이라 y 축 전체가 반올림 수준이 된 artifact(17관절 실데이터에선 불가능).
픽스처에 전신 y 변화(귀) 추가, 각도값은 불변.

### 2차 = 전 항목 PASS

```
[1][2] 기준 모션 전수
  ref-climb                measurable=True  중앙값=24.9°  (이전 24.9)   PASS
  ref-combo                measurable=True  중앙값=63.9°  (이전 63.9)   PASS
  ref-elbow-twist-sister   measurable=True  중앙값=111.1° (이전 111.1)  PASS
  ref-foxtop               measurable=False 전NaN=True                 PASS
  ref-foxtop-split         measurable=False 전NaN=True                 PASS
  ref-invert               measurable=False 전NaN=True                 PASS
  ref-kip-up               measurable=True  중앙값=8.1°   (이전 8.1)    PASS
  ref-pdshape              measurable=True  중앙값=151.9° (이전 151.9)  PASS
  ref-peter-pan            measurable=True  중앙값=6.4°   (이전 6.4)    PASS
  ref-power-spin           measurable=True  중앙값=84.1°  (이전 84.1)   PASS
  ref-sideway-spin         measurable=False 전NaN=True                 PASS
```

[3] 양방향화 — 뒤집힘 기준(pdshape 151.9°) vs 덜 뒤집힌 학생(120°): delta -31.9,
significant, **발화함** → "학생 상체가 기준보다 32° 정도 덜 기울어져 있음 — '상체를
기준 자세 각도만큼 더 기울여 넣으면 …'". 종전에는 미발화였다. **PASS**

[4] 피터팬 무회귀 — 라이브 doc(학생 12.4° vs 기준 6.4°, delta +6.0): "더 기울어져
있음" 방향 유지(문구만 기준 정합형으로 교체). **PASS**

게이트: 백엔드 전체 **4544 passed / 0 failed** (기준선 4537 + 신규 7).
점수 경로 무접촉(postureAxes 는 coach context 전용).
