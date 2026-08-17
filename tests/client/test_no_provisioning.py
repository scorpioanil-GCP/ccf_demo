"""`D-16` — a client call asks a question. It never provisions anything.

The boundary this defends is the one Phase 16's rejected example got wrong, and
the failure was not subtle in hindsight: a consumer that wanted to ask one
question ended up starting a container, minting a store name and creating a
schema, because the example's "run it" path and its "produce it" path were the
same path. The deployment a binding address names is **already populated** —
that is the producer's job, done before a client exists — and a client call that
provisioned would make asking a question a producer-side act.

So this module refuses four constructs inside ``src/ccf/client/``, and **all
four were derived by reading what the rejected example actually did** rather
than by imagining threats:

============================ ==================================================
construct                    where it was measured
============================ ==================================================
a container-management       ``examples/…/scenario/provision.py`` imports
import                       ``PostgresContainer`` and calls ``.start()``
a DDL string literal         the same tree's ``schema.sql`` / seeding path
``uuid4()`` minting a name   ``examples/…/deployment.py::connection`` composes
                             a store name as ``f"{prefix}_{uuid4().hex}"``
a call to ``worker.ingest``  the L1 write path itself — the single-writer
                             handle a client must never reach
============================ ==================================================

**The gate is a function of a source root, not of a fixed path.** That is the
whole design of it. A gate pinned to ``src/ccf/client`` cannot be sabotaged
without editing the real tree and reverting, which leaves nothing behind and
proves nothing on any later CI run. Parameterized, the shipped assertion passes
the real client root and every control passes a ``tmp_path`` tree into **the
same function** — so what the controls prove is that the shipped check fires,
not that a copy of it does.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ccf.client.adapters import inprocess
from ccf.client.binding import SCHEME_REGISTRY
from ccf.client.client import ProductClient

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

#: The client tree the shipped assertion scans.
CLIENT_ROOT = SRC_ROOT / "ccf" / "client"

#: Top-level packages that exist to start and stop infrastructure. Matched on
#: the **root** of a dotted import, so ``testcontainers.community.postgres``
#: is caught by the same entry as ``testcontainers``.
CONTAINER_PACKAGES: frozenset[str] = frozenset(
    {"testcontainers", "docker", "podman", "subprocess"}
)

#: Statements that change a store's shape rather than read it. Two words each,
#: deliberately: a single ``create`` would flag ordinary prose such as "create a
#: client", and a gate that cries wolf gets relaxed rather than obeyed.
DDL_PHRASES: tuple[str, ...] = (
    "create table",
    "create schema",
    "create database",
    "create index",
    "drop table",
    "drop schema",
    "drop database",
    "alter table",
    "truncate table",
)

#: The L1 write call. Matched on the method name alone rather than on
#: ``worker.ingest`` specifically — a strict superset, chosen because the
#: receiver may be spelled ``handle.worker``, ``fabric.handle.worker`` or a
#: local, and a client module has no legitimate reason to call anything
#: ``ingest``.
INGEST_METHOD = "ingest"

#: Store-name minting. ``uuid4`` in a client module is a name being invented,
#: and a name being invented is a store about to be created.
NAME_MINTING = "uuid4"


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """Every string literal that is a docstring, by identity.

    Excluded from the DDL scan: a docstring cannot be executed as SQL, and this
    module's own subject documents at length what it does *not* do. Scanning
    prose for verbs it is explaining would make the gate unusable, and an
    unusable gate gets deleted.
    """
    found: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", [])
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            found.add(id(body[0].value))
    return found


def scan_for_provisioning(root: Path) -> list[str]:
    """Every provisioning construct under ``root``, as ``path:lineno:construct``.

    Args:
        root: The source tree to scan. A **parameter**, so a control can hand
            this function a divergent subject and watch the shipped check fire
            on it.

    Returns:
        The offending triples, sorted. Empty means the tree provisions nothing.

    Raises:
        AssertionError: ``root`` does not exist or holds no Python modules. A
            scan that returns ``[]`` because it scanned nothing is
            indistinguishable from a clean tree, and the second is the answer
            this function exists to give — so the first is loud. This is the
            failure mode that has bitten this project three times: a check that
            stops checking without going red.
    """
    assert root.is_dir(), f"provisioning-scan root does not exist: {root}"
    modules = sorted(root.rglob("*.py"))
    assert modules, f"provisioning-scan root holds no Python modules: {root}"

    findings: list[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_nodes(tree)
        where = path.relative_to(root.parent.parent) if root.parents else path
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    package = alias.name.split(".")[0]
                    if package in CONTAINER_PACKAGES:
                        findings.append(
                            f"{where}:{node.lineno}:container-import:{package}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                package = node.module.split(".")[0]
                if package in CONTAINER_PACKAGES:
                    findings.append(
                        f"{where}:{node.lineno}:container-import:{package}"
                    )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings:
                    continue
                lowered = node.value.lower()
                for phrase in DDL_PHRASES:
                    if phrase in lowered:
                        findings.append(
                            f"{where}:{node.lineno}:ddl-literal:{phrase}"
                        )
            elif isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else func.id
                    if isinstance(func, ast.Name)
                    else ""
                )
                if name == INGEST_METHOD:
                    findings.append(f"{where}:{node.lineno}:ingest-call:{name}")
                elif name == NAME_MINTING:
                    findings.append(
                        f"{where}:{node.lineno}:store-name-minting:{name}"
                    )
    return sorted(findings)


# ---------------------------------------------------------------------------
# The shipped assertion.
# ---------------------------------------------------------------------------


def test_the_client_tree_provisions_nothing() -> None:
    """`D-16`. Nothing in ``src/ccf/client/`` starts, creates, mints or ingests.

    The adapter **boots**, and booting is not provisioning: it reads the
    Control Plane documents a deployment already authored and opens a reader
    over a graph that already holds rows.
    :func:`~ccf.deployment.manifest.load_and_boot`'s own docstring draws the
    same line in the negative, and this test is that line made checkable from
    the consuming side.
    """
    findings = scan_for_provisioning(CLIENT_ROOT)

    assert findings == [], (
        "a client module provisions rather than asks — a client call must never"
        " be a producer-side act (D-16):\n" + "\n".join(findings)
    )


def test_the_client_tree_is_actually_scanned() -> None:
    """The precondition: the scan reads real modules, and enough of them.

    Without this, a moved or renamed client package would make the assertion
    above pass over nothing. :func:`scan_for_provisioning` raises on an absent
    or empty root, and this asserts the population it *did* read is the one a
    reader expects.
    """
    modules = sorted(CLIENT_ROOT.rglob("*.py"))

    assert len(modules) >= 8, f"only {len(modules)} client modules found"
    assert (CLIENT_ROOT / "adapters" / "inprocess.py") in modules, (
        "the in-process adapter — the one module that could plausibly"
        " provision — is not in the scanned set"
    )


# ---------------------------------------------------------------------------
# The controls. Four constructs, four controls, each through the SAME function.
# ---------------------------------------------------------------------------


def _planted(tmp_path: Path, body: str) -> Path:
    """A copy of the real adapter plus one forbidden construct.

    A **copy of the real subject** rather than a minimal stub, so the control
    proves the construct is what the scan reacts to — not that a two-line file
    happens to trip it.
    """
    root = tmp_path / "client"
    root.mkdir(parents=True, exist_ok=True)
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "inprocess.py").write_text(
        (CLIENT_ROOT / "adapters" / "inprocess.py").read_text(encoding="utf-8")
        + "\n\n"
        + body,
        encoding="utf-8",
    )
    return root


def test_control_a_container_import_is_reported(tmp_path: Path) -> None:
    """Control 1 — starting infrastructure inside a client call."""
    root = _planted(
        tmp_path,
        "from testcontainers.community.postgres import PostgresContainer\n",
    )

    findings = scan_for_provisioning(root)

    assert any("container-import:testcontainers" in f for f in findings), findings


def test_control_a_ddl_literal_is_reported(tmp_path: Path) -> None:
    """Control 2 — minting a schema inside a client call."""
    root = _planted(tmp_path, 'SCHEMA = "CREATE TABLE widgets (id int)"\n')

    findings = scan_for_provisioning(root)

    assert any("ddl-literal:create table" in f for f in findings), findings


def test_control_store_name_minting_is_reported(tmp_path: Path) -> None:
    """Control 3 — inventing a store name, as the rejected example did."""
    root = _planted(
        tmp_path,
        "from uuid import uuid4\n\n\ndef store_name():\n"
        '    return f"ccf_{uuid4().hex}"\n',
    )

    findings = scan_for_provisioning(root)

    assert any("store-name-minting:uuid4" in f for f in findings), findings


def test_control_an_ingest_call_is_reported(tmp_path: Path) -> None:
    """Control 4 — the L1 write path, which a client must never reach."""
    root = _planted(
        tmp_path,
        "def push(booted, envelope):\n"
        "    return booted.handle.worker.ingest(envelope)\n",
    )

    findings = scan_for_provisioning(root)

    assert any("ingest-call:ingest" in f for f in findings), findings


def test_control_the_scan_refuses_an_empty_or_absent_root(tmp_path: Path) -> None:
    """Control 5 — the case the other four cannot cover.

    The other controls prove the scan reports a construct that is there. This
    proves it does not report *clean* when it read nothing at all. A gate that
    fails open when its subject moves is the defect class this project has hit
    three times, and every one of them was a walk that skipped rather than
    raised.
    """
    with pytest.raises(AssertionError, match="does not exist"):
        scan_for_provisioning(tmp_path / "absent")

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(AssertionError, match="no Python modules"):
        scan_for_provisioning(empty)


# ---------------------------------------------------------------------------
# The positive half — D-16 is about behaviour, not only about source shape.
# ---------------------------------------------------------------------------


def test_a_second_ask_performs_zero_additional_boots(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The behavioural half, and research asked for it by name.

    A source scan proves the client cannot provision. It says nothing about
    whether the client re-boots, and an un-cached second ``ask()`` raises
    ``SingleWriterViolation`` only in a real deployment — which is the worst
    possible place to find out. Counted, never timed.
    """
    boots = 0
    real = inprocess.load_config_and_boot

    def counted(*args: object, **kwargs: object) -> object:
        nonlocal boots
        boots += 1
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(inprocess, "load_config_and_boot", counted)

    client = ProductClient.for_product(
        "fixture.widgets-over-score", binding=f"inprocess:{seeded_root}"
    )
    client.ask(parameters={"minimum_score": 20})
    after_first = boots
    client.ask(parameters={"minimum_score": 20})

    assert after_first == 1, "the first ask did not boot exactly once"
    assert boots == 1, "the second ask re-booted the deployment"


def test_the_write_path_is_reachable_and_the_client_never_takes_it(
    seeded_root: Path,
) -> None:
    """The honest shape of the single-writer claim across this seam.

    **It would be wrong to assert that no writer is reachable.** The adapter
    boots a real fabric, and ``booted.fabric.handle.worker`` is exactly the L2
    writer the conftest seeds through — so a test asserting "no writer exists"
    would be asserting something false about the object and would pass only by
    checking an attribute name nobody uses.

    The real guarantee is narrower and stronger: the write path is *right
    there*, and no client module calls it. That is a claim about the source,
    which is why :func:`scan_for_provisioning`'s ingest check is the assertion
    and this test's job is to prove that check is **not vacuous** — the thing it
    forbids is genuinely within reach.
    """
    client = ProductClient.for_product(
        "fixture.widgets-over-score", binding=f"inprocess:{seeded_root}"
    )
    client.ask(parameters={"minimum_score": 20})
    booted = inprocess._BOOT_CACHE[seeded_root.resolve()]

    assert hasattr(booted.fabric.handle, "worker"), (
        "the booted handle carries no worker, so the ingest construct the scan"
        " forbids is not actually reachable and that check proves nothing"
    )
    assert hasattr(booted.fabric.handle.worker, INGEST_METHOD)

    assert not [
        finding
        for finding in scan_for_provisioning(CLIENT_ROOT)
        if "ingest-call" in finding
    ], "a client module calls the write path that is sitting right there"


def test_the_scheme_registry_holds_one_transport() -> None:
    """A sanity anchor: this suite is testing the transport it thinks it is."""
    assert SCHEME_REGISTRY["inprocess"] is inprocess.InProcessAdapter
