# Phase 35 렌더 입력 데이터 (Pod 볼륨 회수 영구본)

**이후 렌더는 이 디렉터리를 입력으로 사용한다 (임시폴더 아님).** 재부팅/Pod 소실이
재발해도 이 데이터 + S3 영상 원본만으로 합성 비교 영상 5편을 재현할 수 있다.

## 출처

- RunPod `pqe6uaw7mf8bh9` 볼륨 `/workspace/p35`, 회수일 2026-08-08 (`p35_volume.tgz`).
- 생성 스크립트: `backend/scripts/p35_extract_align.py` (rtmlib RTMW GPU 15fps 재추출
  + 자세거리 DTW 정렬 + 짝 재선정 + 마커 좌표).

## 파일 구성 (9동작 20파일)

| 동작 | 파일 | 비고 |
|------|------|------|
| elbow | align.json, doc.json | 활성 렌더 슬롯 |
| powerspin | align.json, doc.json | 활성 렌더 슬롯 |
| kipup | align.json, doc.json, moments.json | 활성 렌더 슬롯 (r00 순간은 align pairs 주입) |
| pdshapefault | align.json, doc.json | 활성 렌더 슬롯 (S3 키는 pdshape_v3 — 현행 매핑) |
| peterpan | align.json, doc.json | 활성 렌더 슬롯 |
| pdshape | align.json, doc.json | 벤치 슬롯 (correct 영상) |
| realupload | align.json, doc.json, moments.json | 벤치 슬롯 |
| climb | align.json, doc.json | 발굴 스윕 후보 (렌더 슬롯 아님) — quick-260816-r7k 로 재생성됨(06-17 정은지 세트 기준). quick-260816-c3m 이 만든 구버전(05-22/06-11 배치 기준)은 무효화·대체됨 |
| climbfault | align.json, doc.json | 발굴 스윕 후보 (렌더 슬롯 아님, quick-260816-r7k 신규) — 기준 교체 전에는 doc.json 자체가 생성 불가(NotPoleMotionError)였음 |
| combo | align.json, doc.json | 발굴 스윕 후보 (렌더 슬롯 아님, quick-260816-c3m — P35 렌더 미실행) |

## 검증 결과 (2026-08-08)

- 활성 5슬롯(elbow, powerspin, kipup, pdshapefault, peterpan) 기계검증 PASS —
  baseline 렌더 5편 리그(verify_render_prototype.py) ALL PASS + v6 길이 근사 재현.
- pdshape(correct)·realupload 2건은 구버전 포맷(refKp 없음) — 벤치 슬롯이라 무해,
  렌더러(render_compare_prototype.py)도 refKp 를 선택 필드로 다룬다.
- verify/ 스틸 87장(62MB)은 미커밋 — 재생성은 Pod 에서 한 줄:
  `RTMW_DEVICE=cuda python3 scripts/p35_extract_align.py --workdir /workspace/p35`

## 검증 결과 (2026-08-16, quick-260816-c3m)

- climb·combo 2건은 SIM_UID(fvcNXzEqKjgqVxRPVSj1iwFnIpn2) 직접 _process 로 신선
  생성(status=done) + Pod RTMW GPU 15fps 재추출로 align.json 생성 완료. 둘 다
  `discover_sweep.py::source_gate()`(quick-260814-ehz-5, 원본 무편집) PASS —
  align 스키마 11필드 + fps 교차검증(라벨 15.0 vs 실측 프레임/길이) 전부 통과.
  climb/combo 는 `proto/phase35/{motion}_v3.mp4` 산출이나
  `render_compare_prototype.py` 실행이 없다(발굴 스윕 소스 게이트 통과만 목적 —
  렌더 슬롯 아님).
- **climbfault(`fixtures/phase15/climb/fault.mp4` vs `ref-climb`, Mode 1)는
  이번 사이클에서 doc.json 자체가 생성되지 않았다** — SIM_UID direct-process 중
  `NotPoleMotionError: angle 0 < 25`(KISMAM 각도 유사도 안전망,
  `models.NOT_POLE_SIMILARITY_THRESHOLD`)로 실패했고, 원인 파악 후 1회
  재시도(35.8s → 44.0s, 동일 사유 재현 — RTMW_DETERMINISTIC=1 하 결정론적)해도
  같은 결과였다. 이 fault 데모 영상이 기준 climb 동작과 KISMAM 각도 비교상
  구조적으로 너무 달라 비폴/무의미 비교 안전망이 정상 작동한 것으로 판단—
  코드 결함이 아니라 이 영상 콘텐츠 자체의 특성이며, 강제로 게이트를 우회하지
  않았다(CLAUDE.md 분석 정확도 원칙). elbow/powerspin/kipup/pdshapefault/peterpan
  의 기존 fault 영상들은 모두 같은 Mode 1 경로로 정상 통과(점수 60~83)했으므로
  이 실패는 climb/fault.mp4 고유의 콘텐츠 특성으로 보인다 — 재촬영 또는 별도
  조사가 필요하면 belle 판단.
- `foxtop`/`foxtop-split`/`invert`/`sideway-spin` 은 `fixtures/phase15/` 에
  학생 영상이 전혀 없다(정답/오답 둘 다 부재 — `aws s3 ls` 로 실측 확인,
  2026-08-16). `reference/`에는 4개 전부 기준 영상이 존재한다
  (`ref-foxtop.mp4`, `ref-foxtop-split.mp4`, `ref-invert.mp4`,
  `ref-sideway-spin.mp4`) — 즉 학생이 이 4동작을 촬영해서 올리기 전까지는
  발굴 대상이 될 수 없다. belle 촬영 계획의 근거.

## 검증 결과 (2026-08-16, quick-260816-r7k — ref-climb 기준 영상 교체)

**배경**: `reference/ref-climb` 의 기준 영상을 05-22 극초반 배치(2026-06-11 재업로드,
4,223,747 B)에서 06-17 정은지 성공 클라임 세트(`fixtures/phase15/climb/correct.mp4`,
40,928,589 B)로 교체(belle 2026-08-16 결정 — 2026-06-21 "하나만 쓴다면 이전 것 우선"
결정을 촬영 형태 불일치 실측 근거로 뒤집음). 이 교체로 위 c3m 이 만든 climb 의
doc.json/align.json 은 **구 영상 기준이라 무효** — 이번에 새 영상 기준으로
재생성했다.

**climb (correct.mp4 vs 새 ref-climb) — status=done, records=0**
- dimensionScores: `{'stability': 93, 'angle': 100}`, overallScore=100
- align: userFrames=119, refFrames=119, fps=15.0, pairs={} (deductionBreakdown.records=0
  → 짝으로 잡을 결함 구간 자체가 없음 — 렌더 슬롯 아니므로 무해, `combo` 의 기존
  align.json 도 동일하게 pairs={})

**climbfault (fault.mp4 vs 새 ref-climb) — status=done, 교체 전 완전 차단이 해소됨**
- 교체 전(2026-08-16 실측, plan 작성 시점): `NotPoleMotionError: angle 0 < 25` 로
  완전 차단(2회 재현, 결정론적). doc.json 자체가 생성되지 못했다.
- 교체 후: `angle` 유사도 **0 → 86** (차단 해소), dimensionScores:
  `{'stability': 93, 'angle': 86}`, overallScore=86. climb(정답, 100)과 climbfault
  (오답, 86)가 비로소 순서대로 갈린다 — belle 이 짚은 "짝이 어긋나 있었다"는 관찰이
  이 수치로 확정됨.
- align: userFrames=91, refFrames=119, fps=15.0, pairs={} (deductionBreakdown 키 자체가
  doc.json 에 없음 — climb 과 달리 "records=0" 조차 아니라 필드 부재. 원인 미확정,
  아래 "실행 중 발견된 문제" 참조).

**실행 중 발견된 문제 — P35 Pod 스크립트의 프레임 캐시 구멍**

1차 실행(Pod, `r7k-task4-pod.sh`)에서 climb 의 align 재추출이 `refFrames=256` 을
냈다 — 새 `ref.mp4`(40,928,589 B, 새 영상) 를 정상적으로 재다운로드했음에도, 이미
새 영상 기준의 결과가 아니었다(256 은 구 영상 기준 c3m 08-16 오전 실행분의 프레임
수). 원인은 스크립트가 `ref.mp4` 파일만 지우고 `p35_extract_align.py` 가 그 영상에서
뽑아 로컬에 캐시하는 RTMW 프레임 디렉터리 `rf15/`(및 `verify/`)를 안 지운 것 —
`compare_align` 모듈이 `rf15/` 존재 시 재추출 없이 캐시를 그대로 재사용하는 경로가
있어, 새 영상을 내려받고도 옛 영상에서 뽑은 프레임으로 정렬한 것이다. belle 이
`ls -la` 로 `climb/rf15`(최종수정 06:00, 오늘 아침 c3m 실행분) vs `climbfault/rf15`
(최종수정 09:13, 이번 신규 추출) 의 mtime 불일치로 원인을 특정하고,
`rm -rf /workspace/p35/climb/{rf15,verify}` 후 climb 만 재추출해 `refFrames=119`
(climbfault 와 일치)로 수리했다. **레포에 반영된 align.json 은 이 수리 후 버전**
(byte-검증: 회수 파일과 SHA-256 완전 일치 확인). **doc.json 의 dimensionScores(각도
유사도 점수)는 이 오염과 무관** — `pipeline._process()` 는 Firestore 기준 데이터를
읽지 프레임 캐시 파일을 읽지 않는다. 다음에 참조 영상을 바꾸는 Pod 스크립트를 쓸 때는
`ref.mp4` 뿐 아니라 그 영상에서 파생된 로컬 프레임/정렬 캐시 디렉터리(`rf15/`,
`uf15/`, `verify/` 등 `compare_align` 이 만드는 모든 캐시)도 함께 지워야 한다 —
캐시 디렉터리 이름을 영상 콘텐츠 해시 기반으로 바꾸는 게 근본 수리겠지만 이번
quick task 범위 밖이라 belle 판단 대기.

**부수 관찰 — Gemini video fan-out 1회 타임아웃(graceful skip)**

Pod 실행 로그에 `video fan-out 실패 — skipped (graceful): 504 DEADLINE_EXCEEDED`
1회 발생. 코드가 이를 삼키고 분석을 완주시켰다(두 슬롯 모두 status=done) — 크래시나
분석 중단 없음. 로그의 print/logging 출력 순서가 버퍼링 때문에 어느 슬롯 호출에서
발생했는지 명확히 특정되지 않는다. climbfault 의 `deductionBreakdown` 키 자체가
doc.json 에 없는 것(climb 은 키는 있고 records=0)이 이 타임아웃과 관련 있을 가능성이
있으나 확증하지 못했다 — 추측을 사실처럼 적지 않는다.

## 영상 원본 S3 키 (버킷 sunity-motion-pilot-videos, ap-northeast-2)

`p35_extract_align.py` JOBS dict 원문 — motion → (user_key, ref_key):

| motion | user_key | ref_key |
|--------|----------|---------|
| elbow | fixtures/phase15/elbow-twist-sister/fault.mp4 | reference/ref-elbow-twist-sister.mp4 |
| powerspin | fixtures/phase15/power-spin/fault.mp4 | reference/ref-power-spin.mp4 |
| pdshape | fixtures/phase15/pdshape/correct.mp4 | reference/ref-pdshape.mp4 |
| kipup | fixtures/phase15/kip-up/fault.mp4 | reference/ref-kip-up.mp4 |
| realupload | uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/071df9f894d64d1696f106e613f51f5c.mp4 | reference/ref-power-spin.mp4 |
| pdshapefault | uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/pdshapefault1785373695.mp4 | reference/ref-pdshape.mp4 |
| peterpan | uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/peterpanfault1785373695.mp4 | reference/ref-peter-pan.mp4 |
| climb | fixtures/phase15/climb/correct.mp4 | reference/ref-climb.mp4 |
| climbfault | fixtures/phase15/climb/fault.mp4 | reference/ref-climb.mp4 |
| combo | fixtures/phase15/combo/correct.mp4 | reference/ref-combo.mp4 |

산출 mp4 키 (belle presigned 링크가 가리키는 같은 키):
`proto/phase35/{elbow,powerspin,pdshape,kipup,peterpan}_v3.mp4`
(pdshapefault 렌더가 `pdshape_v3` 키로 감 — 현행 매핑. realupload 는 렌더 슬롯 아님.)

코칭 음성 mp3 는 doc.json `result.coachAudio.items[].key`
(`results/{uid}/{analysisId}/coach_audio_{recordId}.mp3`, recordId 콜론 포함)에서 회수.

## align.json 스키마 (1줄 요약)

15fps RTMW 재추출 산출 — `fps`, `userSize/refSize`(px), `userFrames/refFrames`,
`curveRefSec`(user 프레임 인덱스 → ref 초, DTW 정렬곡선), `pairs`({rid}: atVideoSec /
refVideoSec / poseDist / joint / marker), `userKp/refKp`(정규화 x,y flat),
`userScore/refScore`(신뢰도), `joints17`(COCO-17 키). 구버전 포맷은 refKp/refScore 없음.

## 렌더 커맨드 템플릿

```
SP=<scratchpad: user.mp4/ref.mp4/audio/render 프레임 캐시 위치>
DATA=.planning/phases/35-server-rendered-comparison-video/data
PY=backend/.venv/bin/python

cd backend && $PY scripts/render_compare_prototype.py \
  --doc-json $DATA/{m}/doc.json --align-json $DATA/{m}/align.json \
  --user-video $SP/p35/{m}/user.mp4 --ref-video $SP/p35/{m}/ref.mp4 \
  --audio-dir $SP/p35/{m}/audio --workdir $SP/p35/{m}/render \
  --out $SP/p35/{m}/out_{tag}.mp4 > $SP/p35/{m}/report_{tag}.json
```

- kipup 만 `--moments-json $DATA/kipup/moments.json` 추가.
- 리포트는 stdout — 리다이렉트 필수.
- 기계 판정: `$PY scripts/verify_render_prototype.py --mp4 <out> --report <report>`
  exit 0 = ALL PASS 이어야만 S3 업로드.
