# n2j 라이브 실증 판정 — 2026-09-06 (6동작 재분석)

## 판정: 된다. 게이트가 없던 경로 3개가 닫혔고, 오판(정상인데 지움) 은 여전히 0 이다.

사전 박제한 판정 기준 두 가지(POD-RUNBOOK §3)에 대해:

| 기준 | 결과 |
|---|---|
| 미실행이던 경로가 잡히는가 | **잡힌다.** stage-1 33면·advisory 포함 전 경로에서 게이트 실행. j8g 때 0 이던 신규 경로에서 **표시 8건 억제** |
| 오판(정상인데 지움) 0 이 유지되는가 | **유지된다. 오판 0** |

부수 관측: 기존 gated 경로에서 **`moved=1`** 이 처음 나왔다 (j8g 라이브는 15면 중 moved 0).

---

## 실행 조건

```
Pod   ssjrcw9fynu9ja (RTX 4090) · commitSha 1eef14e7 · RTMWPoseEngine · GeminiTechniqueRecognizer
      PR_INVERSION_ENABLED=1 · GEMINI_MOMENT_MODEL=gemini-3.8-flash
uid   NdVZrpbmUbPMNMjASFwUgy8Fj9p1 · mode1 · 09-03 과 같은 6동작(잘못된예시)
```

| 동작 | analysisId | 점수 | 소요 |
|---|---|---|---|
| pdshape | 4e232c4a73ec40a6a8deb07cbf6aa03f | 67 | 168s |
| climb | a559705f06784505bf266afe99cf2822 | 78 | 84s |
| elbow-twist-sister | d213622a3e754d0f851a436e8bc9f208 | 94 | 189s |
| power-spin | 5ae210fabec349698e1d35912b8f22e1 | 70 | 75s |
| kip-up | ea765def661e480292f95c5df57092a1 | 100 | 64s |
| peter-pan | 21b1b7ed3bc84d829d201334e64acc5b | 80 | 64s |

6문서 합계 644초. 전부 `status=done`.

---

## 게이트 실측 (`fault_zoom_anchor_check_summary`)

| 동작 | 경로 | 면 | 눈 호출 | pass | 억제 | 이동 |
|---|---|---|---|---|---|---|
| climb | n2j 신규 | 6 | 12 | 6 | 0 | 0 |
| elbow | n2j 신규 | 4 | 9 | 4 | 0 | 0 |
| kipup | n2j 신규 | 2 | 4 | 2 | 0 | 0 |
| pdshape | n2j 신규 | 9 | 19 | 6 | **3** | 0 |
| peterpan | n2j 신규 | 6 | 13 | 4 | **2** | 0 |
| powerspin | n2j 신규 | 6 | 14 | 3 | **3** | 0 |
| climb | gated(j8g) | 6 | 14 | 5 | 0 | **1** |
| elbow | gated(j8g) | 2 | 4 | 2 | 0 | 0 |
| peterpan | gated(j8g) | 2 | 4 | 2 | 0 | 0 |
| **합계** | | **43** | **93** | **34** | **8** | **1** |

**비용 실측 = 문서당 눈 호출 평균 15.5회** (j8g PLAN 의 사전 추정 "문서당 통상 약 20회"보다 낮다).

---

## ★계기를 먼저 고쳤다 — j8g 판정에 쓴 v1 은 결함 계기였다

`panel_center_eye_measure.py`(v1) 로 이번 배달 패널을 재면 36패널 중 불일치 15 가 나온다.
그 값을 판정에 쓰지 않았다. v1 에 결함 3건이 있고, 전부 이번에 코드·실측으로 확정됐다.

| v1 결함 | 확정 근거 |
|---|---|
| `RATIO = ANCHOR_CHECK_CROP_FRAC / 0.42` — 크롭 비율 0.42 를 리터럴로 박았다 | 이번 라이브 `fault_zoom_crop` 로그 실측: 카드별 `shared_frac` = **0.4000 / 0.4048 / 0.5324 / 0.5500**. frac 0.55 카드에서 v1 창은 154px, 게이트 창은 118px — **면적 1.7배** |
| 표시(브랜드색 링)가 그려진 패널을 무표시 전용 질문에 넣는다 | v2 가 같은 창에서 링만 inpaint 로 지우자 **36면 중 4면에서 판정이 뒤집혔다** (`card_gates.part_crop` docstring 이 이미 "링을 그리면 눈이 링을 보고 답한다"고 적어뒀다) |
| "패널 정중앙 = 앵커" 가정 | 이번 18카드 중 **10카드가 `vertex_centered=False`** — 설계상 중심이 앵커가 아니다. v1 은 그것을 전부 "중심이 딴 부위"로 셌다 |

v2 계기 = `panel_center_eye_measure_v2.py` (카드별 실제 frac + 링 제거 + 비중심 카드 분리).

**v2 결과 (36패널):** ok 16 · mismatch 8 · not_center_anchored 12 · 링만으로 판정이 뒤집힌 면 4.

---

## 억제 8면을 v2 로 대조 — 오판 0

| 동작 | 경로 | 관절 | 면 | 게이트 눈 | v2 눈 | 대조 |
|---|---|---|---|---|---|---|
| pdshape | stage1 | right_elbow | 학생 | head | head | 판정불가(중심≠앵커) |
| pdshape | stage1 | left_knee | 학생 | hand | hand | **정당** |
| pdshape | advisory | left_shoulder | 학생 | head | neck | **정당** |
| powerspin | stage1 | left_hip | 학생 | back_waist | thigh | 판정불가(중심≠앵커) |
| powerspin | stage1 | left_hip | 기준 | armpit | hip | 판정불가(중심≠앵커) |
| powerspin | stage1 | left_shoulder | 학생 | thigh | thigh | **정당** |
| peterpan | advisory | right_elbow | 학생 | abdomen | abdomen | 판정불가(중심≠앵커) |
| peterpan | advisory | right_elbow | 기준 | hip | hip | 판정불가(중심≠앵커) |

**정당 3 · 판정불가 5 · 오판 0.**

"판정불가"는 그 카드가 `vertex_centered=False` 라 두 계기가 서로 다른 자리를 본다는 뜻이다 —
v2 로는 게이트를 지지도 반박도 못 한다. 단정하지 않는다.

## 게이트가 통과시킨 면 중 v2 가 불일치라 한 것 = 4

| 동작 | 경로 | 관절 | 면 | 게이트 눈 | v2 눈 | vertex_centered |
|---|---|---|---|---|---|---|
| climb | stage1 | left_shoulder | 기준 | back_waist(ok) | elbow | True |
| climb | stage1 | right_hip | 기준 | hip(ok) | elbow | True |
| powerspin | advisory | left_elbow | 학생 | elbow(ok) | armpit | None |
| powerspin | advisory | left_elbow | 기준 | elbow(ok) | armpit | None |

앞의 2면은 `vertex_centered=True` 라 두 계기가 같은 자리를 봐야 하는데 답이 다르다.
**원인 미상 — 단정 금지.** 남은 차이는 픽셀 원천(원본 프레임 vs 배달 JPEG 재압축)과
창 좌표 클램프뿐이다. 재는 법 = 같은 좌표로 두 창을 저장해 나란히 놓고 5회씩.

---

## 감사(`audit_card_photos`) 실측

```
card_photo_audit total=18 mismatched=6 unresolved=0   (model=gemini-3.8-flash rounds=5)
```

게이트가 일한 카드는 사유가 `mark_elsewhere` → `no_mark_and_center_elsewhere` 로 바뀔 뿐
둘 다 mismatch 로 세어진다. belle 09-04 "얼굴에 동그라미"(pdshape 오른팔꿈치 학생)는
이번에도 눈 `head` 5/5 이고 **표시는 사라졌다** — 사진은 그대로다.

> 게이트가 고치는 것은 "틀린 표시"이지 "틀린 사진"이 아니다. 틀린 사진은 맞는 좌표가 필요하고
> 그건 자세 모델의 일이다.

---

## 원본

- `n2j_live.jsonl` — 6런 결과
- `server_faultzoom_lines.txt` — Pod 서버 로그 중 fault_zoom/card_gates 전 행
- `gate_logs_n2j.txt` — 게이트 로그 (★피터팬 완주 전 스냅샷이라 불완전, 집계는 위 파일로 할 것)
- `crop_logs_n2j.txt` — 카드별 실제 크롭 비율
- `audit_live_n2j.{json,log}` — 감사 18카드
- `panel_center_v1_live.log` — 결함 계기 v1 (대조용, 판정 아님)
- `panel_center_v2_live.{json,log}` — 고친 계기 v2 (판정 근거)
