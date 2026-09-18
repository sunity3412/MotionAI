# belle 판정 대기 5건 — 2026-09-18 (quick-260918-qm2)

고치지 않았다 — 기록만이다. 각 건 = 관측(파일:줄, 실측 명령) → 선택지 → 판정 요청 한 줄.
수치는 물을 때만 꺼낸다 (belle 보고 형식 — 판정 먼저).

`backend/template.yaml` 은 이 판정 전까지 무접촉이다.

---

## 0. 판정 요청 (한 줄씩)

1. **`sam deploy` 를 살릴 것인가** — 죽은 Phase 31 파라미터 5개에 Default/override 를 줄지,
   파라미터를 걷어낼지.
2. **`template.yaml` 의 `RunpodAnalyzeUrl` / `RunpodAuthToken` 사문 파라미터를 걷어낼 것인가** —
   설명문이 NLF 폴백을 두 번 틀리게 가르친다(A-9 오해의 근원).
3. **배포 스택이 리포보다 1커밋 뒤에 있는 것(`polly:SynthesizeSpeech` 미배포)을 언제 재배포로 닫을 것인가.**
4. **스택 파라미터 · Lambda env · SSM 이 서로 다른 Pod 세대를 가리킨다 — `sam deploy` 전에
   어느 값을 정본으로 할 것인가.**
5. **죽은 코드 — 제거 범위(OTA 가능분 / 네이티브 재빌드분)를 어디까지 잡을 것인가** +
   `DeductionCard` 판정('강사님께 물어보기' 기능 소멸의 물증).

---

## 1. sam deploy 가 지금 불가능하다

**관측**

Default 없는 파라미터 5개 — `VisualInputBucketName` · `DisplayJudgeConfidence` ·
`TrainingJudgeConfidence` · `DisplayPoseTolDeg` · `TrainingPoseTolDeg` — 는 **전부 죽은
Phase 31 것**이다. `backend/samconfig.toml:18` 의 `parameter_overrides` 는 3개만 준다:

```
parameter_overrides = "Stage=pilot VideoBucketName=sunity-motion-pilot-videos FirebaseSaParam=/sunity/motion/firebase-sa"
```

배포 스택에는 그 5개가 아예 없다 — `aws cloudformation describe-stacks --stack-name
sunity-motion-pilot` 의 Parameters 는 Stage / VideoBucketName / FirebaseSaParam /
RunpodAnalyzeUrl / RunpodAuthToken 5개뿐이고 `Visual*` 은 0개다.
Phase 31 자체는 사문이다 — `CALIBRATION.json` 이 `blocked:true`
(`insufficient_pass_samples:3<4`, `confidence_axis_non_discriminating`).

**왜 지금 판정이 필요한가**

실증이 한 달 뒤다. 그 사이 Lambda 코드를 고쳐야 할 일이 생기면 **여기서 멈춘다.**
죽은 트랙의 잔해가 살아 있는 백엔드의 배포 경로를 막고 있다.

**선택지**

| # | 무엇 | 결과 |
|---|---|---|
| A | 5개 파라미터에 Default 를 준다 | 템플릿 1곳 수정으로 배포 복구. 죽은 Phase 31 선언은 남는다 |
| B | 5개 파라미터와 딸린 Phase 31 리소스를 걷어낸다 | 템플릿이 실물과 일치. 변경 면적이 크고 배포 스택과의 drift 를 같이 봐야 한다 |
| C | `samconfig.toml` 의 override 를 5개로 늘린다 | 가장 작은 손. 죽은 값을 계속 넣게 된다 |

**판정 요청:** A / B / C 중 무엇으로 배포 경로를 여는가.

---

## 2. template.yaml 의 Runpod 파라미터 2개가 사문인데 틀린 것을 가르친다

**관측**

`backend/template.yaml:29-40` 의 `RunpodAnalyzeUrl` / `RunpodAuthToken` 은 **선언만 있고
템플릿 어디에서도 `!Ref` 되지 않는다.** 실제 env 는 SSM dynamic reference 로 들어간다
(`:342`, `:481` 의 `{{resolve:ssm:/sunity/motion/runpod-analyze-url}}`).

그런데 설명문이 지금도 이렇게 가르친다 (원문):

```
      RunPod 분석 서버의 POST /analyze 엔드포인트 URL.
      빈 문자열이면 PipelineFunction 이 자체적으로 NLF 추론 시도(폴백, Lambda CPU
      에선 NaN). 운영 배포 시 https://<pod-id>-8000.proxy.runpod.net/analyze.
```

두 번 틀렸다 — 백본은 RTMW 로 바뀌었고, 그 폴백은 배포 환경에서 ImportError 로 막혀 있다
(`backend/functions/pipeline/requirements.txt:1-4`). 이번 정리에서 고친 A-9(Pod 종료 절차)의
원안이 바로 이 문장 위에 서 있었다.

**왜 지금 판정이 필요한가**

Pod 을 띄우고 내리는 일이 매번 있고, 이 설명문을 읽은 사람이 "URL 을 비우면 폴백이 돈다"고
믿으면 종료 절차를 잘못 밟는다.

**선택지**

| # | 무엇 | 결과 |
|---|---|---|
| A | 파라미터 2개를 걷어낸다 | 사문 소멸. 배포 스택에 박제된 낡은 값도 같이 정리해야 한다(4번 건과 한 묶음) |
| B | 설명문만 정정한다 | 손이 가장 작다. 참조 0 인 선언은 남는다 |

**판정 요청:** 걷어낼 것인가, 설명문만 고칠 것인가.

---

## 3. 배포 스택이 리포보다 1커밋 뒤에 있다

**관측**

배포 스택 `LastUpdatedTime` = **2026-07-21T16:17Z**, `template.yaml` 마지막 커밋 = 2026-07-22.
그래서 32-16 이 넣은 `polly:SynthesizeSpeech` 권한이 배포본에 없다.

지금 안 깨지는 이유는 실분석이 Pod 에서 돌고 **Pod 이 자기 AWS 키로 Polly 를 부르기** 때문이다.
Lambda 경로로 음성을 만들 일이 생기면 그때 드러난다.

**왜 지금 판정이 필요한가**

1번이 풀리기 전에는 재배포 자체가 불가능하다 — 두 건이 같은 문에 걸려 있다.

**선택지**

| # | 무엇 | 결과 |
|---|---|---|
| A | 1번을 푼 직후 바로 재배포 | drift 소멸. 4번(Pod 세대 불일치)을 먼저 정해야 안전하다 |
| B | 실증이 끝난 뒤로 미룬다 | 실증 중 배포 사고 위험 0. drift 는 그대로 |

**판정 요청:** 재배포 시점을 언제로 잡는가.

---

## 4. 배포 스택 · Lambda env · SSM 이 서로 다른 Pod 세대를 가리킨다

**관측**

| 어디 | 값 |
|---|---|
| CloudFormation 스택 파라미터 `RunpodAnalyzeUrl` | `p56qusi8cgc91z` 세대 |
| Lambda env `RUNPOD_ANALYZE_URL` | `elevev58iv4mox` 세대 |
| SSM `/sunity/motion/runpod-analyze-url` | `elevev58iv4mox` 세대 |

그리고 `elevev58iv4mox` 주소는 **404** 다(직접 curl). Lambda env 를 CLI 로 바꿔 온 이력과
스택 파라미터가 3중으로 갈라져 있어, 누가 `sam deploy` 를 하면 **어느 값이 남는지 예측 불가**다.

**왜 지금 판정이 필요한가**

1번을 풀어 배포가 가능해지는 순간 이 불일치가 실제 사고가 된다.

**선택지**

| # | 무엇 | 결과 |
|---|---|---|
| A | SSM 을 유일 정본으로 하고 스택 파라미터를 걷어낸다(2번 A 와 한 묶음) | 세대가 하나로 수렴 |
| B | 배포 직전에 스택 파라미터를 현재 값으로 맞춘다 | 손이 작다. 다음 Pod 재생성 때 또 갈라진다 |

**판정 요청:** 정본을 SSM 으로 못 박을 것인가.

---

## 5. 죽은 코드 — 제거 범위 + DeductionCard 판정

**관측**

- 앱 고아 16파일 3,707줄, 즉시 제거 후보 2,991줄.
- **3D 스택 제거는 OTA 가 아니라 네이티브 재빌드**다 — 배포 경로가 다르다.
- `DeductionCard` 는 죽은 게 아니라 **'강사님께 물어보기' 기능 소멸의 물증**이라 별도 판정 대상이다.

**관측(누락 사실을 숨기지 않는다):** `260918-qm2-FINDINGS.md` 에는 `죽은코드` 절이 없다.
이 절의 수치(앱 고아 16파일 3,707줄, 즉시 제거 후보 2,991줄, 3D 스택 제거 = 네이티브 재빌드)는
`260918-qm2-CONTEXT.md` §묶음 C-5 에서 옮긴 것이고 **파일별 목록은 리포 안에 없다**.
FINDINGS 에 있는 파일별 항목은 `app/src/lib/resultSections.ts`(+ `__tests__/resultSections.test.ts`
348줄, 32-11 산물, 내보내기 5개 소비처 0, 테스트 11건은 지금도 통과) 1건뿐이다 —
**파일별 목록은 메인 세션이 첨부해야 판정이 가능하다.**

**왜 지금 판정이 필요한가**

belle 이 "정리가 안 되는 자리"로 지목한 곳이다. 다만 belle 이 "목록만"이라 했으므로
이번 정리에서는 **아무것도 제거하지 않았다.**

**선택지**

| # | 무엇 | 결과 |
|---|---|---|
| A | OTA 가능분만 먼저 제거 | 재빌드 없이 즉시 반영. 3D 스택은 남는다 |
| B | 네이티브 재빌드까지 한 번에 | 전부 정리. 실증 전 빌드 리스크를 진다 |
| C | 실증 이후로 전면 보류 | 실증 중 변경 0 |

**판정 요청:** 제거 범위를 A / B / C 중 무엇으로 잡는가. 그리고 `DeductionCard` 는
되살릴 기능인가, 같이 걷어낼 잔해인가.

---

## 관련

- 실측 원문 = `.planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-FINDINGS.md`
- 잠긴 결정 = `.planning/quick/260918-qm2-doc-truth-repair-18/260918-qm2-CONTEXT.md` §묶음 C
- 판정 원장 = `.planning/STATE.md` — "미종결 트랙 판정 원장 (2026-09-18, quick-260918-qm2)"
- `backend/template.yaml` 은 이 판정 전까지 무접촉.

---

## 5-A. 죽은 코드 파일별 목록 (판정 재료)

실측 요약: 앱 고아 파일 16개 3,707줄 + 백엔드 사문 3건. 즉시 제거 후보 2,991줄, belle 판정 필요 4건. DeductionCard 는 죽은 게 아니라 기능소멸(강사님께 물어보기)의 물증이고, 3D 스택 제거는 OTA 가 아니라 네이티브 재빌드다.

**제거하지 않았다. belle 판정용 목록이다.**

### [보류] app/src/components/DeductionCard.tsx (+GoalGaugeBar.tsx, MissionBadge.tsx, lib/gaugeGeometry.ts) — 716줄

import 0 은 맞으나 기능이 기각된 게 아니라 배선만 끊겼다. 커밋 a5089955(2026-09-09) 본문이 '사용자 담기 질문(userQuestions) — 감점 카드별 강사에게 물어보기로 담던 것. 시안에 그 진입점이 없어 항상 빈 배열'이라 직접 적고 있고, 09-09 마감 메모가 이를 '중복 제거가 아니라 기능 소멸이라 belle 이 알아야 한다'며 belle 판정 대기로 남겼다. 09-18 유령판정 원장 9건(HANDOFF §8)에 이 건은 없다 = 아직 답을 못 받았다. GoalGaugeBar/MissionBadge/gaugeGeometry 는 DeductionCard 만이 유일한 소비처라 같이 묶여 산다.

**근거:** grep -rn "components/DeductionCard'" app/src → 0건. DeductionCard.tsx:94 `const ASK_COACH_LABEL = '강사님께 물어보기'`, :236-241 버튼. types/analysis.ts:696 `source: 'safety'|'mission_stuck'|'unmeasured'|'user'` 중 'user' 생산자 앱 내 0건. gaugeGeometry 소비처 = GoalGaugeBar.tsx:23, DeductionCard.tsx:39 뿐. git show -s a5089955 본문.

### [죽었다] app/src/components/PoseViewer3D.tsx + PoseViewer3DSmokeScreen.tsx + lib/joints.ts + lib/normalizePose3d.ts — 1,109줄

result.tsx 통합이 2026-06-21 커밋 eafd76da 'remove broken 3D viewer'로 명시적으로 제거됐다. 그 뒤 15개월간 재배선 0. 게다가 되살릴 재료 자체가 없다 — 저장 joints3d 의 z 가 전부 0(2026-09-18 실측, 로컬 doc 8건 z std 0.0000)이라 3D 뷰어는 평면만 그린다. joints.ts 는 PoseViewer3D 전용 리셰이퍼이고(자기 docstring:13 이 그렇게 적는다), normalizePose3d 는 joints.ts 만이 소비한다.

**근거:** git log -S "components/PoseViewer3D'" -- app/src/app/analysis/result.tsx → eafd76da(2026-06-21) 'fix(20): ... remove broken 3D viewer'. grep 'from .*/joints' app/src → 0건. grep "normalizePose3d'" → lib/joints.ts:21 단 1건. lib/joints.ts:13 '// PoseViewer3D 가 joints null → return null'. 메모리 joints3d-is-2d-z-is-all-zero.

### [죽었다] app/package.json — three ^0.184.0 / @react-three/fiber ^9.6.1 / @react-three/drei ^10.7.7 / expo-gl ~16.0.10 (node_modules 45MB)

이 네 패키지를 import 하는 곳은 PoseViewer3D.tsx:29-30 과 PoseViewer3DSmokeScreen.tsx:20 둘뿐이고 둘 다 위 항목의 죽은 서브트리다. 다만 ★제거 리스크가 크다: app/ios/ 가 prebuild 된 bare 프로젝트이고 ExpoGL 이 Podfile.lock 에 5곳 박혀 있다. expo-gl 은 autolink 네이티브 모듈이라 지우면 바이너리가 바뀐다 — OTA 로 못 내보내고 EAS 재빌드 + TestFlight 재배포가 필요하다(runtimeVersion policy=appVersion, 현재 1.2.4). 실증이 약 한 달 뒤이므로 '지금 할 일인지'는 belle 이 정해야 한다. 참고로 JS 번들에는 이미 안 실린다(Metro 는 도달 가능한 모듈만 묶는다) — 이득은 네이티브 바이너리 축소와 의존성 정리뿐이다.

**근거:** grep -rn "from 'three'|@react-three|expo-gl" app/src → 실제 import 는 PoseViewer3D.tsx:29,30 / PoseViewer3DSmokeScreen.tsx:20 뿐(나머지는 전부 주석). ls app/ios → 존재. grep -n ExpoGL app/ios/Podfile.lock → :239,:2216,:2351,:2352,:2543. app/app.json:7 runtimeVersion policy appVersion. du -sh: three 38M, @react-three 5.2M, expo-gl 1.9M.

### [죽었다] app/src/components/ReferenceCornerSection.tsx + PoseCompareFrames.tsx + PoseCompareViewer.tsx + lib/visualCards.ts + api.ts:132 requestRotationVideo — 930줄

Phase 31 참고코너(교정된 자세 이미지 + 회전 영상) 앱 표면 전체다. belle 이 2026-07-20 에 회전을 'hidden' 으로 못박았고, 09-09 시안이 섹션째 걷어냈다. 커밋 a5089955 본문이 '참고코너 전체 ... 남아 있던 것은 아무도 안 읽는 S3 재서명 두 벌'이라 명시한다. PoseCompareFrames/PoseCompareViewer 는 ReferenceCornerSection 만이 소비하고, visualCards.ts 는 그 카드 상태머신이라 지금 참조가 자기 테스트 1개뿐이다. requestRotationVideo 는 정의만 있고 호출부 0.

**근거:** grep -rn "components/ReferenceCornerSection'" app/src → 0건. ReferenceCornerSection.tsx:30,31 이 PoseCompareFrames/Viewer 의 유일 import. grep -rn visualCards app/src → lib/__tests__/visualCards.test.mjs 뿐. grep -rn requestRotationVideo app/src → lib/api.ts:132 정의만. 커밋 a5089955 본문.

### [죽었다] app/src/components/ScoreBreakdownSection.tsx — 316줄

같은 일(기준 100 → 감점 행 → 종합 N점 투명 tally)을 components/result/ResultPointsCard.tsx 가 그대로 한다. 대체 사실이 커밋 a5089955 본문 '남긴 것' 절에 명시돼 있다 — '투명 감점합산 — ScoreBreakdownSection 은 없앴지만 tally 자체는 ResultPointsCard 가 그대로 한다. 실물 확인함.' 즉 belle 불변식(투명 감점합산)은 지켜지고 껍데기만 남았다.

**근거:** grep -rn "components/ScoreBreakdownSection'" app/src → 0건. components/result/ResultPointsCard.tsx:4 '이 카드는 앱에 이미 있던 점수 계산 내역(ScoreBreakdownSection)과 같은 것을...'. ResultPointsCard 소비 = app/analysis/result.tsx:35. 커밋 a5089955 본문 '남긴 것' 1항.

### [죽었다] app/src/components/SummaryCard.tsx — 153줄

components/result/ResultSummaryCard.tsx 가 대체했고 그쪽이 result.tsx:33 에서 실제 렌더된다(:1678). 09-09 시안 1 의 요약 카드에는 SummaryCard 가 갖고 있던 '자세히 보기' 펼침이 없고, 그 역할은 교정포인트 탭이 통째로 가져갔다(a5089955 본문). 상위 결정(belle: 중복은 옮기는 게 아니라 지운다)으로 대체된 것이지 미완 작업이 아니다.

**근거:** grep -rn "components/SummaryCard'" app/src → 0건. app/analysis/result.tsx:33 import ResultSummaryCard, :1678 렌더. 커밋 a5089955 본문 '요약 카드 자세히 보기 펼침 상태 — 시안 1 의 요약 카드엔 펼침이 없다'.

### [죽었다] app/src/components/PartChipsRow.tsx — 144줄

09-09 시안이 걷어낸 '옛 셸 부속'에 커밋 본문이 이름째 올려놨다. 부위 단위 탐색은 4탭 구조의 교정포인트 탭(ResultPointsCard/ResultMomentList)이 가져갔다. 다만 tally·부상위험과 달리 커밋이 '남긴 것'으로 후속 대체를 명시하지 않았다 — 부위 칩 UI 자체가 필요하면 belle 이 꺼낼 여지는 있다. 코드 자체는 소비처 0 이고 KeypointOverlay.tsx:205 의 'PartChipsRow 가 대체한다'는 주석은 이제 낡은 서술이다(문서-코드 불일치 1건).

**근거:** grep -rn "components/PartChipsRow'" app/src → 0건. 커밋 a5089955 본문 '옛 셸 부속 — OctagonScore / SummaryCard / DeductionCard / ScoreBreakdownSection / InjuryRiskSection / PartChipsRow 배선과 ... 일체'. 낡은 주석 = components/KeypointOverlay.tsx:205, app/analysis/result.tsx:1327.

### [죽었다] app/src/lib/resultSections.ts — 339줄

결과 화면 '단일 세로 스크롤 10항 순서'(32-GATE-DECISIONS D-02)를 소유하던 순수 뷰모델이다. 그 전제가 09-09 재디자인으로 사라졌다 — belle 이 '탭마다 한 화면, 스크롤이 거의 없으'라고 정해 4탭 구조가 됐고 커밋 a5089955 와 32c22a10 이 result.tsx 에서 이 모듈 배선을 걷어냈다. 지금 남은 소비처는 자기 테스트 파일 1개뿐이다. 단 제거하면 lib/__tests__/resultSections.test.ts 도 같이 가야 하므로 node --test 총건수가 줄어든다는 점을 알고 지울 것.

**근거:** grep -rn resultSections app/src → lib/__tests__/resultSections.test.ts:32 `from '../resultSections.ts'` 외에는 전부 주석. git log -S "lib/resultSections'" → 32c22a10, a5089955 가 제거. 09-09 마감 메모 'belle: 탭마다 한 화면'.

### [보류] backend/functions/reference-api/app.py — GET /reference Lambda (33줄) + template.yaml:301-327 라우트/함수 + :752 로그그룹

앱이 안 부르는 건 맞다 — api.ts 가 치는 경로는 /upload-url, /playback-url, /visual/rotation 셋뿐이고 기준 모션은 Firestore 를 직접 구독한다. 그러나 '죽었다'로 부르기 전에 docstring 을 읽어야 한다: lib/referenceMotions.ts:3-5 가 '지금은 Firestore 직접 구독, 나중에 백엔드 Lambda(GET /reference) 가 켜지면 이 파일 내부만 교체하면 됨(훅 시그니처 고정)'이라고 의도적 대기 상태임을 명시한다. 즉 사문이 아니라 예비 경로다. 게다가 Firestore 는 Spark 무료 플랜(읽기 5만/일 하드 캡)이라 수강생이 늘면 이 Lambda 로 갈아타는 것이 실제 출구다. 총 33줄로 유지비가 거의 없다.

**근거:** app/src/lib/api.ts:91,109,122,135 = 호출 경로 전부. app/src/lib/referenceMotions.ts:3-5 docstring. backend/functions/reference-api/app.py 전문 33줄. backend/template.yaml:301-327, :752. 소비처 grep: 앱·스크립트·테스트 통틀어 GET /reference 호출 0건(POST /reference/auto-register 는 별개 — backend/scripts/reactivate_new6_motions.py:124 가 실사용).

### [보류] backend/functions/pipeline/app.py:7930 split_angle 기하 게이트 (technique.py:49 required_split_deg)

함수 본문만 보면 '항상 False 라 절대 안 도는 분기'라 결함처럼 보인다. 그러나 바로 위 주석 7916-7928 이 왜 그런지 적어놨다 — belle 2026-06-29 '스코프 축소' 결정이다. Pod 실측에서 inter-thigh peak max-split 이 dynamic 동작(kip-up/elbow-twist/pdshape)의 fault/correct 를 변별 못 했고(antiparallel thigh 도 180° 로 saturate), 비-split 동작에서 위양성을 내므로 진짜 split 요구 동작에만 발화하도록 껐다. 주석이 '현재 어떤 recognizer 도 required_split_deg 를 set 안 함 → split 전면 미발화(infra 보존, 진짜 split 동작 지정 시 활성)'이라고 보존 의도를 명시한다. 재개 조건 = recognizer 가 진짜 split 동작에 required_split_deg 를 넣는 것. 한편 split_angle criterion 자체는 죽지 않았다 — Gemini vision 주입(deduction_engine)으로 프로덕션에서 실제로 감점을 낸다.

**근거:** backend/functions/pipeline/app.py:7916-7930 주석 원문 및 `if profile is not None and getattr(profile, "required_split_deg", None) is not None:`. technique.py:49 필드 정의, :115 / gemini_technique_recognizer.py:234,258,371,438 전 생성지점 None. 같은 사실을 pipeline/app.py:2586, 2765 주석이 '사문'이라 부르며 fail-closed 근거로 사용. 살아있는 경로 = evals/realfixture/replay.py:1233 'no_sample_vision_injected_or_peak'.

### [보류] Phase 31 Visual 백엔드 — backend/functions/visual-{request,worker,dispatch}/ + template.yaml VisualQueue/DLQ/알람 9종/로그그룹 3종 + backend/tests/phase31/ 12파일

앱 쪽 소비처는 오늘 실측으로 0 이다(위 참고코너 항목). 배포 쪽은 2026-09-09 실측 기록이 '배포된 Lambda 는 5개뿐, Visual 3종 없음, 스택 파라미터에 VisualJobsEnabled 자체가 없음'이라고 말한다 — 다만 그 재측정을 오늘 못 했다: cloudformation:ListStackResources 와 lambda:GetFunctionConfiguration 이 모두 AccessDenied 다. 근거의 절반이 인용이므로 '죽었다'로 단정하지 않는다. 그리고 제거 규모가 크다(Lambda 3종 + 알람 9종 + 테스트 12파일). 메모리가 '되살리는 것은 belle 이 먼저 꺼낼 때만'이라 적고 있으니 판단을 belle 에게 올리는 것이 맞다.

**근거:** aws cloudformation list-stack-resources --stack-name sunity-motion-pilot → AccessDenied(오늘 실행). aws lambda get-function-configuration --function-name sunity-motion-pilot-visual-request → AccessDenied. 배포 0건 근거는 메모리 phase31-visual-assets-never-deployed 의 2026-09-09 실측 인용(문서 근거, 오늘 재검증 불가). 리포 실측: backend/functions/ 에 visual-dispatch/visual-request/visual-worker 존재, template.yaml:403-772 Visual 리소스 20여개, tests/phase31 12파일. 앱 소비처 0 = grep requestRotationVideo 호출부 0.


### 죽어 보이지만 남겨야 하는 것 (오탐 주의)

- components/InjuryRiskSection.tsx — 파일 전체가 죽어 보이지만 아니다. 컴포넌트 함수(:129 InjuryRiskSection)만 미사용이고, 같은 파일의 riskFlagCopy(:80)/topRiskFlag(:87)를 result.tsx:40 이 import 해 요약 카드 warning 으로 쓴다. 커밋 a5089955 본문 '남긴 것' 2항이 이 분해를 명시적으로 기록했다. 파일 삭제 금지.
- components/OctagonScore.tsx — result.tsx 에서는 09-09 에 걷혔지만 홈 탭이 쓴다((tabs)/index.tsx:15 import, :275 렌더). 커밋 본문의 '옛 셸 부속' 목록에 이름이 있어 죽은 것으로 오인하기 쉽다.
- components/ZoomPinchLayer.tsx — 'components/ZoomPinchLayer' 문자열로 grep 하면 0 이 나오지만 형제 파일이 './ZoomPinchLayer' 로 부른다(VideoCompare.tsx:61, RenderedComparePlayer.tsx:85). 상대경로 import 를 놓친 오탐 사례.
- lib/deductionLabels.ts — DeductionCard 가 쓰던 모듈이라 같이 죽은 것처럼 보이나 살아 있다(result.tsx:72, DeductionDetailSheet.tsx:48, VideoCompare.tsx:54). DeductionCard 묶음을 지울 때 함께 지우지 말 것.
- backend/functions/reference-auto-register/ — 이름이 reference-api 와 붙어 있어 같이 묶기 쉬우나 실사용 소비처가 있다(backend/scripts/reactivate_new6_motions.py:124 가 POST /reference/auto-register 를 친다 + tests 3파일). 정은지 기준 모션 재등록 경로다.
- lib/__tests__/gaugeGeometry.test.ts · resultSections.test.ts · visualCards.test.mjs — 원본을 지우면 동반 삭제 대상이지만, 그 순간 node --test 226건 게이트의 건수가 줄어든다. 게이트 수치가 떨어진 이유를 기록하지 않으면 다음 세션이 회귀로 오인한다.
- backend/tests/phase31/ 12파일 — Visual 백엔드를 남기기로 하면 이것도 남는다. 반대로 지우기로 하면 4835건 게이트 수치가 크게 움직이므로 같은 이유로 원장에 사유를 적고 지울 것.
- required_split_deg 필드(technique.py:49)와 그 전 생성지점의 None — '전부 하드코딩 None' 은 결함이 아니라 belle 2026-06-29 결정의 구현이다. 값을 채우는 recognizer 를 만들기 전에는 건드리지 말 것.
