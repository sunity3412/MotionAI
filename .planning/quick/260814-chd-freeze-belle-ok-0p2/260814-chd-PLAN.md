---
phase: quick-260814-chd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/discover_left_knee.mp3
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/polly_synthesis.json
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/baseline_verdict.json
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/inject_verdict.json
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/frames_md5_baseline.json
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/frames_md5_injected.json
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/cards/
  - .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/stills/
autonomous: true
requirements: [QUICK-260814-CHD]
tags: [freeze-inject, caption-fix, polly-tts, compare_verify, card-inherit]

must_haves:
  truths:
    - "재렌더 영상의 발굴 정지(u12.8667/r12.40) 캡션 = 박제 신규 문장 (구 r04 문구 아님), 음성 = 같은 문장의 새 Polly mp3 (자막=음성 lockstep 유지)"
    - "원본 r04 정지(10.5s)의 캡션·음성·길이 무변경 + 기존 정지 5건 프레임 bit-무회귀"
    - "무수정 compare_verify FAIL = 발굴 freeze 의 H2+H3 정확 2건 (기존 항목 전건 PASS), 사본 delta 적용 시 ALL PASS — align-peak/pole 사칭 0"
    - "상속 무릎 카드 md5 = 0p2 카드(= wif belle 채택 카드)와 동일 — 상이 시 STOP 후 보고 (belle 재채택 필요)"
    - "belle 확인 재료에 구 문구 -> 새 문구 원문 대조 명기"
  artifacts:
    - path: ".planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py"
      provides: "0p2 하네스 사본 확장 — DISCOVER_TEXT 상수 + --synthesize + H3 discover delta"
    - path: ".planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/discover_left_knee.mp3"
      provides: "발굴 문장 Polly 합성 실물 (repo 보존 — 렌더 결정론의 고정 입력)"
    - path: ".planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/polly_synthesis.json"
      provides: "합성 파라미터 기록 (voice/engine/text/md5/durationS)"
    - path: ".planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/inject_verdict.json"
      provides: "리그 stock 2FAIL 국한 + delta ALL PASS + diff 국한 + 카드 md5 무회귀 기계 판정"
  key_links:
    - from: "inject_freeze.py DISCOVER_TEXT 상수"
      to: "Polly Text= 파라미터 / freeze['text'] / H3 delta expected"
      via: "단일 상수 참조 3곳 (문장 단일 소스 — 자막·음성·판정 lockstep)"
      pattern: "DISCOVER_TEXT"
    - from: "evidence/discover_left_knee.mp3"
      to: "freeze['dur']"
      via: "cr.mp3_duration_s(mp3) + cr.FREEZE_TAIL_S(0.4) — compare_render.py:1310 운영 규칙"
      pattern: "mp3_duration_s.*FREEZE_TAIL_S"
    - from: "evidence/cards/ 무릎 카드"
      to: ".planning/quick/260814-0p2-fresh-pdshape-freeze/evidence/cards/ 대응 카드"
      via: "md5 동일성 게이트 (상이 = 카드에 문장 구움 의심 -> STOP)"
---

<objective>
belle 판정(2026-08-14 "영상은 괜찮음, 캡션만 고치면 됨") 반영 — 발굴 정지
(왼무릎, u12.8667/r12.40)의 캡션·음성을 belle 결함 서사("다리 펴고 회전 후
걸기")에 정합하는 신규 문장으로 교체해 로컬 재렌더한다. 원본 r04 정지(10.5s)는
그 순간 기준으로 옳으므로 무변경. S3/Firestore 반영은 belle 확인 후 별도 사이클.

Purpose: 0p2 재렌더가 발굴 정지에 r04 문구를 재사용했는데 그 문구("깊게 접은
다리 모양 그대로 겹쳐 맞춰보세요")는 발굴 순간의 결함 서사(학생 무릎 접힘 vs
기준 신전 — 펴야 함)와 반대 방향이다. 음성=자막 단일 소스(cue_text.py)이므로
캡션만 바꾸면 V-A 불일치가 재발한다 — 새 문장을 Polly 로 새로 합성해야 한다.

Output: chd 하네스 사본(inject_freeze.py) + 새 mp3 + 재렌더 mp4 + 리그 기계
판정(stock 2FAIL 국한 -> delta ALL PASS) + 카드 3장 md5 무회귀 + belle 확인
재료 갱신(/Users/Shared/sunity-freeze-inject-260814/).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260814-0p2-fresh-pdshape-freeze/260814-0p2-SUMMARY.md
@.planning/quick/260814-0p2-fresh-pdshape-freeze/evidence/SUPPORT-SURFACE.md
@.planning/quick/260814-0p2-fresh-pdshape-freeze/inject_freeze.py
@backend/shared/python/sunity_shared/analysis/cue_text.py
@backend/shared/python/sunity_shared/analysis/compare_verify.py (170~283행 — H1~H4)
@backend/functions/pipeline/app.py (3916~4005행 — Polly 합성 미러 대상)
</context>

<locked_decisions>
사전 실측 완료 — 실행 중 재조사 금지:

1. **박제 신규 문장 (실행 중 재작성 금지 — 이 원문 그대로 코드 상수화):**

   `기준 자세는 다리를 곧게 편 채 회전하는 순간인데, 왼쪽 무릎이 접혀 있어요. 무릎을 접은 채 돌지 말고, 다리를 끝까지 편 상태로 회전한 뒤에 걸어보세요.`

   - 패턴 = 기존 코치 문장 구조 미러: 관측(결함) 1문장 + 행동 지시 1문장.
   - 문장 사이 경계 = 마침표 + 공백 (cue_text.py coach_audio_speech_text 의
     Polly run-on 방지 규칙 — belle 08-07 실기기 반려 근거).
   - belle 서사 정합: 올바른 수행 = 다리 펴고 회전 후 걸기.
2. **H3 는 rid 단위 text_overrides 로 구분 불가** (compare_verify.py:256 —
   `(text_overrides or {}).get(rid)`): 발굴 정지와 원본 정지가 rid=r04 를
   공유하므로 override 는 두 정지에 동시 적용돼 원본 쪽이 FAIL 난다. 해소 =
   H2 와 같은 사본 delta — pairSrc=="discover" freeze 만 expected text 를
   DISCOVER_TEXT 로. **align-peak/align-pole 사칭 절대 금지.**
3. **H4 는 rid 존재만 검사** (compare_verify.py:268-281) — r04 가 doc
   coachAudio.items 에 있으므로 새 mp3 로컬 전용이어도 통과. delta 불요.
4. **freeze dur = mp3_duration_s(mp3) + FREEZE_TAIL_S(0.4)** — 새 mp3 로 정지
   길이가 기존 9.8s 에서 변동한다. 정상이며 실측값을 기록.
5. **상속 카드 md5 게이트**: 무릎 카드가 0p2 카드(= wif belle 채택 카드,
   byte-동일 실증)와 md5 상이하면 카드에 문장이 구워져 있다는 뜻 -> **STOP,
   수정 시도 금지, belle 재채택 필요 보고.**
6. Polly 파라미터 = 운영 `_synthesize_coach_audio_items` 미러 (app.py:3981-
   3986): Text / VoiceId="Seoyeon" / Engine="neural" / LanguageCode="ko-KR" /
   OutputFormat="mp3" (Seoyeon·neural = app.py:3937-3938 env 기본값 미러 —
   Pod env 실값은 터미네이트로 확인 불가, 기본값 채택을 기록으로 남긴다).
   자격증명만 로컬 방식: boto3.Session(profile_name="sunity-motion"),
   region ap-northeast-2 (하네스 _s3_client 패턴).
</locked_decisions>

<tasks>

<task type="auto">
  <name>Task 1: 발굴 문장 박제 + Polly 합성 + 하네스 사본 확장</name>
  <files>.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/discover_left_knee.mp3, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/polly_synthesis.json</files>
  <action>
    0p2 `inject_freeze.py` 를 chd quick dir 로 복사해 확장한다 (0p2 원본 파일
    무수정 — 이번 사이클의 diff 는 chd dir 에만).

    사본 조정:
    - `_HERE` 기반 상대 경로라 EV 는 chd evidence/ 로 자동 이동. `OUT` 은
      `SP.parent / "chd_out"` 으로 교체 (0p2 산출과 분리). `SP`(wif_fresh
      캐시 좌표)는 0p2 값 그대로 유지 — 캐시 생존 시 재사용, 휘발 시 기존
      `--fetch` 가 S3 GET 만으로 재수화 (SUPPORT-SURFACE §4).
    - `DISCOVER_TEXT` 상수 신설 = locked_decisions 1 의 박제 원문 그대로
      (문자 단위 동일 — 재작성·윤문 금지).
    - `DISCOVER_MP3 = EV / "discover_left_knee.mp3"` 상수 신설.

    `--synthesize` 스테이지 신설 (멱등 — mp3 존재 시 재합성 금지, Polly 는
    호출마다 바이트가 달라 렌더 결정론이 깨진다):
    - locked_decisions 6 파라미터로 synthesize_speech 1회 호출, AudioStream
      을 DISCOVER_MP3 에 저장.
    - `evidence/polly_synthesis.json` 기록: voiceId, engine, languageCode,
      text(원문), mp3Md5, durationS(cr.mp3_duration_s 실측), 합성 시각,
      "Seoyeon/neural = 운영 env 기본값 미러 (Pod env 실값 확인 불가)" 주석.

    `_install_injection` 수정 — discover freeze 3필드만 교체, 나머지
    (markers/_body_line_viz 미러, ut/rt, rid, joint) 전부 0p2 그대로:
    - `"text": DISCOVER_TEXT` (coach_audio_speech_text(rec) 재사용 제거)
    - `"mp3": DISCOVER_MP3` (audio_dir/r04.mp3 는 원본 r04 정지 전용으로 잔류
      — record-driven 원본 build_timeline 경로 무접촉)
    - `"dur": cr.mp3_duration_s(DISCOVER_MP3) + cr.FREEZE_TAIL_S`
    - DISCOVER_MP3 부재 시 assert 실패 메시지 "합성 선행 필요 (--synthesize)".

    `_verify` delta 확장 — delta_label 지정 시에만 (try/finally 복원):
    - 기존 H2 tuple delta (`_H2_UT_DISPLACING_SRC + ("discover",)`) 유지.
    - H3 discover delta 신설: `cv.authenticity_checks` 를 래퍼로 교체.
      요구사항 (1) report freezes 중 pairSrc=="discover" 는 정확 1건 assert
      (2) 그 freeze 에 대응하는 H3 엔트리만 실제 문자 비교
      `fz["text"] == DISCOVER_TEXT` 로 교체하고 라벨을
      "H3 자막 진품 r04[discover]" + 상세에 "사본 delta — expected=발굴
      박제 문장" 명기 (fail-closed: 불일치면 FAIL 그대로)
      (3) 원본 r04 를 포함한 비-discover freeze 의 H3 판정 무접촉 (엔트리
      매핑은 freeze 순서 보존 — H3 루프와 freezes 순회 순서 동일 실측,
      compare_verify.py:251). text_overrides 미사용 (locked 2).

    `inject()` stock 국한 조건 갱신 (0p2 는 1FAIL, 이번은 2FAIL):
    - 무수정 판정기 FAIL 정확 2건: ① "H2 순간" 포함 + "src=discover" 포함
      ② "H3 자막 진품 r04" 포함 + DISCOVER_TEXT 앞 20자 포함 (FAIL 상세가
      구운 text 40자를 인용하므로 — compare_verify.py:265).
    - 추가 assert: 무수정 lines 에 "H3 자막 진품 r04" PASS("문자 일치")가
      정확 1건 존재 (= 원본 r04 정지의 캡션 무변경 기계 증명).

    `check_inject()` 게이트 확장:
    - discover freeze 의 text == DISCOVER_TEXT (문자 단위)
    - discover freeze 의 freezeS == cr.mp3_duration_s(DISCOVER_MP3) + 0.4
      (오차 0.01s)
    - stock FAIL 2건 국한 + 원본 r04 H3 PASS 1건 (위 조건 그대로)
    - 카드 md5 무회귀: chd cardMd5Run1 의 파일명별 md5 == 0p2
      `evidence/cards/*.png` 실파일 md5 (3장 전건). 무릎 카드 상이 시 별도
      FAIL 메시지 "카드에 문장 구움 의심 — STOP, belle 재채택 필요 보고"
      (locked 5), 기존 2장 상이 시 "카드 회귀".
    - 기존 게이트(delta ALL PASS, 결정론, diff 국한 3층, survivors
      r04:inherit@u12.867/r12.40, 카드 초 라벨 12.9, 눈 실호출 0, replay
      miss 0) 전부 유지.

    실행: `--synthesize` 를 실제 1회 실행해 mp3 실물 + polly_synthesis.json
    을 만든다 (env: `AWS_PROFILE=sunity-motion`). Polly 는 TTS 비-LLM
    실호출 1회 — SUMMARY 의 LLM 학습 영향 절 기재 대상.

    커밋 (원자): 하네스 사본 + mp3 + 합성 기록.
  </action>
  <verify>
    <automated>AWS_PROFILE=sunity-motion /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py --synthesize && test -s /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/discover_left_knee.mp3 && grep -c "DISCOVER_TEXT" /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py</automated>
  </verify>
  <done>
    DISCOVER_TEXT = 박제 원문 문자 단위 동일 상수화 (참조 3곳: Polly Text /
    freeze text / H3 delta expected). mp3 실물 + durationS 실측 기록 존재.
    --synthesize 재실행이 재합성 없이 skip (멱등). 0p2 dir · backend/ 무수정
    (`git status --porcelain backend/ .planning/quick/260814-0p2-fresh-pdshape-freeze/` 출력 0줄).
  </done>
</task>

<task type="auto">
  <name>Task 2: 재렌더 + 리그(stock 2FAIL 국한 -> delta ALL PASS) + 무회귀 기계 검증</name>
  <files>.planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/baseline_verdict.json, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/inject_verdict.json, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/frames_md5_baseline.json, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/frames_md5_injected.json, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/cards/, .planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/stills/</files>
  <action>
    스테이지 순차 실행 (전부 `AWS_PROFILE=sunity-motion` +
    `backend/.venv/bin/python`, S3 GET 만·Firestore 쓰기 0·Gemini 실호출 0):

    1. `--fetch` — wif_fresh 캐시 확인/재수화 (align 272/237 정체성 게이트
       포함) + 전 rid mp3 + Pod eye ledger.
    2. `--baseline && --check-baseline` — 주입 off 렌더 2회 결정론 + 운영
       리그 무수정 ALL PASS + freeze 5건 outSec 운영 doc 대조 (0p2 재현:
       r00 5.33 / r01 15.67 / r04 29.93 / r02 43.0 / r03 57.83).
    3. `--inject` — 주입 on 렌더 2회. 무수정 판정기 FAIL = 발굴 freeze 의
       H2+H3 정확 2건 국한 + 원본 r04 H3 PASS 확인 -> 사본 delta 로 ALL
       PASS. diff 국한 3층 (report 기존 필드 동일 / compose JPEG md5 사슬
       — 삽입 블록+페이드 5프레임 외 bit-동일 / mp4 공유 소스 전이 증명은
       `--recontent` 로).
    4. `--cards` — 운영 _run_gated_card_inherit + 눈 replay 스텁 (실호출 0,
       miss 시 fail-closed 박제 — 실호출 대체 금지).
    5. `--check-inject` — exit 0.

    **STOP 조건** (locked 5): check-inject 가 "카드에 문장 구움 의심" FAIL 을
    내면 즉시 중단 — 수정·재시도 금지, 현 상태 그대로 커밋 후 "무릎 카드가
    캡션에 종속 -> belle 재채택 필요" 를 최종 보고에 명기.

    육안 실물 확인 (frames-before-numbers 게이트):
    - 발굴 정지 중앙 프레임 스틸 1장을 injected mp4 에서 인덱스 정확 추출
      (`_extract_frame_idx` 재사용)해 `evidence/stills/` 저장 + Read 로 열어
      **새 캡션 문장이 화면에 구워져 있는지** 눈 확인 (캡션 교체의 실물 증거).
    - 기존 정지 1장(r04 원본 10.5s)도 같은 방식으로 추출·Read — 구 문구
      잔존(무변경) 눈 확인.

    커밋 (원자): evidence 전건.
  </action>
  <verify>
    <automated>AWS_PROFILE=sunity-motion /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py --check-baseline && AWS_PROFILE=sunity-motion /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python /Users/kimtaesung/Dev/SunityMotion/.planning/quick/260814-chd-freeze-belle-ok-0p2/inject_freeze.py --check-inject</automated>
  </verify>
  <done>
    check-baseline PASS + check-inject PASS (stock 2FAIL 국한 · delta ALL
    PASS · 결정론 2회 · diff 국한 · 카드 3장 md5 == 0p2 · 초 라벨 12.9 ·
    눈 실호출 0). 스틸 2장 육안 확인 완료 (새 캡션 구움 / 구 캡션 무변경).
    inject_verdict.json 에 discover freezeS 실측값 기록.
  </done>
</task>

<task type="auto">
  <name>Task 3: belle 확인 재료 갱신 + 마감 게이트</name>
  <files>.planning/quick/260814-chd-freeze-belle-ok-0p2/evidence/ (안내 사본 원본)</files>
  <action>
    `/Users/Shared/sunity-freeze-inject-260814/` 갱신 (휘발 가능 사본 — 보존
    주장 금지, 정본은 repo evidence/):
    - 재렌더 영상을 새 injected mp4 로 교체 (기존 한글 파일명 유지).
    - 발굴 정지 새 캡션 스틸 + 원본 r04 무변경 스틸 추가 (한글명).
    - `안내.md` 에 "캡션 변경" 절 추가 — 대조는 **실측 인용**: 구 문구 =
      이번 렌더 report 의 원본 r04 freeze text (coach_audio_speech_text
      조립문 그대로 인용), 새 문구 = DISCOVER_TEXT 원문. 함께 명기:
      음성 재합성(Polly Seoyeon neural — 운영 기본값 미러), 발굴 정지 길이
      변동(구 9.8s -> 실측값), S3/doc 반영은 belle 확인 후 별도 사이클
      (SUPPORT-SURFACE §5 + 이번 캡션 소스의 doc 영속화 규약 추가 필요 명기).
    - 안내.md 원문 사본을 repo `evidence/` 에도 저장 (Shared 휘발 대비 정본).

    마감 게이트:
    - `git status --porcelain backend/` 출력 0줄 (backend 원본 무수정).
    - 0p2 quick dir 무수정 확인.

    SUMMARY 작성 시 LLM 학습 영향 절: Gemini 실호출 0 (replay 스텁),
    Polly 1회 = TTS 비-LLM 실호출·학습 전송 0, S3 GET 만·쓰기 0.

    커밋 (원자): 안내 사본 + SUMMARY.
  </action>
  <verify>
    <automated>test -s "/Users/Shared/sunity-freeze-inject-260814/안내.md" && grep -q "걸어보세요" "/Users/Shared/sunity-freeze-inject-260814/안내.md" && [ -z "$(git -C /Users/kimtaesung/Dev/SunityMotion status --porcelain backend/)" ]</automated>
  </verify>
  <done>
    Shared dir 에 재렌더 영상 + 스틸 + 캡션 대조 안내 갱신. backend/ diff 0.
    belle 제시용 새 캡션 문구가 안내.md 에 원문 대조로 존재.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 로컬 -> AWS Polly | 코치 문장 텍스트 송신 (PII 0, 시크릿 0 — TTS 비-LLM) |
| 로컬 -> S3 | GET 만 (기존 자산 회수) — put 은 하네스 스텁 캡처, 실쓰기 0 |
| 하네스 -> 운영 판정기 | 사본 delta 는 라벨 명기 면제만 — 게이트 사칭(align-peak/pole) 금지 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-chd-01 | Tampering | compare_verify 사본 delta | mitigate | 무수정 판정기 FAIL 2건 국한을 먼저 박제한 뒤 discover 라벨 명기 면제만 — 사칭 0, 원본 r04 H3 PASS 별도 assert |
| T-chd-02 | Repudiation | Polly 합성 비결정 | mitigate | 합성 1회 후 repo 고정 (멱등 --synthesize) — 렌더 결정론 2회 게이트가 소비 |
| T-chd-03 | Tampering | backend/ 원본 | mitigate | git porcelain 0줄 게이트 (Task 1·3) |
| T-chd-SC | Tampering | 패키지 설치 | accept | 신규 설치 0 — 기존 backend/.venv 만 사용 |
</threat_model>

<verification>
- Task 1: --synthesize 실행 + mp3 실물 + DISCOVER_TEXT 단일 소스 grep
- Task 2: --check-baseline · --check-inject 둘 다 exit 0 (stock 2FAIL 국한 +
  delta ALL PASS + 카드 md5 3장 + diff 국한 + 결정론 + 눈 실호출 0)
- Task 3: Shared 안내.md 캡션 대조 존재 + backend porcelain 0줄
- 육안: 발굴 정지 스틸 = 새 캡션 구움 / 원본 r04 스틸 = 구 캡션 무변경
</verification>

<success_criteria>
- 열어볼 수 있는 재렌더 실물 (Shared + repo evidence) — 발굴 정지 캡션·음성이
  박제 신규 문장, 원본 정지 5건·카드 3장 무회귀
- 기계 판정 ALL PASS (사본 delta 2축 — H2 tuple + H3 discover expected — 전부
  라벨 명기, 사칭 0)
- belle 제시용 구 문구 -> 새 문구 원문 대조 완비
- backend/ diff 0 · S3/Firestore 쓰기 0 · Gemini 실호출 0 · Polly 1회 기록
</success_criteria>

<output>
Create `.planning/quick/260814-chd-freeze-belle-ok-0p2/260814-chd-SUMMARY.md` when done
</output>
