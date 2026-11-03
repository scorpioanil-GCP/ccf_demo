"""Parser for monthly servicer distribution reports (EX-99.1 to Form 10-D).

## Two formats, dispatched — never guessed

Santander numbers its line items (`{79} Delinquency Percentage ... 10.79 %`);
Toyota uses pure label/value with no numeric markers at all. `detect_format`
decides by counting `{n}` markers, and an unrecognized layout RAISES rather
than returning a dict of zeros. A third issuer's format must stop the load,
because a servicer report that silently parses to zeros would sail through
every downstream check while destroying the reconciliation it exists to
provide.

## This parser produces evidence, not answers

`trigger_occurred` is captured because the servicer publishes it, and because
a disagreement between it and our own loan-level recomputation is a finding
worth surfacing. It must NEVER be the basis for deciding whether a trigger
occurred -- `validators/abs_surveillance.py` recomputes from loan level and
uses this field only as a cross-check. Reading a stored flag that states the
answer is how three of Wave 13b's four defects survived in checks already
reporting PASS.

## None is not zero

Toyota publishes no overcollateralization PERCENTAGE and no 60-day delinquent
BALANCE. Those come back None. Substituting a computed value and returning it
beside genuinely-filed figures would present our arithmetic as the servicer's.

## Bucket boundaries differ by issuer

Santander reports 31-60 / 61-90 / 91-120 / 121+; Toyota reports
30-59 / 60-89 / 90-119 / 120+. Buckets are therefore returned keyed by the
issuer's own boundary labels, so a caller cannot add two non-comparable
buckets together and call the result a total. Cross-issuer comparison must use
the published 60-day percentage or a loan-level recomputation.
"""

from __future__ import annotations

import html
import re
from decimal import Decimal, InvalidOperation

__all__ = [
    "UnparseableServicerReport",
    "detect_format",
    "parse_servicer_report",
]


class UnparseableServicerReport(ValueError):
    """A servicer report could not be parsed under either known format.

    Raised rather than defaulted -- see the module docstring's first section.
    """


#: Every key both format branches must produce. `parse_servicer_report`
#: checks the returned dict against this set before handing it back.
_REQUIRED_KEYS = (
    "pool_balance",
    "note_balance",
    "oc_amount",
    "oc_percent",
    "oc_target",
    "delinquency_percent",
    "delinquency_trigger",
    "trigger_occurred",
    "sixty_day_delinquent_balance",
    "cumulative_net_loss_percent",
    "receivable_count",
    "delinquency_buckets",
    "source_format",
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_NUMBERED_MARKER_RE = re.compile(r"\{\d+\}")
_NIL_RE = re.compile(r"^[—–\-]+$")
_TOKEN_NUMERIC_RE = re.compile(r"^[—–\-]+$|^\(?\$?-?[\d,]+\.?\d*\)?%?$")


def _strip_html(raw_html: str) -> str:
    """Tags out, entities decoded, whitespace collapsed.

    `html.unescape` handles both the numeric entities (`&#8212;`, `&#8194;`)
    and named ones (`&nbsp;`) that these filings mix freely -- hand-rolling a
    substitution table for each one seen so far is exactly the kind of
    pattern that breaks on the next filing that uses one we didn't list.
    """
    text = _TAG_RE.sub(" ", raw_html)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def detect_format(text: str) -> str:
    """`"numbered"` if `{n}` item markers are present, else `"labelled"`.

    Santander wraps every line item in a repeated `{n}` marker; Toyota's
    layout contains none. A handful of stray braces (there are none in
    practice, but defensively) would not cross the threshold -- a genuine
    numbered report carries well over a hundred marker occurrences.
    """
    if len(_NUMBERED_MARKER_RE.findall(text)) >= 5:
        return "numbered"
    return "labelled"


def _to_decimal(raw: str) -> Decimal:
    """Parse one filed value. Em dash, en dash, and hyphen all mean zero."""
    raw = raw.strip()
    if _NIL_RE.fullmatch(raw):
        return Decimal("0")
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    raw = raw.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise UnparseableServicerReport(f"not a decimal value: {raw!r}") from exc
    return -value if negative else value


# --------------------------------------------------------------------------
# Numbered format (Santander / SDART)
# --------------------------------------------------------------------------


def _item_value_zone(text: str, n: int) -> str:
    """Text between an item's second `{n}` marker and the next `{...}`.

    The layout repeats the item number: `{n} LABEL {n} VALUE`. Stopping at
    the next brace of ANY kind (not just the next `{digit+}`) matters
    because some items (e.g. `{63}`) are followed by roman-numeral
    sub-markers (`{i}`, `{ii}`) before the next real item -- stopping only
    at `{\\d+}` would swallow those sub-items' text into `{63}`'s value.
    """
    pattern = re.compile(r"\{" + str(n) + r"\}(.*?)\{" + str(n) + r"\}(.*?)(?=\{|\Z)", re.DOTALL)
    m = pattern.search(text)
    if not m:
        raise UnparseableServicerReport(f"numbered item {{{n}}} not found")
    return m.group(2).strip()


def _leading_numeric_tokens(value_zone: str) -> list[str]:
    """Whitespace-split tokens from the start of `value_zone` while they
    still look like numbers (or the nil dash, or a bare `%`).

    Some item value zones run on into the next section's heading text
    before the next brace appears (item `{72}`'s zone runs into "VII.
    DELINQUENCY Units Dollars ..."). Stopping at the first non-numeric
    token keeps that heading text out of the parsed value.
    """
    tokens = value_zone.split()
    out: list[str] = []
    for tok in tokens:
        if tok == "%" or _TOKEN_NUMERIC_RE.match(tok):
            out.append(tok)
        else:
            break
    return out


def _numbered_single(text: str, n: int) -> Decimal:
    toks = _leading_numeric_tokens(_item_value_zone(text, n))
    if not toks:
        raise UnparseableServicerReport(f"numbered item {{{n}}} has no numeric value")
    return _to_decimal(toks[0])


def _numbered_bucket(text: str, n: int) -> dict[str, object]:
    toks = _leading_numeric_tokens(_item_value_zone(text, n))
    if len(toks) < 3:
        raise UnparseableServicerReport(f"numbered item {{{n}}} bucket malformed: {toks!r}")
    count_raw, balance_raw, percent_raw = toks[0], toks[1], toks[2]
    return {
        "count": int(_to_decimal(count_raw)),
        "balance": _to_decimal(balance_raw),
        "percent": _to_decimal(percent_raw),
    }


def _numbered_yes_no(text: str, n: int) -> bool:
    zone = _item_value_zone(text, n).split()
    if not zone:
        raise UnparseableServicerReport(f"numbered item {{{n}}} has no yes/no value")
    word = zone[0].strip(".").lower()
    if word not in {"yes", "no"}:
        raise UnparseableServicerReport(f"numbered item {{{n}}} value not yes/no: {zone[0]!r}")
    return word == "yes"


def _parse_numbered(text: str) -> dict[str, object]:
    receivable_toks = _leading_numeric_tokens(_item_value_zone(text, 72))
    if not receivable_toks:
        raise UnparseableServicerReport("numbered item {72} has no numeric value")

    return {
        "pool_balance": _numbered_single(text, 64),
        "note_balance": _numbered_single(text, 65),
        "oc_amount": _numbered_single(text, 66),
        "oc_percent": _numbered_single(text, 67),
        "oc_target": _numbered_single(text, 63),
        "delinquency_percent": _numbered_single(text, 79),
        "delinquency_trigger": _numbered_single(text, 80),
        "trigger_occurred": _numbered_yes_no(text, 81),
        "sixty_day_delinquent_balance": _numbered_single(text, 78),
        "cumulative_net_loss_percent": _numbered_single(text, 101),
        "receivable_count": int(_to_decimal(receivable_toks[-1])),
        "delinquency_buckets": {
            "31-60": _numbered_bucket(text, 73),
            "61-90": _numbered_bucket(text, 74),
            "91-120": _numbered_bucket(text, 75),
            "121+": _numbered_bucket(text, 76),
        },
        "source_format": "numbered",
    }


# --------------------------------------------------------------------------
# Labelled format (Toyota / TAOT)
# --------------------------------------------------------------------------

# `Receivables Pool Balance` appears twice: once as a column in the 3-period
# "Pool Data" table (Original / Prior / Current), and once standalone right
# before the delinquency percentages. Anchoring on that neighbor picks the
# single, unambiguous, as-of-period-end figure -- not the 3-column row.
#
# Some periods (e.g. TAOT 2022-B 2026-02) render the dollar sign with a
# following space -- "$ 14,450,000.06" instead of "$14,450,000.06" -- so
# every dollar-amount pattern below allows `\$?\s*` rather than bare `\$?`.
_LBL_POOL_BALANCE = re.compile(
    r"Receivables Pool Balance\s+\$?\s*([\d,\.]+)\s+60-Day Delinquency Percentage",
    re.IGNORECASE,
)
_LBL_DELINQ_PCT = re.compile(r"60-Day Delinquency Percentage\s+([\d.]+)\s*%", re.IGNORECASE)
_LBL_DELINQ_TRIGGER = re.compile(r"Delinquency Trigger Percentage\s+([\d.]+)\s*%", re.IGNORECASE)
_LBL_TRIGGER_OCCURRED = re.compile(
    r"Has a Delinquency Trigger occurred[^?]*\?\s*(Yes|No)", re.IGNORECASE
)
_LBL_OC_TARGET = re.compile(
    r"Overcollateralization Target Amount\s+\$?\s*([\d,\.]+)", re.IGNORECASE
)
_LBL_OC_AMOUNT = re.compile(
    r"Ending Overcollateralization Amount\s+\$?\s*([\d,\.]+)", re.IGNORECASE
)
_LBL_NOTE_BALANCE = re.compile(r"Total Note Balance\s+\$?\s*([\d,\.]+)", re.IGNORECASE)
_LBL_RECEIVABLE_COUNT = re.compile(
    r"Number of Contracts\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", re.IGNORECASE
)
_LBL_CUM_NET_LOSS = re.compile(r"Cumulative Net Loss Ratio\s+([\d.]+)\s*%", re.IGNORECASE)
# Not present in any Toyota filing observed -- see module docstring: `None`
# is not zero, so absence of a match below leaves `oc_percent` as `None`
# rather than deriving one from `oc_amount` / `pool_balance`.
_LBL_OC_PERCENT = re.compile(
    r"Overcollateralization Percentage\s+([\d.]+)\s*%", re.IGNORECASE
)


def _labelled_field(text: str, pattern: re.Pattern[str], name: str) -> re.Match[str]:
    m = pattern.search(text)
    if not m:
        raise UnparseableServicerReport(f"labelled field not found: {name}")
    return m


def _labelled_bucket(text: str, label: str) -> dict[str, object]:
    """`LABEL  pct-of-contracts%  count  pct-of-balance%  $balance`.

    The percent captured is the balance-weighted one (matching the semantic
    of Santander's per-bucket percentage), not the contract-count-weighted
    one that precedes it in Toyota's layout.
    """
    pattern = re.compile(
        re.escape(label) + r"\s+[\d.]+\s*%\s+([\d,]+)\s+([\d.]+)\s*%\s+\$?\s*([\d,\.]+)",
        re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        raise UnparseableServicerReport(f"labelled bucket not found: {label}")
    count_raw, percent_raw, balance_raw = m.groups()
    return {
        "count": int(_to_decimal(count_raw)),
        "balance": _to_decimal(balance_raw),
        "percent": _to_decimal(percent_raw),
    }


def _parse_labelled(text: str) -> dict[str, object]:
    pool_balance = _to_decimal(_labelled_field(text, _LBL_POOL_BALANCE, "pool_balance").group(1))
    delinquency_percent = _to_decimal(
        _labelled_field(text, _LBL_DELINQ_PCT, "delinquency_percent").group(1)
    )
    delinquency_trigger = _to_decimal(
        _labelled_field(text, _LBL_DELINQ_TRIGGER, "delinquency_trigger").group(1)
    )
    trigger_word = _labelled_field(text, _LBL_TRIGGER_OCCURRED, "trigger_occurred").group(1)
    oc_target = _to_decimal(_labelled_field(text, _LBL_OC_TARGET, "oc_target").group(1))
    oc_amount = _to_decimal(_labelled_field(text, _LBL_OC_AMOUNT, "oc_amount").group(1))
    note_balance = _to_decimal(_labelled_field(text, _LBL_NOTE_BALANCE, "note_balance").group(1))
    receivable_count = int(
        _to_decimal(_labelled_field(text, _LBL_RECEIVABLE_COUNT, "receivable_count").group(3))
    )
    cum_loss_m = _LBL_CUM_NET_LOSS.search(text)
    oc_percent_m = _LBL_OC_PERCENT.search(text)

    return {
        "pool_balance": pool_balance,
        "note_balance": note_balance,
        "oc_amount": oc_amount,
        "oc_percent": _to_decimal(oc_percent_m.group(1)) if oc_percent_m else None,
        "oc_target": oc_target,
        "delinquency_percent": delinquency_percent,
        "delinquency_trigger": delinquency_trigger,
        "trigger_occurred": trigger_word.strip().lower() == "yes",
        # Toyota never publishes a single aggregate 60+ day delinquent
        # BALANCE the way Santander's {78} does -- only per-bucket balances
        # and the 60-Day Delinquency PERCENTAGE. Summing the 60-89/90-119/
        # 120+ bucket balances ourselves would be exactly the substitute
        # arithmetic the module docstring says never to present as filed.
        "sixty_day_delinquent_balance": None,
        "cumulative_net_loss_percent": (
            _to_decimal(cum_loss_m.group(1)) if cum_loss_m else None
        ),
        "receivable_count": receivable_count,
        "delinquency_buckets": {
            "30-59": _labelled_bucket(text, "30-59 Days Delinquent"),
            "60-89": _labelled_bucket(text, "60-89 Days Delinquent"),
            "90-119": _labelled_bucket(text, "90-119 Days Delinquent"),
            "120+": _labelled_bucket(text, "120 or more Days Delinquent"),
        },
        "source_format": "labelled",
    }


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def parse_servicer_report(raw_html: str) -> dict[str, object]:
    """Parse one servicer distribution report (EX-99.1 HTML) into a dict.

    Dispatches on `detect_format`. Raises `UnparseableServicerReport` if the
    detected branch cannot find its required fields, or if (defensively)
    the branch somehow returns a dict missing a required key -- see the
    module docstring's first section for why this never falls back to
    zeros.
    """
    text = _strip_html(raw_html)
    fmt = detect_format(text)
    if fmt == "numbered":
        result = _parse_numbered(text)
    else:
        result = _parse_labelled(text)

    missing = [k for k in _REQUIRED_KEYS if k not in result]
    if missing:
        raise UnparseableServicerReport(f"parsed result missing required keys: {missing}")
    return result
