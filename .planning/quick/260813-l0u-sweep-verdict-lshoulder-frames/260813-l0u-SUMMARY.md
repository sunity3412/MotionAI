---
phase: quick-260813-l0u
plan: 01
subsystem: display-grammar-judgment-ledger
tags: [judgment-ledger, fault-zoom, frames-before-numbers, left-shoulder, v7-approved]
requires:
  - quick-260813-ivs (스윕 시트 8장 + sweep_verdict.json + EYE-VERDICT.md 사전 박제)
  - quick-260811-xa1 JUDGMENT.md (판정 장부 정본)
  - P35 doc 정본 (data/pdshapefault/doc.json)
provides:
  - belle 08-13 스윕 시트 판정 전건 장부 박제 (반려 2 / 통과 6 / 소프트 노트 2 / 질문 1 + 사전 박제 대조)
  - 피디쉐입 왼어깨 r02 답변 재료 3종 (전신 프레임 짝 + v7 freeze 프레임 + 감점 claim 단락)
affects:
  - 다음 라운드 의제 2건 (짝 정합 게이트 축 + freeze 장면 선정 축)
key-files:
  created:
    - .planning/quick/260813-l0u-sweep-verdict-lshoulder-frames/recover_frames.py
    - .planning/quick/260813-l0u-sweep-verdict-lshoulder-frames/evidence/lshoulder_fullframe_pair.png
    - .planning/quick/260813-l0u-sweep-verdict-lshoulder-frames/evidence/lshoulder_v7_freeze.png
    - .planning/quick/260813-l0u-sweep-verdict-lshoulder-frames/evidence/frame_match.json
    - .planning/quick/260813-l0u-sweep-verdict-lshoulder-frames/ANSWER-LSHOULDER.md
  modified:
    - .planning/quick/260811-xa1-mark-grammar-round-ufb-freeze-2-belle/JUDGMENT.md (append-only, 삭제 0)
decisions:
  - "프레임 판정자 = 카드 패널 content-match (naive 초 환산 금지) — 선정 결과가 cropLines 참고값과 독립 일치"
  - "deficitDeg 70.0 vs deviation 6.79 수치 불일치는 미해석 보고만 (다음 라운드 입력)"
metrics:
  duration: ~12min
  completed: 2026-08-13
  tasks: 2/2
  commits: 2
---

# Quick 260813-l0u: 스윕 판정 박제 + 왼어깨 freeze 실물 회수 Summary

**One-liner:** belle 08-13 스윕 시트 판정 전건을 JUDGMENT.md 에 append-only 박제
(numstat 64/0)하고, 유일한 질문 건(피디쉐입 왼어깨 "영상은 어떻지..?")의 답변
재료 3종 — 카드 content-match 로 기계 검증한 전신 프레임 짝(user 96/ref 60) +
v7 승인 영상의 왼어깨 freeze 프레임(구운 자막·각도선 121°/147° 실물) + doc 정본
감점 claim 단락(deficitDeg 70.0 불일치 미해석 보고 포함) — 을 실물로 회수했다.

## Task 결과

### Task 1 — JUDGMENT.md append (커밋 524129e6)

- 새 최상위 섹션 "스윕 시트 판정 — belle 08-13" append. **numstat 64 추가 / 0 삭제**
  (append-only 기계 증명, `git show --numstat --format=`).
- 내용 전건: 반려 2 (왼무릎 u3.7/r2.4 · 왼팔꿈치 u8.6/r9.4 — "체크하기전에 이
  두개는 너무나 다른 화면이다", 짝 정합 게이트가 못 거른 케이스로 의제 등재) /
  통과 6 (무언급 = 통과 규칙 명기) / 소프트 노트 2 (freeze 장면 선정 의제 —
  freeze-inherit 승격 경로 재료 명기) / 질문 1 (왼어깨 -> ANSWER 상대경로 링크) /
  사전 박제 대조 (적중 2 · 불일치 1 · 무언급 통과 2 — 정직 기록) / 보드 정리 1줄.

### Task 2 — 왼어깨 답변 재료 3종 회수 (커밋 41d2bc69)

**회수물 1 — 전신 프레임 짝** (`evidence/lshoulder_fullframe_pair.png`):
- content-match 기계 선정: user 후보 49프레임(66~114) 중 **프레임 96** (diff 5.44,
  이웃 8.74/9.06/10.53/11.60 대비 뚜렷한 골, 실초 3.2s) / ref 후보 64프레임(12~75)
  중 **프레임 60** (diff 2.48, 이웃 7.44/7.69/10.08/10.83 대비 뚜렷한 골, 실초
  2.0s). 기록 = `evidence/frame_match.json`.
- cropLines 참고값과 독립 일치: user_frame=32(rep) x step 3 = 96, ref_video_idx=20
  x 3 = 60 — content-match 가 판정자, 참고값이 사후 corroboration.
- 풀프레임 합성: 마크·자막 추가 0, 같은 높이(1200px) 스케일 + 흰 6px 구분선.

**회수물 2 — v7 freeze 프레임** (`evidence/lshoulder_v7_freeze.png`):
- S3 read-only GET 1회 (`proto/phase35/pdshape_v3.mp4`, 1224x1080 30fps 1769프레임).
- 정지 run 스캔(diff<0.5, >=0.8s): 4건 검출 — run1(13.10~24.57s, 대표 565)이
  왼어깨 구간 (구운 자막 "왼쪽 어깨(겨드랑이) 각도가..." 로 특정, run0 =
  오른팔꿈치로 대조 배제). v7 은 전신 프레임 위 각도선 V + 수치 **121°/147°** 구움.

**실측 3 — 감점 claim 단락** (`ANSWER-LSHOULDER.md`):
- doc 정본 r02: measuredValue 26.79 / tolerance 20.0 / deviation 6.79 / points -8.2 /
  atVideoSec 3.222(라벨 공간) + statusLine·whyLine·cueLine 원문 인용.
- **수치 불일치 그대로 보고**: 카드측 deficitDeg 70.0 (userVideoSec 3.556, attached
  블록) vs doc deviation 6.79 — 출처가 다른 두 값, 해석 발명 0, 다음 라운드 입력.

**한글 사본**: `/Users/Shared/sunity-sweep-260813/왼어깨-영상전신짝.png` ·
`왼어깨-승인영상프레임.png` 생성 완료 (보드 게시 = 오케스트레이터 몫).

## 육안 대조 판정 (frames-before-numbers 박제)

선정된 user 프레임 96 크롭과 카드 좌 패널, ref 프레임 60 크롭과 카드 우 패널을
나란히 Read 로 열어 대조했다 — **양측 모두 동일 장면이다** (역립 국면, 팔·머리·
머리카락·배경 식물 위치까지 일치, 카드와의 차이는 구워진 빨간 원 마크와 "3.6s"
초 라벨뿐). 풀프레임 짝도 열어 확인: 좌 user / 우 ref 모두 같은 역립 PD 셰이프
국면(한 다리 걸고 한 다리 뻗음)의 전신이 원본 그대로 담겼다. v7 대표 프레임도
열어 자막 내용으로 왼어깨 구간임을 확인했다.

## Deviations from Plan

### 검증 커맨드 수정 (플랜 verify 스크립트 결함, 코드 무관)

- **발견**: Task 1 의 numstat awk 체크가 `git show` 의 Author 헤더 라인
  (`Author: 김태성 <...>` — NF==3)을 numstat 라인보다 먼저 잡아 false FAIL.
- **처리**: `--format=` 로 헤더 억제 후 재실행 — numstat **64/0** 확인, append-only
  증명 성립. 파일·커밋 내용 변경 0.

### 플래너 실초 추정과 content-match 결과의 차이 (정직 기록)

- 플랜 preverified 는 user 실초 ≈ 2.9s (rep idx 29 ÷ 10.0fps) 로 추정했으나,
  content-match 판정자는 **프레임 96 = 실초 3.2s** (rep idx 32 상당)를 뚜렷한
  골로 선정 — cropLines 의 user_frame=32 와 독립 일치. 후보창(2.2~3.8s)이 양쪽을
  다 덮었고 플랜이 "content-match 가 프레임 판정자"로 지정했으므로 플랜 이탈
  아님. 추정치와 실측의 차이만 여기 박제한다.

그 외 계획 그대로 실행.

## 제약 준수 증명

- backend/ + 하네스 3파일(sweep_render.py, verify_local.py, grammar_round.py)
  diff 0 (git diff --stat 기계 확인).
- JUDGMENT.md append-only — 커밋 numstat 삭제 0.
- Gemini 실호출 0 (이 태스크는 LLM 경로 자체가 없음 — ffmpeg+PIL+stdlib 만).
- Pod 무접촉. S3 = pdshape_v3.mp4 read-only GET 1회만 (쓰기·삭제 0).
- 이모지 0.

## LLM 학습 영향

**없음.** 이 사이클은 외부 LLM(Gemini/Cerebras) 호출 0 — 학습 전송 0, 기계 눈
원장 신규 적재 0. 회수·검증 전부 로컬 ffmpeg/PIL 결정론 연산.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 524129e6 | docs(quick-260813-l0u): belle 08-13 스윕 시트 판정 박제 (JUDGMENT append) |
| 2 | 41d2bc69 | feat(quick-260813-l0u): 피디쉐입 왼어깨 freeze 실물 회수 3종 (frame pair + v7 + claim) |

## Next

- belle 에게 답변 재료 제시 (보드 게시 = 오케스트레이터): 전신 짝 + v7 실물 +
  claim 단락 — "영상은 어떻지" 질문의 직접 답.
- 다음 라운드 의제 (장부 박제 완료): ① 짝 정합 게이트 축 (반려 2건이 게이트
  통과 후 육안 불일치) ② freeze 장면 선정 축 (소프트 노트 2건) ③ deficitDeg
  70.0 vs deviation 6.79 출처 불일치 규명.

## Self-Check: PASSED

- [x] `evidence/lshoulder_fullframe_pair.png` 존재
- [x] `evidence/lshoulder_v7_freeze.png` 존재
- [x] `evidence/frame_match.json` 존재
- [x] `ANSWER-LSHOULDER.md` 존재 (r02 recordId + 70.0 불일치 포함, grep 확인)
- [x] `/Users/Shared/sunity-sweep-260813/왼어깨-영상전신짝.png` · `왼어깨-승인영상프레임.png` 존재
- [x] 커밋 524129e6 · 41d2bc69 git log 존재
- [x] JUDGMENT.md 커밋 numstat 삭제 0
