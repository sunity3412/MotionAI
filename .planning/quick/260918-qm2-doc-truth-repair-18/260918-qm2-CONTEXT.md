# Quick Task 260918-qm2: 문서 진실 수리 + 미종결 트랙 판정 원장 — Context

**Gathered:** 2026-09-18
**Status:** Ready for planning

<domain>
## Task Boundary

정리 2차. 1차(260918-k06)에서 착수점을 4개→1개로 합치고 STATE 원장 누락 46건을 복구했다.
이번은 **문서가 코드와 어긋난 18곳을 고치고**, **미종결 트랙을 판정해 원장에 박는 것**이다.

실측 원문 = `260918-qm2-FINDINGS.md` (에이전트 6대, 파일:줄번호 첨부). **그 판정을 다시 하지 마라.**
여기 적힌 것은 이미 belle 승인 범위이고, 비평가 반려까지 반영된 최종안이다.

**범위 밖 (손대지 마라):**
- `app/` 와 `backend/` 의 **소스 코드** — 단 주석/docstring 정정 3건은 예외(아래 A-11, A-18 명시)
- `backend/template.yaml` — sam deploy 차단 건은 belle 판정 대기다. 고치지 마라.
- 죽은 코드 제거 — belle 이 "목록만"이라 했다. 제거하지 마라.
- 메모리 디렉터리(리포 밖) — 메인 세션이 갱신한다.

</domain>

<decisions>
## 묶음 A — 문서 18곳을 코드와 일치시킨다

FINDINGS 의 `w1:문서어긋남` 18항목이 전부 `before → after` 로 적혀 있다. **그대로 적용하되,
아래 2건은 비평가가 반려했으므로 수정된 문구로 적용한다.**

### ★ A-4 반려 — `docs/reference-motions.md` §6 등록 절차

원안(7단계: `S3 → seed(메타) → reprocess --no-flip → backfill --write-candidate → promote`)을
**그대로 쓰면 새 기준 모션이 망가진 기질로 등록된다.** 비평가 지적 3가지를 반드시 반영하라:

1. ★ **`ROT180_INVERSION_ENABLED=1` 이 빠져 있다.** 이 플래그는 RTMW 엔진이 런타임 env 로만
   읽고 코드 기본은 off 다(`rtmw_engine.py:62-66`). 현행 활성 기질 `rot180_v1` 은 이 플래그가
   켜진 상태로 추출된 것이다. 안 켜고 돌리면 **신규 1편만 비회전 각도로 들어가 11편과 기질이
   섞이고**, 그 비대칭의 실측 결과가 **정은지 자기비교 100 → 60** 이다
   (`backend/runpod_inference/start_server.sh:24` 가 같은 경고를 적어놨다).
   → 절차의 reprocess 단계에 이 env 를 **명령줄에 박아서** 쓰고, 왜 필요한지 한 줄 주석을 달아라.
2. **이미 배포된 `POST /reference/auto-register` 를 언급하지 않았다.** 이 엔드포인트는 Gemini A 로
   메타(motionId/clipRange/checkpointJoints)를 자동 생성해 upsert 한다
   (`backend/functions/reference-auto-register/app.py`, `template.yaml:298-299` 라우트 배포됨).
   다만 **name·athleteName·level 을 안 쓰므로 앱 선택 화면에는 안 뜨고, angles 도 안 만든다** —
   즉 이것만으로 등록이 완결되지 않는다. 절차에 이 사실을 정확히 적어라.
3. **Phase 21(프로 셀프서비스 기준 등록, belle 2026-08-30 요구사항)이 바로 이 수동 절차를
   없애려는 트랙이다.** §6 머리에 "이 절차는 잠정이다 — Phase 21 이 자동화를 목표로 살아 있다"를
   한 줄 적어, 수동 런북이 정본으로 고착되지 않게 하라.

### ★ A-9 반려 — Pod 종료 절차의 Lambda 되돌리기

원안("Lambda `RUNPOD_ANALYZE_URL` 을 제거한다")은 **관측은 맞으나 처방이 틀렸다:**

- **지워도 분석은 살아나지 않는다.** URL 이 비면 `lambda_handler` 가 로컬 `_process` 로 가는데
  그 경로는 배포 환경에서 **ImportError 로 의도적으로 차단**돼 있다
  (`backend/functions/pipeline/requirements.txt:1-4`). 사용자 결과는 양쪽 다 `server_error` 다.
- **SSM 파라미터를 비우는 것은 실행 불가에 가깝다.** 해당 파라미터는 `Type=String` 이라 빈 값을
  못 넣고, `template.yaml:342/481` 이 배포 때 `{{resolve:ssm:...}}` 로 이 이름을 해석하므로
  삭제하면 다음 `sam deploy` 가 그 자리에서 깨진다.

**→ 고쳐 쓸 문구:** 종료 절차에 한 줄을 넣되 내용은
"**Lambda `RUNPOD_ANALYZE_URL` 을 자리표시자로 되돌린다**(값을 지우거나 SSM 파라미터를 삭제하지 말 것).
그리고 **Pod 이 없으면 분석은 어차피 실패한다** — URL 을 비워도 CPU 폴백은 ImportError 로 막혀 있다."
적용 대상 3곳: `.claude/commands/start.md:99`, `.planning/.../POD-RUNBOOK-2026-09-06.md:59`
(정확한 파일은 grep 으로 찾아라), 그리고 리포 안의 관련 런북.

### 나머지 16건은 FINDINGS 원장 줄 그대로 적용

A-1 CLAUDE.md:48/140/144 포즈 엔진 · A-2 `.planning/PROJECT.md` + `codebase/STACK.md` +
`ARCHITECTURE.md` (CLAUDE.md 자동생성 원본) · A-3 reference-motions §5 를 5편→11편 ·
A-5 §3 스키마 snake_case→camelCase · A-6 §4 사문 규칙 삭제 — **단 비평가 정정: `clipRange` 는
살아 있다**(`pipeline/app.py:7989-7993` 공유 베이스 경계, `referenceMotions.ts:178`,
`analysis.ts:1217`). 규칙 1 은 **삭제가 아니라 "실제 소비처는 공유 베이스 경계 한 곳"으로 정정**하고,
소비처 0 인 checkpoints 가중평균·heroFrameUrl 만 지워라 ·
A-7 §7 ViTPose 검증 2항목 삭제 · A-8 DEMO-CARD 죽은 Pod → 빈칸 + 시간 모순(25초/156초) 정리 ·
A-10 design.md 배너 + 낡은 표기 · A-11 `app/src/types/analysis.ts` 주석 4곳 ·
A-12 `ml/ml_CLAUDE.md` · A-13 `docs/contract.md:38` · A-14 CLAUDE.md §5 의 없는 파일 3개 ·
A-15 `app/CLAUDE.md` 차트 라이브러리(설치하라는 두 패키지가 리포에 없다) ·
A-16 `backend/runpod_inference/README.md` — **단 "기본 ON" 이라 쓰지 마라. 코드 기본은 여전히 off 이고
ON 은 `start_server.sh:24` 한 곳뿐이다.** "2026-09-17 이후 운영 Pod 에서 ON" 이라고 정확히 써라 ·
A-17 `docs/runpod-fast-restart.md` 사문 배너 · A-18 `pose_engines/__init__.py:6` docstring

## 묶음 B — 미종결 트랙 판정을 원장에 박는다

FINDINGS 의 판정을 원장에 반영한다. **★ 비평가 반려: "완료"를 "죽었다"로 쓰지 마라.**
과제가 준 정의는 죽었다 = 사문·상위결정 기각·기능제거이고, **완료는 그 셋 중 아무것도 아니다.**
원장에 "죽었다"로 적으면 belle 이 "Qwen3-VL-8B 백본 결정이 기각됐다"로 읽는다.
→ 22-06 과 36-01 은 **"완료(원장 표기만 누락)"** 로 적어라.

| 대상 | 판정 | 원장 표기 |
|---|---|---|
| debug `illustration-slot-crop` | 사문 | 일러스트 전면 제거(2026-08-24 `fb2eef19`)로 표면 소멸 + 문서 자신의 Resolution 이 오측 판정 |
| debug `viewer-axis-flat-skeleton` | 사문 | 축 버그는 `89402fc5` 수리, 카드를 쓰던 ReferenceCornerSection 은 09-09 `aadf0375` 철거 |
| debug `kipup-split-injection-lost` | 해소 | 요청된 combined 라우팅 fix 가 같은 날 `3399fd78` 적용, enum 1순위 `e697364e` 추가 |
| debug `recognizer-ipsf-fallback` | 해소 | REGISTERED_MOTIONS 10개 + yaml 전수 생성, 인식기 상시 gemini. EXTEND 부재는 belle 06-27 결정 |
| debug `inversion-joint-attribution` | **살았다** | 마커 배선 완료. 남은 것 = 회전 ON 이후 발화 재측정(초과 관절 8→2, 임계는 5) |
| debug `ref-student-substrate-gap` | **보류** | 비대칭은 09-17 묶음으로 해소. 남은 것 = elbow-twist 학생 ON 재분석 1편(Pod 필요) |
| 22-06 | **완료** | bake-off 실행 완료(Qwen3-VL-8B CONFIRMED, belle 2026-07-13, 산출물 2/2 커밋). SUMMARY 만 미작성 |
| 22-08 / 22-09 / 22-10 | 보류 | 미착수(artifact 부재, 운영 참조 0건). 재개 조건 = `promotion_ledger.current` 가 null 을 벗어나는 것 + RunPod 충전 |
| 31-12 | 사문 | belle 2026-07-20 축소마감(31-CLOSEOUT)이 원 플랜 기각 + CALIBRATION `blocked:true` + 09-09 재디자인이 앱 소비처 제거 |
| 33-07 | 사문 | flip 은 09-17 `rot180_v1` 로 실행됨(`02b1155a`). 잔여 = 기준 18fps vs 학생 9fps |
| 33-16 | 사문 | 게이트 대상 화면이 08-24 일러스트 제거 + 09-09 4탭 재디자인으로 소멸 |
| 33-21 | 사문(no-op) | 33-06 elbow-twist 여유 +3.10 ≥ +2.0 이라 플랜 자신이 규정한 no-op |
| 36-01 | **완료** | 실행 완료(`f957bad9`). 전제는 belle 2026-09-01 로그인 게이트 결정으로 대체 |
| 36-02 | **살았다** | 코드는 배포됨(`41fa1abd`). 남은 것 1건 = belle 실계정 로그인으로 linked/uid 유지 실측. 파일럿 비차단 |
| 36 카카오·네이버 | 보류 | belle 2026-08-31 "출시 준비 때". 버튼 미렌더, `POST /auth/social` 배포 라우트 0 |

### ★ 비평가가 새로 찾은 것 — 이것도 원장에 넣어라

| 대상 | 판정 | 원장 표기 |
|---|---|---|
| **ROADMAP 미체크 29건 중 14건** | 표기 누락 | SUMMARY 가 디스크에 실재하는데 체크박스만 안 찍힘: 01-23/24/25 · 05-03/04/05 · 12-01/02/03 · 23-03 · 24-03 · 25-01 · 25-04 · 32-15. **각 항목을 `- [x]` 로 찍어라.** 진짜 미체크는 22-06/08/09/10 · 31-12 · 33-07/16/21 · 36-01/02 와 TBD 4줄뿐 |
| **Phase 35** | 사문(표기 낡음) | ROADMAP 은 "0 plans / 미착수"라 적는데 합성 mp4 경로는 이미 배선·운영 중(`result.tsx:1720` RenderedComparePlayer). quick 트랙으로 우회 완료 |
| **Phase 18** | 보류 | `backend/evals/phase18/` 에 baseline·assert 실재. 남은 것 = Pod live sweep + sensitivity 셋 — **SCORE-09 잔여와 같은 물건** |
| **Phase 21** | **살았다 · 파일럿 Step 2 직결** | belle 2026-08-30 요구사항. 정은지 촬영 → 자동 등록. A-4 의 수동 절차가 이 트랙이 없애려는 것 |
| **REQUIREMENTS.md Pending 17건** | 재판정 필요 | 아무도 안 열어봤다. **SCORE-09 는 belle 지시로 열려 있고**(STATE 두 곳이 "Phase 23 을 SCORE-09 미처리로 닫지 말 것"이라 못박음), **SCORE-10 은 이미 구현 완료인데 Pending** (`deduction_engine.tally` 실재, `vision_veto.SEVERITY_CAP`·`apply_downward_cap` 코드에서 소멸). SCORE-10 을 Complete 로 고치고, 나머지 16건은 "재판정 대상"으로 표시만 하라 — 전수 판정은 이번 범위 밖 |
| **플라이휠 크롭 반출 7사이클 0** | 정상 | 반출기 고장 아님 — `admit && !uploaded` 행만 올리는데 admit 104건이 전부 uploaded 라 pending=0. **진짜 미결은 09-14 재판정이 admit→hold 로 강등한 40건이 `uploaded=True` 인 채 S3 에 남아 있는 것**(해제 경로 코드에 0건, 그중 1건 사유가 `customer_anonymize_required`). 그리고 신규 63행 전량 hold — 눈 트랙 재료는 08-26 이후 증가 0 |

## 묶음 C — belle 판정 대기로 남길 것 (고치지 마라, 기록만)

1. ★ **`sam deploy` 가 지금 불가능하다.** Default 없는 파라미터 5개
   (VisualInputBucketName · DisplayJudgeConfidence · TrainingJudgeConfidence ·
   DisplayPoseTolDeg · TrainingPoseTolDeg — **전부 죽은 Phase 31 것**)에 `samconfig.toml` 의
   `parameter_overrides` 가 값을 안 준다(Stage·VideoBucketName·FirebaseSaParam 3개뿐).
2. **`template.yaml:29-40` 의 `RunpodAnalyzeUrl`/`RunpodAuthToken` 파라미터는 참조 0 의 사문**인데,
   설명문이 "URL 이 비면 PipelineFunction 이 자체 NLF 추론 시도(폴백)"라고 **두 번 틀리게** 가르친다
   (백본은 RTMW 로 바뀌었고 그 폴백은 ImportError 로 막혀 있다). A-9 오해의 근원이다.
3. **배포 스택이 리포보다 1커밋 뒤에 있다** — 스택 2026-07-21, template 마지막 커밋 2026-07-22.
   그래서 32-16 이 넣은 `polly:SynthesizeSpeech` 권한이 배포본에 없다. 지금 안 깨지는 이유는
   실분석이 Pod 에서 돌고 Pod 이 자기 AWS 키로 Polly 를 부르기 때문이다.
4. **배포 스택·Lambda env·SSM 이 서로 다른 Pod 세대를 가리킨다** — 스택 파라미터 `p56qusi8cgc91z`,
   Lambda env 와 SSM `elevev58iv4mox`(오늘 종료됨). 누가 `sam deploy` 를 하면 어느 값이 남는지 예측 불가.
5. **죽은 코드 목록** — FINDINGS 의 `죽은코드` 절 전체. 앱 고아 16파일 3,707줄, 즉시 제거 후보 2,991줄,
   3D 스택 제거는 OTA 가 아니라 **네이티브 재빌드**다. `DeductionCard` 는 죽은 게 아니라
   **'강사님께 물어보기' 기능 소멸의 물증**이라 별도 판정 대상.

이 5건은 **새 문서 `260918-qm2-BELLE-JUDGMENT.md` 에 모아 쓰고**, 착수점 인계서
(`.planning/quick/260918-day-closeout/HANDOFF.md`)에서 그 파일을 가리켜라.

### Claude's Discretion

- 각 문서의 정확한 문장 표현
- 원장 표의 열 구성
- ROADMAP 체크박스 14건을 한 커밋으로 묶을지 나눌지

</decisions>

<specifics>
## Specific Ideas

- **정정은 삭제가 아니라 정정으로.** 이 저장소는 "왜 그렇게 판단했나"의 이력을 중요하게 다룬다.
  사문 문서는 지우지 말고 상단에 배너를 붙여라.
- **이모지 금지** (CLAUDE.md §7). 슬롭 금지.
- 커밋은 묶음별 원자 커밋. `app/`·`backend/` 소스 변경은 주석 정정 3건(A-11, A-16, A-18)뿐이어야
  하고, 그 외 코드 diff 가 나오면 잘못된 것이다.
- **게이트를 깨지 마라** — 백엔드 4835 passed / 앱 tsc clean 이 현재 기준선이다. 문서·주석만
  고치므로 깨질 이유가 없지만, 끝나고 확인은 메인 세션이 한다.

</specifics>

<canonical_refs>
## Canonical References

- `260918-qm2-FINDINGS.md` — 실측 원문(에이전트 6대, 파일:줄번호). **판정 근거는 전부 여기 있다.**
- `CLAUDE.md` §5 · §7
- `.planning/STATE.md` — 원장 정본 (1차 정리에서 단일 표로 합쳐 날짜순 정렬됨)
- `.planning/quick/260918-day-closeout/HANDOFF.md` — 단일 착수점

</canonical_refs>
