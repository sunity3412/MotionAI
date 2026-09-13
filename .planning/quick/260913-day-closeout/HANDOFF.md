---
title: 인수인계서 — 2026-09-13 세션
date: 2026-09-13
next_section: Pod 띄워 회전 실증 + 재학습 판단
status: 회전 코드 landing(플래그 off) · 수집 복구+한달치 완료 · 실증 미착수
---

# 인수인계서 — 2026-09-13

**§6 을 먼저 읽어라.** 관측과 좌표만 적었다. 진단은 진단이라고 표시했다.

---

## 0. 30초 요약

- **C(역립에서 관절을 못 본다)의 원인을 찾아 고쳤다.** 거꾸로 매달린 사람을
  **거꾸로인 채로 모델에 넣고 있었다.** 돌려서 넣으면 붕괴 프레임 9→0, 뼈 길이
  위반 −63%. 두 영상(다른 사람·다른 촬영)에서 재현.
- **코드는 들어갔고 플래그는 꺼져 있다.** 지금 앱 산출은 어제와 동일하다.
- **플라이휠 수집이 3주간 조용히 죽어 있었다**(08-24부터). 원인 확정·수리·재발
  방지 테스트·실패 알림까지 넣고, **한 달치를 따라잡았다(375→427편).**
  **재학습 임계 400편을 넘겼다.**
- belle 이 확정한 것: **"명백히 틀린 영상이 100점이 되는 것은 말이 안 된다."**
  (감점 게이트 설계의 기준선. 아래 §5)

---

## 1. 지금 상태 (2026-09-13 23:5x 실측)

```
브랜치   main            HEAD da4f2554     미커밋 tracked 0
게이트   pytest 4827 passed / 20 skipped / 0 failed / 0 errors
         tsc 0
수집     manifest 427편 (재학습 임계 400 돌파) · 분석 원장 384행
Pod      0대 (확인 안 함 — 오늘 띄우지 않았다)
플래그   ROT180_INVERSION_ENABLED=0  (start_server.sh:24)
마커     TRAINING-DUE.md 없음 · FLYWHEEL-BROKEN.md 없음
```

**★ pytest 수치 정정.** 09-10 인계서의 "4680 passed / 12 failed / 7 errors" 는
**오측이다.** 그 숫자는 `backend/.venv` 가 아닌 인터프리터로 돌린 결과다.
`backend/.venv/bin/python -m pytest backend/tests` 로 돌리면 리포 루트·backend
어디서든 **실패 0 / 수집오류 0** 이다. worktree 에는 `.venv` 가 없으니
**서브에이전트가 보고한 게이트 수치를 그대로 믿지 말 것.**

---

## 2. 오늘 한 것 (커밋 9개)

| 커밋 | 내용 |
|---|---|
| `c421ad21` | 회전 계획 + 실측 근거 `evidence/MEASUREMENTS.md` |
| `b3965541` | 순수 모듈 `inversion_rot180.py` — 회전·역매핑·불일치 |
| `84fe2987` | 엔진 배선 `ROT180_INVERSION_ENABLED` (기본 off) |
| `75f12516` | Pod env 자리 + `/health` 노출 |
| `c8955db2` `601d60d4` | 병합 + 요약(오케스트레이터 직접 검증본) |
| `e3004253` | 분석 원장 밀린 46건 복구 (338→384) |
| `f6b56c20` | ★ 수집 진입점 `shared/python` 경로 — 3주 정지 복구 |
| `c9415abe` | 회귀 테스트 (하위 프로세스 import) |
| `510abe33` | `FLYWHEEL-BROKEN.md` 마커 + 알림 |
| `95ad9037` | Gemini 실패의 영구 폐기 차단 |
| `da4f2554` | 한 달치 수집 375→427편 |

---

## 3. 실측 — 회전 (근거 전문 = `.planning/quick/260913-udr-.../evidence/MEASUREMENTS.md`)

로컬 격리 venv 로 **운영 추론을 바이트 수준 재현**(최대 좌표차 1.8e-06px)한 뒤 측정.

| 변형 | conf | 붕괴 프레임 | 뼈위반 p90 |
|---|---|---|---|
| 현행 1-pass | 0.567 | **9** | 2.108 |
| **프레임 180° 회전** | **0.707** | **0** | **0.776** |
| 같은 bbox 강제 + crop 만 180° | 0.519 | 0 | 2.163 |

- **분해**: 붕괴 소멸은 포즈 모델 몫, conf·뼈위반 개선은 **검출기** 몫
  → crop affine 만 돌리면 절반만 얻는다. **검출 전에 프레임을 돌려야 한다.**
- 기준 모션(정은지, 158프레임)에서 재현: conf 0.516→0.716, 붕괴 3→0,
  R전완 뼈위반 **19.9→0.83**
- **정립 프레임은 안 해친다** (0.635→0.644 / 0.582→0.670)
- 지금 운영 ON 인 PR 원근 워프는 같은 조건에서 boneCV **−2%**, 회전은 **−23%**

**기각된 것 (다시 열지 말 것)**
- SimCC 디코드 교체(softmax+min): 판별력이 안 는다 — 현행 mean **0.913** /
  mmpose min 0.912 / margin 0.694 / 엔트로피 0.917. 기존 임계 8곳 재유도 위험만 남는다
- "불일치가 conf 보다 정확하다": **과장이었다.** 독립 기준(뼈 길이) 대비 AUROC
  conf 0.807 / 불일치 0.793 / **결합 0.818**. 불일치의 값어치는 판별력이 아니라
  **임계를 놓을 골짜기**(0.33~0.51 torso)다
- 영상 회전 메타데이터 버그 / 인물 선택(`kps_batch[0]`) 오류: 둘 다 **기각**

---

## 4. 플라이휠 — 3주 정지의 전말

`.planning/FLYWHEEL-LOG.md` 의 **rc 열이 매주 증거를 남기고 있었다.**

```
08-17  신규 50  rc 0/0/0/0
08-24  신규  0  rc 1/0/1/0   ← 여기부터
08-31  신규  0  rc 1/0/0/0
09-07  신규  0  rc 1/0/1/1
```

- **launchd 스케줄은 정상이었다** (매주 월 10:07 실제 실행)
- 원인 = `359b9de5`(08-18, Gemini 모델 하드코딩 제거)가 `curate_vision.py` 에
  `sunity_shared` import 를 넣었는데 수집 진입점이 `shared/python` 을 sys.path 에
  안 넣었다. **마지막 성공 08-17 / 첫 실패 08-24 — 날짜 일치**
- 수리 + 회귀 테스트(RED 직접 관측) + `FLYWHEEL-BROKEN.md` 마커
- **한 달치 수집 결과**: 다운로드 52 / skip 221 / unavailable 46(403) / **fail 0**
  → 375 → **427편**. **Gemini 과금 0원**(캐시 969건 전부 히트 — 8월에 선별은 돼
  있었고 다운로드만 죽어 있었다)

**함께 고친 것**: Gemini 호출 실패가 `reject` 로 **영구 캐시**돼 재시도가 영영 안
되던 결함(피해 33건). 주석은 "unknown 보류"인데 구현이 달랐다. 실패 경로는 이제
캐시하지 않는다.

---

## 5. belle 과 정리된 것 — 감점 게이트

**belle 확정**: *"명백하게 틀린 영상인데 왜 100점이 되는거지? 그건 아니겠지"*
→ **"못 본 관절 감점을 지워서 점수가 올라가는" 설계는 기각.**

왜 그런 얘기가 나왔나(관측): 점수 산식이 `100 − Σ감점` 이라 감점을 지우면
점수가 오른다. 실측 powerspin **62→67**, 산술 elbow-twist **63→100**.

**★ 오늘 코드는 감점을 한 줄도 안 건드렸다** (pipeline/app.py · dimensions.py ·
deduction_engine.py 전부 `git diff` 무접촉 확인). 회전만 넣었다.

**남은 판단(급하지 않음)**: 몇 곳까지 못 봤을 때 점수를 아예 안 줄 것인가.
단 **회전을 켜면 못 보는 경우가 줄어드니, 그 숫자를 보고 정하는 것이 순서다.**

---

## 6. 다음 섹션이 할 일

### A. ★ Pod 띄워 회전 실증 (가장 먼저)

로컬 CPU 실측이 **GPU 실경로에서 재현되는지 아무도 안 봤다.** 숫자 셋을 얻는 게 목표:

1. 로컬 개선(붕괴 9→0, 뼈위반 −63%)이 CUDA 에서도 나오는가
2. **점수가 몇 점에서 몇 점으로 움직이는가** (belle 에게 예고해야 할 값)
3. "못 본 관절"이 8개 중 몇 개로 줄어드는가

절차:
1. Pod 생성 (RTX PRO 4500 Blackwell, EU-RO-1, 네트워크 볼륨 `a5z753defc`)
   — 메모리 `demo-only-pod-bring-up-procedure`
2. **리포 bundle 반입** — 오늘 커밋이 Pod 볼륨에 없다. 이게 없으면 회전 코드가
   Pod 에 존재하지 않는다
3. `start_server.sh:24` 를 `=1` 로 + Pod 사본 md5 를 리포 정본과 일치시킬 것
   (메모리 `pod-start-script-canonical-and-versioned`)
4. `/health` 에서 `envFlags.ROT180_INVERSION_ENABLED == true` 확인
5. Lambda `RUNPOD_ANALYZE_URL` 새 proxy + SSM `pod-expected=up`
6. belle 영상(`c64afae69fd24366b4b5f375aa0a91fb`) 재분석 → 위 숫자 3개 기록
7. **끝나면 즉시 Terminate + `pod-expected=down`**

★ **아직 미검증인 09-10 추정**: 분석 산출을 바꾸는 것이 Lambda 배포인가 Pod 번들
반입인가. pipeline Lambda 배포본이 **2026-07-22 판**이고 레이어도 v16(최신 v20).
**Pod 경로를 먼저 재서 이걸 확정하라.**

### B. 재학습 — 재료는 갖춰졌다 (belle 요청)

- **수집 427편 / 임계 400 돌파.** 분석 원장 admit 334 / 임계 60 (이쪽은 진작 넘음)
- 돌리는 법: 메모리 + `.planning/CONTINUE-2026-08-16.md` 래퍼 예시
  1. 5090 이상 Pod 추가 (EU-RO-1, 기존 볼륨)
  2. `bash backend/scripts/pod_doctor.sh`
  3. `TRAIN_VENV_ISOLATED=1 bash backend/training/sft/setup_train_venv.sh`
  4. preflight → label → assemble → train → gates → promote
- **직전 판(v29) 성적 = 넘어야 할 선**: 빈 골격 9/29 · faults 2 · 4동작 중 1동작만
  짚음 · **게이트 FAIL**
- ★ **반드시 함께 전달할 관측 2건**:
  · 이 학습이 좋아지게 하는 것은 **결함 짚는 눈**(Qwen3-VL)이지 관절 좌표가 아니다
    (메모리 `flywheel-trains-the-eye-not-the-coordinates`)
  · **`rtmw_error_profile.json`(247편 기반)은 회전 적용 전 산출로 잰 분포다.**
    그 위에 세운 좌표 보정 트랙(`datagen/perturb.py`)은 토대가 오염돼 있다.
    회전을 켠 뒤 **재측정**해야 한다 — **미착수**

### C. belle 이 오늘 꺼낸 미해결 2건

1. **카메라 앵글 / Gemini Omni** — belle: *"omni flash 모델 나왔으니 체크하라고
   했었고 여태 계속 개발 실패"*.
   **관측**: 메모리 `gemini-omni-1-1-flash-released-interactions-api` 에 원인이
   박제돼 있다 — `gemini-omni-1.1-flash` 는 **Interactions API 전용**이고
   `generateContent` 로 부르면 **HTTP 400 "This model only supports Interactions API."**
   7월 "탈락" 판정도 8-28 재확인도 같은 벽이었다.
   **미검증 추정**: 모델이 못 하는 게 아니라 **호출 표면이 달라서** 실패했을 수 있다.
   → 다음 세션이 Interactions API 경로로 한 번 찔러보고 판정할 것.
2. **`camera_angle_problematic` / `occlusion_severe` / `grip_visible` 이 왜
   파이프라인에만 있나** — belle: *"나머지 두개는 모르겠네 왜 파이프라인에만 있었는지"*.
   **관측**: `docs/contract.md` 에 `occlusion_high_in_phase`·`heavy_occlusion` 항목은
   있는데 `app/src/types/analysis.ts` 에는 `geminiCalls`(호출 횟수)뿐이다.
   **계약 3벌 중 앱 쪽만 안 열려 있다.**
   ★ 그리고 **승인 픽스처 4개 전부 `각도문제=False, 심한가림=False`** 다 —
   팔이 폴에 완전히 붕괴한 그 영상까지도. **신호가 있는데 발화를 안 한다.**
   표본 4개라 단정 금지. 쓰려면 먼저 이걸 재야 한다.

### D. 인스타그램 — 닫힌 건 (belle 이 먼저 꺼낼 때만)

- **익명 접근이 죽었다**: `eunji.poledancer` 포함 6계정 전부 **401 Unauthorized**
  (2026-09-13 직접 확인). 코드 주석의 "2026-07 확인" 전제가 깨졌다
- 마지막 성공 수집 **08-14** (37편은 S3 에 실물 존재 — 업로드 시각 확인함)
- **쿠키로 뚫는 것은 약관이 명시 금지**: Instagram ToU §4.2 *"...in an automated
  way without our express permission, **regardless of whether such automated access
  or collection is undertaken while logged-in**"*. 로그인 여부가 면책이 아니다
- **선수분 동의로도 안 된다**: ToU §7.2 *"This agreement does not give rights to
  any third parties."*
- **합법 경로**: ToU §4.3 *"you are free to share your content with anyone else,
  wherever you want"* — **본인이 직접 파일을 주는 것**. 원본 화질이라 오히려 더 좋다
- belle 반응: *"그건 나중에 생각하고"* → **belle 이 먼저 꺼낼 때까지 다시 묻지 말 것**

---

## 7. ★ 함정 (밟으면 시간을 태운다)

1. **서브에이전트의 게이트 수치를 믿지 말 것.** worktree 에 `backend/.venv` 가
   없어 다른 인터프리터로 돌아간다. 반드시 `backend/.venv/bin/python -m pytest`
   로 직접 재라. (오늘 "12 failed / 7 errors" 오보를 그렇게 잡았다)
2. **worktree 를 제거하기 전에 SUMMARY 를 꺼내라.** 오늘 `git worktree remove
   --force` 로 실행자 SUMMARY 를 날렸다. 코드는 병합돼 안전했지만 문서는 유실됐다
3. **`/tmp` 로그는 재부팅으로 사라진다.** 09-07 실패 원인을 이걸로 못 봤다.
   이제 `FLYWHEEL-BROKEN.md` 가 마지막 20줄을 리포에 박제한다
4. **수집은 `backend/.venv/bin/python` 으로만 돌려라.** 시스템 python3 에는
   `yt_dlp`·`gallery_dl` 이 없고, 실패를 **삼켜서** "신규 0편"으로 보고한다
5. **`GEMINI_KEY_PARAM` 없이 수집을 돌리면 0편으로 조용히 끝난다.**
   런북 §1.1 one-liner 에 그 변수가 빠져 있다. `flywheel_cycle.sh` 를 쓰면 안전
6. **수동 수집 전에 `/tmp/sunity-flywheel.lock` 을 잡아라.** 안 잡으면 월 10:07
   launchd 와 겹쳐 manifest 가 깨진다. 끝나면 `rmdir`
7. **IG 6계정은 yaml 에 `enabled: false` 인데 수집기가 그 플래그를 무시한다.**
   "false 니까 안 받겠지"로 읽으면 틀린다. 좁히려면 `--only eunji`
8. **`unjudgedJoints` 를 시뮬 doc 에서 읽지 말 것** — 09-10 에 손으로 넣은 값이다
   (`simCopy=true`). 09-09/09-10 인계서 §7 승계, 오늘도 유효
9. **복사한 doc 은 합성 경로를 못 탄다** · **`uploads/` 를 같이 옮기면 파이프라인이
   재실행돼 doc 이 failed 로 덮인다** (09-09 인계서 §7 승계)

---

## 8. 참조

```
오늘 quick 디렉터리
  260913-udr-rot180-inversion-pass/         회전 (PLAN·SUMMARY·evidence/MEASUREMENTS.md)
  260913-vqr-flywheel-collection-unbreak.../ 수집 복구 (PLAN)
  260913-day-closeout/                       이 문서

새 프로덕션 파일
  backend/shared/python/sunity_shared/analysis/inversion_rot180.py
  backend/tests/test_inversion_rot180.py · test_rtmw_engine_rot180.py
  backend/tests/phase22/test_watch_import_path.py

로컬 증거 (리포 밖 · PII · 휘발 가능)
  /Users/Shared/sunity-lr-audit/
    decompose.py · headtohead.py · orient_probe.py · tta_clean.py · conf_instruments.py
    venv/ (python3.12, rtmlib 0.0.15, onnxruntime CPU)
    weights/ (RTMW-x 384x288 + yolox_m)
    user.mp4 (belle pdshape 93.8MB) · ref.mp4 (정은지)
  ★ 수치는 전부 evidence/MEASUREMENTS.md 에 옮겨 적었다. 스크립트도 evidence/ 에 복사함
```

**belle 계정** = `csKWYvI3WCPYPysNQ9KkWecaUvq1` · **검증본** = `c64afae69fd24366b4b5f375aa0a91fb`
