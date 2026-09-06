# 24.7 close-time panel — bundle-src-part-1.md

Subject: the SHIPPED tree of `phase-24.7` at `ad8dc5a9` (src/ and runtime/), diff base `6a019322`.
Read `prompt.md` for the instruction and `known-findings.md` for what NOT to re-derive.
Feed this file via STDIN, never as an argv string. Quote the line below verbatim in your review;
a review that does not quote it is recorded as a failed reviewer, not a reviewer.

```
READ-PROOF bundle-src-part-1.md: fb9dcf4996c221ae
```

Subjects in this part (2): `DIFFSTAT+DIFF src runtime`, `runtime/ccf_runtime/authz/delivery_boundary.py`

## git diff 6a019322..HEAD --stat -- src runtime

```
 runtime/ccf_runtime/authz/delivery_boundary.py |  17 +-
 src/ccf/products/constraints.py                | 168 ++++++--
 src/ccf/products/request.py                    | 531 +++++++++++++++++++++----
 src/ccf/products/request_schema.py             | 121 ++++++
 src/ccf/products/resolver.py                   | 118 +++++-
 src/ccf/replay/engine.py                       | 173 +++++++-
 src/ccf/replay/record.py                       | 146 ++++++-
 7 files changed, 1123 insertions(+), 151 deletions(-)
```

## git diff 6a019322..HEAD -- src runtime

```diff
diff --git a/runtime/ccf_runtime/authz/delivery_boundary.py b/runtime/ccf_runtime/authz/delivery_boundary.py
index be58586e..2383f341 100644
--- a/runtime/ccf_runtime/authz/delivery_boundary.py
+++ b/runtime/ccf_runtime/authz/delivery_boundary.py
@@ -72,7 +72,11 @@ from ccf.products.refusal import (
 )
 from ccf.products.resolver import RefusalRecorderProtocol
 from ccf.projection.plan import Perspective
-from ccf.replay.record import NO_ROLE_RESOLVED, PolicyBinding
+from ccf.replay.record import (
+    NO_ROLE_RESOLVED,
+    PolicyBinding,
+    ResolutionNotApplicable,
+)
 from ccf_runtime.authz.product_entitlement import (
     PerspectiveResolverProtocol,
     ProductEntitlementRefused,
@@ -310,6 +314,11 @@ def govern_absence(
         ),
         recorded_at=determined_at,
         policy_bindings=(),
+        # Dimension 2: the absence is decided at the door, before any
+        # resolver could run, and the record SAYS so with its reason — a
+        # positive absence stated by the door, never inferred by the seam
+        # from a keyword the door left out (`D-IMPL-264` D-09/D-10 am.1).
+        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
     )
 
 
@@ -484,6 +493,12 @@ def govern_entitlement(
                 role=refused.role if refused.role is not None else NO_ROLE_RESOLVED,
             ),
             recorded_at=determined_at,
+            # Dimension 2: entitlement is refused before resolution begins —
+            # the resolver never ran, so there is no resolution to record and
+            # the record says WHY there is none, in the `NO_ROLE_RESOLVED`
+            # voice: a positive absence the door states, never one the seam
+            # infers from silence (`D-IMPL-264` D-09/D-10 am.1).
+            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
             policy_bindings=(
                 (
                     PolicyBinding(
diff --git a/src/ccf/products/constraints.py b/src/ccf/products/constraints.py
index 1f300cf3..d42142e9 100644
--- a/src/ccf/products/constraints.py
+++ b/src/ccf/products/constraints.py
@@ -104,6 +104,7 @@ __all__ = [
     "PolicyConstraintResolver",
     "PolicyResolutionConflict",
     "ReferencePolicyConstraintResolver",
+    "ResolutionOutcome",
     "TechnicalCapability",
     "applicable",
     "constraints_in_force",
@@ -324,6 +325,61 @@ class PolicyResolutionConflict(CCFContract):
     )
 
 
+class ResolutionOutcome(CCFContract):
+    """One resolution's answer — completed request or governed refusal — with the evidence accumulated so far.
+
+    **SDK-defined, not whitepaper-derived (CLAUDE.md §11).** The ruling of
+    record is ``docs/DECISIONS.md`` **D-IMPL-264** D-08 (Dave, 2026-09-05,
+    ``24.7-RULINGS.md`` §3 Q8), verbatim: *"Return the refusal paired with the
+    partial resolution. Keep refusal vocabulary separate from resolution
+    provenance rather than cloning resolution fields into multiple refusal
+    classes. I would think of this as a common resolution outcome shape:
+    completed request or governed refusal, both with the resolution evidence
+    accumulated so far."* What the whitepaper commits to is the hook this
+    shape serves: §7.8 audits every plane decision against the Control Plane
+    that permitted it, and §7.10's five-dimension record is complete only when
+    dimension 2 carries what resolution established — including what it
+    established on the way to a refusal (D-07, Dave: *"'It failed before
+    producing an effective request' must not erase what resolution already
+    established."*).
+
+    **Two members, both required, and the two vocabularies stay apart.**
+    :attr:`evidence` is the :class:`~ccf.products.provenance.EffectiveRequest`
+    as it stood when the resolution exited — complete on success, partial on a
+    refusal — and it is the SAME type either way, so replay dimension 2 and
+    :attr:`~ccf.products.refusal.RefusalEnvelope.provenance` read one shape
+    whichever way the determination went. :attr:`refusal` is the governed
+    determination that stands instead of a completed request, or ``None``; the
+    three refusal classes gain no cloned resolution field, which is the half of
+    Q8 that keeps a refusal a refusal. Neither member is defaulted: the
+    completion says ``refusal=None`` out loud, on ``D-IMPL-264`` P-2's rule
+    that absence is stated and never inferred from omission.
+
+    Unlike :class:`~ccf.products.door.DoorOutcome`, which carries exactly one
+    of its halves, this shape ALWAYS carries the evidence: the resolution step
+    ran, so there is always something it established — at minimum the contract
+    pin it consulted. Pydantic's own validation is therefore the whole guard.
+
+    Attributes:
+        evidence: What resolution established before it exited — every
+            parameter resolved so far with ``(value, authority, source)`` and
+            any bound attached, the guidance folded so far, every override
+            attempt verified, and every source consulted.
+        refusal: The governed refusal, when the resolution did not complete;
+            ``None`` when :attr:`evidence` is the completed effective request.
+    """
+
+    evidence: EffectiveRequest
+    refusal: (
+        ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation | None
+    )
+
+    @property
+    def completed(self) -> bool:
+        """``True`` when the resolution produced an effective request."""
+        return self.refusal is None
+
+
 @dataclass(frozen=True)
 class _Candidate:
     """One folded hard bound, with the ordering keys priority resolves by.
@@ -694,6 +750,31 @@ def _with_overrides(
     return refusal.model_copy(update={"overrides": verified_overrides})
 
 
+def _evidence_so_far(
+    *,
+    effective: Mapping[str, EffectiveParameter],
+    guidance: Sequence[ParameterBound],
+    applied: set[ProvenanceSource],
+    verified_overrides: tuple[OverrideRecord, ...],
+    asked_at: datetime,
+) -> EffectiveRequest:
+    """The resolution as it stands at one exit, rendered the one way.
+
+    ``D-IMPL-264`` D-07/D-08. Called at every exit of
+    :func:`resolve_effective_request` — the five refusal exits and the one
+    completion — over the same locals, so a partial record and a completed one
+    are the same construction sorted the same way, and dimension 2 cannot
+    render one resolution as a family of blocks depending on where it exited.
+    """
+    return EffectiveRequest(
+        parameters=tuple(effective[name] for name in sorted(effective)),
+        guidance=tuple(sorted(guidance, key=_guidance_key)),
+        overrides=verified_overrides,
+        applied=tuple(sorted(applied, key=_sort_key)),
+        asked_at=asked_at,
+    )
+
+
 def resolve_effective_request(
     *,
     request: ProductRequest,
@@ -707,7 +788,7 @@ def resolve_effective_request(
     tenant: str,
     class_defaults: Mapping[str, Any] | None = None,
     class_source: ProvenanceSource | None = None,
-) -> EffectiveRequest | ConstraintRefusal | PolicyResolutionConflict | ProductRequestViolation:
+) -> ResolutionOutcome:
     """The one resolution: defaults, caller, policy, capability, validation.
 
     Whitepaper §7.8; SDK-defined per CLAUDE.md §11 (``D-IMPL-253`` Q4-Q8,
@@ -780,13 +861,18 @@ def resolve_effective_request(
             resolve later is worse than no default.
 
     Returns:
-        The :class:`~ccf.products.provenance.EffectiveRequest` — every
-        parameter carrying ``(value, authority, source)`` and its bound, even
-        when nothing constrained the request — or one of the three governed
-        determinations: a :class:`ConstraintRefusal`, a
-        :class:`PolicyResolutionConflict`, or the
-        :class:`~ccf.products.request.ProductRequestViolation` the existing
-        conformity comparison returns over the effective values.
+        A :class:`ResolutionOutcome` (``D-IMPL-264`` D-08). Its ``evidence``
+        is ALWAYS present — the
+        :class:`~ccf.products.provenance.EffectiveRequest` as it stood at the
+        exit, every parameter resolved so far carrying ``(value, authority,
+        source)`` and its bound, even when nothing constrained the request.
+        Its ``refusal`` is ``None`` when the resolution completed, or one of
+        the three governed determinations that stand instead: a
+        :class:`ConstraintRefusal`, a :class:`PolicyResolutionConflict`, or
+        the :class:`~ccf.products.request.ProductRequestViolation` the
+        existing conformity comparison returns over the effective values. A
+        refusal reached halfway through carries the half that ran (D-07):
+        *"that partial work is still governed truth and belongs in replay."*
 
     Raises:
         ValueError: ``class_defaults`` is non-empty and ``class_source`` is
@@ -923,16 +1009,32 @@ def resolve_effective_request(
         by_parameter.setdefault(pinned.constraint.parameter, []).append(pinned)
 
     guidance: list[ParameterBound] = []
+
+    def evidence_so_far() -> EffectiveRequest:
+        # What this resolution has established at the moment it is called —
+        # read off the accumulators as they stand, so a refusal three lines
+        # below carries exactly what was resolved above it (D-IMPL-264 D-07).
+        return _evidence_so_far(
+            effective=effective,
+            guidance=guidance,
+            applied=applied,
+            verified_overrides=verified_overrides,
+            asked_at=request.asked_at,
+        )
+
     for key in sorted(by_parameter):
         folded = _fold(key=key, pinned=by_parameter[key])
         if isinstance(folded, PolicyResolutionConflict):
-            return _with_overrides(folded, verified_overrides)
+            return ResolutionOutcome(
+                evidence=evidence_so_far(),
+                refusal=_with_overrides(folded, verified_overrides),
+            )
         candidates, parameter_guidance = folded
         guidance.extend(parameter_guidance)
 
         presence = [c for c in candidates if c.fold == _PRESENCE]
         if presence and key not in effective:
-            return ConstraintRefusal(
+            absent = ConstraintRefusal(
                 reason="required-absent",
                 key=key,
                 detail=(
@@ -944,6 +1046,7 @@ def resolve_effective_request(
                 requested=None,
                 overrides=verified_overrides,
             )
+            return ResolutionOutcome(evidence=evidence_so_far(), refusal=absent)
         if key not in effective:
             continue
 
@@ -971,7 +1074,10 @@ def resolve_effective_request(
                     bound=candidate.bound,
                 )
                 continue
-            return _with_overrides(refusal, verified_overrides)
+            return ResolutionOutcome(
+                evidence=evidence_so_far(),
+                refusal=_with_overrides(refusal, verified_overrides),
+            )
         if ordered and effective[key].bound is None:
             effective[key] = effective[key].model_copy(
                 update={"bound": ordered[0].bound}
@@ -1004,7 +1110,7 @@ def resolve_effective_request(
             continue
         presented = _as_number(effective[name].value)
         if presented is not None and presented > capability.maximum:
-            return ConstraintRefusal(
+            exceeded = ConstraintRefusal(
                 reason="bound-exceeded",
                 key=name,
                 detail=(
@@ -1018,6 +1124,7 @@ def resolve_effective_request(
                 requested=effective[name].value,
                 overrides=verified_overrides,
             )
+            return ResolutionOutcome(evidence=evidence_so_far(), refusal=exceeded)
         if effective[name].bound is None:
             effective[name] = effective[name].model_copy(
                 update={"bound": technical}
@@ -1030,14 +1137,17 @@ def resolve_effective_request(
         request=request.model_copy(update={"parameters": values}), declared=declared
     )
     if verdict is not None:
-        return _with_overrides(verdict, verified_overrides)
+        # The whole effective set was resolved; only conformity refused it.
+        return ResolutionOutcome(
+            evidence=evidence_so_far(),
+            refusal=_with_overrides(verdict, verified_overrides),
+        )
 
-    resolved = EffectiveRequest(
-        parameters=tuple(effective[name] for name in sorted(effective)),
-        guidance=tuple(sorted(guidance, key=_guidance_key)),
-        overrides=verified_overrides,
-        applied=tuple(sorted(applied, key=_sort_key)),
-        asked_at=request.asked_at,
+    resolved = ResolutionOutcome(
+        evidence=evidence_so_far(),
+        # Stated, not defaulted: the completion says there is no refusal
+        # rather than leaving absence to be inferred (D-IMPL-264 P-2).
+        refusal=None,
     )
     # D-IMPL-254: the Authority layer's value is the record, never a scalar
     return resolved
@@ -1246,12 +1356,7 @@ class PolicyConstraintResolver(Protocol):
         capabilities: tuple[TechnicalCapability, ...],
         class_defaults: Mapping[str, Any] | None = None,
         class_source: ProvenanceSource | None = None,
-    ) -> (
-        EffectiveRequest
-        | ConstraintRefusal
-        | PolicyResolutionConflict
-        | ProductRequestViolation
-    ):
+    ) -> ResolutionOutcome:
         """Resolve ``request`` into its effective values, or refuse it.
 
         The instant is ``request.asked_at`` and never a clock: a resolver that
@@ -1279,8 +1384,10 @@ class PolicyConstraintResolver(Protocol):
             class_source: The artifact pin ``class_defaults`` were read from.
 
         Returns:
-            The :class:`~ccf.products.provenance.EffectiveRequest`, or the
-            governed determination that stands instead of one.
+            The :class:`ResolutionOutcome` (``D-IMPL-264`` D-08): the completed
+            :class:`~ccf.products.provenance.EffectiveRequest`, or the governed
+            determination that stands instead of one — and, either way, the
+            evidence the resolution accumulated before it exited.
         """
         ...
 
@@ -1357,12 +1464,7 @@ class ReferencePolicyConstraintResolver:
         capabilities: tuple[TechnicalCapability, ...],
         class_defaults: Mapping[str, Any] | None = None,
         class_source: ProvenanceSource | None = None,
-    ) -> (
-        EffectiveRequest
-        | ConstraintRefusal
-        | PolicyResolutionConflict
-        | ProductRequestViolation
-    ):
+    ) -> ResolutionOutcome:
         """Read what is in force, verify the overrides, resolve. See the Protocol.
 
         Raises:
diff --git a/src/ccf/products/request.py b/src/ccf/products/request.py
index c51aa66b..88d2b618 100644
--- a/src/ccf/products/request.py
+++ b/src/ccf/products/request.py
@@ -108,7 +108,9 @@ from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
 from ccf.products.provenance import OverrideRecord
 from ccf.products.contract import (
     NO_REQUEST_CONTRACT,
+    NOT_DISCOVERABLE,
     ProductClassRegistrationError,
+    ProductDiscovery,
     ServeObligations,
 )
 
@@ -161,6 +163,7 @@ __all__ = [
     "ProductRequestContract",
     "ProductRequestViolation",
     "ProductRequestViolationReason",
+    "refuse_intent",
     "refuse_request",
     "refuse_request_contract_pin",
     "refuse_undeclared_class_default",
@@ -185,6 +188,12 @@ __all__ = [
 #: translate. The fourth has no payload analogue: a payload belongs to whatever
 #: product carried it, while a request is **addressed**, and a request handed
 #: to the wrong class's contract is a mis-delivery rather than a bad argument.
+#: The same token, at ``key="intent"``, is the verdict of :func:`refuse_intent`
+#: (``D-IMPL-264`` D-01): §6.3 makes intent an addressing token, and a class
+#: not registered to serve the intent is addressed to the wrong class in the
+#: same family as a lane mismatch. No tenth token was added for it — the
+#: vocabulary is fixed at nine (criterion 7) and ``key`` already reads *the
+#: field that disagreed* for this reason.
 #:
 #: The fifth, ``not-supported-at-tier``, is the Context Product Specification
 #: Standard's ``400 not_supported_at_tier`` (``references/Context_Product_Specification_Standard_v0-3.md``
@@ -206,6 +215,17 @@ __all__ = [
 #: is the one :class:`~ccf.products.contract.ServeObligations` holds the
 #: CLASS's declared default to (``24.5-L-14``, ``24.6-L-04``): the request
 #: boundary and the class boundary read the same interval.
+#:
+#: The seventh and eighth, ``below-minimum`` and ``above-maximum``, are the
+#: two ends of a numeric :class:`ArgumentDomain` (``D-IMPL-259``). The ninth,
+#: ``not-in-domain``, is the enumerated shape's one verdict (``D-IMPL-264``
+#: D-05, Dave: *"Wrong type and valid type/wrong value are materially
+#: different failures. The presented value can be named; disclosure controls
+#: whether the allowed set is exposed."*): a well-typed value that is not a
+#: member of the class's declared set. A wrong-typed value is still
+#: ``type-mismatch`` — the payload comparison runs first and this verdict
+#: never reaches it. Appended last, never inserted, so every older record's
+#: reason meets the same roster prefix.
 ProductRequestViolationReason = Literal[
     "undeclared-parameter",
     "missing-required-parameter",
@@ -215,6 +235,7 @@ ProductRequestViolationReason = Literal[
     "not-a-proportion",
     "below-minimum",
     "above-maximum",
+    "not-in-domain",
 ]
 
 #: How :func:`~ccf.products.payload.refuse_payload`'s reasons read on the
@@ -322,47 +343,90 @@ class ProductRequest(CCFContract):
 
 
 class ArgumentDomain(CCFContract):
-    """The valid domain of one declared numeric parameter — the seventh key.
+    """The valid domain of one declared parameter — the seventh key.
 
-    **SDK-defined** (CLAUDE.md §11); the ruling of record is ``D-IMPL-259``
+    **SDK-defined** (CLAUDE.md §11); the rulings of record are ``D-IMPL-259``
     (Dave, 2026-09-05): *"cp-04 ``max_depth`` has a declared request-contract
     minimum of 1 … Requests below 1 … are governed request-validity refusals
     returned as data; values 1–100 are valid and are never clamped."* And the
     scoping sentence that puts the type HERE rather than in the constraint
     layer: *"don't turn ``1`` into a Policy Constraint. It is simply the
-    parameter's valid domain."*
+    parameter's valid domain."* — and ``D-IMPL-264`` (Dave, 2026-09-05,
+    Q3/Q4/Q6), which gives the type its second shape. The whitepaper hook is
+    §6.3 **Addressability** (``docs/CCF_Whitepaper_1-2.md:1465``): the
+    request contract is the interface a caller queries by name, and a domain
+    is part of what that interface declares.
 
     **What this is and is not.** A domain is part of the *request contract*
-    — a statement of which numbers are meaningful questions of this class —
+    — a statement of which values are meaningful questions of this class —
     in the same register as ``type`` and ``required``. It is not a policy
     constraint (no artifact pin, no priority, no comparability fold, no
     authority — ``ccf.products.constraints`` never reads it) and it is not a
     technical capability (no substrate, no identity — the number a backend
     can walk is read off the backend through ``capability_bindings``). Both of
     those bound a request *after* it is well-formed; a domain says what
-    well-formed means for a number, so it is judged where ``type`` is judged,
+    well-formed means for a value, so it is judged where ``type`` is judged,
     by :func:`refuse_request`, and a value outside it is a
-    :class:`ProductRequestViolation` — ``below-minimum`` or ``above-maximum``
-    — returned as data, never a substituted number.
-
-    **Inclusive on both ends**, because a boundary a caller may ask for and a
-    boundary a caller may not are two different declarations and the shorter
-    one to write is the one the ruling used (*"values 1–100 are valid"*).
-    Either end may be absent; a domain naming neither is refused at
-    construction, because a domain that admits everything is not a
-    declaration but a key with nothing under it.
+    :class:`ProductRequestViolation` — ``below-minimum``, ``above-maximum``
+    or ``not-in-domain`` — returned as data, never a substituted value.
+
+    **Two shapes, exactly one of them** (``D-IMPL-264`` D-03, Dave: *"Exactly
+    one domain shape: numeric bounds or enumerated values. Non-empty,
+    duplicate-free … Neither shape is also invalid if ``ArgumentDomain`` is
+    present."*):
+
+    * **Numeric bounds** — ``minimum`` and/or ``maximum``, inclusive on both
+      ends, because a boundary a caller may ask for and a boundary a caller
+      may not are two different declarations and the shorter one to write is
+      the one the ruling used (*"values 1–100 are valid"*). Either end may
+      be absent.
+    * **An enumerated member set** — ``members``, the closed set of legal
+      values, over any supported primitive type (``D-IMPL-264`` D-06, Dave:
+      *"Any supported primitive type, with homogeneous members matching the
+      declared property type. Don't unnecessarily make this
+      string-specific."*). Homogeneity is by CLASS — string, numeric
+      (``int`` and :class:`~decimal.Decimal` together), boolean — and
+      ``bool`` is its own class, never a number, on :func:`_as_decimal`'s
+      reading.
+
+    A domain declaring both shapes, neither shape, an empty set, a duplicated
+    member or a heterogeneous set is refused at construction, naming the
+    defect: a domain that admits everything, or that no value could satisfy,
+    is not a declaration but a key with nothing under it.
+
+    **Membership is exact typed equality** (``D-IMPL-264`` D-04, Dave,
+    verbatim: *"Exact canonical match. No trimming, case folding, aliases, or
+    silent substitution. Canonicalization, if ever wanted, should be an
+    explicit mechanism upstream of domain validation."*). ``"AB"`` is not
+    ``"ab"``, ``" ab"`` is not ``"ab"``, ``True`` is not ``1`` and ``"1"`` is
+    not ``1``; within the numeric class ``Decimal("2")`` IS ``2``, because the
+    contract reads a number by its value and not by its Python type. Nothing
+    here trims, folds, aliases or substitutes — ``tests/products/
+    test_request_contract.py`` plants each of those in turn and watches the
+    membership tests red.
 
     Attributes:
         minimum: The smallest value a caller may ask for, or ``None`` when the
-            domain is unbounded below. Held as a :class:`~decimal.Decimal` for
-            the reason :class:`~ccf.products.contract.ServeObligations` holds
-            its tolerance as one: a float boundary that is not the number the
+            numeric domain is unbounded below (or the domain is enumerated).
+            Held as a :class:`~decimal.Decimal` for the reason
+            :class:`~ccf.products.contract.ServeObligations` holds its
+            tolerance as one: a float boundary that is not the number the
             author wrote is a boundary nobody declared.
-        maximum: The largest, or ``None`` when unbounded above. Declared
-            rarely in practice — a ceiling a backend imposes is a capability,
-            not a domain (``D-IMPL-253`` Q21) — but the type is symmetric so a
-            genuine domain ceiling (*"a percentage"*, *"a calendar month"*)
-            has a place to be declared rather than a policy to be faked.
+        maximum: The largest, or ``None``. Declared rarely in practice — a
+            ceiling a backend imposes is a capability, not a domain
+            (``D-IMPL-253`` Q21) — but the type is symmetric so a genuine
+            domain ceiling (*"a percentage"*, *"a calendar month"*) has a
+            place to be declared rather than a policy to be faked.
+        members: The closed set of legal values, or ``None`` when the domain
+            is numeric. Hash-transparent at ``None`` (``D-IMPL-243``): every
+            numeric domain written before the member set existed
+            canonicalizes byte-for-byte as it did, so no committed request
+            contract's content address moves. The schema render derives the
+            advertised ``enum`` from this field (``D-IMPL-264`` D-00, P-1:
+            *"the request contract is the authority for legal values; schemas
+            and discovery advertise that authority but never independently
+            define it"*), which is why the declaration is not itself named
+            ``enum``.
     """
 
     minimum: Decimal | None = Field(
@@ -371,16 +435,38 @@ class ArgumentDomain(CCFContract):
     maximum: Decimal | None = Field(
         default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
     )
+    members: tuple[str | int | bool | Decimal, ...] | None = Field(
+        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
+    )
 
     @model_validator(mode="after")
     def _at_least_one_end_and_in_order(self) -> "ArgumentDomain":
-        """Refuse an empty domain and an inverted one, by name."""
-        if self.minimum is None and self.maximum is None:
+        """Refuse a domain that is not exactly one well-formed shape, by name.
+
+        The name predates the second shape and is kept: the numeric half is
+        still *at least one end, in order*; the enumerated half is *a
+        non-empty, duplicate-free, homogeneous set*; and the shapes are
+        exclusive (``D-IMPL-264`` D-03/D-06 beside ``D-IMPL-259``).
+        """
+        numeric = self.minimum is not None or self.maximum is not None
+        if numeric and self.members is not None:
+            raise ValueError(
+                "an argument domain declares exactly one shape — numeric "
+                "bounds (minimum and/or maximum) OR an enumerated member set "
+                "(members) — and this one declares both; a value cannot be "
+                "held to a magnitude and to a closed set at once "
+                "(D-IMPL-264 D-03, D-IMPL-259)"
+            )
+        if not numeric and self.members is None:
             raise ValueError(
-                "an argument domain declares a minimum, a maximum or both; a "
-                "domain with neither admits every number and is a key with "
-                "nothing under it (D-IMPL-259)"
+                "an argument domain declares a minimum, a maximum or both, or "
+                "an enumerated member set; a domain with neither shape admits "
+                "every value and is a key with nothing under it "
+                "(D-IMPL-264 D-03, D-IMPL-259)"
             )
+        if self.members is not None:
+            _refuse_a_malformed_member_set(self.members)
+            return self
         for name, value in (("minimum", self.minimum), ("maximum", self.maximum)):
             if value is not None and not value.is_finite():
                 raise ValueError(
@@ -399,11 +485,29 @@ class ArgumentDomain(CCFContract):
             )
         return self
 
-    def refuses(self, value: Decimal) -> ProductRequestViolationReason | None:
-        """Which end ``value`` misses, or ``None`` when it lies inside."""
-        if self.minimum is not None and value < self.minimum:
+    def refuses(self, value: object) -> ProductRequestViolationReason | None:
+        """Which way ``value`` misses this domain, or ``None`` when it lies inside.
+
+        Numeric shape: the value's magnitude against the declared ends
+        (``below-minimum`` / ``above-maximum``); a value with no magnitude is
+        not judged here — the payload comparison names it ``type-mismatch``
+        first, and this step runs after (``24.5-L-13``). Enumerated shape:
+        exact typed equality against the member set (``not-in-domain``), on
+        the rule :func:`_is_member` states — the presented value's class must
+        be the set's class and the value must equal a member under that
+        class's own equality. *"No trimming, case folding, aliases, or silent
+        substitution"* (``D-IMPL-264`` D-04).
+        """
+        if self.members is not None:
+            if any(_is_member(value, member) for member in self.members):
+                return None
+            return "not-in-domain"
+        number = _as_decimal(value)
+        if number is None:
+            return None
+        if self.minimum is not None and number < self.minimum:
             return "below-minimum"
-        if self.maximum is not None and value > self.maximum:
+        if self.maximum is not None and number > self.maximum:
             return "above-maximum"
         return None
 
@@ -526,22 +630,65 @@ class ProductRequestContract(VersionedArtifact):
         default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
     )
 
+    @model_validator(mode="after")
+    def _intent_is_not_declared_as_an_argument(self) -> "ProductRequestContract":
+        """Refuse an ``intent`` property: a shadow of the top-level field.
+
+        ``D-IMPL-264`` D-01 (Dave, verbatim): *"`intent` is a top-level
+        request concept, not an ordinary argument. `ProductDiscovery.intents`
+        is the declaration of what the class serves. A duplicate
+        `arguments.properties.intent` is a shadow declaration and should fail
+        contract construction."* Every request carries
+        :attr:`ProductRequest.intent` as one of the four address axes (§6.3),
+        and what a class serves is declared once, on
+        :class:`~ccf.products.contract.ProductDiscovery`; a parameter of the
+        same name would be a second place to say it, judged by a different
+        rule (the payload comparison) from the one that judges the field
+        (:func:`refuse_intent`). Refused at construction — first, before any
+        other validator — so an author is told about the shadow before the
+        rest of the document is judged around it.
+
+        The comparison is against the ONE field name and nothing else — no
+        collection of reserved names lives in this module (the
+        ``_string_collection_constants`` guard in
+        ``tests/products/test_request_contract.py``).
+
+        Amendment 1 F-2: the frozen rungs cp-01 through cp-04 declare exactly
+        this shadow and fail here; they are evidence, read by the tests and
+        never edited (``D-IMPL-261``).
+        """
+        if "intent" in self.arguments.properties:
+            raise ValueError(
+                f"the request contract for {self.schema_name!r} at class lane "
+                f"{self.schema_version!r} declares 'intent' under "
+                "arguments.properties, which is a shadow of the top-level "
+                "request field ProductRequest.intent; what a class serves is "
+                "declared once, on ProductDiscovery.intents, and judged there "
+                "— remove the argument (D-IMPL-264 D-01, amendment 1 F-2)"
+            )
+        return self
+
     @model_validator(mode="after")
     def _every_domain_bounds_a_declared_number_the_default_respects(
         self,
     ) -> "ProductRequestContract":
         """Refuse a domain the class cannot hold a caller to, naming every offender.
 
-        Four ways a declared domain is not one (``D-IMPL-259``), checked
-        together on the defaults validator's precedent: a name the class never
-        declared; a name declared with a type that has no magnitude (a domain
-        over a string bounds nothing, and ``bool`` is not a number to this
-        contract); a name the class declares and **always refuses** (a domain
-        over an inert parameter describes questions the tier step never lets
-        through); and a declared default that lies outside the domain — the
-        class contradicting itself, which fails HERE, where the author can
-        still fix it, rather than in front of a caller who omitted the
-        parameter (``D-IMPL-258`` (5)'s rule, one key over).
+        Five ways a declared domain is not one (``D-IMPL-259``; ``D-IMPL-264``
+        D-03/D-06), checked together on the defaults validator's precedent: a
+        name the class never declared; a name declared with a type that has
+        no magnitude under a NUMERIC domain (bounds over a string bound
+        nothing, and ``bool`` is not a number to this contract); an
+        ENUMERATED domain whose members are typed against the declared
+        property (a string set over an integer, a number over a boolean —
+        *"homogeneous members matching the declared property type"*); a
+        name the class declares and **always refuses** (a domain over an
+        inert parameter describes questions the tier step never lets
+        through); and a declared default that lies outside the domain,
+        judged by the same :meth:`ArgumentDomain.refuses` the domain step
+        uses — the class contradicting itself, which fails HERE, where the
+        author can still fix it, rather than in front of a caller who
+        omitted the parameter (``D-IMPL-258`` (5)'s rule, one key over).
         """
         if not self.argument_domains:
             return self
@@ -558,32 +705,44 @@ class ProductRequestContract(VersionedArtifact):
         )
         unmeasurable = sorted(
             name
-            for name in self.argument_domains
+            for name, domain in self.argument_domains.items()
             if name in self.arguments.properties
+            and domain.members is None
             and not _has_magnitude(self.arguments.properties[name].type)
         )
+        mistyped = sorted(
+            f"{name} declares {self.arguments.properties[name].type} but "
+            f"enumerates {_member_class(domain.members[0])}"
+            for name, domain in self.argument_domains.items()
+            if name in self.arguments.properties
+            and domain.members is not None
+            and not _members_match_type(
+                domain.members, self.arguments.properties[name].type
+            )
+        )
         contradicted = sorted(
             name
             for name, domain in self.argument_domains.items()
             if name in self.defaults
             and name not in undeclared
             and name not in unmeasurable
-            and _as_decimal(self.defaults[name]) is not None
-            and domain.refuses(_as_decimal(self.defaults[name])) is not None  # type: ignore[arg-type]
+            and domain.refuses(self.defaults[name]) is not None
         )
-        if not (undeclared or inert or unmeasurable or contradicted):
+        if not (undeclared or inert or unmeasurable or mistyped or contradicted):
             return self
         raise ValueError(
             f"the request contract for {self.schema_name!r} at class lane "
             f"{self.schema_version!r} declares argument domains it cannot "
             f"hold a caller to: {undeclared} are not declared arguments, "
-            f"{unmeasurable} are declared with a type that has no magnitude "
-            f"(a domain bounds integer and number only), {inert} are "
-            f"declared and always refused, and {contradicted} carry a declared "
-            "default outside their own domain — a class that would refuse the "
-            "value it fills in for an omission contradicts itself, and that "
-            "fails at declaration rather than in front of a caller "
-            "(D-IMPL-259, D-IMPL-258 (5))"
+            f"{unmeasurable} are bounded numerically but declared with a type "
+            "that has no magnitude (numeric bounds hold integer and number "
+            f"only), {mistyped} are enumerated with members typed against the "
+            f"declared property (mistyped), {inert} are declared and always "
+            f"refused, and {contradicted} carry a declared default outside "
+            "their own domain — a class that would refuse the value it fills "
+            "in for an omission contradicts itself, and that fails at "
+            "declaration rather than in front of a caller "
+            "(D-IMPL-259, D-IMPL-264 D-03/D-06, D-IMPL-258 (5))"
         )
 
     @model_validator(mode="after")
@@ -937,6 +1096,119 @@ def _as_decimal(value: object) -> Decimal | None:
     return Decimal(value)
 
 
+def _member_class(value: object) -> str | None:
+    """Which of the three member classes ``value`` belongs to, or ``None``.
+
+    ``boolean`` is read FIRST, because ``bool`` is an ``int`` to Python and
+    not to this contract — the discipline :func:`_as_decimal` and
+    :func:`_refuse_tolerance` already hold. ``int`` and
+    :class:`~decimal.Decimal` are one ``numeric`` class, ``str`` is
+    ``string``. Spelled as a function rather than a module-level table for the
+    reason :func:`_has_magnitude` gives: this module's own guard refuses any
+    module-level collection of string literals (``D-IMPL-264`` D-06).
+    """
+    if isinstance(value, bool):
+        return "boolean"
+    if isinstance(value, (int, Decimal)):
+        return "numeric"
+    if isinstance(value, str):
+        return "string"
+    return None
+
+
+def _members_match_type(
+    members: tuple[str | int | bool | Decimal, ...], type_name: str
+) -> bool:
+    """Do these (homogeneous) members match the declared JSON Schema type?
+
+    ``string`` takes the string class; ``boolean`` the boolean class;
+    ``number`` the numeric class; ``integer`` the numeric class with every
+    member an ``int`` (a ``Decimal("1.5")`` is a number, not an integer).
+    ``array`` and ``object`` take no enumerated domain at all — a member set
+    is a set of primitives (``D-IMPL-264`` D-06). Spelled as a function, not
+    a table, for the reason :func:`_has_magnitude` gives.
+    """
+    member_class = _member_class(members[0])
+    if type_name == "string":
+        return member_class == "string"
+    if type_name == "boolean":
+        return member_class == "boolean"
+    if type_name == "number":
+        return member_class == "numeric"
+    if type_name == "integer":
+        return member_class == "numeric" and all(
+            isinstance(member, int) for member in members
+        )
+    return False
+
+
+def _is_member(value: object, member: object) -> bool:
+    """Is ``value`` exactly ``member``, under that member's class equality?
+
+    The ONE membership judgment (``D-IMPL-264`` D-04, Dave: *"Exact canonical
+    match. No trimming, case folding, aliases, or silent substitution."*),
+    called by :meth:`ArgumentDomain.refuses` and, through it, by the domain
+    step and the contract validator, so a default and a caller's value are
+    judged by one rule. Class first, then value: a string is compared as the
+    untouched ``str``; a boolean by identity; a number by
+    :func:`_as_decimal` value, so ``Decimal("2")`` is ``2`` while ``True``
+    is never ``1`` and ``"1"`` is never ``1``.
+    """
+    member_class = _member_class(member)
+    if member_class is None or _member_class(value) != member_class:
+        return False
+    if member_class == "numeric":
+        return _as_decimal(value) == _as_decimal(member)
+    if member_class == "boolean":
+        return value is member
+    return value == member
+
+
+def _refuse_a_malformed_member_set(
+    members: tuple[str | int | bool | Decimal, ...],
+) -> None:
+    """Empty, non-finite, heterogeneous or duplicated — named, in that order.
+
+    The enumerated half of :meth:`ArgumentDomain._at_least_one_end_and_in_order`
+    (``D-IMPL-264`` D-03/D-06). Duplication is judged by :func:`_is_member`
+    itself, so ``1`` and ``Decimal("1")`` ARE duplicates while ``1`` and
+    ``True`` are a heterogeneous pair, refused one check earlier.
+    """
+    if not members:
+        raise ValueError(
+            "an enumerated argument domain declares a non-empty member set; "
+            "an empty set admits no value and is a key with nothing under it "
+            "(D-IMPL-264 D-03, D-IMPL-259)"
+        )
+    for member in members:
+        number = _as_decimal(member)
+        if number is not None and not number.is_finite():
+            raise ValueError(
+                "an enumerated argument domain's members must be finite "
+                f"numbers, not {member!r} (D-IMPL-264 D-06, D-IMPL-259)"
+            )
+    classes = sorted({str(_member_class(member)) for member in members})
+    if len(classes) != 1:
+        raise ValueError(
+            "an enumerated argument domain's members are homogeneous — one "
+            "class for the whole set, and bool is its own class — but this "
+            f"set mixes {classes} (D-IMPL-264 D-06, D-IMPL-259)"
+        )
+    duplicated = sorted(
+        {
+            repr(later)
+            for index, later in enumerate(members)
+            if any(_is_member(later, earlier) for earlier in members[:index])
+        }
+    )
+    if duplicated:
+        raise ValueError(
+            "an enumerated argument domain's members are duplicate-free, "
+            f"judged by the membership rule itself; {duplicated} appear more "
+            "than once (D-IMPL-264 D-03, D-IMPL-259)"
+        )
+
+
 #: The three keys a request-contract declaration carries, in the order
 #: :meth:`ProductRequestContract.from_declared` reports them missing. They are
 #: this class's own field names rather than a second vocabulary — the envelope
@@ -987,7 +1259,7 @@ class ProductRequestViolation(CCFContract):
     re-derives either to learn what the gap was.
 
     Attributes:
-        reason: Which of the eight ways the request missed.
+        reason: Which of the nine ways the request missed.
         key: Where. A parameter reads by name, a nested member reads
             ``parent.member`` and an element of a declared list reads
             ``parent[].member``; a class mismatch reads the field that
@@ -1014,7 +1286,18 @@ class ProductRequestViolation(CCFContract):
             sentence sees what the declaration said. For a proportion refusal
             it carries the parameter name, the presented value and the
             interval, so a caller reads which number missed and what it had
-            to be.
+            to be. For a ``not-in-domain`` refusal it carries the parameter
+            name, the presented value and the sorted member set — and the
+            allowed set travels ONLY here, never as a typed member, so
+            :data:`~ccf.products.disclosure.PERMITTED_AT_MINIMAL` decides its
+            exposure without a new row (``D-IMPL-264`` D-05, the disclosure
+            channel); advertising the set to a caller BEFORE the request is
+            the other channel, the canonical contract render (D-02), and is
+            not a refusal's business. For an intent refusal
+            (:func:`refuse_intent`, ``class-mismatch`` at ``key="intent"``)
+            it carries the presented intent and the sorted declared set on
+            exactly the same rule — the set ONLY here, never in
+            ``declared_type`` (``D-IMPL-264`` amendment 3 A-8 a).
         overrides: Every override the request attempted, with its entitlement
             result, when this violation was reached by
             :func:`~ccf.products.constraints.resolve_effective_request` —
@@ -1222,36 +1505,62 @@ def _refuse_tolerance(
 def _refuse_domain(
     *, request: ProductRequest, declared: ProductRequestContract
 ) -> ProductRequestViolation | None:
-    """Does every presented number lie inside its declared domain?
-
-    The domain step (``D-IMPL-259``). Runs LAST, after the payload comparison
-    has said each parameter is declared, honored and well-typed and after the
-    interval step has judged the tolerance, so this function only ever judges
-    a declared number's magnitude against the class's own declaration of what
-    numbers are meaningful. Names are read in sorted order so the first
-    verdict is the same verdict on every run — the replay property every
-    comparison in this package carries.
+    """Does every presented value lie inside its declared domain?
+
+    The domain step (``D-IMPL-259``, ``D-IMPL-264`` D-04/D-05). Runs LAST,
+    after the payload comparison has said each parameter is declared, honored
+    and well-typed and after the interval step has judged the tolerance, so
+    this function only ever judges a well-typed value against the class's
+    own declaration of what values are meaningful: a number's magnitude
+    against a numeric domain, or a value's exact typed membership in an
+    enumerated one. Names are read in sorted order so the first verdict is
+    the same verdict on every run — the replay property every comparison in
+    this package carries.
+
+    The one membership judgment is :meth:`ArgumentDomain.refuses`, which the
+    contract validator also calls over a declared default, so a caller's
+    value and a default are judged by one rule. A presented value with no
+    magnitude under a numeric domain is not judged here (the payload
+    comparison named it first); an enumerated domain receives the presented
+    value as it is — untrimmed, unfolded, unaliased (D-04).
 
     Nothing here clamps and nothing here reads a policy or a capability: a
-    value below the floor is refused with the floor named, exactly as a
-    caller's value above a technical capability is refused by
-    :mod:`ccf.products.constraints` with the capability named — two
-    boundaries, two vocabularies, one posture (*"never clamped"*).
+    value below the floor is refused with the floor named, a value outside
+    the set is refused with the set named, exactly as a caller's value above
+    a technical capability is refused by :mod:`ccf.products.constraints`
+    with the capability named — two boundaries, two vocabularies, one
+    posture (*"never clamped"*).
     """
     for key in sorted(declared.argument_domains):
         if key not in request.parameters:
             continue
         presented = request.parameters[key]
-        value = _as_decimal(presented)
-        if value is None:
-            continue
         domain = declared.argument_domains[key]
-        reason = domain.refuses(value)
+        reason = domain.refuses(presented)
         if reason is None:
             continue
-        limit = domain.minimum if reason == "below-minimum" else domain.maximum
-        edge = "below the declared minimum" if reason == "below-minimum" else "above the declared maximum"
         property_ = declared.arguments.properties.get(key)
+        if reason == "not-in-domain":
+            members = ", ".join(repr(member) for member in sorted(domain.members or ()))
+            detail = (
+                f"{key}: {presented!r} is not a member of this class's "
+                f"declared domain [{members}] — the parameter's legal values, "
+                "declared beside its type and judged by exact typed equality, "
+                "refused by name rather than substituted (D-IMPL-264 D-04/D-05)"
+            )
+        else:
+            limit = domain.minimum if reason == "below-minimum" else domain.maximum
+            edge = (
+                "below the declared minimum"
+                if reason == "below-minimum"
+                else "above the declared maximum"
+            )
+            detail = (
+                f"{key}: {presented} lies {edge} {limit} of this class's "
+                "request contract — the parameter's valid domain, declared "
+                "beside its type and refused by name rather than substituted "
+                "(D-IMPL-259)"
+            )
         return ProductRequestViolation(
             reason=reason,
             key=key,
@@ -1259,12 +1568,7 @@ def _refuse_domain(
             presented_type=type(presented).__name__,
             declared_keys=frozenset(declared.arguments.properties),
             presented_keys=frozenset(request.parameters),
-            detail=(
-                f"{key}: {presented} lies {edge} {limit} of this class's "
-                "request contract — the parameter's valid domain, declared "
-                "beside its type and refused by name rather than substituted "
-                "(D-IMPL-259)"
-            ),
+            detail=detail,
         )
     return None
 
@@ -1358,6 +1662,75 @@ def refuse_request(
     return _refuse_domain(request=request, declared=declared)
 
 
+def refuse_intent(
+    *, request: ProductRequest, discovery: ProductDiscovery
+) -> ProductRequestViolation | None:
+    """Is this request's intent one the class is registered to serve?
+
+    ``D-IMPL-264`` D-01 as amended by amendment 1 (F-1 a). Dave, verbatim:
+    *"Absence of a discovery declaration is non-applicability. Presence of a
+    discovery declaration makes its intent set authoritative, including an
+    explicitly empty set."* The whitepaper hook is §6.3: intent is one of the
+    axes a caller addresses a product by, and the registry entry a class
+    publishes is what says which intents it answers.
+
+    Three states, and the first is not the third:
+
+    * ``discovery == NOT_DISCOVERABLE`` — **no declaration exists**, and the
+      intent is **unjudged**: ``None``, whatever the intent. The sentinel is
+      the positive assertion *this class is reached by direct reference*,
+      not a statement that it serves zero intents; every class shipped
+      before this phase is in that state and serves exactly as it did. The
+      comparison is by equality with the sentinel, so a deployment that
+      writes the sentinel's exact content has written the not-discoverable
+      state and is read as such.
+    * declared, and ``request.intent in discovery.intents`` — ``None``.
+    * declared, and not a member — a :class:`ProductRequestViolation`
+      returned as data (``D-IMPL-251``): ``class-mismatch`` at
+      ``key="intent"``, because §6.3 makes intent an addressing token and a
+      class not registered to serve it is addressed to the wrong class, in
+      the same family as a lane mismatch. A declared **empty** set refuses
+      every intent — *"an explicitly declared empty set means 'serves
+      none'"* — which is the state the sentinel is NOT.
+
+    Membership is exact (D-04's rule, one field over): ``"A"`` is not
+    ``"a"`` and ``" a"`` is not ``"a"``; nothing trims, folds or aliases.
+
+    The declared set rides in ``detail`` ONLY — never in ``declared_type``,
+    which :data:`~ccf.products.disclosure.PERMITTED_AT_MINIMAL` lets cross —
+    so a refusal shell reveals it according to the disclosure level, exactly
+    as the enumerated argument domain's members do (``D-IMPL-264`` amendment
+    3 A-8 a, Dave: *"a refusal shell reveals it only according to the
+    disclosure level"*). Advertising the set BEFORE the request is the
+    canonical discovery representation's business, not a refusal's.
+
+    A sibling of :func:`refuse_request`, not a step inside it: that function
+    sees the request and the contract only, and the declaration that carries
+    ``discovery`` is in scope where the class is resolved
+    (:meth:`ccf.products.resolver.GovernedResolver.resolve`), which hosts
+    this judgment beside its address check. Direct validators that never
+    hold a declaration never judge intent — consistent with D-09.
+    """
+    if discovery == NOT_DISCOVERABLE:
+        return None
+    if request.intent in discovery.intents:
+        return None
+    return ProductRequestViolation(
+        reason="class-mismatch",
+        key="intent",
+        declared_type=None,
+        presented_type=request.intent,
+        declared_keys=frozenset(),
+        presented_keys=frozenset(),
+        detail=(
+            f"this request is addressed with intent {request.intent!r} and the"
+            f" class it names is registered to serve {sorted(discovery.intents)};"
+            " a declared intent set is authoritative and an explicitly empty one"
+            " serves none (D-IMPL-264 D-01, amendment 1 F-1 a; whitepaper §6.3)"
+        ),
+    )
+
+
 def request_seeds(request: ProductRequest | None) -> frozenset[str] | None:
     """The walk starting points a question implies — its subject, and nothing else.
 
diff --git a/src/ccf/products/request_schema.py b/src/ccf/products/request_schema.py
new file mode 100644
index 00000000..1eac218c
--- /dev/null
+++ b/src/ccf/products/request_schema.py
@@ -0,0 +1,121 @@
+"""The canonical rendering of a request contract's argument schema.
+
+**SDK-defined, not whitepaper-derived** (CLAUDE.md §11). The rulings of record
+are ``D-IMPL-264`` D-00, D-02 as refined by amendment 1 (F-5 d), and
+principle P-1 (Dave, 2026-09-05). The whitepaper hook is §6.3
+**Addressability**: a product class exposes an interface a caller queries by
+name, and what that interface accepts is part of what it declares.
+
+**One declaration of record** (D-00). A closed set of legal values, or a
+numeric domain, is declared in exactly one place —
+:attr:`ccf.products.request.ProductRequestContract.argument_domains`, as an
+:class:`~ccf.products.request.ArgumentDomain` — and this module DERIVES the
+advertised ``enum`` and ``minimum`` / ``maximum`` from it. P-1, Dave
+verbatim: *"The request contract is the authority for legal values; schemas
+and discovery advertise that authority but never independently define it."*
+That is why the render is a function over the contract and not a field on
+the schema type: :class:`~ccf.skills.catalog.SkillArgumentProperty` has no
+``enum`` (it is ``extra=forbid``), so no declaration can plant one — and if
+the base render ever carried one anyway, :func:`render_request_input_schema`
+refuses it rather than merging two declarations that could disagree.
+
+**Representation without delivery** (D-02 amendment 1, F-5 d). Dave, verbatim:
+*"The legal set is intrinsically advertisable contract truth and must have a
+canonical SDK rendering. 24.7 does not invent the Experience Layer surface on
+which that rendering is published."* And: *"Do not create a new MCP or HTTP
+publication surface in 24.7."* **This module publishes nothing.** No MCP
+tool or resource, no HTTP route and no CLI verb serves the render, and no
+module in ``src/`` or ``runtime/`` consumes it. On which Experience Layer
+surface a caller learns the valid vocabulary before asking is carry row
+``24.7-C-01`` — the ``D-IMPL-22`` / ``D-IMPL-23`` class of question
+(CLAUDE.md §8.3), deferred by ruling and not this module's.
+
+**One parameter, deliberately.** The render takes the contract and nothing
+else. D-02, Dave: *"A caller should be able to know the valid vocabulary
+before making the request."* Request validity is not a per-caller matter, so
+there is no consumer-side conditioning input here; a second parameter would
+be exactly the place such a dependence would be introduced, and
+``tests/products/test_request_schema_render.py`` pins the signature to one.
+
+Algorithmic module (CINV-03).
+"""
+
+from __future__ import annotations
+
+from decimal import Decimal
+from typing import Any
+
+from ccf.products.request import ArgumentDomain, ProductRequestContract
+
+__ccf_mode__ = "algorithmic"
+
+__all__ = ["render_request_input_schema"]
+
+
+def render_request_input_schema(contract: ProductRequestContract) -> dict[str, Any]:
+    """Render ``contract``'s argument schema with its declared domains derived in.
+
+    Composes :meth:`ccf.skills.catalog.SkillArgumentSchema.to_input_schema`
+    over ``contract.arguments`` and then, for each declared
+    :class:`~ccf.products.request.ArgumentDomain`, sets exactly one of two
+    things on that parameter's property: ``enum`` (the enumerated shape,
+    members in declared order) or ``minimum`` and/or ``maximum`` (the
+    numeric shape, an absent end not emitted). Pure and total over the
+    contract; nothing is authored. A contract with no domains renders
+    byte-identically to ``to_input_schema()`` alone.
+
+    Numbers are rendered in the JSON-legal form nearest the author's intent:
+    an integral :class:`~decimal.Decimal` becomes an ``int`` and any other
+    becomes a ``float``. ``bool`` members stay ``bool`` (the enumerated shape
+    reads ``bool`` first — :func:`ccf.products.request._member_class`).
+
+    Raises:
+        ValueError: the base render already carries ``enum``, ``minimum`` or
+            ``maximum`` on any property. That is a second declaration of
+            legal values outside the one declaration of record (D-00, P-1),
+            and it is refused by name — on a domained property because it
+            would compete with the declaration, on any other because it
+            would BE a declaration the contract never made.
+    """
+    rendered = contract.arguments.to_input_schema()
+    properties: dict[str, Any] = rendered["properties"]
+    _refuse_a_second_declaration(properties)
+    for name, domain in contract.argument_domains.items():
+        properties[name].update(_derived_keys(domain))
+    return rendered
+
+
+def _refuse_a_second_declaration(properties: dict[str, Any]) -> None:
+    """The base render is not a declaration surface for legal values."""
+    for name, spec in properties.items():
+        planted = [key for key in ("enum", "minimum", "maximum") if key in spec]
+        if planted:
+            raise ValueError(
+                f"the argument schema's own render carries {planted} on "
+                f"parameter {name!r}; the legal values of a parameter have one "
+                "declaration of record — ArgumentDomain on the request "
+                "contract — and this render derives from it rather than "
+                "merging a second declaration that could disagree "
+                "(D-IMPL-264 D-00, P-1)"
+            )
+
+
+def _derived_keys(domain: ArgumentDomain) -> dict[str, Any]:
+    """What one domain contributes to its parameter's rendered property."""
+    if domain.members is not None:
+        return {"enum": [_render_value(member) for member in domain.members]}
+    derived: dict[str, Any] = {}
+    if domain.minimum is not None:
+        derived["minimum"] = _render_value(domain.minimum)
+    if domain.maximum is not None:
+        derived["maximum"] = _render_value(domain.maximum)
+    return derived
+
+
+def _render_value(value: str | int | bool | Decimal) -> str | int | bool | float:
+    """One declared value in JSON-legal form; only a Decimal is translated."""
+    if isinstance(value, Decimal):
+        if value == value.to_integral_value():
+            return int(value)
+        return float(value)
+    return value
diff --git a/src/ccf/products/resolver.py b/src/ccf/products/resolver.py
index 2ae5aa70..f23886f9 100644
--- a/src/ccf/products/resolver.py
+++ b/src/ccf/products/resolver.py
@@ -183,9 +183,7 @@ from ccf.products.debt_scorer import (
 )
 from ccf.products.constraints import (
     CAPABILITY_TRAVERSAL_DEPTH,
-    ConstraintRefusal,
     PolicyConstraintResolver,
-    PolicyResolutionConflict,
     ReferencePolicyConstraintResolver,
     TechnicalCapability,
     _ConstraintSource,
@@ -215,12 +213,16 @@ from ccf.products.refusal import (
 from ccf.products.request import (
     ProductRequest,
     ProductRequestContract,
-    ProductRequestViolation,
+    refuse_intent,
     refuse_undeclared_class_default,
 )
 from ccf.projection.engine import ExecutionResult, ProjectionEngine
 from ccf.projection.plan import Perspective, ProjectionPlan
-from ccf.replay.record import PolicyBinding, build_replay_record
+from ccf.replay.record import (
+    PolicyBinding,
+    ResolutionNotApplicable,
+    build_replay_record,
+)
 from ccf.replay.serve import (
     QueryPinWriter,
     ReplayWriter,
@@ -561,7 +563,7 @@ class RefusalRecorderProtocol(Protocol):
         policy_bindings: tuple[PolicyBinding, ...] = (),
         assembler_id: str | None = None,
         assembler_version: str | None = None,
-        resolution: EffectiveRequest | None = None,
+        resolution: EffectiveRequest | ResolutionNotApplicable,
     ) -> RefusalEnvelope:
         """Append ``envelope``'s decision record, then return it with its address.
 
@@ -612,8 +614,20 @@ class RefusalRecorderProtocol(Protocol):
                 recorder was constructed with.
             assembler_id: The assembler in force, and ``assembler_version`` its
                 lane — dimension 4 (``D-IMPL-253`` Q16).
-            resolution: The Authority layer's record, when the question reached
-                that layer — dimension 2 (``D-IMPL-253`` Q1/Q6).
+            resolution: The resolution state — dimension 2 (``D-IMPL-253``
+                Q1/Q6; ``D-IMPL-264`` D-10). REQUIRED, with no default, as of
+                24.7-04: the
+                :class:`~ccf.products.provenance.EffectiveRequest` the
+                Authority layer produced — complete, or the partial record it
+                established before refusing (D-07) — or a
+                :class:`~ccf.replay.record.ResolutionNotApplicable` marker
+                stating, with its reason, that no resolution applies (D-09).
+                A caller that ran no resolver says so; this seam never says
+                it on the caller's behalf. ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
+        constructs or delegates construction of a replay record must require
+        an explicit resolution state: effective/partial resolution or explicit
+        not-applicable marker. No intermediate layer may manufacture the
+        marker from omission."*
 
         Returns:
             The same envelope with its
@@ -801,11 +815,18 @@ class ReplayRefusalRecorder:
         policy_bindings: tuple[PolicyBinding, ...] = (),
         assembler_id: str | None = None,
         assembler_version: str | None = None,
-        resolution: EffectiveRequest | None = None,
+        resolution: EffectiveRequest | ResolutionNotApplicable,
     ) -> RefusalEnvelope:
         """Disclose, append the INTERNAL truth, then hand back the shell.
 
         See :meth:`RefusalRecorderProtocol.record` for the argument contract.
+        ``resolution`` is passed through to the builder exactly as received
+        and is required here for the reason it is required there
+        (24.7-04; ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
+        constructs or delegates construction of a replay record must require
+        an explicit resolution state: effective/partial resolution or explicit
+        not-applicable marker. No intermediate layer may manufacture the
+        marker from omission."*).
 
         **The order is the architecture** (``D-IMPL-254``). The record is built
         from the **internal** envelope — the determination as the fabric
@@ -1257,12 +1278,51 @@ class GovernedResolver:
             temporal_boundary=request.asked_at,
         )
 
+        # 24.7-07: is this class registered to serve the intent the request is
+        # addressed with? An ADDRESSING verdict, and it precedes resolution for
+        # the reason `_refuse_address` states for the lane check: judging the
+        # parameters of a request for a class that does not serve its intent
+        # is a confident verdict about the wrong question. Judged HERE, where
+        # the declaration that carries `discovery` is in scope, and not inside
+        # `refuse_request`, which never sees it — so direct validators that
+        # hold no declaration never judge intent (D-09). Three states
+        # (`D-IMPL-264` D-01 as amended, F-1 a): no declaration
+        # (`NOT_DISCOVERABLE`) → unjudged, every existing deployment serves
+        # as it did; declared and a member → serves; declared and not a member
+        # — including a declared EMPTY set — → refused as data.
+        violation = refuse_intent(request=request, discovery=declaration.discovery)
+        if violation is not None:
+            # No resolution ran, and the record says so positively rather than
+            # by omission (D-09/D-10, P-2). What DID decide this outcome is the
+            # class's declared intent set, so the deciding declaration IS
+            # pinned — minted the way `class_source` mints it below, so the pin
+            # resolves to the exact bytes that declared the set (`D-IMPL-264`
+            # amendment 3 B-3 a, Dave: *"The refusal was decided by the class's
+            # declared intent set, so replay should preserve the declaration
+            # that actually governed the outcome"*). No request contract and no
+            # constraint is pinned, because none was resolved against — which
+            # is what lets replay read *request-contract pin + applicable
+            # constraint pins* as the evidence that resolution ran, and never
+            # a class-declaration pin (D-11 as narrowed by the same amendment).
+            return self._record_refusal(
+                envelope=envelope_for(violation, request=identity),
+                execution=None,
+                request=request,
+                perspective=perspective,
+                policy_bindings=(
+                    PolicyBinding(
+                        key=self.product_class_key, version=content_hash(declaration)
+                    ),
+                ),
+                resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
+            )
+
         # THE DOOR, and this composition is the resolver standing at it. The
         # comparison the two shipped doors cannot make, because neither holds
         # the registered class it compares against (`D-IMPL-121`) — and, as of
         # `24.6-03`, the Control Plane read no door could make either.
         declared = self._request_contract(declaration)
-        resolved = self.constraint_resolver.resolve(
+        outcome = self.constraint_resolver.resolve(
             product_class=product_class,
             request=request,
             declared=declared,
@@ -1296,26 +1356,37 @@ class GovernedResolver:
                 version=content_hash(declaration),
             ),
         )
-        if isinstance(
-            resolved,
-            (ConstraintRefusal, PolicyResolutionConflict, ProductRequestViolation),
-        ):
+        if outcome.refusal is not None:
             # No lineage: every one of these is reached while the effective
             # request is still being built, which is strictly before the graph
             # is touched. `envelope_for` refuses a lineage here, which is what
             # makes the assembly-boundary split structural.
             #
             # 24.6-07: and no execution, so dimension 1 says positively that
-            # nothing was read. The bundle pin is the recorder's; nothing else
-            # governed this, because the resolution that would have produced
-            # the pins is what failed.
+            # nothing was read. The bundle pin is the recorder's. What DID
+            # govern this is the resolution that ran up to the refusal —
+            # defaults applied, the constraints in force folded, capabilities
+            # consulted — and that partial work is governed truth. It rides on
+            # dimension 2 with the pins it was resolved from, exactly as a
+            # completed resolution does on the two post-assembly branches
+            # below (`D-IMPL-264` D-07, Dave: *"'It failed before producing
+            # an effective request' must not erase what resolution already
+            # established."*). The shell carries the same partial record as
+            # its `provenance`, so the record and the shell cannot disagree.
             return self._record_refusal(
-                envelope=envelope_for(resolved, request=identity),
+                envelope=envelope_for(
+                    outcome.refusal,
+                    request=identity,
+                    policy_bindings=outcome.evidence.applied,
+                    provenance=outcome.evidence,
+                ),
                 execution=None,
                 request=request,
                 perspective=perspective,
+                policy_bindings=self._applied_bindings(outcome.evidence),
+                resolution=outcome.evidence,
             )
-        effective = resolved
+        effective = outcome.evidence
         # The engine answers the EFFECTIVE question — defaults applied, policy
         # bounds in force. It is a SIBLING of the caller's request and never a
         # replacement: `identity.parameters` and the request that lands in
@@ -1504,7 +1575,7 @@ class GovernedResolver:
         request: ProductRequest,
         perspective: Perspective,
         policy_bindings: tuple[PolicyBinding, ...] = (),
-        resolution: EffectiveRequest | None = None,
+        resolution: EffectiveRequest | ResolutionNotApplicable,
     ) -> RefusalEnvelope:
         """Mint this refusal's decision record, then return the addressed shell.
 
@@ -1517,6 +1588,15 @@ class GovernedResolver:
         module reads a clock: the caller supplies it at serve time and replay
         supplies it at replay time, through this same code path.
 
+        ``resolution`` is required with no default (24.7-04): every branch
+        that reaches here ran the resolution step and passes what it
+        established — complete or partial (D-07) — and this thin layer
+        never substitutes a marker for what a branch did not say. ``D-IMPL-264`` amendment 1 (F-3 a), Dave verbatim: *"Any API that
+        constructs or delegates construction of a replay record must require
+        an explicit resolution state: effective/partial resolution or explicit
+        not-applicable marker. No intermediate layer may manufacture the
+        marker from omission."*
+
         Raises:
             Exception: whatever the artifact store raises, deliberately
                 uncaught. *A failure to record is a failure to serve* — and
diff --git a/src/ccf/replay/engine.py b/src/ccf/replay/engine.py
index cea82f35..d662d451 100644
--- a/src/ccf/replay/engine.py
+++ b/src/ccf/replay/engine.py
@@ -94,13 +94,19 @@ from ccf.artifacts.protocol import (
 )
 from ccf.contracts.base import CCFContract
 from ccf.contracts.canonical import content_hash, generation_mismatch
+from ccf.controlplane.artifacts import PolicyConstraint
 from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneProtocol
 from ccf.graph.protocols import GraphReader
 from ccf.products.contract import ContextProductContract
-from ccf.products.request import request_seeds
+from ccf.products.request import ProductRequestContract, request_seeds
 from ccf.projection.engine import OperatorRegistry, ProjectionEngine
 from ccf.projection.plan import Perspective, ProjectionOutput, ProjectionPlan
-from ccf.replay.record import NO_GRAPH_QUERIES, DecisionReplayRecord
+from ccf.replay.record import (
+    NO_GRAPH_QUERIES,
+    NO_REQUEST_RESOLUTION,
+    DecisionReplayRecord,
+    ResolutionNotApplicable,
+)
 from ccf.replay.snapshots import SnapshotReader, snapshot_of_execution
 
 __ccf_mode__ = "algorithmic"
@@ -111,6 +117,7 @@ __all__ = [
     "ReplayError",
     "ReplayGenerationMismatch",
     "ReplayOutcome",
+    "ReplayResolutionClaimMismatch",
     "ReplayUnresolvable",
     "replay",
     "resolve_artifact",
@@ -196,6 +203,77 @@ class ReplayGenerationMismatch(ReplayError):
         )
 
 
+class ReplayResolutionClaimMismatch(ReplayError):
+    """The record claims no resolution applies, and its own pins say one ran.
+
+    ``D-IMPL-264`` D-11 (24.7-09) with amendment 3 B-3 a; whitepaper §7.10
+    (the five-dimension record's completeness commitment, applied to
+    dimension 2's resolution); CLAUDE.md §11 (replay enforced at write time
+    and verified at read time). Raised by :func:`replay` **after** every
+    binding has resolved at its pinned version and **before** anything is
+    re-executed, when dimension 2's ``request_resolution`` is a
+    :class:`~ccf.replay.record.ResolutionNotApplicable` marker while at
+    least one of the record's ``policy_bindings.bindings``, resolved at its
+    EXACT pinned version through the Control Plane, is a
+    :class:`~ccf.products.request.ProductRequestContract` or a
+    :class:`~ccf.controlplane.artifacts.PolicyConstraint`. Dave's sentence
+    for why those two classes and only those two: *"request-contract pin +
+    applicable constraint pins are the evidence that effective-request
+    resolution ran."* A record that both pins that evidence and claims the
+    resolution never happened has contradicted itself, and the engine
+    refuses to replay a contradiction into a confident answer.
+
+    Not a :class:`ReplayDivergence` — nothing was re-executed and found to
+    differ; the check reads the record and the Control Plane, never the
+    graph. Not a :class:`ReplayUnresolvable` — nothing is missing; the pins
+    resolve, which is exactly how the contradiction becomes visible. It is
+    its own finding, with its own token, so an operator can tell *"this
+    record's dimension 2 is not the truth about this decision"* from either
+    of those. Dave, ``D-IMPL-264`` P-2: *"`not applicable` is an explicit
+    governed fact with a reason. Missing resolution information is an
+    internal integrity failure."* This is the read-side half of that rule.
+
+    Attributes:
+        reason: The token, ``resolution_claim_mismatch``, fixed on the class
+            so a caller can branch on it without parsing the message.
+        claimed_reason: The reason the marker stated — the claim that the
+            pins contradict.
+        pinned: Every ``(key, version, artifact class name)`` in the
+            record's bindings that resolved to a trigger class, in the
+            record's binding order. The evidence, named so the operator can
+            re-resolve it.
+        content_address: Where the refused record was resolved from.
+    """
+
+    reason: Final[str] = "resolution_claim_mismatch"
+
+    def __init__(
+        self,
+        *,
+        content_address: str,
+        claimed_reason: str,
+        pinned: tuple[tuple[str, str, str], ...],
+    ) -> None:
+        self.content_address = content_address
+        self.claimed_reason = claimed_reason
+        self.pinned = pinned
+        evidence = ", ".join(
+            f"({key!r}, {version!r}) → {class_name}"
+            for key, version, class_name in pinned
+        )
+        super().__init__(
+            f"{self.reason}: the DecisionReplayRecord at {content_address!r} "
+            f"claims no request resolution applies ({claimed_reason!r}) while "
+            "its own policy bindings pin, at their recorded versions, "
+            f"{evidence} — the evidence that effective-request resolution ran "
+            "(D-IMPL-264 D-11, amendment 3). A record that pins the contract "
+            "or constraint a resolution consulted and states that none applied "
+            "has contradicted itself; it is refused by name rather than "
+            "replayed into an answer about a decision whose governance it "
+            "misstates"
+        )
+
+
 @runtime_checkable
 class ReplayEnvironment(Protocol):
     """The deployment side of a replay (SDK-defined seam).
@@ -525,6 +603,83 @@ def _resolve_bindings(
             ) from missing
 
 
+def _verify_resolution_claim(
+    *,
+    record: DecisionReplayRecord,
+    control_plane: ControlPlaneProtocol,
+    content_address: str,
+) -> None:
+    """Hold dimension 2's not-applicable claim against the record's own pins.
+
+    ``D-IMPL-264`` D-11 (24.7-09), Dave verbatim: *"Replay verification
+    protects against a false `not-applicable` claim. The verification must
+    use the pinned historical contract/constraint state, not today's
+    configuration."* Called by :func:`replay` immediately after
+    :func:`_resolve_bindings` — so every pin is already known to resolve —
+    and before any plan or operator is resolved, because a record whose
+    dimension 2 misstates its own governance should not be re-executed at
+    all.
+
+    **The evidence base, and why it is exactly two classes** (amendment 3,
+    B-3 a): *"request-contract pin + applicable constraint pins are the
+    evidence that effective-request resolution ran. Do not use 'any class
+    declaration pin exists' as the proxy, because the intent check can
+    legitimately pin the class declaration before parameter resolution
+    occurs."* This is true of the tree, not only of the ruling: in ``src/``
+    and ``runtime/`` a :class:`~ccf.products.request.ProductRequestContract`
+    or a :class:`~ccf.controlplane.artifacts.PolicyConstraint` reaches a
+    record's ``policy_bindings.bindings`` only through
+    ``GovernedResolver._applied_bindings(effective)``, which exists only
+    once a resolution has run. A ``ProductClassDeclaration`` pin is
+    deliberately NOT a trigger — the intent refusal pins the deciding
+    declaration beside a ``refused-before-resolution`` marker, and that
+    record is telling the truth. So a marker beside no contract or
+    constraint pin is legitimate non-applicability (D-09) and replays; a
+    marker beside either is a contradiction and is refused.
+
+    **Pinned state only.** Each binding is resolved through
+    ``control_plane.resolve(key, version)`` at the version the record wrote,
+    never through a latest read, never through the deployment's current
+    registration under the same key. The classification is by the artifact
+    class that comes back, not by the key's name: keys are deployment
+    vocabulary and the engine knows none of it.
+
+    **The legacy sentinel is exempt** (D-12; F-4). A record carrying
+    :data:`~ccf.replay.record.NO_REQUEST_RESOLUTION` asserts it predates the
+    marker and is left exactly as it was — the same compatibility promise
+    the :data:`~ccf.replay.record.NO_GRAPH_QUERIES` exemption makes further
+    down :func:`replay`. Dave: *"Do not retroactively declare previously
+    valid replay artifacts defective because the SDK acquired a stronger
+    contract."* A value that is neither the sentinel nor a marker — the
+    :class:`~ccf.products.provenance.EffectiveRequest` that ran — makes no
+    not-applicable claim, so there is nothing to verify.
+    """
+    value = record.policy_bindings.request_resolution
+    if value == NO_REQUEST_RESOLUTION:
+        # D-12 / F-4: a record carrying the pre-marker sentinel asserts it
+        # predates the explicit resolution state and is exempt — that is
+        # the sentinel's compatibility promise, exactly as NO_GRAPH_QUERIES
+        # below exempts a pre-seam record from the query-pin comparison.
+        return
+    try:
+        marker = ResolutionNotApplicable.model_validate_json(value)
+    except ValueError:
+        # An EffectiveRequest (complete or partial) — a resolution ran and
+        # the record says so. Nothing is claimed not to apply.
+        return
+    pinned: list[tuple[str, str, str]] = []
+    for binding in record.policy_bindings.bindings:
+        artifact = control_plane.resolve(binding.key, binding.version)
+        if isinstance(artifact, (ProductRequestContract, PolicyConstraint)):
+            pinned.append((binding.key, binding.version, type(artifact).__name__))
+    if pinned:
+        raise ReplayResolutionClaimMismatch(
+            content_address=content_address,
+            claimed_reason=marker.reason,
+            pinned=tuple(pinned),
+        )
+
+
 def replay(
     *,
     record_address: str,
@@ -556,6 +711,14 @@ def replay(
             running record class declares as a generation boundary
             (``D-IMPL-243`` amendment 1). Raised before any binding is
             resolved and before anything is re-executed.
+        ReplayResolutionClaimMismatch: dimension 2 claims no request
+            resolution applies while a binding, resolved at its pinned
+            version, is a request contract or a policy constraint — the
+            evidence that a resolution ran (``D-IMPL-264`` D-11, amendment
+            3). Raised after every binding has resolved and before anything
+            is re-executed. A record carrying the legacy
+            :data:`~ccf.replay.record.NO_REQUEST_RESOLUTION` sentinel is
+            exempt (D-12).
         ReplayDivergence: something resolved but did not reproduce.
         ~ccf.replay.snapshots.SnapshotPinUnresolvable: dimension 1 carries a
             real store pin and the reader is not
@@ -577,6 +740,12 @@ def replay(
         content_address=record_address,
     )
     _resolve_bindings(record=record, control_plane=control_plane)
+    # D-IMPL-264 D-11 (24.7-09): with every pin known to resolve, hold the
+    # record's not-applicable claim against what those pins ARE at their
+    # recorded versions — before any plan or operator is resolved.
+    _verify_resolution_claim(
+        record=record, control_plane=control_plane, content_address=record_address
+    )
 
     path = record.content_generation_path
     try:
diff --git a/src/ccf/replay/record.py b/src/ccf/replay/record.py
index 0b88831e..cee11052 100644
--- a/src/ccf/replay/record.py
+++ b/src/ccf/replay/record.py
@@ -64,7 +64,7 @@ from __future__ import annotations
 
 from collections.abc import Mapping
 from datetime import datetime
-from typing import TYPE_CHECKING, Final
+from typing import TYPE_CHECKING, Final, Literal
 
 from pydantic import Field, field_validator
 
@@ -159,6 +159,8 @@ __all__ = [
     "PerspectiveConditioning",
     "PolicyBinding",
     "PolicyBindingsSnapshot",
+    "ResolutionNotApplicable",
+    "ResolutionNotApplicableReason",
     "build_replay_record",
 ]
 
@@ -237,6 +239,63 @@ NO_ADAPTER = "no-adapter"
 #: module exists to close.
 NO_REQUEST_RESOLUTION = "no-request-resolution"
 
+#: The closed reason vocabulary of :class:`ResolutionNotApplicable` (24.7-04;
+#: ``D-IMPL-264`` D-09/D-10). Hyphenated lowercase like every sentinel in
+#: this module. Two reasons, and a marker states exactly one of them:
+#:
+#: ``no-resolution-step``
+#:     The path that minted the record never invokes a constraint resolver
+#:     — a direct validator, a test fixture. ``D-IMPL-264`` D-09: *"A path
+#:     that never invokes resolution should say so explicitly. Do not
+#:     redefine all direct validators as defective merely because the newer
+#:     resolver exists."*
+#: ``refused-before-resolution``
+#:     The determination was reached before resolution could begin — a
+#:     delivery-boundary denial of entitlement, or of a standing resource's
+#:     existence, decided at the door with no resolver in the frame.
+ResolutionNotApplicableReason = Literal[
+    "no-resolution-step", "refused-before-resolution"
+]
+
+
+class ResolutionNotApplicable(CCFContract):
+    """Dimension 2's request-resolution value when NO resolution applies — a
+    positive claim, with its reason (24.7-04; ``D-IMPL-264`` D-09/D-10, P-2).
+
+    SDK-defined (CLAUDE.md §11); the whitepaper hook is §7.10's completeness
+    commitment — a record missing any one of the five dimensions leaves a
+    whole class of audit question with no answer — applied to dimension 2's
+    resolution: a record that says nothing about whether the question's
+    parameters were resolved leaves *"was this decision governed by the
+    constraints in force?"* unanswerable.
+
+    A positive claim in the :data:`NO_REQUEST_RESOLUTION` voice, and the
+    claim that sentinel could never quite make. Dave, ``D-IMPL-264`` P-2:
+    *"`not applicable` is an explicit governed fact with a reason. Missing
+    resolution information is an internal integrity failure."* The sentinel
+    said *no resolution was recorded* — which a dropped resolution also
+    says. This marker says *no resolution applies, and here is why* — which
+    a dropped resolution cannot say, because a caller has to construct it to
+    state it, and :func:`build_replay_record` refuses to mint a record
+    without either this or the resolution that ran (D-10).
+
+    ``reason`` is REQUIRED and closed (:data:`ResolutionNotApplicableReason`):
+    an author who never stated why resolution does not apply has not stated
+    non-applicability — the :class:`~ccf.products.provenance.ProvenanceSource`
+    discipline. No default means no hash-transparency key and no roster
+    entry (``D-IMPL-243``): the marker's canonical bytes are the reason and
+    nothing else. The builder renders it into
+    :attr:`PolicyBindingsSnapshot.request_resolution` from the VALUE through
+    :func:`~ccf.contracts.canonical.canonical_bytes`, never accepted
+    pre-serialized — so it is a JSON object string there, distinguishable
+    from the legacy sentinel by shape, and it reads back as itself.
+
+    Attributes:
+        reason: Why no resolution applies to this decision.
+    """
+
+    reason: ResolutionNotApplicableReason
+
 #: Dimension 1's watermark when the decision read **no** graph state at all
 #: (24.6-07; ``D-IMPL-253`` Q13). A positive claim in the
 #: :data:`NO_HITL_ACTIONS` voice, and the one this phase most needed: a refusal
@@ -520,6 +579,20 @@ class PolicyBindingsSnapshot(CCFContract):
     positive :data:`NO_REQUEST_RESOLUTION` claim, and it is hash-transparent at
     that value (``D-IMPL-243``) — so every record written before the Authority
     layer existed keeps its content address, byte for byte.
+
+    The field holds one of **three forms**, and only the first is a
+    compatibility claim (24.7-04; ``D-IMPL-264`` D-10, D-12): the legacy
+    sentinel :data:`NO_REQUEST_RESOLUTION`, read off every record written
+    before 24.7 and off any record parsed from bytes that omit the field —
+    the field's default, which the builder no longer writes; the canonical
+    bytes of the :class:`~ccf.products.provenance.EffectiveRequest` that
+    resolution produced, complete or partial; or the canonical bytes of a
+    :class:`ResolutionNotApplicable` marker stating, with its reason, that no
+    resolution applies. The type stays ``str`` and the default stays the
+    sentinel so that no committed record's address moves; a new record
+    carries one of the two canonical forms because
+    :func:`build_replay_record` refuses to mint one without an explicit
+    resolution state.
     """
 
     bindings: tuple[PolicyBinding, ...]
@@ -1123,6 +1196,7 @@ def build_replay_record(
     policy_bindings: tuple[PolicyBinding, ...],
     assembly_mode: AssemblyMode,
     recorded_at: datetime,
+    resolution: "EffectiveRequest | ResolutionNotApplicable",
     refusal: "RefusalEnvelope | None" = None,
     tenant_id: str | None = None,
     assembler_id: str | None = None,
@@ -1135,7 +1209,6 @@ def build_replay_record(
     assembly_refusal: str | None = None,
     adapter: AdapterPin | None = None,
     request: ProductRequest | None = None,
-    resolution: "EffectiveRequest | None" = None,
 ) -> DecisionReplayRecord:
     """Assemble the record from what the execution and the product already know.
 
@@ -1284,14 +1357,26 @@ def build_replay_record(
       before.
 
     ``resolution`` is the 24.6-03 Authority seam (``D-IMPL-253`` Q1/Q6,
-    ``D-IMPL-254``), threaded into dimension 2 exactly as ``adapter`` is: the
-    caller passes the :class:`~ccf.products.provenance.EffectiveRequest` its
-    constraint resolver produced, and this builder renders it — from the
-    **value**, with :func:`~ccf.contracts.canonical.canonical_bytes`, so one
-    resolution has one rendering. When ``None`` (every fabric-direct decision
-    and everything before this extension) dimension 2 carries the positive
-    :data:`NO_REQUEST_RESOLUTION` claim and every field the builder wrote before
-    it is byte-for-byte what it was.
+    ``D-IMPL-254``), threaded into dimension 2 exactly as ``adapter`` is —
+    and, as of 24.7-04, REQUIRED (``D-IMPL-264`` D-10, P-2). The caller
+    states one of two things: the
+    :class:`~ccf.products.provenance.EffectiveRequest` its constraint
+    resolver produced — complete, or the partial record a resolver
+    established before refusing (D-07) — or a :class:`ResolutionNotApplicable`
+    marker with the reason no resolution applies (D-09). This builder renders
+    either — from the **value**, with
+    :func:`~ccf.contracts.canonical.canonical_bytes`, so one resolution has
+    one rendering and a marker is never accepted pre-serialized.
+
+    There is no third choice. Omitting ``resolution`` is a ``TypeError`` at
+    the call — the signature has no default to fall back to — and passing
+    ``None`` is a ``ValueError`` from the first guard below. Dave: *"No
+    implicit omission for new records"*; *"Missing resolution information
+    is an internal integrity failure."* Nothing here infers the marker from
+    an absent argument: a record that cannot say whether resolution ran is
+    not built. The legacy :data:`NO_REQUEST_RESOLUTION` sentinel is still
+    what a record written before this extension reads (D-12) — it is the
+    field's default, never this builder's output.
 
     It is a **parameter** and not a fact read off ``execution`` for
     ``adapter``'s first reason: the resolution happens *before* the engine runs
@@ -1344,7 +1429,34 @@ def build_replay_record(
     :data:`~ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE`, so every call site
     written before this extension is byte-for-byte what it was.
     """
-    # 24.6-07: the outcome guard, at the top and before anything is derived. A
+    # 24.7-04: the resolution-state guard, FIRST — before any outcome is
+    # judged — because a missing resolution state is not a malformed outcome,
+    # it is an integrity failure of the caller (`D-IMPL-264` P-2). `None` is
+    # the omission the ruling closed; the signature has no default, so an
+    # omitted keyword never reaches here at all.
+    if resolution is None:
+        raise ValueError(
+            "build_replay_record requires an explicit resolution state: the"
+            " `EffectiveRequest` the resolution produced (complete or partial),"
+            " or a `ResolutionNotApplicable` marker stating why none applies."
+            " `None` is neither. `D-IMPL-264` D-10 / P-2: \"`not applicable`"
+            " is an explicit governed fact with a reason. Missing resolution"
+            " information is an internal integrity failure.\""
+        )
+    # Function-local for the reason `_refusal_names` is (DEF-17-02): the
+    # module-scope import is typing-only, and the runtime needs the value
+    # only here.
+    from ccf.products.provenance import EffectiveRequest
+
+    if not isinstance(resolution, (EffectiveRequest, ResolutionNotApplicable)):
+        raise ValueError(
+            "the resolution state is rendered from the VALUE, once, by this"
+            " builder, and is never accepted pre-serialized: pass the"
+            " `EffectiveRequest` or the `ResolutionNotApplicable` marker"
+            f" itself, not a {type(resolution).__name__}. A block a caller"
+            " serialized could be a family of blocks (24.6-03)"
+        )
+    # 24.6-07: the outcome guard, next and before anything is derived. A
     # record carrying both halves would describe two decisions and a record
     # carrying neither would describe none, so both are unrepresentable rather
     # than merely discouraged — the `DoorOutcome._exactly_one_half` posture,
@@ -1442,12 +1554,12 @@ def build_replay_record(
             # VALUE rather than accepted as a pre-serialized block — the
             # `_admissible_refusal_block` argument, applied where it can be
             # applied absolutely: a resolution cannot land as a family of
-            # blocks because the caller never hands one over.
-            request_resolution=(
-                canonical_bytes(resolution).decode("utf-8")
-                if resolution is not None
-                else NO_REQUEST_RESOLUTION
-            ),
+            # blocks because the caller never hands one over. 24.7-04: the
+            # same expression renders the not-applicable marker; there is no
+            # sentinel branch because there is no `None` to reach it
+            # (`D-IMPL-264` D-10). The sentinel stays the FIELD default so a
+            # record parsed from bytes that omit it still reads it (D-12).
+            request_resolution=canonical_bytes(resolution).decode("utf-8"),
         ),
         model_version=ModelVersionRecord(
             assembly_mode=assembly_mode,
```


<!-- mid-payload read-proof -->
```
READ-PROOF bundle-src-part-1.md: fb9dcf4996c221ae
```

## runtime/ccf_runtime/authz/delivery_boundary.py — FULL TEXT at ad8dc5a9

```python
"""The governed delivery-boundary step — determination, replay and disclosure in one call.

**SDK-defined, not whitepaper-derived** (CLAUDE.md §11, §8.3). The rulings of
record are ``D-IMPL-256`` and ``D-IMPL-254``.

The invariant, in Dave's own words (``D-IMPL-256``, criterion 36):

    *"Every governed determination that crosses a CCF delivery boundary —
    fulfilled or refused, tool or resource, authorized or denied — must reach
    the replay writer before the response is released. A delivery boundary
    unable to satisfy that invariant is unavailable, not partially governed."*

And the sequence principle it turns on, verbatim:

    *"The sequence should conceptually remain: request → identity/policy →
    determination → replay → disclosure shaping → transport encoding — not:
    request → determination → HTTP/MCP → transport notices refusal → writes
    replay. Replay belongs to the governed determination, not to HTTP or MCP.
    That matters because otherwise the standing-resource/tool asymmetry simply
    reappears somewhere else."*

**This module is the delivery-boundary DETERMINATION step of ``D-IMPL-254``'s
Authority layer, and replay belongs here** — SDK-defined under CLAUDE.md §11
and ``D-IMPL-256``, not whitepaper-derived. A transport calls
:func:`govern_entitlement` and **encodes what it returns**. It does not catch
:class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused`, does
not build a shell, does not read a clock and does not mint a record. The one
``except`` clause for that refusal anywhere under this package is the one in
:func:`govern_entitlement` below, and its uniqueness is what makes the sequence
structural rather than conventional — a second one at a transport would put the
transport back in charge of minting replay, which is the shape the ruling names
and rejects.

What this module imports, and what it deliberately does not
-----------------------------------------------------------
It imports the fabric's own product package and this package's entitlement
seam, and **no transport**: nothing here names the HTTP tree or the MCP tree
directly. A determination module that imported a transport would be the
inversion criterion 36 forbids, in the same spirit as
``tests/invariants/test_mcp_role_separation.py``'s rule that the MCP roles are
separate modules importing none of their siblings.

**That statement is about this module's own imports, and it is deliberately
not transitive.** The entitlement seam module beside this one already reaches
the shared HTTP error vocabulary and the MCP verified-token type, because a
single definition of *entitled* has to be renderable in both protocols and has
to name the type a verified caller arrives as. That is unchanged and correct,
and nobody should "fix" it: the discipline is that the *determination* does not
reach for a transport's machinery, not that a vocabulary two doors share must
be duplicated per door. It is also why the verified-token type is read from
that seam module here rather than from where it is defined — it is part of the
seam this module composes, and taking it from the seam keeps this module's own
import list to two packages.

Algorithmic module (CINV-03): no LLM client, and no wall-clock read of any
kind — the only instant this module knows is the one the deployment declared on
its own entitlement source.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

from ccf.products.refusal import (
    RefusalEnvelope,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.resolver import RefusalRecorderProtocol
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_ROLE_RESOLVED,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf_runtime.authz.product_entitlement import (
    PerspectiveResolverProtocol,
    ProductEntitlementRefused,
    ProductEntitlementSourceProtocol,
    TokenGrant,
    entitled_perspective,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "SURFACE_HTTP_ROUTE",
    "SURFACE_MCP_RESOURCE",
    "SURFACE_MCP_TOOL",
    "UnrecordableDeliveryBoundaryError",
    "govern_absence",
    "govern_entitlement",
    "recorded_boundary",
]


#: The three delivery surfaces, as the mechanism tokens
#: :attr:`~ccf.products.refusal.ResourceRequestIdentity.surface` carries.
#:
#: Defined **once**, here, beside the governed step that mints them, and never
#: as a literal at a door. Three doors spelling one surface three ways is three
#: vocabularies in the audit record, and an examiner filtering on a surface
#: would silently miss two of them.
SURFACE_HTTP_ROUTE: Final[str] = "http-route"
SURFACE_MCP_TOOL: Final[str] = "mcp-tool"
SURFACE_MCP_RESOURCE: Final[str] = "mcp-resource"


class UnrecordableDeliveryBoundaryError(ValueError):
    """A delivery boundary that entitles without a recorder is not built.

    ``D-IMPL-256`` (2), Dave, verbatim and stated **once** so the three
    builders that raise this write no prose of their own:

        *"a door configured to make governed determinations without the ability
        to record them is not a valid governed door."*

    His posture on the alternative, in the same ruling: a door that served
    authorized requests normally *"but fail[ed] closed only when denial
    happens"* would *"make auditability contingent on outcome"* — and it would
    reopen the observational leak the checker measured, because unauthorized
    and nonexistent requests would then diverge merely because the door was
    misconfigured.

    A :class:`ValueError` rather than a new base, on this codebase's own
    construction-refusal posture: a boot that cannot satisfy an invariant stops
    at construction rather than at the first request
    (*"Prefer fail-at-construction/boot where practical"*).
    """


def recorded_boundary(
    *, refusal_recorder: object | None, builder: str
) -> RefusalRecorderProtocol:
    """Return the recorder, or refuse to build an entitling delivery boundary.

    The ONE construction-time check ``D-IMPL-256`` (2) asks for. The three
    builders — the HTTP app, the egress MCP server and the experience MCP
    server — call it and add nothing: the posture is stated in
    :class:`UnrecordableDeliveryBoundaryError` and nowhere else, so three doors
    cannot drift into three explanations of one rule.

    **Structural conformance, and no I/O probe.**
    :class:`~ccf.products.resolver.RefusalRecorderProtocol` is
    ``@runtime_checkable``, so the check is real without calling anything. A
    probe that appended a record to prove the store works would write a record
    nobody asked for — an artifact in the audit trail describing no decision,
    which is the opposite of what an audit trail is for. A store that is
    reachable at construction and broken at the first determination is the case
    the seam's own *"a failure to record is a failure to decide"* posture
    covers.

    Args:
        refusal_recorder: What the builder was handed. ``None`` is the
            commonest failure — a deployment that bound an entitlement source
            and forgot the recorder.
        builder: The builder's own name, so the message names where to fix it
            rather than where it was noticed.

    Returns:
        ``refusal_recorder``, unchanged, typed as the Protocol.

    Raises:
        UnrecordableDeliveryBoundaryError: it is absent or does not conform.
    """
    if refusal_recorder is None:
        raise UnrecordableDeliveryBoundaryError(
            f"{builder} was asked to build an entitling delivery boundary with"
            " no `refusal_recorder=`; a door configured to make governed"
            " determinations without the ability to record them is not a valid"
            " governed door (D-IMPL-256 (2)). Pass a"
            " `ccf.products.resolver.RefusalRecorderProtocol` — the SDK ships"
            " `ReplayRefusalRecorder` over the same artifact store the resolver"
            " already holds — or build a boundary that does not entitle"
        )
    if not isinstance(refusal_recorder, RefusalRecorderProtocol):
        raise UnrecordableDeliveryBoundaryError(
            f"{builder} was passed a `refusal_recorder=` of type"
            f" {type(refusal_recorder).__name__}, which does not conform to"
            " `ccf.products.resolver.RefusalRecorderProtocol`; a door"
            " configured to make governed determinations without the ability"
            " to record them is not a valid governed door (D-IMPL-256 (2))."
            " The conformance check is structural — the recorder needs a"
            " `record` method — and it runs at construction rather than at the"
            " first denial, so a misconfigured door never answers at all"
        )
    return refusal_recorder


def _determined_at(entitlement_source: ProductEntitlementSourceProtocol) -> datetime:
    """The one instant a governed determination is stamped from.

    Read ONCE per determination, off the entitlement source's own declared
    clock, and refused when it carries no UTC offset: the instant is what the
    replay record and the audit event are both stamped from, and an instant
    whose offset is the deciding host's local configuration replays
    differently on every host (``D-IMPL-38``).
    """
    determined_at = entitlement_source.clock()
    if determined_at.tzinfo is None or determined_at.utcoffset() is None:
        raise ValueError(
            f"the entitlement source's clock returned {determined_at.isoformat()!r},"
            " which carries no UTC offset; the instant a governed determination"
            " was reached is what its replay record and its audit event are"
            " both stamped from, and an instant whose offset is the deciding"
            " host's local configuration replays differently on every host"
            " (D-IMPL-38). Declare the source's clock so that it returns a"
            " timezone-aware instant"
        )
    return determined_at


def govern_absence(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    product_version: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    perspective: Perspective,
    absent: LookupError,
    entitlement_source: ProductEntitlementSourceProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> RefusalEnvelope:
    """The governed determination for a product class the deployment does not serve.

    ``D-IMPL-260`` P-C (Dave, verbatim): *"an unregistered product class must
    reach the caller as the common shell; the status may stay 404."* Before
    this step, a deployment resolver's ``ProductNotServable`` — the absence of
    a gate-admitted product at the address the caller resolved and was
    entitled to — left each door in that door's own vocabulary: an
    ``HTTPException(404, str(absent))`` on HTTP, an opaque runtime failure on
    the MCP tool, a transport error on the resources. A caller could tell
    *there is no such class* from *there is no such subject* by the shape of
    the non-answer, and none of the three was a recorded decision.

    It is the same determination the assembler reaches for a subject nothing
    resolves — :class:`~ccf.products.refusal.SubjectUnavailableRefusal` with
    ``cause="nonexistent"`` — minted here at the boundary because the
    resolver that would have minted it is the one that has nothing to serve.
    Recorded THEN disclosed, through the same
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` an entitlement denial
    goes through, under the same
    :class:`~ccf.products.refusal.ResourceRequestIdentity`, and rendered by
    each door through the same function its other refusals go through — so
    the three doors say one thing, and a consumer reads *subject unavailable*
    with a replay reference behind it.

    **What it is not.** Not a catch-all: only the typed absence — a
    ``LookupError`` the deployment's resolver raised to say *nothing is
    servable there* — reaches this step, and a transport that catches more
    than that here would be converting a runtime fault into a governed "no"
    the fabric never made (``D-IMPL-253`` Q20). Dimension 2 pins nothing: no
    policy decided the absence. Dimension 4 carries the perspective the
    caller was already entitled under — the role that participated
    (``D-IMPL-260`` P-D).

    Args:
        grant: The verified caller.
        tenant: The tenant the caller addressed.
        product_class: The class the caller addressed and was entitled to.
        product_version: The class's lane, or ``None`` when the surface named
            none.
        parameters: What the caller supplied, for the request identity.
        asked_at: The instant asked as-of, or ``None`` (the caller deferred to
            the server's decision instant).
        surface: One of the three surface tokens.
        address: What the caller addressed, verbatim.
        perspective: The perspective the delivery boundary already authorized
            for this call — the entitlement step returned it.
        absent: The resolver's own statement of the absence. Its text is the
            internal ``detail``; what a consumer sees of it is the Disclosure
            layer's decision.
        entitlement_source: The source whose declared clock stamps the
            determination.
        refusal_recorder: The seam that mints the record and discloses.

    Returns:
        The disclosed shell, carrying the replay reference of the record this
        determination produced.
    """
    determined_at = _determined_at(entitlement_source)
    envelope = envelope_for(
        SubjectUnavailableRefusal(
            cause="nonexistent",
            detail=str(absent),
            error_code=None,
        ),
        request=RequestIdentity(
            product_id=product_class,
            product_version=product_version,
            parameters=parameters,
            temporal_boundary=asked_at,
        ),
        resource=ResourceRequestIdentity(
            surface=surface,
            address=address,
            tenant_id=tenant,
            determined_at=determined_at,
        ),
        policy_bindings=(),
    )
    return refusal_recorder.record(
        envelope,
        perspective=Perspective(
            principal_id=grant.client_id, role=perspective.role
        ),
        recorded_at=determined_at,
        policy_bindings=(),
        # Dimension 2: the absence is decided at the door, before any
        # resolver could run, and the record SAYS so with its reason — a
        # positive absence stated by the door, never inferred by the seam
        # from a keyword the door left out (`D-IMPL-264` D-09/D-10 am.1).
        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
    )


def govern_entitlement(
    *,
    grant: TokenGrant,
    tenant: str,
    product_class: str,
    product_version: str | None,
    requested_role: str | None,
    parameters: Mapping[str, Any],
    asked_at: datetime | None,
    surface: str,
    address: str,
    entitlement_source: ProductEntitlementSourceProtocol,
    perspective_resolver: PerspectiveResolverProtocol,
    refusal_recorder: RefusalRecorderProtocol,
) -> Perspective | RefusalEnvelope:
    """Decide entitlement, and on a denial mint and disclose before returning.

    The ONE governed step every entitling delivery boundary calls, in
    ``D-IMPL-256``'s ruled sequence: **request → identity/policy →
    determination → replay → disclosure shaping → transport encoding**. The
    first five happen here; only the sixth is the transport's, and by the time
    it runs there is nothing left to decide — a caller receives either the
    entitled :class:`~ccf.projection.plan.Perspective` or an **already-recorded,
    already-disclosed** shell.

    The order, and the order is the property:

    1. ``determined_at = entitlement_source.clock()`` — read **once**, before
       the determination, because it is the instant *of* the determination. No
       other clock is read in this module and no wall-clock call appears in it
       at all. The replay record minted below is stamped from this read; the
       ``authz_decision`` audit event the source appends inside its own
       ``authorize`` is stamped from a SECOND read of the same clock, so the
       two agree exactly under a pinned clock and to within one read under a
       wall clock. Carrying this instant INTO ``authorize`` is a Protocol
       change recorded as a carried finding at the Phase 24.6 close, not a
       claim this docstring makes. (Its earlier text claimed *"the same
       instant by construction"*, which was false.)
    2. :func:`~ccf_runtime.authz.product_entitlement.entitled_perspective` runs
       the one resolution order every door runs. An entitled request returns
       the perspective and **writes nothing**: a fulfilled decision is the
       resolver's to record, and a second record here would make one decision
       two.
    3. A denial becomes
       :class:`~ccf.products.refusal.SubjectUnavailableRefusal` with
       ``cause="unauthorized"`` — the one canonical outcome an unauthorized
       principal shares with a nonexistent subject (``D-IMPL-253`` Q27) —
       enveloped with the request identity **and** a
       :class:`~ccf.products.refusal.ResourceRequestIdentity`, and handed to
       :meth:`~ccf.products.resolver.RefusalRecorderProtocol.record`, which
       appends the internal truth and returns the disclosed shell.

    **A failed append propagates.** Nothing here catches the store's error: *a
    failure to record is a failure to decide*, which is the resolver's own
    posture and is what makes criterion 36 hold at the boundary rather than
    only in the fabric.

    Args:
        grant: The verified caller identity. Never a caller's claim.
        tenant: The tenant the request was addressed under — established by the
            calling surface, never read from a caller's body.
        product_class: The Context Product class requested.
        product_version: The class's own lane, or ``None`` when the surface
            named none.
        requested_role: The role the caller asked for, or ``None`` on a surface
            with no way to ask. Handed to the perspective resolver and used for
            nothing else here: the role a denial RECORDS is the one the
            determination was made under —
            :attr:`~ccf_runtime.authz.product_entitlement.ProductEntitlementRefused.role`,
            the resolved perspective's role the source decided against — and
            a denial reached before any role of the caller's was established
            records :data:`~ccf.replay.record.NO_ROLE_RESOLVED`, the door's
            own positive claim rather than a ``None`` the recorder would have
            to interpret (``D-IMPL-260`` P-D: *"the role that actually
            participated, explicit absence if none was established, never a
            substituted default"*).
        parameters: What the caller supplied, for the request identity.
        asked_at: The instant the caller asked as-of, or ``None`` — the
            positive *the caller deferred to the server's decision instant*.
            Refused when it carries no UTC offset, on
            the egress door's own posture: an ambiguous boundary
            replays differently on every host (``D-IMPL-38``).
        surface: One of :data:`SURFACE_HTTP_ROUTE`, :data:`SURFACE_MCP_TOOL`,
            :data:`SURFACE_MCP_RESOURCE`.
        address: What the caller addressed — the product URI a standing
            resource names, or the route path an HTTP caller asked for. What
            was asked for, never what the fabric resolved it to.
        entitlement_source: The deployment's entitlement decision seam, and the
            holder of the determination clock.
        perspective_resolver: The deployment's role-derivation seam.
        refusal_recorder: The ONE minting seam. Checked at construction by
            :func:`recorded_boundary`, so by the time this runs it conforms.

    Returns:
        The entitled perspective, or the disclosed refusal shell carrying the
        address of its own record.

    Raises:
        ValueError: ``asked_at`` carries no UTC offset, or the source's clock
            returned a naive instant. Both are deployment defects that would
            make a determination replay differently on a different host.
        Exception: whatever the artifact store raises on append, deliberately
            uncaught.
    """
    if asked_at is not None and (
        asked_at.tzinfo is None or asked_at.tzinfo.utcoffset(asked_at) is None
    ):
        raise ValueError(
            f"asked_at {asked_at.isoformat()!r} carries no UTC offset; the"
            " instant a question was asked as-of is the boundary a replay"
            " resolves against and cannot be ambiguous (D-IMPL-38)"
        )

    # (1) The determination instant, read ONCE and first.
    determined_at = _determined_at(entitlement_source)

    try:
        # (2) The one resolution order. Entitled: return it, write nothing.
        return entitled_perspective(
            grant=grant,
            tenant=tenant,
            product_class=product_class,
            requested_role=requested_role,
            entitlement_source=entitlement_source,
            perspective_resolver=perspective_resolver,
        )
    except ProductEntitlementRefused as refused:
        # (3) The governed determination. `cause="unauthorized"` is internal
        # truth; what a consumer sees is the Disclosure layer's decision, taken
        # inside `record` below and nowhere else.
        envelope = envelope_for(
            SubjectUnavailableRefusal(
                cause="unauthorized",
                detail=refused.message,
                error_code=refused.error_code,
            ),
            request=RequestIdentity(
                product_id=product_class,
                product_version=product_version,
                parameters=parameters,
                temporal_boundary=asked_at,
            ),
            resource=ResourceRequestIdentity(
                surface=surface,
                address=address,
                tenant_id=tenant,
                determined_at=determined_at,
            ),
            # The policy that DECIDED, carried on the refusal from the source's
            # own single resolution (D-34, `24.6-08`). The empty tuple is the
            # positive "no policy was consulted", which is the honest answer
            # for the subject-conflict path and for a tenant that registered
            # none.
            policy_bindings=(
                (refused.policy,) if refused.policy is not None else ()
            ),
        )
        # The mint AND the disclosure, both inside the seam and in that order.
        # Nothing is disclosed before it is recorded, and a failed append
        # propagates rather than releasing an unrecorded response.
        return refusal_recorder.record(
            envelope,
            perspective=Perspective(
                principal_id=grant.client_id,
                # Dimension 4: the role the source DECIDED under, off the
                # determination itself — not the role the caller asked for,
                # which the resolver may have replaced or defaulted — and the
                # positive absence when none was established (D-IMPL-260 P-D).
                role=refused.role if refused.role is not None else NO_ROLE_RESOLVED,
            ),
            recorded_at=determined_at,
            # Dimension 2: entitlement is refused before resolution begins —
            # the resolver never ran, so there is no resolution to record and
            # the record says WHY there is none, in the `NO_ROLE_RESOLVED`
            # voice: a positive absence the door states, never one the seam
            # infers from silence (`D-IMPL-264` D-09/D-10 am.1).
            resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
            policy_bindings=(
                (
                    PolicyBinding(
                        key=refused.policy.identity,
                        version=refused.policy.version,
                    ),
                )
                if refused.policy is not None
                and refused.policy.version is not None
                else ()
            ),
        )
```


---
End of bundle-src-part-1.md. Read-proof, again:
```
READ-PROOF bundle-src-part-1.md: fb9dcf4996c221ae
```
