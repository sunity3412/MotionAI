# tg6 Task 1 — Pod 준비 확인 + 코드 사실 박제

측정 시각: 2026-08-21T12:2xZ (UTC). 전건 SSH 원격 실측 (`root@213.173.105.5:30279`).
수리 0 / 설치 0 / 서버 재기동 0. 시크릿 값 기록 0 (변수명·길이만).

## (a) 상속 원천 — get_analysis_discovery = doc 자체 result.discovery

Pod HEAD `a6401ee5` 기준 (로컬 HEAD 와 동일 sha — 라인 번호 공용):

- `backend/functions/pipeline/app.py:4254-4258` — `_run_deferred_compare_render` 는
  `firestore_admin.get_analysis_discovery(uid, analysis_id)` 로 **그 doc 자체의
  `result.discovery`** 를 조달한다. 조달 대상 = 렌더 중인 분석 doc 하나뿐.
- `backend/shared/python/sunity_shared/firestore_admin.py:1753` —
  `def get_analysis_discovery(uid, analysis_id)` 정의 (read 짝, `_validate_discovery` 강제).
- 발굴(discovery)은 **분석 사후 belle 채택물** (app.py:4247-4248 주석 원문:
  "발굴은 분석 **사후** belle 채택물이라 어떤 실행에도 in-memory 근거가
  원리적으로 없다(호출부에도 없다) — Firestore 가 유일 진실").
- 따라서 **승인 코퍼스 doc → 신선 doc 전파 설계가 아니다.** 신선 분석
  (Task 2, `p34fresh{ts}` 신규 doc)은 `result.discovery` 가 없으므로 렌더
  freezes 에 `:discover` 항목이 **없는 것이 설계상 정상**. kgq 반영분 상속
  검증은 발굴을 보유한 운영 doc 2건의 no-write 재구동(Task 3)으로 한다.

## (b) D-di7-03 배선 이력

1. **quick-260814-di7** — 발굴 doc 영속화 + build_timeline 주입 레이어 프로덕션
   반영. 단 Pod 렌더 스테이지의 S3 discover mp3 → audio_dir 회수 경로는
   **이연 명기** (di7 SUMMARY "다음 1단계": "discovery mp3 회수 배선 — 이번
   사이클 의제 밖, D-di7-03 명기대로 그때 재검").
2. **quick-260814-ghs** — 회수 배선 구현: `app.py:4245-4286`
   (discovery 조달 + mp3 basename 회수(`audio_dir/<basename(mp3Key)>`) +
   doc_like 탑재, 전 경로 fail-open, 실패 4경로 각각 log.warning 흔적).
   검증은 **FakeS3 + monkeypatch 유닛만** (phase35 129 passed) — 프로덕션 쓰기 0,
   Pod 무접촉. ghs SUMMARY 원문: "부수 관측: 조달 성립 시
   `log.info(\"compare_render discovery 조달 n=%d rids=%s …\")` — Pod 실증 때
   이 줄이 실행 증거가 된다 ([[wiring-claims-need-log-evidence]])".
3. **운영 실행 증거는 이번 tg6 Task 3 이 최초** — 위 log.info 라인이 실 Pod
   `_run_deferred_compare_render` 재구동에서 나오는지가 판정축.

## (c) Pod 파리티 실측

| 항목 | 실측 |
|------|------|
| 서버 health | `curl localhost:8000/health` == **200** (SSH 경유) |
| Pod repo HEAD (착수 시) | `cb9e51ba` — origin/main 대비 5커밋 뒤 (전부 planning docs + pnp/o3m, backend porcelain 빈 출력) |
| ff pull | `git pull --ff-only` 성공 → HEAD == origin/main == 로컬 == **a6401ee5** |
| discovery 조달 grep | `backend/functions/pipeline/app.py` **4261** (조달 실패 warning) / **4282** (조달 성립 log.info) — ghs 배선 Pod 코드 실재 |
| start_server.sh md5 | `/workspace/start_server.sh` == repo `backend/runpod_inference/start_server.sh` == `16dc04db335938f88d253810ea1c11d5` (정본-사본 일치) |
| 서버 인터프리터 | `/usr/bin/python3` (`ps`: `/usr/bin/python3 /usr/local/bin/uvicorn runpod_inference.server:app --host 0.0.0.0 --port 8000 --workers 1`) |

## Task 2/3 env 소싱 확정 (서버 동일 env)

- 방법: `source /workspace/aws_env.sh && source /tmp/tg6_env.sh` 후
  `/usr/bin/python3` 로 드라이버 실행. `/tmp/tg6_env.sh` = 정본
  `/workspace/start_server.sh` 의 **head -43** (pkill/uvicorn 기동 라인 45-51 앞
  전부 — export 블록 + SSM 토큰 조회 포함, 서버 기동과 동일 경로).
- 소싱 검증 실측 (값 미기록): `RTMW_ONNX_PATH` 실파일(368,653,488B
  rtmw-x-384.onnx) / `YOLOX_ONNX_PATH` 실파일(101,259,744B yolox_m.onnx) /
  `FIREBASE_SA_PATH` 파일 존재 / `GEMINI_API_KEY` len=53 (SSM 조회 성공) /
  `RECOGNIZER_BACKEND=gemini` / `GEMINI_VISION_VETO_ENABLED=1`.
- env 변수명 목록 (start_server.sh export 블록): AWS_DEFAULT_REGION,
  CEREBRAS_KEY_PARAM, GEMINI_COACH_ENABLED, GEMINI_VISION_VETO_ENABLED,
  GEMINI_MAX_VETO_WALL_S, GEMINI_UPLOAD_PREFETCH, GEMINI_FANOUT_WORKERS,
  STUDENT_FRAME_CACHE, GEMINI_MOMENT_MODEL, GEMINI_SPOTCHECK_MODEL,
  PR_INVERSION_ENABLED, RTMW_DETERMINISTIC, RTMW_ONNX_PATH, YOLOX_ONNX_PATH,
  RTMW_DEVICE, FIREBASE_SA_PATH, LD_LIBRARY_PATH, PYTHONPATH,
  RUNPOD_AUTH_TOKEN, RECOGNIZER_BACKEND, GEMINI_API_KEY
  (+ aws_env.sh: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION).
