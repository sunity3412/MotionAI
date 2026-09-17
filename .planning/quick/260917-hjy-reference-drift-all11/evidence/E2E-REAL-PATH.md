# 실측 — 앱 전 경로 E2E (회전 묶음 배포 후, 2026-09-17)

belle 지시: *"E2E 돌려."*

**결론: 87점. 로컬 예측(87)을 실제 파이프라인이 그대로 냈다.**
지금까지는 채점 코드를 직접 호출해 검증했고, 이번이 **앱→Lambda→Pod 전 경로**를 태운 첫 실측이다.

Pod `9t9mbgax2f0i3e` (RTX PRO 4500 Blackwell) · `/health` envFlags 에
**`ROT180_INVERSION_ENABLED: true`** 확인 · `start_server.sh` md5 가 리포 정본과 일치
(`e4790f167657db76fbac973f55e81905`) · Lambda `RUNPOD_ANALYZE_URL` 을 이 Pod 으로 동기화.

입력 = belle pdshape 영상(09-14 와 **같은 파일**), mode1, reference `ref-pdshape`.
경로 = `backend/scripts/e2e_app_path.py` (upload-url → Firestore 문서 먼저 → S3 PUT).

---

## 1. 결과 — 60점 → 87점

| 항목 | 09-14 (회전ON / 옛 기준) | **09-17 (묶음)** |
|---|---|---|
| overallScore | 60 | **87** |
| angle 차원 | 38 | **87** |
| stability | 91 | 91 |
| 원감점 | −58.8 | **−13.3** |
| 감점 기록 | 6건 | **1건** |
| 억제 기록 | 1 | 0 |
| visionVeto | applied | **applied** |
| unjudgedJoints | [] | [] |

남은 감점 1건: `angle_vs_reference__left_elbow` · 편차 11.09° · **−13.3점**.

로컬 예측은 87 이었고(측정오차 억제 미적용 하한), **실제 파이프라인도 87** 이다 —
Gemini 시각 판정·측정오차 억제·감점 엔진이 전부 돈 결과다.

## 2. 산출물 — 전부 생성됨

```
faultZoomStatus=done · 확대 카드 2장 (marked + plain 각 1벌)
coachStatus=done · coachAudio status=done (mp3 1건)
tips 3건 · spotCheck · dimensionExplanation · forceSignalsReport 생성
```

09-14 에 "회전이 렌더를 깬다"고 오진했던 자리다(그때는 Pod 을 완료 3분 만에 껐다).
**이번엔 후처리까지 기다려 확인했다** — 렌더/확대카드/음성 정상.

## 3. 단계별 소요 (stage_timing)

| 단계 | ms |
|---|---|
| **s3_download** | **752,814** ← 89MB, EU-RO-1 ↔ ap-northeast-2 교차 리전 |
| rtmw (회전 2패스, 182프레임) | 134,320 |
| fault_zoom | 114,990 |
| veto_collect (Gemini) | 81,773 |
| coach_dual | 26,814 |
| frame_extract | 27,632 |
| ref_fetch_download | 4,923 |
| dtw_scoring | 121 |

★ **분석 시간의 2/3 이 S3 다운로드다.** Pod 이 유럽(EU-RO-1)이고 버킷이 서울이라
89MB 에 12.5분 걸렸다. 한때 0바이트 임시파일만 보이길래 "멈췄다"고 오진할 뻔했는데,
boto3 의 임시 파일(`*.mp4.<suffix>`)이 따로 차고 있었다. **멈춘 게 아니라 느린 것이다.**

## 4. ★ 확대 카드 — 하나는 좋고 하나는 애매하다

### 카드 1 (`zoom_angle_vs_reference__left_elbow`, tier=confirmed) — **좋다**

두 패널이 **같은 자세(역립)** 에서 잡혔고 빨간 각도 표식이 **양쪽 다 실제 왼팔꿈치**에 있다.
belle 쪽은 팔이 거의 펴졌고 정은지 쪽은 접혀 있어 **감점 사유가 그림으로 그대로 읽힌다**.
(`deficitDeg=37.6`, `refMatch=dtw`, user 6.50s ↔ ref 6.83s)

### 카드 2 (`zoom_adv_left_shoulder`, tier=advisory) — **한쪽에만 표식**

게이트 로그가 명시적이다:

```
side=user joint=left_shoulder expected=armpit|back_waist|chest|shoulder
          action=pass       trail=unclear/unreadable   eye_calls=3
side=ref  joint=left_shoulder expected=(동일)
          action=suppressed trail=head/mismatch        eye_calls=2
요약: scope=render sides=4 eye_calls=9 pass=3 suppressed=1 unbound=0
```

- **기준 쪽**은 눈이 "머리"로 읽어 표식이 **억제**됐다 → 그 패널엔 표식이 없다.
- **학생 쪽**은 눈이 **"못 읽겠다"(unclear/unreadable)** 였는데 **action=pass** 다.

즉 **게이트가 판독 실패를 통과로 처리한다**(fail-open). 그 결과 비교 카드가
**한쪽에만 동그라미**가 있는 모양으로 배달됐다 — belle 09-04 "두 카드가 같은 팔"
계열의 읽기 혼란이 재발할 수 있는 형태다([[unmarked-zoom-card-reads-as-duplicate]]).

★ **원의 위치가 틀렸다고는 단정하지 않는다.** 처음엔 배경(화분)으로 보였으나 표시 없는
`__plain` 원본과 대조하니 그의 등/견갑 부근일 수 있고, 게이트 허용 목록에 `back_waist` 가
들어 있다. 좁은 크롭에서 좌표 오류와 크롭 폭을 가를 수 없다
([[tight-crop-cannot-separate-coord-from-crop]]) — **belle 눈 판정 대상**.

## 5. 운영 상태

```
Pod 종료 확인 (0대) · SSM pod-expected=down 복귀
Lambda RUNPOD_ANALYZE_URL 은 이제 죽은 주소 (= 종전 상태, 다음 시연 때 다시 동기화)
RunPod 잔액 $3.29 → $2.79
```

## 6. 산출물

```
evidence/e2e/
  doc_summary.json                          분석 doc 요약(점수·감점·카드·타이밍)
  server.log                                Pod 서버 로그(노이즈 제거)
  zoom_angle_vs_reference__left_elbow.png   카드1 (marked)
  zoom_angle_vs_reference__left_elbow__plain.png
  zoom_adv_left_shoulder.png                카드2 (marked)
  zoom_adv_left_shoulder__plain.png
```

분석 = `users/t58gzBEa61gAMZdq1UL0AA360hE3/analyses/63701c81623e4189bbc9538f2e06084f`
