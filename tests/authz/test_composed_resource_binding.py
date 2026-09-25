"""The composed body resource binding (D-IMPL-353 §1.2 at the HTTP door; the join).

The artifact store takes the class and the name of a write from the
capability's resource, ``"<class>/<name>"``, so the HTTP gate must decide on
exactly that string — spelled from two body fields. ``ResourceBinding.body``
names ONE field; :meth:`ResourceBinding.body_composed` names a ``str.format``
template over several, the HTTP counterpart of the MCP wrapper's
``resource_composed``. Every claim below is drafted from what would fail:

=====================================  =====================================
Claim                                  What would fail here
=====================================  =====================================
a template names at least one field    a literal-only template would let the
                                       request pick nothing and the deploy-
                                       ment authorize a constant
positional / attribute fields refused  ``{0}`` or ``{a.b}`` would reach into
                                       the body in ways a scope mapping never
                                       named
the gate formats over declared names   a body field the template did not name
                                       cannot reach the resource
a missing or empty field is a deny     the caller chooses what to send; every
                                       choice leads to the check running
the positive control at the door       the authorizer is asked with the com-
                                       posed string, and the store files
                                       under exactly it
=====================================  =====================================
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from ccf_runtime.authz.route_declaration import (
    ResourceBinding,
    ResourceSource,
    composed_fields,
)


# --- the grammar -------------------------------------------------------------


@pytest.mark.parametrize(
    ("template", "fields"),
    [
        ("{artifact_class}/{name}", ("artifact_class", "name")),
        ("{tenant}/ccf.skill-catalog-entry/{name}", ("tenant", "name")),
        ("{only}", ("only",)),
    ],
)
def test_composed_fields_names_the_body_fields_in_order(
    template: str, fields: tuple[str, ...]
) -> None:
    assert composed_fields(template) == fields


@pytest.mark.parametrize(
    "template",
    [
        "no fields at all",
        "",
        "{}",
        "{0}/{1}",
        "{a.b}",
        "{a[0]}",
        "{unbalanced",
        "{not-an-identifier}",
    ],
)
def test_a_template_naming_nothing_usable_is_refused(template: str) -> None:
    assert composed_fields(template) == ()
    with pytest.raises(ValueError, match="BODY_COMPOSED"):
        ResourceBinding.body_composed(template)


def test_body_composed_is_its_own_source() -> None:
    binding = ResourceBinding.body_composed("{artifact_class}/{name}")
    assert binding.source is ResourceSource.BODY_COMPOSED
    assert binding.name == "{artifact_class}/{name}"
    # The single-field form is untouched.
    assert ResourceBinding.body("name").source is ResourceSource.BODY


# --- the gate's extraction ---------------------------------------------------


@dataclass
class _Entry:
    """The one attribute of a route-table entry ``_resource`` reads."""

    declaration: Any


@dataclass
class _Declaration:
    resource: ResourceBinding
    action_id: str = "test.action"


def _receive_for(body: bytes) -> Any:
    delivered = {"done": False}

    async def receive() -> dict[str, Any]:
        if delivered["done"]:
            return {"type": "http.disconnect"}
        delivered["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _extract(binding: ResourceBinding, body: object) -> str | None:
    """Run the gate's own extraction over ``body``."""
    from ccf_runtime.http_api.gate import AuthorizationGate

    gate = AuthorizationGate.__new__(AuthorizationGate)
    resource, _replay = asyncio.run(
        gate._resource(
            {"type": "http", "query_string": b""},
            _receive_for(json.dumps(body).encode("utf-8")),
            entry=_Entry(declaration=_Declaration(resource=binding)),
            path_parameters={},
        )
    )
    return resource


def test_the_gate_composes_exactly_the_declared_fields() -> None:
    binding = ResourceBinding.body_composed("{artifact_class}/{name}")
    assert _extract(binding, {"artifact_class": "c", "name": "n", "artifact": {}}) == "c/n"


@pytest.mark.parametrize(
    "body",
    [
        {"artifact_class": "c"},  # name absent
        {"artifact_class": "c", "name": ""},  # name empty
        {"artifact_class": "", "name": "n"},  # class empty
        {"artifact_class": "c", "name": 7},  # not a string
        {"artifact_class": ["c"], "name": "n"},
        [],  # not an object
        "c/n",  # a string the caller composed itself
    ],
)
def test_a_field_the_template_needs_that_the_body_cannot_supply_is_a_deny(
    body: object,
) -> None:
    binding = ResourceBinding.body_composed("{artifact_class}/{name}")
    assert _extract(binding, body) is None


def test_a_body_field_the_template_did_not_name_cannot_reach_the_resource() -> None:
    """``str.format`` sees only the declared names, so a stray ``{`` in the
    body's other fields, or an extra field, changes nothing."""
    binding = ResourceBinding.body_composed("{artifact_class}/{name}")
    assert (
        _extract(
            binding,
            {"artifact_class": "c", "name": "n", "tenant": "other", "x": "{name}"},
        )
        == "c/n"
    )


def test_the_single_field_body_binding_is_unchanged() -> None:
    assert _extract(ResourceBinding.body("key"), {"key": "t/k/v"}) == "t/k/v"
    assert _extract(ResourceBinding.body("key"), {"key": ""}) is None
