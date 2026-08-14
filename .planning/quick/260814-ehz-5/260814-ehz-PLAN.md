---
phase: quick-260814-ehz
quick_id: 260814-ehz
slug: discovery-sweep-5motions
date: 2026-08-14
status: planned
description: 발굴 일반화 스윕 — 승인 5동작(13 record) 전체에 wif 발굴 하네스를 일반화해 돌려 동작별 발굴/침묵 시트 생산. belle "pdshape 만?" 의 답 + "다른 영상들도 이런식으로 아주 잘 부탁해" 이행. 운영 코드 무접촉(backend diff 0), 사전 박제 장부(DISCOVERY-LEDGER) append — 승격 실적 누적
wave: 1
depends_on: []
type: execute
plan: 01
autonomous: true
requirements: [QUICK-260814-EHZ]
files_modified:
  - .planning/quick/260814-ehz-5/discover_sweep.py
  - .planning/quick/260814-ehz-5/evidence/
  - .planning/quick/260814-ehz-5/DISCOVERY-SHEET.md
  - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
  - .planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md
must_haves:
  truths:
    - "승인 5동작(elbow/kipup/pdshapefault/peterpan/powerspin) 13 record 전수에 스캔이 실행되고, record 마다 후보 수 또는 침묵 사유 분포(홀드 없음 / 짝 불성립 / claim 유도 불가 / 눈 기각)가 기계 산출로 시트에 박제된다 — 실행 로그가 침묵을 증명 (0건 동작 포함)"
    - "데이터 소스 실측 선행 게이트 — 동작별 로컬 replay 가능성(P35 doc/align + S3 영상 + 프레임/길이 fps 교차검증)을 열어 확인 후 박제. 불가 동작은 '로컬 불가 — Pod 필요' 로 정직 박제, 억지 성립 0"
    - "게이트 임계 = card_gates 모듈 상수 그대로 (ii0 확정값, 재튜닝 0 — 하네스에 임계 신설 0). 초 환산 = align 15fps 타임베이스, 9.0/18.0 라벨 분모 사용 0"
    - "눈 claim 은 관절별 하드코딩이 아니라 후보 순간의 트랙 대조 방향에서 유도 — user 각도 vs ref 각도의 track_claim 이분(card_gates 기존 상수)이 서로 반대일 때만 성립, 근거 수치 박제. 유도 불가(중간각/동일 claim/split 단일 마크 부재)는 사유 박제 정직 탈락"
    - "짝 탐색 = align 매핑 이웃 창 ±2s + 요소 정체성 제약 (wif Rule 2 — 전역 포즈 유사도 단독 금지, claim-대조 짝 병기)"
    - "기계 눈 실호출은 record 당 상한 16회 코드 강제 (gemini-3.5-flash temp 0) + 호출 로그/원장 리포 evidence 만. 눈 PASS 후보만 운영 헬퍼(app._run_gated_card_inherit) 그대로 렌더 — 새 문법 발명 0, 결정론 2회 md5"
    - "frames-before-numbers — 최종 후보 전건의 전신 스틸 + 카드 실물을 실행자 Read 육안 확인(VISUAL-REVIEW) 후에만 시트/장부 게재"
    - "동작별 추천(또는 '발굴 0 — 추천 없음' + 사유)이 belle 판정 전 커밋으로 사전 박제 — wif DISCOVERY-LEDGER.md 승격 실적 집계란에 행 append, belle 판정란 공란 (git 이력이 증인)"
    - "제약 준수 — backend/ diff 0 + git status --porcelain backend/ 빈 출력, S3 read-only(업로드 0), Firestore 쓰기 0(읽기만), Pod 무접촉, 채점 무접촉, 이모지 0, SUMMARY 에 LLM 학습 영향 필수 기재"
  artifacts:
    - path: ".planning/quick/260814-ehz-5/discover_sweep.py"
      provides: "일반화 발굴 하네스 — wif discover_knee.py 사본 확장 (원본 무수정): 동작/record 파라미터화, P35 data 직접 마운트(ufb sweep 패턴), claim 유도, 소스 게이트"
      contains: "card_gates"
    - path: ".planning/quick/260814-ehz-5/evidence/"
      provides: "동작별 {motion}/candidates.json + stills/ + eye_ledger/ + eye_calls.log + cards/ + render_verdict.json + VISUAL-REVIEW.md"
    - path: ".planning/quick/260814-ehz-5/DISCOVERY-SHEET.md"
      provides: "발굴/침묵 시트 — 동작별 1행 요약표(후보 수/눈 PASS/추천 좌표/침묵 사유 분포) + 후보별 절 + 승인 freeze 대조(재발견/신규 판별)"
    - path: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      provides: "승격 실적 장부 append — 동작별 추천 행(행 2~) + belle 판정란 공란"
    - path: "/Users/Shared/sunity-discovery-sweep-260814/"
      provides: "belle 확인 재료 — 한글 파일명 카드/전신 짝 스틸 + 안내.md (이미지 전달 정본 = 보드 embed, 보드 갱신은 오케스트레이터 몫)"
    - path: ".planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md"
      provides: "기계 판정 요약 + LLM 학습 영향 + 한계 박제 + 보드 재료 경로 + Self-Check"
  key_links:
    - from: ".planning/quick/260814-ehz-5/discover_sweep.py"
      to: "backend/shared/python/sunity_shared/analysis/card_gates.py"
      via: "hold_gate/pair_gate/track_claim/joint_angle/joint_limb/crit_joint/machine_eye/align_to_report 임포트 재사용 — 수정 0, 임계 재튜닝 0"
      pattern: "card_gates"
    - from: ".planning/quick/260814-ehz-5/discover_sweep.py"
      to: ".planning/quick/260811-ufb-freeze-only/verify_local.py"
      via: "SWEEP_JOBS 5동작 S3 키/motion_id 정본(:378-389) + 동작별 데이터 마운트(P35 doc/align 직접 로드 + ii0 poles.json + refmotion Firestore 읽기) 패턴 상속"
      pattern: "SWEEP_JOBS"
    - from: ".planning/quick/260814-ehz-5/discover_sweep.py"
      to: "backend/functions/pipeline/app.py"
      via: "_run_gated_card_inherit 주입 렌더 (wif render 스테이지 패턴 — S3/Firestore 스텁, 후보 순간 freeze 1건 report)"
      pattern: "_run_gated_card_inherit"
    - from: ".planning/quick/260814-ehz-5/DISCOVERY-SHEET.md"
      to: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      via: "동작별 추천 행 append — 시트가 재료, 장부가 실적 원장"
      pattern: "260814-ehz"
---

<objective>
belle 질문 "pdshape 에서만 한겨?" 의 답이자 지시 "다른 영상들도 이런식으로 아주 잘
부탁해" 의 이행. wif 사이클이 fresh pdshape doc 에서 성립시킨 발굴(좌표 무입력
스캔 → 게이트 3종 → 기계 눈 → 카드, belle 채택 = 승격 실적 1/1)을 승인 5동작
전체(13 record)로 일반화해 전수 실행하고, 동작별 발굴/침묵 시트를 생산한다.
발굴 0건인 동작은 실행 로그 + 탈락 사유 분포로 침묵을 증명한다 (조작 금지).

Purpose: 운영 자동화 전 관문 — 발굴이 pdshape 특수해가 아니라 일반 규율임을
전수 측정으로 보이거나, 침묵하는 동작의 사유를 정직하게 박제한다. 승격 경로 =
사전 박제 장부의 일치 실적 누적 (freeze-inherit-is-fallback-not-goal).

Output: discover_sweep.py(일반화 하네스) + 동작별 evidence + DISCOVERY-SHEET.md
+ DISCOVERY-LEDGER.md append(사전 박제) + /Users/Shared 한글 재료 + SUMMARY.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260813-wif-knee-discovery/260813-wif-SUMMARY.md
@.planning/quick/260813-wif-knee-discovery/discover_knee.py
@.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
@.planning/quick/260811-ufb-freeze-only/verify_local.py
@.planning/quick/260813-ivs-5/260813-ivs-SUMMARY.md
@backend/shared/python/sunity_shared/analysis/card_gates.py

배경 (locked — 재협상 금지):

- 스윕 대상 = ufb verify_local.SWEEP_JOBS 5동작 (S3 키/motion_id 정본, :378-389):
  elbow(ref-elbow-twist-sister) / kipup(ref-kip-up) / pdshapefault(ref-pdshape) /
  peterpan(ref-peter-pan) / powerspin(ref-power-spin).
  ★주의: pdshapefault(uploads/.../pdshapefault1785373695.mp4)는 wif 가 발굴한
  fresh pdshape doc(p34fresh1786628533)과 **다른 영상**이다 — kpo/ufb 대조 행은
  이 스윕에 적용되지 않고, 대조 행 = 각 동작의 승인 freeze(ii0 probes.log)다.
- 로컬 데이터 소스 (플래너 2026-08-14 실측 — 5동작 전부 로컬 replay 가능 확인):
  `.planning/phases/35-server-rendered-comparison-video/data/{motion}/doc.json +
  align.json` 전건 존재, align 키 = userKp/refKp/userScore/refScore/curveRefSec/
  fps 15.0/userSize/refSize (5동작 동일 스키마). 폴 = `.planning/quick/
  260811-ii0-card-gates-5/sweep_out/poles.json` 정본. 승인 freeze = 같은 디렉터리
  `probes.log`. 영상 = S3 read-only 다운로드 (ufb sweep 과 같은 키).
- record 인벤토리 (플래너 실측 — doc.json deductionBreakdown.records):
  elbow 4 (right_elbow/right_shoulder/left_hip/right_knee) · kipup 1 (split_angle)
  · pdshapefault 4 (left_elbow/right_elbow/left_shoulder/left_knee) · peterpan 1
  (left_shoulder) · powerspin 3 (leg_extension/split_angle/left_shoulder) = 13.
- 게이트 임계 = card_gates 모듈 상수 (HOLD_MAX_DPS 60 / PAIR_POSE_MAX 0.85 /
  POLE_DIFF_MAX 0.375 / HOLD_CONF_MIN 0.35 / EYE_BENT_MAX_DEG 100 /
  EYE_EXT_MIN_DEG 150) — ii0 확정값, 재튜닝 금지.
- 운영 eye 경로 (app.py:4533-4584 _eye_check) = user 측 track_claim 이분,
  중간각/좌표 부재 = 비구속(midrange). **발굴 규율은 더 엄격**: 양측 claim 대조
  유도가 성립한 후보만 눈 판정, 눈 PASS 만 렌더. split(crit_joint(split_angle/
  leg_extension)="split")은 cg.kp 단일 마크 좌표가 없어 눈 유도 불가 — 후보는
  스캔/짝 수치로 시트에 남기되 카드 렌더 없음, 사유 박제 (운영 helper 의 peak
  pass-through/비구속과의 대조를 시트에 명기).
- 이 사이클 = 판정 재료 생산만. 운영 코드 무접촉(backend/ diff 0), 채점 무접촉,
  S3 read-only, Pod 무접촉, Firestore 쓰기 0 (읽기 = refmotion 만). 발굴 채택
  반영은 belle 판정 후 di7 일반 경로로 별건.
- Gemini = card_gates.machine_eye 실호출만 (gemini-3.5-flash, temp 0, record 당
  상한 16회 코드 강제). 키 = SSM --profile sunity-motion (키 값 로그 금지).
- 이모지 금지. frames-before-numbers. 원자 커밋. 사전 박제는 belle 판정 전 커밋.
</context>

<tasks>

<task type="auto">
  <name>Task 1: 하네스 일반화 + 소스 게이트 + 5동작 13 record 전수 스캔/짝 + 육안</name>
  <files>.planning/quick/260814-ehz-5/discover_sweep.py, .planning/quick/260814-ehz-5/evidence/</files>
  <action>
    discover_sweep.py 를 ehz 디렉터리에 신설한다 — wif discover_knee.py 의 사본
    확장 (wif 원본 3파일 무수정: discover_knee.py / candidates.json / LEDGER).
    운영 코드는 임포트만 (card_gates / fault_zoom / compare_render / app 헬퍼 —
    수정 0, 임계 신설 0). 캐시 루트는 --cache-root CLI 인자 (실행 세션 scratchpad
    하위 — wif 처럼 구 세션 UUID 하드코딩 금지. scratchpad = 휘발, "보존" 주장
    금지, 보존 재료 = evidence/ 커밋분만).

    (1) 동작 파라미터화: SWEEP_JOBS 딕셔너리(ufb verify_local :378-389 원문 키
    5동작 — S3 user/ref 키 + motion_id)를 하네스 상수로 옮기고, 동작별 마운트는
    ufb sweep() 패턴 그대로 — doc/align = P35 data 디렉터리 직접 로드 (build_align
    재구축 불필요 — align.json 이 곧 판정 트랙, cg.align_to_report 로 변환),
    폴 = ii0 poles.json 을 render workdir 에 pole_{side}.json 으로 마운트,
    refmotion = firestore_admin.get_reference_motion 읽기 (쓰기 0), 영상 = S3
    read-only 다운로드, 30fps 스틸/눈 프레임 = compare_render.extract_frames.

    (2) 소스 게이트 (선행 — record 스캔 전에 동작별 판정): 동작마다 doc/align
    실물 존재 + align 스키마(userKp/refKp/curveRefSec) + 영상 다운로드 성공 +
    fps 교차검증(align frames / imageio duration 이 align fps 라벨과 0.5 이내,
    wif check_candidates 방식)을 확인해 candidates.json meta.sourceGate 에 박제.
    하나라도 실패하면 그 동작은 "로컬 불가 — Pod 필요" 로 정직 박제하고 스캔
    생략 (조작 금지). 초 환산은 전부 align 15fps 타임베이스 — 9.0/18.0 라벨
    분모 사용 0 (u8i 규율).

    (3) 전수 스캔: 동작별 doc 의 deductionBreakdown.records **전건**(13 record
    인벤토리 — context 표와 대조해 누락 0 확인)에 대해, record 의 crit_joint
    (cg.crit_joint — 동작명/ID 리터럴 분기 0)로 사용자 클립 전 구간 hold_gate
    스캔 → 1초 버킷 압축 (wif 선례 — 원시 run 은 rawRuns 전건 보존, 게이트
    임계 무변경, 표 granularity 만).

    (4) 짝 탐색 (wif Rule 2 일반화): 버킷 대표마다 align curveRefSec 매핑 이웃
    창 ±2s (시퀀스 순서 제약 — 전역 포즈 최소 금지) 안에서 2종 병기 —
    ① poseMin (중립: 양측 홀드 + pair_gate 통과 중 포즈거리 최소)
    ② claimContrast (발굴 짝: 버킷 pass 프레임 중 user claim 이 성립하는 대표를
      claim 값별로 뽑고, ref 는 **반대 claim** 트랙 한정 포즈 최소 — wif 의
      need_ext 하드코딩을 양방향 유도로 일반화. claim 이분 = cg.track_claim
      기존 상수, 신규 임계 0).
    claimContrast 가 성립한 후보만 발굴 후보다. 유도 불가(양측 중간각 / 동일
    claim / split 마크 좌표 부재)는 후보 행에 사유 문자열로 박제 — 정직 탈락.
    record 별 탈락 사유 분포(홀드 0 / 짝 불성립 / claim 유도 불가)를 집계해
    candidates.json 에 박제 (침묵 증명 재료).

    (5) 승인 freeze 대조 행: record 마다 ii0 probes.log 의 해당 rid 승인 정지
    (ut/rt)를 _gate_row 재계산으로 대조 박제 + 각 발굴 후보의 승인 freeze 와의
    거리(dUserSec, 버킷 포함 여부)를 기록 — 재발견(승인 순간 재생산)인지 신규
    순간인지 판별 재료. 재발견-only 는 검증 행 (wif cand04b 선례 — 중복 발명
    금지, 신규 카드 미채택).

    (6) 압축 + frames-before-numbers: record 당 claimContrast 성립 후보를 게이트
    수치 순으로 최대 4개 압축 (wif 눈 4후보 규율 — 전 프레임 눈 전수 금지).
    압축 후보 전건의 user/ref 전신 스틸을 evidence/{motion}/stills/ 에 덤프하고
    실행자가 Read 로 한 장씩 열어 육안 기록 (evidence/VISUAL-REVIEW.md — 후보
    id 전건, 접힘/신전·같은 국면 여부 관찰). 육안 탈락은 사유 명기로 표에 잔존.

    산출: evidence/{motion}/candidates.json (5동작 — 소스 게이트 + record 전수
    + 후보 + 대조 행 + 탈락 분포) + stills/ + VISUAL-REVIEW.md. --check 스테이지
    (wif check_candidates 확장): 5동작 후보표 존재 + record 인벤토리 커버 13/13
    + 압축 후보 stills 실물 + VISUAL-REVIEW 후보 id 전건 + fps 교차검증.

    금지: 임계 조정, 동작명 분기(마운트 좌표 제외), 승인 freeze 순간을 후보에서
    배제(스캔이 재발견하면 정직하게 표기), backend/ 수정.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python .planning/quick/260814-ehz-5/discover_sweep.py --check && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    5동작 candidates.json 전건 존재 (소스 게이트 판정 + 13 record 전수 스캔 수치
    + claimContrast/poseMin 짝 + 승인 freeze 대조 + 탈락 사유 분포), 압축 후보
    stills 실물 + VISUAL-REVIEW.md 육안 기록, backend/ diff 0 + porcelain 빈 출력.
  </done>
</task>

<task type="auto">
  <name>Task 2: 기계 눈 실판정 (record 당 상한 16회) + 눈 PASS 후보 렌더 (운영 헬퍼, 결정론 2회)</name>
  <files>.planning/quick/260814-ehz-5/evidence/</files>
  <action>
    (1) eye 스테이지: 육안 통과 압축 후보에 card_gates.machine_eye 실호출 —
    user 측 claim = 유도된 uClaim, ref 측 claim = 유도된 rClaim (wif 의 bent/
    extended 하드코딩 대신 Task 1 유도값 — 근거 각도 수치를 원장에 같이 박제).
    양측 match + limb 정합(cg.joint_limb 기대값, split 은 None 비차단이나 split
    후보는 눈 대상 아님 — Task 1 에서 이미 유도 불가 탈락)이어야 눈 PASS.
    상한 = **record 당 16회, (motion, rid) 키 계수기로 코드 강제** (wif 전역
    계수기의 record 키 일반화 — 프로세스 분리 시 각 프로세스 내 강제 + 로그
    합산 검증, wif 편차 4 선례). 호출마다 evidence/{motion}/eye_calls.log 1줄
    (record·후보·측·claim·판정·conf·record 누계) + 원장(마킹 크롭 PNG + JSON)
    evidence/{motion}/eye_ledger/ 적재. 같은 (측,프레임,관절,claim) 메모 재사용
    + 헬퍼 키 공간 등재 (wif _eye_call 패턴 — render 눈 실호출 중복 억제).
    눈 기각은 기각 그대로 박제 — 재시도/크롭 재조정 통과 조작 금지 (1후보 1판정).

    (2) render 스테이지: 눈 PASS 후보만 운영 헬퍼 그대로 렌더 — wif render()
    패턴 (app._run_gated_card_inherit 에 후보 순간 freeze 1건 report 주입,
    pairSrc="discovery", S3 스텁 로컬 라우팅 + firestore update 캡처 + 로그
    캡처), 동작별 마운트는 Task 1 자산 재사용. 확정 문법 그대로 — 새 문법 발명
    0, 스타일 파라미터 신설 0. 같은 입력 2회 재렌더 md5 비교 (2회차 눈 = 메모
    replay — 실호출 계수 불변), 결정론 결과를 evidence/{motion}/
    render_verdict.json 에 박제 (상이하면 상이 사실 그대로 — 채택 차단 사유
    아님, ufb 선례). 카드마다 전신 프레임 짝 스틸 동반 산출.

    (3) 산출 카드 전건을 Read 로 열어 육안 확인 (붕괴/오크롭/마크 이탈 관찰 —
    VISUAL-REVIEW.md 에 카드 절 append) 후에만 evidence/{motion}/cards/ 확정.
    눈 PASS 0건인 동작은 렌더 생략 — 침묵 그대로 (실행 로그가 증거).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && backend/.venv/bin/python -c "
import json, pathlib, re
ev = pathlib.Path('.planning/quick/260814-ehz-5/evidence')
fails = []
for m in ('elbow','kipup','pdshapefault','peterpan','powerspin'):
    lp = ev / m / 'eye_calls.log'
    if lp.exists():
        per = {}
        for ln in lp.read_text().splitlines():
            mm = re.search(r'CALL .* rid=(\S+)', ln)
            if mm:
                per[mm.group(1)] = per.get(mm.group(1), 0) + 1
        for rid, n in per.items():
            if n > 16:
                fails.append(f'{m}/{rid} eye calls {n} > 16')
    rv = ev / m / 'render_verdict.json'
    if rv.exists():
        data = json.loads(rv.read_text())
        for cid, c in (data.get('cards') or {}).items():
            if 'deterministic' not in c:
                fails.append(f'{m}/{cid} determinism 미기록')
print('EYE/RENDER GATE', 'FAIL: ' + '; '.join(fails) if fails else 'PASS')
raise SystemExit(1 if fails else 0)
" && grep -q "카드" .planning/quick/260814-ehz-5/evidence/VISUAL-REVIEW.md && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    눈 판정 원장 + 호출 로그 (record 당 16회 이하 기계 검증), 눈 PASS 후보의
    카드 + 전신 짝 스틸 실물 + 결정론 2회 기록, 카드 육안 확인 기록, 눈 기각/
    유도 불가 record 는 사유 박제. S3 쓰기 0, backend/ 무접촉 유지.
  </done>
</task>

<task type="auto">
  <name>Task 3: 발굴/침묵 시트 + DISCOVERY-LEDGER 사전 박제 append + 한글 재료 + SUMMARY</name>
  <files>.planning/quick/260814-ehz-5/DISCOVERY-SHEET.md, .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md, .planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md</files>
  <action>
    (1) DISCOVERY-SHEET.md — 서두에 기계 증명 요지 (데이터 좌표 표 5동작 · 소스
    게이트 결과 · 임계 출처 = ii0 확정값 재튜닝 0 · 초 환산 = align 15fps ·
    눈 호출 집계). 본문 = **동작별 1행 요약표**:
    | 동작 | record | 스캔 후보(버킷) | claim 유도 성립 | 눈 PASS | 재발견/신규 |
    추천 | 침묵 사유 분포 | — 13 record 전 행. 이어 동작별 절: 후보 카드/스틸
    상대 링크 + 게이트 수치 + 눈 판정 + 육안 관찰 + 승인 freeze 대조(재발견인지
    신규인지). 발굴 0건 동작/record 는 침묵 절 — 스캔 실행 수치(pass 프레임/
    버킷 수)와 탈락 사유 분포로 침묵을 증명. split record 는 "눈 유도 불가
    (단일 마크 좌표 부재) — 운영 helper 는 peak/비구속" 대조를 명기. 판정은
    belle 몫임을 서두에 명시. 이모지 0.

    (2) wif DISCOVERY-LEDGER.md 에 **append** (기존 내용 무수정 — 아래에 절
    추가): "## 발굴 일반화 스윕 (260814-ehz) — 사전 박제" 절. 동작별 추천 행 —
    발굴 성립 동작은 추천 후보 정확히 1안 + 근거 (게이트 수치·눈 판정·재발견/
    신규), 발굴 0건 동작은 "발굴 0 — 추천 없음" + 침묵 사유. 승격 실적 집계
    표에 행 append (행 2~ : 사이클 260814-ehz, 동작별 사전 추천, belle 판정란
    공란, 일치 여부 공란). DISCOVERY-SHEET.md 상대 링크. **belle 판정 전 커밋**
    (git 이력이 증인 — 판정란 선기입 금지).

    (3) /Users/Shared/sunity-discovery-sweep-260814/ — 한글 파일명 재료:
    동작별 눈 PASS 후보 카드 + 전신 짝 스틸 (예: "엘보트위스트_후보1_카드_
    NN.Ns.png", "엘보트위스트_후보1_전신짝_학생.jpg") + 요약표/안내.md (동작별
    1행 요약 + 열람 순서 — 각도 수치 캡션 금지, D-09 계열). 이미지 전달 정본 =
    보드 embed (보드 갱신은 오케스트레이터 몫) — SUMMARY 보드 재료 절에 파일
    절대경로 목록 명기.

    (4) 260814-ehz-SUMMARY.md — 기계 판정 한 줄 (동작별 후보/눈 PASS/추천 집계
    + 침묵 동작), 소스 게이트 결과, 한계 박제 (운영 방출 아님 — 반영은 belle
    판정 후 di7 일반 경로 별건 / split 눈 유도 불가 / 눈 기각분 / 재발견-only
    동작), LLM 학습 영향 필수 기재 (Gemini 호출 수 record 별 + 총계 + 비용
    추산 + 추론만·학습 전송 0 + 원장 = 리포 evidence 만·S3 쓰기 0 + Phase 22
    씨앗 후보), 다음 = belle 판정 대기 (LEDGER 기입).

    (5) 최종 게이트 + 원자 커밋: git status --porcelain backend/ 빈 출력 확인
    (git add 무력화 함정 차단) 후 .planning 한정 커밋 — Task 1/2 산출물 커밋이
    선행돼 있어야 하며, LEDGER append + SHEET 커밋이 사전 박제 커밋이다.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && grep -q "260814-ehz" .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md && grep -q "belle 판정" .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md && for m in elbow kipup pdshapefault peterpan powerspin; do grep -q "$m" .planning/quick/260814-ehz-5/DISCOVERY-SHEET.md || exit 1; done && grep -qi "LLM 학습" .planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md && ls /Users/Shared/sunity-discovery-sweep-260814/ | wc -l | awk '{exit !($1>=2)}' && test -z "$(git status --porcelain backend/)"</automated>
  </verify>
  <done>
    DISCOVERY-SHEET.md 에 5동작 전 행 + 침묵 증명, DISCOVERY-LEDGER.md 에 동작별
    사전 박제 행 + belle 판정란 공란 append (판정 전 커밋), /Users/Shared 한글
    재료 + 안내.md, SUMMARY 에 LLM 학습 영향 + 한계 박제 + 보드 재료 절대경로,
    backend/ diff 0 상태로 커밋 완료.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 하네스 → Gemini API | 관절 마킹 크롭 이미지 외부 전송 (추론만) |
| 하네스 → AWS (S3/SSM) | 자격증명 사용 — 읽기 한정이어야 함 |
| 하네스 → Firestore | refmotion 읽기만 — 쓰기 경로 스텁 필수 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ehz-01 | Information Disclosure | _ensure_gemini_key (SSM) | mitigate | 키 값 로그/파일 기록 0 (wif 패턴 — len 만 출력) |
| T-ehz-02 | Tampering | S3 | mitigate | download_file 만 사용, put_object 는 _S3Stub 로컬 라우팅 강제 (업로드 0) |
| T-ehz-03 | Tampering | Firestore | mitigate | update_analysis_fault_zoom 드라이버 내 캡처 스텁 (app 바인딩 포함 양쪽 교체 + finally 복원, wif 선례) |
| T-ehz-04 | Information Disclosure | Gemini 전송 | accept | 크롭 이미지 = 학습 재료 인물 관절부만, 추론 호출 한정 (T-kpo-01 기결론) — SUMMARY LLM 절 기재 |
| T-ehz-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 — 기존 backend/.venv 만 사용 |
</threat_model>

<verification>
- backend/ 무접촉: `git diff --stat backend/` 0줄 + `git status --porcelain backend/` 빈 출력 (전 태스크 공통 — rtk 래퍼 wc 판정 금지, wif 편차 3 선례)
- wif 원본 무수정: discover_knee.py / wif candidates.json 실물 diff 0 (LEDGER 는 append 만 — 기존 절 무변경)
- 게이트 임계 = card_gates 상수 그대로 (discover_sweep.py 에 신규 튜닝 상수 0)
- 초 환산 = align 15fps 단일 (하네스 내 9.0/18.0 라벨 분모 0)
- Gemini 호출 = machine_eye 만, record 당 16회 이하 (로그 기계 검증)
- 최종 후보/카드 실물 전수 육안 확인 기록 (frames-before-numbers)
- 사전 박제(LEDGER append + SHEET)가 belle 판정보다 먼저 커밋 (git 이력 증인)
- 소스 게이트: 로컬 불가 동작이 있으면 "Pod 필요" 정직 박제 — 억지 성립 0
</verification>

<success_criteria>
- 승인 5동작 13 record 전수에 스캔 실행 실적 존재 — 동작별 발굴 후보(게이트
  수치 + 눈 판정 + 카드) 또는 침묵 증명(실행 수치 + 탈락 사유 분포)이 시트에 박제
- 발굴 성립 후보는 눈 PASS + 확정 문법 카드 + 전신 짝 스틸 + 승인 freeze 대조
  (재발견/신규 판별)까지 belle 대조 재료로 존재
- 동작별 추천이 근거와 함께 belle 판정 전 git 이력으로 사전 박제 — wif
  DISCOVERY-LEDGER 승격 실적 장부에 행 append (판정란 공란)
- /Users/Shared 한글 재료 + SUMMARY (LLM 학습 영향 + 보드 재료 경로) 완비
- 운영 코드·채점·S3 업로드·Pod·Firestore 쓰기 전부 무접촉 (판정 재료 생산만)
</success_criteria>

<output>
Create `.planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md` when done
</output>
