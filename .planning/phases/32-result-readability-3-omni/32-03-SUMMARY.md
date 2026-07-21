---
phase: 32-result-readability-3-omni
plan: 03
subsystem: ops
tags: [runpod, pod-deploy, sweep, d23-gate, eas-update, ota, motion-alignment, fault-zoom, human-verify]

# Dependency graph
requires:
  - phase: 32-01
    provides: "D-16 trim_only 사다리 + D-20 crop parity + crop side px 로그 (백엔드 wave-1)"
  - phase: 32-02
    provides: "수동 슬라이더 + 대략/직접 맞춤 배지 + legacy 폴백 + 겹침 수리 (앱 wave-1)"
provides:
  - "프로덕션 Pod 6seluxc43awmqi 가동 + SSM v16/Lambda RUNPOD_ANALYZE_URL 재동기화 (구 Pod 사망 복구)"
  - "D-23 웨이브 게이트 첫 실행 실적 — 6동작 전수 스윕 점수 diff 0 + trim_only 방출 8건 + crop parity 18/18 (32-03-SWEEP.md)"
  - "wave-1 앱 OTA 발행 (production 2cf7b6af / preview 13f4cccd) + 1분 롤백 경로"
  - "32-GATE-DECISIONS.md — D-17 3건 확정 + D-23 매핑 + 실기기·폰트 피드백 (32-07/32-08/32-10/32-11/32-13 입력)"
affects: [32-08 (큐 밀도 1개/슬라이더 -방향 버그/적용중 표시), 32-10 (시트 문구·글자 잘림), 32-11 (비교 형태·자세 카드·정렬 시각 표시), 32-13 (스팟체크 — 자세 카드 품질 담보), 32-07 (타이포 하한), 32-09/32-12/32-14/32-15 (D-23 스윕 매핑)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-23 스윕 = phase25 harness 재사용 (SERIAL in-process _process, 기준선/배포후 2-run A/B, EVAL_OUT_DIR repo 밖)"
    - "Pod 재생성 표준 절차 실증 (bootstrap_wave5 + 서빙 패키지 + start_server + 스모크 + SSM/Lambda in-process 재동기화)"
    - "OTA 발행 전 롤백 group 선기록 + 시뮬 부팅 확인 + 빌드 경로 청결 검증"

key-files:
  created:
    - .planning/phases/32-result-readability-3-omni/32-03-SWEEP.md
    - .planning/phases/32-result-readability-3-omni/32-03-PROGRESS.md
    - .planning/phases/32-result-readability-3-omni/32-GATE-DECISIONS.md
  modified: []

key-decisions:
  - "기준선 = 배포 전 스윕 신규 생성 (커밋된 phase25/29 baseline은 26~31 코드 변화 혼입으로 wave-1 격리 불가)"
  - "스윕 PNG(인물 이미지)는 repo 미커밋 — S3 키·바이트 수치·육안 판정만 문서화 (PII-in-git 회피)"
  - "belle: 자세 비교 카드 존치 + phase 내 완성 / 비교 형태 1안 / 큐 밀도 구간당 1개 / D-23 매핑 수용"
  - "시각 확인 3건은 배치 UAT 이월 (belle 몰아서-점검 원칙) — 실시간 접점은 뒤 웨이브가 소비하는 결정만"

patterns-established:
  - "배포 시점 diff-0 증명 = 같은 Pod·같은 env·같은 기질(substrate)에서 pre/post 2-run — 다른 시기 기록과 비교 금지"
  - "relaxed crop parity 판정 = fault_zoom_crop 구조 로그 비율 + PNG 바이트/육안 이중 증거"

requirements-completed: [D-17, D-23, D-16, D-20]

# Metrics
duration: ~3h (Pod 셋업·스윕 2회 대기 포함, checkpoint 왕복 별도)
completed: 2026-07-21
---

# Phase 32 Plan 03: 실물 게이트 — Pod 배포 + 6동작 전수 스윕 + OTA + belle 실기기 확정 Summary

**죽은 프로덕션 Pod를 신규 6seluxc43awmqi(RTX 4090)로 복구·재동기화하고, wave-1 백엔드를 배포 전/후 6동작 전수 스윕(SERIAL)으로 실측해 점수 diff 0 + 저신뢰 trim_only 방출 8건 + crop parity 18/18을 증명(D-23 첫 실행), 앱 수리를 OTA 발행(롤백 준비)한 뒤 belle 실기기 리뷰로 D-17 3건(비교 형태 1안·자세 카드 존치+phase 내 완성·큐 밀도 구간당 1개)과 D-23 매핑을 확정했다**

## Performance

- **Duration:** ~3h 실행 (16:10~19:00 KST, 스윕 2회 각 ~70분 포함) + checkpoint 왕복
- **Completed:** 2026-07-21
- **Tasks:** 3/3 (Task 3 = blocking human-verify — belle 확정 회신으로 완결)

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | Pod 배포 + 6동작 전수 스윕 실측 (D-23 PASS) | `08b8d10` |
| 2 | wave-1 앱 OTA 발행 (production+preview, 롤백 준비) | `4a0c668` |
| 3 | D-17 3건 + D-23 매핑 적재 (32-GATE-DECISIONS.md) | `b76361d` |

## Accomplishments

### Task 1 — Pod 복구 + D-23 웨이브 게이트 첫 실행 (상세: `32-03-SWEEP.md`)

- **Pod 복구:** 구 `xps7co0m2njzpi` 사망(404) → belle 신규 생성 `6seluxc43awmqi` (RTX 4090 24GB, Network Volume 재사용). bootstrap → 서빙 패키지 → start_server(VETO env 박제 확인) → `/health` 200 → 스모크(무인증 401/토큰 422) → **SSM v16 + Lambda env 재동기화** (in-process patch, 4키 보존, Successful 확인).
- **6동작 전수 스윕 (기준선 36fdde9 vs 배포후 c45eb95, 각 13멤버 SERIAL):**

| motion | fault (기준→배포후) | correct (기준→배포후) | maTier 전환 (배포후) |
|---|---|---|---|
| power-spin | 55 → 55 | 100 → 100 | disabled→**trim_only** ×2 (anchors 40/50 보존) |
| peter-pan | 79 → 79 | 100 → 100 | fault: disabled→**trim_only** (30) / correct: rate_clamp 불변 |
| elbow-twist-sister | 66 → 66 | 100 → 100 | disabled→**trim_only** ×2 (82/100) |
| pdshape | 58 → 58 | 100 → 100 | disabled→**trim_only** ×2 (84/72) |
| kip-up | 80 → 80 | 100 → 100 | fault: disabled→**trim_only** (32) / correct: warped 불변 |
| climb | gate → gate (NotPole angle 10<25) | gate → gate | — |

- **점수·verdict·dimensionScores·criteria 전 멤버 diff 0** — 32-01 "채점 무접촉" 실측 증명. cold-rerun 결정론 PASS.
- **crop parity:** `fault_zoom_crop` 로그 18/18 이 user/ref side 비 0.8~1.25 내 (17건 1.00, 1건 1.07), **relaxed 재현 6건 전부 1.00**. 육안: ETS fault `zoom_left_knee.png` ref측 광각 → 배율 일치로 교정 실측 (PNG는 S3 보존, repo 미커밋 — 인물 이미지).
- **프로덕션 체인 E2E PASS:** S3 uploads → SQS → Lambda(신 URL) → Pod → done, score 100 + trim_only 라이브.

### Task 2 — OTA 발행 (상세: `32-03-PROGRESS.md`)

- production `2cf7b6af-e583-487a-bdb4-8c1cce4a51f6` / preview `13f4cccd-7c46-42a8-81c5-d3654c28b226` (runtime 1.0.0).
- 롤백 1분: `npx eas update:republish --group c153e0ec-...` (production) / `--group 853915f7-...` (preview) — 발행 전 선기록.
- 빌드 경로 청결(메인 리포·실 node_modules·typecheck clean) + Expo Go 시뮬 부팅 확인(온보딩 정상 렌더, 크래시 0).

### Task 3 — belle 실기기 리뷰 확정 (상세: `32-GATE-DECISIONS.md`)

- OTA 적용 실기기 검증: 슬라이더 작동 확인 (belle "작동도 잘 되는데").
- **D-17 3건:** ① 비교 형태 = 양옆 동시 + 탭 확대 + 가로 유지 ② 자세 비교 카드 = **존치 + phase 내 완성** (실체=결함 순간 프레임 쌍, 32-10 문구 + 32-13 스팟체크 담보, 숨김은 최후 폴백) ③ 큐 밀도 = 결함 구간당 1개.
- **D-23 매핑 확정** + 커버리지 갭 기록 (학생 fixture 6동작뿐 — 등록 10동작 중 4개 미커버, 해소는 별도 촬영·적재 작업).
- 실기기 피드백 3건(슬라이더 −방향 끊김 버그→32-08, 정렬 지점 시각 표시→32-11, "적용중입니다"→32-08/32-11) + 폰트 피드백 2건(로딩 화면 최소 폰트→32-07, 시트 글자 잘림→32-10) 적재.

## Deviations from Plan

**1. [운영 전제 변경] 구 Pod 사망 → 신규 Pod 재생성 경유 (checkpoint 왕복)**
- 이전 executor가 Task 1 (1)에서 전 Pod 404 확인 → decision checkpoint 반환 → belle이 신규 Pod 생성 → 본 executor가 재개. 플랜의 "미가동이면 멈추고 승인 요청" 경로 그대로 이행.

**2. [플랜 내 선택] 기준선 = 배포 전 스윕 신규 생성**
- 플랜 (2)의 대안("가장 최근 스윕 기록") 대신 신규 생성 경로 채택 — 커밋 baseline(phase25/29)은 phase 26~31 코드 변화가 섞여 wave-1 효과 격리 불가. 같은 Pod·같은 env 2-run A/B가 유일하게 유효.

**3. [환경 실측 기록] 스윕 2회는 CPU 기질로 실행 (A/B 유효성 무손상)**
- sweep 셸에 LD_LIBRARY_PATH 미설정 → RTMW CPU EP (기준선·배포후 동일 조건 → diff-0 비교 유효). 프로덕션 서버는 start_server.sh가 LD_LIBRARY_PATH 주입 → GPU 정상 (PID environ 실측 + E2E GPU 경로 score 100 일치).

**4. [Task 2 전제 보정] "32-02 시뮬 확인 완료" 전제가 실제론 이월 상태**
- 32-02는 worktree 제약으로 시뮬 픽셀 확인을 32-03에 이월했음(32-02-SUMMARY 명시). 보완: 메인 리포에서 Expo Go 시뮬 부팅 확인(크래시 0) 수행 후 발행, 결과 화면 픽셀 확인은 Task 3 실기기 + 배치 UAT 경로로 커버.

**5. [스코프 조정 — belle 결정] 실기기 시각 확인 3건 배치 UAT 이월**
- Task 3 how-to-verify 중 겹침 해소/배지/줌 배율 육안은 belle 몰아서-점검 원칙에 따라 HUMAN-UAT 적립으로 이월 (32-GATE-DECISIONS.md "배치 UAT 대기" 목록). 결정 3건+매핑은 즉시 확정 완료.

## Known Issues (후속 웨이브 라우팅 — 이 플랜에서 미수정)

- **슬라이더 − 방향 초반 끊김 버그** (음수 오프셋 0-클램프 seek 루프 의심) — 32-08 (wave 4, VideoCompare 차기 작업)에서 수정하도록 게이트 문서에 적재. belle/coordinator 라우팅 결정.
- fault_zoom 로그 `analysis_id=None` — 32-01 known follow-up (pipeline 배선 대기), SERIAL 스윕 판정에는 영향 0.

## Verification

- Pod `/health` 200 (배포 전·후) + 스모크 401/422 ✓
- 6동작 전수 스윕 표 존재 + 점수 diff 0 ✓ (`32-03-SWEEP.md`)
- 저신뢰 trim_only + anchors 보존 ≥1건 → **8건** ✓
- crop parity 육안 + 로그 수치 양쪽 기록 ✓
- `eas update:list` 최신 = 신규 발행 + 롤백 group 기록 ✓
- `grep -c "실물 게이트" 32-GATE-DECISIONS.md` = 2 (≥1) + "D-23 스윕 매핑" 섹션 존재 ✓

## Self-Check: PASSED

- FOUND: 32-03-SWEEP.md / 32-03-PROGRESS.md / 32-GATE-DECISIONS.md / 32-03-SUMMARY.md
- FOUND commits: 08b8d10 (T1), 4a0c668 (T2), b76361d (T3)
- 파일 삭제 0. STATE.md/ROADMAP.md 무접촉 (orchestrator 소관). push 보류 (coordinator 지시 — 다음 배포 시점 일괄).

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-21*
