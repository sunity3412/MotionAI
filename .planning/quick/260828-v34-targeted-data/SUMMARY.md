# v34 — 표적 데이터 첫 학습 (2026-08-28) · NOT PROMOTED

## 한 줄

**표적 fault 시연 6편을 라벨 100% 통과시켜 학습에 태웠고 train 은 완주했지만,
gates 는 FAIL — 겨냥했던 침묵 4동작이 여전히 결함 0건이다. 데이터를 넣는 것만으로는
안 풀렸다.**

## 판정 (v38-20260828-024523, checkpoint-76)

```
[eval18] power-spin           fault 멤버 결함 0건 — 짚기 실패
[eval18] peter-pan            fault 멤버 결함 0건 — 짚기 실패
[eval18] elbow-twist-sister   fault 멤버 결함 0건 — 짚기 실패
[eval18] pdshape              fault 멤버 결함 0건 — 짚기 실패
[determinism] real-kipup-correct  run1/run2 verdict 상이
[svg_spec] 결함 리포트 8건 중 wellformed 0건 (target_angle_deg=None, 0.00 < 0.5)
→ 기본 모드 exit=1, require-pass 모드 exit=1, NOT PROMOTED
```

**★내 해석 (belle 확인 전)**: 이번 판의 유일한 새 정보는 **"표적 데이터 6편으로는
침묵 4동작이 안 열린다"** 는 반증이다. 08-26 LR 실험이 세운 가설(잔여 침묵 = 표적
데이터 공백)이 **이번 실측으로 지지받지 못했다.** 다만 표본이 작다 — 동작당 1~2편이고,
평가 동작과 정확히 같은 동작의 fault 가 아닌 것도 섞여 있다. "데이터가 원인이 아니다"
로 뒤집기 전에 아래 미측정 항목부터 재야 한다.

**svg_spec 축은 새 결함**: 결함 리포트가 8건 나왔다(= 전역 침묵은 아님). 그런데 그
8건 전부 `target_angle_deg` 가 None 이라 형식 게이트에서 0/8 로 죽었다. 이건 침묵과
다른 축이고, **먼저 볼 값이 싸다** — 리포트는 나오는데 수치 슬롯만 비는 것이므로
학습 데이터의 해당 필드 충족률부터 확인할 것.

## 사이클 회계

```
accepted 302 · new_labeled 5 · rejected(judge 35 / parse 24 / contract 6)
sft_wall 10,147s (2h49m) · est_gemini_calls 10
라벨 6/6 accepted: peter-pan fault(9) · Elbow-Grip-Spin(9) · Handspring(8)
                   fault-demo B5CJY(9) · 파워스핀 실수(9) · Tuck-Spin(10)
```

## 이번 판에서 뚫은 관문 (전부 실측, 스크립트에 박제됨)

| 결함 | 실측 | 조치 |
|---|---|---|
| RTMW 가 CPU 로 돌고 있었다 (08-27 도 동일) | GPU 0%, `RTMW_DEVICE` 미주입 = 조용한 cpu 디폴트 | 사이클 스크립트가 직접 export. `.bashrc` 박제는 새 컨테이너에서 소멸 |
| ORT CUDA EP 미탑재 | `onnxruntime-gpu` 무핀 → 1.29 + rtmlib 이 CPU 판 동반 → providers=[Azure,CPU] | 1.22 핀 + CPU 판 제거, **CUDA EP 없으면 rc=5 로 죽는 게이트** |
| 결정론이 14배 느리다 | A/B: ON 1.92fps / OFF 27.48fps (영상 1편 78분 → 5편 45분) | 라벨 경로에서 제거. 옵션값이 ORT 1.19.2 기준이라 1.22 에서 conv fallback |
| 병합본이 조용히 잘렸다 | **볼륨 156G / 쿼터 150G** → 샤드 3/4, index 없음 | 미승격 `-merged` 3개 삭제(156G→110G). **디스크 여유·병합 완결성 검사 추가** |
| 병합본에 비전 전처리기 누락 | Qwen3-VL 은 VLM — preprocessor/video_preprocessor/chat_template 필요 | 토크나이저 복사에 3종 추가 |

## 다음 판 전에 잴 것 (권장 없음 — 이걸 재야 답이 나온다)

1. **svg_spec 축**: 학습셋 리포트 행의 `target_angle_deg` 충족률. 교사가 이 필드를
   안 채우고 있으면 모델 탓이 아니다. (싸고 빠름 — GPU 불필요)
2. **표적 데이터가 실제로 실렸나**: distill 210행 중 이번 6편이 만든 행 수와,
   그 행들이 침묵 4동작의 결함을 가르치는지. 08-26 실측은 "결함행 0~1개"였다.
3. **누수가드 확인**: eval18 의 4동작과 이번 수집분이 같은 동작인지. 다른 동작이면
   이번 판은 애초에 그 축을 못 건드린 것이다.

## 잔여물

Pod `f1futqhr1nd5mm` terminate 완료(0대), 잔액 $5.18. 볼륨 126G/150G —
**다음 사이클 전 여유 확보 필요**(병합본 1벌 = 17G).
launchd `com.sunity.podhunt` / `com.sunity.cyclewatch` 는 unload 상태.
