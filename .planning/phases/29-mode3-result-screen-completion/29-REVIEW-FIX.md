---
phase: 29-mode3-result-screen-completion
fixed_at: 2026-07-17T00:00:00Z
review_path: .planning/phases/29-mode3-result-screen-completion/29-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 29: Code Review Fix Report

**Fixed at:** 2026-07-17
**Source review:** .planning/phases/29-mode3-result-screen-completion/29-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (Warning 5 / Critical 0 — fix_scope=critical_warning, Info 8건 제외)
- Fixed: 5
- Skipped: 0

검증: 앱 수정 3건 모두 `npm run typecheck` (tsc --noEmit) PASS. 백엔드 수정은
`tests/test_mode3_fault_zoom_selection.py` + `tests/test_mode3_tally_seam.py` +
`tests/test_playback_url_reference.py` 27 passed, `sam validate --lint` PASS.
채점 수학/감점 값/breakdown 방출 의미는 무접촉 — 전부 표시 도메인/인프라/자원
정리 수정. 배포(`sam deploy`/`eas update`) 미실행 (RunPod SSM 재동기화 대기 정책).

## Fixed Issues

### WR-01: 재생바 결함 틱 시각 환산 — 프레임/듀레이션 도메인 이중 불일치

**Files modified:** `app/src/lib/userAnalyses.ts`, `app/src/app/analysis/result.tsx`, `app/src/components/VideoCompare.tsx`, `app/src/lib/deductionLabels.ts`
**Commit:** d450e6b
**Status:** fixed: requires human verification (표시 로직 수정 — 실기기에서 틱 탭 → 결함 프레임 도달 확인 필요, 리뷰 원문 지시 동일)
**Applied fix:** 앱 측 최소 수정 (백엔드 방출 무접촉 — 계약 3면 변경 없음, `anglesFrames` 는 기존 AnalysisDoc 계약 필드):
- `normalize()` 가 top-level `anglesFrames`(9fps angles 공간 T)를 매핑하도록 추가 (learningOptIn 패턴 미러 — number 일 때만 통과).
- `result.tsx` wrapper → `AnalysisResultContent` 에 `anglesFrames` prop 전달, `tickFrameCount` 배선을 `userKeypointReport?.frames`(18fps 업샘플) → `anglesFrames ?? 0`(9fps) 으로 교체. 구 doc(필드 부재)은 0 → 틱 자연 생략 (graceful).
- `VideoCompare.tsx` 초 환산을 `sec = frameIndex * leftDuration / tickFrameCount` 로 교체 (분모=9fps T, 기준 duration=좌측 사용자 영상 master 도메인). legacy `min(dL,dR)` 앞당김 해소. 렌더 게이트에 `leftDuration > 0` 추가. 트랙 위 위치 pct 는 기존 재생 도메인 클램프 유지.
- `deductionLabels.ts` 의 stale 환산 규칙 주석을 9fps/leftDuration 규칙으로 갱신 (함수 로직 무변경 — frame 도메인만 방출 유지).

### WR-02: mode3 prev 재발급 ext — videoFormat 미배선으로 mov 영상이 존재하지 않는 .mp4 키 서명

**Files modified:** `app/src/app/analysis/result.tsx`
**Commit:** 3be8f9d
**Applied fix:** 리뷰 권장 1안(실측 키 파생) 채택 — `const ext = prevDoc.result?.myVideoKey?.endsWith('.mov') ? 'mov' : 'mp4'`. `myVideoKey` 는 normalize 가 result 를 통짜 통과시키므로 앱에 실제 도달함을 확인 (videoFormat 은 생산자 0 + normalize 미매핑으로 항상 undefined 였음). useEffect deps 도 `prevDoc?.videoFormat` → `prevDoc?.result?.myVideoKey` 로 교체. 계약 3면 수정 불필요 (신규 필드 없음).

### WR-03: 현재(좌측) 본인 영상 TTL 재발급 경로 부재 — 7일 지난 분석 열람 시 좌측 안 뜸

**Files modified:** `app/src/app/analysis/result.tsx`
**Commit:** 60e0164
**Applied fix:** `freshPrevUrl` 훅 1:1 미러로 `freshMyUrl` 훅 신설 — 현재 doc `createdAt` 6일 초과 시 `requestPlaybackUrl(analysisId, ext)` 재발급 (ext 는 WR-02 와 동일하게 `result.myVideoKey` 파생). wrapper 가 `analysisId` prop 을 Content 로 전달 (기존 `useAnalysisDoc` 구독 doc 의 ID — 신규 fetch 0). `leftUrl` 소스 체인을 `freshMyUrl || result.myVideoUrl || undefined` 로 교체 (재발급 실패 시 기존 폴백 유지, __DEV__ warn).

### WR-04: mode3 zoom prev 영상 다운로드 실패 시 임시파일 누수

**Files modified:** `backend/functions/pipeline/app.py`
**Commit:** a1bc50f
**Applied fix:** 리뷰 fix 스니펫 그대로 — `_build_mode3_fault_zoom_comparisons` 에서 `prev_video_path = tmp.name` 바인딩을 `_s3.download_file` **앞**으로 이동. download 예외 시에도 `finally: _safe_unlink_local_video(prev_video_path)` 가 `delete=False` 임시파일을 정리한다 (장수명 Pod 누적 방지, T-05-03-02 규율 정합). 관련 테스트 3파일 27 passed.

### WR-05: PlaybackUrlFunction LogGroup(30일 보존) 누락

**Files modified:** `backend/template.yaml`
**Commit:** 3ae4715
**Applied fix:** 로그 보관 30일 섹션에 `PlaybackUrlLogGroup` (`/aws/lambda/sunity-motion-${Stage}-playback-url`, `RetentionInDays: 30`) 추가 — 기존 4개 함수 LogGroup 패턴 동일, 함수 선언 순서에 맞춰 ReferenceApiLogGroup 뒤 배치. `sam validate --lint` PASS. 템플릿 변경만 — 배포는 지침대로 미실행 (다음 `sam deploy` 시 반영; 기존 자동 생성 로그 그룹이 이미 존재하면 CFN 생성 충돌이 날 수 있어 배포 시 `aws logs delete-log-group --log-group-name /aws/lambda/sunity-motion-pilot-playback-url` 선삭제 또는 import 검토 권장).

## Skipped Issues

없음 — in-scope 5건 전부 수정.

---

_Fixed: 2026-07-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
