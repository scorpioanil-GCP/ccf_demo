"""The two source legs for collateral coverage, and nothing else.

[ADAPT] everything. [MECHANISM] nothing — **this module imports no `ccf` at
all**. It opens two systems of record, walks one, joins the other, and hands
back what it found.

Boundaries are ruled (`D-IMPL-315`): vocabulary, source access and admission.
No binder, no gates, no replay, no serve.

## What makes this product a graph rather than a column

`ccf_v2.collateral_pledge` carries `facility_id, asset_id, provenance, basis`
and **no priority column**. Priority lives only in the graph, reified as
`ex:CollateralPledge` nodes carrying `lienPosition` — because priority belongs
to the *(facility, asset) pair* and hanging it on either endpoint would drop
half of each fact. A reader who takes the Postgres pledge table at face value
sees "this asset secures two facilities" and cannot tell that one holds a first
lien and the other a second.

**The reverse walk is what turns a column into a graph.** Having found the
anchor's assets, this module walks each asset's `securedBy` edges BACK to every
other facility sharing it. Skipping that step is exactly how shared collateral
goes unnoticed, and the answer looks fine without it.

## Three traps in this estate, each measured rather than inherited

1. **Dates are untyped ISO-8601 strings and must be compared as strings.**
   This Fluree build corrupts ``^^xsd:date`` literals on write — 65 of 65
   filing dates stored wrong, 53 distinct deltas, so it is arbitrary rather
   than an offset. ISO-8601 sorts lexicographically, so string comparison is
   correct; casting is not.
2. **Never ``COUNT(*)`` over a multi-pattern WHERE.** It under-reports on this
   build — 17 where the query returns 65 rows. Everything here counts
   client-side.
3. **A join across secured parties and amendments fans out.** One filing names
   two secured parties and another carries three amendment rows, so the
   terminated-lien join returns 16 rows for 13 filings. Count filings, never
   rows.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

HERE = Path(__file__).parent

READ_TIMEOUT_SECONDS = 120


def _document(path: Path) -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed


def vocabulary() -> Mapping[str, Any]:
    """The sources' own names, read from the artifact rather than written here."""
    declaration: Mapping[str, Any] = _document(
        HERE / "artifacts" / "source-vocabulary.yaml"
    )["declaration"]
    return declaration


def _setting(source: str, name: str) -> str:
    """One connection value from the environment, or the declared remedy."""
    declared = _document(HERE / "backends.yaml")["declaration"]["sources"]
    setting = declared[source]["settings"][name]
    value = os.environ.get(setting["from_env"])
    if not value:
        raise RuntimeError(f"{setting['from_env']} is unset. {setting['remedy'].strip()}")
    return value


def _declared(source: str, name: str) -> Any:
    """A declared (non-environment) setting, such as the walk ceiling."""
    return _document(HERE / "backends.yaml")["declaration"]["sources"][source]["settings"][name]


# ---------------------------------------------------------------------------
# What the two legs found.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pledge:
    """One (facility, asset) pair and the priority that belongs to the pair."""

    facility_id: str
    asset_id: str
    #: `PrimaryLienPosition` / `SubordinateLienPosition`, or None where the
    #: graph carries an edge the reified pledge does not cover. Absent is
    #: reported, never defaulted to senior — assuming seniority is the error
    #: this product exists to surface.
    lien_position: str | None


@dataclass(frozen=True)
class Asset:
    asset_id: str
    category: str | None
    description: str | None
    valuation: Decimal | None
    valuation_date: str | None
    valuation_age_days: int | None
    haircut: Decimal | None
    pledgor: str | None
    provenance: str | None


@dataclass(frozen=True)
class Deposit:
    account_id: str
    holder: str | None
    currency: str | None
    balance: Decimal | None
    jurisdiction: str | None
    setoff_contractual: bool
    setoff_enforceable: bool


@dataclass(frozen=True)
class UccFiling:
    """One filed UCC-1, and the amendment history that dates its life."""

    filing_number: str
    debtor_of_record: str
    filed_on: str | None
    lapses_on: str | None
    filing_status: str | None
    secured_parties: tuple[str, ...]
    #: (action, filed_on) per amendment. An amendment's action is NOT scalar —
    #: two in this register carry two actions each, so this is a list of pairs
    #: rather than a mapping.
    amendments: tuple[tuple[str, str | None], ...]

    @property
    def terminated_on(self) -> str | None:
        """The earliest Termination date, as a string. None if never released."""
        dates = sorted(d for a, d in self.amendments if a == "Termination" and d)
        return dates[0] if dates else None


@dataclass(frozen=True)
class Coverage:
    """Everything the two legs found, before any fabric call."""

    facility_id: str
    borrower_lei: str | None
    borrower_name: str | None
    commitment: Decimal | None
    pledges: tuple[Pledge, ...]
    assets: Mapping[str, Asset]
    #: Facilities OTHER than the anchor that share one of its assets, found by
    #: the reverse walk. The thing a column cannot tell you.
    sharing: Mapping[str, tuple[Pledge, ...]]
    deposits: tuple[Deposit, ...]
    filings: tuple[UccFiling, ...]
    haircuts: Mapping[str, Decimal]
    enforceable_jurisdictions: frozenset[str]
    ledger_watermark: str
    #: Filed debtor names that resolve to no LEI. Reported, not hidden.
    unresolved_debtors: tuple[str, ...] = field(default_factory=tuple)


class _GraphLeg:
    """A read-only SPARQL client. `FROM <ledger>` precedes `WHERE`, always."""

    def __init__(self, *, url: str, ledger: str, client: httpx.Client) -> None:
        self._url, self._ledger, self._client = url.rstrip("/"), ledger, client

    @property
    def ledger(self) -> str:
        return self._ledger

    def query(self, body: str) -> list[Mapping[str, Any]]:
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body.encode("utf-8"),
        )
        response.raise_for_status()
        rows: list[Mapping[str, Any]] = response.json()["results"]["bindings"]
        return rows

    def watermark(self) -> str:
        """The ledger's `t`, matched on name AND branch, or `unreported`.

        Never a number this code invented: a fabricated watermark would put a
        specific, checkable, false claim about the source into the payload.
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return "unreported"
        # `name:branch`, or a bare name whose branch is `main`. Fluree keys the
        # two separately, and a bare `fibo-v2` partitions to an EMPTY branch —
        # which matches no listing and silently reports `unreported` against a
        # ledger that is right there.
        name, sep, branch = self._ledger.partition(":")
        if not sep:
            branch = "main"
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch") == branch:
                return str(entry["t"])
        return "unreported"


def _values(terms: Sequence[str]) -> str:
    return " ".join(f"<{term}>" for term in terms)


def _local(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


# ---------------------------------------------------------------------------
# The four reads. §D steps 1-4; step 5 is Π and step 6 is the SDK's.
# ---------------------------------------------------------------------------


def _resolve_facility(cur: Any, schema: str, vocab: Mapping[str, Any],
                      facility_id: str) -> tuple[str | None, str | None, Decimal | None]:
    """Step 1 — the anchor. An unknown facility raises rather than serving empty."""
    table = vocab["attribute_leg"]["facility_table"]
    cur.execute(
        f'SELECT f.borrower_lei, e.legal_name, f.commitment_amount '
        f'FROM "{schema}".{table} f '
        f'LEFT JOIN "{schema}".legal_entity e ON e.lei = f.borrower_lei '
        f"WHERE f.facility_id = %s",
        (facility_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise LookupError(
            f"facility {facility_id!r} resolves to no row in {schema}.{table};"
            " an unknown facility is a claim about the request, not about the world"
        )
    return row[0], row[1], row[2]


def _policy(cur: Any, schema: str, vocab: Mapping[str, Any]) -> tuple[
        dict[str, Decimal], frozenset[str]]:
    """Step 2 — the haircut schedule and the enforceability register.

    Loaded BEFORE anything reads graph state, which is the ordering §D fixes:
    on a graph the policy envelope shapes what is walked rather than filtering
    what came back.
    """
    leg = vocab["attribute_leg"]
    cur.execute(f'SELECT asset_class, haircut FROM "{schema}".{leg["haircut_table"]}')
    haircuts = {str(a): Decimal(str(h)) for a, h in cur.fetchall()}
    cur.execute(
        f'SELECT jurisdiction FROM "{schema}".{leg["enforceability_table"]}'
        " WHERE enforceable"
    )
    return haircuts, frozenset(str(j) for (j,) in cur.fetchall())


def _walk_collateral(leg: _GraphLeg, vocab: Mapping[str, Any],
                     facility_id: str) -> tuple[list[Pledge], dict[str, list[Pledge]]]:
    """Step 3a — the anchor's assets, then the REVERSE walk to shared facilities.

    Two hops and the second is the point. Hop one answers *what secures this
    facility*; hop two answers *who else has a claim on it*, which is the
    question a collateral column cannot be asked at all.

    Priority comes from the reified pledge, joined on the (facility, asset)
    pair. A pair the pledge nodes do not cover reports `lien_position=None`
    rather than defaulting to senior.
    """
    g = vocab["graph_leg"]
    anchor = f"http://example.org/fibo/{facility_id}"

    assets = [
        _local(b["o"]["value"])
        for b in leg.query(
            f'SELECT ?o FROM <{leg.ledger}> WHERE {{ <{anchor}> <{g["secured_by"]}> ?o }}'
        )
    ]
    if not assets:
        return [], {}

    # The reverse walk, batched over every asset at once.
    asset_uris = [f"http://example.org/fibo/{a}" for a in assets]
    reverse = leg.query(
        f'SELECT ?f ?a FROM <{leg.ledger}> WHERE {{'
        f' VALUES ?a {{ {_values(asset_uris)} }} ?f <{g["secured_by"]}> ?a }}'
    )

    # Every reified pledge touching these assets, for the priority half.
    positions: dict[tuple[str, str], str] = {}
    for b in leg.query(
        f'SELECT ?f ?a ?pos FROM <{leg.ledger}> WHERE {{'
        f' VALUES ?a {{ {_values(asset_uris)} }}'
        f' ?p <{g["pledged_asset"]}> ?a ;'
        f'    <{g["pledged_facility"]}> ?f ;'
        f'    <{g["lien_position"]}> ?pos }}'
    ):
        positions[(_local(b["f"]["value"]), _local(b["a"]["value"]))] = _local(
            b["pos"]["value"]
        )

    mine: list[Pledge] = []
    sharing: dict[str, list[Pledge]] = {}
    for b in reverse:
        other, asset = _local(b["f"]["value"]), _local(b["a"]["value"])
        pledge = Pledge(facility_id=other, asset_id=asset,
                        lien_position=positions.get((other, asset)))
        if other == facility_id:
            mine.append(pledge)
        else:
            sharing.setdefault(other, []).append(pledge)
    return mine, sharing


def _walk_setoff(leg: _GraphLeg, vocab: Mapping[str, Any],
                 borrower_name: str | None) -> list[str]:
    """Step 3b — deposits the bank may apply, reached from the BORROWER.

    Set-off attaches to the party rather than to the facility, which is why it
    lives in a different system and never enters a facility-shaped frame.
    """
    if not borrower_name:
        return []
    g = vocab["graph_leg"]
    holder = "".join(ch for ch in borrower_name.title() if ch.isalnum())
    uri = f"http://example.org/fibo/{holder}"
    accounts = {
        _local(b["s"]["value"])
        for predicate in (g["set_off_against"], g["netted_under"])
        for b in leg.query(
            f'SELECT ?s FROM <{leg.ledger}> WHERE {{ ?s <{predicate}> <{uri}> }}'
        )
    }
    return sorted(accounts)


def _walk_ucc(leg: _GraphLeg, vocab: Mapping[str, Any],
              debtor_names: Sequence[str]) -> list[UccFiling]:
    """Step 3c — the public register, and the amendment history that dates it.

    Every date here is an untyped ISO-8601 string and is kept as one. An
    amendment's action is a LIST rather than a scalar: two amendments in this
    register carry two actions each, and modelling one would silently drop half
    of a secured-party substitution.
    """
    if not debtor_names:
        return []
    g = vocab["graph_leg"]
    quoted = " ".join(f'"{n}"' for n in debtor_names)

    core: dict[str, dict[str, Any]] = {}
    for b in leg.query(
        f'SELECT ?f ?num ?debtor ?filed ?lapses ?status FROM <{leg.ledger}> WHERE {{'
        f' VALUES ?debtor {{ {quoted} }}'
        f' ?f <{g["debtor_of_record"]}> ?debtor ;'
        f'    <{g["filing_number"]}> ?num ;'
        f'    <{g["filed_on"]}> ?filed .'
        f' OPTIONAL {{ ?f <{g["lapses_on"]}> ?lapses }}'
        f' OPTIONAL {{ ?f <{g["filing_status"]}> ?status }} }}'
    ):
        core[b["f"]["value"]] = {
            "number": b["num"]["value"], "debtor": b["debtor"]["value"],
            "filed": b["filed"]["value"],
            "lapses": b.get("lapses", {}).get("value"),
            "status": b.get("status", {}).get("value"),
        }
    if not core:
        return []

    uris = list(core)
    parties: dict[str, set[str]] = {}
    for b in leg.query(
        f'SELECT ?f ?label FROM <{leg.ledger}> WHERE {{'
        f' VALUES ?f {{ {_values(uris)} }}'
        f' ?f <{g["secured_party_of"]}> ?sp . ?sp <{g["label"]}> ?label }}'
    ):
        parties.setdefault(b["f"]["value"], set()).add(b["label"]["value"])

    actions: dict[str, list[tuple[str, str | None]]] = {}
    for b in leg.query(
        f'SELECT ?f ?act ?when FROM <{leg.ledger}> WHERE {{'
        f' VALUES ?f {{ {_values(uris)} }}'
        f' ?f <{g["amended_by"]}> ?a . ?a <{g["amendment_action"]}> ?act .'
        f' OPTIONAL {{ ?a <{g["filed_on"]}> ?when }} }}'
    ):
        actions.setdefault(b["f"]["value"], []).append(
            (b["act"]["value"], b.get("when", {}).get("value"))
        )

    return [
        UccFiling(
            filing_number=v["number"], debtor_of_record=v["debtor"],
            filed_on=v["filed"], lapses_on=v["lapses"], filing_status=v["status"],
            secured_parties=tuple(sorted(parties.get(uri, ()))),
            amendments=tuple(sorted(actions.get(uri, ()))),
        )
        for uri, v in sorted(core.items(), key=lambda kv: kv[1]["number"])
    ]


def _enrich(cur: Any, schema: str, vocab: Mapping[str, Any], *,
            asset_ids: Sequence[str], account_ids: Sequence[str]) -> tuple[
                dict[str, Asset], list[Deposit]]:
    """Step 4 — ONE batched query per set. Never one per node."""
    leg = vocab["attribute_leg"]
    assets: dict[str, Asset] = {}
    if asset_ids:
        cur.execute(
            f'SELECT asset_id, category, description, valuation, valuation_date,'
            f' valuation_age_days, haircut, pledgor_lei, provenance_valuation'
            f' FROM "{schema}".{leg["asset_table"]} WHERE asset_id = ANY(%s)',
            (list(asset_ids),),
        )
        for r in cur.fetchall():
            assets[r[0]] = Asset(
                asset_id=r[0], category=r[1], description=r[2],
                valuation=r[3], valuation_date=r[4].isoformat() if r[4] else None,
                valuation_age_days=r[5], haircut=r[6], pledgor=r[7], provenance=r[8],
            )
    deposits: list[Deposit] = []
    if account_ids:
        cur.execute(
            f'SELECT account_id, holder_lei, currency, balance, jurisdiction,'
            f' setoff_contractual, setoff_enforceable'
            f' FROM "{schema}".{leg["deposit_table"]} WHERE account_id = ANY(%s)',
            (list(account_ids),),
        )
        deposits = [
            Deposit(account_id=r[0], holder=r[1], currency=r[2], balance=r[3],
                    jurisdiction=r[4], setoff_contractual=bool(r[5]),
                    setoff_enforceable=bool(r[6]))
            for r in cur.fetchall()
        ]
    return assets, deposits


def _debtor_names(cur: Any, schema: str, vocab: Mapping[str, Any],
                  borrower_lei: str | None) -> tuple[list[str], list[str]]:
    """Which filed debtor names this borrower owns, and which resolve to nobody.

    The register keys on legal NAME and the fabric keys on LEI. The crosswalk's
    match is a claim carrying a score, never asserted as filed fact — so the
    unmatched names are RETURNED rather than dropped. Measured in this estate:
    1 of 16 filed names resolves, and several of the other 15 are visibly
    subsidiaries of the one that does.
    """
    table = vocab["attribute_leg"]["crosswalk_table"]
    cur.execute(f'SELECT filed_debtor_name, lei, match_band FROM "{schema}".{table}')
    rows = cur.fetchall()
    mine = [n for n, lei, _ in rows if lei and lei == borrower_lei]
    unresolved = [n for n, lei, _ in rows if not lei]
    return mine, unresolved


def acquire(*, facility_id: str, include_setoff: bool) -> Coverage:
    """Open both stores and read what secures this facility.

    Args:
        facility_id: The anchor, as the caller named it.
        include_setoff: The EFFECTIVE value — already folded through the class
            default and any policy bound by `resolve_effective_request`. This
            function applies no default of its own; a second default would be a
            second authority for one value.
    """
    vocab = vocabulary()
    schema = _setting("collateral_attributes", "schema")

    with psycopg.connect(_setting("collateral_attributes", "dsn")) as db:
        with db.cursor() as cur:
            borrower_lei, borrower_name, commitment = _resolve_facility(
                cur, schema, vocab, facility_id)
            haircuts, enforceable = _policy(cur, schema, vocab)
            filed_names, unresolved = _debtor_names(cur, schema, vocab, borrower_lei)

    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        leg = _GraphLeg(url=_setting("collateral_graph", "url"),
                        ledger=_setting("collateral_graph", "ledger"), client=client)
        pledges, sharing = _walk_collateral(leg, vocab, facility_id)
        accounts = _walk_setoff(leg, vocab, borrower_name) if include_setoff else []
        filings = _walk_ucc(leg, vocab, filed_names)
        watermark = leg.watermark()

    asset_ids = sorted({p.asset_id for p in pledges}
                       | {p.asset_id for ps in sharing.values() for p in ps})
    with psycopg.connect(_setting("collateral_attributes", "dsn")) as db:
        with db.cursor() as cur:
            assets, deposits = _enrich(cur, schema, vocab,
                                       asset_ids=asset_ids, account_ids=accounts)

    return Coverage(
        facility_id=facility_id, borrower_lei=borrower_lei,
        borrower_name=borrower_name, commitment=commitment,
        pledges=tuple(pledges), assets=assets,
        sharing={k: tuple(v) for k, v in sorted(sharing.items())},
        deposits=tuple(deposits), filings=tuple(filings),
        haircuts=haircuts, enforceable_jurisdictions=enforceable,
        ledger_watermark=watermark, unresolved_debtors=tuple(sorted(unresolved)),
    )
