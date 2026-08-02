"""`perf/gate.py` — the perf battery's report + gate, one pipeline (D-02/D-03).

Repo-owned and reviewed per D-IMPL-70: this script is the only judge of
benchmark timings. It reads a pytest-benchmark raw JSON export (the
``--benchmark-json`` file, which contains every raw timing in
``benchmarks[].stats.data``), computes p50/p95/p99 + median per benchmark,
prints a terminal percentile table, writes a machine-readable results JSON
next to the raw file (``<suite>.results.json``, under gitignored
``perf/results/``), and — when a committed baseline exists for the declared
runner class — applies the relative-median thresholds from
``perf/thresholds.toml``.

Exit codes
----------
* ``0`` — everything passed, or nothing was gated. A missing baseline is
  **report-only**: every ungated entry prints a loud ``NO BASELINE — NOT
  GATED`` notice and the run stays green (D-13). This is a deliberate
  contrast with ``tools/lints``, which has no report-only mode: the CINV
  lints guard invariants that must block from the first commit, while perf
  gating is only meaningful once a Dave-approved baseline exists for the
  runner class in force (D-IMPL-70).
* nonzero — at least one **gated slowdown regression**: the current median
  exceeded ``baseline_median * (1 + threshold)``.

Speed-ups never fail. A benchmark that suddenly runs faster than the
threshold in the improving direction emits a loud WARN instead — a 10x
"improvement" usually means the benchmark stopped measuring the real work
(11-RESEARCH.md Open Question 1 recommendation).

Baselines
---------
Baselines are median-only JSON per runner class at
``perf/baselines/<runner-class>.json`` (D-12), with schema
``{"metadata": {"date", "commit", "approved"}, "benchmarks": {id: median_seconds}}``.
This script NEVER writes to ``perf/baselines/`` — re-baselining is a manual,
Dave-approved act (D-13/D-IMPL-70), and the absence of any write path here is
source-asserted by ``tests/perf_gate``.

The runner class comes from the ``CCF_PERF_RUNNER_CLASS`` environment
variable (D-10): CI sets ``gh-ubuntu-24.04``; the Makefile defaults
``local``. An unknown, missing, or invalid key selects no baseline and the
run is report-only. Keys are restricted to a safe charset (alphanumerics,
dash, dot, underscore) before being joined into the baseline path (T-11-02).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import statistics
import sys
import tomllib
from dataclasses import dataclass, field

#: Directory of committed, reviewed baselines (read-only from this script).
BASELINES_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent / "baselines"

#: Safe charset for the runner-class key (T-11-02) — anchored full match.
RUNNER_CLASS_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")

#: Environment variable naming the runner class (D-10).
RUNNER_CLASS_ENV = "CCF_PERF_RUNNER_CLASS"

#: Loud per-entry verdict for ungated benchmarks (D-13).
NOT_GATED = "NO BASELINE — NOT GATED"


class ThresholdConfigError(ValueError):
    """A thresholds.toml violation: unknown suite, malformed table, or an
    override tighter than its suite default (loosen-only rule, D-22)."""


@dataclass
class Row:
    """One benchmark's report line: percentiles plus gate verdict."""

    benchmark_id: str
    p50: float
    p95: float
    p99: float
    median: float
    baseline_median: float | None
    threshold: float | None
    verdict: str


@dataclass
class Report:
    """Evaluation outcome: table rows, drift/speed-up warnings, exit code."""

    rows: list[Row] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exit_code: int = 0


def compute_percentiles(data: list[float]) -> dict[str, float]:
    """p50/p95/p99 (nearest-rank on the sorted timings) + true median.

    Nearest-rank: percentile p is the value at sorted index
    ``ceil(p/100 * n) - 1``. On a 100-element list this selects the 50th,
    95th, and 99th smallest values respectively. Median is
    ``statistics.median`` (interpolates on even counts), matching the number
    pytest-benchmark reports and the gate compares (D-03).
    """
    if not data:
        raise ValueError("cannot compute percentiles of empty timing data")
    ordered = sorted(data)
    n = len(ordered)

    def nearest_rank(p: float) -> float:
        index = max(0, -(-int(p * n) // 100) - 1)  # ceil(p*n/100) - 1
        return ordered[min(index, n - 1)]

    return {
        "p50": nearest_rank(50),
        "p95": nearest_rank(95),
        "p99": nearest_rank(99),
        "median": statistics.median(ordered),
    }


def resolve_threshold(suite: str, benchmark_id: str, config: dict) -> float:
    """The relative-median threshold in force for one benchmark.

    Suite default from ``[suite.<name>] default`` (D-11); a per-benchmark
    ``[override."<id>"] threshold`` applies when present but may only LOOSEN
    the suite default — a tighter override raises :class:`ThresholdConfigError`
    (D-22).
    """
    suites = config.get("suite", {})
    if suite not in suites or "default" not in suites[suite]:
        raise ThresholdConfigError(
            f"suite {suite!r} has no [suite.{suite}] default in thresholds.toml"
        )
    try:
        default = float(suites[suite]["default"])
    except (TypeError, ValueError) as exc:
        raise ThresholdConfigError(
            f"suite {suite!r} default is malformed: {exc}"
        ) from exc
    override_table = config.get("override", {}).get(benchmark_id)
    if override_table is None:
        return default
    try:
        override = float(override_table["threshold"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ThresholdConfigError(
            f"override for {benchmark_id!r} is malformed: {exc}"
        ) from exc
    if override < default:
        raise ThresholdConfigError(
            f"override for {benchmark_id!r} ({override}) is tighter than the "
            f"suite {suite!r} default ({default}); overrides may only loosen "
            "(D-22 — tighten by lowering the suite default instead)"
        )
    return override


def sanitize_runner_class(value: str | None) -> str | None:
    """The runner-class key if it is safe to use in a path, else None.

    Restricting to ``[A-Za-z0-9._-]+`` (with no separators) forecloses path
    traversal out of ``perf/baselines/`` (T-11-02). ``..`` alone would pass
    the charset, so it is rejected explicitly.
    """
    if not value or not RUNNER_CLASS_PATTERN.match(value) or value in {".", ".."}:
        return None
    return value


def evaluate(
    results: dict[str, dict[str, float]],
    baseline: dict[str, float] | None,
    config: dict,
    suite: str,
) -> Report:
    """Gate current medians against baseline medians (pure; no I/O).

    ``results`` maps benchmark id -> percentiles dict; ``baseline`` maps
    benchmark id -> approved median seconds, or is None when no baseline file
    exists for the runner class. Slowdowns beyond threshold FAIL; speed-ups
    beyond threshold WARN and never fail; entries absent from the baseline
    are loudly NOT GATED (D-13); baseline entries with no current benchmark
    warn so ID drift is visible in both directions (Pitfall 6).
    """
    report = Report()
    for benchmark_id, stats in results.items():
        median = stats["median"]
        baseline_median = None if baseline is None else baseline.get(benchmark_id)
        if baseline_median is None:
            report.rows.append(
                Row(benchmark_id, stats["p50"], stats["p95"], stats["p99"],
                    median, None, None, NOT_GATED)
            )
            continue
        threshold = resolve_threshold(suite, benchmark_id, config)
        delta = (median - baseline_median) / baseline_median
        if delta > threshold:
            verdict = "FAIL"
            report.exit_code = 1
        elif delta < -threshold:
            verdict = "WARN"
            report.warnings.append(
                f"{benchmark_id}: speed-up of {-delta:.1%} exceeds the "
                f"{threshold:.0%} threshold — verify the benchmark still "
                "measures the real work (warn-only, never fails)"
            )
        else:
            verdict = "PASS"
        report.rows.append(
            Row(benchmark_id, stats["p50"], stats["p95"], stats["p99"],
                median, baseline_median, threshold, verdict)
        )
    if baseline is not None:
        for orphan in sorted(set(baseline) - set(results)):
            report.warnings.append(
                f"baseline entry {orphan!r} has no matching current benchmark "
                "— possible benchmark-ID drift (Pitfall 6)"
            )
    return report


def load_raw(path: pathlib.Path) -> dict[str, dict[str, float]]:
    """Benchmark id -> percentiles, from a pytest-benchmark raw JSON export."""
    payload = json.loads(path.read_text())
    results: dict[str, dict[str, float]] = {}
    for bench in payload["benchmarks"]:
        results[bench["fullname"]] = compute_percentiles(bench["stats"]["data"])
    return results


def load_baseline(runner_class: str | None) -> tuple[dict[str, float] | None, str]:
    """(medians-or-None, human reason) for the runner class' baseline file."""
    if runner_class is None:
        return None, f"invalid or unset {RUNNER_CLASS_ENV} — report-only (D-10)"
    baseline_path = BASELINES_DIR / f"{runner_class}.json"
    if not baseline_path.is_file():
        return None, f"no baseline file {baseline_path} — report-only (D-13)"
    payload = json.loads(baseline_path.read_text())
    return {k: float(v) for k, v in payload["benchmarks"].items()}, str(baseline_path)


def print_table(report: Report, suite: str, baseline_note: str) -> None:
    """Terminal percentile table + verdicts + warnings (D-02)."""
    print(f"perf gate — suite {suite!r} — baseline: {baseline_note}")
    header = f"{'benchmark':<60} {'p50':>12} {'p95':>12} {'p99':>12} {'median':>12} {'base':>12} {'thr':>6}  verdict"
    print(header)
    print("-" * len(header))
    for row in report.rows:
        base = f"{row.baseline_median:.6g}" if row.baseline_median is not None else "—"
        thr = f"{row.threshold:.0%}" if row.threshold is not None else "—"
        print(
            f"{row.benchmark_id:<60} {row.p50:>12.6g} {row.p95:>12.6g} "
            f"{row.p99:>12.6g} {row.median:>12.6g} {base:>12} {thr:>6}  {row.verdict}"
        )
    for warning in report.warnings:
        print(f"WARNING: {warning}")


def write_results(raw_path: pathlib.Path, suite: str, report: Report) -> pathlib.Path:
    """Machine-readable results JSON next to the raw file (D-02 pipeline)."""
    results_path = raw_path.with_name(
        raw_path.name.replace(".raw.json", ".results.json")
        if raw_path.name.endswith(".raw.json")
        else f"{suite}.results.json"
    )
    payload = {
        "suite": suite,
        "benchmarks": {
            row.benchmark_id: {
                "p50": row.p50,
                "p95": row.p95,
                "p99": row.p99,
                "median": row.median,
                "baseline_median": row.baseline_median,
                "threshold": row.threshold,
                "verdict": row.verdict,
            }
            for row in report.rows
        },
        "warnings": report.warnings,
        "exit_code": report.exit_code,
    }
    results_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return results_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report + gate for one perf suite: computes p50/p95/p99/median "
            "from a pytest-benchmark raw JSON export and gates the median "
            "against the committed baseline for the declared runner class."
        )
    )
    parser.add_argument("raw_json", type=pathlib.Path,
                        help="pytest-benchmark --benchmark-json output file")
    parser.add_argument("--suite", required=True,
                        help="suite name (micro|scale|crossproc|replay) — selects "
                             "the [suite.<name>] default in perf/thresholds.toml")
    args = parser.parse_args(argv)

    config = tomllib.loads(
        (pathlib.Path(__file__).resolve().parent / "thresholds.toml").read_text()
    )
    results = load_raw(args.raw_json)
    runner_class = sanitize_runner_class(os.environ.get(RUNNER_CLASS_ENV))
    baseline, baseline_note = load_baseline(runner_class)
    report = evaluate(results, baseline, config, args.suite)
    print_table(report, args.suite, baseline_note)
    results_path = write_results(args.raw_json, args.suite, report)
    print(f"results written: {results_path}")
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
