"""What `examples/external/00-hello-context/serve.py` assembled, and what an
external consumer actually received (plan 15-20).

`make example-ext-00` proves the spine runs; `pytest` proves it is correct
(D-09). This module is where the correctness now lives.

Precedent
---------

The loader below follows ``tests/examples/test_ext00_hardening.py``, which is
the module in this family: the example directory is not a package, so each
example module is loaded by file path with ``importlib.util``. That module in
turn names ``test_ext00_fixture_schemas.py`` as its own precedent, so the chain
is stated end to end rather than rediscovered. One thing is added here that
``test_ext00_hardening.py`` does not need: the module is registered in
``sys.modules`` *before* ``exec_module``. ``serve.py`` uses
``from __future__ import annotations``, so ``NamedTuple`` and ``@dataclass``
field annotations resolve through ``sys.modules[cls.__module__]`` and fail with
an opaque ``AttributeError`` otherwise (plan 15-13, deviation 2).

**These tests spawn no fixture harness and touch no vendor API.** The three
that need a live front door share one module-scoped server, spawned through
``run.py``'s own ``_spawn``/``_terminate``, so the READY handshake and the
kill-fallback teardown under test are the harness's real ones.

What moved here, and from where
-------------------------------

| Pre-rewrite location | What it asserted | Where it is now |
| --- | --- | --- |
| ``serve.py:538-560`` | the assembled payload matches ``product.yaml``'s ``expected:`` block, checked fabric-side before READY | ``test_the_assembled_product_matches_the_declared_expectation`` and its two siblings, reading the same values from ``expected.yaml`` |

What deliberately did **not** move
----------------------------------

* ``serve.py``'s gate narrowing. ``ServableProduct`` is not constructible
  outside ``run_gates``, so holding one IS the evidence the gates ran
  (INV-CH7-52) and a refusal must not be proceeded past *in the deployment*,
  not merely noticed in a test. It is now a ``match``/``case`` that raises,
  which is stricter than the old ``isinstance`` check because it does not
  vanish under ``python -O``.
* ``serve.py``'s single ``print`` — the ``READY <port>`` line. That is process
  protocol between parent and child, not narration; the parent's blocking
  ``readline()`` is the readiness gate.
* ``run.py``'s ten ``print`` calls (22 lines). Eight of them are the ``PASS
  N:`` lines, and ``test_ext00_hardening.py::
  test_the_d15_fallback_works_with_every_client_leg_deselected`` asserts every
  one of ``PASS 1:`` through ``PASS 8:`` appears in a real ``run.py``
  invocation. That module is out of scope for this plan and unmodified, so the
  narration stays where an unmodifiable test pins it. The *claims* behind it
  are asserted here as well, which is what makes ``tests/`` own the
  correctness even though the console output did not move.

Which category each assertion is in (plan 15-13, R7)
-----------------------------------------------------

Stated per test rather than implied, because the phase's running finding is
"a check that passes for a reason unrelated to what it claims to verify" and
three different shapes of assertion live in this file:

* **Independent expectation** — the expected value is authored in a document
  nothing in ``serve.py`` reads, so either side changing alone fails.
  ``expected.yaml`` is the whole of this category.
* **Propagation check** — both ends resolve from the same artifact, so an
  artifact edit moves both. It fails when the *wiring* is wrong, which is a
  real and different property; it is not a statement about whether the fabric
  computed the right answer.
* **SDK mechanism claim** — asserted directly against the SDK's own contract,
  and fails when the SDK changes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tempfile
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.products.gates import ServableProduct

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"


def _load_module(name: str, path: pathlib.Path) -> Any:
    """Load an example module by file path (the example dir is no package).

    ``sys.modules`` is populated before ``exec_module`` because ``serve.py``
    defers its annotations; see the module docstring.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def serve_module() -> Any:
    return _load_module("ext00_serve_output", EXAMPLE_DIR / "serve.py")


@pytest.fixture(scope="module")
def run_module() -> Any:
    return _load_module("ext00_run_output", EXAMPLE_DIR / "run.py")


@pytest.fixture(scope="module")
def assembled(serve_module: Any) -> Any:
    """One in-process assembly of the finserv slice, gated and recorded.

    Every instant this deployment uses is declared in ``decision.yaml``, so a
    second assembly reproduces the first byte for byte. That is what lets the
    client-leg tests below compare what crossed the wire against a value this
    process computed for itself rather than against a value the server handed
    it.
    """
    with tempfile.TemporaryDirectory(prefix="ccf-ext00-test-") as scratch:
        return serve_module.build_credit_context(
            database_path=pathlib.Path(scratch) / "fabric.sqlite3"
        )


def _declaration(assembled: Any, key: str) -> Any:
    artifact = assembled.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact)
    return artifact.declaration


# --------------------------------------------------------------------------
# serve.py's relocated self-check — independent expectations
#
# `expected.yaml` is read by NOTHING in `serve.py`. The events, the resolution
# rules and the operator parameters produce the payload; this document states
# separately what the deployment believes that produces. Either side changing
# alone fails these three.
# --------------------------------------------------------------------------


def test_the_assembled_product_matches_the_declared_entity_count(
    assembled: Any,
) -> None:
    """Relocated from ``serve.py:544`` (independent expectation)."""
    expected = _declaration(assembled, "expected")
    assert (
        assembled.servable.product.payload["entity_count"]
        == expected["entity_count"]
    )


def test_the_assembled_product_matches_the_declared_entity_classes(
    assembled: Any,
) -> None:
    """Relocated from ``serve.py:546-550`` (independent expectation).

    The RESTRICTED watchlist signal is substituted out by the policy operator
    and the stale rating narrative is ranked out by similarity, so a payload
    carrying either would fail here — which is what makes "the operators did
    something" distinguishable from "the operators are identity functions".
    """
    expected = _declaration(assembled, "expected")
    classes = sorted(
        {
            entry["entity_class"]
            for entry in assembled.servable.product.payload["entities"]
        }
    )
    assert classes == sorted(expected["entity_classes"])


def test_the_assembled_product_matches_the_declared_relationship_types(
    assembled: Any,
) -> None:
    """Relocated from ``serve.py:551-555`` (independent expectation).

    The edge to the restricted signal is substituted out with the signal, so
    its absence is not a leak by omission.
    """
    expected = _declaration(assembled, "expected")
    assert assembled.servable.product.payload["relationship_types"] == sorted(
        expected["relationship_types"]
    )


# --------------------------------------------------------------------------
# The gate and the replay record — SDK mechanism claims
# --------------------------------------------------------------------------


def test_only_a_gate_admitted_product_is_ever_returned(assembled: Any) -> None:
    """SDK mechanism claim: ``ServableProduct`` is not constructible outside
    ``run_gates`` (INV-CH7-52), so holding one is the evidence the three
    validation gates ran on what the front door serves."""
    assert isinstance(assembled.servable, ServableProduct)


def test_the_replay_record_names_the_decision_it_recorded(
    assembled: Any,
) -> None:
    """Propagation check on dimensions 1, 2, 4 and 5, plus one SDK claim.

    Both ends of the first four resolve from the same artifacts, so this fails
    when the WIRING is wrong — a perspective built from the wrong document, a
    binding assembled by a rule nobody wrote down — not when a value is
    re-authored. ``model_version`` is the SDK claim: this deployment is
    keyless and model-free, so dimension 3 must say so.
    """
    record = assembled.record
    perspective = assembled.artifacts["perspective"]
    decision = _declaration(assembled, "decision")
    governance = _declaration(assembled, "product-governance")

    assert record.tenant_id == assembled.address.tenant
    # `decision.yaml`'s instants arrive as TEXT: the artifact loader suppresses
    # PyYAML's timestamp resolver (D-02) so the zone is parsed by the field's
    # own annotation rather than guessed. Compare the parsed values, not their
    # spellings.
    assert record.context_fabric_snapshot.temporal_boundary == datetime.fromisoformat(
        decision["temporal_boundary"]
    )
    assert record.perspective_conditioning.role == perspective.role
    assert record.perspective_conditioning.principal_id == (
        perspective.principal_id
    )
    assert record.content_generation_path.plan_id == governance["plan_id"]
    assert record.model_version.model_version == "none"


def test_the_lineage_declares_exactly_the_operators_the_class_requires(
    assembled: Any,
) -> None:
    """A TRANSCRIPTION check since Phase 15.1 — say what it is rather than
    imply independence it does not have.

    Under design E2 (``docs/DECISIONS.md`` D-IMPL-86 and its correction of
    2026-08-05) the product's ``lineage.operators_invoked`` is filled from
    ``product-class.yaml``'s ``required_operator_keys`` — the Control Plane
    CLAIM — and never from ``execution``. So both sides of this assertion now
    trace to that one artifact, and what it verifies is that ``serve.py``
    carried the claim into the Contract without altering it. That is narrow, and
    it is deliberately not dressed up as more.

    **Where the independence actually lives, and it is not here.** The plan's
    operator set comes from a SECOND authored document,
    ``projection-requirements.yaml``, and ``refuse_operator_set_divergence``
    holds the two to each other between plan construction and
    ``ProjectionEngine.execute``. The ``assembled`` fixture existing at all is
    the evidence that binder admitted — edit either artifact alone and
    ``serve.py`` refuses to compose, so this module never reaches its
    assertions. Downstream, Gate 2 compares the transcribed claim against the
    engine's report of executing the plan, which is ASSEMBLY-PATH INTEGRITY: the
    engine is a faithful transcriber of the plan rather than an independent
    witness of it.

    The residual is unchanged in kind: a deployment that transcribed one of the
    two artifacts out of the other would collapse the binder, and neither this
    assertion nor Gate 2 would see it.
    """
    declared = assembled.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert sorted(assembled.servable.product.lineage.operators_invoked) == (
        sorted(declared.required_operator_keys)
    )


def test_the_served_product_is_the_class_the_deployment_declared(
    assembled: Any,
) -> None:
    """Propagation check on the product class's identity and its TTL lane."""
    declared = assembled.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    product = assembled.servable.product
    assert product.schema_name == declared.schema_name
    assert product.schema_version == declared.schema_version
    assert product.ttl_anchor == declared.ttl_anchor
    assert assembled.address.product_class == declared.schema_name
    assert assembled.address.version == declared.schema_version


# --------------------------------------------------------------------------
# What an external consumer actually received
#
# The claim the three client legs exist to demonstrate is that an agent with
# ZERO CCF imports consumes the typed product, its lineage, and its
# five-dimension replay record over the authenticated MCP surface. Before this
# module that claim was only ever *observed* — `run.py` checked that the
# strings `operators_invoked` and `content_generation_path` appeared somewhere
# in the leg's output, which a server returning a differently-shaped or
# truncated document would also satisfy.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bare_leg_output(run_module: Any, assembled: Any) -> Iterator[dict[str, str]]:
    """Run ``client_bare.py`` once against a live ``serve.py``.

    The server is spawned through ``run.py``'s own ``_spawn``, so the READY
    handshake and the bounded wait under test are the harness's real ones, and
    torn down through its ``_terminate`` kill fallback. One spawn for the whole
    module; the leg is deterministic and needs no vendor key or replay server.
    """
    tokens = _declaration(assembled, "tokens")["tokens"]
    active = next(entry for entry in tokens if entry["status"] == "active")
    focus = _declaration(assembled, "focus")

    with tempfile.TemporaryDirectory(prefix="ccf-ext00-leg-") as scratch:
        proc, port = run_module._spawn("serve.py", pathlib.Path(scratch))
        try:
            stdout = run_module._run_leg(
                "client_bare.py",
                {
                    **os.environ,
                    "CCF_MCP_URL": f"http://127.0.0.1:{port}/mcp",
                    "CCF_TOKEN": active["token"],
                    "CCF_EXAMPLE_TENANT": assembled.address.tenant,
                    "CCF_EXAMPLE_ENTITY": focus["entity_ref"],
                },
            )
        finally:
            run_module._terminate(proc)

    # `[<label>] <body>` per line, which is the leg's whole output contract.
    received: dict[str, str] = {}
    for line in stdout.splitlines():
        if line.startswith("[") and "] " in line:
            label, _, body = line[1:].partition("] ")
            received[label] = body
    yield received


def test_the_client_leg_read_the_product_the_deployment_declared(
    bare_leg_output: dict[str, str], assembled: Any
) -> None:
    """**Independent expectation, end to end.**

    This is the one assertion in the client-leg group whose expected value is
    authored in a document no part of the serving path reads. It closes the
    whole loop — ``expected.yaml`` -> L1 -> L6 -> the authenticated MCP
    surface -> an agent holding a URL and a bearer token — and it fails if any
    stage of that loop stops producing what the deployment declared.
    """
    expected = _declaration(assembled, "expected")
    payload = json.loads(bare_leg_output["get_context"])["payload"]
    assert payload["entity_count"] == expected["entity_count"]
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == (
        sorted(expected["entity_classes"])
    )
    assert payload["relationship_types"] == sorted(
        expected["relationship_types"]
    )


def test_the_served_lineage_reaches_the_client_leg_unchanged(
    bare_leg_output: dict[str, str], assembled: Any
) -> None:
    """Wire-fidelity check: byte equality against an independently recomputed
    fabric-side value.

    Honest about what it is. Both ends resolve from the same artifacts, so an
    artifact edit moves both and this cannot catch one. What it catches is a
    *transport* fault — the surface re-serializing, reordering, truncating, or
    serving a lineage block belonging to a different product than the one it
    assembled. The two values are computed in two different processes: the
    right-hand side is this test process assembling the slice for itself, the
    left-hand side crossed a socket.
    """
    assert bare_leg_output["get_lineage"].encode("utf-8") == canonical_bytes(
        assembled.servable.product.lineage
    )


def test_the_served_replay_record_reaches_the_client_leg_unchanged(
    bare_leg_output: dict[str, str], assembled: Any
) -> None:
    """Wire-fidelity check on the five-dimension record (whitepaper §7.10).

    Same shape as the lineage test above, and the same honest scope. The
    record the leg reads back is the one the ArtifactStore holds at the exact
    content address of the delivery that was recorded BEFORE the bytes left,
    so a surface that served a stale or foreign record fails here.
    """
    assert bare_leg_output["get_replay_record"].encode(
        "utf-8"
    ) == canonical_bytes(assembled.record)


def test_the_client_leg_received_all_five_replay_dimensions(
    bare_leg_output: dict[str, str],
) -> None:
    """SDK mechanism claim: dimension count, named rather than grepped.

    ``run.py`` PASS 5 checks that the substring ``content_generation_path``
    appears somewhere in the leg's output. That passes for a document carrying
    one dimension and four empty keys. Here the parsed document must carry all
    five.
    """
    record = json.loads(bare_leg_output["get_replay_record"])
    assert set(record) >= {
        "context_fabric_snapshot",
        "policy_bindings",
        "model_version",
        "perspective_conditioning",
        "content_generation_path",
    }


# --------------------------------------------------------------------------
# The example's core claim (EXAM-04), asserted where a runner can fail a build
# --------------------------------------------------------------------------


def test_the_committed_client_legs_import_no_ccf(run_module: Any) -> None:
    """The charter, over the shipped files (mirrors ``run.py`` PASS 3)."""
    run_module._assert_zero_ccf_imports()


@pytest.mark.parametrize(
    "injected", ["from ccf.boot import boot\n", "import ccf_runtime\n"]
)
def test_the_zero_import_assertion_fails_when_a_leg_imports_ccf(
    run_module: Any,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    injected: str,
) -> None:
    """The assertion is verified to REFUSE, not merely to pass.

    A grep that matched nothing would be green forever, and this example's
    whole point rests on it. The legs are copied to ``tmp_path``, one is given
    a CCF import, and ``_EXAMPLE_ROOT`` is pointed at the copies — so the real
    function, its real glob and its real regex are exercised. Both import
    forms are probed because the pattern must catch ``from ccf ...`` and
    ``import ccf_runtime`` alike.
    """
    for leg in sorted(EXAMPLE_DIR.glob("client_*.py")):
        shutil.copy(leg, tmp_path / leg.name)
    monkeypatch.setattr(run_module, "_EXAMPLE_ROOT", tmp_path)

    # The copies alone still pass — so the failure below is the injection.
    run_module._assert_zero_ccf_imports()

    target = tmp_path / "client_bare.py"
    target.write_text(injected + target.read_text(encoding="utf-8"), "utf-8")
    with pytest.raises(AssertionError) as excinfo:
        run_module._assert_zero_ccf_imports()
    assert "client_bare.py" in str(excinfo.value)


def test_the_readme_keeps_its_seven_template_headings(run_module: Any) -> None:
    """D-17/D-08, mirrors ``run.py`` PASS 4 (propagation check on the
    template): the seven Phase-13 heading names, by name and in order."""
    run_module._assert_seven_heading_readme()
