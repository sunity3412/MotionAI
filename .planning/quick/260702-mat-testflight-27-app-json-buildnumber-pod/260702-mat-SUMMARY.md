---
quick_id: 260702-mat
status: complete
date: 2026-07-02
---

# Summary: TestFlight 빌드 27 배포 (Pod 테스트 전 선행)

## 결과

**iOS 빌드 #27 TestFlight 제출 완료.**

- 빌드 #27 (production, id `409cbe70-5e00-4f3a-87cd-7bca677808d9`) 은 이번 세션 전 2026-07-02 11:45 에 이미 빌드되어 있었음 (커밋 11899b5 = main HEAD).
- 이번 세션에서 `eas submit -p ios --id 409cbe70...` 무인 제출 실행 → **App Store Connect 업로드 성공**.
- Apple 처리(5~10분) 후 TestFlight 에 노출: https://appstoreconnect.apple.com/apps/6772934567/testflight/ios
- 제출 상세: https://expo.dev/accounts/sunity3412/projects/sunity-ai-coach/submissions/f86c9b2c-d150-456a-8821-18cf068b5086

## 안드로이드 판단

- 직원이 설치한 APK = 빌드 #1 (preview-android, 2026-06-30), 커밋 **11899b5 — iOS #27 과 동일 코드**.
- 그 이후 앱 코드 변경 0건 → **재빌드 불필요, 업데이트할 내용 없음**. 기존 설치 앱이 이미 최신.
- 앱 코드가 변경되는 시점에 `eas build -p android --profile preview-android` 로 새 APK 링크 생성하면 됨.

## 참고 (버전 관리 방식)

- `appVersionSource: remote` 라서 app.json 의 `buildNumber: "1"` / `versionCode: 1` 은 무시됨 (버전은 EAS 원격 관리, production 프로파일 autoIncrement).
- 코드/파일 변경 없음 — 운영(배포) 작업만 수행.
