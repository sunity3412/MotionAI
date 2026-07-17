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
