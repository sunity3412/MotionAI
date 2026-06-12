# Phase 17 — Gemini Vision 4 영역 + Eval/Guardrail (Promptfoo local eval)

본 디렉토리는 belle / Claude 가 PR 작성 전 수동 로컬 실행하는 Promptfoo eval 박제다.

## 본 plan 의 범위 (W6 정합)

- 본 plan = **local eval** (수동 실행).
- 임계값 미달 시 belle 가 PR 작성을 보류 (수동 게이트, 자동 block 0).
- **CI 자동 게이트 (.github/workflows/phase17-evals.yml) 는 본 Phase 17 scope 밖** —
  별도 후속 plan ("Phase 17C — eval CI integration") 으로 진입.
- 본 README / promptfooconfig.yaml 에 PR pre-merge 자동 block 표현 박제 0건.

## 디렉토리 구조

```
backend/evals/phase17/
├── README.md                       # 본 문서 (실행 절차)
├── promptfooconfig.yaml            # Promptfoo config (local eval)
├── dataset/
│   ├── reference_dataset.yaml      # 30-entry 영역 × 시나리오 매트릭스
│   └── labels.json                 # belle/정은지/강사 라벨링 sheet
└── assertions/
    ├── objectivity_reject.py       # E1 객관성 reject regex
    ├── ipsf_routing.py             # E2/E3 IPSF 명칭 + routing_branch 매치
    └── coach_tone.py               # E4 강사 보조 톤 binary pass
```

## 사전 준비

1. Promptfoo 설치:
   ```bash
   npm install -g promptfoo
   # 또는 npx promptfoo eval --config promptfooconfig.yaml
   ```
2. 환경변수 박제:
   - `GEMINI_API_KEY` (Google AI Studio belle 키).
   - `FIREBASE_SA_PATH` (Firestore 박제 시).
   - (선택) `AWS_PROFILE` — S3 reference 영상 다운로드 시.

## 실행 절차

```bash
cd backend/evals/phase17
promptfoo eval --config promptfooconfig.yaml
```

결과는 stdout 에 영역별 PASS rate + 실패 case 박힌다. Promptfoo web UI 로 시각화:

```bash
promptfoo view
```

## 임계값 (수동 검사 — 미달 시 PR 작성 보류)

| Dimension | 임계값 | 출처 |
|-----------|--------|------|
| E1 (객관성) | 100% | AI-SPEC §5 / §6 G1 |
| E2 (IPSF 명칭 매치) | ≥ 90% | AI-SPEC §5 |
| E3 (routing_branch 정확도) | ≥ 90% | AI-SPEC §5 |
| E4 (coach tone binary + judge correlation ≥ 0.7) | ≥ 85% | AI-SPEC §5 |
| E5 (영역 C precision/recall) | ≥ 95% | AI-SPEC §5 |
| E6 (정은지 hard gate) | 100% | AI-SPEC §5 / PROJECT.md |
| E7 (영역 D 좌표 회귀) | ≥ 90% | AI-SPEC §5 |
| E8 (latency p95 ≤ 40s + per-call cost ≤ $0.08) | — | AI-SPEC §5 |

## 라벨링 진입 상태 (`dataset/labels.json`)

- **정은지 5건** — Plan 12 referenceKeypointReport 산출본 재사용. `label_status: labeled`.
- **나머지 25건** — TODO. 학원 파일럿 진입 시 belle 가 PR 로 추가.

## 비용

- 30 examples × 4 영역 ≈ 120 호출 = $1.80/PR (AI-SPEC §4b $2,200/년 정합).
- Promptfoo cache 박제 — 동일 (video, prompt) 조합 재호출 0.

## 자동 CI 게이트 (후속 plan)

본 plan 박제 X. 후속 plan ("Phase 17C — eval CI integration") 에서 박제 예정:

1. `.github/workflows/phase17-evals.yml` — promptfoo eval 자동 실행 박제.
2. PR comment bot — 실패 case 박제.
3. main branch protection — eval 통과 시 merge 허용 박제.

본 plan 의 정합 박제는 **로컬 eval config + 30 entry dataset + assertion 3개** 까지.

## 라이센스 & 의존성

- Promptfoo: MIT License (npm package).
- assertion scripts: Apache 2.0 (sunity_shared 와 동일 박제).
- Gemini API: belle 의 Google AI Studio 키 (별도 quota 박제).
