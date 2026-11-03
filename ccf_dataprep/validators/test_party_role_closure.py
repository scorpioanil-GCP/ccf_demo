"""The party-chain closure (known-issues §62), tested in both directions.

A closure check that always reports "no gaps" looks exactly like one that
works. Each check here is paired with an input it must reject.
"""
from __future__ import annotations

import json
import re

import pytest

from ccf.config import REPO_ROOT
from ccf.party_roles import (
    C_AGENT, C_CORPORATION, C_FORMAL_ORG, C_LEGAL_ENTITY, C_LEGAL_PERSON,
    C_ORGANIZATION, C_PARTY, C_SPV, SUPERCLASSES, ancestors, closure_gaps,
    missing_ancestors, with_ancestors,
)

ONTOLOGY = REPO_ROOT / "sources" / "fibo" / "dev.fibo-quickstart.ttl"
SCREEN = REPO_ROOT / "sources" / "screening"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
FULL_CHAIN = {C_LEGAL_ENTITY, C_FORMAL_ORG, C_LEGAL_PERSON,
              C_ORGANIZATION, C_PARTY, C_AGENT}


# --- the closure itself ----------------------------------------------------

def test_corporation_closes_to_all_seven_roles():
    assert set(with_ancestors(C_CORPORATION)) == FULL_CHAIN | {C_CORPORATION}


def test_spv_reaches_party_and_agent():
    assert {C_PARTY, C_AGENT, C_LEGAL_PERSON} <= ancestors(C_SPV)


def test_legal_entity_takes_both_parents():
    """The link v1 got wrong: LegalEntity sits under FormalOrganization AND
    LegalPerson. Losing either parent drops a route to Party."""
    assert {C_FORMAL_ORG, C_LEGAL_PERSON} <= ancestors(C_LEGAL_ENTITY)


def test_a_class_outside_the_chain_gains_nothing():
    other = "https://www.omg.org/spec/Commons/Organizations/ServiceProvider"
    assert ancestors(other) == frozenset()
    assert with_ancestors(other) == (other,)


# --- the gap detector: must say different things for different inputs ---

def test_detector_flags_the_measured_shape():
    """The exact shape found on ICJ-SPV-*: chain stopped at LegalEntity."""
    stopped = {C_SPV, C_LEGAL_ENTITY, C_FORMAL_ORG, C_ORGANIZATION}
    assert missing_ancestors(stopped) == {C_LEGAL_PERSON, C_PARTY, C_AGENT}


def test_detector_passes_a_closed_node():
    assert missing_ancestors(set(with_ancestors(C_SPV))) == frozenset()


def test_closure_gaps_reports_only_the_broken_node():
    gaps = closure_gaps({
        "ok": set(with_ancestors(C_CORPORATION)),
        "broken": set(with_ancestors(C_CORPORATION)) - {C_PARTY, C_AGENT},
    })
    assert set(gaps) == {"broken"}
    assert gaps["broken"] == {C_PARTY, C_AGENT}


# --- the chain matches the published ontology --------------------------------

PREFIXED = {
    C_AGENT: "cmns-pts:Agent", C_PARTY: "cmns-pts:Party",
    C_ORGANIZATION: "cmns-org:Organization",
    C_FORMAL_ORG: "cmns-org:FormalOrganization",
    C_LEGAL_PERSON: "cmns-org:LegalPerson",
    C_LEGAL_ENTITY: "cmns-org:LegalEntity",
    C_CORPORATION: "fibo-be-le-cb:Corporation",
    C_SPV: "fibo-be-le-lp:SpecialPurposeVehicle",
}


_NAMED = re.compile(r"^\t\t([\w-]+:\w+)\s*[,;]?$")


def _named_superclasses(lines: list[str], subject: str) -> set[str]:
    """The NAMED rdfs:subClassOf objects of `subject` in the quickstart Turtle.

    Restrictions (`[ ... ]`, three tabs deep) are excluded: a class that only
    appears as an `owl:onClass` inside one is not a superclass. The block ends
    at a line that is a bare `.` after its indent — the file writes it as
    TAB-dot, which an earlier version of this reader missed, running on into
    the next classes (caught by the negative control below).
    """
    start = lines.index(subject)
    out: set[str] = set()
    in_sub = False
    for line in lines[start + 1:]:
        if line.strip() == "." or line.rstrip().endswith(" ."):
            break
        if line.startswith("\t") and not line.startswith("\t\t"):
            in_sub = line.strip().startswith("rdfs:subClassOf")
            inline = line.strip().removeprefix("rdfs:subClassOf").strip(" ;,")
            if in_sub and inline:
                out.add(inline)
            continue
        if in_sub and (m := _NAMED.match(line)):
            out.add(m.group(1))
    return out


def test_every_link_is_published_in_fibo():
    """Each (sub, sup) pair must be a named superclass in the quickstart.
    A missing file FAILS rather than skips: an unchecked chain is the very
    failure this module exists to remove."""
    assert ONTOLOGY.exists(), f"{ONTOLOGY} missing; fetch it via ccf.fibo"
    lines = ONTOLOGY.read_text().splitlines()
    for sub, sups in SUPERCLASSES.items():
        named = _named_superclasses(lines, PREFIXED[sub])
        for sup in sups:
            assert PREFIXED[sup] in named, f"{PREFIXED[sub]} ⊑ {PREFIXED[sup]}"


def test_the_link_check_can_fail():
    """Negative control: Corporation's only named superclass is LegalEntity.
    Agent (an ancestor, not a direct parent) must NOT be reported, and the
    reader must return exactly one parent — not zero, not the next class's."""
    lines = ONTOLOGY.read_text().splitlines()
    assert _named_superclasses(lines, "fibo-be-le-cb:Corporation") == {
        "cmns-org:LegalEntity"}
    assert _named_superclasses(lines, "cmns-org:LegalEntity") == {
        "cmns-org:FormalOrganization", "cmns-org:LegalPerson"}


# --- the loaders now emit the closure ------------------------------------------

def _types_by_node(triples: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for t in triples:
        s, p, o = t.split(" ", 3)[:3]
        if p == f"<{RDF_TYPE}>":
            out.setdefault(s.strip("<>"), set()).add(o.strip("<>"))
    return out


def test_offshore_loader_emits_closed_types():
    from loaders.load_offshore_wave13b import build_triples

    doc = json.loads((SCREEN / "wave13b_offshore.json").read_text())
    triples, _ = build_triples(doc)
    nodes = _types_by_node(triples)
    assert nodes, "loader emitted no typed nodes — the test saw nothing"
    assert closure_gaps(nodes) == {}


def test_bo_chains_loader_emits_closed_types():
    from loaders.load_bo_chains_wave13b import build_triples

    doc = json.loads((SCREEN / "wave13b_bo_chains.json").read_text())
    nodes = _types_by_node(build_triples(doc, threshold=25.0))
    assert nodes, "loader emitted no typed nodes — the test saw nothing"
    assert closure_gaps(nodes) == {}


# --- the live ledger --------------------------------------------------------------

@pytest.fixture(scope="module")
def live_map():
    from ccf import fluree
    from ccf.party_roles import chain_type_map
    return chain_type_map(fluree.query)


def test_live_ledger_has_no_gaps(live_map):
    assert closure_gaps(live_map) == {}


def test_live_party_query_reaches_previously_hidden_nodes(live_map):
    """Named survivors of each broken population, found by a Party query."""
    ex = "http://example.org/fibo/"
    for local in ("ICJ-SPV-001", "ICJ-INT-001", "HLD-0001", "CycHarborstoneKy"):
        assert C_PARTY in live_map.get(ex + local, set()), local


def test_live_every_legal_entity_is_a_party(live_map):
    """The population check, counted independently of the gap detector."""
    le = {s for s, ts in live_map.items() if C_LEGAL_ENTITY in ts}
    party = {s for s, ts in live_map.items() if C_PARTY in ts}
    assert le and le <= party
