---
quick_id: 260702-mat
description: TestFlight 빌드 27 배포 + 안드로이드 APK 최신화 확인 — Pod 테스트 전 선행 작업
date: 2026-07-02
---

# Quick Task 260702-mat: TestFlight 27 배포

## 조사 결과 (ground truth)

- `appVersionSource: remote` — app.json 의 buildNumber/versionCode 는 무시됨. 버전은 EAS 원격 관리.
- iOS 원격 buildNumber = 27. **빌드 #27 은 이미 존재** (production 프로파일, 2026-07-02 11:45 시작, FINISHED).
  - build id: `409cbe70-5e00-4f3a-87cd-7bca677808d9`
  - 커밋: `11899b5` = 현재 main HEAD (앱 코드 변경 없음)
- Android APK 빌드 #1 (preview-android, 2026-06-30) 도 **같은 커밋 11899b5** 에서 빌드됨.
  - 직원이 설치한 APK = iOS #27 과 동일 코드. 재빌드 불필요.

## Tasks

1. iOS 빌드 #27 을 TestFlight 에 제출 (`eas submit -p ios --id 409cbe70-...`).
   - ASC API Key 등록되어 있어 무인 제출 가능.
   - 이미 제출된 경우 Apple 이 중복 거절 → 무해, 결과 보고.
2. 안드로이드: 재빌드 없음 (동일 커밋 확인 완료). 사용자에게 사실 보고.
3. SUMMARY.md + STATE.md 업데이트, docs 커밋.
