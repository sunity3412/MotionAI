# Pod D-15 재계측 커맨드 시퀀스 (quick-260714-hv4)

> Pod 실행은 이 plan 범위 밖 — 오케스트레이터가 로컬 커밋 push 후 SSH 로 직접 수행한다.
> 판정 기준(4 게이트 임계·비교식)은 불완화 — 프롬프트/디코딩 양식만 학습 분포에 정렬.

## 현 Pod 좌표

- Pod: `xkaejqz9u72osv` A100 80GB
- SSH: `ssh root@213.173.105.9 -p 43181`

## 0. 전제 — push + Pod pull

로컬(오케스트레이터):

```bash
rtk git push
```

Pod:

```bash
ssh root@213.173.105.9 -p 43181
cd /workspace/SunityMotion && git pull
```

## 1. 기존 legacy FAIL 아티팩트 백업 (필수 선행 — 덮어쓰기 소실 방지)

aligned 재계측도 같은 파일명 규약(`bakeoff_{model}_{run_tag}.json`, run_tag=run1/run2)을
쓰므로, 재계측 전 직전 legacy v4 FAIL 아티팩트를 반드시 옮겨둔다 (비교 근거 보존):

```bash
EVAL_OUT_DIR="${EVAL_OUT_DIR:-/workspace/eval_out}"
mv "$EVAL_OUT_DIR/phase22" "$EVAL_OUT_DIR/phase22_legacy_v4"
mkdir -p "$EVAL_OUT_DIR/phase22"
ls "$EVAL_OUT_DIR/phase22_legacy_v4"   # 백업 확인
```

## 2. 본판정 — aligned 재계측 (rp=1.0, 순수 정렬 효과 격리)

```bash
cd /workspace/SunityMotion/backend
PROMPT_MODE=aligned nohup bash training/sft/run_sft_gates.sh \
  /workspace/phase22_export/sft-run1/awq \
  > /workspace/sft_gates_aligned.log 2>&1 &
```

- 완료 마커: `GATES ALLDONE` (로그 tail 로 확인)

```bash
tail -f /workspace/sft_gates_aligned.log   # 진행 관찰
grep "GATES ALLDONE" /workspace/sft_gates_aligned.log
```

- 판정: 로그 마지막 줄 `GATES ALLDONE (base=X require_pass=Y)` 의 exit 코드.
  - `base=0 require_pass=0` = 전 게이트 PASS
  - `base=0 require_pass=3` = FAIL 없음 + SKIPPED 잔존 (artifact/필드 확인)
  - `base=1` = 게이트 FAIL — 로그의 `Phase 22-07 gates FAIL:` 항목 확인
- 본판정은 반드시 `REPETITION_PENALTY` 미설정(기본 1.0). rp!=1.0 결과는 게이트
  본판정으로 쓰지 않는다.

## 3. rp A/B (별도 소규모 — 게이트 본판정 아님)

repetition 스팸 관찰용 소규모 A/B. **본판정에 rp!=1.0 사용 금지** — determinism
비교(cold 2회)와 판정 근거는 rp=1.0 아티팩트만 유효하다.

vLLM 이 이미 떠 있는 상태(또는 run_sft_gates.sh 의 serve 단계만 재사용)에서
val 4행 수준 관찰 실행:

```bash
cd /workspace/SunityMotion/backend
# serve 가 내려가 있으면 aligned 인자로 별도 기동 후:
EVAL_OUT_DIR=/workspace/eval_out_rp_ab \
PYTHONPATH=shared/python:training:. python3 evals/phase22/run_bakeoff.py \
  --model /workspace/phase22_export/sft-run1/awq \
  --prompt-mode aligned --repetition-penalty 1.05 \
  --run-tag rpab --skip-judge
```

- 산출: `/workspace/eval_out_rp_ab/phase22/bakeoff_*_rpab.json` — `_meta.repetition_penalty`
  로 구분. records 의 faults 반복/스팸 여부만 육안 비교.
- 관찰 후 판단: rp 가 fault 스팸을 줄이면 belle 결정 안건으로 올린다 (게이트 기준
  변경은 아님 — 디코딩 파라미터 논의).

## 4. 비교 리포트 (선택)

```bash
python3 - <<'EOF'
import json, glob
for tag, root in (("legacy_v4", "/workspace/eval_out/phase22_legacy_v4"),
                  ("aligned",   "/workspace/eval_out/phase22")):
    for p in sorted(glob.glob(f"{root}/bakeoff_*_run1.json")):
        d = json.load(open(p))
        print(tag, p.split("/")[-1], json.dumps(d.get("axes"), ensure_ascii=False))
EOF
```

- 관전 포인트: json_parse_rate(방어 파서 + 자유생성), 라우팅 키 존재(traceability),
  synthetic holdout 보정<무보정, eval18 변별 4페어.
