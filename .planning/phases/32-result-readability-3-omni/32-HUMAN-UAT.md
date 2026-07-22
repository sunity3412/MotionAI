# Phase 32 HUMAN-UAT — 아침 몰아보기 점검 목록

> belle 야간 지시: "한번에 다 업데이트하고 리스트대로 내가 하나씩 점검" ([[batch-uat-after-phase-31]]).
> 32-12 가 코드·빌드·제출·시뮬레이터 검증까지 완료하고 실기기 확인은 이 목록으로 이월.

## 선행 상태 (32-12 실행 executor 완료분)

- 앱 버전 1.0.0 → **1.1.0** bump (runtimeVersion=appVersion → 신규 runtime "1.1.0").
- native 모듈 추가: expo-audio(재생 중 큐 오디오), expo-font(Pretendard). → **OTA 단독 배포 불가, 새 TestFlight 빌드 설치 1회 필수** (기존 1.0.0 바이너리는 native 부재).
- EAS iOS production build + TestFlight 제출 상태 = 32-12-SUMMARY 기록 참조.
- 신규 runtime 1.1.0 대상 OTA 발행 = 32-12-SUMMARY 기록 참조 (이후 32-13 앱 OTA 는 이 runtime).

---

## A. 새 빌드 설치 후 실기기 확인 (belle — 신규 1.1.0 빌드에서만 유효)

기존 빌드에서의 확인은 무효 (native 모듈 부재). TestFlight 새 빌드(1.1.0) 설치 후:

1. **앱 기동** — 스플래시 후 인트로/홈이 **Pretendard 로 렌더**되는지 (시스템 폰트 대비 자획 정돈). 흰 화면/멈춤 없이 진입.
2. **결과 화면 첫인상** — 요약 카드 1장으로 "오늘 뭘 고칠지" 읽히는가 (D-09 헤드라인 수치 0).
3. **오늘 고칠 것 카드** — 상태→왜→행동 3단 문장이 읽히는가 + 게이지·미션이 D-10 강도인가.
4. **동작 비교 — 음성 안내(신규)** — 재생 중 자막 큐 전환 시점에 "음성 안내" 토글 ON 시 같은 문장이 음성으로 나오는가 (기본 OFF — 학원 소음). OFF 시 자막만.
5. **부분 실패 정직 고지(신규, D-29)** — 커버리지 갭이 있는 분석에서 "화면에 잘 잡힌 부분 위주로 분석" 고지 + 촬영 가이드 링크가 뜨는가.
6. **전체 실패 카피(신규, D-30)** — (재현 가능 시) not_pole/no_human/server_error 화면 카피가 친숙·응원 톤 + "다시 분석하기" → 분석탭 진입 동작.
7. **성공 판정 프레임 (SEED §9)** — ① 자기 말로 문제 설명 가능 ② 다음 행동 하나 말할 수 있음 ③ 강사에게 물어볼 것이 생김.

### 실데이터 doc (리뷰: mock/legacy 아닌 실데이터 승인)

- 가장 확실한 방법 = **belle 본인 새 분석 1건 업로드** (belle uid 하 실 doc — 음성·커버리지·폰트·미션 전 경로 실행).
- 32-16/32-09 스윕 산출 실 doc(`users/phase25eval/analyses/{powerspin,peterpan,elbowtwistsister,pdshape,kipup}{Fault,Correct}1784649897` 등, coachAudio 보유)은 Firestore 규칙상 phase25eval uid 하라 belle 계정으로 직접 열람 불가 — 열람이 필요하면 테스트 계정 커스텀 토큰 로그인 또는 doc 복사 필요(백로그). 백엔드 방출·조인·스코어 diff 0 은 32-16-SWEEP.md 에서 실증 완료.

---

## B. 일러스트 (D-21) — belle 최종 승인 게이트 (아침 이월, 무검수 노출 0)

- **확정 스타일 = 2안 준실사** (`samples/illust_variant2_pro.jpg`, belle "셋다 너무 멋진디, 상상이상").
- **belle 지적 품질 게이트: AI 일러스트는 해부학 오류(사지 개수·관절 방향) 위험** — 1안에서 다리 3개 오류 발견 실사례. **해부학 검수 + belle 최종 승인 없이 앱 반영 금지.**
- **32-12 실행 결정:** 결함별 일러스트 세트는 **신규 생성 에셋**이라 해부학 검수·belle 승인 전 **앱 미도입** — 현행 실프레임+텍스트 폴백 유지 (드릴다운 시트의 내 crop vs 정은지 crop 쌍 + 문구 3단). **승인 전 무검수 노출 0 준수** (앱 코드 무산출).
- **아침 belle 결정 필요:** ① 일러스트 도입을 진행할지 (진행 시 결함별 세트 생성 → 해부학 전수 검수 → belle 승인 → 별도 quick/plan 으로 앱 배선) ② 아니면 실프레임 폴백 유지.

---

## C. Polly 음성 최종 확정 (32-16 이월 — 아침 청취)

- 잠정 = **Seoyeon neural** 가동 중 (프로덕션 기본값). 후보 3종 `samples/voice/{seoyeon_neural,jihye_neural,seoyeon_generative}.mp3`.
- belle 청취 후: Seoyeon neural 유지 → 작업 0 / Jihye neural → Pod `POLLY_VOICE_ID=Jihye` / Seoyeon generative → Pod `POLLY_ENGINE=generative` (start_server.sh export + 재기동, **재배포 불요**).
- 앱 음성 안내(32-12) 는 이 음성을 그대로 재생 — 음성 스왑 시 앱 변경 0.

---

## D. 이전 웨이브 이월 (32-GATE-DECISIONS §배치 UAT 대기)

1. 참고 지표 카드 장문 줄겹침 해소 (D-03 수리분 픽셀 확인).
2. 새 분석에서 "대략 맞춤" 배지 노출 (trim_only + low_global_confidence).
3. 새 분석 확대비교 줌 쌍 배율 육안 (crop parity).

---

## E. 엔진 웨이브 (32-14/32-15) — 새 분석 실기기 확인

1. **12관절 오버레이 (32-14)** — 새 분석 결과 화면 키포인트 오버레이에 발목·팔꿈치 점 4개가 추가돼 12점 렌더되는지 (기존 doc 은 8점 유지 정상).
2. **확대비교 다리 라인 발목 연장 (32-14 부수)** — 새 분석 crop PNG 의 다리 각도 라인이 무릎이 아닌 발목까지 이어지는지 (백엔드 육안은 32-15 스윕 crop 21장에서 확인 완료).
3. **PR 인버전 보정 (32-15)** — 거꾸로 동작(elbow-twist·pdshape 계열) 새 분석 1건: 분석 완료 정상 + 오버레이/crop 이 인체 위 정합 + 분석 시간 체감 (+수 초 예상, GPU 기준). 백엔드 수치 실증은 32-15-SUMMARY 표 참조.
