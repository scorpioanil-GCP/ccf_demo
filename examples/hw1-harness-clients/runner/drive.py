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

**Legs are discovered structurally, never listed.** A leg is a `client_*.py`
sitting directly in the example root, and its name is the stem after
`client_`; see :func:`known_legs`. The same discipline
`tests/examples/test_client_example_purity.py::reader_visible_modules` applies
one directory up — and it is what lets a later plan add a harness by adding a
file, with no registry line here to forget. An empty discovery is refused, and
a `--legs` name that was not discovered is an error rather than a silent skip.

**One seeded copy per leg**, plus one for the reference run, all under one
temporary parent removed in a `finally`. Two spawned door children must never
hold one graph, and giving each leg its own copy makes that impossible rather
than merely refused.

**Each leg is checked for the PAYLOAD, not merely for an address**
(:func:`payload_violations`). Every other check in this example reads a 64-hex
string, so a client that printed its content address and nothing else would
pass all of them while "the client prints the returned Context Product" was
false. The markers that check greps for are themselves gated by
:func:`marker_violations`, on the default path, *before* any leg is driven: a
degenerate marker set makes the whole run's payload evidence worthless, and
discovering that after three subprocess drives is discovering it late.

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
from ccf.products.door import PRODUCT_REQUEST_TOOL
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

#: This runner's own directory, and the example tree it copies its subject
#: from. Derived from ``__file__`` rather than from the working directory, so
#: the runner behaves identically under ``make`` and under a bare interpreter
#: invocation from anywhere in the tree.
RUNNER_DIR = pathlib.Path(__file__).resolve().parent

#: This example's root — the directory the harness client programs live in, and
#: the one :func:`known_legs` globs. `H-11` locks its contents to
#: ``client_*.py``, which is what makes the glob a complete leg list.
EXAMPLE_ROOT = RUNNER_DIR.parent

#: The prefix a client program's filename carries. A leg's NAME is the stem
#: after it, so adding a harness is adding a file.
CLIENT_PREFIX = "client_"

#: How long one leg may take, spawn of its own door included. A bound rather
#: than a preference: a leg that never returns would hang CI silently.
LEG_TIMEOUT_SECONDS = 120

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

#: ``consume.py``'s answer size, as printed — ``N of M assembled``. Parsed so a
#: zero-company answer can be refused; see :func:`reference_run`.
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


def client_program(leg: str) -> pathlib.Path:
    """The client program a leg name denotes."""
    return EXAMPLE_ROOT / f"{CLIENT_PREFIX}{leg}.py"


def known_legs() -> tuple[str, ...]:
    """Every leg this runner can drive, derived from the tree rather than listed.

    A leg joins by its ``client_*.py`` existing directly in the example root —
    the same structural discipline
    ``tests/examples/test_client_example_purity.py::reader_visible_modules``
    applies to the same directory, and the reason a later plan adds a harness
    without editing a registry line here.

    The non-recursive glob is deliberate: this runner lives one directory down
    precisely so it is not itself a client, and a recursive walk would sweep it
    back in.

    Raises:
        AssertionError: no client program was discovered. A run over no legs
            would compare nothing and report the strongest claim in this
            example on the strength of it.
    """
    legs = tuple(
        sorted(
            path.stem[len(CLIENT_PREFIX) :]
            for path in EXAMPLE_ROOT.glob(f"{CLIENT_PREFIX}*.py")
        )
    )
    if not legs:
        raise AssertionError(
            f"no {CLIENT_PREFIX}*.py program sits in {EXAMPLE_ROOT}, so this"
            " runner would drive nothing and pass"
        )
    return legs


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


def marker_violations(names: Sequence[str], chrome_words: Sequence[str]) -> list[str]:
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
    4. No word colliding with ``chrome_words``, the words the runner and the
       reference client print themselves.

    An empty marker set is refused too: a payload assertion over no markers is
    a vacuous pass, which is the failure mode the other three exist to prevent
    one row at a time.

    ``chrome_words`` is a PARAMETER and never a global read inside this
    function — :data:`CONSOLE_VOCABULARY` is what the default path passes. Both
    of this check's inputs being arguments is what lets a control feed it a
    doctored vocabulary and watch property 4 fire on its own, which is the
    difference between a checked property and a claimed one.
    """
    chrome = frozenset(chrome_words)
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
        collisions = sorted(word for word in _words(name) if word in chrome)
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


def observed_markers(stdout: str, declared_names: Sequence[str]) -> list[str]:
    """The declared names that actually appear in ``stdout``, in declared order."""
    return [name for name in declared_names if name in stdout]


def payload_violations(
    reference_stdout: str,
    leg_stdout: str,
    declared_names: Sequence[str],
) -> list[str]:
    """Criteria 1-3, as a function of three arguments a control can doctor.

    Each criterion says the client *prints the returned Context Product*. Every
    other check in this phase reads a 64-hex content address — so a client that
    printed its address and nothing else would satisfy all of them while
    criteria 1-3 were false. This is the check that refuses that client, and
    **CONTROL A** is the doctored stdout that is exactly its shape.

    Three violations, and the third is the one an equal content address does
    not already rule out:

    - ``declared_names`` empty — a marker search over no markers is a vacuous
      pass. :func:`marker_violations` is the deeper guard on the same concern;
      this is the floor beneath it, so a caller cannot reach a vacuous pass by
      handing this function an empty list directly.
    - no declared name in ``leg_stdout`` — the leg printed an address and not a
      product.
    - the SET of declared names in ``leg_stdout`` differs from the set in
      ``reference_stdout`` — the leg printed *a* product, but not the same one.
      A client that truncates, paginates or reformats what it prints reports
      the same address while showing the reader less than the reference did,
      and only a set comparison sees it.

    Args:
        reference_stdout: What ``consume.py`` printed for the same question.
        leg_stdout: What the harness client printed.
        declared_names: The payload markers, from
            ``examples/hw1-harness-clients/runner/scenario-rows.yaml``.

    Returns:
        One violation per property broken; empty when the leg printed the
        product.
    """
    violations: list[str] = []
    if not declared_names:
        violations.append(
            "no declared markers — a payload assertion over an empty marker set"
            " passes without reading any output at all"
        )
    in_leg = observed_markers(leg_stdout, declared_names)
    in_reference = observed_markers(reference_stdout, declared_names)
    if declared_names and not in_leg:
        violations.append(
            "the leg's stdout carries no declared company name, so it printed a"
            " content address rather than the Context Product the address names"
        )
    if set(in_leg) != set(in_reference):
        violations.append(
            f"the leg's stdout names {sorted(in_leg)} and the reference names"
            f" {sorted(in_reference)}; an equal content address does not by"
            " itself make two printed products the same product"
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

    **The shape has three keys, and each earns its place.** ``arguments`` is
    what the tool takes, minus the one argument a client must build itself.
    ``tool`` is the tool's NAME, read from
    ``ccf.products.door::PRODUCT_REQUEST_TOOL`` rather than spelled, so no
    client selects a tool from a literal of its own and a rename of the SDK's
    tool reaches the legs without touching them. ``temporal_boundary`` is
    stated separately because it is not a tool argument: it is the third field
    of the encoded ``WireRequest`` each client builds, and a client inferring
    it from ``asked_at`` would be inferring rather than being told — right on
    this pinned path and wrong on a deferred one, which is the worst kind of
    correct.
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
        "tool": PRODUCT_REQUEST_TOOL,
        "temporal_boundary": as_of,
        "arguments": {
            "tenant": config["tenant_id"],
            "product_class": product_class["schema_name"],
            "version": product_class["schema_version"],
            "subject": question["subject"],
            "intent": question["intent"],
            "freshness": question["freshness"],
            "asked_at": as_of,
            "parameters": parameters,
        },
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


def reference_run(root: pathlib.Path, as_of: str) -> tuple[str, str]:
    """Ask the reference client the same question; return its address and stdout.

    Criterion 4's reference leg. ``consume.py`` runs as a subprocess against
    the SAME subject every other leg reaches, addressed only through
    ``CCF_BINDING`` — that is the whole channel, because ``consume.py`` calls
    ``ProductClient.for_product`` with no address argument.

    **Both halves are returned because both are compared.** The address is
    criterion 4's operand; the stdout is :func:`payload_violations`' second
    operand, and re-running the reference to obtain it would be running two
    references and comparing the legs against whichever answered second.

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
            str(screening_threshold(question["arguments"]["parameters"])),
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
    return found.group(1), completed.stdout


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


def drive_leg(leg: str, root: pathlib.Path, as_of: str) -> tuple[str, str]:
    """Run one harness client against ``root``; return its address and stdout.

    The three flags are the whole contract (`H-03`): the door's location as an
    opaque ``command + args`` pair, and the question as one JSON document.
    Neither is knowledge the client holds.

    **Both streams ride the failure message.** ADK writes ``[EXPERIMENTAL]``
    warnings and the spawned door logs to stderr, so a non-zero exit is
    unreadable without it. **The address is parsed from stdout alone**, which
    is the other half of the same decision: a leg cannot report an address by
    logging one.

    No child-termination helper is needed or wanted here. ``subprocess.run``
    cannot outlive its own call and kills the child on ``timeout``, and the
    door is spawned by the client's own harness library (`H-01`), one process
    further down than this runner can see.
    """
    command, arguments = resolve_door(root)
    completed = subprocess.run(
        [
            sys.executable,
            str(client_program(leg)),
            "--server-command",
            command,
            *_repeated("--server-arg", arguments),
            "--question-json",
            json.dumps(build_question(root, as_of)),
        ],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=LEG_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"leg {leg!r} exited {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    found = _CONTENT_ADDRESS_RE.search(completed.stdout)
    if found is None:
        raise AssertionError(
            f"leg {leg!r} printed no content address on stdout\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return found.group(1), completed.stdout


def _repeated(flag: str, values: Sequence[str]) -> list[str]:
    """Flatten ``values`` into a repeated ``flag`` argument list, in order."""
    return [item for value in values for item in (flag, value)]


def main() -> int:
    """Seed the subjects, ask the question every way, and compare the answers.

    Sync, and it enters no event loop: whatever asynchrony a harness needs is
    the harness's, inside its own client program. Every child this entry point
    starts goes through ``subprocess.run`` and cannot outlive the call — the
    door itself is spawned by each client's own library (`H-01`), never here.

    The order is deliberate. The markers are checked first, because a
    degenerate marker set makes every payload observation below it worthless
    and finding that out after three subprocess drives is finding it out late.
    Then the reference answers. Then each leg, against its own copy. Then one
    failure channel for all three checks — divergent addresses, address-only
    output, and a marker set that could not have carried the claim.
    """
    parser = argparse.ArgumentParser(description="Drive the hw1 harness clients.")
    discovered = known_legs()
    parser.add_argument(
        "--legs",
        default=",".join(discovered),
        help=f"comma-separated subset of: {','.join(discovered)}",
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
    unknown = sorted(set(legs) - set(discovered))
    if unknown:
        raise AssertionError(f"unknown legs: {unknown}; discovered {list(discovered)}")

    violations: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ccf-hw1-clients-") as scratch:
        with contextlib.ExitStack() as stack:
            subject = _subject_factory(stack, pathlib.Path(scratch), live=args.live)

            root = subject("reference")
            rows = declared_rows(DECLARED_ROWS_DOCUMENT, scenario_attributes(root))
            markers = declared_markers(rows, scenario_attributes(root))
            violations += _labelled(
                "the declared markers cannot carry a payload assertion",
                marker_violations(markers, sorted(CONSOLE_VOCABULARY)),
            )
            if violations:
                raise AssertionError("\n  ".join(violations))

            command, arguments = resolve_door(root)
            print(f"subject             {root}")
            print(f"door command        {command}")
            print(f"door args           {arguments}")
            print(f"question            {json.dumps(build_question(root, AS_OF))}")

            reference, reference_stdout = reference_run(root, AS_OF)
            print(f"reference address   {reference}")

            observed: dict[str, str] = {}
            for leg in legs:
                address, stdout = drive_leg(leg, subject(leg), AS_OF)
                observed[leg] = address
                payload = payload_violations(reference_stdout, stdout, markers)
                violations += _labelled(f"leg {leg!r} did not print the product", payload)
                verdict = "MATCH" if address == reference else "DIVERGED"
                names = ", ".join(observed_markers(stdout, markers))
                print(f"leg {leg:<16}{address}  {verdict}  names: {names}")

            violations += _labelled(
                "the harness legs did not agree with the reference",
                compare_addresses(reference, observed),
            )

    if violations:
        raise AssertionError("\n  ".join(violations))
    print(f"legs compared       {len(legs)}")
    return 0


def _subject_factory(
    stack: contextlib.ExitStack, scratch: pathlib.Path, *, live: bool
) -> Any:
    """One seeded copy per named consumer — or the tracked deployment, `H-09`.

    ``--live`` means one thing across every leg: point at a real populated
    deployment instead of a seeded temporary copy. It is the choice of subject
    root and NOTHING else, so the leg-driving code path below is identical
    either way and no branch exists that CI never exercises.
    """

    def subject(name: str) -> pathlib.Path:
        if live:
            return SOURCE_DEPLOYMENT
        return stack.enter_context(seeded_subject(scratch / name))

    return subject


def _labelled(heading: str, violations: Sequence[str]) -> list[str]:
    """Prefix a check's violations with what failed, for one shared channel."""
    return [f"{heading}:\n    " + "\n    ".join(violations)] if violations else []


if __name__ == "__main__":
    sys.exit(main())
