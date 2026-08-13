# SUPPORT-SURFACE — 하네스 freeze 주입 지원 범위 실측 박제 (착수 전 선행)

quick-260814-0p2 Task 1 (1). locked 제약: "하네스가 freeze 주입을 지원하지 않으면
지원 범위 실측을 먼저 박제". 아래는 실행자가 원본 파일을 직접 열어 확인한 실측이다.

## 1. freeze 주입은 현행 렌더러 미지원 — 실측

**`compare_render.build_timeline` (compare_render.py:1119-1321) 의 freezes 는
record-driven 이다.** 정지 1건의 유일한 생산 경로는 doc record 루프
(compare_render.py:1188 `for rec in records:`)이며:

- 레코드당 최대 1건 — freezes.append 는 이 루프 안의 단일 지점(:1306)뿐.
- mp3 필수 — `mp3 = audio_dir / f"{rid}.mp3"; if not mp3.exists(): ... 정지 스킵`
  (:1190-1194, excluded reason `no_mp3`).
- 순간 = record 의 atVideoSec (align.pairs enrich :1168-1171 포함) — 외부 순간을
  받는 파라미터 없음.

**`--pair-override-json` (rid→{refVideoSec, note}, :1214-1222)은 기존 record
freeze 의 rt(기준측)만 덮어쓴다.** 주석 원문(:1220-1222): "ut 는 기존 순간
유지(user 장면 무접촉), rt 만 명시값." — ut 무접촉, **정지 추가 경로 부재**.

따라서 "채택 발굴 순간(u12.8667/r12.40) 정지 추가"는 현행 하네스로 불가 →
**확장은 확정이며 0p2 사본(inject_freeze.py)에서만 수행한다** (원본
compare_render.py 무수정 — backend/ diff 0 게이트).

## 2. 리그 게이트 H2 는 외부 삽입을 설계상 검출한다 — 실측

**`compare_verify.verify` (compare_verify.py:313) 의 H2 (:225-249)** 는 freeze
마다 `userSec` 을 doc record `atVideoSec` 과 ±0.2s(`_H2_TOL_S`, :174) 대조한다.
면제 튜플은 `_H2_UT_DISPLACING_SRC = ("align-peak", "align-pole")` (:173) 뿐이다.

- 삽입 freeze: userSec 12.8667 vs doc r04 atVideoSec **10.503501167055687**
  (align.pairs 실측 동일값) → delta 2.363s > 0.2s → 운영 판정기 그대로는
  **구조적으로 H2 FAIL**. 이것이 H2 의 존재 이유("doc 에 없는 순간 = 외부 삽입
  의심" 검출)이며, 게이트가 설계대로 작동하는 것이다.
- 해소 = **정직한 사본 delta 1값**: 신규 freeze 에 pairSrc 신설 라벨
  `"discover"` 를 붙이고, 리그 실행 시 `_H2_UT_DISPLACING_SRC` 에 그 1값만
  드라이버 프로세스 수준(monkeypatch)으로 추가한다. 판정 로직·타 항목 무접촉.
- **align-peak / align-pole 사칭 절대 금지** (T-0p2-02 — 게이트 속이기 금지).
- 기존 freeze 전건은 **무수정 판정기 기준 PASS 를 별도 assert** 한다
  (T-0p2-01): 삽입 렌더에 무수정 verify 를 먼저 돌려 "FAIL = 신규 freeze 의
  H2 정확히 1건뿐"임을 기계 확인 후, 사본 delta 를 적용한 verify 로 ALL PASS.

나머지 H 항목은 운영 그대로 PASS 가능 (실측 근거):

- H1 정지 회계 (:206-222) — **rid 집합 동일성**. 삽입 freeze 의 rid 는 기존
  r04 와 중복 → set 붕괴로 accounted 집합 불변 = 무해.
- H3 자막 진품 (:251-266) — 삽입 freeze 의 text = 운영
  `coach_audio_speech_text(r04 record)` 재사용 (새 문구 발명 0) → 문자 일치.
- H4 음성 조인 (:268-281) — r04 는 doc coachAudio.items 에 존재 (실측: key
  `results/{uid}/{aid}/coach_audio_r04:angle_vs_reference__left_knee.mp3`).

## 3. r04 mp3 존재 실측

doc p34fresh1786628533 `result.coachAudio.status == "done"`, items 5건
(r00~r04 전건). r04 키 = `results/fvcNXzEqKjgqVxRPVSj1iwFnIpn2/
p34fresh1786628533/coach_audio_r04:angle_vs_reference__left_knee.mp3`
→ S3 GET 로 회수 (부재 아님 — locked 의 "없으면 캡션만" 분기는 미발동).
freeze dur = 운영 규칙 그대로 `mp3_duration_s(mp3) + FREEZE_TAIL_S(0.4)`
(compare_render.py:1310, :51).

## 4. 캐시 재수화 상태

wif 세션 scratchpad 캐시(`wif_fresh/`) 생존 확인 — 재사용:

- doc.json (result 5 records, coachAudio done) / refmotion.json
- user.mp4 (93,834,785 bytes) / ref.mp4 (4,517,365 bytes)
- align.json — userFrames **272** / refFrames **237** / fps 15.0 (P35 트랙
  replay 프레임 수 정확 일치 = 영상 정체성 게이트, wif fetch 검증분)
- render/u30_1080 · r30_1080 (30fps 1080p 추출 캐시) + pole_user.json
  (xNorm 0.5019) / pole_ref.json (xNorm 0.5014)
- 신규 회수 = 전 rid mp3 5건 (S3 GET → wif_fresh/audio/{rid}.mp3, ufb
  verify_local --fetch 패턴) + Pod 기계 눈 원장
  `results/{uid}/{aid}/eye/ledger.json` (S3 GET — Task 2 replay 스텁 소스)

## 5. 운영 반영 시 필요한 backend 변경 목록 (별도 사이클 — 이번 diff 0)

이번 사이클은 로컬 실증까지다. belle 실물 확인 후 반영 단계에서 필요한 변경:

1. **`compare_render.build_timeline` 주입 레이어** — record-driven freezes 에
   "발굴 채택 순간" 정지를 추가하는 공식 경로 (입력: rid, ut, rt, pairSrc 라벨.
   mp3/text/dur/viz 는 기존 record 규칙 재사용 — 이번 사본 래퍼가 그 스펙 실증).
2. **`compare_verify._H2_UT_DISPLACING_SRC` 에 발굴 라벨 추가** —
   `("align-peak", "align-pole", "discover")`. H2 는 "ut 를 의도적으로 옮기는
   승인 문법" 면제 축이므로 라벨 추가가 설계 정합 (판정 로직 무변경).
3. **발굴 순간의 doc 영속화 규약** — 12.8667/12.40 이 어디 저장되고 파이프라인
   어느 단계가 읽는가 (예: doc discovery 필드 / pair_overrides 확장). 이번
   사이클 스코프 밖 — belle 반영 결정과 함께.
