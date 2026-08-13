---
phase: quick-260813-u8i
plan: 01
subsystem: ml-display
tags: [fault_zoom, fps-label-chain, timestamp, pipeline, runpod]

requires:
  - phase: quick-260813-nh4
    provides: 승인 5동작 스윕 정본(sweep_verdict_port.json — survivors/dropped/md5/freezes) + Pod fresh p34fresh1786613939 (구 라벨 앵커 5.9s/18.6s)
  - phase: quick-260810-e4v
    provides: effective_fps/probe_effective_fps 실효 rate 인프라 (U1~U3) — 이 수리는 그 잔존 마지막 자리(카드 라벨)
provides:
  - fault_zoom 카드 초 라벨 ÷9.0 잔존 소멸 — keyword-only label_fps=(user,ref) 실효 fps 환산 (표시 전용, 채점·freeze·좌표 무접촉)
  - app.py 두 경로 배선 (게이트 = 기존 eff dict 재사용 / 스테이지 = probe fail-open, confirmed+advisory)
  - 승인 스윕 7게이트 기계 증명 (대조 런 md5 == nh4 정본 전건 = 변경원이 라벨뿐)
  - Pod 실증 p34fresh1786628533 — left_elbow 카드 5.9s→5.3s 앵커 적중 (기계+육안)
affects: [fault-zoom, 카드 표시 문법, 미세조정 라운드, freeze 타임베이스 의제]

tech-stack:
  added: []
  patterns: "라벨 게이트 = fail-open (카드를 죽이지 않음), 좌표 게이트(display_anchor)만 fail-closed — 층위 유지"

key-files:
  created:
    - backend/tests/test_fault_zoom_label_fps.py
    - .planning/quick/260813-u8i-fps-fps-pod/verify_label.py
    - .planning/quick/260813-u8i-fps-fps-pod/evidence/ (label_check.json, EYE-LABEL.md, sweep_cards/, pod/)
  modified:
    - backend/shared/python/sunity_shared/analysis/fault_zoom.py
    - backend/functions/pipeline/app.py
    - docs/contract.md (§11.8)
    - app/src/types/analysis.ts (주석만)

key-decisions:
  - "라벨 분모만 측별 교체 — u_video_sec/r_video_sec 변수 1개 (F-3 단일 산출: _stamp_time 픽셀과 userVideoSec/refVideoSec 필드 동시 수리)"
  - "라벨 fail-open (비유한/비양수 = frames_fps 폴백) — 라벨 때문에 카드를 죽이지 않는다"
  - "검증 게이트에 클립 끝 clamp 분기 추가 (peterpan 실측) — 허용치 완화가 아니라 운영 clamp 의 거울"

patterns-established:
  - "대조 런 shim 재현: 새 인자만 종전값으로 강제한 런의 md5 가 정본 전건 재현 = 변경원 단일성의 기계 증명"

requirements-completed: [QUICK-260813-U8I]

duration: 59min
completed: 2026-08-13
---

# Quick 260813-u8i: 카드 초 라벨 ÷9.0 잔존 수리 Summary

**fault_zoom 확대 카드의 초 라벨이 실효 fps 환산으로 교정되어 freeze 실초를 가리킨다 — Pod fresh 실측 left_elbow 5.9s→5.3s / left_hip 18.6s→16.7s, 라벨 외 픽셀·순간·좌표·채점 무변경은 대조 런 md5 전건 재현으로 기계 증명.**

## Performance

- **Duration:** 59min
- **Started:** 2026-08-13T13:08:26Z
- **Completed:** 2026-08-13T14:07:57Z
- **Tasks:** 3/3
- **Files modified:** 코드 4 (fault_zoom.py, app.py, contract.md, analysis.ts) + 테스트 1 + 검증/증거

## Accomplishments

- **÷9.0 라벨 사슬 소멸**: `build_fault_zoom_comparisons` keyword-only `label_fps=(user|None, ref|None)` — 초 라벨 환산 분모만 측별 교체. frames_fps(9.0)는 프레임 선택에만 잔류(무접촉). 미지정 = byte-동일 하위호환(신규 테스트 5건 + 기존 fault_zoom 96건 무접촉 PASS).
- **두 운영 경로 배선**: 게이트 경로(`_run_gated_card_inherit`)는 기존 eff dict 재사용(probe 신규 0), 스테이지 경로(`_render_fault_zoom`)는 측별 probe fail-open — confirmed/advisory 동일 전달, Mode1/Mode3 분기 0.
- **변경=라벨뿐 기계 증명**: label_fps 를 (9.0,9.0)으로 강제한 대조 런의 zoom 카드 md5 가 nh4 정본 **전건 재현**(md5Δ 0) + survivors/dropped/display_anchor 좌표 nh4 정본 동일 + 산식 5파일 diff 0 + pytest 59 failed 동일(4167 passed) + 수리 diff 추가 라인 동작명/ID 리터럴 0.
- **라벨 라운드트립 10카드 전건 PASS**: |신 라벨 − freeze 실초| ≤ 측별 1.5프레임/eff(≈0.15s) — 기대값 전부 nh4 정본 freezes 기계 유도(하드코딩 앵커 0). 구 라벨은 전건 ~1.11배 부풀어 있었다.
- **Pod 실증** (`p34fresh1786628533`, 347.4s): /health commitSha == push HEAD, 점수 60 유지, records atVideoSec 15자리 전건 동일, survivors/display_anchor 좌표 nh4 fresh 동일, doc userVideoSec ≈ freeze(Δ ≤ 0.066s), **left_elbow 카드 픽셀 5.9s→5.3s / left_hip 18.6s→16.7s 육안 확인**. 신 userVideoSec 이 record atVideoSec 와 완전 동치가 되어 F-3 정합이 필드 수준에서 성립.

## Task Commits

1. **Task 1 (TDD RED):** `1eccf9cd` test — label_fps 4행동 실패 테스트
2. **Task 1 (TDD GREEN):** `5e857582` feat — label_fps 배선 + contract/analysis.ts 서술 정정
3. **Task 2:** `ebfad42c` chore — verify_label.py 7게이트 전건 PASS + 증거
4. **Task 3:** `f9a8f3f0` chore — Pod 실증 (health/재분석 로그/회수 카드/판정)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 검증 게이트 결함] peterpan 클립 끝 clamp 경계 케이스**
- **Found during:** Task 2 (1차 게이트 런 FAIL 1건)
- **Issue:** 플랜 게이트 공식 |신 라벨 − freeze 실초| ≤ 1.5프레임/eff 이 peterpan user 측에서 0.322s 로 실패. 실측: freeze 초(6.444s)가 **클립 끝(62프레임/eff = 6.223s) 너머** — 운영 override 가 마지막 프레임(61)으로 clamp 하므로 라벨의 정답은 표시된 마지막 프레임의 실초(6.122s)다. rep9 보정 k 는 실측 전 동작 1.0 (플랜 가정 적중), 실패 원인은 보정이 아니라 clamp.
- **Fix:** verify_label.py 게이트 3 에 clamp 분기 추가 — `round(freeze x eff) >= video_n-1` 이고 신 라벨 == 마지막 프레임 실초일 때만 좁게 통과(허용치 완화 아님, 운영 공식의 거울). 운영 코드는 무접촉.
- **Files modified:** .planning/quick/260813-u8i-fps-fps-pod/verify_label.py
- **Commit:** `ebfad42c`

## 한계 박제 (이 수리가 다루지 않는 것)

- **peterpan freeze 초 자체가 클립 밖** (6.444s > 6.223s) — freeze 타임베이스 상류 의제(별건). 이 수리로 라벨은 실존하는 마지막 프레임의 실초(6.1s)를 가리키게 됐고, 종전 라벨(6.8s)은 6.2s 클립에 존재하지 않는 초였다.
- **체커 참고 1건 실증**: ref 측 이중 반올림으로 0.1s 표시에서 freeze 와 한 눈금 다를 수 있음 — 실측 최대 Δ 0.066s(left_hip ref)로 이번 코퍼스에선 눈금 이탈 없음. 기계 게이트(1.5프레임/eff)가 정본.
- freeze 장면 선정·마크 가독성·legs 크롭 등 미세조정 의제는 별건 유지 (STATE 대기열).
- 합성 비교 **영상** 렌더의 outSec 미세 변동(r01 15.83→15.67, mp3 길이 기지 비결정)은 이 수리 밖 — 카드/점수/records 는 전건 동일.
- 승인 스윕 display_anchor 좌표의 "nh4 정본 동일" 판정은 전이 사슬(대조 런 md5 == nh4 정본 + 본 런 좌표 == 대조 런 좌표)로 성립 — nh4 가 스윕 성공 좌표 라인을 따로 박제하지 않았기 때문 (Pod fresh 좌표는 nh4 POD-VERDICT 직접 대조로 4자리 전건 동일).

## LLM 학습 영향 (필수 기재)

- **로컬 검증**: Gemini 실호출 0 (machine_eye 스텁 12회 계수, 더미 키) — 학습 전송 0.
- **Pod 재분석 (운영 경로 허용분)**: generateContent 4건 = gemini-3.1-pro-preview x3(기술 인식기) + gemini-3.5-flash x1 (눈 machine_eye 2회 포함 사슬). **추론만, 학습 전송 0.** 눈 원장(마킹 크롭+판정) S3 additive 보존 entries=2 — Phase 22 플라이휠 씨앗 누적.

## Self-Check: PASSED

- backend/tests/test_fault_zoom_label_fps.py — FOUND
- .planning/quick/260813-u8i-fps-fps-pod/verify_label.py — FOUND
- evidence/label_check.json ("pass": true) — FOUND
- evidence/EYE-LABEL.md · evidence/pod/POD-VERDICT.md · pod/cards 2장 — FOUND
- 커밋 1eccf9cd / 5e857582 / ebfad42c / f9a8f3f0 — git log 존재, origin/main push 완료
