---
phase: quick-260821-kgq
plan: 01
subsystem: discovery-adopt / compare-render / production-ops
tags: [discovery-adopt, production-apply, freeze-inject, polly-tts, s3-doc]
requires:
  - quick-260814-di7 (doc 영속화 규약 + 주입 레이어 정식 경로 + pdshape knee 반영)
  - quick-260814-ehz (발굴 일반화 스윕 — cand17B/cand01E 좌표 정본)
  - quick-260814-chd (Polly 합성 경로 + 렌더 결정론 규율)
provides:
  - 피디쉐입 운영 compare_v1.mp4 갱신 (7 freezes — elbow 16.5s 발굴 정지 추가, 기존 6건 보존)
  - 파워스핀 renderedCompare/discovery 신설 (3 freezes — shoulder 0.5s 발굴 정지)
  - DISCOVERY-LEDGER belle 08-21 판정 기입 (채택 확정 2 · 보류 2)
  - powerspin compose 사슬 정본 (frames_md5 baseline/inject — 후속 사이클 대조축)
affects: [후속 Pod 실증 사이클, 발굴 채택 사이클 5번째 이후]
key-files:
  created:
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/{discover_left_elbow,discover_left_shoulder}.mp3
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/polly_synthesis.json
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/{pdshape,powerspin}_{wire_verdict,production_log,live_verdict}.json
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/{pdshape,powerspin}_frames_md5_inject.json
    - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/stills/{pdshape_discover_freeze_left_elbow,powerspin_discover_freeze_left_shoulder}.png
  modified:
    - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md (append only)
decisions:
  - "D-01 이행: belle 08-21 '추천 1, 2 둘 다 오케이' — cand17B/cand01E 일괄 프로덕션 반영"
  - "D-02 이행: 동반 2건(cand14B/cand02B) 장부에 판정 보류로만 기입 — 재질문 0"
  - "D-03 이행: di7 경로 그대로 — backend/ 변경 0 (porcelain 빈 출력)"
  - "D-04 이행: 캡션 = 박제 서술 조립, LLM 호출 0"
  - "D-05 이행: Polly Seoyeon/neural/ko-KR 동작당 1회 합성 후 repo 고정 (멱등)"
metrics:
  duration: 25분
  completed: 2026-08-21T06:20Z
  commits: 5 (017409e 장부+합성 / e438bf3 pdshape wire / 32bfad2 pdshape apply / a5c7974 powerspin wire / 233ccad powerspin apply)
---

# quick-260821-kgq: 발굴 신규 채택 2건 프로덕션 반영 (피디쉐입 elbow · 파워스핀 shoulder) Summary

**기계 판정 한 줄**: 두 동작 check-wire / check-apply 전건 exit 0 — 피디쉐입
베이스라인 사슬 == chd 승인본(bit-exact, 왼무릎 정지 보존 실렌더 증명) + 주입
7 freezes(기존 6건 정체성 전건 보존) + 파워스핀 신설 3 freezes, 프로덕션 쓰기
8건 전건 md5 왕복 재확인 + live 재fetch 렌더 왕복 PASS, push 완료(origin delta 0).

## 최종 캡션 2문장 — 원문 박제 (belle 사후 확인 재료)

**피디쉐입 왼팔꿈치 (cand17B, u16.4667/r15.1333) — DISCOVER_TEXT_ELBOW:**

> 기준 자세는 팔을 곧게 뻗어 폴을 잡는 순간인데, 왼쪽 팔꿈치가 접혀 있어요. 손을 급하게 뻗어 잡으면 팔꿈치가 접혀요. 조금 더 돌고 올라온 뒤에 팔을 뻗어 편하게 잡아보세요.

**파워스핀 왼어깨 (cand01E, u0.4667/r0.7333) — DISCOVER_TEXT_SHOULDER:**

> 기준 자세는 팔을 굽혀 몸을 높이 들어올린 순간인데, 왼쪽 팔이 곧게 뻗어 있어요. 시작할 때 팔을 굽혀 몸을 폴 쪽으로 당겨서, 안정적인 위치를 만든 뒤에 돌아보세요.

(소스: ehz DISCOVERY-SHEET §3-1/§4-1 육안 서술 + belle 08-14 원문 조립 — D-04.
수치 표기 0, 각도 마크 0. 스틸 육안 확인: 캡션 구움 + 결함 대조 성립 —
evidence/stills/ 2장.)

## LLM 학습 영향

이 사이클 LLM 추론 호출 **0** (Gemini 0 / Cerebras 0). **Polly TTS 2회**(동작당
1회 — 비-LLM 음성 합성, 송신 내용 = 위 코치 문장 텍스트만, PII/시크릿 0, 학습
전송 0). 합성 후 repo 고정(멱등) — 재실행 시 재합성 0.

## 프로덕션 쓰기 8건 요약 (전건 production_log 박제 + md5 왕복)

**피디쉐입 (uid fvcN…/aid p34fresh1786628533)** — 쓰기 전 사전 assert: live
renderedCompare == di7 정본 6 freezes + discovery == knee 1건 정확 + 현행 S3
mp4 md5 == `77cdcd436472438f3580cbb8d48683f3` (fetch·apply 2회 확인):

1. `compare_v1.mp4` 같은 키 덮어쓰기 — 신규 md5 `adc69707f1db5f118b882e96f5a4bba4` (왕복 ==)
2. `discover_audio_r00_left_elbow.mp3` — md5 `c0bab5c9073ec86cc60873350dce87b0` (왕복 ==)
3. `result.discovery` = 2 items (**knee 병합 보존** + elbow rid=r00, adoptedAt 08-21)
4. `result.renderedCompare` = 7 freezes: r00 5.33 / r01 15.67 / r04 29.93 /
   **r04:discover 42.07** / r02 54.17 / **r00:discover 68.8** / r03 83.0
   (r03 outSec 69.0→83.0 이동 = elbow 정지 14.0s 삽입 위치상 정직 기록)

**파워스핀 (uid csKW…/aid powerspinFault1785373695)** — 쓰기 전 사전 assert:
renderedCompare/discovery **부재** 확인 + canonical mp4 키 기존 객체 부재
(head_object 404) 확인 후 신규 put:

5. `compare_v1.mp4` 신규 키 — md5 `497fb708c0fc49370fc26860eb1b408c` (왕복 ==)
6. `discover_audio_r02_left_shoulder.mp3` — md5 `909728c5739e4eea41e09e61ace7c1e7` (왕복 ==)
7. `result.discovery` = 1 item (shoulder rid=r02)
8. `result.renderedCompare` = 3 freezes: **r02:discover 0.5** / r02 16.47 / r00 32.03

## 기존 정지 보존 — 기계 확인

- **피디쉐입 6건 (왼무릎 discover 포함)**: 베이스라인(elbow 추가 전) 렌더의
  compose 사슬이 chd `frames_md5_injected.json` 과 **bit-exact 동일** — 재구축
  환경(현 세션 재fetch + 재추출)에서도 승인본이 정확 재현됨. 주입 렌더에서
  기존 6건의 정체성 키(rid/joint/userSec/refSec/pairSrc/text/freezeS/markers/
  legsViz/poleViz/bodyViz) 전건 동일 (wire_verdict `oldFreezesPreserved`).
- **파워스핀 record 정지 (실측 2건 — 아래 Deviations)**: 주입 전후 정체성 전건
  동일 + 무수정 compare_verify H1 회계(eligible 집합 동일성) PASS.
- rid 해석: live doc criterion suffix 정확 1건 매칭 — pdshape elbow = **r00**
  (P35 순서와 동일이나 재해석으로 확정, 최대 감점 record -15.3 sanity PASS),
  powerspin shoulder = **r02** (예상과 일치).

## 검증 왕복 (live)

두 동작 모두: Firestore 재fetch doc == 반영 payload → live doc + **S3 방금 쓴
키에서 GET 한 mp3** 로 재렌더 → compose 사슬 == inject 사슬 + 무수정
compare_verify **ALL PASS** + `[discover]` 로그 (pdshape 2건 / powerspin 1건).
음성 게이트: 신규 항목 userSec +0.5s 비틀기 → `H2 순간 {rid}[discover]` FAIL
정확 1건 발생 확인 후 원복 (fail-closed 실증, H3/H4 동반 FAIL 은 di7 선례대로
perturbFailLines 에 정직 박제).

## Deviations from Plan

**1. [관측 상이 — live 값 사용] 파워스핀 record freeze 2건 (plan 추정 3건)**
- **Found during:** Task 3 --baseline
- **Issue:** plan 은 record freezes 3건(r00/r01/r02)을 예상했으나 live 실측 =
  2건(r00/r02). `r01:split_angle` 은 atVideoSec 부재 + align pairs 밖 —
  `select_pairs`/`build_timeline` fail-closed 스킵 (kipup "split 단일 마크
  좌표 부재" 선례와 동형의 구조적 침묵. ehz 시트도 powerspin split 2 record
  침묵을 같은 사유로 기록).
- **처리:** plan 자체 지침("다르면 관측 기록 후 live 값 사용") 적용 — 게이트를
  eligible 집합 동일성(H1 미러)으로 판정하고 관측을 wire_verdict
  `planDeviationNote` 에 박제. 반영 freezes = 3건(record 2 + discover 1),
  H1 회계·무수정 verify 전건 PASS. 프로덕션 안전 불변식(사전 assert/md5/왕복)
  은 전부 원계획대로 집행.
- **Files:** evidence/powerspin_wire_verdict.json (baseline 절)

**2. [환경] 드라이버 인터프리터 = backend/.venv 재실행 가드**
- 시스템 python3 에 imageio_ffmpeg/google-cloud 부재 → wire_adopt.py 가
  `backend/.venv/bin/python`(버전 박힌 경로)으로 자기 재실행. backend/ 코드
  수정 0 (porcelain 빈 출력) — 경로 발명 아님, 실행 환경 고정.

그 외 plan 대로. backend/ 변경 0 · 채점 무접촉 · 이모지 0 · 시크릿 로그 0 ·
S3/Firestore 쓰기는 위 8건이 전부.

## 보류 2건 — 장부 기입 (D-02)

DISCOVERY-LEDGER "belle 판정 (2026-08-21)" 절에 기입: pdshapefault
r03/cand14B 왼무릎(u13.60/r12.9333) · r02/cand02B 왼어깨(u1.0667/r2.20) —
**판정 보류** (판정 부재, belle 재질문 금지 명기). 승격 실적 집계는 행 4'/6'
append (기존 행 무수정 — 08-14 조건부 판정이 08-21 채택 확정으로 종결).

## Pod 실증

범위 밖 — Pod 없음 (belle Terminate, `pod-expected=down`). 새 Pod 재진입 시
운영 경로(`_run_deferred_compare_render`) discovery 재현 + discover mp3 회수
배선 재검은 di7 SUMMARY "다음 1단계" 그대로 승계.

## Known Stubs

None — 반영 전건이 운영 데이터에 배선됨 (플레이스홀더/빈 값 0).

## Threat Flags

없음 — 신규 표면 0 (쓰기 전건이 threat_model T-kgq-01~03 mitigate 절차대로
집행, Polly 송신 = T-kgq-04 accept 범위 내, 신규 패키지 설치 0).

## Self-Check: PASSED

- 커밋 5건 존재 (017409e / e438bf3 / 32bfad2 / a5c7974 / 233ccad), push 완료
  (origin/main..HEAD 빈 출력)
- evidence 실재: verdict×2 + production_log×2 + live_verdict×2 + frames_md5×3
  + mp3×2 + polly_synthesis.json + stills×2
- check-wire / check-apply 두 동작 전건 exit 0 (재실행 확인)
- `rtk git status --porcelain backend/` 빈 출력
