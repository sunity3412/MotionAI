# 재학습 시점 도달 — 2026-09-14 10:07

> **정정 (2026-09-18, quick-260918-k06):** 아래 성적표·Pod·비용·학습률·파일럿 연결 5곳을 실측으로 고쳤다. 낡은 문장은 지우지 않고 취소선으로 남긴다.

플라이휠이 자동 판정했다. **다음 세션에서 belle 에게 알릴 것.**

| 축 | 현재 | 임계 |
|---|---|---|
| 수집 영상 | 513 | 400 |
| 분석 원장 admit | 334 | 60 |

## 돌리는 법
1. ~~belle 이 5090 이상 Pod 추가 (EU-RO-1, 기존 볼륨)~~ → **A100 PCIe 80GB ($1.39/hr)** Pod 추가 — EU-RO-1, 기존 볼륨은 유지. `run_sft.sh:169-190` 실측 주석: 4090 24GB OOM, **5090 32GB 도 OOM**. 완주한 v36·v38 은 전부 A100.
2. `bash backend/scripts/pod_doctor.sh` — 결손 복구
3. train_venv312 없으면: `TRAIN_VENV_ISOLATED=1 bash backend/training/sft/setup_train_venv.sh`
4. 전 사이클: preflight → label → assemble → train → gates → promote
   (래퍼 예시 = .planning/CONTINUE-2026-08-16.md)

## 학습률 — 돌리기 전에 반드시 정할 것
리포 기본 `SFT_LR=1e-5` (`run_sft.sh:180`) 는 08-26 실험(quick-260826-v34)에서 **"침묵의 진범"으로 실측된 값**이다.
`1e-4` 는 리포 본체가 아니라 `.planning/quick/260828-v34-targeted-data/v34_cycle.sh:45` 일회성 래퍼에만 있다.
문서대로 돌리면 침묵을 만든 설정으로 학습한다 — **LR 을 명시하고 시작할 것.**

## 비용 (한 사이클)
신규 라벨 142편 × 약 9분 ≈ 21시간 + 학습 2h49m + 게이트 1h → **약 $33~38** (A100 $1.39/hr 기준).
현재 RunPod 잔액 **$18.90** 으로는 한 사이클 불가 → **충전이 선행.**

## 직전 판 성적 — ~~v29~~ v38 (2026-08-28) — 이번에 넘어야 할 선
~~빈 골격 9/29 · faults 2 · 4동작 중 1동작만 짚음 · 게이트 FAIL~~ (v29 성적 — 낡음)

정정: `promotion_ledger.json` entries 5건(v28·v29·v35·v36·v38) 전부 `promoted=false`, `current: null` — **한 번도 승격된 적 없음**.
넘어야 할 선 = 게이트 통과 + 승격(hard 게이트 4+4). 게이트 통과 ≠ 승격.

## 파일럿 연결 — 없음
승격해도 **앱에 꽂을 배선이 0건** — 운영 코드에 `promotion_ledger`/`phase22_sft`/`SFT_MODEL` 참조 0. 22-08/09/10 은 PLAN 만 있고 미실행.
**이번 실증(2026-10 중순)에는 안 닿는다.** 재학습은 실증 뒤 우선순위로 belle 에게 물을 것.
