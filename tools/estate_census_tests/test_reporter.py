"""Controls over `tools/estate_census/reporter.py` — the generation-time proof.

Dave's contract, verbatim: *"Add a synthetic failing test/result carrying
credentials through each representation and prove the artifact emitted by the
census machinery contains the redacted form and not the secret."* That is
`test_the_emitted_artifacts_carry_the_redacted_form_and_not_the_secret`, and it
runs the REAL plugin in a REAL pytest subprocess over a synthetic failing module.
Nothing here asserts on a stub: the subject is the file the census machinery
actually wrote.

**Why a subprocess and not an in-process call.** A reporter tested by calling its
hooks directly proves the hooks work. It does not prove the plugin is reachable
by ``-p tools.estate_census.reporter``, that ``pytest_configure`` registers it,
or that a real ``TestReport`` carries what the hooks read — and those are the
parts that would break silently. This follows the
`tools/check_version_stamp_tests` model, where the emitted artifact is the subject.

**The positive control is `test_the_leak_detector_would_see_the_secret_in_an_unredacted_artifact`**,
which points the same detector at pytest's OWN unredacted output from the same run
and requires it to fire. Without it, a clean artifact could mean the redaction
worked or that the synthetic test never carried a secret at all.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.estate_census.reporter import (
    ESTATE_BEFORE_ENV,
    LABEL_ENV,
    OUT_JSON_ENV,
    OUT_XML_ENV,
    CensusReporter,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: A secret whose characters are chosen for what broke a draft, not for realism:
#: an ``@`` truncated a URI match, a ``/`` stopped one matching at all.
SECRET = "p@ss/w0rd-S3cr3t"

#: A synthetic module that fails four ways, each carrying the credential in a
#: different serialization — the four Dave's contract names plus the stdout path,
#: which is in ``report.sections`` and in no traceback.
LEAKY_MODULE = f'''
SECRET = "{SECRET}"

def test_pg_uri_in_the_message():
    dsn = f"postgresql://ccf:{{SECRET}}@192.168.4.76:5432/ccf_v2"
    assert False, f"could not connect to {{dsn}}"

def test_libpq_keyword_in_the_message():
    dsn = f"host=192.168.4.76 port=5432 user=ccf password={{SECRET}} dbname=ccf_v2"
    raise RuntimeError(f"connection failed for {{dsn}}")

def test_mongo_uri_in_the_message():
    uri = f"mongodb://ccf:{{SECRET}}@192.168.4.76:27017/fibo_v2?authSource=admin"
    assert False, f"mongo refused: {{uri}}"

def test_bearer_token_on_stdout_only():
    print(f"Authorization: Bearer {{SECRET}}")
    print(f"CCF_CP_15_TOKEN_READ={{SECRET}}")
    assert False, "failed after printing credentials to stdout"

def test_a_green_one():
    assert True
'''


def surviving_runs(secret: str, text: str, minimum: int = 4) -> list[str]:
    """Runs of at least `minimum` consecutive secret characters left in `text`."""
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


@pytest.fixture(scope="module")
def census_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """One real pytest subprocess under the real plugin. Shared by the tests below."""
    workspace = tmp_path_factory.mktemp("census-reporter")
    module = workspace / "test_leaky_synthetic.py"
    module.write_text(LEAKY_MODULE)
    out_json, out_xml = workspace / "bundle.json", workspace / "bundle.xml"
    env = dict(os.environ)
    env[OUT_JSON_ENV] = str(out_json)
    env[OUT_XML_ENV] = str(out_xml)
    env[LABEL_ENV] = "reporter-control"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")]
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run(
        [
            sys.executable, "-B", "-m", "pytest",
            "-p", "no:cacheprovider",
            "-p", "tools.estate_census.reporter",
            "-q", "--rootdir", str(workspace), str(module),
        ],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False, timeout=300,
    )
    return {
        "returncode": done.returncode,
        "stdout": done.stdout,
        "json_text": out_json.read_text() if out_json.is_file() else "",
        "xml_text": out_xml.read_text() if out_xml.is_file() else "",
        "json_path": out_json,
        "xml_path": out_xml,
    }


def test_the_synthetic_run_actually_produced_both_artifacts(census_run: dict[str, object]) -> None:
    """A precondition: every assertion below is vacuous if nothing was written."""
    assert census_run["json_text"], "the reporter wrote no JSON bundle"
    assert census_run["xml_text"], "the reporter wrote no JUnit rendering"


def test_the_leak_detector_would_see_the_secret_in_an_unredacted_artifact(
    census_run: dict[str, object],
) -> None:
    """THE POSITIVE CONTROL. pytest's own console output from the same run carries
    the secret verbatim and always will — only the census ARTIFACT is redacted. If
    the detector cannot see it there, a clean artifact proves nothing."""
    assert surviving_runs(SECRET, str(census_run["stdout"])), (
        "the detector is blind, or the synthetic module never carried the secret"
    )


def test_the_emitted_artifacts_carry_the_redacted_form_and_not_the_secret(
    census_run: dict[str, object],
) -> None:
    """Dave's named requirement, over all four supported serializations at once."""
    for label in ("json_text", "xml_text"):
        text = str(census_run[label])
        leaked = surviving_runs(SECRET, text)
        assert not leaked, f"{label}: {leaked[0]!r} survived redaction"
    combined = str(census_run["json_text"])
    for probe, description in (
        ("ccf:***@192.168.4.76", "PostgreSQL URI userinfo"),
        ("password=***", "libpq keyword form"),
        ("mongodb://ccf:***@", "Mongo URI userinfo"),
        ("Authorization: ***", "bearer header captured from stdout"),
        ("CCF_CP_15_TOKEN_READ=***", "repo token variable captured from stdout"),
    ):
        assert probe in combined, f"{description} not present in its redacted form"


def test_the_emitted_junit_is_well_formed_despite_credential_bearing_tracebacks(
    census_run: dict[str, object],
) -> None:
    """Per-field redaction then serialization: the writer adds the delimiters after
    redaction, so a greedy value class cannot eat a closing quote and corrupt the
    document — the incident that silently broke a census file for hours."""
    ET.fromstring(str(census_run["xml_text"]).encode())


def test_the_bundle_records_exact_pytest_node_ids_not_dotted_class_names(
    census_run: dict[str, object],
) -> None:
    """JUnit's ``classname`` is a dotted module path and Wave 1's classification
    evidence is in that non-runnable form. ``report.nodeid`` is exact."""
    bundle = json.loads(str(census_run["json_text"]))
    node_ids = list(bundle["outcomes"])
    assert node_ids, "no outcomes recorded"
    for node in node_ids:
        assert "::" in node, node
        assert node.split("::")[0].endswith(".py"), node
        assert not node.startswith("tests."), f"dotted classname leaked into a node id: {node}"


def test_the_bundle_counts_four_separate_numbers(census_run: dict[str, object]) -> None:
    bundle = json.loads(str(census_run["json_text"]))
    counts = bundle["counts"]
    assert counts["failed"] == 4, counts
    assert counts["passed"] == 1, counts
    assert counts["errors"] == 0, counts
    assert set(counts) == {"passed", "failed", "errors", "skipped", "xfailed", "xpassed"}


def test_the_bundle_records_the_pytest_exit_status_and_the_selected_roster(
    census_run: dict[str, object],
) -> None:
    bundle = json.loads(str(census_run["json_text"]))
    assert bundle["provenance"]["exit_status"] == 1
    assert len(bundle["collected"]) == 5
    assert set(bundle["collected"]) == set(bundle["outcomes"])


def test_the_reporter_is_inert_when_no_output_path_is_declared(tmp_path: Path) -> None:
    """The plugin lives in a tree ordinary suites import from. One that wrote a file
    on every run would eventually write one nobody asked for."""
    module = tmp_path / "test_trivial.py"
    module.write_text("def test_ok():\n    assert True\n")
    env = dict(os.environ)
    env.pop(OUT_JSON_ENV, None)
    env.pop(OUT_XML_ENV, None)
    env.pop(ESTATE_BEFORE_ENV, None)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")])
    before = set(tmp_path.iterdir())
    done = subprocess.run(
        [
            sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
            "-p", "tools.estate_census.reporter", "-q", "--rootdir", str(tmp_path), str(module),
        ],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False, timeout=300,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert set(tmp_path.iterdir()) == before, "the inert plugin wrote something"


def test_an_unreadable_before_measurement_leaves_the_field_empty_rather_than_inventing_one(
    tmp_path: Path,
) -> None:
    """The classifier refuses a bundle with no measured before-position, so the
    failure surfaces as INDETERMINATE instead of as a run that silently proved
    nothing about the estate."""
    module = tmp_path / "test_trivial.py"
    module.write_text("def test_ok():\n    assert True\n")
    out_json = tmp_path / "bundle.json"
    env = dict(os.environ)
    env[OUT_JSON_ENV] = str(out_json)
    env[ESTATE_BEFORE_ENV] = str(tmp_path / "does-not-exist.json")
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")])
    subprocess.run(
        [
            sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
            "-p", "tools.estate_census.reporter", "-q", "--rootdir", str(tmp_path), str(module),
        ],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False, timeout=300,
    )
    bundle = json.loads(out_json.read_text())
    assert bundle["estate"]["before"] == {}


def test_a_collection_error_is_recorded_rather_than_leaving_a_silent_gap(tmp_path: Path) -> None:
    """Measured: one uncollectable module makes pytest exit 2 having run NOTHING,
    while a summary counting only failures shows none. Both the exit status and the
    collection error must reach the bundle."""
    (tmp_path / "test_good.py").write_text("def test_ok():\n    assert True\n")
    (tmp_path / "test_bad.py").write_text("import a_module_that_does_not_exist\n")
    out_json = tmp_path / "bundle.json"
    env = dict(os.environ)
    env[OUT_JSON_ENV] = str(out_json)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / "runtime")])
    subprocess.run(
        [
            sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
            "-p", "tools.estate_census.reporter", "-q", "--rootdir", str(tmp_path), str(tmp_path),
        ],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False, timeout=300,
    )
    bundle = json.loads(out_json.read_text())
    assert bundle["collection_errors"], "the uncollectable module left no trace"
    assert bundle["provenance"]["exit_status"] == 2


def test_the_reporter_class_can_be_constructed_without_touching_the_filesystem() -> None:
    """A construction guard, so a signature change is caught here rather than only
    inside a subprocess where the failure reads as a pytest problem."""
    reporter = CensusReporter(
        out_json=Path("/dev/null"), out_xml=None, estate_before={}, label="unit"
    )
    assert reporter is not None
