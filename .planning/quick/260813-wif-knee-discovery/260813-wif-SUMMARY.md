---
phase: quick-260813-wif
plan: 01
subsystem: ml-display
tags: [knee-discovery, card_gates, machine-eye, freeze-inherit-promotion, fault_zoom]

requires:
  - phase: quick-260811-ii0
    provides: 성립 게이트 3종 확정 임계 (hold<60도/초 3창 · pose<0.85 · poleDiff<0.375 · conf 0.35)
  - phase: quick-260811-kpo
    provides: card_gates 운영 모듈 + 왼무릎 인증 짝 (u 12.80/r 12.24, belle 육안 인증) + 눈 상한 16회/record
  - phase: quick-260811-ufb
    provides: freeze-only 구조 (r04 왼무릎 freeze u10.50 hold=moving 침묵) + verify_local --fetch 패턴
  - phase: quick-260813-u8i
    provides: label_fps 실효 fps 카드 라벨 + Pod 실증 doc p34fresh1786628533
provides:
  - 발굴 하네스 discover_knee.py (fetch/scan/eye/render/check — card_gates 임포트 재사용, 임계 재튜닝 0)
  - 후보표 candidates.json (18버킷 게이트 수치 전건 + kpo/ufb 대조 행 + 승인 짝 재생산 검증 행)
  - 기계 눈 PASS 후보 2안 카드 (cand13b = kpo 재발견 / cand02b = 신규) + 눈 원장 + 호출 로그
  - DISCOVERY-LEDGER.md 사전 박제 (추천 1안 = cand13b, belle 판정란 + 승격 실적 집계란 1행 신설)
affects: [freeze-inherit 승격 경로, 카드 발굴 사이클, 기계 눈 게이트]

tech-stack:
  added: []
  patterns: "발굴 짝 2종 병기 — poseMin(중립) + eyeEligible(kpo 의미론: user bent 대표 x ref extended 한정 포즈 최소). 포즈 유사도 단독은 결함을 지우는 방향 (nh4 교훈의 거울)"

key-files:
  created:
    - .planning/quick/260813-wif-knee-discovery/discover_knee.py
    - .planning/quick/260813-wif-knee-discovery/evidence/ (candidates.json, VISUAL-REVIEW.md, stills/ 64, eye_ledger/, eye_calls.log, cards/ 2, render_verdict.json)
    - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
    - /Users/Shared/sunity-knee-discovery-260813/ (한글 사본 9)
  modified: []

key-decisions:
  - "후보 단위 = 1초 버킷 (kpo 눈 지연 평가 클러스터 선례) — per-frame run 48건은 표 granularity 문제라 버킷 18건으로, 원시 run 은 rawRuns 로 전건 박제"
  - "짝 탐색 = align 매핑 이웃 창 ±2s (시퀀스 제약) + kpo 의미론 짝 병기 — 임계 신설 0, claim 이분은 card_gates 기존 상수"
  - "렌더 = 운영 헬퍼 그대로 (freeze 1건 주입) — build_fault_zoom_comparisons override/criterion_units/native_frame_at/label_fps 경로를 헬퍼가 소유, 새 문법 발명 0"
  - "추천 1안 = cand13b (kpo 인증 장면 재발견) — 요소 정체성 확실성이 마크 가독성(cand02b V drawn)보다 장부 1행에서 우선"

requirements-completed: [QUICK-260813-WIF]

duration: 약 40min (2026-08-13T14:31Z ~ 15:10Z경)
completed: 2026-08-13
---

# Quick 260813-wif: 왼무릎 신규 발굴 사이클 Summary

**기계 판정 한 줄**: 클립 전 구간 홀드 스캔(124/272프레임, 18버킷) + 요소 제약
짝 + 기계 눈 실판정으로 **왼무릎 결함 후보 2안이 성립** — cand13b(u12.87/r12.40)
= **kpo belle 인증 짝(12.80/12.24)의 자율 재발견** (좌표 입력 0, 눈 양측 leg
확정 conf 0.9/0.95), cand02b(u1.53/r2.33) = 신규 순간 (V 예각 vs 일자 대조
drawn, 눈 0.95/0.95). 눈 기각 2건(cand06b/cand10 — ref 마크 팔 겹침)은 기각
그대로 박제. 카드 2안 렌더 결정론 md5 동일. 추천 1안 = cand13b 사전 박제
(belle 판정 전 커밋).

## kpo 12.8/12.3 재발견 여부 (핵심 질문 답)

**재발견 성립.** 전 구간 스캔이 kpo 인증 순간(u 12.80)을 포함하는 홀드 버킷
(12.07~12.93s)을 독립적으로 찾았고, kpo 의미론 짝 탐색이 r 12.40 을 골랐다
(kpo r 12.24 의 +0.16s 이웃 — 같은 신전 홀드). 정확히 같은 인덱스가 아닌 이유도
기계 산출: **kpo 정확 좌표(r 12.24 = idx 184)는 재계산에서 기준측 hold=moving**
(이웃 프로브 전건 moving, candidates.json contrast.kpo.refHoldNeighbors) —
스캔은 게이트가 성립하는 같은 홀드의 이웃 프레임을 잡았다. 추가 검증 행:
스캔이 belle 라운드 5 "B" 채택 짝(u3.667/r2.4)도 독립 재생산 (cand04b).

## 산출물

- `discover_knee.py` — fetch(doc p34fresh1786628533 Firestore 실조회 + S3
  read-only + align replay 재수화)/scan/eye/render/check 스테이지. 운영 코드
  임포트만 (card_gates/fault_zoom/compare_align/app 헬퍼 — 수정 0).
- `evidence/candidates.json` — 18후보 게이트 수치 전건 (hold 양측 dps·pose·
  poleDiff·conf·실초·align 매핑·kpo 관계) + 대조 행 2 + 실효 fps 교차검증 meta.
- `evidence/stills/` 64장 + `VISUAL-REVIEW.md` — 전건 Read 육안 기록
  (frames-before-numbers). 최종 압축 4후보 -> 눈 PASS 2.
- `evidence/eye_ledger/` + `eye_calls.log` — 실호출 10회 (상한 16 코드 강제,
  eye 프로세스 8 + 렌더 헬퍼 프로세스 2, 각 프로세스 내 계수기 강제) + 마킹
  크롭/판정/conf 원장 전건.
- `evidence/cards/` 2안 + `render_verdict.json` — 운영 헬퍼 경유 확정 문법
  카드 (display_anchor align 단일 출처 로그 실물 + label_fps 실효 환산 라벨
  12.9s/1.5s + 결정론 2회 md5 동일).
- `DISCOVERY-LEDGER.md` — 사전 박제 (추천 cand13b + 근거), belle 판정 기입란,
  freeze 상속 승격 실적 집계란 **1번째 행** 신설.
- `/Users/Shared/sunity-knee-discovery-260813/` — 한글 사본 9파일.

## 보드 재료 (이미지 전달 = 보드 embed 정본, 파일 절대경로)

- /Users/Shared/sunity-knee-discovery-260813/후보1_왼무릎_카드_12.9s.png
- /Users/Shared/sunity-knee-discovery-260813/후보1_전신짝_학생_12.9s.jpg
- /Users/Shared/sunity-knee-discovery-260813/후보1_전신짝_기준_12.4s.jpg
- /Users/Shared/sunity-knee-discovery-260813/후보2_왼무릎_카드_1.5s.png
- /Users/Shared/sunity-knee-discovery-260813/후보2_전신짝_학생_1.5s.jpg
- /Users/Shared/sunity-knee-discovery-260813/후보2_전신짝_기준_2.3s.jpg
- /Users/Shared/sunity-knee-discovery-260813/대조_kpo인증짝_학생_12.8s.jpg
- /Users/Shared/sunity-knee-discovery-260813/대조_kpo인증짝_기준_12.3s.jpg
- /Users/Shared/sunity-knee-discovery-260813/발굴장부_사전박제.md

## 계획 대비 편차

1. **[표 granularity] 후보 단위 = 1초 버킷** — per-frame 연속 run 클러스터는
   48건(단일 프레임 run 다수)이라 전수 육안이 재료로 기능하지 못함. kpo 눈
   지연 평가의 1초 버킷 선례로 18건 압축, 원시 run 은 rawRuns 로 전건 보존.
   게이트 임계 무변경.
2. **[Rule 2 — 발굴 성립 조건] kpo 의미론 짝 병기** — 포즈거리 최소 단독 짝은
   결함(굽힘 차이)을 구조적으로 지운다 (실측: cand13 중립 짝이 **역대조** —
   user 신전 vs ref 접힘을 골랐다). kpo 생산 규칙("눈 확정 가능한 후보 중 포즈
   최소")을 짝 탐색에 명문화 — ref claim=extended 한정 포즈 최소. 신규 상수 0
   (claim 이분 = card_gates 기존 상수).
3. **[검증 게이트 대체] Task 1 verify 의 `rtk git diff` 라인 수 판정** — rtk
   래퍼가 빈 diff 에도 포맷 1줄을 내 `wc -l == 0` 판정이 구조적으로 불성립.
   원본 `git diff --stat backend/`(0줄) + porcelain 빈 출력으로 동일 의도 검증.
4. **[한계] 눈 상한 계수기는 프로세스 단위** — eye 스테이지(8회)와 render
   스테이지(2회)가 별도 프로세스라 계수기가 리셋됨. 각 프로세스 내 상한 강제는
   성립, 합산 10회 <= 16 로 record 상한도 실질 준수 (로그 전건 박제).

## 한계 박제 (운영 방출 아님 — 판정 재료만)

- **이 사이클은 카드 방출이 아니다.** 운영 doc/S3/Firestore 무변경 — 방출
  정책(freeze-only 구조에 발굴 경로를 언제/어떻게 붙일지)은 belle 판정 +
  승격 실적 누적 후 별건.
- **kpo 재계산 불일치**: kpo 정확 좌표(r 12.24)의 기준측 hold 가 재계산에서
  moving — kpo 당시 "양측 PASS" 박제와 불일치 (kpo 는 Pod 내 자체 align,
  이번은 P35 replay align — 트랙 등가는 nh4/u8i 로 증명됐으나 hold 경계
  민감성은 남음). 해석 없이 이웃 프로브 수치로 박제.
- **트랙 각도 vs 육안 불일치 (기준 12.27s)**: 육안 신전인데 트랙 142.3도
  (중간각) — keypoint 정밀도 한계 후보, 환각 게이트 의제와 같은 뿌리.
- **눈 기각 2건**: cand06b/cand10 의 ref 신전 순간은 트랙 left_knee 좌표가
  팔 겹침 영역에 있어 눈이 기각 — 마크-전위 구멍의 실측 재확인 (통과 조작 0).
- **cand13b 카드 V 미베이크**: user left_ankle conf 0.489 < 0.5 게이트 —
  링 대조만. 정직한 침묵이나 마크 가독성은 cand02b 대비 약함.
- **freeze 스캔 대조**: ufb freeze(u10.50)는 스캔에서도 hold=moving — ufb
  침묵 판정 재확인 (freeze-only 구조가 옳게 침묵했음의 실측).
- 채점 무접촉: backend/ diff 0 + porcelain 빈 출력 (산식 파일 포함 전부).
  S3 read-only (업로드 0, 카드/원장은 리포 evidence 만) · Pod 무접촉 ·
  Firestore 쓰기 0.

## LLM 학습 영향 (필수 기재)

- **Gemini 실호출 10회** (gemini-3.5-flash, temp 0, 기계 눈 판정만): eye
  스테이지 8 + 렌더 헬퍼 user 측 2. **추론만 — 학습 전송 0.** 개인정보는
  관절 마킹 크롭 이미지 외 미전송.
- 비용: 10회 x 크롭 1장 + 짧은 프롬프트 — kpo 실측 환산(40~46회 ≈ $0.01)
  기준 $0.01 미만.
- **원장 = 리포 evidence 만, S3 쓰기 0** (제약 준수): eye_ledger/ 크롭+판정
  8건 + 운영 헬퍼 원장(ledger.json + 크롭 1건). Phase 22 플라이휠 "홀드 자세
  시각 검증" 학습 씨앗 후보로 누적 — 학습 투입 여부는 별도 사이클 belle 결정.

## 다음 (belle 판정 대기)

DISCOVERY-LEDGER.md 판정 기입란 — 후보 1(cand13b)/후보 2(cand02b) 채택·반려·
보류 + 눈 기각분 처분. 판정 결과로 승격 실적 집계란 1행이 채워진다 (일치/불일치
그대로 — 사전 추천 = cand13b, 커밋 이력이 증인).

## Self-Check: PASSED

- discover_knee.py / candidates.json / VISUAL-REVIEW.md / stills 64 /
  eye_ledger 17파일 / eye_calls.log (12줄, 실호출 10) / cards 2 /
  render_verdict.json / DISCOVERY-LEDGER.md / /Users/Shared 사본 9 — 전건 존재.
- 커밋 08b82973 (Task 1) / d8c03514 (Task 2) — git log 존재. Task 3 커밋은
  본 SUMMARY 직후 (DISCOVERY-LEDGER 사전 박제).
- backend/ diff 0 + porcelain 빈 출력 재확인.
