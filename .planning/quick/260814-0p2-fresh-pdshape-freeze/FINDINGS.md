# FINDINGS — 발굴 채택 순간의 영상 반영 실증 (quick-260814-0p2)

**한 줄**: belle 채택 순간 cand13b(u12.8667/r12.40, 왼무릎)를 fresh pdshape
비교 영상(doc p34fresh1786628533)의 정지 목록에 추가·재렌더했고, 무릎 카드가
그 freeze 를 상속해 방출됐다 — 기존 정지 5건 무변경 기계 증명 + 리그 성립.
S3 업로드·doc 갱신은 하지 않았다 (belle 실물 확인 대기).

## 1. 리그 판정 요약

| 렌더 | 판정기 | 결과 |
|------|--------|------|
| 베이스라인(주입 off) | compare_verify.verify **무수정** | **ALL PASS** — freeze 5건 outSec 이 운영 doc renderedCompare 와 전건 일치(0.01s 단위) |
| 주입(정지 6건) | compare_verify.verify **무수정** | FAIL = `H2 순간 r04 (src=discover)` **정확 1건 국한** — 기존 freeze 전건은 무수정 기준 PASS (T-0p2-01). H2 가 외부 삽입을 설계대로 검출한 것 |
| 주입(정지 6건) | + `_H2_UT_DISPLACING_SRC` **사본 delta 1값** (`"discover"`) | **ALL PASS** (A/A2/B/C/D/E/F/G/H1~H4 전 항목) |

면제는 plan 명기 방식만 — align-peak/align-pole **사칭 없음**, 신설 라벨
`discover` 로만 주입했고 무수정 판정기의 정직한 FAIL 을 먼저 박제했다.

## 2. 기계 증명 3종

- **결정론**: 베이스라인·주입 각 2회 렌더 mp4 md5 동일 + compose 프레임 md5
  사슬 동일 + report 동일. 카드 2회 md5 동일.
- **diff 국한** (3층):
  - report: 기존 정지 5건의 (rid/joint/userSec/refSec/pairSrc/text/freezeS/
    마크·viz 요약) 전건 동일 + 신규 정지 정확 1건 (r04, u12.8667, r12.40,
    pairSrc=discover).
  - compose 소스(정본 층): 삽입 블록 293프레임(= freeze 9.78s x 30) + 복귀
    크로스페이드 5프레임 외 **전 프레임 JPEG md5 bit-동일** (prefix 1262프레임
    + suffix 전건). 삽입점 이후 출력 초가 신규 정지 길이만큼 이동하는 것은
    의도 변경 — 내용 동일성으로 증명 (무변경 주장 아님).
  - mp4: 프레임 인덱스 정확 추출(select=eq) — 삽입 전 프레임은 cross md5
    동일, 삽입 후는 H.264 재인코드 노이즈뿐(crossMax 3~69, mean 0.0001~0.6,
    양쪽 프레임이 같은 bit-동일 소스 JPEG 에 코덱 노이즈 수준으로 앵커 —
    전이 증명. hlv "디코드 노이즈 Δ/255 구조 차 0" 선례).
- **카드 상속**: `card_gates verdict` survivors =
  `['r00:inherit@u5.302/r5.13', 'r04:inherit@u12.867/r12.40',
  'r03:inherit@u16.667/r15.20']` — 기존 생존 2건 무회귀(u8i Pod 실증과 동일)
  + 신규 freeze 상속 방출. dropped = r01/r04(구 10.5s)/r02 (Pod 기준과 동일
  사유 — 구 r04 freeze 는 hold=moving 침묵 유지). 카드 초 라벨 =
  **12.9s** (doc 12.904301433811272 — 실효 fps 환산, wif 정본과 15자리 일치,
  9.0/18.0 분모 사용 0). **상속 카드 = wif belle 채택 카드와 md5 byte-동일**
  (e891e7ae…).

## 3. 제약 준수 증빙

- **backend/ diff 0**: 전 Task `git status --porcelain backend/` 빈 출력 +
  `git diff --stat backend/` 0줄. 운영 코드 무수정 — 확장은 전부 하네스 사본
  (inject_freeze.py 의 monkeypatch — build_timeline 래퍼 + verify 면제 튜플).
- **S3 쓰기 0**: fetch = GET 만 (mp3 5건 + Pod eye ledger + 영상 캐시 재사용).
  카드 스테이지 put_object 는 로컬 스텁 캡처 (키 7건 — 카드 3 + 눈 원장 4,
  실제 업로드 0).
- **Firestore 쓰기 0**: doc/refmotion 은 wif 캐시 재사용 (이번 사이클 Firestore
  호출 자체가 0). `update_analysis_fault_zoom` 은 스텁 캡처.
- **Gemini 실호출 0**: 기계 눈 = replay 스텁 (Pod eye ledger 2건 + wif 원장
  1건, 좌표 키 매칭 — wif 로그 실측 xy=333,437 재현). 6히트/미스 0/실호출 0.
  스텁에 네트워크 경로 자체가 없고 env 키도 가짜값 — 이중 보증.
- **Pod 무접촉** · **채점 무접촉** (deductionBreakdown 읽기만).

## 4. LLM 학습 영향

이번 사이클 LLM 호출 0 (기계 눈 전부 replay — 신규 추론·학습 전송 0).
눈 원장 신규 적재 없음 — 기존 원장(Pod S3 + wif evidence) 재사용만.

## 5. 보존 / 휘발 구분

- **보존 (리포 커밋)**: inject_freeze.py, evidence/ 전건 (SUPPORT-SURFACE,
  baseline/inject verdict, frames_md5 2본, cards 3장, stills 11장,
  VISUAL-REVIEW, 이 문서).
- **휘발 가능**: 재렌더 mp4 실물은 세션 scratchpad(`0p2_out/`)와
  `/Users/Shared/sunity-freeze-inject-260814/` **사본**에만 있다 — 이들은
  보존본이 아니다. **보존은 belle 확인 후 반영 단계의 S3 업로드가 담당**한다
  (scratchpad/Users/Shared 를 "보존"으로 주장하지 않는다). 재현은
  inject_freeze.py 가 결정론으로 보장 (md5 박제).

## 6. belle 확인 재료 (파일 절대경로 — 이미지 전달 정본은 보드 embed)

- /Users/Shared/sunity-freeze-inject-260814/재렌더영상_신규정지포함.mp4
- /Users/Shared/sunity-freeze-inject-260814/신규정지_왼무릎_12.9s_스틸.png
- /Users/Shared/sunity-freeze-inject-260814/상속카드_왼무릎_12.9s.png
- /Users/Shared/sunity-freeze-inject-260814/기존카드_왼팔꿈치_5.3s_무회귀.png
- /Users/Shared/sunity-freeze-inject-260814/기존카드_왼골반_16.7s_무회귀.png
- /Users/Shared/sunity-freeze-inject-260814/기존정지_{왼팔꿈치,왼무릎10.5s,오른어깨,왼골반}_{기존영상,재렌더}.png (8장)
- /Users/Shared/sunity-freeze-inject-260814/안내.md

## 7. S3 업로드 보류 명기 + 다음 1단계

**이번 사이클은 로컬 재렌더 실물까지다. S3 업로드 0 · doc 갱신 0.**

다음 1단계 = belle 실물 확인 → 반영 (별도 사이클):

1. 재렌더 mp4 S3 업로드 + doc renderedCompare 갱신 (freeze 6건).
2. **backend 필요 변경** (SUPPORT-SURFACE §5 — 재조사 불요):
   - `compare_render.build_timeline` 주입 레이어 (발굴 순간 정지 추가의 공식
     경로 — 이번 사본 래퍼가 스펙 실증: mp3/text/dur/viz 전부 기존 record
     규칙 재사용, pairSrc 라벨만 신설).
   - `compare_verify._H2_UT_DISPLACING_SRC` 에 `"discover"` 라벨 추가
     (ut 이동 승인 문법 면제 축 — 판정 로직 무변경).
   - 발굴 순간(12.8667/12.40)의 doc 영속화 규약 (어디 저장하고 파이프라인
     어느 단계가 읽는가 — belle 반영 결정과 함께).
