#!/usr/bin/env python3
"""Wave 18 Task 14 -- the CO-LENDER's own positions, at two disclosure
precisions.

Writes `sources/screening/wave18_peer.json`. Writes nothing to any store:
`loaders/load_peer_wave18.py` does the loading, and it is the only file in
this repository that connects to the peer fabric.

## What this produces, and why it is not our data

The product is `syndicated-lending-co-lender`, and §C files the peer as
`Simulated peer fabric -- a second CCF instance | synthetic --
engineered | separate instance`. The whole demonstration is assembly
ACROSS an organizational boundary, so the peer's estate has to be two
things at once: genuinely separate (its own database, role, ledger --
enforced by `validators/test_fabric_isolation.py`, not by convention),
and genuinely LESS PRECISE than our own. A peer that answered every
question exactly would make the boundary invisible.

Two counterparty identities live on that fabric, the same two Task 10's
bilateral envelopes name (`sources/screening/wave18_envelopes.json`):

    Bank Of America, National Association  B4TYDEB6GKMZO031MB27  exact
    Citibank, National Association         E57ODZWZ7FF32TWEFA76  band

`counterparty` is the LEI, not our `SYNM-` member id. A `SYNM-` id is an
identifier this project minted for its own use; it means nothing on
another bank's fabric, and keying the peer's rows on it would quietly
make the boundary a fiction -- the two estates would share a private
namespace. LEI is the one identifier both sides genuinely hold, and
CLAUDE.md rule 4 already names it as the key that spans the public side.

## Positions are DERIVED FROM THE STORE, never typed out

Every (counterparty, facility) pair and every dollar figure below comes
from a live SPARQL query against OUR Fluree ledger's
`ex:SyndicateParticipation` nodes -- the reified commitment edges Task 8
built from the six filed commitment schedules. Nothing here hand-types a
facility id or an amount.

That matters twice over. It guarantees the peer's rows reference
facilities that genuinely exist on our side (a peer position on a
facility we do not hold is unassemblable and would fail silently), and
it means the AHR positional split -- Schedule 2.01A carries two dollar
columns under one parsed tranche label, see `ccf.syndicate`'s
`TRANCHE_TO_FACILITIES` note -- is read exactly once, by
`loaders/load_fluree_wave18.py`, rather than re-implemented here and
left to drift. `ccf_v2.facility` is then read (read-only) to confirm
every derived facility_id is a real row, and `WAVE18_EXCLUDED_FACILITIES`
(Ruling T6-R2) is applied to this artifact's own output.

## The mixed-precision condition: engineered, not counted

§F's floor is that one counterparty discloses an exact figure and another
discloses only a band. Two properties make that real, and neither is a
row count:

**1. The band must not resolve to the figure.** The band is a lookup on a
fixed, published ladder (`BAND_LADDER_USD`), NOT a function of the
position it covers. Every position between $20M and $140M discloses the
identical band, so knowing the ladder -- knowing this file -- narrows the
figure no further than the band already does. A band computed as
"true +/- x%" would be invertible by anyone who read the generator; this
one is not. What IS engineered is the ladder's own boundaries, chosen so
that the one banded position lands well away from every naive estimator
of a band (midpoint, geometric mean, quartiles, terciles) -- see
`band_for()`. That choice is the engineering, and the rows it produces
are labelled `synthetic -- engineered` for exactly that reason.

**2. The banded counterparty must carry no exact figure ANYWHERE on the
peer fabric** -- not merely on the rows flagged as banded. This artifact
therefore never records the true figure for a banded counterparty, in any
field: not as `share_usd`, not in `basis`, not in a comment. `basis`
cites the filed document and character offsets instead, so the figure
stays re-derivable from the public filing by anyone holding OUR estate,
and unavailable to anyone holding the peer's. `_assert_no_banded_figure_
leaks()` re-checks that against the serialized JSON before it is written.

The figure being public on our side does not weaken the floor. §F is
about what the peer DISCLOSES through the negotiated interface; Task 16
assembles from the peer's disclosure, not from our copy of the filing.
It is what makes the placement checkable rather than a claim --
`validators/test_syndicate.py` re-derives it from
`wave18_schedules.json`, independently of anything this file emits.

    uv run generators/generate_peer_positions.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect
from ccf.syndicate import (
    LOCAL_COMPOSITE_TTL_SECONDS,
    MAX_FEDERATION_LATENCY_MS,
    WAVE18_EXCLUDED_FACILITIES,
)

SCREEN = REPO_ROOT / "sources" / "screening"
OUT_PATH = SCREEN / "wave18_peer.json"

#: Pinned, not `date.today()`. Wave 16's `AS_OF_IB` records why the estate
#: pins its as-of dates: a floating one silently re-dates every row on every
#: re-run, and an idempotency check comparing a named value would then fail
#: for a reason that has nothing to do with the loader.
AS_OF = date(2026, 8, 26)

#: The two counterparty identities, and their disclosure precision. Same two
#: Task 10 wrote bilateral envelopes for; the LEIs are real GLEIF
#: registrations recorded in `sources/screening/wave18_institutions.json`.
BOFA_LEI = "B4TYDEB6GKMZO031MB27"
CITI_LEI = "E57ODZWZ7FF32TWEFA76"

DISCLOSURE_PRECISION: dict[str, str] = {
    BOFA_LEI: "exact",
    CITI_LEI: "band",
}

#: Task 15 -- the three §F conditions that sound like runtime behaviour but
#: are declarations in data: a request that times out, a claim nobody
#: attested, a remote TTL shorter than ours. §B's own request-parameter
#: surface names both bounds this file engineers against:
#: `max_federation_latency` defaults to 5s; the product's local TTL is 4h.
#: The SDK reads these declarations and acts on them -- this project never
#: acts, it only writes the row the SDK would read.
# MAX_FEDERATION_LATENCY_MS and LOCAL_COMPOSITE_TTL_SECONDS (both §B) are
# imported from ccf/syndicate.py, not redefined here (whole-branch review
# fix -- consolidates what were four independent copies under two names).

#: The remote product's address, per §B's own addressability pattern
#: (`/context-products/cb/syndicate/{facility-id}/co-lender-position`).
#: Not a new binding: it is a text value stamped into a Postgres column,
#: never an `ex:`/FIBO IRI, and it reuses the path the spec already
#: publishes rather than inventing one.
PRODUCT_ADDRESS_PREFIX = "/context-products/cb/syndicate"

#: The peer's published disclosure-band ladder, in USD. A position is
#: disclosed as the tier that CONTAINS it -- a lookup, never a function of
#: the position, so the same band covers everything from $20M to $140M and
#: reading this ladder narrows nothing.
#:
#: The boundaries are engineered (see the module docstring). The one banded
#: position this wave carries -- Citibank's AHR revolving commitment, a
#: filed public figure this file deliberately does not repeat -- sits at
#: 41.7% of the second tier's width, which puts it at least 14.3% away from
#: the band's midpoint, geometric mean, both outer quartiles and both
#: terciles. `band_for()` re-proves that from the ladder on every run
#: rather than trusting this sentence.
#:
#: Note what this comment is and is not. A placement fraction beside the
#: bounds INVERTS -- 20M + 0.417 x 120M is the figure, and so is
#: 80M / 1.143 -- which is exactly why Ruling T14-R2 struck the same two
#: quantities out of the emitted artifact. It is stated here because a
#: source comment is not loader input and cannot be carried across the
#: boundary by a later task, and because the figure is public on OUR side
#: anyway (Ruling T14-R1): it is a filed SEC schedule row and a literal in
#: our own Fluree ledger. The property under test was only ever "absent
#: from the PEER fabric". Do not read this comment as a pattern to copy
#: into `sources/screening/*.json`, which is where it was wrong.
BAND_LADDER_USD: tuple[int, ...] = (0, 20_000_000, 140_000_000, 500_000_000)

#: The naive estimators a reader holding only the band might reach for. A
#: band that puts any of them on the true figure has disclosed the figure.
#: Fractions of the band width, low -> high.
NAIVE_ESTIMATOR_FRACTIONS: dict[str, float] = {
    "midpoint": 0.5,
    "lower quartile": 0.25,
    "upper quartile": 0.75,
    "lower tercile": 1 / 3,
    "upper tercile": 2 / 3,
}

#: The margin every naive estimator must clear, as a fraction of the true
#: figure. Asserted in `band_for()`; the test suite re-derives the true
#: figure from the filed schedules and re-checks the same bound.
MIN_ESTIMATOR_MARGIN = 0.10

#: The peer's own view of each facility it lends on. Invented -- another
#: bank's internal credit opinion is bank-internal by nature and exists in
#: no public source (CLAUDE.md's second provenance class).
#:
#: The VOCABULARY is deliberately not ours. Our `own_position` rows carry
#: notch grades (`BBB-`, `B+`, `A`) from `ccf_v2.rating_scale`; a peer's
#: internal scale is its own and is not comparable notch-for-notch, so
#: pretending both sides share one scale would invent an agreement that
#: does not exist. These are the regulatory classification categories the
#: Shared National Credit programme itself uses (`sources/snc/` --
#: pass / special mention / substandard), which is the one credit
#: vocabulary both banks genuinely share, and which is coarser than ours.
#: The peer being coarser than us is the point of this task.
#:
#: The SNC report in `sources/snc/` carries programme-level aggregates
#: only -- no per-credit classification for any facility here -- so the
#: assignment of a category to a facility is invented, not read. The
#: vocabulary is public; the values are not.
PEER_VIEW: dict[str, dict[str, str]] = {
    "FAC-6F4065": {"internal_rating": "pass",
                   "workout_posture": "standard servicing"},
    "FAC-A4A5EE": {"internal_rating": "pass",
                   "workout_posture": "standard servicing"},
    "FAC-405B7A": {"internal_rating": "pass",
                   "workout_posture": "standard servicing"},
    "FAC-2A2C38": {"internal_rating": "pass",
                   "workout_posture": "standard servicing"},
    "FAC-E386A4": {"internal_rating": "pass",
                   "workout_posture": "standard servicing"},
    # The peer's own coarse view diverges from ours on exactly one credit.
    # A peer estate whose every row carried the same value would make any
    # query against it degenerate, and the divergence is the kind of thing
    # a co-lender product exists to surface. Invented, like every other
    # value in this table.
    "FAC-3DF1D5": {"internal_rating": "special mention",
                   "workout_posture": "enhanced monitoring"},
}

PROVENANCE_EXACT = "synthetic — internal"
PROVENANCE_BANDED = "synthetic — engineered"

#: CLAUDE.md's exact vocabulary, em dash and all.
PROVENANCE_CLASSES = {"public", "synthetic — internal", "synthetic — engineered"}

#: Task 15's three product declarations. `(counterparty, facility_id)` must
#: be a pair the peer genuinely holds a position on -- checked in
#: `build_declarations()` -- so a declaration never describes a product the
#: peer does not actually expose.
#:
#: Provenance per row, not per table (CLAUDE.md rule 1): the baseline row
#: is an ordinary invented bank-internal fact -- a peer declaring normal
#: service is not itself manufacturing a condition -- so it is
#: `synthetic — internal`, the same class Task 14 gave the exact-disclosure
#: rows. The other two exist *specifically* to create a condition public
#: data cannot supply (a timeout, an attestation gap), so they are
#: `synthetic — engineered`, the same class Task 14 gave the band.
DECLARATION_PROVENANCE_NORMAL = "synthetic — internal"
DECLARATION_PROVENANCE_ENGINEERED = "synthetic — engineered"

DECLARATION_SPECS: tuple[tuple, ...] = (
    # (counterparty, facility_id, ttl_seconds, latency_ms, attestation, provenance, note)
    (
        BOFA_LEI, "FAC-6F4065", 21_600, 650,
        {"method": "bilateral signed digest",
         "signer": "bofa_syndicated federation service",
         "signed_at": "2026-08-26T00:00:00Z"},
        DECLARATION_PROVENANCE_NORMAL,
        "baseline: fast (well under the 5s bound), attested, TTL at 6h "
        "(above the 4h local composite) -- the contrast case for both the "
        "timeout floor and the TTL floor. Without this row, every "
        "declaration would be slow or short-TTL and neither floor would "
        "prove anything.",
    ),
    (
        CITI_LEI, "FAC-405B7A", 10_800, 7_200,
        {"method": "bilateral signed digest",
         "signer": "bofa_syndicated federation service",
         "signed_at": "2026-08-26T00:00:00Z"},
        DECLARATION_PROVENANCE_ENGINEERED,
        "engineered to breach the default 5s max_federation_latency bound "
        "(§B) so fail-closed is observed rather than merely described. "
        "Still attested -- it is the LATENCY floor's contrast case, not "
        "the attestation floor's.",
    ),
    (
        BOFA_LEI, "FAC-A4A5EE", 7_200, 900,
        None,
        DECLARATION_PROVENANCE_ENGINEERED,
        "engineered unattested claim (attestation IS NULL) with a sub-4h "
        "TTL, so both the attestation floor and the 'TTL below the local "
        "composite' floor bind on one row. Fast latency on purpose -- it "
        "must not also be the timeout contrast, or the three floors stop "
        "being independently demonstrated.",
    ),
)


# --- derivation ------------------------------------------------------------

def derive_filed_shares() -> dict[tuple[str, str], dict]:
    """(counterparty LEI, facility_id) -> {"amount_usd", "passages"}.

    Read live from OUR Fluree ledger's reified participation nodes -- the
    store, never a hand-typed list. Amounts sum across the tranches that
    roll into one Postgres facility (RB Global's Revolving A/B/C all land
    on FAC-A4A5EE), which is the same accumulation
    `generators/generate_syndicate_internal.py::derive_positions` performs
    for our own side.
    """
    leis = " || ".join(f'?lei = "{lei}"' for lei in sorted(DISCLOSURE_PRECISION))
    sparql = (
        f"SELECT ?lei ?fac ?amt ?passage FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
        f"?p <{EX}participationOf> ?m . "
        f"?p <{EX}participationIn> ?fac . "
        f"?p <{EX}commitmentUsd> ?amt . "
        f"?p <{EX}sourcePassage> ?passage . "
        f"?m <{EX}lei> ?lei . "
        f"FILTER({leis}) }}"
    )
    bindings = fluree.query(sparql)["results"]["bindings"]
    assert bindings, (
        "no participation nodes found for either counterparty LEI -- "
        "loaders/load_fluree_wave18.py has not run, or the member nodes "
        "carry no ex:lei. Refusing to emit a peer estate derived from "
        "nothing.")

    out: dict[tuple[str, str], dict] = {}
    for b in bindings:
        lei = b["lei"]["value"]
        facility_id = b["fac"]["value"].rsplit("/", 1)[-1]
        assert facility_id.startswith("FAC-"), (
            f"participation node points at {b['fac']['value']!r}, which does "
            f"not resolve to a facility id")
        assert facility_id not in WAVE18_EXCLUDED_FACILITIES, (
            f"{facility_id} is excluded by Ruling T6-R2 "
            f"({WAVE18_EXCLUDED_FACILITIES.get(facility_id)}) but carries a "
            f"participation node -- the Fluree load is stale")
        row = out.setdefault((lei, facility_id),
                             {"amount_usd": 0, "passages": []})
        row["amount_usd"] += int(b["amt"]["value"])
        row["passages"].append(b["passage"]["value"])

    for row in out.values():
        row["passages"] = sorted(set(row["passages"]))
    return out


def assert_facilities_exist(facility_ids: set[str]) -> None:
    """Every facility the peer takes a position on must be a real row in
    `ccf_v2.facility`. Read-only, and it is the point of the exercise: a
    peer position on a facility our side does not hold cannot be assembled
    across the boundary, and nothing downstream would say so."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f'SELECT facility_id FROM "{PG_SCHEMA_V2}".facility '
            f"WHERE facility_id = ANY(%s)", (sorted(facility_ids),))
        found = {r[0] for r in cur.fetchall()}
    missing = sorted(facility_ids - found)
    assert not missing, (
        f"{missing} appear in Fluree participation nodes but are not rows "
        f"in {PG_SCHEMA_V2}.facility")


# --- the band --------------------------------------------------------------

def band_for(true_usd: int) -> tuple[int, int]:
    """The ladder tier containing `true_usd`, with every naive estimator
    re-proved to miss it by at least `MIN_ESTIMATOR_MARGIN`.

    The proof runs here, on every generation, against the ladder as it
    actually is -- not against a remembered claim about it. Change a
    boundary and this raises rather than quietly shipping a band centred
    on the answer.
    """
    for low, high in zip(BAND_LADDER_USD, BAND_LADDER_USD[1:]):
        if low < true_usd < high:
            break
    else:
        raise AssertionError(
            f"{true_usd} falls on a ladder boundary or outside the ladder "
            f"{BAND_LADDER_USD}. A figure sitting ON a bound is disclosed by "
            f"that bound; extend or move the ladder deliberately.")

    width = high - low
    for name, fraction in NAIVE_ESTIMATOR_FRACTIONS.items():
        estimate = low + fraction * width
        margin = abs(estimate - true_usd) / true_usd
        assert margin >= MIN_ESTIMATOR_MARGIN, (
            f"the band [{low}, {high}]'s {name} ({estimate:,.0f}) is within "
            f"{margin:.1%} of the true figure -- under the "
            f"{MIN_ESTIMATOR_MARGIN:.0%} floor, so the band leaks it")

    geometric = (low * high) ** 0.5 if low else 0.0
    if low:
        margin = abs(geometric - true_usd) / true_usd
        assert margin >= MIN_ESTIMATOR_MARGIN, (
            f"the band [{low}, {high}]'s geometric mean ({geometric:,.0f}) is "
            f"within {margin:.1%} of the true figure")

    return low, high


# `band_placement()` USED TO LIVE HERE, and it was a leak (Ruling T14-R2,
# fix round 1). It emitted `fraction_of_band_width` and
# `naive_estimator_margins` into the artifact beside the band bounds, and
# its docstring called that "safe to publish: it is only invertible if you
# already hold the true figure". That was false by two keys:
#
#     20e6 + 0.4167 * 120e6      = 70,004,000     (0.006% out)
#     80e6 / 1.1429              = 69,997,375     (0.004% out)
#
# The bounds are the only other input either inversion needs, and they sit
# in the same JSON object. The rationale named the reader it imagined --
# someone already holding the answer -- and missed the one that was
# actually there.
#
# The computation is NOT lost: `band_for()` above still derives every
# estimator and still refuses to return a band that lands within
# MIN_ESTIMATOR_MARGIN of the figure. That is where the work was always
# done. What is gone is publishing the result into a file this project
# commits to git and does not control the readers of. The placement stays
# independently checkable from
# `validators/test_syndicate.py::test_the_band_brackets_the_filed_figure_
# without_revealing_it`, which re-derives the figure from the filed
# schedule rather than from anything this generator emits.


# --- rows ------------------------------------------------------------------

def position_id(lei: str, facility_id: str) -> str:
    """Content-derived and stable: a hash of the two things that identify
    the position, and nothing else. Never a row index -- four loaders on
    `main` already rewrite other waves' rows when a table grows, and a
    positional key is how. `as_of` is deliberately NOT in the digest: a
    re-dated run must update the row it already wrote, not mint a second."""
    digest = hashlib.sha256(f"{lei}|{facility_id}".encode()).hexdigest()
    return f"PPOS-{digest[:10].upper()}"


def product_id_for(facility_id: str) -> str:
    """The remote product's address for one facility, per §B's own
    addressability pattern -- not a value this file invents."""
    return f"{PRODUCT_ADDRESS_PREFIX}/{facility_id}/co-lender-position"


def declaration_id(lei: str, product_id: str) -> str:
    """Content-derived and stable, same discipline as `position_id()`: a
    hash of the two things that identify the declaration, never a row
    index."""
    digest = hashlib.sha256(f"{lei}|{product_id}".encode()).hexdigest()
    return f"PDEC-{digest[:10].upper()}"


def build_rows(filed: dict[tuple[str, str], dict]) -> list[dict]:
    rows: list[dict] = []
    for (lei, facility_id), filed_row in sorted(filed.items()):
        precision = DISCLOSURE_PRECISION[lei]
        view = PEER_VIEW.get(facility_id)
        assert view is not None, (
            f"{facility_id}: no PEER_VIEW entry. A new facility must be given "
            f"the peer's own rating and posture deliberately, not defaulted "
            f"into one.")

        row = {
            "position_id": position_id(lei, facility_id),
            "counterparty": lei,
            "facility_id": facility_id,
            "share_usd": None,
            "band_low": None,
            "band_high": None,
            "internal_rating": view["internal_rating"],
            "workout_posture": view["workout_posture"],
            "as_of": AS_OF.isoformat(),
            "provenance": (PROVENANCE_EXACT if precision == "exact"
                           else PROVENANCE_BANDED),
            # Traceability only -- the loader owns the DDL's columns and
            # ignores everything else here.
            "disclosure_precision": precision,
            "basis": {
                "source_passages": filed_row["passages"],
                "note": (
                    "the filed commitment-schedule rows this position is "
                    "derived from, cited as document#offset exactly as "
                    "Task 8's ex:sourcePassage does"),
            },
        }

        if precision == "exact":
            row["share_usd"] = filed_row["amount_usd"]
        else:
            low, high = band_for(filed_row["amount_usd"])
            row["band_low"] = low
            row["band_high"] = high
            row["basis"]["note"] += (
                "; the figure itself is deliberately absent from this "
                "artifact and from the peer fabric -- re-derive it from the "
                "cited filing offsets if you hold our estate")

        rows.append(row)
    return rows


def build_counterparties(rows: list[dict], filed: dict) -> list[dict]:
    """One entry per counterparty identity -- the peer's Fluree nodes."""
    labels = _legal_names()
    out = []
    for lei, precision in sorted(DISCLOSURE_PRECISION.items()):
        held = sorted(r["facility_id"] for r in rows if r["counterparty"] == lei)
        assert held, f"{lei} holds no position; a counterparty with no rows " \
                     f"cannot demonstrate a disclosure precision"
        out.append({
            "counterparty": lei,
            "legal_name": labels[lei],
            "disclosure_precision": precision,
            "facility_ids": held,
            "provenance": (PROVENANCE_EXACT if precision == "exact"
                           else PROVENANCE_BANDED),
        })
    return out


def _legal_names() -> dict[str, str]:
    """Legal names from the Task 3 institutions artifact -- public, GLEIF
    registered, never retyped here."""
    doc = json.loads((SCREEN / "wave18_institutions.json").read_text())
    names = {m["lei"]: m["legal_name"] for m in doc["members"] if m["lei"]}
    for lei in DISCLOSURE_PRECISION:
        assert lei in names, (
            f"{lei} is not a member in wave18_institutions.json -- the peer's "
            f"counterparty identities must be the same institutions our own "
            f"side resolved, not new ones invented here")
    return names


def build_declarations(rows: list[dict]) -> list[dict]:
    """Task 15's three product declarations, tied to real peer positions.

    Each `(counterparty, facility_id)` in `DECLARATION_SPECS` must already
    be a position this artifact holds (`rows`, from `build_rows()`) -- a
    declaration describing a product the peer does not actually expose
    would be unassemblable and would fail silently, same reasoning as
    `assert_facilities_exist()` above for positions.
    """
    held = {(r["counterparty"], r["facility_id"]) for r in rows}
    declarations = []
    for lei, facility_id, ttl, latency, attestation, provenance, note \
            in DECLARATION_SPECS:
        assert (lei, facility_id) in held, (
            f"{lei} holds no position on {facility_id} -- a product "
            f"declaration must describe a product the peer actually "
            f"exposes")
        pid = product_id_for(facility_id)
        declarations.append({
            "declaration_id": declaration_id(lei, pid),
            "counterparty": lei,
            "product_id": pid,
            "declared_ttl_seconds": ttl,
            "declared_latency_ms": latency,
            "attestation": attestation,
            "provenance": provenance,
            "note": note,
        })

    ids = [d["declaration_id"] for d in declarations]
    assert len(ids) == len(set(ids)), "duplicate declaration_id"
    return declarations


def assert_declarations_shape(declarations: list[dict]) -> None:
    """Refuse to write an artifact whose declarations collapse a contrast.

    Re-proves §F's three floors here, before anything is written, the same
    way `assert_artifact_shape()` re-proves the mixed-precision floor for
    positions above.
    """
    assert declarations, "no product declarations at all"

    for d in declarations:
        assert d["provenance"] in PROVENANCE_CLASSES, (
            f"{d['declaration_id']}: provenance {d['provenance']!r} is not "
            f"one of CLAUDE.md's three classes")

    assert len(declarations) > 1, (
        "only one declaration -- if everything is unattested, nothing is "
        "contrasted, and one row cannot show that")

    unattested = [d for d in declarations if d["attestation"] is None]
    assert len(unattested) == 1, (
        f"{len(unattested)} unattested declarations; the floor needs "
        f"exactly one so the case stays identifiable")

    latencies = [d["declared_latency_ms"] for d in declarations]
    assert any(l > MAX_FEDERATION_LATENCY_MS for l in latencies), (
        f"no declaration exceeds the {MAX_FEDERATION_LATENCY_MS}ms "
        f"default bound -- fail-closed would never be observed")
    assert any(l <= MAX_FEDERATION_LATENCY_MS for l in latencies), (
        "every declaration is slow -- a fabric where every peer times out "
        "demonstrates nothing about fail-closed, it just looks broken")

    ttls = [d["declared_ttl_seconds"] for d in declarations]
    assert min(ttls) < LOCAL_COMPOSITE_TTL_SECONDS, (
        f"shortest declared TTL is {min(ttls)}s; the local composite is "
        f"{LOCAL_COMPOSITE_TTL_SECONDS}s, so the TTL floor would never bind")
    assert max(ttls) > LOCAL_COMPOSITE_TTL_SECONDS, (
        "no declared TTL exceeds the local composite -- a TTL merely equal "
        "to it does not show the local composite winning as the shorter "
        "value, so the 'shortest of them' rule would stay untested")


# --- self-check ------------------------------------------------------------

def assert_no_banded_figure_leaks(document: dict,
                                  filed: dict[tuple[str, str], dict]) -> None:
    """Scan the serialized artifact for four literal spellings of the
    banded figure.

    **This is a digit-spelling scan and nothing more.** It catches the
    figure written out; it does not and cannot catch the figure being
    RECONSTRUCTIBLE from other fields. It reported green for exactly that
    reason in the first round of this task, while `band_placement()` --
    six functions above it, in this same module -- was publishing the
    fractions needed to invert the band back to the figure (Ruling
    T14-R2). An earlier version of this docstring claimed it caught the
    figure "in any field or any spelling of the digits", which is the
    claim that made the green reading trustworthy and wrong.

    The defence against reconstruction is not here. It is that the
    artifact carries no derived quantity of the figure at all -- only the
    band bounds, which is what a band IS -- and `band_for()` refuses to
    produce bounds a naive estimator resolves.

    Checked against the SERIALIZED text rather than the row dicts, because
    the spelling this can catch is one that reached the file through some
    field nobody thought to look at."""
    blob = json.dumps(document, ensure_ascii=False)
    for (lei, facility_id), filed_row in filed.items():
        if DISCLOSURE_PRECISION[lei] == "exact":
            continue
        amount = filed_row["amount_usd"]
        # Spellings a figure could plausibly reach a JSON file in. A bare
        # `amount / 1e6` ("70") is deliberately NOT among them: two digits
        # match inside offsets and unrelated amounts, so it would fail on
        # every run for reasons that have nothing to do with a leak -- a
        # check that cannot pass teaches as little as one that cannot fail.
        for spelling in (str(amount), f"{amount:,}",
                         f"${amount / 1e6:g}M", f"{amount / 1e6:g} million"):
            assert spelling not in blob, (
                f"the true figure for {lei} on {facility_id} appears in the "
                f"artifact as {spelling!r} -- a banded counterparty must "
                f"carry no exact figure anywhere")


def main() -> int:
    filed = derive_filed_shares()
    assert_facilities_exist({fid for _, fid in filed})

    rows = build_rows(filed)
    counterparties = build_counterparties(rows, filed)

    precisions = {c["disclosure_precision"] for c in counterparties}
    assert precisions == {"exact", "band"}, (
        f"§F's mixed-precision floor needs both precisions present, got "
        f"{precisions}")

    declarations = build_declarations(rows)
    assert_declarations_shape(declarations)

    document = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Tasks 14-15",
        "method": (
            "peer positions derived live from OUR Fluree ledger's "
            "ex:SyndicateParticipation nodes (the six filed commitment "
            "schedules, Task 8), keyed on the counterparty's real GLEIF LEI "
            "and confirmed against ccf_v2.facility. Bank of America "
            "discloses an exact figure; Citibank discloses only the band "
            "from a fixed published ladder that contains its position -- "
            "the ladder is a lookup, not a function of the figure, so it "
            "narrows nothing. The peer's internal rating and workout "
            "posture use the SNC programme's coarse regulatory categories, "
            "deliberately not our notch grades: the peer is less precise "
            "than we are, and that is what makes the boundary visible. "
            "Product declarations (Task 15) are the three §F conditions "
            "that sound like runtime behaviour -- a request that times "
            "out, a claim nobody attested, a remote TTL shorter than ours "
            "-- represented as declarations in data. The SDK reads and "
            "acts on them; this project never does."),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": AS_OF.isoformat(),
        "band_ladder_usd": list(BAND_LADDER_USD),
        "counterparties": counterparties,
        "positions": rows,
        "declarations": declarations,
    }

    assert_no_banded_figure_leaks(document, filed)
    OUT_PATH.write_text(json.dumps(document, indent=2, ensure_ascii=False)
                        + "\n")

    exact = sum(1 for r in rows if r["share_usd"] is not None)
    banded = len(rows) - exact
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  counterparties        {len(counterparties)}")
    print(f"  positions             {len(rows)} ({exact} exact, {banded} band)")
    for c in counterparties:
        print(f"  {c['counterparty']}  {c['disclosure_precision']:<5} "
              f"{len(c['facility_ids'])} facilities  {c['legal_name']}")
    print(f"  declarations          {len(declarations)}")
    for d in declarations:
        attested = "attested" if d["attestation"] is not None else "UNATTESTED"
        print(f"    {d['declaration_id']}  {d['counterparty']}  "
              f"ttl={d['declared_ttl_seconds']}s  "
              f"latency={d['declared_latency_ms']}ms  {attested}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
