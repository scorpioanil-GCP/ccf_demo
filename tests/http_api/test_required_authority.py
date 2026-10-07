"""There is no unauthenticated arm left to build (``SEC-001``).

The successor to ``test_insecure_default_warning.py``, which asserted the
``D-IMPL-73`` posture: ``create_app`` with no auth hook built an application
that performed no authentication, emitted a ``CcfInsecureDefaultWarning`` at
construction and one logging WARNING at the first request, and could be
silenced with ``acknowledge_insecure_default=True``.

That ruling is withdrawn. The reason the old suite is **replaced rather than
adapted** is what the warning was measured to be worth: a warning is only a
gate if something escalates it, and this repository holds **zero**
``filterwarnings`` directives — measured by
:func:`test_no_filterwarnings_directive_ever_escalated_the_warning` below,
which greps the configuration rather than remembering. So the posture shipped
behind a signal that nothing in CI ever read.

What this file asserts instead, drafted from what would fail here:

==========================================  ==================================
Requirement                                 What would fail here
==========================================  ==================================
no unauthenticated arm                      ``auth`` would take ``None``, or
                                            carry a default
no acknowledgment switch                    the kwarg would be back, under
                                            any spelling
the warning classes are gone                a caller could still import them
                                            and believe the posture exists
the three D-IMPL-73-justified optionals     ``product_entitlement``,
are required                                ``perspective_resolver`` or
                                            ``refusal_recorder`` would carry
                                            a default whose justification was
                                            deleted with the ruling
the served posture sentence is honest       the document would still tell an
                                            adopter the API authenticates
                                            nothing
no permissive authorizer ships              a dev/allow-all authorizer would
                                            be importable from the library
==========================================  ==================================
"""

from __future__ import annotations

import inspect
import pathlib
import re
from tests.composition import declared_erasure_trust, no_erasures
from typing import Any

import pytest

from ccf_runtime.http_api.app import AUTH_POSTURE_SENTENCE, create_app

from .conftest import Fabric

#: The repository root, for the configuration grep below.
_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestTheSignatureHasNoInsecureArm:
    def test_required_parameters_have_no_default(self) -> None:
        signature = inspect.signature(create_app)
        without_default = {
            name
            for name, parameter in signature.parameters.items()
            if parameter.default is inspect.Parameter.empty
            and name != "deps"
        }
        assert without_default == {
            "auth",
            "authorizer",
            "product_entitlement",
            "perspective_resolver",
            "refusal_recorder",
            # Required, not optional (`SEC-017`; `D-IMPL-374`): every
            # keyword-only parameter of `create_app` is required
            # (`D-IMPL-353` §4 rule 1). Its value may be `None` (see the next
            # test); the argument may not be omitted.
            "replay_record_product_class",
        }

    def test_no_parameter_accepts_none(self) -> None:
        """``| None`` on any of the five would re-open the arm by typing.

        One parameter is typed ``| None`` BY RULING and is named here rather
        than hidden: ``replay_record_product_class`` (``SEC-017``;
        ``D-IMPL-374`` (2), fix round 1). It is REQUIRED — the test above holds
        that — and ``None`` is a value the deployment passes. It is not an
        insecure arm: given ``None``, a bearer with a declared product roster
        is REFUSED every replay read, so ``None`` there fails closed. Every
        other parameter stays held to the original rule, including any added
        later.
        """
        signature = inspect.signature(create_app)
        optional = [
            name
            for name, parameter in signature.parameters.items()
            if name not in {"deps", "replay_record_product_class"}
            and "None" in str(parameter.annotation)
        ]
        assert optional == []

    def test_the_acknowledgment_switch_is_gone(self) -> None:
        assert "acknowledge_insecure_default" not in inspect.signature(
            create_app
        ).parameters

    @pytest.mark.parametrize(
        "name",
        [
            "CcfInsecureDefaultWarning",
            "CcfDeadAuthorizerWarning",
            "CcfDeadEntitlementWarning",
        ],
    )
    def test_the_warning_classes_are_gone(self, name: str) -> None:
        """Deleted, not deprecated: an importable class is a live posture."""
        import ccf_runtime.http_api.app as module

        assert not hasattr(module, name)

    def test_omitting_authority_is_a_type_error(self, fabric: Fabric) -> None:
        from ccf_runtime.http_api.dependencies import ApiDependencies

        with pytest.raises(TypeError):
            create_app(  # type: ignore[call-arg]
                ApiDependencies(erasure_index=no_erasures(), erasure_trust=declared_erasure_trust(), 
                    control_plane=fabric.registry,
                    artifact_store=fabric.store,
                    product_resolver=fabric.product_resolver,
                )
            )


class TestTheWarningWasNeverAGate:
    def test_no_filterwarnings_directive_ever_escalated_the_warning(
        self,
    ) -> None:
        """The measurement behind deleting rather than escalating.

        Population: every ``pyproject.toml``, ``setup.cfg``, ``pytest.ini``,
        ``tox.ini`` and ``Makefile`` in the repository root tree, plus every
        workflow file under ``.github/``. If a later phase adds a
        ``filterwarnings`` escalation this test goes red, which is the
        correct outcome: the claim in this module's docstring would then be
        stale.
        """
        candidates = [
            *_ROOT.glob("pyproject.toml"),
            *_ROOT.glob("setup.cfg"),
            *_ROOT.glob("pytest.ini"),
            *_ROOT.glob("tox.ini"),
            *_ROOT.glob("Makefile"),
            *_ROOT.glob(".github/**/*.yml"),
            *_ROOT.glob(".github/**/*.yaml"),
        ]
        assert candidates, "the population is empty; the globs are wrong"
        carrying = [
            str(path.relative_to(_ROOT))
            for path in candidates
            if "filterwarnings" in path.read_text(encoding="utf-8")
        ]
        assert carrying == []


class TestTheServedPostureIsHonest:
    def test_the_sentence_says_the_api_authenticates(self) -> None:
        assert AUTH_POSTURE_SENTENCE == (
            "Every request to this API is authenticated and authorized before"
            " it is routed: there is no unauthenticated arm, no path is"
            " exempt, every route declares the action identifier its"
            " authorization is decided under, and what each action reaches is"
            " the deployment's own versioned scope mapping rather than any"
            " default this API ships."
        )

    def test_the_document_carries_it_verbatim(self, app: Any) -> None:
        assert AUTH_POSTURE_SENTENCE in app.openapi()["info"]["description"]

    def test_the_withdrawn_sentence_appears_nowhere_in_the_runtime(
        self,
    ) -> None:
        """The old sentence claimed the opposite; it must not survive.

        Population: every ``.py`` file under ``runtime/``.
        """
        stale = re.compile("performs no authentication or authorization")
        found = [
            str(path.relative_to(_ROOT))
            for path in (_ROOT / "runtime").rglob("*.py")
            if stale.search(path.read_text(encoding="utf-8"))
        ]
        assert found == []


class TestNoPermissiveAuthorizerShips:
    def test_every_exported_authorizer_denies_against_an_empty_plane(
        self,
    ) -> None:
        """By construction, not by convention (``SEC-001``).

        Population: every public class in :mod:`ccf_runtime.authz.protocol`
        carrying an ``authorize`` method. Each is constructed against an
        **empty** Control Plane and asked; an authorizer that answered
        ``allowed=True`` there would be a permissive one, whatever it was
        called.

        The positive control is in the same assertion: the one implementation
        that exists is exercised, so a population that had silently become
        empty would fail the ``assert examined`` below rather than pass
        vacuously.
        """
        from datetime import UTC, datetime

        import ccf_runtime.authz.protocol as protocol
        from ccf.controlplane.registry import ControlPlaneRegistry
        from ccf_runtime.mcp.auth import TokenGrant

        examined: list[str] = []
        for name in protocol.__all__:
            candidate = getattr(protocol, name)
            if not inspect.isclass(candidate):
                continue
            if not callable(getattr(candidate, "authorize", None)):
                continue
            if getattr(candidate, "_is_protocol", False):
                continue
            examined.append(name)
            authorizer = candidate(
                control_plane=ControlPlaneRegistry(),
                scope_mapping_key="absent/mapping",
                scope_mapping_version="1",
                clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
            )
            decision = authorizer.authorize(
                grant=TokenGrant(client_id="anyone", scopes=("any",)),
                tenant="any-tenant",
                action_id="any.action",
                resource="any-resource",
            )
            assert decision.allowed is False, (
                f"{name} allowed against an empty Control Plane"
            )
        assert examined == ["ControlPlaneTenantAuthorizer"]
