# 33-PHASE-GATE-EVIDENCE — 33-16 페이즈 게이트 실측 (2026-07-30)

> 33-16 Task 1 산출물. 6동작 시리얼 re-sweep + 재생성 crop/voice **전수** 열람 +
> fixture-less 대체 검증 + 미스→히트 캐시 실증 편승. Task 2(시뮬 전수)·Task 3(belle
> 확인 ②)는 본 문서 하단 섹션에 이어서 기록한다.

## 0. 실행 환경

- Pod: `i7o8b05j4olo2t` (RTX 4090 24GB, EU-RO, Network Volume 계보 유지 — 구
  s5jtnzs9q9oalf 대체, belle 직접 생성 = Task 0 운영 승인 충족)
- 코드: main `e4031d5` (33-12~15 포함). bootstrap_full.sh 로 Pod repo 갱신 확인
- 서버: start_server.sh 기동, 프록시 `/health` commitSha=`e4031d5…2250`,
  adaptersReady, recognizer=Gemini. SSM `/sunity/motion/runpod-analyze-url`(v22) +
  Lambda `sunity-motion-pilot-pipeline` env `RUNPOD_ANALYZE_URL` 둘 다
  `https://i7o8b05j4olo2t-8000.proxy.runpod.net/analyze` 로 갱신 (기존 env 4종 병합,
  AUTH_TOKEN 무변경). X-RunPod-Token 스모크: 무토큰 401 / 유토큰 422(인증 통과) PASS
- 스위프 레시피: 33-A4 §6-0 과 동일 (`run_sweep.py --reference-version
  phase33-cm3-run1 --tag cold`, SERIAL, RTMW_DETERMINISTIC=1, PR_INVERSION_ENABLED=1,
  recognizer=Fallback, vision-veto ON, EVAL_OUT_DIR=/workspace/eval_out_33_16)

### 0-1. Pod→S3 서울 저하 우회 (채점 무접촉)

07-29 12:00Z 발생한 Pod(EU-RO)→S3 서울 대용량 GET 저하가 **미회복** (재실측
13KB/s, 2MB/80s; 일반 EU 다운링크 1.5MB/s 정상 → S3 피어링 국한). PUT 은 244KB/s 로
가용. 우회:

- 영상 22개(fixture 12 + reference 10, 761MB)를 Mac(서울, 고속)에서 S3 다운로드 후
  scp 로 Pod `/workspace/_s3stage/<원본 key>` 에 스테이징 (병렬 7스트림, 무결성 =
  파일 수/용량 대조)
- eval 전용 래퍼(`/workspace/_33_16_sweep_wrapper.py` 등 3종)가
  `pipeline._s3.download_file` **만** 로컬 우선으로 프록시 — 스테이지 미보유 키는
  원본 S3 폴백, put_object/presign 등 나머지 메서드는 전부 원본 위임. **repo
  무변경·채점 경로 무접촉** (다운로드된 바이트는 원본과 동일 — S3 원본을 Mac 경유
  복사한 것). 효과: `stage=s3_download` 86,064ms(07-28 저하) → 102ms
- ⚠ belle 실기기 UAT 의 앱 분석은 Pod 가 S3 에서 직접 다운로드 — **저하 미회복 시
  다운로드 단계 hang 가능**. UAT 전 회복 재확인 필요 (§7 잔여 리스크)

## 1. 6-fixture 시리얼 re-sweep — 13/13 기대치 일치

runId=1785373695, uid=phase25eval. 기대 = 33-23 / 33-SCORING-REVERIFY /
33-A4-FIX-NOTE §6-1 (모두 동일 값).

| motion | fault | correct | 기대 (f/c) | 판정 |
|---|---:|---:|---|:---:|
| power-spin | 80 | 100 | 80/100 | PASS |
| peter-pan | 86 | 100 | 86/100 | PASS |
| elbow-twist-sister | 60 | 100 | 60/100 | PASS |
| pdshape | 60 | 100 | 60/100 | PASS |
| kip-up | 79 | 100 | 79/100 | PASS |
| climb | NotPoleMotionError angle 0<25 | 동 3<25 | 게이트 반려 | PASS |

- cold-rerun(pdshape correct 2회차, 별도 id): 100/100, activated criteria 동일,
  `selection_identical: true` — 결정론 재현
- 산출물: `/workspace/eval_out_33_16/phase25/phase25_breakdowns.json` +
  `phase25_sweep_report.json` (repo 밖)

### 1-1. assert_gates.py 결과 원문 + 처분

```
Phase 25 gates FAIL:
  - [kipup_upper] (c) upper-body record joint left_elbow not in pointed set [] — 감점 출처가 vision-짚기가 아님
  - [kipup_upper] (c) upper-body record joint left_shoulder not in pointed set [] — 감점 출처가 vision-짚기가 아님
  - [fault_no_regression] power-spin: fault overallScore=80 > phase24 baseline=60 (fault 변별 퇴행 방향)
  - [fault_no_regression] peter-pan: fault overallScore=86 > phase24 baseline=79 (fault 변별 퇴행 방향)
  - [fault_no_regression] pdshape: fault overallScore=60 > phase24 baseline=58 (fault 변별 퇴행 방향)
  · SKIPPED (sensitivity set deferred / warm report absent)
```

처분: **두 게이트 계열 모두 33-22 이전 설계 기준의 stale gate** 로 판정, 게이트
수정은 하지 않음 (D-20 채점 무접촉).

- `fault_no_regression` (fault ≤ phase24 baseline): belle 승인 33-22 감점상한
  재설계([[scoring-ipsf-deduction-cap-no-zero-pileup]])가 의도적으로 fault 점수를
  올린 것과 정면충돌 — power-spin 60→80 이 바로 그 승인 결과. 현행 정본 기대 =
  33-23 기대표이며 본 스위프는 그것과 13/13 일치 (§1)
- `kipup_upper (c)` (감점 출처=vision 짚기): 33-22 에서 감점 판정이 window 측정+tol
  로 이동, 짚기는 관측 전용 강등 (하니스 자체 출력에 "관측 지표(게이트 아님)" 명시)
- 선례: 33-22-SUMMARY 가 동일 계열("phase25 reuses phase24's gate")을 기록,
  33-A4-FIX-NOTE §6 도 assert_gates 아닌 기대표 대조로 판정. phase25 게이트 정비는
  별도 plan 사안으로 이월

## 2. 편승 ① — 진짜 미스→히트 캐시 동일성 실증 (33-A4 §6-4 이월분 종결)

`_a4_cachecheck2.py` 재실행 (신선 프로세스, production substrate,
RECOGNIZER_BACKEND=gemini, fixture power-spin fault = 실증 doc 동일 바이트
video_hash `574a774c…`). 절차: 현 캐시 doc 스냅샷(`_33_16_cache_snapshot_pre.json`)
→ 삭제(진짜 미스 전제) → run1/run2 → 원본 백업(`_a4_cache_backup_574a774c7d19.json`)
복구 (readback ok=True, model=gemini-3.1-pro, moments=4 — 지점 2·3 수리 플랜 증거
입력 보존).

- run1 = 진짜 미스: `lookup hit=false`, 신선 Gemini 호출 (recognizerMs **5367**)
- run2 = 히트: `lookup hit=true`, `_profile_from_cache` (recognizerMs **36**)
- **동일성**: hold_window 두 회차 `[0,36]` 동일, measuredValue 4건 소수점 동일
  (leg_extension 79.24 / left_shoulder 33.16 / left_hip 21.23 / right_hip 24.59),
  점수 60=60 → **신선↔캐시 경로 동일성 실증 완료** (hold_window fix 검증 체인의
  마지막 공백 종결). 산출: `/workspace/_a4_cachecheck2_out.json` (runId=1785375197)

## 3. 편승 ② — fixture-less 4종 self-comparison, e4031d5 재실행 (D-23)

어제 §6-2 는 crop fix 이전 코드(6137631)라 **오늘 코드로 재실행** (shadow
phase33-cm3-run1, runId=1785375638). 기대(33-S4): score 100 / maxDev ~0.003.

| motion | score | maxDev | hold_window (어제와 동일 여부) |
|---|---:|---:|---|
| ref-foxtop | 100 | 0.00270 | (207,243) 동일 |
| ref-foxtop-split | 100 | 0.00281 | (162,198) 동일 |
| ref-invert | 100 | 0.00277 | (36,72) 동일 |
| ref-sideway-spin | 100 | 0.00293 | (81,117) 동일 |

4/4 PASS — 침묵 스킵 0 (D-23). crop 재생성분은 §4 전수 열람에 포함.

## 4. 전수 열람 — crop PNG 26장 (D-19, 이미지 직접 열람)

S3 `results/phase25eval/<analysisId>/` 를 Mac 에 sync 하여 **26장 전부 열어봄**
(코드 통과 아님, 이미지 육안). 시간 칩·좌(학생)/우(기준) 패널 구성 정상.

### 4-1. criterion-keyed 카드 11장 (앱 감점 시트에 표시되는 전부) — 정상

| 멤버 | 카드 | 페어 국면 | 스케일 | 관절 정확 | 마커 |
|---|---|---|---|---|---|
| powerspinFault | left_elbow / left_shoulder / left_knee | 동일 | 동일(151px) | ✓ | 양측 |
| peterpanFault | left_shoulder / right_knee | 동일 | 동일 | ✓ | 양측 |
| pdshapeFault | left_elbow / right_shoulder | 동일 | 동일 | ✓ | 양측 |
| pdshapeFault | left_shoulder / right_elbow | 동일 | 동일 | ✓ | user 만 (ref_kind=relaxed → 생략 게이트) |
| kipupFault | left_shoulder | 동일 | 동일 | ✓ | 양측 |
| kipupFault | left_elbow | 동일 | 동일 | ✓ | ref 만 (user_kind=relaxed → 생략 게이트) |

- 마커 생략 전건이 파이프라인 로그의 `user_kind/ref_kind=relaxed` 와 1:1 대응 —
  IN-01 신뢰 강등 정책("마커는 민감 → relaxed anchor 생략")의 정상 작동. 모순 0건
- same-moment 증거: 카드별 user_frame/ref_rep_idx 가 로그에 박제 (예: pdshapeFault
  전 카드 user_frame=91 / ref_video_idx=56, 시간 칩 10.1s 공통)

### 4-2. advisory 카드 5장 — 정책대로 (user 마커만, 감점 시트 조인 금지 대상)

powerspinFault 2, pdshapeFault 1, peterpanFault 1, kipupFault 1. `tier=advisory`,
`criterion=None` → 앱 `matchZoomForDeductionRecord` 가 감점 시트 오매칭 금지. ref
마커는 advisory 정책상 미표시(관찰 확인), user 마커는 valid 시에만.

### 4-3. 성공 멤버 관심부위 카드 8장 + selfcomp 4장 — dormant (앱 미표시) + 관찰 2건

- pdshapeCorrect ↔ pdshapeColdCorrect 크롭 시각 동일 — 결정론이 crop 계층에서도 재현
- kipupCorrect left_hip: 점선 원 + 화살표(위치 안내 마커) 정상 렌더
- **관찰 A (cross-phase 페어 2건)**: elbowtwistsisterCorrect right_knee(좌 수직
  신전 vs 우 역립), refsidewayspin selfcomp left_hand(좌 lean-back vs 우 클라임).
  모두 `criterion=None` 카드 — ref 측이 기준 record 대표 프레임(ref_rep_idx)이라
  사용자 프레임과 국면이 어긋날 수 있음. **앱 노출 경로 없음** (감점 시트 =
  criterion join 전용, standalone 비교 카드는 31-08/31-11 숨김 확정 —
  `pickCompareFrames` 소비처 렌더 안 함). 향후 관심부위 카드를 표면화하려면
  same-moment 정합을 먼저 수리해야 함 — 표면화 plan 의 선행조건으로 기록
- **관찰 B (0-card 멤버 2건)**: powerspinCorrect (감점 0 + 관심부위 후보 없음 →
  카드 0, fzStatus=done), elbowtwistsisterFault (pose_match user_kp=0/2 → 전 카드
  fail-closed 억제, fzStatus=done — 33-21 elbow-twist HALT 보류와 정합). 앱은
  "사진 없이 수치·문구만" graceful 경로 — 표시 결함 아님. belle UAT 시 elbow-twist
  감점 상세에 사진이 없는 것은 이 fail-closed 가 원인

### 4-4. 틀리면 걸리는 장치 (D-18) 자답

페어 국면 불일치·잘못된 마커·스케일 불일치는 §4 열람에서 걸리도록 전 장을 열었고,
실제로 관찰 A 2건이 **걸렸다** (dormant 데이터라 belle 화면 무영향). 앱 노출분
(criterion 11 + advisory 5)에서는 잔존 결함 0.

## 5. 전수 재생 — coach mp3 22건 (D-19)

- 22/22 afplay 재생 완료 (5.30~5.95s, 손상 0)
- 텍스트 결정론 교차 검증: mp3 원문 = 감점 record 의 `cueLine` (Polly Seoyeon
  neural, `_synthesize_coach_audio_items` — 코드 확인) = phrasebook 33-13 목표-선행
  문구. criterion 이 같으면 mp3 길이가 멤버 불문 byte-수준 동일 (예: left_shoulder
  5.304s 전건) — 동일 텍스트→동일 합성의 방증
- 방향 어휘: phrasebook 문구는 기준-겹침 서술(예: power-spin left_shoulder "왼쪽
  팔과 몸통 사이 각을 기준 자세에 나란히 겹쳐본다는 느낌으로") — '천장' 모순 카피
  부재 확인. 절대방향('옆으로') 명시 여부는 belle 확인 ② 청취 문항으로 이월

## 6. 산출물 위치

- crop/mp3 로컬 사본: scratchpad `33_16_artifacts/<analysisId>/` (세션 임시)
- 스위프 로그: Pod `/workspace/_33_16_sweep.log`, selfcompare
  `/workspace/_33_16_selfcompare.log`, cachecheck `/workspace/_33_16_cachecheck.log`
- 우회 래퍼 3종 + 런처: Pod `/workspace/_33_16_*.{py,sh}` (eval 전용, repo 밖)

## 7. Task 2 — 시뮬레이터 실측 (iPhone 16 Pro, Metro dev, e4031d5 JS)

방법: Debug 빌드 + Metro(최신 JS), 스위프 doc 4건(powerspinFault/kipupFault/
elbowtwistsisterFault/pdshapeCorrect)을 시뮬 익명 uid 아래로 admin 복사해 실데이터
렌더. coachAudio 는 재서명 가드(H-02, uid-canonical exact 비교)가 타 uid key 를
정확히 거부(404)함을 실측 — 검증용으로 mp3 를 시뮬 uid 경로로 복사 + doc key 동기
후 200 확인 (가드 자체가 설계대로 작동한다는 실증. 스크린샷·녹화 = scratchpad
sim_*.png / sim_cue_*.mp4, 세션 임시).

### 7-1. PASS (렌더·크래시·레이아웃)

- 앱 기동/인트로/홈(분석 보유 상태: 평균 80점 + 최근 킵업 79 옥타곤)/기록 4건
  리스트/결과 화면 — 크래시 0, 상태바 겹침 0 (safe-area, 33-15 #1)
- 감점 카드: 헤드라인 무수치(D-09), 다음 행동 cueLine 무수치(D-16), 자세히 보기
  토글+앵커 스크롤(D-17), "아래에 다른 감점 항목 2개 더 보기" 어포던스(D-17)
- 확대비교 상세 시트(A-5): ② 항목 배지 + 관절 정확 제목, 내 영상|정은지 선수 라벨,
  양측 마커 crop(재스위프 재생성분과 동일 PNG), "사진 속 초는…" 캡션(33-15 초 표기),
  근거 박스 "기준 대비 27.4° 차이 (허용 20° 초과 7.4°) −8.9" + AI 추정 고지
- A-7 일러스트: power-spin PASS 에셋이 시트 슬롯에 렌더 (다리 라인 곧은 선 가이드 —
  라인 계열 키잉 정합), 캡션 = terminologyMap.angle 데이터 소비
- 33-13: 키포인트 기본 숨김(첫 진입 스켈레톤 0, 항목 그룹 마커만) → 토글 on 스켈레톤
  양 패널 등장 → **앱 재실행 후에도 영속** / 코치마크 2건 1회성 표시 후 재진입 미표시
- A-6 (kipupFault, 재생 중 자연 발화): 재생 3.1s 에서 **영상 정지 + 양 패널 dim +
  "음성 중 — 잠시 멈춤" pill + 왼쪽 팔꿈치 부위 강조 + 목표-선행 자막** 전 요소 발화
  (sim_cue_kipup.mp4 f_30~38), 음성 종료 후 강조·pill 해제 ✓
- 동작 비교 카드: 대략 맞춤 배지 + 미세조정 슬라이더 + 정렬됨 + 바 마커 ①②③(감점
  큐) + 가로로 크게 보기 — 전부 렌더

### 7-2. FAIL / 관찰 (OTA 차단 사유 — D-21)

- **[F-1] 음성 큐 종료 후 자동 재개 실패**: 강조·pill 해제까지는 되지만 영상이
  3.1s 정지 상태로 영구 유지 (재생 ▶ 복귀, CUE_PAUSE_MAX_MS=15s 안전 상한도 미발화
  — 2분+ 관찰). 33-13 #1 시퀀스의 "음성 종료 → 자동 재개" FAIL. 수동 재생은 가능.
- **[F-2] 큐 정지 중 기준(정은지) 영상 계속 재생**: 학생 정지 중 ref 는 4.0→7.8s
  진행 (drift-sync tick 이 rightPlayer 를 되살리는 것으로 추정) — "잠시 멈춤" pill
  과 모순되는 표면, 재개 시 좌우 desync.
- 관찰: powerspinFault 는 큐 창 3개가 전부 같은 순간(crop userFrame=2, 0.2s)에
  겹쳐 재생 중 전환이 원리적으로 없음 — 진입 시(정지 상태) 1회 발화 후 "정지 중
  발화=강조만" 설계 경로. 단일-순간 결함 doc 에서는 정지-재개 UX 가 자연 재생으로는
  나타나지 않는다 (belle UAT 해석 시 참고).
- Metro WARN 2건: expo-video `allowsFullscreen` deprecated (기능 영향 0, 후속 정리)

### 8. 잔여

- [ ] **F-1/F-2 수리** (별도 gap-closure — VideoCompare 큐 재개/드리프트 tick 상호작용)
      → 수리 후 시뮬 재확인부터 재개
- [ ] 시뮬 잔여 항목: 참고하세요 섹션 모순 카피(33-15 #3), 점수 내역 '관절 각도 참고'
      행(33-15 #2), elbow-twist 0-crop graceful 렌더, pdshapeCorrect 성공 화면 —
      F-1 수리 후 일괄
- [ ] OTA 발행 (33-12~15 일괄) — **F-1/F-2 수리 + 시뮬 재통과 전 금지** (D-21)
- [ ] Task 3: belle 확인 ② (5문항 + phase-32 3문항) — 접점 2/2
- [ ] 일러스트 미완 4동작 재시도 — 옵션, 미실행 (fail-closed 숨김 유지 중)
- ⚠ belle 실기기 분석 전 Pod→S3 회복 재확인 (§0-1 — 미회복 시 앱 분석 hang 위험)
