#!/usr/bin/env python3
"""Wave 15 — load the covenant definition chain into Fluree.

Closes the gap `validators/spec_coverage.py` found in `covenant-cross-reference`
and `covenant-in-force-as-of`: `ex:definedBy`, `ex:measuredBy` and
`ex:crossReferences` had ZERO assertions and `ex:CovenantDefinition`,
`ex:DefinedTerm` and `ex:MeasurementPeriod` had ZERO instances, while both
products were registered as done. The T4 product's own summary is "the covenant
sits in one section and its defined terms in another", and nothing in the
estate could express that.

## The shape

    covenant --definedBy--> CovenantDefinition --crossReferences--> DefinedTerm
                                    |
                                    +--measuredBy (on the covenant)--> MeasurementPeriod

Depth 3 is the covenant, its ratio definition, and a term that definition
depends on. All three hops are real spans of real filed EX-10 text with
document ids and character offsets, per §C's `public` classification.

## What attaches to what, and why not to the 180 synthetic covenants

The estate holds two covenant populations:

    COV-*     180 nodes, `provenance: synthetic — internal`, hung off synthetic
              facilities. NO document, NO offsets.
    COVSRC-*   37 nodes, `provenance: public`, each carrying `documentId`,
              `startOffset`, `endOffset`, `passageSha256`, `anchorVerified`.

Definitions attach to COVSRC only. A `definedBy` edge from a synthetic covenant
to a real definition in a filed agreement would assert that a made-up covenant
on a made-up facility is defined by Bausch Health's actual credit agreement --
a join that reads as evidence and is not. The synthetic covenants keep their
thresholds and stay definition-less, which is the honest state.

## The one covenant this loader creates

BGC Group's agreement carries a real net-capital covenant that Wave 5's regex
had no pattern for -- "Net Excess Capital ... to be less than $300,000,000".
It matters because its defined term is the corpus's ONLY definition that
incorporates a convention stated elsewhere: "as shown on the Borrower's SEC
Forms 10-Q and 10-K". That is §F's cross-document reference, and §F does NOT
list it as engineered, so finding it rather than inventing it is the difference
between the product demonstrating something and staging it.

Its node is `COVDEF-*`, never `COVSRC-*`: Wave 6 owns that namespace and this
loader must not write into it.

## The cross-document target is a real FIBO type

`fibo-fnd-arr-rep:Report` (subClassOf `cmns-doc:Document`), verified declared
against the complete FIBO Production ontology. The 10-K node carries only its
type, a label and `ex:documentId` -- no text, no passages. MongoDB remains the
single writer for document content; this is an identity anchor for an edge,
the same shape as the `ex:documentId` COVSRC nodes already carry.

Run: uv run loaders/load_covenant_definitions_wave15.py
"""

from __future__ import annotations

import json
import re
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT, mongo_db

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "covenant_definitions.json"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

C_REPORT = f"{FIBO}FND/Arrangements/Reporting/Report"

#: The REAL FIBO class for a defined-terms entry, asserted on every definition
#: and defined term this loader writes:
#:
#:   "contractual element that specifies the meaning of a term in a legal
#:    document, whose definition is substitutable for the term whenever it
#:    occurs in the body of that document"
#:
#: Both covenant specs' §C say of CovenantDefinition and DefinedTerm that "no
#: FIBO term exists". That is not so, and it was found only because
#: partition.py refused `ex:DefinedTerm` as shadowing and the check had to be
#: answered with a search rather than an assertion. The vault mirror has been
#: told; see the Wave 15 exchange bundle.
#:
#: The `ex:` types are kept ALONGSIDE this one, never instead of it. They carry
#: a role distinction FIBO does not make -- which contractual definition is the
#: one a covenant is measured by, and which is a term that definition depends
#: on -- and a node asserting only `ex:DefinedTerm` would be invisible to a
#: consumer querying FIBO for contractual definitions.
C_CONTRACTUAL_DEFINITION = f"{FIBO}FND/Agreements/Contracts/ContractualDefinition"

C_COVENANT = f"{EX}Covenant"
C_DEFINITION = f"{EX}CovenantDefinition"
C_DEFINED_TERM = f"{EX}DefinedTerm"
C_PERIOD = f"{EX}MeasurementPeriod"
C_DEBT = f"{EX}ContextDebt"

P_DEFINED_BY = f"{EX}definedBy"
P_MEASURED_BY = f"{EX}measuredBy"
P_CROSS_REFERENCES = f"{EX}crossReferences"

#: Covenant types this loader may CREATE a covenant node for.
#:
#: Exactly one, and the restriction is deliberate. `net_capital` is the
#: category Wave 5's regex had no pattern for and that this wave added after
#: measuring that its absence was what sent §F's cross-document bullet to the
#: engineered pile. Every other type is Wave 6's to anchor: finding a clause
#: for `minimum_liquidity` in a document Wave 6 did not anchor means Wave 6
#: made a judgement, not that it made a mistake, and a second writer creating
#: the covenant anyway is how one covenant ends up asserted twice with
#: different thresholds.
#:
#: This bound is also what makes the direction decision safe. Direction comes
#: from covenant-type semantics because the comparator in the text cannot be
#: parsed reliably (see extract_covenant_definitions.covenant_clause), so
#: creation is confined to a category whose direction is not in doubt.
CREATABLE = {"net_capital"}

BATCH = 400


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:60]


def doc_key(document_id: str) -> str:
    """A URI-safe key for a document id like `0001-26-1:ex10_1.htm`."""
    return slug(document_id)


def covsrc_index() -> dict[tuple[str, str], str]:
    """(documentId, covenantType) -> the Wave 6 covenant anchor node."""
    q = (f"SELECT ?s ?d FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ ?s <{EX}documentId> ?d }}")
    docs = {b["s"]["value"]: b["d"]["value"]
            for b in fluree.query(q)["results"]["bindings"]
            if "COVSRC" in b["s"]["value"]}
    q2 = (f"SELECT ?s ?t FROM <{FLUREE_LEDGER_V2}> "
          f"WHERE {{ ?s <{EX}covenantType> ?t }}")
    types = {b["s"]["value"]: b["t"]["value"]
             for b in fluree.query(q2)["results"]["bindings"]}
    out: dict[tuple[str, str], str] = {}
    for node, did in docs.items():
        ct = types.get(node)
        if ct:
            out[(did, ct)] = node
    return out


#: The concept a net-capital definition incorporates from the periodic report.
#: Used to choose WHICH 10-K section the cross-document edge lands on.
CONVENTION_HINT = {"net_capital": "net capital"}


def report_node_for(lei: str, covenant_type: str) -> tuple[str, str] | None:
    """The 10-K section the definition incorporates: (node uri, document_id).

    Resolved from MongoDB rather than constructed, so the edge points at a
    report that is actually held -- a constructed id is a valid triple pointing
    at nothing, the phantom-borrower defect.

    ## Why this is not simply "the most recent 10-K"

    It was, and that was two bugs. BGC files its 10-K as two documents with the
    SAME filed_date -- an MD&A section and a risk-factors section -- so
    `sort=[("filed_date", -1)]` had no tie-break and returned whichever Mongo
    happened to order first. That is:

      1. arbitrary -- nothing connected the chosen section to what the
         definition actually incorporates; it landed on a relevant document by
         luck, both sections mentioning "net capital" 17 times each, and
      2. NOT REPRODUCIBLE -- an unstable sort can return the other section on a
         re-run, and `crossReferences` is multi-valued, so the conflict guard
         would not catch it. The reload would silently add a SECOND edge and
         the definition would then cite two reports, one of them chosen by a
         coin flip on a previous Tuesday.

    So: prefer sections whose text actually discusses the incorporated concept,
    and break every remaining tie on `document_id`, which is stable. Returns
    None when no 10-K mentions it rather than falling back to an arbitrary one
    -- an edge to a report that does not state the convention is worse than no
    edge, because it looks like evidence of a link that was never checked.
    """
    hint = CONVENTION_HINT.get(covenant_type)
    docs = list(mongo_db()["document"].find(
        {"lei": lei, "form": "10-K"}, {"document_id": 1, "text": 1}))
    if not docs:
        return None
    if hint:
        docs = [d for d in docs if hint in d["text"].lower()]
        if not docs:
            return None
    chosen = min(docs, key=lambda d: d["document_id"])
    return f"{EX}report-{doc_key(chosen['document_id'])}", chosen["document_id"]


def build() -> tuple[list[str], dict]:
    payload = json.loads(ARTIFACT.read_text())
    covsrc = covsrc_index()

    triples: list[str] = [
        triple(C_DEFINITION, RDF_TYPE, OWL_CLASS),
        triple(C_DEFINITION, RDFS_LABEL, "CovenantDefinition", literal=True),
        triple(C_DEFINED_TERM, RDF_TYPE, OWL_CLASS),
        triple(C_DEFINED_TERM, RDFS_LABEL, "DefinedTerm", literal=True),
        triple(C_PERIOD, RDF_TYPE, OWL_CLASS),
        triple(C_PERIOD, RDFS_LABEL, "MeasurementPeriod", literal=True),
        triple(C_REPORT, RDF_TYPE, OWL_CLASS),
        triple(C_REPORT, RDFS_LABEL, "Report", literal=True),
        triple(C_CONTRACTUAL_DEFINITION, RDF_TYPE, OWL_CLASS),
        triple(C_CONTRACTUAL_DEFINITION, RDFS_LABEL, "ContractualDefinition",
               literal=True),
    ]

    stats = {"definitions": 0, "defined_terms": 0, "periods": 0,
             "defined_by": 0, "measured_by": 0, "cross_refs": 0,
             "cross_document": 0, "covenants_created": 0,
             "definitions_without_covenant": 0}

    for doc in payload["documents"]:
        did = doc["document_id"]
        dkey = doc_key(did)
        lei = doc.get("lei")

        for df in doc.get("definitions", []):
            ct = df["covenant_type"]
            dnode = f"{EX}covdef-{dkey}-{ct}"
            triples += [
                triple(dnode, RDF_TYPE, C_DEFINITION),
                triple(dnode, RDF_TYPE, C_CONTRACTUAL_DEFINITION),
                triple(dnode, RDFS_LABEL, df["term"], literal=True),
                triple(dnode, f"{EX}covenantType", ct, literal=True),
                triple(dnode, f"{EX}provenance", "public", literal=True),
                # Passage anchors -- §C wants "definition entities WITH passage
                # anchors", so the offsets ride on the node, not in a note.
                triple(dnode, f"{EX}documentId", did, literal=True),
                triple(dnode, f"{EX}startOffset", str(df["decl_offset"]),
                       literal=True),
                triple(dnode, f"{EX}endOffset", str(df["body_end"]),
                       literal=True),
                triple(dnode, f"{EX}declarationConvention", df["convention"],
                       literal=True),
            ]
            stats["definitions"] += 1

            # --- components: definition -> defined term -------------------
            for c in df["components"]:
                tnode = f"{EX}defterm-{dkey}-{slug(c['term'])}"
                triples += [
                    triple(tnode, RDF_TYPE, C_DEFINED_TERM),
                    triple(tnode, RDF_TYPE, C_CONTRACTUAL_DEFINITION),
                    triple(tnode, RDFS_LABEL, c["term"], literal=True),
                    triple(tnode, f"{EX}documentId", did, literal=True),
                    triple(tnode, f"{EX}startOffset", str(c["declared_at"]),
                           literal=True),
                    triple(tnode, f"{EX}provenance", "public", literal=True),
                    triple(dnode, P_CROSS_REFERENCES, tnode),
                ]
                stats["defined_terms"] += 1
                stats["cross_refs"] += 1

            # --- the covenant this definition defines ---------------------
            cov = covsrc.get((did, ct))
            if cov is None and ct in CREATABLE and df.get("covenant_clause"):
                # A real covenant Wave 6 had no pattern for. Created here,
                # in a namespace this loader owns.
                cl = df["covenant_clause"]
                cov = f"{EX}COVDEF-{dkey}-{ct.upper()}"
                triples += [
                    triple(cov, RDF_TYPE, C_COVENANT),
                    triple(cov, RDFS_LABEL,
                           f"{ct} {doc.get('sec_name') or ''}".strip(),
                           literal=True),
                    triple(cov, f"{EX}covenantType", ct, literal=True),
                    triple(cov, f"{EX}threshold", str(cl["threshold"]),
                           literal=True),
                    triple(cov, f"{EX}unit", cl["unit"], literal=True),
                    triple(cov, f"{EX}direction", cl["direction"], literal=True),
                    triple(cov, f"{EX}provenance", "public", literal=True),
                    triple(cov, f"{EX}documentId", did, literal=True),
                    triple(cov, f"{EX}startOffset", str(cl["clause_offset"]),
                           literal=True),
                ]
                stats["covenants_created"] += 1

            if cov is not None:
                triples.append(triple(cov, P_DEFINED_BY, dnode))
                stats["defined_by"] += 1
            else:
                stats["definitions_without_covenant"] += 1

            # --- cross-document: definition -> the 10-K it incorporates ---
            if df.get("cross_document_citation") and lei:
                rep = report_node_for(lei, ct)
                if rep:
                    rnode, rdid = rep
                    triples += [
                        triple(rnode, RDF_TYPE, C_REPORT),
                        triple(rnode, RDFS_LABEL, f"10-K {rdid}", literal=True),
                        triple(rnode, f"{EX}documentId", rdid, literal=True),
                        triple(dnode, P_CROSS_REFERENCES, rnode),
                    ]
                    stats["cross_document"] += 1
                    stats["cross_refs"] += 1

        # --- measurement periods, and the covenants measured by them ------
        for per in doc.get("measurement_periods", []):
            pnode = f"{EX}mperiod-{dkey}-{slug(per['term'])}"
            triples += [
                triple(pnode, RDF_TYPE, C_PERIOD),
                triple(pnode, RDFS_LABEL, per["term"], literal=True),
                triple(pnode, f"{EX}documentId", did, literal=True),
                triple(pnode, f"{EX}startOffset", str(per["decl_offset"]),
                       literal=True),
                triple(pnode, f"{EX}provenance", "public", literal=True),
            ]
            stats["periods"] += 1
            for (cdid, _ct), cov in covsrc.items():
                if cdid == did:
                    triples.append(triple(cov, P_MEASURED_BY, pnode))
                    stats["measured_by"] += 1

    return triples, stats


def engineered_unresolvable(triples: list[str]) -> str:
    """§F: >= 1 covenant with an UNRESOLVABLE DEFINITION, emitting Context Debt.

    Engineered, and §F names it as such -- the only engineered element in this
    load. Everything else is filed text.

    It is added because the existing `DEBT-0000` does NOT satisfy this bullet,
    though the gate counted it as if it did: its reason reads "no passage span
    contains the extracted offset", which is an unresolvable OFFSET. An
    unresolvable offset and an unresolvable definition are different failures
    with different remedies, and only the second one exercises the definition
    chain.

    The engineered condition: a covenant whose definition cites a defined term
    the agreement never declares, so the chain terminates in nothing.
    """
    debt = f"{EX}DEBT-0001"
    cov = f"{EX}COV-UNRESOLVED-DEFINITION"
    dangling = "Adjusted Consolidated Working Capital"
    dnode = f"{EX}covdef-engineered-unresolvable"
    triples += [
        triple(cov, RDF_TYPE, C_COVENANT),
        triple(cov, RDFS_LABEL, "leverage (engineered, unresolvable definition)",
               literal=True),
        triple(cov, f"{EX}covenantType", "leverage", literal=True),
        triple(cov, f"{EX}provenance", "synthetic — engineered", literal=True),
        triple(cov, P_DEFINED_BY, dnode),

        triple(dnode, RDF_TYPE, C_DEFINITION),
        triple(dnode, RDF_TYPE, C_CONTRACTUAL_DEFINITION),
        triple(dnode, RDFS_LABEL,
               "Consolidated Leverage Ratio (engineered)", literal=True),
        triple(dnode, f"{EX}covenantType", "leverage", literal=True),
        triple(dnode, f"{EX}provenance", "synthetic — engineered", literal=True),
        # NO crossReferences: the term it depends on is never declared. That
        # absence IS the condition -- the chain stops here.
        triple(dnode, f"{EX}unresolvedTerm", dangling, literal=True),

        triple(debt, RDF_TYPE, C_DEBT),
        triple(debt, RDFS_LABEL, "unresolvable covenant definition", literal=True),
        triple(debt, f"{EX}covenantType", "leverage", literal=True),
        triple(debt, f"{EX}provenance", "synthetic — engineered", literal=True),
        triple(debt, f"{EX}reason",
               f"covenant definition cites the defined term "
               f"'{dangling}', which the agreement never declares; the "
               f"definition chain terminates unresolved",
               literal=True),
        triple(debt, f"{EX}unresolvedTerm", dangling, literal=True),
        triple(debt, P_CROSS_REFERENCES, dnode),
    ]
    return dnode


def conflicts(triples: list[str]) -> list[str]:
    """Refuse when the ledger already holds a DIFFERENT value for a scalar.

    Fluree is append-only with set semantics: an identical re-run is a no-op,
    but a CHANGED source value inserts a second, contradicting triple on the
    same subject and predicate, and both then stand forever with nothing
    marking which supersedes which.

    This guard exists because it was needed. The first run of this loader
    wrote `direction "max"` on a Viskase liquidity covenant that is a floor;
    the fix changed the value, and without a guard the reload would have left
    the ledger asserting both directions at once. That node was retracted by
    hand -- Fluree's DELETE is a retraction, current state changes and history
    is preserved -- and this makes the next such mistake refuse instead.
    """
    single_valued = {f"{EX}direction", f"{EX}threshold", f"{EX}unit",
                     f"{EX}covenantType", f"{EX}documentId",
                     f"{EX}startOffset", f"{EX}endOffset"}
    want: dict[tuple[str, str], str] = {}
    for line in triples:
        m = re.match(r"<([^>]+)> <([^>]+)> (.+) \.$", line)
        if not m:
            continue
        s, p, o = m.group(1), m.group(2), m.group(3)
        if p in single_valued:
            want[(s, p)] = o.strip('"')

    out: list[str] = []
    for (s, p), v in want.items():
        q = (f"SELECT ?o ?x FROM <{FLUREE_LEDGER_V2}> "
             f"WHERE {{ <{s}> <{p}> ?o }}")
        held = [b["o"]["value"] for b in fluree.query(q)["results"]["bindings"]]
        for h in held:
            if h != v:
                out.append(f"{s.rsplit('/', 1)[-1]} <{p.rsplit('/', 1)[-1]}>: "
                           f"ledger={h!r} source={v!r}")
    return out


def main() -> int:
    print("Wave 15 — covenant definition chain into Fluree\n")
    if not ARTIFACT.exists():
        print(f"  missing {ARTIFACT}; run generators/"
              f"extract_covenant_definitions.py first")
        return 1

    triples, stats = build()
    engineered_unresolvable(triples)

    bad = conflicts(triples)
    if bad:
        print("  LEDGER CONFLICT — a different value is already asserted:")
        for b in bad[:20]:
            print(f"    {b}")
        print("\n  Superseding is a modelled act, never a side effect of a "
              "reload. Nothing written.")
        return 1

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    print(f"  wrote {len(triples)} triples")
    for k, v in stats.items():
        print(f"    {k:32s} {v}")

    q = (f"SELECT ?c ?t FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
         f"?c <{P_DEFINED_BY}> ?d . ?d <{P_CROSS_REFERENCES}> ?t . "
         f"?t <{RDF_TYPE}> <{C_DEFINED_TERM}> }}")
    chains = fluree.query(q)["results"]["bindings"]
    depth3 = {b["c"]["value"] for b in chains}
    print(f"\n  covenants whose chain reaches depth 3: {len(depth3)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
