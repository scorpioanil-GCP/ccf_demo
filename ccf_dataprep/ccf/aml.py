"""The name guard `aml-typology-match` runs before any synthetic party is
minted. CLAUDE.md rule 2 is a **hard legal constraint**: no named real
company and no real natural person may ever appear as a party in this
product. `RealNameIndex.blocks()` is how that constraint is enforced at
GENERATION time (Task 6), not caught later in review.

## What is indexed, and why it is wider than "real"

`RealNameIndex.build()` reads, in one pass each:

    legal_entity          legal_name + gleif_legal_name          public
    sanctions_entry       row count only (denominator; see below) public
    sanctions_name        name (primary/a.k.a./f.k.a./n.k.a.)     public
    person                name_as_filed + display_name,          public
                          NUMERIC keys only (see boundary below)
    person_name_variant   variant_name, joined to NUMERIC persons public
    psc_person            native_forename + native_surname        invented*
    peer_entity           entity_name                             public
    registry_company      legal_name + transliterated_names[]     public
                          + other_names[]
    institutional_holder  manager_name                            public

`sanctions_entry.primary_name` is not indexed separately: it is measured
(19,730 entries, 19,730 `name_kind = 'primary'` rows in `sanctions_name`) to
duplicate `sanctions_name` 1:1, so indexing both would only double-count:
`sanctions_entry` contributes its row count to `counts` as the denominator
proof that the join population did not silently collapse, and
`sanctions_name` carries the actual name.

**`psc_person` is a starred exception.** Its native forms are not real —
`generators/derive_psc_persons.py` invents every one, per CLAUDE.md rule 3
("no real name ... exists anywhere to load"). They are indexed anyway,
defensively: `psc_person.person_key` is a `PSC-####` key, the exact
namespace this brief tells Task 6 it MAY use for its own new AML parties. A
new invented AML party colliding by name with an *already-invented* Wave 13b
person would blur the boundary pseudonymization exists to draw, even though
no legal exposure follows from it directly. So this index protects two
different things with one mechanism: real identities (legal exposure, rule
2) and already-spoken-for invented identities (collision, rule 3's
downstream integrity) — never a numeric `person` key, which is always a
real Form 4 filer (see the boundary below).

## The two-population boundary in `person`

`person` is a two-writer table. Numeric keys (`0001*`, `0002*`, ...) are
real SEC filers — 817 `person_role` rows join `legal_entity`, i.e. these are
officers **of real companies**. `PSC-####` keys are Wave 13b's fully
invented cast (CLAUDE.md rule 3). Only the numeric population is indexed
here as "real names to block" — `is_psc_key()` is the boundary expression,
and the same boundary filters `person_name_variant` (via a join back to
`person`) so a PSC-cast variant never enters the index through that table
either.

## Blocking strategy — none. `blocks()` runs an EXACT scan.

This module went through two rounds of coordinator review, each finding a
DIFFERENT constructible bypass in a token/n-gram shortlisting index that
used to sit in front of the comparison:

  1. **Pure token reordering.** `"GROUP DEVELOPMENT AND TECHNOLOGY"` scores
     `similarity() == 1.0` against `sanctions_name` row SDN-8408's real,
     currently-sanctioned `"TECHNOLOGY AND DEVELOPMENT GROUP LTD"`, but
     every shared token (`GROUP`, `DEVELOPMENT`, `AND`, `TECHNOLOGY`) had a
     posting list common enough in this corpus to exceed the rarity cap on
     its own, so the shortlist logic dropped every one of them and
     `blocks()` returned `None`.
  2. **Token substitution, after (1) was patched with an exact-token-SET
     route.** `"TECHNOLOGY TRADING DEVELOPMENT GROUP"` (`similarity() ==
     0.9118`, confirmed, against the same SDN-8408 name) still returned
     `None`. Substituting one token for another mints accidental n-grams at
     the new word boundary (`OGYT`/`GYTR` at the `TECHNOLOGY|TRADING`
     junction) that happened to be RARER than the genuinely shared keys
     (the `DEVELOPMENT` token, the `LOPM` n-gram), so the rarest-first cap
     picked the wrong keys and crowded out the real match. The
     exact-token-set route from fix (1) does not help here either, because
     substitution changes the token set. (A second candidate cited in the
     same review round against SDN-25421,
     `"NATIONAL DEVELOPMENT NATIONAL INVESTMENT GROUP"`, was reported at
     "similarity 0.9195" -- recomputed here, that figure is
     `SequenceMatcher.quick_ratio()`, difflib's own fast UPPER-BOUND
     approximation, not `.ratio()`. This module's actual `similarity()` for
     that exact pair is `0.896551724137931`, below `BLOCK_THRESHOLD`, so
     `blocks()` returning `None` for that literal string is correct
     behaviour, not a residual bypass. The same substitution mechanism
     against the same real name IS independently confirmed with
     `"NATIONAL DEVELOPMENT TRADING INVESTMENT GROUP"`, `similarity() ==
     0.9302325581395349`.)

Each fix closed one hole and exposed a different one, and each was found
only because someone went looking for that specific shape — the signature
of a heuristic standing in for a question that is actually decidable at
this scale. So the shortlisting index was **deleted rather than patched a
third time**: `blocks()` now compares the candidate against every indexed
name, with no token or n-gram shortlist in front of it at all.

**The one thing still skipped is provably lossless, not a heuristic.** For
every pair, `blocks()` computes two cheap, EXACT quantities before ever
calling `SequenceMatcher.ratio()`:

  * the token-Jaccard score, which is not an approximation — it IS the
    token component of `similarity()`;
  * `2 * min(len_a, len_b) / (len_a + len_b)` — the textbook upper bound on
    what `SequenceMatcher.ratio()` could possibly return for two strings of
    those lengths (this is the same arithmetic behind
    `SequenceMatcher.real_quick_ratio()`).

Only when BOTH already fall below `BLOCK_THRESHOLD` is the (comparatively
expensive) `ratio()` call skipped for that one pair — and skipping it there
cannot exclude a true match, because neither quantity could reach the
threshold no matter what `ratio()` would have said. This has no equivalent
of either failure mode above: it does not depend on a token or n-gram being
shared, common, or rare — it is a length calculation and an exact set
computation, both already correct for every pair, not a guess about which
pairs are worth checking.

**Measured cost** (2026-08-25, this machine, 72,869 indexed records):
`RealNameIndex.build()` takes ~0.5s. 200 `.blocks()` calls against
Task-6-shaped candidates (two short invented words + a common corporate
suffix, matching the style Task 6 actually generates) take **~75 seconds
total, ~375ms/call average** -- an affordable one-time generation cost for
a ~200-party batch that runs once, not a per-request path. (One of those
200 random candidates, "Jgbn International", legitimately collided with
the real "GPB INTERNATIONAL SA" on the character-level measure -- exactly
the kind of coincidental near-miss this guard exists to catch; Task 6's
generator is expected to pick a different name when `blocks()` fires, the
same way it would for a real collision.) See `docs/known-issues.md` §26
for the full breakdown, including the three bypass rounds this module went
through before arriving at the exact-scan shape above.

## `BLOCK_THRESHOLD` — calibrated, not chosen by taste

CLAUDE.md rule 5 requires the estate to carry >= 1 real false-positive pair
(two different people who fuzzy-match strongly). The one already on record
(`validators/test_persons.py`, `generators/resolve_persons.py`) is real,
public, and lives in `person`: **"Davison James E"** (CIK 0001403411) and
**"Davison James E. Jr."** (CIK 0001403412) file Form 4s under the same
issuer but are two different people.

Measured with THIS module's own `similarity()` (2026-08-25):

    similarity("Davison James E", "Davison James E. Jr.") == 0.9090909090909091

`BLOCK_THRESHOLD = 0.90`, strictly below that measured score, so a
candidate AML party name that similar to a real person is refused. This is
deliberately tighter than `ccf.resolve`'s or `generators.persons`' own
thresholds, which exist to route a *known* pair to human review, not to
auto-block generation outright; a guard that runs unattended has to be the
more conservative of the two.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

#: Below the real Davison/Davison Jr. false-positive pair's measured score
#: (0.9090909090909091) — see the module docstring for the measurement and why
#: this pair, not a round number, sets the line.
BLOCK_THRESHOLD = 0.90

#: Element names that would let a reader infer a SAR exists for a specific
#: alert — a filed status, a SAR identifier, a narrative, a classification,
#: or a genuine/noise flag. `aml_alert.case_id` is in this set too, though
#: NOT because every case has a SAR: it does not. Wave 17's 24 engineered
#: cases split into a filed and an unfiled half (coordinator ruling, fix
#: rounds 2-3; see `generators/generate_sar_records.py`), so "this alert
#: has a case_id" is no longer equivalent to "a SAR exists for this alert's
#: case" -- that equivalence held only in the wave's original, since-fixed
#: 1:1 version, and this docstring said so until fix round 3 corrected it.
#: `case_id` stays forbidden anyway: it identifies WHICH of the 24
#: engineered cases an alert belongs to, and resolving which of those are
#: among the filing half requires exactly the departmental-store read
#: (`sar_classification`, joined by `alert_id`) `l1` must never make. A
#: rule narrowed to "only forbid the 12 case_ids that currently file" would
#: itself require `l1`'s own plan-builder to consult that table to know
#: which 12 to name -- the very reach into SQLite this floor exists to keep
#: `l1` away from. Blanket-forbidding the field, regardless of the current
#: split, is what avoids that. The `l1` projection plan must name none of
#: these.
#:
#: **This constant lives here, once.** It was duplicated verbatim into
#: `loaders/load_postgres_wave17.py` (the copy that ENFORCES it at write
#: time) and `validators/test_aml_typology.py` (the copy that CHECKS it),
#: kept in sync by nothing stronger than a docstring asking the next editor
#: to remember. In many jurisdictions disclosing that a SAR exists is itself
#: an offence, so a silent divergence between the enforcing copy and the
#: checking copy is the worst available version of that defect: the checker
#: would keep passing against a set the loader no longer polices. One
#: definition, imported by both.
SAR_REVEALING_ELEMENT_NAMES = frozenset({
    "sar_filing_history", "sar_narrative", "sar_id", "sar_status",
    "sar_classification", "filing_status", "sar_disposition", "case_id",
    "matched_case", "is_genuine", "genuine_case_flag", "case_linkage",
})

_PSC_KEY_RE = re.compile(r"^PSC-\d+$")

_PUNCT_RE = re.compile(r"[.,'’`\"()\[\]{}\-_/\\&]+")
_WS_RE = re.compile(r"\s+")

#: Legal-form suffixes stripped as whole tokens only — never as substrings,
#: so e.g. `CO` does not eat the `CO` inside `COMPANY` handling; each is
#: matched post-tokenization against an exact token.
_CORP_SUFFIXES = frozenset({
    "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY",
    "LTD", "LIMITED", "LLC", "LLP", "LP", "PLC", "GMBH", "AG", "SA", "SAS",
    "SARL", "SPA", "BV", "NV", "OY", "OYJ", "AB", "AS", "APS", "KFT",
    "ZRT", "PTE", "PVT", "PC", "LC", "LTDA", "SRL", "SDN", "BHD", "KG",
    "KGAA",
})


def is_psc_key(k: str) -> bool:
    """True only for `PSC-` followed by one or more digits.

    The code expression of the two-population boundary in `person`:
    `PSC-####` is Wave 13b's invented cast (CLAUDE.md rule 3); every other
    `person_key` shape is a real SEC filer. Wave 17 may mint new `PSC-*`
    keys and must never touch a numeric one.
    """
    return bool(k) and bool(_PSC_KEY_RE.match(k))


def normalize_name(s: str) -> str:
    """Casefold, strip punctuation and corporate suffixes, collapse
    whitespace.

    Returns `""` for input with no alphanumeric content, so a caller can
    tell "nothing to compare" from "compared and differed". Diacritics are
    folded (`Müller` -> `MULLER`) the same way `ccf.names.normalize` does,
    for the same reason: real screening systems fold, and folding is one of
    the mechanisms that make near-miss collisions visible rather than
    hiding them behind an accent.

    `sanctions_name` already carries its own `name_norm` column (upper-cased,
    punctuation stripped, no corporate-suffix or diacritic handling). This
    function is applied uniformly to BOTH sides of every comparison this
    module makes -- indexed names and candidates alike -- rather than
    comparing a stored `name_norm` against a freshly computed one. Spot
    checks agree between the two on the rows sampled, but they are two
    separate pipelines that could silently drift; running one function over
    everything removes that risk rather than trusting it stays in sync.
    """
    if not s:
        return ""
    decomposed = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    folded = stripped.upper()
    folded = _PUNCT_RE.sub(" ", folded)
    tokens = [t for t in _WS_RE.split(folded) if t]
    kept = [t for t in tokens if t not in _CORP_SUFFIXES]
    # An input that is ENTIRELY corporate-suffix tokens (or none) keeps its
    # tokens rather than collapsing to "" -- dropping everything would make
    # two different bare-suffix strings compare equal.
    return " ".join(kept or tokens)


def _pair_score(na: str, nb: str, ta: frozenset[str], tb: frozenset[str]) -> float:
    """Shared scoring core for `similarity()` and `RealNameIndex.blocks()`,
    so the two can never quietly drift apart -- the exact risk this
    module's own `normalize_name` docstring names for `sanctions_name`'s
    `name_norm` column, applied to itself. Callers pass already-normalized
    strings and their already-split token sets so this does no redundant
    work on either side.
    """
    seq = SequenceMatcher(None, na, nb).ratio()
    tok = len(ta & tb) / len(ta | tb) if (ta and tb) else 0.0
    return max(seq, tok)


def similarity(a: str, b: str) -> float:
    """0.0-1.0. Max of character-level and token-level overlap.

    Neither measure subsumes the other: character-level (`SequenceMatcher`)
    catches spelling and transliteration drift and short substring
    near-misses ("Pregis" / "Regis"); token-level (order-insensitive
    Jaccard) catches pure reordering ("SMITH, ROBERT" / "ROBERT SMITH").
    Taking the max means either one alone is enough to flag a collision.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    ta = frozenset(t for t in na.split(" ") if t)
    tb = frozenset(t for t in nb.split(" ") if t)
    return _pair_score(na, nb, ta, tb)


@dataclass
class RealNameIndex:
    """Every name this estate already carries, scanned EXACTLY on every
    `.blocks()` call -- see the module docstring's "Blocking strategy"
    section for why there is no shortlisting index in front of this, and
    what boundary keeps invented Wave 17 identities from ever entering it.
    """

    counts: dict[str, int] = field(default_factory=dict)
    #: (raw name, normalized form, normalized token set) per indexed name.
    _records: list[tuple[str, str, frozenset[str]]] = field(default_factory=list)

    @classmethod
    def build(cls) -> "RealNameIndex":
        """Read every guarded source, in one pass each. Pure reads only:
        no Fluree, no Mongo, no writes anywhere -- see the module
        docstring for the exact source list.
        """
        from ccf.config import pg_connect

        idx = cls()
        conn = pg_connect()
        try:
            with conn.cursor() as cur:
                idx._load_legal_entity(cur)
                idx._load_sanctions(cur)
                idx._load_person_and_variants(cur)
                idx._load_psc_person(cur)
                idx._load_peer_entity(cur)
                idx._load_registry_company(cur)
                idx._load_institutional_holder(cur)
        finally:
            conn.close()
        return idx

    @classmethod
    def from_names(cls, names) -> "RealNameIndex":
        """Build an index from an explicit list of names, with no database
        access -- for tests that need a small, hand-chosen index rather than
        the full ~72,900-record scan `build()` performs. Reuses `_add()`, so
        a name built this way is normalized identically to one read from
        Postgres.
        """
        idx = cls()
        for name in names:
            idx._add(name)
        return idx

    # -- per-source loaders, one query each -------------------------------

    def _add(self, raw) -> None:
        if raw is None:
            return
        raw = str(raw).strip()
        if not raw:
            return
        norm = normalize_name(raw)
        if not norm:
            return
        tokens = frozenset(t for t in norm.split(" ") if t)
        self._records.append((raw, norm, tokens))

    def _load_legal_entity(self, cur) -> None:
        cur.execute("SELECT legal_name, gleif_legal_name FROM legal_entity")
        rows = cur.fetchall()
        self.counts["legal_entity"] = len(rows)
        for legal_name, gleif_legal_name in rows:
            self._add(legal_name)
            self._add(gleif_legal_name)

    def _load_sanctions(self, cur) -> None:
        # sanctions_entry.primary_name duplicates sanctions_name's
        # name_kind='primary' rows 1:1 (measured: 19,730 == 19,730) -- read
        # sanctions_entry only for its row count, the denominator proof that
        # the join population is real, not for names (see module docstring).
        cur.execute("SELECT count(*) FROM sanctions_entry")
        self.counts["sanctions_entry"] = cur.fetchone()[0]

        cur.execute("SELECT name FROM sanctions_name")
        rows = cur.fetchall()
        self.counts["sanctions_name"] = len(rows)
        for (name,) in rows:
            self._add(name)

    def _load_person_and_variants(self, cur) -> None:
        cur.execute("SELECT person_key, name_as_filed, display_name FROM person")
        rows = cur.fetchall()
        self.counts["person"] = len(rows)
        for person_key, name_as_filed, display_name in rows:
            if is_psc_key(person_key):
                continue  # Wave 13b invented cast -- never a real person
            self._add(name_as_filed)
            self._add(display_name)

        cur.execute(
            "SELECT p.person_key, v.variant_name FROM person_name_variant v "
            "JOIN person p ON p.person_key = v.person_key"
        )
        rows = cur.fetchall()
        self.counts["person_name_variant"] = len(rows)
        for person_key, variant_name in rows:
            if is_psc_key(person_key):
                continue  # variant of an invented person, not a real one
            self._add(variant_name)

    def _load_psc_person(self, cur) -> None:
        # Invented (CLAUDE.md rule 3), indexed defensively -- see the
        # module docstring's starred exception.
        cur.execute("SELECT native_forename, native_surname FROM psc_person")
        rows = cur.fetchall()
        self.counts["psc_person"] = len(rows)
        for forename, surname in rows:
            self._add(forename)
            self._add(surname)
            if forename and surname:
                self._add(f"{forename} {surname}")

    def _load_peer_entity(self, cur) -> None:
        cur.execute("SELECT entity_name FROM peer_entity")
        rows = cur.fetchall()
        self.counts["peer_entity"] = len(rows)
        for (entity_name,) in rows:
            self._add(entity_name)

    def _load_registry_company(self, cur) -> None:
        cur.execute(
            "SELECT legal_name, transliterated_names, other_names "
            "FROM registry_company"
        )
        rows = cur.fetchall()
        self.counts["registry_company"] = len(rows)
        for legal_name, transliterated_names, other_names in rows:
            self._add(legal_name)
            for n in (transliterated_names or []):
                self._add(n)
            for n in (other_names or []):
                self._add(n)

    def _load_institutional_holder(self, cur) -> None:
        cur.execute("SELECT manager_name FROM institutional_holder")
        rows = cur.fetchall()
        self.counts["institutional_holder"] = len(rows)
        for (manager_name,) in rows:
            self._add(manager_name)

    # -- the exact scan -----------------------------------------------------

    def blocks(self, candidate: str) -> str | None:
        """The colliding indexed name, or `None`.

        An EXACT scan against every indexed name -- see the module
        docstring's "Blocking strategy" section for why there is no
        shortlisting index in front of this any more. The only pair-level
        skip is provably lossless: when a pair's exact token-Jaccard score
        AND its length-based upper bound on `SequenceMatcher.ratio()`
        (`2 * min(len_a, len_b) / (len_a + len_b)`, the same arithmetic as
        `SequenceMatcher.real_quick_ratio()`) are BOTH already below
        `BLOCK_THRESHOLD`, the actual `ratio()` call is skipped for that
        pair -- it cannot reach the threshold regardless of what `ratio()`
        would return, so nothing is lost by not computing it.

        Deterministic regardless of database iteration order: among every
        candidate scoring >= `BLOCK_THRESHOLD`, the highest score wins,
        ties broken by the name string itself -- never by which row
        happened to be read or inserted first.
        """
        norm = normalize_name(candidate)
        if not norm:
            return None
        cand_tokens = frozenset(t for t in norm.split(" ") if t)
        len_c = len(norm)

        best_name: str | None = None
        best_score = -1.0
        for raw, norm_r, tokens_r in self._records:
            tok = (len(cand_tokens & tokens_r) / len(cand_tokens | tokens_r)
                   if (cand_tokens and tokens_r) else 0.0)
            len_r = len(norm_r)
            total = len_c + len_r
            seq_upper = (2.0 * min(len_c, len_r) / total) if total else 0.0
            if tok < BLOCK_THRESHOLD and seq_upper < BLOCK_THRESHOLD:
                # Neither component can reach BLOCK_THRESHOLD for this pair:
                # `tok` already IS the exact token score, and `seq_upper` is
                # a strict, correct upper bound on what SequenceMatcher
                # could return for these two lengths. Skipping ratio() here
                # cannot exclude a pair that would have scored >= threshold.
                continue
            score = _pair_score(norm, norm_r, cand_tokens, tokens_r)
            if score > best_score or (score == best_score and
                                       (best_name is None or raw < best_name)):
                best_score = score
                best_name = raw

        if best_score >= BLOCK_THRESHOLD:
            return best_name
        return None
