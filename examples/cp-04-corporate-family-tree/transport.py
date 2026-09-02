"""The in-process transport cp-04 supplies to `ProductClient`.

[ADAPT] all of it. [MECHANISM] the `TransportAdapter` Protocol this satisfies,
and the door emission it reuses unchanged.

**WHY THIS FILE EXISTS AT ALL, MEASURED RATHER THAN ASSERTED.** The SDK ships an
in-process adapter, and cp-04 cannot use it. `src/ccf/client/adapters/inprocess.py::_boot`
builds its resolver through `build_governed_resolver` from a `binding.yaml`, and
that resolver reads an **already-populated graph**: nothing on that path performs
an L1 ingest. cp-04 must open **two** systems of record during the assembly and
write what it read through L2, so a resolver handed a populated graph has already
skipped the half of this product that makes it a multi-store product. The
binding document could not express the second store either —
`src/ccf/client/adapters/binding_document.py::RULED_OUT_KEYS` refuses a
`resolver:` key **by name** — so `ProductClient.for_product` was never available
to this rung whatever it wanted.

That is **RECORDED as an SDK-surface finding** at spec §F.4 Conflict 2, where
Dave ruled it at Gate 1 (`D-IMPL-225` amendment 2): the consume path is the
documented direct-adapter constructor `ProductClient(product_id=…, adapter=…)`
at `src/ccf/client/client.py::ProductClient.__init__`, the binding stays
single-store, and **the two-store assembly happens inside the product**. It is
**not closed here** — `D-04` of `24-CONTEXT.md` governs, and criterion 49 forbids
this phase touching `src/`.

**THE DIRECTION IS THE WHOLE CONTENT OF THE STANDALONE CLAIM.** This module
knows about `assembler.py`; `assembler.py` knows nothing about this module, and
nothing about a transport, a server, a tool or a resource. `CFT-G14` is that
check — one standalone assembler serving both callers — and it is only
demonstrable while the arrow points this way.

**THE WIRE IS DEGENERATE IN BOTH DIRECTIONS, ON PURPOSE.** `ask` encodes the
question to canonical text and the door half parses it back with
`ccf.products.door::door_question`; the two halves never share the
`WireRequest` object. That is `C-07`'s discipline copied deliberately rather
than skipped because the wire is short: a door handed the client's own object
echoes the caller's copy back to the caller, and the decoder's echo cross-check
then compares an object with itself. Everything the answer half puts on the wire
comes from `ccf.products.door::door_answer`, so the vessel is serialized exactly
once and the content address is `sha256` of those same bytes.

**WHAT THIS ADAPTER DOES NOT DO IS AS LOAD-BEARING AS WHAT IT DOES.** It reads
no member of the request to decide anything, it builds no `Result`, and it
constructs no `DoorOutcome` of its own. A governed refusal that has a refusal
*value* — a `ProductRequestViolation` — crosses as a refusal envelope. A refusal
the assembler **raises** propagates: `AssemblyRefused` is not in
`ccf.products.refusal::REFUSAL_KINDS`, so there is no envelope for it, and
synthesizing one here would report a refusal in a vocabulary the fabric does not
have. That gap is the same one §F.4 records for `not_supported_at_tier` — the
fourth rung in a row to meet it — and this file works within it rather than
papering over it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import RelationshipClaim
from ccf.products.door import WireRequest, door_answer, door_question
from ccf.products.request import ProductRequest

import assembler
import deployment
import projection


def declared_product_id() -> str:
    """The class this deployment serves, read from `ccf_config.yaml`.

    Never a literal here. A product id spelled in code is a second place for
    one Control Plane fact to be wrong, and the failure it produces is a
    `ProductNotResolvable` naming a class nobody registered.
    """
    return str(deployment.config()[deployment.KEY_PRODUCT_CLASS]["schema_name"])


@dataclass
class FamilyTreeInProcessAdapter:
    """Carry one question to the standalone assembler, and encode the answer.

    Conforms to `src/ccf/client/wire.py::TransportAdapter` structurally — the
    Protocol is `runtime_checkable`, so the conformance is asserted at
    construction in `run.py` rather than left to inspection.

    Args:
        root: Scratch space for this run's fabric — the per-run SQLite L3 and
            the file-backed artifact store. A directory, never a store: which
            substrate holds what is the deployment's declaration.
        role: The perspective role to serve under, or ``None`` for the
            deployment's declared default. It arrives at construction and
            **not** on the wire, because the request contract is a closed
            declared world (`D-IMPL-98`) and `role` is not one of its
            arguments — the perspective is the door's, exactly as the shipped
            adapter takes it from the binding rather than from the question.
    """

    root: Path
    role: str | None = None
    #: Every `Assembled` this adapter produced, in order. The Protocol pins the
    #: assembler's return type to `AssemblyOutcome`, which carries the
    #: governance of the assembly and not the served vessel — so the vessel
    #: reaches the door through the observer callback the seam already declares
    #: rather than through a widened return type.
    seen: list[Any] = field(default_factory=list)

    def ask(self, request: WireRequest) -> bytes:
        """Encode the question, hand it to the door half, return its bytes.

        Raises:
            ccf.agents.errors.AssemblyRefused: the assembler refused on
                identity, contract or existence. Propagated rather than
                translated — see this module's docstring for why there is no
                envelope to translate it into.
        """
        asked_at = request.temporal_boundary or datetime.now(UTC)
        return self._door(
            canonical_bytes(request).decode("utf-8"), asked_at=asked_at
        )

    def _door(self, asked_json: str, *, asked_at: datetime) -> bytes:
        """The producer half — parse the encoded question, answer it, emit bytes.

        It takes **text** and never a `WireRequest` object, so the echo the
        answer carries is minted from what this half decoded rather than from
        the object the client half held.
        """
        asked = door_question(asked_json)
        declared = declared_product_id()
        if asked.product_id != declared:
            raise ValueError(
                f"this deployment serves {declared!r} and was asked"
                f" {asked.product_id!r}; a question aimed at another class is a"
                " wiring defect and is never a governed refusal, because a"
                " caller told otherwise would record an audited 'no' the fabric"
                " never made"
            )
        typed = self._typed_request(asked, asked_at=asked_at)
        resolved = self._resolve(typed)
        return door_answer(
            resolved,
            echo=asked,
            resolved_request=typed,
            product_class=declared,
            version=typed.schema_version,
        )

    def _typed_request(
        self, asked: WireRequest, *, asked_at: datetime
    ) -> ProductRequest:
        """Retype the decoded question through the deployment's own composer.

        **`debt_tolerance` is converted here and nowhere earlier.** The wire
        admits `str`, `int`, `bool`, `None` and containers of those — a
        `Decimal` is refused at `WireRequest` construction because canonical
        JSON renders it as text and the echo cross-check would then report a
        transport failure on a healthy wire. The request contract declares the
        argument `type: number`, and `src/ccf/products/payload.py::_matches`
        admits `int` and `Decimal` for that and refuses a `float`. So the value
        crosses as text and becomes a `Decimal` at this boundary, which is
        where a client sending JSON would convert it too.

        **The anchor travels as the declared `lei` argument**, because
        `WireRequest` has no subject field and inventing one would be a second
        address channel. `deployment.request` composes the subject from
        `artifacts/question.yaml`; where the caller named a different anchor,
        that is a question about a different company and the subject follows
        the parameter rather than the artifact.
        """
        parameters: dict[str, Any] = dict(asked.parameters)
        tolerance = parameters.get(deployment.PARAM_DEBT_TOLERANCE)
        if tolerance is not None:
            parameters[deployment.PARAM_DEBT_TOLERANCE] = Decimal(str(tolerance))
        typed = deployment.request(parameters=parameters, asked_at=asked_at)
        anchor = parameters.get(deployment.PARAM_LEI)
        if anchor is not None and str(anchor) != typed.subject:
            typed = typed.model_copy(update={"subject": str(anchor)})
        return typed

    def _resolve(self, typed: ProductRequest) -> Any:
        """Assemble through the seam, and hand the door what it can serve.

        The scenario is captured on the way past because two of the assembly's
        collaborators need it and neither can be given it earlier:
        `deployment.relationship_claims` needs the edges the source read
        collected, and the door needs the `ServedProduct` the spine built.
        Capturing it in the reader is the one place both are reachable, and it
        keeps `assembler.py` free of either.
        """
        state: dict[str, Any] = {}

        def read(booted: Any, asked: ProductRequest, **kwargs: Any) -> Any:
            scenario = deployment.read(booted, asked, **kwargs)
            state["scenario"] = scenario
            state["booted"] = booted
            return scenario

        def claims(*, minted: Mapping[str, str]) -> Sequence[RelationshipClaim]:
            scenario = state["scenario"]
            return deployment.relationship_claims(
                tenant=state["booted"].tenant_id,
                at=scenario.request.asked_at,
                edges=scenario.edges,
                nodes=sorted(scenario.facts),
                minted=minted,
                envelopes_by_node=scenario.envelopes_by_node,
            )

        before = len(self.seen)
        product = assembler.FamilyTreeAssembler(
            config=deployment.CONFIG,
            root=self.root,
            connection=deployment.connection(root=self.root),
            read=read,
            plan_class=projection.plan_class(),
            claims=claims,
            observer=self.seen.append,
        )
        outcome = product.assemble(
            request=typed,
            perspective=deployment.perspective(self.role),
            tenant_id=deployment.tenant_id(),
        )
        # A GOVERNED REFUSAL RETURNED AS DATA CROSSES AS A REFUSAL (`D-60`).
        # `ProductRequestViolation` is one of `REFUSAL_KINDS`, so `door_answer`
        # envelopes it with the question it was refused against.
        #
        # THE INDEX IS TAKEN BEFORE THE CALL AND NOT AFTER. `seen` is the
        # adapter's whole history, so a bare `seen[-1]` would hand the door the
        # PREVIOUS question's vessel whenever this one produced none — a stale
        # answer served with a fresh echo, which is the one failure a content
        # address cannot catch because the address would be right about the
        # wrong product.
        produced = self.seen[before:]
        if not produced:
            return outcome
        served = getattr(produced[-1], "served", None)
        return outcome if served is None else served
