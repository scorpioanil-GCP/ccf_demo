#!/usr/bin/env python3
"""Wave 18 Task 10 -- the two asymmetric bilateral disclosure envelopes.

Writes `sources/screening/wave18_envelopes.json`, consumed by
`loaders/load_fluree_wave18.py::build_envelopes`. §C assigns "bilateral
disclosure envelopes per counterparty" to Fluree as `P`, `T` --
`synthetic — internal` -- negotiated bilaterally between our desk and each
counterparty, never derived from public filings.

## Two counterparties, per design §6

Bank of America, N.A. (`SYNM-9d3fd0fd`) is the primary co-lender, disclosure
precision `exact` (Task 14-16 territory). Citibank, N.A. (`SYNM-8e5427c6`)
is the second peer identity, disclosure precision `band` -- both member_ids
resolved from `wave18_institutions.json` here, not hard-coded, the same
`_jpmorgan_member_id`-style resolve-and-assert
`generate_syndicate_internal.py` already uses, so a changed artifact fails
loudly instead of silently binding the wrong node.

## Element vocabulary -- reused, not invented

§F: "≥ 2 bilateral envelopes with asymmetric terms, so request-scope and
disclose-scope visibly differ." Every scope element named below is drawn
from `generate_syndicate_internal.py::PLANS` -- the same element vocabulary
Task 7's three `syndicate_projection_plan` rows use -- so Task 16's
assembly can resolve every element to something real. Nothing here is a
parallel, invented name; `_assert_known_elements` enforces this at
generation time, not only by convention.

## What the asymmetry encodes

Neither envelope's `disclose_scope` ever contains `own_position` -- the
element that carries `internal_rating` and `workout_posture`. That is not
an arbitrary omission: `competition_law_rule` CLR-003 (Task 6,
`wave18_internal.json`) states this bank's own workout posture and
restructuring intent "must not be communicated to a co-lender before it is
raised through the formal steering committee or agent bank process." The
envelope enforces exactly that boundary on our OUTBOUND side. It does not
constrain what we may RECEIVE -- a peer disclosing its own `own_position`
to us is that peer's own compliance decision, not ours -- which is why
`request_scope` is allowed to ask for it while `disclose_scope` never
offers it back. Neither scope ever names a pricing/spread element (CLR-001)
or another borrower's terms (CLR-002): this vocabulary has no such element
to begin with, so those two rules are honoured by omission rather than by
a runtime check.

**Both envelopes' own request and disclose scopes are, in fact, entirely
disjoint sets** -- nothing either envelope asks a counterparty for is also
something it hands back, and vice versa. That is the concrete shape
"asymmetric" takes here -- sharper than any subset relation, and it is
what the loaded data actually shows (confirmed by fix round 1's live
recomputation, not merely asserted in this docstring).

**Bank of America** -- exact precision, the primary co-lender we hold the
richest relationship with. We request `own_position` (their rating and
workout posture on the shared facilities, at THEIR discretion to share) and
`member_commitment` (their own filed commitment figure -- concrete
grounding: `docs/wave18-design.md` §7 records that per-lender commitment
shares do NOT reconcile against any facility's recorded total across all
twelve Wave 18 facilities, so confirming a co-lender's own filed number
directly is a real desk workflow, not a demo convenience). We disclose
`syndicate_composition` (who else is in the syndicate -- filed, not
sensitive) and `amendment_vote_posture` (our own stated position on the
open vote -- a courtesy circulated through the agent in practice, but
within the envelope's own remit to state explicitly).

**Citibank** -- band precision, a narrower relationship. Citibank both
requests and discloses FEWER elements than BofA -- one against two in each
direction, not a subset of BofA's scopes (the request sides do not even
overlap: BofA's own request is `{own_position, member_commitment}`,
Citibank's is `{amendment_vote_posture}`, disjoint from it). We request
only `amendment_vote_posture` (not their full position) and disclose only
`syndicate_composition` (not our own vote posture back) -- a band-precision
peer both receives and grants less than an exact-precision one.

## Versioning

§E gives envelopes a ~365-day `λ_c` and lists renegotiation as a
supersession trigger; §C assigns `T` alongside `P`. `envelope_version` is
`"v1"` for both -- this task mints the first version of each, nothing to
supersede yet. `valid_from` reuses the estate's standing valid-time
spelling (`ex:validFrom`, see `ccf/syndicate.py::EX_VALID_FROM`'s own
docstring for why `ex:effectiveFrom` is deliberately NOT minted here), set
to `AS_OF` below -- the same date `generate_syndicate_internal.py` uses for
its own_position rows, so every synthetic-internal artifact in this wave
carries one consistent as-of date rather than a silent drift between them.

Run: uv run generators/generate_disclosure_envelopes.py
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from ccf.config import REPO_ROOT
from generators.generate_syndicate_internal import PLANS

SCREEN = REPO_ROOT / "sources" / "screening"
INSTITUTIONS_PATH = SCREEN / "wave18_institutions.json"
OUT = SCREEN / "wave18_envelopes.json"

#: Same as-of date `generate_syndicate_internal.py::AS_OF` uses -- one
#: consistent date across this wave's synthetic-internal artifacts.
AS_OF = date(2026, 8, 26)

#: Real GLEIF LEIs -- resolved and asserted against the artifact below, not
#: trusted blind, the same discipline `_jpmorgan_member_id` already uses.
BOFA_LEI = "B4TYDEB6GKMZO031MB27"
CITIBANK_LEI = "E57ODZWZ7FF32TWEFA76"

#: The full element vocabulary this wave's projection plans use --
#: envelope scope elements must be a subset of this, or a scope names
#: something Task 16's assembly can never resolve.
KNOWN_ELEMENTS: set[str] = set().union(*PLANS.values())

ENVELOPE_SPECS = [
    {
        "counterparty_lei": BOFA_LEI,
        "counterparty_label": "Bank of America, N.A.",
        "request_scope": ["own_position", "member_commitment"],
        "disclose_scope": ["syndicate_composition", "amendment_vote_posture"],
        "envelope_version": "v1",
        "rationale": (
            "primary co-lender, exact precision. We request their own "
            "position (rating, workout posture -- at their discretion to "
            "share, not ours to disclose) and their own filed commitment "
            "figure (per-lender shares do not reconcile against any "
            "facility total, design §7, so confirming directly is a real "
            "desk need). We disclose only syndicate composition and our "
            "own vote posture -- never own_position outbound, honouring "
            "CLR-003's ban on informally sharing our workout intent."
        ),
    },
    {
        "counterparty_lei": CITIBANK_LEI,
        "counterparty_label": "Citibank, N.A.",
        "request_scope": ["amendment_vote_posture"],
        "disclose_scope": ["syndicate_composition"],
        "envelope_version": "v1",
        "rationale": (
            "band precision, a narrower relationship -- Citibank both "
            "requests and discloses fewer elements than BofA (one against "
            "two in each direction), not a subset of BofA's scopes -- the "
            "request sides do not overlap at all. We request only their "
            "vote posture (not their full position) and disclose only "
            "syndicate composition (not our own vote posture back). A "
            "band-precision peer receives and grants less than an "
            "exact-precision one."
        ),
    },
]


def _resolve_member(institutions: dict, lei: str, expected_label_substring: str
                     ) -> dict:
    matches = [m for m in institutions["members"] if m["lei"] == lei]
    assert len(matches) == 1, (
        f"expected exactly one member with LEI {lei}, found {len(matches)}")
    member = matches[0]
    assert expected_label_substring.upper() in member["legal_name"].upper(), (
        f"LEI {lei} resolves to {member['legal_name']!r}, not a name "
        f"containing {expected_label_substring!r} -- facts changed "
        f"underneath this task")
    return member


def _assert_known_elements(spec: dict) -> None:
    for key in ("request_scope", "disclose_scope"):
        elements = spec[key]
        assert elements, (
            f"{spec['counterparty_label']}: {key} is empty -- an envelope "
            f"that requests or discloses nothing proves nothing (§F)")
        unknown = set(elements) - KNOWN_ELEMENTS
        assert not unknown, (
            f"{spec['counterparty_label']}: {key} names element(s) not in "
            f"any syndicate_projection_plan perspective -- invented "
            f"vocabulary Task 16 can never resolve: {sorted(unknown)}")
    assert set(spec["request_scope"]) != set(spec["disclose_scope"]), (
        f"{spec['counterparty_label']}: request_scope and disclose_scope "
        f"are the SAME set -- this envelope is not asymmetric")
    #: Whole-branch review fix. The module docstring states "both envelopes'
    #: own request and disclose scopes are, in fact, entirely disjoint
    #: sets" -- a stronger claim than != above, and until now enforced
    #: nowhere: a third envelope sharing even one element across its two
    #: scopes would falsify that published statement silently.
    overlap = set(spec["request_scope"]) & set(spec["disclose_scope"])
    assert not overlap, (
        f"{spec['counterparty_label']}: request_scope and disclose_scope "
        f"share element(s) {sorted(overlap)} -- the module docstring's "
        f"disjointness claim does not hold for this envelope")


def build_envelopes(institutions: dict) -> list[dict]:
    envelopes = []
    for spec in ENVELOPE_SPECS:
        _assert_known_elements(spec)
        member = _resolve_member(
            institutions, spec["counterparty_lei"],
            spec["counterparty_label"].split(",")[0])
        envelopes.append({
            "counterparty_member_id": member["member_id"],
            "counterparty_lei": spec["counterparty_lei"],
            "counterparty_legal_name": member["legal_name"],
            "request_scope": spec["request_scope"],
            "disclose_scope": spec["disclose_scope"],
            "envelope_version": spec["envelope_version"],
            "valid_from": AS_OF.isoformat(),
            "rationale": spec["rationale"],
            "provenance": "synthetic — internal",
        })

    # Cross-envelope check: the two envelopes must differ from each other,
    # not merely be internally asymmetric each on its own (design §6/CLAUDE
    # instructions -- "the two envelopes should differ from each other, not
    # just internally").
    req_sets = [frozenset(e["request_scope"]) for e in envelopes]
    dis_sets = [frozenset(e["disclose_scope"]) for e in envelopes]
    assert len(set(req_sets)) > 1 or len(set(dis_sets)) > 1, (
        "the two envelopes' scopes are identical to each other -- the "
        "asymmetry must vary by counterparty, not be a fixed template")

    return envelopes


def main() -> int:
    institutions = json.loads(INSTITUTIONS_PATH.read_text())
    envelopes = build_envelopes(institutions)

    asymmetric = [e for e in envelopes
                  if set(e["request_scope"]) != set(e["disclose_scope"])]
    assert len(asymmetric) >= 2, (
        f"§F requires >= 2 asymmetric envelopes, got {len(asymmetric)}")

    doc = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Task 10",
        "method": (
            "two bilateral envelopes, one per peer counterparty identity "
            "(design §6) -- Bank of America (exact) and Citibank (band). "
            "Scope elements drawn from generate_syndicate_internal.py's "
            "PLANS vocabulary (the same one Task 7's syndicate_projection_"
            "plan rows use); asymmetry grounded against Task 6's "
            "competition_law_rule rows, checked here at generation time"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "envelope_count": len(envelopes),
        "asymmetric_envelope_count": len(asymmetric),
        "envelopes": envelopes,
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"wrote {OUT.relative_to(REPO_ROOT)}: {len(envelopes)} envelopes, "
          f"{len(asymmetric)} genuinely asymmetric")
    for e in envelopes:
        print(f"  {e['counterparty_legal_name']:<28} "
              f"request={e['request_scope']} disclose={e['disclose_scope']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
