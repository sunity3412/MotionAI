# phase22 v6 — belle 아침 브리핑 (2026-07-16 새벽 작업)

## TL;DR
- **v6 코드(교사 밀도 A + 믹스 재균형 B + 좌표 descope C1) 완성·테스트·push 완료** (273 pass, 무회귀 0).
- **밀도 레버 3종 전부 밤새 검증** — 결론: **프롬프트로도, 2교사로도 밀도를 크게 못 올린다**(영상 내용 + 프레임 한계). **v6의 진짜 레버는 B+C1 재균형**(코드 완료, SFT로만 검증 가능 = Pod 필요).
- **GPT 2교사(terra) 수집 149/149 완주, 오류 0** — terra가 결함 추가한 영상 **13개(그중 8개는 Gemini가 놓친 정타 복구)**. 모두 정적·자세 결함(split_angle/limb_extension/pole_gap). 데이터 S3 보존.
- **다음 = Pod 켜서 SFT v6** (belle 결정 필요: terra 13영상 union 병합 여부 + 지금 assemble→SFT 갈지).

## 밤새 검증한 것 (belle "확실히 해줘" 요청대로)

### 1. 프롬프트 밀도(A) = 실패 확정
새 "결함 다 짚어라" 프롬프트로 Gemini 재라벨 → 실제 영상 4개: 더촘촘 **0** / 동일 3 / 성김 1. Gemini는 격려한다고 결함을 더 보지 않는다(인지한 만큼만). median 1은 **대부분 영상이 잘 된 수행(정타)**이라 결함이 원래 적은 것.

### 2. GPT 교사 — 모델별 실측
- **gpt-4o(구형): 폴 영상 거부** ("I can't assist with that" — 콘텐츠 정책). 못 씀.
- **gpt-5.6 계열: 거부 안 함.** belle 리서치대로 **sol=정밀 자세분석**(우리 런타임 주분석기 후보, 비쌈, 보수적) / **terra=일반 피드백**(쌈, 약간 더 적극 flag) / **luna=전처리**.
- **sol vs terra A/B** (Ayesha 결함영상 / Allegra 정타):
  - terra: Ayesha 2 / Allegra 0
  - sol: Ayesha **0** / Allegra 0  ← sol이 더 보수적("109도 V다리는 이 변형에 충분"이라 안 짚음)
  - **둘 다 정타 위양성 0 + 기술조건부 판정 정확.**
- **판단: union 2교사 = terra** (역할=Gemini 놓친 것 잡기=재현율↑, terra가 더 기여 + 훨씬 쌈). **sol은 나중에 제품 런타임 주분석기 후보로 보류.**

### 3. terra 2교사 수집 결과 (149영상 전체)
- terra>gemini **13** / ==70 / <gemini 66 (전체 fault: gemini 147 vs terra 47).
- **terra는 프레임(정지영상)만 봐서 동작(모션) 결함은 못 잡고 정적·자세 결함만 잡음** → Gemini(네이티브 영상) 대비 전체적으론 성김. 하지만:
  - **13영상에 결함 추가**(split_angle/limb_extension/pole_gap = 정지프레임에 보이는 자세 결함)
  - **8영상은 "복구"**: Gemini가 정타(0)로 놓친 걸 terra가 진짜 결함 발견 (pole-split 3, Inverted-split 2, chopper/invert/geumgangmakgi 등)
- **가치 = 모듬 밀도는 아니고 "선택적 + 8복구".** 저위험(terra 결함은 근거/좌표 있음).

## 결론 & 추천

**밀도는 재라벨로 크게 못 올린다가 확정.** v6는 **B+C1 재균형**(perturb 214행 익사 제거 → fault 신호 22%→40%)에 달렸고, 이건 **SFT로만 검증** 가능.

**추천 다음 스텝:**
1. **terra 13영상 union 병합** (저위험, 8복구는 fault 영상 80→88로 늘려 밸런스도 개선) — 정합성 있게 오늘 belle과 함께.
2. **v6 assemble** (Gemini 기존 라벨 + terra 13추가 + B+C1 재균형, build_jsonl `include_perturb=False`).
3. **Pod 켜서 SFT v6** (새 Pod + 같은 네트워크 볼륨, ~3.5h) → 병합 → 게이트 판정. ← **v6가 되는지 아닌지 진짜 답은 여기서.**

**belle 결정 필요:** (a) terra 13 union 병합할지 (추천: yes, 저위험) (b) 지금 assemble→Pod SFT 진행할지.

## 산출물 위치
- terra 수집: `s3://.../training/phase22/v6_terra_collect_20260716.jsonl` + 이 폴더 `overnight-artifacts/`
- 스크립트: `overnight-artifacts/{collect_terra,gpt_teacher_test,relabel_faults}.py`
- v5 학습셋(참고): `overnight-artifacts/`엔 없음, S3 `training/phase22/jsonl/`

## 잡음/주의
- **OpenAI 키 SSM 개행 제거함**(`/sunity/motion/openai-api-key`, 붙여넣기 개행이 헤더 깨뜨렸던 것 fix).
- **키가 에러 트레이스에 1회 노출됨**(belle 본인 세션 기록) — 신경쓰이면 회전 권장.
- **Pod terminated**(belle) — 네트워크 볼륨 생존, SFT 때 새 Pod+볼륨.
- 로컬 venv(google-genai/openai/boto3): 세션 스크래치라 새 세션엔 재설치 필요.
