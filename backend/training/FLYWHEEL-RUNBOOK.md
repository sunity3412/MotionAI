# Phase 22 데이터 플라이휠 운영 런북

> 목적: v7 SFT 성패와 무관하게 "스포츠 모션 분석의 힉스필드"를 만들기 위해 데이터를
> 계속 쌓는(연속 수집) 운영 절차를 박제한다. belle 확정 2026-07-16.

이 런북은 belle 이 문서만 보고 주기 수집을 반복 실행할 수 있도록 하는 단일 절차서다.
§1(쌓기)은 수집+큐레이션(저비용)만 다룬다. RTMW/교사 라벨링(공부 배치)은 §2(22-12)가 소유한다.

---

## §1. 쌓기 (연속 수집)

수집+큐레이션만 = 저비용(RTMW/Gemini 교사 증류 없음, 다운로드-전 Gemini 선별 게이트만).
22-02 수집기(collect_phase22_youtube.py / collect_phase22_instagram.py, D-09)를
재발명 없이 재사용한다. YT 폴 채널 + 정은지 IG(eunji.poledancer, cap 60)를 belle
트리거 1커맨드로 주기 수집한다.

### 1.1 belle 트리거 기본 절차 (1커맨드)

```bash
PHASE22_BELLE_GREENLIGHT=1 AWS_PROFILE=sunity-motion python3 backend/scripts/phase22_watch.py --run
```

**사전 조건 체크리스트 (실행 전 확인):**

- [ ] 로컬 venv 에 `yt-dlp` / `gallery-dl` 기설치 (신규 pip 설치 불요 — 22-02 재사용).
- [ ] Gemini 키 = SSM `/sunity/motion/gemini-api-key` (AWS_PROFILE=sunity-motion 로 조회).
- [ ] Gemini 크레딧 잔여 확인 (선별 게이트가 과금 — 고갈 시 verdict 전부 unknown → skip).
- [ ] AWS 자격 = sunity-motion (S3 `fixtures/phase22/` 쓰기 — Motion AI 전용, EC2 무관).

**과금 게이트:** `PHASE22_BELLE_GREENLIGHT=1` 이 없으면 `--run` 은 SystemExit(2)로 차단된다
(belle 승인 = 과금 승인). 이 게이트는 무인 스케줄에서도 유지한다(§1.4).

**멱등 (재과금 0):** verdict 캐시 + 매니페스트 s3_key 집합으로 기존 수집분은 재-curate·
재다운로드 없이 skip 된다. 즉 매주 실행해도 신규 영상만 과금·적재된다.

### 1.2 실행 전 무과금 확인 (dry-run)

```bash
python3 backend/scripts/phase22_watch.py --dry-run
```

watch 대상 채널/계정 목록 + 배치 원장 불변식 self-check + 하위 수집기 dry-run 위임을
네트워크·과금 0 으로 수행한다. 실 수집 전 대상·필터가 살아있는지 확인하는 용도.

### 1.3 스코프 제한 (파일럿 옵션)

- 특정 계정만: `--only eunji` (채널/계정명 부분일치).
- 채널당 상한: `--limit-per-channel 20`.
- IG 계정 cap: `--cap-per-account 60`.
- 전체 gate 상한(과금 안전장치): `--max-candidates 30`.

정은지 IG 만 주기 수집하려면:

```bash
PHASE22_BELLE_GREENLIGHT=1 AWS_PROFILE=sunity-motion \
  python3 backend/scripts/phase22_watch.py --run --only eunji
```

### 1.4 주기 권장 + 스케줄 옵션

**권장 주기: 주 1회.** 정은지 IG 하루 ~1영상 페이스 → 주당 ~7후보 + YT 신규 업로드.

스케줄 자동화 예시(launchd/cron) — **단, 무인 과금 금지:** 스케줄에서도
`PHASE22_BELLE_GREENLIGHT` 게이트를 유지하고, 무인 실행을 켤 때는 belle 이 명시적으로
env 를 스케줄 정의에 넣어 승인한 것으로 간주한다(env 부재 = 실행 자체가 SystemExit 2로
중단). 즉 스케줄 등록 = 과금 승인의 지속 위임이며, 크레딧 소진·레지스트리 오염 감시는
belle 몫이다.

cron 예시(매주 월 09:00, belle 이 env 를 명시 승인해 넣은 경우만):

```cron
0 9 * * 1 cd /path/to/SunityMotion && PHASE22_BELLE_GREENLIGHT=1 AWS_PROFILE=sunity-motion python3 backend/scripts/phase22_watch.py --run >> backend/training/data/watch_reports/cron.log 2>&1
```

기본은 belle 수동 트리거(§1.1)를 권장한다 — 크레딧/레지스트리 상태를 매 실행 전에
사람이 확인하는 편이 안전하다.

### 1.5 리포트 읽는 법

매 실행 말미에 stdout 요약 + `backend/training/data/watch_reports/{batch_id}.json`
이중 기록(은폐 금지, T-22-11-05):

| 필드 | 의미 |
|------|------|
| `batch_id` | `watch-YYMMDD` (같은 날 2회차부터 `-2`,`-3`) |
| `new_rows` | 이번 실행 신규 수집 행 수 |
| `new_by_source` | 신규 분해 (youtube / instagram) |
| `new_by_bucket` | 신규 분해 (정타 / fault) |
| `curated_reject` | 큐레이션 reject 수 |
| `skipped_existing` | 기존 수집분 skip 수(멱등 증거) |
| `cumulative_rows_after` | 실행 후 누적 training 행 수 |

가이드: **reject 급증 = 레지스트리 필터 점검** (discipline/duration/series 필터가
정상 영상을 과잉 배제하는지, curation_profile 이 맞는지 확인). skip 만 있고 new_rows=0 =
신규 업로드 없음(정상). new_by_bucket 이 fault=0 지속 = fault 표본은 내부 트랙(§1.6)이
소유(공개 YT/IG 는 정타 편중이 예측된 귀결).

### 1.6 동의·라이선스 경계 (D-12 / D-09)

- 수집분 usage = `training-only-no-redistribution` (앱 미노출·재배포 없음, Mode1 reference 와 별개).
- IG 는 **공개 릴스만** 로그인/쿠키 미사용으로 접근(gallery-dl). 로그인 요구 시 계정
  skip — **쿠키 도입 금지**(T-22-11-06). 얼굴 픽셀 학습 불필요(포즈/모션만).
- 신규 채널 등재는 **belle 승인 후** `phase22_sources.yaml` 형식 준수(필수 키:
  name/channel_url/platform/tier/bucket/notes). 옵트아웃은 entry 에 `watch: false`.
- **동의 3겹(D-12):** (1) 파일럿 = 학원 참가 동의서 1장에 학습 활용 포함(오프라인 포괄) —
  파일럿 내부 영상은 학습동의 필수, (2) 정식 = 가명처리(얼굴 블러+식별자 제거) 후 학습,
  (3) 출시 전 법률 검토 1회 문서화.
- **내부(고객) 영상은 이 러너 스코프 밖.** 내부 fault 트랙은 anonymize 경로
  (22-04 customer_track: enumerate_internal → anonymize_batch, `learningOptIn=false` 제외 +
  가명처리 강제)로만 등재된다. 이 watch 러너는 공개 YT/IG 만 수집한다.

### 1.7 배치 원장 규약

- `_meta.collection_batches[]` = 초기 라운드 마감 이후 증분 등재 원장(append-only).
  각 배치 = `{batch_id, opened_at, approved_by:belle, trigger, sources, new_rows,
  curated_reject, skipped_existing, status, cumulative_rows_after}`.
- `_meta.collection_complete=true` 의 의미 = "131행 초기 수집 라운드 마감" 보존
  (build_jsonl DR-06 게이트의 소유 플래그 — watch 증분이 이 플래그를 건드리지 않는다).
  배치 등재는 assert_ledger_invariants 가 실행마다 append-only + 마감 무결성을 강제한다.
- 신규 watch 수집 행에는 `collection_batch=batch_id` 필드가 붙는다 — **22-12(공부 배치)가
  이 필드로 신규분을 식별**해 라벨링 대상 배치를 소비한다. 기존 131행 마감분은 이 필드
  부재로 구분된다.

---

## §2. 공부 (라벨링 배치 루프)

> 22-12 가 추가한다(RTMW 추출 + 교사 증류 + JSONL 조립). §1 이 생산한
> `collection_batch` 신규분을 입력 배치로 소비. (헤더 예약 — 본문은 22-12.)
