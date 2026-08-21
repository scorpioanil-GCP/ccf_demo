"""The fabric-side runner for `examples/hw1-harness-clients` — one door, three
harnesses, one content address.

**This file is fabric-side, and it is the one file in this example permitted to
import `ccf`** (`H-02`). Everything beside it under the example root is a
harness client that must not know CCF exists: a client receives the door's
location as an opaque `command + args` pair and the question as an address, and
it learns both from `argv`. What this runner does is produce those two inputs
honestly — resolve them from the deployment's own documents rather than compose
them from remembered values — and then answer the question itself, through the
reference client, so there is something for each leg's answer to be compared
against.

**Why it lives in a subdirectory, and why the name is `drive.py`.** Two shipped
gates meet here and neither may be weakened:

* `tests/examples/test_client_example_purity.py::reader_visible_modules` walks
  each client example root with a NON-RECURSIVE `glob("*.py")`. This runner
  imports `ccf`, so it would fail that purity gate on sight — and it is exempt
  not by an allowlist entry but *structurally*, by living one directory down
  where the glob cannot see it (`H-11`). **Moving this file to the example root
  would silently exempt nothing and fail everything**; moving the gate would be
  weakening a rule to accommodate a file, which `H-12` forbids.
* `tests/examples/test_artifact_schema_headers.py` enforces a bijection between
  `examples/**/artifacts/` directories and example roots, where an example root
  is defined mechanically as a directory DIRECTLY CONTAINING `run.py`. Naming
  this file `run.py` would make `runner/` an example root in its own right and
  demand an `artifacts/` directory it has no artifacts for. The natural name for
  a runner is precisely the one that breaks the gate. Do not "tidy" it back.

**What the runner hands each leg** (`H-03`): three flags, and no more —
`--server-command`, a repeatable `--server-arg`, and a single `--question-json`.
The eight values the door requires (tenant, product class, its registered
version, subject, intent, freshness, the temporal boundary, and the request
parameters) are deployment facts, so under CLAUDE.md §9 they may not be literals
in client code; they travel as one JSON document rather than as eight scalar
flags because eight flags is eight parsing sites in each of three clients, and
three items of `argv` is what makes the three clients readably the same program
three ways.

**What the runner answers against** (`H-05`). The CI subject is a seeded
temporary copy of `examples/hw1-companies-over-revenue/deployment`, never the
tracked tree, and each consumer takes its own copy so two server children can
never hold one graph. The copy carries `deployment/` and `server/` under one
temp parent because `binding.yaml`'s `server:` key resolves against the
directory HOLDING the deployment and the loader refuses a value that resolves
inside it — a copy without the sibling produces a refusal that reads exactly
like a deployment declaring no server.

**The seeding writer is closed before anything else boots.** The writer is held
per graph (`ccf.graph._writer::_LIVE_WRITERS`), so a seeder that stayed open
would make the door's own boot raise `SingleWriterViolation` and this example
would be measuring the seed's failure to let go rather than anything about a
client. `tests/client/conftest.py::seed` is the pattern; it is re-implemented
here rather than imported, because a shipped example must not depend on the test
tree.

Run it: `make example-hw1-harness-clients`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from typing import Any, cast

import yaml

from ccf.client.adapters.binding_document import load_binding_document
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_config_and_boot
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

#: This runner's own directory, and the example tree it copies its subject
#: from. Derived from ``__file__`` rather than from the working directory, so
#: the runner behaves identically under ``make`` and under a bare interpreter
#: invocation from anywhere in the tree.
RUNNER_DIR = pathlib.Path(__file__).resolve().parent

#: The tracked example whose deployment this one borrows. `H-05`: borrowed by
#: COPY. Nothing in this module ever opens a path under it for writing.
SOURCE_EXAMPLE = RUNNER_DIR.parents[1] / "hw1-companies-over-revenue"

#: The two tracked directories the subject is built from. They must land beside
#: each other under one parent (see :func:`build_subject`).
SOURCE_DEPLOYMENT = SOURCE_EXAMPLE / "deployment"
SOURCE_SERVER = SOURCE_EXAMPLE / "server"

#: The declared input document this runner interprets — the rows the temporary
#: subject is seeded with. `D-IMPL-163` (Dave, 2026-08-20) narrows `D-32` to
#: producer OUTPUT, which is what makes a declared input document beside its
#: reader admissible; the document states the reasoning at length.
DECLARED_ROWS_DOCUMENT = RUNNER_DIR / "scenario-rows.yaml"

#: The second declared input document: what this demonstration ASKS. Its
#: header states why a threshold cannot be a constant in this file (CLAUDE.md
#: §6.4 names one explicitly) and why a demonstration's number is not part of
#: the question's identity (``D-IMPL-131``).
DECLARED_QUESTION_DOCUMENT = RUNNER_DIR / "question.yaml"

#: The reference client — the SAME program the two ``example-hw1*`` recipes
#: run, driven here against the seeded copy. Reference rather than replica: a
#: second implementation of "ask this product" would be a second thing to keep
#: in step, and the address it produced would prove that instead.
CONSUME_PROGRAM = SOURCE_EXAMPLE / "consume.py"

#: The temporal boundary every leg pins, read from the declared question
#: document rather than spelled here.
AS_OF = str(
    cast(
        Mapping[str, Any],
        yaml.safe_load(DECLARED_QUESTION_DOCUMENT.read_text(encoding="utf-8")),
    )["as_of"]
)

#: The legs this runner knows how to drive. Empty in this plan by design: the
#: substrate is proven before any leg exists, because a leg wired against an
#: unproven substrate measures the substrate's failure and reports it as the
#: leg's. Wave 3 and wave 4 append.
KNOWN_LEGS: tuple[str, ...] = ()

#: ``consume.py``'s answer size, as printed — ``N of M assembled``. Parsed so a
#: zero-company answer can be refused; see :func:`reference_address`.
_ANSWER_COUNT_RE = re.compile(r"^\s*(\d+) of (\d+) assembled", re.MULTILINE)

#: ``consume.py``'s content-address line. The address is 64 hex characters
#: because it is a sha256 over the product's canonical bytes.
_CONTENT_ADDRESS_RE = re.compile(r"content address\s+([0-9a-f]{64})")

#: What a populated deployment leaves on disk, and what must therefore never
#: ride into the copy. **Load-bearing, not tidiness.**
#: ``examples/hw1-companies-over-revenue/deployment/graph.sqlite3`` exists in a
#: developer's working tree right now — it is gitignored, not absent — so a
#: plain ``copytree`` carries a populated graph in, makes the seed's own effect
#: unmeasurable, and makes CI and a developer's machine disagree about what was
#: proven. ``__pycache__`` joins the list because a stale compiled sibling is
#: state too.
COPY_IGNORE = shutil.ignore_patterns("graph.sqlite3*", "artifact-store", "__pycache__")

#: The one ROLE name this runner spells. Roles are the interface the declared
#: document and the deployment's ``scenario.yaml`` share; the SOURCE keys they
#: map onto are the deployment's own vocabulary and are read, never spelled.
NAME_ROLE = "name"

#: Shortest usable payload marker. Below this a token occurs by accident inside
#: a path, a flag, or a run of hex digits, and a stdout match stops meaning that
#: the payload was printed. Stated by
#: ``examples/hw1-harness-clients/runner/scenario-rows.yaml``, checked by
#: :func:`marker_violations`.
MINIMUM_MARKER_CHARS = 4

#: The words the runner and the reference client print themselves, taken from
#: ``examples/hw1-companies-over-revenue/consume.py::main`` and from this
#: module's own output. A declared name sharing a word with this set would make
#: "stdout carries a declared company name" true of a run that printed nothing
#: but chrome — which is the assertion the markers exist to make meaningful.
CONSOLE_VOCABULARY: frozenset[str] = frozenset(
    {
        "answer",
        "address",
        "assembled",
        "boundary",
        "commands",
        "companies",
        "content",
        "context",
        "debt",
        "detail",
        "door",
        "expires",
        "governance",
        "lineage",
        "of",
        "perspective",
        "record",
        "refused",
        "replay",
        "revenue",
        "server",
        "temporal",
    }
)

#: A name made only of hex digits and spaces. Such a name matches INSIDE the
#: 64-character content address every leg prints.
_HEX_ONLY_RE = re.compile(r"[0-9a-fA-F ]+")

#: Word split for the console-vocabulary comparison. Punctuation is not part of
#: a word, so ``Halcyon-Revenue`` collides exactly as ``Halcyon Revenue`` does.
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _words(text: str) -> list[str]:
    """The lowercased words of ``text``, for the vocabulary comparison."""
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def _document(path: pathlib.Path) -> Mapping[str, Any]:
    """Parse one YAML document this runner reads as data."""
    return cast(Mapping[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def scenario_attributes(root: pathlib.Path) -> Mapping[str, str]:
    """The role→source-key mapping, read from the COPY's own ``scenario.yaml``.

    The three roles this deployment names are read, never spelled. A runner
    restating the source keys would have hard-coded the deployment's vocabulary
    into a second place, and the two would drift silently — the same objection
    ``examples/hw1-companies-over-revenue/deployment/projection.py`` records for
    itself.
    """
    return cast(Mapping[str, str], _document(root / "scenario.yaml")["attributes"])


def declared_rows(
    document: pathlib.Path, attributes: Mapping[str, str]
) -> list[dict[str, str]]:
    """The declared rows, keyed by this deployment's own source vocabulary.

    ``document`` is keyed by ROLE (``reference``, ``name``, ``revenue``);
    ``attributes`` is the deployment's role→key mapping. Applying one to the
    other here is what keeps the two documents from drifting: neither states the
    other's vocabulary.

    Values are stringified because a claim attribute is text on the way in —
    ``projection.py`` reads the revenue back through ``Decimal(...)`` — and
    because a float never reaches the wire in this SDK at all.
    """
    rows = _document(document)["companies"]
    return [
        {attributes[role]: str(value) for role, value in row.items()} for row in rows
    ]


def declared_markers(
    rows: Sequence[Mapping[str, str]], attributes: Mapping[str, str]
) -> list[str]:
    """The declared names, in document order — the payload markers.

    Plans ``20-03`` and ``20-04`` assert that a leg's stdout carries the product
    PAYLOAD rather than merely a content address, and they do it by looking for
    these names. Read through ``attributes`` like every other value, so the one
    role name spelled here is :data:`NAME_ROLE` and no source key is.
    """
    return [row[attributes[NAME_ROLE]] for row in rows]


def marker_violations(names: Sequence[str]) -> list[str]:
    """Refuse a marker set that would make the payload assertion vacuous.

    ``examples/hw1-harness-clients/runner/scenario-rows.yaml`` states four
    properties its ``name`` values must hold and names this function as the
    thing that checks them mechanically. Renaming a company to something
    generic breaks the downstream payload assertion **without failing anything
    that looks related**, which is exactly the class of defect a check has to
    exist for. The four, in order:

    1. Distinct names, each at least :data:`MINIMUM_MARKER_CHARS` long. A
       shorter token occurs by accident in a path, a flag or a run of hex.
    2. No name a substring of another, case-insensitively — a stdout match on
       the shorter one could not say which row printed.
    3. No name matching only hex digits and spaces. Such a name matches INSIDE
       the 64-hex content address the legs also print, so the payload assertion
       would pass on chrome alone.
    4. No word colliding with :data:`CONSOLE_VOCABULARY`, the words the runner
       and the reference client print themselves.

    An empty marker set is refused too: a payload assertion over no markers is
    a vacuous pass, which is the failure mode the other three exist to prevent
    one row at a time.
    """
    violations: list[str] = []
    if not names:
        violations.append(
            "no declared markers — a payload assertion over an empty marker set"
            " passes without reading any output at all"
        )
    seen: set[str] = set()
    for name in names:
        lowered = name.lower()
        if lowered in seen:
            violations.append(f"{name!r} is declared twice; markers must be distinct")
        seen.add(lowered)
        if len(name) < MINIMUM_MARKER_CHARS:
            violations.append(
                f"{name!r} is shorter than {MINIMUM_MARKER_CHARS} characters and"
                " would match by accident in a path, a flag or a run of hex"
            )
        if _HEX_ONLY_RE.fullmatch(name):
            violations.append(
                f"{name!r} is hex digits and spaces only, so it matches inside the"
                " 64-character content address every leg prints"
            )
        collisions = sorted(
            word for word in _words(name) if word in CONSOLE_VOCABULARY
        )
        if collisions:
            violations.append(
                f"{name!r} collides with console vocabulary {collisions}; a marker"
                " the runner prints itself is true of a run that printed no payload"
            )
    for index, name in enumerate(names):
        for other_index, other in enumerate(names):
            if index != other_index and name.lower() in other.lower():
                violations.append(
                    f"{name!r} is a substring of {other!r}; a stdout match on the"
                    " shorter one cannot say which row printed"
                )
    return violations


def build_subject(parent: pathlib.Path) -> pathlib.Path:
    """Copy ``deployment/`` and ``server/`` under one parent; return the root.

    **Copying the deployment alone is a defect.** ``binding.yaml`` declares
    ``server: server/serve.py``, resolved against the directory HOLDING the
    deployment (``D-10``), and ``load_binding_document`` refuses a value that
    resolves back inside the root. A copy without the sibling therefore produces
    a refusal that reads exactly like a deployment declaring no server at all.
    No ``binding.yaml`` rewrite is needed for the copy: the relative value is
    already correct against the new parent.

    ``server/compose.py`` and ``server/egress-door.yaml`` travel too —
    ``serve.py`` does ``from compose import compose``, relying on its own
    directory being on ``sys.path`` as a spawned script.
    """
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / SOURCE_DEPLOYMENT.name
    shutil.copytree(SOURCE_DEPLOYMENT, root, ignore=COPY_IGNORE)
    shutil.copytree(SOURCE_SERVER, parent / SOURCE_SERVER.name, ignore=COPY_IGNORE)
    return root


def seed(root: pathlib.Path) -> int:
    """Populate the copy's graph from the declared document, then let go.

    Boots from the copy's own ``ccf_config.yaml`` with the connection
    ``load_binding_document`` resolves from the copy's own ``binding.yaml``.
    **Never a recomposed connection**: ``binding.yaml`` states
    ``connection.database_path.path`` relative to the deployment root, so a
    seeder composing its own would be a second place the graph's location is
    decided — it would seed one file while the door booted another, and every
    assertion downstream would measure an empty fabric.

    The ``finally`` close is the load-bearing line. It releases
    ``ccf.graph._writer::_LIVE_WRITERS``; without it the door's own boot raises
    ``SingleWriterViolation`` and this example measures the seed rather than the
    client.

    Returns:
        The number of rows ingested.
    """
    document = _document(DECLARED_ROWS_DOCUMENT)
    observed_at = datetime.fromisoformat(str(document["observed_at"]))
    rows = declared_rows(DECLARED_ROWS_DOCUMENT, scenario_attributes(root))

    booted = load_config_and_boot(
        root / "ccf_config.yaml",
        registry=ControlPlaneRegistry(),
        connection=load_binding_document(root).connection,
    )
    try:
        for index, payload in enumerate(rows):
            booted.handle.worker.ingest(
                SignalEnvelope(
                    tenant_id=booted.tenant_id,
                    envelope_id=f"{DECLARED_ROWS_DOCUMENT.stem}/{index}",
                    source=SourceIdentity(system_id=DECLARED_ROWS_DOCUMENT.stem),
                    # Both instants come from the document. `observed_time`
                    # becomes the claim's `valid_from` and `ingestion_timestamp`
                    # becomes its `observed_at` — the figure the half-life curve
                    # reads — so a clock read in either position would make the
                    # served content address move between runs.
                    ingestion_timestamp=observed_at,
                    observed_time=observed_at,
                    raw_payload=dict(payload),
                )
            )
    finally:
        booted.handle.close()
    return len(rows)


@contextlib.contextmanager
def seeded_subject(parent: pathlib.Path) -> Iterator[pathlib.Path]:
    """Build a subject under ``parent``, seed it, and yield its deployment root.

    Composed as a context manager so a caller cannot reach a seeded subject
    without having gone through the close in :func:`seed`. **One seeded copy per
    consumer** (`H-05` leaves this to discretion; this is the call): the
    reference run takes its own and each client leg takes its own, so two server
    children holding one graph is impossible rather than merely refused — the
    discipline ``tests/client/conformance/conftest.py`` already states for its
    subjects.
    """
    root = build_subject(parent)
    seed(root)
    yield root


def resolve_door(root: pathlib.Path) -> tuple[str, list[str]]:
    """The opaque ``command + args`` pair a client hands to its harness.

    Resolved from the deployment's OWN ``binding.yaml`` through the shipped
    loader, never composed from a remembered path: ``server:`` resolves against
    the directory holding the deployment (``D-10``), and a runner that rebuilt
    that path itself would be a second place the program's location is decided.
    The shape is the one ``ccf.client.adapters.mcp_stdio::McpStdioAdapter``
    builds for ``StdioServerParameters`` — the interpreter, then the program and
    the deployment root — because the whole point of `H-02` is that what a
    client receives is an ordinary program invocation and nothing CCF-shaped.
    """
    return sys.executable, [str(load_binding_document(root).server), str(root)]


def request_violations(
    parameters: Mapping[str, Any], required: Sequence[str]
) -> list[str]:
    """Refuse a declared request the deployment's contract does not accept.

    The declared question document states parameters by NAME; the deployment
    states which names its request contract requires. Comparing them here is
    what lets the runner spell no parameter name of its own and still fail
    loudly when the two documents drift apart — rather than sending a request
    the door refuses several layers away from the edit that caused it.

    An empty ``required`` is itself a violation: a name comparison against an
    empty contract passes for every possible question, which is a vacuous
    check rather than a passing one.
    """
    violations: list[str] = []
    if not required:
        violations.append(
            "the deployment's request contract requires no parameters, so a name"
            " comparison against it would pass for any question at all"
        )
    declared = set(parameters)
    expected = set(required)
    for name in sorted(declared - expected):
        violations.append(
            f"the declared question supplies {name!r}, which this deployment's"
            " request contract does not require"
        )
    for name in sorted(expected - declared):
        violations.append(
            f"this deployment's request contract requires {name!r}, which the"
            " declared question does not supply"
        )
    for name, value in sorted(parameters.items()):
        if isinstance(value, float):
            violations.append(
                f"{name!r} is declared as a float; `WireRequest` refuses one,"
                " because canonical JSON renders it as text"
            )
    return violations


def build_question(root: pathlib.Path, as_of: str) -> dict[str, Any]:
    """The question's address, assembled from the subject's own documents.

    Eight values the door requires — ``tenant``, ``product_class``,
    ``version``, ``subject``, ``intent``, ``freshness``, ``asked_at`` and the
    request ``parameters`` — are deployment facts, so under CLAUDE.md §9 they
    may not be literals in client code. The runner resolves them here and each
    client receives them on ``argv`` as one ``--question-json`` document
    (`H-03`): the client learns the question's address as INPUT, never as
    knowledge, and its ``argv`` surface stays at three items.

    ``asked_at`` is the boundary this run pins, not ``binding.yaml``'s
    ``question.asked_at``. That key answers ``as_of=None`` — the deployment's
    stated decision instant when a caller defers (``D-04``) — and criterion 4
    compares one content address across three harnesses, so every leg pins the
    boundary explicitly and an unpinned run is not a pinned comparison.
    """
    binding = _document(root / "binding.yaml")
    config = _document(root / "ccf_config.yaml")
    declared = _document(DECLARED_QUESTION_DOCUMENT)
    product_class = config["product_class"]
    question = binding["question"]
    parameters = dict(declared["parameters"])

    violations = request_violations(
        parameters, list(config["request_contract"]["arguments"]["required"])
    )
    if violations:
        raise AssertionError(
            f"{DECLARED_QUESTION_DOCUMENT} and {root / 'ccf_config.yaml'}"
            " disagree about what this product is asked:\n  " + "\n  ".join(violations)
        )

    return {
        "tenant": config["tenant_id"],
        "product_class": product_class["schema_name"],
        "version": product_class["schema_version"],
        "subject": question["subject"],
        "intent": question["intent"],
        "freshness": question["freshness"],
        "asked_at": as_of,
        "parameters": parameters,
    }


def screening_threshold(parameters: Mapping[str, Any]) -> int:
    """The single declared request parameter, as ``consume.py``'s one flag.

    ``consume.py`` takes the screening threshold as ``--min-revenue``. Which
    declared parameter that flag carries is resolved by there being exactly
    one, and the runner refuses rather than guesses if that stops being true —
    a deployment growing a second request parameter needs a decision about
    which flag carries which, not a runner that silently picks the first.
    """
    if len(parameters) != 1:
        raise AssertionError(
            f"{DECLARED_QUESTION_DOCUMENT} declares {len(parameters)} request"
            " parameters; `consume.py` takes exactly one screening threshold on"
            " `--min-revenue`, so which parameter it carries is no longer"
            " resolvable by there being only one"
        )
    (value,) = parameters.values()
    return int(value)


def reference_address(root: pathlib.Path, as_of: str) -> str:
    """Ask the reference client the same question, and return its address.

    Criterion 4's reference leg. ``consume.py`` runs as a subprocess against
    the SAME subject every other leg reaches, addressed only through
    ``CCF_BINDING`` — that is the whole channel, because ``consume.py`` calls
    ``ProductClient.for_product`` with no address argument.

    **A non-empty answer is required.** An empty deployment yields a perfectly
    real content address, which is exactly why "it printed an address" is not
    evidence: the seed has to be observable in the answer, or criterion 4's
    comparison is true and uninteresting. The assembled count is parsed and a
    zero raises with both captured streams.
    """
    question = build_question(root, as_of)
    completed = subprocess.run(
        [
            sys.executable,
            str(CONSUME_PROGRAM),
            "--min-revenue",
            str(screening_threshold(question["parameters"])),
            "--as-of",
            as_of,
        ],
        env={**os.environ, "CCF_BINDING": f"inprocess:{root}"},
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"the reference client exited {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )

    counted = _ANSWER_COUNT_RE.search(completed.stdout)
    if counted is None:
        raise AssertionError(
            "the reference client printed no assembled count, so its answer"
            " cannot be shown to be non-empty\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if int(counted.group(1)) == 0:
        raise AssertionError(
            "the reference answer names zero companies — an unseeded subject"
            " still yields a real content address, so a comparison against this"
            " one would be true and uninteresting\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )

    found = _CONTENT_ADDRESS_RE.search(completed.stdout)
    if found is None:
        raise AssertionError(
            "the reference client printed no content address\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return found.group(1)


def compare_addresses(reference: str, observed: Mapping[str, str]) -> list[str]:
    """Criterion 4, as a function of two arguments a control can doctor.

    Returns one violation per leg whose address differs from the reference, and
    one violation when ``observed`` is empty — a comparison over no legs is a
    vacuous pass, and a runner that lost its legs would otherwise report the
    strongest claim in this example on the strength of having compared nothing.
    """
    violations: list[str] = []
    if not observed:
        violations.append(
            "no leg reported a content address, so the cross-harness comparison"
            " compared nothing and passed"
        )
    for leg, address in sorted(observed.items()):
        if address != reference:
            violations.append(
                f"leg {leg!r} reported {address}, the reference reported"
                f" {reference}"
            )
    return violations


def main() -> int:
    """Seed a subject, resolve the door, ask the question, compare the answers.

    Sync, and it enters no event loop: whatever asynchrony a harness needs is
    the harness's, inside its own client program. The only child this entry
    point starts is the reference client, through ``subprocess.run``, which
    cannot outlive the call — the door itself is spawned by each client's own
    library (`H-01`), never here.
    """
    parser = argparse.ArgumentParser(description="Drive the hw1 harness clients.")
    parser.add_argument(
        "--legs",
        default=",".join(KNOWN_LEGS),
        help=f"comma-separated subset of: {','.join(KNOWN_LEGS) or '(none wired yet)'}",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="point every leg at the real tracked deployment instead of a"
        " seeded temporary copy (it must already be populated); one meaning"
        " across all legs",
    )
    args = parser.parse_args()
    legs = tuple(leg.strip() for leg in args.legs.split(",") if leg.strip())
    unknown = sorted(set(legs) - set(KNOWN_LEGS))
    if unknown:
        raise AssertionError(f"unknown legs: {unknown}")

    with tempfile.TemporaryDirectory(prefix="ccf-hw1-clients-") as scratch:
        with contextlib.ExitStack() as stack:
            if args.live:
                root = SOURCE_DEPLOYMENT
            else:
                root = stack.enter_context(
                    seeded_subject(pathlib.Path(scratch) / "reference")
                )
            rows = declared_rows(DECLARED_ROWS_DOCUMENT, scenario_attributes(root))
            _refuse_bad_markers(rows, root)

            command, arguments = resolve_door(root)
            print(f"subject             {root}")
            print(f"door command        {command}")
            print(f"door args           {arguments}")
            print(f"question            {json.dumps(build_question(root, AS_OF))}")

            reference = reference_address(root, AS_OF)
            print(f"reference address   {reference}")

            observed: dict[str, str] = {}
            violations = compare_addresses(reference, observed) if legs else []
            if violations:
                raise AssertionError(
                    "the harness legs did not agree with the reference:\n  "
                    + "\n  ".join(violations)
                )
    print(f"legs compared       {len(legs)}")
    return 0


def _refuse_bad_markers(rows: Sequence[Mapping[str, str]], root: pathlib.Path) -> None:
    """Check the declared markers on the default path, and refuse a bad set."""
    violations = marker_violations(
        declared_markers(rows, scenario_attributes(root))
    )
    if violations:
        raise AssertionError(
            "the declared markers cannot carry a payload assertion:\n  "
            + "\n  ".join(violations)
        )


if __name__ == "__main__":
    sys.exit(main())
