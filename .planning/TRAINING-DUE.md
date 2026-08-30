# 재학습 시점 도달 — 2026-08-24 10:08

플라이휠이 자동 판정했다. **다음 세션에서 belle 에게 알릴 것.**

| 축 | 현재 | 임계 |
|---|---|---|
| 수집 영상 | 353 | 400 |
| 분석 원장 admit | 325 | 60 |

## 돌리는 법
1. belle 이 5090 이상 Pod 추가 (EU-RO-1, 기존 볼륨)
2. `bash backend/scripts/pod_doctor.sh` — 결손 복구
3. train_venv312 없으면: `TRAIN_VENV_ISOLATED=1 bash backend/training/sft/setup_train_venv.sh`
4. 전 사이클: preflight → label → assemble → train → gates → promote
   (래퍼 예시 = .planning/CONTINUE-2026-08-16.md)

## 직전 판(v29) 성적 — 이번에 넘어야 할 선
빈 골격 9/29 · faults 2 · 4동작 중 1동작만 짚음 · 게이트 FAIL
