---
quick_id: 260922-gnj
slug: mode1
date: 2026-09-22
status: complete
---

# Quick 260922-gnj — Mode1 안정화 측정 (belle 지시: *"mode1 정은지와 비교하는 것만이라도 오늘 좀 안정화를 찾아봐"*)

## 판정 — 셋

1. **재현성은 문제 아니다.** 같은 영상이 GPU·Gemini 조건을 바꿔도 차원까지 동일하다.
2. **변별은 5동작 중 4동작에서 된다.** 정은지 정타 100 vs 일부러 틀린 영상 66~89.
3. **kip-up 만 변별 0 — 고장이다.** ("한계"라고 적었다가 같은 날 철회했다. 아래 §정정)

---

## 관측 (잰 값·코드 사실)

측정 환경: Pod `m2czli3w4wqpe5` RTX 4090 EU-RO-1 · commitSha `208dc500` ·
기준 라이브러리 `rot180_v1` · `PR_INVERSION=1 ROT180_INVERSION=1 RTMW_DETERMINISTIC=1` ·
`MODE3_REFERENCE_RELATIVE` 미설정(OFF) · 경로 = `e2e_app_path.py`(앱과 동일 순서) · 직렬.

### 축 A/C — 정타 vs 실수 (mode1, 각자 자기 기준 모션 대비)

| 동작 | 정타 | 실수 | 분리 | criteria yaml |
|---|---|---|---|---|
| power-spin | 100 | **66** | 34 | 21행 (무릎 EXTEND 2) |
| peter-pan | 100 | **85** | 15 | 7행 (criteria 전부 `[]`) |
| pdshape | 100 | **87** | 13 | 7행 (`[]`) |
| climb | 100 | **89** | 11 | 7행 (`[]`) |
| kip-up | 100 | **100** | **0** | 7행 (`[]`) |

정타 5/5 전부 100점 · 감점 기록 0건 · `visionVeto` not_applicable.
`elbow-twist-sister` 정타는 **112.6MB > MAX_VIDEO_BYTES 100MB** 로 upload-url 400 →
앱 경로 측정 불가(제품 자기 한도, 결함 아님). 재인코딩은 입력을 바꾸므로 안 했다.

### 축 B — 재현성 (power-spin 정타, 같은 파일)

| 런 | Pod/GPU | Gemini | 점수 | 차원 |
|---|---|---|---|---|
| 1 | L4 (구 Pod) | 캐시 히트(09-20 저장 답) | 100 | angle 100 · line 91 · stability 84 |
| 2 | 4090 (신 Pod) | 캐시 히트 | 100 | angle 100 · line 91 · stability 84 |
| 3 | 4090 (신 Pod) | **캐시 doc 삭제 → 신규 호출** | 100 | angle 100 · line 91 · stability 84 |

→ GPU 교체 + Gemini 신규 호출에도 **차원까지 동일**.
캐시 키 = `{video_sha256}__{motion_query}` + model + yaml_version (`technique_cache.py`).
수강생 첫 업로드는 항상 캐시 미스이므로 런3 이 그 경로를 대표한다.

### 감점 출처 (`deduction_engine.py:82` — 3종)

```
power-spin 실수  -20.0  ipsf_absolute      (criteria yaml 무릎 EXTEND)
                 -14.3  reference_relative (정은지 대비)
climb 실수        -3.1  reference_relative  source=geometry  왼팔-몸통 각
                  -8.3  reference_relative  source=geometry  오른 무릎
kip-up 실수       0건   두 축 모두 침묵
```
감점마다 한국어 `cueLine` + `coachQuestion` 동반 — 수치가 아니라 처방이 나온다.
power-spin 실수: baseline 100 · 상한 40 · raw −34.3 → 66, `line` 차원 91 → **0**
(micro-bent 0점 트랙 발화).

### kip-up 실수 Pod 로그 — 어깨를 찾았는데 붙일 기준이 없다

```
fault_zoom_anchor_check  joint=left_shoulder  criterion=none  action=pass
fault_zoom_crop          region=arms          criterion=none
fault_zoom_angle_bake    criterion=none       angle_bake=omitted:no_criterion
card_gates 스킵          (records/freezes/report 부재)
```
`deductionBreakdown`: final 100 · executionRawTotal 0 · records 0 ·
**coverageGaps `[]`** (= "검사할 게 없었다"는 표시조차 안 남는다) · visionVeto not_applicable.

### 인프라 관측

- 첫 Pod(L4)의 서울 S3 링크가 **붕괴**했다: 57 KB/s → 20 KB/s → 0.9 KB/s.
  climb 이 104분에 5.5MB 를 받았다. 교체한 4090 Pod 은 **3.29 MB/s**, 런당 70~151초.
- 런1 단계별: `s3_download` 905초(전체의 80%) / 분석 자체 3.7분 / `rtmw` 5.7초.
- `start_server.sh` 의 `endpoint_sync` 는 SSH 세션에서 `RUNPOD_POD_ID` 를 export 해야
  발화한다(컨테이너 env 가 SSH 세션에 안 실린다). export 하면 Lambda·SSM 자동 갱신.
- 볼륨 사본 `/workspace/start_server.sh` 가 낡아 있었다(`d756bf…` → 리포 `2a59f5…`).

---

## 진단 (승계 전 재검증 대상)

- **`reference_relative` 가 빈-criteria 동작의 실질 채점 축이다.** climb/peter-pan/pdshape
  가 criteria 없이도 11~15점 분리하는 것이 근거. 2026-06-27 이 후임으로 지목한 축이
  실제로 동작한다 ([[criteria-yaml-emptied-on-purpose-successor-named]] 확인).
- **kip-up 침묵의 원인은 허용오차 문턱이다** — 메모리 기록(어깨 편차 20.6도 vs 허용오차
  20도 → 0.6도 초과 = −0.7점 + 신뢰구간 억제)과 이번 관측(어깨를 앵커했는데 criterion
  없음)이 같은 방향. `[미확인]` 이번 실행에서 seed 값/CI 를 직접 찍어 확인하지는 않았다.
  → 허용오차를 낮추면 숫자는 맞출 수 있으나 **커브핏**이고, belle 판단은
  *"둘 다 점수로서는 옳다"* 였다. 그 동작의 결함 정의는 yaml 주석이 belle 도메인으로
  이미 지목해 놨다("실결함 검출은 별 트랙").

## 내가 중간에 틀렸다가 고친 것

1. `[정정]` "s3_download 15분은 지역 탓, 실증 대기시간이 된다" → **그 Pod 링크 고장**이었다.
   교체 후 같은 구간 16초. 실증 대기 걱정거리 아니다.
2. `[정정]` "kip-up 이 멈췄다" → 멈춘 게 아니라 느렸고 completion 까지 갔다(88분).
3. `[정정]` "criteria 가 빈 4동작은 채점을 아예 안 한다" → **틀렸다.** climb·peter-pan·
   pdshape 가 빈 criteria 로도 변별한다. 침묵은 kip-up 하나다. kip-up 1건으로
   일반화하려 했던 것이 성급했다.

## 사고 1건 (같은 함정 반복 금지)

드라이버 `--timeout` 을 900s 고정으로 둬서, 느린 Pod 에서 kip-up 이 안 끝났는데
배치가 climb 을 제출했다 — **동시 분석 2건**. 겹친 두 건은 기록에 `(overlapped)` 로
표시했고, 새 Pod 에서 전부 재측정해 표의 수치는 전부 단독 실행분이다.
이후 러너는 `--timeout 5400` + 앞 런 terminal 대기로 바꿨다.

## 안 한 것

- 허용오차·문턱 수정 0건 (커브핏 금지).
- 채점 코드 변경 0건. 오늘 리포 변경은 `pod_teardown.py` 안전 수리(260922-gav)뿐이다.
- 학생 영상 0편 — 오늘 전부 정은지 fixture다
  ([[firestore-analyses-are-fixtures-not-students]] 그대로).


---

## ★ 정정 — "kip-up 은 고장이 아니라 한계"를 철회한다 (2026-09-22 belle 대화)

화면에 나가는 문장을 꺼내보니, 일부러 틀린 영상에 앱이 이렇게 내보낸다:
```
100점 / "측정된 감점 항목이 없었어요 — 지금 자세를 유지해보세요"
     / "정은지 선수와 거의 동일한 자세입니다 · 관절각 일치도 99점"
     / 보완운동 0건 · 확대카드 1장(criterion=none)
```
**틀린 자세를 유지하라고 단언한다.** 수강생 입장에서 이건 고장이다.
무너지는 곳은 판정이지 파이프라인이 아니다(비교·카드까지 다 돈다).

## belle 도메인 판독 (사진 육안, 정타/실수 정지컷)
1. 다리가 뜬 **높이** — 정타가 훨씬 높다. ★**각도 축에 이 표현이 없다**
   (`JOINT_KEYS` 8개 전부 관절 굽힘각).
2. **왼팔** — 정타는 잘 굽어 있고 실수는 펴져서 힘을 덜 받는다.
belle 가설: **팔이 원인, 높이가 증상** — 원인 쪽은 이미 재고 있다 `[미검증]`.

## 내 짜맞춤 1건
belle 이 팔을 짚은 뒤 나는 왼팔꿈치 **중앙값 3.5도**(허용오차 20도)를 "방향이 같다"고
내밀었다. 작은 줄 알면서 맞는 쪽을 골랐다 — belle 이 *"또 내 말에 짜맞춰서 하는 거 아니냐,
100점이라고 했잖아"* 로 잡아냈다. 왼어깨 31.8도는 사진 받기 **전** 표에 있었으므로 그건
짜맞춤이 아니지만, **사후 발굴은 분석이 한 일이 아니다.**

## 06-27 무릎 라벨은 낡았다
실측 무릎 최소각: 정타 149.8 / 실수 160.6 — **정타가 더 굽는다**(라벨과 반대).
