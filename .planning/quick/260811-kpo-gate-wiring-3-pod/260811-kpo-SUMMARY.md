---
quick_id: 260811-kpo
slug: gate-wiring-3-pod
date: 2026-08-11
status: complete
commits:
  - 36fdb628  # feat: card_gates 운영 이식 + 확정 임계 + 기계 눈 2단 판정 + 테스트 8건
  - 84dedb47  # feat: compare_render 스테이지 뒤 성립 게이트 카드 상속 배선
  - e1b0df81  # fix: 실측 수리 3건 (절정 재배치 게이트/rep9 역변환/눈 지연 평가) + 눈 원장
  - 2112975a  # feat: 로컬 검증 사다리 + evidence (정답표/무회귀/눈 원장 46건)
duration: 약 2시간 (06:15~08:15 UTC, Pod 재분석 666s 포함)
---

# 성립 게이트 운영 배선 + Pod 실증 — Summary

> **기계 판정 한 줄**: Pod 재분석(p34fresh1786433865)에서 **왼골반 카드 소멸 +
> 왼무릎 카드 방출(홀드 짝 12.8s/12.3s, 접힘 vs 신전 육안 확인) + 왼팔꿈치
> 생존·귀속(attribution=pole_proximity)** — `card_gates verdict` 운영 로그 실물 +
> 점수 60 유지 + renderedCompare done + 승인 코퍼스 joint-scope 9/9 생존
> (ii0 스윕 수치 동일) + pytest 기준선 59 동일.

## 무엇을 배선했나

ii0 성립 게이트 3종(홀드/짝정합/기계눈)을 카드 생산 경로에 심었다:

- `backend/shared/python/sunity_shared/analysis/card_gates.py` — ii0 gates.py 운영
  이식. 확정 임계 박제 (hold<60도/초 3창 최소 Theil-Sen · pose<0.85 가중 모드 ·
  poleDiff<0.375 몸통 단위, 260811-ii0-SWEEP-REPORT §2 유도 — 재튜닝 금지 주석).
  machine_eye 는 ii0 미달 3 지정 수리 반영 **2단 판정**(상태 + 사지 종류) —
  마크-전위 구멍(kneepath 실측)을 arm↔leg 확정 상충으로 차단. 좌우 이름 금지 유지.
- `backend/functions/pipeline/app.py` — `_run_gated_card_inherit`:
  compare_render 리그 PASS·done 부착 뒤 freeze 를 게이트 판정, 생존 record 만
  |dev| 내림차순으로 `criterion_units_from_records(max_units=4)` 에 전달 (record
  순서 상한 구조 제거). 렌더 = bz5 실증 경로(`build_fault_zoom_comparisons`
  override + criterion_units + native_frame_at). S3 기존 키 규칙(zoom_) →
  `update_analysis_fault_zoom` 대체 부착, advisory 보존. 실패 전량 graceful —
  기존 fault_zoom 카드 자연 폴백 (blast radius 0). 채점 5파일 diff 0.
- `card_gates verdict analysis_id=... total=.. survivors=.. dropped=..
  reanchored=.. eye_calls=..` 로그 1줄 = 배선 실행 증거
  (wiring-claims-need-log-evidence).

## 검증 결과

| 항목 | 결과 | 증거 |
|---|---|---|
| 왼골반 카드 미방출 (운영) | **성립** — hold FAIL 111도/초(측정 짝) + 재정박 전 후보 눈 기각(마크 팔/몸통 전위) 예산 소진 | pod_verdict_log.txt, doc 카드 목록 |
| 왼무릎 카드 방출 | **성립** — 재정박 (u 12.80s 접힌 무릎 / r 12.3s 신전 무릎, 홀드 양측 + 같은 역립 국면 육안, 눈 양측 확정 leg) | pod_cards/zoom_..left_knee.png, 로컬 카드와 동일 짝 |
| 왼팔꿈치 생존 + 귀속 | **성립(Pod)** — freeze 상속 5.3s + attribution=pole_proximity doc 부착. 로컬 리플레이는 pole_diff 0.1498 vs 0.15 근소 미달로 미부착 (아래 유보) | doc 카드, evidence/post-judgment.md |
| 승인 무회귀 | **9/9** joint-scope hold+pair 생존 — ii0 스윕 표와 속도/거리 수치 동일. align-peak 3건 비구속 | evidence/approved_verdict.json |
| 채점 무접촉·재현성 | **점수 60 동일**, records 5건 recordId/criterion/atVideoSec/points 소수점까지 이전 fresh doc 과 동일 | Pod 로그 "분석 완료 666.1s — status=done score=60" |
| 영상 스테이지 무회귀 | renderedCompare **done** + freezes 5 | doc renderedCompare |
| pytest | **59 failed 기준선 동일** / 4149 passed (+8 = 신규 card_gates 테스트) | 로컬 실행 |
| Pod /health | commitSha 2112975a == HEAD, 정본 start_server.sh md5 일치 | Task 3 로그 |

## 계획 대비 편차 (전부 실측 근거 — 픽스처 curve-fit 0)

1. **[Rule 1] 절정 재배치 freeze 게이트** — PLAN (a) "align-peak 비구속"을 그대로
   적용하면 fresh 왼골반 freeze(align-peak 16.7s, 힙 legs_cue 표시 재배치)가
   hold+pair 를 통과해 카드가 샌다 (로컬 실측 — must_have 1 위반). 각도-주장
   record(angle_vs_reference__*)는 pairSrc 무관 **측정 짝(align pairs)** 으로
   게이트하고, 절정 축 criterion(split_angle/leg_extension)만 비구속으로 유지 —
   PLAN (d) "왼골반 기대 경로"와 ii0 fresh 판정(4.70s 이중 기각)이 근거.
   승인 align-peak 3건 비구속은 그대로 (무회귀 확인).
2. **[Rule 1] override 인덱스 rep9 역변환** — 실초×실효 rate 만으로 override 를
   만들면 기준측 라벨 오차(rep 실효 15 vs 라벨 18)로 표시가 1.33배 밀린다
   (실측: 5.13s 지정이 6.8s 를 그림). `ref_display_frame_index` 의 역변환으로
   양 패널 동일 실초 정합 (신규 상수 0).
3. **[Rule 2 — T-kpo-03 상한 완화, belle 확인 요망]** PLAN (d) "eye 호출 최종
   후보 ≤2회"는 user 트랙 광역 keypoint 전위(다수 순간에서 무릎/힙 마크가
   팔·몸통에 얹힘 — UNIFY §3 의 운영 확인) 아래에서 왼무릎을 원리적으로 죽인다
   (첫 후보 = 전위 순간 → 눈 기각 → record 사망, 로컬 실측). (d) 의 1차 의미론
   "풀 게이트(눈 포함) 통과 후보 중 포즈거리 최소"를 지키도록 눈을 포즈 순서로
   지연 평가 (클러스터 1초 버킷 선두만 + 캐시, record 당 상한 16). 실측 사용량:
   분석당 40~46회, gemini-3.5-flash ≈ $0.01 대 — 구독료 하한 내.
4. **[추가 지시 반영] 기계 눈 원장 보존** — (마킹 크롭 + claim + 판정 + conf)
   짝을 운영 경로에서 S3 additive 보존 (`results/{uid}/{aid}/eye/` — 카드 부착
   뒤 별도 try, 실패 비차단). 로컬 46건 + Pod 40건 evidence 커밋.

## 미달/유보 정직 박제

1. **로컬 리플레이의 left_elbow 귀속 미부착** — pair 폴거리 차 0.1498 vs
   POLE_MARGIN 0.15 (0.0002 차). 이웃 프레임 diff 0.007~0.244 요동 실측 — **순간
   측정은 프레임 지터에 불안정**. UNIFY 부록 D 창설 실측(diff 0.14 = 비대칭 성립)
   과 임계 선택이 상충. 임계 완화는 안 함(curve-fit 금지) — 창 기반(분위수) 귀속
   측정(_pole_prox_pair 지속-분리 선례)이 다음 수리 후보, belle 결정 항목.
   Pod 실분석에서는 성립(부착)됐으므로 이번 정답표는 충족.
2. **r01 right_elbow 로컬/Pod 판정 상이** — 로컬(P35 트랙 리플레이) 기각 vs Pod
   (자체 align) 재정박 생존. 원인 = align 반올림 오차 + Gemini 경계 판정. 정답표
   무구속 축이지만 재정박 경계의 환경 민감성 실측으로 박제 (Pod가 정본).
3. **카드 초 표기 ÷9.0 라벨 잔존** — 카드 표시 초(5.9s/14.2s)가 실초(5.3s/12.8s)
   와 어긋나는 기존 잔존 결함 (STATE 박제 "fault_zoom 카드 초 표기 아직 ÷9.0").
   이번 범위 밖 — 무접촉.
4. **재정박 탐색은 정지 화면 정합만 검증** — 눈이 확정 못 하는(중간각) 후보는
   자격 제외로 좁혔으나, 확정 가능한 후보 중 포즈 최소가 반드시 "belle 가 고른
   순간"은 아니다 (사전 예측 3.667/2.4 vs 실제 12.8/12.3 — 육안 판정으로 인증).
   방출 카드의 belle 육안 최종 판정은 다음 사이클.
5. Cerebras 코치 폴백 + Gemini 504 재시도 로그 (Pod 재분석 중) — 기존 graceful
   경로, 분석 무훼손. 이번 배선과 무관.

## LLM 학습 영향

**Gemini 호출은 추론(기계 눈 판정)뿐 — 학습 재료 전송 0.** 단, 판정 재료
**86건**(로컬 46 + Pod 40: 관절 마킹 크롭 PNG + claim/판정/conf 레코드)이
Phase 22 플라이휠 "홀드 자세 시각 검증" 학습 후보로 보존됨 —
위치: 리포 `evidence/eye_ledger/`(로컬)·`evidence/pod_eye_ledger/`(Pod) +
S3 `results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/p34fresh1786433865/eye/`.
학습 투입 여부·라벨링은 별도 사이클의 belle 결정 (추론-보존만, 과금 학습 0).

## 재료 좌표

- Pod: cv8poc707mqtxh (4090) — **그대로 둠** (스톱/터미네이트 안 함).
  서버 = commitSha 2112975a, 재분석 로그 = `/workspace/_kpo_reanalysis.log`.
- 새 doc: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / `p34fresh1786433865` (score 60).
- SSM runpod-analyze-url: Pod 동일·주소 불변 — 갱신 불필요 (PLAN 지시).
- 검증 드라이버: `verify_local.py` (--fetch/--run/--approved/--check).
- 판정 기록: `evidence/pre-judgment.md`(사전 박제) → `evidence/post-judgment.md`
  (실물 판정 + 오판 철회 3건 박제).

## Self-Check: PASSED

- 산출 파일 6종 존재 확인 (card_gates.py / test_card_gates.py / verify_local.py /
  SUMMARY / pod 카드 PNG / pod verdict 로그).
- 커밋 5개 (36fdb628 / 84dedb47 / e1b0df81 / 2112975a / 82d7eed0) 존재 + push 완료.
- 전 커밋 범위 파일 삭제 0. 채점 5파일 diff 0. Pod repo == HEAD (backend diff 0).
