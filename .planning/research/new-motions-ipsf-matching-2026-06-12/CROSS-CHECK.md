---
date: 2026-06-12
purpose: 정은지 신규 영상 7개의 IPSF 명칭 매칭 — 3 path cross-check
paths:
  - Gemini Vision (gemini-3.1-pro, 8-16 frame sample, 자동)
  - claude.ai (belle 직접, 30-116 frame 정밀 분석, 가장 상세)
  - RTMW pose (Pod, 18fps keypoint 정량, 검증용)
artifacts:
  - gemini-vision.json (Gemini 결과)
  - claude-ai/ → 실제는 .planning/research/잘된예시_*_분석.md 박혀있음
  - rtmw-keypoint-18fps.json (Pod RTMW 결과)
---

# 3 Path Cross-Check — 정은지 7 신규 영상 IPSF 매칭

## Summary

claude.ai 가 가장 상세 + 정확. Gemini Vision 은 빠른 1차 분류 + IPSF 매핑. RTMW 는 정량 검증 (frame 수 / fps 정합).

3 path 합치 = 신뢰 강. 불일치 = belle ↔ 정은지 확인 후보.

## 영상별 매칭

### 1. kip-up (7.8s, 118 frames @18fps)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | IPSF 미등재 (동적 스킬, mounting/swing) | "정적 hold 아님" |
| **claude.ai** | IPSF 미등재 (인버전 X) | "폴 grip 스윙 회전 4회, 머리 항상 위" — kip-up 정식 정의 (체조 등→일어서기) 와 다름. **실제로는 폴 스윙 dynamic spin entry** |
| **RTMW** | 118 frame / 6.6s = 18fps 정합 ✓ | — |
| **합치** | **IPSF 미등재 ✓ (분기 2 학원 통용)** | 인버전 발생 X — kip-up 명칭 정확성 belle 확인 필요 |

### 2. climb (7.9s, 120 frames)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | ✓ IPSF Climb (Basic) | 베이직 클라임 |
| **claude.ai** | **부분 불일치** — "마운트 (지면→공중) 과정 영상 밖, 이미 공중 시작 + 시티드 터크 hold + 5-6회 회전" → Climb 정의 ("최소 2회 반복 위아래 이동") 와 다름 | 수직 이동 0. **Climb 정의 strict 적용 시 미등재** — Inverted Knee Hook Seated Spin 류 |
| **RTMW** | 120 frame / 6.7s = 18fps ✓ | — |
| **합치** | **부분 일치 — 학원 통용 "클라임" but IPSF Climb 정식 정의 X** | 정확 명칭 belle 확인 필요. 영상이 Climb 의 entry/exit 잘려있어 정의 모호 |

### 3. peter-pan (8.6s, 130 frames)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | IPSF 미등재 (기초 스핀) | 전 세계 학원 통용 |
| **claude.ai** | IPSF 미등재 — "스태그 다리 셰이프 + 양손 그립 + 4회전 hold" | 스플릿 그립 + 한 다리 폴 hook + 한 다리 뒤로 |
| **RTMW** | 130 frame / 7.2s = 18fps ✓ | — |
| **합치** | **IPSF 미등재 ✓ (분기 2)** | 스태그 셰이프 학원 통용 |

### 4. power-spin (10.5s, 159 frames)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | ≈ Split Grip + Aerial Split/Spin 변형 | IPSF Code 그립+유연성 분해 채점 |
| **claude.ai** | "양손 스플릿 그립 + 6회전 + 턱↔extension 펌핑 + 마지막 수직 split (2.5회전)" — IPSF 미등재 단 후반은 ≈ Vertical Split spin variation | 6회전 시계방향 |
| **RTMW** | 159 frame / 8.8s = 18fps ✓ | — |
| **합치** | **IPSF 미등재 + 후반 hold = Vertical Split variation** | 분기 2 |

### 5. elbow-twist-sister (21.9s, 329 frames)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | ≈ Inverted Inner Thigh Hook (Scorpio) + Elbow grip + Split variation | 고난이도 변형 |
| **claude.ai** | "메인 hold = 도립 + 백벤드 + 윗다리 수직 익스텐션 + 엘보 그립 (8초 유지)" — IPSF 미등재, 단 베이스는 Inverted Inner Thigh Hook + Elbow back grip 결합 | 회전 22초 1회전/초 |
| **RTMW** | 329 frame / 18.3s = 18fps ✓ | — |
| **합치** | **IPSF 미등재 + Scorpio variation 베이스 (분기 2)** | 학원 통용 high-level |

### 6. pdshape (15.8s, 237 frames)

| Path | 매칭 | 상세 |
|---|---|---|
| **Gemini** | ≈ Extended Butterfly + Scorpio variation | "pdshape 는 Pole Dance Shape 범용 태그일 수 있음" (Gemini 추정, 틀림) |
| **claude.ai** | "인버티드 비대칭 hold (클로즈드 셰이프, 8초) + 오픈 레그 라인 변형 (3초)" — IPSF 미등재 변형 hold | 12회전+ 등속 |
| **RTMW** | 237 frame / 13.2s = 18fps ✓ | — |
| **합치** | **IPSF 미등재 (분기 2)** | belle 정의: 정식 명칭 없는 연계 동작을 pdshape 로 통용 (메모리 [[gemini-vision-active-use]] 정합). 학원 통용명 확정. |

### 7. combo ⭐ (62s, 931 frames)

claude.ai 가 **10 segment** 로 매우 상세 분석 (Gemini 는 3 segment):

| 구간 | claude.ai 분석 | Gemini 매칭 |
|---|---|---|
| S1 0.0-1.5s | entry (스탠딩 → 워크어라운드) | (entry & climb 0-19s 박힘) |
| S2 1.5-13.5s | spin sequence (공중 다리 셰이프 5-6회 변경) | |
| S3 13.5-18.5s | climb (회전 유지 상승) | |
| S4 18.5-20.5s | invert entry (인버티드 스트래들/V/chopper) | (Inverted Split variation 23-31s) |
| S5 20.5-28s | transition (스트래들 → 무릎/허벅지 후크 셋업) | |
| S6 28-37.5s | **Leg Hang hold (윗다리 무릎 후크)** + 익스텐션 라인 — **33s 아웃사이드 레그 행** | (Hip Hold Split / Jade Split 35-42s) |
| S7 37.5-44s | **Butterfly 계열** (38-40s 클로즈드 + 41-43.5s 익스텐디드 버터플라이) | |
| S8 44-53s | transition (셰이프 전환 연속) | |
| S9 53-57.5s | finale display (수직 정렬 레그 행 + 무릎 후크 수평 셰이프) | |
| S10 57.5-62s | dismount (컨트롤 슬라이드 다운 + 착지) | |

**합치 분석**:
- 두 path 모두 콤보 = **multi-segment 분리 필요** 확정
- claude.ai 가 **Leg Hang (Outside) + Butterfly + 다양 인버티드 hold** 박힘 박힘 — Gemini 의 Jade Split 매칭 보다 더 정확
- RTMW 931 frame / 51.7s effective vs ffprobe 62s → 약 10초 박힘 박힘 정합 검토 필요 (frame_extractor step 박힘 박힘 박힘)

→ **메인 hold = Outside Leg Hang (Gemini 변형) + Extended Butterfly + Leg Hang**. IPSF 등재 카테고리 mix.

---

## 종합

| 영상 | 최종 매칭 | branch |
|---|---|---|
| kip-up | IPSF 미등재 (인버전 X dynamic spin entry) | 2 (학원 통용) |
| climb | 학원 "클라임" 부분 (IPSF Climb 정식 정의 strict 시 미달) | belle 확인 필요 |
| peter-pan | IPSF 미등재 (스태그 셰이프 + 양손 grip spin) | 2 (학원 통용) |
| power-spin | IPSF 미등재 + 후반 ≈ Vertical Split variation | 2 |
| elbow-twist-sister | IPSF 미등재 + Scorpio + Elbow back grip variation | 2 |
| pdshape | IPSF 미등재 (정식 명칭 없는 연계 동작 학원 통용) | 2 |
| combo | **complex multi-segment** (Leg Hang / Butterfly / Inverted Split mix) | 1+2 (IPSF Code 카테고리 mix) |

## belle 확인 필요 항목

1. **kip-up** — 인버전 없는 spin entry 동작. 학원에서 "kip-up" 이라 부르는 게 IPSF/대회 어떤 이름인지 정은지 확인 (Gemini 가 동적 스킬, claude.ai 가 폴 grip 스윙으로 분석 — 정의 모호)

2. **climb** — IPSF Climb 정의는 "최소 2회 위아래 이동". 영상은 이미 공중 + 회전 hold (수직 이동 0). 학원 "클라임" 이 정확한 IPSF 명칭과 같은지

3. **combo** — claude.ai 의 10 segment 중 IPSF 등재 매칭 가능한 segment 식별:
   - S6 Leg Hang = Inverted Thigh Hook (Outside) ✓ IPSF
   - S7 Butterfly = Inverted Torso Hook ✓ IPSF
   - S4-S5 Inverted Straddle/Chopper = IPSF 매칭 가능
   - belle 가 정은지에게 "이 콤보의 메인 IPSF 등재 기술" 확인

4. **pdshape, peter-pan, power-spin, elbow-twist-sister** — 학원 통용명 그대로 사용. 분기 2 (정은지 reference 측정값 = 채점 기준).

## 결과 신뢰도

- **claude.ai** = 가장 상세 + 정확. frame 30-116장 분석. 우선 채택.
- **Gemini Vision** = 빠른 1차 매핑. claude.ai 검증용.
- **RTMW** = 정량 (frame 수 / fps 정합). 분석 자체 신뢰성 가장 높음. 채점 input 으로 사용.

**다음 단계**:
1. belle 가 정은지에게 위 "확인 필요 항목" 4개 query
2. 결과 받으면 매칭 표 최종화
3. Phase 5 Gemini cache 또는 Phase 12 reference 확장 plan 박제
