# 350-03 — the CLI carries a credential, and the audit actor is not caller-typed

`SEC-016` and `SEC-012` from the security review of 2026-09-23, Tier 1.

`SEC-016`: the shipped `ccf` CLI had **zero** `Authorization` / `Bearer`
references across all 15 `.py` files under `runtime/ccf_runtime/cli/` — it could
not authenticate at all, which is the finding a reviewer said must land WITH the
authorization work or we ship auth that operators are forced to turn off.

`SEC-012`: `ccf skill revoke --actor` let the caller TYPE the audit actor, which
was then written into the replay-relevant grant ledger.

## What did NOT change, stated first

- **No flag takes a token value.** A secret in `argv` is a secret in `ps`. The
  deployment names *where* the credential is; the SDK reads it — the existing
  `SecretReference` discipline (D-08), not a new scheme.
- **The SDK ships no token and no default location for one**, exactly as
  `FileTokenSource` already records for its own source.
- **The `--local` in-process leg is untouched** and still constructs the app the
  way it did. Reconciling it with required authentication is join-time work.

## ccf_runtime.cli.credential.resolve_remote_credential

- Surface: ccf_runtime.cli.credential.resolve_remote_credential
- Public surface: true
- Change type: added
- Before: absent — the CLI had no credential concept
- After: resolves the remote-leg bearer from `--token-env` / `CCF_TOKEN_ENV` or
  `--token-file` / `CCF_TOKEN_FILE`, beside the existing base-URL resolution
- Why: `SEC-016`. Unset, empty, unreadable, and *both sources at once* are all
  refusals — both-at-once because which credential was in force is an audit
  fact, so a precedence rule would be a silent choice
- Migration: a remote invocation must now name a credential source

## ccf_runtime.cli.credential.authorization_headers

- Surface: ccf_runtime.cli.credential.authorization_headers
- Public surface: true
- Change type: added
- Before: absent
- After: the single site where the resolved secret is unwrapped, attached as
  client-default headers on the one `httpx.AsyncClient` the CLI constructs
- Why: one unwrap site is auditable; a value unwrapped at several is not
- Migration: none — internal to the CLI's request path

## ccf_runtime.cli.credential.CredentialUnresolved

- Surface: ccf_runtime.cli.credential.CredentialUnresolved
- Public surface: true
- Change type: added
- Before: absent
- After: the typed refusal when nothing names a credential, or when what is
  named cannot be read. Reported at **exit 2 on stderr** — the same status the
  existing missing-base-URL check already took
- Why: both are deployment wiring that must be settled before a request can be
  built, so they belong on the same exit status rather than on two. A typed
  class rather than a bare `ValueError` so the door can distinguish it
- Migration: none. The exit-code contract in `cli/main.py`'s docstring was
  widened to say so, rather than left asserting something the code no longer did

## runtime/ccf_runtime/cli/commands/skill.py

- Surface: runtime/ccf_runtime/cli/commands/skill.py
- Public surface: false
- Change type: behavior
- Before: `--actor` on skill grant/revoke; the caller typed the audit actor
- After: the flag is deleted and a grant file naming an `actor:` key is refused;
  the actor is whoever the credential says you are
- Why: `SEC-012`. An audit actor a caller can type is not an audit actor
- Migration: drop `--actor`. Measured with its population: no consumer of
  `ccf_runtime.cli` exists outside `runtime/ccf_runtime/cli/` and `tests/cli/`,
  and no doc, example or script references the flag

## THE DECISION INSIDE THIS, STATED BECAUSE IT IS A POSTURE CHANGE

**A remote call with no credential refuses, and there is no opt-out flag.**
Sending a credential only when one happens to be configured is a guard whose
applicability the caller decides — the defect this remediation has already hit
twice. The precedent is WR-02/WR-03: a credentialed URL once connected
anonymously and the failure was silent.

## Regression evidence

`tests/cli/test_credential.py` (new) plus additions to `tests/cli/test_cli.py`.
The load-bearing red was `test_a_remote_call_without_a_credential_refuses`
failing with **`DID NOT RAISE SystemExit`** — the CLI proceeding with an
anonymous request, which is `SEC-016` as an executable artifact.

**Sabotage-verified, 11 severings, 11 reds**: header never sent (3 tests),
no-credential proceeds anonymously, unset env var accepted (2), missing token
file tolerated, empty token file accepted, two sources silently ordered,
credential not masked, revoke body carries an actor, `--actor` restored, and a
grant file's actor accepted.

The lane's first attempt at one severing was a no-op that stayed green; it
rejected its own result and rewrote the severing as a real one, which then
reddened. Recorded because a sabotage that cannot redden its gate is the failure
mode this project keeps finding.

## The follow-up this had, now closed at the join

`tests/cli/test_cli.py::test_skill_grant_and_revoke` was marked
`xfail(strict=False)` pending the HTTP lane deleting the server-side
`GrantRequest.actor` / `GrantRevocationRequest.actor` fields, which are
required on `extra=forbid` contracts. Those landed, the test XPASSed at the
join, and the marker is removed. The two halves met exactly as predicted,
which is the cheap evidence that the handoff was stated correctly rather than
guessed.

## The posture change this forced, recorded because it surprises people

`--local` is **suspended**. It built its app with `acknowledge_insecure_default`,
and that posture is deleted (`SEC-002`). `build_local_dependencies` mints a
fresh EMPTY Control Plane per invocation, so the one shipped authorizer —
deny-by-default against a registered scope mapping — has nothing to decide
against, and `create_app`'s other three seams are required now too. Reviving
the mode means declaring a real local deployment; that is a decision about what
`--local` MEANS and is not taken here. It refuses at exit 2 naming each seam a
local deployment would have to declare, pinned by
`tests/cli/test_cli.py::test_local_is_suspended_and_names_what_reviving_it_would_cost`
so the message cannot decay into a bare "not supported".

The in-process leg used to be exempt from credentials on the reasoning that it
crossed no network boundary. It is not exempt now: the gate is total, an
in-process request is a request, and the absence of a network boundary entitles
it to nothing.
