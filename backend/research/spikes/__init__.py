"""R&D spike 격리 패키지 — 운영 코드(functions/, shared/)와 완전 분리.

이 패키지의 모든 코드는 Plan 01-07 이후 스파이크 전용. 운영 import 경로에
포함되지 않는다. D-06/D-07 NLF 격리 패턴 동일.

라이선스:
  MotionBERT: Apache 2.0 (https://github.com/Walter0807/MotionBERT/blob/main/LICENSE)
  HybrIK (백업): MIT (https://github.com/Jeff-sjtu/HybrIK)
  본 spike 코드: 운영 코드베이스 라이선스와 동일

포함 모듈:
  mediapipe_to_h36m17  — MP33 → H3.6M 17 joint 매핑 어댑터
  spike_motionbert     — MediaPipe 2D + MotionBERT 3D lift 스파이크 하네스
"""
