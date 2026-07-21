---
phase: 32-result-readability-3-omni
plan: 16
subsystem: backend-pipeline, backend-api, contract
tags: [tts, polly, coach-audio, playback-url, h-02, d18, d23, sam-deploy, pod-deploy, sweep]

# Dependency graph
requires:
  - phase: 32-08
    provides: "D-18 B안(Polly neural) 확정 + 샘플 게이트 결정 기록 (32-GATE-DECISIONS §샘플 게이트)"
  - phase: 32-09
    provides: "records recordId·cueLine 방출 (합성 원문) + D-23 스윕 기준선 (runId 1784636486)"
  - phase: 32-11
    provides: "wave 6 완료 (실행 순서 의존)"
provides:
  - "pipeline 사후 coach_audio 스테이지 — records cueLine 을 Polly(neural)로 합성해 S3 coach_audio_{recordId}.mp3 저장 + result.coachAudio 부분 갱신 (프로덕션 라이브)"
  - "playback-url asset 'coachAudio' — 서버 구성 canonical key + exact 비교(H-02) 재서명 (32-12 audioCue prefetch 의 백엔드 선행)"
  - "coachAudio 계약 3면 lockstep (models COACH_AUDIO_KEYS + analysis.ts CoachAudio + contract.md §12.7) + firestore_admin scoped validator + userAnalyses normalize"
  - "s3keys.build_coach_audio_key — 저장·재서명 canonical key 단일 출처"
  - "SAM/Pod 배포 + 6동작 전수 스윕 diff 0 + presigned mp3 200 스모크 (D-23 배포 게이트)"
  - "Polly 한국어 음성 후보 샘플 3종 (belle 청취 확정 게이트 재료 — samples/voice/)"
affects: [32-12 (audioCue.ts B-branch prefetch 소비), 32-13 (배포 웨이브), 32-14, 32-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TTS 사후 스테이지 = fault_zoom 사후 분리 뼈대 복제 (complete 후 표현물 도착, 전 경로 graceful, 채점 무접촉)"
    - "오디오 asset 재서명 = H-02 정본 확장 (서버 구성 canonical + 저장 items exact 비교 + recordId 형식 화이트리스트)"
    - "음성/엔진 = env 우선(POLLY_VOICE_ID/POLLY_ENGINE) — belle 확정 게이트 후 재배포 없이 스왑 가능한 설계"

key-files:
  created:
    - backend/tests/phase32/test_coach_audio.py
    - backend/template-32-16-deploy.yaml
    - .planning/phases/32-result-readability-3-omni/samples/voice/ (mp3 3종 + README)
    - .planning/phases/32-result-readability-3-omni/32-16-SWEEP.md
  modified:
    - backend/functions/pipeline/app.py
    - backend/functions/playback-url/app.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/shared/python/sunity_shared/models.py
    - backend/shared/python/sunity_shared/s3keys.py
    - backend/template.yaml
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/userAnalyses.ts

key-decisions:
  - "합성 텍스트 = records cueLine 그대로 (문구집 32-05 골격 소유 — 변형 0, D-09 무수치 승계)"
  - "cueLine 보유 records 가 있는데 전부 합성 실패 → status 'failed' (IAM/Polly 전면 장애를 done+[] 로 위장하지 않음 — 스윕 검출 가능성)"
  - "coachAudio asset 은 VISUAL_JOB_KINDS 무접촉 별도 분기 (visual job 계약 오염 0, 기존 asset 응답 바이트 불변)"
  - "coach_audio 스테이지를 fault_zoom 렌더 앞에 배치 — 합성(수 초)이 zoom(수십 초)을 기다리지 않아 32-12 prefetch 성립 시점 단축"
  - "배포 = 브리지 템플릿(라이브 기준선 3ae4715 + 32-16 델타) — phase 31 fail-closed 파라미터 게이트 존중 (미보정 값 주입 금지)"

patterns-established:
  - "사후 부분 갱신 필드 추가 = update_analysis_{field} helper + scoped validator + 단일 field-path .update() (fault_zoom 뼈대)"

requirements-completed: [D-23]
requirements-partial: [D-18 (구현·배포·스윕 완료 — 최종 음성 belle 청취 확정 checkpoint 대기), D-09 (오디오 문장 = 승인 문구집 cueLine 그대로 — 무수치 승계)]

# Metrics
duration: ~1h 50m (스윕 76분 포함)
completed: 2026-07-22
---

# Phase 32 Plan 16: 백엔드 TTS Polly 스테이지 + coachAudio 계약 + 배포·스윕 Summary

**B안(AWS Polly neural) 오디오 백엔드를 완결 배선 — 분석 사후 스테이지가 records 의 cueLine 을 recordId 조인 키로 합성·저장하고, playback-url 이 H-02 exact 비교로만 mp3 를 재서명하며, SAM+Pod 배포 후 6동작 전수 스윕 점수 diff 0 + 실 mp3 200 스모크로 프로덕션 실증. 남은 것은 belle 음성 청취 확정(checkpoint) 하나 — env 스왑 설계로 확정 후 재배포 불요.**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | Polly 사후 스테이지 + coachAudio 계약 3면 + normalize | `f07b3a5` |
| 2 | playback-url coachAudio asset (H-02 exact 가드) | `93a21d4` |
| 3 | graceful·asset guard·validator 테스트 26건 | `0a5e7f6` |
| 4(부분) | 음성 후보 샘플 3종 커밋 (belle 청취 대기 — checkpoint) | `ebef2fd` |
| 5 | 브리지 배포 템플릿 | `312ec21` |
| 5(수리) | cold 타임아웃 + results/* GetObject 배포 수리 | `9615d7c` |

## Accomplishments

### Task 1 — Polly 사후 합성 스테이지 + 계약 3면 (D-18)

- **pipeline `_run_deferred_coach_audio`**: complete(status='done') 이후 `_stage("coach_audio")` 블록 — cueLine 보유 records 만 Polly(neural, ko-KR) 합성 → `results/{uid}/{analysisId}/coach_audio_{recordId}.mp3` 저장 → `update_analysis_coach_audio` 로 `result.coachAudio` {status, items} 단일 field-path 부분 갱신. record 단위 격리(1건 실패 = 그 record 만 생략), 전면 실패 = failed 마킹, write 실패도 무전파 — 분석 무훼손 (SP-3, fault_zoom 뼈대).
- **음성 env 스왑 설계**: `POLLY_VOICE_ID`/`POLLY_ENGINE` env 우선 (기본 Seoyeon neural 잠정) — belle 확정 음성이 기본값과 다르면 Pod env 2개 + Lambda env 로 재배포 없이 반영.
- **계약 3면**: models `COACH_AUDIO_KEYS`/`COACH_AUDIO_ITEM_KEYS`/`COACH_AUDIO_STATUSES` + `PLAYBACK_ASSET_COACH_AUDIO` ↔ analysis.ts `CoachAudio`/`CoachAudioItem` + `AnalysisResult.coachAudio?` ↔ contract.md §12.7 신설. **런타임 생성 예외 각주** 1줄 포함 (클라우드 TTS = 분석 시점 사전 생성 — CONTEXT '런타임 신규 생성 AI 0' 은 시각 생성 OFF 지칭, belle D-18 명시 승인).
- **firestore_admin**: `_validate_coach_audio` (키 화이트리스트 + status enum + item scalar-only 라우팅 + key results/ prefix) + `update_analysis_coach_audio` (fault_zoom 뼈대 — write 전 validator 강제).
- **userAnalyses normalize**: status 2값 화이트리스트 + item recordId/key(`normalizeResultKey` — results/ 강등 H-02) 방어 파싱, malformed item 드롭, 부재 = legacy 하위호환.
- **s3keys.build_coach_audio_key**: 저장(pipeline)과 재서명(playback-url) canonical key 단일 출처 — drift 원천 차단.

### Task 2 — playback-url coachAudio asset (H-02)

- `_handle_coach_audio`: recordId 형식 화이트리스트(`r[0-9]{2}:[A-Za-z0-9_]{1,64}` — path injection 이 key 빌더에 닿기 전 400) → 서버가 canonical key **구성** → 저장 items 중 같은 recordId 항목과 **전체 문자열 exact 비교** 후에만 1시간 presign (audio/mpeg). 가드 위반 전부 동일 404 (leak 0).
- 기존 asset 종류(correctedPose/rotation)는 `VISUAL_JOB_KINDS` 분기 무접촉 — 응답 바이트 불변.

### Task 3 — 테스트 26건 (phase32 suite 93 → 119 passed)

- 합성 스테이지: 성공 recordId 조인 / 부분 실패 격리 / 전면 실패 failed / 무결함 done+[] / write 실패 무전파 / **채점 무접촉 딥 동등 가드**.
- asset 가드: fresh 200 + stale key·타 uid key·failed status·부재·형식 위반 404/400 + 기존 visual asset 무회귀.
- validator 형상 10종 거부 + update helper 의 write 전 validator 경유 + 계약 lockstep 경량 가드 (TS CoachAudioItem 필드 == COACH_AUDIO_ITEM_KEYS).
- 회귀 selection (firestore/lockstep/contract/motion_alignment/deduction): 426 passed / 1 failed / 12 collection errors — 기존 1 failed·12 errors 는 32-06/32-09 와 동일한 사전 실재 환경 실패 (초과 실패 0).

### Task 5 — SAM/Pod 배포 + 6동작 전수 스윕 + mp3 스모크 (D-23)

- **SAM**: 브리지 템플릿(`template-32-16-deploy.yaml` — 라이브 기준선 3ae4715 + polly IAM + playback-url 수리)로 `sam build --use-container` + deploy ×3 (초기 + 수리 2회). polly:SynthesizeSpeech 정책 라이브 확인, RUNPOD_ANALYZE_URL env 현행 Pod 유지 확인.
- **Pod**: push `17708b0..312ec21` → git pull → `__pycache__` 청소 + 재기동 → `/health` 200 (`pipeline_loaded: true`).
- **스윕**: 6동작 12멤버 SERIAL 76분 (runId `1784649897`) — **DIFF_MEMBERS=0** (32-09 기준선 대비 점수·criteria·err 전 멤버 동일), coachAudio 전 완주 doc 방출 (fault items 3/3/7/7/1 = record 수 완전 조인, correct done+0, climb failed 부재 정상), canonical key 전 항목 일치, S3 HEAD 21/21, validator 전 doc PASS, 동기 경로 timingsMs 회귀 0. 상세 = `32-16-SWEEP.md`.
- **스모크** (실 배포 Lambda): coachAudio asset 200 → presigned GET 200 `audio/mpeg` 27KB → 미등재 recordId 404 → 형식 위반 400 → 미지원 asset 400.

### Task 4 (checkpoint 대기) — 음성 후보 샘플

- ap-northeast-2 ko-KR 가용 전수(describe-voices 실계정): Seoyeon(neural/generative/standard), Jihye(neural).
- 동일 코칭 문장(32-08 샘플 문장 — 문구집 leg_extension cueLine+whyLine)으로 3종 생성·커밋: `samples/voice/seoyeon_neural.mp3` / `jihye_neural.mp3` / `seoyeon_generative.mp3` (+README 청취 안내).
- 샘플 생성 = sunity-motion 자격의 SynthesizeSpeech 실증 (Pod 프로덕션 경로와 동일 IAM 사용자).
- **belle 확정 후 (continuation)**: 기본값과 다르면 pipeline 상수·env 반영 + 32-GATE-DECISIONS 1줄 기록.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 차단 해소] 브리지 배포 템플릿 (정본 template.yaml 배포 불가)**
- **Found during:** Task 5 (배포 준비 — 라이브 스택 파라미터 조회)
- **Issue:** 정본 template.yaml 은 phase 31 시각 스택 포함 — 그 파라미터 4종(Display/Training Judge·PoseTol)은 CALIBRATION blocked 로 **의도적으로 값이 없어 배포 실패가 정답** (31 H10-05 fail-closed, phase 31 SAM 배포 이월). 미보정 더미 값 주입은 31 게이트 파괴라 금지.
- **Fix:** 라이브 스택 기준선(3ae4715) + 32-16 델타만의 `template-32-16-deploy.yaml` 생성·배포 — phase 31 표면 무접촉, 정본에는 polly 정책이 이미 반영돼 향후 전체 배포 시 수렴. 폐기 시점 헤더 명기.
- **Files modified:** backend/template-32-16-deploy.yaml
- **Commit:** `312ec21`

**2. [Rule 1 - Bug] playback-url cold start 타임아웃 (asset 경로 500)**
- **Found during:** Task 5 (mp3 스모크 — HTTP 500)
- **Issue:** cold 실측 auth leg 7.7s + Firestore 첫 init ~6s > Timeout 10s (256MB ≈ 0.16 vCPU CPU 스로틀) — coachAudio 뿐 아니라 31 asset 경로(correctedPose/rotation)도 cold 에서 전부 타임아웃일 latent 결함. 타임아웃 후 런타임 재시작으로 warm 이 성립하지 않는 악순환.
- **Fix:** PlaybackUrlFunction Timeout 10→30 + MemorySize 512 (CPU 2배). 정본 + 브리지 lockstep.
- **Files modified:** backend/template.yaml, backend/template-32-16-deploy.yaml
- **Commit:** `9615d7c`

**3. [Rule 2 - 필수 기능 결손] playback-url role 에 results/* GetObject 부재 (presigned 403)**
- **Found during:** Task 5 (mp3 스모크 — 서명 200 후 다운로드 403)
- **Issue:** presigned URL 은 서명 role 권한으로 GET 되는데 role 은 uploads/*·reference/* 만 허용 — results/* asset URL 이 전부 403. 29 reference/* 때와 동일 함정의 재발이며, phase 31 asset 경로의 latent 결함이기도 함 (31 SAM 배포가 이월돼 라이브에서 미검출).
- **Fix:** s3:GetObject 에 `results/*` 추가 (asset 재서명은 H-02 로 서버 구성 canonical key 만 서명 — 권한 확장은 모델링된 경계 안). 정본 + 브리지 lockstep.
- **Files modified:** backend/template.yaml, backend/template-32-16-deploy.yaml
- **Commit:** `9615d7c`

### 실행 순서 조정 (오케스트레이터 checkpoint 프로토콜)

- 플랜 순서는 Task 4(음성 확정) → Task 5(배포)이나, 배경 executor 는 대화형 불가 — 오케스트레이터 지시대로 **배포·스윕까지 완료 후 checkpoint 반환**. 음성이 env 스왑 설계라 확정 후 재배포 불요 (기본값 Seoyeon neural 잠정 가동 중).

## Authentication Gates

없음 — sunity-motion 자격(로컬 profile = Pod IAM 사용자 동일)으로 Polly·SAM·SSH 전부 통과.

## Known Stubs

없음 — 잠정 음성(Seoyeon neural)은 stub 이 아니라 가동 중인 기본값이며, belle 확정은 교체 여부 결정 (checkpoint).

## Threat Flags

없음 — 신규 표면(pipeline→Polly, playback-url coachAudio, results/* 서명 권한)은 전부 플랜 threat_model(T-32-29/30/31) 의 mitigate 경계 안에서 구현됨 (합성 텍스트 = 문구집 문장만, key = 서버 구성 + exact 비교, graceful + 채점 무접촉 + 스윕 검증).

## Verification

- `pytest tests/phase32` → **119 passed** (기존 93 + 신규 26) / 회귀 selection 기준선 초과 실패 0
- `npm run typecheck` clean
- 계약 3면 + validator/normalize 대칭 + 런타임 생성 예외 각주 (contract.md §12.7)
- SAM deploy 성공 (polly IAM 라이브 확인) + Pod `/health` 200
- 6동작 전수 스윕 DIFF_MEMBERS=0 + coachAudio 방출·조인·canonical·S3 실존 전수 + validator PASS (`32-16-SWEEP.md`)
- playback mp3 presigned 200 스모크 + 가드 404/400
- STATE.md/ROADMAP.md 무접촉 (orchestrator 소관)

## Next (continuation 필요분)

1. belle 음성 확정 (checkpoint) → 기본값과 다르면 pipeline 기본 상수 또는 Pod/Lambda env 반영 + 32-GATE-DECISIONS §샘플 게이트 1줄 기록.
2. 32-12 오디오 배선(audioCue.ts B-branch)이 이 플랜의 playback-url + coachAudio 계약을 소비 (백엔드 선행 완료).

## Self-Check: PASSED

- FOUND: backend/tests/phase32/test_coach_audio.py
- FOUND: backend/template-32-16-deploy.yaml
- FOUND: .planning/phases/32-result-readability-3-omni/samples/voice/{seoyeon_neural,jihye_neural,seoyeon_generative}.mp3
- FOUND: .planning/phases/32-result-readability-3-omni/32-16-SWEEP.md
- FOUND commits: f07b3a5 / 93a21d4 / 0a5e7f6 / ebef2fd / 312ec21 / 9615d7c (git log 확인)
- 파일 삭제 0 (전 커밋 add/modify만)

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22 (Task 4 음성 확정 checkpoint 대기)*
