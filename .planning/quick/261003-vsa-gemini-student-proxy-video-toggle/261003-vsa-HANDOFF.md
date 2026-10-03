# 261003-vsa 인계 — 2026-10-03 밤 마감 (belle "이런 정리하고 낼하자")

## 관측 — 승계 가능 [확인]

**오늘 끝난 것**
- quick 261002-pa2(공급자 검토 요청 문구 + 요청 취소) 배포 완료 — layer :25 · reference-upload-url · 공급자 웹. TESTB 실토큰 P0~P4 기대값 일치. belle 폰 렌더 확인은 **보류 [미확인]** — 재개 = pa2 DEPLOY.md '선택 확인' 1번(reactivate)부터.
- quick 261003-qmg(기준 영상 Gemini prefetch + scene join 이동) — 같은 4090 Pod 교차 n=2: 점수까지 155→112초, 결과 불변.
- quick 261003-svg(프레임 추출 축소 생략 + 사후 두 갈래, `POST_STAGE_PARALLEL` 기본 ON) — 같은 4090 Pod 교차 n=2: 점수까지 118.5→105.3초 · 점수 뒤 241.8→181.5초 · 전체 360→287초, 결과 불변.
- 두 변경 모두 코드가 origin/main 에 있다 → **다음 Pod 기동(bootstrap 의 git pull)부터 운영에 들어간다.**
- Pod 0대 · Lambda `RUNPOD_ANALYZE_URL` = `https://pod-down.invalid/analyze` · SSM `pod-expected=down` [확인 조회]. 볼륨 리포 = main.

**belle 기억 "예전엔 90초 안"** — 맞다. 09-24/25 점수 전 stage 합 중앙값 44~54초(+단계 밖 ≈33초). 그때는 fixture 반복 재분석이라 recognizer 0.4~0.9초 · veto 4~14초가 캐시(TechniqueCache · VisionVetoCache, 영상 hash 키)에서 나왔다. 수강생 영상은 매번 새것이라 캐시가 없다 [진단 — 미확인, 아래].

**이번 quick(vsa)의 근거 — 남은 최대 레버**
- svg 뒤 점수까지 109초 중 ≈80초 = Gemini 가 학생 4K 원본(HEVC 2160×3840, 101MB)을 다루는 시간: 업로드→ACTIVE 36초 + 첫 generateContent 43초 [Pod 로그 `261003-svg.../evidence/svg_after*.log`].
- 로컬(프로덕션 GeminiFileSession + find_scene_flags, 1회씩): 4K 101MB = ACTIVE 37.0 + scene 54.3초 · 1080p 3.7MB = 8.4 + 4.0초 · **frame_extractor 프레임(640px, 9.99fps) 다시 묶은 0.43MB = 5.7 + 3.2초**(묶기 0.15초). scene 4 flag 세 변형 동일.
- Gemini 모델은 09-05 부터 `gemini-3.8-flash` 그대로(커밋 85105aca). belle "모델은 업뎃됐는데 속도는 떨어짐" — 서버 쪽 변화 여부는 확인할 방법이 없어 열어 둔다.

**vsa 진행 상태**
- PLAN 완료(`261003-vsa-PLAN.md`, 3 tasks — 인코더 · 부품+계약 `analysisVersion.geminiStudentInput` · `_process` 배선). 소비처 전수 9곳 중 7곳 프록시, 시간축 = 마지막 강제 프레임 뺀 T−1 장 · 실효 fps.
- 실행기는 **코드 쓰기 전에 멈췄다**(belle 마감 지시). `git status` = 추적 파일 변경 0, 커밋 0 [확인].

## 내일 할 일 (순서)

1. 실행기 재기동: 같은 PLAN 으로 gsd-executor (기본 OFF 불변식 = qmg/svg 하네스 무수정 통과).
2. Pod 동등성 검증(오케스트레이터 실행, belle 승인 = 10-03 "뭐라도 해봐" — Pod 비용 ≈$1, 2시간):
   - 스크립트 = `tools/vsa_round.sh <ip> <port> <podId> <commit> <proxy 0|1> <tag> <pair...>` (서버 재시작 시 `GEMINI_STUDENT_PROXY` · `RENDERED_COMPARE_ENABLED=0` 주입, 런마다 메타데이터만 바꾼 remux 사본으로 캐시 우회, 직렬).
   - fixture = `s3://sunity-motion-pilot-videos/fixtures/phase15/{climb,kip-up,pdshape,peter-pan,power-spin}/{correct,fault}.mp4` → scratchpad `vsa_fix/{motion}__{kind}.mp4` 로 받아 둘 것(scratchpad 는 휘발). 학생 uid 파일 `qmg_uid` 도 휘발 — 익명 1개 새로 만들면 된다.
   - 라운드 = OFF · OFF(흔들림 기준선) · ON(1회만 — 프록시는 결정론이라 2회째는 캐시 적중, PLAN '실행기/오케스트레이터가 알아야 할 것' 1).
   - 비교 = overallScore · deductionBreakdown · visionVeto verdict · recognizer 핵심 필드 · stage 시간. 기준 = OFF↔OFF 차이보다 OFF↔ON 차이가 크지 않을 것.
   - remux 사본을 intake 원장에 넣지 말 것(주 1회 학습 입력).
3. belle 판정 → `GEMINI_STUDENT_PROXY=1` 을 start_server.sh 에 박제할지 결정.

## 진단 — 재검증 대상 [미확인]

- 9월 말 90초는 반복 영상 캐시 덕이고 수강생 체감은 오늘 숫자 쪽이다. 확인 = 정은지 기준 + 처음 보는 영상 1건 실측(27-09 cold 중앙값 124.7초와 맞춰 볼 것).
- 같은 영상 8회에도 recognizer 캐시 miss — 로그 "Gemini motion 미등록" → 미등록 동작은 저장 안 하는 듯.
- 프록시 ON 이면 점수까지 ≈30~40초 — 로컬 scene 1회 기준 산술. recognizer·veto 의 실제 지연과 판정 동등성은 Pod 검증 전까지 모른다.

## 그 밖의 다음 후보

- coach B(`gemini-3.1-pro-preview`) 504 → ≈60초 대기 후 재시도, svg 측정 4건 중 3건 — 사후 병렬 구간의 바닥.
- compare_render 72초 — 혼자 남은 최장 사후 단계(RTMW 사용, 병렬 밖).
- qmg 측정 중 옛 코드 1건 fault-zoom 사후 렌더 실패(경고 1줄, 원인 로그 없음).

## 보조 파일

- `tools/vsa_round.sh` — 동등성 검증 라운드 실행기(위).
- `tools/svg_arm.sh` — 판 하나(커밋)로 서버 재시작 → E2E 1건 → 사후 끝 대기 → 로그 보존. 포트·podId 는 하드코딩이라 고쳐 쓸 것.
- `tools/fx_bench.py` — 프레임 추출 축소 생략 전후 로컬 벤치(픽셀 동일 확인).
