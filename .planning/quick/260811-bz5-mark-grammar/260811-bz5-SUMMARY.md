---
quick_id: 260811-bz5
date: 2026-08-11
status: complete
commits: 3
---

# 표시 문법 프로토타입 — 결과 (belle 판정 대기)

**판정 페이지**: https://claude.ai/code/artifact/27e89578-b701-47c3-881f-38e28d58287a
**실물**: `/Users/Shared/sunity-cards-260811-grammar/{current,ghost,wedge,hybrid}/` (휘발) +
리포 `out/` (보존) · 하네스 `render_harness.py`

## 성립한 것

1. **로컬 재렌더 하네스 (Pod 무관)** — Firestore keypointReport + S3 원본 영상 + 운영
   `build_fault_zoom_comparisons` 호출로 기준선 재현 **confirmed 4/4 픽셀 PASS**
   (mean|d| 1.07~1.10, >16 차이 픽셀 0%). round-trip 인증 5/5.
   ★저장 `userFrameIdx`/`refFrameIdx` 는 **rep 공간(18fps)**, 함수 override 는
   **frames 배열 공간(9fps)** — ÷2 변환이 다리다 (fault_zoom.py 3300).
2. **후보 문법 3종** — 기준 사이각을 학생 몸통축+카이럴리티에 이식(방위차 무관):
   A 고스트(점선+쐐기) / B 쐐기(쐐기+화살촉) / C 하이브리드(쐐기 상시, 고스트는
   델타≥8도만). A 는 델타 4~7도에서 고스트가 본선에 겹쳐 이발소 기둥 오독 → C 로 교정.

## 판정을 가르는 실측 (이번 라운드의 핵심 발견)

| 카드 | 감점 근거 | 순간 델타 | 판정 |
|---|---|---|---|
| left_hip | 20.0도 | 10도 | 문법으로 풀림 (쐐기가 읽힘) |
| right_elbow | 5.9도 | 6도 | 문법으로 풀림 (감점 전부가 보임) |
| left_elbow | **29.1도** | 4도 | **국면 문제 — 문법 밖** |
| right_shoulder | **10.0도** | 1도 | **국면 문제 + 표시 퇴화** (선 2개가 3도 차 평행) |

→ belle "뭘 말하는지 모르겠다"의 절반은 문법이 아니라 **그 순간에 잰 결함이 없어서**다.
기존 [[deduction-invisible-at-the-shown-moment]] 축과 같은 뿌리 — 갈림: (a) 델타가
보이는 순간으로 카드 이동 (b) 안 보이면 카드 접기/측정창 정직 캡션.

## 무접촉 확인

채점 산식·운영 코드 무접촉 (하네스는 quick 디렉터리, drawing 교체는 하네스 내 patch).
LLM 학습 재료 무접촉. advisory 카드 재현은 프레이밍만 어긋남(운영 배치가 region='arms'
그룹 unit — select_advisory_joints 입력이 doc 에 미저장) — 결함 ②(legacy 마커) 별건.

## 다음 (belle 판정 후)

1. 문법 채택 시 → `fault_zoom._draw_joint_angle` 에 이식 (운영 사이클: 테스트 + 기존
   승인 PASS 무회귀 + Pod 실검증 — **Pod 필요해지는 시점이 여기**).
2. 국면 문제 2카드 → 별건 착수 (순간 선정 or 정직 강등 — belle 갈림 선택 필요).
