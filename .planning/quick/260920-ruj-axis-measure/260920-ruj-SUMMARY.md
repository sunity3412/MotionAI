---
id: 260920-ruj
title: 학생 영상 도착 즉시 재는 측정 스크립트를 리포에 박제
date: 2026-09-20
status: complete
---

# 260920-ruj — 측정 장비를 리포로 + **바닥 수치 정정**

## 0. 판정

**됐다.** 그리고 장비를 세우는 과정에서 **내가 belle 에게 보고한 수치 하나가 틀렸다는 것이
드러났다.** 그게 이 작업의 가장 큰 산출이다.

## 1. ★ 정정 — 현재 파이프라인의 바닥은 내가 보고한 것보다 훨씬 낮다

§14~§17 에서 belle 에게 *"정은지 자기비교 바닥이 pdshape 15.0 · elbow-twist 15.8 이고
감점 문턱이 20도라 **여유가 2.0~2.3도**"* 라고 보고했다. 그 값들은 **옛 판**(학생·기준 둘 다
rot180 이전)에서 잰 것이다. 오늘 Pod 실측(양쪽 rot180)은 다르다:

```
동작              §14 (옛 판 양쪽)   오늘 Pod (rot180 양쪽)   문턱 20도까지 여유
ref-kip-up             2.7                 2.8                  17.2
ref-peter-pan          5.0                 5.1                  14.9
ref-pdshape           15.0        →        5.8                  14.2   ★ 9도 개선
ref-power-spin         7.5                 7.5                  12.5
ref-climb              7.3                 7.9                  12.1
```

**pdshape 의 바닥이 15.0 → 5.8 로 내려갔다.** pdshape 은 역립 프레임 89.9% 동작이고,
2026-09-17 rot180 승격이 겨냥한 것이 정확히 그 자세다. **그 작업이 실제로 먹었다.**

→ **"여유 2.0~2.3도"는 인용하지 말 것. 현재 판은 12.1~17.2도다.**
→ `[미확인]` `ref-elbow-twist-sister`(역립 80.2%, 옛 판 15.8)는 **현재 판 미측정**이다.
  pdshape 처럼 내려갔을 가능성이 크지만 안 쟀다. Pod 한 번이면 닫힌다 — 우선 측정 대상.

## 2. 무엇을 만들었나

**`backend/scripts/measure_reference_axis.py`** — 분석 doc 을 읽어 한 표로:

```
편차 · 바닥대비(얹힌 양) · 감점 문턱까지 여유 · DTW 매칭 top-1 일치 · line_score · 저장 점수
```

- 운영 함수만 호출한다(`_deviation_against` · `_reference_angles_fps` ·
  `segments.ref_boundary_frame` · `dimensions.line_score`). **채점 코드 재구현 0.**
- **읽기 전용.** 전수 스캔을 일부러 막았다(`--uid` 또는 `--ids` 필수) — Firestore 무료 플랜.
- `--ref-version` 으로 기준 버전을 고정할 수 있다. 버전을 섞으면 편차가 통째로 틀린다
  ([[reference-version-mismatch-trap]]).

**`backend/scripts/reference_axis_floors.json`** — 현재 판 바닥 5동작 + 미측정 6동작 명시.

### ★ 함정 하나를 여기서 잡았다

처음 판은 기준 doc 의 `techniqueProfile` 에서 EXTEND 관절을 읽었는데 **운영과 답이 달랐다**
(line 81 vs 91). 원인: `ref-power-spin` doc 은 무릎을 `bent_ok` · 오른팔꿈치를 `extend` 라
적는데 **`ref-power-spin.yaml` 은 양 무릎 EXTEND** 다. 운영 채점기는 **yaml** 을 본다
(`gemini_technique_recognizer` → `load_grouped_criteria`). 스크립트를 yaml 쪽으로 고쳤다.

`[미확인]` **doc 과 yaml 이 왜 어긋나는지는 안 봤다.** doc 의 `techniqueProfile` 은 시딩
스냅샷으로 보이는데, 누가 소비하는지 추적하지 않았다. 별건.

## 3. 검증

오늘 Pod 분석 5건으로 스모크. 정은지 본인 영상이 **바닥 위로 +0.0도**로 정확히 나오고,
`line_score` 가 운영과 일치한다(power-spin 91).

## 4. 다음 — 학생 영상이 오면

```
backend/.venv/bin/python backend/scripts/measure_reference_axis.py \
    --uid <학생 uid> --floors backend/scripts/reference_axis_floors.json
```

그 표의 **'얹힌 양'** 이 이 축의 마지막 미지수다. 단 스크립트가 스스로 경고하듯
**그 값이 "학생이 못해서"인지 "남이라서"인지는 한 학생·한 동작으로는 못 가른다** —
같은 학생의 여러 동작, 또는 같은 동작의 여러 학생이 있어야 갈린다.

**프로세스**: `/gsd-quick` 으로 착수했으나 GSD 기본 모델(Fable) 크레딧 소진으로 에이전트를
못 띄워 PLAN·실행·SUMMARY 를 직접 작성했다(260920-ra8 과 동일).
