---
phase: 38-supplier-link
plan: 13
subsystem: infra-supplier-web
tags: [s3, cloudfront, oac, firebase-authorized-domain, real-device, belle-approval]
requires:
  - phase: 38-supplier-link (38-09)
    provides: POST /reference/upload-url 라이브 + CORS, Firestore 규칙 라이브
  - phase: 38-supplier-link (38-11)
    provides: /supplier/upload · /supplier/guide
provides:
  - "공급자 링크 https://d2ivnoigym2xlu.cloudfront.net/supplier (S3 sunity-motion-pilot-supplier-web + CloudFront E16SR4IPFYH46Q + OAC EDVM240S2C0RM)"
  - "belle 실기기 승인 — 로그인 · 초대 수락 · 홈 · 올리기 STEP 01/02 · 대기 중 행 · 가이드"
affects: [38-14 (Pod 코드 배포 → requeue → 정은지 초대)]
key-files:
  created:
    - .planning/phases/38-supplier-link/38-13-DEPLOY.md
    - .planning/phases/38-supplier-link/infra/cloudfront-supplier.json
    - .planning/phases/38-supplier-link/infra/supplier-bucket-policy.json
completed: 2026-10-01
---

# 38-13 Summary — 공급자 링크 HTTPS 배포 + 실기기 belle 승인

**공급자 페이지가 HTTPS 링크 한 장으로 떠 있고, belle 이 실기기에서 로그인부터 올리기·대기 중 행·가이드까지 보고 승인했다 — 그 사이 belle 폰 확인에서 나온 수정은 quick 260930-lfw · 260930-o0u · 260930-w9l 로 반영됐다.**

## 관측 [확인]

- Task 1 배포 `ac03388d`: 새 버킷 + OAC + distribution, 재사용 리소스 0 → 롤백은 전부 삭제(`38-13-DEPLOY.md` 롤백 절). HTTPS 200 · http→301 · S3 직접 403 · API CORS 통과.
- Task 2 Authorized domain: 콘솔 등록 줄 원문은 이 기록에 없다. 대신 lfw 에서 belle 폰 Google 팝업 로그인 → 초대 수락 성공 [확인 belle] = 도메인 허용이 된 상태.
- Task 3 belle 실기기:
  - lfw(09-30): A-2 두 번째 계정 · 초대 수락 → 홈 + 코드 줄 · 복사 · 크게 보기 ○.
  - 09-30 저녁: STEP 01/02 · 올리기 · 토스트 · 대기 중 행 · 가이드 기능 ○ + 수정 요청 12건(원문 = DEPLOY Task 3 절) → belle 결정 → quick 260930-w9l 로 반영·배포.
  - 10-01 새벽 재확인: *"1~9번 다 오케이"* → **approved**.
- 38-10 이월 4·5(공급자 probe 브라우저 CORS · `where supplierUid` 구독): 폰에서 홈 표시 + 올린 행이 `대기 중` 으로 바뀐 것으로 충족 [확인 belle 09-30 스크린샷].
- 정리: 시험 doc 1건(클라임) 백업 뒤 삭제 + S3 객체 삭제 + TESTB deactivate. 남은 reference doc 12개 모두 시드(대기 0).

## 미확인 · 다음 플랜이 알아야 할 것

- [미확인] CloudFront 과금 방식(콘솔에서만 보임).
- [미확인 — 38-14] 소리 제거 · 썸네일 · 1GB/2분 처리(Pod 코드는 w9l 에서 코드+테스트만). **Pod 코드 배포가 requeue 보다 먼저**(옛 코드는 새 doc 을 30초 상한으로 본다).
- [미확인 — 법률 자문 · 38-14 초대 전] AI 학습 = 공급자 계약 근거로 기록된다(w9l). 정은지 초대 전에 계약서 학습 조항 존재·서명 확인.
- Figma 282:506 은 w9l 이후 코드와 다르다(`38-DESIGN-v2.md` 끝 w9l 절).
- BELLE 코드가 Google 로그인 없는 옛 익명 계정(FDJr…)에 붙어 있다 — belle 본인 Google 계정 초대 여부 belle 결정.

## Self-Check

- 커밋 `ac03388d` 존재 [확인 git log]. DEPLOY.md Task 3 절에 `[확인 belle]` 표식과 원문 [확인].
