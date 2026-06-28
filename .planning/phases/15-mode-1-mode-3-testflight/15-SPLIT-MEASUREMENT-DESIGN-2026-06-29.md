# 객관 split-각도 측정 설계 (분석 정확도, 2026-06-29)

## 왜 (belle 도메인 + 코드로 확정)
- belle 육안: kip-up correct vs fault의 변별 = **다리 벌림(split)**, 무릎 굽힘 아님(둘 다 펴짐).
- 코드(`app.py:2045`): **객관 split 측정 substrate 부재** — split_angle criterion은 Gemini 비전이 "스플릿/스트래들" 키워드로 짚을 때만 활성(`vision_veto.py:44`). 기하 측정 0.
- kip-up 100점 원인: Gemini 비전이 alignment 게이트에 막힘(not_applicable) → split 결함 미검출.
- split은 객관·IPSF 정의(180°±20°, NotebookLM)·키포인트로 계산 가능한데 안 하고 Gemini에 의존.

## 가치 (kip-up 하나가 아님)
- ✅ split 동작 일반화(어떤 split이든) — curve-fit 아님
- ✅ **Gemini 의존 축소 = audit P3** ("Gemini 판단 → 객관 IPSF 측정으로 이전")
- ✅ 빠진 객관 차원 1개 채움 = 분석 정확도 직접 개선
- ✅ belle "검증 방법"과 맞물림: 합성 검증으로 측정 정확도 증명 가능

## 설계 결정
1. **split 정의(IPSF)**: 두 다리 사이 각도 = (left_hip→left_ankle) vs (right_hip→right_ankle) 2D 벡터 사이각. full split=180°, 모은 다리=0°. (IPSF: "inner thighs hips-to-knees lines" — hip→knee도 후보. hip→ankle가 전체 다리 라인.)
   - 2D 이미지 평면(키포인트 2D RTMW와 일관, [[single-camera-first-multi-view-last]]). 단일 카메라 근사.
2. **측정 순간**: **max-split 프레임(peak)** — min-variance hold-window 아님. kip-up 교훈: 안정 윈도우는 dynamic peak를 씻어냄(무릎도 그래서 못 잡음). split의 변별 순간 = 최대로 벌린 순간.
3. **채점 방식**: **reference_relative 우선(Mode1)** — 학생 max-split vs 정은지 max-split 부족분 감점. 객관 180° 강요는 over-EXTEND 실수 재발 위험(full split 아닌 동작의 correct를 위양성). 정은지 자기 pair는 correct≈reference→clean, fault<reference→감점. = angle_vs_reference 미러.
   - 객관 180°(ipsf_absolute)는 "full split 요구 동작" 확인 후 후속(per-move expects_split flag).
4. **substrate**: 키포인트(keypoints_4ch, _process에서 가용) 필요. md 빌더는 angles만 받음 → split deficit를 _process에서 계산해 md 빌더 인자로 주입(angle_vs_reference 패턴 미러).

## 데이터 의존 (열린 항목)
- **reference split 데이터 부재**: 레퍼런스는 meanAngles + bodyComparisonSourcePose(1프레임 키포인트)만 저장. split 시계열 없음.
  - 옵션 A: bodyComparisonSourcePose 1프레임에서 split 계산(대표 프레임이 split 순간이 아닐 수 있음 — 제한적).
  - 옵션 B: 레퍼런스 재처리로 max-split(또는 키포인트 시계열) 저장 — 재-seed 필요(pod).
  - 권고: B(재-seed 시 referenceSplitAngle 필드 추가). A는 임시.

## 구현 순서
1. **[지금, pod 무관] split 기하 측정 primitive + 합성 검증** — 순수 함수 `split_angle(keypoints)` + 알려진 다리 배치→알려진 각도 단위테스트(모은 다리≈0°, 90° 벌림=90°, full split≈180°). **측정 정확도 증명(belle #1).**
2. max-split 프레임 선택 + 학생 split deficit 계산(_process, keypoints_4ch).
3. reference split: 재-seed로 referenceSplitAngle 저장(pod) 또는 source-pose 임시.
4. md 빌더에 split deficit 주입 → split_angle criterion 발화.
5. 검증: 합성(측정) + pod 재-sweep(kip-up split 잡히나, 정타 clean한가) + 게이트.

## 검증 = belle "점수 신뢰" 방법
- 합성 정답: 키포인트에 알려진 split 주입 → 측정값 일치 + 단조성(더 벌릴수록 split↑).
- pod re-sweep: kip-up fault < correct (split 변별), 다른 동작 회귀 0.
- belle 감사: split 감점이 육안과 일치하나.
