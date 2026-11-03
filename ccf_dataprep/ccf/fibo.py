"""Verify a local name's absence from FIBO before this repo mints an `ex:` term.

Replaces an ad-hoc grep that failed silently in three ways, all measured
against this repo's own history:

1. **The ontology is git-ignored.** `.gitignore` ignores `sources/**`, so the
   9 MB `dev.fibo-quickstart.ttl` is never committed. A `grep` run against a
   missing file emits nothing on stdout, and "nothing" was read as "this term
   is absent from FIBO" — the check failed toward "safe to mint", which is
   exactly backwards for a check whose only job is to catch that mistake.
2. **The grep pattern was syntax-specific to the wrong syntax.**
   `rdf:about="&prefix;Local"` is an RDF/XML idiom. The EDM Council quickstart
   distribution is Turtle (`@prefix ...`, `a owl:Class ;`), where that pattern
   returns zero matches for every term in the file, real or invented — a
   pattern that can never say "present" is indistinguishable from one that
   correctly says "absent", which is why this failure mode went unnoticed.
3. **`prod` is not the whole ontology.** `prod.fibo-quickstart.ttl` carries
   Release-maturity content only and silently omits 40 Provisional modules —
   nine of which contain terms this repo already binds (known-issues §19.8).
   A shadow of a Provisional term reads as unshadowed against `prod`. Only
   `dev.fibo-quickstart.ttl` is a verified superset, so only `dev` can
   establish absence; `prod` can prove a term stable, never that it is
   missing.

The fix that matters is structural, not the specific pattern: this module
refuses to conflate "the term is absent" with "I could not check". Every path
that cannot honestly answer raises `OntologyUnusable` instead of returning a
boolean. Nothing in this module ever returns `True` (absent, safe to mint) as
a side effect of a broken file, a missing file, or a failed download.
"""

from __future__ import annotations

import re
from pathlib import Path

from ccf.config import REPO_ROOT
from ccf.fetch import get

#: Where the quickstart lives once fetched. Git-ignored (`sources/**`), so a
#: fresh checkout will not have it -- `_ensure_ontology()` is what makes that
#: survivable.
_ONTOLOGY = REPO_ROOT / "sources" / "fibo" / "dev.fibo-quickstart.ttl"

#: Tried in order. `latest` tracks the current master; the dated fallback
#: exists because EDM Council has moved `latest` before.
_QUICKSTART_URLS = (
    "https://spec.edmcouncil.org/fibo/ontology/master/latest/dev.fibo-quickstart.ttl",
    "https://spec.edmcouncil.org/fibo/ontology/master/2026Q1/dev.fibo-quickstart.ttl",
)

_USER_AGENT = (
    "ccf_dataprep/1.0 (+dcastilloaz@gmail.com) "
    "FIBO absence-check fetch -- see ccf/fibo.py"
)

#: A real download of this file is ~9 MB. Anything smaller is an error page,
#: a redirect stub, or a truncated stream -- never a usable ontology.
MIN_BYTES = 5_000_000

#: A term unambiguously present in every FIBO distribution. Every answer this
#: module gives is only as trustworthy as this control passing first.
_POSITIVE_CONTROL = "LegalEntity"

#: Text of a verified-usable ontology file, keyed by resolved path so a test
#: pointing at a stub does not collide with the real file's cached text.
#: Populated by `_load_verified_text()`; read once per process per path.
_CACHE: dict[str, str] = {}


class OntologyUnusable(RuntimeError):
    """Raised when this module cannot honestly answer a `fibo_absent` query.

    Absence and inability-to-check must never share a return value. Every
    condition that would otherwise force a guess -- a missing file, a file
    too small to be real, a failed download, or a positive control that does
    not fire -- raises this instead of returning `True`. Returning `True` on
    a broken check is the exact defect this module exists to remove.

    NOT raised for a prose mention of a term (an `rdfs:label` or
    `skos:definition` containing the word) that is not a declaration -- see
    `fibo_absent`'s docstring, Fix Round 1. That used to raise via a raw
    substring corroboration check; the check was wrong, not the ontology.
    """


def _ensure_ontology() -> Path:
    """Return the ontology path, downloading it on first use if absent.

    Idempotent: a file already on disk at or above `MIN_BYTES` is reused
    as-is. Otherwise each URL in `_QUICKSTART_URLS` is tried in turn; the
    first that yields a response of at least `MIN_BYTES` is written to
    `_ONTOLOGY`. If every URL fails or every response is too small, raises
    `OntologyUnusable` -- never returns a path to something unusable.
    """
    if _ONTOLOGY.exists() and _ONTOLOGY.stat().st_size >= MIN_BYTES:
        return _ONTOLOGY

    errors: list[str] = []
    for url in _QUICKSTART_URLS:
        try:
            resp = get(url, timeout=120, headers={"User-Agent": _USER_AGENT})
        except Exception as exc:  # noqa: BLE001 -- any failure, try next URL
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
            continue
        content = resp.content
        if len(content) < MIN_BYTES:
            errors.append(
                f"{url}: only {len(content):,} bytes (< MIN_BYTES={MIN_BYTES:,})"
            )
            continue
        _ONTOLOGY.parent.mkdir(parents=True, exist_ok=True)
        _ONTOLOGY.write_bytes(content)
        return _ONTOLOGY

    raise OntologyUnusable(
        "Could not obtain a usable FIBO dev quickstart from any known URL "
        f"(need >= {MIN_BYTES:,} bytes):\n  " + "\n  ".join(errors)
    )


def ontology_path() -> Path:
    """Path to a verified-present FIBO dev quickstart, fetching on first use."""
    return _ensure_ontology()


def _load_verified_text() -> str:
    """Read the ontology text, verified usable, cached per process.

    Verification is size (a truncated download or error page is too small to
    be the real file) followed by the positive control (a pattern that
    cannot find `LegalEntity` is not measuring FIBO, whatever else it finds).
    Both raise `OntologyUnusable` rather than letting a bad file answer any
    query. Reading and verifying happen once per path per process -- a 9 MB
    re-read per lookup would make callers like `partition.py`, which check
    dozens of terms, unusably slow.
    """
    path = _ensure_ontology()
    key = str(path)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    size = path.stat().st_size
    if size < MIN_BYTES:
        raise OntologyUnusable(
            f"{path} is {size:,} bytes, below MIN_BYTES={MIN_BYTES:,}. Too "
            "small to be the FIBO dev quickstart -- likely an error page, a "
            "stub, or a truncated download. Refusing to answer any absence "
            "query against it."
        )

    text = path.read_text(errors="replace")

    control_pattern = _qualified_name_pattern(_POSITIVE_CONTROL)
    if not control_pattern.search(text):
        raise OntologyUnusable(
            f"Positive control failed: pattern {control_pattern.pattern!r} "
            f"found no match for {_POSITIVE_CONTROL!r} in {path} "
            f"({size:,} bytes). {_POSITIVE_CONTROL} is unambiguously part of "
            "FIBO -- if this pattern cannot find it, either the pattern or "
            "the file is wrong, and no 'absent' answer from this module can "
            "be trusted until that is fixed."
        )

    _CACHE[key] = text
    return text


def _qualified_name_pattern(local_name: str) -> re.Pattern[str]:
    """Word-bounded Turtle qualified-name pattern for `local_name`.

    Matches `prefix:Local` or `#Local`, not a substring inside a longer name
    (`LegalEntity` must not match inside `LegalEntityIdentifier`) and not the
    RDF/XML `rdf:about="&prefix;Local"` idiom, which this Turtle file never
    contains and which returned zero for every term when tried here before.
    """
    return re.compile(rf"[:#]{re.escape(local_name)}\b")


def _full_iri_pattern(local_name: str) -> re.Pattern[str]:
    """Full-IRI declaration form for `local_name`: `<...#Local>` or `<.../Local>`.

    A term can be declared entirely by its full IRI with no prefixed form
    used nearby -- that is the genuine gap `_qualified_name_pattern` alone
    would miss. Angle brackets appear only in IRI position in Turtle, never
    inside an `rdfs:label` or `skos:definition` string, so this cannot match
    prose the way a raw substring search does.
    """
    return re.compile(rf"<[^>\s]*[/#]{re.escape(local_name)}>")


def fibo_absent(local_name: str) -> bool:
    """True iff `local_name` is absent from the FIBO dev quickstart.

    Presence is decided by DECLARATION FORM ONLY -- a term counts as present
    iff either the prefixed qualified-name pattern or the full-IRI pattern
    matches. Fix Round 1: the original design corroborated a "not found by
    the anchored pattern" result with a raw, unanchored substring search, and
    that was wrong. `Banker`, `Covenant`, `Deal` and `MeasurementPeriod` all
    have zero declarations in the ontology but were flagged UNUSABLE anyway,
    because the bare word shows up in ENGLISH PROSE -- inside an
    `rdfs:label`, `skos:definition`, `cmns-dsg:hasDescription` or
    `skos:editorialNote` string (e.g. "American Banker's Association (ABA)",
    "Contract Deal Date"). A raw substring search cannot tell a declaration
    from a sentence that happens to contain the word; the full-IRI pattern
    can, because prose is never wrapped in angle brackets. So there is no
    corroboration step left to disagree, and no prose mention can force an
    unjustified refusal to answer.

    Never returns a bool it cannot justify: an unusable ontology (missing,
    too small, failing its positive control) raises `OntologyUnusable`
    instead, here and in everything this function calls.
    """
    text = _load_verified_text()

    if _qualified_name_pattern(local_name).search(text):
        return False
    if _full_iri_pattern(local_name).search(text):
        return False

    return True
