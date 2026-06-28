---
phase: quick-260629-cej
plan: 01
type: execute
wave: 1
files_modified:
  - backend/shared/python/sunity_shared/analysis/features.py
  - backend/tests/test_split_angle.py
requirements: [SPLIT-MEASURE-PRIMITIVE]
must_haves:
  truths:
    - "features.split_angle_series(keypoints) returns per-frame inter-thigh split angle in degrees from COCO-17 keypoints, NaN-safe"
    - "split is the angle at the hip-center between the two thighs (hip→knee lines) per IPSF definition; legs-together≈0°, perpendicular≈90°, full straight-line split≈180°"
    - "synthetic tests prove the measurement matches known leg geometries within tolerance and is monotonic (wider spread → larger angle)"
  artifacts:
    - path: "backend/shared/python/sunity_shared/analysis/features.py"
      provides: "split_angle_series + max_split helper (pure, numpy-only)"
      contains: "def split_angle_series"
    - path: "backend/tests/test_split_angle.py"
      provides: "synthetic ground-truth + monotonicity tests"
      contains: "split_angle_series"
---

<objective>
객관 split-각도 측정 primitive (분석 정확도 — belle 입력: kip-up 변별=다리 벌림). 순수 기하 함수만,
pod/네트워크 무관. 측정 정확도를 합성 정답으로 증명(belle "검증 방법" #1). 채점 wiring은 후속 task.
설계 = .planning/phases/15-mode-1-mode-3-testflight/15-SPLIT-MEASUREMENT-DESIGN-2026-06-29.md
</objective>

<context>
@./CLAUDE.md
@backend/shared/python/sunity_shared/analysis/features.py
@backend/shared/python/sunity_shared/analysis/skeleton.py
</context>

<key_facts>
- 키포인트 형상 = (T,17,3|4) xyz[+불확실도], compute_joint_angles 와 동일(features.py:36). 4채널이면 4번째 무시.
- COCO 인덱스 = skeleton.kp_index(name): left_hip/right_hip/left_knee/right_knee/left_ankle/right_ankle.
- 기존 _angle_deg(a,b,c) = vertex b 에서 a,c 사이각(deg). features.py 내 존재(compute_joint_angles 사용).
- IPSF split 정의(NotebookLM 2026-06-27): "lines the inner thighs form in alignment with hips to knees" → 두 허벅지(hip→knee) 사이각, hip-center vertex. full split(다리 일직선)=180°.
</key_facts>

<tasks>
<task type="auto">
  <name>Task 1: split_angle_series + max_split primitive (features.py)</name>
  <files>backend/shared/python/sunity_shared/analysis/features.py</files>
  <action>
    순수 함수 추가(numpy-only, 기존 _angle_deg/kp_index 재사용):
    - split_angle_series(keypoints) -> np.ndarray (T,): 각 프레임 inter-thigh split.
      hip_center = midpoint(left_hip, right_hip) (xyz, :3 만). 
      split[t] = _angle_deg(left_knee[t], hip_center[t], right_knee[t]) — vertex=hip_center, 두 ray=좌우 무릎.
      입력 검증 = compute_joint_angles 와 동일((T,17,≥3) 아니면 ValueError). 점 NaN이면 그 프레임 split NaN.
      도크스트링에 IPSF 정의 + 180°=full split + hip→knee(허벅지) 근거 인용.
    - max_split(split_series) -> tuple[float,int] | (nan,-1): 유한값 중 최댓값 + 프레임 인덱스.
      변별 순간(peak)용 — 도크스트링에 "안정 hold-window 아닌 peak: dynamic 동작의 변별 순간은 최대 벌림" 명시(kip-up 교훈).
    엔진/AWS/네트워크 의존 0. 이모지 금지.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python python3 -c "
import numpy as np
from sunity_shared.analysis.features import split_angle_series, max_split
from sunity_shared.analysis.skeleton import kp_index
# build 1 frame: hips at origin-ish, legs spread to a known angle in 2D (z=0)
kp=np.zeros((1,17,3))
def put(name,x,y): kp[0,kp_index(name)]=[x,y,0.0]
put('left_hip',-1,0); put('right_hip',1,0)
# legs straight down (together-ish): knees directly below each hip
put('left_knee',-1,-1); put('right_knee',1,-1); put('left_ankle',-1,-2); put('right_ankle',1,-2)
print('near-parallel down:', round(float(split_angle_series(kp)[0]),1))
# full split: knees opposite horizontal from hip center
put('left_knee',-2,0); put('right_knee',2,0)
print('full split:', round(float(split_angle_series(kp)[0]),1))
"</automated>
  </verify>
  <done>near-parallel ~0°, full split ~180°. max_split 동작.</done>
</task>

<task type="auto">
  <name>Task 2: 합성 정답 + 단조성 테스트 (test_split_angle.py)</name>
  <files>backend/tests/test_split_angle.py</files>
  <action>
    합성 키포인트로 알려진 기하 → 알려진 split 검증(±2° tol):
    - 다리 모음(양 무릎 hip 바로 아래) ≈ 0°
    - 직교(한 다리 수평, 한 다리 수직) ≈ 90°
    - full split(양 무릎 hip-center 반대 수평) ≈ 180°
    - 단조성: 벌림 각을 점진 증가시키며 split_angle_series 가 단조 증가
    - NaN-safety: 한 점 NaN이면 그 프레임 NaN, 나머지 정상
    - max_split: 시계열에서 peak 프레임/값 정확
    구조적 단언만, 의미있는 테스트만(수치 채우기 금지). 실제 함수 시그니처 소스 확인 후.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion/backend && PYTHONPATH=shared/python python3 -m pytest tests/test_split_angle.py -q</automated>
  </verify>
  <done>전 테스트 통과. 합성 정답(0/90/180) + 단조성 + NaN-safety + max_split.</done>
</task>
</tasks>

<success_criteria>
- split_angle_series + max_split 순수 함수, 키포인트→inter-thigh split(deg), IPSF 정의.
- 합성 정답 0/90/180° ±2° + 단조성 + NaN-safety 테스트 통과.
- 엔진/AWS 코드 변경 0(features.py 추가만). 회귀 0.
</success_criteria>

<output>
Create .planning/quick/260629-cej-split-angle-geometric-measurement-primit/260629-cej-SUMMARY.md when done.
</output>
