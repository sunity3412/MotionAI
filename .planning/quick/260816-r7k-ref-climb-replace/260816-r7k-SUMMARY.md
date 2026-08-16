---
phase: 260816-r7k-ref-climb-replace
plan: 1
subsystem: ml-reference-data
tags: [firestore, s3, rtmw, mode1-scoring, p35-render-data, backup-verification, tdd]

# Dependency graph
requires: []
provides:
  - "reference/ref-climb 기준 영상을 06-17 정은지 성공 클라임 세트로 교체 (S3 영상 + Firestore 18필드 전부 새 기준)"
  - "구 자산(S3 영상 + Firestore 11-doc 전체 스냅샷) byte-검증된 백업 + 명문화된 롤백 레시피"
  - "mirror_reference_candidate_top_level.py — candidate 버전 → top-level 선택적 미러 스크립트 (재사용 가능, _release 무접촉)"
  - "climbfault(fault.mp4 vs ref-climb) NotPoleMotionError 완전 차단 해소 실증 (angle 0 → 86)"
  - "P35 data/climb·climbfault 새 기준 재생성 + 렌더 캐시 오염 발견·수리 절차"
affects: [mode1-scoring, p35-render-pipeline, reference-motion-management, discover-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "candidate 버전 문서 → 선택적 top-level 미러 (전역 reference/_release 무접촉) — 배치 전용 _flip_active_pointer 대신 단일 모션 교체용 스크립트 신설"
    - "복원 리허설이 인프라 제약(IAM)으로 불가할 때 → 백업의 perDocSha256(canonical hash)를 라이브 컬렉션과 직접 재대조하는 완전성 검증으로 대체 (round-trip 재현이 아니라 별도 근거로 승인받고 명시)"
    - "Pod GPU 실행이 sandbox 정책상 직접 SSH 불가할 때 → 실행 스크립트를 scratchpad 파일로 작성해 넘기고, 결과 파일을 같은 scratchpad 로 회수해 직접 검증하는 핸드오프 프로토콜"

key-files:
  created:
    - backend/scripts/mirror_reference_candidate_top_level.py
    - backend/tests/test_mirror_reference_candidate_top_level.py
    - .planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json
    - .planning/phases/35-server-rendered-comparison-video/data/climbfault/align.json
  modified:
    - .planning/phases/35-server-rendered-comparison-video/data/climb/doc.json
    - .planning/phases/35-server-rendered-comparison-video/data/climb/align.json
    - .planning/phases/35-server-rendered-comparison-video/data/README.md

key-decisions:
  - "복원 리허설(격리 컬렉션 round-trip)이 Firestore Admin API 인덱스 관리 권한 부족(403)으로 불가 → belle 가 IAM 변경 대신 백업 완전성 검증(perDocSha256 11/11 전량 대조)으로 게이트를 대체, 내가 같은 대조를 독립 재현해 근거 확인 후 진행"
  - "Pod 에서 실 write 를 수행하는 스크립트 실행이 Claude Code auto-mode 분류기에 차단됨 → SSH 우회 시도 대신 belle 가 Pod 실행을 맡고 나는 scratchpad 스크립트 작성 + 결과 파일 검증으로 역할 분담"
  - "reprocess_reference_motions_phase4.py 의 _flip_active_pointer 재사용 대신 범위 좁힌 mirror_reference_candidate_top_level.py 신설 — 전역 reference/_release.activeCandidate 무접촉으로 다른 10개 모션 영향 차단"
  - "_build_mirror_fields 는 계획의 명시 스펙(BASE_FIELDS 결측시 ValueError)보다 한 단계 더 fail-closed 하게 구현 — DOWNSTREAM_FIELDS 결측도 동일하게 막음(threat_model T-r7k-04 방어 강화)"

requirements-completed: ["belle-2026-08-16-ref-climb-replace"]

# Metrics
duration: 1h49m (Task 2·Task 4 의 Pod GPU 구간은 belle 가 직접 실행, 대기 시간 포함)
completed: 2026-08-16
---

# Phase 260816-r7k-ref-climb-replace Plan 1: ref-climb 기준 영상 교체 Summary

**ref-climb 기준을 05-22 극초반 배치(4.2MB)에서 06-17 정은지 세트(40.9MB)로 교체, mode1 climb 짝 어긋남(정답 26점·오답 완전차단)을 100/86 으로 정상화**

## Performance

- **Duration:** 약 1시간 49분 (17:00 백업 시작 ~ 18:48 Task 4 커밋). Task 2(Pod GPU 재처리)와 Task 4(Pod GPU climbfault 실증)의 실제 Pod 실행 구간은 belle 가 직접 수행(SSH 분류기 차단으로 역할 분담).
- **Started:** 2026-08-16T08:00:29Z (KST 17:00:29, Task 1 백업)
- **Completed:** 2026-08-16T09:48:09Z (KST 18:48:09, Task 4 커밋)
- **Tasks:** 4/4 완료
- **Files modified:** 7 (신규 4 + 수정 3)

## Accomplishments

- `reference/ref-climb` S3 영상 + Firestore 18필드(base 11 + downstream 7) 전부 새 영상(06-17 정은지 성공 클라임) 기준으로 교체, `anglesRealFps=14.944` 실측 기록
- 구 영상(S3 `_archive/`)과 구 Firestore 11-doc 전체 스냅샷(S3 백업 + 로컬)이 byte-검증된 채로 보존, 롤백 레시피 명문화
- 다른 기준 모션 10개 — 문서(SHA-256) + 영상(LastModified) 양쪽 완전 무변경 기계 검증
- climbfault(오답 영상) 의 완전 차단(`NotPoleMotionError: angle 0 < 25`)이 해소되고 climb(정답, 100)과 climbfault(오답, 86)가 순서대로 갈리는 것을 수치로 확정
- `mirror_reference_candidate_top_level.py` TDD(RED→GREEN, 20 테스트) 신설 — 전역 `_release` 포인터 무접촉을 grep 으로 자기증명 가능하게 구현
- 실행 중 두 가지 결함 발견·수리: (1) S3 멀티파트 복사로 인한 ETag 불신뢰(SHA-256 재검증으로 우회), (2) Pod P35 스크립트의 프레임 캐시(`rf15/`) 미삭제로 인한 1차 align 오염(belle 발견·수리, 검증 후 반영)

## Task Commits

| Task | 내용 | 커밋 | 비고 |
|------|------|------|------|
| 1 | 백업(Firestore 11-doc + S3 영상 아카이브) 후 신규 영상 업로드 | (커밋 없음) | `files: 없음` — S3/Firestore 쓰기 + 로컬 백업 아티팩트만, 레포 파일 변경 없음 |
| 2 | Pod GPU 재처리(base + downstream 필드, candidate 버전) | (커밋 없음) | Pod 에 이미 커밋된 스크립트 실행, Firestore candidate 서브문서만 write. belle 가 직접 실행(SSH 분류기 차단) |
| 3 | 미러 스크립트 작성+테스트 → 실행 → 실측 fps 백필 → 전체 검증 | `a8b959ff` (test, RED) → `7dfd60ab` (feat, GREEN) | TDD 게이트 정상 순서 확인(RED 커밋이 GREEN 커밋보다 먼저) |
| 4 | 교체 효과 실증(climbfault) + P35 데이터 재생성 + README 갱신 | `7114287e` (feat) | Pod 실행은 belle, 회수 파일은 내가 직접 검증 후 반영 |

## Files Created/Modified

- `backend/scripts/mirror_reference_candidate_top_level.py` — candidate 버전 문서를 top-level 에 선택적으로 미러(`_build_mirror_fields` 순수 함수 + CLI), `reference/_release` 전역 포인터 무접촉
- `backend/tests/test_mirror_reference_candidate_top_level.py` — 순수 함수 behavior 테스트 20개(BASE/DOWNSTREAM 필드 정합·부기 필드 비누출·양쪽 결측 fail-closed)
- `.planning/phases/35-server-rendered-comparison-video/data/climb/doc.json`, `align.json` — 새 ref-climb 기준으로 재생성 (구 c3m 데이터 대체)
- `.planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json`, `align.json` — 신규(교체 전에는 doc.json 자체가 생성 불가했음)
- `.planning/phases/35-server-rendered-comparison-video/data/README.md` — 검증 결과 섹션 추가(append, 기존 c3m 섹션 보존) + 파일구성/S3키 표에 climbfault 행 추가

## Decisions Made

### 1. 복원 리허설 → 백업 완전성 검증 대체 (경위와 근거 — 통과한 척하지 않고 있는 그대로)

Task 1 의 `backup_reference_docs.py --rehearse-restore` 실행 중, 백업 자체(11-doc read + 4-check 무결성 게이트 + S3 업로드/재다운로드 byte 비교)는 전부 **GATE PASS** 했으나, 이어지는 **격리 컬렉션 round-trip 리허설**이 다음 오류로 실패했다:

```
google.api_core.exceptions.PermissionDenied: 403 The caller does not have permission
```

원인: `_ensure_rehearsal_exemptions()` 가 격리 컬렉션 `reference_restore_rehearsal` 에 (40k index-entry 한도 회피용) single-field 인덱스 면제를 걸려다 실패. 읽기전용 `gcloud projects get-iam-policy` 로 근본 원인을 확인했다 — Firebase Admin SDK 서비스 계정(`firebase-adminsdk-fbsvc@sunity-ai-coach.iam.gserviceaccount.com`)이 `roles/firebase.sdkAdminServiceAgent` / `roles/firebaseauth.admin` / `roles/iam.serviceAccountTokenCreator` 만 갖고 있고, Firestore Admin API 의 `UpdateField`(인덱스 설정 변경)에 필요한 권한(`roles/datastore.indexAdmin` 등)이 없었다. 이 시점에서 실행을 멈추고 A(IAM 권한 부여)/B(로컬 Firestore 에뮬레이터로 대체)/C(리허설 생략) 세 옵션을 belle 에게 제시했다.

**belle 결정**: 옵션 A/B/C 어느 것도 아니고, IAM 변경 없이 **백업 완전성 검증**으로 게이트의 목적을 대체 — 백업 JSON 의 `docs[mid]` 를 라이브 `reference/{mid}` 문서와 **필드 단위 + canonical SHA-256** 로 직접 대조해 11/11 완전 일치·결측 0 을 확인. 근거: 리허설이 증명하려던 것은 "`set(merge=False)` 로 되쓰는 경로가 실제로 동작하는가"인데, 이 plan 의 Task 2/3 이 어차피 같은 `set()` 경로를 쓰므로 거기서 실패하면 즉시 드러난다. 반면 리허설이 막힌 지점(인덱스 면제)은 **격리 컬렉션에만 필요한 제약**이고 실제 롤백 대상인 `reference/{id}` 는 owner 가 콘솔에서 이미 그 면제를 걸어뒀다(스크립트 docstring 명시) — 즉 리허설 실패는 롤백 가능성과 무관한 도구 제약이었다는 판정.

**내가 독립 재현**: belle 의 판정을 그대로 옮기지 않고, 백업 파일에 이미 있는 `header.perDocSha256`(11개 문서, 백업 스크립트가 백업 시점에 계산해둔 canonical hash)을 라이브 Firestore 와 지금 다시 대조하는 코드를 직접 실행 — **11/11 SHA-256 완전 일치, 결측 0** 확인 후에야 Task 1 나머지(아카이브 복사 + 신규 영상 업로드)로 진행했다.

**결론**: 이 plan 은 "REHEARSAL PASS" 문자열이 찍힌 적이 없다 — 그 게이트는 **대체 검증으로 우회**됐다. 백업의 durable 성(S3 byte-verified) 은 원래 계획대로 증명됐고, "되쓰기 경로 자체가 동작하는가"는 round-trip 리허설이 아니라 Task 2/3 의 실제 candidate/top-level write 성공으로 사후 증명됐다(둘 다 성공).

### 2. Pod SSH 실행 차단 → 역할 분담

Task 2 실행 중 `reprocess_reference_motions_phase4.py` 를 SSH 로 Pod 에서 실행하려 하자 Claude Code auto-mode 분류기가 차단했다("Blocked by classifier... user can add a Bash permission rule"). 직전까지 진단/git pull/env 확인 등 읽기 위주 SSH 는 전부 정상 동작했고, **정확히 Firestore 에 실 write 를 수행하는 스크립트 실행 1건만** 막혔다. 명령 재구성이나 우회를 시도하지 않고(지침상 금지) 그대로 멈추고 보고했다.

belle 가 "분류기 차단 회피가 아니라 역할 분담"으로 프로토콜을 제시: 내가 실행 스크립트를 scratchpad 에 파일로 작성해두면 belle 가 Pod 에 올려 실행하고 결과 파일을 같은 scratchpad 로 scp 회수한다. Task 2 는 belle 가 직접 실행(결과를 내가 Firestore 직접 재조회로 독립 검증), Task 4 는 내가 작성한 `r7k-task4-pod.sh` 를 belle 가 실행하고 결과 파일을 회수, 내가 직접 열어 검증 후 레포에 반영했다.

### 3. `_flip_active_pointer` 재사용 대신 신규 스크립트

`reprocess_reference_motions_phase4.py::_flip_active_pointer` 는 flip 마다 전역 `reference/_release.activeCandidate` 도 함께 쓴다. 이 quick task 는 ref-climb 1개 모션만 옮기는 것이라 이 전역 필드에 값을 심으면 다른 10개 모션의 향후 승격 로직과 혼선을 만들 수 있다(현재는 아무 코드도 `_release` 를 읽지 않음 — 확인됨, 그래도 새로 심지 않음). `mirror_reference_candidate_top_level.py` 를 신설해 `reference/{motion_id}` 단일 문서만 write, `_release` 는 코드 어디에서도 참조하지 않음을 grep 으로 자기증명 가능하게 만들었다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] S3 멀티파트 복사로 ETag 가 계획서 기대값과 불일치 — SHA-256 직접 대조로 우회**

- **Found during:** Task 1 (신규 영상 업로드 후 검증)
- **Issue:** `aws s3 cp` 로 39MB 파일을 복사하자 결과 ETag 가 `cb6cf3f8609f41815e53e1c037c05381-5` 로, 계획서가 기대한 소스 ETag `8dd30a35761c5f8d50a9412b3832dd59` 와 불일치. S3 멀티파트 업로드/복사는 ETag = 파트별 MD5 의 해시 + `-N`(파트 수)이라, 같은 바이트도 업로드 방식에 따라 ETag 포맷 자체가 달라진다(잘 알려진 S3 함정) — Task 1 의 자체 verify 블록은 ContentLength 만 확인해 PASS 했지만, 그것만으로는 불충분하다고 판단.
- **Fix:** 소스(`fixtures/phase15/climb/correct.mp4`)와 목적지(`reference/ref-climb.mp4`) 를 각각 다운로드해 SHA-256 직접 대조 — `a73d4fff1bdddfa387553757397302812a7708c377080fe2bed7c722c6a96cc0` 로 byte-IDENTICAL 확인.
- **Files modified:** 없음(검증 절차 추가일 뿐)
- **Verification:** 위 SHA-256 대조 통과
- **Committed in:** 해당 없음(Task 1 은 레포 파일 변경 없음)

**2. [Rule 3 - Blocking] zsh 의 `set -e` 가 `&&` 체인 마지막 명령 실패를 삼켜 거짓 PASS 발생**

- **Found during:** Task 1 verify 블록 최초 실행
- **Issue:** 이 환경의 Bash 도구가 `/bin/zsh` 로 실행되는데, 계획서 원문의 `test -n "$LATEST" && jq -e ... ; set -e` 패턴을 그대로 돌리면 `&&` 체인의 마지막 명령(jq)이 실패해도 스크립트가 중단되지 않는다(bash 라면 중단됨, 경험적으로 확인). 동시에 `ls -t *.json | head -1` 이 mtime 순 정렬이라 `reference-11-preC-*.MANIFEST.json`(백업 이후 생성돼 mtime 이 더 최신) 을 실제 백업 파일보다 먼저 골라, **잘못된 파일을 검증하고도 "PASS" 가 찍히는 거짓양성**이 발생했다.
- **Fix:** `bash -c '...'` 로 명시 실행하고 파일 경로를 정확히 지정해 진짜 백업 파일 기준으로 재검증. 이후 Task 2~4 의 유사 검증은 `&&` 체인 대신 각 명령을 개별 실행 + 명시적 exit code 확인으로 전환.
- **Files modified:** 없음
- **Verification:** `bash -c` 재검증 PASS(check A~D 전부), `bash -c` 자체 exit code 0
- **Committed in:** 해당 없음

**3. [Rule 2 - Missing Critical] `_build_mirror_fields` 에 DOWNSTREAM_FIELDS 결측 fail-closed 추가**

- **Found during:** Task 3 (TDD 설계)
- **Issue:** 계획의 `<behavior>` 명세는 BASE_FIELDS 결측 시 ValueError 만 명시했다. 그러나 threat_model T-r7k-04("일부는 새 영상, 일부는 구 영상을 가리키는 내부 불일치 문서")는 DOWNSTREAM_FIELDS 결측에도 똑같이 적용되는 위협이다.
- **Fix:** `_build_mirror_fields` 가 BASE_FIELDS 뿐 아니라 DOWNSTREAM_FIELDS 결측 시에도 ValueError 를 던지도록 구현, 대응하는 테스트(`test_raises_on_missing_downstream_field`, 7개 파라미터화) 추가.
- **Files modified:** `backend/scripts/mirror_reference_candidate_top_level.py`, `backend/tests/test_mirror_reference_candidate_top_level.py`
- **Verification:** 20/20 테스트 PASS(계획 명시 3개 behavior + 이 추가분)
- **Committed in:** `7dfd60ab`

**4. [Rule 1 - Bug] Pod P35 스크립트의 프레임 캐시 미삭제로 인한 1차 align 오염 (belle 발견·수리)**

- **Found during:** Task 4 (Pod 실행, belle 담당)
- **Issue:** 내가 작성한 `r7k-task4-pod.sh` 는 `/workspace/p35/climb/ref.mp4` 만 삭제했다. 하지만 `p35_extract_align.py` → `compare_align` 모듈이 그 영상에서 RTMW 로 뽑아 로컬에 캐싱하는 프레임 디렉터리 `rf15/`(및 `verify/`)는 지우지 않았다. 그 결과 1차 align 재추출이 새 `ref.mp4`(40,928,589B, 새 영상, 정상 재다운로드됨)를 무시하고 그날 아침 c3m 실행분의 옛 프레임 캐시(`rf15/`, mtime 06:00, 256 프레임)를 재사용 — `climb align refFrames=256`(옛 값) vs `climbfault align refFrames=119`(신규 추출, 정상)로 같은 참조 영상인데 프레임 수가 어긋나는 내부 불일치가 발생했다.
- **belle 의 진단**: `ls -la` 로 `climb/rf15`(mtime 06:00) vs `climbfault/rf15`(mtime 09:13) 의 시각 차이로 캐시 재사용을 특정. `rm -rf /workspace/p35/climb/{rf15,verify}` 후 climb 만 재추출해 `refFrames=119`(climbfault 와 일치)로 수리.
- **내가 재검증**: 회수된 `climb/align.json` 을 직접 열어 `refFrames=119`(수리 후 값) 확인, scratchpad 원본과 레포 반영본 SHA-256 byte-일치 확인 — 로그 파일(`r7k-task4.log`)은 수리 **전** 1차 실행분만 담고 있어 그것만으로는 수리가 실제 반영됐는지 알 수 없었으므로 반드시 실제 JSON 을 열어 확인했다.
- **점수 데이터는 이 오염과 무관**: `pipeline._process()` 는 Firestore 기준 데이터(이미 새 영상으로 갱신됨)를 읽지, 이 로컬 프레임 캐시를 읽지 않는다 — `dimensionScores`(angle 100/86)는 캐시 문제와 완전히 독립적이다. 오염은 P35 렌더 입력용 `align.json` 에만 있었다.
- **다음에 같은 실수를 안 만들려면**: 참조 영상을 교체하는 Pod 스크립트는 `ref.mp4` 뿐 아니라 그 영상에서 파생되는 로컬 캐시 전체(`rf15/`, `uf15/`, `verify/` 등 `compare_align` 이 만드는 모든 디렉터리)를 함께 지워야 한다. 근본 수리는 캐시 디렉터리 이름을 영상 콘텐츠 해시 기반으로 바꾸는 것이겠지만 이번 quick task 범위 밖 — belle 판단 대기.
- **Files modified:** `.planning/phases/35-server-rendered-comparison-video/data/climb/align.json`(수리 후 버전 반영)
- **Verification:** climb/climbfault 양쪽 align.json `refFrames=119` 일치, scratchpad↔레포 SHA-256 byte-동일
- **Committed in:** `7114287e`

---

**Total deviations:** 4 auto-fixed (2 Rule 1, 1 Rule 2, 1 Rule 3) + 2 상위 결정(리허설 대체, Pod 역할분담 — belle 승인 사안, 별도 기재)
**Impact on plan:** 전부 정확성/일관성을 위한 수정. 계획 범위를 벗어난 기능 추가는 없음(DOWNSTREAM_FIELDS fail-closed 는 계획의 threat_model 이 이미 요구한 것을 명시 스펙보다 엄격하게 구현한 것).

## climbfault — 교체 전/후 angle 수치 대조 (있는 그대로, 덮지 않음)

| 대상 | 교체 전 | 교체 후 |
|---|---|---|
| climb (correct.mp4 vs ref-climb) | `dimensionScores.angle = 26` (임계 25, 간신히 통과) | `dimensionScores = {'stability': 93, 'angle': 100}`, `overallScore = 100` |
| climbfault (fault.mp4 vs ref-climb) | `NotPoleMotionError: angle 0 < 25` — 완전 차단(2회 재현, RTMW_DETERMINISTIC=1 하 결정론적) | `dimensionScores = {'stability': 93, 'angle': 86}`, `overallScore = 86`, status=done — **차단 해소** |

belle 이 짚은 "짝이 어긋나 있었다"(정답이 간신히 통과·오답이 아예 차단이 아니라, 정답이 확실히 높고 오답이 확실히 낮되 분석은 통과해야 함)가 이 교체로 수치상 확정됐다 — climb=100, climbfault=86 로 순서와 격차 모두 상식적인 범위에 들어왔다.

climbfault 의 `result` 에는 climb 과 달리 `deductionBreakdown` 키 자체가 없다(climb 은 키는 있고 `records=0`). Pod 로그에 `video fan-out 실패 — skipped (graceful): 504 DEADLINE_EXCEEDED` 가 1회 있었는데, 로그의 print/logging 출력 순서가 버퍼링 때문에 이 타임아웃이 어느 슬롯 호출에서 발생했는지 명확히 특정되지 않는다 — 이 결측이 그 타임아웃과 관련 있을 가능성은 있으나 **확증하지 못했고, 추측을 사실처럼 적지 않는다.** 둘 다 `align.json.pairs = {}` 인데, 이는 비정상이 아니다 — 같은 배치(quick-260816-c3m)의 `combo`(비렌더 슬롯, 이번 task 가 건드리지 않음)도 기존에 이미 `pairs = {}` 이고, climb/climbfault/combo 는 README 에 "발굴 스윕 후보(렌더 슬롯 아님)"로 명시돼 있어 pairs 가 비어도 실제 렌더 파이프라인에는 영향이 없다.

## Gemini video fan-out 1회 타임아웃 (graceful skip, 있는 그대로)

Task 4 Pod 실행 로그(`r7k-task4.log`)에 아래 1줄이 있다:
```
video fan-out 실패 — skipped (graceful): 504 DEADLINE_EXCEEDED. {'error': {'code': 504, 'message': 'Deadline expired before operation could complete.', 'status': 'DEADLINE_EXCEEDED'}}
```
코드가 이 예외를 삼키고 분석을 완주시켰다 — climb/climbfault 둘 다 `status=done` 으로 끝났고 크래시나 분석 중단은 없었다. 위에서 언급한 climbfault 의 `deductionBreakdown` 필드 결측과의 인과관계는 미확증(로그 순서 버퍼링으로 어느 슬롯인지 특정 불가).

## 롤백 절차 (문제 발생 시, PLAN.md `<rollback_procedure>` 원문 그대로 복사)

1. **S3 영상 되돌리기**:
   ```bash
   aws s3 cp s3://sunity-motion-pilot-videos/reference/_archive/ref-climb-pre-quick260816r7k.mp4 s3://sunity-motion-pilot-videos/reference/ref-climb.mp4 --profile sunity-motion
   ```
   (head-object 로 `ContentLength=4223747`, `ETag="4c4dfdbf48c30d80789186e4e8080b72"` 확인. 단, ETag 는 복사 방식에 따라 값이 달라질 수 있으니 — 이번 실행에서 실제로 겪은 문제 — 최종 확인은 **다운로드 후 SHA-256 대조**로 할 것)

2. **Firestore 문서 되돌리기** (Task 1 의 백업 JSON 이 유일한 완전 복원 원천 — `versions/phase4_v1` 서브문서는 downstream 7필드가 없어 불완전, 반드시 백업 JSON 사용):
   ```python
   import json, sys
   sys.path.insert(0, 'backend/shared/python'); sys.path.insert(0, 'backend')
   from sunity_shared import firestore_admin as fa
   backup = json.load(open('.planning/debug/backups/reference-11-preC-20260816-170029.json'))
   # 또는 S3 사본 재다운로드: s3://sunity-motion-pilot-videos/backups/reference-11-preC-20260816-170029.json
   fa._doc('reference/ref-climb').set(backup['docs']['ref-climb'], merge=False)
   ```
   (`merge=False` — 이번에 새로 추가된 필드(quick-260816-r7k 관련 UpdatedAt 감사 필드 등)까지 포함해 백업 시점 상태로 완전히 되돌림)

3. `reference/ref-climb/versions/quick-260816-r7k` 서브문서는 지우지 않아도 무해(참조되지 않음 — activeVersion 이 phase4_v1 로 되돌아가면 아무도 이 서브문서를 읽지 않는다).

4. 다른 10개 기준 모션과 `reference/_release` 는 이 plan 이 애초에 건드리지 않았으므로(SHA-256+LastModified 로 확인 완료) 롤백 대상 아님.

**백업 원천 (Task 1)**:
- S3 durable 백업: `s3://sunity-motion-pilot-videos/backups/reference-11-preC-20260816-170029.json`
- whole-file SHA-256: `4a1c70f0349265cf209b372cec8b8b0612fac27b29f090ec1c409b95ce8bcc1b`
- 로컬 사본(gitignored): `.planning/debug/backups/reference-11-preC-20260816-170029.json` (+ `.MANIFEST.json`)
- S3 영상 아카이브: `s3://sunity-motion-pilot-videos/reference/_archive/ref-climb-pre-quick260816r7k.mp4`(구 영상, 4,223,747B, byte-검증 완료)

## 2026-06-21 결정을 뒤집었음 (명시)

2026-06-21 belle 결정("하나만 쓴다면 이전 것 우선")을 **의도적으로 뒤집었다**. 2026-08-16 belle 이 "걍 따지지말고 교체하자"로 재결정 — 두 클라임 영상의 촬영 스튜디오·형태 불일치를 오늘 실측하고 내린 판단이며, belle 은 "두 클라임이 같은 동작인지 나중에 다시 물어볼 수 있다"고 했으므로 구 자산(S3 영상 + Firestore 문서 전체 스냅샷)을 절대 파괴하지 않고 위 백업 절차로 보존했다.

## LLM 학습 영향

`reference/ref-climb` 는 mode1(정은지 기준 비교) 채점의 기준 데이터이자, `p35_new_motion_docs.py`/`discover_sweep.py` 류의 발굴·재학습 파이프라인이 읽는 재료이기도 하다. 이번 교체로:
- climb 관련 향후 재학습 재료 구성이 **새 영상 기준**으로 갱신됨 — 구 영상 기준으로 만들어진 과거 산출물(예: 이번에 대체된 c3m 의 climb align/doc)은 무효화됐고, 앞으로 climb 발굴/스윕에 투입될 데이터는 이 교체 이후 재료만 유효하다.
- climbfault 의 차단 해소(angle 0→86)로, 지금까지 "비폴 영상으로 차단돼 분석조차 안 되던" climbfault 케이스가 이제 정상적으로 mode1 파이프라인을 통과한다 — 향후 발굴 스윕(`discover_sweep.py`) 대상에 climbfault 가 새로 편입될 수 있는 여지가 생겼다(이번 plan 범위는 아님, belle 판단 필요).
- 다른 10개 기준 모션은 문서·영상 모두 완전 무변경이므로 그쪽 재학습 재료 구성에는 영향 없음.

## Issues Encountered

없음 — 위 "Deviations from Plan" 에 기재된 4건은 전부 자동 수정되어 계획을 완주했다. 별도의 미해결 이슈는 없다(단, climbfault 의 `deductionBreakdown` 결측 원인은 미확증 상태로 남겨둠 — 위 명시).

## User Setup Required

None - 외부 서비스 신규 설정 불요.

## Next Phase Readiness

- ref-climb mode1 비교는 이제 실제 정은지 06-17 클라임 세트 기준으로 채점된다 — 앱에서 즉시 이 효과를 본다(추론 서버 재기동 없이 Firestore 를 읽는 구조이므로 별도 배포 불요).
- climbfault 가 discover_sweep 대상 후보로 새로 열렸다 — belle 판단 필요(이번 plan 범위 밖).
- Pod P35 스크립트의 참조영상-캐시 무결성 이슈(`rf15/` 등)는 이번엔 수동 수리로 넘겼으나, 근본 수리(콘텐츠 해시 기반 캐시 키)는 별도 후속 작업으로 남음.
- `reference-downstream-backfill.json`(레포 루트, 이번 세션 시작 전부터 존재하던 untracked 파일)은 이 plan 이 만든 것이 아니라 손대지 않았다 — 필요 시 별도 확인.

## Self-Check: PASSED

- 파일 존재 확인 9/9: `mirror_reference_candidate_top_level.py`, `test_mirror_reference_candidate_top_level.py`, `climbfault/{doc,align}.json`, `climb/{doc,align}.json`, `README.md`, 백업 JSON, 이 SUMMARY 자체 — 전부 FOUND.
- 커밋 존재 확인 3/3: `a8b959ff`(test), `7dfd60ab`(feat), `7114287e`(feat) — 전부 `git log --oneline --all` 에서 확인.
- Task 1/2 는 계획대로 레포 파일 변경이 없어 커밋 없음(정상) — 대신 S3/Firestore 상태를 직접 재조회해 검증함(본문 각 절 참조).

## TDD Gate Compliance (Task 3)

Task 3 는 `tdd="true"` — gate 순서 확인: `test(...)` 커밋(`a8b959ff`, RED)이 `feat(...)` 커밋(`7dfd60ab`, GREEN)보다 먼저 존재. RED 단계에서 `ModuleNotFoundError` 로 실패 확인(우연한 조기 통과 없음) 후 구현, GREEN 단계에서 20/20 PASS 확인. REFACTOR 커밋은 없음(리팩터링 필요 없었음). 게이트 정상.

---
*Phase: 260816-r7k-ref-climb-replace*
*Completed: 2026-08-16*
