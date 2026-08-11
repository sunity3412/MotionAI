---
quick_id: 260811-ii0
slug: card-gates-5
date: 2026-08-11
status: complete
commits:
  - 17612ab2 (Task 1: gates.py 3종 + rep162 환각 캘리브레이션)
  - 29906baf (Task 2: 승인 5동작 스윕 + 증거 + 임계 확정)
  - "(Task 3: 본 SUMMARY + SWEEP-REPORT 커밋)"
---

# 260811-ii0 요약 — 성립 게이트 + 5동작 스윕

## 기계 판정 한 줄

**승인 정지(joint-scope) 9/9 전건 생존 + pdshape 왼골반 탈락(홀드 111도/초 전환 +
기계 눈 불일치 이중 기각) + 왼무릎 방출 경로 = r03 상속 성립** (게이트 전건 PASS +
육안 동일 국면). 상세·한계는 `260811-ii0-SWEEP-REPORT.md`.

## 산출물

- `gates.py` — hold_gate(3창 Theil-Sen robust 각속도, fail-closed) ·
  pair_gate(가중 포즈거리 + 몸중심-폴 parity) · detect_pole_x(배경 중앙값 세로 에지) ·
  machine_eye(관절 마킹 크롭 Gemini 판정, 좌우 이름 금지). 채점·운영 코드 무접촉,
  동작명 분기 0.
- `sweep_gates.py` — pole/approved/fresh/eye 4 스테이지. 동작 = data glob,
  승인 정지 정본 = 렌더러 probe(`run_probes.sh`/`probes.log`, r01 오버라이드 포함).
- `sweep_out/*.json` — 튜닝 이력 3라운드(t0/t1/final) 전부 박제.
- `evidence/` 25장 — 전부 직접 열어 확인 (frames-before-numbers).

## 확정 임계 (승인 코퍼스 생존 조건 유도, 양측 대조군 실측)

| 게이트 | 임계 | 근거 |
|---|---|---|
| hold | < 60도/초 (3창 최소) | 승인 최대 53 (출발값 유지 — 구조 수리로 해결, 완화 불필요) |
| pose | < 0.85 | 승인 최대 0.74 / NEG 최소 0.96 사이 |
| poleDiff | < 0.375 몸통 | 승인 최대 0.31(차이가 결함인 belle 승인 표시) / NEG 0.44 사이 |

## 핵심 발견 (다음 사이클 입력)

1. **게이트 적용 범위 = record 선정 경로(src) 기준**: align-peak(벌림 절정) 정지는
   홀드/포즈 parity 축이 아님 (파워스핀 절정 428도/초 — 스핀 절정은 홀드가 아니다).
2. **홀드는 경계 순간이 정당** — 3창(과거/대칭/미래) 최소 판정. 전환은 3창 전부
   높아 판별력 유지 (왼골반 111 기각 실측).
3. **기계 눈 마크-전위 구멍 실측**: 환각 keypoint 마크가 다른 굽은 사지에 얹히면
   claim-일치가 뚫린다 → 신규 발굴 짝은 수치 게이트만으로 방출 불가, 프로세스 5번
   (방출 전 바닥 대조) 필수의 실측 근거. 상속 경로가 바닥이라 엉망 경로는 없음.
4. **doc keypointReport 타임베이스 라벨 오차 재확인** (라벨 18fps vs 실효 20.1) —
   게이트 판정 트랙은 align(재추출 정본) 고정. 운영 배선 시 보정 전제.

## 블로커

없음. Pod 불필요 (전부 로컬 + S3 + Gemini REST + Firestore REST).
Firestore gRPC 는 이 환경에서 DNS 차단 — REST 폴백으로 실조회 완료.

## LLM 학습 영향

없음 — Gemini 는 추론(판정) 호출 9회뿐, 학습 재료 무접촉.
