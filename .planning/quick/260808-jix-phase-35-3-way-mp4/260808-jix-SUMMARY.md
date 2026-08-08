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

## 실 E2E 라운드 (2026-08-08 오후 — orchestrator 수리 사이클)

**대상**: uid=fvcNXzEqKjgqVxRPVSj1iwFnIpn2 / analysisId=2fe3ae94cc584b58a850968dd2ab0951
(시뮬 실업로드 엘보 72점 — 08-06 픽스처 재분석과 동점 = 채점 재현성). 스테이지는
계약대로 방어: 리그 FAIL → `renderedCompare {status:'failed', key:''}` 실기록,
앱 폴백 정상. 추가 커밋: d48575a(아티팩트 보존) / eec0102(Pod 드라이버) /
4decd09(수리 3건).

### 수리 커밋과 실측 근거 (추측 수리 0 — 전건 아티팩트 실측 후)

| 항목 | 원인 확정 (동사 = 재봤다) | 수리 | 재검증 |
|------|--------------------------|------|--------|
| 아티팩트 소실 | 리그 FAIL 시 tempfile workdir 정리로 mp4·report·align 소실 — 첫 E2E 진단 불가 | FAIL·예외 경로만 `/tmp/compare_fail_{analysisId}` 로 이동 보존(재시도 덮어씀) + align/report.json 을 workdir 에 즉시 기록. done = 현행 즉시 정리 | 유닛 3건 + Pod 실FAIL 에서 보존 실작동 (`/tmp/compare_fail_2fe3…` 생성 확인) |
| D 재생 무음 FAIL (-24.6dB @0.2s) | mp4 재생 구간은 전부 무음 실측(음성 전 0.2~0.45s **-91dB** / 정지-간 **-91dB** / tail **-120dB**) — 첫 정지가 이른 편(voice 0.47s)에서 C/D probe 창(0.2s+0.8~1.0s)이 음성 구간 침범 | 침범 시에만 첫 재생 갭(≥1.5s)+0.3s 로 probe 재배치 — 판정 기준(<-70dB) 불변 = 완화 아님 (E 의 "이른 첫 정지 창 이동" 계열) | 픽스처 3편 리그 무변경 ALL PASS(침범 없음 — 재배치 미발동) + 신선 mp4 GPU 재렌더 **D PASS(-91.0dB @12.3s)** |
| "Mean of empty slice" 경고 | `_spread_series` 스무딩 nanmean 이 전량-NaN 창에서 RuntimeWarning (결과는 어차피 NaN) | 유효값 합/개수 등가 계산 — 경고 0, NaN fail-closed 유지 | **byte 게이트 2차 3/3 IDENTICAL** (cnt>0 열 부동소수 연산 순서 동일 실증) + 경고 0건 |
| 드라이버 CPU 폴백 | torch 미로드 프로세스에서 ORT CUDA 가 libcudnn.so.9 미발견 → CPU align (E 13% vs 서버 GPU 28% — align 이 달라짐) | 드라이버 torch 프리로드 (서버 등가 조건) | GPU 재실행이 서버 실측(28%)을 정확 재현 |

### E 저더 ref 28% — 원인 확정, 수리 보류 (orchestrator 판정 대상)

**실측 체인** (GPU-parity 재실행 아티팩트, `scratchpad/e2e_fail_gpu/`):
- E 창(out 70.81~73.31 = user 13.41~15.91)은 정렬곡선의 **slope 0.656 단일 구간**
  (user 10.13~16.47) 위 — 30fps 출력에서 ref 프레임이 3~4장마다 1장 반복.
- 중복 패턴 = `D...D.D..D…` — **연속 run 최장 1** (균일 저속). v1 반려 실증상
  (가다-서다 = 클러스터 정지, 8/62)과 기계적으로 다른 패턴.
- 원곡선에 플래토 0 (최장 slope<0.1 run = 0프레임) — "곡선 평탄 구간" 가설 기각.
  DTW 가 정당하게 만든 저속 워프다 (user 가 ref 보다 빠르게 수행한 구간).
- **승인 픽스처 5편의 같은 문법 실측**: 전 재생 구간 인덱스 중복률 elbow 16.1%
  (min slope 0.730 — 신선 doc 와 같은 값대), pdshapefault **23.9% (min slope
  0.102)**, powerspin 7.8% — 전부 belle 5라운드 승인 렌더. E 가 픽스처에서 PASS
  한 것은 창이 head/고속 구간에 착지한 표집 우연 (elbow 픽스처 창 3%).

**결론**: 렌더러는 승인 문법 그대로다. E 의 window-rate 메트릭이 "승인된 균일
저속"과 "반려된 클러스터 정지"를 구분하지 못하고, 신선 doc 에서 창이 저속 구간에
착지해 FAIL 났다. **리그 완화 금지 제약에 따라 E 는 무변경** — 게이트 법대로
doc failed 유지(앱 폴백 정상). 처분 선택지 (orchestrator/belle 판정):
1. GPU FAIL mp4 직접 시청 판정 — `scratchpad/e2e_fail_gpu/compare.mp4` (12.6MB,
   회수됨). 균일 저속이 체감 저더인지 belle 기준으로.
2. E 메트릭 정련 — 클러스터 판별(연속 중복 run ≥2 비율)로 교체: v1 반려는 잡고
   승인 문법은 통과. 단 pdshapefault 승인 렌더에 slope 0.102 구간(연속 run 발생
   가능)이 있어 승인 5편 + 신선 doc 전건 재검증 필요.
3. 렌더러 저슬로프 프레임 블렌딩 — 중복 자리를 이웃 보간으로. 승인 픽스처에도
   중복이 있어(16~24%) **승인 렌더 byte 불변 제약과 원리적 충돌** (전량 재렌더
   + belle 재승인 전제).

### 이 라운드의 미검증

| 항목 | 이유 |
|------|------|
| ~~`--write` 실마킹~~ | **해소** — E 지표 정련(아래 절) 후 GPU 리그 ALL PASS → `--write` 완료 (doc done + S3 부착 검증) |
| ~~E 처분~~ | **해소** — orchestrator 처분 ② (E 지표 정련) 결정·구현 완료 |

## E 지표 정련 (orchestrator 처분 ② — 커밋 a12e0fd)

**결정 근거**: 구 E(임의 2.5s 창 표집, 반복률 ≤15%)는 승인 5편이 전 구간 16~24%
균일 저속(run=1) 문법을 보유한 것을 창 착지 운으로만 통과시키고, 같은 문법의
신선 doc 을 FAIL 시킨 결함 판정기 — v1 증상(클러스터)으로의 교정 + 표집 운
제거(전 구간 스캔 = 강화)이지 완화가 아니다.

**새 산식 (E v2)**: 전 재생 구간(freeze/fade margin 0.3s 제외) 30fps 전수 스캔,
좌/우 패널 각각 —
```
정지 이벤트 = dup(diff<0.05) 최대 run 중
              · 길이 2..5 프레임 (67~167ms)
              · 양옆 인접 전이가 실모션 (diff ≥ 0.5)
FAIL       = 어느 2.0s 슬라이딩 창에 정지 이벤트 ≥ 4
```

**상수 근거 (전부 구조 유도 — compare_verify.py STUTTER_* 주석 박제)**:
| 상수 | 값 | 근거 |
|------|----|------|
| dup 임계 | 0.05 | v1 승계 (동일 인코드 프레임 ≈ 0) |
| 실모션 하한 | 0.5 | dup 임계 ×10 — C 재생 동적성의 decade-분리 구조 승계. 스틸 플리커(승인 pdshapefault 헤드 실측 이웃 0.05~0.06)는 '가다' 불성립 |
| run 대역 | 2..5 | run1(33ms) = 풀다운 계열 비가시 — 승인 코퍼스 지배 성분(elbow 56·fresh 62 전부 run1). run≥6(≥200ms) = '멈춤/스틸' 의미론 (승인 pdshapefault 크롤 run7·9) |
| 창/횟수 | 2.0s / 4회 | 승인 코퍼스 실측 상계 = 3회(powerspin 꼬리·pdshapefault 헤드 — 0.4s 경계 정착 버스트, belle 승인 렌더) 초과 & v1 케이던스(hold2~3+move2~3 = 초당 5~7회 → 2s 창 10회+)의 1/2.5 이하 최소 정수 |

**3겹 검증 (전건 PASS 후 --write — 요건 순서 준수)**:
| 게이트 | 판정 | 실측 |
|--------|------|------|
| (a) 승인 5편 전 구간 스캔 | **ALL PASS** | elbow 0/0 · kipup 0/0 · pdshapefault ref 3이벤트/최악3 · powerspin(v7) ref 3/3 · peterpan(v7) 0/0 — 전부 임계 4 미만 (실측 여유 = 승인 버스트가 정확히 상계) |
| (b) 신선 doc GPU 재실행 리그 | **ALL PASS** | A/A2/B×5/C/D×5(D-무음 -91dB @12.3s 재배치)/E user·ref 0이벤트/F 전건 — --write 실행 내 전 판정 |
| (c) 합성 클러스터 역검증 | **10/10 GREEN** | v1형 케이던스(hold3+move2·hold2+move3) 합성 mp4 end-to-end = **정확히 E 로만 FAIL**(타 항목 PASS), 균일 슬로모 mp4 = ALL PASS. 순수 코어 8케이스(경계 정착 3회 PASS 핀·스틸 크롤 PASS·플리커 비이벤트·가장자리 제외) |

**--write 결과 (2026-08-08 08:04 UTC)**:
- doc `result.renderedCompare` = `{status:'done', key:'results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/2fe3ae94cc584b58a850968dd2ab0951/compare_v1.mp4'}` — canonical **exact match TRUE** (Pod 에서 Firestore 실조회).
- S3 객체 실존: **12,613,270 bytes / video/mp4** / LastModified 2026-08-08 08:04:23+00:00 (head_object 실측).
- 시뮬 단일 mp4 재생 확인 = orchestrator 후속.

**회귀 유지**: 렌더러 byte 불변 (`git diff 4decd09..HEAD -- compare_render/compare_align/cue_text` = 0줄 — byte 게이트 2차 결과 유효 승계), 채점 diff 0 (누적), pytest FAILED/ERROR node-ID baseline IDENTICAL, phase35 46케이스 GREEN.

## 렌더 방어 라운드 (2026-08-08 밤 — belle 실기기 pdshape 반려)

**배경**: belle doc `127a2a90c1d74c62ad61270eb3fe5625` (ref-pdshape, 20.2s) —
records 2건이 영상 끝자락(이탈 국면, at 17.56/17.78), ref 짝도 ref 끝(16.4~16.6s).
motionAlignment `tier=trim_only reason=low_global_confidence`. belle: "어떤
지점에서 뭘 말하는지 모르는 수준". 원칙: **승인(v7급) 못 미치면 렌더 미출하** —
채점 수술(측정창·좌우)은 Phase 34, 이 라운드는 렌더 계층 fail-closed 만.
커밋: ddb4145(방어 4) / eaa2426(방어 2) / fee6aad(드라이버 로그 가시화).

### 투입된 방어 (2/4종 — 2·4)

| 방어 | 구현 | 검증 실측 |
|------|------|----------|
| **2. 정렬 강등 스킵** | doc `motionAlignment.tier != 'warped'`(trim_only/disabled/부재/오염 = 저신뢰 계열) → 스테이지 진입 스킵, **필드 미기록** = 앱 듀얼 폴백 | belle doc Pod no-write 재현: `INFO compare_render 스킵 (motionAlignment tier=trim_only — warped 아님…)` + 마킹 0 + 리그 미도달. 유닛 4형상 |
| **4. 진품 판정 리그 H** | H1 정지 **rid 집합** 회계(수 아닌 동일성 — 통째 삽입이 1==1 로 지나친 유닛 실측 후 강화) / H2 정지 순간 == doc·align 측정 순간(±0.2s, 끝 클램프 미러, align-peak·align-pole 승인 이동 문법 면제) / H3 구운 자막 == cue_text 조립문·오버라이드 문자 일치 / H4 음성 rid == 그 분석 coachAudio 조인. 운영 스테이지는 doc/align 상시 전달 | v7 통째 삽입 시뮬 = H1·H2·H4 **다축 동시 FAIL** (유닛 11) + 승인 5편 리그(H 포함) ALL PASS + 렌더러 no_mp3 제외 회계(`report.excludedFreezes`) 신설에도 픽스처 mp4 **byte 불변 3/3** |
| (부속) freeze 전멸 스킵 | 제외 회계로 렌더 대상 0 = "표현할 것 없음" — failed 아닌 **필드 미기록**, 리그 미도달 | 유닛 (verify 호출 0·마킹 0 assert) |

**belle doc 사후 조치**: 반려된 렌더가 doc 에 `done` 으로 남아 있었음(실측) —
원칙 적용으로 `failed(key '')` 강등 (Pod 실쓰기, before/after 실측: done→failed,
분석 본체 status=done·72점 무훼손). belle 앱은 그 doc 에서 듀얼 플레이어 폴백.

### 방어 1·3 (홀드-내 판정 / 의미 축 G) — STOP (승인 코퍼스 실측 기각)

지정 산식(스크린 v1 에너지 p60+이동평균, 관대 파라미터)으로 승인 코퍼스 전수 실측:

| 픽스처 (승인 렌더) | freeze 홀드-내 (u∧r, p60) | 비고 |
|--------------------|---------------------------|------|
| elbow | **0/4** | r03·r02 만 u-측 O, ref-측 전건 X |
| kipup | **0/1** | 승인 피크 1.47s = 킵업 아펙스(스윙 중) — 홀드 원리적 불성립 |
| pdshapefault | **0/4** | |
| powerspin | **0/2** | **ref 홀드 자체가 0개** (스핀 — 저에너지 1s 지속 구간 부재) |
| peterpan | **0/1** | **user 홀드 자체가 0개** |

기각 근거 (fixture curve-fit 아님 — 전제 자체의 반례): 승인 표시 문법이 **피크·
폴-접촉 순간**(align-peak = 벌림 최대 국면)을 의도적으로 고르므로 "표시 순간 =
저에너지 홀드 안" 전제가 승인 코퍼스와 충돌한다. 관대 파라미터(p60)로도 0/12,
powerspin·peterpan 은 홀드 집합이 공집합 — 어떤 임계도 이 게이트를 (a) "픽스처
제외 0" 과 동시에 성립시킬 수 없다. 지시된 STOP 규칙("전부 PASS 아니면 STOP")
적용 — 미구현·보고.

**대안 후보 (belle 반려의 렌더-계층 가시 부분, 승인 코퍼스 무결 — 결정 대기)**:
ref-경계 핀 판정 — rt 가 ref 영상 끝 ε(0.5s) 이내(= DTW 종점 강제 정렬 artifact,
belle doc 실측 16.4~16.6/16s 끝)면 freeze 제외 + 리그 축. 승인 5편 rt 실측 전건
경계 밖 (max rt/ref: elbow 15.07/21.9 등). 단 ut 이탈-국면 자체(17.78/20.2 —
경계 아님)는 측정창 문제 = Phase 34 소관. 방어 2(tier)가 belle doc 계열을 이미
전단에서 차단하므로 대안은 warped-tier 의 잔여 위험용.

### 완료 정의 대비 커버리지

"belle 재업로드 시 이상한 정지는 원리적으로 못 나간다":
- 저신뢰 정렬 doc (belle doc 계열, trim_only/disabled/부재) → **방어 2 가 전단 차단** (재현 실측).
- 신뢰 정렬(warped) doc → 리그 A~F + **H 진품** 전 항목 PASS 만 부착. 잔여: warped +
  홀드-밖 순간의 의미 결함은 방어 1/3 STOP 으로 이 라운드 미커버 — 대안 후보 결정 대기.

### 회귀

픽스처 mp4 byte 불변 3/3(제외 회계 추가에도 — report 에 `excludedFreezes` 키만
증가, 문서화) · 승인 5편 새 리그(H 포함) ALL PASS · phase35 유닛 88 GREEN ·
pytest FAILED/ERROR node-ID baseline IDENTICAL · 채점 모듈 diff 0 (누적).

## 경계 핀 + UI 라운드 (2026-08-08 심야 — 결정 2건 + 앱)

커밋: 67e0ed2(리그 G 경계 핀) / 8ef52e2(freezes 계약 3-way) / 2b0dfe2(앱 UI).
push + Pod pull 반영.

### 결정 1 — G 경계 핀 (홀드-내 대안 승인분)

- **판정**: 렌더된 freeze 의 rt 가 ref 영상 **양끝 0.5s 이내** = DTW 종점 강제
  정렬 아티팩트 → 렌더러 사전 제외(`ref_boundary_pin` 회계) + 리그 G 이중 방어.
  상수 단일 출처 `REF_BOUNDARY_PIN_S`(compare_verify) — 근거 주석 박제 (belle
  doc 실측 rt 16.4~16.6/끝 0.2s 이내 vs 승인 5편 시작 여유 min 0.8·끝 여유 min
  1.0, FREEZE_TAIL 0.4·재재생 1.5s 경계-특수-구간 스케일 계열).
- **시작 경계 대칭 적용** (지시된 실측 게이트): 승인 12 freeze 전수 실측 —
  rt 시작 여유 min 0.8(pdshapefault r01, belle 명시 override) > 0.5 → 안전.
  **ut 는 미적용**: 승인 peterpan r00 이 ut=5.89/6.1s (끝 클램프+재재생 문법,
  ud-ut=0.2)라 끝 경계가 승인 문법과 충돌 + ut 는 측정 순간 소관(Phase 34).
- 실측 함정 박제: 자동 문법(사지군 가중 짝)이 pairs 주입 핀 값을 self-heal —
  유닛 벡터는 override 경로로 교체 (경계 판정이 문법 전체 **뒤** 최종 방어).
- 검증: 픽스처 mp4 byte 불변 3/3 + 리그(G 포함) 승인 5편 ALL PASS + 유닛
  (경계 4벡터 + build_timeline 제외 회계).

### 결정 2 — 2fe3ae94 소급 강등 (실측)

- before: `{status:'done', key:'results/fvcNXz…/2fe3ae94…/compare_v1.mp4'}`,
  tier=trim_only(low_global_confidence — 현행 방어 2 미통과 doc).
- after: `{status:'failed', key:''}` — 분석 본체 무훼손(status done·72점).
- 원칙 일관 성립: **renderedCompare done ⇒ 현행 방어 전체 통과본** (현재 전
  doc 중 done 0건 — 다음 done 은 tier=warped + 리그 A~H ALL PASS 만).

### UI 라운드 (RenderedComparePlayer — 시뮬 확인/OTA 는 orchestrator)

| 항목 | 구현 |
|------|------|
| 가로 크게 보기 | 260702-t0v 90° 회전 Modal 패턴 재사용 — 같은 player 인스턴스 두 번째 VideoView attach(동기 로직 0, 새 useVideoPlayer 금지 선례 준수), 탭 재생/일시정지 + 우상단 닫기. portrait 고정 유지 JS-only |
| 정지 틱 + 탭 점프 | 계약 확장 `renderedCompare.freezes?:[{rid,outSec}]` (done 전용, 3-way lockstep: contract.md §12.9 표 + models `RENDERED_COMPARE_OPTIONAL_KEYS`/`FREEZE_KEYS` + validator + analysis.ts `RenderedCompareFreeze`). 스테이지가 렌더 리포트 voiceStartOutS 를 각인. 앱 씬 바 틱 탭 = 정지 직전(-0.5s) 시크. **구버전 doc(freezes 부재) = 틱 없이 재생만** (fail-open) — 두 형상 유닛(validator·스테이지 각인·passthrough) + typecheck GREEN |
| 잔존 코드 무접촉 | 대략맞춤·미세조정·음성토글 등 폴백 경로 소비 코드 diff 0 |

### 회귀 (이 라운드)

픽스처 mp4 byte 불변 3/3 · 승인 5편 리그(G+H 포함) ALL PASS · phase35 유닛 73
GREEN · typecheck GREEN · pytest FAILED/ERROR node-ID baseline IDENTICAL ·
채점 모듈 diff 0 (누적).

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
