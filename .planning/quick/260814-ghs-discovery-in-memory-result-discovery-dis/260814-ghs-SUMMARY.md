---
phase: quick-260814-ghs
plan: 01
subsystem: testing
tags: [pipeline, compare_render, discovery, firestore, observability, tdd]

requires:
  - phase: quick-260814-di7
    provides: "result.discovery 영속화(update_analysis_discovery) + build_timeline 주입 레이어 + compare_verify H1~H4 discover fail-closed"
  - phase: quick-260814-0p2
    provides: "발굴 정지 주입 재렌더 실증(사본 delta) — 정식 경로 승격 대상 스펙"
provides:
  - "firestore_admin.get_analysis_discovery — update_analysis_discovery 의 read 짝 (검증 경유, 부재 = [])"
  - "_run_deferred_compare_render 발굴 조달 블록 (fail-open + WARNING) + discover mp3 basename 회수 (항목별 비차단)"
  - "doc_like discovery 주입 — di7 H1~H4 discover fail-closed 가 운영 경로에서 처음 활성화"
  - "조달-반영 대조 회계 log.warning — 조용한 소실 재발 차단"
  - "운영 스테이지 층 discovery 회귀 6축 (실 build_timeline 계측 스텁)"
affects: [발굴 반영 사이클, Pod 실증, SUPPORT-SURFACE §5]

tech-stack:
  added: []
  patterns:
    - "사후 채택물 조달 = Firestore 유일 진실 (in-memory 근거가 원리적으로 없는 데이터의 doc_like 조립 규약)"
    - "조달-반영 대조 회계 — 실패 원인 불문 한 줄이 남는 관측 게이트 (차단 아님)"
    - "운영 스테이지 테스트가 실 build_timeline 을 호출하는 계측 스텁 (mock 이 가리던 층을 여는 하네스)"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/functions/pipeline/app.py
    - backend/tests/phase35/test_compare_render_stage.py

key-decisions:
  - "조달 소스 = Firestore get_analysis 위 read 짝 (호출부 인자 전달은 무의미 — 호출부에도 근거가 없다)"
  - "field projection 미도입 — analysis doc 은 1 MiB 상한이라 전체 읽기 비용이 유계, 프로젝션은 별건 최적화"
  - "get_analysis_discovery 는 형상 위반을 raise (삼키면 갭 A 와 같은 침묵 재발) — 스테이지가 fail-open + WARNING 으로 처리"
  - "회계 로그 위치 = report.json 기록 뒤 / freeze 전멸 조기 return 앞 (전멸 시에도 로그가 남아야 한다)"
  - "형상 위반 축을 6번째 테스트로 추가 (플랜 verification 4 + T-ghs-01 이 요구, 5축은 이 경로를 직접 못 잼)"

patterns-established:
  - "RED 먼저: 수리 전 실패 출력을 실물로 박제한 뒤에만 수리 (조용한 소실의 재현 증거)"
  - "fail-open 3중(부재/읽기실패/형상위반) + 흔적 필수 — 발굴 없는 절대다수 렌더 무영향"

requirements-completed: [QUICK-260814-GHS]

duration: 9min
completed: 2026-08-14
---

# quick-260814-ghs: 운영 재렌더 discovery 조용한 소실 수리 Summary

**발굴 채택 freeze 가 운영 재렌더 경로에서만 freeze 도 excluded 행도 안 남기고 사라지던 결함을, Firestore read 짝 조달 + discover mp3 basename 회수 + 조달-반영 대조 회계로 수리하고 네 실패 경로 전부를 관측 가능하게 만들었다.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-14T03:03:15Z
- **Completed:** 2026-08-14T03:12:11Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **갭 A (조용한 소실) 수리** — `_run_deferred_compare_render` 가 조립하는 `doc_like` 에 `result.discovery` 가 실린다. render 와 verify 가 **같은 doc_like** 를 받으므로 di7 의 H1~H4 discover fail-closed 의미론이 운영 경로에서 처음으로 실제 활성화된다 (종전에는 discovery 가 없어 대조 자체가 성립조차 안 했다).
- **갭 B (di7 이연분) 수리** — `discover_audio_{rid}_{joint}.mp3` 를 coach mp3 와 같은 `audio_dir` 로 basename 회수. `build_timeline` 의 조인 규약(`audio_dir/<basename(mp3Key)>`)과 lockstep.
- **침묵 제거** — 네 실패 경로(조달 읽기 실패 / 형상 위반 / mp3 부재 / 렌더 미반영) 전부가 WARNING 또는 `discover_no_mp3` excluded 행 중 하나를 남긴다. 테스트 6축이 이를 강제한다.
- **RED 실물 박제** — 수리 전 실행 로그로 4 failed / 1 passed 확인 후 수리. 추가 6번째 축까지 포함해 **수리 전 코드 상대 5 failed / 1 passed** 를 별도 재현 실행으로 확인.
- **무회귀 구조 증명** — `compare_render.py` / `compare_verify.py` diff 0, 산식 7파일 diff 0, pytest 기준선 59 failed IDENTICAL.

## Task Commits

1. **Task 1: RED — 운영 스테이지 discovery 회귀 5축 작성 + 실패 재현** — `7ffc13bc` (test)
2. **Task 2: GREEN — discovery 조달 + mp3 회수 + 미반영 회계** — `ccd8de84` (fix, 형상 위반 축 추가 포함)
3. **Task 3: 게이트 — pytest 기준선 · 산식 무접촉 · push** — `4b3c5ad1` (docs, 주석 행 포인터 교정 1건 외 코드 변경 0)

## Files Created/Modified

- `backend/shared/python/sunity_shared/firestore_admin.py` — `get_analysis_discovery(uid, analysis_id) -> list[dict]` 신설 (+30행). `update_analysis_discovery` 의 read 짝. `get_analysis` 위에 얹고 `_validate_discovery` 를 강제 경유, 부재 = `[]`, 형상 위반 = raise.
- `backend/functions/pipeline/app.py` — `_run_deferred_compare_render` 3지점 (+77행): ① align_quality 게이트 뒤 조달 블록 (fail-open + 항목별 mp3 회수) ② `_result_for_doc["discovery"]` 주입 ③ report.json 뒤 / 전멸 return 앞 조달-반영 대조 회계.
- `backend/tests/phase35/test_compare_render_stage.py` — 섹션 6 신설 (+308행): 실 `build_timeline` 을 호출하는 계측 스텁 `disc_env` + 회귀 6축.

## RED 실패 라인 원문 (조용한 소실 재현 증거)

수리 전(커밋 `7ffc13bc` 시점) 실행:

```
F.FFF                                                                    [100%]
=================================== FAILURES ===================================
test_compare_render_stage.py:699: KeyError: 'discovery'
test_compare_render_stage.py:766: AssertionError: []
test_compare_render_stage.py:789: AssertionError: assert {'reason': 'discover_no_mp3', 'rid': 'r07'} in []
test_compare_render_stage.py:822: AssertionError: []
4 failed, 1 passed, 18 deselected in 0.63s
```

읽는 법 — 이 네 줄이 곧 결함의 성질이다:

| 라인 | 축 | 실패가 말하는 것 |
|------|-----|------------------|
| `KeyError: 'discovery'` | (a) 조달 | 운영 조립 doc 에 discovery 키가 **아예 없다** (갭 A) |
| `AssertionError: []` | (c) 읽기 실패 | 경고가 한 줄도 없다 = 침묵 |
| `{'discover_no_mp3','r07'} in []` | (d) mp3 부재 | freeze 도 **excluded 행도** 없다 — 리그도 못 잡는 조용한 소실 |
| `AssertionError: []` | (e) 미반영 | 조달분이 렌더에 없어도 흔적 0 |

`.` 하나(= (b) 무회귀 축)가 PASS 한 것이 판정 성립 조건이었다 — 무회귀 축이 못 서면 나머지 판정이 무의미하다.

추가 확인 (6축 전체 상대 RED): 현재 테스트 코드를 **수리 전 `app.py`(RED 커밋 산출물)** 에 물려 재실행 → `5 failed, 1 passed`. 6번째 축(형상 위반)도 `test_compare_render_stage.py:789: AssertionError: []` 로 실패 = 수리가 성립시킨 축임이 확인됐다. (스크래치 pytest 플러그인이 RED 커밋의 `app.py` 를 테스트 모듈명으로 선점 캐시하는 방식 — 리포 무접촉, 산출물은 휘발.)

## 조달 소스 설계 결정과 근거

**결정: Firestore 가 유일 진실. `get_analysis` 위에 read 짝을 얹는다.**

- **왜 in-memory 가 아닌가** — coachAudio 는 "그 분석이 방금 합성한" mp3 목록을 스테이지가 손에 쥐고 있어서 그것을 doc 에 싣는 처방이 성립했다. discovery 는 **분석 사후 belle 채택물**이라 어떤 파이프라인 실행에도 in-memory 근거가 원리적으로 없다. 호출부(`app.py:7986-` 계열)에도 없으므로 인자 전달 설계는 무의미하다.
- **왜 field projection 을 안 쓰는가** — analysis doc 은 Firestore 1 MiB 상한이라 전체 읽기 비용이 유계이고, 프로젝션(`select()`) 도입은 신규 SDK 표면을 여는 별건 최적화다. 검증된 `get_analysis` 재사용이 표면 최소.
- **왜 validator 를 caller 가 아닌 read 짝에서 강제하는가** — 오염 payload 가 doc_like 로 새면 렌더러/리그가 그것을 진품으로 취급한다 (T-ghs-01). read 짝이 `_validate_discovery` 를 강제 통과시키고 **raise 한다** — 여기서 조용히 `[]` 로 흘리면 갭 A 와 똑같은 침묵이 다시 생긴다. graceful 처리는 스테이지의 책임.
- **배치** — `get_analysis` 정의가 파일 뒤(:2205)지만 모듈 전역은 호출 시점에 해석되므로 `update_analysis_discovery` 바로 뒤 배치가 무해하다 (read/write 짝을 나란히 두는 가독성 우선). 주석에 명기.

## 네 실패 경로의 흔적 수단

| 실패 경로 | 흔적 | 후속 동작 | 못박는 테스트 |
|-----------|------|-----------|----------------|
| 조달 읽기 실패 (Firestore 예외) | `log.warning("compare_render discovery 조달 실패 …", exc_info=True)` | fail-open — 발굴 없이 렌더 진행, `done` 부착 | (c) |
| 형상 위반 (`_validate_discovery` raise) | 같은 WARNING (같은 except 수렴) + **doc_like 미도달** | fail-open, S3 GET 0 | (f) |
| discover mp3 회수 실패 (S3) | `log.warning("… discover mp3 회수 실패 rid=%s key=%s — discover_no_mp3 로 흘림")` + `build_timeline` 의 `discover_no_mp3` excluded 행 | 그 항목만 제외, record freeze 생존 → `done` | (d) |
| 조달분 렌더 미반영 (원인 불문) | `log.warning("compare_render discovery 미반영 rids=%s excluded=%s …")` | 관측만 — 차단 아님, `done` 진행 | (e) |

부수 관측: 조달 성립 시 `log.info("compare_render discovery 조달 n=%d rids=%s …")` — Pod 실증 때 이 줄이 실행 증거가 된다 (`[[wiring-claims-need-log-evidence]]`).

**H1 이 안 깨지는 이유** — `compare_verify` 의 H1 eligible 은 `record rid ∪ discovery rid`, accounted 는 `freezes ∪ excluded` 다. mp3 부재로 `discover_no_mp3` excluded 행이 남으면 회계가 맞아 H1 은 여전히 PASS 한다 (mp3 부재가 리그를 깨지 않는다).

## 게이트 결과

| 게이트 | 기준 | 실측 |
|--------|------|------|
| phase35 전건 | 신규 6축 포함 PASS | **129 passed** |
| pytest 기준선 | 59 failed IDENTICAL | **59 failed / 4211 passed / 26 skipped** (4205 + 신규 6 = 4211) |
| 산식 7파일 diff (`dimensions·kismam·motiondtw·temporal·features·assemble·deduction_engine`) | 빈 출력 | **빈 출력** |
| `compare_render.py` / `compare_verify.py` diff | 빈 출력 (di7 fail-closed 의미론 무손상) | **빈 출력** — 구조로 증명 |
| 동작명·실 분석 ID 리터럴 (`pdshape·p34fresh·peterpan·powerspin·kipup`) | 매치 0 | **0** (합성 fixture 만) |
| 변경 파일 | 플랜 명시 3개 | **3개** (app.py +77 / firestore_admin.py +30 / 테스트 +308) |
| push | origin delta 0 | **0** (`4b3c5ad1`) |

**프로덕션 쓰기 0** — 이번 사이클에서 S3 put / Firestore update 를 한 번도 실행하지 않았다. 테스트는 `FakeS3` + `monkeypatch` 로만 동작한다. **Pod 무접촉** (터미네이트 상태 유지). **채점 무접촉**.

## Decisions Made

- 조달 소스 = Firestore read 짝 (위 절 근거).
- 형상 위반은 read 짝에서 raise, 스테이지가 fail-open 처리 — 검증 책임과 graceful 책임의 분리.
- 회계 로그는 **관측이지 차단이 아니다** — 미반영이 있어도 `done` 부착을 막지 않는다. 발굴 없는/일부 실패한 분석의 렌더가 죽는 것이 더 나쁘다.
- 회계 로그 배치를 freeze 전멸 조기 return **앞**으로 — 전멸(= 가장 나쁜 경우)에도 로그가 남아야 한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 테스트 하네스 align 길이 확장 (30/40 → 90/90 프레임)**
- **Found during:** Task 1 (RED 하네스 작성)
- **Issue:** 플랜이 지정한 `_disc_item` 초(userSec 3.2 / refSec 2.9)가 `stage_env` 기본 align(`_quality_align(tu=30, tr=40)` @15fps → ref 2.67s)에서 G 경계 핀(`REF_BOUNDARY_PIN_S=0.5s`, 유효 rt 범위 [0.5, 2.17])에 걸린다. 그대로 두면 발굴 freeze 가 `ref_boundary_pin` 으로 제외돼 **조달 축을 잴 수 없다** (수리해도 (a) 가 계속 실패).
- **Fix:** `disc_env` fixture 에서만 `build_align` 을 `_quality_align(tu=90, tr=90)` (6.0s)로 덮어썼다. 원본 `stage_env` 및 기존 테스트 무접촉.
- **Files modified:** `backend/tests/phase35/test_compare_render_stage.py`
- **Verification:** RED 에서 (a) 가 `KeyError: 'discovery'`(= 조달 부재)로 실패 — 경계 핀 제외가 아니라 의도한 사유로 실패함을 확인. 수리 후 PASS.
- **Committed in:** `7ffc13bc` (Task 1 커밋)

**2. [Rule 2 - Missing Critical] 형상 위반 축(6번째 테스트) 추가**
- **Found during:** Task 2 (GREEN)
- **Issue:** 플랜 `<verification>` 4 와 위협 등록부 **T-ghs-01**(Tampering, disposition=mitigate)은 **형상 위반**을 네 실패 경로 중 하나로 명시하고 "테스트가 이를 강제하는가"를 요구하는데, 5축은 이 경로를 직접 재지 않는다. 읽기 실패 축은 같은 `except` 로 수렴할 뿐 **validator 가 실제로 경유되는지**(= 오염 payload 가 doc_like 로 새지 않는지)를 증명하지 못한다.
- **Fix:** `test_stage_malformed_discovery_never_reaches_renderer` 추가 — `pairSrc="align"`(enum 위반, 사칭 라벨) 항목이 들어오면 ① `"discovery" not in doc_like["result"]` ② discover freeze 0 ③ WARNING 존재 ④ discover mp3 S3 GET 0 ⑤ `done` 진행.
- **Files modified:** `backend/tests/phase35/test_compare_render_stage.py`
- **Verification:** 수리 전 `app.py` 상대 재실행에서 이 축도 `AssertionError: []` 로 실패(RED 성립) → 수리 후 PASS. phase35 129 passed.
- **Committed in:** `ccd8de84` (Task 2 커밋). **정직 박제:** 이 축은 RED 커밋(`7ffc13bc`) 이후에 추가됐으므로 원 RED 실행(4 failed / 1 passed)에는 포함되지 않는다 — 별도 재현 실행으로 RED 성립을 확인했다.

**3. [Rule 1 - Bug] 조달 블록 주석의 행 포인터 오기 교정**
- **Found during:** Task 3 (게이트)
- **Issue:** 조달 블록 주석이 coachAudio 처방을 `:4265-` 로 가리켰는데 조달 블록 삽입으로 그 블록이 `:4302-` 로 밀렸다. 리포 관행상 주석의 행 포인터는 탐색 좌표로 쓰이므로 틀린 포인터는 다음 사람의 재탐색 비용이다.
- **Fix:** `:4265-` → `:4302-`.
- **Files modified:** `backend/functions/pipeline/app.py`
- **Verification:** phase35 129 passed (코드 무변경, 주석만).
- **Committed in:** `4b3c5ad1`

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 missing critical, 1 bug)
**Impact on plan:** 스코프 확장 0. 1번은 플랜의 테스트 값이 하네스 기본 align 과 충돌한 것을 fixture 국소로 해소, 2번은 플랜 자신의 verification 항목을 충족, 3번은 주석 정확도. 산식·`compare_*`·프로덕션 데이터 전부 무접촉.

## Issues Encountered

- **RED 관측을 6축 전체로 확장하는 방법** — `git stash`/`reset` 은 금지(워크트리 stash 공유 사고 이력)라 수리본을 되돌리지 않고 RED 를 재현해야 했다. 해법: 스크래치 pytest 플러그인이 RED 커밋의 `app.py` 를 테스트 모듈명(`pipeline_app_phase35_compare_render`)으로 **선점 캐시**하면 `_load_module` 이 sys.modules 히트를 그대로 반환한다 → 현재 테스트 코드가 수리 전 스테이지를 상대로 돌아간다. 리포 무접촉, 산출물은 scratchpad(휘발).

## LLM 학습 영향

- **추론 호출 0** — Gemini(기계 눈) 0회 · Cerebras 0회 · Polly(TTS, 비-LLM) 0회. 이번 사이클은 코드 수리 + 테스트만이라 외부 모델을 한 번도 부르지 않았다. 플랜 예상(0)과 실측 일치.
- **학습 전송 0** — 어떤 사용자/영상 데이터도 외부 모델로 나가지 않았다. 테스트 fixture 는 전부 합성 값(합성 좌표·rid `r07`·임의 초)이며 실좌표·동작명·실 분석 ID 리터럴 0 (게이트로 확인).
- **누적 원장 기여 0행** — 눈 판정 원장(Phase22 씨앗)에 추가된 항목 없음.

## User Setup Required

None — 외부 서비스 설정 변경 없음. AWS/Firestore/RunPod 무접촉.

## Next Phase Readiness

**다음 1단계 = 새 Pod 실증 사이클 (스코프 밖 — belle 승인 필요).**

이 사이클이 증명한 것은 "운영 스테이지가 discovery 를 조달해 렌더러에 싣는다"까지이고, **실 doc 을 물고 실 GPU 에서 재렌더된 영상·카드**는 아직 없다. 승인은 산출물이 아니라 생산 경로에 붙는다는 원칙대로, 다음 실증 사양:

1. **Pod 요청** — belle 에게 GPU 모델 명시해 요청 (권장 = RTX 4090, EU-RO-1, 기존 네트워크 볼륨 재사용). 현재 Pod 는 08-14 심야 터미네이트 상태.
2. **재진입 6단계** — 메모리 `current-pod-mddy6gsqmt24ud.md` 절차 정본 (코드 동기 → bootstrap → 기동 → health 4항목 → `start_server.sh` md5 정본 대조 → **SSM `runpod-analyze-url` + Lambda env 새 proxy URL 재동기**).
3. **판정 재료** — 실제 `result.discovery` 보유 doc 을 재렌더하고 다음 셋을 회수: ① 실행 로그 `compare_render discovery 조달 n=…` + `[discover] rid=…` ② 리그 `[discover]` 항목 PASS 라인 ③ 영상 실물(발굴 정지 구간) + 카드 md5 대조.
4. **함께 처리할 별건** — 발굴 채택분 S3 업로드 + doc 갱신은 아직 보류 상태다 (`SUPPORT-SURFACE.md §5` 변경 목록). 이 사이클의 수리는 그 반영 사이클의 **선행 조건**을 채운 것이다 — 반영해도 재분석에서 살아남는다는 보증.

**알려진 한계 (정직 박제):**
- 신규 rid 발굴은 `markers = []` fail-open (doc records 에 없는 rid — di7 스펙). 표시 문법 보강은 별건.
- `peterpan` freeze 초가 align 클립 밖인 상류 의제(u8i)는 이 사이클 범위 밖 — 발굴 rt 도 같은 G 경계 핀을 공유하므로 그 의제가 풀리면 함께 재확인 필요.

## Self-Check: PASSED

- 파일 실재: `backend/shared/python/sunity_shared/firestore_admin.py`(`def get_analysis_discovery` 1건) · `backend/functions/pipeline/app.py` · `backend/tests/phase35/test_compare_render_stage.py` · 본 SUMMARY — 4/4 FOUND
- 커밋 실재: `7ffc13bc` · `ccd8de84` · `4b3c5ad1` — 3/3 FOUND, origin delta 0
- `git status --short backend/` 빈 출력 (미커밋 코드 변경 0)

---
*Phase: quick-260814-ghs*
*Completed: 2026-08-14*
