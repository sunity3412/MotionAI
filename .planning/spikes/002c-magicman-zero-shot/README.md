---
spike: 002c
name: magicman-zero-shot
type: comparison
validates: "Given MagicMan (THU 2024) 가 인체 NVS 강력 후보, when license + zero-shot 추론 viability 박제, then production 진입 가능 여부 결정"
verdict: INVALIDATED
related: [001, 002a, 002b, 002d]
tags: [human-nvs, license-gate, smplx, blocked, non-commercial-weights]
---

# Spike 002c: MagicMan Zero-shot License Gate

## What This Validates

**Given** MagicMan (`thuhcsi/MagicMan`, NeurIPS 2024) 가 인체 특화 Novel View Synthesis + SMPL-X conditioning 강력 후보,
**when** license + 학습 weight + 학습 데이터 license 박제,
**then** production 진입 가능 여부가 결정된다 (BLOCKED 시 zero-shot 추론 검증 자체 deferred).

## Research

### License Stack 검증 (4-tier)

| Tier | Asset | License | 상업 사용 |
|---|---|---|---|
| 1 | 코드 (`thuhcsi/MagicMan`) | MIT | ✓ |
| 2 | 학습 weight (공식 release) | **transitive non-commercial** (학습 데이터 상속) | ✗ |
| 3 | 학습 데이터 — THuman2.1 | **CC BY-NC 4.0 (비상업)** | ✗ |
| 3 | 학습 데이터 — 2K2K | **research-only** | ✗ |
| 4 | SMPL-X (conditioning) | Max-Planck research-only | ✗ |

**핵심:** 코드만 OSS (MIT) 인 케이스. weight 가 비상업 학습 데이터로 학습됐기 때문에 weight 자체가 transitive 비상업. Sunity 의 [`rtmw-clean-weight-release-gate`] 메모리와 **완전 동일 함정**.

### Re-train 가능성 (자체 path)

- **Commercial-friendly 인체 스캔 데이터셋 부재** — AGORA / 3DPW / EMDB 모두 비상업. BEDLAM2 도 비상업.
- 폴스포츠 자체 인체 스캔 수집 = 불가 (학원 학생 영상은 RGB only, 3D mesh ground truth 0)
- → MagicMan 자체 re-train **비현실적**

## How to Run

이 spike 는 license 검증 단독 — 코드 호출 없음. license 차단으로 zero-shot 검증 자체 deferred (자원 절감, depth over speed 정합).

## Investigation Trail

### Iteration 1 — License audit (2026-06-13)

**시도:** Agent 가 GitHub `thuhcsi/MagicMan` LICENSE + 학습 데이터 (THuman2.1, 2K2K) license + SMPL-X 의존 박제.

**발견:**
- 코드 MIT 만 보면 viable 처럼 보이나, weight 가 transitive 비상업
- commercial-friendly 인체 스캔 데이터셋 부재 → 자체 re-train 비현실적
- [`rtmw-clean-weight-release-gate`] 와 동일 함정

**Pivot:** zero-shot 도메인 적합성 검증 자체 의미 없음 (license 가 production 차단). 자원을 002b SMPL-X virtual render 에 집중.

## Results

### Verdict: **INVALIDATED for production** ✗

**근거:**
1. ✗ Weight 가 비상업 (transitive). 학생 영상 상업 분석 차단.
2. ✗ commercial-friendly 인체 스캔 데이터셋 부재 → 자체 re-train 비현실적
3. ✗ [`rtmw-clean-weight-release-gate`] 동일 함정

**Recommendation:**
- ❌ MagicMan production 진입 금지
- ❌ zero-shot 검증 자체 deferred (license 가 production 차단이라 의미 없음)
- ✅ 자원을 002b SMPL-X virtual render 에 집중 (자체 path 강력 우선)

### Surprises / 박제 사항

- MagicMan 의 SMPL-X conditioning 자체도 SMPL-X license (Max-Planck research-only) 에 의존 → 4-tier 모두 production 차단
- 인체 NVS 영역의 SOTA 가 거의 모두 비상업 데이터셋 학습 = belle 의 메모리 [`rtmw-clean-weight-release-gate`] 가 인체 NVS 도메인 전반에 적용됨

### Carry-forward

- **002b SMPL-X virtual camera render 가 자체 path 의 유일한 viable 후보** — RTMW joints (이미 운영, Apache-2.0) → SMPL-X fit (research-only 인데 *output 좌표만* 사용, weight 노출 X path 가능성 조사 필요) → virtual camera render
- 002b 의 SMPL-X 사용 자체에 license 의문 발생 → 002b 빌드 시 동시 검증
- Higgsfield (002a) + MagicMan (002c) 둘 다 차단 = **3-way → 2-way (002b + 002d) 비교 set 축소 가능성**

### Carry-forward for Phase 4 CONTEXT.md

- D-18 Path C ("MagicMan + RTMW hybrid") **확정 차단** — 별도 phase / future 도 옵션 0
- D-19 4-way 비교 set 추가 갱신 권고: Higgsfield + MagicMan 동시 제외 = **002b + 002d 만 남음**
- D-20 라이선스 카탈로그 보강: MagicMan (코드 MIT + weight 비상업 transitive) 박제

### Memory implication

`camera-angle-ai-single-view-synth` 메모리의 "MagicMan license research-only 추정" → **확정 비상업 박제**. 인체 NVS 도메인 전반의 데이터셋 license 함정 박제.

## Sources

- [MagicMan GitHub](https://github.com/thuhcsi/MagicMan)
- [MagicMan project page (thuhcsi)](https://thuhcsi.github.io/MagicMan/)
- [THuman2.0 / 2.1 license](https://github.com/ytrock/THuman2.0-Dataset) — CC BY-NC 4.0
- [2K2K dataset license](https://github.com/SangHunHan92/2K2K) — research-only
- [SMPL-X license](https://smpl-x.is.tue.mpg.de/modellicense.html) — Max-Planck research
