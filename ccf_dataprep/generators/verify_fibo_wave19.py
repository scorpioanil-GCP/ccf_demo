#!/usr/bin/env python3
"""Wave 19 — verify the `large-exposure-rwa-concentration` vocabulary against
the local FIBO ontology, and settle which "connected group" / regulatory-
regime / insider terms are genuinely absent and safe to mint under `ex:`.

**Never fetch spec.edmcouncil.org for this.** A URL there returns HTTP 200 for
names that were never declared ("EDM Council URLs resolve for fake terms") —
that is exactly how a module name gets mistaken for a binding. This script
reads only `sources/fibo/dev.fibo-quickstart.ttl` (`dev`, not `prod` —
`prod.fibo-quickstart.ttl` omits 40 modules, several of which this project
already binds) and asserts presence by **subject position**: a term counts as
declared only when it opens its own Turtle block (`prefix:Local` alone at the
start of a line), never when it merely appears as the object of someone
else's triple.

**The trap this script is built to survive.** The absence check written
during design for this exact task returned "0 hits" for *every* candidate,
including `Exposure` and `Capital` — both plainly declared. The regex
required a trailing space; a declaration puts the qname alone on the line, so
the check was structurally incapable of matching anything and every "absent"
verdict it produced was worthless. `KNOWN_PRESENT` below is the control that
catches a repeat of exactly that failure: if any of these reports absent, the
matcher is broken and no MISSING verdict in this run means anything, so the
script refuses to proceed past it.

For every object property this prints `rdfs:domain` and `rdfs:range` so a
name that reads right and means something else — Wave 18's
`fibo-loan-ln-reg:administeredBy`, scoped to a regulator overseeing a rule,
not a facility's admin agent — is visible in the output, not just asserted in
prose. Two more traps of that shape turned up while checking this wave's
"connected group" vocabulary and are recorded under REJECTED_TRAPS below:
`cmns-pts:hasRelatedPartyRole` (PartyRole -> PartyRole, no "economically
connected" semantics) and `fibo-sec-fund-civ:fundHasRelatedParty` (scoped to
a CollectiveInvestmentVehicle, not a bank's obligor book).

Run: uv run generators/verify_fibo_wave19.py
Exit: non-zero if any KNOWN_PRESENT term is not declared (matcher broken), if
any REUSE term is not declared where claimed, or if any term proposed for
`ex:` minting turns out to collide with a real declared FIBO term under any
prefix.
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

#: Terms FIBO DOES declare, confirmed 2026-08-27 by direct grep of
#: sources/fibo/dev.fibo-quickstart.ttl (not spec.edmcouncil.org). If any of
#: these comes back absent, the matcher is broken and no absence result in
#: this run means anything. This is the control the design-session attempt
#: lacked — see the module docstring.
KNOWN_PRESENT = (
    "fibo-fbc-pas-fpas:Exposure",
    "fibo-fbc-pas-fpas:ExposureBearer",
    "fibo-fbc-pas-fpas:hasExposureTo",
    "fibo-be-oac-cpty:ContractualControl",
    "fibo-be-oac-cpty:MajorityControllingParty",
    # Task 5 needs a bank type. All three below are declared, verified
    # 2026-08-27 (pre-flight ruling P5).
    "fibo-fbc-fct-fse:Bank",
    "fibo-fbc-fct-fse:BankHoldingCompany",
    "fibo-fbc-fct-usfse:NationalBank",
)

# ---------------------------------------------------------------------------
# Terms this wave uses. `decision` records what this run concludes about
# each — not asserted ahead of the check, printed alongside it.
# ---------------------------------------------------------------------------

CLASSES: list[dict] = [
    {
        "qname": "fibo-fbc-pas-fpas:Exposure",
        "group": "EXPOSURE (large-exposure-rwa-concentration)",
        "decision": "ADOPT — the exposure amount node; reached via "
                    "ExposureSituation, not directly off a Party (see "
                    "hasExposureTo below)",
    },
    {
        "qname": "fibo-fbc-pas-fpas:ExposureBearer",
        "group": "EXPOSURE (large-exposure-rwa-concentration)",
        "decision": "ADOPT — the role a bank or obligor plays when it bears "
                    "an exposure",
    },
    {
        "qname": "fibo-fbc-pas-fpas:ExposureSituation",
        "group": "EXPOSURE — supporting evidence",
        "decision": "supporting — this is the REIFICATION NODE "
                    "hasExposureTo actually connects FROM (domain, not "
                    "Exposure or ExposureBearer). Recorded so Task 8/9 does "
                    "not skip it and wire ExposureBearer -> Exposure "
                    "directly, which the declared domain does not permit.",
    },
    {
        "qname": "fibo-be-oac-cpty:ContractualControl",
        "group": "CONTROL (ConnectedGroup control leg)",
        "decision": "ADOPT — one of the two Basel 'connected clients' "
                    "legs (control); subClassOf fibo-fnd-oac-ctl:DeJureControl",
    },
    {
        "qname": "fibo-be-oac-cpty:MajorityControllingParty",
        "group": "CONTROL (ConnectedGroup control leg)",
        "decision": "ADOPT — the controlling-party role for the control leg",
    },
    {
        "qname": "fibo-fbc-fct-fse:Bank",
        "group": "BANK TYPES (Task 5)",
        "decision": "ADOPT — generic bank type",
    },
    {
        "qname": "fibo-fbc-fct-fse:BankHoldingCompany",
        "group": "BANK TYPES (Task 5)",
        "decision": "ADOPT — bank holding company type",
    },
    {
        "qname": "fibo-fbc-fct-usfse:NationalBank",
        "group": "BANK TYPES (Task 5)",
        "decision": "ADOPT — US national bank charter type",
    },
]

OBJECT_PROPERTIES: list[dict] = [
    {
        "qname": "fibo-fbc-pas-fpas:hasExposureTo",
        "group": "EXPOSURE (large-exposure-rwa-concentration)",
        "decision": "ADOPT — domain ExposureSituation, NOT ExposureBearer. "
                    "Using this means an ExposureSituation node sits between "
                    "the bearer and the amount, same reified shape as Wave "
                    "18's SyndicateParticipation.",
    },
    {
        "qname": "fibo-be-oac-cctl:hasSubsidiary",
        "group": "CONNECTED GROUP — subsidiaryOf REUSE, not minted",
        "decision": "REUSE (already bound in the v2 table since Wave 8; "
                    "declared nowhere in the loaded graph yet per "
                    "validators/spec_coverage.py's FAMILY_TREE note). Domain "
                    "cmns-org:LegalEntity matches how nodes are already "
                    "typed in this estate, same as the already-used "
                    "hasGlobalUltimateParent/hasDomesticUltimateParent "
                    "precedent (role-typed range, direct-entity domain, "
                    "used without separately instantiating the role "
                    "individual). Task 5's brief candidate list included a "
                    "bare `subsidiaryOf` for minting under ex: — checked and "
                    "REJECTED: FIBO already declares this exact relation and "
                    "this project already binds it. Minting ex:subsidiaryOf "
                    "would duplicate a predicate this estate already has.",
    },
    {
        "qname": "fibo-be-oac-cctl:isSubsidiaryOf",
        "group": "CONNECTED GROUP — supporting evidence",
        "decision": "supporting — the inverse direction, domain Subsidiary "
                    "range ControllingAffiliate; hasSubsidiary is preferred "
                    "for the ConnectedGroup edge because its domain is the "
                    "plain LegalEntity type nodes already carry",
    },
]

#: Two traps found while checking whether FIBO already covers "connected
#: group" / "related party" before minting ex:ConnectedGroup /
#: ex:economicallyDependentOn / ex:connectedTo. Same shape as Wave 18's
#: administeredBy trap: a name that reads right, wrong domain.
REJECTED_TRAPS: list[dict] = [
    {
        "qname": "cmns-pts:hasRelatedPartyRole",
        "note": "domain cmns-pts:PartyRole, range cmns-pts:PartyRole — "
                "role-to-role, no 'economically connected clients' "
                "semantics, and nothing in this estate types a PartyRole "
                "individual for obligors today. NOT ours.",
    },
    {
        "qname": "fibo-sec-fund-civ:fundHasRelatedParty",
        "note": "domain fibo-sec-sec-pls:CollectiveInvestmentVehicle, range "
                "fibo-sec-fund-civ:FundsProcessingParty — scoped to a fund's "
                "processing party (administrator, transfer agent, ...). "
                "NOT a bank's obligor book. NOT ours.",
    },
]

ALL_TERMS = [(t, "class") for t in CLASSES] + [
    (t, "property") for t in OBJECT_PROPERTIES
]

#: Candidates for `ex:` minting. Each is checked absent under EVERY prefix,
#: not just the ones this script otherwise queries — a bare local-name
#: collision under some other FIBO module would be exactly as wrong as
#: reusing an existing term's local name would have been.
EX_MINTED_CHECKED_ABSENT: list[dict] = [
    {
        "local": "ConnectedGroup",
        "note": "the grouping node for a Basel 'group of connected "
                "clients' — no FIBO class for this concept exists anywhere "
                "in the ontology (checked: Connected*, GroupOfConnected"
                "Clients, RelatedParty*, AffiliatedParty* — see "
                "REJECTED_TRAPS for the two near-misses).",
    },
    {
        "local": "economicallyDependentOn",
        "note": "the economic-dependency leg of 'connected clients' — "
                "distinct from ContractualControl (the control leg, FIBO "
                "already supplies that one). Checked: EconomicDependence, "
                "dependentOn, isDependentOn, hasDependency — none declared.",
    },
    {
        "local": "connectedTo",
        "note": "ConnectedGroup -> member edge. Checked: isConnectedWith, "
                "connectedWith, isRelatedTo — none declared.",
    },
    {
        "local": "governedByRegime",
        "note": "LimitEnvelope -> the regulatory regime version it "
                "implements. No regime/version vocabulary exists anywhere "
                "in the ontology under any prefix.",
    },
    {
        "local": "RegimeVersion",
        "note": "a versioned large-exposure regulatory regime (e.g. Basel "
                "III large-exposure framework as of a date) — no FIBO class "
                "for a regulatory regime's VERSION exists.",
    },
    {
        "local": "LimitEnvelope",
        "note": "the node carrying limitPctOfCapital / limitAbsoluteUsd for "
                "a given regime version. No FIBO class bundles a "
                "concentration-limit pair this way.",
    },
    {
        "local": "InsiderDesignation",
        "note": "a designated-insider flag on a connected-group member for "
                "insider-lending-limit purposes. Checked: Insider* under "
                "every prefix — none declared.",
    },
    {
        "local": "assertedBy",
        "note": "who asserted a bitemporal fact (ConnectedGroup membership, "
                "InsiderDesignation) — this estate's existing bitemporal "
                "predicates (ex:validFrom, ex:assertedAt) are all ex: "
                "already; no FIBO/PROV vocabulary is loaded in this "
                "ontology.",
    },
    {
        "local": "assertedOn",
        "note": "literal date companion to assertedBy, same reasoning.",
    },
    {
        "local": "designatedPerson",
        "note": "InsiderDesignation -> the fibo-fnd-aap-ppl:Person or "
                "cmns-org:LegalEntity it designates. No FIBO predicate "
                "names an insider designation's subject.",
    },
    {
        "local": "citesProvision",
        "note": "links an InsiderDesignation or LimitEnvelope to the "
                "regulatory provision text it cites (MongoDB passage). No "
                "citation/provision-reference vocabulary exists in this "
                "ontology.",
    },
    {
        "local": "effectiveFrom",
        "note": "literal ISO date. Same reasoning Wave 18 already recorded "
                "for `effectiveDate`: fibo-fnd-agr-ctr:hasEffectiveDate "
                "exists but is an owl:ObjectProperty over the reified class "
                "cmns-dt:Date, not a literal — every temporal predicate "
                "this estate has ever written carries a plain literal "
                "instead, and this wave follows that precedent rather than "
                "introducing the one reified exception.",
    },
    {
        "local": "effectiveTo",
        "note": "literal ISO date, companion to effectiveFrom, same "
                "reasoning.",
    },
    {
        "local": "limitPctOfCapital",
        "note": "literal numeric percentage on a LimitEnvelope. No FIBO "
                "predicate carries a bare percentage-of-capital limit.",
    },
    {
        "local": "limitAbsoluteUsd",
        "note": "literal numeric absolute-dollar limit on a LimitEnvelope, "
                "same reasoning.",
    },
    {
        "local": "rssd",
        "note": "literal attribute carrying a bank's Federal Reserve RSSD "
                "ID, same shape as the existing ex:lei attribute — an "
                "identifier value, not a FIBO relationship.",
    },
]


def load_ontology() -> str:
    if not ONTOLOGY.exists():
        print(f"FATAL: {ONTOLOGY} does not exist.")
        print("This script never fetches spec.edmcouncil.org. Obtain the file")
        print("out of band and re-run.")
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
    term) would be exactly as wrong as reusing an existing term's local name
    would have been. Subject position only, same discipline as `find_block`:
    a local name appearing only as an object is not a declaration.
    """
    pattern = re.compile(
        rf"^([A-Za-z][\w-]*:{re.escape(local_name)})$", re.M
    )
    m = pattern.search(text)
    return m.group(1) if m else None


def extract_list(block: str, predicate: str) -> list[str]:
    """Every qname mentioned in the value of `predicate ... ;` in `block`."""
    m = re.search(rf"{re.escape(predicate)}\s+(.*?);", block, re.S)
    if not m:
        return []
    return re.findall(r"[A-Za-z][\w-]*:[A-Za-z][\w-]*", m.group(1))


def extract_label(block: str) -> str:
    m = re.search(r'rdfs:label\s+"([^"]*)"', block)
    return m.group(1) if m else ""


def main() -> int:
    print("Wave 19 — verifying the large-exposure-rwa-concentration "
          f"vocabulary against {ONTOLOGY.relative_to(REPO_ROOT)}\n")

    text = load_ontology()

    if find_block(text, POSITIVE_CONTROL) is None:
        print(f"FATAL: positive control {POSITIVE_CONTROL!r} not found in "
              "subject position. The file or the pattern is wrong — no "
              "'absent' answer below can be trusted until this passes.")
        return 2
    print(f"  positive control ok: {POSITIVE_CONTROL} declared\n")

    print("=== KNOWN_PRESENT (matcher control) ===")
    broken = [t for t in KNOWN_PRESENT if find_block(text, t) is None]
    for t in KNOWN_PRESENT:
        ok = find_block(text, t) is not None
        print(f"  {'ok      ' if ok else 'MISSING '} {t}")
    print()
    if broken:
        print("FATAL: KNOWN_PRESENT term(s) reported absent — the matcher "
              "is broken and NO absence verdict below means anything:")
        for t in broken:
            print(f"    {t}")
        return 2

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

    n_ok = len(ALL_TERMS) - len(missing)
    print(f"  {n_ok}/{len(ALL_TERMS)} terms declared in subject position "
          f"({len(missing)} missing)\n")

    if missing:
        print("  MISSING terms must not be claimed as FIBO bindings:")
        for m in missing:
            print(f"    {m}")

    print("=== REJECTED TRAPS — declared, but wrong domain/range for us ===")
    for entry in REJECTED_TRAPS:
        block = find_block(text, entry["qname"])
        status = "ok (declared, rejected on domain/range)" if block else \
            "NOT DECLARED — remove this trap entry, it no longer applies"
        print(f"  {status:45s} {entry['qname']}")
        print(f"             note: {entry['note']}")
    print()

    print("=== EX: TERMS CHECKED ABSENT BEFORE MINTING ===")
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
