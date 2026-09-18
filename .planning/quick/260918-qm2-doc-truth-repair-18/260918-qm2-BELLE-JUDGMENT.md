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
