# Phase 35: 서버측 정렬 합성 비교 영상 - Context

**Gathered:** 2026-08-07
**Status:** Ready to build — **plan-phase·research 생략, 이 문서가 곧 스펙** (belle 지시)

<domain>
## Phase Boundary

Pod가 user·ref 두 패널을 DTW warp 정렬로 나란히 붙이고 감점 정지·음성·자막 타이밍까지 구운
**단일 mp4** 를 렌더한다. 앱은 그것만 재생 — 동기·스냅·재개·드리프트 버그 계열이 원리적으로 소멸.
1단계 = 전 동작 프로토타입 배치 5편(엘보·킵업·파워스핀·pdshape·belle 실업로드) → belle 평가.
채택 시 라이브 동기 기계는 폴백 강등.

</domain>

<decisions>
## Implementation Decisions (belle 2026-08-07 discuss 16문항 + 작업 방식 지시)

### 작업 방식 — 굴레 탈출 (belle 원문: "매번 플랜→실패→계획→실패… 이 굴레는 벗어나야")
- **D-00:** plan-phase·research·plan-checker 생략. **완료 정의 = 폰으로 여는 mp4 링크 + 기계 판정 PASS.**
  실패의 산출물은 문서가 아니라 재렌더. belle 확인 전에 기계 판정(리그) 선행 — belle는 심사만.
  향후 세션도 이 phase 에 /gsd-plan-phase 를 돌리지 말 것.

### 정지·강조 연출
- **D-01:** 현행 문법 그대로 굽기 — 양패널 프리즈 + 활성 부위 빨강 + 자막. 줌인 컷 없음
  (변인 = "렌더 전환" 하나만 남겨 평가를 깨끗하게).
- **D-02:** 기준(정은지) 패널 = **전 구간 DTW 워핑**(user 타임라인에 재샘플) — 모든 순간 국면 일치,
  짝 스냅 자체가 소멸. 구간별 재생 속도 변화 감수. belle 지적("짝이 비슷한 파트지만 일치 자세는
  아님")의 구조적 해소.
- **D-03:** 정지 구간 화면 = 자막 + 부위 빨강만 (pill·디밍 없음 — 33 D-05 심플 승계).
- **D-04:** 프리즈 길이 = 음성 길이 + 0.4초.
- (재량 확정) 감점 0 동작(pdshape) = 정지 0회 순수 나란히 재생. 감점 번호·틱은 굽지 않고 앱 UI가
  렌더 타임라인 좌표로 표시. 큐 배치 = 시간순(fpw 승계), 렌더 타임라인은 자유라 겹침 문제 원리적 소멸.

### 음성·자막 굽기
- **D-05:** 코칭 음성을 mp4 오디오 트랙에 먹싱. 합성 텍스트 = 자막 조립식 lockstep 미러 유지
  (`_coach_audio_speech_text`).
- **D-06:** 사용자 "음성 끄기"(32 D-18) = 플레이어 mute. 원본 소리를 안 쓰므로 mute = 코칭만 꺼짐.
  렌더는 1벌.
- **D-07:** 자막은 화면에 굽기 — 스크럽·가로·공유 어디서나 제자리(#8 계열 소멸). 문구 수정 = 재렌더.
- **D-08:** 원본 영상 소리 제외 — 코칭 음성만 (학원 소음·음악 저작권 회피).

### 저신뢰 표시 (보드 #4·#5·#6 동승 결정)
- **D-09:** 저신뢰 관절 감점 큐 = 정지·자막·음성 유지 + **부위 빨강 억제**(IN-01 승계).
  **하드 조건 = "AI 공부중" 상태가 사용자에게 분명히 인지될 것** (belle 원문: "AI 공부중임을 좀
  잘 나타내줘야 뭘 하든 괜찮을 듯"). 기제는 Claude 재량 — 카드 고지 강화로 충족.
- **D-10:** 저신뢰 고지는 카드에서만 — 자막·음성 문장에 고지문 오염 금지(lockstep 이라 음성으로도
  읽혀버림).
- **D-11:** #5 빈 기준 패널 → 기준 전신 프레임(그 순간) + "AI 공부중 — 이 구간은 확대 비교가
  안 돼요" 1줄. 빈 것보다 낫고 거짓 정보 0.
- **D-12:** #6 사이각 널뛰기 → 신뢰도 시간축 스무딩·히스테리시스 후 그리기 — 이번 데이터측
  사이클에 포함 (근본 수리).

### 배치 전달·평가
- **D-13:** 전달 = S3 presigned 링크 5개, 폰 브라우저 직접 시청 (앱 개입 없이 렌더 자체 평가).
- **D-14:** 평가 = 편당 관점 체크리스트 5항목 — 동기 / 짝 자세 일치 / 부드러움 / 이해도 / 전체 느낌,
  PASS·FAIL. **이 표가 경험 계약서(돌파 ②)의 초안.**
- **D-15:** 채택 기준 = **전 동작 "라이브보다 낫다"** (한 동작 매몰 금지 정합).
- **D-16:** 킵업 split 측정 순간 + 실업로드 측정 순간 산출을 프로토타입에 포함 — 5편 전부 큐 있는
  렌더 (V-2 데이터측 잔여 동반 해소).

### Claude's Discretion
fps·해상도·인코딩·키프레임 간격 / 부위 빨강 렌더 방식 / 자막 타이포·배치(브랜드 #FF4B33·Pretendard
준수) / 프레임 보간 여부 / 파이프라인 구조(로컬 프로토 → Pod 배치 포트) / 기계 판정 스크립트 구성.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before implementing.**

### 결정 정본
- `.planning/CONTINUE-2026-08-01.md` — "08-07 마감" 절: 돌파 3수 승인·배치 매트릭스 근거
- `.planning/phases/33-result-trust-recovery/33-CONTEXT.md` — D-05(심플)·D-07(판정기준)·D-08(최악
  케이스)·D-13(음성 정지+강조 문법)·D-19(눈확인)·D-21(시뮬 후 OTA)·D-23(전 동작 검증) 승계
- `.planning/phases/32-result-readability-3-omni/32-CONTEXT.md` — D-09(헤드라인 수치 금지)·D-17(양옆
  +탭확대+가로)·D-18(자막+오디오 동시) 승계

### 렌더 입력 계약 (코드 앵커)
- `app/src/types/analysis.ts` — `cueTrack`(인증 순간 atVideoSec = 프리즈 앵커)·`refVideoSec`·감점
  record 계약
- `backend/functions/pipeline/app.py` — `_coach_audio_speech_text`(자막=음성 lockstep 원문),
  cueTrack 빌드, mp3 S3 키
- `backend/shared/python/sunity_shared/analysis/motiondtw.py:137,179` — paired-range DTW 정렬
  (Phase 28 자산) = 워핑 경로 산출 재사용
- `backend/shared/python/sunity_shared/analysis/fault_zoom.py` — refVideoSec 짝 방출(워핑 정합
  크로스체크용)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `motiondtw.align_paired`(paired-range DTW): ref→user 프레임 대응 경로 — D-02 워핑의 심장
- 재생 하네스(저장 좌표·Gemini 캐시, GPU 불요): 로컬 렌더 프로토에 좌표·순간 공급
- Polly 재합성 파이프(로컬 boto3 실증됨): 음성 트랙 소재
- Pod `pqe6uaw7mf8bh9` 가동 중(health PASS): split 순간 산출·5편 배치 렌더 담당

### Established Patterns
- 렌더 합성은 CPU 작업(PIL+ffmpeg) — 로컬 맥에서 1편 프로토 가능, GPU 불요
- 자막 문장 = `composeCueSubtitleKo` 조립식과 문자 단위 동일해야(미러 핀 테스트 존재)

### Integration Points (채택 후 — 지금은 범위 밖)
- 앱 재생 화면: 단일 mp4 + 틱 좌표 매핑, 라이브 동기 기계 폴백 강등

</code_context>

<specifics>
## Specific Ideas

- belle: "AI 공부중임을 좀 잘 나타내줘야 뭘 하든 괜찮을 듯" — 저신뢰 전달이 채택 조건의 일부
- 1차 평가의 통제: 렌더 전환 자체가 유일 변인이 되도록 현행 큐 문법 보존
- 완료 심사 순서: 기계 판정 전 항목 PASS → belle 링크 전달 (역순 금지)

</specifics>

<deferred>
## Deferred Ideas

- **#4 본체** — 저신뢰 감점의 점수 반영 비대칭(점수 확정 vs 표기 강등)을 채점 차원에서 어떻게 →
  **Phase 34** (채점 접촉이라 이 phase 밖)
- 앱 통합(단일 mp4 재생 화면·틱 좌표 매핑·mute 설정 배선) → 채택 후
- 라이브 동기 기계 폴백 강등·수리 계열 코드 정리 → 채택 후
- 임계 0.5 일반화 검증(#4 ⚠) — 배치 렌더 부산물로 신뢰도 분포 리포트 뽑아 후속 판단

</deferred>

---

*Phase: 35-server-rendered-comparison-video*
*Context gathered: 2026-08-07*
