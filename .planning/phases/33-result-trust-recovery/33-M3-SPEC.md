---
status: LOCKED
plan: 33-19
blocks: 33-05
authority: .planning/debug/ref-student-substrate-gap.md (## 인계 — C+M3 실행 계획 · Task 3)
review_anchor: 33-REVIEWS.md codex concern 4 / suggestion 5
requirements: [D-02, D-18, D-20, D-27, D-29]
created: 2026-07-23
---

# 33-M3-SPEC — M3 정렬(`find_action_segment`) 수정 잠금 스펙

> **이 문서는 LOCKED 다.** 33-05(M3 코드)는 이 스펙을 **그대로** 구현하고 여기에 명시된
> 불변식을 RED 테스트로 고정한다. 구현 중 이 스펙에서 벗어나야 하면 **코드보다 먼저 이 문서를
> 다시 잠근다**(re-lock). 스펙 없는 M3 코드는 채점 누출(codex concern 4)을 막을 수 없다.

## 0. 왜 스펙이 먼저인가 (codex concern 4)

"채점 파일 무변경"은 **정렬 전용(alignment-only)을 증명하지 못한다.** 구간 선택(segment
selection)은 감점 산식이 그대로여도 감점의 **입력**을 바꾼다. 더 위험한 지점:

- `find_action_segment`(motiondtw.py:80-91)는 **사용자 `(start,end)` 하나만** 반환한다.
- `MotionMatch`(motiondtw.py:72-77)는 **reference range 를 담지 않는다.**
- 그래서 `motion_dtw`(motiondtw.py:94-100)는 `dtw(F_user[s:e], F_ref)` — **F_ref 를 통째로**
  소비한다.

SEED 의 처방 "`nu < nr` 일 때 기준(reference)을 학생 길이에 맞춰 창을 잡는다"는 **현행 API 로는
표현 불가능**하다 — reference range 를 운반할 자리가 없기 때문이다. 그리고 나이브한 best-match
reference window 는 **어려운 기준 국면(예: foxtop-split 의 split, 확장 구간)을 조용히 제거**해
점수를 **체계적으로 부풀린다**(inflation). 이것이 Core Value(점수 신뢰)를 가장 직접 건드리는
결함이라 코드보다 스펙을 먼저 잠근다.

이 스펙이 M3 코드를 **증명 가능하게 정렬 전용·비팽창**으로 만드는 계약이다.

---

## 1. API — paired user+reference range

### 1.1 `MotionMatch` 확장 (reference range 운반)

```python
@dataclass(frozen=True)
class MotionMatch:
    start: int          # 사용자 시퀀스 동작 구간 시작 (프레임, inclusive)
    end: int            # 사용자 끝 (exclusive)
    ref_start: int      # NEW — reference window 시작 (프레임, inclusive)
    ref_end: int        # NEW — reference window 끝 (exclusive)
    distance: float     # 정규화 DTW 거리
    path: list          # [(user_local_idx, ref_local_idx)...]
                        #   두 인덱스 모두 **윈도우 로컬**:
                        #   user_local ∈ [0, end-start), ref_local ∈ [0, ref_end-ref_start)
```

- **불변**: `path` 의 ref 인덱스는 `F_ref[ref_start:ref_end]` 로컬 0-base 다. reference 를
  통째로 쓰면(`ref_start=0, ref_end=nr`) 현행과 byte-identical.
- 현행 소비자는 `match.start/end` 만 참조 → **추가 필드는 하위호환**(기본 소비 경로 무변경).
  단 path 의 ref 인덱스를 쓰는 곳(per_joint_deviation·segments·표시 각도)은 **반드시**
  windowed reference 를 함께 넘겨야 한다(§5 ripple).

### 1.2 `find_action_segment` 새 시그니처 (paired ranges)

```python
def find_action_segment(
    F_user, F_ref, radius: int = 12
) -> tuple[tuple[int, int], tuple[int, int]]:
    """(사용자 (u_s, u_e), 기준 (r_s, r_e)) 를 함께 반환.

    짧은 쪽은 통째, 긴 쪽을 짧은 쪽 길이로 슬라이딩(양방향 대칭). 준비/대기 제거는
    긴 쪽에서 발생한다. 어느 쪽도 통째면 (0, n) 반환.
    """
```

- **반환 계약 (양방향 대칭 슬라이딩)** — `nu = len(F_user)`, `nr = len(F_ref)`:
  - `nu == nr` → `((0, nu), (0, nr))` (둘 다 통째).
  - `nu > nr` → **현행 유지**: 사용자를 `nr` 길이로 슬라이딩 → best `(u_s, u_s+nr)`,
    기준 통째 `(0, nr)`. (이미 발동하는 경로.)
  - `nu < nr` → **신규 경로(핵심 수정)**: 기준을 `nu` 길이로 슬라이딩 → best `(r_s, r_s+nu)`,
    사용자 통째 `(0, nu)`. **단 §2 coverage floor / §4 fail-closed 통과 시에만.**
- `motiondtw.py:83` 의 `if nu <= nr: return 0, nu`(기준 통째)가 12/12 무력화의 원인 —
  이 분기를 위 `nu < nr` 신규 경로로 대체한다.
- best window 선정 기준: **DTW 정규화 거리 최소** (현행 `find_action_segment` 와 동일한
  `dtw(...).distance` 지표, 새 지표 도입 금지). step 상한도 현행과 동일(`~60 윈도우`).

### 1.3 `motion_dtw` 소비

```python
(u_s, u_e), (r_s, r_e) = find_action_segment(F_user, F_ref, radius=radius)
dist, path = dtw(F_user[u_s:u_e], F_ref[r_s:r_e], radius=radius)
return MotionMatch(u_s, u_e, r_s, r_e, float(dist), path)
```

- `dtw` 는 **windowed 양쪽**을 받는다(`F_ref[r_s:r_e]`). path 는 자동으로 윈도우 로컬.

---

## 2. COVERAGE FLOOR (기준 국면 조용한 제거 금지)

reference window 는 **어려운 기준 국면을 조용히 떨어뜨릴 수 없다.** 두 겹의 바닥:

### 2.1 수치 바닥 — `COVERAGE_FLOOR = 0.80`

- 정의: 선택된 reference window 가 유지하는 기준 프레임 비율 = `(r_e - r_s) / nr`.
  `nu < nr` 경로에서 이 값은 정확히 `nu / nr` 다(윈도우 길이 = nu).
- **규칙**: `nu / nr < COVERAGE_FLOOR (0.80)` 이면 reference 를 **창으로 자르지 않는다** →
  §4 fail-closed(기준 통째 정렬)로 폴백.
- **근거 (SEED 밀도 실측)**: Task 1 재추출(기준 target-fps 9.0)로 밀도가 맞으면 유효 밀도비
  ≈ 1.0, `nu ≈ nr` 이 된다(SEED: 실효 밀도비 pre-Task1 = 10/15 = 0.667 → 재추출 후 ~1.0).
  이때 정당한 트리밍은 **준비/대기(head/tail buffer)뿐**이며 그 양은 클립의 소수다. 학생 클립이
  밀도 정합된 기준의 **80% 미만**이라면 그것은 준비/대기 트리밍이 아니라 **학생이 동작 내용을
  실제로 빠뜨린 것** — 이를 기준 창으로 숨기면 곧 점수 팽창이다. 그러므로 0.80 아래는 자르지
  않고 전체 기준에 정렬해 **누락이 편차로 드러나게** 한다. (0.80 = "≤20% 만 head+tail 준비로
  트리밍 허용"의 상한. tol 20°·slope 1.2 등 채점 상수와 무관한 **정렬 게이트 상수**다 — D-20/D-29
  채점 임계 재fit 아님.)

### 2.2 구조 바닥 — 공유 베이스 기술은 두 국면 모두 유지

- 대상: `sharedBaseMotionId` + `baseUntilS` 를 가진 reference(segments.py 소비 경로).
- `ref_boundary_frame`(segments.py:19-31)이 산출하는 **base/확장 경계**가 선택된 window
  `[r_s, r_e)` **내부에 엄격히** 있어야 한다: `r_s < boundary_full < r_e`.
  즉 window 는 base 국면과 확장 국면을 **각각 최소 1프레임 이상** 포함해야 한다.
- 경계가 window 밖(한 국면 통째 제거)이면 → §4 fail-closed(기준 통째). 이것이 codex 가
  지목한 "어려운 확장 국면 조용히 제거 → 점수 팽창" 공격을 직접 차단한다.

---

## 3. BOUNDARY — `nu < nr` / `nu ≈ nr` 규칙

- **`nu < nr` (창 트리밍 발동 조건)**: §2 두 바닥 모두 통과 시, 기준을 `nu` 길이 window 로
  슬라이딩해 min-DTW window `[r_s, r_s+nu)` 선택. 이것이 SEED 의 "준비/대기 제거"가 **실제로
  발동**하는 유일한 경로. window 는 **연속(contiguous) 구간**만 허용(내부 프레임 스킵 금지 →
  국면 건너뛰기 방지).
- **`nu ≈ nr` (Task 1 이후 지배적 케이스)**: `nu == nr` 이면 둘 다 통째. `nu` 가 `nr` 보다 1~수
  프레임 작으면 `nu < nr` 경로가 head/tail 에서 소량만 트리밍(정확히 준비/대기). coverage
  `nu/nr ≈ 0.97~1.0 ≥ floor` 이므로 발동. 이것이 SEED 성공판정 #5("M3 발동 확인")를 만족.
- **양방향 대칭**: `nu > nr` 은 사용자 트리밍(현행), `nu < nr` 은 기준 트리밍(신규). 두 경로는
  "긴 쪽을 짧은 쪽 길이로 min-DTW 슬라이딩, 짧은 쪽 통째"라는 **하나의 규칙**의 두 방향이다.
  동작 id 분기 없음(§6 I3).

---

## 4. FAIL-CLOSED — 모호하면 전체 기준 정렬

정렬이 모호하거나 바닥을 위반하면 **조용히 잘린 정렬을 쓰지 않고** 항상 **전체 기준
`(r_s=0, r_e=nr)`** 로 폴백한다(= 현행 동작 등가, 절대 팽창 불가). fail-closed 트리거:

1. **coverage floor 위반**: `nu / nr < 0.80` (§2.1).
2. **구조 바닥 위반**: 공유 베이스 기술에서 best window 가 base/확장 경계를 내부에 두지
   못함 (§2.2).
3. **모호(ambiguous) window**: best window 와, 그 거리에서 `AMBIGUITY_EPSILON` 이내인 다른
   후보 window 가 **실질적으로 다른 기준 프레임 집합**을 선택하는 경우 —
   두 window 프레임 집합의 Jaccard 겹침 `< AMBIGUITY_OVERLAP_MIN`.
   - `AMBIGUITY_EPSILON = 0.02` (정규화 DTW 거리 단위; 현행 distance 스케일 기준 근접 판정).
   - `AMBIGUITY_OVERLAP_MIN = 0.80` (겹침 80% 미만이면 어느 국면을 남길지 근-동률로 갈리는
     상태 → 임의 선택 금지).
   - 근거: 근-동률 후보가 서로 다른 국면을 남기면(예: 준비를 남기고 기술을 버릴지 그 반대)
     min-distance 의 임의 선택이 팽창 window 를 고를 수 있다. 이 경우 전체 기준으로 폴백.

> fail-closed 는 **항상 안전한 방향**(전체 기준 = 더 많은 편차 노출)으로만 폴백한다. 절대 잘린
> window 로 폴백하지 않는다(codex suggestion 5). fail-closed 발동은 팽창 아님 — 현행 동작 등가.

---

## 5. RIPPLE — 프로덕션 호출부 3곳 + 안전 플래그 의무

`motion_dtw` 프로덕션 호출부는 **3곳**(SEED 실측). 세 곳 모두 path 의 ref 인덱스를 쓰는
소비자에 **windowed reference `a_ref[ref_start:ref_end]`** 를 넘겨야 한다.

| 사이트 | 파일:행 | 역할 | M3 파급 의무 |
|---|---|---|---|
| S1 | `backend/functions/pipeline/app.py:1770` | mode1 채점 본류 + 표시 각도(동일 DTW path 재사용, :1746-1770) | `per_joint_deviation`·segments·**표시 각도** 모두 `a_ref[ref_start:ref_end]` 소비. 표시(현재/기준 각도)와 점수 source 통일 유지 |
| S2 | `backend/functions/pipeline/app.py:4015` | 공유 `_process` 코어 (Lambda/Pod 단일 경로) | `per_joint_deviation(match.path, user_seg, a_ref[match.ref_start:match.ref_end])`. segments 에 `ref_start` + windowed a_ref 전달 |
| S3 | `backend/shared/python/sunity_shared/analysis/safety_flags.py:245` | 안전 플래그 (의도적으로 같은 `motion_dtw` 재계산, D-07) | window 변경이 안전 정렬도 바꿈 → **안전 플래그 회귀 검증 동반 필수**(위양성/위음성 신규 0) |

### 5.1 segments.py 일관성 (ref 인덱스 공간)

- `per_joint_deviation`(motiondtw.py:103-130)은 path 의 `(u, r)` 로 `A_ref[r]` 를 참조한다.
  window 후 `r` 은 **window 로컬**이므로 반드시 `A_ref_win = A_ref[ref_start:ref_end]` 를
  넘겨야 한다(전체 A_ref 를 넘기면 인덱스 어긋남 → 조용한 오채점).
- `segment_scores`(segments.py:41-74)는 새 인자 `ref_start` 를 받고 `a_ref_win` 을 쓴다:
  - `boundary_full = ref_boundary_frame(clip, base_until_s, nr_full)` (전체 기준 길이로 산출).
  - `boundary_win = boundary_full - ref_start`.
  - `split_path_by_ref(path, boundary_win)` — path 가 window 로컬이므로 경계도 로컬로 시프트.
  - `0 < boundary_win < len(a_ref_win)` 아니면 `None`(현행 분할 무의미 처리 그대로). §2.2
    구조 바닥이 통과했으면 이 조건은 항상 만족 → 공유 베이스 분할 유효 유지.
- 시그니처 변경: `segment_scores(ref, base_motion_name, path, user_seg, a_ref_win, ref_start, nr_full)`.

---

## 6. INVARIANTS — 정렬 전용 증명 의무 (33-05 RED 테스트)

이 불변식들이 "M3 가 채점에 누출되면 걸리는 장치"(D-18)다. 전부 33-05 의 **RED 테스트**로
먼저 실패시키고 GREEN 으로 통과시킨다. 하나라도 못 만들면 M3 코드는 시작 불가.

- **I1 — zero-on-identity**: 동일 입력(`A_user == A_ref`) → `per_joint_deviation == 0`
  정확히. (DTW path 가 identity → 모든 `|Δ|=0`.) 기존 `test_per_joint_deviation_identical_sequences_zero`
  (test_motiondtw.py:66-77) **계속 green** + window 경로에서도 재확인.
- **I2 — byte-identical (already-aligned)**: 이미 정렬된 쌍(준비/대기 없음, `nu == nr` 이고
  min-distance window 가 전체 `[0, nr)`)에 대해 window 후 `per_joint_deviation` 이 M3 **이전**
  전체-기준 path 결과와 **byte-identical**(`np.array_equal`, 부동소수 비트 동일). 정렬이 바뀌지
  않아야 할 입력에서 출력이 바뀌지 않음을 증명.
- **I3 — no motion-key branches (D-02)**: window 선정 로직은 motion id/technique key 로
  **분기하지 않는다**. (a) 소스 검사: `motiondtw.py` window 선정에 `motion_id`/`technique`/동작
  이름 참조 0. (b) 행동 검사: 동일 수치 시퀀스에 라벨만 바꿔도 선택 window 동일. 특정 동작
  (파워스핀·킵업 등)에 맞춘 경로 금지 — 범위는 전역이다.
- **I4 — coverage floor 준수 (기준 국면 조용한 제거 0)**:
  - floor 테스트: `nu/nr < 0.80` 케이스 → resolver 가 전체 기준(`ref_start==0, ref_end==nr`)
    으로 폴백함을 assert.
  - 구조 테스트: 공유 베이스 기술에서 best window 가 경계를 밖에 두면 fail-closed 됨을 assert.
  - 발동 테스트: `nu < nr` 이고 바닥 통과 케이스 → `ref_start > 0` 또는 `ref_end < nr` (창이
    실제로 잘림)을 assert (SEED 성공판정 #5).
- **I5 — formula/constants hash-identical (D-20/D-29)**: `per_joint_deviation` 산식(median of
  `|Δ|`)과 채점 상수(`kismam.tol=20°`, `slope=1.2`, `cap=90`, `MEAN_EPSILON_DEG=0.1`,
  `P99_EPSILON_DEG=1.0`)가 **불변**. constants-hash 테스트로 산식 본문 + 상수 집합의 해시를
  고정 — 어떤 변경도 트립. M3 는 정렬 substrate 수정이지 감점 산식/임계 재fit 아님.

### 6.1 안전 플래그 회귀 (S3 파급)

- safety_flags no-FP/no-FN 회귀 테스트: window 변경 전후 fixture 안전 플래그 집합이 동일
  (신규 위양성/위음성 0). SEED 성공판정 #6.

---

## 7. 33-05 이 추가할 정확한 테스트 (RED 목록)

1. `test_m3_byte_identical_when_already_aligned` — I2.
2. `test_m3_zero_on_identity_through_window` — I1(window 경로).
3. `test_m3_coverage_floor_fallback` — `nu/nr < 0.80` → 전체 기준 폴백 (I4).
4. `test_m3_shared_base_structural_floor` — 경계 밖 window → fail-closed (I4·§2.2).
5. `test_m3_window_actually_fires` — `nu < nr` 바닥 통과 → `ref_start/ref_end` 트리밍 (I4·§3).
6. `test_m3_ambiguous_falls_back_full_reference` — 근-동률·다른 국면 → 전체 기준 (§4).
7. `test_m3_no_motion_key_branch` — 라벨 무관 동일 window (I3).
8. `test_m3_constants_hash_unchanged` — I5.
9. `test_m3_safety_flags_no_regression` — §6.1.
10. 기존 갱신: `test_motiondtw.py:35-42`(`test_segment_search_finds_embedded_motion`)·
    `:45-51`(`test_motion_dtw_trims_and_aligns`) 를 paired-range 반환에 맞춰 갱신
    (SEED Task 3: "기존 테스트가 현행 동작을 고정 → 함께 갱신").

---

## 8. 상수 요약 (이 스펙이 잠그는 정렬 게이트 상수 — 채점 상수 아님)

| 상수 | 값 | 역할 | 채점 임계 여부 |
|---|---|---|---|
| `COVERAGE_FLOOR` | **0.80** | `nu/nr` 이 미만이면 기준 미트리밍(전체 정렬) | 아님 (정렬 게이트) |
| `AMBIGUITY_EPSILON` | **0.02** | 근-동률 window 판정(정규화 DTW 거리) | 아님 |
| `AMBIGUITY_OVERLAP_MIN` | **0.80** | 근-동률 후보 프레임 집합 겹침 하한 | 아님 |

> **D-20/D-29 재확인**: 위 3상수는 **정렬 substrate 게이트**다. 감점 산식·`tol 20°`·`slope 1.2`·
> `cap 90`·`MEAN_EPSILON_DEG`·`P99_EPSILON_DEG` 는 **전부 불변(재fit 0)**. gate 가 걸리면 임계를
> 올리지 말고 원인을 조사한다(SEED 성공판정 #8).

---

## 9. LOCKED 선언

- 이 스펙은 **LOCKED**. 33-05 는 §1~§8 을 verbatim 구현하고 §7 테스트를 RED→GREEN 으로 만든다.
- 벗어남이 필요하면 **코드보다 먼저 이 문서를 re-lock** 한다(변경 이력 남김).
- 선행 의존: 33-05 는 Task 1(11종 재추출, 밀도 정합)·Task 2(다운스트림 백필) 완료 후에만
  착수(SEED Task 순서 불변). M3 를 먼저 고치면 기준이 여전히 조밀해 다른 국면으로 이동할 뿐.
