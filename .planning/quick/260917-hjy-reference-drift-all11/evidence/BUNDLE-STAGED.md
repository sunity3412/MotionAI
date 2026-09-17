# 묶음 완료 — 승격·플래그 둘 다 반영됨 (2026-09-17)

belle 승인: *"묶음(회전 켜기 + 기준 6편 재추출) 진행."*

**승격 완료.** `reference/_release.activeCandidate = rot180_v1`, `start_server.sh` 의
`ROT180_INVERSION_ENABLED = 1`. 둘 다 반영됐다. 아래 §5 가 최종 검증이다.

---

## 1. 한 것

Pod `40wfzz7k225a6q` (RTX PRO 4500 Blackwell, ORT-gpu 1.19.2, `ROT180_INVERSION_ENABLED=1`).

| 단계 | 도구 | 결과 |
|---|---|---|
| 재처리 | `reprocess_reference_motions_phase4.py --version rot180_v1 --no-flip` | 11/11 → `reference/{id}/versions/rot180_v1` |
| 파생 백필 | `backfill_reference_downstream.py --reference-version rot180_v1 --write-candidate` | 11/11 (meanAngles·techniqueProfile·bodyNormalizationProfile·forceDirectionPattern·bodyComparisonSourcePose·keypointReport·captureViews) |
| 라이브 확인 | 11편 top-level `angles`/`pipelineVersion` 재read | **전원 무변화** |

- 프레임 수가 저장본과 전부 일치(120/931/329/426/485/260/118/237/130/159/298) — 샘플링 재현.
- 백필 무결성 게이트(candidate vs live 재추론): **meanAngleDelta 0.0025° · p99 0.005°**.
  회전을 켠 두 독립 추론이 그만큼만 어긋난다 = 회전 결정론 확증.

## 2. 점수 검증 (새 버전 실물로)

로컬 채점 seam(파이프라인 코드 직접 호출)으로 `versions/rot180_v1` 을 먹여 재채점:

| 학생 / 기준 | angle | 초과 관절 | 원감점 | 점수 |
|---|---|---|---|---|
| belle pdshape / 현행 라이브 | 38 | 7 | −62.4 | **60** |
| belle pdshape / **rot180_v1** | **87** | 2 | −13.4 | **87** |
| 정은지 자기비교 / 현행 라이브 | 41 | 6 | −57.4 | **60** |
| 정은지 자기비교 / **rot180_v1** | **100** | 0 | 0.0 | **100** |

09-17 예측(86~88)을 실물 버전이 재현했다. 대조군(현행 라이브)은 저장된 저장값과 일치.

## 3. ★ 도중에 잡은 구조적 결함 — Firestore 1MB 한도

`ref-combo`(931프레임) 백필이 **1,085,164 bytes > 1,048,576** 으로 실패했다.

원인은 **같은 보고서를 두 번 저장**하는 것이었다:

```
백필 E-2 가 keypointReport 를 만들고 referenceKeypointReport = dict(같은 것) 로 복사
  → 실측: 두 필드가 완전히 동일 (ref-pdshape / ref-kip-up 확인, `==` True)
  → ref-combo 기준 332KB 가 두 벌
```

그런데 `referenceKeypointReport` 는 `firestore_admin._REFERENCE_CONSUMER_FIELDS` 에
**없다** — candidate 에서는 아무도 안 읽는다. 유일한 소비처는 33-07 flip 의 top-level
미러링이다.

**수리(2건, 같은 커밋):**
- `backfill_reference_downstream.py` — 두 값이 같으면 candidate 에 중복 저장 안 한다
  (다르면 종전대로).
- `reprocess_reference_motions_phase4.py` — flip 이 `referenceKeypointReport` 를 못 찾으면
  candidate 의 `keypointReport` 로 폴백(로그 남김). 이 폴백이 없으면 낡은 top-level
  보고서가 새 angles 와 남아 33-07 타임베이스 어긋남이 재발한다.

수리 후 ref-combo 백필 성공. 게이트 `pytest 4827 passed / 0 failed`.

> 부수 사실: **라이브 top-level `ref-combo` 는 이미 1013KB 로 한도의 99%** 다
> (joints3d 370KB + referenceKeypointReport 332KB + keypointReport 245KB).
> 지금은 라이브의 `keypointReport` 가 옛 v1.0/8관절이라 간신히 맞는 것이고,
> 새 파이프라인은 둘 다 v1.1/12관절이라 중복을 지우지 않으면 못 들어간다.
> **콤보보다 긴 기준 모션을 추가하면 이 한도에 다시 걸린다.**

## 4. 남은 한 단계 — 승격

```bash
FIREBASE_SA_PATH=firebase-sa.json \
  backend/.venv/bin/python backend/scripts/promote_reference_version.py --version rot180_v1
```

dry-run 확인 완료 — `candidate 11/11 완비`, 현재 포인터 `None`.

그 스크립트는 `reprocess_reference_motions_phase4._flip_active_pointer` 를 그대로 호출한다
(로직 재구현 0): pre_phase4 백업 → activeVersion → top-level 미러 → `_release.activeCandidate`
→ post-write verify(11/11 + content hash).

### ★ 승격과 플래그는 반드시 같이 간다

| 조합 | 결과 |
|---|---|
| 포인터만 flip (플래그 0) | 학생 미교정 vs 기준 교정 → **비대칭, 지금보다 나쁨** |
| 플래그만 1 (포인터 None) | 학생 교정 vs 기준 미교정 → **정은지 60점 문제 그대로** |
| **둘 다** | 60 → 87 / 자기비교 100 |

그래서 이 커밋은 **`start_server.sh` 의 `ROT180_INVERSION_ENABLED` 를 0 그대로 둔다.**
승격 write 가 되는 시점에 같이 1 로 올린다.

**롤백**: `reference/_release.activeCandidate` 를 `None`/이전 값으로 되돌리면 즉시 원복.
top-level 원본은 `reference/{id}/versions/pre_phase4` 에 백업된다(flip 이 최초 1회 저장).


---

## 5. 승격 실행 + 최종 검증

```
post-write verify PASS — 11/11 activeVersion='rot180_v1' + per-doc hash + 전역 포인터 일치
reference/_release.activeCandidate = 'rot180_v1'
start_server.sh:24  ROT180_INVERSION_ENABLED = 1
```

### 5-1. 승격 중에 같은 1MB 벽을 한 번 더 맞았다 (top-level 미러)

candidate 는 고쳤는데 **top-level 미러**가 또 걸렸다(1,082,424 bytes). 미러가
`keypointReport`(v1.1 332KB)와 `referenceKeypointReport`(v1.1 332KB)를 **둘 다** 쓰는데
새 파이프라인에선 두 값이 같기 때문이다.

이때 ref-climb 한 편만 미러된 **부분 상태**가 생겼다(포인터는 아직 None 이라 해석 경로는
불변). 실물로 확인하고 수리 후 재실행했다.

**수리 원칙** — 두 필드의 성격이 다르다:

| 필드 | consumer 필드? | top-level 필요? |
|---|---|---|
| `referenceKeypointReport` | **아니오** | **필수** — resolver 가 안 덮어준다 |
| `keypointReport` | 예 | 불필요 — 포인터가 서면 candidate 에서 overlay |

`keypointReport` 의 유일한 소비처 `_reference_angles_fps`(`pipeline/app.py:7000`)도
resolver 를 거친 `ref` 를 읽는다. 앱은 `angles`/`meanAngles` 만 읽고 두 보고서를 안 읽는다.
→ **두 값이 같으면 top-level 미러에서 `keypointReport` 를 생략**한다(다르면 종전대로).

### 5-2. 실제 해석 경로 검증 (`firestore_admin.get_reference_motion`)

```
get_reference_motion('ref-pdshape') → pipelineVersion=rot180_v1 activeVersion=rot180_v1
  anglesFrames=237
  referenceKeypointReport v=1.1 frames=237   (top-level 미러)
  keypointReport          v=1.1 frames=237   (candidate overlay — 미러 생략이 옳았다는 증거)
```

11편 전수: `pipelineVersion`·`anglesFrames`·두 보고서 frames·`joints3d` 가 **11/11 정합**
(120/931/329/426/485/260/118/237/130/159/298 — 각도·보고서·좌표가 같은 프레임 공간).

### 5-3. 최종 점수 (승격된 라이브 기준으로 재채점)

| 학생 | angle | 초과 관절 | 원감점 | **점수** |
|---|---|---|---|---|
| belle pdshape (회전ON) | **87** | 1 | −13.3 | **87** |
| 정은지 자기비교 (회전ON) | **100** | 0 | 0.0 | **100** |

승격 전 60 / 60 에서 올라왔고, 스테이징 단계 예측(87 / 100)과 일치한다.

## 6. 롤백 (한 묶음으로)

```bash
# (1) 기준 포인터
#     reference/_release.activeCandidate 를 삭제하거나 이전 값으로
# (2) 엔진 플래그
#     start_server.sh:24  ROT180_INVERSION_ENABLED=0
```

**한쪽만 되돌리면 안 된다** — 비대칭 비교가 되어 승격 전보다 나빠진다.
top-level 원본은 `reference/{id}/versions/pre_phase4` 에 있다(flip 이 최초 1회 저장, 11/11 확인).
