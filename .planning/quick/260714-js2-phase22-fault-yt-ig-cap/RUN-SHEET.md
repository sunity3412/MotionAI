# RUN-SHEET — Phase 22 fault 타겟 재수집 라운드 (fault-yt-ig-260714)

> belle 승인 2026-07-14. 코드/레지스트리/문서 준비 = quick-260714-js2 완료분.
> **이 시트의 커맨드는 오케스트레이터(메인 세션)가 실행한다** — 과금(Gemini)·다운로드·
> S3 적재가 발생하므로 executor 플랜 범위 밖. 각 단계의 과금 지점과 중단 조건을 명시한다.

## 0. 환경 준비

```bash
export AWS_PROFILE=sunity-motion
export GEMINI_KEY_PARAM=/sunity/motion/gemini-api-key
source /path/to/scratch/ytvenv/bin/activate   # yt-dlp/gallery-dl venv (22-02 당시 scratch ytvenv)
cd /Users/kimtaesung/Dev/SunityMotion/backend
```

- **Gemini 크레딧 잔여 확인 선행** (고갈 이력 2026-06-20 — 잔여 부족 시 curate 가 unknown 폭증으로 조용히 무효화된다).
- PATH 에 ffmpeg 필요 (yt-dlp mp4 병합).

## 1. 안전 확인 (과금 0, 네트워크 0)

```bash
python3 scripts/collect_phase22_youtube.py --dry-run
python3 scripts/collect_phase22_instagram.py --dry-run
```

- 둘 다 exit 0 + 키 스킴 전부 `fixtures/phase22/` (uploads/ 0) 확인.
- YT dry-run 출력에 `yt_search_*` 5개 엔트리 + Tier-2 fault 채널 5개가 보여야 한다.

## 2. 신규 검색쿼리 실체 검증 (--curate 전 필수)

신규 검색 엔트리 5개(`yt_search_kr_common_mistakes` / `yt_search_kr_posture_correction` /
`yt_search_en_common_mistakes` / `yt_search_en_beginner_mistakes` / `yt_search_en_invert_mistakes`)는
후보 등재만 된 상태 — **실체 미검증**.

1. yt-dlp 로 각 검색어 dry 열거 (Gemini 미호출, 과금 0):
   ```bash
   yt-dlp --flat-playlist --skip-download --print "%(id)s | %(duration)s | %(title)s" \
     "ytsearch20:폴댄스 흔한 실수"
   # 나머지 4개 검색어 동일 반복
   ```
2. 제목 육안 스팟체크 — 교정형 튜토리얼("잘못된 예시" 시연 기대) 비중 확인. 무관 콘텐츠
   지배적이면 해당 엔트리는 --only 에서 제외(레지스트리 수정 불요, 실행 스킵으로 충분).
3. **belle 확인 후에만 3단계 진입.**

## 3. YT fault 재큐레이션 (--curate: Gemini 과금 발생, 다운로드 0)

**과금 지점**: 후보당 Gemini URL 판정 1회 (프로필 스코프 캐시 키 `{vid}::fault_demo` 라
22-02 캐시와 별개 — 재큐레이션 대상 채널은 전건 신규 과금으로 계산할 것).
`--max-candidates` 상한을 반드시 걸어 첫 배치 과금을 통제한다.

```bash
# 기존 Tier-2 fault 채널 5개 재큐레이션 (채널별 순차, 상한 필수)
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only BerryTV_FallInPole --max-candidates 40
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only PoleDanceLessonsPoleDream --max-candidates 40
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only PoleFreaks --max-candidates 40
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only becciedunnfitness --max-candidates 40
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only poleplace --max-candidates 40

# 신규 검색쿼리 엔트리 (2단계 통과분만)
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only yt_search_kr_common_mistakes --max-candidates 30
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only yt_search_kr_posture_correction --max-candidates 30
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only yt_search_en_common_mistakes --max-candidates 30
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only yt_search_en_beginner_mistakes --max-candidates 30
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --curate --only yt_search_en_invert_mistakes --max-candidates 30
```

- **중단 조건**: unknown 이 keep+reject 대비 지배적이면 즉시 중단 — 키/크레딧 문제
  (curate 가 unknown 을 캐시하지 않는 게 아니라 캐시하므로, 원인 해소 전 계속 돌리면
  unknown verdict 가 캐시에 박제된다. 크레딧 충전 후 캐시에서 해당 unknown 키 제거 필요).
- keep 집계를 belle 에게 보고 → **belle 확인 후 4단계 --collect.**

## 4. YT 다운로드 + S3 적재 (--collect: 다운로드·S3 발생, Gemini 재과금 0)

```bash
# curate 캐시의 keep verdict 만 소비 (재과금 0). 채널/엔트리별 동일 --only 로 순차.
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_youtube.py --collect --only BerryTV_FallInPole
# ... (3단계에서 keep 이 나온 채널/검색 엔트리 반복)
```

- manifest 행이 추가되며 `label_bucket=fault` (fault_demo 프로필 keep 은 bucket=fault 강제).
- 멱등: 기존 s3_key 는 skip.

## 5. IG eunji cap 상향 수집 (다운로드 + File API 과금 + S3)

**과금 지점**: 릴스당 Gemini File API 업로드+판정 1회 (URL 판정보다 라운드트립 큼 —
mode1 속도 실측에서 File API 가 최대 레버였던 그 경로).

```bash
PHASE22_BELLE_GREENLIGHT=1 python3 scripts/collect_phase22_instagram.py --collect --only eunji
```

- `cap_per_account: 60` 레지스트리 값이 CLI 기본 20 을 오버라이드 (커맨드 인자 불요).
- eunji 는 `curation_profile` 미부여 = default 프로필 (정타 위주 본인 릴스, cap 상향만).
- **중단 조건**: gallery-dl 로그인월/rate-limit 로 다운로드 0 건이면 중단 후 belle 상의
  (쿠키 인증 재설정 등 — 무리한 재시도 금지, IG ToS 회색).

## 6. 사후 처리

1. 집계 확인:
   ```bash
   python3 -c "
   import json; m=json.load(open('training/data/manifest.json'))
   rows=m['rows']; print('rows', len(rows))
   from collections import Counter
   print(Counter(r['label_bucket'] for r in rows))
   "
   ```
2. `LICENSE-AUDIT.md §7-2 (e)` 에 실측 수치 기입 + §5 원장 갱신.
3. `manifest _meta.recollection_rounds[0].status` 를 `"open"` → `"collected"` 로 갱신.
4. 게이트 확인: `python3 -m pytest tests/phase22/ -q` GREEN (균등 게이트는 fault 행 증가
   방향에서 waiver subset 조건 자동 충족 — 위반이 줄어드는 방향).
5. 커밋 (`data(quick-...)` 또는 후속 라운드 스코프로).

## 부록 — 이 라운드의 불변 게이트

- `PHASE22_BELLE_GREENLIGHT=1` 없이 --curate/--collect 실행 차단 (exit 2).
- uploads/ prefix 금지 (assert_non_notified, HIGH 1).
- 점수/severity verdict 필드 영구 부재 (normalize 화이트리스트 + 테스트 fence).
- 미성년 제외 (@polesportkids enabled=false), anonymize 정책 무변경.
- 정은지 성공/실패 페어 6쌍(eval18) 학습 투입 영구 금지 — 이 라운드 수집 경로와 무관.
