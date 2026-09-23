---
quick_id: 260923-swh
slug: clip-intake
date: 2026-09-23
status: complete
---

# Quick 260923-swh — 영상 받는 도구 + 짝 비교

## 판정

**된다.** 영상이 오면 메모를 시트로 옮겨 등록 → Pod 띄워 분석 → 짝 비교까지 명령 세 개다.
kip-up 짝에서 저장된 값(어깨 20.62도 · −0.7점 억제)을 그대로 재현했다.
**단 분석(analyze)은 Pod 이 있어야 실제로 돈다 — 오늘은 Pod 없이 거절 경로만 확인했다.**

## 만든 것

| 파일 | 역할 |
|---|---|
| `backend/scripts/intake_clips.py` | `register` 영상+메모 → 해시 · S3 영구 사본 · 원장 / `analyze` 앱 경로 분석 → 분석 연결 원장 |
| `backend/scripts/measure_reference_axis.py` | `--pairs` · `--pair` · `--clips` 추가. **새 계산 없음** — 편차는 기존 `deviate()`(운영 `_deviation_against`), 점수·감점은 저장값 |
| `backend/training/data/clips.jsonl` | 사람 영상 원장(신규). 소급 12행 |
| `backend/training/data/analysis_runs.jsonl` | video_hash → 분석 doc 연결(신규). 소급 11행 |
| `backend/tests/test_intake_clips.py` | 규격 위반이 코드에서 막히는지 7건 |
| `37-DATA-SPEC.md` §2-2 | clip 은 manifest 확장이 아니라 별 파일 — 이유 아래 |

## 관측

### 1. 사람 영상을 manifest 에 넣으면 안 되는 이유 `[확인: 코드]`
`gemini_teacher.eligible_for_distill` = holdout 아니고 `s3_key` 있으면 증류 후보. **동의는 안 본다.**
플라이휠이 주 1회 manifest 를 돌리므로, manifest 에 넣은 학생 영상은 자동으로 학습 후보가 되고
인물·세션 분리 평가셋이 학습셋으로 샌다. 그래서 `clips.jsonl` 을 따로 뒀다. 데이터 디렉터리를
glob 하는 학습 코드는 없다(확인). 분석 doc 은 `learningOptIn=False` 로 만들어진다(e2e 경로).

### 2. 소급 — 연결이 증거로 확정됐다 `[확인]`
- 분석 doc id 11건: 지난 세션 대화 기록에서 복원(그때 리포에 안 남았다).
- 영상 ↔ doc: 앱 경로 업로드 사본 `uploads/{uid}/{analysisId}.mp4` 와 fixture 원본의 S3 ETag
  (둘 다 단일 PUT = 내용 MD5)가 11/11 일치.
- 11건 전부 commit 208dc500 · rot180_v1.

### 3. 인수 검증 — kip-up 짝 `[확인]`
```
정타 9fbe0cab 저장 100  창 [0,118) 79/118프레임  DTW 6.51
실수 e83811d3 저장 100  창 [0,118) 68/118프레임  DTW 26.94
left_shoulder 3.5 → 20.6  ·  억제: 20.62도 → −0.7점, 구간 15.89~24.33 (허용 20.0)
```
power-spin 짝으로 감점 기록 출력 경로(leg_extension −20.0 · 왼어깨 −14.3 · 억제 2건)와
elbow-twist 짝으로 "분석 기록 없음" 경로도 확인. `--clips` 는 기존 표로 10건 출력.

### 4. 등록 도구 실행 확인 `[확인]`
- 드라이런(실제 영상 2편 · 새 학생 · 짝 · 지원 밖 동작 줄): 새 영상 2 · 새 사람 1 · 짝 1,
  같은 파일을 다른 라벨로 다시 적은 줄은 **해시로 걸러지고 라벨 충돌 경고**. 쓰기 0.
- 드라이런이 **실제 사용성 버그 1건**을 잡았다 — 같은 시트에서 새 사람을 첫 줄에만 소개하면 둘째
  줄이 거절됐다. `validate_sheet` 로 고치고 테스트 추가.
- S3 `fixtures/intake/` 쓰기 권한: 시험 객체 쓰고 즉시 삭제 — 통과.
- `analyze --pending`: Lambda 주소가 자리표시자라 **거절**(설계대로). Pod 에서의 실제 분석은 미실행.

### 5. 게이트
**4999 passed / 20 skipped / 0 failed** (backend/.venv 직접, 53초). 직전 4992 + 새 테스트 7.

## 관측 — 지나가며 본 것 (진단 아님)
`fixtures/phase15/kip-up/correct.mp4`(40MB)와 기준 영상 사본 `reference/ref-kip-up.mp4`(2.3MB)는
**바이트가 다르다**(별도 인코딩). 문서들이 "정타 = 기준 영상 그 자체"라 적어 왔는데, 같은 사람·같은
촬영일 뿐 같은 파일은 아니다 `[같은 테이크인지 미확인]`. 정타 대 기준 편차(0.8~4.1도)에는 재인코딩
잡음도 섞여 있다. 어느 쪽이든 **평가에 쓰면 누수**라 clip note 에 적었다.

## belle 이 영상 줄 때 같이 받을 것 (파일마다)
```
1. 동작 이름   2. 누가 (학생이면 이름 대신 "학생 1" 처럼)   3. 잘한 것 / 일부러 틀린 것 (+무엇을)
4. 촬영 방향 (옆/앞/뒤)   5. 학생·강사면: 학습에 써도 된다는 동의를 받았는지 (모르면 "모름")
```
파일은 홈 폴더(git 저장소) 밖 `/Users/Shared/sunity-intake/<날짜>/` 에 둔다.

## 안 한 것
- 실제 영상 등록 0건(오늘은 받을 영상이 없다). 시험 등록 데이터는 원장에 쓰지 않았다.
- Pod 기동 0. 채점 코드 변경 0(이 quick 에서는).
- 다른 동작 짝의 편차 해석 0 — 도구 확인용으로만 돌렸다(m49 §1 "죽은 축" 규율).
