---
phase: quick-260814-chd
plan: 01
subsystem: ml-display
tags: [freeze-inject, caption-fix, polly-tts, compare_verify, card-inherit]

requires:
  - phase: quick-260814-0p2
    provides: freeze 주입 하네스 + SUPPORT-SURFACE 실측 + 카드 3장 md5 정본 + belle 확인 재료 골격
  - phase: quick-260813-wif
    provides: 채택 순간 cand13b (u12.8667/r12.40) + 눈 원장 + belle 채택 무릎 카드 (md5 대조 원본)
provides:
  - inject_freeze.py — chd 사본 (DISCOVER_TEXT 단일 소스 + --synthesize 멱등 + H3 discover 사본 delta + 카드 md5 STOP 게이트 + --stills)
  - evidence/discover_left_knee.mp3 — 발굴 문장 Polly 합성 실물 (repo 고정 — 렌더 결정론 입력)
  - 재렌더 영상 (발굴 정지 캡션·음성 = 박제 신규 문장, 원본 r04 무변경) + 리그 기계 판정
  - belle 확인 재료 갱신 (/Users/Shared/sunity-freeze-inject-260814/ — 구/새 문구 원문 대조)
affects: [freeze-inherit 승격 경로, 비교 영상 렌더러, 반영 사이클 (S3/doc — belle 확인 후)]

tech-stack:
  added: []
  patterns: "캡션 교체는 문장 단일 소스 상수(DISCOVER_TEXT) 3곳 참조(Polly Text / freeze text / H3 expected)로 자막=음성=판정 lockstep. Polly 는 호출마다 바이트가 달라 합성 1회 후 repo 고정(멱등 --synthesize)이 렌더 결정론의 전제. H3 는 rid 공유 시 text_overrides 불가 — pairSrc 기준 사본 delta 로 해당 엔트리만 expected 교체 (fail-closed, 라벨 명기)"

key-files:
  created:
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/discover_left_knee.mp3
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/polly_synthesis.json
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/baseline_verdict.json
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/inject_verdict.json
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/frames_md5_{baseline,injected}.json
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/cards/ (3)
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/stills/ (2)
    - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/안내.md
    - /Users/Shared/sunity-freeze-inject-260814/ 갱신 (mp4 교체 + 스틸 3 + 안내 — 휘발 가능 사본, 보존 아님)
  modified: []

key-decisions:
  - "H3 해소 = rid 단위 text_overrides 불가(원본 r04 와 rid 공유 — compare_verify.py:256) → pairSrc==discover 인 freeze 의 H3 엔트리만 expected=DISCOVER_TEXT 실제 문자 비교로 교체하는 사본 delta. 라벨 'H3 자막 진품 r04[discover]' + 상세 '사본 delta' 명기, fail-closed. align-peak/pole 사칭 0 (T-chd-01)"
  - "Polly 파라미터 = 운영 기본값 미러 (Seoyeon/neural — Pod env 실값은 터미네이트로 확인 불가, 채택 사유를 polly_synthesis.json 에 기록). 합성 1회 후 repo 고정 (T-chd-02)"
  - "원본 r04 정지(10.5s) 무변경 — 그 순간은 둘 다 접힌 국면이라 구 문구('접은 모양 그대로 겹쳐보라')가 옳음. 무변경의 기계 증명 = 무수정 판정기에서 원본 r04 H3 PASS('문자 일치') 정확 1건 assert"

requirements-completed: [QUICK-260814-CHD]

duration: 약 18min (2026-08-14T00:07Z ~ 00:25Z경)
completed: 2026-08-14
---

# Quick 260814-chd: 발굴 정지 캡션·음성 교체 재렌더 (belle 판정 반영) Summary

**기계 판정 한 줄**: 발굴 정지(왼무릎 u12.8667/r12.40)의 캡션·음성을 belle
결함 서사 정합 신규 문장(박제 원문)으로 교체 재렌더 — 무수정 판정기 FAIL 이
발굴 freeze 의 H2+H3 정확 2건 국한(원본 r04 H3 PASS 1건 = 캡션 무변경 기계
증명) → 사본 delta 2축(라벨 명기) ALL PASS + diff 국한 3층 + **카드 3장 md5
== 0p2 전건(STOP 게이트 미발동 — 무릎 카드 = belle 채택 카드 그대로)**.
S3/Firestore 쓰기 0 — belle 확인 대기.

## 성립한 것

1. **문장 단일 소스**: DISCOVER_TEXT 상수(박제 원문 문자 단위) 1곳 →
   Polly Text / freeze text / H3 delta expected 3곳 참조. 자막=음성=판정
   lockstep 구조 유지 (cue_text 원칙의 발굴 정지판).
2. **Polly 합성 1회 고정**: 64,700 bytes / 10.780s / md5 7fb6a4a3…
   (Seoyeon·neural·ko-KR — 운영 `_synthesize_coach_audio_items` 기본값 미러).
   `--synthesize` 재실행 = 멱등 skip 확인. 발굴 정지 길이 = 10.78 + 0.4 =
   **11.18s** (구 9.8s 에서 변동 — 운영 규칙 그대로, 실측 기록).
3. **베이스라인 재현**: 주입 off 렌더 2회 결정론(md5/compose/report 전건
   동일) + 운영 리그 무수정 ALL PASS + freeze 5건 outSec 운영 doc 재현
   (r00 5.33 / r01 15.67 / r04 29.93 / r02 43.0 / r03 57.83 — 0.01s).
4. **stock 2FAIL 국한**: 무수정 판정기 FAIL 정확 2건 = ① `H2 순간 r04:
   |12.87-10.50|=2.36s (src=discover)` ② `H3 자막 진품 r04: 불일치:
   구운='기준 자세는 다리를 곧게 편 채…'` — 게이트가 외부 삽입과 캡션 교체를
   설계대로 검출. **원본 r04 H3 PASS("문자 일치") 정확 1건** = 원본 정지 캡션
   무변경의 기계 증명. 사본 delta 2축(H2 tuple + H3 discover expected) 적용
   시 ALL PASS — 전 delta 라벨 명기, align-peak/pole 사칭 0.
5. **diff 국한 3층**: report 기존 필드 전건 동일 + compose JPEG md5 사슬
   (삽입 335프레임 @out 42.067s + 페이드 외 bit-동일, 335 == freezeS
   11.18x30 예측 일치) + mp4 공유 소스 전이 증명 contentOk (recontent 재확인
   포함). 결정론 2회 전건 동일.
6. **카드 무회귀 (STOP 게이트 미발동)**: survivors = r00/r03 +
   r04:inherit@u12.867/r12.40 (0p2 와 동일), 카드 3장 md5 == 0p2 실파일
   전건 — 무릎 카드 e891e7ae… = wif belle 채택 카드 그대로 (카드는 캡션에
   비종속임이 기계 증명됨). 카드 초 라벨 12.9 (실효 fps). 눈 replay 6히트 /
   miss 0 / 실호출 0.
7. **육안 실물** (frames-before-numbers): 스틸 2장 Read 확인 — 발굴 정지 =
   새 문장이 화면에 구움 + 학생 접힘 vs 기준 신전 대조 성립 / 원본 r04 정지 =
   구 문구 잔존(무변경).
8. **belle 확인 재료**: Shared dir 갱신 (mp4 교체 + 새캡션/구캡션 스틸 +
   안내.md 캡션 변경 절 — 구 문구는 이번 렌더 report 의 원본 r04 freeze text
   실측 인용, 새 문구는 DISCOVER_TEXT 원문. 음성 재합성·길이 변동·S3 보류·
   doc 영속화 규약 필요 명기). repo evidence/ 에 안내 정본 사본.

## 제약 준수

backend/ diff 0 (porcelain 게이트 전 Task) · 0p2 quick dir 무수정 ·
S3 쓰기 0 (GET 만 — 영상 2/mp3 5/eye ledger; put 은 스텁 캡처) · Firestore
쓰기 0 (읽기 전용 재수화) · 채점 무접촉 · Pod 무접촉 · 이모지 0.

**LLM 학습 영향**: Gemini 실호출 0 (replay 스텁 6히트/미스 0 — 네트워크 경로
자체 부재 + 가짜 키 이중 보증). **Polly 1회 = TTS 비-LLM 실호출** (코치 문장
텍스트만 송신, PII 0·시크릿 0) — 학습 전송 0. 합계: LLM 추론 호출 0.

## Deviations from Plan

**1. [Rule 2 - 확인 재료 정합] Shared 구 스틸(신규정지_왼무릎_12.9s_스틸.png)
을 새 캡션 프레임으로 교체**
- **Found during:** Task 3
- **Issue:** 0p2 재료의 그 스틸은 구 캡션이 구워진 프레임 — 교체된 영상 옆에
  두면 belle 확인 재료가 자기모순
- **Fix:** 같은 발굴 정지 장면의 새 캡션 프레임으로 갱신 (신규 스틸 2장 추가와
  별개로 기존 파일명도 최신화)
- **Files modified:** /Users/Shared/sunity-freeze-inject-260814/ (사본 dir)
- **Commit:** 16661244 (안내 사본 커밋에 포함 — Shared 는 git 밖)

그 외 plan 그대로 실행 (STOP 게이트 미발동, locked_decisions 위반 0).

## 다음 1단계 (belle 결정 대기)

belle 실물 확인 (Shared dir) → 반영 별도 사이클: ① 재렌더 mp4 + 새 mp3 S3
업로드 + doc renderedCompare/coachAudio 갱신 (새 Pod) ② backend 반영 = 0p2
SUPPORT-SURFACE §5 목록 + **이번 캡션 소스(발굴 순간 전용 문장)의 doc 영속화
규약** (record cueLine 조립 밖의 문장을 파이프라인 어디에 저장해 읽는가).

## Self-Check: PASSED
