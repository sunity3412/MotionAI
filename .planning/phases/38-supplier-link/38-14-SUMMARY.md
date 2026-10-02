---
phase: 38-supplier-link
plan: 14
subsystem: e2e-supplier-registration
tags: [runpod, e2e, supplier, review, mode1, self-check, belle-approval]
requires:
  - phase: 38-supplier-link (38-13)
    provides: 공급자 링크 https://d2ivnoigym2xlu.cloudfront.net/supplier
  - quick: 261001-thx
    provides: 분석 불가만 막기 · review 상태 · 검수 CLI(list/show/approve/reject/deactivate)
provides:
  - "공급자 링크 등록 → review → 운영 승인 → 수강생 picker → mode1 done 의 실물 1회 완주(대역 계정 = 구조 검증)"
  - "pod_teardown.py 모르는 옵션 거부(c5d8fd85)"
affects: [공급자 제출/요청 취소 문구·버튼(다음 quick), 분석 시간 단축(다음 quick), 정은지 직접 완주(Success ① 독립 사용자)]
key-files:
  created:
    - .planning/phases/38-supplier-link/infra/legacy-reference-after-e2e.json
    - .planning/phases/38-supplier-link/evidence/runpod_server_38_14_1002.log
  modified:
    - .planning/phases/38-supplier-link/38-14-E2E.md
    - backend/scripts/pod_teardown.py
completed: 2026-10-02
---

# 38-14 Summary — 공급자 등록 첫 실물 완주 (대역 계정)

**belle 의 다른 계정이 링크로 올린 사이드웨이 스핀이 review 로 들어가고, belle 사진 확인 뒤 승인 → 수강생 앱 picker 에 떠서 mode1 이 done(100점)으로 끝났다. 자기 재분석 100점, 기존 기준 11개 diff 0. 정은지(belle 아닌 사람)의 직접 완주는 아직이다.**

## 관측 [확인]

- 10-01 두 번 실패(여러 명 · 대각선 출발) → 261001-thx(분석 불가만 막기) 배포 뒤 10-02 셋째 시도: 같은 영상이 진단만 남기고 review (업로드 뒤 59초).
- 검수: 썸네일 + 10·50·90% 사진 4장을 belle 화면에 띄움 → belle *"응 권장대로 진행하자"* → approve → active · isActive True.
- 자기 재분석 `cc8b5995…` done, `selfScore` 100.0 == `result.overallScore` 100 == `deductionBreakdown.final` 100, `selfCheckJobId` == 기준 `jobId`.
- 수강생 mode1 `2a7495bb…` (belle 아이폰, 새 기준 선택) done 100, 점수까지 3분 40초. belle *"같은 영상이라 100점 오케이"*.
- 재PUT 불변(R5): 다른 mp4 를 `upload.mp4` 에 → Lambda `스킵: 등록 대기 doc 아님 … status=active`, v1 ETag · anglesUpdatedAt 그대로.
- 기존 기준 baseline diff 0 (R10). Pod 로그 `기준 모션 또는 keyframe 데이터 없음` 0.
- Pod 4090 SECURE 1시간 59분 $1.46, 종료 · SSM down · Lambda 자리표시자.
- 정리(belle *"지우기"*): 10-01 실패 doc 2건 + S3 4객체 삭제, 테스트 기준 deactivate, TESTB deactivate.
- 함정 수리: `pod_teardown.py --help` 가 `--help` 를 Pod id 로 받아 주소를 되돌렸다 → 모르는 `-` 옵션은 exit 2(`c5d8fd85`).

## 판정

| Success | 판정 |
|---|---|
| ① 링크만으로 새 동작 → picker → mode1 | 구조 검증 ○ · 독립 사용자 [미확인] |
| ② 분석 불가만 막고 나머지는 진단 | ○ |
| ③ 자기 재분석(일관성 진단) | 100 · belle ○ |
| ④ 기존 기준 무접촉 | ○ (diff 0) |

## 진단 (재검증 대상)

- 점수까지 3분 40초 중 Gemini 3단계 ≈ 2분 + stage_timing 밖 ≈ 42초가 **기준 영상 Gemini 업로드·ACTIVE 대기**다(로그 관측). 매 분석마다 기준을 다시 올리는지, 분석 간 재사용이 되는지는 [미확인].
- scene_finder join(app.py:8913)이 recognizer 앞에 있으나 첫 소비처는 veto 뒤(app.py:9542) — 뒤로 미루면 겹칠 수 있다 [코드 읽기, 실측 전].
- 플랜 acceptance 의 `register-reference ok ≥ 1` 은 261001-thx 이전 문구 — 지금 성공 줄은 `register-reference review`.

## 다음

1. 공급자 "제출 / 요청 취소"(belle 10-02: 메일 없음, 문구 "검토는 보통 하루 안에 끝나요. 결과는 이 화면에서 볼 수 있어요." + 검토 요청 취소 버튼).
2. 분석 시간 단축 — 기준 영상 Gemini 핸들 재사용/미리 올리기 + scene_finder join 이동, Pod 실측으로 확인.
3. Success ① 독립 사용자 = 정은지 직접 완주(초대·코드).

STATE `stopped_at` 제안: "2026-10-02 — Phase 38 14/14 실행 완료(38-14 대역 구조 검증 ○, 독립 사용자 [미확인]). 다음 = 공급자 제출/요청 취소 quick → 분석 시간 단축 quick."

### 갱신 (2026-10-02 저녁 마감)
- 위 '다음' 1번 = quick 261002-pa2 **코드·테스트 완료, 배포 안 함**(pytest 5910/20 · node 97/97 · typecheck 0). 10-03 첫 일 = `.planning/quick/261002-pa2-supplier-review-request-copy-and-cancel/261002-pa2-DEPLOY.md` 순서(롤백 보존 → layer → reference-upload-url → 웹) + belle 폰 확인. 배포 뒤 확인용 계정(TESTB 잠깐 되살리기 / belle uid / 403 로 두기) 결정이 남아 있다(DEPLOY.md '선택 확인').
