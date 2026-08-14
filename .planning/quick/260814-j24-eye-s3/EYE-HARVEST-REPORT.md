# 기계 눈 원장 → 학습 경로 개통 실측 리포트 (quick 260814-j24)

> 작성 2026-08-14. belle 지시 "학습으로 흘러들어가게 해내야 한다" 의 실행 결과.
> 이 문서의 모든 수치는 실행 산출물 파싱 실측이며 추정치가 아니다.
> **이번 사이클의 성립 증거 = 눈 원장 행이 변환된 학습 JSONL 실물 파일이 존재한다는 것**
> (`.planning/quick/260814-j24-eye-s3/assemble_out/jsonl/train.jsonl`, §5 에 원문 인용).

---

## 0. 한 줄 결론

눈 원장 157 + 운영 S3 48 = **205행을 스캔**해 content-hash 병합으로 **141행 원장**을 만들었고,
그중 **41행이 적재 허용(admit)**, **100행이 보류(hold)** 다. admit 41행 중 **29행이 트랙-눈
불일치**(keypoint 환각/마크 전위 라벨)이고, 균등·leakage 규율을 통과한 **7행이 실제 학습
JSONL 로 방출**됐다. 보류 100행은 전부 **user 측 크롭 가명처리(B-1) belle 결정 대기**다.

---

## 1. 규모 실측

### 1-1. 스캔 원천

| 원천 | 파일/원장 | entry | 크롭 해결 | 비고 |
|------|---------:|------:|----------|------|
| 리포 evidence (`.planning/**/[pod_]eye_ledger/`) | JSON 69 | 157 | **157/157** | PNG 미해결 0 |
| 운영 S3 `results/{uid}/{aid}/eye/ledger.json` | ledger 5 | 48 | **48/48** | 읽기 전용, 크롭 PNG 48 |
| **합계** | | **205** | | `observed=="error"` **0건** |

원장 JSON 3형태 전부 흡수 확인: `analysisId+entries` 8 · `flat` 8 · `flat+motion` 53.

**플래너 `<measured_facts>` 대조 — 전건 일치**(69 / 159 PNG / 157 entry / `observed=error` 0 /
`match=false` 95(user 64·ref 31) / side user 112·ref 45 / joint 40·36·26·24·13·13·5 /
claim 화살표 8종 / PNG 해결률 157-157). 어긋난 항목 **없음**.

> 단 하나 보강: 원장 디렉토리 매칭은 이름이 정확히 `eye_ledger` 인 것만으로는 부족했다.
> `260811-kpo/evidence/pod_eye_ledger`(40 entry)가 빠져 157 이 아니라 117 이 나온다.
> 수확기는 **이름에 `eye_ledger` 를 포함하는 디렉토리**를 훑는다(`iter_eye_ledger_dirs`).

### 1-2. 병합 후 원장 (`backend/training/data/eye_manifest.json`, 141행)

중복 64행은 **같은 크롭 바이트**다(멱등 키 = PNG content hash 16자). 실체는
ufb/xa1/fxx 사이클이 같은 2장을 각자 evidence 로 복사해 둔 것 + 운영 S3 크롭 48장 중
**47장이 리포 evidence 사본과 byte-동일**(S3 고유 생존 1행). 첫 등장 행이 남고 뒤는 skip
(append-only, 기존 행 무변형).

| 축 | 분포 |
|----|------|
| disposition | **admit 41 · hold 100** |
| disposition_reason | `internal_seed_ref` 41 · `customer_anonymize_required` 100 |
| side | user 100 · ref 41 |
| source_kind | repo_evidence 140 · s3_operational 1 |
| joint | left_hip 39 · right_elbow 31 · right_shoulder 24 · left_knee 20 · left_shoulder 12 · left_elbow 10 · right_knee 5 |
| observed | bent 67 · extended 54 · unclear 13 · off_body 7 |
| limb(눈이 본 사지) | arm 68 · leg 53 · other 15 · unclear 5 |
| claim→observed | bent→bent 51 · bent→extended 34 · extended→extended 20 · extended→bent 16 · bent→unclear 11 · extended→off_body 4 · bent→off_body 3 · extended→unclear 2 |
| **트랙-눈 불일치** | **90** (admit 29 / hold 61) |

### 1-3. admit 41행 (학습 적재 허용분)

| 축 | 분포 |
|----|------|
| motion | ref-pdshape 30 · ref-elbow-twist-sister 8 · ref-power-spin 2 · ref-peter-pan 1 |
| joint | right_elbow 10 · left_knee 8 · left_hip 7 · left_shoulder 6 · left_elbow 4 · right_shoulder 4 · right_knee 2 |
| observed | extended 18 · bent 16 · unclear 4 · off_body 3 |
| 불일치 | **29 / 41** |

### 1-4. JSONL 로 나간 행

| 항목 | 수 |
|------|---:|
| 원장 admit | 41 |
| val motion leakage 드롭 | 0 |
| 트랙 독립 균등(`_balance_media`) 트림 | **34** |
| **train.jsonl eye 행** | **7** (그중 불일치 **6**) |
| 함께 조립된 text 행 | 2 |

**41 → 7 의 뿌리는 코드가 아니라 motion 커버리지다.** 균등 규율은 `max ≤ 2×min` 인데
admit 의 motion 별 최소가 `ref-peter-pan` **1행**이라 상한이 2로 내려앉는다
(30·8·2·1 → 2·2·2·1). 손실은 은폐하지 않고 `_meta.eye_balance_trimmed=34` 로 방출한다.
처방 = 수확 범위 확대(동작별 눈 호출 균등), 코드 완화가 아니다.

---

## 2. 프라이버시 판정 P-1~P-5 (전문)

| ID | 대상 | 판정 | 근거 |
|----|------|------|------|
| **P-1** | user 측 크롭 | **hold — 적재 0** | LICENSE-AUDIT §7-1(c) "anonymize 강제 불변, 적재 전 강제, 소급 불가"(D-12). 얼굴 블러 미적용 크롭이므로 belle 결정(B-1) 전까지 적재 금지 |
| **P-2** | ref 측 크롭 | **admit** | LICENSE-AUDIT §5-1 internal seed 17행 = "자사 촬영 + 파일럿 참가 동의서(D-12 1겹)". `build_jsonl._is_customer_source("internal")` = False → D-12 가명처리 요건 비대상. 같은 정은지 영상 **통째**가 이미 `anonymized=false` 로 학습 소비 중(manifest rows[0]) → 그 크롭이 원본보다 엄격할 근거 없음 |
| **P-3** | 운영 S3 `results/{uid}/{aid}/eye/` | **hold — 적재 0, 원장 기록만** | LICENSE-AUDIT §7-1(d) 컷오프 2026-07-13 이후 문서는 `learningOptIn=true` 엄격. 눈 원장은 2026-08 생성 = 컷오프 이후. §3 동의 실측 결과 플래그 **부재** → fail-safe 보류 |
| **P-4** | 수확 행의 식별자 | **uid·analysisId 금지** | LICENSE-AUDIT 119행 "매니페스트에 uid·사용자 식별자 필드 금지(테스트 fence)" + §7-1(f) "uid/analysisId 비파생, video_hash 기반만". eye 행 식별자는 크롭 content hash 단독 |
| **P-5** | motion 미해결 행 | **hold** | motion 없는 샘플은 `_balance_media` 에서 무조건 통과(`m is None` → kept) = 균등 규율 우회 = dump-all. 제약 위반이므로 fail-closed |

**3중 박제**: 코드 fence(`harvest_eye.consent_disposition` + `assert_no_identifier_keys`,
테스트 52개) · LICENSE-AUDIT §7-3 · 이 리포트.

### P-4 실측 검증

`eye_manifest.json` 141행 전수:
- 금지 키(`uid`/`uidHash`/`analysisId`/`analysis_id`/`email`/`user_id`/`s3_key`/`key`) **0**
- Firebase uid 패턴(20자 이상 영숫자 혼합) 값 **0**
- 원문 문자열 검색: `fvcNXz` **0회** · `results/` **0회** · `p34fresh` **0회**

행 식별자는 `eye_id = media_sha16`(sha256 앞 16자) 단독이고, `source_ref` 는 리포 상대경로
또는 `s3-operational:{sha16}`(내용 파생)뿐이다.

---

## 3. 동의 실측 (Firestore 읽기 — 오케스트레이터 B-2 해제분)

플랜은 "이번 사이클 Firestore 무접촉이라 optIn 확인 불가"를 이유로 P-1/P-3 을 hold 했다.
오케스트레이터가 **읽기만** 해제해, 추정 대신 **측정**했다.

읽기 대상 = 눈 원장이 가리키는 분석 doc 전건(`users/{uid}/analyses/{aid}`, read-only).

| analysisId | 존재 | `learningOptIn` 필드 | 값 | createdAt(ms) | 컷오프(2026-07-13, 1783900800000) 대비 |
|---|---|---|---|---|---|
| p34fresh1786363530 | O | **부재** | null | 1786363530473 | 이후 |
| p34fresh1786433865 | O | **부재** | null | 1786433865845 | 이후 |
| p34fresh1786458292 | O | **부재** | null | 1786458292069 | 이후 |
| p34fresh1786593512 | O | **부재** | null | 1786593512030 | 이후 |
| p34fresh1786613939 | O | **부재** | null | 1786613939048 | 이후 |
| p34fresh1786628533 | O | **부재** | null | 1786628533389 | 이후 |

**측정 결과: 6/6 문서에서 `learningOptIn` 필드가 존재하지 않는다(false 도 아니고 부재).**
6/6 이 belle 일괄승인 컷오프 **이후** 생성이다.

`enumerate_internal.consent_allows` 계약(부재 + 컷오프 이후 = strict 제외)의 기계적 적용 →
**P-1/P-3 은 hold 로 확정**된다. "동의가 확인되지 않았다"가 아니라 **"동의 플래그가 없다는
것이 측정 결과"** 다. 각 행의 `consent_flag: null` 이 이 측정을 그대로 담고 있다.

부수 소득: 같은 읽기에서 `referenceMotionId` = **6/6 전건 `ref-pdshape`** 를 실측해,
motion 미해결(P-5) 행을 추정 없이 해소했다(§4).

- Firestore **쓰기 0**, S3 **쓰기 0**, 읽은 필드는 `status`/`learningOptIn`/`createdAt`/
  `mode`/`referenceMotionId` 뿐이며 결과는 리포에 저장하지 않았다(휘발 scratchpad).
- 동의 실측이 true 였다면? 코드는 그 경우도 준비돼 있다(`consent_disposition(..., consent=True)`
  → ref 측 S3 행은 `internal_seed_ref_optin_verified` 로 admit). 다만 **user 측 크롭은
  optIn=true 라도 hold** 다 — 동의와 가명처리는 다른 층이고 얼굴 블러(B-1)는 belle 미결이다.
  `learningOptIn=false` 는 어떤 조합에서도 무조건 제외(`consent_denied`, §7-1(b)).

---

## 4. motion 해결 — 추정 0, 근거 3종

| 대상 | 해결 방법 | 근거(원문 위치) |
|------|-----------|------------------|
| ehz 스윕형 53 파일 | entry `motion` 필드 + **어휘 정규화** | `quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS` — elbow→ref-elbow-twist-sister / kipup→ref-kip-up / pdshapefault→ref-pdshape / peterpan→ref-peter-pan / powerspin→ref-power-spin |
| kpo·ufb·xa1·fxx 원장(88행) | 원장 `analysisId` → Firestore `referenceMotionId` | §3 실측(6 doc 전건 `ref-pdshape`) |
| wif 발굴 원장(7행) | 사이클 자체 코드 상수 | `quick/260813-wif-knee-discovery/discover_knee.py:63 MOTION_ID="ref-pdshape"`, `:65 REF_VIDEO_KEY="reference/ref-pdshape.mp4"` |
| 잔여 2행 | **미해결 — 주입 안 함** | powerspin `ledger.json#0`(motion 필드·매핑 없음) + S3 1행. 둘 다 user 측이라 어차피 hold |

**어휘 정규화를 왜 했는가**: 하네스 이름(`pdshapefault`)을 그대로 두면 `build_jsonl` 의
val-motion leakage 대조가 manifest 어휘(`ref-pdshape`)와 영영 만나지 않아 **게이트가 장식**이
된다. 정규화는 추정이 아니라 위 표의 근거 문서를 코드로 옮긴 것이고, 각 행의
`motion_source` 에 근거 문자열이 그대로 박혀 있다(근거 없는 주입은 `resolve_motion` 이 거부).

**재현 명령**(수확은 이 4개 맵 파일 + 아래 명령으로 재현된다. 맵 원문은 §9 부록):

```bash
AWS_PROFILE=sunity-motion PYTHONPATH=backend/training \
backend/.venv/bin/python backend/training/datagen/harvest_eye.py --run --with-s3 \
  --motion-alias motion_alias.json --analysis-motion-map analysis_motion_map.json \
  --motion-map motion_map.json --consent-map consent_map.json
```

---

## 5. 학습 JSONL 실물 (직접 열어 확인)

경로 `.planning/quick/260814-j24-eye-s3/assemble_out/jsonl/train.jsonl` (9행 = eye 7 + text 2).
로컬 조립만 수행했고 **S3 업로드 0**(`uploaded: []`).

### 5-1. 첫 행 원문 (그대로 인용, 불일치 행이기도 하다)

```json
{"messages": [{"role": "system", "content": "당신은 폴스포츠 자세 분석의 검증자입니다. 주황색 원으로 표시된 관절 한 곳만 보고 그 관절이 접혔는지(bent) 펴졌는지(extended) 판정하고, 판정 불가면 unclear, 표시가 관절 위가 아니면 off_body 로 답합니다. 점수는 매기지 않습니다."}, {"role": "user", "content": [{"type": "image", "image": "s3://sunity-motion-pilot-videos/training/phase22/eye/a664e1ccff9ea702.png"}, {"type": "text", "text": "Eye_Task: {\"claim\": \"extended\", \"joint\": \"left_hip\", \"side\": \"ref\"}\n\n표시된 관절만 보고 다음 키를 갖는 JSON 만 출력하라: joint, limb, observed, reason, side, track_claim, track_claim_agrees. ..."}]}, {"role": "assistant", "content": "{\"joint\": \"left_hip\", \"limb\": \"arm\", \"observed\": \"extended\", \"reason\": \"주황색 원은 인물의 왼쪽 어깨 및 팔 부위를 가리키고 있으며, 이 팔은 곧게 펴져 있는 상태로 관찰됩니다.\", \"side\": \"ref\", \"track_claim\": \"extended\", \"track_claim_agrees\": false}"}], "_track": "eye", "_motion": "ref-pdshape", "_video_hash": null, "_has_faults": false, "_eye_agrees": false, "_eye_observed": "extended", "_media_pending_upload": true}
```

이 행이 왜 최고가치인가: **트랙은 "왼골반이 펴짐" 이라 주장했고 눈도 "펴짐" 이라고 했는데
`track_claim_agrees` 는 false 다.** 이유는 눈이 본 사지가 `arm` 이기 때문이다 — 마크가
골반이 아니라 **어깨/팔에 얹혀 있었다**. 상태만 보면 우연히 일치하지만 **다른 관절을 재고
있었던 것**이고, 이것이 belle 2026-08-11 지목한 keypoint 환각의 라벨된 실례다.

### 5-2. eye 7행 전량 (불일치 6 / 일치 1)

| 행 | motion | side | joint | limb | track_claim | observed | agrees |
|---|--------|------|-------|------|-------------|----------|--------|
| 1 | ref-pdshape | ref | left_hip | arm | extended | extended | **false** |
| 2 | ref-pdshape | ref | left_hip | leg | extended | bent | **false** |
| 3 | ref-elbow-twist-sister | ref | right_elbow | leg | extended | extended | **false** |
| 4 | ref-elbow-twist-sister | ref | right_elbow | leg | bent | extended | **false** |
| 5 | ref-peter-pan | ref | left_shoulder | arm | bent | extended | **false** |
| 6 | ref-power-spin | ref | left_shoulder | arm | bent | bent | true |
| 7 | ref-power-spin | ref | left_shoulder | other | bent | unclear | **false** |

1·3행은 상태가 같은데 사지가 어긋난 **마크 전위** 라벨, 2·4·5행은 상태가 뒤집힌 **환각**
라벨이다. 원장 전체에는 마크 전위 라벨이 **20행**(admit 5 / hold 15) 있다.

### 5-3. 불변식 확인

- assistant JSON 재귀 스캔에서 `score`/`severity`/`overall`/`points` 계열 키 **0**
  (`EYE_TASK_KEYS` 화이트리스트가 구조적으로 부재를 강제 — 테스트 fence).
- 사람 점수 라벨 **0** (눈 판정은 bent/extended/unclear/off_body enum 뿐).
- eye 샘플은 전부 `_video_hash: null` → val 미유입(train 전용), val.jsonl 은 0바이트.
- `hold` 행 유입 **0** (loader 층 + build 층 이중 fail-closed).

---

## 6. 고가치 표본의 소재 — B-1 의 실제 비용

플랜이 지목한 "트랙이 5~7도 극단 굽힘을 주장했는데 눈이 펴짐으로 뒤집은 행" 을
실측 추적했다(조건: `claim=bent` ∧ `observed=extended` ∧ `trackAngleDeg ≤ 10`).

| 행 | side | joint | trackAngleDeg | sec | 원천 | disposition |
|---|------|-------|--------------:|-----|------|-------------|
| 1 | user | right_shoulder | 3.4 | 11.0 | repo | **hold** |
| 2 | user | right_shoulder | 4.2 | 11.0 | repo | **hold** |
| 3 | user | right_shoulder | 4.2 | 11.0 | S3 | **hold** |
| 4 | user | left_hip | 5.0 | 9.067 | repo | **hold** |
| 5 | user | right_knee | 6.0 | 10.733 | repo | **hold** |
| 6 | user | left_hip | 6.8 | 12.6 | repo | **hold** |
| 7 | user | right_shoulder | 7.6 | 6.933 | repo | **hold** |
| 8 | user | right_shoulder | 7.6 | 6.933 | S3 | **hold** |

**8/8 전부 user 측 = 전부 hold.** 이 부류는 admit 에 단 한 건도 없다.
**이것이 B-1(user 크롭 가명처리) 미결의 구체적 비용이다** — 트랙이 사람 몸을 거의 접힌
것으로 오인한 가장 극단적인 순간의 라벨이 지금은 원장에만 있고 학습에는 못 간다.

정정 1건: 플랜/메모리는 이 부류를 "elbow 5건" 으로 기억했으나 실측 관절은
**right_shoulder 5 · left_hip 2 · right_knee 1** 이다(ehz 의 `elbow` 는 동작 doc 이름이지
관절이 아니다. 그 doc 안의 저각도 뒤집힘은 left_hip 5.0/6.8, right_knee 6.0 이다).
`elbow` **관절**의 저각도(≤10도) 행은 전부 `observed=bent` 또는 `off_body` 라 뒤집힘이 아니다.

부수 실측: `bent→extended` 뒤집힘 전체는 48행(admit 4 / hold 44),
`extended→bent` 는 22행(admit 15 / hold 7) — 즉 **뒤집힘 라벨의 대다수(44/48)가 user 측**이다.

---

## 7. belle 결정 대기 항목

| ID | 항목 | 결정하면 열리는 것 | 이번 사이클 상태 |
|----|------|-------------------|------------------|
| **B-1** | user 측 크롭 **100행**(불일치 61행 포함, §6 고가치 8건 전부 포함)을 얼굴 블러 가명처리해 살릴 것인가 | 학습 적재 41 → 최대 141(3.4배), 불일치 29 → 90 | **hold, 임의 진행 0**. 크롭은 관절 중심이라 얼굴 포함 사례 실측 존재(xa1 "원이 얼굴 둘러쌈"). 원장에 keypoint 좌표가 없어 크롭 단위 얼굴 위치를 모름 → 별도 검출 재추론 = **별건 사이클** |
| **B-2** | 운영 S3 수확분 동의 확인용 Firestore read | — | **오케스트레이터가 해제 → 실행 완료**(§3). 결과 = 플래그 6/6 부재 → hold 확정. 쓰기는 여전히 0 |
| **B-3** | ref 크롭에 정은지 얼굴이 포함될 수 있음(어깨/팔꿈치 크롭) | — | 기존 정책상 비대상(§5-1 internal seed)이나 **본인 관련이므로 통지**. admit 41행 중 어깨 크롭 10행(left_shoulder 6 · right_shoulder 4) |
| **B-4**(신규) | eye 균등 축을 motion 이 아니라 (joint × observed)로 볼 것인가 | 균등 트림 34 → 대폭 축소 | 이번 사이클은 기존 `_balance_media` 규율 그대로 적용(41→7). 규율 변경은 belle 승인 사항 |

---

## 8. 다음 사이클에 필요한 작업

1. **크롭 PNG S3 업로드** — admit 행의 `media_key = training/phase22/eye/{sha16}.png` 로
   업로드. 그전까지 `--upload` 는 fail-closed 로 차단된다(존재하지 않는 키를 가리키는
   학습셋을 canonical 로 올리지 않기 위한 의도된 정지, `_meta.eye_media_pending_upload > 0`).
   ★ 이 차단은 `run_retrain_cycle.sh assemble` 스테이지에도 걸린다 — 크롭 업로드 전에
   재학습 사이클을 돌리려면 `--with-eye` 를 빼고 실행해야 한다.
2. **수확 범위 확대** — motion 별 admit 최소가 1(ref-peter-pan)이라 균등 상한이 2로 내려앉는다.
   동작별 눈 호출을 고르게 쌓으면 7행 병목이 풀린다(코드 완화 아님).
3. **B-1 결정 시** — 얼굴 검출 재추론 → 크롭 블러 → 재수확(멱등이라 재실행 안전, 다만
   블러하면 바이트가 바뀌어 새 `eye_id` 가 생기므로 구 행의 supersede 규약 설계 필요).
4. **실 학습 사이클** — 위 1~2 이후 `run_retrain_cycle.sh assemble` 이 eye 트랙을 태운 채
   canonical 을 교체하고, 게이트/승격 래칫은 무변경으로 흐른다.

---

## 9. LLM 학습 영향 (필수 절)

- **이번 작업의 Gemini/LLM 실호출 0.** 눈 판정은 이미 쌓여 있던 원장을 읽었을 뿐이고,
  새로 모델을 부른 적이 없다. 과금 0.
- **학습 전송 0.** 어떤 데이터도 외부로 나가지 않았다. S3 쓰기 0, Firestore 쓰기 0.
  JSONL 은 리포 안 로컬 파일이며 canonical prefix 업로드는 fail-closed 로 막혀 있다.
- **다만 경로가 뚫렸다.** 이번 사이클 이후 `run_retrain_cycle.sh assemble` 은
  `--with-eye` 로 눈 원장을 학습 코퍼스에 태운다. 즉 **다음 사이클부터 기계 눈이 만든
  판정이 우리 모델의 학습 신호가 된다.** 무엇이 들어가는지는 위 §1-3/§5 가 전부다:
  ref 측 크롭 41행(현재 균등 통과 7행), 사람 점수 라벨 0, 점수 필드 구조적 부재.
- **학습 신호의 성격** — 이 트랙이 가르치는 것은 "각도 트랙의 주장이 그림과 맞는가" 다.
  불일치 라벨 29/41 이 실려 있어, 모델이 배우는 것은 정답 맞히기가 아니라 **파이프라인의
  오답을 지적하는 능력**이다. 반대로 오염 위험도 여기에 있다: 눈(Gemini) 자체가 틀린
  판정을 낸 행이 섞이면 그 오답도 같이 학습된다. 이번 원장은 belle 육안 검수를 거친
  사이클(kpo/ufb/xa1/wif/ehz)의 산출이지만 **행 단위 육안 인증은 아니다** — 규모가 커지면
  행 단위 검수 규약이 필요하다.

---

## 부록 A. 재현용 맵 원문 (scratchpad 휘발 대비 박제)

```json
// motion_alias.json — 하네스 이름 → manifest 어휘
{
  "elbow":        {"motion": "ref-elbow-twist-sister", "evidence": "quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS"},
  "kipup":        {"motion": "ref-kip-up",             "evidence": "quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS"},
  "pdshapefault": {"motion": "ref-pdshape",            "evidence": "quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS"},
  "peterpan":     {"motion": "ref-peter-pan",          "evidence": "quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS"},
  "powerspin":    {"motion": "ref-power-spin",         "evidence": "quick/260814-ehz-5/discover_sweep.py:73-84 SWEEP_JOBS"}
}
```

```json
// analysis_motion_map.json — analysisId → motion (Firestore 실측)
// 값은 7개 키 모두 {"motion": "ref-pdshape",
//   "evidence": "firestore:analyses.referenceMotionId (2026-08-14 read-only 실측, 6 doc 전건 ref-pdshape)"}
// 키: p34fresh1786363530 / 1786433865 / 1786458292 / 1786593512 / 1786613939 / 1786628533
//     + p34fresh1786628533-wif-cand02b (evidence 는 discover_knee.py:63 MOTION_ID)
```

```json
// motion_map.json — 디렉토리 단위
{
  ".planning/quick/260813-wif-knee-discovery/evidence/eye_ledger": {"motion": "ref-pdshape", "evidence": "quick/260813-wif-knee-discovery/discover_knee.py:63 MOTION_ID + :65 REF_VIDEO_KEY"}
}
```

```json
// consent_map.json — 동의 실측 결과(§3). 7개 키 전부 null = 플래그 부재.
```

## 부록 B. 게이트 실측

| 게이트 | 결과 |
|--------|------|
| pytest 전체 기준선 | **59 failed / 4289 passed / 26 skipped** — failed 수 기준선(59) 동일 |
| phase22 스위트 | 380 passed / 1 skipped (`test_build_jsonl.py` **무수정** 통과 = 무회귀 독립 증인) |
| 채점·운영 경로 | `backend/shared/python/sunity_shared/analysis` diff **0줄** |
| `manifest.json` 변경 지점 | 단일 hunk `@@ -52 +52,46 @@` = `_meta.collection_batches` 뿐. rows 239 무접촉 |
| 멱등 | `--run` 2회차 added **0** / skipped 205 / rows_after 141 |
| 식별자 fence | 141/141 통과, uid 패턴 값 0 |
| S3 | 읽기만(list_objects_v2 / get_object). 쓰기 API 호출 **0** |
| Firestore | 읽기 6 doc. 쓰기 **0** |
