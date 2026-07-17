---
phase: 29-mode3-result-screen-completion
reviewed: 2026-07-17T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - app/app.json
  - app/package.json
  - app/src/app/analysis/result.tsx
  - app/src/components/InjuryRiskSection.tsx
  - app/src/components/ScoreBreakdownSection.tsx
  - app/src/components/VideoCompare.tsx
  - app/src/lib/api.ts
  - app/src/lib/deductionLabels.ts
  - backend/evals/phase29/README.md
  - backend/evals/phase29/assert_gates.py
  - backend/evals/phase29/eval_keys.json
  - backend/evals/phase29/run_sweep.py
  - backend/functions/pipeline/app.py
  - backend/functions/playback-url/app.py
  - backend/template.yaml
  - backend/tests/test_mode3_fault_zoom_selection.py
  - backend/tests/test_mode3_tally_seam.py
  - backend/tests/test_playback_url_reference.py
  - docs/contract.md
findings:
  critical: 0
  warning: 5
  info: 8
  total: 13
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-07-17
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 29 (mode3 결과화면 완성) 19개 파일을 검토했다. 핵심 계약 게이트는 전부 확인 통과:

- **OTA 크래시 게이트 PASS** — `VideoCompare.tsx` 에 `expo-screen-orientation` 정적 import 없음. `requireOptionalNativeModule('ExpoScreenOrientation')` 런타임 감지 + 함수 스코프 lazy `require` 만 사용 (VideoCompare.tsx:212-213, 303, 313). `app/src` 전체 grep 에서도 정적 import 0.
- **playback-url requirements PASS** — `backend/functions/playback-url/requirements.txt` 에 `firebase-admin>=6,<7` + `pyyaml>=6.0,<7.0` 존재 (a55a817 회귀 fix 확인).
- **계약 미러 PASS** — `docs/contract.md` §2 에 referenceMotionId 변형(가드 4종, 동일 404) 문서화, §10 에 mode3 방출 조건(D-01 status 불변 / D-02 항등) 문서화. 앱 `CRITERION_REGION_KEYPOINTS`(deductionLabels.ts:110-114) ↔ 백엔드 `_MODE3_ZOOM_CRITERION_REGION`(pipeline/app.py:3017-3021) 항목 동일 확인.
- **Firestore nested-array ban PASS** — deductionBreakdown records = flat dict list (contract.md:1513).
- **`npm run typecheck` (tsc --noEmit) 통과 확인.**
- **playback-url 보안 경로 견고** — reference 재서명은 Firestore doc `videoS3Key` 화이트리스트 + `reference/` prefix + isActive 가드 + 형식 regex, 실패 전부 동일 404. 테스트가 임의 s3Key 주입/EoP 케이스를 커버.
- **mode3 tally seam 견고** — `mode3_held` status 보존, in-place 점수 교체 항등(D-02), md 빈 dict passthrough(D-03) 전부 테스트/게이트로 고정. sweep tee 는 read-only 이며 pipeline 호출부(app.py:4203, keyword-only)와 wrapper 시그니처가 정합함을 호출부 추적으로 확인.

다만 재생바 결함 틱의 **프레임 도메인 이중 불일치**(9fps 측정 인덱스 ÷ 18fps 저장 프레임수), mode3 prev 재발급의 **videoFormat 미배선**(mov 영상 재발급 URL 이 존재하지 않는 .mp4 키를 서명), mode3 zoom **임시파일 누수**, 좌측(현재) 영상의 TTL 재발급 부재, template 의 playback-url 로그 보존 정책 누락 등 5건의 Warning 이 있다.

## Warnings

### WR-01: 재생바 결함 틱 시각 환산 — 프레임 도메인/듀레이션 도메인 이중 불일치 (틱이 실제 결함 시점의 절반 위치에 찍힘)

**File:** `app/src/lib/deductionLabels.ts:296-315`, `app/src/components/VideoCompare.tsx:777-781`, `app/src/app/analysis/result.tsx:1518`
**Issue:** 두 개의 독립적인 도메인 불일치가 겹친다.

(a) **fps 도메인:** `buildDeductionTicks` 가 방출하는 `frameIndex` 는 `visionVeto.windowMedianAngleDeltas.sourceFrameIndices.user` — 백엔드에서 이 인덱스는 **9fps angles 배열 공간**이다 (pipeline/app.py:2925-2928 "인덱스 공간 = 9fps frames 배열과 동일", features.py `window_median_angle_deltas` 가 student_angles 인덱스를 그대로 방출). 그런데 `tickFrameCount` 는 `userKeypointReport.frames`(result.tsx:1518)로, 저장 keypointReport 는 **18fps 로 upsample** 되어 있다 (pipeline/app.py:4491 `upsample_to_fps(..., target_fps=18.0)`). VideoCompare 의 환산 `sec = frameIndex * duration / tickFrameCount`(VideoCompare.tsx:778)는 분자(9fps 인덱스)와 분모(18fps 프레임수)의 도메인이 달라 **틱 위치와 seek 목적지가 실제 시점의 약 1/2** 이 된다. 이는 CR-01/D2("prev keypointReport 18fps 오독 → 절반 시각")와 동일 클래스의 버그를 앱 쪽에서 재현한 것이다. "①번 감점 시점으로 이동"이 엉뚱한 순간으로 점프한다.

(b) **duration 도메인:** `duration` 은 정렬 비활성(legacy) 경로에서 `min(leftDuration, rightDuration)`(VideoCompare.tsx:518-526)이다. `frameIndex` 는 좌측(사용자) 영상 도메인이므로 올바른 환산 기준은 `leftDuration` 인데, 우측(정은지) 영상이 더 짧은 legacy doc 에서는 min 이 좌측보다 작아 틱이 추가로 앞당겨진다.

틱은 mode1 veto-applied doc 에서만 방출되므로 범위는 제한적이나, 방출되는 모든 케이스에서 위치가 틀린다.
**Fix:**
```ts
// deductionLabels.buildDeductionTicks 는 frame 도메인만 방출하므로,
// 초 환산 기준을 "angles(9fps) 실효 fps" 로 교정한다. 백엔드가
// keypointReport 를 18fps 업샘플 저장하므로 frames 대신
// 파이프라인 fps 상수(9)를 쓰거나, 백엔드가 tick 을 초 단위로 방출.
// 최소 수정 (VideoCompare 쪽):
const sec = (tick.frameIndex * leftDuration) / anglesFrameCount; // anglesFrames = doc.anglesFrames (9fps 공간)
```
`tickFrameCount` 를 `userKeypointReport.frames`(18fps) 가 아닌 `anglesFrames`(9fps, AnalysisDoc 에 이미 저장됨) 로 배선하고, 환산 기준 duration 을 `duration`(비교 도메인) 대신 `leftDuration`(master) 으로 교체. 수정 후 실기기에서 틱 탭 → 결함 프레임 도달 확인 필요.

### WR-02: mode3 prev 영상 재발급 ext — `prevDoc.videoFormat` 은 어떤 경로에서도 채워지지 않아 mov 업로드의 재발급 URL 이 존재하지 않는 .mp4 키를 서명

**File:** `app/src/app/analysis/result.tsx:692`
**Issue:** `const ext = prevDoc.videoFormat || 'mp4'` — 그러나 (1) 앱 어디에서도 `videoFormat` 을 Firestore doc 에 기록하지 않고(`grep videoFormat app/src` 결과 소비처 result.tsx 뿐, 생산자 0), (2) `userAnalyses.ts` 의 `normalize()` 가 doc 을 재구성할 때 `videoFormat` 필드를 매핑하지 않으므로 raw 에 있어도 탈락한다. 결과적으로 `videoFormat` 은 **항상 undefined → ext 항상 'mp4'**. `mov` 는 허용 업로드 포맷(`VideoFormat = 'mp4' | 'mov'`, api.ts:87-90)이므로, 6일 이상 지난 mov prev 영상 재발급 시 Lambda 는 `uploads/{uid}/{analysisId}.mp4`(존재하지 않는 키)를 서명해 반환하고(서명은 객체 존재와 무관하게 성공), 앱은 그 깨진 URL 을 `freshPrevUrl` 로 채택 → prev 영상이 조용히 안 뜬다. 타입이 optional(`videoFormat?`) 이라 tsc 는 통과 — 런타임에서만 드러난다.
**Fix:** ext 를 저장된 실측 키에서 파생하는 것이 가장 견고하다 — prev doc 의 `result.myVideoKey`(백엔드가 항상 기록, pipeline/app.py:4155) 에서 확장자를 파싱해 `requestPlaybackUrl` 에 전달:
```ts
const ext = prevDoc.result?.myVideoKey?.endsWith('.mov') ? 'mov' : 'mp4';
```
또는 업로드 시점(loading.tsx doc 생성)에 `videoFormat` 기록 + `normalize()` 에 매핑 추가 (계약 3면 동시 수정).

### WR-03: 현재(좌측) 영상은 TTL 재발급 경로가 없음 — 7일 지난 분석 결과를 열면 본인 영상이 안 뜸

**File:** `app/src/app/analysis/result.tsx:1444`
**Issue:** D-09 가 mode3 prev(`freshPrevUrl`)와 mode1 reference(`freshRefUrl`)의 presigned 7일 TTL 만료를 재발급으로 해소했지만, **비교 화면의 좌측 = 현재 분석 본인 영상(`result.myVideoUrl`)은 재발급 훅이 없다**. 사용자가 7일 넘은 분석을 기록 탭에서 다시 열면 좌측 슬롯이 만료 URL 로 로드 실패("준비 중"/검은 화면)한다. 동일 결함 클래스이고 재발급 수단(`requestPlaybackUrl(analysisId, ext)`)이 이미 존재하므로 배선만 빠진 상태다.
**Fix:** `freshPrevUrl` 훅과 동일 패턴으로 현재 doc 의 `createdAt` 이 6일 초과면 `requestPlaybackUrl(현재 analysisId, ext)` 재발급 후 `leftUrl` 최우선 소스로 사용 (ext 는 WR-02 와 동일하게 `result.myVideoKey` 파생 권장).

### WR-04: mode3 zoom prev 영상 다운로드 실패 시 임시파일 누수

**File:** `backend/functions/pipeline/app.py:3084-3109`
**Issue:** `_build_mode3_fault_zoom_comparisons` 에서:
```python
tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
tmp.close()
_s3.download_file(bucket, prev_video_key, tmp.name)
prev_video_path = tmp.name   # ← download 성공 후에만 할당
```
`download_file` 이 예외를 던지면(`prev_video_key` 삭제/권한/네트워크) `prev_video_path` 는 여전히 `None` 이라 `finally: _safe_unlink_local_video(prev_video_path)` 가 no-op — `delete=False` 로 만든 빈 임시파일이 디스크에 남는다. 장수명 RunPod Pod 에서 실패가 반복되면 누적된다 (프로젝트가 T-05-03-02 에서 명시한 "delete=False 는 caller 책임 정리" 규율 위반).
**Fix:**
```python
tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
tmp.close()
prev_video_path = tmp.name      # download 전에 먼저 바인딩
_s3.download_file(bucket, prev_video_key, prev_video_path)
```

### WR-05: PlaybackUrlFunction 만 LogGroup(30일 보존) 누락 — 로그 무기한 보존

**File:** `backend/template.yaml:161-185` (vs. 296-316)
**Issue:** 템플릿 하단 "로그 보관 30일 (비용 관리 — backend_CLAUDE.md)" 섹션에 upload-url/reference/reference-auto-register/pipeline 4개 함수의 LogGroup(RetentionInDays: 30)이 명시돼 있으나 `sunity-motion-${Stage}-playback-url` 은 없다. Lambda 가 자동 생성하는 로그 그룹은 보존기간 "만료 없음" — 템플릿 스스로 선언한 비용 정책을 이 함수만 벗어난다. 또한 CFN 관리 밖 리소스라 스택 삭제 시에도 잔존한다.
**Fix:**
```yaml
  PlaybackUrlLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/lambda/sunity-motion-${Stage}-playback-url
      RetentionInDays: 30
```

## Info

### IN-01: app.json — `android.permission.RECORD_AUDIO` 중복 선언

**File:** `app/app.json:36-39`
**Issue:** `permissions` 배열에 동일 권한이 두 번 들어 있다.
**Fix:** 중복 항목 1개 제거.

### IN-02: playback-url analysisId 검증 — `str.isalnum()` 은 유니코드 문자 허용 + 상한 없음

**File:** `backend/functions/playback-url/app.py:125-127`
**Issue:** 주석은 "uuid hex 32자" 를 의도하나 실제 가드는 `analysis_id.isalnum() and len(analysis_id) >= 16` — Python `isalnum()` 은 한글 등 유니코드 영숫자도 True 이고 길이 상한이 없다. `/`·`.` 이 불가능해 path traversal 은 안 되고 uid-scoped 라 보안 구멍은 아니나, reference 경로의 ASCII regex(`_REF_ID_RE`) 대비 느슨하다 (기존 코드이나 리뷰 범위 파일).
**Fix:** `re.fullmatch(r"[a-zA-Z0-9]{16,64}", analysis_id)` 류 ASCII 화이트리스트로 교체.

### IN-03: `_handle_reference` isActive 가드 — `is not False` (부재/비 bool 값 통과)

**File:** `backend/functions/playback-url/app.py:82`
**Issue:** `doc.get("isActive") is not False` 는 필드 부재(legacy 11 doc 호환 의도)뿐 아니라 `0`, `"false"` 등 비 boolean 값도 통과시킨다. 현재 생산자(auto-registration)가 진짜 boolean 만 쓰므로 실해는 없으나, "승인 전 doc = isActive 미기록" 형태의 생산자가 미래에 생기면 미승인 영상이 서명된다. 의도된 결정(HIGH-2 리뷰 반영)이므로 기록만 남긴다.
**Fix:** 신규 reference 생산 경로가 추가될 때 `is True` 로 조이거나, 시드 스크립트가 항상 boolean 을 기록함을 가드 주석에 박제.

### IN-04: ScoreBreakdownSection — Pressable 분기에서 조립해 둔 a11y 라벨(`a11y`)을 버림

**File:** `app/src/components/ScoreBreakdownSection.tsx:82-126`
**Issue:** 번호+감점 점수를 포함한 `a11y` 문자열을 조립하지만 `onRecordPress` 전달 시(Pressable 분기) `accessibilityLabel` 은 `` `${row.label} 감점 상세 보기` `` 로 대체돼 감점 점수·번호 정보가 스크린리더에서 사라진다. `a11y` 는 View 분기에서만 사용 — 반쯤 죽은 변수.
**Fix:** Pressable 의 라벨을 `` `${a11y}, 상세 보기` `` 형태로 통합.

### IN-05: VideoCompare — 하드코딩 색상 `'#F4F4F4'`

**File:** `app/src/components/VideoCompare.tsx:1152`
**Issue:** `slotEmpty.backgroundColor: '#F4F4F4'` — "컬러 하드코딩 금지, 토큰만"(app/CLAUDE.md) 위반. 파일 내 유일한 리터럴 색상.
**Fix:** `colors.softBg` 등 기존 토큰으로 교체.

### IN-06: result.tsx — 미해결 TODO + 손상된 필러 주석

**File:** `app/src/app/analysis/result.tsx:1888`
**Issue:** `userName={undefined /* TODO: Firebase displayName 박제 박제 박제 박제 */}` — "박제" 4연속 반복은 의미 없는 손상 텍스트이고 TODO 가 방치돼 있다 (프로젝트 "박제 filler 금지" 원칙과도 충돌).
**Fix:** 주석을 `/* TODO: Firebase displayName 연결 */` 로 정리하거나 TODO 를 이슈로 승격 후 제거.

### IN-07: 전체화면 범례 탭 — Modal dismiss 와 시트 present 가 같은 커밋에 배칭되는 iOS 경합 가능성

**File:** `app/src/components/VideoCompare.tsx:1064-1068`, `app/src/app/analysis/result.tsx:1521`
**Issue:** `closeFullscreen()` 직후 동기적으로 `onLegendPress(item.number)` → `setDetailRecordIndex` 를 호출한다. React 배칭으로 전체화면 Modal 언마운트와 DeductionDetailSheet(Modal) 마운트가 동일 커밋에 들어갈 수 있고, iOS 는 dismiss 진행 중 present 를 드롭하는 사례가 있다 (planner_findings 3 의 회피책이 "닫기 선행"이지만 프레임 분리는 보장 안 됨). 실기기 재현 미확인이라 Info — HUMAN-UAT 관찰 항목에 "전체화면 범례 탭 → 시트 오픈" 추가 권장.
**Fix:** 재현 시 `setTimeout(() => onLegendPress(n), 0)` 또는 Modal `onDismiss` 콜백에서 시트 오픈으로 프레임 분리.

### IN-08: run_sweep — production Firestore 에 eval doc 영구 적재 (정리 절차 없음)

**File:** `backend/evals/phase29/run_sweep.py:183-201`
**Issue:** 멤버별 `users/phase29eval*{RUNID}/analyses/*` doc 을 production Firebase 프로젝트에 생성하고 삭제하지 않는다 (cold+warm = 24 doc/run). phase24/25 계보 승계 패턴이라 의도된 관행이나, 반복 실행 시 테스트 데이터가 누적되고 기록 화면류 전역 쿼리가 생기면 오염원이 된다.
**Fix:** sweep 종료 시 생성 uid 목록을 출력하고 선택적 `--cleanup` 플래그로 batch delete 제공, 또는 README 에 수동 정리 절차 1줄 추가.

---

## 검증 노트 (이상 없음 확인 항목)

- `assert_gates.py`: 게이트 5종+보조 로직 추적 — label 키(`success`/`fault`)가 eval_keys.json 과 정합, `preSeamOverall` 부재를 fail 로 처리(무음 배선결함 방지), phase24 `check_traceability` 재사용 경로 유효. 점수 리터럴 하드코딩 없음(100/0 항등 상수뿐).
- `run_sweep.py`: tee wrapper 시그니처가 pipeline 실호출(4203 keyword-only, 2454 positional 3+kwargs)과 정합. EVAL_OUT_DIR repo-내부 가드 유효. 멤버별 고유 uid 로 prev-free 보장 논리 확인.
- `test_mode3_tally_seam.py` / `test_mode3_fault_zoom_selection.py` / `test_playback_url_reference.py`: 모두 실제 시그니처·가드와 일치, mock 경계 적절, EoP·주입 케이스 커버.
- `pipeline/app.py` mode3 seam: `mode3_quant` sentinel 은 방출 dict 에 실리지 않음(직접 확인), 예외 시 passthrough graceful, `_build_mode3_fault_zoom_comparisons` 호출부 인자 순서 정합, `dtw_ref_fps=_pipeline_frame_fps()` CR-01 반영 확인.
- `result.tsx` wrapper/Content 훅 순서 분리 유지, cleanPass/showBreakdownSection/mode3 한계고지 게이트가 "정확히 1곳 노출" 불변식 충족.

---

_Reviewed: 2026-07-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
