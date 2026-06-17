# 15-SC4-AGGREGATE-EVIDENCE — 13-영상 통합 SC4 집계 (read-only)

> **소유:** 15-05 단독 (HIGH 3 — depends_on:["15-03","15-04"] wave 3, two evidence set 확정 후 합산).
> **방법:** read-only status 카운트 합산만 — 15-03 Mode 1 evidence + 15-04 Mode 3 evidence 의 기록 카운트를 더할 뿐, analysis doc 재분석·재sweep **0** (T-15.05-00 mitigate).
> **검증:** verify 가 `mode1_total`/`mode3_total`/`combined_total`/`combined_server_error` 실 카운트를 parse — 단순 파일 존재 체크 아님 (T-15.05-08 / MEDIUM 4 mitigate).
> ROADMAP SC4: 다양한 동작/앵글 세트에서 크래시·tracking 실패 없이 일관된 점수 완주.

---

## Source-of-truth (read-only inputs)

| Source plan | Evidence file | 산출 카운트 (read-only) |
|---|---|---|
| 15-03 (Mode 1, MODE_EXPERT) | `15-MODE1-FALSEPOSITIVE-EVIDENCE.md` §Mode1 7/7 server_error==0 GATE | 7 motion: 7 done / server_error 0 / no_human 0 / not_pole_motion 0 (uid `phase15_mode1_…254964` + retry `…675370`) |
| 15-04 (Mode 3, MODE_SELF) | `15-MODE3-DUALCOACH-EVIDENCE.md` §Mode3status | 6 페어(=12 doc): 12 done / server_error 0 / no_human 0 / not_pole_motion 0 (runId `1781690825384`) |

**SC4 집계 단위 정합 (count reconciliation):**
SC4 의 "13-영상" 통합 단위는 **분석 unit(motion/pair)** 이다 — Mode 1 은 7 motion, Mode 3 은 6 motion/pair. 따라서 통합 unit 수는 7 더하기 6 으로 13.
15-04 §Mode3status 가 보고하는 `total = 12` 는 ANALYSIS DOC 수(6 페어 × {fault, success})이며, SC4 의 unit 카운트(6 motion/pair)와 다른 척도다. SC4 는 Mode 3 의 **6 motion/pair** 를 unit 으로 합산한다(combo 는 Mode-1-only 7 에 포함, Mode-3 페어 없음 — 정상). server_error 합산은 doc-level 카운트(Mode 1 7 doc + Mode 3 12 doc 모두 server_error 0)와 unit-level 모두 0 으로 동일하게 0 이다.

---

## §SC4-집계 표 — 13-영상 통합 status 카운트 (15-03 Mode1 7 + 15-04 Mode3 6 합산)

| 구분 | total | completed (done) | no_human | not_pole_motion | server_error (안전게이트 외 unexpected) |
|---|---|---|---|---|---|
| Mode 1 (MODE_EXPERT, 15-03) | 7 | 7 | 0 | 0 | 0 |
| Mode 3 (MODE_SELF, 15-04, motion/pair unit) | 6 | 6 | 0 | 0 | 0 |
| **통합 (13-영상)** | **13** | **13** | **0** | **0** | **0** |

**Assert:**
- `combined_total == 13` (7 + 6) — 13-영상 통합 unit 수.
- `combined completed == 13` — 13/13 전부 완주 (크래시·tracking 실패 없이 done).
- 안전게이트 분류 `no_human == 0`, `not_pole_motion == 0` — 13-영상 중 안전게이트 발동 0.
- **`combined_server_error == 0`** — 안전게이트(no_human/not_pole_motion) 외 unexpected pipeline 실패/크래시 == 0 (ROADMAP SC4 핵심 assert). doc-level(Mode 1 7 doc + Mode 3 12 doc) 로 검사해도 server_error 0.
- 어느 카운트라도 누락이거나 `server_error > 0` 이면 SC4 미충족 → verify non-zero FAIL (MEDIUM 4 — 파일 존재 silent 통과 차단).

**도출 근거 (임의 채우기 0):** 위 모든 값은 15-03 §Mode1 GATE 표(done 7 / server_error 0)와 15-04 §Mode3status 표(done 12 / server_error 0, 6 페어)에서 read-only 파생. SC4 verify 정규식이 parse 하는 고정 키:값은 아래 machine-parseable 블록 참조.

---

## Machine-parseable counts (verify regex `키[:=]숫자` parse target)

mode1_total: 7
mode3_total: 6
combined_total: 13
combined_completed: 13
combined_no_human: 0
combined_not_pole_motion: 0
combined_server_error: 0

---

## SC4 결론

13-영상(Mode 1 7 motion + Mode 3 6 motion/pair) 통합 sweep 이 **크래시-프리·일관 완주** 했다 — 13/13 completed, 안전게이트 발동 0, **unexpected pipeline 실패(server_error) == 0**. 다양한 동작(climb/combo/elbow-twist-sister/kip-up/pdshape/peter-pan/power-spin × Mode1 + 6 fail→success 페어 × Mode3)·앵글 세트에서 일관되게 분석을 완주했다(ROADMAP SC4 PASS). 사람 점수 라벨 ground truth 미사용(D-06) — 본 집계는 status 카운트(객관 pipeline 상태)만 합산하며 점수 품질 판정은 15-03/15-04 evidence 소관.

> **재sweep/재분석 0** (HIGH 3): 본 문서는 15-03·15-04 의 확정 evidence 카운트를 read-only 합산만 했다.
