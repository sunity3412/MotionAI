---
title: 인수인계서 — 동작비교(합성 영상) 경로 마감
date: 2026-09-09
next_section: belle 실기기 캡처 판정 수령
status: 구현·배포·실물검증 완료, belle 판정 대기
---

# 인수인계서 — 동작비교 합성 영상 경로

**다음 섹션이 할 일: belle 이 실기기에서 찍은 캡처를 받아 판정을 처리한다.**
판단·진단은 최소로 하고 **관측과 좌표**를 적는다.

---

## 0. 30초 요약

- 동작비교 탭의 **합성 영상 경로**(RenderedComparePlayer)를 시안 2 로 맞추고
  belle 이 요구한 기능 4개를 넣었다: 감점 행 탭 이동 · 관절선 온오프 ·
  0.5배속 · 음성 · 전체화면.
- **관절선 끄기**는 서버가 표시 없는 mp4 를 한 벌 더 굽는 방식이다. 앱은 소스만
  갈아끼운다 (재생 위치·재생 상태 유지).
- OTA `bc942c78-50c5-4fde-82f0-9b4b3ed1d0b3` (preview / 런타임 1.2.4) 발행됨.
- 시뮬레이터에서 **전 항목 실물 확인**했다 (아래 §4).
- 검증본을 **belle 계정으로 옮겨 뒀다** — 앱 껐다 켜면 기록 탭 맨 위.
- **belle 판정 대기 = 4가지** (§5).

---

## 1. 지금 상태 (실측)

```
브랜치   main            HEAD 7e4e8ce3
OTA      bc942c78-50c5-4fde-82f0-9b4b3ed1d0b3  preview / 런타임 1.2.4
Pod      없음 (3ahwfagt36pvxy TERMINATED)      SSM pod-expected=down
Lambda   playback-url    2026-09-09 14:09 갱신 · 레이어 sunity-motion-pilot-shared:20
게이트   pytest 4731/0 · tsc 0 · node --test 226/0
```

**belle 계정 = `csKWYvI3WCPYPysNQ9KkWecaUvq1`** (belle 확인 2026-09-09:
기록 탭이 "pdshape 60점만 반복"). 전 계정이 익명 로그인이라 데이터만으로는
특정 불가 — 다음에도 belle 에게 기록 탭을 물어서 맞출 것.

**belle 이 봐야 할 doc**
```
users/csKWYvI3WCPYPysNQ9KkWecaUvq1/analyses/c64afae69fd24366b4b5f375aa0a91fb
  createdAt 2026-09-09 14:48 · done · 60점 · ref-pdshape
  renderedCompare.key      results/csKWYvI3…/c64afae6…/compare_v1.mp4
  renderedCompare.keyPlain results/csKWYvI3…/c64afae6…/compare_v1__plain.mp4
  freezes 6  [{r02,3.53,11.97} {r04,17.7,9.78} {r05,27.67,9.95}
              {r00,39.83,9.71} {r01,49.57,9.71} {r03,67.8,11.46}]
```
`POST /playback-url` 실측 200, 응답에 `playbackUrl` + `playbackUrlPlain`,
두 URL 다 HTTP 206 (객체 실존). 2026-09-09 15:4x 확인.

---

## 2. 이번 라운드에 바뀐 것

| 커밋 | 내용 |
|---|---|
| `d4b8aaed` | 감점 행 탭 = 그 지점 이동 + 컨트롤 4개 한 줄 |
| `d0717130` | 합성 가지도 시안 2 로 (카드·역할 알약·컨트롤) |
| `093a8393` | 관절선 끄기 영상판 (서버 `__plain` mp4 + 앱 토글) |
| `67c7ea15` | 관절선 끈 판에 **자막 유지** + contract §12.9 3-way lockstep |
| `be108c62` | 행 시간=재생기 시계+정렬 · 자막 안전영역 · 라이브텍스트 off |
| `c4465a18` | 두 경로 컨트롤 치수를 `theme/compareControls.ts` 한 곳으로 |

### 손댄 파일

```
app/src/components/RenderedComparePlayer.tsx   합성 경로 본체
app/src/components/VideoCompare.tsx            듀얼(폴백) 경로
app/src/components/result/ResultMomentList.tsx secText 오버라이드
app/src/app/analysis/result.tsx                행 시간·정렬 배선
app/src/theme/compareControls.ts               신설 (두 경로 공유 치수)
app/src/lib/api.ts                             fetchVisualAssetUrls
backend/shared/…/analysis/compare_render.py    _draw_caption / _caption_bottom
backend/shared/…/s3keys.py                     build_rendered_compare_key(plain=)
backend/shared/…/models.py, firestore_admin.py keyPlain · freezeS
backend/functions/pipeline/app.py              plain mp4 렌더·업로드
backend/functions/playback-url/app.py          playbackUrlPlain
docs/contract.md §12.9 + playback-url 절
```

---

## 3. 구조 — 손대기 전 알아야 할 것

### 3-1. 동작비교 탭에는 **경로가 둘**이다

```
result.tsx:1637
  renderedCompareReady && !renderedUnavailable
    ├ true  → RenderedComparePlayer   서버가 합성한 단일 mp4 1개
    └ false → VideoCompare            영상 2개를 앱이 라이브 동기
```

`renderedCompareReady = result.renderedCompare?.status === 'done' && key 있음`.
`renderedUnavailable` = `POST /playback-url` 이 실패하면 **그 세션만** true.

**★ 화면만 보면 두 경로를 구분할 수 없다.** 구분법:

| | 합성 | 듀얼 |
|---|---|---|
| 접근성 트리 `Video` 요소 | 1개 | **2개** |
| '관절선 표시' | `AXSwitch` (checked) | `Button` (selected) |
| 음성 기본값 | ON | OFF |

`mcp__ios-simulator__ui_describe_all` 로 본다.

### 3-2. Mode3 는 합성 경로가 없다

`pipeline/app.py:4669` — `mode != mode1` 이면 스킵. Mode3 는 항상 듀얼이다.
그래서 듀얼 경로를 지울 수 없다.

### 3-3. 관절선 끄기 = 영상 두 벌

정지 프레임에서 표시(관절 원·각도선·호·수치)를 그리기 **전** 캔버스를 한 장 떠서
두 번째 mp4 를 굽는다 (`compare_render.render(out_plain=…)`).
**자막은 두 판 모두에 굽는다** — 토글 이름이 '관절선' 이므로 그것만 끈다.
재생 구간 프레임은 두 판이 같아서 **하드링크**로 재사용한다 (디스크·시간 0).

### 3-4. 자막은 화면 밖으로 나가면 안 된다

앱이 이 mp4 를 시안 블록 비율(`276.04 : 177.9`)에 **폭을 맞춰** 넣고 위아래를
자른다. 1224×1080 기준 **보이는 세로 = 146 ~ 934** (가운데 73%).
`_caption_bottom(W)` 가 자막 밴드 밑선을 934 에 붙인다.
**블록 비율을 바꾸면 `APP_BLOCK_ASPECT` 도 같이 바꿔야 한다** (테스트 3건이 잡는다).

---

## 4. 실물로 확인한 것 (2026-09-09, 시뮬레이터 iPhone 16 Pro)

- 합성 플레이어 진입 — 29°/28° 마커, 관절선·음성 칩 ON
- 감점 행 탭 → 그 지점 이동 (유튜브 스크립트) ✓
- 재생이 그 정지에 닿으면 그 행이 켜짐 ✓
- **관절선 OFF → 0:43.5 위치 그대로, 표시만 사라짐** ✓
- 관절선 ON → 같은 0:43.5 에서 마커 복귀 ✓
- **관절선 OFF 에서도 자막 유지** ✓
- 행 시간·순서가 재생기 시계와 일치 ✓ (0:03.5 → 1:07.8)
- 일시정지 프레임에 iOS 스캔 단추 없음 ✓

**mp4 실측**: 표시 판 ↔ 관절선 끈 판 픽셀 차이 **0.76%** (t=5.5s).
자막을 두 판에 굽기 전에는 12.91% 였다 — 그 차이가 자막이었다.

---

## 5. belle 판정 대기 (다음 섹션의 입력)

belle 폰에서 앱 껐다 켜고 → 기록 탭 **맨 위**(오늘 14:48) → 동작비교.

1. 감점 행 시간이 재생기 시간과 같은 시계로 읽히는지
2. 행을 누르면 그 지점으로 이동하는지
3. 관절선 칩 — 표시만 사라지고 위치·자막은 그대로인지
4. 일시정지 때 우하단에 iOS 스캔 단추가 안 뜨는지

---

## 6. 이월 (이번 라운드에서 손대지 않음)

- **브랜드색 대비 미달 2건** — belle 판정 필요. `#FF4B33` 변경 금지 규칙과 충돌.
  · 감점 칩 글자 `#FF4B33` on `#FCEFED` = 2.97:1 (필요 4.5:1)
  · 흰 글자 on 브랜드 빨강, 일반 크기 = 3.33:1 (필요 4.5:1)
- **더 잴 것 5건** — `260909-ji1-SUMMARY.md` §남은 것. 데이터 조건이나 피그마
  속성 직접 읽기가 필요해 이번 범위 밖이었다.
- **영상 위아래 잘림** — 합성본은 27% 가 아니라 **13.5%씩** 잘린다(§3-4).
  belle 이 "잘려 보인다" 하면 `APP_BLOCK_ASPECT` 와 앱 `frame` 을 같이 본다.

---

## 7. ★ 함정 (밟으면 시간을 태운다)

### 7-1. 복사한 doc 은 합성 경로를 못 탄다

`renderedCompare.key` 가 원본 uid 를 가리키면 `playback-url` 이 canonical key 와
**exact 비교**에서 떨어져 **404** → 앱이 **조용히 듀얼로 강등**된다. 에러 표시가
없어서 "왜 시안대로 안 나오지"로 보인다. 2026-09-09 에 한 시간 태웠다.

옮길 때: 문자열 안 `/{srcUid}/` 전부 재작성 + **`results/` 객체만** 복사.

### 7-2. `uploads/` 는 같이 옮기면 안 된다

`uploads/` 에 객체가 생기면 **S3 이벤트 → SQS → 파이프라인**이 다시 돈다.
Pod 이 내려가 있으면 delegate 404 로 실패해 **방금 옮긴 doc 이 `failed` 로
덮어써진다** (2026-09-09 실제로 당함 · 객체 삭제 + doc 재기록으로 복구).
합성 가지 재생에 `uploads/` 는 필요 없다.

### 7-3. `/upload-url` 은 Firestore doc 을 만들지 않는다

doc 은 앱이 만든다 (`analysis/loading.tsx:160`). 스크립트로 E2E 를 돌리면서
doc 을 안 만들면 `mode` 가 없어
`compare_render 스킵 (mode1+기준 영상 경로 아님) mode=None` 이 된다.

### 7-4. 시뮬 사진첩 영상 2개는 pdshape 가 아니다

둘 다 `not_pole_motion` (angle=0). 승인 픽스처는
`uploads/csKWYvI3…/cbf59609…mp4` (`fileName: belle_pdshape.mp4`, 93.8MB).

### 7-5. Pod 에서 `pkill -f "uvicorn.*server:app"` 은 자기 자신을 죽인다

ssh 원격 명령 문자열이 그 패턴을 포함해서 자기를 매칭한다 (exit 255).
PID 로 죽이거나 `uvi[c]orn` 처럼 쪼갤 것.
서버 기동은 `source /workspace/aws_env.sh && bash /workspace/start_server.sh`
— **aws_env.sh 를 먼저 source 하지 않으면 `NoCredentialsError`** 로 죽는다.

### 7-6. `sam deploy` 없이 Lambda 갱신

배포본(`get-function` / `get-layer-version` 의 Code.Location)을 내려받아
**바뀐 파일만** zip 에 덮어쓰고 publish → `update-function-code` →
`update-function-configuration --layers`. 레이어는 repo 보다 한 달 낡을 수 있어
통째로 갈아엎으면 위험하다. 프로파일은 `AWS_PROFILE=sunity-motion`
(기본 프로파일은 SSM 권한 없음).

---

## 8. Pod 이 필요해지면

새 분석은 Pod 없이 **실패한다** (폴백 없음). 기동 절차:

1. RunPod Pod 생성 (RTX PRO 4500 Blackwell, EU-RO-1, 네트워크 볼륨 `a5z753defc`)
2. 리포 bundle 반입 → `git checkout` → `source aws_env.sh && bash start_server.sh`
3. `/health` 로 `commitSha` + `pipeline_loaded: true` 확인
4. Lambda `RUNPOD_ANALYZE_URL` 을 새 proxy URL 로, SSM `pod-expected=up`
5. **끝나면 즉시 Terminate + `pod-expected=down`**

상세는 메모리 [[demo-only-pod-bring-up-procedure]].
