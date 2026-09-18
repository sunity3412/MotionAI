# 학원 실증 점검 카드 — 2026-09-18

## 지금 상태 (기동 후 기입)

| | |
|---|---|
| Pod | `{podId}` · GPU · 리전 · 시간당 비용 — 기동 후 채워넣기 |
| 서버 | `https://{podId}-8000.proxy.runpod.net` |
| 서빙 코드 | `8c64b941` (health 의 commitSha 로 확인됨) |
| Lambda | RUNPOD_ANALYZE_URL 동기화 완료 |
| SSM | pod-expected = **up** |
| 앱 OTA | `0dddb65f` preview/1.2.4 (강사 교정 v2 포함) |
| 회전 | ROT180_INVERSION_ENABLED = **ON** |

## 실증 직전 30초 점검

```bash
curl -s https://{podId}-8000.proxy.runpod.net/health | python3 -m json.tool
```

이 셋을 보세요:
- `"pipeline_loaded": true`
- `"poseEngine": "RTMWPoseEngine"`
- `"recognizer": "GeminiTechniqueRecognizer"`

**하나라도 빠지면 분석이 실패합니다** (폴백 없음).

## 앱에서 할 것

1. 앱 **완전 종료 후 재실행** (OTA 를 받아야 강사 교정 v2 가 보입니다)
2. 영상 업로드 → 분석
3. 결과 → 보완운동 탭 → "강사에게 확인할 점" 카드에 **입력 한 행**이 보이면 OTA 적용된 것

## 끝나면 반드시

**Pod 종료** — 안 끄면 시간당 $0.49 가 계속 나갑니다.

```bash
# Claude 에게 "Pod 종료해줘" 라고 하시면 됩니다. 수동이면 RunPod 콘솔에서 Terminate.
```
그리고 SSM `pod-expected` 를 `down` 으로.

Lambda `RUNPOD_ANALYZE_URL` 을 자리표시자 `https://pod-down.invalid/analyze` 로 되돌린다
(`aws lambda update-function-configuration` 은 병합이 아니라 치환 — 나머지 변수를 통째로 다시 넣는다).
**값을 지우거나 SSM `/sunity/motion/runpod-analyze-url` 을 삭제하지 말 것** — SSM 은 Type=String 이라
빈 값이 안 들어가고, `backend/template.yaml:342/481` 이 `{{resolve:ssm:...}}` 로 이 이름을 해석하므로
삭제하면 다음 `sam deploy` 가 그 자리에서 깨진다. 그리고 **Pod 이 없으면 분석은 어차피 실패한다** —
URL 을 비워도 CPU 폴백은 배포 환경에서 ImportError 로 막혀 있다
(`backend/functions/pipeline/requirements.txt:1-4`). 이 되돌리기는 '죽은 주소로 위임' 대신
'즉시 실패'로 만드는 것이지 분석을 살리는 것이 아니다.

## 알려진 제약 (실증 중 당황하지 않기)

- **Pod 이 EU, 버킷이 서울** — 영상이 크면 다운로드가 분석 시간의 상당 부분입니다.
  (2026-09-18 실측: 88.7MB 가 156초 — 아래 단계별 표와 같은 값입니다.
  종전 기록 752초는 재현되지 않았습니다.)
- **Pod 이 없으면 분석은 그냥 실패합니다.** 폴백 경로가 없습니다.
- 확대 카드·음성은 분석 완료 **후 3~5분** 더 걸려 만들어집니다. 바로 안 보여도 정상입니다.

---

## ✅ E2E 실증 완료 (2026-09-18 12:57)

앱과 동일 경로로 완주. `analysisId=31c0128cdb1b4b2db88972614d68ed86`

```
status        done
overallScore  100        (정은지 자기비교 = 만점, 어제와 동일)
dimensionScores  angle 100 · stability 84
elapsedSec    352
coachStatus   done  ·  coachAudio  done  ·  faultZoomStatus  done (카드 1장)
```

### 단계별 시간 (88.7MB 영상)

| 단계 | 시간 |
|---|---:|
| **s3_download** | **156.3s** ← 전체의 44% |
| veto_collect (Gemini) | 54.4s |
| recognizer (Gemini) | 33.6s |
| frame_extract | 29.2s |
| fault_zoom (확대카드) | 29.4s |
| scene_finder (Gemini) | 25.0s |
| **rtmw (GPU)** | **11.9s** ← 병목 아님 |
| ref_fetch | 5.7s |
| firestore | 2.6s |
| dtw_scoring | 0.1s |

**병목은 GPU 가 아니라 다운로드 + Gemini 3단계입니다.**
수강생 폰 영상(20~30MB)이면 다운로드가 40~50초로 줄어 **총 3~4분** 예상.

### 오늘 넣은 2단 게이트 — 라이브 확인

```
side=user joint=right_shoulder action=pass trail=shoulder/ok
side=ref  joint=right_shoulder action=pass trail=chest/ok
summary: sides=2 pass=2 suppressed=0 unbound=0
```

양쪽 1단 통과 → **2단이 안 돌았다. 설계대로다**(2단은 지우기 직전에만).
★ **2단 구제 경로 자체는 아직 운영에서 안 타봤다** — 지워지는 케이스가 나와야 보인다.

### 곁가지 관측 (실증 무관, 다음에 볼 것)

`userMarked=True` 인데 `refMarked=None` 이다. 게이트는 양쪽 다 `pass` 였으므로
**한쪽만 표시되는 원인이 게이트 말고 또 있다.** belle 이 09-18 에 본 "한쪽에만 동그라미"와
같은 모양일 수 있다 — 게이트를 고쳐도 안 없어지는 종류.
