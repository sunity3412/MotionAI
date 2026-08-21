---
phase: quick-260821-pnp
plan: 01
subsystem: analysis
tags: [discovery, sweep, climbfault, vision-veto, harness-env-trap]

requires:
  - phase: quick-260821-ls0
    provides: climbfault 침묵 판정(doc 층) + 하네스 8동작 등재 + Firestore 원본 대조 규율
  - phase: quick-260814-ehz
    provides: 발굴 일반화 하네스 discover_sweep.py + 침묵 증명 규율
provides:
  - climbfault P35 doc = veto-ON 재분석본 (p35newclimbfault1787297579, overall 92, visionVeto applied, records 1)
  - RECORD_INVENTORY climbfault=1 재실측 정정 + 8동작 --check PASS (records 14/14)
  - climbfault 재스윕 evidence (후보 4 · 눈 전건 기각 — ehz 층 침묵 실행 수치 박제)
  - wif DISCOVERY-LEDGER 행 10' 정정 + pnp 사전 추천(침묵) + 빈 판정란 (belle 노출 전 커밋)
  - p35_new_motion_docs.py veto env 함정 경고 + docstring env 3종·visionVeto.status 표식
affects: [발굴 자동화, 코퍼스 하네스 재발 방지, Phase 22 플라이휠]

tech-stack:
  added: []
  patterns:
    - "생성 모드 표식 = doc 자체의 visionVeto.status (disabled/skipped_error/applied) — 하네스 env 함정을 산출물에서 사후 판별"
    - "침묵 2층 구분 유지 — ls0(재료 부재) vs pnp(재료 있음 + 눈 전건 기각, ehz elbow 형)"

key-files:
  created:
    - .planning/quick/260814-ehz-5/evidence/climbfault/eye_calls.log
    - .planning/quick/260814-ehz-5/evidence/climbfault/eye_verdicts.json
    - .planning/quick/260814-ehz-5/evidence/climbfault/eye_ledger/ (json 6 + png 6)
    - .planning/quick/260814-ehz-5/evidence/climbfault/stills/ (개별 8 + PAIR 4)
  modified:
    - .planning/phases/35-server-rendered-comparison-video/data/climbfault/doc.json (veto-ON 본 교체)
    - .planning/quick/260814-ehz-5/discover_sweep.py (RECORD_INVENTORY 1행 + 주석 1줄)
    - .planning/quick/260814-ehz-5/evidence/climbfault/candidates.json (재스윕 전표로 재생성)
    - .planning/quick/260814-ehz-5/evidence/VISUAL-REVIEW.md (append only)
    - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md (append only)
    - backend/scripts/p35_new_motion_docs.py (경고 + docstring — 기본 거동 무변경)
    - .planning/quick/260821-pnp-climbfault-veto-on-doc-veto-env/260821-pnp-PLAN.md (기대 analysisId 정정)

key-decisions:
  - "기대 analysisId 불일치 → STOP 후 오케스트레이터 판정으로 회수본(...7579) 재박제 — 원인 = 오케스트레이터 핀 오류(no-veto run ID 오귀속), 실측이 핀을 이긴다"
  - "align.json 유지 가설 실측 확인 — 새 doc + 기존 align 소스 게이트 PASS, 재추출 불요 (Pod 학습 무간섭)"
  - "눈 전건 기각을 그대로 박제 — 억지 성립·임계 재튜닝·재시도 0 (1후보 1판정)"

requirements-completed: [QUICK-260821-PNP]

duration: 11min
completed: 2026-08-21
---

# Quick Task 260821-pnp: climbfault veto-ON doc 교체 + 재스윕 + veto env 함정 수리 Summary

**climbfault 코퍼스 doc 을 veto-ON 재분석본(record 1건)으로 교체하고 그 위에서
스윕을 재실행해 후보 4건이 기계 눈에서 전건 기각되는 침묵(ehz 층)을 수치와
실물로 박제했으며, ls0 장부 행 10 의 전제를 정정하고 하네스의 veto env 함정에
경고를 심었다.**

## Performance

- **Duration:** 약 11분 (2026-08-21T09:34:29Z → 09:45:35Z, checkpoint 대기 포함)
- **Tasks:** 3/3
- **Files:** doc 1 교체 + 하네스 2 수정(인벤토리·경고) + evidence 재생성 +
  장부/육안 append 2 + PLAN 정정 1

## 기계 판정 한 줄

doc 교체(4필드 assert PASS, 재박제 후) → 소스 게이트 **PASS**(새 doc + 기존
align 로컬 replay — align 무접촉) → record **1/1** 스캔(hold 52/91f, 6버킷,
claimOK 5) → 압축 후보 **4** → PAIR 4장 육안 전건 확인 → 기계 눈 실호출
**6회**(캐시 2) → **눈 PASS 0 (전건 기각)** → 카드 0 → 8동작 `--check`
**PASS (records 14/14)**.

| 항목 | 값 |
|---|---|
| 교체 doc | `p35newclimbfault1787297579` (overall 92, baseline 100→92, visionVeto **applied**) |
| record | 1건 — `r00:angle_vs_reference__right_knee`, atVideoSec 2.4088s, deviation 6.56 |
| 후보/눈/카드 | 4 / PASS 0 (기각 4) / 0 |
| 사전 추천 (장부 박제) | **발굴 0 — 침묵 (ehz 층: 재료 있음 + 눈 전건 기각)** |

## Task Commits

1. **Task 1: doc veto-ON 교체 + 인벤토리 1 정정 + 소스 게이트** — `c4ea10d4` (feat)
2. **Task 2: 재스윕 실행 (스캔→짝시트→눈) + 실물 열람 + --check 무회귀** — `ae1ee6d4` (feat)
3. **Task 3: 장부 행 10' 정정 + 사전 박제 + 하네스 veto env 경고** — `3558a90b` (fix)

## 눈 기각 상세 (정직 박제 — 통과 조작 없음)

- **ref 측 기각 2건** (4.4667s·7.2667s 후면 뷰): 트랙 claim extended
  (164.7/158.2도)를 눈이 **bent**(conf 0.95/0.85)로 기각. 실행자 육안도 눈과
  일치 — 다리가 접혀 발목 교차(크롭 실물 확인). **후면 가림에서의 트랙 환각을
  눈이 잡은 실물** (ehz elbow 기각 5건과 동형). 마크 원이 무릎이 아닌 힙~허벅지
  상부에 앉는 후면 뷰 트랙 좌표 품질 한계도 VISUAL-REVIEW 에 병기.
- **user 측 limb 불일치 2건** (3.333s·4.8s): 마크는 무릎 위치이나 무릎을 감싼
  팔뚝이 겹쳐 observed=bent/**arm** fail-closed (ii0 §3-2 마크-전위 방어 동작).
- **user 측 일치 2건**: bent/leg conf 0.98 — 학생 오른무릎 접힘은 트랙·눈 합의.

## Deviations from Plan

**1. [전제 붕괴 → checkpoint → 오케스트레이터 판정] 기대 analysisId 핀 오류 정정**
- **Found during:** Task 1 §1 4필드 assert
- **관측:** Pod 회수본의 analysisId = `p35newclimbfault1787297579` ≠ 플랜 pinned
  `p35newclimbfault1787296839` (740초 차이). 나머지 3필드(92 / applied /
  records 1 right_knee 2.409s)는 전건 일치.
- **판정 (오케스트레이터):** 핀 오류 — `...6839` 은 **veto 없이 돈 1차 재분석**
  (outdir `/workspace/p35_260821`, records 0)의 ID 였고, 오케스트레이터가 이를
  veto-ON doc 에 오귀속해 플랜에 박았다. `/workspace/p35_260821_veto/` 에는
  veto-ON 실행 1회만 쓰였으며 회수본의 visionVeto.status=applied 가 생성 모드를
  자증. 시간 산술(1차 633초 + ~2분 후 발사 = 740초 차)도 정합.
- **Fix:** 플랜 명시 STOP 이행(교체·커밋 없이 checkpoint 반환) → 오케스트레이터
  옵션 1 지시로 PLAN 기대값을 `...7579` 로 정정(동일 커밋 포함) 후 진행.
  Pod 재접촉 없음 — 접촉 총량은 scp GET 1회로 종결.
- **Commit:** c4ea10d4

**2. [제약 우선] SUMMARY docs 커밋 생략** — 실행 제약 "Do NOT commit docs
artifacts" 이 우선 (ls0 선례 동일). SUMMARY 는 파일로만 생성.

그 외 이탈 없음 — 임계 재튜닝 0, align 재추출 0, record 소스 발명 0.

## LLM 사용·학습 영향 (필수 절)

- **Gemini 실호출 6회** — 전부 `--eye` 단계 `card_gates.machine_eye`
  (캐시 적중 2건은 실호출 아님, 상한 16/record 내). record 분해: climbfault/r00
  6회 (user 4 + ref 고유 프레임 2).
- **모델: gemini-3.5-flash** (machine_eye 기본값, eye_calls.log 원장).
- **비용: flash 이미지 판정 6회 — 단가 기준 $0.01 미만 추정** (정확 청구액은
  Google AI Studio 콘솔 몫).
- **키 경로: SSM `/sunity/motion/gemini-api-key` → 환경변수 주입만** (키 값
  로그 0). 그 외 LLM 호출 0 (Cerebras 0).
- **학습 전송 0** — 추론 호출뿐. 외부로 나간 이미지 = 눈 크롭 6장(기승인 기계
  눈 경로, T-pnp-03 accept). 원장 보존 = `evidence/climbfault/eye_ledger/`.

## 프로덕션·Pod 무접촉 확인

- **S3 put 0** (영상 GET 만 — 렌더 자체가 0건이라 _S3Stub 경유도 0) /
  **Firestore 쓰기 0** (refmotion ref-climb 읽기 1건만) / **Pod 접촉 = scp GET
  1회뿐** (GPU·재분석·align 재추출 0 — v32 SFT 학습 무간섭).
- climb·combo doc 은 이번 범위 밖 — 100점(감점 0)이라 veto ON 이어도 record 0
  예상이므로 재생성하지 않음.
- backend 수정 = p35_new_motion_docs.py 1파일 (경고 + docstring — 기본 거동
  무변경, dry-run 출력 무회귀 실행 확인).

## Known Limitations (정직 박제)

1. **check() 출력 문자열 "5 motions" 하드코딩 잔존** — 검증 로직은 8동작 전부
   순회 (ls0 결정 유지, 수정 안 함).
2. **climbfault poleDiff 전건 None** — ii0 poles.json 에 climbfault 미등재라
   pair_gate 폴 축이 비구속. 수치는 candidates.json 에 그대로.
3. **기준 후면 뷰 트랙 좌표 품질** — 무릎 마크가 힙 부근에 앉음. 별건 조사
   의제 후보로 장부 판정란에 등재만 (판정은 belle 몫).
4. `.planning/quick/260821-fe9-20-a-vs-b/__pycache__/` 미추적 잔존 — 본 작업
   산출 아님, 무접촉 (out-of-scope).

## 다음

**belle 판정 대기 — 요청하지 않음.** 재료 위치 = wif DISCOVERY-LEDGER 의
`## climbfault veto-ON 재스윕 (260821-pnp)` 절 (행 10' 정정 + 침묵 추천 + 빈
판정란) + `evidence/climbfault/` (PAIR 4장 · 눈 크롭 6장 · 원장).

## Self-Check: PASSED

- 산출물 실물 확인:
  - `data/climbfault/doc.json` = `p35newclimbfault1787297579` (4필드 assert
    재실행 PASS) — FOUND
  - `discover_sweep.py` `"climbfault": 1` — FOUND
  - `evidence/climbfault/candidates.json` recordCount 1 + sourceGate PASS — FOUND
  - `evidence/climbfault/` stills 8 + PAIR 4 + eye_ledger 12 + eye_calls.log +
    eye_verdicts.json — FOUND
  - `VISUAL-REVIEW.md` · `DISCOVERY-LEDGER.md` append (`-`행 0) + `260821-pnp`
    태그 — FOUND
  - `p35_new_motion_docs.py` 토큰 3종 + dry-run 무회귀 — PASS
- 커밋 존재 3/3 — `c4ea10d4` · `ae1ee6d4` · `3558a90b`
- 게이트 재실행: `--check` PASS (records 14/14) · Task 1/3 verify PASS
- align.json diff 0 · 기존 5동작 + climb·combo evidence 무변경

---
*Phase: quick-260821-pnp*
*Completed: 2026-08-21*
