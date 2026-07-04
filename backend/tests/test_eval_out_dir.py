"""eval sweep 산출물 경로 분리 테스트 — 25-SWEEP-EVIDENCE 근본원인 4 재발 방지.

2026-07-02 FAIL run 의 sweep 산출물이 repo 내 evals/*/baseline/ 을 덮어써 pod network
volume 의 소스트리를 오염시켰고, 이후 게이트가 오염된 기준으로 판정했다. 방지 구조:

  · run_sweep(phase24/25): 신규 산출물은 repo 밖 EVAL_OUT_DIR (기본 /tmp/sunity_eval_out)
    로만 기록. EVAL_OUT_DIR 이 repo 안을 가리키면 즉시 중단(SystemExit).
  · assert_gates(phase24/25): 신규 산출물은 같은 EVAL_OUT_DIR 에서 읽되, 방향-비교 기준
    (phase24 baseline)은 항상 git 커밋본(repo 내 read-only) 경로에서 읽는다 — 신규
    산출물과 기준의 물리적 분리.

모듈은 파일 경로 로드(evals/ 는 패키지 아님 — phase24/25 테스트 패턴). 환경변수 해석은
run_sweep 은 호출 시점, assert_gates 는 import 시점이므로 케이스마다 fresh 로드한다.
"""

import importlib.util
import pathlib

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parent
EVALS = BACKEND / "evals"


def _load(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inside_repo(p: pathlib.Path) -> bool:
    p = pathlib.Path(p).resolve()
    root = REPO_ROOT.resolve()
    return p == root or root in p.parents


# ── run_sweep: 출력 경로가 repo 밖 ───────────────────────────────────────────


@pytest.mark.parametrize("phase", ["phase24", "phase25"])
def test_sweep_default_out_dir_outside_repo(monkeypatch, phase):
    monkeypatch.delenv("EVAL_OUT_DIR", raising=False)
    sweep = _load(EVALS / phase / "run_sweep.py", f"{phase}_sweep_default")
    out = sweep._resolve_out_dir()
    assert not _inside_repo(out), f"default sweep out dir {out} is inside the repo"
    assert out.name == phase  # phase 별 서브디렉토리 격리


@pytest.mark.parametrize("phase", ["phase24", "phase25"])
def test_sweep_respects_eval_out_dir_env(monkeypatch, tmp_path, phase):
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    sweep = _load(EVALS / phase / "run_sweep.py", f"{phase}_sweep_env")
    assert sweep._resolve_out_dir() == (tmp_path / phase).resolve()


@pytest.mark.parametrize("phase", ["phase24", "phase25"])
def test_sweep_refuses_out_dir_inside_repo(monkeypatch, phase):
    # 근본원인 4 의 사고 형상: 출력이 repo(pod network volume 소스트리) 안 → 즉시 중단.
    monkeypatch.setenv("EVAL_OUT_DIR", str(EVALS))
    sweep = _load(EVALS / phase / "run_sweep.py", f"{phase}_sweep_guard")
    with pytest.raises(SystemExit):
        sweep._resolve_out_dir()


@pytest.mark.parametrize("phase", ["phase24", "phase25"])
def test_sweep_never_writes_committed_baseline_dir(monkeypatch, tmp_path, phase):
    # 커밋 baseline 디렉토리는 sweep 출력 경로 후보가 될 수 없다.
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    sweep = _load(EVALS / phase / "run_sweep.py", f"{phase}_sweep_sep")
    assert sweep._resolve_out_dir() != (EVALS / phase / "baseline").resolve()


# ── assert_gates: 신규 산출물 = EVAL_OUT_DIR / 기준 = git 커밋본 ──────────────


def test_phase25_gate_new_artifacts_outside_repo(monkeypatch):
    monkeypatch.delenv("EVAL_OUT_DIR", raising=False)
    gates = _load(EVALS / "phase25" / "assert_gates.py", "p25_gates_paths")
    for p in (gates._REPORT_ARTIFACT, gates._REPORT_WARM_ARTIFACT,
              gates._BREAKDOWN_ARTIFACT):
        assert not _inside_repo(p), f"phase25 new artifact path {p} is inside the repo"


def test_phase25_gate_new_artifacts_follow_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    gates = _load(EVALS / "phase25" / "assert_gates.py", "p25_gates_env")
    out = (tmp_path / "phase25").resolve()
    assert gates._REPORT_ARTIFACT == out / "phase25_sweep_report.json"
    assert gates._REPORT_WARM_ARTIFACT == out / "phase25_sweep_report_warm.json"
    assert gates._BREAKDOWN_ARTIFACT == out / "phase25_breakdowns.json"


def test_phase25_gate_baseline_is_committed_repo_path(monkeypatch, tmp_path):
    # EVAL_OUT_DIR 이 어디를 가리키든 비교 기준(phase24 baseline)은 git 커밋본 고정.
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    gates = _load(EVALS / "phase25" / "assert_gates.py", "p25_gates_baseline")
    committed = EVALS / "phase24" / "baseline" / "phase24_sweep_report.json"
    assert gates._P24_REPORT_ARTIFACT == committed
    assert _inside_repo(gates._P24_REPORT_ARTIFACT)
    assert committed.exists()  # 커밋본 존재 — 기준이 실제로 read-only 소스에서 온다


def test_phase24_gate_breakdown_artifact_outside_repo(monkeypatch):
    monkeypatch.delenv("EVAL_OUT_DIR", raising=False)
    gates = _load(EVALS / "phase24" / "assert_gates.py", "p24_gates_paths")
    assert not _inside_repo(gates._BREAKDOWN_ARTIFACT), (
        f"phase24 new artifact path {gates._BREAKDOWN_ARTIFACT} is inside the repo"
    )
    assert gates._BREAKDOWN_ARTIFACT.name == "phase24_breakdowns.json"


def test_sweep_and_gate_paths_agree(monkeypatch, tmp_path):
    # run_sweep 이 쓰는 곳 == assert_gates 가 읽는 곳 (같은 env 해석).
    monkeypatch.setenv("EVAL_OUT_DIR", str(tmp_path))
    sweep = _load(EVALS / "phase25" / "run_sweep.py", "p25_sweep_agree")
    gates = _load(EVALS / "phase25" / "assert_gates.py", "p25_gates_agree")
    out = sweep._resolve_out_dir()
    assert gates._REPORT_ARTIFACT == out / "phase25_sweep_report.json"
    assert gates._BREAKDOWN_ARTIFACT == out / "phase25_breakdowns.json"
