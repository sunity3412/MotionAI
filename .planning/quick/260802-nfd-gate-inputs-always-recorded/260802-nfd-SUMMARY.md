# quick-260802-nfd — 저신뢰 귀속 게이트 입력 상시 기록

**한 줄**: `attributionReliability` 마커를 `unreliable` 값과 무관하게 항상 `result` 에 실어,
안 걸린 케이스의 게이트 입력(visibility/dtwDistance/overTolJointCount/geminiSilent)을
관측 가능하게 만들었다. 임계값·강등 동작·점수는 전부 무접촉.

**커밋**: `d12825b0` (단일 원자 커밋, 5 files / +205 −17)
**착수 base**: `7062484a`

---

## 1. 무엇을 바꿨나

| 파일 | 변경 |
|------|------|
| `backend/functions/pipeline/app.py` | 부착 조건(`_attr_marker.get("unreliable")`) 제거. 부착 로직을 `_attach_attribution_marker(result, seed_audit)` 로 추출 — 인라인이라 단위 테스트 seam 이 없었다. `_assess_attribution_reliability` **무변경**. |
| `backend/tests/test_attribution_reliability_marker.py` | 부착 seam 테스트 6건 추가 (아래 §5). |
| `app/src/types/analysis.ts` | `AttributionReliability` / `AnalysisResult.attributionReliability` 주석 갱신 — "unreliable=True 일 때만 실림", "역립 저신뢰에서만 방출" 전제 제거. |
| `app/src/lib/userAnalyses.ts` | `normalizeAttributionReliability` 주석의 "부재(정상 doc)=undefined" 전제 갱신. **코드 무변경** (§3 참조). |
| `docs/contract.md` | §4 `AnalysisResult` 필드 표에 1행 추가 + `attributionReliability` 전용 절 신설 (종전 미기재). |

**앱 코드는 한 줄도 안 고쳤다.** 주석만 갱신했다 — 이유는 §2.

---

## 2. 앱 게이트가 엄격 비교인지 — 소스로 확인한 결과

**결과: 엄격 비교다.** 그래서 앱은 안 고쳐도 된다.

`app/src/app/analysis/result.tsx:1076` 을 열어 읽었다:

```ts
const attributionUnreliable = result.attributionReliability?.unreliable === true;
```

`=== true` 엄격 비교. `unreliable: false` 가 실려도 `attributionUnreliable` 은 `false`.

그리고 **강등 표면 전부가 이 단일 boolean 하나만 소비한다**는 것도 확인했다 —
`grep -n "attributionUnreliable" result.tsx` 로 소비처 32곳을 전수 확인했고, 그중
`attributionReliability` 객체를 직접 다시 읽는 곳은 3곳뿐이다:

| 위치 | 코드 | 안전 근거 |
|------|------|-----------|
| `result.tsx:1076` | `?.unreliable === true` | 엄격 비교 — false 통과 |
| `result.tsx:2284` | `?.aggregateStatement ?? FALLBACK` | 삼항 `attributionUnreliable ? {...} : summaryContent.todayFix` 안쪽 — false 면 도달 불가 |
| `result.tsx:2780` | `?.aggregateStatement ?? FALLBACK` | `aggregateMode={attributionUnreliable}` 와 쌍. `ScoreBreakdownSection.tsx:105` `{aggregateMode ? <Text>{aggregateText}</Text> : ...}` — false 면 미렌더 |

**필드 존재(`!= null`, truthy 객체 검사)로 분기하는 소비처는 0건.** 이것이 이 변경의 안전 근거다.

---

## 3. 강등 동작 무변경 근거

소비처 3곳을 전부 소스로 열어 확인했다. 셋 다 `unreliable` **값**으로만 분기한다.

1. **앱 화면** — `result.tsx:1076` `=== true`. §2 참조. `false` → 강등 게이트 전부 off.
2. **백엔드 팁 재조립** — `backend/shared/python/sunity_shared/analysis/assemble.py:817-819`:
   ```python
   attr = result.get("attributionReliability")
   if isinstance(attr, dict) and attr.get("unreliable"):
       return result   # per-joint 팁 재조립 skip
   ```
   truthy 검사지만 `_assess_attribution_reliability` 가 `unreliable` 을 항상 Python `bool` 로
   넣으므로 `False` → falsy → **early return 안 함** → 기존 per-joint 팁 재조립 경로 그대로.
   (truthy 검사라 `unreliable` 이 `None`/누락이어도 falsy — 하위호환 유지.)
3. **앱 정규화** — `userAnalyses.ts:346-363`:
   ```ts
   if (typeof a.unreliable !== 'boolean' || typeof a.geminiSilent !== 'boolean')
     return undefined;
   ```
   `false` 는 `typeof === 'boolean'` 통과 → 정규화 객체가 **온전히 반환**된다.
   `visibility`/`dtwDistance` 는 `normalizeFiniteNumber(...) ?? null` 이라 `null`(미측정)도 보존,
   `overTolJointCount` 는 `?? 0`. **코드 수정 불필요 — 읽어서 확인했다.**

**`aggregateStatement` 누출 없음**: `_assess_attribution_reliability` 는 `if unreliable:` 안에서만
이 키를 넣는다. 그 함수를 안 건드렸으므로 reliable 마커에는 이 키가 없다. 이 불변식은
추론이 아니라 테스트로 잠갔다 (`test_reliable_marker_carries_no_aggregate_statement`).

**점수 무접촉**: `_attach_attribution_marker` 는 `result["attributionReliability"]` 한 키만 쓴다.
`overallScore` / `deductionBreakdown` 은 읽지도 쓰지도 않는다. 테스트로 스냅샷 대조
(`test_attach_does_not_touch_score_surface`).

---

## 4. 계약 미러 — 몇 곳을 고쳤나

**3곳 중 3곳 확인, 2곳 수정 + 1곳 신설.**

| 미러 | 상태 | 조치 |
|------|------|------|
| `app/src/types/analysis.ts` | "unreliable=True 일 때만 실림 — reliable/부재 doc 은 byte-동일" 로 **틀린 전제 명시** | 수정. 함께 stale line-number 참조(`2282-2324`, `5696-5702` — 실제는 2286-2328, 6024-6030)를 심볼명 인용으로 교체 |
| `docs/contract.md` | `grep -rni attribution docs/` → **0건. 종전 미기재** | §4 필드 표 1행 + 전용 절 신설 (발화 3-조건, 점수 무접촉, 소비 규칙, Firestore flat 정합, lockstep) |
| `backend/shared/python/sunity_shared/models.py` | `grep -n attribution models.py` → **0건. 이 필드 상수를 보유한 적 없음** | 대상 아님 — 미수정. status enum 이 아니라 상수 테이블이 불필요하다 (`timingsMs` 선례: contract.md §4 가 "models.py 상수 불필요" 라고 이미 박제). 이 사이클에서 새로 넣는 것은 스코프 밖. |

---

## 5. 추가한 테스트 (6건)

`backend/tests/test_attribution_reliability_marker.py` 말미. 전부 mock 순수 — Pod/Gemini/S3/Firestore 호출 0.

| 테스트 | 잠그는 불변식 |
|--------|---------------|
| `test_reliable_marker_is_attached_with_gate_inputs` | ① 미발화(over-tol 3)에서도 마커가 `result` 에 실리고 게이트 입력 4종이 관측 가능 |
| `test_reliable_marker_carries_no_aggregate_statement` | ② reliable 마커에 강등 문구 부재 |
| `test_attach_does_not_touch_score_surface` | ③ `overallScore`/`deductionBreakdown` 부착 전후 byte-불변 (reliable/unreliable 양쪽) |
| `test_unreliable_attach_still_carries_aggregate_statement` | 대조군 — 발화 케이스는 종전대로 문구 동반 |
| `test_attach_is_noop_when_marker_absent` | 마커 미산출(레거시 경로) → 필드 미생성, 하위호환 |
| `test_marker_is_flat_scalars_only` | Firestore 중첩 배열 금지 — 전 값 스칼라/None |

---

## 6. 검증 — 돌린 값

### pytest (돌렸다)

```
기준선 (base 7062484a):  59 failed, 3801 passed, 27 skipped, 42 warnings in 41.77s
변경 후 (HEAD d12825b0): 59 failed, 3807 passed, 27 skipped, 42 warnings in 38.06s
```

실패 **집합** diff (node ID 정렬 후 `diff`):

```
$ diff baseline-failures.txt final-failures.txt ; echo "DIFF_EXIT=$?"
DIFF_EXIT=0
```

→ **실패 59건 집합 동일, 신규 실패 0, 회복 0.** passed +6 = 신규 테스트 6건.

명령 (브리프의 `cd backend` 수집 중단 함정 회피 — 절대경로 사용):
```
PYTHONPATH=<wt>/backend/tests /Users/kimtaesung/Dev/SunityMotion/backend/.venv/bin/python \
  -m pytest -q <wt>/backend/tests
```

> **기준선 불일치 1건 (미조사)**: 브리프의 2026-08-02 기준선은 `59 failed / 3802 passed`,
> 내가 base `7062484a` 에서 실측한 값은 `59 failed / **3801** passed`. passed 1건 차이.
> 원인을 안 팠다 — 브리프 기준선의 측정 커밋이 main tip(`080aec1c`)일 가능성이 크지만
> **확인 안 했다.** 실패 집합이 동일하고 diff 가 0이라 이 사이클 판정에는 영향 없다고 봤다.

### tsc (돌렸다)

```
tsc --noEmit --project app/tsconfig.json → exit 0, 에러 0
```

> 워크트리에 `app/node_modules` 가 없어서(gitignore 대상) 메인 저장소 `node_modules` 를
> 심볼릭 링크로 붙여 실행한 뒤 제거했다. 커밋에 안 들어갔다 (`git status` 클린 확인).

### git diff (봤다)

`git diff 7062484a` 로 전체 diff 를 눈으로 읽었다. 부수 오염 1건 잡았다 —
`.planning/spikes/001-dataset-eval-harness/__pycache__/*.pyc` **2개가 git 추적 대상**이라
pytest 실행이 이들을 수정했다. 파일 단위 `git checkout -- <경로>` 로 각각 복원했고
커밋에 포함되지 않았다 (`git diff --diff-filter=D HEAD~1 HEAD` → 삭제 0).

---

## 7. 적용 범위 (읽어서 확인한 사실)

부착 지점은 `_process` 의 `vision_fault_context is not None` 분기 안이다. 레거시 폴백 분기
(`else`, 6041~)는 `seed_audit` 자체가 없어 종전대로 마커가 부재하다 — 그 경로는 게이트 입력을
산출하지도 않으므로 정상이다.

→ **이번 변경으로 게이트 입력이 남는 모집단 = vision 컨텍스트를 산출하는 mode1 분석.**
브리프 실측에서 `motionAlignment.distance` 보유가 925건 중 186건이었던 것과 같은 계열의 경계다.

**백필 없음.** 기존 907건의 doc 은 여전히 visibility 기록이 없다. 이 변경은 **앞으로 생기는
분석**부터 적용된다.

---

## 8. 안 본 것 (검증 안 한 것 — 확인하지 마시고 그대로 읽으세요)

- **실기기/시뮬레이터 렌더 확인 안 했다.** 앱 코드는 한 줄도 안 고쳤고(주석만) tsc 0 이지만,
  "reliable 마커가 실린 doc 을 앱이 강등 없이 그린다"를 **화면으로 본 적 없다.** §2 의 근거는
  전부 소스 독해다.
- **실 doc 재산출 안 했다.** Pod/GPU/Gemini 호출 0 이 하드 제약이었으므로, 실제 분석을 돌려
  Firestore doc 에 `attributionReliability: {unreliable:false, ...}` 가 실제로 찍히는 것을
  **조회해서 본 적 없다.** 파이프라인 단위 테스트로만 잠갔다.
- **기존 907건 doc 재산출/백필 안 했다.** 계획에도 없다 (§7).
- **임계값 재조정 판단 안 했다.** 이 사이클은 재는 것까지다. DTW 임계 60 이 관측 분포
  90%tile 위에 앉아 있다는 브리프의 지적은 **다음 사이클의 입력**이지 이번 결론이 아니다.
- **브리프의 925건 전수 실측 수치(발화 18건/1.9%, elbow-twist 17건, DTW 90%tile 60.4 등)는
  내가 잰 것이 아니다.** 오케스트레이터가 준 값을 코드 주석·커밋 메시지에 인용했을 뿐,
  Firestore 를 직접 조회해 재확인하지 않았다.
- **pytest 기준선 1건 차이(3801 vs 3802) 원인 미조사** (§6).
- **배포 안 했다.** SAM 배포·Pod 재기동·OTA 발행 전부 미수행. 백엔드 변경이므로 실제
  효과를 보려면 Lambda/Pod 배포가 필요하다.

---

## 9. Self-Check

- `backend/functions/pipeline/app.py` `_attach_attribution_marker` — 존재 확인 (diff 로 읽음)
- `backend/tests/test_attribution_reliability_marker.py` 신규 6건 — 25 passed 로 실행 확인
- `docs/contract.md` `attributionReliability` 절 — diff 로 확인
- 커밋 `d12825b0` — `git rev-parse --short HEAD` 로 확인
- 작업 트리 클린 (`git status --short` 무출력, pyc 오염 복원 완료)

**Self-Check: PASSED**
