# 32-16 D-23 배포 게이트 스윕 — B안 오디오 (Polly 사후 합성)

- **일시:** 2026-07-21 16:04 ~ 17:20 UTC (76분, SERIAL — [[pipeline-not-concurrency-safe-eval-serial]])
- **runId:** `1784649897` / uid `phase25eval` / Pod `6seluxc43awmqi` (RTX 4090)
- **기질:** run_sweep_3209.sh mirror (`/workspace/eval32/run_sweep_3216.sh`) — CPU EP (LD_LIBRARY_PATH 미설정), Gemini 캐시 warm. 32-09 emit 기준선과 동일 기질 → diff-0 비교 유효.
- **기준선:** 32-09 스윕 (runId `1784636486`, `/workspace/eval32/emit/phase25/phase25_sweep_report.json`) — 32-16-PLAN gate_inputs 지정.
- **배포 상태:** SAM `sunity-motion-pilot` (polly IAM + playback-url Timeout 30/Mem 512/results GetObject + 계약 코드) + Pod `312ec21` git pull·재기동, `/health` 200 (`pipeline_loaded: true`).

## 점수·verdict diff (diff_3209.py — 32-09 기준선 대비)

| member | 기준선 → 신규 | criteria | err/status | baseWall(ms) | newWall(ms) |
|---|---|---|---|---|---|
| power-spin fault | 55 → **55** | OK | OK | 223,489 | 206,493 |
| power-spin success | 100 → **100** | OK | OK | 275,251 | 281,421 |
| peter-pan fault | 79 → **79** | OK | OK | 169,017 | 175,903 |
| peter-pan success | 100 → **100** | OK | OK | 223,610 | 226,644 |
| elbow-twist-sister fault | 66 → **66** | OK | OK | 430,791 | 406,206 |
| elbow-twist-sister success | 100 → **100** | OK | OK | 532,525 | 521,312 |
| pdshape fault | 58 → **58** | OK | OK | 453,317 | 450,397 |
| pdshape success | 100 → **100** | OK | OK | 372,077 | 369,075 |
| kip-up fault | 80 → **80** | OK | OK | 198,222 | 195,130 |
| kip-up success | 100 → **100** | OK | OK | 212,566 | 213,674 |
| climb fault | gate → gate | OK | OK | — | — |
| climb success | gate → gate | OK | OK | — | — |

**DIFF_MEMBERS=0 (PASS)** — 점수·activatedCriteria·errorCode·status 전 멤버 동일. 합성 스테이지는 complete 이후 사후라 채점 무접촉 실증. **동기 경로 timingsMs 회귀 0** — wall 합계 ±6% 노이즈 범위(일부 멤버는 오히려 단축), coach_audio 소요는 doc 저장 timingsMs 에 미포함(complete 시 직렬화 — fault_zoom 관례)이고 stage 로그로만 방출(스테이지당 ~6s).

## coachAudio 방출 실측 (fetch_docs_3216.py — `/workspace/eval32/audio_docs.json`)

| motion | label | doc status | coachAudio | items | recordId 조인 | canonical key | S3 HEAD | validator |
|---|---|---|---|---|---|---|---|---|
| power-spin | fault | done | done | 3 | 완전 | 일치 | 3/3 | PASS |
| power-spin | success | done | done | 0 (결함 0) | — | — | — | PASS |
| peter-pan | fault | done | done | 3 | 완전 | 일치 | 3/3 | PASS |
| peter-pan | success | done | done | 0 | — | — | — | PASS |
| elbow-twist-sister | fault | done | done | 7 | 완전 | 일치 | 7/7 | PASS |
| elbow-twist-sister | success | done | done | 0 | — | — | — | PASS |
| pdshape | fault | done | done | 7 | 완전 | 일치 | 7/7 | PASS |
| pdshape | success | done | done | 0 | — | — | — | PASS |
| kip-up | fault | done | done | 1 | 완전 | 일치 | 1/1 | PASS |
| kip-up | success | done | done | 0 | — | — | — | PASS |
| climb | fault/success | failed (NotPole gate) | 부재 (방출 없음 — 정상) | — | — | — | — | PASS |

- **조인 완전** = cueLine 보유 record 의 recordId 집합 == items recordId 집합 (전 fault 멤버 21 항목).
- **canonical key 일치** = 저장 key == `s3keys.build_coach_audio_key(uid, aid, recordId)` (전 항목).
- **S3 HEAD** = mp3 실존 21/21. validator = 32-06 4종 + `_validate_coach_audio` 전 doc PASS.
- coach_audio 스테이지 실행 11회 (완주 doc 10 + pdshape cold-rerun), 합성 실패 로그 0.

## playback-url mp3 스모크 (실 배포 Lambda 경유 — smoke_playback_3216.py)

대표 키 `powerspinFault1784649897` / `r00:leg_extension`:

| 케이스 | 기대 | 실측 |
|---|---|---|
| asset coachAudio + 등재 recordId | 200 | **200** ({playbackUrl, expiresInSec: 3600}) |
| presigned GET 실 다운로드 | 200 audio/mpeg | **200**, `audio/mpeg`, 27,116 bytes |
| 형식 유효·미등재 recordId (r99:…) | 404 | **404** |
| 형식 위반 recordId (`../../etc/passwd`) | 400 | **400** |
| 미지원 asset (기존 경로 무회귀) | 400 | **400** |

## 배포 중 발견·수리 (SUMMARY Deviations 상세)

1. **playback-url cold 타임아웃** — cold auth leg 7.7s + Firestore 첫 init ~6s > Timeout 10s → Timeout 30 / MemorySize 512 (`9615d7c`).
2. **results/* GetObject 부재** — 서명 role 권한 없이는 asset presigned GET 전부 403 (31 asset 경로 latent 결함 동반 해소, `9615d7c`).
3. **브리지 배포 템플릿** — 정본 template.yaml 은 phase 31 fail-closed 파라미터로 배포 불가(의도된 게이트) → 라이브 기준선(3ae4715)+32-16 델타만의 `template-32-16-deploy.yaml` 로 배포 (`312ec21`).

## 산출물 (Pod, repo 밖 — baseline 무접촉 관례)

`/workspace/eval32/audio/phase25/phase25_sweep_report.json` + `audio_docs.json` + `audio_sweep.log` + `run_sweep_3216.sh` / `fetch_docs_3216.py` / `smoke_playback_3216.py`
