#!/usr/bin/env python3
"""Wave 13b Task 7 — KYC documents and their passages.

§C rows:

    KYC document text — incorporation, ownership declarations
        no public equivalent at document level   synthetic — internal  MongoDB  L
    Passage spans and offsets on KYC documents
        derived at ingestion                     derived               MongoDB  L

§F8: **~30 KYC documents with passages, including >= 1 ownership declaration
CONTRADICTING the registry.**

## The contradiction has to be checkable, not merely asserted

A document that says "this declaration contradicts the registry" in its own
prose proves nothing — a validator reading that sentence is reading the
generator's opinion. So each ownership declaration carries **structured claims**
(`declared_owner_name`, `declared_pct`, `declared_owner_person_key`) alongside
its text, and the contradiction is a disagreement between those fields and the
`bo_chain` rows loaded in Task 8. The gate recomputes it; nothing here sets a
`contradicts_registry` flag for the gate to read back.

Three kinds of contradiction are planted, because they fail differently:

    wrong_person      the declaration names a DIFFERENT natural person than
                      the chain resolves to — the dangerous one, since a
                      screening system that trusts the declaration screens
                      the wrong human being
    understated_pct   the declared stake falls below the jurisdiction's
                      threshold while the chain's effective stake clears it,
                      so the declaration reads as "no UBO to report"
    stale_owner       the declaration names a person who WAS the owner and
                      the chain has since moved — right once, wrong now

## Passage offsets are computed against the emitted text

Every passage records `start_offset` / `end_offset` into the document's own
`text`, plus a sha256 of the passage. The loader re-slices the text at those
offsets and compares the hash, so an offset that drifts is caught rather than
trusted — the anchoring discipline Wave 6 established.

Output: sources/screening/wave13b_kyc_documents.json

    uv run generators/generate_kyc_documents_wave13b.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from random import Random

from ccf.config import REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
AS_OF = date(2026, 8, 22)

TARGET_DOCUMENTS = 32
CONTRADICTION_COUNT = 4          # §F8 floor is 1; four so one failure is not fatal

DOC_KINDS = [
    ("ownership_declaration", "Declaration of Beneficial Ownership"),
    ("incorporation_certificate", "Certificate of Incorporation"),
    ("board_resolution", "Board Resolution — Account Opening"),
    ("source_of_wealth", "Source of Wealth Statement"),
    ("ubo_form", "Ultimate Beneficial Owner Form"),
]

CONTRADICTION_KINDS = ("wrong_person", "understated_pct", "stale_owner")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def declaration_text(entity_name: str, jurisdiction: str, owner_name: str,
                     pct: float, declared_on: date, threshold: float) -> list[tuple[str, str]]:
    """Return (heading, body) sections. Offsets are computed by the caller."""
    return [
        ("Declaration",
         f"This declaration is made on behalf of {entity_name}, a company "
         f"registered in {jurisdiction}, in connection with the opening and "
         f"continued maintenance of banking facilities. It is given on "
         f"{declared_on.isoformat()} and supersedes any previous declaration "
         f"of beneficial ownership held by the institution."),
        ("Beneficial owner",
         f"The undersigned confirms that {owner_name} is the ultimate "
         f"beneficial owner of {entity_name}, holding an effective interest of "
         f"{pct:.2f} per cent. of the issued share capital, whether directly "
         f"or through one or more intermediate holding entities."),
        ("Threshold statement",
         f"The applicable reporting threshold in {jurisdiction} is "
         f"{threshold:.0f} per cent. The interest declared above "
         f"{'exceeds' if pct >= threshold else 'does not exceed'} that "
         f"threshold and is "
         f"{'therefore reportable' if pct >= threshold else 'accordingly not reportable'} "
         f"under the applicable regulations."),
        ("Undertaking",
         "The undersigned undertakes to notify the institution in writing "
         "within thirty days of any change to the information set out above, "
         "including any change in the identity of the ultimate beneficial "
         "owner or in the percentage interest held."),
    ]


def generic_text(kind: str, title: str, entity_name: str, jurisdiction: str,
                 declared_on: date) -> list[tuple[str, str]]:
    if kind == "incorporation_certificate":
        return [
            ("Certificate",
             f"This is to certify that {entity_name} was incorporated under "
             f"the laws of {jurisdiction} and that the company is, as at "
             f"{declared_on.isoformat()}, in good standing on the register."),
            ("Registered office",
             f"The registered office of {entity_name} is situated in "
             f"{jurisdiction}. The company has not changed its registered "
             f"office in the twelve months preceding the date of this "
             f"certificate."),
        ]
    if kind == "board_resolution":
        return [
            ("Resolution",
             f"RESOLVED that {entity_name} open and maintain banking "
             f"facilities and that the authorised signatories named in the "
             f"schedule be empowered to operate those facilities on behalf of "
             f"the company."),
            ("Certification",
             f"The foregoing resolution was duly passed at a meeting of the "
             f"board of directors of {entity_name} held on "
             f"{declared_on.isoformat()} and has not been rescinded or "
             f"amended."),
        ]
    if kind == "source_of_wealth":
        return [
            ("Source of wealth",
             f"The funds introduced to {entity_name} derive from the "
             f"disposal of operating businesses and from accumulated "
             f"investment income over a period exceeding ten years. No part "
             f"of the funds derives from a jurisdiction subject to "
             f"comprehensive sanctions."),
            ("Supporting evidence",
             "Supporting documentation comprising audited financial "
             "statements and completion statements has been provided to the "
             "institution and is held on file."),
        ]
    return [
        ("Particulars",
         f"This form records the ultimate beneficial ownership particulars "
         f"of {entity_name} as at {declared_on.isoformat()}, for the purposes "
         f"of the institution's periodic know-your-customer refresh."),
        ("Confirmation",
         f"The particulars given are true and complete to the best of the "
         f"knowledge of the person signing on behalf of {entity_name}."),
    ]


def assemble(sections: list[tuple[str, str]]) -> tuple[str, list[dict]]:
    """Join sections into one text, recording each passage's exact span."""
    parts: list[str] = []
    passages: list[dict] = []
    cursor = 0
    for heading, body in sections:
        block = f"{heading}\n{body}"
        if parts:
            parts.append("\n\n")
            cursor += 2
        start = cursor
        parts.append(block)
        cursor += len(block)
        passages.append({
            "heading": heading,
            "start_offset": start,
            "end_offset": cursor,
            "length": cursor - start,
            "text": block,
            "sha256": sha(block),
        })
    return "".join(parts), passages


def main() -> int:
    rng = Random(20260822)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT c.chain_id, c.entity_id, c.person_key, c.effective_pct,
                   v.name AS entity_name, p.display_name,
                   c.person_is_eu_resident
              FROM bo_chain c
              JOIN offshore_vehicle v ON v.vehicle_id = c.entity_id
              JOIN person p ON p.person_key = c.person_key
             ORDER BY c.chain_id
        """)
        chains = cur.fetchall()
        cur.execute("SELECT vehicle_id, name, jurisdiction FROM offshore_vehicle")
        vehicle_juris = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        cur.execute("SELECT jurisdiction, threshold_pct FROM bo_threshold "
                    "WHERE intent = 'onboarding'")
        thresholds = {j: float(t) for j, t in cur.fetchall()}
        cur.execute("SELECT display_name FROM person WHERE person_key_source='psc'")
        all_names = [r[0] for r in cur.fetchall()]

    default_threshold = 25.0
    print("Wave 13b Task 7 — KYC documents and passages\n")
    print(f"  chains available   {len(chains)}")

    subjects = rng.sample(chains, min(TARGET_DOCUMENTS, len(chains)))

    # An `understated_pct` contradiction only EXISTS where the true effective
    # stake clears the threshold — understating 20% to 18% conceals nothing,
    # because there was no reportable owner either way. The first version
    # planted both on chains already below 25% (4.32% and 20.38%), so the gate
    # recomputed zero of them: a condition counted but not created, which is
    # precisely the failure CLAUDE.md's "volume targets are floors with a
    # purpose" warns about. Subjects are now chosen by eligibility.
    def threshold_for(entity_id: str) -> float:
        return thresholds.get(vehicle_juris[entity_id][1], default_threshold)

    eligible_understate = [
        i for i, sub in enumerate(subjects)
        if float(sub[3]) >= threshold_for(sub[1])
    ]
    if len(eligible_understate) < 2:
        print(f"  FAIL: only {len(eligible_understate)} chain(s) clear their "
              f"threshold; an understated declaration cannot conceal anything")
        return 1

    understate_slots = rng.sample(eligible_understate, 2)
    remaining = [i for i in range(len(subjects)) if i not in understate_slots]
    other_slots = rng.sample(remaining, CONTRADICTION_COUNT - 2)
    planned = {i: "understated_pct" for i in understate_slots}
    planned[other_slots[0]] = "wrong_person"
    planned[other_slots[1]] = "stale_owner"
    contradiction_slots = set(planned)

    documents = []
    all_passages = []
    for i, (chain_id, entity_id, person_key, effective_pct, entity_name,
            person_name, person_is_eu_resident) in enumerate(subjects):
        _name, juris = vehicle_juris[entity_id]
        threshold = thresholds.get(juris, default_threshold)
        declared_on = AS_OF - timedelta(days=rng.randrange(30, 900))

        contradiction = None
        declared_owner = person_name
        declared_owner_key = person_key
        declared_pct = float(effective_pct)

        if i in contradiction_slots:
            contradiction = planned[i]
            if contradiction == "wrong_person":
                # A DIFFERENT person entirely. The dangerous case: a screening
                # system trusting the declaration screens the wrong human.
                others = [n for n in all_names if n != person_name]
                declared_owner = rng.choice(others)
                declared_owner_key = None
            elif contradiction == "understated_pct":
                # Pushed below the threshold while the chain clears it, so the
                # declaration reads as "nothing to report". Only assigned to
                # chains that DO clear it — see the eligibility filter above.
                declared_pct = round(rng.uniform(1.0, threshold - 1.0), 2)
            else:  # stale_owner
                others = [n for n in all_names if n != person_name]
                declared_owner = rng.choice(others)
                declared_owner_key = None
                declared_pct = round(float(effective_pct) * 0.5, 2)

            kind, title = DOC_KINDS[0]      # always an ownership declaration
        else:
            kind, title = rng.choice(DOC_KINDS)

        if kind == "ownership_declaration":
            sections = declaration_text(entity_name, juris, declared_owner,
                                        declared_pct, declared_on, threshold)
        else:
            sections = generic_text(kind, title, entity_name, juris, declared_on)

        text, passages = assemble(sections)
        document_id = f"KYC-{i + 1:04d}"
        documents.append({
            "document_id": document_id,
            "title": f"{title} — {entity_name}",
            "kind": kind,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "jurisdiction": juris,
            "chain_id": chain_id,
            "declared_on": declared_on.isoformat(),
            # Structured claims. The gate compares THESE to bo_chain; it never
            # reads a "contradicts" flag, and none is written.
            "declared_owner_name": declared_owner if kind == "ownership_declaration" else None,
            "declared_owner_person_key": declared_owner_key if kind == "ownership_declaration" else None,
            "declared_pct": declared_pct if kind == "ownership_declaration" else None,
            "applicable_threshold_pct": threshold,
            "text": text,
            "text_length": len(text),
            "text_sha256": sha(text),
            "passage_count": len(passages),
            "classification": "confidential",
            # Residency follows the PERSON the file concerns, not the
            # entity's place of incorporation. GDPR restricts transfers of
            # personal data; an offshore vehicle's jurisdiction says nothing
            # about where its beneficial owner lives. Keying on the vehicle
            # made this field constant ('GLOBAL' on all 32) — a column that
            # never varies cannot discriminate anything downstream.
            "residency": "EU" if person_is_eu_resident else "GLOBAL",
            "provenance": "synthetic — internal",
            "source": "invented KYC file; no public equivalent exists at "
                      "document level (§C)",
            # Recorded for the record's sake, NOT for the gate: the gate
            # recomputes the disagreement from declared_* vs bo_chain.
            "planted_contradiction_kind": contradiction,
        })
        for j, p in enumerate(passages, start=1):
            all_passages.append({
                "passage_id": f"{document_id}-P{j:02d}",
                "document_id": document_id,
                **p,
                "structure_aligned": True,
                "alignment": "heading",
                "provenance": "derived",
            })

    kinds = Counter(d["kind"] for d in documents)
    planted = Counter(d["planted_contradiction_kind"] for d in documents
                      if d["planted_contradiction_kind"])
    declarations = [d for d in documents if d["kind"] == "ownership_declaration"]

    print(f"  documents          {len(documents)}   {dict(kinds)}")
    print(f"  passages           {len(all_passages)}")
    print(f"  ownership declarations {len(declarations)}")
    print(f"  planted contradictions {sum(planted.values())}  {dict(planted)}")

    # Verify the offsets before writing: a passage that does not re-slice to
    # its own hash is an anchoring defect, and this is the cheapest place to
    # find it.
    bad = []
    by_doc = {d["document_id"]: d for d in documents}
    for p in all_passages:
        text = by_doc[p["document_id"]]["text"]
        if sha(text[p["start_offset"]:p["end_offset"]]) != p["sha256"]:
            bad.append(p["passage_id"])
    print(f"  offset check       {len(all_passages) - len(bad)}/"
          f"{len(all_passages)} passages re-slice to their own hash")

    # Every planted contradiction must actually BE one when recomputed the way
    # validators/beneficial_ownership.py recomputes it. A plant that does not
    # reproduce is a label, not a condition.
    realised = {"wrong_person": 0, "understated_pct": 0, "stale_owner": 0}
    for d in documents:
        kind = d["planted_contradiction_kind"]
        if not kind:
            continue
        true_pct = float(next(c[3] for c in subjects if c[0] == d["chain_id"]))
        true_name = next(c[5] for c in subjects if c[0] == d["chain_id"])
        if kind in ("wrong_person", "stale_owner"):
            if d["declared_owner_name"] != true_name:
                realised[kind] += 1
        elif d["declared_pct"] < d["applicable_threshold_pct"] <= true_pct:
            realised[kind] += 1
    print(f"  recomputed as real     {realised}")

    failures = []
    unrealised = [k for k, v in realised.items()
                  if planted.get(k, 0) and not v]
    if unrealised:
        failures.append(f"planted but NOT reproducible when recomputed: "
                        f"{unrealised} — a label, not a condition")
    if bad:
        failures.append(f"{len(bad)} passage(s) do not re-slice: {bad[:3]}")
    if len(documents) < 30:
        failures.append(f"§F8: {len(documents)} documents, floor ~30")
    if sum(planted.values()) < 1:
        failures.append("§F8: no ownership declaration contradicts the registry")
    if len(planted) < 2:
        failures.append("only one KIND of contradiction planted; they fail "
                        "differently and one kind proves only that kind")
    if failures:
        print()
        for f in failures:
            print(f"  FAIL  {f}")
        return 1

    out = SCREEN / "wave13b_kyc_documents.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 13b — KYC documents and passages (§C, §F8)",
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "as_of": AS_OF.isoformat(),
                "document_count": len(documents),
                "passage_count": len(all_passages),
                "declaration_count": len(declarations),
                "planted_contradictions": dict(planted),
                "documents": documents,
                "passages": all_passages,
            },
            indent=1,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)} "
          f"({out.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
