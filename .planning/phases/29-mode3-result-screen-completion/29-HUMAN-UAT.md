---
status: pending
phase: 29-mode3-result-screen-completion
source: [29-08-PLAN.md Task 3, 29-04-SUMMARY.md, 29-07-SUMMARY.md]
started: 2026-07-17
updated: 2026-07-17
channel: production + preview
ota_production_group: 4d079a4b-0986-453b-a22c-9605b1120082
ota_preview_group: df164e4d-5359-4168-8783-19a5525de073
ota_commit: f3eb332
ios_build: aaa54678-72db-478e-b626-59dc8bedc36f
android_build: 04dc0e96-65c6-4c94-9885-4caab95aceef
---

# Phase 29 — HUMAN-UAT (실기기 확인 적립)

> **batch UAT — /gsd-audit-uat 시 일괄 확인. 즉시 belle 호출 금지.**
> (batch-uat-after-phase-31 원칙: 실기기 확인은 phase 별 HUMAN-UAT.md 에 적립만 하고, 나중에 `/gsd-audit-uat` 로 한 번에 검수한다. 이 문서의 어떤 항목도 즉시 belle 호출을 유발하지 않는다. 단, checkpoint:decision 성격의 판단이 필요하면 그때만 belle.)

## 확인 경로 요약

- **구빌드(TestFlight 27 계열):** production/preview OTA 수신 후 앱 기동 → JS-only 개선분(mode3 내역·부상 대응법·D1 fix·라벨) 즉시 도달, 가로 코드는 lazy require 라 무해.
- **새 빌드:** iOS build `aaa54678` (TestFlight 무인 제출) / Android build `04dc0e96` (APK). 진짜 가로 전환 + F1(문의하기 메일 컴포저) 네이티브 포함.

---

## Tests

| # | 항목(요구 토큰) | 확인 경로 | 기대 결과 | result |
|---|---|---|---|---|
| 1 | **D-14** 부상 대응법 권고 | mode1/mode3 결과 → 부상 위험 카드 | "이렇게 해보세요" 권고 행 + 점검 캡션 표시. 부상 확정 단정 카피 없음. legacy doc 포함 표시 | [pending] |
| 2 | **D-01**~D-05 mode3 내역/게이트 | power-spin mode3 분석 결과 화면 | power-spin → 점수 내역(deductionBreakdown) 렌더 + overallScore == breakdown.final. kip-up 등 4동작 → 내역 없음 + 한계 고지 1줄. 미등록 동작 → 행동 유도 안내. legacy doc → 통합 배너("다시 분석하면 최신 분석 적용") | [pending] |
| 3 | **D-06**/D-07 비교 라벨·첫 분석 | mode3 결과 비교 섹션 | 비교 라벨 "이번 영상"/"지난 영상" 표기. 첫 분석(mode3 isFirst) → 비교 섹션 숨김 + "다음 분석부터 비교" 안내 1줄 | [pending] |
| 4 | **D-08** + **power-spin** 드릴다운 end-to-end | power-spin mode3 감점 분석 → 확대 카드 → 점수 내역 행 탭 | (a) 결함 부위 확대 카드 표시(improved 카드 없음), (b) 점수 내역 leg_extension 행에 번호 + 영상 위 그룹 마커(legs centroid) 표시, (c) 행 탭 → 드릴다운 시트에 region 'legs' zoom 카드·행동구 매칭. criterion→region 투영 전 구간 정합 (29-PLAN-REVIEW HIGH-1) | [pending] |
| 5 | **D-10** mode3 second+ 워핑 | mode3 두 번째+ 분석 비교 재생 | 이전 영상이 이번 영상 타임라인에 워핑돼 재생. 신뢰도 배지·배속 클램프 자연스러움(28 사다리 동일). 진입→이탈 반복 크래시 없음 | [pending] |
| 6 | **D-09** 정은지 비교영상 재생(D1 재발) | 7일+ 경과 mode1 doc → 비교 재생 | 정은지 reference 비교영상이 재생됨(빈 화면/미표시 없음). D1 재발 여부 확인 — playback-url referenceMotionId 재서명 정상 | [pending] |
| 7 | **D-11** (새 빌드) 진짜 가로 전환 | 전체화면 비교 뷰어 진입/닫기 | 진입 시 진짜 가로(LANDSCAPE) 전환, 닫으면 세로 복귀, 앱 전체 세로 고정 유지, flicker 없음 (A1/A2 가정 판정). **실패 시 plugin initialOrientation/requireFullScreen 조정 후보 명기** | [pending] |
| 8 | **D-12** (구빌드 27) OTA 무크래시 폴백 | 구빌드 27 → OTA 수신 후 앱 기동 → 전체화면 뷰어 | 앱 정상 기동(크래시 0) + 전체화면 뷰어 = 기존 90° 회전 핵 폴백 동작. 정적 import 0 게이트 근거 | [pending] |
| 9 | **F1** (새 빌드) 문의하기 메일 컴포저 | 마이페이지 → 문의하기 | expo-mail-composer 네이티브 포함 → 메일 컴포저 열림 (빌드 27 부재 → 새 빌드 동승 해소) | [pending] |
| 10 | **iPad** 관찰(참고) | iPad 에서 전체화면 뷰어 진입 | 가로 lock 동작 여부 관찰. 파일럿 iPhone 중심 — 실패해도 blocker 아님 (Pitfall 5, lockAsync 실패 무해화) | [pending] |

---

## Summary

- total: 10
- passed: 0
- issues: 0
- pending: 10
- skipped: 0
- blocked: 0

## Notes

- **T-29-08-01 (OTA 구빌드 크래시) mitigation 근거:** 발행 전 정적 `from 'expo-screen-orientation'` import grep = 0 (Task 1 blocking gate 통과) — 항목 8(D-12)이 실기기 최종 확인.
- 항목 4의 criterion→region 투영은 backend(29-03)·app(29-04) 양측 매핑 표가 SUMMARY 에 cross-side 박제됨. 실기기는 렌더 경로 전 구간(내역 행 번호 → 그룹 마커 → legs zoom)만 확인하면 됨.
- power-spin 외 등록 4동작은 criteria 가 비어 breakdown 미방출 — 항목 2의 "내역 없음 + 한계 고지"가 정상 동작이며 버그가 아니다.
