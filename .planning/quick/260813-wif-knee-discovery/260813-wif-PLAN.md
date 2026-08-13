---
phase: quick-260813-wif
quick_id: 260813-wif
slug: knee-discovery
date: 2026-08-13
status: planned
description: 왼무릎 신규 발굴 사이클 — fresh 영상의 진짜 결함(왼무릎 다리 안 폄)이 영상 freeze 에 없어 카드 침묵인 케이스를 성립 게이트(홀드·짝정합·align 신뢰)로 발굴. 후보 홀드 순간 탐색 + 기계 눈 실판정 + 후보 카드 2~3안 렌더 + 내 판정 사전 박제(DISCOVERY-LEDGER) — belle 대조 재료 생산. 운영 코드 무접촉(backend diff 0), freeze 상속 승격 경로 실적 장부 첫 실전
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [QUICK-260813-WIF]
files_modified:
  - .planning/quick/260813-wif-knee-discovery/discover_knee.py
  - .planning/quick/260813-wif-knee-discovery/evidence/
  - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
  - .planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md
must_haves:
  truths:
    - "왼무릎 record 에 대해 클립 전 구간 홀드 후보 탐색이 card_gates 운영 이식본 순수 함수(hold_gate <60도/초 3창 Theil-Sen · pair_gate pose<0.85 + poleDiff<0.375 · 신뢰 하한 0.35)로 수행되고, 후보마다 게이트 수치가 기계 산출된다 — 임계 재튜닝 0 (ii0 SWEEP-REPORT §2 확정값 그대로)"
    - "기준측 짝 탐색은 포즈 유사도 단독이 아니라 시퀀스 순서·기술 요소 정체성 제약을 명시적으로 건다 (nh4 교훈: 포즈 유사도는 닮은 다른 요소를 고른다) — align 매핑 이웃 창 우선 + kpo 실적 짝(u 12.80s/r 12.3s, belle 육안 인증)과의 대조 행이 후보표에 존재한다"
    - "모든 초 환산은 실효 fps(probe_effective_fps) — 9.0/18.0 라벨 분모 사용 0 (fps 라벨 사슬 재발 금지, u8i 수리 준수)"
    - "frames-before-numbers: 후보 순간의 user/ref 전신 프레임 실물을 전수 Read 로 열어 육안 확인한 뒤에만 후보표·카드·장부에 올린다 — 수치만으로 방출 후보 선정 0"
    - "기계 눈 실판정 — card_gates.machine_eye(gemini-3.5-flash, 관절 마킹 크롭, 좌우 이름 금지, 2단 판정 상태+사지 종류)이 최종 후보의 user 접힘/ref 신전을 확정. 호출 수·비용 로그 + 상한 16회/record 준수 + 원장(크롭+claim+판정+conf) 적재 여부(리포 evidence 만, S3 쓰기 0) SUMMARY 명기"
    - "후보 카드 2~3안이 확정 문법 그대로 렌더된다 — 관절 위 V + 표시 좌표(마크 앵커·크롭 중심) = 해당 순간 align 단일 출처 + label_fps 실효 fps. 새 문법 발명 0, 후보 순간별 카드 실물 + 전신 프레임 짝 스틸 존재"
    - "사전 박제: DISCOVERY-LEDGER.md(xa1 JUDGMENT 형식)에 내 추천 정확히 1안 + 근거(게이트 수치·눈 판정·kpo 실적 짝과의 관계)가 belle 판정 전에 기록되고, belle 판정 기입란 + 일치/불일치 집계란(freeze 상속 승격 실적 장부)이 존재한다"
    - "제약 준수 — backend/ diff 0 + git status --porcelain backend/ 빈 출력(git add 무력화 함정 차단) · 채점 무접촉 · S3 read-only(업로드 0) · Pod 무접촉(로컬 캐시 우선, 없으면 --fetch 재수화 선례) · Firestore 쓰기 0 · 이모지 0 · SUMMARY 에 LLM 학습 영향 필수 기재"
  artifacts:
    - path: ".planning/quick/260813-wif-knee-discovery/discover_knee.py"
      provides: "발굴 하네스 — fetch(재수화)/scan(홀드 후보)/pair(기준 짝+제약)/eye(기계 눈)/render(카드) 스테이지, card_gates 순수 함수 임포트 재사용"
      contains: "card_gates"
    - path: ".planning/quick/260813-wif-knee-discovery/evidence/"
      provides: "candidates.json(후보표: 게이트 수치·초·kpo 대조 행) + stills/(전신 프레임 짝) + cards/(후보 카드 2~3안) + eye_ledger/(크롭+판정+conf) + eye_calls.log(호출 수·비용)"
    - path: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      provides: "사전 박제 장부 — 후보별 재료 + 내 추천 1안 + 근거 + belle 판정란 + 일치/불일치 집계란"
    - path: "/Users/Shared/sunity-knee-discovery-260813/"
      provides: "한글 파일명 사본(카드+전신 짝 스틸) — belle 열람용"
    - path: ".planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md"
      provides: "보드 게시 재료 + LLM 학습 영향 + 한계 박제 + Self-Check"
  key_links:
    - from: ".planning/quick/260813-wif-knee-discovery/discover_knee.py"
      to: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      via: "hold_gate/pair_gate/detect_pole_x/machine_eye/mark_crop/align_to_report/joint_angle 임포트 재사용 — 수정 0"
      pattern: "from sunity_shared.analysis import card_gates|card_gates\\."
    - from: ".planning/quick/260813-wif-knee-discovery/discover_knee.py"
      to: ".planning/quick/260811-ufb-freeze-only/verify_local.py"
      via: "--fetch 재수화 패턴 상속 (Firestore REST doc + S3 read-only 영상 → scratchpad 캐시)"
      pattern: "--fetch"
    - from: ".planning/quick/260813-wif-knee-discovery/discover_knee.py"
      to: "backend/shared/python/sunity_shared/analysis/fault_zoom.py"
      via: "build_fault_zoom_comparisons override + criterion_units + native_frame_at + label_fps(실효 fps) — bz5/kpo 실증 로컬 렌더 경로, 운영 무접촉"
      pattern: "build_fault_zoom_comparisons"
---

<objective>
belle fresh 영상(uid fvcNXzEqKjgqVxRPVSj1iwFnIpn2, doc p34fresh1786628533)의 진짜
결함 = 왼무릎(다리 안 폄)이 ufb freeze-only 구조에서 침묵(freeze 가 hold=moving 미달)인
케이스를, 시스템이 스스로 옳은 순간을 잡는 발굴 하네스로 회복 후보화한다:
클립 전 구간 홀드 후보 탐색 → 기준 짝(요소 정체성 제약) → align 신뢰 → 기계 눈
실판정 → 확정 문법 카드 2~3안 → 내 판정 사전 박제(DISCOVERY-LEDGER).

Purpose: freeze 상속은 내 실패로 강제된 바닥이지 목표가 아니다
(memory freeze-inherit-is-fallback-not-goal). 승격 경로 = 사전 박제 장부의 belle
일치 실적 — 이 사이클이 그 첫 실전. 판정 재료 생산만, 운영 방출 정책은 belle
판정·실적 후 별건.

Output: 발굴 하네스(discover_knee.py) + 후보표/스틸/카드/눈 원장(evidence/) +
DISCOVERY-LEDGER.md(사전 박제) + /Users/Shared/ 한글 사본 + SUMMARY(보드 재료).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260811-ii0-card-gates-5/260811-ii0-SUMMARY.md
@.planning/quick/260811-kpo-gate-wiring-3-pod/260811-kpo-SUMMARY.md
@.planning/quick/260811-ufb-freeze-only/260811-ufb-SUMMARY.md
@.planning/quick/260813-u8i-fps-fps-pod/260813-u8i-SUMMARY.md
@backend/shared/python/sunity_shared/analysis/card_gates.py
@.planning/quick/260811-ufb-freeze-only/verify_local.py
@.planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md

배경 (locked — 재협상 금지):
- 진짜 결함 = 왼무릎(다리 안 폄). 08-11 belle 육안 + 기계 눈 + 3중 게이트 생존으로
  확립된 정답. kpo 에서 재정박 카드(u 12.80s/r 12.3s 홀드 짝) belle 육안 인증 실적
  있음 → ufb 재정박 제거로 침묵.
- 이 사이클 = 판정 재료 생산만. 운영 코드 무접촉(backend/ diff 0), 채점 무접촉,
  S3 read-only, Pod 무접촉(로컬 캐시 우선 — Pod mddy6gsqmt24ud 는 손대지 않는다,
  죽어 있으면 verify_local --fetch 재수화 선례로 로컬 회수), Firestore 쓰기 0.
- Gemini = 기계 눈 실호출만 (gemini-3.5-flash, 상한 16회/record 기결론, 비용 로그).
  키 = SSM --profile sunity-motion (memory gemini-key-local-ssm-profile).
- 이모지 금지. frames-before-numbers(후보 실물 전수 육안 후에만 제시).
</context>

<tasks>

<task type="auto">
  <name>Task 1: 발굴 하네스 — 재수화 + 홀드 후보 탐색 + 기준 짝(요소 정체성 제약) + 육안 전수</name>
  <files>.planning/quick/260813-wif-knee-discovery/discover_knee.py, .planning/quick/260813-wif-knee-discovery/evidence/candidates.json, .planning/quick/260813-wif-knee-discovery/evidence/stills/</files>
  <action>
    discover_knee.py 를 wif 디렉터리에 신설한다. 운영 코드는 임포트만(수정 0) —
    backend/shared/python 을 sys.path 에 얹고 card_gates(hold_gate, pair_gate,
    detect_pole_x, align_to_report, joint_angle, torso_px_median, body_pole_dist)를
    재사용한다. 신규 튜닝 상수 0 — ii0 확정 임계(hold<60도/초 3창 최소, pose<0.85,
    poleDiff<0.375, conf>=0.35) 그대로.

    (1) fetch 스테이지: ufb verify_local.py 의 --fetch 패턴 상속 — Firestore REST 로
    doc p34fresh1786628533(uid fvcNXzEqKjgqVxRPVSj1iwFnIpn2) + 참조 모션 report 회수,
    S3 read-only 로 fresh 사용자 영상 + 기준 영상 다운로드 → 세션 scratchpad 캐시
    (/private/tmp/claude-501/.../scratchpad 아래). 로컬 캐시가 이미 있으면 재사용.
    scratchpad 는 휘발 — "보존" 주장 금지, 보존 재료는 wif evidence/ 커밋분만.

    (2) scan 스테이지: doc 에서 왼무릎 record(criterion 에 left_knee 귀속 —
    crit_joint 로 판별)를 특정하고, 사용자 클립 전 구간에서 hold_gate 후보 순간을
    스캔한다(왼무릎 각도 트랙, 3창 Theil-Sen). 초 환산은 전부 실효 fps
    (frame_extractor.probe_effective_fps 또는 캐시 프레임 수/길이 유도) — 9.0/18.0
    라벨 분모 사용 금지 (u8i 수리 준수, ii0 발견 4 재확인).

    (3) pair 스테이지: 홀드 생존 후보마다 기준측 짝을 찾되 nh4 교훈을 제약으로
    명문화한다 — 전역 포즈 유사도 최소 선택 금지. 탐색 창 = align(정렬) 매핑이
    가리키는 기준 시각의 이웃(±2s 급)을 1차로 하고, 같은 기술 요소 국면(역립 국면 —
    kpo 인증 짝과 같은 국면대)을 벗어나는 후보는 표에 사유와 함께 별도 표기.
    pair_gate(pose+poleDiff, 기준측 hold 포함 양측 홀드) + align 신뢰(관절 conf>=0.35
    양측) 통과분만 생존. 후보표에 kpo 실적 짝(u 12.80s/r 12.3s) 대조 행을 반드시
    포함 — 이번 스캔이 그 순간을 재발견하는지/다른 순간을 내는지가 핵심 재료.

    (4) frames-before-numbers: 생존 후보 전건의 user/ref 전신 프레임을
    evidence/stills/ 에 덤프하고 실행자가 Read 로 한 장씩 열어 육안 확인
    (접힘/신전·같은 국면 여부 관찰 기록). 육안 탈락 후보는 표에 남기되 사유 명기.
    최종 후보 2~4개로 압축, evidence/candidates.json 에 게이트 수치
    (hold dps 양측·pose·poleDiff·conf·실초·align 매핑) 전부 박제.

    금지: 동작명/분석 ID 리터럴 분기, 임계 조정, freeze 순간을 후보에서 배제하지
    말 것(freeze 가 스캔에서 살아나면 그것도 정직하게 표에 — ufb 판정과의 대조 재료).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260813-wif-knee-discovery/discover_knee.py --check-candidates && rtk git diff --stat backend/ | wc -l | grep -q '^ *0$' && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    candidates.json 에 홀드+짝+신뢰 게이트 수치가 후보 전건 기록(kpo 대조 행 포함,
    초 = 실효 fps 환산) + stills/ 전신 짝 실물 존재 + 실행자 육안 확인 기록.
    backend/ diff 0 + porcelain 빈 출력.
  </done>
</task>

<task type="auto">
  <name>Task 2: 기계 눈 실판정 + 후보 카드 2~3안 렌더(확정 문법 그대로)</name>
  <files>.planning/quick/260813-wif-knee-discovery/evidence/eye_ledger/, .planning/quick/260813-wif-knee-discovery/evidence/eye_calls.log, .planning/quick/260813-wif-knee-discovery/evidence/cards/</files>
  <action>
    (1) eye 스테이지: 최종 후보(2~4개)에 대해 card_gates.machine_eye 실호출 —
    gemini-3.5-flash, 관절 마킹 크롭(mark_crop), 좌우 이름 금지 관례, 2단 판정
    (상태 bent/extended + 사지 종류 arm/leg). user 측 claim=접힘 확정 + ref 측
    claim=신전 확정 + 양측 limb=leg 확정이어야 눈 PASS (kpo 왼무릎 인증과 동일
    의미론). Gemini 키 = SSM --profile sunity-motion 조회. 호출마다
    evidence/eye_calls.log 에 1줄(후보·측·판정·conf·누계) — 상한 16회/record 를
    코드로 강제(초과 시 중단하고 잔여 후보는 눈 미판정으로 표기). 원장
    (마킹 크롭 PNG + claim/판정/conf JSON)은 evidence/eye_ledger/ 에 적재.
    S3 eye/ 적재는 하지 않는다(S3 read-only 제약) — SUMMARY 에 "원장 = 리포
    evidence 만, S3 쓰기 0" 명기. 눈이 후보를 기각하면 그 기각도 재료 — 억지
    재시도·크롭 재조정으로 통과 조작 금지.

    (2) render 스테이지: 눈 PASS 후보 중 상위 2~3안을 확정 문법 그대로 카드 렌더 —
    fault_zoom.build_fault_zoom_comparisons 를 override(후보 순간 프레임 인덱스,
    kpo 의 ref_display_frame_index 역변환 선례로 양 패널 동일 실초 정합) +
    criterion_units + native_frame_at(원본 해상도 크롭) + label_fps(측별 실효 fps,
    u8i)로 호출한다. 마크 = 관절 위 V, 표시 좌표(마크 앵커·크롭 중심) = 해당 후보
    순간의 align 단일 출처(fxx/nh4 B 스펙과 같은 원리 — freeze 가 아니라 후보
    순간의 align 재계산). 새 문법 발명 금지 — 스타일 파라미터 신규 0.
    카드마다 전신 프레임 짝 스틸을 함께 산출(카드 크롭이 무엇을 잘랐는지 belle 이
    대조할 수 있게). 산출 전건을 Read 로 열어 육안 확인(붕괴/오크롭/마크 이탈 0
    확인) 후에만 evidence/cards/ 확정.

    (3) 렌더 결정론 1회 재실행 — 같은 입력 재렌더 md5 비교, 상이하면 상이 사실을
    박제(ufb 결정론 선례, 카드 채택 차단 사유는 아님).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && ls .planning/quick/260813-wif-knee-discovery/evidence/cards/*.png | wc -l | awk '{exit !($1>=2)}' && test -s .planning/quick/260813-wif-knee-discovery/evidence/eye_calls.log && awk 'END{exit !(NR<=16)}' .planning/quick/260813-wif-knee-discovery/evidence/eye_calls.log && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    후보 카드 2~3안 + 전신 짝 스틸 실물 존재(전수 육안 확인 기록), 눈 원장 +
    호출 로그(16회 이하) 존재, S3 쓰기 0, backend/ 무접촉 유지.
  </done>
</task>

<task type="auto">
  <name>Task 3: 사전 박제 장부 + 한글 사본 + SUMMARY(보드 재료)</name>
  <files>.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md, .planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md</files>
  <action>
    (1) DISCOVERY-LEDGER.md — xa1 JUDGMENT.md 형식 상속: 서두에 기계 증명 요지
    (데이터 좌표·게이트 임계 출처·초 환산 = 실효 fps), 후보별 절(카드/스틸 상대
    링크 + 게이트 수치 + 눈 판정 + 육안 관찰 + kpo 실적 짝과의 관계 — 재발견인지
    신규 순간인지). 마지막에 **내 추천 정확히 1안 + 근거** 를 belle 판정 전에
    기록(사전 박제). belle 판정 기입란(후보별 채택/반려/보류)과 일치/불일치
    집계란(사전 추천 vs belle 실제 — freeze 상속 승격 경로 실적 장부, 이번이
    1번째 행)을 비워서 만든다. 판정은 belle 몫 — 재료 페이지임을 서두에 명시.
    이모지 0.

    (2) /Users/Shared/sunity-knee-discovery-260813/ 에 카드+전신 짝 스틸 한글
    파일명 사본 복사 (예: "후보1_왼무릎_카드_12.8s.png", "후보1_전신짝.png") +
    DISCOVERY-LEDGER 사본. 이미지 전달은 보드 embed 만 확실하므로(memory) SUMMARY
    보드 재료 절에 파일 절대경로 목록을 정리한다.

    (3) 260813-wif-SUMMARY.md — 기계 판정 한 줄(후보 수·게이트 생존·눈 판정·추천),
    kpo 12.8/12.3s 재발견 여부, 한계 박제(운영 방출 아님 — 방출 정책은 belle
    판정·실적 후 별건 / freeze 스캔 결과와 ufb 판정 대조 / 눈 기각분), LLM 학습
    영향 필수 기재(호출 수·추론만·학습 전송 0·원장 = 리포 evidence 만 + Phase 22
    씨앗 후보), 다음 = belle 판정 대기(DISCOVERY-LEDGER 기입).

    (4) 최종 게이트: rtk git diff --stat backend/ 빈 출력 + git status --porcelain
    backend/ 빈 출력(git add 무력화 함정 차단) + 산출물 전건 존재 확인 후 wif
    디렉터리 커밋(.planning 만).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && grep -q "추천" .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md && grep -q "belle 판정" .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md && grep -qi "LLM 학습" .planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md && ls /Users/Shared/sunity-knee-discovery-260813/ | wc -l | awk '{exit !($1>=3)}' && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    DISCOVERY-LEDGER.md 에 추천 1안 사전 박제 + belle 판정란/집계란 존재,
    /Users/Shared/ 한글 사본 존재, SUMMARY 에 보드 재료 + LLM 학습 영향 + 한계
    박제, backend/ diff 0 상태로 커밋 완료.
  </done>
</task>

</tasks>

<verification>
- backend/ 무접촉: `rtk git diff --stat backend/` 빈 출력 + `git status --porcelain backend/` 빈 출력 (전 태스크 공통 게이트)
- 채점 무접촉: 채점 산식 파일 수정 0 (backend 무접촉에 포함되나 SUMMARY 에 명기)
- 게이트 수치 임계 = ii0 확정값 그대로 (하네스 diff 에 신규 튜닝 상수 0)
- 초 환산 = 실효 fps 단일 (9.0/18.0 라벨 분모 grep 0 — 하네스 내)
- Gemini 호출 로그 16회 이하 + 실호출은 machine_eye 만
- 후보/카드 실물 전수 육안 확인 기록 (frames-before-numbers)
- 사전 박제가 belle 판정보다 먼저 커밋되어 있음 (git 이력이 증인)
</verification>

<success_criteria>
- 왼무릎 결함에 대해 시스템이 스스로 잡은 홀드 후보 순간(게이트 3종 수치 완비) +
  기계 눈 확정 + 확정 문법 카드 2~3안 + 전신 짝 스틸이 belle 대조 재료로 존재
- kpo 실적 짝(12.8/12.3s)과의 관계가 후보표·장부에 명시 (재발견/신규 판별)
- 내 추천 1안이 근거와 함께 belle 판정 전 git 이력으로 박제 + 실적 집계란 신설
- 운영 코드·채점·S3·Pod·Firestore 전부 무접촉 (판정 재료 생산만)
</success_criteria>

<output>
Create `.planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md` when done
</output>
