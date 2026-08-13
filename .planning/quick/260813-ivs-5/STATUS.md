# 승인 5동작 새 문법 스윕 현황표 (quick-260813-ivs)

수치 출처 = `evidence/sweep_verdict.json` + `evidence/measure.json` + ii0 `probes.log` 정본.
손 재유도 없음 — 파생 열은 표 하단 계산식으로만 유도.

전제 (판정 맥락):
- 렌더 = 무패치 운영 `app._run_gated_card_inherit` (fxx 배선 포함). 마크 튜닝·코드 수정 0.
- 기계 눈 = **machine_eye 스텁** (match 고정, Gemini 실호출 0, eyeStubCalls=6).
  ufb 08-11 실눈 스윕에서 기각됐던 2건(pdshapefault r01, peterpan r00)이 이번엔 방출됨 —
  카드 문법 판정 재료로만 볼 것 (눈 판정은 이 사이클 범위 밖).
- 게이트 미달 침묵 = **정직한 침묵 — 방출 0 은 결함이 아님** (사유 그대로 기록).

## 동작 x 관절(rid) 전수 — 방출/침묵

| 동작 | rid | criterion(관절) | src | freeze u/r (s) | 게이트/방출 판정 | 카드 실물 | 마크 문법 실측 (drawCalls/bake) | align 앵커 실적용 |
|---|---|---|---|---|---|---|---|---|
| elbow | r00 | angle_vs_reference__right_elbow | align | 11.111 / 12.07 | 생존 -> 방출 | `sweep_cards/elbow/zoom_angle_vs_reference__right_elbow.png` | V 미베이크 (`omitted:user_gate` — user rep12 스펙 미성립) -> 원 앵커 양패널 | O (shift 관측 — 크롭 중심·원 = align freeze 좌표) |
| elbow | r01 | angle_vs_reference__right_shoulder | align-w | 7.444 / 10.20 | 생존 -> **침묵**: `display_anchor drop side=user` (align conf 게이트 미달 — fail-closed 카드 미방출, 독립 재계산으로 실증) | 없음 | — | drop (user 측) |
| elbow | r03 | angle_vs_reference__right_knee | align | 10.111 / 11.60 | 생존 -> **침묵**: rep12 양측 신뢰 좌표 0 (memberPts 실측 u/r nValid=0, relaxed 만 — build 내 무로그 skip) | 없음 | — | 로그 성립, 실적용 전 단계서 침묵 |
| elbow | r02 | (left_hip) | align-peak | 11.133 / 11.80 | **dropped** `hold=hold pair=pose_far` (정직한 침묵) | 없음 | — | — |
| kipup | r00 | split_angle | align-peak | 1.467 / 2.00 | 생존(peak) -> 방출 | `sweep_cards/kipup/zoom_split_angle.png` | legs 문법 (`omitted:legs_owned` — 다리 사이각 렌더는 legs 카드 소유, 양패널 선 2 + 호) | N/A (비-angle criterion) |
| pdshapefault | r01 | angle_vs_reference__right_elbow | override | 1.222 / 0.80 | 생존 -> 방출 (**주의: 08-11 실눈 기각 이력** `extended->bent/arm` — 스텁이라 방출) | `sweep_cards/pdshapefault/zoom_angle_vs_reference__right_elbow.png` | **V 양패널 drawn** (drawCalls V,V) | O (shift 4건) |
| pdshapefault | r02 | angle_vs_reference__left_shoulder | align | 3.222 / 2.00 | 생존 -> 방출 | `sweep_cards/pdshapefault/zoom_angle_vs_reference__left_shoulder.png` | V 미베이크 (`omitted:ref_gate`) -> 원 앵커 양패널 | X (rep12 vertex 미성립 -> 종전 좌표 경로) |
| pdshapefault | r03 | angle_vs_reference__left_knee | align | 3.667 / 2.40 | 생존 -> 방출 | `sweep_cards/pdshapefault/zoom_angle_vs_reference__left_knee.png` | V 미베이크 (`omitted:ref_crop_relaxed`) -> user 원만, ref 무마크 | X (ref relaxed -> 종전 경로) |
| pdshapefault | r00 | angle_vs_reference__left_elbow | align-w | 8.556 / 9.40 | 생존 -> 방출 | `sweep_cards/pdshapefault/zoom_angle_vs_reference__left_elbow.png` | V 미베이크 (`omitted:ref_crop_relaxed`) -> user 원만, ref 무마크 | X (ref relaxed -> 종전 경로) |
| peterpan | r00 | angle_vs_reference__left_shoulder | align | 6.444 / 7.60 | 생존 -> 방출 (**주의: 08-11 실눈 기각 이력** `unclear/other` — 스텁이라 방출) | `sweep_cards/peterpan/zoom_angle_vs_reference__left_shoulder.png` | **V 양패널 drawn** (drawCalls V,V) | O (shift 4건) |
| powerspin | r02 | angle_vs_reference__left_shoulder | align | 3.222 / 5.73 | 생존 -> **침묵**: rep12 양측 신뢰 좌표 0 (memberPts 실측 u/r nValid=0 — build 내 무로그 skip) | 없음 | — | 로그 성립, 실적용 전 단계서 침묵 |
| powerspin | r00 | leg_extension | align-peak | 5.733 / 8.67 | 생존(peak) -> 방출 | `sweep_cards/powerspin/zoom_leg_extension.png` | `omitted:unmapped` (angle 대상 아님) -> 원 앵커 양패널 | N/A (비-angle criterion) |
| powerspin | r01 | — | — | — | **dropped** `no_freeze` (승인 렌더에 이 record 의 정지 없음) | 없음 | — | — |

집계: 방출 8 / 침묵 5 (drop 2 + display_anchor 1 + rep12 신뢰 0 x 2). survivors 의 @u/r 은
`freezeMatchViolations` 전부 빈 배열 — probes.log freeze 정본과 전건 일치 (순간 발명 0).

## 하이브리드(P3) 문법 관측

- `HYBRID_ANGLE_SUFFIXES = {"hip"}` (fxx 선언 데이터 실측 인용).
- 이 코퍼스에서 **hip criterion 카드 방출 0** -> `_draw_hybrid_joint_angle` 호출 0,
  `hybrid_fallback` 관측 0. **P3 하이브리드 실물은 이 승인 코퍼스 스윕에 없다** —
  유일한 실물은 fxx fresh doc(pdshapefault p34fresh) 왼골반 카드.
- 방출 카드의 V 실측 = 전부 기존 V (pdshapefault r01, peterpan r00 양패널).

## 부위/패널 비율 실측 (미세조정 판정 재료)

| 카드 | 패널 | crop kind | crop side px | 원본 프레임 (w x h) | 크롭/원본 % | 부위 스프레드 (패널 px) | 부위/패널 % | 사지선 64px / 부위 % |
|---|---|---|---|---|---|---|---|---|
| elbow right_elbow | user | valid | 864 | 2160x3840 | 40.0 | 미산출 (user rep12 스펙 미성립) | — | — |
| elbow right_elbow | ref | valid | 432 | 1080x1920 | 40.0 | 111.0 | 30.8 | 58 |
| kipup split_angle | user | valid | 1245 | 2160x3840 | 57.6 | (legs — 스펙 관측 대상 아님) | — | — |
| kipup split_angle | ref | valid | 615 | 1080x1920 | 56.9 | — | — | — |
| pdshapefault left_elbow | user | valid | 907 | 2160x3840 | 42.0 | (종전 경로 — 스펙 미관측) | — | — |
| pdshapefault left_elbow | ref | relaxed | 454 | 1080x1920 | 42.0 | — | — | — |
| pdshapefault left_knee | user | valid | 907 | 2160x3840 | 42.0 | — | — | — |
| pdshapefault left_knee | ref | relaxed | 454 | 1080x1920 | 42.0 | — | — | — |
| pdshapefault left_shoulder | user | valid | 907 | 2160x3840 | 42.0 | — | — | — |
| pdshapefault left_shoulder | ref | valid | 454 | 1080x1920 | 42.0 | — | — | — |
| pdshapefault right_elbow | user | valid | 966 | 2160x3840 | 44.7 | 172.8 | 48.0 | 37 |
| pdshapefault right_elbow | ref | valid | 483 | 1080x1920 | 44.7 | 181.1 | 50.3 | 35 |
| peterpan left_shoulder | user | valid | 198 | **360x640 (저해상 원본)** | 55.0 | 256.3 | **71.2** | 25 |
| peterpan left_shoulder | ref | valid | 594 | 1080x1920 | 55.0 | 203.5 | 56.5 | 31 |
| powerspin leg_extension | user | valid | 907 | 2160x3840 | 42.0 | — | — | — |
| powerspin leg_extension | ref | valid | 731 | 1080x1920 | **67.7** | — | — | — |

계산식 (1줄): 크롭/원본 % = crop side px ÷ min(원본 w,h) x 100 · 부위 스프레드 패널 px = spec 3점(실관절 정규화 좌표) 최대 쌍거리의 프레임 px ÷ crop side x 360 · 부위/패널 % = 같은 값 ÷ 3.60 · 사지선/부위 % = 64 ÷ 부위 스프레드 패널 px x 100 — 입력 전부 measure.json `crops`/`shifts(panelMetrics)`/`markConstants`.

관측 포인트 (수치 그대로):
- angle 카드는 crop 비율이 양패널 동일 (shared_frac 배선 — 40.0/42.0/44.7/55.0% 짝 일치).
- **powerspin leg_extension 만 비대칭** (user 42.0 vs ref 67.7%) — legs 카드는 shared_frac
  경로 밖 (종전 프레이밍 유지, fxx 적용 범위 L-10 명기 그대로).
- **peterpan user 원본이 360px 짧은 변** (합성 업로드 영상) -> 부위/패널 71.2% 로 유일하게
  밴드(ms2 목표 0.50, 밴드 0.40~0.55) 밖 + user 패널이 육안으로 흐릿.
- 마크 고정 px (markConstants): 사지선 64 / 몸통선 85 / 호 반경 16 / 쐐기 반경 151.2
  @ 패널 360px = 패널 대비 17.8 / 23.6 / 4.4 / 42.0%. 부위 대비는 위 표 (25~58% 산포 —
  부위 스프레드가 카드마다 달라 같은 64px 가 다르게 체감되는 근거 수치).

## 알려진 표기 한계 (이 사이클 무접촉 — 기존 유보 인용)

- 카드 좌하 초 표기가 freeze 실초보다 큼 (예: elbow r00 freeze u=11.111s ↔ 표기 12.3s) —
  fps 라벨 사슬(÷9.0 계열) 잔존, kpo 유보 3. 방출 판정 seam 은 freeze 정본이고 이번
  freeze-match 게이트가 전건 일치를 증명 — 표기만 별건.
