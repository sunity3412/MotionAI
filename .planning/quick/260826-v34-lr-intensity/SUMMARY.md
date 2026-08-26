# LR 강도 실험 결과 — 침묵 첫 돌파 (2026-08-26)

- 실행: pod vtve7bqks38dpu (A100 PCIe $1.39/hr), 산출 디렉터리 v36-20260826-020859,
  train 9584s(72스텝), 원장 7c78e08. NOT PROMOTED (gates 양 모드 FAIL).

## 예측 대조 (PREDICTION.md 박제 → 실측)

| # | 예측 | 실측 | 판정 |
|---|---|---|---|
| 1 | train loss 뚜렷이 하락 | 0.93~1.03 → 0.44~0.50 (eval 0.854→0.547) | 적중 |
| 2 | 결함 짚기 0/29 탈출 (≥1) | **9리포트·33결함, run1/run2 동일(결정론 재현)** | 적중 |
| 3 | 전체 PASS 는 절반 미만 확률 | FAIL 유지 | 적중 |
| 4 | 0 이면 강도 축 기각 | 해당 없음 (0 아님) | — |

## 핵심 판정

- **v32~v33 침묵의 진범 = 학습 강도(LR 1e-5 과소)**. 같은 데이터에서 LR 만 1e-4 로
  올리자 침묵이 깨졌다. 데이터 규모 가설(v33)은 이 축을 안 재고 있었던 것.
- **v33 형식 후퇴(exact 0.62)의 원인도 eye 혼입이 아니라 학습 부족** — 같은 데이터
  재실험에서 형식 축 완전 회복(parse·exact 1.0, cer 0). eye 혼입 가설 기각.

## 잔여 FAIL 사유 (다음 처방 재료)

1. eval18 3동작 fault 멤버 무결함: peter-pan · elbow-twist-sister · pdshape.
   **학습셋 실측과 정확히 겹침** — 결함 가르치는 행(총 123/275)이 split 43·jade 15·
   climb 5 로 편중, 침묵 3동작은 0~1행. 표적형 데이터 공백.
2. power-spin 변별 역전 (fault 2 ≤ correct 3).
3. svg_spec: 결함 리포트 9건 전부 target_angle_deg 비수치 → wellformed 0/9.

## 사이클 중 수리 (커밋)

- transformers 5.x 병합본 tokenizer_config(list형 extra_special_tokens)를 4.57 이
  못 읽음 → 베이스 토크나이저 4종 덮기로 해결 (LoRA 는 토크나이저 불변이라 안전).
- gates venv (구드라이버 pod): vllm 0.11.0 + transformers==4.57.1 + torch cu128
  (컨테이너 디스크 /root/gates_venv2 — 휘발). 볼륨 쿼터 재발(병합 중) → v35 산출물
  삭제로 해소 (belle 실행).
