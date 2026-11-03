#!/usr/bin/env python3
"""The no-LEI gate must be able to FAIL, and must prove the old floors were blind.

This gap was invisible for the whole life of the estate, and not because
nobody looked. Its predecessor §C row was marked COVERED against
`conditions.py`'s crosswalk floors, and every one of those floors is keyed on
LEI:

    SELECT COUNT(*) FROM crosswalk c JOIN legal_entity e USING (lei)

An inner join on the very property this population LACKS cannot report its
absence. It was a gate selecting by the property it polices, and it returned a
healthy 50 throughout.

So the arms here do two jobs: the ordinary one, and the one that matters --
asserting the LEI-keyed floor STILL cannot see these clients, which is what
makes the new gate necessary rather than decorative.

    uv run --with pytest pytest validators/test_internal_client.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "internal_client", REPO / "validators" / "internal_client.py")
ic = importlib.util.module_from_spec(_spec)
sys.modules["internal_client"] = ic
_spec.loader.exec_module(ic)

LEI_TTL_HOURS = 24


def test_a_client_with_name_and_jurisdiction_resolves():
    assert ic.resolves({"legal_name": "Halbrook Ltd",
                        "legal_jurisdiction": "GB"})


def test_a_client_with_no_name_does_not_resolve():
    """THE FALSIFIER. A row that exists and carries nothing is the shape this
    gap would take if it were 'closed' by inserting empty identifiers."""
    assert not ic.resolves({"legal_name": None, "legal_jurisdiction": "GB"})


def test_a_client_with_a_blank_name_does_not_resolve():
    assert not ic.resolves({"legal_name": "   ", "legal_jurisdiction": "GB"})


def test_a_client_with_no_jurisdiction_does_not_resolve():
    assert not ic.resolves({"legal_name": "Halbrook Ltd",
                            "legal_jurisdiction": None})


# --- the freshness ceiling §G's acceptance criterion turns on --------------

def test_a_months_long_ceiling_is_lower_than_the_lei_ceiling():
    """§D: LEI-registered entities refresh in 24 HOURS; private no-LEI clients
    on a KYC cadence of MONTHS. 'Lower ceiling' means staler-permitted, so the
    no-LEI number must be the LARGER duration."""
    assert ic.reports_lower_ceiling(ceiling_days=180, lei_ttl_hours=LEI_TTL_HOURS)


def test_a_ceiling_shorter_than_the_lei_ttl_is_not_a_lower_ceiling():
    """A no-LEI client claiming an hourly refresh has been given the public
    entity's SLA, which is the misreporting §G exists to catch."""
    assert not ic.reports_lower_ceiling(ceiling_days=0,
                                        lei_ttl_hours=LEI_TTL_HOURS)


# --- the blindness proof ---------------------------------------------------

def test_an_lei_keyed_join_cannot_see_a_no_lei_client():
    """THE ARM THAT MATTERS.

    Hand-built rather than live so the claim is about the JOIN, not about
    today's data: an inner join on `lei` drops every row whose `lei` is NULL,
    however many of them there are. That is why the old floor read 50 and
    healthy while this population was 0, and why it would still read healthy
    now that the population is 30.
    """
    crosswalk = [{"internal_client_id": "CLI-000001", "lei": "REALLEI0000000000001"},
                 {"internal_client_id": "CLI-000101", "lei": None},
                 {"internal_client_id": "CLI-000102", "lei": None}]
    entities = [{"lei": "REALLEI0000000000001"}]
    assert ic.lei_keyed_join_count(crosswalk, entities) == 1
    assert ic.no_lei_clients(crosswalk) == 2


def test_the_blindness_is_total_not_partial():
    """Every no-LEI client is invisible to the LEI-keyed join, not merely
    most -- so the floor cannot degrade gracefully into a partial warning."""
    crosswalk = [{"internal_client_id": f"CLI-{i:06d}", "lei": None}
                 for i in range(101, 131)]
    assert ic.lei_keyed_join_count(crosswalk, []) == 0
    assert ic.no_lei_clients(crosswalk) == 30
