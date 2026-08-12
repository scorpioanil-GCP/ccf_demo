"""Measurement instrument for the Phase 15.6 ruling package (plan 15.6-01).

**This module measures costs. It does not test correctness.** Every figure it
produces exists to fill a MEASURED COST cell in
``docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md`` so that Dave rules on numbers
rather than on projections. ``15.6-RESEARCH.md`` § B2 carries a recommendation
explicitly labelled *"spike to confirm"*, and three of its assumptions — A1 (the
free reconstruction ride for anything nested inside ``DebtAssessment``), A5 (the
home of the obligation binding) and A7 (that the three example artifacts break
only under a *required* field) — were reasoned rather than executed. This module
executes what is executable and names what is not.

The rule this module obeys
--------------------------
**Assert only facts that no plan in this phase is scoped to change; report
everything else.**

``pyproject.toml`` sets ``testpaths = ["tests"]``, so ``tests/spikes/`` runs
under ``make ci-core``, which has to stay green from wave 1 onward. Plans
``15.6-05``, ``15.6-06``, ``15.6-07`` and ``15.6-08`` each move the very
``Observation``, ``DebtAssessment`` and ``DebtProfile`` shapes this module
measures, and plans ``15.6-10`` and ``15.6-11`` move the manifest and citation
counts. A module asserting any of those would go red on *correct* work by a
later plan in its own phase, and the only available repair would be to edit the
evidence. Editing the evidence to keep a gate green is the opposite of evidence.

So the separation is load-bearing, not stylistic:

* **Reported** (via :func:`measure_all`, never compared in an assertion):
  every tree-derived count, the Q-C required-versus-optional split, the Q-D
  fields-in-hand comparison, the Q-E regeneration census, the three Q-B2
  entitlement findings, and the outcome of the real rehydration tripwire.
* **Asserted**: only properties of the content-addressing function applied to
  stand-in models this module itself owns, and the three-door enumeration in
  ``runtime/``, which no plan in this phase touches.

The one exception on the reported side is an instrument check: the AST walk
asserts that it *found* each symbol at all. A walk returning zero for
``DebtAssessment`` means the walker is broken, which is a fact about the
instrument rather than about the tree, and it stays true however many call sites
later plans add or remove.

This module recommends nothing. It costs the options Dave already has in front
of him and adds nothing new to decide.

Reading the figures
-------------------
``pytest tests/spikes/test_debt_evidence_placement_cost.py -s`` prints the whole
figure set as JSON. Set ``CCF_SPIKE_REPORT=/path/to/figures.json`` to also write
it to a file. Neither writes anything into the tree.

Retiring owner
--------------
**Plan ``15.6-12``, task 1.** This is a measurement instrument with a
phase-length life. ``15.6-12``'s phase-close sweep either retires it or
re-points it at the post-ruling tree, and accounts for the choice in the gate
package. No other plan owns it.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.contracts.claims import EntityClaim, LineageEntry
from ccf.halflife.assessment import (
    NO_SCORER_PINS,
    DebtAssessment,
    DebtFactors,
    DebtSignal,
)
from ccf.halflife.decay import Observation
from ccf.operators.categories import PolicyFilter
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.projection.engine import ProjectionEngine
from ccf.projection.plan import ProjectionOutput
from ccf.replay.record import ContentGenerationPath
from ccf.replay.serve import ServedProduct

# --------------------------------------------------------------------------
# Tree location
# --------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The trees walked for call sites. ``perf/`` and ``tools/`` are included
#: because ``15.6-RESEARCH.md`` § B1 names both as couplings a ``src/``-only
#: sweep misses.
SEARCH_ROOTS: tuple[str, ...] = (
    "src",
    "runtime",
    "tests",
    "perf",
    "examples",
    "tools",
)

#: The trees swept for 64-hex content-address literals. Wider than
#: :data:`SEARCH_ROOTS` because a pin can live in a document as easily as in a
#: module, and the Q-E question is *what regenerates*, not *what imports*.
ADDRESS_SWEEP_ROOTS: tuple[str, ...] = (
    "src",
    "runtime",
    "tests",
    "examples",
    "tools",
    "perf",
    "docs",
    "public",
)

#: Never walked: virtualenvs, bytecode caches, and this instrument's own
#: package — an instrument that counted itself would report its own stand-ins
#: as tree cost.
EXCLUDED_PARTS: frozenset[str] = frozenset(
    {".venv", "venv", "__pycache__", ".git", "node_modules", "spikes"}
)

#: The symbols whose blast radius the Track B questions are priced against.
MEASURED_SYMBOLS: tuple[str, ...] = (
    "DebtAssessment",
    "DebtFactors",
    "Observation",
    "ContextProductContract",
    "ContentGenerationPath",
)

#: The governed in-process delivery seam. Bare-name calls only: a plain
#: ``serve(...)`` is the seam, while ``server.serve(...)`` is an unrelated
#: method of the same name, and a figure merging the two would overstate the
#: population a record-only carrier reaches.
SERVE_CALL_SYMBOL = "serve"

REHYDRATION_TRIPWIRE = pathlib.Path("tests/replay/test_engine_rehydration.py")

#: Set to anything other than ``"1"`` to skip the tripwire run; the figure is
#: then reported as not taken, with the reason. Never estimated.
TRIPWIRE_ENV = "CCF_SPIKE_RUN_TRIPWIRE"

#: Where :func:`measure_all` writes its JSON, if set.
REPORT_ENV = "CCF_SPIKE_REPORT"

#: The three shipped delivery doors, in the enumeration
#: ``tests/invariants/test_mcp_role_separation.py`` holds as exhaustive.
DELIVERY_DOORS: tuple[tuple[str, str], ...] = (
    ("runtime/ccf_runtime/mcp/egress.py", "build_egress_server"),
    ("runtime/ccf_runtime/http_api/routes/product.py", "build_router"),
    ("runtime/ccf_runtime/mcp/experience.py", "build_experience_server"),
)

#: The three example artifacts an ``Observation.model_validate`` reads.
OBSERVATION_ARTIFACTS: tuple[str, ...] = (
    "examples/00-quickstart/artifacts/decision.yaml",
    "examples/01-agent-basics/artifacts/debt-evaluation.yaml",
    "examples/08-e2e-demo/artifacts/decision.yaml",
)

_HEX64 = re.compile(r"\b[0-9a-f]{64}\b")

#: The **truncated** address form, which a 64-hex sweep does not see. Added
#: because the sweep found zero full-length literals in the one file
#: ``15.6-RESEARCH.md`` § B1 names as moving, and the reason turned out to be
#: that the file prints its addresses elided. A census blind to the elided form
#: would have reported a smaller regeneration surface than the tree has.
_HEX_TRUNCATED = re.compile(r"\b[0-9a-f]{12,63}\.\.\.")

#: Files a 64-hex sweep reaches whose literals are not product content
#: addresses, or are product addresses that do not move when
#: ``DebtAssessment`` reshapes. Keyed by repo-relative path prefix; the value
#: is the observed reason. Reported, never asserted — every classification
#: here is a reading of a file some later plan may edit.
_ADDRESS_CLASSIFICATION: tuple[tuple[str, str, str], ...] = (
    (
        "tests/replay/test_harness_trace.py",
        "does not move",
        "self-normalizing: the module substitutes a freshly computed "
        "content_hash for the captured literal before comparing",
    ),
    (
        "tests/replay/test_engine_rehydration.py",
        "does not move",
        "computed, not pinned: the comparison is against a live "
        "content_hash(outcome.product) rather than against a literal",
    ),
    (
        "examples/external/00-hello-context/.store/",
        "does not move",
        "gitignored store index; regenerates on every run",
    ),
    (
        "examples/external/00-hello-context/fixtures/",
        "does not move",
        "recorded LLM request bodies; the replay server fingerprints model, "
        "sorted tool names and message count, never message content",
    ),
    (
        "examples/08-e2e-demo/artifacts/scenario.yaml",
        "does not move",
        "source fingerprints and a ring signature, not product addresses",
    ),
    (
        "examples/08-e2e-demo/artifacts/expected_output.txt",
        "MOVES",
        "two recorded addresses, printed by the example ELIDED to a 16-hex "
        "prefix and compared against this file: the replay-record address and "
        "the skill-set-in-force hash. The replay record carries "
        "ContentGenerationPath, which carries debt, so a DebtAssessment "
        "reshape moves the record address as well as the product address. A "
        "64-hex sweep finds nothing here, which is why the truncated census "
        "exists",
    ),
    (
        "docs/CONTEXT_PRODUCT_RULING_EVIDENCE.md",
        "does not move",
        "the 15.5-01 evidence document: observed addresses recorded as a "
        "historical measurement of a stand-in, not a live pin anything "
        "compares against",
    ),
    (
        "docs/DECISIONS.md",
        "does not move",
        "append-only ruling record; the literals are quoted measurements from "
        "the sessions that made the rulings, never re-derived",
    ),
    (
        "docs/PHASE_I4_GATE.md",
        "does not move",
        "a transcript of a past failing test run, quoted in the gate package",
    ),
    (
        "docs/SURFACE-AUDIT.md",
        "does not move",
        "a sha256 of the committed surface baseline file, quoted as a "
        "historical record",
    ),
    (
        "tools/lints/tests/test_no_hardcoding.py",
        "does not move",
        "a CINV-01 allowlist fingerprint over literal text; no product is "
        "involved",
    ),
    (
        "tests/peering/test_admission_record.py",
        "does not move",
        "a sha256 of the claims.py file text; moves only if claims.py is "
        "edited, which no Track B gap requires",
    ),
    (
        "tests/authz/test_authz_audit.py",
        "does not move",
        "canonical bytes of an AuditEvent, which carries no product",
    ),
    (
        "tests/test_surface_completeness.py",
        "does not move",
        "a digest of the frozen v0.2 surface baseline file, frozen by design",
    ),
    (
        "tests/perf_synth/",
        "does not move",
        "synthetic dataset hashes, unrelated to any product",
    ),
    (
        "tools/lints/allowlist.yaml",
        "does not move",
        "CINV-01 finding fingerprints over literal text",
    ),
)


# --------------------------------------------------------------------------
# The AST walk
# --------------------------------------------------------------------------


def _python_files() -> Iterator[pathlib.Path]:
    """Yield every ``.py`` file under :data:`SEARCH_ROOTS`, exclusions applied."""
    for root_name in SEARCH_ROOTS:
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if EXCLUDED_PARTS & set(path.parts):
                continue
            yield path


@lru_cache(maxsize=1)
def _parsed_tree() -> tuple[tuple[pathlib.Path, ast.Module], ...]:
    """Parse every walked file once; an unparseable file is skipped, not raised."""
    parsed: list[tuple[pathlib.Path, ast.Module]] = []
    for path in _python_files():
        try:
            parsed.append((path, ast.parse(path.read_text(encoding="utf-8"))))
        except (SyntaxError, UnicodeDecodeError):
            continue
    return tuple(parsed)


def _called_name(node: ast.Call) -> tuple[str, str] | None:
    """Return ``(kind, name)`` for a call's callee, if it resolves to a name.

    ``kind`` separates a bare ``Symbol(...)`` from a ``receiver.symbol(...)``.
    """
    func = node.func
    if isinstance(func, ast.Name):
        return ("name", func.id)
    if isinstance(func, ast.Attribute):
        return ("attribute", func.attr)
    return None


@lru_cache(maxsize=None)
def count_call_sites(symbol: str, kind: str = "any") -> dict[str, Any]:
    """Count direct calls of ``symbol`` by AST walk.

    A **call-site** count, not a ``grep -rl`` file-membership estimate: a module
    constructing the same type nine times is nine repair sites, not one.
    """
    per_file: dict[str, int] = {}
    per_tree: dict[str, int] = {}
    total = 0
    for path, tree in _parsed_tree():
        resolved = [
            _called_name(node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ]
        matches = [
            pair
            for pair in resolved
            if pair is not None
            and pair[1] == symbol
            and (kind == "any" or pair[0] == kind)
        ]
        if not matches:
            continue
        relative = path.relative_to(REPO_ROOT)
        per_file[str(relative)] = len(matches)
        per_tree[relative.parts[0]] = per_tree.get(relative.parts[0], 0) + len(
            matches
        )
        total += len(matches)
    return {
        "symbol": symbol,
        "kind": kind,
        "call_sites": total,
        "distinct_files": len(per_file),
        "by_tree": dict(sorted(per_tree.items())),
        "by_file": dict(sorted(per_file.items())),
    }


@lru_cache(maxsize=None)
def count_receiver_calls(receiver: str, attribute: str) -> dict[str, Any]:
    """Count ``receiver.attribute(...)`` calls by AST walk.

    Separate from :func:`count_call_sites` because ``Observation.model_validate``
    is a *different* repair site from ``Observation(...)``: the first reads a
    document, the second is written in code, and a required field costs them
    differently.
    """
    per_file: dict[str, int] = {}
    per_tree: dict[str, int] = {}
    total = 0
    for path, tree in _parsed_tree():
        hits = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == attribute
                and isinstance(func.value, ast.Name)
                and func.value.id == receiver
            ):
                hits += 1
        if not hits:
            continue
        relative = path.relative_to(REPO_ROOT)
        per_file[str(relative)] = hits
        per_tree[relative.parts[0]] = per_tree.get(relative.parts[0], 0) + hits
        total += hits
    return {
        "expression": f"{receiver}.{attribute}",
        "call_sites": total,
        "distinct_files": len(per_file),
        "by_tree": dict(sorted(per_tree.items())),
        "by_file": dict(sorted(per_file.items())),
    }


# --------------------------------------------------------------------------
# Q-A — the four candidate placements. ASSERTED.
# --------------------------------------------------------------------------
#
# Every stand-in below is owned by this module. `src/` is never modified: the
# measurement is about what *would* happen to the content address and to the
# rehydrator, and a source edit here would pre-empt the ruling.

_BOUNDARY = datetime(2026, 3, 15, tzinfo=UTC)
_EXPIRY = datetime(2026, 3, 15, 12, tzinfo=UTC)
_PLAN_ID = "spike/plan"
_BASE_PAYLOAD: Mapping[str, Any] = {"answer": "42"}

#: The opaque identifier a carrier would name. Deliberately unmistakable in a
#: byte-level search, because "is this value recoverable from (record,
#: projection)?" is answered by looking for it rather than by reasoning.
_EVIDENCE_TOKEN = "spike-evidence-token-0001"
_EVIDENCE: tuple[str, ...] = (_EVIDENCE_TOKEN,)

#: The declared-schema half of the fork, in the ``(key, version)`` shape
#: `ccf.products.payload` already ships. Owned by this module; nothing is
#: registered in any Control Plane.
_PAYLOAD_SCHEMA_KEY = "spike.debt-evidence"
_PAYLOAD_SCHEMA_VERSION = "1.0.0"


class _AssessmentWithEvidence(DebtAssessment):
    """Placement 1: an optional evidence member *inside* the assessment.

    Owned by this module and imported nowhere else. It exists so the hash and
    reconstructibility questions can be answered without touching
    :class:`~ccf.halflife.assessment.DebtAssessment`.
    """

    evidence: tuple[str, ...] = ()


class _ProductWithEvidence(ContextProductContract):
    """Placement 2: a new top-level field on the vessel, sibling to ``debt``."""

    evidence: tuple[str, ...] = ()


class _PathWithEvidence(ContentGenerationPath):
    """Placement 4: a new member of the replay record's dimension 5."""

    evidence: tuple[str, ...] = ()


def _factors() -> DebtFactors:
    return DebtFactors(
        freshness=Decimal("0.9"),
        completeness=Decimal("1"),
        semantic_consistency=Decimal("1"),
    )


def _assessment() -> DebtAssessment:
    return DebtAssessment(
        debt=Decimal("0.1"),
        signal=DebtSignal.OK,
        factors=_factors(),
        scorers=NO_SCORER_PINS,
    )


def _assessment_with_evidence() -> _AssessmentWithEvidence:
    return _AssessmentWithEvidence(
        debt=Decimal("0.1"),
        signal=DebtSignal.OK,
        factors=_factors(),
        scorers=NO_SCORER_PINS,
        evidence=_EVIDENCE,
    )


def _product(
    *,
    debt: DebtAssessment | None,
    payload: Mapping[str, Any],
) -> ContextProductContract:
    """The shipped vessel as every existing call site constructs it today."""
    return ContextProductContract(
        schema_name="spike.measurement",
        schema_version="1.0.0",
        plan_id=_PLAN_ID,
        tenant_id="tenant-spike",
        temporal_boundary=_BOUNDARY,
        expires_at=_EXPIRY,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"temporal.as-of-boundary"}),
            policy_bundle_versions=frozenset({"policy-v1"}),
            graph_snapshot_at=_BOUNDARY,
        ),
        payload=payload,
        debt=debt,
    )


def _product_with_toplevel_evidence(
    evidence: tuple[str, ...],
) -> _ProductWithEvidence:
    base = _product(debt=_assessment(), payload=_BASE_PAYLOAD)
    return _ProductWithEvidence(
        **{name: getattr(base, name) for name in type(base).model_fields},
        evidence=evidence,
    )


def _path(
    *, product: ContextProductContract, debt: DebtAssessment | None
) -> ContentGenerationPath:
    """Dimension 5 as the shipped builder fills it, for this stand-in product."""
    return ContentGenerationPath(
        plan_id=_PLAN_ID,
        operator_plan=("temporal.as-of-boundary",),
        steps=(),
        product_content_address=content_hash(product),
        debt=debt,
    )


def _projection(payload: Mapping[str, Any]) -> ProjectionOutput:
    """The whole of what a re-execution hands a rehydrator. Two fields."""
    return ProjectionOutput(plan_id=_PLAN_ID, payload=payload)


def _recoverable_from(
    *, path: ContentGenerationPath, projection: ProjectionOutput, token: str
) -> bool:
    """Is ``token`` present anywhere in the canonical bytes of the two inputs?

    The reconstructibility question answered by looking rather than by
    reasoning. ``rehydrate_product`` receives exactly ``(record, projection)``;
    a value absent from the canonical rendering of both is a value no
    implementation of that signature can produce.
    """
    haystack = canonical_bytes(path) + canonical_bytes(projection)
    return token.encode("utf-8") in haystack


def measure_qa_placements() -> dict[str, Any]:
    """The four candidate placements, each with an observed verdict.

    The verdicts are properties of :func:`~ccf.contracts.canonical.content_hash`
    applied to stand-ins this module owns, so plans ``15.6-06``, ``15.6-07`` and
    ``15.6-08`` may all reshape the shipped types without falsifying one:
    "adding a member to the hashed body moves the address" survives any
    reshaping of any field list.
    """
    baseline = _product(debt=_assessment(), payload=_BASE_PAYLOAD)
    baseline_address = content_hash(baseline)

    # --- placement 1: nested inside DebtAssessment ------------------------
    nested_assessment = _assessment_with_evidence()
    nested_product = _product(debt=nested_assessment, payload=_BASE_PAYLOAD)
    nested_path = _path(product=nested_product, debt=nested_assessment)
    nested_projection = _projection(_BASE_PAYLOAD)
    # The rehydrator's shipped one-liner, verbatim: the assessment comes off
    # the record and is carried onto the rebuilt product without inspection.
    nested_rehydrated = _product(
        debt=nested_path.debt, payload=nested_projection.payload
    )

    # --- placement 2: a new top-level field on the vessel ------------------
    toplevel_product = _product_with_toplevel_evidence(_EVIDENCE)
    toplevel_path = _path(product=toplevel_product, debt=_assessment())
    toplevel_projection = _projection(_BASE_PAYLOAD)
    # The only rebuild available to a `(record, projection)` rehydrator: the
    # field falls back to its default, because neither input names the value.
    toplevel_rehydrated = _ProductWithEvidence(
        **{
            name: getattr(toplevel_product, name)
            for name in ContextProductContract.model_fields
        }
    )

    # --- placement 3: declared content inside the payload ------------------
    declared_payload: Mapping[str, Any] = {
        **_BASE_PAYLOAD,
        "debt_evidence": {
            "payload_schema_key": _PAYLOAD_SCHEMA_KEY,
            "payload_schema_version": _PAYLOAD_SCHEMA_VERSION,
            "observations": list(_EVIDENCE),
        },
    }
    declared_product = _product(debt=_assessment(), payload=declared_payload)
    declared_path = _path(product=declared_product, debt=_assessment())
    declared_projection = _projection(declared_payload)
    declared_rehydrated = _product(
        debt=declared_path.debt, payload=declared_projection.payload
    )

    # --- placement 4: on the replay record only ----------------------------
    record_only_product = baseline
    record_only_path = _PathWithEvidence(
        plan_id=_PLAN_ID,
        operator_plan=("temporal.as-of-boundary",),
        steps=(),
        product_content_address=content_hash(record_only_product),
        debt=_assessment(),
        evidence=_EVIDENCE,
    )
    record_only_projection = _projection(_BASE_PAYLOAD)
    record_only_rehydrated = _product(
        debt=record_only_path.debt, payload=record_only_projection.payload
    )

    return {
        "baseline_product_content_address": baseline_address,
        "qa_nested": {
            "placement": "an optional member inside DebtAssessment",
            "content_address_moves": content_hash(nested_product)
            != baseline_address,
            "observed_address": content_hash(nested_product),
            "reconstructible_from_record_and_projection": (
                content_hash(nested_rehydrated) == content_hash(nested_product)
            ),
            "value_present_in_record_or_projection_bytes": _recoverable_from(
                path=nested_path,
                projection=nested_projection,
                token=_EVIDENCE_TOKEN,
            ),
            "reason": (
                "canonical_bytes walks a model field-by-field over "
                "type(value).model_fields and recurses into nested models, so "
                "a member inside the assessment is inside the product's "
                "address; and the assessment already rides "
                "ContentGenerationPath.debt, so the rehydrator's existing "
                "one-line `debt=record.content_generation_path.debt` carries "
                "the reshaped assessment verbatim with no implementation "
                "change at any of the shipped rehydrate_product sites"
            ),
        },
        "qa_toplevel": {
            "placement": "a new top-level field on ContextProductContract",
            "content_address_moves": content_hash(toplevel_product)
            != baseline_address,
            "observed_address": content_hash(toplevel_product),
            "reconstructible_from_record_and_projection": (
                content_hash(toplevel_rehydrated)
                == content_hash(toplevel_product)
            ),
            "value_present_in_record_or_projection_bytes": _recoverable_from(
                path=toplevel_path,
                projection=toplevel_projection,
                token=_EVIDENCE_TOKEN,
            ),
            "rehydrated_address": content_hash(toplevel_rehydrated),
            "reason": (
                "the field is in the hashed body, so the address moves; and "
                "ProjectionOutput carries exactly (plan_id, payload) while "
                "dimension 5 carries no member naming the value, so the "
                "token does not appear in the canonical bytes of either "
                "input and no implementation of the "
                "(record, projection) signature can reproduce it. The rebuilt "
                "product falls back to the field default and hashes "
                "differently, which is the ReplayDivergence raise path"
            ),
        },
        "qa_declared": {
            "placement": "declared content inside payload, under the "
            "payload_schema_key / payload_schema_version shape",
            "content_address_moves": content_hash(declared_product)
            != baseline_address,
            "observed_address": content_hash(declared_product),
            "reconstructible_from_record_and_projection": (
                content_hash(declared_rehydrated)
                == content_hash(declared_product)
            ),
            "value_present_in_record_or_projection_bytes": _recoverable_from(
                path=declared_path,
                projection=declared_projection,
                token=_EVIDENCE_TOKEN,
            ),
            "reason": (
                "payload is a hashed field, so the address moves; and payload "
                "comes back verbatim on ProjectionOutput.payload, so the "
                "rebuild reproduces the address exactly. What replay does "
                "*not* do is compare the evidence against any declared "
                "schema: the conformity comparison lives at bind, on a seam "
                "no shipped door calls"
            ),
        },
        "qa_record": {
            "placement": "a new member of ContentGenerationPath only",
            "content_address_moves": content_hash(record_only_product)
            != baseline_address,
            "observed_address": content_hash(record_only_product),
            "reconstructible_from_record_and_projection": (
                content_hash(record_only_rehydrated)
                == content_hash(record_only_product)
            ),
            "value_present_in_record_or_projection_bytes": _recoverable_from(
                path=record_only_path,
                projection=record_only_projection,
                token=_EVIDENCE_TOKEN,
            ),
            "reason": (
                "the product's field list is untouched, so its bytes and its "
                "address are what they are today and the rebuild is trivially "
                "exact. The value is on the record and reaches no delivered "
                "product at all — which is what the Q-B door enumeration "
                "prices"
            ),
        },
    }


# --------------------------------------------------------------------------
# The real tripwire. REPORTED.
# --------------------------------------------------------------------------

#: Which placements the real tripwire can be run against as the tree stands.
TRIPWIRE_SHAPES: Mapping[str, str] = {
    "qa_nested": (
        "cannot be exercised end to end: DebtAssessment is frozen and "
        "extra=forbid, so an evidence member cannot exist on the shipped type "
        "without editing src/ccf/halflife/assessment.py, which this plan is "
        "forbidden to do. The tripwire's baseline outcome is recorded instead, "
        "and the round trip is executed above against a stand-in subclass "
        "carried through the real ContentGenerationPath.debt field"
    ),
    "qa_toplevel": (
        "cannot be exercised end to end: requires a new field on "
        "ContextProductContract, a new member on ContentGenerationPath and a "
        "rehydrate_product that reads it back — three source changes across "
        "src/ and every shipped rehydrator"
    ),
    "qa_declared": (
        "exercised: payload is already an open Mapping, so a payload carrying "
        "declared evidence needs no source change and the tripwire runs "
        "exactly as it does today"
    ),
    "qa_record": (
        "exercised: the product's bytes are unchanged, so the tripwire runs "
        "unchanged and its result is the measured baseline"
    ),
}


@lru_cache(maxsize=1)
def run_rehydration_tripwire() -> dict[str, Any]:
    """Run ``tests/replay/test_engine_rehydration.py`` and report the outcome.

    A separate interpreter rather than a nested ``pytest.main`` call: the outer
    session's capture, plugin registry and already-imported conftest modules are
    left entirely alone, so the figure measures the tripwire and not the
    interaction between two pytest sessions.
    """
    if os.environ.get(TRIPWIRE_ENV, "1") != "1":
        return {
            "ran": False,
            "reason": f"{TRIPWIRE_ENV} is not '1'; measurement skipped",
        }
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(REHYDRATION_TRIPWIRE), "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = completed.stdout.strip().splitlines()
    return {
        "ran": True,
        "command": f"python -m pytest {REHYDRATION_TRIPWIRE} -q",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "summary": lines[-1] if lines else "",
    }


# --------------------------------------------------------------------------
# Q-B — the record-only placement's consumer reach. ASSERTED.
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def measure_qb_doors() -> dict[str, Any]:
    """What each shipped delivery door serializes, read off its source.

    Asserted rather than reported because no plan in this phase touches
    ``runtime/``, so the fact is stable under the phase's own work; it is also
    the single fact that decides whether a record-only carrier reaches a
    consumer at all.
    """
    doors: dict[str, Any] = {}
    for relative, builder in DELIVERY_DOORS:
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        tree = ast.parse(source)
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        doors[relative] = {
            "builder": f"{relative}::{builder}",
            "builder_resolves": builder in defined,
            "serializes_servable_product": "servable.product" in source,
            "reads_replay_ref": "replay_ref" in source,
            "served_product_fields": tuple(ServedProduct.model_fields),
        }
    return {
        "doors": doors,
        "door_count": len(doors),
        "enumeration_source": (
            "tests/invariants/test_mcp_role_separation.py holds this "
            "three-door table as exhaustive over runtime's product-serving "
            "handlers; a fourth door fails that suite"
        ),
    }


def measure_qb_in_process_reach() -> dict[str, Any]:
    """The in-process population a record-only carrier *would* reach. REPORTED."""
    governed = count_call_sites(SERVE_CALL_SYMBOL, "name")
    return {
        "governed_serve_call_sites": governed["call_sites"],
        "governed_serve_distinct_files": governed["distinct_files"],
        "by_tree": governed["by_tree"],
        "note": (
            "these are the callers holding a ServedProduct in process, and "
            "therefore the whole population that could read a record-only "
            "carrier. Reported rather than asserted because this phase adds "
            "and moves call sites in tests/ and examples/"
        ),
    }


# --------------------------------------------------------------------------
# Q-E — the regeneration surface, re-derived at this plan's base. REPORTED.
# --------------------------------------------------------------------------


def _sweep_files() -> Iterator[pathlib.Path]:
    for root_name in ADDRESS_SWEEP_ROOTS:
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if EXCLUDED_PARTS & set(path.parts):
                continue
            yield path


def _classify(relative: str) -> tuple[str, str]:
    for prefix, verdict, reason in _ADDRESS_CLASSIFICATION:
        if relative.startswith(prefix):
            return verdict, reason
    return (
        "UNCLASSIFIED",
        "no classification recorded for this path; a reader has to open it",
    )


def measure_qe_regeneration_surface() -> dict[str, Any]:
    """Re-derive the 64-hex content-address census at this plan's own base.

    ``15.6-RESEARCH.md`` § B1 reports one moving file. This function does not
    carry that figure: it re-derives the census and reports the drift, if any.
    Reported and never asserted — plans ``15.6-06``, ``15.6-07`` and
    ``15.6-08`` each regenerate what this census counts.
    """
    hits: dict[str, int] = {}
    truncated: dict[str, int] = {}
    for path in _sweep_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = str(path.relative_to(REPO_ROOT))
        found = len(_HEX64.findall(text))
        if found:
            hits[relative] = found
        elided = len(_HEX_TRUNCATED.findall(text))
        if elided:
            truncated[relative] = elided

    classified = {
        relative: {
            "full_length_literals": hits.get(relative, 0),
            "truncated_literals": truncated.get(relative, 0),
            "verdict": _classify(relative)[0],
            "reason": _classify(relative)[1],
        }
        for relative in sorted(set(hits) | set(truncated))
    }
    moving = sorted(
        relative
        for relative, row in classified.items()
        if row["verdict"] == "MOVES"
    )
    unclassified = sorted(
        relative
        for relative, row in classified.items()
        if row["verdict"] == "UNCLASSIFIED"
    )
    return {
        "sweep_roots": ADDRESS_SWEEP_ROOTS,
        "files_with_address_literals": len(classified),
        "files_with_full_length_literals": len(hits),
        "files_with_truncated_literals": len(truncated),
        "total_full_length_literals": sum(hits.values()),
        "total_truncated_literals": sum(truncated.values()),
        "by_file": classified,
        "files_that_move_when_DebtAssessment_reshapes": moving,
        "moving_file_count": len(moving),
        "unclassified_files": unclassified,
        "research_figure_for_comparison": 1,
        "drift_against_research_figure": len(moving) - 1,
        "finding": (
            "the census reproduces 15.6-RESEARCH.md's one-file figure only "
            "once the ELIDED address form is swept as well. A 64-hex sweep "
            "over the same trees finds zero literals in "
            "examples/08-e2e-demo/artifacts/expected_output.txt, because the "
            "example prints its addresses truncated to a 16-hex prefix. The "
            "second finding is what that file actually pins: not the product "
            "content address but the REPLAY RECORD address and the "
            "skill-set-in-force hash. Both still move on a DebtAssessment "
            "reshape — the record carries ContentGenerationPath, which carries "
            "debt — so the count is unchanged and the mechanism named in the "
            "research is not the mechanism in the file"
        ),
    }


# --------------------------------------------------------------------------
# Q-C — the Observation identity field's cost split. REPORTED.
# --------------------------------------------------------------------------

#: The positive sentinel an optional identity would carry, in the
#: ``NO_SCORER_PINS`` voice. Owned by this module; nothing is proposed by it.
_NO_SUBJECT = "no-subject"


class _ObservationWithRequiredIdentity(Observation):
    """Stand-in: the identity as a required field."""

    subject_uri: str


class _ObservationWithOptionalIdentity(Observation):
    """Stand-in: the identity as an optional field behind a positive sentinel."""

    subject_uri: str = _NO_SUBJECT


def _observation_mappings(relative: str) -> tuple[Mapping[str, Any], ...]:
    """Every mapping in a YAML artifact that carries ``observation_type``."""
    document = yaml.safe_load(
        (REPO_ROOT / relative).read_text(encoding="utf-8")
    )
    found: list[Mapping[str, Any]] = []

    def walk(node: object) -> None:
        if isinstance(node, Mapping):
            if "observation_type" in node and "observed_at" in node:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(document)
    return tuple(found)


def measure_qc_observation_cost() -> dict[str, Any]:
    """The required-versus-optional split, with the breakage executed.

    Every count here is reported: plan ``15.6-05`` changes all of them.
    """
    constructions = count_call_sites("Observation", "name")
    validations = count_receiver_calls("Observation", "model_validate")

    executed: dict[str, Any] = {}
    for relative in OBSERVATION_ARTIFACTS:
        mappings = _observation_mappings(relative)
        rows: list[dict[str, Any]] = []
        for mapping in mappings:
            payload = dict(mapping)
            required_outcome: dict[str, Any]
            try:
                _ObservationWithRequiredIdentity.model_validate(payload)
            except ValidationError as error:
                required_outcome = {
                    "raised": type(error).__name__,
                    "error_count": error.error_count(),
                    "error_types": sorted(
                        {item["type"] for item in error.errors()}
                    ),
                    "missing_fields": sorted(
                        {
                            str(item["loc"][0])
                            for item in error.errors()
                            if item["loc"]
                        }
                    ),
                }
            else:
                required_outcome = {"raised": None}

            optional_outcome: dict[str, Any]
            try:
                validated = _ObservationWithOptionalIdentity.model_validate(
                    payload
                )
            except ValidationError as error:
                optional_outcome = {"raised": type(error).__name__}
            else:
                optional_outcome = {
                    "raised": None,
                    "subject_uri": validated.subject_uri,
                }
            rows.append(
                {
                    "keys_present": sorted(payload),
                    "required_field": required_outcome,
                    "optional_field": optional_outcome,
                }
            )
        executed[relative] = {
            "observation_mappings_found": len(mappings),
            "outcomes": rows,
        }

    broken_by_required = sorted(
        relative
        for relative, row in executed.items()
        if any(
            outcome["required_field"]["raised"] is not None
            for outcome in row["outcomes"]
        )
    )
    broken_by_optional = sorted(
        relative
        for relative, row in executed.items()
        if any(
            outcome["optional_field"]["raised"] is not None
            for outcome in row["outcomes"]
        )
    )
    return {
        "observation_fields_today": tuple(Observation.model_fields),
        "construction_census": constructions,
        "model_validate_census": validations,
        "artifacts_examined": OBSERVATION_ARTIFACTS,
        "executed_breakage": executed,
        "artifacts_broken_by_a_required_field": broken_by_required,
        "artifacts_broken_by_an_optional_field": broken_by_optional,
        "code_files_touched_by_a_required_field": sorted(
            set(constructions["by_file"]) | set(validations["by_file"])
        ),
        "code_files_touched_by_an_optional_field": sorted(
            set(constructions["by_file"])
        ),
        "note": (
            "the split is executed, not inferred from extra=forbid semantics: "
            "each artifact's actual observation mapping is model_validate'd "
            "against a stand-in carrying a required field and again against "
            "one carrying an optional field, and what each raises is recorded"
        ),
    }


# --------------------------------------------------------------------------
# Q-D — the join key already in hand. REPORTED, with one asserted limb.
# --------------------------------------------------------------------------

_ASSEMBLER_SITE = "examples/s1-01-hello-context-product/deployment.py"


def measure_qd_join_key() -> dict[str, Any]:
    """Fields in hand at the assembler, against fields carried into Observation.

    The asserted limb is that :class:`~ccf.contracts.claims.EntityClaim`
    declares ``entity_uri`` and ``lineage`` among its fields — which no plan in
    this phase changes and which the ``claims.py`` file-hash pin in
    ``tests/peering/test_admission_record.py`` actively prevents changing.
    Everything else here is reported.
    """
    return {
        "call_site": f"{_ASSEMBLER_SITE}::KycScenario",
        "fields_in_hand_on_record_claim": tuple(EntityClaim.model_fields),
        "fields_on_each_lineage_entry": tuple(LineageEntry.model_fields),
        "fields_carried_into_observation": tuple(Observation.model_fields),
        "fields_available_and_discarded": tuple(
            sorted(set(EntityClaim.model_fields) - set(Observation.model_fields))
        ),
        "consequence": (
            "gap 1 is 'stop discarding the join key', not 'build one'. "
            "D-IMPL-99's NOT MEASURABLE verdict was true of the TYPE — "
            "Observation carries exactly (observation_type, observed_at) and "
            "no identity — and was never true of the CALL SITE, where the "
            "assembler holds the whole EntityClaim in the loop variable, reads "
            "two of its fields and drops the rest"
        ),
        "observation_construction_sites_in_src_and_runtime": {
            path: hits
            for path, hits in count_call_sites("Observation", "name")[
                "by_file"
            ].items()
            if path.startswith(("src/", "runtime/"))
        },
    }


# --------------------------------------------------------------------------
# Q-B2 — does an evidence pointer leak entitlement? REPORTED.
# --------------------------------------------------------------------------
#
# Three measurements, each carrying the `path::Symbol` of the hop it read.
# This module recommends nothing here, proposes no mitigation and reaches no
# verdict: the Wave-2 checkpoint puts the question to Dave as a new D-IMPL
# entry, and an executor's opinion in this section would be the thing that
# launders a preference into a ruling.


def _parameter_names(target: Any) -> tuple[str, ...]:
    return tuple(inspect.signature(target).parameters)


def measure_qb2_entitlement() -> dict[str, Any]:
    """Three cited measurements of where entitlement reaches the assembly.

    Executed by reading the shipped signatures rather than by describing them:
    whether a stage takes a perspective at all is a fact about its parameter
    list, and a parameter list is readable.
    """
    from ccf_runtime.authz.product_entitlement import entitled_perspective
    from ccf.deployment import build_operator_registry

    execute_parameters = _parameter_names(ProjectionEngine.execute)
    registry_parameters = _parameter_names(build_operator_registry)
    policy_filter_parameters = _parameter_names(PolicyFilter.__init__)
    entitlement_parameters = _parameter_names(entitled_perspective)

    hops = (
        {
            "hop": 1,
            "symbol": "runtime/ccf_runtime/mcp/egress.py::build_egress_server",
            "reading": (
                "the door's handler calls entitled_perspective with the "
                "verified grant and binds the return value to a local, then "
                "passes it to the deployment's product resolver"
            ),
        },
        {
            "hop": 2,
            "symbol": (
                "runtime/ccf_runtime/authz/product_entitlement.py"
                "::entitled_perspective"
            ),
            "reading": (
                "resolves a Perspective from the verified grant, refuses a "
                "subject conflict, and authorizes the (tenant, product_class, "
                "role) triple. Its parameters are "
                f"{entitlement_parameters}"
            ),
        },
        {
            "hop": 3,
            "symbol": (
                "examples/s1-01-hello-context-product/spine.py"
                "::assemble_and_serve"
            ),
            "reading": (
                "reads the graph with reader.as_of(tenant_id=..., at=...) — "
                "tenant and instant, no principal — and builds the operator "
                "registry from the deployment's operator-parameter artifacts"
            ),
        },
        {
            "hop": 4,
            "symbol": (
                "src/ccf/deployment/operators.py::build_operator_registry"
            ),
            "reading": (
                "constructs every operator from artifacts. Its parameters are "
                f"{registry_parameters}"
            ),
        },
        {
            "hop": 5,
            "symbol": "src/ccf/operators/categories.py::PolicyFilter",
            "reading": (
                "the only admissibility narrowing in the operator chain. Its "
                f"constructor parameters are {policy_filter_parameters}, and "
                "its admission test reads policy_bundle_version and a "
                "classification attribute off the entity record against "
                "deployment-declared parameter values"
            ),
        },
        {
            "hop": 6,
            "symbol": "src/ccf/projection/engine.py::ProjectionEngine",
            "reading": (
                "runs the operator chain to a surviving view, then invokes the "
                "plan with the perspective. Its execute parameters are "
                f"{execute_parameters}"
            ),
        },
        {
            "hop": 7,
            "symbol": (
                "examples/s1-01-hello-context-product/deployment.py"
                "::KycScenario"
            ),
            "reading": (
                "the assembler enumerates view.entities to build the "
                "Observation sequence the freshness scorer consumes; the view "
                "it is handed is the post-operator view, not a "
                "principal-conditioned one"
            ),
        },
    )

    return {
        "disclaimer": (
            "This module recommends nothing, proposes no mitigation and "
            "reaches no verdict in this section. The three findings below are "
            "measurements; the ruling is Dave's, as a new D-IMPL entry at the "
            "Wave-2 checkpoint"
        ),
        "prior_ruling_by_analogy": (
            "D-IMPL-105 ruled the analogous question for completeness "
            "precisely because a caller could infer what they are not allowed "
            "to see. No shipped ruling covers evidence pointers"
        ),
        "finding_1_view_scoping": {
            "question": (
                "is the graph view the assembler enumerates to build "
                "Observations perspective-scoped or tenant-scoped?"
            ),
            "answer": "tenant-scoped and operator-parameter-narrowed",
            "call_chain": hops,
            "evidence": {
                "projection_engine_execute_parameters": execute_parameters,
                "build_operator_registry_parameters": registry_parameters,
                "policy_filter_init_parameters": policy_filter_parameters,
                "perspective_reaches_the_operator_stage": (
                    "perspective" in registry_parameters
                    or "perspective" in policy_filter_parameters
                ),
                "perspective_reaches_the_projection_stage": (
                    "perspective" in execute_parameters
                ),
            },
        },
        "finding_2_two_principals": {
            "question": (
                "would two principals with different product-class "
                "entitlements, assembling the same product class over the same "
                "graph state, enumerate the same set of entity_uri values?"
            ),
            "answer": (
                "yes, as the shipped path stands: the operator stage that "
                "produces the enumerated view takes no perspective, so the two "
                "principals are handed the same view"
            ),
            "paths_converge_at": "src/ccf/projection/engine.py::ProjectionEngine",
            "paths_diverge_at": "src/ccf/projection/plan.py::ProjectionPlan",
            "evidence": (
                "ProjectionEngine.execute threads perspective into the plan "
                "invocation only; the operator chain that computes the "
                "surviving view is built by build_operator_registry from "
                "artifact-supplied parameters, whose parameter list carries no "
                "principal and no perspective. Entitlement is decided before "
                "assembly, at entitled_perspective, on the (tenant, "
                "product_class, role) triple — a per-class decision, not a "
                "per-entity one"
            ),
        },
        "finding_3_exposure_delta": {
            "question": (
                "what would a pointer derived from the full graph expose that "
                "a pointer derived from the perspective-scoped view would not?"
            ),
            "answer": (
                "on the shipped path the two are the same set, so the delta is "
                "empty — and that is the finding. There is no "
                "perspective-scoped view to derive a narrower pointer from: "
                "the narrowing that does happen is PolicyFilter's, keyed on "
                "permitted policy-bundle versions and permitted "
                "classifications declared per deployment, identically for "
                "every principal of the class"
            ),
            "narrowing_symbol": "src/ccf/operators/categories.py::PolicyFilter",
            "entity_fields_a_pointer_could_name": tuple(
                EntityClaim.model_fields
            ),
            "evidence": (
                "PolicyFilter's admission test reads the entity record's "
                "policy_bundle_version and a per-class classification "
                "attribute against parameter values supplied by the "
                "deployment's operator-parameter artifacts. Nothing in that "
                "test names the principal, so an evidence pointer derived from "
                "the surviving view names whatever the class's policy "
                "parameters admitted, for every caller entitled to the class"
            ),
        },
    }


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def measure_all() -> dict[str, Any]:
    """Every figure this module produces, as one mapping.

    This is the reporting half. It is a plain helper the tests call; it is not
    a fixture, and nothing it returns is compared in an assertion.
    """
    return {
        "instrument": {
            "module": "tests/spikes/test_debt_evidence_placement_cost.py",
            "plan": "15.6-01",
            "retiring_owner": "15.6-12 task 1",
            "search_roots": SEARCH_ROOTS,
            "address_sweep_roots": ADDRESS_SWEEP_ROOTS,
            "excluded_path_parts": tuple(sorted(EXCLUDED_PARTS)),
            "self_excluded": (
                "tests/spikes/ is excluded from every walk; this module's own "
                "stand-in constructors are not tree cost"
            ),
        },
        "qa_placements": measure_qa_placements(),
        "qa_tripwire": run_rehydration_tripwire(),
        "qa_tripwire_shapes": dict(TRIPWIRE_SHAPES),
        "qb_doors": measure_qb_doors(),
        "qb_in_process_reach": measure_qb_in_process_reach(),
        "qb2_entitlement": measure_qb2_entitlement(),
        "qc_observation_cost": measure_qc_observation_cost(),
        "qd_join_key": measure_qd_join_key(),
        "qe_regeneration_surface": measure_qe_regeneration_surface(),
    }


def _render(figures: Mapping[str, Any]) -> str:
    return json.dumps(figures, indent=2, sort_keys=True, default=str)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_the_report_is_producible_and_is_printed_for_the_evidence_document(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Produce the figure set. Nothing here compares a tree-derived value.

    Run with ``-s`` to read the figures, or set ``CCF_SPIKE_REPORT`` to a path
    to have them written there as JSON.
    """
    figures = measure_all()
    rendered = _render(figures)
    with capsys.disabled():
        print(f"\n=== 15.6-01 measured figures ===\n{rendered}")
    destination = os.environ.get(REPORT_ENV)
    if destination:
        pathlib.Path(destination).write_text(rendered, encoding="utf-8")
    assert set(figures) >= {
        "qa_placements",
        "qb_doors",
        "qb2_entitlement",
        "qc_observation_cost",
        "qd_join_key",
        "qe_regeneration_surface",
    }


@pytest.mark.parametrize("symbol", MEASURED_SYMBOLS)
def test_the_ast_walk_finds_the_symbol_at_all(symbol: str) -> None:
    """An instrument check, deliberately not a count check.

    A walk returning zero for ``DebtAssessment`` means the walker is broken.
    That is a fact about the instrument, and it stays true however many call
    sites plans ``15.6-05``/``06``/``07``/``08``/``10``/``11`` add or remove.
    The counts themselves are reported, never asserted.
    """
    measured = count_call_sites(symbol)
    assert measured["call_sites"] > 0, symbol
    assert measured["distinct_files"] > 0, symbol


# --- Q-A: the four placements. ASSERTED. ----------------------------------


def test_qa_nested_moves_the_address_and_is_reconstructible() -> None:
    """Placement 1: the address moves, and the record carries it back.

    The free ride: ``DebtAssessment`` already rides both
    ``ContextProductContract.debt`` and ``ContentGenerationPath.debt``, so the
    rehydrator's shipped one-liner carries a reshaped assessment verbatim.
    """
    placements = measure_qa_placements()
    nested = placements["qa_nested"]
    assert nested["content_address_moves"] is True
    assert nested["reconstructible_from_record_and_projection"] is True
    assert nested["value_present_in_record_or_projection_bytes"] is True


def test_qa_toplevel_moves_the_address_and_is_not_reconstructible() -> None:
    """Placement 2: the address moves and nothing can rebuild it.

    ``ProjectionOutput`` carries exactly ``(plan_id, payload)``, and that is
    the whole constraint. A vessel field the record does not also carry is a
    field ``rehydrate_product`` cannot produce, so every replay of every
    product would raise ``ReplayDivergence``.
    """
    placements = measure_qa_placements()
    toplevel = placements["qa_toplevel"]
    assert toplevel["content_address_moves"] is True
    assert toplevel["reconstructible_from_record_and_projection"] is False
    assert toplevel["value_present_in_record_or_projection_bytes"] is False


def test_qa_declared_moves_the_address_and_is_reconstructible() -> None:
    """Placement 3: payload is hashed, and payload comes back verbatim."""
    placements = measure_qa_placements()
    declared = placements["qa_declared"]
    assert declared["content_address_moves"] is True
    assert declared["reconstructible_from_record_and_projection"] is True
    assert declared["value_present_in_record_or_projection_bytes"] is True


def test_qa_record_only_leaves_the_address_untouched() -> None:
    """Placement 4: the delivered bytes are what they are today."""
    placements = measure_qa_placements()
    record_only = placements["qa_record"]
    assert record_only["content_address_moves"] is False
    assert record_only["reconstructible_from_record_and_projection"] is True
    assert record_only["value_present_in_record_or_projection_bytes"] is True
    assert (
        record_only["observed_address"]
        == placements["baseline_product_content_address"]
    )


def test_every_placement_has_a_verdict_and_a_reason() -> None:
    """Structural: the ruling package cannot be handed an unexplained cell."""
    placements = measure_qa_placements()
    for name in ("qa_nested", "qa_toplevel", "qa_declared", "qa_record"):
        verdict = placements[name]
        assert isinstance(verdict["content_address_moves"], bool), name
        assert isinstance(
            verdict["reconstructible_from_record_and_projection"], bool
        ), name
        assert verdict["reason"].strip(), name
        assert name in TRIPWIRE_SHAPES, name


# --- Q-B: the three doors. ASSERTED. --------------------------------------


def test_every_shipped_door_serializes_the_product_and_none_reads_the_ref() -> (
    None
):
    """The record-only placement's consumer reach, read off three files.

    Asserted because no plan in this phase touches ``runtime/``. If a door
    ever grew a ``replay_ref`` read, a record-only carrier would reach a wire
    consumer and this measurement would have to be retaken — which is exactly
    why it is a gate rather than a note.
    """
    measured = measure_qb_doors()
    for relative, row in measured["doors"].items():
        assert row["builder_resolves"] is True, relative
        assert row["serializes_servable_product"] is True, relative
        assert row["reads_replay_ref"] is False, relative
    assert measured["door_count"] == len(DELIVERY_DOORS)


# --- Q-D: the one stable limb. ASSERTED. ----------------------------------


def test_entity_claim_declares_the_join_key_and_the_provenance() -> None:
    """``EntityClaim`` carries ``entity_uri`` and ``lineage``.

    Asserted because no plan in this phase edits ``src/ccf/contracts/claims.py``
    — and because ``tests/peering/test_admission_record.py`` pins that file's
    sha256, so an edit is a failing gate rather than a silent change. Every
    count around this limb is reported.
    """
    declared = set(EntityClaim.model_fields)
    assert "entity_uri" in declared
    assert "lineage" in declared
    assert "observed_at" in declared


# --- Q-C: the stand-ins behave as stand-ins. ASSERTED. --------------------


def test_a_required_identity_refuses_a_two_key_observation_mapping() -> None:
    """The executed half of the Q-C split, over a mapping this module owns.

    The same executed check runs over the three real artifacts in
    :func:`measure_qc_observation_cost`, where its outcome is *reported* —
    plan ``15.6-05`` edits those artifacts. What is asserted here is only that
    the stand-in behaves as a stand-in: a required field refuses a mapping
    that does not carry it, and an optional one does not.
    """
    mapping = {
        "observation_type": "spike-observation",
        "observed_at": "2026-03-15T00:00:00Z",
    }
    with pytest.raises(ValidationError):
        _ObservationWithRequiredIdentity.model_validate(mapping)
    validated = _ObservationWithOptionalIdentity.model_validate(mapping)
    assert validated.subject_uri == _NO_SUBJECT


# --- Q-B2: the section asserts nothing. -----------------------------------


def test_the_entitlement_findings_are_three_cited_measurements() -> None:
    """Structural only: three findings, each carrying the hop it read.

    Nothing about the *answers* is asserted — the call chain runs through
    ``examples/``, which this phase's later plans may move, and the question
    itself is unruled. What is checked is that no finding reaches the Wave-2
    checkpoint without a citation.
    """
    findings = measure_qb2_entitlement()
    for key in ("finding_1_view_scoping", "finding_2_two_principals",
                "finding_3_exposure_delta"):
        row = findings[key]
        assert row["question"].strip(), key
        assert row["answer"].strip(), key
    assert findings["finding_1_view_scoping"]["call_chain"]
    for hop in findings["finding_1_view_scoping"]["call_chain"]:
        assert "::" in hop["symbol"], hop
    assert "::" in findings["finding_2_two_principals"]["paths_converge_at"]
    assert "::" in findings["finding_2_two_principals"]["paths_diverge_at"]
    assert "::" in findings["finding_3_exposure_delta"]["narrowing_symbol"]
