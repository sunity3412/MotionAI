---
id: 260913-udr
slug: rot180-inversion-pass
date: 2026-09-13
status: complete
verification: 로컬 게이트·직접 실측 PASS · GPU 실경로 미검증 (Pod 0대)
commits: [b3965541, 84fe2987, 75f12516, c8955db2]
---

# rot180 inversion pass — 요약

**판정: 된다 (로컬 범위). 배선 완료, 플래그 off 로 출하. GPU 실경로는 미검증.**

---

## 무엇을 했나

역립 클립이면 프레임을 180° 돌려 **검출부터 다시** 하고, 얻은 좌표를 원본 공간으로
되돌려 쓴다. 두 패스가 관절별로 얼마나 다른지 재서 **로그에만** 남긴다.
**감점·점수·계약은 건드리지 않았다.**

| 커밋 | 내용 |
|---|---|
| `b3965541` | 순수 모듈 `inversion_rot180.py` — 회전·역매핑·불일치 계기 |
| `84fe2987` | 엔진 배선 `ROT180_INVERSION_ENABLED` (코드 기본 off) |
| `75f12516` | Pod env 자리 + `/health` 노출 |
| `c8955db2` | main 병합 |

## 오케스트레이터가 직접 잰 것 (실행자 보고를 믿지 않고 재실행)

### 게이트 — 실제 트리 + `backend/.venv`

```
기준선 (신규 테스트 2파일 제외)  4802 passed, 20 skipped, 0 failed, 0 errors
착수 후                          4821 passed, 20 skipped, 0 failed, 0 errors
                                 = 정확히 +19 (신규), 회귀 0
```

★ 실행자는 "4699 passed / 12 failed / 7 errors" 로 보고했다. **틀린 수치다** —
worktree 에는 `backend/.venv` 가 없어 다른 인터프리터로 돌아간 결과다.
09-10 인계서에 적힌 "실패 12 / 수집오류 7" 도 같은 원인일 가능성이 높다.
**게이트는 `backend/.venv` 로, 리포 루트나 `backend/` 어디서든 돌리면 전부 초록이다.**

### 게이트 거동 — mock 추론기로 직접 확인

| 조건 | 추론 호출 | 결과 |
|---|---|---|
| 정립 · 미설정(코드 기본) | 12/12 | 1패스 |
| 정립 · 명시 `0` | 12/12 | 미설정과 **산출 바이트 동일** |
| 정립 · 켬 | 12/12 | **1패스 — 켜도 헛돌지 않는다** |
| 역립 · off | 12/12 | 1패스 |
| 역립 · 켬 | **24/12** | 2패스 + **산출 변화** = 2차가 실제로 채택됨 |

프레임 밖 좌표를 2차가 내면 fail-safe 가 거부하고 1차를 유지하는 것도 확인했다
(첫 시도에서 프레임 밖 난수 좌표를 넣었더니 2패스가 돌고도 산출이 안 바뀌었다 — 옳은 거동).

### 경계 — 금지 파일 무접촉 (`git diff` 로 확인)

`inversion_warp.py` · `temporal.py` · `features.py` · `dimensions.py` ·
`docs/contract.md` · `app/src/types/analysis.ts` 전부 변경 0.

### 3패스 금지 — 코드로 강제됨

`rtmw_engine.py:246-252` 가 `if/else` 다. ROT180 이 켜지면 `_maybe_second_pass_rot180`
로 **return** 하고 PR 훅은 호출되지 않는다.

## 계획에서 바뀐 것 — 코디네이터 정정 2건

**정정 1 (버그 예방).** 계획의 "프레임별 torso 로 정규화"는 붕괴 프레임에서 폭주한다.
실측: 프레임별 torso p1 = **0.00px** → 불일치 p99 **5.98e10**.
클립 중앙값 스칼라 1개로 바꾸면 같은 데이터에서 p99 **3.191**.
`clip_torso_median()` 으로 구현되고 독스트링에 실측이 박제됐다.

**정정 2 (문구).** "불일치가 conf 보다 정확하다"는 **과장이었다**. 독립 기준
(뼈 길이 항상성 — 두 계기 어느 쪽으로도 정의되지 않음) 대비 AUROC:

```
conf 0.807 · 불일치 0.793 · 둘 결합 0.818
```

판별력은 **대등하다**. 불일치의 값어치는 **임계를 놓을 골짜기**(0.33~0.51 torso)이고
conf 분포는 단봉이라 그 자리가 없다. 결합이 둘 중 어느 쪽보다 낫다 — 후속 검토 대상.

## 검증 못 한 것 (정직하게)

- **GPU 실경로 전부.** Pod 0대. `evidence/MEASUREMENTS.md` 의 §2~§5 는 로컬 CPU
  (onnxruntime CPUExecutionProvider) 실측이다. CUDA EP 에서 같은 수가 나오는지 안 쟀다.
- 실영상 end-to-end 로 점수가 어떻게 움직이는지. 이번엔 감점을 안 건드렸으므로
  **플래그 off 인 한 점수는 움직이지 않는다**는 것만 구조로 보장된다.

## 켜는 절차 (이번 작업 아님 — belle 승인 후)

1. `backend/runpod_inference/start_server.sh:24` 를 `=1` 로
2. Pod 의 `/workspace/start_server.sh` 사본 md5 를 리포 정본과 맞출 것
   (메모리 `pod-start-script-canonical-and-versioned`)
3. 재기동 후 `/health` 의 `envFlags.ROT180_INVERSION_ENABLED == true` 확인
4. belle 영상 재분석 → `evidence/MEASUREMENTS.md` §2 수치가 GPU 에서 재현되는지 대조
5. 끝나면 즉시 Terminate + SSM `pod-expected=down`

## 후속 (열어둔 것)

- ★ **판정 불가가 만점으로 번역된다** — `final = max(25, 100 − Σ감점)` 이라 record 0 이면
  100점 (실측 powerspin 62→67, 산술 elbow-twist 63→100). 불일치로 감점을 막으려면
  `wouldBePoints` 동반이 **필수**다. 이것 없이 게이트를 켜지 말 것.
- **`rtmw_error_profile.json` (247편) 재측정** — 회전 적용 전 산출로 잰 분포다.
  그 위에 세운 좌표 보정 트랙(`datagen/perturb.py`)은 토대가 오염돼 있다.
- **SimCC 디코드 교체는 열지 말 것** — 실측상 값이 없다:
  현행 mean 0.913 / mmpose min 0.912 / margin 0.694 / 엔트로피(tau=10) 0.917.
  기존 임계 8곳 재유도 위험만 남는다.
- `rot+pr` 조합이 `rot` 단독보다 boneCV −7% 더 낫다(0.404→0.375). 3패스 비용과 저울질.
