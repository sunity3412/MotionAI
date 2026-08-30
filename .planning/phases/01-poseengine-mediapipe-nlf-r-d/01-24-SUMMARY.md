---
phase: 01-poseengine-mediapipe-nlf-r-d
plan: 24
status: closed-superseded
closed: 2026-08-31
closed_by: quick/260831-c3l-6-summary (미실행 꼬리 삼진 분류)
basis: "belle 2026-08-30 두 목적 — Mode1 잘 분석되는가 / Mode3 발전 확인되는가"
superseded_by: backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py (프로덕션 RTMW 경로)
---

# 01-24 SUMMARY (closure stub — 실행 없이 닫음)

## 원 플랜 목표

NLF + MediaPipe + plan 22 비선택 3D path 코드를 `backend/research/pose_engines/{nlf,mediapipe}/` 로 격리하고 (.samignore + ImportError 강제 테스트 2개), 운영 import 경로 0 을 만든다 (D-23).

## 처분

**사문 (closed-superseded).** 플랜이 만들려던 `backend/research/` 스캐폴딩은 생성된 적이 없고 (미실행), 그 상위 목적(RTMW 단일 백본 운영)은 프로덕션 경로 `sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py` 구현으로 달성됐다. 두 목적(Mode1/Mode3)에 지금 기여하는 잔여 작업 없음.

## 실측 (2026-08-31, 이 스텁 작성 시 직접 확인)

```
$ ls backend/research/pose_engines
ls: backend/research/pose_engines: No such file or directory   (EXIT=1)

$ ls backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py
backend/shared/python/sunity_shared/analysis/pose_engines/rtmw/rtmw_engine.py  19.4K   (EXIT=0)
```

## 관측과 해석

- 관측: 플랜 산출물의 뼈대인 `backend/research/` 디렉터리 자체가 부재 — 플랜은 착수된 적이 없다.
- 관측: RTMW 엔진은 research/ 가 아니라 프로덕션 경로에 실재하며, pipeline 이 소비 중이다 (01-25 스텁의 실측 참조).
- 주의: 이 스텁은 "NLF/MediaPipe 격리 완료" 주장이 **아니다** — 격리 작업 자체는 미실행이다 (관측: research/ 부재). 닫는 근거는 격리라는 수단이 아니라 상위 목적(RTMW 백본 운영)의 달성이다.
- 내 해석: NLF 라이선스 리스크는 격리(이동)가 아니라 백본 pivot(RTMW, memory rtmw-free-stack-pivot)으로 해소 경로가 바뀌었다. NLF 코드 잔존 여부의 라이선스 위생 점검이 필요해지면 별도 건으로 열 것 — 이 플랜의 스캐폴딩 설계는 재사용 가치가 없다.
