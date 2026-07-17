# Phase 30 — HUMAN-UAT / Ops 노트 (배치 이월)

> 실기기·실런타임 확인은 즉시 belle 호출하지 않고 여기에 적립 → phase 마감 후
> `/gsd-audit-uat` 한 번에 (배치 UAT 원칙 [[batch-uat-after-phase-31]]).

## Plan 30-02 (D-04 mode3 recognized motion 데이터 적립)

### Ops 노트 — 실효 런타임(Pod) 동기화 조건

- **D-04 방출 필드의 실효 런타임은 RunPod Pod** (`_process` 실제 실행처 —
  Lambda CPU 경로는 NLF NaN 폴백이라 실분석 미수행). **현재 Pod OFF**
  (2026-07-17 기준 — 이전 Pod olnrvtj0f80pl4 terminate, 새 Pod 미기동).
- **다음 Pod 재가동 시 git 최신 코드 pull 로 자동 반영** (Pod bootstrap =
  repo checkout → server 기동, [[current-pod-hbpvhedq2bu01i]] 절차).
- **재가동 후 확인 항목: mode3 실분석 1건**으로 Firestore
  `users/{uid}/analyses/{id}.result.comparison.recognizedMotionId` 저장 확인
  (인식 성공[profile.motion_id 존재] 시 첫 분석부터 방출). 인식 실패
  (FallbackRecognizer/motion_id=None) 케이스는 두 키 부재가 정상(legacy 동형).

### Ops 노트 — Lambda SAM 배포 보류 사유 (BLOCKED)

- **배포 시도 결과: 보류.** `sam build --use-container` 는 성공했으나
  `sam deploy` 가 CloudFormation 변경셋 생성 단계에서 실패:
  `AWS::EarlyValidation::ResourceExistenceCheck` 훅 검증 FAILED (2회 재시도 동일 —
  transient 아님).
- **원인 분석:** 스택 `sunity-motion-pilot` 자체는 정상(`UPDATE_COMPLETE`,
  직전 배포 2026-07-16 성공). 이번 30-02 diff 는 **순수 Python**(shared layer +
  pipeline function 의 assemble.build_mode3 kwargs / _mode3_comparison 배선)이라
  CloudFormation 리소스를 **추가·삭제하지 않는다** → ResourceExistenceCheck 실패는
  이 코드 변경이 아니라 계정/스택의 기존 리소스 의존성(early-validation 훅이 참조하는
  선존 리소스)에서 발생. 코드 자체는 배포 준비 완료 상태.
- **영향 없음:** 실효 런타임(Pod)이 OFF 라 production 실분석은 어차피 미수행 중 —
  Lambda 미배포로 인한 사용자 노출 회귀 0. Pod 재가동 시 git pull 로 D-04 코드가
  Pod 에 반영되므로 실효 경로는 커버됨.
- **다음 조치(belle/운영):** ResourceExistenceCheck 훅이 지목하는 선존 리소스 확인
  (`aws cloudformation describe-change-set` 의 hook 상세) 후 재배포, 또는 다음 정례
  Lambda 배포 사이클에 합류. 재시도 명령:
  `cd backend && AWS_PROFILE=sunity-motion sam build --use-container && \
  sam deploy --no-confirm-changeset --no-fail-on-empty-changeset`.

### 확인 체크리스트 (Pod 재가동 후)

- [ ] Pod 재가동 → git 최신 코드(30-02 포함) pull 확인
- [ ] mode3 실분석 1건 → `comparison.recognizedMotionId` 저장 확인 (인식 성공 영상)
- [ ] 인식 실패 영상 mode3 → 두 키 부재(legacy 동형) 확인
- [ ] (선택) Lambda SAM 재배포 성공 시 CloudFormation `UPDATE_COMPLETE` 확인

## Plan 30-04 (홈 성장 카드 2층 토글 — E1/E2 사용자 노출)

### Ops 노트 — production OTA 발행 (오케스트레이터 이월)

- **발행 상태: 오케스트레이터 이월 (deferred-to-orchestrator).** EAS 인증은 정상
  (`npx eas-cli whoami` → sunity3412 확인)이나, 본 플랜은 워크트리 격리 실행이라
  발행을 워크트리에서 직접 하지 않는다:
  1. 워크트리 `app/node_modules` 는 메인 체크아웃 심링크(번들 무결성 우려) →
     반환 전 제거됨.
  2. 워크트리 HEAD = base `1d0cc2d`(wave 2 마감) + 30-04 커밋이라, 오케스트레이터가
     wave 3 머지를 완료한 **최종 main 커밋과 git SHA 가 다르다** — EAS update 는 커밋
     메타데이터를 박제하므로 잘못된 커밋으로 발행될 위험.
- **다음 조치(오케스트레이터):** wave 3 머지 후 메인 체크아웃에서 발행:
  `cd app && npx eas-cli update --branch production --message "phase 30: growth card weekly avg + per-motion deltas"`.
  앱 변경분 전부 JS-only(신규 native 모듈 0)라 OTA 가능(Phase 27/28 선례).
- **발행 후 확인:** `npx eas-cli update:list --branch production --limit 1` 에 phase 30
  메시지 최신 업데이트 존재.

### 실기기 확인 항목 (배치 UAT — 즉시 belle 호출 금지)

- [ ] 홈 성장 카드 [추이]/[동작별] 탭 전환 — 카드 높이 불변(홈 레이아웃 안 움직임),
  활성 탭 브랜드색(brandTint 배경 + brand 텍스트) 식별 (D-08/D-03)
- [ ] [추이] 모드 토글 기본값 = 마지막 분석 모드 (해당 모드 주별 점 부족 시 타 모드
  자동 폴백 동작) (D-03)
- [ ] [추이] 선이 주별 평균 점 + 주 시작일 라벨('M/D주')로 그려짐 — raw 건별 나열 아님 (D-01)
- [ ] [동작별] 리스트 — '프로 비교'/'내 기록' 배지 구분, ▲=브랜드레드/▼=파랑,
  '+N점/−N점' 포인트 표기, 첫 기록 동작은 "첫 기록 N점 (비교 전)" (D-05/D-06/D-09)
- [ ] [동작별] 보기에서 모드 토글 미노출 (D-09)
- [ ] 분석 부족 상태에서 정정된 locked 카피("서로 다른 주에 분석을 2번 이상 하면") 표시 (D-03 null 분기)
- [ ] 명시 선택 모드의 주별 점 부족 시 빈 차트가 아니라 안내 카피("이 모드는 주별 데이터가 아직 부족해요") 표시 (D-03)
