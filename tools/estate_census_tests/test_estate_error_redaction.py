"""Step 2(a) completion controls: the estate/watermark error path is redacted
BEFORE serialization, on every path that serializes it.

The defect these close, reproduced on the pushed tree `f7f55468`:
`tools/estate_census/watermarks.py::measure_one` stored a probe exception as
``f"{type(exc).__name__}: {exc}"`` verbatim, and that text reached four
serialization paths — the standalone ``watermarks --out`` file,
`tools/estate_census/evidence.py::build`'s ``estate_before``,
`EvidenceBundle.with_estate`'s attached measurement, and the CLI's own diagnostic
line. The existing controls proved pytest REPORT text was redacted and said
nothing about this path.
`tools/estate_census/evidence.py::credential_in_file` catching it afterwards is
defense in depth and does not satisfy generation-time redaction.

**Why the probe failure is injected rather than provoked.** Measured across nine
real failure modes — connection refused, unknown connection option, malformed
keyword DSN, bad port, malformed URI, unsupported scheme, bad option, malformed
URL — psycopg, pymongo and httpx all omit the password from their exception text.
So the defect is **not reachable through the three shipped drivers today**. That
is a property of those drivers at those versions and not a guarantee the census
may rest on, which is exactly the case Dave's requirement names: *"even if a
future measurement provider returns one."* A synthetic provider is the honest way
to exercise the path.

**No estate is contacted by anything in this module.**

**The positive control is `test_E_the_leak_detector_fires_on_the_unredacted_source_text`.**
It points the same detector at the raw exception text for both synthetic secrets
and requires it to fire. A clean artifact is not evidence until the detector has
proved it can see the secret, and the standard is a surviving SUBSTRING — a
partial leak is still a leak, and ``SECRET not in output`` once called a
ten-of-twelve-character leak clean.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.estate_census import watermarks
from tools.estate_census.__main__ import main
from tools.estate_census.classify import INDETERMINATE_CODES, ReasonCode, classify
from tools.estate_census.evidence import (
    PhaseReport,
    build,
    read_json,
    write_json,
)
from tools.estate_census.watermarks import StoreDeclaration, measure, measure_one

#: The two serializations, with distinct secrets so a control cannot pass on the
#: strength of the other one's redaction. Knowing the URI form proves nothing
#: about the keyword form: a Wave 1 credential sweep that knew only the URI form
#: reported "no DSN points at the estate" while a keyword-form DSN sat in a
#: census log.
URI_SECRET = "URI_SECRET_Aa1-bB2"
KEYWORD_SECRET = "KEYWORD_SECRET_Cc3-dD4"

URI_DSN = f"postgresql://ccf:{URI_SECRET}@192.168.4.76:5432/ccf_v2"
KEYWORD_DSN = f"host=192.168.4.76 port=5432 user=ccf password={KEYWORD_SECRET} dbname=ccf_v2"

SERIALIZATIONS: tuple[tuple[str, str, str], ...] = (
    ("uri", URI_SECRET, URI_DSN),
    ("libpq-keyword", KEYWORD_SECRET, KEYWORD_DSN),
)


def surviving_runs(secret: str, text: str, minimum: int = 4) -> list[str]:
    """Runs of at least `minimum` consecutive secret characters left in `text`.

    The project standard. ``secret not in text`` is not it: that test passed while
    ten of twelve characters of a password sat in the artifact.
    """
    return sorted(
        {
            secret[start:stop]
            for start in range(len(secret))
            for stop in range(start + minimum, len(secret) + 1)
            if secret[start:stop] in text
        },
        key=len,
        reverse=True,
    )


def raising_probe(message: str) -> Any:
    """A measurement provider whose exception text carries a connection target."""

    def probe(*_: Any, **__: Any) -> dict[str, Any]:
        raise RuntimeError(f"could not reach store using {message}")

    return probe


def roster_file(tmp_path: Path, *, kind: str, target_env: str) -> Path:
    path = tmp_path / "roster.json"
    path.write_text(
        json.dumps([{"key": f"{kind}/curated", "kind": kind, "target_env": target_env, "scopes": ["ccf_v2"]}])
    )
    return path


# ==========================================================================
# E — the positive control. Nothing below is evidence without it.
# ==========================================================================


@pytest.mark.parametrize("label,secret,dsn", SERIALIZATIONS, ids=[s[0] for s in SERIALIZATIONS])
def test_E_the_leak_detector_fires_on_the_unredacted_source_text(
    label: str, secret: str, dsn: str
) -> None:
    """THE POSITIVE CONTROL, per serialization."""
    raw = f"RuntimeError: could not reach store using {dsn}"
    assert surviving_runs(secret, raw), f"{label}: the detector cannot see its own secret"
    assert secret in raw


# ==========================================================================
# A and B — the probe error path, both serializations, three legs each.
# ==========================================================================


@pytest.mark.parametrize("label,secret,dsn", SERIALIZATIONS, ids=[s[0] for s in SERIALIZATIONS])
def test_AB_a_probe_exception_is_redacted_in_the_returned_measurement(
    monkeypatch: pytest.MonkeyPatch, label: str, secret: str, dsn: str
) -> None:
    """Leg 1 of 3: the measurement object is already safe when it is RETURNED."""
    monkeypatch.setattr(watermarks, "_postgres_counts", raising_probe(dsn))
    store = StoreDeclaration(key="postgres/curated", kind="postgres", target_env="T", scopes=("ccf_v2",))
    record = measure_one(store, environ={"T": "host=192.168.4.76 dbname=ccf_v2"})

    assert "error" in record, "the artifact must still record that the measurement failed"
    assert "position" not in record, "a failed measurement must not claim a position"
    leaked = surviving_runs(secret, json.dumps(record))
    assert not leaked, f"{label}: {leaked[0]!r} survived into the measurement"
    assert "could not reach store" in record["error"], "the diagnosis was destroyed with the secret"


@pytest.mark.parametrize("label,secret,dsn", SERIALIZATIONS, ids=[s[0] for s in SERIALIZATIONS])
def test_AB_a_probe_exception_is_redacted_in_the_standalone_watermark_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str, secret: str, dsn: str
) -> None:
    """Leg 2 of 3: the ``watermarks --out`` file, written before any bundle exists."""
    monkeypatch.setattr(watermarks, "_postgres_counts", raising_probe(dsn))
    store = StoreDeclaration(key="postgres/curated", kind="postgres", target_env="T", scopes=("ccf_v2",))
    measured = measure((store,), environ={"T": "host=192.168.4.76 dbname=ccf_v2"})
    target = tmp_path / "before.json"
    target.write_text(json.dumps(measured, indent=2, sort_keys=True) + "\n")

    text = target.read_text()
    leaked = surviving_runs(secret, text)
    assert not leaked, f"{label}: {leaked[0]!r} survived into {target.name}"
    assert json.loads(text), "the written watermark file no longer parses"
    assert "error" in measured["postgres/curated"]


@pytest.mark.parametrize("label,secret,dsn", SERIALIZATIONS, ids=[s[0] for s in SERIALIZATIONS])
def test_AB_a_probe_exception_is_redacted_in_the_watermark_cli_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    label: str,
    secret: str,
    dsn: str,
) -> None:
    """Leg 3 of 3: the console. A printed line is unrecoverable, so the real CLI
    handler is invoked and its own stdout is the subject."""
    monkeypatch.setattr(watermarks, "_postgres_counts", raising_probe(dsn))
    monkeypatch.setenv("CCF_CENSUS_CONTROL_DSN", "host=192.168.4.76 dbname=ccf_v2")
    roster = roster_file(tmp_path, kind="postgres", target_env="CCF_CENSUS_CONTROL_DSN")
    out = tmp_path / "before.json"

    code = main(["watermarks", "--roster", str(roster), "--out", str(out)])
    captured = capsys.readouterr()

    assert code == 0
    assert "UNMEASURED" in captured.out, "the CLI stopped reporting the failure"
    leaked = surviving_runs(secret, captured.out + captured.err)
    assert not leaked, f"{label}: {leaked[0]!r} was printed to the console"


# ==========================================================================
# C — the EvidenceBundle build path.
# ==========================================================================


def test_C_the_build_path_redacts_estate_errors_and_still_writes_parseable_json(
    tmp_path: Path,
) -> None:
    """Both serializations at once, through the real `build` then `write_json`."""
    leaky_before = {
        "postgres/curated": {
            "kind": "postgres",
            "target": "host=192.168.4.76 dbname=ccf_v2",
            "error": f"RuntimeError: could not reach store using {URI_DSN}",
        }
    }
    leaky_after = {
        "postgres/curated": {
            "kind": "postgres",
            "target": "host=192.168.4.76 dbname=ccf_v2",
            "nested": {"deeper": [f"RuntimeError: could not reach store using {KEYWORD_DSN}"]},
        }
    }
    bundle = build(
        provenance={"exit_status": 0},
        estate_before=leaky_before,
        estate_after=leaky_after,
        collected=("t.py::a",),
        phase_reports={"t.py::a": (PhaseReport("call", "passed"),)},
        collection_errors=(),
    )
    target = tmp_path / "bundle.json"
    write_json(bundle, target)
    text = target.read_text()

    for label, secret, _dsn in SERIALIZATIONS:
        leaked = surviving_runs(secret, text)
        assert not leaked, f"{label}: {leaked[0]!r} survived into the built bundle"
    assert json.loads(text), "the bundle no longer parses"
    assert "ccf:***@" in text, "the URI error indication did not survive in redacted form"
    assert "password=***" in text, "the keyword error did not survive in redacted form (NESTED value)"
    assert "could not reach store" in text, "the error indication was destroyed"


# ==========================================================================
# D — the attach-estate CLI path.
# ==========================================================================


def test_D_the_attach_estate_cli_cannot_inject_raw_free_text_into_the_bundle(
    tmp_path: Path,
) -> None:
    """The one door into the primary bundle that does not pass through `build`.

    Both sides are checked: an ``estate.before`` that arrived from an older bundle
    or an externally produced watermark file must not bypass the boundary either.
    """
    clean_estate = {"postgres/curated": {"kind": "postgres", "position": {"rows": 156}}}
    bundle = build(
        provenance={"exit_status": 0},
        estate_before=clean_estate,
        estate_after={},
        collected=("t.py::a",),
        phase_reports={"t.py::a": (PhaseReport("call", "passed"),)},
        collection_errors=(),
    )
    bundle_path = tmp_path / "candidate.json"
    write_json(bundle, bundle_path)

    # An externally produced before-measurement, injected past `build` entirely.
    raw = json.loads(bundle_path.read_text())
    raw["estate"]["before"]["postgres/curated"]["error"] = (
        f"RuntimeError: could not reach store using {URI_DSN}"
    )
    bundle_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")

    after = tmp_path / "after.json"
    after.write_text(
        json.dumps(
            {
                "postgres/curated": {
                    "kind": "postgres",
                    "error": f"RuntimeError: could not reach store using {KEYWORD_DSN}",
                    "also": [f"and via {URI_DSN}"],
                }
            }
        )
    )

    code = main(["attach-estate", "--bundle", str(bundle_path), "--after", str(after)])
    assert code == 0

    text = bundle_path.read_text()
    for label, secret, _dsn in SERIALIZATIONS:
        leaked = surviving_runs(secret, text)
        assert not leaked, f"{label}: {leaked[0]!r} survived attach-estate"
    written = read_json(bundle_path)
    assert written is not None, "the output bundle no longer parses"
    assert "password=***" in text, "the attached error indication did not survive redacted"
    assert "ccf:***@" in text, "the pre-existing before-side error was not redacted"

    # And the bundle is still classifiable: a verdict comes back, and it correctly
    # refuses to treat an errored store as an unmoved position.
    verdict = classify(written, written)
    assert verdict.state in ("PASS", "HOLD", "INDETERMINATE")
    assert ReasonCode.ESTATE_NOT_MEASURED in verdict.reason_codes
    assert set(verdict.reason_codes) <= INDETERMINATE_CODES
