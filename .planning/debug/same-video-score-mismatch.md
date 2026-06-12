---
status: resolved
trigger: |
  belle UAT (TestFlight Build 15+ / talkv 영상). 새로 업데이트한 영상들이 "같은 영상" 과 비교함에도 불구하고 점수가 만점을 못 따라감.
  - DTW 는 이미 적용되어 있음 (motion_dtw line 1274). 단순 frame index 매칭 아님.
  - 검증 결과 "angle 차이=59" 가 실제로는 **angle dimension score = 59 점** 였음.
created: 2026-06-12
updated: 2026-06-12
slug: same-video-score-mismatch
---

# Debug Session: same-video-score-mismatch

## Symptoms

- **expected**: 같은 talkv 영상을 동일 reference(정은지) 와 비교 시 angle dim score 만점 근접.
- **actual**: dimensionScores.angle = 58~59 (8 joint KISMAM 평균). overall = 70~76. ref-climb 분석은 같은 영상으로 angle = 95.
- **errors**: 명시적 에러 없음. 수치 이상.
- **reproduction**: 동일 talkv 파일 (`_talkv_dJMcaL4ZHKA_yX7uPsCsGTncpdNrFlHTk1_talkv_high.mp4`) 을 ref-elbow-twist-sister 로 3회 분석 → 모두 angle=58~59. ref-climb 로는 angle=95.

## Hypotheses Tracked

1. ~~REJECTED~~ RTMW 해상도 민감도. 같은 fileName 의 3회 분석 중 2회는 bit-identical (49e8a05b ≡ 9e27196a).
2. ~~REJECTED~~ talkv 영상이 거울상 / 다른 cut. fileName 동일, frame 175 (마지막) 각도 거의 완벽 일치.
3. ~~REJECTED~~ Phase 17 angle 통합 codepath 회귀. 같은 ref-climb 영상이 score 95 → codepath 자체는 정상.
4. ~~REJECTED~~ stability TOL 25°→15° 롤백 영향. TOL 은 stability 차원만, angle 무관.
5. **CONFIRMED** RTMW noise floor on inverted/occluded poses. elbow-twist 양쪽 영상 모두 per-frame median |Δt,t+1| = 6~13°, p99 = 35~50°. climb 는 1.7~6° / 17~30°. inverted = noise 가 climb 의 2~3x.
6. **CONFIRMED** `per_joint_deviation` mean-of-|frame-by-frame-Δ| 메트릭이 noise 에 lossy. mean angles 가 5° 안에 있어도 noise 가 deviation = 20° 를 만든다.

## Evidence

(주요 증거 박제 — 전체 데이터: `app/scripts/_debug_same_video_score{2,3,4,5}.mjs` 출력)

- `c71acb81e8aa47138a0d124df83f9d47` mode1/ref-elbow-twist-sister overall=76 dim={angle:59, stability:92}
- `9e27196a961a4150ad914108c015b828` overall=70 dim={angle:58, stability:81} — **fileName 동일**
- `49e8a05b51b24087ac8cb543cc33b59e` overall=70 dim={angle:58, stability:81} — **fileName 동일, angles bit-identical with 9e27196a**
- ref-climb 분석 `92a24536…` `7d42c38c…` overall=90 dim={line:83, angle:95, stability:93}
- 8-joint KISMAM scores (c71acb81): 48/53/57/59/57/62/66/67 → 역산 deviation = 17.9~24.2° (tol=20°)
- 8-joint signed_delta (mean): -4.9, -3.0, +6.8, +10.4, +1.7, +3.0, -1.2, +10.5 → **모든 관절 mean angle 차이는 5~10° 수준**
- talkv (elbow-twist) intra-sequence median |Δt,t+1|: 10.5, 12.8, 6.8, 13.5, 12.6, 9.1, 13.3, 5.0°
- reference (elbow-twist-sister) intra-sequence median |Δt,t+1|: 11.8, 13.0, 7.5, 10.4, 11.1, 12.5, 10.5, 7.0° — **정은지 reference 도 동일하게 jitter**
- talkv-climb intra-sequence median |Δt,t+1|: 5.8, 1.7, 6.1, 5.0, 8.4, 4.4, 4.7, 3.9° — climb 은 noise 가 elbow-twist 의 1/2
- linear-time-warp |Δ| (talkv vs ref): elbow-twist 20~28°, climb 4~11°. KISMAM tol=20° 에서 elbow-twist → 50대 score, climb → 90대 score. 관측 정합.

## Eliminated

- 가설 1 (해상도 민감도): bit-identical 검증.
- 가설 2 (다른 영상 / 거울상): fileName 동일 확인.
- 가설 3 (Phase 17 회귀): ref-climb 가 score 95 정상.
- 가설 4 (stability TOL 변경 부작용): 영향 차원 분리.

## Resolution

### Root cause

RTMW 가 inverted/occluded 폴 자세에서 frame 당 10°+ jitter 를 만들고, `per_joint_deviation` 가 DTW path 따라 **mean-of-|per-frame-Δ|** 를 계산하기 때문에 mean angles 가 5° 차이여도 deviation = 20° 가 산출되어 KISMAM tol=20° 가 score ≈ 60 으로 깎는다.

이는 코드 회귀가 아니라 **알고리즘 디자인이 noise-dominated joints 에 hostile** 한 것이고, ref-climb 같이 occlusion 없는 자세에선 정상 동작 (score 95).

### Fix (applied)

**Single-file change**: `backend/shared/python/sunity_shared/analysis/motiondtw.py`
- `per_joint_deviation(path, A_user_seg, A_ref)` 평균 → **median** 으로 변경.
- 신호 (path 의 모든 frame 에서 일관된 차이) 는 median 으로도 정확히 잡힘.
- Noise (소수 outlier frame) 는 median 으로 차단.
- 같은 영상 self-compare 시 deviation = 0 보장 (회귀 테스트 추가).

```python
def per_joint_deviation(path, A_user_seg, A_ref):
    A_user_seg = np.asarray(A_user_seg, dtype=float)
    A_ref = np.asarray(A_ref, dtype=float)
    J = A_ref.shape[1]
    if not path:
        return np.zeros(J)
    diffs = np.empty((len(path), J), dtype=float)
    for k, (u, r) in enumerate(path):
        diffs[k] = np.abs(A_user_seg[u] - A_ref[r])
    return np.median(diffs, axis=0)
```

### Tests added (`backend/tests/test_motiondtw.py`)

- `test_per_joint_deviation_identical_sequences_zero` — 같은 영상 self-compare 시 deviation = 0 보장
- `test_per_joint_deviation_robust_to_outlier_frames` — 20 frame 중 2 frame 만 60° outlier → median = 0 (mean 이면 6.0)
- `test_per_joint_deviation_picks_persistent_offset_over_noise` — 일관된 10° 차이 + 단일 frame 50° outlier → joint별 median 이 정확히 분리

### Synthetic verification (`backend/scripts/verify_noise_robustness.py`)

| Scenario | After fix | Expected |
|---|---|---|
| [1] Identical self | **100** | 100 |
| [2] sigma=5° noise (climb-like) | **99** | 90+ |
| [3] sigma=12° noise (twist-like) | **92** | 80+ (was ~55) |
| [4] Real 25° offset on 1 joint | **94** | <95 (detects real diff) |
| [5] Phase-shifted motion | 98 | DTW 가 정렬, 정상 |
| [6] 10% outlier frames | **100** | 95+ (median 차단) |

**Scenario [3] 가 핵심 fix**: same motion + RTMW jitter 의 score 가 55-65 → 92 로 회복.

### Test results

- `tests/test_motiondtw.py`: **9 passed** (3 신규 회귀 테스트 포함)
- `tests/test_dimensions.py + test_assemble.py + test_kismam.py + test_segments.py + test_moment_dimensions.py + pipeline/`: **86 passed** (regression 0)
- `backend/scripts/verify_self_comparison.py --quick` (5 reference motions): all 100점 유지 (sanity)

### Side effects assessed

- `motiondtw.per_joint_deviation` 는 `segments.py` (콤보 모션 base/ext 점수) 에서도 사용 → median 으로 segment 점수도 robust 해짐 (positive). 회귀 테스트 통과 확인.
- `verify_self_comparison.py` quick mode 100점 유지.
- `dimensions.py` (line/stability) 미관계, 영향 없음.

## Deployment Plan (next step)

1. Lambda + RunPod Pod 양쪽 코드 sync 필요. RunPod 는 module 캐싱 → restart 필수.
   - 정확히는: `backend/shared/python/sunity_shared/analysis/motiondtw.py` 만 변경. Lambda 는 SAM redeploy. Pod 는 git pull + uvicorn restart.
2. Belle 가 같은 talkv 파일을 재분석 → angle dim score 95+ 확인.
3. climb 회귀 분석 → score 90+ 유지 확인.
