---
task: 260808-jix
type: execute
date: 2026-08-08
commits:
  - 503a5f83 (라이브러리화 — 프로토 3스크립트 본체를 sunity_shared/analysis 로 이동, byte-보존 게이트)
  - 0da12419 (계약 py측 — models/s3keys/firestore_admin/playback-url + contract.md §12.9)
  - e5ea6249 (deferred 스테이지 + 로컬 리허설 스크립트 + phase35 유닛 36)
  - 33b2d1cc (앱 — 단일 mp4 플레이어 + 폴백 강등 + 이중 발화 방지 분기)
key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/cue_text.py
    - backend/shared/python/sunity_shared/analysis/compare_render.py
    - backend/shared/python/sunity_shared/analysis/compare_align.py
    - backend/shared/python/sunity_shared/analysis/compare_verify.py
    - backend/scripts/verify_compare_stage_local.py
    - backend/tests/phase35/ (4 테스트 모듈, 36 케이스)
    - app/src/components/RenderedComparePlayer.tsx
  modified:
    - backend/functions/pipeline/app.py (cue_text alias + coach_audio 반환형 + compare_render 스테이지)
    - backend/functions/playback-url/app.py (asset 'renderedCompare')
    - backend/shared/python/sunity_shared/{models,s3keys,firestore_admin}.py
    - backend/scripts/{render_compare_prototype,p35_extract_align,verify_render_prototype}.py (얇은 CLI 래퍼)
    - docs/contract.md (§12.9 + asset 표 + changelog)
    - app/src/types/analysis.ts, app/src/lib/api.ts, app/src/app/analysis/result.tsx
---

# 260808-jix: Phase 35 앱 통합 — 합성 비교 영상 프로토 → 운영 승격 (3-way 계약 + 단일 mp4 재생)

## 한 줄

프로토 5편이 belle 판정을 통과한 렌더러를 byte-보존 라이브러리화해 Pod 분석 사후
스테이지(GPU align 재생성 → 렌더 → 리그 ALL PASS 만 doc 부착)에 배선하고, 앱
동작비교를 renderedCompare done doc 에서 단일 mp4 재생(큐 오디오·자막·틱 발화
구조적 OFF)으로 전환했다. 실 Pod E2E·시뮬 확인은 미검증 박제 (Pod 없음).

## 게이트 실측 표

| 게이트 | 판정 | 실측 (동사 = 재봤다) |
|--------|------|----------------------|
| Task 1-0 baseline 렌더 (리팩터 전, HEAD 코드) | PASS | elbow 59.87s / kipup 15.53s / pdshapefault 58.97s — epy v7 길이 재현, 리그 3×ALL PASS (A/A2/B/C/D/E/F 전건) |
| Task 1-7 byte-보존 cmp (리팩터 후 같은 커맨드 재렌더) | **PASS 3/3** | `cmp out_base.mp4 out_base_pre.mp4` → elbow(11474505B)·kipup(4038006B)·pdshapefault(11023055B) 전부 IDENTICAL. report JSON `diff` 3/3 무차이. stderr 로그(grip-fail-closed 라인)까지 동일 |
| 리팩터 후 리그 | PASS | 3편 전부 exit 0 (verify_render_prototype.py — 이제 compare_verify 라이브러리 경유) |
| 로컬 스테이지 리허설 (verify_compare_stage_local.py --motion elbow) | **PASS (exit 0)** | 실 `_run_deferred_compare_render` 경로 — mp3 4건 회수(r{NN}.mp3 계약) → 픽스처 align 주입 → 실렌더 59.87s → 리그 ALL PASS → put_object `results/.../compare_v1.mp4` → done 마킹(실 validator 통과). 캡처 mp4 를 ffmpeg 로 직접 열어 확인: 59.87s h264 1224x1080 30fps + aac 오디오 |
| phase35 유닛 | 36 passed | 게이트 스킵 3종(env/모드/프로브)·align 실패→failed·리그 FAIL→업로드 0·예외→failed·failed write 실패 무raise·성공 경로·계약 validator·재서명 가드·정렬 재계산 핀 |
| pytest 전체 baseline diff | **IDENTICAL** | FAILED/ERROR node-ID 59 == 59 (작업 전 캡처 vs 후), `59 failed, 3990 passed, 26 skipped` — 신규 실패 0, phase35 36 은 passed 로 추가 |
| 채점 무접촉 diff | **0줄** | `git diff --stat d6e32c4a..HEAD -- .../analysis/{deduction_engine,dimensions,kismam,motiondtw,temporal,features,assemble,selfmotion}.py` = 0, working-tree vs main 도 0 |
| 앱 typecheck + grep | GREEN | `tsc --noEmit` 무오류. `grep -c RenderedComparePlayer result.tsx` = 2, renderedCompare in analysis.ts:961 / api.ts:161 |
| 계약 3-way lockstep | 존재 | contract.md §12.9 ↔ models.py RENDERED_COMPARE_* ↔ analysis.ts RenderedCompare (상호 인용 각주) |
| 폴백 가지 diff 0 | PASS | result.tsx diff = 40 insertions / **0 deletions** — VideoCompare props byte-무접촉 (분기 래퍼만 추가) |

## 산출물 구조

- **라이브러리 4모듈** (`sunity_shared/analysis/`): `cue_text`(자막=음성 단일 문장
  소스 — pipeline path-exec 이중 로드 구조 제거), `compare_render`(build_timeline/
  render — doc/align dict 오버로드, FONT_PATH env override + 부재 raise),
  `compare_align`(build_align — rtmlib/cv2 lazy, infer_fn 주입 설계, moments/
  verify_dir 는 프로토 래퍼 전용 kwarg), `compare_verify`(리그 A/A2/B/C/D/E/F).
  프로토 스크립트 3종은 argparse + 라이브러리 호출만 남은 얇은 래퍼.
- **deferred 스테이지** (`pipeline/app.py::_run_deferred_compare_render`):
  spot_check 뒤 마지막 표현물 스테이지. 게이트 = env `RENDERED_COMPARE_ENABLED`
  kill-switch + mode1+ref 로컬 영상 + 능력 프로브(`_compare_render_capability` —
  rtmlib import + YOLOX/RTMW 가중치 실파일, Lambda CPU 경로 자동 스킵). align
  실패 = failed 마킹(doc 리포트 폴백 렌더 금지 — belle 반려 이력), 리그 전 항목
  PASS 아니면 S3 업로드·done 부착 없음. 전 경로 재raise 0, workdir finally 정리.
  `_run_deferred_coach_audio` 반환형 → `list[dict]`(additive — mp3 key 전달).
- **계약**: `result.renderedCompare {status: done|failed, key}` —
  `build_rendered_compare_key`(compare_v1.mp4) 단일 출처, `_validate_rendered_compare`
  (done→results/+.mp4, failed→key ''), playback-url asset `renderedCompare` =
  done + exact 이중 가드(H-02/V-0, 가드 위반 동일 404).
- **앱**: `RenderedComparePlayer`(mount 마다 asset 재서명, 실패 = onUnavailable
  강등) + result.tsx 분기 — done+key doc 은 VideoCompare 자체를 미렌더 = 큐
  오디오 prefetch·자막·재생바 틱 발화가 구조적으로 OFF. PartChipsRow·정렬
  배너는 분기 밖 현행 유지.

## Deviations from Plan

**1. [Rule 3 - 게이트 실행 방식] byte cmp 를 같은 출력 경로 + _pre 사본으로 수행**
- 이유: report JSON 의 `out` 필드가 절대경로라 파일명이 다르면(out_base vs
  out_ref) report diff 0 이 구조적으로 불가.
- 조치: baseline → `out_base.mp4`/`report_base.json` 렌더 후 `_pre` 사본 보존,
  리팩터 후 같은 경로로 재렌더 → `cmp`/`diff`. 게이트 의도(byte-동일) 보존.

**2. [Rule 1 - 테스트 명세 조정] 정렬 재계산 pairs 허용치 — r01 양자화 실측 반영**
- 발견: plan 은 전 pair |Δ|≤0.2s. 실측 = curveRefSec max|Δ| 0.0000s,
  r00/r02/r03 0.000s, **r01 만 2.133s** — 저장 kp 4자리/score 3자리 반올림이
  자세거리 min*1.15 밴드 소속(이산 선택)을 뒤집는 케이스.
- 검증: 리팩터 전 원본 코드(git 503a5f8~1)를 같은 rounded 입력에 재실행 —
  **이동 코드와 동일하게 10.200 산출** (차이는 순수 양자화 유래, 리팩터 무관 증명).
- 조치: r01 은 재계산 결정값 핀(10.200) + 선택 불변식(정렬창·밴드 내)으로 회귀
  고정. 실측 근거는 테스트 docstring 에 박제 ([[evidence-outranks-prior-decisions]]).
- 파일: backend/tests/phase35/test_compare_align_recompute.py

**3. [Rule 2 - 시그니처 보강] `_run_deferred_compare_render` 에 `mode` kwarg 추가**
- plan 의 kwargs 목록에 없었으나 게이트 (b) `mode == MODE_EXPERT` 판정에 필수.
  reference_local_video_path 존재만으로 우회 판정하지 않고 명시 전달.

**4. [Rule 2 - 방어 게이트 추가] local_video_path 부재 스킵**
- 이론상 도달 불가 경로지만(스테이지 도달 = 분석 완료 = 로컬 영상 존재) 부재 시
  명시 스킵 로그 — 조용한 예외 대신 게이트로.

**5. [Rule 2 - Lambda 레이어 안전] FONT_PATH lazy-safe 계산**
- `/opt/python/...` 얕은 계층에서 `parents[5]` 가 IndexError — import 시점이
  아닌 안전 함수(None 반환)로 계산하고 render() 진입 시 raise (스테이지 failed
  수렴). env `RENDER_FONT_PATH` override 우선.

## 미검증 표 (이유와 함께 박제 — 33 선례)

| # | 항목 | 이유 | 검증 경로 |
|---|------|------|----------|
| 1 | Pod 실분석 E2E (실 GPU align 재생성 + 렌더 + S3 업로드 + doc 부착) | Pod 없음 (pqe6uaw7mf8bh9 는 08-08 밤 종료 — [[current-pod-pqe6uaw7mf8bh9]]) | 아래 "Pod 재가동 시 검증 절차" (1)~(3) |
| 2 | 실기기/시뮬 단일 mp4 재생·폴백 전환·세션 중 도착(onSnapshot) 전환 UX | 시뮬 확인은 orchestrator 후속 ([[verify-ui-on-simulator-before-ota]] — OTA 는 이번 범위 밖, 발행 금지 준수) | 시뮬에서 renderedCompare done doc 열기 + 전환 시점 UX 관찰 |
| 3 | playback-url 'renderedCompare' 실배포 재서명 | sam deploy 전 (코드만 커밋) | deploy 후 done doc 으로 POST /playback-url 200 + 404 가드 실측 |
| 4 | Mode3 rendered compare | 의도적 범위 밖 (게이트 (b)가 구조 차단 — 상시 듀얼 플레이어 폴백) | 후속 phase 결정 |
| 5 | 리그 실 FAIL → failed 마킹 실경로 | 유닛은 mock verify — 실렌더 FAIL 재현은 결손 입력 필요 | Pod 절차 (4) |
| 6 | 스테이지의 실 S3 mp3 회수 (download_file) | 로컬 리허설은 스텁(로컬 파일 복사) — 실 GET 은 자격증명·버킷 필요 | Pod 절차 (3) 에 포함 |
| 7 | 자막 문장 lockstep 실검증 (운영 경로 문장 = 앱 자막 조립과 동일) | cue_text 이동은 문자 단위 동일(테스트 GREEN)이나, 운영 doc cueLine 기반 렌더 자막의 시각 확인은 실분석 필요 | Pod 절차 (3) 산출 mp4 를 직접 열어 자막 확인 |

## Pod 재가동 시 검증 절차

Pod 재생성/재가동(절차 = [[current-pod-pqe6uaw7mf8bh9]]) 후 이 순서로:

**(1) 코드·env 확인**
```
cd /workspace/SunityMotion && git pull
echo $YOLOX_ONNX_PATH $RTMW_ONNX_PATH   # 실파일이어야 능력 프로브 통과
ls -la /workspace/yolox_weights/yolox_m.onnx /workspace/rtmw_weights/rtmw-x-384.onnx
echo ${RENDERED_COMPARE_ENABLED:-unset}  # unset 또는 != "0" = ON
```
판정: 가중치 2파일 존재 + env 미설정/1. (끄려면 `RENDERED_COMPARE_ENABLED=0`.)

**(2) 실 GPU align 경유 리허설 (스텁 없는 이중 용도 경로)**
```
cd /workspace/SunityMotion && python3 backend/scripts/verify_compare_stage_local.py \
  --motion elbow --sp /workspace/p35 --build-align
```
판정: exit 0 = `STAGE_LOCAL_VERIFY: PASS (리그 ALL PASS + done 마킹)` — 실
build_align(15fps RTMW 재추출+DTW)이 돈다. 로컬 리허설과 달리 능력 프로브도
실판정. (주의: /workspace/p35/{motion}/ 에 user.mp4·ref.mp4·audio/r{NN}.mp3
필요 — 볼륨 보존분 또는 README S3 키 표에서 회수.)

**(3) 실분석 1건 E2E**
- Mode1 픽스처 업로드(앱 또는 시뮬 — elbow 계열이 검증 밀도 최고: 폴 문법
  + 4정지) → 분석 완료 대기.
- Firestore doc 확인: `result.renderedCompare == {status:'done', key:'results/{uid}/{analysisId}/compare_v1.mp4'}` +
  S3 에 그 키 객체 존재(크기 >1MB) + Pod 로그에 `compare_render done ... freezes=N`.
- 앱(시뮬)에서 그 결과 화면: 동작비교 = **단일 mp4 재생** (듀얼 플레이어·오버레이
  토글 없음), mp4 소리 = 코칭 음성, **앱 큐 오디오 미발화**(이중 발화 0 — 정지
  구간에서 소리가 겹치지 않는지 청취), 자막은 영상 안에만.
- 산출 mp4 를 직접 열어(playback-url 서명 URL) 자막 문장이 감점 카드 문장과
  일치하는지 확인 (미검증 #7).

**(4) 리그 FAIL 강제 → failed 마킹·앱 폴백**
- 방법 = **결손 입력** (임계 임시 조정 금지): 예로 Pod env `RENDER_FONT_PATH=/nonexistent`
  로 1건 분석 → render 가 폰트 부재 raise → 스테이지 failed 수렴.
- 판정: doc `renderedCompare == {status:'failed', key:''}` + 분석 자체는
  status='done' 무훼손(점수·카드 정상) + 앱은 기존 듀얼 플레이어 폴백 렌더.
- 확인 후 env 원복 (다음 분석은 done 경로).

**(5) Lambda(비위임) 경로 자동 스킵**
- RunPod 위임 OFF 상태의 Lambda 직접 처리 1건(또는 CloudWatch 로그 소급):
  `compare_render 스킵 (추출 능력 프로브 미충족 — Lambda CPU 경로 등)` 로그 존재
  + doc 에 renderedCompare 필드 자체 부재(무접촉 스킵).

## Known Stubs

없음 — 이번 범위의 스텁은 검증 스크립트(verify_compare_stage_local.py)의 의도적
주입 지점(픽스처 align/FakeS3)뿐이며 운영 코드 경로에는 스텁·플레이스홀더 0.
앱 분기는 실데이터(doc renderedCompare) 기반 — done doc 이 없으면 기존 경로
그대로다 (기능 부재가 아니라 하위호환 폴백).

## Self-Check: PASSED

- 파일 존재: compare_render/compare_align/compare_verify/cue_text.py,
  verify_compare_stage_local.py, tests/phase35/ 4모듈, RenderedComparePlayer.tsx — 전부 FOUND
- 커밋 존재: 503a5f83 / 0da12419 / e5ea6249 / 33b2d1cc — git log 확인
- 산출물 직접 열람: 스테이지 캡처 mp4 (59.87s h264+aac) ffmpeg 로 스트림 확인
