"""Controls over `tools/estate_census/redaction.py` — the secret-safety half of
`D-IMPL-358` ruling 8.

Every property here was a DEFECT in a draft of that module before it was a test.
Named, because a control whose failure mode was never observed tends to be a
control that cannot fail:

* a URI password containing ``@`` truncated the match and left ten of twelve
  characters in the artifact, while a whole-string equality check called it clean;
* a URI password containing ``/`` matched nothing at all and redacted nothing;
* ``Authorization: Bearer <token>`` had the word ``Bearer`` redacted as the value
  and the token itself survived intact;
* ``CCF_CP_15_TOKEN_READ=<secret>`` — this repository's own estate-variable
  spelling — was missed entirely because ``\\btoken\\b`` cannot match inside an
  identifier where ``_`` is a word character.

**The positive control is `the_leak_detector_finds_a_secret_that_redaction_did_not_remove`**,
which runs the leak detector against three known-broken redactions and requires
it to fire on each. Without it, every assertion below could pass because the
detector is blind rather than because the redaction works.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from tools.estate_census.redaction import (
    PLACEHOLDER,
    find_credential,
    redact_target,
    redact_text,
)

#: Secret shapes chosen for the characters that broke a draft, not for realism.
SECRET_SHAPES: dict[str, str] = {
    "plain": "sUp3r-s3cr3t-pw",
    "at-sign": "p@ssw0rd-secret",
    "slash": "ab/cd/secret99",
    "at-and-slash": "x@y/z@w/secret9",
    "quote-and-xml": 'p@ss"w<ord&1',
    "colon": "a:b:c:secret99",
    "equals": "ab=cd=secret99",
    "percent-encoded": "ab%40cd%2Fsec99",
}


def representations(secret: str) -> dict[str, str]:
    """Every way this project has actually seen a credential written down."""
    return {
        "postgres-uri": f"postgresql://ccf:{secret}@192.168.4.76:5432/ccf_v2",
        "postgres-uri-query": f"postgresql://ccf:{secret}@192.168.4.76/ccf_v2?sslmode=require",
        "libpq-keyword": f"host=192.168.4.76 port=5432 user=ccf password={secret} dbname=ccf_v2",
        "libpq-quoted": f"host=192.168.4.76 user=ccf password='{secret}' dbname=ccf_v2",
        "libpq-spaced": f"host=h user=ccf password = {secret} dbname=ccf_v2",
        "pgpassword-env": f"PGPASSWORD={secret}",
        "mongo-uri": f"mongodb://ccf:{secret}@192.168.4.76:27017/fibo_v2?authSource=admin",
        "mongo-srv": f"mongodb+srv://ccf:{secret}@cluster.example.net/fibo_v2",
        "mongo-multihost": f"mongodb://ccf:{secret}@h1:27017,h2:27017/fibo_v2",
        "traceback-keyword": f'OperationalError: could not connect to "host=h user=ccf password={secret}"',
        "traceback-uri": f"OperationalError: connection to postgresql://ccf:{secret}@h:5432/db failed",
        "bearer-header": f"Authorization: Bearer {secret}",
        "authorization-kv": f"authorization={secret}",
        "repo-token-var": f"CCF_CP_15_TOKEN_READ={secret}",
        "repo-token-var-2": f"CCF_TEST_WIRING_TOKEN={secret}",
        "env-dump": f"CCF_CP_04_POSTGRES_DSN=postgresql://ccf:{secret}@192.168.4.76/ccf_v2",
        "two-uris-one-line": f"a=postgresql://u:{secret}@h1/db b=mongodb://u:{secret}@h2/db",
    }


def surviving_runs(secret: str, text: str, minimum: int = 4) -> list[str]:
    """Runs of at least `minimum` consecutive secret characters left in `text`.

    A SUBSTRING test, deliberately. Asking whether the whole secret is present is
    the check that called a ten-of-twelve-character leak clean.
    """
    length = min(minimum, len(secret))
    return sorted(
        {
            secret[start:stop]
            for start in range(len(secret))
            for stop in range(start + length, len(secret) + 1)
            if secret[start:stop] in text
        },
        key=len,
        reverse=True,
    )


# --------------------------------------------------------------------------
# Preconditions. Nothing below is worth reading if these do not hold.
# --------------------------------------------------------------------------


def test_the_representation_roster_is_populated_and_contains_the_secret() -> None:
    """A vacuity guard: a roster that embedded no secret would pass everything."""
    for name, secret in SECRET_SHAPES.items():
        cases = representations(secret)
        assert len(cases) >= 17, f"{name}: roster shrank to {len(cases)}"
        for case_name, text in cases.items():
            assert secret in text, f"{name}/{case_name} does not contain the secret"


def test_the_leak_detector_finds_a_secret_that_redaction_did_not_remove() -> None:
    """THE POSITIVE CONTROL. Three redactions that shipped broken must be caught.

    Each `broken` below is a real earlier draft of the shipped rule. If the
    detector cannot see these leaks, every other assertion in this module is
    vacuous.
    """
    at_secret = SECRET_SHAPES["at-sign"]
    slash_secret = SECRET_SHAPES["slash"]
    plain = SECRET_SHAPES["plain"]

    # Draft 1: URI password class excluded '@', so it stopped at the first one.
    broken_at = re.sub(
        r"([A-Za-z][A-Za-z0-9+.\-]*://)([^:/?#@\s]*):([^@/?#\s]*)@",
        r"\1\2:" + PLACEHOLDER + "@",
        representations(at_secret)["postgres-uri"],
    )
    assert surviving_runs(at_secret, broken_at), "detector blind to the @-truncation leak"

    # Draft 2: URI password class excluded '/', so the rule matched nothing.
    broken_slash = re.sub(
        r"([A-Za-z][A-Za-z0-9+.\-]*://)([^:/?#@\s]*):([^@/?#\s]*)@",
        r"\1\2:" + PLACEHOLDER + "@",
        representations(slash_secret)["postgres-uri"],
    )
    assert surviving_runs(slash_secret, broken_slash), "detector blind to the /-in-password leak"

    # Draft 3: '\btoken\b' cannot match inside CCF_CP_15_TOKEN_READ.
    broken_token = re.sub(
        r"(\btoken\b)(\s*=\s*)(\S+)",
        r"\1\2" + PLACEHOLDER,
        representations(plain)["repo-token-var"],
        flags=re.IGNORECASE,
    )
    assert surviving_runs(plain, broken_token), "detector blind to the identifier-segment miss"


# --------------------------------------------------------------------------
# The property itself.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("shape", sorted(SECRET_SHAPES))
def test_no_credential_serialization_survives_redaction_in_any_secret_shape(shape: str) -> None:
    """`D-IMPL-358` ruling 8: redact secrets at generation time, both PostgreSQL
    serializations and the Mongo URI form, structurally rather than by value."""
    secret = SECRET_SHAPES[shape]
    leaked: list[str] = []
    for name, text in representations(secret).items():
        surviving = surviving_runs(secret, redact_text(text) or "")
        if surviving:
            leaked.append(f"{name}: {surviving[0]!r} survived in {redact_text(text)!r}")
    assert not leaked, "\n".join(leaked)


def test_a_bearer_token_is_redacted_and_not_merely_its_scheme_word() -> None:
    """The measured ordering defect: the keyword rule matched ``Authorization``,
    consumed ``Bearer`` as its value, and the token survived."""
    secret = SECRET_SHAPES["plain"]
    rendered = redact_text(f"Authorization: Bearer {secret}") or ""
    assert secret not in rendered, rendered
    assert "Bearer" not in rendered or PLACEHOLDER in rendered, rendered


def test_an_identifier_segment_key_is_matched_so_repo_token_variables_are_covered() -> None:
    """``CCF_CP_15_TOKEN_READ`` is this repository's own spelling for a credential
    variable, and ``_`` is a word character, so a ``\\b``-anchored key misses it."""
    secret = SECRET_SHAPES["plain"]
    for variable in ("CCF_CP_15_TOKEN_READ", "CCF_TEST_WIRING_TOKEN", "PGPASSWORD", "DB_PASSWORD"):
        rendered = redact_text(f"{variable}={secret}") or ""
        assert secret not in rendered, f"{variable}: {rendered}"


@pytest.mark.parametrize(
    "innocent",
    [
        "The password policy requires rotation. See test_password_rotation.",
        "http://192.168.4.76:8090/fluree/query",
        "host=localhost port=5432 dbname=ccf_v2 user=ccf",
        "postgresql://ccf@192.168.4.76:5432/ccf_v2",
        "mongodb://192.168.4.76:27017/fibo_v2",
        "tests/examples/test_cp_04_family.py::test_depth[3]",
    ],
)
def test_text_carrying_no_credential_is_left_exactly_as_it_was(innocent: str) -> None:
    """Never sweep by secret VALUE. A value sweep on the four-character password
    ``test`` rewrote 28,507 occurrences of ordinary text; this is the control that
    a grammar-based rule does not repeat it."""
    assert redact_text(innocent) == innocent


def test_the_placeholder_carries_no_xml_or_json_metacharacter() -> None:
    """An angle-bracketed placeholder silently broke an XML census file."""
    assert not set("<>&\"'") & set(PLACEHOLDER), PLACEHOLDER


def test_a_redacted_field_cannot_corrupt_the_xml_it_is_serialized_into() -> None:
    """Redact per field, then serialize — never sweep a serialized document.

    A value class greedy enough to be safe will eat a closing quote; a field
    redacted first and handed to an XML writer cannot, because the writer adds
    the delimiters afterwards.
    """
    secret = SECRET_SHAPES["quote-and-xml"]
    element = ET.Element("testsuite")
    case = ET.SubElement(element, "testcase", {"name": redact_text(representations(secret)["traceback-uri"]) or ""})
    ET.SubElement(case, "failure", {"message": redact_text(representations(secret)["traceback-keyword"]) or ""}).text = (
        redact_text("\n".join(representations(secret).values())) or ""
    )
    blob = ET.tostring(element, encoding="utf-8", xml_declaration=True)
    ET.fromstring(blob)  # raises ParseError if the document was corrupted
    assert not surviving_runs(secret, blob.decode())


def test_the_same_database_reached_by_either_postgres_serialization_renders_identically() -> None:
    """A rebuild normalizes, so a URI DSN and a libpq keyword DSN naming the same
    database produce the same redacted target. That is what makes a target safe to
    record as evidence of WHICH store was read."""
    uri = "postgresql://ccf:SECRET@192.168.4.76:5432/ccf_v2"
    keyword = "host=192.168.4.76 port=5432 user=ccf password=SECRET dbname=ccf_v2"
    assert redact_target(uri) == redact_target(keyword)
    assert "SECRET" not in redact_target(uri)
    assert "ccf" in redact_target(uri)  # the database name survives; the user does not
    assert "user=" not in redact_target(uri)


def test_an_unrecognized_target_shape_is_refused_not_echoed() -> None:
    """A target no parser classified is a target whose secret nobody located, and
    echoing it back to find out would publish it."""
    rendered = redact_target("totally unparseable password=SECRET_LEAK")
    assert "SECRET_LEAK" not in rendered
    assert rendered == "***unparseable-target***"


def test_an_empty_target_is_named_rather_than_rendered_as_nothing() -> None:
    assert redact_target("") == "***empty-target***"
    assert redact_target(None) == "***empty-target***"


def test_find_credential_and_redact_text_agree_in_both_directions() -> None:
    """The detector's grammar is the redactor's grammar, so a hit on an artifact
    means redaction did not RUN rather than that it was imperfect. That is what
    makes `tools/estate_census/classify.py::classify` able to treat a hit as an
    INDETERMINATE verdict instead of a warning."""
    for secret in SECRET_SHAPES.values():
        for name, text in representations(secret).items():
            assert find_credential(text) is not None, f"detector missed {name}"
            assert find_credential(redact_text(text) or "") is None, f"detector fires after redaction on {name}"


def test_redaction_survives_a_json_round_trip() -> None:
    secret = SECRET_SHAPES["at-and-slash"]
    payload = json.dumps({k: redact_text(v) for k, v in representations(secret).items()})
    assert json.loads(payload)
    assert not surviving_runs(secret, payload)
