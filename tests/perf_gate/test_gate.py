"""Deterministic unit tests for the perf report+gate pipeline (`perf/gate.py`).

These tests validate PERF-04's gating mechanics on synthetic fixture inputs —
no timing anywhere — so always-on CI verifies the gate logic without ever
running a benchmark (11-RESEARCH.md Validation Architecture). Covered
behaviors: percentile computation (D-03), suite-default and override threshold
resolution with loosen-only validation (D-11/D-22), pass/fail/warn gating
semantics (D-19..D-21; speed-ups warn, never fail), missing-baseline
report-only with a loud notice and exit 0 (D-13), bidirectional benchmark-ID
drift warnings (11-RESEARCH.md Pitfall 6), runner-class key handling (D-10),
and the structural no-write-to-baselines assertion (D-13 / T-11-03).

gate.py lives outside the installed packages (repo-owned script per
D-IMPL-70), so it is loaded by file path rather than imported as a package.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import sys
from types import ModuleType

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / "perf" / "gate.py"
THRESHOLDS_PATH = REPO_ROOT / "perf" / "thresholds.toml"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location("perf_gate_under_test", GATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses (and other machinery) resolve the defining module through
    # sys.modules, so register it before executing.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def make_config(
    *,
    micro_default: float = 0.10,
    overrides: dict[str, float] | None = None,
) -> dict:
    config: dict = {
        "suite": {
            "micro": {"default": micro_default},
            "scale": {"default": 0.10},
            "crossproc": {"default": 0.25},
            "replay": {"default": 0.15},
        }
    }
    if overrides:
        config["override"] = {
            bench_id: {"threshold": value} for bench_id, value in overrides.items()
        }
    return config


def make_raw_json(path: pathlib.Path, benchmarks: dict[str, list[float]]) -> None:
    """Write a minimal pytest-benchmark raw JSON export with stats.data."""
    payload = {
        "benchmarks": [
            {
                "fullname": bench_id,
                "stats": {"data": data, "median": sorted(data)[len(data) // 2]},
            }
            for bench_id, data in benchmarks.items()
        ]
    }
    path.write_text(json.dumps(payload))


def make_baseline(path: pathlib.Path, medians: dict[str, float]) -> None:
    payload = {
        "metadata": {"date": "2026-08-01", "commit": "abc1234", "approved": "D-GATE-11"},
        "benchmarks": medians,
    }
    path.write_text(json.dumps(payload))


# ---------------------------------------------------------------------------
# Percentile computation (D-03)
# ---------------------------------------------------------------------------

def test_percentiles_on_known_100_element_fixture() -> None:
    # Values 1.0 .. 100.0: nearest-rank sorted-index expectations.
    data = [float(v) for v in range(100, 0, -1)]  # deliberately unsorted input
    stats = gate.compute_percentiles(data)
    assert stats["p50"] == 50.0
    assert stats["p95"] == 95.0
    assert stats["p99"] == 99.0


def test_percentiles_median_matches_statistics_median() -> None:
    data = [3.0, 1.0, 2.0, 4.0]
    stats = gate.compute_percentiles(data)
    assert stats["median"] == 2.5


def test_percentiles_reject_empty_data() -> None:
    with pytest.raises(ValueError):
        gate.compute_percentiles([])


# ---------------------------------------------------------------------------
# Threshold resolution (D-11, D-19..D-22)
# ---------------------------------------------------------------------------

def test_suite_default_applies_without_override() -> None:
    config = make_config()
    assert gate.resolve_threshold("micro", "test_traversal", config) == 0.10
    assert gate.resolve_threshold("crossproc", "test_rt", config) == 0.25


def test_override_applies_when_present() -> None:
    config = make_config(overrides={"test_noisy": 0.30})
    assert gate.resolve_threshold("micro", "test_noisy", config) == 0.30
    # Other benchmarks in the suite keep the default.
    assert gate.resolve_threshold("micro", "test_quiet", config) == 0.10


def test_loosen_only_rejects_tighter_override() -> None:
    config = make_config(micro_default=0.10, overrides={"test_x": 0.05})
    with pytest.raises(gate.ThresholdConfigError):
        gate.resolve_threshold("micro", "test_x", config)


def test_unknown_suite_is_a_config_error() -> None:
    config = make_config()
    with pytest.raises(gate.ThresholdConfigError):
        gate.resolve_threshold("nonexistent", "test_x", config)


def test_repo_thresholds_toml_carries_decided_defaults() -> None:
    import tomllib

    config = tomllib.loads(THRESHOLDS_PATH.read_text())
    assert config["suite"]["micro"]["default"] == 0.10
    assert config["suite"]["scale"]["default"] == 0.10
    assert config["suite"]["crossproc"]["default"] == 0.25
    assert config["suite"]["replay"]["default"] == 0.15


# ---------------------------------------------------------------------------
# Gating semantics (D-19..D-21; RESEARCH Open Question 1)
# ---------------------------------------------------------------------------

def _stats(median: float) -> dict[str, float]:
    return {"p50": median, "p95": median, "p99": median, "median": median}


def test_pass_within_threshold() -> None:
    results = {"test_a": _stats(1.05)}
    baseline = {"test_a": 1.0}
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert report.exit_code == 0
    assert report.rows[0].verdict == "PASS"


def test_fail_on_gated_slowdown() -> None:
    results = {"test_a": _stats(1.2)}  # +20% vs 10% threshold
    baseline = {"test_a": 1.0}
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert report.exit_code != 0
    assert report.rows[0].verdict == "FAIL"


def test_speedup_beyond_threshold_warns_never_fails() -> None:
    results = {"test_a": _stats(0.1)}  # 10x faster — probably a broken benchmark
    baseline = {"test_a": 1.0}
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert report.exit_code == 0
    assert report.rows[0].verdict == "WARN"
    assert any("speed-up" in w.lower() for w in report.warnings)


def test_missing_baseline_dict_reports_not_gated() -> None:
    results = {"test_a": _stats(1.0)}
    report = gate.evaluate(results, None, make_config(), "micro")
    assert report.exit_code == 0
    assert report.rows[0].verdict == "NO BASELINE — NOT GATED"


def test_id_drift_warns_in_both_directions() -> None:
    results = {"test_new": _stats(1.0)}
    baseline = {"test_old": 1.0}
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert report.exit_code == 0
    joined = "\n".join(report.warnings)
    assert "test_old" in joined  # baseline entry with no current benchmark
    # Current benchmark with no baseline entry is loud per-entry (D-13).
    assert report.rows[0].verdict == "NO BASELINE — NOT GATED"


def test_drift_check_ignores_baseline_entries_of_suites_that_did_not_run() -> None:
    """A single-suite run must not warn about other suites' baseline entries.

    The committed baseline covers the whole battery, so `make perf-micro`
    gates only the micro results against it. Baseline entries owned by
    scale/crossproc/replay are not drift — those suites simply did not run.
    """
    results = {"suites/micro/test_gates.py::test_gate_ttl_bounds": _stats(1.0)}
    baseline = {
        "suites/micro/test_gates.py::test_gate_ttl_bounds": 1.0,
        "suites/scale/test_assembly.py::test_assembly_scale[500]": 17.1,
        "suites/crossproc/test_peering.py::test_peering_roundtrip": 0.0007,
        "suites/replay/test_replay_scale.py::test_replay_at_scale[1000]": 0.57,
    }
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert report.exit_code == 0
    assert report.warnings == []


def test_drift_check_still_warns_within_the_suite_that_ran() -> None:
    """Genuine drift inside the executed suite must still warn (Pitfall 6)."""
    results = {"suites/micro/test_gates.py::test_renamed": _stats(1.0)}
    baseline = {
        "suites/micro/test_gates.py::test_gate_ttl_bounds": 1.0,
        "suites/scale/test_assembly.py::test_assembly_scale[500]": 17.1,
    }
    report = gate.evaluate(results, baseline, make_config(), "micro")
    joined = "\n".join(report.warnings)
    assert "test_gate_ttl_bounds" in joined  # vanished from the suite that ran
    assert "test_assembly_scale" not in joined  # scale did not run — not drift


def test_drift_check_keeps_unattributable_baseline_entries_visible() -> None:
    """An entry with no `suites/<name>/` owner cannot be scoped away."""
    results = {"suites/micro/test_gates.py::test_gate_ttl_bounds": _stats(1.0)}
    baseline = {
        "suites/micro/test_gates.py::test_gate_ttl_bounds": 1.0,
        "legacy_unprefixed_id": 1.0,
    }
    report = gate.evaluate(results, baseline, make_config(), "micro")
    assert any("legacy_unprefixed_id" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Runner class handling (D-10, T-11-02)
# ---------------------------------------------------------------------------

def test_runner_class_rejects_path_traversal_charset() -> None:
    assert gate.sanitize_runner_class("gh-ubuntu-24.04") == "gh-ubuntu-24.04"
    assert gate.sanitize_runner_class("local") == "local"
    assert gate.sanitize_runner_class("../../etc/passwd") is None
    assert gate.sanitize_runner_class("a/b") is None
    assert gate.sanitize_runner_class("") is None


# ---------------------------------------------------------------------------
# End-to-end main() on fixture files (D-13 loud notice, exit codes)
# ---------------------------------------------------------------------------

def test_main_missing_baseline_exit_zero_and_loud(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = tmp_path / "micro.raw.json"
    make_raw_json(raw, {"test_a": [1.0, 2.0, 3.0]})
    monkeypatch.setenv("CCF_PERF_RUNNER_CLASS", "no-such-runner")
    monkeypatch.setattr(gate, "BASELINES_DIR", tmp_path / "baselines")
    code = gate.main([str(raw), "--suite", "micro"])
    captured = capsys.readouterr()
    assert code == 0
    assert "NO BASELINE — NOT GATED" in captured.out
    # Results JSON is written next to the raw file (D-02 single pipeline).
    results = json.loads((tmp_path / "micro.results.json").read_text())
    assert "test_a" in results["benchmarks"]
    assert set(results["benchmarks"]["test_a"]) >= {"p50", "p95", "p99", "median"}


def test_main_gated_regression_exits_nonzero(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "micro.raw.json"
    make_raw_json(raw, {"test_a": [2.0, 2.0, 2.0]})
    baselines = tmp_path / "baselines"
    baselines.mkdir()
    make_baseline(baselines / "local.json", {"test_a": 1.0})
    monkeypatch.setenv("CCF_PERF_RUNNER_CLASS", "local")
    monkeypatch.setattr(gate, "BASELINES_DIR", baselines)
    code = gate.main([str(raw), "--suite", "micro"])
    assert code != 0


def test_main_pass_exits_zero(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "micro.raw.json"
    make_raw_json(raw, {"test_a": [1.0, 1.0, 1.0]})
    baselines = tmp_path / "baselines"
    baselines.mkdir()
    make_baseline(baselines / "local.json", {"test_a": 1.0})
    monkeypatch.setenv("CCF_PERF_RUNNER_CLASS", "local")
    monkeypatch.setattr(gate, "BASELINES_DIR", baselines)
    assert gate.main([str(raw), "--suite", "micro"]) == 0


# ---------------------------------------------------------------------------
# Structural: gate.py never writes baselines (D-13, T-11-03)
# ---------------------------------------------------------------------------

#: Method names that mutate the thing they are called on.
_MUTATING_METHODS = frozenset(
    {"write_text", "write_bytes", "unlink", "touch", "rename", "replace", "mkdir"}
)

#: Free functions that mutate a path passed as an argument.
_MUTATING_FUNCTIONS = frozenset(
    {"copy", "copy2", "copyfile", "move", "replace", "rename", "remove", "dump"}
)


def _mentions(node: ast.AST, names: set[str]) -> bool:
    """Whether any `Name` in `node`'s subtree is one of `names`."""
    return any(
        isinstance(child, ast.Name) and child.id in names
        for child in ast.walk(node)
    )


def baseline_write_offenders(source: str) -> list[str]:
    """Every expression in `source` that could write to the baselines dir.

    WR-06: this replaces a line grep that only fired when `"baselines"` and
    `write_text`/`open(` appeared on the SAME source line. Splitting the
    statement across two lines — `p = BASELINES_DIR / "x.json"` then
    `p.write_text(...)` — defeated it entirely, as did `shutil.copy`,
    `os.replace` and `json.dump` to an open handle. A control that reads as
    structural but discriminates almost nothing is worse than no control,
    because it is trusted.

    Aliases are resolved across the whole module before any call is judged,
    so the check is line-independent by construction.
    """
    tree = ast.parse(source)
    aliases = {"BASELINES_DIR"}
    # Fixed point: an alias of an alias is still an alias.
    for _ in range(8):
        grown = set(aliases)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = (
                    [node.target] if isinstance(node, ast.AnnAssign) else node.targets
                )
                if node.value is not None and _mentions(node.value, aliases):
                    grown |= {t.id for t in targets if isinstance(t, ast.Name)}
        if grown == aliases:
            break
        aliases = grown
    aliases.discard("BASELINES_DIR")
    aliases.add("BASELINES_DIR")

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in _MUTATING_METHODS and _mentions(func.value, aliases):
                offenders.append(ast.unparse(node))
                continue
            if func.attr == "open" and _mentions(func.value, aliases):
                offenders.append(ast.unparse(node))
                continue
            if func.attr in _MUTATING_FUNCTIONS and any(
                _mentions(arg, aliases) for arg in node.args
            ):
                offenders.append(ast.unparse(node))
                continue
        name = func.id if isinstance(func, ast.Name) else None
        if name == "open" and any(_mentions(arg, aliases) for arg in node.args):
            offenders.append(ast.unparse(node))
        elif name in _MUTATING_FUNCTIONS and any(
            _mentions(arg, aliases) for arg in node.args
        ):
            offenders.append(ast.unparse(node))
    return offenders


@pytest.mark.parametrize(
    "evasion",
    [
        # The exact reformatting WR-06 named: two lines, so the old grep missed it.
        'p = BASELINES_DIR / "x.json"\np.write_text("{}")\n',
        'p = BASELINES_DIR / "x.json"\nwith p.open("w") as fh:\n    fh.write("{}")\n',
        'p = BASELINES_DIR / "x.json"\nshutil.copy(src, p)\n',
        'p = BASELINES_DIR / "x.json"\nos.replace(tmp, p)\n',
        'p = BASELINES_DIR / "x.json"\nq = p\njson.dump({}, open(q, "w"))\n',
    ],
)
def test_the_no_write_control_catches_a_reformatted_write(evasion: str) -> None:
    assert baseline_write_offenders(evasion), evasion


def test_the_no_write_control_does_not_fire_on_a_read() -> None:
    read_only = 'p = BASELINES_DIR / "x.json"\ndata = json.loads(p.read_text())\n'
    assert baseline_write_offenders(read_only) == []


def test_gate_source_has_no_baseline_write_path() -> None:
    source = GATE_PATH.read_text()
    assert baseline_write_offenders(source) == []
    # The only baseline interaction is a read.
    assert "def record_baseline" not in source


def test_gate_leaves_the_baselines_directory_byte_identical(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Behavioural counterpart to the structural check (D-13, T-11-03).

    The source check can only see what it knows to look for; this one runs the
    gate in every polarity and compares the directory's bytes.
    """
    baselines = tmp_path / "baselines"
    baselines.mkdir()
    make_baseline(baselines / "local.json", {"test_a": 1.0})
    monkeypatch.setenv("CCF_PERF_RUNNER_CLASS", "local")
    monkeypatch.setattr(gate, "BASELINES_DIR", baselines)

    def snapshot() -> dict[str, bytes]:
        return {
            str(p.relative_to(baselines)): p.read_bytes()
            for p in sorted(baselines.rglob("*"))
            if p.is_file()
        }

    before = snapshot()
    for timings in ({"test_a": [1.0]}, {"test_a": [99.0]}, {"test_b": [1.0]}):
        raw = tmp_path / "micro.raw.json"
        make_raw_json(raw, timings)
        gate.main([str(raw), "--suite", "micro"])
    assert snapshot() == before
