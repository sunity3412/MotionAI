---
phase: quick-260816-p1x
plan: 01
subsystem: ml-discovery-harness
tags: [gemini-vision, pose-estimation, discovery-pipeline, card-gates, eyefirst-verification]

requires:
  - phase: quick-260814-ehz-5
    provides: poseMin 후보 데이터(candidates.json), discover_sweep.py mount/source_gate/frame 인프라
  - phase: quick-260813-wif-knee-discovery
    provides: DISCOVERY-LEDGER.md 승격 실적 장부(사전 박제 규율)
provides:
  - eyefirst_verify.py — 좌표/마크 없는 눈 제안 + 폴거리/관절각도/다리기울기 수치 검증 하네스
  - 5동작 좌표 품질 게이트(quality_gate.json)
  - elbow·peterpan poseMin 후보 20건의 눈 제안 + 수치 검증 + 3버킷 판정
  - 힙중심 폴거리 지표의 신체 기준점 한계 발견(belle_direction_probe.json)
affects: [260816-p1x-후속-반영-사이클, 폴거리-지표-재설계-검토]

tech-stack:
  added: []
  patterns:
    - "눈-우선 발굴 구조: 눈이 좌표 없이 후보 제안 → 수치가 promoted/rejected/unmeasurable 3버킷으로 검증(트랙-주장 구조의 대체)"
    - "belle_direction_probe.json: 정식 후보군 밖의 알려진 케이스를 별건으로 직접 검증하는 패턴"

key-files:
  created:
    - .planning/quick/260816-p1x-pole-distance-axis/eyefirst_verify.py
    - .planning/quick/260816-p1x-pole-distance-axis/DISCOVERY-SHEET.md
    - .planning/quick/260816-p1x-pole-distance-axis/evidence/quality_gate.json
    - .planning/quick/260816-p1x-pole-distance-axis/evidence/elbow/eyefirst_verdicts.json
    - .planning/quick/260816-p1x-pole-distance-axis/evidence/peterpan/eyefirst_verdicts.json
    - .planning/quick/260816-p1x-pole-distance-axis/evidence/peterpan/belle_direction_probe.json
    - .planning/quick/260816-p1x-pole-distance-axis/evidence/VISUAL-REVIEW.md
  modified:
    - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md

key-decisions:
  - "폴거리는 '주장하는 축'에서 '검증기'로 역할을 옮겼다 — 눈이 후보를 내고 card_gates.body_pole_dist/joint_angle/limb_tilt_deg(신규)가 검증"
  - "후보 소스 = ehz의 poseMin(claim 무관 최근접 짝) top-4/record — claimContrast 대신 재사용, 재스캔 0"
  - "quality_gate.json 모순율 절대값이 belle 사전 실측과 다름(셈 정의 차이: 프레임 단위 vs 다리별) — 순서(elbow≫peterpan/kipup)만 유지되면 진행하도록 사전 승인됨, 그대로 진행"

requirements-completed: [QUICK-260816-P1X]

duration: ~40min
completed: 2026-08-16
---

# Quick 260816-p1x: 축 반전 눈-우선 검증 Summary

**눈이 좌표 없이 짝 스틸만 보고 후보를 내고, 폴거리(힙중심)/관절각도/다리기울기
수치가 그 후보를 promoted/rejected/unmeasurable 로 검증하는 하네스 —
elbow·peterpan poseMin 후보 20건 실행, promoted 8·rejected 8·unmeasurable 39,
힙중심 폴거리 지표가 belle 의 발목 기준 실측과 반대 방향을 낼 수 있다는 한계
발견.**

## Performance

- **Duration:** 약 40분
- **Tasks:** 3/3 완료
- **Files modified (repo):** 31 (신규 29 + LEDGER append 1 + SHEET 1)
- **Gemini 호출:** 22회(스모크 2 + 전량 20) — gemini-3.5-flash, temperature 0

## Accomplishments

- **축 반전 구조 실증**: 좌표가 깨진 동작(elbow, 해부학 모순 12.7%/23.5%)에서도
  눈-우선 구조는 무력해지지 않았다 — promoted 8건이 나왔고, 그중 r00/cand04
  는 눈이 낸 3개 서술(관절각2 + 폴거리1) **전부**가 수치와 일치했다.
- **검증기가 양방향으로 작동함을 확인**: 같은 elbow 동작에서 rejected 6건도
  나왔다 — 눈이 항상 옳은 게 아니라, 검증기가 실제로 눈의 오답을 걸러낸다.
- **peterpan 발굴 0건을 정직하게 기재**: 눈 제안 4건 중 승격 0, tie-band
  unmeasurable 10 · rejected 2. 억지로 승격시키지 않았다.
- **힙 vs 발목 폴거리 지표 불일치 발견**: belle 가 실측한 정확한 오답 프레임
  (align 2.27s)은 이번 top-4 poseMin 후보에 없었지만(순위 5위), 별건 프로브로
  직접 검증한 결과 — plan 이 지정한 힙중심 지표(`card_gates.body_pole_dist`)
  는 그 오답을 못 잡고 오히려 promoted 로 확인해버렸다. 발목 기준으로 계산
  하면 belle 방향과 일치한다. **폴거리 지표의 신체 기준점 선택이 판정 결과를
  바꾼다**는 정직한 한계 발견 — 다음 사이클 의제 후보로 시트/LEDGER에 명기.

## Task Commits

1. **Task 1: 좌표 품질 게이트 + hip→ankle 기울기 + 눈-우선 제안 구현 + 스모크 2건** - `b939f5c9` (feat)
2. **Task 2: elbow·peterpan 전량 실행 — 후보 20건 눈 제안 + 수치 검증 3버킷** - `702dd788` (feat)
3. **Task 3: DISCOVERY-SHEET + LEDGER 사전 박제 + /Users/Shared + SUMMARY** - 본 커밋(문서만, 실행 에이전트는 커밋하지 않음 — 오케스트레이터가 별도 처리)

## Files Created/Modified

- `eyefirst_verify.py` - contradiction_rate/lowconf_rate(align.json 전용, 동작명 분기 0) + limb_tilt_deg(hip→ankle atan2) + eye_propose(Gemini urllib 직접호출) + select_candidates(poseMin top-4) + compose_pair_still(무마크 가로결합) + verify_difference(3버킷 분류) + run_smoke/run_candidates CLI
- `evidence/quality_gate.json` - 5동작 좌표 품질(모순율/저신뢰율/라벨)
- `evidence/smoke/{elbow,peterpan}.json` - Task1 스모크 원응답(기존 ehz 스틸 재사용)
- `evidence/{elbow,peterpan}/eyefirst_verdicts.json` - 후보 20건 눈 제안 원응답 + 수치 검증 + 버킷
- `evidence/{elbow,peterpan}/stills/*.jpg` - 짝 스틸 20장(무마크, 무축소 1080p 가로결합)
- `evidence/peterpan/belle_direction_probe.json` - belle 실측 프레임 별건 프로브(힙 vs 발목 지표 불일치)
- `evidence/VISUAL-REVIEW.md` - 20건 전건 실행자 육안 확인(frames-before-numbers)
- `DISCOVERY-SHEET.md` - belle 판정 재료(품질표 + 동작별 전 후보 표 + 한계)
- `260813-wif-knee-discovery/DISCOVERY-LEDGER.md` - "축 반전 눈-우선 검증(260816-p1x)" 절 append(사전 박제, 판정란 공란, 승격 실적 집계 행 7·8 추가)

## Decisions Made

- 폴거리를 "주장하는 축"에서 "검증기"로 역할 전환(belle 08-16 승인 구조).
- 후보 소스를 claimContrast 에서 poseMin(claim 무관 최근접)으로 전환 — 재스캔 0.
- quality_gate.json 의 모순율 절대값이 belle 사전 실측과 다르게 나온 것을
  숨기지 않고 정의 차이(프레임 단위 vs 다리별 단위)로 명시한 뒤, 순서가
  유지된다는 사전 승인 조건에 따라 그대로 진행.
- tie-band(POLE_TIE_TORSO=0.15/ANGLE_TIE_DEG=10/TILT_TIE_DEG=8)를 이 하네스의
  신규 하네스 한정자로 신설 — 기존 card_gates 게이트 임계와 달리 belle 판정
  후 근거와 함께 재조정 가능함을 SHEET/코드 주석에 명시.

## Deviations from Plan

None — plan 3개 태스크를 순서대로 실행했다. 다만 Task 2 수행 중 발견한
"belle 실측 프레임이 top-4 poseMin 밖"이라는 사실을 정직하게 다루기 위해
plan 이 명시적으로 요구하지 않은 **별건 프로브**(`belle_direction_probe.json`)
를 추가로 산출했다 — §verification_notes 의 "이 케이스가 rejected 버킷으로
떨어지는지 확인해 SUMMARY 에 적을 것" 요청을 이행하기 위한 것으로, Rule 2
(정직한 재료 생산이라는 plan 목적에 필수)에 해당하는 자체 판단이다. 운영
코드·게이트 임계 변경은 없다.

## Issues Encountered

- Task 2 실행 중 poseMin top-4(포즈거리 최소 순) 선택 방식이 belle 가 실측한
  정확한 프레임을 포함하지 않는 경우가 있음을 확인(peterpan, 순위 5위) —
  §Accomplishments·§한계 참조. 버그가 아니라 압축 규율의 자연스러운 결과이며,
  플랜이 지정한 방식(poseMin, MAX_CANDS_PER_RECORD=4)을 그대로 따른 결과다.

## LLM 학습 영향 (필수 기재)

- **호출 수**: Gemini `generateContent` **22회**(gemini-3.5-flash, temperature
  0) — Task1 스모크 2회 + Task2 전량 20회(계획 상한 20 정확히 소진, 안전망
  EYE_CALL_CAP=16/record 는 미도달).
- **전송 내용**: 학생/기준 전신 정지 프레임을 가로로 붙인 짝 스틸(무마크,
  무크롭) — 폴스포츠 연습 촬영 실루엣뿐, 민감 PII 아님(T-p1x-01 threat_model
  기결론과 동일 근거). 기존 `machine_eye`(관절 마킹 크롭)보다 **전송 범위가
  넓다**(전신 vs 관절 크롭) — SHEET·코드 docstring 에 명기.
- **추론 호출만, 학습 데이터 전송 0** — Google Gemini API 표준 추론 엔드포인트
  (`generateContent`) 호출이며 파인튜닝/학습 파이프라인에 데이터를 보내지
  않는다.
- **원장**: 리포 `evidence/` 커밋분 + `belle_direction_probe.json` 만 —
  scratchpad 캐시(영상/프레임)는 휘발이며 "보존" 주장하지 않는다.
- **키 관리**: SSM `/sunity/motion/gemini-api-key`(profile sunity-motion)에서
  런타임 주입, 키 값 로그 0(`len=` 만 출력).

## 한계 박제

1. 이 사이클은 **belle 판정 재료 생산까지다** — 운영 방출 아님. S3 업로드 0 /
   Firestore 쓰기 0(읽기만) / Pod 무접촉 / 채점 무접촉.
2. **폴거리 지표의 신체 기준점(힙 vs 발목) 불일치**(§Accomplishments) — 이번
   정식 후보군에서는 tie-band 뒤에 가려 드러나지 않았지만, 별건 프로브에서
   명백히 드러났다. 발목 기준 지표 추가는 belle 판정 후 별건 사이클 의제다.
3. **tie-band 값은 이 사이클 신설 하네스 한정자**(재튜닝 금지 대상 아님) —
   기존 card_gates 게이트 임계(HOLD_MAX_DPS 등)와 명확히 구분해야 한다.
   55건 중 39건(71%)이 tie-band 로 unmeasurable — 임계 폭이 적절한지는 더
   많은 fixture 가 필요하다.
4. **좌표 품질표 절대값이 belle 사전 실측과 다름**(모순율 정의 차이) —
   §Decisions Made 에 명기, 순서는 재현됨.
5. **moreSide 텍스트 분류는 Gemini 판단에 의존** — 이번 22회 호출에서
   스키마 위반/enum 이탈은 0건이었으나, "axis/joint/side" 분류 자체가 틀리면
   검증기가 엉뚱한 것을 재는 구조적 한계는 남아 있다.
6. peterpan 발굴 0건은 poseMin(claim 무관 최근접) 방식의 자연스러운 결과 —
   claimContrast(의도적 반대 자세 탐색) 였다면 다른 결과가 나올 수 있으나
   이 사이클은 계획 지정대로 poseMin 만 사용했다.

## 보드 재료 절대경로

- 시트: `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260816-p1x-pole-distance-axis/DISCOVERY-SHEET.md`
- 원장 append: `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md`
- 육안 확인: `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260816-p1x-pole-distance-axis/evidence/VISUAL-REVIEW.md`
- 별건 프로브: `/Users/kimtaesung/Dev/SunityMotion/.planning/quick/260816-p1x-pole-distance-axis/evidence/peterpan/belle_direction_probe.json`
- belle 열람용(한글 파일명 짝 스틸 20장 + 판정요청.md): `/Users/Shared/sunity-pole-eyefirst-260816/`

## User Setup Required

None — 외부 서비스 설정 불요(Gemini 키는 이미 SSM 에 있음).

## Next Phase Readiness

- belle 판정 대기 — DISCOVERY-LEDGER.md 의 "축 반전 눈-우선 검증(260816-p1x)"
  절 판정란에 기입 예정.
- 판정 후 반영 사이클(선택된 elbow 후보 카드화, 힙/발목 폴거리 지표 재검토
  여부, tie-band 조정 여부)은 별건 quick 으로 분리.
- pytest 기준선 유지(4371 passed/59 failed/26 skipped) — 이번 사이클로 인한
  회귀 0.

---
*Phase: quick-260816-p1x*
*Completed: 2026-08-16*

## Self-Check: PASSED

- 아티팩트 10/10 FOUND(eyefirst_verify.py · quality_gate.json ·
  elbow/peterpan eyefirst_verdicts.json · belle_direction_probe.json ·
  VISUAL-REVIEW.md · DISCOVERY-SHEET.md · DISCOVERY-LEDGER.md · 본 SUMMARY ·
  /Users/Shared 판정요청.md).
- 커밋 2/2 FOUND(`b939f5c9` Task1, `702dd788` Task2).
- `/Users/Shared/sunity-pole-eyefirst-260816/` 21개 파일(짝 스틸 20 +
  판정요청.md) 확인.
- Task3 자동 게이트(LEDGER/SHEET 그렙 + LLM학습 기재 + Shared 파일수 + pytest
  failed=59<=59 + backend diff 0) PASS.
