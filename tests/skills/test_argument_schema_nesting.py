"""``SkillArgumentSchema`` widened to one level of nesting (D-IMPL-103).

Dave ruled branch (i) — *extend in place* — with two bounds this module holds
separately, because either one read loosely turns the ruling into a different
one:

* **one level of nesting is the ceiling.** Nested objects and lists-of-objects,
  one deep. Depth 3 and a list of lists are refused, and refused
  *structurally* — the nested types have no nesting fields to fill in, so the
  ceiling is not a rule a later author can relax;
* **a widening, not a replacement.** Every existing depth-1 declaration stays
  valid, unchanged, and renders byte-identically through
  :meth:`~ccf.skills.catalog.SkillArgumentSchema.to_input_schema`.

The second bound is the one a widening most easily breaks and the one nothing
else in the suite would catch, so it is asserted first and asserted on the
rendered surface rather than on the model: an adapter consumes the render, not
the fields.

Requirement CPS-03.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema


def _leaf(json_type: str, description: str) -> SkillArgumentProperty:
    return SkillArgumentProperty.model_validate(
        {"type": json_type, "description": description}
    )


class TestTheWideningIsAWideningAndNotAReplacement:
    """Bound 2 of D-IMPL-103: existing depth-1 usages remain valid."""

    def test_a_depth_one_declaration_still_validates_unchanged(self) -> None:
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "counterparty": {"type": "string", "description": "URI"}
                },
                "required": ["counterparty"],
            }
        )
        assert set(schema.properties) == {"counterparty"}
        assert schema.required == ("counterparty",)

    def test_a_depth_one_declaration_renders_exactly_as_before(self) -> None:
        """The rendered surface is what every harness adapter consumes.

        Byte-for-byte the pre-widening shape: no ``properties``, ``items`` or
        ``required`` key appears on a leaf property because the widening's new
        fields are unset, and an unset nesting field is not a declaration.
        """
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "counterparty": {"type": "string", "description": "URI"}
                },
                "required": ["counterparty"],
            }
        )
        assert schema.to_input_schema() == {
            "type": "object",
            "properties": {"counterparty": {"type": "string", "description": "URI"}},
            "required": ["counterparty"],
            "additionalProperties": False,
        }

    def test_a_leaf_property_is_constructible_from_two_fields(self) -> None:
        assert _leaf("string", "URI").properties is None
        assert _leaf("string", "URI").items is None
        assert _leaf("string", "URI").required == ()


class TestOneLevelOfNestingIsExpressible:
    """Bound 1, the permissive half: the three facts flattening lost."""

    def test_an_object_valued_property_declares_its_own_properties(self) -> None:
        """``ownership_percent_by_party`` — an object keyed by party URI."""
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "ownership": {
                        "type": "object",
                        "description": "ownership by party",
                        "properties": {
                            "party_uri": {"type": "string", "description": "URI"},
                            "percent": {"type": "number", "description": "share"},
                        },
                        "required": ["party_uri"],
                    }
                },
                "required": ["ownership"],
            }
        )
        nested = schema.properties["ownership"]
        assert nested.properties is not None
        assert set(nested.properties) == {"party_uri", "percent"}
        assert nested.required == ("party_uri",)

    def test_a_list_of_objects_is_expressible(self) -> None:
        """``beneficial_owners`` — the UBO owner list the ruling names."""
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "beneficial_owners": {
                        "type": "array",
                        "description": "UBO list",
                        "items": {
                            "type": "object",
                            "description": "one owner",
                            "properties": {
                                "party_uri": {
                                    "type": "string",
                                    "description": "URI",
                                },
                                "percent": {
                                    "type": "number",
                                    "description": "share",
                                },
                            },
                            "required": ["party_uri", "percent"],
                        },
                    }
                },
                "required": ["beneficial_owners"],
            }
        )
        items = schema.properties["beneficial_owners"].items
        assert items is not None
        assert items.properties is not None
        assert set(items.properties) == {"party_uri", "percent"}

    def test_a_list_of_primitives_is_expressible(self) -> None:
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "tags": {
                        "type": "array",
                        "description": "labels",
                        "items": {"type": "string", "description": "one label"},
                    }
                },
                "required": [],
            }
        )
        items = schema.properties["tags"].items
        assert items is not None
        assert items.type == "string"

    def test_nesting_renders_losslessly_and_closed_at_every_object(self) -> None:
        """``additionalProperties`` is false at *every* object level.

        The closed world is part of the contract rather than a renderer option
        (D-IMPL-56), and a nested object left open would be a hole in exactly
        the surface this widening creates.
        """
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "beneficial_owners": {
                        "type": "array",
                        "description": "UBO list",
                        "items": {
                            "type": "object",
                            "description": "one owner",
                            "properties": {
                                "party_uri": {
                                    "type": "string",
                                    "description": "URI",
                                }
                            },
                            "required": ["party_uri"],
                        },
                    }
                },
                "required": ["beneficial_owners"],
            }
        )
        rendered = schema.to_input_schema()
        item_schema = rendered["properties"]["beneficial_owners"]["items"]
        assert item_schema["additionalProperties"] is False
        assert item_schema["required"] == ["party_uri"]
        assert item_schema["properties"] == {
            "party_uri": {"type": "string", "description": "URI"}
        }

    def test_a_nested_schema_is_hashable(self) -> None:
        """Entry hashing walks the schema; catalog discovery compares sets."""
        schema = SkillArgumentSchema.model_validate(
            {
                "properties": {
                    "ownership": {
                        "type": "object",
                        "description": "ownership by party",
                        "properties": {
                            "party_uri": {"type": "string", "description": "URI"}
                        },
                        "required": ["party_uri"],
                    }
                },
                "required": ["ownership"],
            }
        )
        assert isinstance(hash(schema), int)
        assert hash(schema) == hash(schema.model_copy(deep=True))


class TestTheCeilingIsOneLevel:
    """Bound 1, the refusing half: depth 2 is the ceiling, not a floor.

    The ceiling is **structural**, not a validator: the nested types are
    :class:`~ccf.skills.catalog.SkillArgumentMember` (no nesting fields at
    all) and :class:`~ccf.skills.catalog.SkillArgumentElement` (members but no
    ``items``), so a third level and a list of lists are not declarations the
    contract can express. These cases therefore assert a refusal without
    matching the ruling's number in the message — a structural impossibility
    refuses as ``extra=forbid``, which is a stronger guarantee than a rule a
    later author can relax, and asserting on a message would have made the
    weaker implementation the passing one.
    """

    def test_an_object_inside_an_object_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SkillArgumentSchema.model_validate(
                {
                    "properties": {
                        "outer": {
                            "type": "object",
                            "description": "outer",
                            "properties": {
                                "inner": {
                                    "type": "object",
                                    "description": "inner",
                                    "properties": {
                                        "leaf": {
                                            "type": "string",
                                            "description": "leaf",
                                        }
                                    },
                                }
                            },
                        }
                    },
                    "required": [],
                }
            )

    def test_a_list_of_objects_of_objects_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SkillArgumentSchema.model_validate(
                {
                    "properties": {
                        "owners": {
                            "type": "array",
                            "description": "owners",
                            "items": {
                                "type": "object",
                                "description": "one owner",
                                "properties": {
                                    "address": {
                                        "type": "object",
                                        "description": "nested object",
                                        "properties": {
                                            "city": {
                                                "type": "string",
                                                "description": "city",
                                            }
                                        },
                                    }
                                },
                            },
                        }
                    },
                    "required": [],
                }
            )

    def test_a_list_of_lists_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            SkillArgumentSchema.model_validate(
                {
                    "properties": {
                        "matrix": {
                            "type": "array",
                            "description": "rows",
                            "items": {
                                "type": "array",
                                "description": "row",
                                "items": {
                                    "type": "number",
                                    "description": "cell",
                                },
                            },
                        }
                    },
                    "required": [],
                }
            )


class TestTheNestingKeywordsAgreeWithTheDeclaredType:
    """A declaration whose keyword contradicts its type is malformed."""

    def test_properties_on_a_non_object_property_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="object"):
            SkillArgumentProperty.model_validate(
                {
                    "type": "string",
                    "description": "a string",
                    "properties": {
                        "nope": {"type": "string", "description": "nope"}
                    },
                }
            )

    def test_items_on_a_non_array_property_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="array"):
            SkillArgumentProperty.model_validate(
                {
                    "type": "object",
                    "description": "an object",
                    "items": {"type": "string", "description": "nope"},
                }
            )

    def test_a_nested_required_name_that_is_not_declared_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="required"):
            SkillArgumentProperty.model_validate(
                {
                    "type": "object",
                    "description": "an object",
                    "properties": {
                        "declared": {"type": "string", "description": "yes"}
                    },
                    "required": ["undeclared"],
                }
            )

    def test_a_required_name_without_any_properties_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="required"):
            SkillArgumentProperty.model_validate(
                {
                    "type": "string",
                    "description": "a string",
                    "required": ["anything"],
                }
            )
