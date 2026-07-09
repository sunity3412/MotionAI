# Phase 22 학습셋·모델 라이선스 감사 (LICENSE-AUDIT)

> FT-06 산출물. Due Diligence(투자 실사)·상업 출시 게이트 대비 문서.
> 근거: 22-CONTEXT D-04(belle 2026-07-06 확정) + NLM "LLM, Finetuning Guide"(belle 노트) + 22-NLM-EXTRACT §5·§11·§12.
> **작성 2026-07-09. 확정 라이선스 문구는 재조사 금지 — belle 확정본 그대로.**

---

## 1. 모델 라이선스 확정표 (belle 2026-07-06, 재조사 금지)

| 컴포넌트 | 역할 | 라이선스 | 상업 이용 |
|----------|------|----------|-----------|
| **MMPose RTMW / RTMW3D** | 포즈 추정(관절 좌표) | **Apache 2.0** | 무제한 |
| **Qwen 3.6-VL** (<35B) | 분석/추론 엔진 후보 | **Apache 2.0** | 무제한 |
| **InternVL 3.5** (1B~38B) | 분석/추론 엔진 후보 | 코드 **MIT** + LLM/Vision 백본 **Apache 2.0** | 무제한 (MAU·로열티 없음) |
| InternVL 3.5 241B-A28B (MoE) | (대형, 미사용) | Qwen License | 100M MAU 한도 조건 |

- 분석 엔진은 **Qwen 3.6 ↔ InternVL 3.5 중 bake-off로 하나 선택**(D-04). 둘 다 라이선스 클린이므로 **성능만으로 선정**.
- 참고(NLM): InternVL 3.5는 내부 LLM 백본으로 Qwen3를 채택 — 두 후보 모두 Qwen 계열 언어지능.

## 2. 금지 목록 (상업 출시 fence)

- **LLaVA 계열** — 상업 이용 불가. 사용 금지.
- **InternVL-U**(시각 생성/편집 통합 파생모델) — 가중치·코드는 MIT지만, 정렬 학습 코퍼스 **ScaleEdit-12M**이 **CC BY-NC-SA 4.0(비상업)**. 비상업 데이터로 학습된 모델은 파생물로 해석되어 비상업 제약이 전염될 법적 취약성.
  - **결론**: InternVL-U를 그대로 상업 서빙 금지. **아키텍처만 차용**(MMDiT 생성 헤드 구조) + **시각 생성 헤드를 자사 스포츠 데이터로 완전 재학습**해 법적 제약 우회 — v2 트랙(D-03). v1은 InternVL-U 미사용(픽셀 생성 없음, SVG 기하 스펙까지만).

## 3. 데이터 수집 정책 (Phase 22 학습 코퍼스)

- **usage = training-only-no-redistribution**: 수집 영상은 **학습 전용**. 재배포 없음, 앱 미노출, Mode1 reference와 별개.
- **provenance 원장**: `backend/training/data/manifest.json`(행별 source_url·channel·tier·license_evidence·vision_verdict) + 유튜브 `info.json` 사이드카(S3 fixtures/phase22/). 저작권 분쟁 시 출처 입증 근거.
- **사람 숫자 점수 라벨 영구 금지** — 버킷(정타/fault)만. 채점은 Phase 24 감점 엔진(불변).
- 출처 티어: 1순위 공식 대회 채널(IPSF·KPSA·KPSF·PSO·CzechPoleDance·PoleSportContest·USPSF), 2순위 강사/스튜디오(YouTube·Instagram), 개인 브로거·TV예능 제외.

### 3-1. Instagram 트랙 특수 주의 (ToS)
- IG 공개 릴스는 gallery-dl `/reels/` 경로로 접근(2026-07 확인). 다만 **Instagram ToS는 대량 스크래핑을 제약** — 로그인월·쿠키 인증·rate-limit 회색지대. 유튜브보다 법적 노출 큼.
- 완화: 학습전용·비재배포, provenance 기록, 공식/스튜디오·선수 본인(정은지=파트너 동의) 계정 위주, 개인 추정 계정 보류.

### 3-2. 미성년 프라이버시 플래그
- `@polesportkids`(키즈 대회 전용 채널)는 **기본 비활성(enabled=false)** — **미성년자** 영상은 프라이버시·동의 민감도가 성인보다 높음. 일반 대회 채널에도 주니어 부문 포함될 수 있음.
- **A9 법률 검토에 미성년 데이터 취급을 별도 항목으로 상정.** counsel 확인 전 미성년 전용 소스 harvest 금지.

## 4. 고객 데이터 동의 3겹 (D-12)

1. **파일럿**: 학원 참가 동의서 1장에 학습 활용 포함(오프라인 포괄).
2. **정식**: 처리방침 고지 + **가명처리(얼굴 블러 + 식별자 제거) 후 학습 활용** — 가명정보의 과학적 연구 목적 활용 구조. 모델은 포즈/모션만 학습, 얼굴 픽셀 불필요(anonymize.py가 적재 전 강제, 소급 불가).
3. **출시 전 법률 검토 1회 문서화** (DD 대비). 고지 문구 구현 = 온보딩 phase(SCENARIO 0.5).
- 매니페스트에 uid·사용자 식별자 필드 금지(video_hash·Firestore 경로 참조만).

## 5. 이월 항목 (A9 — 상업 출시 게이트)

- **유튜브/인스타 등 공개 영상의 학습 이용 법적 지위는 파일럿 리서치 용도로 유예 상태.**
- **본 감사 문서는 법률 자문(counsel) 서명 전까지 `release-clean`을 함의하지 않는다.** 상업 출시 게이트는 별도 — 출시 전 법률 검토 1회에 포함:
  1. 공개영상 학습 이용 최종 법적 판단
  2. InternVL-U 생성 헤드 자체 재학습 완료 확인(ScaleEdit 전염 차단)
  3. IG ToS 준수 방식 확정
  4. 미성년 데이터 취급 정책
  5. 가명처리·동의 구조 실사

---

*Phase: 22-custom-vlm-finetune · FT-06 · 2026-07-09*
