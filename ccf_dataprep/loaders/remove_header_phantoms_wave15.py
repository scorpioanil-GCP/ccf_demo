#!/usr/bin/env python3
"""Retract the three Exhibit 21 TABLE HEADERS that became companies.

See docs/known-issues.md §19.6. `generators/fetch_exhibit21.py` filtered header
cells with a regex whose first alternative was `subsidiaries?` -- the `?`
applies to the final `s`, so it matched "subsidiaries" and "subsidiarie" and
never "Subsidiary". Header cells reading `Subsidiary`, `Legal Name` and
`Company Name` were parsed as subsidiary names, and `load_fluree_wave3.py`
built them into the graph as legal entities:

    SubSubsidiary   "SUBSIDIARY" / "Subsidiary"   Genesis Energy · Hain Celestial
    SubLegalName    "Legal Name"                  Las Vegas Sands · Targa Resources
    SubCompanyName  "Company Name"                Regis Corporation

Two filers' headers normalise to one local name, so each phantom is a SINGLE
node owned by BOTH filers. The visible damage is in the first one: Genesis
Energy's engineered depth chain runs through it, so THE HAIN CELESTIAL GROUP —
a natural-foods company — owns AP MARINE LLC, BR PORT SERVICES LLC and CAMERON
HIGHWAY PIPELINE, three hops down, because a spreadsheet header was shared.

**Which nodes, derived not listed.** The phantom set is computed by applying
`fetch_exhibit21.BARE_HEADER` — the same regex the fixed parser now uses — to
every bridging stub's labels. A hardcoded list of three could silently
disagree with the parser after either changed; this cannot.

**Idempotent, and with nothing to converge on.** Unlike the parent-direction
remediation, which had to distinguish "inverted" from "already corrected" or
it would flip back on a second run, a retraction of triples that are already
absent is simply a no-op.

Run: uv run loaders/remove_header_phantoms_wave15.py --dry-run
     uv run loaders/remove_header_phantoms_wave15.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWNS = ("https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/"
        "Ownership/owns")
BRIDGING = "synthetic — bridging"
BATCH = 200

_spec = importlib.util.spec_from_file_location(
    "fetch_exhibit21", REPO_ROOT / "generators" / "fetch_exhibit21.py")
ex21 = importlib.util.module_from_spec(_spec)
sys.modules["fetch_exhibit21"] = ex21
_spec.loader.exec_module(ex21)


def q(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def term(binding: dict) -> str:
    """Re-serialise a binding EXACTLY as it must appear in DELETE DATA.

    Read back rather than reconstructed. A retraction only removes a triple it
    matches character for character, so guessing whether an object was a URI
    or a literal is the one thing that would make this silently do nothing.
    """
    if binding["type"] == "uri":
        return f"<{binding['value']}>"
    return f'"{esc(binding["value"])}"'


def phantoms() -> dict[str, list[str]]:
    """Bridging stubs whose every label is a bare table header."""
    labels: dict[str, list[str]] = {}
    for b in q(f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
               f'?s <{EX}provenance> "{BRIDGING}" . ?s <{RDFS_LABEL}> ?l }} '
               f"LIMIT 2000"):
        labels.setdefault(b["s"]["value"], []).append(b["l"]["value"])
    return {s: ls for s, ls in labels.items()
            if all(ex21.BARE_HEADER.match(x) for x in ls)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    found = phantoms()
    if not found:
        print("  no header phantoms in the ledger — nothing to retract.")
        return 0

    retract: list[str] = []
    orphan_risk: list[str] = []

    for subject, labels in sorted(found.items()):
        out = q(f"SELECT ?p ?o FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ <{subject}> ?p ?o }}")
        inc = q(f"SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s ?p <{subject}> }}")
        print(f"\n  {subject.rsplit('/', 1)[-1]}  labels={labels}")
        print(f"    {len(out)} triples out, {len(inc)} in")
        print("    owned by: "
              + ", ".join(sorted({b['s']['value'].rsplit('/', 1)[-1]
                                  for b in inc})))

        for b in out:
            retract.append(f"<{subject}> <{b['p']['value']}> {term(b['o'])} .")
            # A child reachable ONLY through the phantom would be cut loose by
            # this retraction. Checked rather than assumed: leaving an
            # unreachable subtree behind would trade a visible wrong edge for
            # an invisible missing one.
            if b["p"]["value"] == OWNS:
                child = b["o"]["value"]
                others = [x for x in q(
                    f"SELECT ?p FROM <{FLUREE_LEDGER_V2}> "
                    f"WHERE {{ ?p <{OWNS}> <{child}> }}")
                    if x["p"]["value"] != subject]
                short = child.rsplit("/", 1)[-1]
                if others:
                    print(f"    child {short} keeps "
                          f"{len(others)} other parent(s) — safe")
                else:
                    orphan_risk.append(short)
        for b in inc:
            retract.append(f"<{b['s']['value']}> <{b['p']['value']}> "
                           f"<{subject}> .")

    print(f"\n  {len(found)} phantoms, {len(retract)} triples to retract")

    if orphan_risk:
        print(f"\n  STOP: {len(orphan_risk)} entities are reachable ONLY "
              f"through a phantom and would be cut loose: {orphan_risk}",
              file=sys.stderr)
        print("  Re-parent them before retracting.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("\n  [dry-run] nothing retracted. Sample:")
        for line in retract[:4]:
            print(f"    {line[:110]}")
        return 0

    for i in range(0, len(retract), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(retract[i:i + BATCH]) + "\n}")

    # Named subjects, read back. A triple COUNT would drop by 35 whether the
    # right 35 went or not.
    failed = []
    for subject in found:
        left = (len(q(f"SELECT ?p ?o FROM <{FLUREE_LEDGER_V2}> "
                      f"WHERE {{ <{subject}> ?p ?o }}"))
                + len(q(f"SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> "
                        f"WHERE {{ ?s ?p <{subject}> }}")))
        print(f"  {subject.rsplit('/', 1)[-1]:18s} {left} triples remain")
        if left:
            failed.append(subject)
    if failed:
        print(f"\n  FAIL: {len(failed)} phantoms still present.",
              file=sys.stderr)
        return 1
    print(f"\n  {len(found)} phantoms gone. Hain Celestial no longer owns an "
          f"oil pipeline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
