# Deferred items — quick-260730-l7t (33-G §C-1)

이 플랜의 변경이 **원인이 아닌** 발견분. SCOPE BOUNDARY 규칙에 따라 고치지 않고 기록만 한다.

---

## D-1 (신규 발견, blocking 후보) — S10 다리 사이각이 12관절 doc 에서 조용히 생략된다

**증상.** `split_angle`(legs) 카드에서 골반→양다리 선 + 사이각 호가 그려지지 않고 원 마커로
폴백한다. 33-G 표는 S10 을 **PASS** 로 적어 두었는데, 그 판정은 코드 존재
(`_draw_leg_angle`/`_draw_side_leg_angle`)만 확인한 것이고 12관절 doc 실측이 아니었다.

**근본원인 (실측 확정, quick-260730-l7t 스위프).**

| 요소 | 값 | 소유 |
|---|---|---|
| `REGION_MEMBERS["legs"]` | `(left_hip, right_hip, left_knee, right_knee)` — **ankle 미포함** | 32-14 이전 8관절 정의 |
| legs crop 박스 | 멤버(hips+knees) bbox × `_BBOX_MARGIN` → `(73, 247, 219)` | `_side_crop._box_for` |
| `_leg_line_pts` 다리 끝 | **ankle 우선**, 저신뢰/부재 시 knee 폴백 | `_leg_line_pts` |
| 실측 | `left_end` out=(78.8, **465.1**) / `right_end` out=(282.4, **486.1**), 허용 상한 = `_OUT + 36 = 396` | `_pt_in_crop` |

즉 **crop 멤버 집합(ankle 없음)과 드로잉 점 집합(ankle 우선)이 어긋난다.** 32-14(D-22 1단)로
keypointReport 가 12관절이 되면서 `_leg_line_pts` 가 ankle 을 잡기 시작했지만
`REGION_MEMBERS` 는 8관절 시절 정의로 남아, 벌림이 큰 스플릿일수록 ankle 이 crop 밖으로
나가 `_pt_in_crop` 게이트가 탈락한다. 8관절 doc(ankle 부재)에서는 knee 폴백이라 crop 안에
들어와 그려졌다 — 그래서 기존 테스트/fixture(8관절 합성)는 GREEN 이고 회귀로 안 잡혔다.

**이 플랜이 원인이 아닌 근거.**
- `REGION_MEMBERS` · `_leg_line_pts` · `_box_for` · `_pt_in_crop` · `_crop_box` · `_render_crop`
  전부 **무수정**.
- legacy/advisory/mode3 9케이스 PNG 해시 **변경 0** (`legacy_baseline.json` match: true).
- split/다관절 카드는 정중앙 crop 경로에서 **제외**했다(L-10) — 프레이밍이 종전과 동일.

**수리 후보 (별 플랜).** 둘 중 하나 — 어느 쪽도 이 플랜의 승인 범위 밖이다.
1. `REGION_MEMBERS["legs"]` 에 ankle 추가 → crop 이 발끝까지 담는다. 단 crop 이 넓어져
   "부위 확대" 성격이 약해지고 32-03 parity 수치가 이동한다 (승인 목업 대조 필요).
2. `_leg_line_pts` 의 다리 끝 선택을 **그 카드 crop 에 들어오는 관절**로 제한(ankle →
   crop 밖이면 knee 폴백). crop 배율 불변, 선은 정강이까지만 그려진다.

**33-G 표 반영.** S10 을 무조건 PASS 로 남기지 않고 "12관절 doc 미검증" 단서를 붙였다
(§C-4 Pod 재스위프에서 실 doc 로 판정).

---

## D-2 (환경, 이 플랜 무관) — `backend/tests` 전체 실행 시 58 FAILED + 12 collection ERROR

`python3 -m pytest backend/tests -q` 는 리포 루트에서 **collection ERROR 2건**
(`test_pole_detector.py` / `test_rtmw_133_to_coco17_adapter.py` — `No module named 'fixtures'`),
`backend/` 에서 실행하면 12건이 된다. `PYTHONPATH=backend/tests` 를 주면 수집은 되고
**58 FAILED** 가 남는다.

**전부 pre-existing.** 작업 시작 커밋(`6ff667a`)을 throwaway worktree 에 체크아웃해 같은
커맨드를 돌린 결과 FAILED/ERROR **node ID 80줄 중 FAILED/ERROR 58건이 완전 동일**(diff 0):

```
baseline(6ff667a): 58 failed, 3706 passed, 27 skipped
HEAD(this plan)  : 58 failed, 3726 passed, 26 skipped
FAILED/ERROR node ID diff = IDENTICAL → 회귀 0
```

skipped 27→26 차이는 `phase32/test_inversion_warp.py:120` 이 로컬 spike 산출물
(`.planning/spikes/004-*/kpts/`, untracked)의 존재 여부로 skip 을 결정하기 때문 — worktree 에는
그 untracked 파일이 없어 skip 됐고 메인 트리에서는 실행되어 통과했다. 이 플랜 무관.

`fixtures` import 실패는 `backend/tests/__init__.py` 유무에 따른 pytest rootdir/sys.path
삽입 문제로, 별도 정리 대상.
