"""분석 알고리즘 코어 (모델 무관·순수). #7.

흐름(ml_CLAUDE.md): keypoints → 관절각/특징벡터(features) →
MotionDTW(motiondtw) → KISMAM 점수/Top-3(kismam) → 결과 조립(assemble).
무거운 모델(YOLO11/ViTPose-S)·ffmpeg·Cerebras 는 interfaces 의 프로토콜 뒤로
분리 — 어댑터 구현은 AWS/가중치 준비 후 후속(#7-follow).
"""
