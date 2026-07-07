# Phase 27: 분석 속도 개선 (Gemini 라운드트립·후처리 축소) - Research

**Researched:** 2026-07-07
**Domain:** 파이프라인 레이턴시 최적화 (Gemini File API / 단일 분석 내부 병렬화 / Firestore 사후 업데이트)
**Confidence:** HIGH (코드 분해·호출 인벤토리 = 직접 코드 리딩) / MEDIUM (Gemini API 한계치 = 공식 docs 2026-07-07 확인) / LOW (일부 실측 수치 배분 — 계측 선행 필요)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**게이트 강도 (belle 2026-07-07 확정)**
- **D-01:** **정확도 무회귀가 hard gate** — 점수·verdict·faults가 EVAL18 순차 대조에서 무회귀. 시간은 "가능한 범위에서 현실적으로 최대 절감"이 목표치 (1분은 지향점, hard 아님). belle 원문: "너무 1분에 집착 안 해도 됨. 4분 넘어가는데도 아무 조치가 없어서 나온 피드백 — 빠르면 빠를수록 좋고 현실적으로."
- **D-02:** 피드백의 본질 = "오래 걸리는데 **아무 조치/변화가 없다**"는 체감. 절대 시간 단축과 대기 중 체감 개선(D-06)을 동급 레버로 취급.

**veto 처리**
- **D-03:** vision veto는 **파이프라인 내 겹치기** — 포즈 추정 진행 중 비전 호출을 가능한 구간부터 병렬 시작 (단일 분석 내부 병렬 — 분석 간 동시성 오염과 별개, 분석 간 SERIAL 불변). 점수는 결과 시점에 **동기 확정** — 사후 점수 변경 금지. veto 완전 비동기(점수 사후 보정)는 기각.

**허용 레버 범위**
- **D-04:** 기본 = **모델·입력 불변** 레버만: inline 전송(File API 우회), 파일 핸들 재사용, 호출 병렬화, 캐시. 프레임 수/해상도 축소는 **금지** (정확도 영향).
- **D-05:** Pro→Flash 전환은 **조건부 허용** — EVAL18 순차 대조에서 verdict·점수 동일할 때만 채택 (과거 실측: video split 판정에서 Flash≈Pro, 레버=프롬프트). 채택/기각 근거를 SUMMARY에 기록.

**후처리·대기 경험**
- **D-06:** fault_zoom PNG 렌더는 **사후 업데이트로 분리** — 점수/verdict/감점 내역 먼저 complete(앱은 onSnapshot으로 즉시 표시), zoom PNG는 렌더 완료 후 필드 업데이트로 도착. 결과 화면의 확대카드 자리는 로딩 상태 표시. zoom은 점수가 아닌 표현물이므로 D-03의 "사후 변경 금지"와 충돌하지 않음.
- **D-07:** **로딩 대기 중 재미 요소 추가** (belle 아이디어): 분석 대기 화면에 폴스포츠 관련 콘텐츠 — v1 = 저비용 텍스트 로테이션(폴스포츠 팁/동작 소개/재미 문구), 캐릭터 애니메이션(심플한 캐릭터가 폴 동작)은 에셋 확보 시 업그레이드 옵션. 형태 세부는 Claude 재량이되 라이트 테마·이모지 금지·기존 로딩 화면(navy 예외) 규칙 준수.

### Claude's Discretion
- 병렬화 구현 방식(스레드/asyncio/BackgroundTasks), inline 전송 크기 임계 처리, 캐시 키 설계 (단, 과거 캐시 키 충돌 사고 이력 참조 — PROMPT_VERSION류 버전 키 포함 필수).
- 진행률 표시 정밀화(단계별 %)는 D-02 범위에서 재량 (85% 멈춤 오인 재발 방지 관점).
- 로딩 재미 요소의 문구/구성.

### Deferred Ideas (OUT OF SCOPE)
- 프레임/해상도 입력 축소 — 정확도 영향 검증 부담, 이번 phase 금지 (D-04).
- veto 완전 비동기(점수 사후 보정) — 신뢰 리스크로 기각.
- 캐릭터 애니메이션 에셋 제작 — 에셋 확보 시 D-07 업그레이드 (디자인 트랙).
- 근본 해법 = Phase 22 자체 서빙(vLLM)으로 Gemini 라운드트립 소멸 — 이 phase는 그때까지의 저비용 브리지.
</user_constraints>

## Summary

mode1 분석 152s(포즈 51 + 비전 52 + 후처리 49)의 진짜 범인은 **같은 학생 영상을 Gemini File API에 최대 4~5회 중복 업로드**(scene_finder C + moment extractor + veto + coach B, 각각 업로드→PROCESSING 폴링→generate→delete 풀 라운드트립)하는 구조와, **같은 영상을 ffmpeg로 최대 3회 재디코딩**(pose 추출 → veto still 페어 → fault_zoom 렌더)하는 후처리다. 모든 Gemini 호출부는 순차 실행이며(veto fan-out 4콜도 순차, coach B→Cerebras도 순차), 병렬화·핸들 재사용·inline 전송(D-04 허용 레버)만으로 모델·입력 불변인 채 큰 절감이 가능하다.

세 가지 대형 레버: (1) **업로드 1회 + 핸들 공유** — File API 핸들은 서버측 리소스(48h TTL)라 분석 시작 시 1회 업로드한 핸들 이름을 전 모듈이 재사용 가능. 업로드+폴링 15~20s × 중복 횟수만큼 소멸. (2) **포즈∥비전 겹치기(D-03)** — Gemini 업로드와 moment extractor·scene_finder는 포즈 산출물이 필요 없어(영상 파일만 소비) S3 다운로드 직후 백그라운드 스레드로 시작 가능. veto 판정 자체는 DTW/점수 산출 후에만 가능하지만, 그 시점엔 핸들이 이미 ACTIVE. (3) **fault_zoom 사후 분리(D-06)** — `complete_analysis` 직후 zoom 렌더를 실행하고 `result.faultZoomComparisons`만 부분 업데이트. 앱 타입은 이미 optional이라 계약 파괴 없음 (로딩 상태 마커 1필드 추가 필요).

단계별 타이밍 계측이 현재 없다(veto telemetry.durationMs와 coach latency_ms만 존재). **Wave 0에서 stage-timing 로그를 먼저 넣고 cold-run baseline을 실측**해야 D-01 무회귀 게이트(EVAL18 순차 대조)와 before/after 절감 증명이 동시에 성립한다. 152s 분해와 전체 197s(3m17s) 사이 ~45s가 미계상(코치 듀얼트랙 + Cerebras + hook + Firestore 대형 doc write 추정)이므로 계측 없이 레버 효과를 단정하지 말 것.

**Primary recommendation:** Wave 0 = stage-timing 계측 + cold baseline. Wave 1 = GeminiFileSession(업로드 1회·핸들 공유·종료 시 일괄 delete) + still PNG inline 전환. Wave 2 = 업로드 prefetch(포즈∥비전 겹치기) + veto fan-out 병렬화(ThreadPoolExecutor) + coach B∥Cerebras 동시화. Wave 3 = fault_zoom 사후 분리(D-06) + 프레임 배열 재사용. Wave 4 = 앱(진행률 정밀화 + 로딩 재미 요소 D-07). Pro→Flash(D-05)는 EVAL18 통과 시에만 별도 커밋.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gemini 업로드/핸들 세션·호출 병렬화 | RunPod GPU 서버 (pipeline `_process`) | — | 모든 Gemini 호출이 Pod에서 실행 (Lambda는 위임만) |
| 단계별 타이밍 계측 | RunPod GPU 서버 (pipeline) | Firestore audit 필드 | 로그 + doc 필드로 before/after 실측 |
| fault_zoom 사후 업데이트 | RunPod GPU 서버 + `firestore_admin` | 앱 (onSnapshot 자동 반영) | complete 후 부분 update — 앱은 구독만 |
| zoom 로딩 상태 표시 | 앱 `result.tsx` | 데이터 계약 (TS+Py+contract.md 3-way) | optional 필드 + pending 마커 소비 |
| 진행률 정밀화 / 로딩 재미 요소 (D-02/D-07) | 앱 `loading.tsx` | 백엔드 status 갱신 시점 교정 | status 머신은 계약 고정 — 갱신 "시점"만 실제 단계 경계로 이동 |
| EVAL18 무회귀 게이트 | Pod eval 하니스 (`sweep_phase15.py` SERIAL) | `backend/evals/phase18` baseline | 기존 하니스 재사용, 신규 발명 금지 |

## 실측 분해 — 함수 단위 병목 지도 (Research Q1)

### mode1 fresh-run (cache-miss) Gemini 호출 인벤토리

기본 Pod env (GEMINI_COACH/FINDING default ON, RECOGNIZER_BACKEND=gemini, GEMINI_VISION_VETO_ENABLED=1, D/synthesis OFF) 기준. 전부 `_process` 안에서 **순차** 실행.

| # | 호출부 | 모델 | 영상 업로드 | generate 횟수 | 핸들 재사용 | 캐시 | 소스 |
|---|--------|------|------------|--------------|------------|------|------|
| 1 | scene_finder (영역 C) `find_scene_flags` | `gemini-3.5-flash` (DEFAULT_C_MODEL) | 학생 영상 **업로드 #1** + 폴링(2s 간격, 상한 120s) + 종료 시 delete | 1 (+검증실패 시 1) | 없음 — `GeminiVisionCall.call()` 이 호출마다 업로드→delete | 없음 | `gemini/client.py:211-242`, `gemini/scene_finder.py:161-173` |
| 2 | recognizer (`GeminiTechniqueRecognizer` → `GeminiMomentExtractor`) | `gemini-3.1-pro-preview` | 학생 영상 **업로드 #2** + 폴링(2s) | 1+ | 없음 | `TechniqueCache` (Firestore, video_hash 키) — **새 학생 영상은 항상 miss** | `judging/gemini_moment_extractor.py:350-365`, `analysis/gemini_technique_recognizer.py` |
| 3 | veto collect `assess_fault_context_video` (multi-scope fan-out) | `gemini-3.1-pro-preview` (DEFAULT_VISION_MODEL) | 학생 영상 **업로드 #3** + 기준 영상 **업로드 #1** + still PNG 2장 업로드 (`MAX_VETO_UPLOADS=4`) + 폴링(3s 간격, 상한 180s) | **4콜 순차** (upper×2 still + lower + line), 각각 `thinking_budget=-1`(dynamic thinking) | fan-out 내부에선 핸들 재사용 O (업로드 1회→4콜) — **모듈 간 재사용 X** | `VisionVetoCache` (in-memory + Firestore, hash pair + PROMPT_VERSION/SCHEMA_VERSION/granularity 키) — 새 영상 miss | `gemini_vision_scorer.py:1167-1344, 1612-1734` |
| 4 | coach B `GeminiCoachWriter.write` | `gemini-3.1-pro-preview` (DEFAULT_B_MODEL) | 학생 영상 **업로드 #4** + 폴링(2s) — **retry 시 attempt마다 재업로드 (최대 #5)** | 1×attempt (최대 2) | 없음 (`GeminiVisionCall` 1회용) | 없음 | `gemini/coach_writer_v2.py:431-490` |
| 5 | Cerebras coach (`_COACH_WRITER.write`) — Gemini 아님 | llama 계열 | — | 1×attempt (최대 2) | — | — | coach B **완료 후 순차** 호출 (`app.py:3534-3539`) |
| 6 | coach hook `GeminiCoachHookWriter` | pro (text-only) | **업로드 0** (텍스트만) | 1 (+retry 1) | — | — | `gemini/coach_hook_writer.py` — 빠름, 레버 아님 |
| (off) | 영역 D keypoint augmenter / synthesis / 영역 A | pro | — | — | — | — | default OFF — 인벤토리 제외 |

**핵심 사실: 학생 영상이 Gemini File API에 최대 4~5회 업로드된다.** 각 업로드 = HTTP 전송(≤100MB 파일) + PROCESSING 폴링(2~3s 간격) + ACTIVE 대기. ROADMAP 실측 "File API 업로드+폴링 15~20s×2회+"는 veto의 2개 영상 업로드만 본 수치 — 전 모듈 합산 시 업로드 라운드트립이 비전 구간의 지배 요인. `GeminiVisionCall`(#1, #4)과 vision_scorer(#3)는 각자 호출 종료 시 `files.delete`를 실행한다(2026-07-06 20GB 적체 사고 대응 — 이 규율은 반드시 보존).

### ffmpeg 재디코딩 인벤토리 (후처리 49s의 구성)

| # | 위치 | 무엇을 디코딩 | 소스 |
|---|------|--------------|------|
| 1 | `_extract_video_analysis_inputs` | 학생 영상 (9fps/640px) — 포즈 추정 입력 | `app.py:1305-1314` |
| 2 | `_build_selected_frame_pair` (veto still 추출) | 학생 영상 **재추출** + 기준 영상 추출 | `app.py:1713-1715` |
| 3 | `_render_fault_zoom` | 학생 영상 **3번째 추출** + 기준 영상 **재추출** | `app.py:2571-2573` |

동일 `FfmpegFrameExtractor(target_fps=9.0, max_side=640)` 파라미터 — 결과 프레임 배열을 1회 산출해 재사용하면 재디코딩 2회(학생) + 1회(기준)가 소멸. 이후 fault_zoom의 나머지 비용 = PNG crop 합성 + `_s3.put_object` per 카드 + presigned URL 발급 + `complete_analysis` 대형 doc write (18fps keypointReport flat 배열 + joints3d flat + angles flat).

### 순차 구조 (겹치기 지도, Research Q2)

```
S3 download ──► ffmpeg extract ──► RTMW estimate ──► body profile / pole detect
                    │  (여기부터 local_video_path 존재)
                    ▼
      [현재] scene_finder C (RTMW 끝난 뒤 순차)          ← 영상 파일만 필요: RTMW와 병렬 가능
      [현재] recognizer.recognize (moment extractor)     ← Gemini 경로는 angles 미소비(영상만): RTMW와 병렬 가능
                    ▼
      reference doc fetch + ref 영상 S3 download          ← 포즈 stage와 병렬 가능 (Firestore/S3 I/O)
                    ▼
      DTW(_deviation_against) → kismam → dimension_scores → overall   ← 포즈 산출물 의존 (병렬 불가)
                    ▼
      _collect_vision_fault_context (veto collect)        ← overall/DTW match/profile/ref 영상 의존
        · still 페어 추출(ffmpeg 재디코딩)                 ← pose_frames + DTW match 의존
        · assess_fault_context_video: 업로드 2+2 → 4콜 순차 ← **업로드는 선행 prefetch 가능, 4콜은 상호독립 → 병렬 가능**
                    ▼
      coach B (Gemini, 영상 재업로드) → Cerebras (순차)     ← 상호독립 → **동시 실행 가능**
                    ▼
      build_result → _apply_vision_veto(ctx 재사용, Gemini 0콜) → force/safety/hook → keypoint report
                    ▼
      fault_zoom 렌더(ffmpeg 재디코딩 ×2) + S3 업로드       ← **D-06: complete 이후로 이동 가능**
                    ▼
      complete_analysis (Firestore 대형 write)
```

**비전 호출의 포즈 의존 경계 (정확한 선):**
- 포즈 산출물 **불필요** (S3 다운로드 직후 시작 가능): Gemini 업로드 자체(핸들 prefetch), scene_finder C, moment extractor(Gemini recognizer 경로 — `_call_extractor(frames=video_path)`만 소비, angles 미사용. 단 FallbackRecognizer는 angles 소비 — env 분기 주의), 기준 영상 S3 다운로드 + 기준 영상 Gemini 업로드.
- 포즈 산출물 **필요** (겹치기 불가): DTW/kismam/overall, veto collect의 still 페어(pose_frames + DTW match), veto verdict 판정(overall·dimension_scores gate), coach context(assessments), fault_zoom(keypoint report + DTW match).
- D-03 준수 확인: veto **판정·점수 확정은 동기** 그대로 — 병렬화 대상은 "업로드 준비"와 "상호독립 generate 콜"뿐. 점수 사후 변경 없음.

### 공유 상태 오염 위험 (단일 분석 내부 병렬 시)

| 공유 상태 | 위험 | 판정 |
|-----------|------|------|
| `_RECOGNIZER.motion_query_hint` (모듈 전역, WR-07 이력) | recognize를 스레드로 띄우기 **전에** hint rebind가 완료돼야 함. 분석 간은 SERIAL이라 안전 — 분석 내에서는 "hint 세팅 → recognize 시작" 순서만 지키면 됨 | 순서 보장 필요 (병렬 시작점 앞에서 rebind) |
| `gemini_vision_scorer._CLIENT` (모듈 싱글톤 genai.Client) | google-genai Client는 httpx 기반이나 **스레드 안전성 공식 미문서** [ASSUMED] | 스레드별 Client 생성 또는 싱글톤 유지 후 실측 검증. File API **핸들 이름은 서버측 리소스**라 어느 Client에서든 사용 가능 — 핸들 공유에 Client 공유 불필요 (VERIFIED: 코드상 handle은 `files/...` name 문자열) |
| `VisionVetoCache` in-memory dict + Firestore | 키가 (hash pair, PROMPT_VERSION, SCHEMA_VERSION, granularity, n, fi) 로 완전 결정 — 같은 분석 안 병렬 태스크는 서로 다른 네임스페이스 접근 | 안전. 단 **캐시 키 충돌 사고 이력(90d038f)**: 신규 입력 형태 도입 시 granularity 마커 bump 필수 |
| `TechniqueCache` (Firestore, video_hash) | 분석 내 1회 호출 | 안전 |
| `_FRAME_EXTRACTOR`/`_RTMW_ENGINE` 등 어댑터 싱글톤 | GPU 모델 — 분석 내에서 estimate는 1회만. 병렬 대상 아님 | 접근 금지 유지 (Gemini 스레드가 RTMW 재실행 금지 — B4 hard gate) |
| `tempfile` local paths + `_safe_unlink_local_video` finally | 병렬 태스크가 아직 파일을 읽는 중에 unlink 되면 안 됨 | 병렬 태스크 join 후 finally 정리 (구조적으로 보장할 것) |

### 152s vs 197s 미계상 구간

power-spin 실측 총 3m17s(197s) 대비 51+52+49=152s — **~45s 미계상** (coach B 업로드+generate, Cerebras, hook, safety/force 연산, Firestore write 추정). 현재 코드에 단계별 타이밍 로그가 없어(veto `telemetry.durationMs`, coach `_meta.latency_ms`만 존재) 이 배분은 로그 타임스탬프 재구성치다. **레버 우선순위를 확정하려면 Wave 0 계측이 선행 필수** (Research Q6).

## Standard Stack

### Core (전부 기존 — 신규 설치 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | >=1.0,<2.0 (Pod requirements 기존 핀) | Files API / inline Part / generate_content | 이미 전 Gemini 호출부가 사용. `types.Part.from_bytes` inline·`client.aio` async 지원 [CITED: googleapis.github.io/python-genai, 2026-07-07 확인] |
| `concurrent.futures.ThreadPoolExecutor` | stdlib | 단일 분석 내부 병렬화 | 기존 `_process`가 동기 함수(FastAPI BackgroundTasks 스레드풀에서 실행) — asyncio 전환 없이 최소 침습. `threading`은 이미 pipeline이 import |
| `time.monotonic` + stdlib `logging` | stdlib | stage-timing 계측 | 기존 로깅 규율(key=value 구조 로그) 그대로 |
| `firestore_admin` `.set(merge=True)` / `.update()` | firebase-admin >=6,<7 (기존) | D-06 zoom 부분 업데이트 | `complete_analysis`가 이미 `set(payload, merge=True)` 패턴 (`firestore_admin.py:1023`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | asyncio + `client.aio` | async가 이론상 깔끔하나 `_process` 4200줄 전체가 동기 — 내부에서 `asyncio.run()` 섬을 만들면 이벤트루프/스레드 경계 버그 표면 증가. 병렬 대상이 I/O-bound HTTP 몇 개뿐이라 스레드로 충분 |
| File API 핸들 공유 | 매 호출 inline 전송 | inline은 **매 generate 호출마다 영상 바이트 재전송** — veto fan-out 4콜이면 같은 영상을 4번 보냄. 다회 호출 구조에선 핸들 공유가 우월. inline은 "1회 호출 + 소형 파일" 모듈(still PNG)에 적합 |
| 신규 상태 필드로 진행률 | 신규 status enum 추가 | status enum은 TS/Python/contract.md 3-way lockstep — enum 추가 대신 **기존 status 갱신 시점을 실제 단계 경계로 이동** + 필요 시 optional 수치 필드가 저비용 |

**Installation:** 없음 — 신규 패키지 0.

## Package Legitimacy Audit

이 phase는 **외부 패키지를 설치하지 않는다** (stdlib + 기존 핀 재사용). slopcheck 실행 불필요.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### Pattern 1: GeminiFileSession — 업로드 1회 + 핸들 공유 + 종료 일괄 delete

**What:** `_process` 시작 시(또는 prefetch 스레드에서) 학생/기준 영상을 File API에 1회 업로드하고, ACTIVE 핸들을 분석-로컬 세션 객체에 담아 scene_finder·recognizer·veto·coach B에 주입. `_process` outer finally에서 일괄 `files.delete`.
**When to use:** 같은 분석 안에서 같은 영상을 2회 이상 Gemini에 보내는 모든 경로.
**Key facts:**
- File API: 파일당 2GB, 프로젝트당 20GB, **48h TTL**, 업로드 후 영상은 PROCESSING→ACTIVE 폴링 필요 [CITED: ai.google.dev/gemini-api/docs/files, 2026-07-07 확인]
- 핸들(`files/...` name)은 서버측 리소스 — 여러 generate_content 호출·여러 Client 인스턴스에서 재사용 가능 (veto fan-out이 이미 fan-out 내부에서 이 패턴을 증명: "업로드는 1회만(ref+student 핸들 재사용) — N 회는 generateContent 만 반복" `gemini_vision_scorer.py:96`)
- **delete 규율 보존 필수**: 세션 종료 시 반드시 delete (2026-07-06 20GB 적체 → RESOURCE_EXHAUSTED 분석 간헐 실패 실증). 세션 도입으로 delete가 "호출마다"에서 "분석마다"로 바뀌는 것뿐, 누수 0 불변.
- 주입 방식: `GeminiVisionCall`에 `preuploaded_handle` optional 인자(있으면 upload/delete skip), vision_scorer `assess_fault_context_video`에 handle kwargs — 기존 시그니처는 default로 무변경 유지 (RunPod server.py 무수정 원칙).

### Pattern 2: 업로드 prefetch + 포즈∥비전 겹치기 (D-03)

**What:** `_extract_video_analysis_inputs`에서 S3 다운로드가 끝난 직후, ThreadPoolExecutor에 (a) 학생 영상 Gemini 업로드, (b) 기준 영상 S3 다운로드 + Gemini 업로드, (c) scene_finder, (d) moment extractor(Gemini recognizer 경로)를 submit. 메인 스레드는 RTMW→DTW→점수 산출을 계속. veto collect 시점에 future.result()로 join — 그 시점엔 핸들 ACTIVE·scene/moment 결과 준비 완료.
**Ordering constraints:**
- `recognizer.motion_query_hint` rebind(WR-07)는 recognize future submit **이전**에 완료.
- FallbackRecognizer(env OFF) 경로는 angles 의존 — Gemini 경로에서만 prefetch (기존 env 분기 재사용).
- future 예외는 기존 graceful 규율 그대로 흡수 (분석 흐름 차단 0).
- finally의 `_safe_unlink_local_video`는 모든 future join 후에 실행.
**Sizing:** 업로드 prefetch만으로 비전 구간의 "업로드+폴링" 대기가 포즈 51s 그늘로 숨는다 — 이게 D-03의 실질 수확.

### Pattern 3: inline 전송 임계 처리 (Part.from_bytes)

**What:** still PNG 2장(수백 KB)은 File API 업로드+폴링 대신 `types.Part.from_bytes(data=..., mime_type="image/png")`로 generate_content contents에 직접 삽입 — 업로드 2회 + 폴링 + delete 2회가 통째로 소멸.
```python
# Source: googleapis.github.io/python-genai (2026-07-07 확인)
from google.genai import types
still_part = types.Part.from_bytes(data=png_bytes, mime_type="image/png")
response = client.models.generate_content(model=..., contents=[ref_part, stu_part, prompt], config=...)
```
**영상 inline 임계:** 공식 기준 — 총 request 크기(파일+프롬프트) 20MB 초과 시 Files API 권장 [CITED: ai.google.dev/gemini-api/docs/video-understanding, 2026-07-07 확인. 같은 페이지에 "<100MB inline" 서술도 있으나 이는 신형 interactions API 예시 문맥 — 보수적으로 20MB 임계 채택]. 앱 업로드 상한 100MB(`analyze.tsx MAX_BYTES`)라 inline 불가 영상 다수 — **판단 규칙: `os.path.getsize() < ~18MB`이고 그 영상을 소비하는 generate 호출이 1회뿐인 모듈(scene_finder 단독 사용 시)만 inline, 그 외는 Pattern 1 핸들 공유**. 핸들 공유가 전면 도입되면 영상 inline의 이득은 "폴링 제거"뿐이라 우선순위 낮음 — still PNG inline이 확실한 수확.
**캐시 키 주의:** inline/handle 전환은 입력 픽셀 불변이므로 granularity bump 불필요 — 단, still 전달 방식 변화가 응답 분포를 바꿀 가능성이 이론상 0이 아니므로 EVAL18로 확인 (D-01).

### Pattern 4: veto fan-out 병렬화 + coach B∥Cerebras 동시화

**What:**
- `_run_part_frame_fanout`의 4콜(upper×2, lower, line)은 상호독립(각각 독립 generate_content, 결과는 사후 집계) — ThreadPoolExecutor(max_workers=4)로 동시 발사. wall-clock budget 가드는 "제출 전 elapsed 확인" → "future timeout"으로 이식하되 **fail-closed resource_limited 의미론 보존** (부분 완료 = resource_limited, D-13 HIGH-2 Option A 불변).
- 결과 순서 결정론: `per_call` 순서가 집계에 들어가므로 **future를 call_plan 인덱스 순서로 join**해 순차 실행과 동일한 리스트 순서 보장 (병렬성은 실행만, 집계 입력 순서는 불변 — 결정론 게이트 정합).
- coach: `gemini_future = pool.submit(gemini_write)` + Cerebras를 메인 스레드에서 실행 후 join — 두 writer는 같은 immutable coach_context dict를 읽기만 함 (B3 정합, 안전).
**Rate limit:** 유료 tier 인터랙티브 RPM은 공개 문서에 미기재 — AI Studio 콘솔에서 확인 필요 [CITED: ai.google.dev/gemini-api/docs/rate-limits, 2026-07-07 확인 — 표에 Batch 한도만 명시]. 동시 4~6콜은 통상 여유이나 429 시 기존 5xx retry 규율로 흡수됨을 확인할 것.

### Pattern 5: fault_zoom 사후 분리 (D-06)

**What:** 현재 `_attach_fault_zoom_comparisons`(complete 전, result dict에 부착) → complete **이후** 실행으로 이동:
1. `complete_analysis` 호출 시 `result.faultZoomStatus = "pending"` (신규 optional scalar — nested-array 금지 정합, 3-way 계약 lockstep 필요: `analysis.ts` + `models.py` + `contract.md`).
2. complete 직후 같은 BackgroundTask 안에서 zoom 렌더 (별도 태스크 불필요 — 분석 간 SERIAL 불변 유지: 다음 분석은 어차피 이 task 종료 후).
3. `firestore_admin`에 신규 함수 `update_analysis_fault_zoom(uid, analysis_id, comparisons)` — `.update({"result.faultZoomComparisons": [...], "result.faultZoomStatus": "done", "updatedAt": ...})` field-path 업데이트. 기존 `_validate_dict_only_scalars` 계열 scoped validator로 zoom item 검증 재사용.
4. 실패 시 `faultZoomStatus = "failed"` — 앱은 확대카드 자리 숨김/안내 (graceful, 기존 "부가 기능 실패는 분석 비차단" 규율).
**앱 영향:** `FaultZoomComparison`은 이미 `faultZoomComparisons?: FaultZoomComparison[]` optional (`analysis.ts:525`). result.tsx의 `selectedZoom`은 `?? []` 소비 — **pending 상태에서 로딩 placeholder를 그리는 분기만 추가**. onSnapshot 구독이라 zoom 도착 시 자동 rerender (추가 폴링 0).
**주의:** zoom 렌더가 참조하는 `local_video_path`/`reference_local_video_path`가 outer finally에서 unlink됨 — 사후 분리 시 unlink를 zoom 렌더 이후로 이동 (temp 파일 생명주기 재배치).
**D-03 충돌 없음:** zoom은 표현물 — 점수/verdict/감점 내역은 complete 시점에 확정 (CONTEXT 명시).

### Pattern 6: stage-timing 계측 (Research Q6)

**What:** 현재 단계별 타이밍 로그 부재. `_process`에 경량 타이머:
```python
# 구조 로그 규율 정합 (key=value)
_t0 = time.monotonic()
... stage ...
log.info("stage_timing analysis_id=%s stage=%s elapsed_s=%.1f", analysis_id, "pose_extract", time.monotonic() - _t0)
```
측정 단계(최소): s3_download / frame_extract / rtmw / ref_fetch_download / dtw_scoring / gemini_upload(핸들별) / scene_finder / recognizer / veto_collect / coach_dual / assemble_misc / fault_zoom / firestore_complete. 추가로 Firestore audit 필드 `result.timingsMs`(flat dict[str,int] — scalar-only validator 통과)로 저장하면 EVAL18 sweep 리포트에서 before/after 표를 기계 추출 가능. **cold/warm 구분 필수**: veto/technique 캐시 hit run은 Gemini 0콜이라 타이밍 비교 무효 — `telemetry.cacheHit`를 리포트에 같이 기록.
**기존 텔레메트리 재사용:** veto `telemetry.durationMs`/`completedCalls`, coach `_meta.latency_ms`, Pod의 arize-phoenix(google-genai 자동 계측, TELEMETRY_OK gate)가 이미 있음 — 신규 계측은 stage 경계만.

### Pattern 7: 프레임 배열 재사용 (ffmpeg 재디코딩 제거)

**What:** `_extract_video_analysis_inputs`가 이미 산출한 9fps/640px 프레임 배열을 `_VideoAnalysisInputs`에 보존(또는 분석-로컬 dict 캐시 `{video_path: frames}`)해 `_build_selected_frame_pair`와 `_render_fault_zoom`이 재사용. 기준 영상도 최초 추출 1회 후 재사용.
**메모리 주의:** 640px 30s 영상 ≈ 270프레임 × ~0.7MB = ~190MB/영상. Pod RAM 여유 확인 후, 부담 시 학생 영상만 캐시하고 기준 영상은 사후(zoom) 시점 1회 추출로 타협. Lambda 폴백 경로(256MB~1GB)는 캐시 비활성 분기 필요.

### 앱 — 진행률 정밀화 + 로딩 재미 요소 (D-02/D-07)

- **status 갱신 시점 교정:** 현재 `_process`가 frame_extraction/pose_analysis status를 **실제 작업 전에 연달아 write** (`app.py:3088-3093`) → 앱 진행률이 즉시 85%(comparison) 도달 후 정지. 갱신을 실제 단계 경계로 이동(추출 후 pose_analysis, RTMW 후 comparison)하면 enum 추가 없이 진행률이 실제와 근사. `PROGRESS_CEIL` creep(loading.tsx, 85% 멈춤 fix 이력)은 유지.
- **재미 요소 v1:** loading.tsx에 텍스트 로테이션(폴스포츠 팁/동작 소개) — 기존 `STATUS_MESSAGE` 라인 아래 별도 로테이터. navy 예외 화면 규칙·이모지 금지·Pretendard 준수. 문구는 Claude 재량 (CONTEXT).
- **파일 겹침:** result.tsx는 Phase 26의 26-02(wrapper/child 분리)와 겹침 — 실행 순서 조율 필요 (CONTEXT canonical_refs 명시).

### Anti-Patterns to Avoid

- **asyncio 전면 재작성:** `_process` 동기 구조 유지 — 스레드풀 섬만. 이벤트루프 도입은 이 phase 범위·리스크 초과.
- **veto 부분-샘플 채택:** wall budget 안에 4콜 미완료 시 부분 결과로 verdict 내기 금지 — fail-closed `resource_limited` 의미론 불변 (비결정성 = 위양성 게이트 약화).
- **점수 사후 변경:** zoom 외 어떤 필드도 complete 후 변경 금지 (D-03/D-06 경계).
- **캐시 키에 버전 미포함 신규 캐시:** 신규 캐시(핸들 세션 포함 아님 — 핸들은 캐시가 아니라 분석-로컬 세션)는 PROMPT_VERSION류 버전 키 필수 (90d038f 사고 이력).
- **`GEMINI_MAX_VETO_WALL_S` 축소로 시간 단축:** 예산 축소는 fail-closed라 resource_limited 빈도만 올림 — 속도 레버 아님 (피드백 B의 레버 후보였으나 구조상 부적합).
- **thinking_budget / media_resolution 조정:** 응답 분포를 바꾸는 모델-측 파라미터 — D-04 "모델·입력 불변" 위반. media_resolution low(66 tokens/frame)는 사실상 해상도 축소 [CITED: ai.google.dev video-understanding docs] — 금지.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 병렬 실행 | 수동 threading.Thread + 조인 플래그 | `concurrent.futures.ThreadPoolExecutor` | future 예외 전파/timeout/결과 순서가 표준화 — 수동 스레드는 예외 무음 삼킴 |
| Gemini 재시도/폴링 | 신규 재시도 래퍼 | 기존 `GeminiVisionCall` retry + `_upload_video` 폴링 | 4xx/5xx/schema-retry 규율이 이미 검증됨 — 핸들 주입 인자만 추가 |
| 무회귀 판정 | 신규 eval 스크립트 | `backend/scripts/sweep_phase15.py --pair-sequential` + `evals/phase18/assert_baseline.py` + baseline JSON | EVAL18 하니스·baseline·SERIAL 규율 기존 (phase24/25가 같은 계보) |
| zoom 부분 업데이트 검증 | 신규 validator | `firestore_admin` scoped validator 패턴 재사용 | nested-array 금지/flat 규율 단일 출처 |

**Key insight:** 이 phase의 모든 빌딩블록(업로드/폴링/재시도/캐시/eval)이 코드베이스에 이미 있다 — 신규 발명이 아니라 **호출 토폴로지 재배열**이 작업의 본질.

## Common Pitfalls

### Pitfall 1: 캐시 warm-hit가 타이밍 실측을 오염
**What goes wrong:** EVAL18 재실행 시 VisionVetoCache/TechniqueCache hit → Gemini 0콜 → "빨라졌다" 착시.
**How to avoid:** before/after 타이밍은 cold run(새 video hash 또는 캐시 네임스페이스 격리)으로만 비교. `telemetry.cacheHit`를 리포트에 필수 기록. 무회귀 판정(점수·verdict)은 warm이어도 유효하나 **cold 결정론 게이트(cold/warm 동일)는 별도** — phase25 `check_cold_warm_determinism` 패턴 재사용.

### Pitfall 2: 핸들 공유 도입 후 delete 규율 붕괴 → 20GB 적체 재발
**What goes wrong:** 세션이 예외 경로에서 delete를 건너뛰면 48h TTL 전에 프로젝트 20GB 한도 도달 → `files.upload` RESOURCE_EXHAUSTED → 분석 간헐 실패 (2026-07-06 실증).
**How to avoid:** 세션 delete를 `_process` outer finally에 배치 + 실패 시 log.warning (기존 규율 복제). NoHuman/NotPole 조기 raise 경로에서도 finally 도달 확인.

### Pitfall 3: 병렬 태스크 생존 중 temp 파일 unlink
**What goes wrong:** prefetch future가 아직 영상을 업로드 중인데 메인 경로가 NotPoleMotionError로 raise → finally가 파일 unlink → future가 이상 실패.
**How to avoid:** finally에서 **모든 future를 join(또는 cancel+wait)한 뒤** unlink. zoom 사후 렌더 도입 시 unlink 시점을 zoom 이후로 이동.

### Pitfall 4: fan-out 병렬화가 집계 순서를 바꿔 결정론 게이트 FAIL
**What goes wrong:** as_completed 순서로 per_call을 쌓으면 run마다 리스트 순서가 달라져 `primary = parsed_verdicts[0]` 등 집계가 비결정적.
**How to avoid:** future를 call_plan 인덱스 순서로 join — 실행만 병렬, 집계 입력 순서는 순차와 byte-동일.

### Pitfall 5: status 갱신 시점 이동이 앱 진행률 역행을 유발
**What goes wrong:** 앱 PROGRESS_PCT는 status 인덱스 기반 단조 가정 — 백엔드가 status를 건너뛰거나 늦게 쓰면 UI가 오래 낮은 %에 머무름(반대 방향 오인).
**How to avoid:** loading.tsx의 `Math.max` 단조 로직은 유지된 채 시점만 이동하므로 역행은 없음 — 다만 각 단계 체감 길이가 바뀌니 PROGRESS_PCT 배분(현 comparison=85)을 실측 타이밍에 맞춰 재배분.

### Pitfall 6: Pod 런타임 env가 git에 없음 (runtime state)
**What goes wrong:** `start_server.sh`(VETO=1, GEMINI_MAX_VETO_WALL_S=300 등)는 Pod 파일시스템에만 존재 — 코드가 새 env(예: GEMINI_UPLOAD_PREFETCH=1)를 도입해도 Pod에 주입 안 하면 무음 비활성.
**How to avoid:** 신규 env는 setdefault 박제 패턴(CONTEXT integration point) + Pod start_server.sh 갱신을 plan의 명시 태스크로. Pod 재생성 시 proxy URL→Lambda env 동기화도 기존 함정.

### Pitfall 7: 429/rate limit이 병렬화 후 처음 표면화
**What goes wrong:** 순차일 땐 안 걸리던 분당 요청 한도가 동시 4~6콜에서 429 → 기존 코드가 4xx는 즉시 graceful None → veto가 resource_limited/skipped로 빠져 **속도 개선이 정확도 회귀로 전이**.
**How to avoid:** AI Studio에서 belle 프로젝트 tier 한도 확인(공개 문서에 미기재). EVAL18 순차 대조에서 `completedCalls==plannedCalls` 확인. 429 발생 시 병렬도 축소(4→2) 폴백 상수화.

### Pitfall 8: coach B의 retry가 재업로드를 동반
**What goes wrong:** 핸들 공유를 coach B에 적용 안 하면 retry attempt마다 영상 재업로드 (현행 `_build_call()` per attempt).
**How to avoid:** coach B에 세션 핸들 주입 — retry는 generate만 반복.

## Code Examples

### 업로드 prefetch + 순서보존 join (Pattern 2/4 골격)
```python
# _process 안 — 분석-로컬 executor (분석 간 SERIAL 불변, 분석 내부만 병렬)
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini") as pool:
    # S3 다운로드 직후 (RTMW 시작 전) — 포즈 산출물 미의존 태스크 submit
    student_handle_f = pool.submit(session.upload, local_video_path)   # File API 업로드+ACTIVE 폴링
    scene_f = pool.submit(_call_wave1_scene_finder, local_video_path, is_reference_local)
    # ... RTMW / DTW / 점수 산출 (메인 스레드) ...
    scene_result = scene_f.result()          # veto/coach 직전 join — 예외는 기존 graceful 규율로 흡수
    student_handle = student_handle_f.result()
```

### fan-out 병렬 (순서 결정론 보존)
```python
futures = [pool.submit(_one_call, call_plan[i]) for i in range(planned)]
for idx, fut in enumerate(futures):          # as_completed 금지 — 인덱스 순서 join
    raw_text = fut.result(timeout=remaining_budget())
    ...  # 기존 per_call append 로직 그대로
```

### D-06 zoom 부분 업데이트 (firestore_admin 신규 함수 골격)
```python
def update_analysis_fault_zoom(uid: str, analysis_id: str, comparisons: list[dict], status: str) -> None:
    for c in comparisons:
        _validate_dict_only_scalars(c, path="faultZoomComparisons[]")   # flat 규율 재사용
    _doc(models.analysis_doc_path(uid, analysis_id)).update({
        "result.faultZoomComparisons": comparisons,
        "result.faultZoomStatus": status,          # "done" | "failed"
        "updatedAt": int(time.time() * 1000),
    })
```

### still PNG inline (Pattern 3)
```python
# Source: googleapis.github.io/python-genai — Part.from_bytes (2026-07-07 확인)
from google.genai import types
with open(pair.student_frame_path, "rb") as f:
    stu_part = types.Part.from_bytes(data=f.read(), mime_type="image/png")
# generate_content contents 에 file 핸들 대신 Part 삽입 — 업로드/폴링/delete 0
```

## State of the Art (2026-07 현행, ai.google.dev 확인)

| Old Approach | Current Approach | 확인일 | Impact |
|--------------|------------------|--------|--------|
| File API만 (영상) | inline: 총 request ≤20MB이면 Files API 불요 (docs는 신형 interactions API 예시에서 "<100MB inline"도 언급 — SDK 1.x generate_content 기준 20MB 보수 채택) | 2026-07-07 | still PNG·소형 영상 라운드트립 제거 |
| — | Files API: 2GB/file, 20GB/project, 48h TTL, 영상은 ACTIVE 폴링 필요, 무료 | 2026-07-07 | 핸들 세션 설계 근거 |
| 공개 rate limit 표 | 인터랙티브 RPM/TPM은 문서 비공개 — AI Studio 콘솔에서 프로젝트별 확인 | 2026-07-07 | 병렬도 상한은 실측/콘솔 확인 |
| `client.models.generate_content` | docs 예시가 `client.interactions.create`로 이동 중 — **migration 금지** (SDK 1.x generate_content 유지, 이 phase 범위 아님) | 2026-07-07 | 기존 코드 유지 정당 |
| — | `media_resolution` low=66 tokens/frame — **입력 충실도 변경 = D-04 금지 레버** | 2026-07-07 | 손대지 말 것 |

모델 string은 프로젝트 확정값 유지: Pro=`gemini-3.1-pro-preview`, Flash=`gemini-3.5-flash` (`gemini/config.py` 단일 출처, 2.5 계열 금지).

## Flash 전환 대상 선별 (D-05, Research Q4)

| 호출 | 현행 모델 | 판단 복잡도 | Flash 후보 순위 | 근거 |
|------|----------|------------|----------------|------|
| moment extractor (recognizer) | pro | 낮음 — key moment 타임스탬프 추출 | **1순위** | 분류·추출성 태스크. TechniqueCache 키에 model명 포함 — 전환 시 자동 cache-miss로 오염 0 |
| coach B (영상 코칭 문장) | pro | 중간 — 생성 태스크, tone validator가 사후 게이트 | 2순위 | 실패해도 Cerebras cross-fill 폴백 존재 — 회귀 표면 제한적 |
| veto fan-out verdict | pro | **높음** — 점수 직결 (감점 seed) | 최후·기본 보류 | 과거 실측 "video split 판정 Flash≈Pro" ([[flash-beats-pro-video-split-judgment]])는 split 단일 판정 — 3-scope 짚기 전체의 등가 증거 아님. EVAL18 verdict·점수 **동일**일 때만 |
| scene_finder C | flash (이미) | — | — | 전환 완료 상태 |
| coach hook | pro (text) | 낮음 | 3순위 (수확 작음 — 업로드 0) | 레이턴시 기여 미미 |

채택 절차 (D-05 고정): 후보별 env override(`GEMINI_*_MODEL` 기존 패턴)로 EVAL18 순차 대조 → verdict·점수·faults 동일 시에만 채택, 근거를 SUMMARY에 기록. veto는 캐시 키에 model명 포함이라 전환 실험이 프로덕션 캐시를 오염하지 않음.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| RunPod Pod (svn31pzja7uay0, 4090) | 전 실측·EVAL18 | ✓ (memory 2026-07-05) | — | Pod 재생성 시 proxy URL→Lambda env 동기화 필요 |
| google-genai (Pod) | 전 Gemini 레버 | ✓ (requirements 핀) | >=1.0,<2.0 | — |
| Gemini API 키 (SSM `/sunity/motion/gemini-api-key`) | Gemini 호출 | ✓ (기존 운영) | — | 크레딧 고갈 이력([[gemini-credits-depleted]]) — sweep 전 잔액 확인 |
| ffmpeg (imageio-ffmpeg, Pod) | 프레임 재사용 리팩터 | ✓ | >=0.5.1 | — |
| EVAL18 하니스 (`sweep_phase15.py` + phase18 baseline) | D-01 게이트 | ✓ (repo) | — | — |
| Cerebras SDK/키 | coach 병렬화 | ✓ (기존 운영) | — | 기존 graceful no-op |
| Pod `start_server.sh` env | 신규 env 주입 | **git 밖 — Pod에만 존재** | — | plan에 Pod env 갱신 태스크 명시 필수 |

**Missing dependencies with no fallback:** 없음 (신규 설치 0).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (backend) / `tsc --noEmit` (app) |
| Config file | `backend/requirements-dev.txt` (별도 pytest.ini 없음 — 기존 관례) |
| Quick run command | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q -k "phase27 or fault_zoom or vision"` (신설 테스트 네이밍에 따라 조정) |
| Full suite command | `cd backend && PYTHONPATH=shared/python:. python3 -m pytest tests/ -q` + `cd app && npm run typecheck` |

### Phase Requirements → Test Map (requirement ID 미발급 — CONTEXT 결정 기준 매핑)

| 결정 | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| D-01 | EVAL18 6페어 점수·verdict·faults 무회귀 | Pod eval (SERIAL, artifact-gated) | `python backend/scripts/sweep_phase15.py --pair-sequential` → `evals/phase18/assert_baseline.py` 대조 (EVAL_OUT_DIR 리포 밖) | ✓ 기존 하니스 |
| D-03 | 병렬화 후 결정론 (cold/warm 동일, 집계 순서 불변) | Pod eval + unit | phase25 `check_cold_warm_determinism` 패턴 + fan-out 순서보존 unit test (fake client) | ✗ Wave 0 (unit) |
| D-04 | 핸들 세션 — 업로드/삭제 카운트 (누수 0) | unit | fake genai client로 upload/delete 호출 수 assert | ✗ Wave 0 |
| D-06 | complete 후 zoom 부분 업데이트 + pending→done 전이 | unit + 실기기 | firestore_admin mock unit + belle 실기기 onSnapshot 확인 (manual — UI 반영은 자동화 범위 밖) | ✗ Wave 0 (unit) |
| D-02/D-07 | 진행률/로딩 화면 | typecheck + manual | `npm run typecheck` + belle 실기기 | ✓ (typecheck) |
| 계측 | stage_timing 로그 방출 + timingsMs flat | unit | caplog로 stage_timing 라인 assert + validator 통과 | ✗ Wave 0 |

### Sampling Rate
- **Per task commit:** 관련 unit 테스트 quick run + `npm run typecheck` (앱 변경 시)
- **Per wave merge:** backend full pytest (기존 54 pre-existing failure 기준선 대비 신규 0)
- **Phase gate:** Pod에서 EVAL18 SERIAL cold sweep → baseline 대조 무회귀 + cold/warm 결정론 + **before/after stage-timing 표** (cold run, cacheHit=false 확인) → `/gsd-verify-work`

### Wave 0 Gaps
- [ ] stage-timing 계측 코드 + `tests/test_stage_timing.py` (로그 라인/flat dict 검증)
- [ ] cold baseline 실측 1회 (변경 전 — before 수치 확보, Pod에서 EVAL18 1페어 이상)
- [ ] fake genai client fixture (upload/delete 카운트 + fan-out 순서 결정론용) — 기존 test_client.py monkeypatch 패턴 확장
- [ ] `tests/test_fault_zoom_deferred.py` (D-06 부분 업데이트 + validator)

## Security Domain

### Applicable ASVS Categories (L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3/V4 인증·세션·접근제어 | no (신규 endpoint 0) | 기존 X-RunPod-Token / Firebase 토큰 불변 |
| V5 Input Validation | yes | zoom 부분 업데이트에 기존 scoped validator 재사용 (nested-array/scalar-only) — 신규 검증 경로 발명 금지 |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | (a) Gemini File API delete 규율 = 사용자 영상 제3자 보존 최소화(프라이버시) — 세션 도입 후에도 분석 종료 시 삭제 불변. (b) inline 전송 시 영상 바이트를 로그에 남기지 않음 (기존 "never log secrets" 규율) |
| V10 SSRF/외부호출 | yes | Gemini/Cerebras endpoint는 SDK 고정 — 신규 URL 입력 표면 0. 신규 env는 Parameter Store/Pod env만 (.env 하드코딩 금지, CLAUDE.md §3) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 병렬 태스크 예외 무음 삼킴 → 부분 결과로 점수 산출 | Tampering | fail-closed resource_limited 의미론 보존 + future 예외를 기존 graceful status로 명시 매핑 |
| 캐시 키 충돌 → stale verdict (90d038f 계보) | Tampering | 입력 형태 변화 시 granularity/버전 키 bump (기존 규율) |
| Files API 쿼터 고갈 DoS (20GB) | DoS | 세션 finally 일괄 delete + 삭제 실패 log.warning |

## Project Constraints (from CLAUDE.md)

- 기술 스택 변경 금지 — 신규 패키지 0으로 정합. Gemini 호출은 Pod에서만 (Lambda 250MB lazy-import 규율 유지 — 신규 import도 lazy).
- 시크릿: AWS Parameter Store — 신규 env는 Pod env/SSM만, .env 하드코딩 금지.
- 디자인: 로딩 화면 navy 예외 유지, 브랜드 #FF4B33/Pretendard/라이트 전용, 이모지 금지 (D-07 문구 포함).
- 계약 3-way lockstep: `analysis.ts` + `models.py`/`validation.py` + `contract.md` 동시 수정 (faultZoomStatus 등 신규 필드).
- Firestore nested-array 금지 — 신규 필드 flat/scalar-only.
- 코드 품질: 작은 단위 작업, 의미있는 테스트만, 주석에 spec 인용 (`design.md §`, `contract.md §`).
- 분석 간 동시성 비안전 invariant — eval/batch SERIAL 유지 (병렬은 단일 분석 내부만).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | google-genai Client의 멀티스레드 동시 generate_content 안전성 (httpx 기반 추정) — 공식 미문서 | Pattern 2/4 | 병렬 콜에서 산발 오류 → 스레드별 Client 생성으로 회피 가능 (핸들은 이름 문자열이라 Client 무관) |
| A2 | 인터랙티브 rate limit이 동시 4~6콜을 수용 (belle 프로젝트 tier) | Pattern 4 | 429 → veto resource_limited 증가 = 정확도 회귀. AI Studio 콘솔 확인 + 병렬도 폴백 상수 |
| A3 | inline 총 request 한계 20MB (docs의 "<100MB inline" 서술은 interactions API 문맥으로 해석) | Pattern 3 | 크면 이득 확대·작으면 그대로 — still PNG에는 무영향, 영상 inline 임계만 조정 |
| A4 | 152s 배분(51/52/49)의 함수-단위 세부와 미계상 ~45s의 구성 — 로그 재구성 추정 | 실측 분해 | 레버 우선순위 오판 가능 → Wave 0 계측이 교정 (계측-먼저 순서로 리스크 흡수) |
| A5 | Pod RAM이 프레임 배열 캐시(~190MB×2)를 수용 | Pattern 7 | OOM 위험 시 학생 영상만 캐시로 축소 |
| A6 | 핸들 공유/still inline이 Gemini 응답 분포를 바꾸지 않음 (픽셀 동일) | Pattern 1/3 | EVAL18 무회귀 게이트가 최종 판정 (D-01이 방어) |

## Open Questions

1. **미계상 ~45s의 정체** — coach B 업로드+generate / Cerebras / hook / Firestore write 중 배분 불명. Wave 0 계측이 답. 계측 결과에 따라 coach 병렬화의 기대 수확이 달라짐.
2. **Pod 현행 env 스냅샷** — RECOGNIZER_BACKEND=gemini 활성 여부, GEMINI_VISION_VETO_ENABLED, GEMINI_MODEL override 유무 (start_server.sh는 git 밖). 실행 전 Pod SSH로 확인 필요 — 인벤토리 표의 "업로드 4회"는 전 토글 ON 가정.
3. **업로드 1회당 실제 소요** (전송 vs PROCESSING 폴링 배분) — 영상 크기 의존. 계측으로 확정 후 inline 임계(A3)와 prefetch 수확 재평가.
4. **EVAL18 cold 재실행 비용** — Gemini 크레딧 잔액 확인 ([[gemini-credits-depleted]] 이력) + 6페어 × cold 2회(before/after) 순차 실행 시간 확보.

## Sources

### Primary (HIGH confidence)
- 코드 직접 리딩 (2026-07-07): `backend/functions/pipeline/app.py` (_process 전체·veto collect·fault_zoom·complete), `sunity_shared/gemini/client.py`, `analysis/gemini_vision_scorer.py`, `gemini/coach_writer_v2.py`, `gemini/scene_finder.py`, `gemini/config.py`, `judging/gemini_moment_extractor.py`, `analysis/gemini_technique_recognizer.py`, `firestore_admin.py`, `runpod_inference/server.py`, `app/src/app/analysis/loading.tsx`, `app/src/types/analysis.ts`, `backend/evals/phase18|24|25`
- https://ai.google.dev/gemini-api/docs/files — Files API 한계치 (2026-07-07 확인)
- https://ai.google.dev/gemini-api/docs/video-understanding — inline/미디어 해상도 (2026-07-07 확인)
- https://googleapis.github.io/python-genai/ — Part.from_bytes / client.aio / files.upload (2026-07-07 확인)

### Secondary (MEDIUM confidence)
- https://ai.google.dev/gemini-api/docs/rate-limits — 인터랙티브 한도 비공개 확인 (2026-07-07)
- 프로젝트 메모리: [[flash-beats-pro-video-split-judgment]], [[pipeline-not-concurrency-safe-eval-serial]], [[gemini-latest-model-versions]], 캐시 키 충돌 이력(90d038f), 2026-07-06 20GB 적체 실증

### Tertiary (LOW confidence)
- 152s 함수-단위 배분 추정 (로그 타임스탬프 재구성 — Wave 0 계측으로 대체 예정)

## Metadata

**Confidence breakdown:**
- 코드 분해·호출 인벤토리: HIGH — 전 호출부 직접 리딩
- Gemini API 한계치·SDK API: MEDIUM-HIGH — 공식 docs 당일 확인, 단 inline 한계 서술 이중성·thread-safety 미문서
- 타이밍 배분·레버별 절감 예측: LOW — 계측 부재, Wave 0 선행으로 설계 반영

**Research date:** 2026-07-07
**Valid until:** 2026-08-06 (Gemini API docs는 빠르게 변함 — inline/interactions 서술 재확인 권장. Phase 22 shadow 전환 시 이 문서의 Gemini 레버 대부분 소멸)
