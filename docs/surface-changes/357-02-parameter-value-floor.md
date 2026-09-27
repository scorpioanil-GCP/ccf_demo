# 357-02 — the parameter-value floor: `PARAMETER_VALUE_FLOOR_V1` and its roster

`D-IMPL-357` item 7, ruled 2026-09-27, option (a). Wave 1, task R1. A **second**
named, **separately versioned** mechanism grammar beside `SUBJECT_FLOOR_V1` —
not a widening of the first. `refuse_floor` keeps judging `request.subject`
against the subject floor and now judges every **declared** `string` parameter,
at every declared depth (`parent`, `parent.member`, `parent[]`,
`parent[].member`), against this one.

The three names published here are `PARAMETER_VALUE_FLOOR_V1` (the compiled
grammar), `PARAMETER_VALUE_FLOOR_VERSION` (its version marker, which rides in
every refusal `detail` the floor decides) and `PARAMETER_VALUE_FLOOR_EXCLUSIONS`
(the named roster of what it is required to keep refusing, each with a sample
that exercises it).

## ccf.products.request.PARAMETER_VALUE_FLOOR_V1

- Surface: ccf.products.request.PARAMETER_VALUE_FLOOR_V1
- Public surface: true
- Change type: added
- Before: absent — a declared `string` parameter was judged by `SUBJECT_FLOOR_V1`, the ADDRESS grammar, which forbids a space
- After: `Final[re.Pattern[str]]` — `re.compile(r"^(?=.{1,512}\Z)[A-Za-z0-9][A-Za-z0-9:/._~@+=-]*(?: [A-Za-z0-9:/._~@+=-]+)*\Z")`, the SDK-owned parameter-VALUE floor: ASCII letters and digits, plus `:` `/` `.` `_` `~` `@` `+` `=` `-` after the first character, plus **one ordinary INTERIOR space**, to a cap of **512 code points**. The first character must be alphanumeric. **Leading, trailing and doubled space are refused**, because a value differing from another only by invisible padding reads as equal to a human while hashing differently — a governance and replay hazard rather than an injection one. Anchored with `\Z`, like the subject floor, so an adopter copying the printed grammar and applying it with `re.match` cannot admit a value carrying an injected trailing newline.
- Why: `SUBJECT_FLOOR_V1` is an ADDRESS grammar and stays one — its documented safe position is a SPARQL IRI `<…>`, and SPARQL 1.1's `IRIREF` production excludes `#x20` while admitting `:` and `=`, which is why a space may never enter a subject and why "a space is no worse than the `:` already admitted" is wrong on the grammar. A declared `string` PARAMETER is a value, not an address: `Term Loan` is an ordinary one. Two roles need two grammars, and the second is an ALLOWLIST so a character nobody considered is refused by default rather than admitted by omission.
- Migration: none for a subject — the subject floor is **unchanged**, still forbids a space, and still decides `request.subject`. A declared `string` PARAMETER is now judged by this grammar instead of the address grammar, which is strictly WIDER for parameters (every character the subject floor admits, this floor admits — asserted over the class, not over samples), so no request that was admitted before is refused now. **Do not paste this pattern into an `ArgumentDomain(pattern=…)`**: that registration is refused by the SDK's own grammar shape guard, which fails closed on a repeat inside a look-around, and the refusal is correct — this floor already runs on every governed request, so re-declaring it narrows nothing. Declare a narrowing that expresses your own identifier rule instead; a declared `pattern` may narrow and can never widen past this floor, because the floor is judged first.

## ccf.products.request.PARAMETER_VALUE_FLOOR_VERSION

- Surface: ccf.products.request.PARAMETER_VALUE_FLOOR_VERSION
- Public surface: true
- Change type: added
- Before: absent
- After: `Final[str] = "PARAMETER_VALUE_FLOOR_V1"`
- Why: the grammar is versioned by name, like the subject floor; a future tightening or widening is a NEW name, never an edit to this pattern, and the name rides in every refusal this floor decides (`detail`) so a record says which grammar judged it
- Migration: none; new name. A consumer that classifies refusals by the deciding grammar reads this marker out of `ProductRequestViolation.detail` rather than re-deriving it from the key.

## ccf.products.request.PARAMETER_VALUE_FLOOR_EXCLUSIONS

- Surface: ccf.products.request.PARAMETER_VALUE_FLOOR_EXCLUSIONS
- Public surface: true
- Change type: added
- Before: absent
- After: `Final[Mapping[str, str]]` — a read-only mapping of 38 named exclusions to a sample that exercises each: the quote and escape characters (`'`, `"`, `\`, `` ` ``), the tokens that are structural in SQL, SPARQL or both (`;` `,` `(` `)` `|` `^` `{` `}` `[` `]`), the tokens that are structural in an IRI or URI (`<` `>` `%` `#` `?` `&`), the control and format characters (LF, CR, TAB, NUL, DEL, a C1 control, U+200B, U+FEFF, U+00A0, U+2028), the padding shapes (leading, trailing and doubled space, space-only, empty), and the out-of-bounds cases (over the 512 cap, non-ASCII, an em dash)
- Why: the ruling was to name the exact lexical exclusions rather than leave structural IRI/SPARQL tokens as prose, so a control can certify each one by name. The roster is a module constant and not a list retyped in a test, so the control cannot drift from the class that implements it.
- Migration: none; new name. The roster is a floor on what the grammar refuses, not a complete denylist — the grammar is an allowlist and refuses everything outside it, whether or not the roster names it.

## The exact semantic boundary, and the residuals

**What passing this floor means, exactly**: the text is *lexically admissible as
a governed string parameter*. It does **not** mean the value is safe for
arbitrary SQL, SPARQL, an IRI, a shell, or any other sink. Sink safety remains
the typed or bound sink contract's responsibility. A character class also cannot
establish safety against a **multi-character** construct: `-` is admitted, so
the SQL comment sequence `--` is admitted, and this floor does not claim
otherwise. The refusal `detail` this floor emits states that boundary verbatim,
so the promise an adopter reads is no wider than the one implemented.

**The adopter population is wider than what this admits, and that is recorded
rather than glossed.** The close census measured exactly two refused values in
the committed examples, and **two values are not the adopter population**.
Ordinary banking labels this floor still refuses include `Tier 1 (CET1)`
(parentheses), `Standard & Poor's` (ampersand and apostrophe), `25%` (percent),
`Moody's, Inc.` (apostrophe and comma), and any non-ASCII name — `Cafe` written
with an accent, for instance. Each is refused **deliberately**: parentheses,
comma and semicolon are structural in SQL and SPARQL; `%` enables
encode-smashing; `&` and `#` delimit in a URI; the apostrophe is a quote
character. Each is a **named residual held for a later ruling**, not an
oversight, and the ruling of record for this release is: interior space only;
leading, trailing and doubled space refused; the residuals stay named rather
than widened.
