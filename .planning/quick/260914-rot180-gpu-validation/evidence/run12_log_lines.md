# 런1·2 서버 로그 — 세션 중 전사본 (원본 유실)

★ **`start_server.sh:51` 의 `> /tmp/runpod_server.log` 는 재기동마다 로그를 truncate 한다.**
플래그를 켜려고 서버를 재기동한 순간 런1·2 의 로그가 사라졌다. 아래는 사라지기 전에
세션에서 읽어 전사해 둔 줄이다. 판정에 쓰는 수치(붕괴·뼈위반·점수·unjudged)는 전부
Firestore doc(`docs/*.json`)에서 나오므로 실제 손실은 없다.

**교훈**: Pod 로그는 **종료 전**이 아니라 **재기동 전**에 내려받아야 한다.

---

## 런1 (ROT180 off) — analysis 09ae90ad953b4d60b36cd23c92f46ba9

```
pr_inversion detect is_inverted=True ratio=0.705 run=15 valid=149/182
pr_inversion applied=true replaced=182/182 second_pass_ms=10918
stage_timing stage=s3_download                  elapsed_ms=4231
stage_timing stage=gemini_upload_prefetch_submit elapsed_ms=0
stage_timing stage=frame_extract                elapsed_ms=29042
stage_timing stage=rtmw                         elapsed_ms=147562   ← Blackwell cold JIT 포함
stage_timing stage=scene_finder                 elapsed_ms=0
stage_timing stage=recognizer                   elapsed_ms=452
stage_timing stage=ref_fetch_download           elapsed_ms=2994
stage_timing stage=dtw_scoring                  elapsed_ms=142
stage_timing stage=veto_collect                 elapsed_ms=10050
stage_timing stage=assemble_misc                elapsed_ms=3
stage_timing stage=firestore_complete           elapsed_ms=3123
stage_timing stage=coach_dual                   elapsed_ms=84156
stage_timing stage=coach_hook                   elapsed_ms=13869
stage_timing stage=coach_audio                  elapsed_ms=10509
```

사용 모델(기동 로그): `GEMINI_MOMENT_MODEL: gemini-3.8-flash`

## 런2 (ROT180 off, 재현 확인) — analysis 62eac2bbef594c7ab08db128baa5b9d9

```
pr_inversion detect is_inverted=True ratio=0.705 run=15 valid=149/182   ← 런1 과 동일
pr_inversion applied=true replaced=182/182 second_pass_ms=10922
stage_timing stage=s3_download         elapsed_ms=6673
stage_timing stage=frame_extract       elapsed_ms=29090
stage_timing stage=rtmw                elapsed_ms=22253    ← JIT 이후 정상 속도
stage_timing stage=scene_finder        elapsed_ms=12198
stage_timing stage=recognizer          elapsed_ms=103
stage_timing stage=ref_fetch_download  elapsed_ms=1975
stage_timing stage=dtw_scoring         elapsed_ms=143
stage_timing stage=veto_collect        elapsed_ms=8391
stage_timing stage=assemble_misc       elapsed_ms=3
stage_timing stage=firestore_complete  elapsed_ms=2942
```

**Blackwell cold JIT 실측 = 147.6s − 22.3s ≈ 125s.** 메모리
`rtmw-blackwell-lean-bootstrap` 의 "첫 추론 ~127s PTX→SASS" 와 일치. 컨테이너 수명 동안
1회만 든다(드라이버 ComputeCache).
