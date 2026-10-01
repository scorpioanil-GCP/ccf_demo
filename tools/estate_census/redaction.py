"""Credential redaction at GENERATION time (`D-IMPL-358` ruling 8, support
machinery under `D-IMPL-276`).

**Two jobs, deliberately two functions, because they are not the same job.**

`redact_target` handles a connection target the census *holds* — a DSN read out
of the environment. There the whole string is a parseable structure, so the safe
operation is to **parse it and rebuild it from its non-secret parts**, carrying
neither user nor password forward. That is the posture
`src/ccf/graph/backends/postgres.py::_graph_identity` already takes, and it is
strictly stronger than erasing a substring: a field that is never read cannot be
re-emitted by a later formatting change.

`redact_text` handles free text the census *captures* — a pytest traceback, a
failure message, a skip reason. **That text cannot be parsed structurally**,
because it is prose with a credential embedded somewhere inside it, so this one
necessarily matches on the credential-bearing *grammar*. Stated plainly rather
than left implicit: the "rebuild, do not substitute" rule applies to
`redact_target`, and there is no structural alternative for `redact_text`.

Why both are needed, measured 2026-09-22 and recorded in the Wave 2 handoff: a
pytest traceback renders the raising frame's **arguments**, so a guard that
prints a carefully redacted message has the unredacted DSN printed beside it in
the frame that raised. Redacting only what the census formats itself is not
enough; it must redact what it captures.

**Three rules this module obeys, each bought with a recorded incident.**

* **Never sweep by secret VALUE.** A value sweep on the four-character password
  ``test`` rewrote 28,507 occurrences of ordinary text. Nothing here is given
  the secret; every rule matches structure or grammar.
* **No angle brackets in the placeholder.** An angle-bracketed placeholder
  silently broke an XML census file. `PLACEHOLDER` is the house ``***``
  already asserted in-tree for the write fence.
* **Redact each field BEFORE serializing it, never sweep a serialized
  document.** A value class greedy enough to be safe will eat a closing quote,
  which corrupts XML; a field redacted first and then handed to an XML writer
  cannot, because the writer adds the delimiters afterwards.
  `tools/estate_census/evidence.py::write_junit_xml` is what depends on this.

Known and accepted over-redaction: a grammar match is deliberately generous, so
``password: the credential`` in a docstring quoted inside a traceback loses the
word ``the``. Over-redacting prose is harmless; under-redacting a credential is
not, and every ambiguous case here is resolved toward over-redaction.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from psycopg.conninfo import conninfo_to_dict, make_conninfo

#: The house placeholder. ``***`` rather than an angle-bracketed token because
#: an angle-bracketed placeholder silently broke an XML census file, and rather
#: than a bespoke spelling because ``***`` is what the write fence already emits
#: and what `tests/examples/test_curated_estate_write_fence.py` already asserts.
#: Contains no ``<``, ``>`` or ``&``, so it survives XML and JSON unchanged.
PLACEHOLDER = "***"

#: libpq / driver keys whose VALUE is a credential. Matched as a *segment* of a
#: surrounding identifier, not as a whole word: this repository's own estate
#: variables are spelled ``CCF_CP_15_TOKEN_READ``, and ``_`` is a word
#: character, so a ``\b``-anchored ``token`` match does not see them. Measured:
#: with ``\btoken\b`` the value of ``CCF_CP_15_TOKEN_READ`` survived redaction
#: in full.
SECRET_KEY_WORDS: tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "sslpassword",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "accesskey",
    "credential",
    "private_key",
)

#: Connection-parameter keys dropped entirely when a target is rebuilt. ``user``
#: joins ``password`` because a rebuilt identity needs neither, and a username
#: is estate configuration detail that has no business in a committed artifact.
DROPPED_TARGET_KEYS: frozenset[str] = frozenset(
    {"password", "passwd", "passfile", "sslpassword", "user", "username"}
)

_SECRET_KEY = r"[A-Za-z0-9_.\-]*(?:" + "|".join(SECRET_KEY_WORDS) + r")[A-Za-z0-9_.\-]*"
_VALUE = r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[^\s;,&]+"

#: ``Bearer <token>``. Runs BEFORE `_KEYWORD`: measured, the keyword rule would
#: otherwise match ``Authorization`` and consume the single word ``Bearer`` as
#: its value, leaving the token itself untouched in the artifact.
_BEARER = re.compile(r"(?P<kind>\b(?:Bearer|Basic|Token|Digest)\s+)(?P<value>\S+)")

#: An ``Authorization`` header's credential is the remainder of the line, not a
#: whitespace-delimited token, so it is matched to end-of-line.
_AUTHZ = re.compile(
    r"(?P<key>\bauthorization\b)(?P<sep>\s*[=:]\s*)(?P<value>[^\r\n]+)", re.IGNORECASE
)

#: ``scheme://user:SECRET@host``. The password class is ``\S*`` — it admits
#: ``@``, ``/``, ``?`` and ``#`` — and is applied per whitespace-delimited token
#: by `_redact_uris_per_token`. Measured, both halves are load-bearing: a class
#: excluding ``@`` stopped at the first ``@`` inside ``p@ssword`` and left ten of
#: twelve characters in the artifact, and a class excluding ``/`` failed to match
#: ``ab/cd/secret`` at all and redacted nothing.
_URI_USERINFO = re.compile(
    r"(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*://)(?P<user>[^:/?#@\s]*):(?P<pw>\S*)(?P<at>@)"
)

_KEYWORD = re.compile(
    r"(?P<key>" + _SECRET_KEY + r")(?P<sep>\s*[=:]\s*)(?P<value>" + _VALUE + r")",
    re.IGNORECASE,
)


def _redact_uris_per_token(text: str) -> str:
    """Apply the URI rule inside each whitespace-delimited token separately.

    A URI cannot contain whitespace, so a token boundary is a URI boundary. That
    is what makes the greedy "to the last ``@``" match safe: applied to a whole
    line carrying two URIs it would swallow everything between the first
    password and the second, mangling the message; applied per token it cannot
    reach past the URI it is redacting.
    """
    return "".join(
        part
        if part.isspace()
        else _URI_USERINFO.sub(
            lambda m: f"{m['scheme']}{m['user']}:{PLACEHOLDER}{m['at']}", part
        )
        for part in re.split(r"(\s+)", text)
    )


def redact_text(text: str | None) -> str | None:
    """Every credential grammar this project has met, removed from free text.

    Order matters and is asserted by
    `tools/estate_census_tests/test_redaction.py::test_a_bearer_token_is_redacted_and_not_merely_its_scheme_word`.
    """
    if not isinstance(text, str) or not text:
        return text
    text = _BEARER.sub(lambda m: f"{m['kind']}{PLACEHOLDER}", text)
    text = _AUTHZ.sub(lambda m: f"{m['key']}{m['sep']}{PLACEHOLDER}", text)
    text = _redact_uris_per_token(text)
    return _KEYWORD.sub(lambda m: f"{m['key']}{m['sep']}{PLACEHOLDER}", text)


def _looks_like_postgres(target: str) -> bool:
    """The same two-serialization test `tests/examples/estate_guard.py` applies.

    A PostgreSQL target is either a URI or libpq keyword form, and knowing one
    proves nothing about the other: a Wave 1 credential sweep that knew only the
    URI form reported "no DSN points at the estate" while a keyword-form DSN sat
    in a census log.
    """
    return target.startswith(("postgres://", "postgresql://")) or (
        "=" in target and "://" not in target
    )


def redact_target(target: str | None) -> str:
    """A connection target rebuilt from its non-secret parts.

    Not a substitution over the original string — a rebuild. The parsed host,
    port and database survive; user and password are never carried forward, so
    no later formatting change can re-emit them.

    Returns the literal ``"***unparseable-target***"`` when the target cannot be
    classified. **Refusing to render is the safe answer**: a target nobody has
    parsed is a target whose secret nobody has located, and echoing it back to
    find out would publish it. This is the same *don't know is not pass* posture
    `tools/check_product_gates.py` takes for an unreadable collection.
    """
    if not isinstance(target, str) or not target.strip():
        return "***empty-target***"
    return _refuse_if_still_credentialed(_rebuild_target(target))


def _rebuild_target(target: str) -> str:
    """The rebuild itself. Split out so `redact_target` can post-condition it."""
    if _looks_like_postgres(target):
        try:
            parsed = conninfo_to_dict(target)
        except Exception:
            return "***unparseable-target***"
        kept = {
            key: value
            for key, value in parsed.items()
            if key not in DROPPED_TARGET_KEYS and isinstance(value, str)
        }
        try:
            return make_conninfo(**kept)
        except Exception:
            return "***unparseable-target***"
    try:
        split = urlsplit(target if "://" in target else f"//{target}")
    except ValueError:
        return "***unparseable-target***"
    authority = split.netloc.rsplit("@", 1)[-1]
    if not authority:
        return "***unparseable-target***"
    scheme = f"{split.scheme}://" if split.scheme else ""
    return f"{scheme}{authority}{split.path}"


def _refuse_if_still_credentialed(rendered: str) -> str:
    """A rebuilt target that still trips `find_credential` is not rendered.

    The rebuild paths cover the shapes this project has met. A target none of
    them classifies falls through to the URL branch, which echoes an authority
    it could not decompose — and an echo is exactly how a credential in an
    unrecognized shape would reach an artifact. So the rendered result is
    checked against the same grammar the census uses to reject evidence, and a
    hit refuses rather than renders. Asserted by
    `tools/estate_census_tests/test_redaction.py::test_an_unrecognized_target_shape_is_refused_not_echoed`.
    """
    return "***unparseable-target***" if find_credential(rendered) else rendered


def find_credential(text: str) -> str | None:
    """The first credential grammar still present in `text`, or ``None``.

    The census uses this on an artifact it is about to trust or commit. Dave's
    rule: *"Raw evidence containing a secret is never committed and is not
    treated as valid census evidence."* So a positive answer here is not a
    warning, it is an INDETERMINATE verdict —
    `tools/estate_census/classify.py::classify` is where that happens.

    Detection is by grammar, never by value, and it is deliberately the same
    grammar `redact_text` removes: anything this finds, that function would have
    removed, so a hit means redaction did not run rather than that it was
    imperfect. `tools/estate_census_tests/test_redaction.py` asserts exactly
    that pairing in both directions.
    """
    if not isinstance(text, str) or not text:
        return None
    for label, pattern in (
        ("uri-userinfo-password", _URI_USERINFO),
        ("authorization-header", _AUTHZ),
        ("bearer-token", _BEARER),
        ("keyword-credential", _KEYWORD),
    ):
        for match in pattern.finditer(text):
            value = match.groupdict().get("value") or match.groupdict().get("pw") or ""
            if value.strip("'\"") not in ("", PLACEHOLDER):
                return f"{label} at offset {match.start()}"
    return None
