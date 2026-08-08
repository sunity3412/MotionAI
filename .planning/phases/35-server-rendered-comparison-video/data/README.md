# Phase 35 렌더 입력 데이터 (Pod 볼륨 회수 영구본)

**이후 렌더는 이 디렉터리를 입력으로 사용한다 (임시폴더 아님).** 재부팅/Pod 소실이
재발해도 이 데이터 + S3 영상 원본만으로 합성 비교 영상 5편을 재현할 수 있다.

## 출처

- RunPod `pqe6uaw7mf8bh9` 볼륨 `/workspace/p35`, 회수일 2026-08-08 (`p35_volume.tgz`).
- 생성 스크립트: `backend/scripts/p35_extract_align.py` (rtmlib RTMW GPU 15fps 재추출
  + 자세거리 DTW 정렬 + 짝 재선정 + 마커 좌표).

## 파일 구성 (7동작 16파일)

| 동작 | 파일 | 비고 |
|------|------|------|
| elbow | align.json, doc.json | 활성 렌더 슬롯 |
| powerspin | align.json, doc.json | 활성 렌더 슬롯 |
| kipup | align.json, doc.json, moments.json | 활성 렌더 슬롯 (r00 순간은 align pairs 주입) |
| pdshapefault | align.json, doc.json | 활성 렌더 슬롯 (S3 키는 pdshape_v3 — 현행 매핑) |
| peterpan | align.json, doc.json | 활성 렌더 슬롯 |
| pdshape | align.json, doc.json | 벤치 슬롯 (correct 영상) |
| realupload | align.json, doc.json, moments.json | 벤치 슬롯 |

## 검증 결과 (2026-08-08)

- 활성 5슬롯(elbow, powerspin, kipup, pdshapefault, peterpan) 기계검증 PASS —
  baseline 렌더 5편 리그(verify_render_prototype.py) ALL PASS + v6 길이 근사 재현.
- pdshape(correct)·realupload 2건은 구버전 포맷(refKp 없음) — 벤치 슬롯이라 무해,
  렌더러(render_compare_prototype.py)도 refKp 를 선택 필드로 다룬다.
- verify/ 스틸 87장(62MB)은 미커밋 — 재생성은 Pod 에서 한 줄:
  `RTMW_DEVICE=cuda python3 scripts/p35_extract_align.py --workdir /workspace/p35`

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
