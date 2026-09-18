---
quick_id: 260918-fyf
slug: rotbundle-other-motions
date: 2026-09-18
description: 어제 배포한 회전 묶음이 pdshape 외 동작 점수에 무엇을 했는지 측정
---

# 회전 묶음 배포 — pdshape 외 동작은 아직 아무도 안 쟀다

## 왜 급한가

2026-09-17 에 **운영에 배포**했다: `reference/_release.activeCandidate=rot180_v1`
+ `ROT180_INVERSION_ENABLED=1`. 확인한 것은 **pdshape 1편뿐**(60→87점).

기준 11편이 **전부 재추출**돼 활성화됐는데 **나머지 10편이 점수에 무슨 짓을 했는지
측정 0건**이다. 특히 **kip-up 은 위양성 재발 이력**이 있다
([[kipup-fp-RESOLVED-phase24A]] 가 2026-08-31 에 재발 관측됨 — RESOLVED 를 믿지 말 것).

배포된 것의 위험이므로 판정보다 먼저다.

## 무엇을 재는가 (범위를 정직하게 자른다)

**잴 수 있는 것 (Pod 불필요):**
학생 각도를 고정한 채 **기준만 배포 전/후로 바꿔** 채점 seam 을 다시 돌린다.
= "기준 교체가 각 동작 점수를 어디로 옮겼는가".

**못 재는 것 (Pod 필요 — 이번 범위 밖):**
학생 쪽도 `ROT180_INVERSION_ENABLED=1` 로 다시 뽑아야 완전한 배포 재현이다.
로컬에 있는 학생 doc 은 전부 회전 OFF 분석본이다. **이 한계를 산출물에 명시**하고,
기준 교체만으로 점수가 흔들리는 동작이 나오면 그때 Pod 을 띄울 근거로 쓴다.

## 재료 (전부 로컬, 실측 확인됨)

| | |
|---|---|
| 학생 doc 4편 | `260731-iis-.../docs_after/` — elbow-twist 63점 · **kip-up 79점** · pdshape 100점 · power-spin 60점 (angles 전부 있음) |
| 배포 후 기준 | Firestore 라이브 `reference/{id}` (= rot180_v1) |
| 배포 전 기준 | Firestore 백업 `reference/{id}/versions/pre_phase4` (11/11 존재) |
| 채점 경로 | `260917-hjy/evidence/rescore2.py` — 파이프라인 코드 직접 호출(재구현 0) |

## 작업

### Task 1 — 기준 2벌 pull (배포 전 / 배포 후)
Firestore 1회 읽기로 로컬 JSON 2벌. 이후 분석은 로컬 파일만 읽는다.
verify: 11/11 동작에 angles 존재 · 두 벌이 실제로 다른 동작이 몇 편인지 출력.

### Task 2 — 학생 4편 x 기준 2벌 채점
`rescore2.py` 의 호출 형태 그대로. 동작별 angle 차원 점수 + 초과 관절 + 초과합.
verify: pdshape 가 어제 실측(60→87 계열)과 같은 방향으로 움직이면 계기가 맞다.

### Task 3 — 판정
동작별 점수 이동표 + **나빠진 동작이 있는지**. kip-up 은 별도로 본다.
verify: 산출물이 실물(MEASUREMENTS.md)로 남고 belle 이 표만 보고 판단 가능.

## 함정

1. **계기부터 검증한다** — pdshape 로 어제 수치를 재현 못 하면 나머지 숫자를 믿지 말 것
   ([[dont-trust-subagent-gate-numbers]] 동형).
2. **Firestore 읽기 최소화** — 1회 pull 후 로컬만. 전수 스캔 금지.
3. **학생측 OFF 한계를 숨기지 말 것.** 이건 부분 측정이다.
4. 저장 각도는 **8관절**(`jointKeys`)이고 학생 doc 은 `anglesJointKeys` 순서가 다를 수 있다 —
   `rescore2.reshape` 가 재정렬한다. 직접 인덱싱 금지.
