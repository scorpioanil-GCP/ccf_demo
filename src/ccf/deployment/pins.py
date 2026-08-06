"""The pin record a manifest load produces: ``(key, version, class_id, registration)``.

SDK-defined mechanism (CLAUDE.md §6.4 and §10). The whitepaper fixes that a
decision resolves the configuration in force when it was made (§7.10) and that
resolution is by exact version, never "latest" (D-IMPL-26); it does not specify
the record a deployment carries those pins around in. That record is this
module, and its whole design is a constraint on what it must never become.

**A plain typed record that grows no projection helpers.**

The constraint is worth stating as a constraint rather than a style note,
because the convenience that would break it is genuinely attractive. Today an
adopter writes::

    build_replay_record(policy_bindings=..., ...)

naming the bindings in force at the call site. A helper — ``pins.policy_bindings()``
— would shorten that to ``policy_bindings=pins.policy_bindings()``, and in doing
so would move the *selection* of which bindings are in force out of the
adopter's code and into the SDK. That is a governance-boundary move wearing an
ergonomics costume: dimension 2 of the five-dimension Decision Replay record
would then be assembled by a rule nobody in the deployment wrote down.

:meth:`ResolvedPins.version_for` is **lookup**, not selection — the caller
already knows the key it wants and is asking what version answered to it. That
is why it is the one accessor permitted, and why a method whose name implies a
choice about *which* artifacts matter does not belong on this type. The standing
assertion is ``tests/deployment/test_manifest.py``, which pins the public method
set exactly.

**Register-role entries only (D-IMPL-80).** See :class:`ResolvedPins`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import RegistrationMode

__ccf_mode__ = "algorithmic"

__all__ = ["ArtifactPin", "ResolvedPins", "UnpinnedArtifactError"]


class UnpinnedArtifactError(LookupError):
    """No pin was recorded under the requested manifest key.

    A :class:`LookupError` rather than a returned ``None``, on the registry's
    own no-silent-default posture (D-IMPL-38): a caller reaching for a pin has
    already decided it needs one, and handing back a value nobody chose would
    push the failure to whatever reads the version next.

    Two distinct situations raise it, and the message names the key so they are
    distinguishable at the point of failure: the key is not in the manifest at
    all, or the key is in the manifest under ``role: load`` and therefore has no
    version because nothing registered it.
    """


class ArtifactPin(CCFContract):
    """One artifact in force: the key it is registered under and its version.

    Attributes:
        key: The Control Plane key, taken verbatim from the manifest entry.
        version: The content version :meth:`register_typed
            <ccf.controlplane.registry.ControlPlaneRegistry.register_typed>`
            returned. A content hash (D-IMPL-26), so pin identity *is* content
            identity — which is what makes two loads of one manifest produce a
            byte-identical pin set.
        class_id: The artifact class the document was validated against,
            carried so a reader of the pin set can say *what kind of thing* was
            in force without re-resolving it.
        registration: Which registration path the entry actually travelled —
            ``typed`` or ``versioned`` (D-IMPL-83, RESOLVED 2026-08-05, Dave).

            A **recorded fact**, exactly like ``class_id``: this module's
            no-growth constraint forbids *methods that select*, not *fields that
            record*, which is why the mode lands here and :class:`ResolvedPins`
            gains no accessor for it.

            The audit log remains the **primary** evidence.
            :meth:`register_versioned
            <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>`
            already audits every outcome with ``action="register_versioned"`` and
            ``resolved=True|False`` — which is how
            ``test_the_author_versioned_definitions_kept_their_bump_check`` reads
            it — and this field is the convenience for a reader who has the
            returned pins in hand and no audit log.

            Consequence accepted with the ruling: the field is additive to a
            :class:`~ccf.contracts.base.CCFContract`, so the pin set's content
            hash changes. ``test_two_loads_of_one_manifest_produce_an_identical_pin_set``
            still holds, because both loads change identically.
    """

    key: str
    version: str
    class_id: str
    registration: RegistrationMode


class ResolvedPins(CCFContract):
    """Every artifact a manifest load put in force, in manifest order.

    **Register-role entries only (D-IMPL-80).** A manifest entry marked
    ``role: load`` is parsed, validated, and handed back to the caller, but it
    is never registered — so it has no version, and there is nothing to pin.
    :meth:`version_for` raising :class:`UnpinnedArtifactError` for a load-role
    key is therefore **correct behavior, not a lookup bug**: the absence is the
    ruling working. The parsed artifact is still reachable, on the boot result's
    ``artifacts`` mapping; ``role`` governs registration and pinning, never
    visibility.

    See the module docstring for why :meth:`version_for` is the only accessor
    this type may ever grow.

    Attributes:
        entries: The pins, in the order the manifest declared them. Order is
            carried rather than sorted so the record reads back against the
            document that produced it.
    """

    entries: tuple[ArtifactPin, ...] = ()

    def version_for(self, key: str) -> str:
        """Return the version pinned under ``key``.

        Raises:
            UnpinnedArtifactError: no ``role: register`` entry in the manifest
                carried this key — either it is absent entirely, or it is
                declared ``role: load`` and was deliberately never registered.
        """
        for entry in self.entries:
            if entry.key == key:
                return entry.version
        raise UnpinnedArtifactError(
            f"no version is pinned under manifest key {key!r}; the manifest"
            " either does not name it or names it with role 'load', which is"
            " parsed and returned but never registered (D-IMPL-80)"
        )
