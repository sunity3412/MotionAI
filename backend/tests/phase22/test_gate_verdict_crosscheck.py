"""게이트 판정 교차검증 계약 — quick-260815-glc.

2026-08-15 실측: 게이트가 `base=1 require_pass=1` 로 FAIL 했는데 러너는
`게이트 exit=0` 을 기록했다. run_sft_gates.sh 의 마지막 문장이 `echo` 라 스크립트
종료 코드가 항상 0 이었기 때문이다. promotion 은 "require-pass exit 0 만 pass=True"
계약으로 그 값을 읽으므로 **실패한 모델이 승격될 수 있었다** — 실제로 승격을 막은
것은 판정이 아니라 무관한 promote 예외였다(안전장치가 아니라 우연).

수리는 두 겹이다:
  (1) run_sft_gates.sh 가 require-pass 코드로 종료한다.
  (2) run_retrain_cycle.sh 가 종료 코드와 **로그에 선언된 값**을 대조해 어긋나면
      나쁜 쪽으로 확정한다(fail-closed).

이 파일은 (2)를 **실제 shell 텍스트를 실행해서** 검증한다 — 로직을 python 으로
베껴 쓰면 "내 사본이 내 사본과 같다"가 되어 배선을 증명하지 못한다.
"""

from __future__ import annotations

import re
import subprocess
import textwrap
from pathlib import Path

_CYCLE = (
    Path(__file__).resolve().parents[3]
    / "backend" / "training" / "sft" / "run_retrain_cycle.sh"
)


def _extract_crosscheck() -> str:
    """run_retrain_cycle.sh 에서 교차검증 블록을 원문 그대로 잘라낸다."""
    src = _CYCLE.read_text(encoding="utf-8")
    start = src.index("  declared=$(grep -oE 'GATES ALLDONE")
    end = src.index('  echo "$gate_exit" > "$GATE_EXIT_FILE"')
    block = textwrap.dedent(src[start:end])
    assert "fail-closed" in block or "gate_exit=1" in block, "교차검증 블록을 못 찾았다"
    return block


def _run_block(tmp_path, log_text: str, gate_exit: int) -> int:
    log = tmp_path / "gates.log"
    log.write_text(log_text, encoding="utf-8")
    script = tmp_path / "check.sh"
    script.write_text(
        "set -u\n"
        f'gate_log="{log}"\n'
        f"gate_exit={gate_exit}\n"
        'declared=""\n'
        + _extract_crosscheck()
        + '\necho "RESULT=$gate_exit"\n',
        encoding="utf-8",
    )
    out = subprocess.run(
        ["bash", str(script)], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, out.stdout + out.stderr
    m = re.search(r"RESULT=(\d+)", out.stdout)
    assert m, out.stdout
    return int(m.group(1))


FAIL_LOG = "…\nGATES ALLDONE (base=1 require_pass=1)\n"
PASS_LOG = "…\nGATES ALLDONE (base=0 require_pass=0)\n"


def test_declared_fail_overrides_exit_zero(tmp_path):
    """★이번 사고 그대로 — exit 0 인데 선언은 FAIL 이면 FAIL 로 확정."""
    assert _run_block(tmp_path, FAIL_LOG, gate_exit=0) == 1


def test_agreement_passes_through(tmp_path):
    assert _run_block(tmp_path, PASS_LOG, gate_exit=0) == 0
    assert _run_block(tmp_path, FAIL_LOG, gate_exit=1) == 1


def test_exit_worse_than_declared_is_kept(tmp_path):
    """반대 방향(exit 이 더 나쁨)은 낮추지 않는다 — 나쁜 쪽 확정."""
    assert _run_block(tmp_path, PASS_LOG, gate_exit=11) == 11


def test_missing_declaration_with_exit_zero_is_failed(tmp_path):
    """완주 선언이 없는데 exit 0 이면 게이트가 안 돈 것 — 승격 금지."""
    assert _run_block(tmp_path, "vLLM 사망\n", gate_exit=0) == 1


def test_missing_declaration_with_nonzero_exit_is_kept(tmp_path):
    assert _run_block(tmp_path, "vLLM 사망\n", gate_exit=11) == 11


def test_gate_script_exits_with_require_pass_code():
    """(1)겹 — 러너 스크립트가 require-pass 코드로 종료하는지 원문 확인."""
    src = (
        _CYCLE.parent / "run_sft_gates.sh"
    ).read_text(encoding="utf-8").rstrip().splitlines()
    assert src[-1].strip() == 'exit "${REQ_RC:-0}"', (
        "게이트 스크립트가 require-pass 코드로 끝나지 않는다 — 마지막 줄: " + src[-1]
    )
