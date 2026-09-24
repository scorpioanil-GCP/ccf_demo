# 351-01 — an imported skill package is untrusted input

`SEC-003` (HIGH) from the security review of 2026-09-23, landed on `main` ahead
of the rest of the remediation under Dave's ruling of 2026-09-24, because the
SDK is going to a small group of developers for feedback and this is the one
finding whose cost falls on **the recipient's own machine** rather than on the
repository.

## What did NOT change, stated first

- **The mapping is unchanged.** Frontmatter `name`/`description` → the catalog
  entry, the body → a `ccf.prompt-artifact`, `references/` → further pinned
  artifacts, and the body bound by `InstructionBinding` reference — all register
  exactly as before for a package that is what it claims to be.
- **Nothing else from the remediation is here.** This commit carries `SEC-003`
  only; the `SEC-001` approval-gate work stays on its own branch. Verified: zero
  occurrences of `_gate_authority`, `GATE_APPROVE` or `workflow_definition_hash`
  in the diff.

## ccf_runtime.cli.commands.CommandRefused

- Surface: ccf_runtime.cli.commands.CommandRefused
- Public surface: true
- Change type: added
- Before: absent — only a refusal that had already crossed the HTTP boundary
  could reach the documented exit-1-with-body contract, so a verb refusing its
  own local inputs could do nothing but raise
- After: a `ValueError` subclass; `ccf_runtime.cli.main.main` catches it, prints
  it on stdout and returns `EXIT_REFUSED`
- Why: a hostile skill package is a governance outcome and has to read like one.
  An operator handed a traceback learns less than an operator handed a refusal
- Migration: none for existing verbs. A new verb refusing its own inputs should
  raise this rather than a bare `ValueError`

## ccf_runtime.cli.commands.skill_import.MAX_REFERENCE_BYTES

- Surface: ccf_runtime.cli.commands.skill_import.MAX_REFERENCE_BYTES
- Public surface: true
- Change type: added
- Before: absent — `reference.read_text()` was unbounded
- After: `1_048_576`, the per-file ceiling the containment helper enforces
- Why: a skill package exists to be distributed, which makes it untrusted input,
  and an unbounded read of untrusted input is a resource hazard independent of
  what the bytes turn out to be. Public so an operator can see the ceiling they
  are held to
- Migration: none below the ceiling; a package above it is refused

## ccf_runtime.cli.commands.skill_import.MAX_REFERENCES

- Surface: ccf_runtime.cli.commands.skill_import.MAX_REFERENCES
- Public surface: true
- Change type: added
- Before: absent — one import registered as many prompt artifacts as the
  directory held
- After: `64`, the per-import ceiling on registered reference artifacts
- Why: the same reason as the byte ceiling, one level up — the count was as
  unbounded as the size was
- Migration: none below the ceiling

## runtime/ccf_runtime/cli/commands/skill_import.py

- Surface: runtime/ccf_runtime/cli/commands/skill_import.py
- Public surface: false
- Change type: behavior
- Before: `references.iterdir()` filtered on `reference.is_file()`, which
  **follows symlinks**, and `SKILL.md` was read the same way. No `resolve()`, no
  `is_symlink()`, no containment check and no ceiling anywhere in the module
- After: every read goes through one containment helper that refuses a symlink
  outright, refuses a path resolving outside the package, refuses anything that
  is not a regular file, and refuses a file over the byte ceiling; the reference
  count is checked before any read
- Why: `SEC-003`, and it chains. A shared package carrying
  `references/usage.md -> ~/.aws/credentials` had those bytes registered as a
  prompt artifact, where `GET /config/resolution` — unauthorized, `SEC-002`,
  still open on this branch — served them to any caller. The most complete
  exfiltration path the review found. A symlink is refused rather than
  resolved-and-allowed because a link inside a *distributed* package has no
  legitimate meaning on the importing machine, and refusing is the only answer
  that does not depend on where the link points
- Migration: a package that wants a file's contents ships the file

## Regression evidence

`tests/cli/test_skill_import.py`: five refusals — a symlinked reference
(asserting the secret's bytes appear in no output and no reference artifact
reaches the registry), a symlinked `SKILL.md`, a reference symlinked at a target
*inside* the package, an oversized reference, and too many references — each
with the ordinary package as a live control in the same module.

**Sabotage-verified.** Severing the symlink refusal alone reddens nothing,
because containment catches the review's case (its target sits outside the
package); that is why the inside-the-package symlink test exists, and it is what
proves the symlink refusal is load-bearing rather than shadowed. The containment
check is a **backstop that cannot currently fail** — given the symlink refusal
and `iterdir` yielding only direct children, nothing reachable trips it — and it
says so in its own docstring rather than being left to read as independent
evidence.
