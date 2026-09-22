"""Frozen cp-05's governed exposure rollup, presented to the SDK's standard door.

**A binding adapter and nothing more** (the CP-14 completion GO, exposure
option 3, Dave 2026-09-17). `examples/cp-05-credit-exposure-rollup` is a frozen
specimen (`D-IMPL-261`, `D-IMPL-281`) whose gross and adjusted exposure are
determined in ``assembler.py`` AFTER the traversal and BEFORE Π (`D-IMPL-299`:
assembly determines exposure; projection decides which of it is material to the
caller). The paved road offers no seam between the operators and Π
(`CP14-F-33`), and that limitation stands: nothing here relocates the
aggregation, reverses `D-IMPL-299`, or adds a hook. The specimen's low road —
``produce.produce_governed`` — already runs the whole governed path and returns
the one shape a door may release: a ``ServedProduct`` minted by delivery, or a
``RefusalEnvelope`` recorded, disclosed and addressed. This module presents that
path to :func:`ccf_runtime.mcp.product_door.open_door` through the door's own
structural contract, ``ServesProducts``: nine members, every one of which the
frozen tree already holds.

**What is reused, and what is written.** The door, the producer assertion, the
bearer verification, the entitlement policy and source, the perspective
resolver, the refusal recorder's contract and the replay machinery are the
SDK's. What this module writes is: the nine attributes, one ``resolve`` that
translates a ``ProductRequest`` into the call the specimen's own door made, the
two pre-assembly refusals that door recorded, and ONE guard the frozen tree
needs and cannot express itself — the instant.

**The instant guard.** ``produce_governed`` takes no ``asked_at``: the frozen
tree answers at the instant its own ``artifacts/question.yaml`` pins, and the
served contract's ``temporal_boundary`` is that instant. A question asked at
any other instant is REFUSED BY NAME with a replay record, never answered at
the pin and presented as if it were the caller's — the substitution a consumer's
admission would otherwise not catch (`CP05D-F-01` in ``FINDINGS.md``). The
wire's ``freshness`` and ``families`` are likewise not threaded (the specimen
never judged the first and uses the second as an acquisition-boundary label,
not a business input); both are disclosed, neither is refused.

Everything else — the request contract, the policy bounds, the tolerance
comparison, the reconciliation gate, the record on both branches — is behind
``produce_governed`` and this module does not touch it.
"""

from __future__ import annotations

import datetime as _dt
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from ccf.controlplane.artifacts import PRODUCT_CLASS, EgressDoorBinding, ProductClassDeclaration, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import EnvironmentDocument, load_environment_document
from ccf.products.refusal import GovernedRefusalRaised, RequestIdentity, envelope_for
from ccf.products.request import ProductRequest, ProductRequestViolation, refuse_request
from ccf.products.resolver import ProductNotResolvable, ReplayRefusalRecorder, ResolverOutcome
from ccf.projection.plan import Perspective
from ccf.replay.record import ResolutionNotApplicable
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource

HERE = Path(__file__).resolve().parent
#: The FROZEN specimen this door serves. Imported, never copied, never edited.
SPECIMEN = HERE.parent / "cp-05-credit-exposure-rollup"

#: The bare module names a product tree occupies. ANY two trees in one process
#: occupy exactly the same ones, which is why they are evicted rather than
#: assumed absent (`AIA-F-07`).
_COLLIDING = ("produce", "deployment", "projection", "acquisition", "assembler")


class WrongProductLoaded(ImportError):
    """This door loaded a module that does not live in the specimen it serves."""


def _specimen_modules() -> tuple[Any, Any]:
    """Import the frozen specimen's modules, and PROVE they are the specimen's.

    A product tree is imported by BARE MODULE NAME off ``sys.path``, and
    **Python resolves a bare name from ``sys.modules`` before it ever consults
    ``sys.path``** — so inserting :data:`SPECIMEN` does nothing at all when
    another tree's ``produce`` is already resident. This module is *imported*
    rather than run as ``__main__``, so a second tree frequently is.

    Measured 2026-09-22 on the release-hardening sweep, with
    ``cp-21-large-exposure`` resident: this door bound **cp-21's** ``produce``
    and would have served the large-exposure product through the exposure
    rollup's door. cp-21's producer defines ``product()`` too, so there was no
    ``AttributeError`` to catch it — the door would have answered, correctly
    shaped and entirely wrong. That is the dangerous half of `AIA-F-07`: a
    governance failure wearing a successful answer.

    So: evict, insert, import, **verify the file actually loaded lives in the
    specimen**, and restore whatever was displaced. A mismatch raises rather
    than binding, because a door that cannot prove which product it serves
    must not open.
    """
    saved = {name: sys.modules.pop(name, None) for name in _COLLIDING}
    sys.path.insert(0, str(SPECIMEN))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        for module in (produce, deployment):
            resolved = Path(module.__file__ or "").resolve().parent
            if resolved != SPECIMEN.resolve():
                raise WrongProductLoaded(
                    f"this door serves {SPECIMEN.name!r} and loaded"
                    f" `{module.__name__}` from {resolved}; a door that cannot"
                    " prove which product it serves must not open (`AIA-F-07`)"
                )
        return produce, deployment
    except BaseException:
        # Only on FAILURE is what was displaced put back. On success the
        # specimen STAYS resident and SPECIMEN stays on `sys.path`, and that
        # is deliberate: cp-05's own modules import their siblings lazily, so
        # unwinding here would leave this door bound to modules whose later
        # imports resolve somewhere else — measured 2026-09-22, when a
        # restoring version booted, announced READY, and then failed every
        # served question with `producer-unavailable`.
        #
        # The eviction above is what makes the VERIFICATION meaningful in a
        # poisoned process; keeping the result is what makes the door work.
        # This module is the last thing loaded in the door's process, and in
        # a test process it is the one binding that has proven what it holds.
        sys.path.remove(str(SPECIMEN))
        for name in _COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]
        raise


prod, dep = _specimen_modules()

#: This door's own identity document.
DOOR = HERE / "artifacts" / "door.yaml"


def _text(value: Any) -> str | None:
    """A number reaches `produce_governed` as text, never as a float."""
    return None if value is None else str(value)


class ExposureProducer:
    """The nine members `ServesProducts` names, held from what frozen cp-05 already holds."""

    def __init__(self, *, root: Path) -> None:
        self._config = dep.load(dep.CONFIG)
        self._contract = dep.request_contract(self._config)
        declaration = parse_artifact(
            {"semver": self._config["semver"], **self._config["product_class"]}, PRODUCT_CLASS
        )
        assert isinstance(declaration, ProductClassDeclaration)
        self._declaration = declaration
        perspective = self._config["default_perspective"]
        self._perspective = Perspective(principal_id=str(perspective["principal_id"]), role=str(perspective["role"]))
        # THE ONE CONTROL PLANE THE DOOR REGISTERS ITS ENTITLEMENT INTO. The
        # frozen tree boots its own registry per question and accepts none,
        # so this one governs the door's admission and the disclosure posture
        # of the refusals recorded HERE; in-resolver refusals keep the
        # specimen's minimal posture (`CP05D-F-03`).
        self._control_plane = ControlPlaneRegistry()
        self._entitlement_source = ControlPlaneProductEntitlementSource(
            control_plane=self._control_plane, clock=lambda: datetime.now(UTC)
        )
        door_document = dep.load(DOOR)
        door = EgressDoorBinding.model_validate({"semver": door_document["semver"], **door_document[dep.DECLARATION]})
        self._door = door
        self._environment = load_environment_document(HERE)
        # ONE store, ONE recorder — the specimen's own replay binding names
        # the class and the directory; every question's resolver files its
        # records under the same root (`replay_root`), and the two
        # pre-assembly refusals below are appended through this recorder.
        self._replay_root = root / "replay"
        store, _writer, _pins = dep.replay_writers(self._replay_root)
        self._recorder = ReplayRefusalRecorder(
            artifact_store=store,
            replay_record_class=dep.load(dep.REPLAY)[dep.DECLARATION]["record_class"],
            tenant_id=str(self._config["tenant_id"]),
            assembly_mode=self._config["product_class"]["assembly_mode"],
            disclosure_level_for=self._entitlement_source.disclosure_level_for,
        )
        question = dep.load(dep.QUESTION)[dep.DECLARATION]
        self._pinned_instant = _dt.datetime.fromisoformat(question["asked_at"])

    # -- the nine members --------------------------------------------------

    @property
    def tenant_id(self) -> str:
        return str(self._config["tenant_id"])

    @property
    def declaration(self) -> ProductClassDeclaration:
        return self._declaration

    @property
    def default_perspective(self) -> Perspective:
        return self._perspective

    @property
    def control_plane(self) -> ControlPlaneRegistry:
        return self._control_plane

    @property
    def refusal_recorder(self) -> ReplayRefusalRecorder:
        return self._recorder

    @property
    def door(self) -> EgressDoorBinding | None:
        return self._door

    @property
    def environment(self) -> EnvironmentDocument:
        return self._environment

    @property
    def entitlement_source(self) -> ControlPlaneProductEntitlementSource:
        """The source the door is opened with, so the recorder and the door read one posture."""
        return self._entitlement_source

    @property
    def pinned_instant(self) -> datetime:
        """The one instant the frozen tree answers at."""
        return self._pinned_instant

    def resolve(
        self, *, tenant: str, product_class: str, version: str, perspective: Perspective,
        request: ProductRequest | None,
    ) -> ResolverOutcome:
        """Translate the door's five arguments into the specimen's one call.

        Re-implements no part of the governed path: `produce_governed` boots,
        assembles, governs, records and delivers. What is left here is the
        wrong-address refusal and the resource surface's absent standing answer
        (the specimen's own door recorded both), the instant guard, and the
        translation of `ProductRequest.parameters` into keywords.
        """
        if tenant != self.tenant_id:
            raise ProductNotResolvable(
                f"this door serves tenant {self.tenant_id!r} and was asked as {tenant!r}"
            )
        declared = self._config["product_class"]
        identity = RequestIdentity(
            product_id=product_class, product_version=version,
            parameters={} if request is None else request.parameters,
            temporal_boundary=None if request is None else request.asked_at,
        )
        if (product_class, version) != (declared["schema_name"], str(declared["schema_version"])):
            violation = refuse_request(request=request, declared=self._contract) or self._violation(
                "not-supported-at-tier", key="schema_name", presented=f"{product_class}@{version}",
                declared_type=f"{declared['schema_name']}@{declared['schema_version']}", request=request,
                detail=(f"this door serves {declared['schema_name']!r} at lane"
                        f" {declared['schema_version']!r} and was addressed for"
                        f" {product_class!r} at lane {version!r}"),
            )
            return self._refused(envelope_for(violation, request=identity), perspective=perspective, request=request)
        if request is None:
            return self._refused(envelope_for(self._violation(
                "missing-required-parameter", key="lei", presented=None, declared_type="string", request=None,
                detail=(f"{declared['schema_name']} is parameterized — an exposure rollup is a"
                        " fact about a QUESTION asked at an instant, not a standing answer — so a"
                        " resource read carrying no request has no anchor, no intent and no"
                        " threshold to serve"),
            ), request=identity), perspective=perspective, request=None)
        if request.asked_at != self._pinned_instant:
            return self._refused(envelope_for(self._violation(
                "not-supported-at-tier", key="asked_at", presented=request.asked_at.isoformat(),
                declared_type=self._pinned_instant.isoformat(), request=request,
                detail=(f"this producer answers at its one recorded instant"
                        f" {self._pinned_instant.isoformat()} and was asked at"
                        f" {request.asked_at.isoformat()}; the frozen assembly takes no"
                        " instant, so the question is refused rather than answered at the"
                        " wrong one and presented as the caller's (CP05D-F-01)"),
            ), request=identity), perspective=perspective, request=request)
        supplied = dict(request.parameters)
        # `D-IMPL-304`, THE ADOPTION. The frozen tree resolves the effective
        # request BEFORE acquisition and, on a refusal, RAISES a ValueError that
        # drops the partial evidence — which every door reads as a runtime
        # failure. So this adapter runs the specimen's own resolution first,
        # through the specimen's own seam, and hands a refusal up as the typed
        # governed handoff WITH the evidence the SDK established, while it is
        # still available. On success the frozen spine resolves a second time
        # inside `produce_governed`; the duplication is deterministic (same
        # inputs, same seam) and is the measured cost of a wrapper over a
        # frozen spine (`CP05D-F-01`). Frozen cp-05 is not edited.
        outcome = self._resolution(request, supplied)
        if outcome.refusal is not None:
            raise GovernedRefusalRaised(outcome.refusal, resolution=outcome.evidence, request=identity)
        _payload, governed, _record = prod.produce_governed(
            anchor=request.subject, intent=request.intent,
            depth=supplied.get("depth"),
            materiality=_text(supplied.get("materiality")),
            debt_tolerance=_text(supplied.get("debt_tolerance")),
            basis=supplied.get("basis"),
            follow_guarantees=supplied.get("follow_guarantees"),
            follow_cross_default=supplied.get("follow_cross_default"),
            as_of=supplied.get("as_of"),
            replay_root=self._replay_root,
        )
        return governed

    def _resolution(self, request: ProductRequest, supplied: Mapping[str, Any]) -> Any:
        """The specimen's own effective-request resolution, through the specimen's own seam.

        Exactly what `produce_governed` does first (a scratch fabric for the
        registry the constraints are read from; the same supplied mapping, the
        family token from the pinned question), so the refusal this adapter
        hands up is the one the frozen spine would have raised, with the
        `ResolutionOutcome`'s evidence intact.
        """
        question = dep.load(dep.QUESTION)[dep.DECLARATION]
        with tempfile.TemporaryDirectory(prefix="cp05-door-resolution-") as scratch:
            fabric, registry = dep.boot(Path(scratch))
            try:
                _typed, outcome = dep.effective_request(
                    config=self._config,
                    registry=registry,
                    supplied={
                        "depth": supplied.get("depth"),
                        "materiality": _text(supplied.get("materiality")),
                        "follow_guarantees": supplied.get("follow_guarantees"),
                        "follow_cross_default": supplied.get("follow_cross_default"),
                        "basis": supplied.get("basis"),
                        "debt_tolerance": _text(supplied.get("debt_tolerance")),
                        "as_of": supplied.get("as_of"),
                        "families": [str(question["parameters"]["families"][0])],
                    },
                    subject=request.subject,
                    intent=request.intent,
                    freshness=str(question["freshness"]),
                    asked_at=self._pinned_instant,
                )
            finally:
                handle = getattr(fabric, "handle", None)
                if handle is not None:
                    handle.close()
        return outcome

    def _violation(
        self, reason: Any, *, key: str, presented: str | None, declared_type: str | None,
        request: ProductRequest | None, detail: str,
    ) -> ProductRequestViolation:
        """One request violation in the SDK's own shape, for the two refusals the door delegates."""
        return ProductRequestViolation(
            reason=reason, key=key, declared_type=declared_type,
            presented_type=None if presented is None else presented,
            declared_keys=frozenset(self._contract.arguments.properties),
            presented_keys=frozenset() if request is None else frozenset(request.parameters),
            detail=detail,
        )

    def _refused(self, envelope: Any, *, perspective: Perspective, request: ProductRequest | None) -> Any:
        """Record a pre-assembly refusal the same way an assembled one is recorded.

        Stamped with the QUESTION'S instant — the SDK's own pre-resolution
        refusals record `request.asked_at`, never the wall clock — so two
        identical refusals are one record and replay is bit-stable (close
        review, 2026-09-17). A resource read carries no instant; it is stamped
        at the frozen tree's pin, the only instant this producer answers at.
        """
        return self._recorder.record(
            envelope, perspective=perspective,
            recorded_at=self._pinned_instant if request is None else request.asked_at,
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
        )
