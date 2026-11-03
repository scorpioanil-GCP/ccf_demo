#!/usr/bin/env python3
"""Wave 18 — verify the `SEC/Debt/DistributedLoans/` terms against the local
FIBO ontology, and settle the two open semantic questions in Task 4.

**Never fetch spec.edmcouncil.org for this.** A URL there returns HTTP 200 for
names that were never declared ("EDM Council URLs resolve for fake terms") —
that is exactly how a module name gets mistaken for a binding. This script
reads only `sources/fibo/dev.fibo-quickstart.ttl` (`dev`, not `prod` —
`prod.fibo-quickstart.ttl` omits 40 modules, several of which this project
already binds) and asserts presence by **subject position**: a term counts as
declared only when it opens its own Turtle block (`prefix:Local` alone at the
start of a line), never when it merely appears as the object of someone
else's triple. `SyndicateMember` is referenced inside `FinanceSyndicateMember`'s
own restriction as an `allValuesFrom`/`someValuesFrom` value — a substring
search over the whole file would count that as a hit for terms that are only
ever *mentioned*, never declared, which is precisely the false-presence shape
CLAUDE.md's binding protocol exists to catch.

For every object property this prints `rdfs:domain` and `rdfs:range` so a
name that reads right and means something else — `fibo-loan-ln-reg:administeredBy`
is scoped to a regulator overseeing a rule, not a facility's admin agent — is
visible in the output, not just asserted in prose.

Run: uv run generators/verify_fibo_wave18.py
Exit: non-zero if any claimed-FIBO term is not declared in the ontology, or if any
term minted under ex: turns out to collide with a real declared FIBO term.
"""

from __future__ import annotations

import re
import sys

from ccf.config import REPO_ROOT

ONTOLOGY = REPO_ROOT / "sources" / "fibo" / "dev.fibo-quickstart.ttl"

#: A term unambiguously declared in every FIBO distribution. If this cannot be
#: found in subject position, the file is not being read correctly and no
#: other answer here can be trusted.
POSITIVE_CONTROL = "cmns-org:LegalEntity"

# ---------------------------------------------------------------------------
# The terms Wave 18 uses. `decision` records what this run concludes about
# each — not asserted ahead of the check, printed alongside it.
# ---------------------------------------------------------------------------

CLASSES: list[dict] = [
    {
        "qname": "fibo-sec-dbt-dln:SyndicatedLoan",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — SyndicatedFacility binds here",
    },
    {
        "qname": "fibo-sec-dbt-dln:FinanceSyndicate",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — the syndicate itself",
    },
    {
        "qname": "fibo-sec-dbt-dln:FinanceSyndicateMember",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — SyndicateMember binds here, NOT the two traps below",
    },
    {
        "qname": "fibo-sec-dbt-dln:AdministrativeAgent",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — administrative-agent role type",
    },
    {
        "qname": "fibo-sec-dbt-dln:LeadArranger",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — arranger role, if used",
    },
    {
        "qname": "fibo-sec-dbt-dln:Bookrunner",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — arranger role, if used",
    },
    {
        "qname": "fibo-sec-dbt-dln:SyndicationAgent",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — arranger role, if used",
    },
    {
        "qname": "fibo-sec-dbt-dln:DocumentationAgent",
        "group": "SYNDICATE STRUCTURE",
        "decision": "ADOPT — arranger role, if used",
    },
    {
        "qname": "fibo-fnd-agr-agr:Commitment",
        "group": "COMMITMENT",
        "decision": "ADOPT — a promise-to-act situation; commitment SHARE amount "
                    "is still ex: (see object properties)",
    },
    {
        "qname": "fibo-be-fct-fct:SyndicateMember",
        "group": "SYNDICATEMEMBER TRAP — confirm, do not use",
        "decision": "TRAP #2a — generic syndicate-member role, parent of "
                    "FinanceSyndicateMember but not itself the lending term",
    },
    {
        "qname": "fibo-bp-iss-ipo:SyndicateMember",
        "group": "SYNDICATEMEMBER TRAP — confirm, do not use",
        "decision": "TRAP #2b — IPO underwriting syndicate member; unrelated "
                    "PartyRole, no connection to lending",
    },
    {
        "qname": "fibo-be-fct-fct:Syndicate",
        "group": "MEMBERSHIP QUESTION — supporting evidence",
        "decision": "supporting — carries the restriction "
                    "cmns-col:hasMember someValuesFrom cmns-pts:Party, whose "
                    "inverse is cmns-col:isMemberOf",
    },
]

OBJECT_PROPERTIES: list[dict] = [
    {
        "qname": "cmns-col:isMemberOf",
        "group": "MEMBERSHIP QUESTION",
        "decision": "ADOPT — no domain/range restriction of its own; "
                    "FinanceSyndicateMember's own OWL restriction "
                    "(isPlayedBy/isMemberOf/allValuesFrom FinanceSyndicate) "
                    "and Syndicate's hasMember restriction both use it. Mint "
                    "nothing.",
    },
    {
        "qname": "cmns-col:hasMember",
        "group": "MEMBERSHIP QUESTION — supporting evidence",
        "decision": "supporting — declared inverse of isMemberOf; this is the "
                    "property Syndicate's own restriction uses",
    },
    {
        "qname": "cmns-rlcmp:isPlayedBy",
        "group": "MEMBERSHIP QUESTION — supporting evidence",
        "decision": "supporting — domain cmns-rlcmp:Role; the outer layer of "
                    "FinanceSyndicateMember's restriction, not itself the "
                    "membership edge",
    },
    {
        "qname": "fibo-loan-ln-reg:administeredBy",
        "group": "ADMINISTERED-BY TRAP",
        "decision": "TRAP #1a — domain LoanRegulatoryRequirement, range "
                    "cmns-rga:RegulatoryAgency. A regulator overseeing a "
                    "rule. NOT our facility-administered-by-agent.",
    },
    {
        "qname": "fibo-sec-fund-civ:administeredBy",
        "group": "ADMINISTERED-BY TRAP",
        "decision": "TRAP #1b — domain CollectiveInvestmentVehicle, range "
                    "FundAdministrator. A fund's administrator. Also NOT "
                    "ours — found while checking #1a, same local name.",
    },
]

#: Fix round 1 (T4-R1). Task 8 will build a REIFIED participation node — a
#: plain triple cannot carry an amount plus a filing offset, so the node
#: needs its own type and two connecting predicates. Left unbound, Task 8
#: invents unbound local names at generation time, exactly the failure
#: CLAUDE.md's binding protocol exists to prevent. Each local name below was
#: checked absent from the ontology under EVERY prefix, not just the ones
#: this task otherwise uses — a bare local-name collision under some other
#: FIBO module would be exactly as wrong as reusing `administeredBy`'s local
#: name was almost wrong.
EX_MINTED_CHECKED_ABSENT: list[dict] = [
    {
        "local": "SyndicateParticipation",
        "note": "the reified node type — member, facility, commitment "
                "amount, and the filing offset it was read from, as one "
                "n-ary fact. Required explicitly: Fluree runs without OWL "
                "inference (CLAUDE.md rule 7), so a query for "
                "participations must find only nodes typed as one.",
    },
    {
        "local": "participationOf",
        "note": "participation node -> the FinanceSyndicateMember",
    },
    {
        "local": "participationIn",
        "note": "participation node -> the fibo-sec-dbt-dln:SyndicatedLoan",
    },
    {
        "local": "AmendmentEvent",
        "note": "Task 9 -- a dated, filed amendment/restatement event on a "
                "Wave 18 facility. Deliberately DISTINCT from the existing "
                "`ex:Amendment` (Wave 5, load_temporal_wave5.py, 25 "
                "assertions, covenant-in-force-as-of's own bitemporal "
                "chain) -- reusing that class would inflate a different "
                "product's population with facilities it never touches.",
    },
    {
        "local": "effectiveDate",
        "note": "Task 9 -- literal ISO date on an AmendmentEvent. "
                "`fibo-fnd-agr-ctr:hasEffectiveDate` DOES exist (checked, "
                "found) but is an owl:ObjectProperty ranging over the "
                "reified class cmns-dt:Date, not a literal -- every "
                "temporal predicate this estate has ever written "
                "(ex:validFrom, ex:assertedAt, Wave 5/6/7's own "
                "effective-date fields) carries a plain literal instead, "
                "and introducing the one reified exception here for no "
                "benefit besides 'it exists' is the module-membership trap "
                "CLAUDE.md warns against. Rejected; ex: minted instead.",
    },
    {
        "local": "AmendmentVote",
        "note": "Task 9 -- the live, open vote node itself, distinct from "
                "a dated AmendmentEvent (a vote in progress has no "
                "effective date yet).",
    },
    {
        "local": "voteState",
        "note": "Task 9 -- 'open' (only value used this wave) on an "
                "AmendmentVote node.",
    },
    {
        "local": "envelopeVersion",
        "note": "Task 10 -- a version label literal on a "
                "DisclosureEnvelope node. No existing predicate carries a "
                "bare version LABEL on an arbitrary node -- the "
                "PolicyVersion pattern (Waves 5/12/13a) models version as "
                "its own NODE type, a different shape.",
    },
    {
        "local": "counterparty",
        "note": "Task 10 -- DisclosureEnvelope -> the FinanceSyndicateMember "
                "it is negotiated with. `fibo-fnd-agr-ctr:Counterparty` "
                "(bound in the v2 table's Wave 0 section) is a PARTY ROLE "
                "class, not a predicate -- it cannot supply the edge itself.",
    },
    {
        "local": "AmendmentThreshold",
        "note": "Task 11b -- the R half of \"Voting thresholds and "
                "amendment mechanics\" (§C: MongoDB + Fluree, L + R). No "
                "vote/consent/threshold/quorum/majority vocabulary exists "
                "anywhere in the ontology, and neither SEC/Debt/"
                "DistributedLoans/ nor FND/Agreements/Contracts/ (this "
                "estate's other agreement-law module) has an amendment- or "
                "consent-provision class among their declared classes.",
    },
    {
        "local": "consentStandard",
        "note": "Task 11b -- the standard a filing names for a threshold "
                "(\"Required Lenders\", \"each affected Lender\", \"all "
                "Lenders\", ...), on an AmendmentThreshold node.",
    },
    {
        "local": "consentPercent",
        "note": "Task 11b -- the numeric percentage a filing states for a "
                "percentage-of-exposure standard, present only when one is "
                "stated -- never invented for a per-Lender veto standard.",
    },
    {
        "local": "amendmentType",
        "note": "Task 11b -- which kinds of amendment/waiver require this "
                "consent standard, drawn from the filing's own enumerated "
                "carve-out list.",
    },
    {
        "local": "thresholdGoverns",
        "note": "Task 11b -- AmendmentThreshold -> the SyndicatedLoan "
                "facility it governs. Two REAL, DECLARED FIBO/Commons "
                "properties were checked and rejected for the bare word "
                "\"governs\": `cmns-rga:governs` (\"has and exercises "
                "authority over\" -- a regulator/polity over a "
                "jurisdiction) and `fibo-fnd-txn-sec:governs` (a "
                "SecuritiesTransactionContract over a secondary-market "
                "transaction) -- both real, both wrong domain. "
                "`cmns-cxtdsg:appliesTo` was checked and rejected too, "
                "same reason. `thresholdGoverns` avoids the collision "
                "outright.",
    },
]

ALL_TERMS = [(t, "class") for t in CLASSES] + [
    (t, "property") for t in OBJECT_PROPERTIES
]



def load_ontology() -> str:
    if not ONTOLOGY.exists():
        print(f"FATAL: {ONTOLOGY} does not exist.")
        print("This script never fetches spec.edmcouncil.org. Obtain the file")
        print("out of band (see ccf/fibo.py's _QUICKSTART_URLS) and re-run.")
        sys.exit(2)
    size = ONTOLOGY.stat().st_size
    if size < 5_000_000:
        print(f"FATAL: {ONTOLOGY} is only {size:,} bytes — too small to be "
              "the real dev quickstart (expect ~9MB). Refusing to answer any "
              "query against a truncated file.")
        sys.exit(2)
    return ONTOLOGY.read_text(errors="replace")


def find_block(text: str, qname: str) -> str | None:
    """The Turtle block opened by `qname` in SUBJECT position.

    Matches only a line that is `qname` and nothing else, then captures every
    following line up to (not including) the next line that starts in column
    zero with a non-whitespace character — the next top-level subject. A
    `qname` appearing only as an object (inside someone else's block, e.g. an
    `owl:allValuesFrom` value) is never in subject position and is not
    captured by this pattern at all.
    """
    pattern = re.compile(
        rf"^{re.escape(qname)}\n(.*?)(?=^\S|\Z)", re.M | re.S
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def find_any_prefix_subject(text: str, local_name: str) -> str | None:
    """The qname of ANY term declared as `<some-prefix>:local_name`.

    Used to check an `ex:` local name is safe to mint — a collision under a
    prefix this script never otherwise queries (e.g. a derivatives-module
    term) would be exactly as wrong as reusing `administeredBy`'s bare local
    name almost was. Subject position only, same discipline as `find_block`:
    a local name appearing only as an object is not a declaration.
    """
    pattern = re.compile(
        rf"^([A-Za-z][\w-]*:{re.escape(local_name)})$", re.M
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def extract_list(block: str, predicate: str) -> list[str]:
    """Every qname mentioned in the value of `predicate ... ;` in `block`.

    Values that are plain qnames come back exactly; values that are OWL
    restrictions (blank nodes) come back as every qname inside the
    restriction, which is deliberately shown as evidence rather than
    resolved — the restriction chain itself is what Task 4's membership
    question turns on.
    """
    m = re.search(rf"{re.escape(predicate)}\s+(.*?);", block, re.S)
    if not m:
        return []
    return re.findall(r"[A-Za-z][\w-]*:[A-Za-z][\w-]*", m.group(1))


def extract_label(block: str) -> str:
    m = re.search(r'rdfs:label\s+"([^"]*)"', block)
    return m.group(1) if m else ""


def main() -> int:
    print("Wave 18 — verifying SEC/Debt/DistributedLoans terms against "
          f"{ONTOLOGY.relative_to(REPO_ROOT)}\n")

    text = load_ontology()

    if find_block(text, POSITIVE_CONTROL) is None:
        print(f"FATAL: positive control {POSITIVE_CONTROL!r} not found in "
              "subject position. The file or the pattern is wrong — no "
              "'absent' answer below can be trusted until this passes.")
        return 2
    print(f"  positive control ok: {POSITIVE_CONTROL} declared\n")

    missing: list[str] = []
    by_group: dict[str, list[tuple[dict, str, str | None]]] = {}

    for term, kind in ALL_TERMS:
        block = find_block(text, term["qname"])
        by_group.setdefault(term["group"], []).append((term, kind, block))
        if block is None:
            missing.append(term["qname"])

    for group, rows in by_group.items():
        print(f"=== {group} ===")
        for term, kind, block in rows:
            qname = term["qname"]
            if block is None:
                print(f"  MISSING  {qname}  — not declared in subject "
                      "position anywhere in the ontology")
                continue
            label = extract_label(block)
            print(f"  ok       {qname}" + (f"  ({label})" if label else ""))
            if kind == "property":
                domain = extract_list(block, "rdfs:domain")
                rng = extract_list(block, "rdfs:range")
                print(f"             rdfs:domain: {domain or '(none declared)'}")
                print(f"             rdfs:range:  {rng or '(none declared)'}")
            else:
                subclass = extract_list(block, "rdfs:subClassOf")
                if subclass:
                    print(f"             rdfs:subClassOf (raw qnames incl. "
                          f"any restriction chain): {subclass}")
            print(f"             decision: {term['decision']}")
        print()

    n_ok = sum(1 for _, _, b in [(t, k, blk) for t, k in ALL_TERMS
                                   for blk in [find_block(text, t["qname"])]]
               if b is not None)
    print(f"  {n_ok}/{len(ALL_TERMS)} terms declared in subject position "
          f"({len(missing)} missing)\n")

    if missing:
        print("  MISSING terms must not be claimed as FIBO bindings:")
        for m in missing:
            print(f"    {m}")

    print("=== EX: TERMS CHECKED ABSENT BEFORE MINTING (reified participation node) ===")
    collisions: list[str] = []
    for entry in EX_MINTED_CHECKED_ABSENT:
        local = entry["local"]
        hit = find_any_prefix_subject(text, local)
        if hit is None:
            print(f"  ok       ex:{local}  — absent from the ontology under "
                  "every prefix; safe to mint")
        else:
            collisions.append(local)
            print(f"  COLLISION ex:{local}  — already declared as {hit!r}; "
                  "do NOT mint, use the existing term instead")
        print(f"             note: {entry['note']}")
    print(f"\n  {len(EX_MINTED_CHECKED_ABSENT) - len(collisions)}/"
          f"{len(EX_MINTED_CHECKED_ABSENT)} ex: terms confirmed absent and "
          f"safe to mint ({len(collisions)} collision(s))\n")

    if missing or collisions:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
