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

## §2. 공부 (주기 재학습 배치 루프)

§1 이 쌓은 `collection_batch` 신규분을 belle 주 1회 트리거로 몰아서 학습으로 전환한다:
라벨(신규분만 과금) → 병합 조립(perturb 포함) → SFT → D-15 게이트 → **통과 시만 승격
(단방향 래칫)**. 전부 기존 자산 orchestration — 신규 코드는 러너 셸
(`training/sft/run_retrain_cycle.sh`) + 승격 래칫(`training/sft/promotion.py`) 뿐이다.

게이트 FAIL 이 기본 상태여도(v4~v6 이력) 데이터는 계속 쌓이고, 통과하는 라운드에서만
모델이 전진한다 — "쌓기(§1)"와 "공부(§2)"의 분리를 운영으로 완성한다.

### 2.1 전제 조건 체크리스트 (실행 전 확인)

- [ ] **진행 중 학습 없음.** v7 등 SFT/서빙이 돌고 있지 않은지 belle 이 먼저 확인한다
      (러너 preflight 의 `pgrep` serial lock 이 이중 방어하지만 — 파이프라인 동시성
      비안전이라 중첩은 오염이다).
- [ ] **Pod 기동.** belle 이 콘솔에서 Pod 를 start 한다(생명주기 = belle, 실행 = Claude
      SSH). 접속은 프록시 `ssh.runpod.io` (-tt + stdin 파이프). **Pod 재생성 시 SSH
      엔드포인트/포트가 바뀌므로** 재생성했다면 새 접속 정보를 확인한다.
- [ ] **신규 배치 존재.** §1 watch 수집이 1배치 이상 쌓였는지 `manifest.json` 의
      `_meta.collection_batches[]` 로 확인한다(신규 없으면 label stage 는 전부 skip = 과금 0,
      학습만 재실행되어 낭비 — 신규분이 있을 때만 사이클을 돈다).
- [ ] **Gemini 크레딧 확인.** 예상 과금 = 신규 행 수 × 2콜(교사 1 + judge 1). 신규 행 수는
      `collection_batches[].new_rows` 합으로 어림한다. 크레딧 부족 시 label 이 중간에
      429 로 중단된다(재개는 안전 — 아래 2.3).

### 2.2 belle 트리거 (1커맨드, 박제)

`cd /workspace/SunityMotion/backend` 에서:

```bash
PHASE22_BELLE_GREENLIGHT=1 nohup bash training/sft/run_retrain_cycle.sh all \
  > /workspace/cycle_$(date -u +%y%m%d).log 2>&1 &
```

`PHASE22_BELLE_GREENLIGHT=1` 이 없으면 preflight 가 SystemExit(2)로 차단한다(라벨 stage
Gemini 과금 = belle 승인). 러너는 preflight → label → assemble → train → gates → promote 를
**전부 순차** 실행한다(병렬 없음 — 동시성 비안전).

### 2.3 stage 재시작 (중단 시)

개별 stage 를 지정해 이어서 돌린다:

```bash
bash training/sft/run_retrain_cycle.sh [preflight|label|assemble|train|gates|promote]
```

- **label 은 재실행 안전** — full_batch 가 행별 결과 파일로 영속화하므로 이미 라벨링한
  행은 skip 되어 **재과금 0** (429 로 끊겼어도 그대로 이어서 신규분만 처리).
- assemble 이후는 각 stage 를 순서대로 개별 실행할 수 있다(예: 학습만 다시:
  `... train` → `... gates` → `... promote`).

### 2.4 flashinfer env 박제 (Blackwell 게이트 오탐 우회)

Blackwell(sm_120, compute cap >= 12) Pod 의 게이트 vLLM 이 flashinfer 샘플러 오탐으로
죽는다(2026-07-16 실증). 러너의 gates stage 가 `nvidia-smi` 로 compute cap 을 판별해
compute cap >= 12 에서만 자동 적용한다:

```bash
export VLLM_USE_FLASHINFER_SAMPLER=0
export TORCH_CUDA_ARCH_LIST=12.0
```

**주의: `TORCH_CUDA_ARCH_LIST=12.0` 은 sm_120 전용이다.** A100(sm_80) 등 비-Blackwell Pod
에서는 러너가 자동으로 설정하지 않는다(강제하면 학습/서빙이 깨진다 — 수동 export 금지).

### 2.5 래칫 해석 (게이트 판정 → 승격)

- **게이트 FAIL = 실패 아님.** 데이터는 쌓였고 모델만 미승격이다. 러너는 FAIL 에서도
  exit 0 로 정상 종료하며 마지막 줄에 `NOT PROMOTED — 기존 모델 유지` 를 명시한다.
- **current 의 진실은 `training/sft/promotion_ledger.json` 이다.** 게이트 PASS
  (`assert_gates --require-pass` exit 0)만 `current` 포인터를 전진시킨다(단방향 래칫).
  FAIL 로그는 다음 처방(데이터 믹스·교사 밀도·용량)의 근거일 뿐, current 를 오염시키지
  않는다. FAIL entry 는 원장에 attempt 로만 기록된다.
- **PASS 시** current 가 전진하고, 이것이 Wave 3(22-08 서빙 swap) 진입 조건이 된다.

### 2.6 종료 절차

1. cycle report 확인: `/workspace/cycle_reports/cycle_<ts>.json` (2.7).
2. 원장·매니페스트 변경 커밋: `promotion_ledger.json` (승격 시 current 갱신) +
   manifest(라벨 결과) 를 **git commit + push** (Pod 작업 = push 한 단위).
3. belle 콘솔에서 Pod **stop** — 과금 차단(Claude 는 API 키 없어 stop 불가, belle 몫).

### 2.7 비용 관측치 읽는 법

promote stage 가 `/workspace/cycle_reports/cycle_<ts>.json` 을 방출한다(은폐 금지):

| 필드 | 의미 |
|------|------|
| `new_labeled` | 이번 사이클 신규 라벨링 행 수(기존 행 skip 제외) |
| `accepted` | 4중 필터 수락 수 |
| `rejected_judge` / `rejected_parse` / `rejected_contract` | reject 분해 |
| `est_gemini_calls` | 추정 Gemini 호출 = `new_labeled × 2` (교사 + judge) |
| `sft_wall_seconds` | SFT 학습 wall time(초) |
| `gates` | 게이트 판정(PASS/FAIL — 사람/judge 점수 수치는 저장 안 함, 객관성 gate) |
| `promoted` | current 전진 여부(true = PASS 승격) |

가이드: **`est_gemini_calls` 가 예상 밖으로 크면** label stage 를 중단하고(Ctrl-C 또는
Pod 콘솔) belle 이 신규 배치 규모·크레딧을 확인한 뒤 재개한다. new_labeled=0 인데 사이클을
돌렸다면 신규 수집이 없었다는 뜻(§1 을 먼저 돌려 배치를 쌓아야 함).

### 2.8 최종 리허설 (플랜 종료 상태 확인)

로컬(과금·Pod 0)에서 플랜 산출이 살아있는지 일괄 확인:

```bash
cd backend
python3 -m pytest tests/phase22 -q                       # 전 스위트 무회귀
bash -n training/sft/run_retrain_cycle.sh                # 러너 문법
python3 -m pytest tests/phase22/test_promotion.py -q     # 래칫 로직
python3 -c "import json; l=json.load(open('training/sft/promotion_ledger.json')); \
  assert l['current'] is None and l['entries']==[]; print('ledger init OK')"
```
