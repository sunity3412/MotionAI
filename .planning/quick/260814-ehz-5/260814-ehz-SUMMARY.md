---
phase: quick-260814-ehz
plan: 01
subsystem: analysis
tags: [discovery, card-gates, machine-eye, gemini, sweep, silence-proof]

requires:
  - phase: quick-260813-wif
    provides: 왼무릎 발굴 하네스(discover_knee.py) + 사전 박제 장부 + belle 채택 실적 1/1
  - phase: quick-260811-ufb
    provides: SWEEP_JOBS 5동작 S3 키/motion_id 정본 + 동작별 마운트 패턴
  - phase: quick-260811-ii0
    provides: card_gates 확정 임계 + poles.json + probes.log 승인 freeze 정본
provides:
  - 발굴 하네스 일반화 (discover_sweep.py — 동작/record 파라미터화 + 양방향 claim 유도 + 소스 게이트)
  - 승인 5동작 13 record 전수 발굴/침묵 시트 (DISCOVERY-SHEET.md)
  - 동작별 사전 박제 추천 5행 (wif DISCOVERY-LEDGER append, belle 판정 전 커밋)
  - 눈 PASS 5후보 카드 + 전신 짝 + 눈 원장 58건
affects: [발굴 자동화, split 축 발굴, freeze 타임베이스 의제, Phase 22 플라이휠]

tech-stack:
  added: []
  patterns:
    - "양방향 claim 유도 — user 트랙 claim 의 반대 claim ref 한정 짝 탐색 (관절 하드코딩 제거)"
    - "소스 게이트 선행 — record 스캔 전에 동작별 로컬 replay 가능성 판정, 실패 시 정직 박제 후 스캔 생략"
    - "침묵 증명 — 발굴 0 동작을 실행 수치 + 탈락 사유 분포로 입증"
    - "record 키 눈 호출 계수기 — (motion, rid) 키로 상한 16회 코드 강제"

key-files:
  created:
    - .planning/quick/260814-ehz-5/discover_sweep.py
    - .planning/quick/260814-ehz-5/DISCOVERY-SHEET.md
    - .planning/quick/260814-ehz-5/evidence/ (5동작 candidates/stills/eye_ledger/cards/render_verdict + VISUAL-REVIEW)
  modified:
    - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md (append only)

key-decisions:
  - "claim 유도를 관절별 하드코딩(need_ext)에서 트랙 대조 방향 유도로 일반화 — user claim 의 반대 claim ref 만 짝 후보"
  - "split 3 record 는 단일 마크 좌표 부재로 눈 유도 불가 → 정직 탈락, 운영 helper 의 peak pass-through 와 층이 다름을 명기"
  - "재발견-only 후보(cand13B)는 검증 행으로 두고 신규 추천에서 제외 — 중복 발명 금지"
  - "'발굴 0 = 추천 없음'도 하나의 추천으로 장부에 세어 판정과 대조 — 침묵이 무판정으로 빠져나가지 않게"
  - "육안 탈락은 명백 파손(판독 불가/국면 상이/경계/트랙-육안 모순)에만 적용, 애매는 기계 눈에 위임"

patterns-established:
  - "무축소 짝 시트 — 후보별 (학생|기준) 원본 해상도 가로 결합을 육안 검수 단위로"
  - "승인 freeze 대조 행 — record 마다 ii0 probes.log 정지를 재계산해 재발견/신규 판별"

requirements-completed: [QUICK-260814-EHZ]

duration: 50min
completed: 2026-08-14
---

# quick-260814-ehz: 발굴 일반화 스윕 Summary

**승인 5동작 13 record 전수에 발굴을 돌려 2개 동작에서 눈 PASS 5건을 얻고 3개 동작의 침묵을 실행 수치로 증명했다 — 그리고 일반화된 코드가 belle 채택 카드를 byte-동일하게 재생산했다.**

## Performance

- **Duration:** 약 50분
- **Started:** 2026-08-14T01:58Z (10:58 KST)
- **Completed:** 2026-08-14T02:48Z (11:48 KST)
- **Tasks:** 3/3
- **Files modified:** 하네스 1 + 시트 1 + 장부 1(append) + evidence 다수 (backend/ 0)

## 기계 판정 한 줄

소스 게이트 **5/5 PASS**(전 동작 로컬 replay, Pod 불요) → **13/13 record 스캔** →
claim 대조 성립 88버킷 → 압축 37 → 육안 통과 29(탈락 8) → 기계 눈 실호출 **58회**
(record 당 최대 9 ≤ 상한 16) → **눈 PASS 5 / 기각 24** → 카드 5장(2회 재렌더
md5 5/5 동일).

| 동작 | 눈 PASS | 사전 추천 |
|---|---|---|
| elbow | 0 | 발굴 0 — 추천 없음 |
| kipup | 0 | 발굴 0 — 추천 없음 (split) |
| pdshapefault | 4 | **cand17B 왼팔꿈치 (16.47s / 15.13s)** |
| peterpan | 0 | 발굴 0 — 추천 없음 |
| powerspin | 1 | **cand01E 왼어깨 (0.47s / 0.73s)** |

★ **일반화 무결성 증명**: pdshapefault r03 `cand13B`(12.87/12.40)가 산출한 카드
md5 `e891e7ae1fd13b0be1a7ec0470095edb` = wif 에서 belle 이 채택한 카드와
**byte-동일**. 좌표 무입력 + 다른 doc 마운트(P35 align.json 직접) + 일반화된
양방향 claim 유도에서 같은 순간·같은 산출물에 도달했다. 게이트 수치도 15자리
일치(poleDiff 만 폴 출처 차이로 0.235106 → 0.237352).

## 소스 게이트 결과 (record 스캔 전 판정)

5동작 전건 PASS — P35 doc/align 실물 + align 스키마 + S3 read-only 영상 +
fps 교차검증(프레임수/길이 14.94~15.03 vs align 라벨 15.0, 허용 0.5).
**"로컬 불가 — Pod 필요" 로 떨어진 동작 0건.** 실효 fps(9.92~10.00)도 박제.

## 침묵의 내용 (조작 0)

- **elbow (0/12)** — 홀드 111~218/268프레임 통과, claim 대조 34버킷 성립, 육안
  12건 통과 후 **기계 눈이 12건 전부 기각**. 그중 5건은 트랙이 5.0/6.0/6.8도
  극단 굽힘을 주장한 순간인데 눈이 "펴져 있다"로 봤다 — 트랙 환각을 눈이 잡은
  실물이다. 3건은 limb 상충(팔 마크가 다리/off_body).
- **peterpan (0/1)** — 홀드 90/91프레임 통과했으나 짝은 7버킷 중 1건만 성립,
  그 1건도 눈이 기준 측 기각(트랙 17.0도 bent vs 눈 extended).
- **split 3 record (kipup r00 · powerspin r00/r01)** — 벌림각은 표시할 단일
  관절 좌표가 없어 눈 유도가 원리적 불가. 시도조차 하지 않고 사유 박제.
  운영 helper 는 같은 축을 `align-peak` pass-through 로 **면제**하는데 발굴은
  **침묵**한다 — 층이 다르다는 대조를 시트 §7 에 명기.

## Deviations from Plan

### Rule 3 - 실행 편의 (하네스 스테이지 1개 추가)

**1. [Rule 3] `--pairsheet` 스테이지 신설**
- **Found during:** Task 1 육안 단계
- **Issue:** 압축 후보 37건 × 2측 = 74장을 개별로 열면 "두 패널이 같은 국면인가"
  판정이 분리돼 오히려 부정확해진다.
- **Fix:** 후보별 (학생|기준) 스틸을 **무축소 가로 결합**한 짝 시트를 산출하는
  스테이지를 하네스에 추가. 개별 스틸도 그대로 남긴다(삭제 0). 각 패널은 추출
  원본 해상도(608x1080) 그대로 — 몽타주 축소본 검수 금지 규율 준수.
- **Files modified:** discover_sweep.py
- **Commit:** 983d9f72

**2. [Rule 3] `evidence/visual_verdicts.json` 신설 + eye 스테이지 연동**
- **Found during:** Task 1 → Task 2 이행
- **Issue:** 육안 탈락 판정을 코드에 하드코딩하면 근거가 안 보이고, CLI 인자로만
  주면 재현이 안 된다.
- **Fix:** 육안 탈락 8건을 사유 문자열과 함께 JSON 데이터로 커밋하고 eye 스테이지가
  읽어 건너뛴다(로그에 사유 출력). VISUAL-REVIEW.md 가 서술 근거.
- **Commit:** 983d9f72

계획 대비 그 외 이탈 없음 — 임계 재튜닝 0, 동작명 분기 0(마운트 좌표 제외),
승인 freeze 순간 배제 0, backend/ 수정 0.

## Known Limitations (정직 박제)

1. **운영 방출 아님.** 반영은 belle 판정 후 di7 일반 경로로 별건. S3 업로드 0 /
   Firestore 쓰기 0 / Pod 무접촉 / 채점 무접촉.
2. **pdshapefault 는 wif 와 같은 원본 영상이다** (wif fresh doc 의 replay 트랙이
   곧 P35 pdshapefault align). 3-2 는 "독립 표본 재발견"이 아니라 **같은 영상·
   다른 경로 재생산**이다 — 과장하지 않는다.
3. **압축 상한 4/record.** 성립한 claim 대조 88버킷 중 37건만 눈까지 갔다 —
   상한 밖에 더 나은 후보가 있을 가능성을 배제 못 한다.
4. **split 축 발굴 미해결** — 눈에게 물을 새 질문 형식(벌림 정도)이 필요하고
   이번에 발명하지 않았다.
5. **peterpan freeze 타임베이스** — 승인 freeze 6.444s 가 align 클립 6.067s
   밖이라 대조 행이 클램프됐다. u8i 가 박제한 상류 의제 재확인.
6. **하네스 부작용 1건** — 렌더 중 `card_gates eye ledger 적재 실패 (비차단)`
   경고가 카드마다 1회. 드라이버가 눈 판정 메모를 재사용하며 크롭을 안 넘겨서다.
   **운영 코드 결함 아님**(운영 `_eye_cache` 는 튜플이라 이 경로가 없다).
   크롭 원장은 `eye_ledger/` 에 전건 보존.
7. **눈 기각 24건은 되돌리지 않았다** — 재시도·크롭 재조정·임계 완화 0.

## LLM 학습 영향

- **호출**: `card_gates.machine_eye` (gemini-3.5-flash, temperature 0, JSON
  schema 강제) **실호출 58회**. record 별 = elbow r00 6 / r01 4 / r02 5 / r03 5,
  pdshapefault r00 9 / r01 7 / r02 7 / r03 8, peterpan r00 2, powerspin r02 5.
  **전건 record 당 상한 16 이하** — `(motion, rid)` 키 계수기로 코드 강제,
  CAP 발동 0, 캐시 히트 10회(실호출 계수 불변).
- **비용**: kpo 관측치(40~46회 ≈ $0.01) 기준 **약 $0.013 추산**. 그 외 LLM 호출 0
  (Cerebras 0, Polly 0).
- **학습 전송 0**: 추론 호출만이다. Gemini 로 나간 것은 관절 중심 정사각 크롭
  이미지 + 좌우 이름 없는 상태/사지 질문뿐이고, 학습 재료로의 사용은 별도
  사이클의 belle 결정 사항이다 (T-kpo-01 / T-ehz-04 무접촉).
- **원장 보존 위치 = 리포 `evidence/{motion}/eye_ledger/` 뿐** (마킹 크롭 PNG +
  판정 JSON). **S3 쓰기 0** — 운영 헬퍼의 S3 원장 업로드 경로는 로컬 스텁으로
  라우팅했다. scratchpad 캐시(영상/프레임)는 휘발이라 보존으로 치지 않는다.
- **Phase 22 씨앗 후보**: 이번 원장 58건은 "홀드 자세 시각 검증" 학습 후보다.
  특히 **기각 24건**이 값지다 — 트랙이 극단 굽힘(5~7도)을 주장한 순간을 눈이
  "펴짐"으로 뒤집은 5건은 keypoint 환각 라벨의 직접 재료다.

## 보드 재료 (belle 확인용 — 이미지 전달 정본 = 보드 embed)

`/Users/Shared/sunity-discovery-sweep-260814/`

- `/Users/Shared/sunity-discovery-sweep-260814/안내.md`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_추천_왼팔꿈치_카드_16.5초.png`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_추천_왼팔꿈치_전신짝_학생16.5초_기준15.1초.jpg`
- `/Users/Shared/sunity-discovery-sweep-260814/파워스핀_추천_왼어깨_카드_0.5초.png`
- `/Users/Shared/sunity-discovery-sweep-260814/파워스핀_추천_왼어깨_전신짝_학생0.5초_기준0.7초.jpg`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_동반_왼무릎_카드_13.6초.png`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_동반_왼무릎_전신짝_학생13.6초_기준12.9초.jpg`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_동반_왼어깨_카드_1.1초.png`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_동반_왼어깨_전신짝_학생1.1초_기준2.2초.jpg`
- `/Users/Shared/sunity-discovery-sweep-260814/피디쉐입_검증_왼무릎_카드_12.9초_기채택본과동일.png`

## 다음

**belle 판정 대기** — 시트 §9 의 5개 항목. 판정은 wif
`DISCOVERY-LEDGER.md` 의 "belle 판정 기입란"과 승격 실적 집계 행 2~6 에 기입한다
(선기입 금지 — 사전 박제는 커밋 `b2a2f019` 이후 docs 커밋으로 판정 전에 박혔다).

## Self-Check: PASSED

- 산출물 실물 확인 14/14 — 하네스 · 시트 · 장부 · VISUAL-REVIEW · visual_verdicts
  · 5동작 candidates.json · 추천 카드 2장 · /Users/Shared 안내.md.
- 커밋 존재 확인 2/2 — `983d9f72`(Task 1), `b2a2f019`(Task 2).
- 게이트 재실행: `discover_sweep.py --check` PASS (5동작, record 13/13,
  stills+VISUAL-REVIEW 전건) · 눈/렌더 게이트 PASS (record 당 ≤16, 결정론 기록
  전건) · Task 3 검증식 PASS.
- 제약 확인: `git diff --stat backend/` **0줄**, `git status --porcelain backend/`
  **빈 출력**, wif 원본 파일 무변경(LEDGER 는 append 만).
