# 260920 — reference_relative 바닥 해부 (SUMMARY §14 증거)

§13 이 남긴 질문("동작별 상수 오프셋이 어디서 오나")에 답하려고 돌린 측정 일체.
**Pod 0 · Gemini 0 · GPU 0.** Firestore 는 읽기만(약 3,100건).

## 재현 순서

모두 `backend/.venv/bin/python` 으로 돌린다. 스크립트 상단의 `D` 경로가 세션 scratchpad 를
가리키므로, 재현하려면 그 값을 이 디렉터리로 바꾸고 아래 순서대로 데이터를 다시 받는다.

```
1. scan.py            collection_group('analyses') 경량 전수 스캔  -> scan.json      (1,250 read)
2. fetch_angles.py    대상 875건 angles + 기준 11편 전문           -> students.json / references_full.json  (886 read)
3. fetch_src.py       videoKey / sourceLabel / fileName            -> src.json       (853 read)
4. fetch_versions.py  reference/{id}/versions/* + createdAt 분포    -> ref_versions.json  (11 read)
5. baseline.py        라이브 기준으로 875건 편차 전수               -> baseline.json
6. facts.py           라벨(correct/fault/self/upload) 부착          -> facts.json
```

데이터 파일(students.json 등)은 용량이 커서 커밋하지 않았다. 위 1~4 를 다시 돌리면 생긴다.

## 측정 스크립트 (§14 의 각 절에 대응)

| 파일 | 답하는 것 | SUMMARY |
|---|---|---|
| `harness.py` | 공용 하네스. 운영 `pipeline/app.py::_deviation_against` 를 그대로 호출 | 전 절 |
| `is_correct_the_reference.py` | `correct.mp4` 가 기준 영상 그 자체인가 | §14-1 |
| `recheck_selfgate.py` | §12-2 의 타당성 게이트를 세 방법으로 다시 걸기 | §14-2 |
| `version_probe.py` | 09-17 rot180 승격이 기준을 얼마나 옮겼나 | §14-3 |
| `matched_floor.py` | 버전을 맞춘 바닥 정본표 | §14-3, §14-4 |
| `grid_effect.py` | 시간 격자 몫 (보간 상한) | §14-4 |
| `same_frame_probe.py` | 같은 원본 프레임에서 두 추출이 다른가 | §14-4 |
| `keypoint_probe.py` | 다른 만큼이 키포인트 어디에 있나 (Procrustes) | §14-4 |
| `chance_matched.py` | 바닥 / 우연 비 (버전 일치) | §14-4 |
| `self_score.py` | 정은지 본인 영상의 점수 (profile=None) | §14-2 |
| `version_vs_score.py` | 같은 분석을 두 기준 버전으로 채점 | §14-3 |
| `final_table.py` | 정본 소비처 표 (운영 tally, profile=기준doc) | §14-5 |

## `agents/`

워크플로 서브에이전트 7종(self-floor / angle-range / alignment / joint-anatomy /
camera-view / consumer / matching-recheck)과 그 적대 검증 7종이 남긴 스크립트·산출물.
용량 400KB 초과 산출물 2건(`G_match.json`, `b_c5_consumer.json`)은 제외했다 —
각각 `G_match_compute.py`, `b_c5_consumer.py` 를 다시 돌리면 생긴다.

## 주의

- **`facts.json` 의 `scalar`/`dev` 는 라이브(rot180_v1) 기준으로 계산된 값이다.**
  09-17 이전 분석에는 버전 불일치가 섞여 있다. 정본은 `matched_floor.json` 쪽이다.
- 이 조사가 쓰는 "편차 스칼라"(관절별 median 8개의 중앙값)는 **운영에 없는 집계**다.
  운영은 관절마다 criterion 하나씩 심는다(`app.py` `_emit_reference_relative`).
- `final_table.py` 는 `vision_pointed_joints` worst-window 분기가 꺼진 상태다 —
  이 축 단독 하한이지 운영 mode1 점수가 아니다(§14-6).
