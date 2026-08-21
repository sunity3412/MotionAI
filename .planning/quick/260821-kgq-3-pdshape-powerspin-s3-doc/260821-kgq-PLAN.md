---
phase: quick-260821-kgq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
  - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py
  - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/
  - .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/260821-kgq-SUMMARY.md
autonomous: true
requirements: [QUICK-260821-KGQ]
tags: [discovery-adopt, production-apply, freeze-inject, polly-tts, s3-doc]

user_decisions:
  - "D-01: belle 08-21 '추천 1, 2 둘 다 오케이' — cand17B(피디쉐입 왼팔꿈치 u16.4667/r15.1333) · cand01E(파워스핀 왼어깨 u0.4667/r0.7333) 채택, 일괄 프로덕션 반영 승인"
  - "D-02: 동반 2건(피디쉐입 왼무릎 13.6s cand14B · 왼어깨 1.1s cand02B)은 판정 없음 — 장부에 '판정 보류'로만 기록, belle 재질문 금지"
  - "D-03: di7 확정 경로 그대로 재사용(정지 삽입 재렌더 → 검증 → S3/doc 반영 → live 왕복) — 새 경로 발명 금지, backend/ 코드 변경 0 원칙"
  - "D-04: 캡션은 새로 짓지 않는다 — 박제된 발굴 서술(ehz 시트 §3-1/§4-1 + belle 08-14 원문)에서 조립, LLM 호출 0"
  - "D-05: 음성 = chd 합성 경로 재사용 — AWS Polly(Seoyeon/neural/ko-KR, 운영 _synthesize_coach_audio_items 기본값 미러), 1회 합성 후 repo 고정(멱등)"

must_haves:
  truths:
    - "DISCOVERY-LEDGER 에 belle 08-21 판정(채택 2 · 보류 2)이 원문과 함께 기입되고 승격 실적 집계 행이 갱신돼 있다 (D-01/D-02)"
    - "피디쉐입 운영 compare_v1.mp4 에 왼팔꿈치 16.5s 발굴 정지(캡션+음성)가 삽입돼 있고, 기존 정지 6건(왼무릎 r04:discover 포함)이 전부 보존돼 있다"
    - "파워스핀 doc 에 renderedCompare + discovery 가 신설되고 왼어깨 0.5s 발굴 정지가 렌더에 들어 있다"
    - "프로덕션 쓰기 전건이 production_log 에 로그되고, 쓰기 전 사전 assert + 쓰기 후 GET 재확인 + live 재fetch 왕복 검증이 전부 PASS 다"
    - "이 사이클 LLM 추론 호출 0 (Gemini 0 / Cerebras 0) — Polly TTS 2회(비-LLM)만, SUMMARY 에 명기"
  artifacts:
    - path: ".planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py"
      provides: "di7 wire_discover.py 미러 드라이버 (2동작 파라미터화, --synthesize/--fetch/--baseline/--inject/--apply/--live/--check 스테이지)"
    - path: ".planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/discover_left_elbow.mp3"
      provides: "cand17B 캡션 Polly 합성 고정본 (렌더 결정론 입력)"
    - path: ".planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/discover_left_shoulder.mp3"
      provides: "cand01E 캡션 Polly 합성 고정본"
    - path: ".planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/pdshape_production_log.json"
      provides: "피디쉐입 프로덕션 쓰기 전건 로그 (md5 왕복 포함)"
    - path: ".planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/powerspin_production_log.json"
      provides: "파워스핀 프로덕션 쓰기 전건 로그"
    - path: ".planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md"
      provides: "belle 08-21 판정 기입 (append only)"
      contains: "08-21"
  key_links:
    - from: "doc result.discovery items"
      to: "compare_render.build_timeline 주입 레이어"
      via: "di7 정식 경로 — [discover] 실행 로그"
      pattern: "\\[discover\\]"
    - from: "discovery items[].mp3Key"
      to: "S3 results/{uid}/{aid}/discover_audio_{rid}_{joint}.mp3"
      via: "s3keys.build_discover_audio_key canonical 단일 출처"
      pattern: "build_discover_audio_key"
    - from: "renderedCompare.freezes"
      to: "발굴 정지 항목"
      via: "rid '{rid}:discover' 틱 (contract.md §12.9/§12.10)"
      pattern: ":discover"
---

<objective>
발굴 신규 채택 2건을 프로덕션에 반영한다 — belle 08-21 판정("추천 1, 2 둘 다
오케이")의 이행. 피디쉐입 왼팔꿈치 16.5s(cand17B)·파워스핀 왼어깨 0.5s(cand01E)를
di7 확정 경로(정지 삽입 재렌더 → 검증 → S3/doc 반영 → live 왕복 검증) 그대로
재사용해 반영하고, DISCOVERY-LEDGER 에 판정을 기입한다 (D-01~D-05).

Purpose: 발굴→채택→반영 사이클의 3번째·4번째 실적 — freeze 상속 승격 경로 누적.
Output: 운영 compare_v1.mp4 2건(피디쉐입 갱신·파워스핀 신설) + doc discovery/
renderedCompare 갱신 + 장부 기입 + production_log/verdict 박제 + SUMMARY.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/kimtaesung/Dev/SunityMotion/CLAUDE.md
@.planning/quick/260814-di7-s3-doc-freeze-discover/260814-di7-SUMMARY.md
@.planning/quick/260814-di7-s3-doc-freeze-discover/wire_discover.py
@.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py
@.planning/quick/260814-ehz-5/260814-ehz-SUMMARY.md
@.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md
</context>

<locked_coordinates>
플래너가 evidence 실물에서 확정한 좌표 — 실행 중 재조사 금지, 단 rid 는 live doc
에서 재해석(아래 명기).

**채택 1 — cand17B (피디쉐입 왼팔꿈치)**
- 출처: ehz `evidence/pdshapefault/eye_verdicts.json` `r00/cand17B` — joint
  `left_elbow`, uSec **16.4667** / rSec **15.1333**, uClaim bent(94.1도) /
  rClaim extended(162.5도), 눈 양측 arm 확정 PASS.
- 프로덕션 doc: uid `fvcNXzEqKjgqVxRPVSj1iwFnIpn2` / aid `p34fresh1786628533`
  (di7 가 왼무릎 discover 를 반영한 그 현행 운영 doc — planning context 명기).
- **rid 주의**: P35 doc 에서는 r00 이지만 p34fresh doc 은 record 순서가 다르다
  (knee 가 P35=r03 vs p34fresh=r04). **live doc 의 records 에서
  `angle_vs_reference__left_elbow` suffix 로 정확히 1건 매칭해 rid 를 해석**하고,
  2건 이상/0건이면 STOP. ehz 시트 §3-1 sanity: 그 record = pdshapefault 최대
  감점 record(-15.3).
- 현행 운영 상태 (di7 production_log 정본 — 사전 assert 기준):
  - `results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/p34fresh1786628533/compare_v1.mp4`
    md5 = `77cdcd436472438f3580cbb8d48683f3`
  - renderedCompare.freezes 6건 = r00 5.33 / r01 15.67 / r04 29.93 /
    **r04:discover 42.07** / r02 54.17 / r03 69.0
  - result.discovery.items = 1건 (r04 left_knee u12.8667/r12.4, mp3Key
    `.../discover_audio_r04_left_knee.mp3`, text = chd DISCOVER_TEXT)

**채택 2 — cand01E (파워스핀 왼어깨)**
- 출처: ehz `evidence/powerspin/eye_verdicts.json` `r02/cand01E` — joint
  `left_shoulder`, uSec **0.4667** / rSec **0.7333**, uClaim extended(179.0도) /
  rClaim bent(30.2도) — **방향 반대**(학생이 뻗고 기준이 접음), 눈 양측 arm 확정.
- 프로덕션 doc: uid `csKWYvI3WCPYPysNQ9KkWecaUvq1` / aid
  `powerspinFault1785373695` (ehz candidates.json meta + doc.json coachAudio 키
  `results/csKWYvI3WCPYPysNQ9KkWecaUvq1/powerspinFault1785373695/...` 에서 확정).
- 영상: user `fixtures/phase15/power-spin/fault.mp4` / ref
  `reference/ref-power-spin.mp4` (bucket `sunity-motion-pilot-videos`).
- records 3건 예상: r00 leg_extension / r01 split_angle /
  r02 angle_vs_reference__left_shoulder (rid 는 역시 live doc suffix 매칭으로
  해석). **discovery 반영 이력 없음** — P35 로컬 스냅샷에 renderedCompare 부재.
  live doc 에 renderedCompare 가 이미 있으면 예상 밖 상태 = STOP + 보고.

**보류 2 (장부 기입만 — D-02)**: 피디쉐입 r03/cand14B 왼무릎(u13.60/r12.93) ·
r02/cand02B 왼어깨(u1.0667/r2.20) — "판정 보류" 기록, 재질문 금지.

**캡션 정본 (D-04 — 문자 단위 그대로 사용, 실행 중 개작 금지)**

박제 소스: ehz DISCOVERY-SHEET.md §3-1/§4-1 육안 서술 + DISCOVERY-LEDGER belle
08-14 원문. 문법 = chd DISCOVER_TEXT (기준 국면 서술 → 결함 지적 → 행동 지시),
수치 표기 금지(D-09), 각도 마크 없음(belle 08-14 "각도 표기 부적절" 존중 —
discover 주입 레이어는 knee 외 관절에 마커를 그리지 않는다).

- DISCOVER_TEXT_ELBOW (cand17B):
  "기준 자세는 팔을 곧게 뻗어 폴을 잡는 순간인데, 왼쪽 팔꿈치가 접혀 있어요.
  손을 급하게 뻗어 잡으면 팔꿈치가 접혀요. 조금 더 돌고 올라온 뒤에 팔을 뻗어
  편하게 잡아보세요."
  (소스: 시트 §3-1 "학생은 팔꿈치에서 꺾인 예각 V, 기준은 팔을 따라 곧게 뻗은
  선" + belle 08-14 "좀 더 돌고 올라와야 팔을 뻗어 편하게 올라왔는데 좀 빠르게
  손을 뻗어 잡아서 이런 현상이 발생")
- DISCOVER_TEXT_SHOULDER (cand01E):
  "기준 자세는 팔을 굽혀 몸을 높이 들어올린 순간인데, 왼쪽 팔이 곧게 뻗어
  있어요. 시작할 때 팔을 굽혀 몸을 폴 쪽으로 당겨서, 안정적인 위치를 만든 뒤에
  돌아보세요."
  (소스: 시트 §4-1 "학생은 곧은 선, 기준은 접힌 V" + belle 08-14 "안정적인
  위치를 만들기 위해 기준 영상은 팔을 굽혀 더 들어올린 것… 자세도 안정적")

두 문장은 SUMMARY 에 원문 그대로 박제한다 (belle 사후 확인용 — planning context
게이트).
</locked_coordinates>

<tasks>

<task type="auto">
  <name>Task 1: 장부 판정 기입 + 캡션 음성 Polly 합성 고정</name>
  <files>.planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/discover_left_elbow.mp3, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/discover_left_shoulder.mp3, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/polly_synthesis.json</files>
  <action>
  (1) DISCOVERY-LEDGER.md 에 **append only** 로 "belle 판정 (2026-08-21)" 절을
  추가한다 (D-01/D-02): belle 원문 "추천 1, 2 둘 다 오케이" · "대기 건 먼저 봐야
  한번에 적용하기 편하지 않겠어" 인용 + ehz 기입란의 pdshapefault/powerspin 행이
  08-21 판정으로 **최종 채택 확정**됐음을 기록 (08-14 조건부 판정을 08-21 이
  종결). 동반 2건(cand14B 13.6s · cand02B 1.1s)은 "판정 보류" 로 기입 (판정
  부재 — 재질문 금지 명기). 승격 실적 집계 표에 행 append: 행 4(pdshapefault
  cand17B)·행 6(powerspin cand01E)의 최종 상태를 "08-21 채택 확정 — 일치" 로
  갱신하는 행/주석 (기존 행 수정 금지, append 로 정정 이력 보존).
  기존 본문 어떤 행도 수정·삭제하지 않는다.

  (2) `wire_adopt.py` 드라이버 골격 작성 — di7 `wire_discover.py` 를 베이스로
  복사·개작 (D-03: 새 경로 발명 금지). 핵심 변경: 좌표를 동작별 상수 블록
  (JOBS dict — pdshape/powerspin 각각 uid/aid/joint/uSec/rSec/DISCOVER_TEXT/
  기대 사전 상태)으로 파라미터화, `--motion {pdshape|powerspin}` 인자.
  스테이지: `--synthesize`(이 태스크) / `--fetch` / `--baseline` / `--inject` /
  `--check-wire` / `--apply` / `--live` / `--check-apply` (Task 2·3 에서 사용).
  캐시 경로 = **현 세션 scratchpad** (구 세션 scratchpad 는 휘발 — wire_discover
  의 OLD_SP 재사용 로직은 제거하고 S3/Firestore 재fetch 로 대체. 재료 보존은
  repo evidence 만). backend/ 는 import 만 하고 수정 0.

  (3) `--synthesize` 실행: 두 DISCOVER_TEXT 를 chd `inject_freeze.py synthesize()`
  미러로 Polly 합성 (D-05 — VoiceId Seoyeon / neural / ko-KR,
  ap-northeast-2, AWS_PROFILE sunity-motion). 각 1회 합성 후 evidence/ 에 고정,
  재실행 = 멱등 skip. `polly_synthesis.json` 에 두 건의 text 원문/md5/bytes/
  durationS/파라미터 기록. **Polly 는 TTS 비-LLM — Gemini/Cerebras 호출 0.**
  합성 후 mp3 재생 길이를 ffprobe(imageio-ffmpeg 동봉 바이너리 가능)로 실측해
  기록 (freeze 길이 = duration + 0.4s 운영 규칙의 입력).
  </action>
  <verify>
    <automated>python3 .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py --synthesize 2>&1 | grep -q "멱등" && rtk grep -c "2026-08-21" .planning/quick/260813-wif-knee-discovery/DISCOVERY-LEDGER.md</automated>
  </verify>
  <done>장부에 08-21 판정 절이 append 돼 있고(채택 2·보류 2·집계 갱신), mp3 2건이 evidence 에 고정돼 있으며(--synthesize 재실행 = 멱등 skip), polly_synthesis.json 에 캡션 원문·md5 가 박제. git diff 에서 DISCOVERY-LEDGER 는 append 만.</done>
</task>

<task type="auto">
  <name>Task 2: 피디쉐입 사이클 — 현행 운영본 베이스 재렌더 → 검증 → 반영 → live 왕복</name>
  <files>.planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/pdshape_wire_verdict.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/pdshape_production_log.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/pdshape_live_verdict.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/stills/</files>
  <action>
  di7 사이클 그대로 (D-03), 대상 = p34fresh 운영 doc. 전 스테이지 backend/
  원본 코드 무수정 호출 (compare_render.build_timeline / compare_verify /
  firestore_admin / s3keys).

  **--fetch**: live doc 재fetch (firestore_admin, 읽기) + 영상 S3 GET + coach
  mp3 5건 + knee discover mp3 S3 GET(md5 == `7fb6a4a3859cbea445266a9877847f94`
  대조 — chd repo 고정본과 동일 확인) + **현행 운영 compare_v1.mp4 S3 GET +
  md5 로그** (planning context 명기 — 기대값 `77cdcd436472438f3580cbb8d48683f3`,
  불일치 = STOP). rid 해석: live doc records 에서
  `angle_vs_reference__left_elbow` suffix 정확히 1건 → ELBOW_RID 확정.
  사전 상태 assert: renderedCompare.key == s3keys canonical + freezes 6건 ==
  locked_coordinates 값 + discovery.items == knee 1건 정확. 하나라도 어긋나면
  **쓰기 없이 STOP + 관측 그대로 보고**.

  **--baseline** (회귀 게이트 — 왼무릎 정지 보존의 실렌더 증명): live doc
  **그대로**(elbow 추가 전) 렌더 2회 → 결정론(compose 사슬/report 동일) + 사슬
  == chd `frames_md5_injected.json` + 무수정 compare_verify **ALL PASS** +
  report freeze 6건 == di7 정본 (5.33/15.67/29.93/42.07/54.17/69.0). 사슬
  불일치 = 환경 drift 의심 — STOP + 보고 (프로덕션 쓰기 진입 금지).

  **--inject**: discovery payload = **기존 knee 항목 + 신규 elbow 항목 병합**
  (update_analysis_discovery 는 field 통째 교체라 knee 를 잃으면 회귀 —
  planning context 게이트). elbow 항목: rid=ELBOW_RID, joint=left_elbow,
  userSec 16.4667 / refSec 15.1333, pairSrc="discover",
  text=DISCOVER_TEXT_ELBOW, mp3Key=build_discover_audio_key(단일 출처),
  adoptedAt="2026-08-21". `models._validate_discovery` 사전 통과 확인 후 doc
  사본 렌더: [discover] 로그 2건(knee+elbow) + freezes **7건** (기존 6건 rid·ut
  정체성 전건 보존 기계 확인 — outSec 이동은 elbow 삽입 위치상 발생 시 정직
  기록) + 무수정 verify ALL PASS + 결정론 2회 + 음성 게이트(elbow userSec
  +0.5s 비틀기 → H2 discover FAIL 정확 발생 후 원복). 신규 elbow 정지 프레임
  스틸 추출 → evidence/stills/ 저장 + **실행자 Read 육안 확인**
  (frames-before-numbers: 캡션 문장이 화면에 구워졌는가, 학생 접힘 vs 기준
  신전 대조가 읽히는가). --check-wire 게이트 exit 0 후 커밋.

  **--apply** (belle 08-21 승인 — D-01): 쓰기 4건, 전건 pdshape_production_log
  로그 (di7 형식 미러 — sourceMd5/s3RoundtripMd5): ① inject 렌더 mp4 →
  canonical `compare_v1.mp4` 같은 키 덮어쓰기 (직전 사전 assert 재실행 + 현행
  S3 md5 == 77cdcd43… 재확인 후) ② elbow mp3 → canonical discover_audio 키
  ③ update_analysis_discovery (knee+elbow 2 items) ④
  update_analysis_rendered_compare (freezes 7건, elbow = "{ELBOW_RID}:discover"
  틱, preFreezes 6건 로그).

  **--live**: doc 재fetch == 반영 payload → live doc + S3 방금 쓴 mp3 GET 로
  재렌더 → 사슬 == inject 사슬 + 무수정 verify ALL PASS + [discover] 2건 로그
  → pdshape_live_verdict.json. --check-apply exit 0.
  </action>
  <verify>
    <automated>python3 .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py --motion pdshape --check-wire && python3 .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py --motion pdshape --check-apply && rtk git status --porcelain backend/</automated>
  </verify>
  <done>pdshape wire_verdict(사전 assert·baseline==chd 사슬·inject 7 freezes·기존 6건 보존·verify ALL PASS·음성 게이트 FAIL 정확 발생)·production_log(쓰기 4건 md5 왕복)·live_verdict(재fetch·재렌더 왕복 PASS) 3종 박제, check 2종 exit 0, backend/ porcelain 빈 출력, 신규 정지 스틸 육안 확인 완료.</done>
</task>

<task type="auto">
  <name>Task 3: 파워스핀 사이클(신규) + SUMMARY 박제 + push</name>
  <files>.planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/powerspin_wire_verdict.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/powerspin_production_log.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/evidence/powerspin_live_verdict.json, .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/260821-kgq-SUMMARY.md</files>
  <action>
  같은 드라이버로 powerspin 사이클 (D-03). 차이점만:

  **--fetch**: live doc = `csKWYvI3WCPYPysNQ9KkWecaUvq1/powerspinFault1785373695`.
  사전 상태 assert 는 **부재 확인** — renderedCompare 부재(있으면 예상 밖 상태
  = STOP + 보고, planning context "discovery 반영 이력 없음" 검증 결론) +
  discovery 부재. rid 해석: `angle_vs_reference__left_shoulder` suffix 정확히
  1건 → SHOULDER_RID (예상 r02 — 다르면 관측 기록 후 live 값 사용). 영상 =
  fixtures/phase15/power-spin/fault.mp4 + reference/ref-power-spin.mp4 S3 GET,
  coach mp3 3건 GET.

  **--baseline**: discovery 없는 live doc 렌더 2회 — 결정론 + 무수정
  compare_verify ALL PASS + record freezes 3건(r00/r01/r02) 성립. (선행 승인
  사슬이 없는 신규 렌더라 chd 대조 게이트는 없음 — 자기 결정론 + 무수정 리그가
  게이트. 이 차이를 verdict 에 명기.)

  **--inject**: discovery items = 1건 (rid=SHOULDER_RID, joint=left_shoulder,
  userSec 0.4667 / refSec 0.7333, pairSrc="discover", text=
  DISCOVER_TEXT_SHOULDER, mp3Key canonical, adoptedAt="2026-08-21") →
  freezes 4건 (기존 record 정지 3건 rid·ut 보존 + shoulder ":discover") +
  [discover] 로그 + verify ALL PASS + 결정론 + 음성 게이트(+0.5s → H2 FAIL) +
  신규 정지 스틸 추출·Read 육안 확인. --check-wire exit 0 후 커밋.

  **--apply**: 쓰기 4건 powerspin_production_log — ① 렌더 mp4 → canonical
  compare_v1.mp4 (**신규 키** — 덮어쓸 기존 객체 없음 확인 후 put, 있으면 STOP)
  ② shoulder mp3 canonical 키 ③ update_analysis_discovery (1 item) ④
  update_analysis_rendered_compare (freezes 4건, status done). **--live**:
  재fetch == payload + live 재렌더 왕복 PASS → powerspin_live_verdict.json +
  --check-apply exit 0.

  **SUMMARY**: summary.md 템플릿. 필수 박제 — ① 최종 캡션 2문장 **원문 그대로**
  (belle 사후 확인용, planning context 게이트) ② LLM 학습 영향: Gemini/Cerebras
  호출 0 · Polly 2회(TTS 비-LLM, 코치 문장 텍스트만 송신) · 학습 전송 0 ③
  프로덕션 쓰기 8건 요약 + 사전 assert/왕복 md5 ④ 기존 정지 보존 기계 확인
  (피디쉐입 6건·파워스핀 record 3건) ⑤ Pod 실증 = 범위 밖(Pod 없음 — 뜨면
  별도) ⑥ deviation (있다면 — backend/ 변경이 불가피했다면 사유와 함께) ⑦
  보류 2건 장부 기입 사실. 커밋 후 **push 까지** (origin delta 0 확인).
  </action>
  <verify>
    <automated>python3 .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py --motion powerspin --check-wire && python3 .planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/wire_adopt.py --motion powerspin --check-apply && rtk git status --porcelain backend/ && rtk git log origin/main..HEAD --oneline | head -1</automated>
  </verify>
  <done>powerspin verdict 3종 박제(check 2종 exit 0), 캡션 2문장 원문이 SUMMARY 에 박제, LLM 호출 0 명기, backend/ porcelain 빈 출력, push 완료(origin/main..HEAD 빈 출력).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 → S3/Firestore 프로덕션 | AWS_PROFILE sunity-motion 자격으로 운영 데이터 덮어쓰기 |
| 로컬 → AWS Polly | 코치 문장 텍스트 송신 (PII 0, 시크릿 0) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-kgq-01 | Tampering | compare_v1.mp4 덮어쓰기 | mitigate | 쓰기 전 사전 assert (doc key == canonical + 현행 S3 md5 == 77cdcd43…) — 불일치 STOP, 쓰기 후 GET md5 왕복 재확인 |
| T-kgq-02 | Tampering | doc discovery 통째 교체 | mitigate | 기존 knee 항목 병합 필수 + _validate_discovery 사전 통과 + live 재fetch == payload 대조 |
| T-kgq-03 | Repudiation | 프로덕션 쓰기 | mitigate | production_log.json 전건 로그 (di7 형식 — op/key/md5/at) + git 커밋 |
| T-kgq-04 | Info Disclosure | Polly 송신 | accept | 코치 문장 텍스트만 — PII/시크릿 0, 학습 전송 0 (SUMMARY 명기) |
| T-kgq-SC | Tampering | 패키지 설치 | accept | 이 사이클 신규 패키지 설치 0 — 기존 venv/의존성만 사용 |
</threat_model>

<verification>
- 두 동작 check-wire / check-apply 전건 exit 0 (기계 게이트).
- `rtk git status --porcelain backend/` 빈 출력 (D-03 — backend 코드 변경 0).
- DISCOVERY-LEDGER diff = append only.
- evidence 6종(verdict×4 + production_log×2) + mp3 2건 + polly_synthesis.json 실재.
- push 완료 (origin/main..HEAD 빈 출력).
</verification>

<success_criteria>
- belle 08-21 채택 2건이 운영 S3/doc 에 반영되고 live 왕복 검증 PASS.
- 기존 정지 전건 보존 기계 확인 (피디쉐입 6건 — 왼무릎 discover 포함).
- 보류 2건은 장부 기입만 (재질문 0).
- LLM 추론 호출 0 (Polly TTS 2회만) — SUMMARY 명기.
- 캡션 2문장 원문 SUMMARY 박제 (belle 사후 확인 재료).
</success_criteria>

<output>
Create `.planning/quick/260821-kgq-3-pdshape-powerspin-s3-doc/260821-kgq-SUMMARY.md` when done
</output>
