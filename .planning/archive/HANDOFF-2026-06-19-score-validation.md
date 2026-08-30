# Handoff — 2026-06-19 (점수 신뢰도 검증 + v2 진입 준비)

**작성:** 2026-06-19 (Phase 19 실행 후 belle 실증 세션)
**상태:** Phase 19 완료·배포·실증까지 함. 다음 = Phase 20 (v2 비전 점수) 열기. 오늘 belle가 pod 터미네이트.

---

## 오늘 한 것

1. **Phase 19 (vision-hybrid) 실행 완료** — 4 plan, 7 요구사항(SCORE-06/07, TRUST-01~05), 코드리뷰 8건 fix, 백엔드 1699 테스트 통과. main에 커밋·푸시(origin = github.com/sunity3412/MotionAI).
2. **배포** — pod(새 ID `dlwrixxe4ujmgk`, RTX PRO 4500 Blackwell)에 새 코드 pull + 서버 기동, Lambda `RUNPOD_ANALYZE_URL` 동기화. 분석은 pod에서 도므로 Lambda 코드 재배포 불필요(URL만).
3. **EAS 빌드 #21** finished + TestFlight 자동제출 예약(submission `fd0662ca`). 3D 렌더 수정 + 새 UI 포함. belle TestFlight 확인 대기.
4. **실증 eval (belle 6 성공/실패 페어, Mode1 vs 정은지 reference)** — Phase 18을 사실상 수동 실행.

---

## 핵심 발견 (재현 검증됨)

### EVAL 순차 baseline (오염 없는 확정값)
| 동작 | FAIL | OK | 판정 |
|------|------|-----|------|
| power-spin | 72 | 100 | ✅ 변별 |
| peter-pan | 79 | 100 | ✅ |
| elbow-twist-sister | 59 | 100 | ✅ |
| pdshape | 58 | 100 | ✅ |
| kip-up | **100** | 100 | ✗ 위양성 |
| climb | failed(not_pole) | failed(not_pole) | ✗ 게이트 |

- **4/6 깨끗이 fail<success** (angle 채널이 29~42° 결함 잡음). 재설계는 작동 중.
- **결정론 확정**: 같은 영상 5회(pdshape-ok 100×3, power-spin-fail 72×2) → byte-identical. 같은 입력 = 항상 같은 점수, 흔들림 0.

### 중대 실수 박제 (반복 금지)
- 처음에 **12개 `/analyze`를 동시 실행** → 파이프라인이 동시성-비안전(모듈 전역 공유)이라 결과 cross-contamination → "overall=stability 버그" 가짜 추적에 몇 시간 허비. **eval/batch는 반드시 순차.** 메모리 [[pipeline-not-concurrency-safe-eval-serial]].

---

## belle 스펙 (기록 확인 — 변경 금지)

`.planning/HANDOFF-score-accuracy.md` (2026-06-12) 박제:
- **같은 정은지 = 95~100점 범위** (객관 정확도로, tol 완화 금지, KISMAM tol=20° 유지)
- **잘못된 동작 → 50 이하 정직**
- **Gemini Vision을 점수 path에 활용** (그 문서 Stage C = "Gemini per-pose 시각 점수"가 핵심)

→ 오늘 정타=100은 95~100 범위 **충족**. 남은 위반 = "잘못된 동작 ≤50" 게이트를 **kip-up이 100으로 깸**. 해결책 = belle가 2026-06-12에 이미 정한 **Gemini 시각 점수**(= v2 비전 거부권). 방향 일관, 새로 지어낸 것 아님.

---

## 진짜 남은 문제 (3개)

1. **kip-up 위양성** (100 vs 100) — 비-각도형 실패(타이밍/완성도)는 DTW가 흡수 → 각도 채널 맹점. **v2 Gemini 시각 점수 필요.**
2. **climb 차단** — correct-climb조차 ref-climb 유사도 <25 → not_pole 게이트. ref-climb reference 품질/촬영각 문제. reference 재검토 필요(코드 fix 아님).
3. **상단 변별 + Gemini 인식기 결정성** — within-20°=정확히 100이라 good vs perfect 구분 없음. + Gemini 인식기(line 차원 결정)는 LLM이라 이론상 run마다 흔들릴 수 있음(이번 5회는 일관). → temperature 0 + reference별 profile 캐싱 박제 검토.

---

## 남은 phase (재우선순위 결과)

| Phase | 상태 | 남은 일 |
|------|------|--------|
| 15-05 | 빌드 ✓ → belle 실기기 핸드오프만 (SC4 집계 마무리) | 실증 마무리 |
| 19 | Needs Review | 3D 렌더 육안(빌드로 가능) |
| **18** 일부러-실수 eval set | Pending·미계획 | 오늘 수동 eval을 정식 fixture로 박제 (baseline = 위 표) |
| **20 (신규)** v2 비전 점수 | 미생성 | **kip-up 위양성 + 상단변별 + climb. belle 스펙(95~100, ≤50, Gemini 점수) = 게이트** |
| 10 부상위험(SAFE-01) | Pending·미계획 | 안전기능, 분석신뢰 줄기 뒤 |
| 하우스키핑 | — | 01 close-out, 02/04/05/16/17 verify, 03/06 review |

**제안 순서(belle 미확정):** 15-05 핸드오프 → 18 정식화(baseline 박제) → 20(v2). belle가 내일 최종 결정.

---

## 내일 즉시 할 일 (pod 재생성 후)

belle가 pod 터미네이트함. **Network Storage 재사용**으로 새 pod 생성 시 `/workspace`(repo·weights·스크립트) persist, **pip 패키지만 리셋**.

1. 새 pod SSH 접속 → proxy URL 확보(`https://<NEWID>-8000.proxy.runpod.net`)
2. 셋업(한 방): `bash /workspace/SunityMotion/scripts/pod_bootstrap_full.sh` (레포에 박제, apt+git pull+전체 pip deps+weights 체크. 구 `bootstrap_wave5.sh`는 STALE — gemini/cerebras/fastapi 누락)
3. 서버 기동: `source /workspace/aws_env.sh && bash /workspace/start_server.sh` (토큰=Lambda, Gemini키=SSM 자동 주입)
4. health: `curl https://<NEWID>-8000.proxy.runpod.net/health` → `{"status":"ok","pipeline_loaded":true}`
5. **Lambda URL 동기화**: `aws lambda update-function-configuration --function-name sunity-motion-pilot-pipeline --profile sunity-motion --region ap-northeast-2 --environment 'Variables={RUNPOD_ANALYZE_URL=https://<NEWID>-8000.proxy.runpod.net/analyze,RUNPOD_AUTH_TOKEN=59801424ce0960d8b2fba39afb8751a4fbfe88a67dac1c02d170b29121b07405,FIREBASE_SA_PARAM=/sunity/motion/firebase-sa,VIDEO_BUCKET=sunity-motion-pilot-videos}'`

### 검증 데이터 위치 (재사용)
- S3: `uploads/eval18/{move}{fail|ok}.mp4` (영숫자 키 — analysisId 정규식 `[A-Za-z0-9]+`, 하이픈 금지)
- Firestore eval baseline: `users/eval18/analyses/{move}{fail|ok}` (kipupfail 등)
- 순차 재실행 스크립트: `/workspace/eval18_serial.py` (네트워크 스토리지 — 동시 금지, 한 개씩)
- 로컬 원본 영상: `~/Downloads/정은지 선수 추가 영상/` (실패 6 + 잘된 예시 7)
- 페어 매핑: 실패 = 파일명(킵업/파워스핀/피터팬/클라임/엘보트위스트시스터/pdshape 잘못된예시), 성공 = `잘된 예시/fixtures:{move}-correct.mp4`

---

## 다음 세션 첫 명령 (belle 결정 후)
- 우선순위 확정 → `/gsd-phase add` (Phase 20: v2 비전 점수) 또는 18 정식화부터
- v2 게이트 = belle 스펙(같은 정은지 95~100 / 잘못된 동작 ≤50 / Gemini 점수) + EVAL baseline 표
