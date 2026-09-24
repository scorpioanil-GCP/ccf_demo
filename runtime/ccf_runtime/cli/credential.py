"""The credential the ``ccf`` CLI carries on its remote leg (SEC-016).

SDK-defined (CLAUDE.md §8.3; D-IMPL-22). The CLI is a thin client over the
HTTP API, and until this module existed it was a thin client that could
not authenticate: no ``Authorization`` header, no bearer token, no way to
name one. An operator handed an authenticated deployment therefore had
exactly one working configuration — the one with authentication turned
off — which makes the SDK's own authorization work unshippable.

**A source is named; a value is never typed.** The deployment says
*where* the credential comes from and the SDK reads it, which is the
discipline :class:`~ccf.controlplane.artifacts.SecretReference` and
:func:`ccf.deployment.manifest._resolve_secret_references` already hold
for backend credentials (D-08). Two sources are accepted:

* the *name* of an environment variable (``--token-env NAME`` or
  ``CCF_TOKEN_ENV``), and
* the *path* of a file holding the token (``--token-file PATH`` or
  ``CCF_TOKEN_FILE``), the shape
  :class:`ccf_runtime.mcp.auth.FileTokenSource` reads on the serving
  side — a file is revocable by editing it.

There is deliberately no flag that takes a token *value*: a secret in
``argv`` is a secret in ``ps``. There is no default variable and no
default path, for the reason :class:`~ccf_runtime.mcp.auth.FileTokenSource`
records — a default location for a secret is a place an attacker knows to
look — and because "which credential was in force" has to stay
answerable. The SDK ships no token (CINV-01).

**Unset, empty and absent are refusals, never fallbacks.** Naming a
source asserts a credential is required, so a named variable that is
unset resolves to a refusal rather than to an anonymous call. Naming
*no* source on a remote invocation is the same refusal, and this is the
load-bearing decision in the module: a CLI that authenticated only when
a credential happened to be configured, and proceeded unauthenticated
otherwise, would be a guard whose applicability the caller decides —
which is not a guard. The precedent is WR-02/WR-03, where a credentialed
URL connected anonymously because the wire client derived no header from
``base_url`` userinfo: the failure was silent, and a refusal is what
stops it arriving through a new door.

**Nothing here can echo a credential.** The resolved value is wrapped in
``pydantic.SecretStr``, which masks itself in ``repr`` and ``str`` and
which :func:`ccf.contracts.canonical.canonical_bytes` refuses outright,
so a credential cannot be content-hashed into an artifact even by
accident. Every refusal below is built from the *names* the operator
supplied and never from what they resolved to.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import SecretStr

__ccf_mode__ = "algorithmic"

__all__ = [
    "CredentialUnresolved",
    "authorization_headers",
    "resolve_remote_credential",
]


class CredentialUnresolved(ValueError):
    """The remote leg has no usable credential, and will not proceed.

    Raised rather than returned as ``None`` because there is no caller
    that can do anything useful with "no credential" — the remote leg is
    a network boundary and the one alternative to holding a credential is
    not making the call. :mod:`ccf_runtime.cli.main` maps this to the
    documented exit status 2 (deployment wiring, reported on stderr), the
    same status a missing base URL already takes: both say the operator
    has to configure something before any request can be built.
    """


def _refuse_no_source() -> CredentialUnresolved:
    """The refusal an operator sees when nothing names a credential."""
    return CredentialUnresolved(
        "no credential is configured for the remote leg. Name the"
        " environment variable holding the token with --token-env NAME"
        " (or set CCF_TOKEN_ENV), or the file holding it with"
        " --token-file PATH (or set CCF_TOKEN_FILE). The SDK ships no"
        " token and no default location for one, and it does not call a"
        " remote API anonymously — there is no flag that turns this off."
    )


def resolve_remote_credential(
    *,
    token_env: str | None,
    token_file: str | None,
    environ: Mapping[str, str],
) -> SecretStr:
    """Resolve the bearer credential for one remote invocation.

    Args:
        token_env: Name of the environment variable holding the token — a
            name, never a value. ``None`` when the operator named no
            environment source.
        token_file: Path of a file holding the token. ``None`` when the
            operator named no file source.
        environ: The environment to read ``token_env`` from. Passed in
            rather than read here so the resolution stays a pure function
            of its inputs, which is what lets it be tested without
            mutating the process.

    Returns:
        The token, wrapped so it masks itself everywhere but at the one
        unwrap site in :func:`authorization_headers`.

    Raises:
        CredentialUnresolved: no source is named; both sources are named;
            or the named source is unset, empty or unreadable. Every
            message names the *source* the operator supplied and never
            what it held — in the unset case there is nothing to name,
            and in the others naming it would be the disclosure this
            module exists to prevent.
    """
    if token_env and token_file:
        # Precedence between two configured sources would be a silent
        # choice about which principal acted, and the ledger the CLI
        # writes to is replay-relevant. Refuse instead of ordering them.
        raise CredentialUnresolved(
            f"two credential sources are configured: the environment"
            f" variable {token_env!r} and the token file {token_file!r}."
            " Which credential was in force is an audit fact and the CLI"
            " will not guess at it — configure exactly one."
        )

    if token_env:
        # The process environment is read here and nowhere else in this
        # package. The value is bound only to reach `SecretStr`; the
        # refusal below is built from the variable NAME, never from it.
        raw = environ.get(token_env)
        if raw is None or not raw.strip():
            raise CredentialUnresolved(
                f"the environment variable {token_env!r} names this"
                " invocation's credential and is unset or empty. Naming a"
                " source asserts a credential is required, so the CLI"
                " refuses rather than calling the API anonymously — set"
                " the variable, or name a different source."
            )
        return SecretStr(raw.strip())

    if token_file:
        path = Path(token_file)
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as unreadable:
            raise CredentialUnresolved(
                f"the token file {token_file!r} names this invocation's"
                " credential and could not be read:"
                f" {unreadable.strerror or type(unreadable).__name__}."
                " A file that cannot be read is not an absent credential"
                " — set the path, or name a different source."
            ) from unreadable
        if not contents.strip():
            raise CredentialUnresolved(
                f"the token file {token_file!r} names this invocation's"
                " credential and holds nothing. An empty file is a"
                " misconfiguration, not a decision to go anonymous."
            )
        # Surrounding whitespace is file formatting, not credential
        # material: a token file written by `echo` ends in a newline.
        return SecretStr(contents.strip())

    raise _refuse_no_source()


def authorization_headers(credential: SecretStr) -> dict[str, str]:
    """The bearer header for ``credential`` — the one unwrap site.

    Every other line in this package handles the credential as a
    ``SecretStr``. Keeping ``get_secret_value`` to a single call makes
    "where can this value escape?" a question a grep answers.
    """
    return {"Authorization": f"Bearer {credential.get_secret_value()}"}
