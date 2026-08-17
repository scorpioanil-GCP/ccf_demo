# 17-12 — `binding.yaml` as a data-only document, with one named exception

`D-IMPL-141` was **rejected as proposed** and is now RESOLVED (Dave,
2026-08-16). The entry that stood PROPOSED had `binding.yaml` carry `resolver:`
and `question:` as `<module-path>:<attribute>` factories the loader imports and
calls; that shape reintroduces producer Python into a deployment directory and
was declined. The ruling of record is
`docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md`,
Amendment A.

## What did **not** change, stated first

- **The document is still not a Control Plane artifact.** Not registered, not
  content-hashed, no `semver`, and it still never reaches Decision Replay
  dimension 2. That posture is unchanged and is what lets connection material
  live here at all.
- **Path containment is unchanged in rule and strengthened in reach.** Still the
  two-check rule `ManifestEntry` holds a manifest to — the written check refuses
  an absolute path and a `..` segment, the resolved check refuses a plain name
  that is a symlink out. It now applies to `artifact_store` and to the rooted
  `connection` form as well as to `config`.
- **The strict-loader posture is unchanged.** An unknown top-level key is still
  refused by name rather than ignored.
- **`load_reference` is unchanged in behaviour.** Same per-root module naming,
  same `sys.path` window, same four refusals. Only its docstring and the key it
  is reached for moved.
- **`GovernedResolver` is untouched.** No field gained a default, no argument
  changed. Wiring the reference debt scorer as a *default* remains `17-13`'s
  work; this plan passes it explicitly.
- **`ProductClient`, `Result`, `WireRequest`, `WireOutcome` and the refusal
  envelope are untouched.** The client surface did not move.

## ccf.client.adapters.binding_document.REQUIRED_KEYS

- Surface: ccf.client.adapters.binding_document.REQUIRED_KEYS
- Public surface: true
- Change type: removed
- Before: `("config", "resolver", "question")` — three required keys, two of
  them `<module-path>:<attribute>` factory references
- After: absent. Replaced by `DATA_KEYS` and `REFERENCE_KEYS`, which are
  separate constants because the distinction between *data* and *the one
  permitted reference* is the whole ruling. A single `REQUIRED_KEYS` tuple would
  have made the exception invisible at the constant that defines the schema
- Why: `D-IMPL-141`'s rejection removed `resolver:` and turned `question:` into
  a data mapping, so the tuple named nothing that still exists
- Migration: a caller enumerating required keys reads `(*DATA_KEYS,
  *REFERENCE_KEYS)`. `tests/client/test_binding_document.py` does exactly that,
  so a new required key cannot arrive without an absence-refusal test covering it

## ccf.client.adapters.binding_document.DATA_KEYS

- Surface: ccf.client.adapters.binding_document.DATA_KEYS
- Public surface: true
- Change type: added
- Before: absent
- After: the thirteen keys a binding document states as data — `config`,
  `question`, `perspective`, `product_class_key`, `request_contract_key`,
  `operator_parameter_keys`, `policy_bundle_key`, `replay_record_class`,
  `query_pin_class`, `max_ttl_seconds`, `product_ttl_seconds`,
  `artifact_store`, `debt`. All required
- Why: spec §3 measured that the request vocabulary and the perspective are
  data — `Perspective` is two plain strings, `subject`/`intent`/`freshness` are
  plain `str` — so the factories that used to produce them were factories
  producing constants
- Migration: a deployment on the rejected shape moves its resolver factory's
  arguments into the document verbatim and deletes the factory

## ccf.client.adapters.binding_document.REFERENCE_KEYS

- Surface: ccf.client.adapters.binding_document.REFERENCE_KEYS
- Public surface: true
- Change type: added
- Before: absent
- After: `("plan",)` — a **one-element** tuple naming the single permitted
  `<module-path>:<attribute>` reference, the deployment's projection
- Why: Amendment A.3 grants exactly one Python module and A.4 requires the
  loader to refuse any other reference by name. The tuple is one element on
  purpose: granting a second exception becomes a visible edit to a named
  constant that a reviewer can see, rather than a widened condition inside a
  branch. `tests/client/test_binding_document.py` asserts its length
- Migration: none for a conforming deployment. A deployment wanting a second
  reference does not get one; that is the point

## ccf.client.adapters.binding_document.RULED_OUT_KEYS

- Surface: ccf.client.adapters.binding_document.RULED_OUT_KEYS
- Public surface: true
- Change type: added
- Before: absent. A removed key would have fallen through to the unknown-key
  refusal
- After: a mapping from a rejected key to what to do instead — `resolver` and
  `connection_factory` today — refused **before** the unknown-key check, with a
  message that says the key was *ruled out* and cites the spec
- Why: an unknown key and a ruled-out key are different mistakes with different
  remedies. Told *"not a binding-document key"*, an author of the rejected
  `D-IMPL-141` shape re-spells it and tries again; told *"ruled out"* with the
  ruling named, they read it
- Migration: delete the key. The message names the replacement

## ccf.client.adapters.binding_document.looks_like_a_reference

- Surface: ccf.client.adapters.binding_document.looks_like_a_reference
- Public surface: true
- Change type: added
- Before: absent. Nothing checked whether a *value* was reference-shaped; only
  key names were policed
- After: a predicate returning `True` for a value naming a `.py` module path, a
  colon and a non-empty attribute. The loader walks every data position —
  recursively, so nested mappings and sequences are covered — and refuses any
  match, naming the dotted position
- Why: **this is the half of the narrowing that key-name refusal cannot
  reach.** A reference smuggled through a key the schema *does* permit would
  widen the exception with no decision recorded anywhere, which is exactly the
  precedent Amendment A.4 forbids. The shape checked is *names a Python file*
  rather than *contains a colon*, because a declared `asked_at` carries three
  colons and is data — the narrow predicate is what makes the check usable
  rather than a source of false refusals
- Migration: none. A conforming document has one reference and it is under
  `plan:`

## ccf.client.adapters.binding_document.QuestionDeclaration

- Surface: ccf.client.adapters.binding_document.QuestionDeclaration
- Public surface: true
- Change type: added
- Before: absent. The question arrived from a deployment factory as a
  `ResolverCall`
- After: a frozen, keyword-only dataclass carrying `subject`, `intent`,
  `freshness` and `asked_at`, parsed from the document. `asked_at` is refused
  unless it is a zoned ISO 8601 instant — a zone-less instant is a silent
  default (`D-IMPL-38`), and which zone it silently meant is the difference
  between two different answers
- Why: the deployment's answer to `D-04`'s *"`as_of=None` means the server's
  decision instant"* is a value, not a computation
- Migration: move the three tokens and the default instant out of the question
  factory and into `question:`

## ccf.client.adapters.binding_document.DebtDeclaration

- Surface: ccf.client.adapters.binding_document.DebtDeclaration
- Public surface: true
- Change type: added
- Before: absent. Every deployment wrote its own debt scorer; the client fixture
  carried a 55-line one
- After: a frozen, keyword-only dataclass carrying `half_life_key`,
  `debt_profile_key`, and the `completeness` and `semantic_consistency` this
  deployment **declares**. The declared values are `Decimal`, parsed from
  strings and never through a `float`
- Why: `17-11` shipped `AssemblyDebtScorer` but measured that the SDK has no
  reference scorer for `C` or `S`, so the values stay the deployment's. Declared
  through `DeclaredFactor`, they land in replay under their own scorer pin
  (`D-IMPL-47`), so an examiner can tell an assertion from a measurement without
  reading code. A library default would be `D-IMPL-38`'s *a value nobody chose*
  landing inside a delivered product's content address
- Migration: a deployment that measures `C` or `S` supplies its own conforming
  scorer through its own resolver; this document's declared values are the
  no-measurement path

## ccf.client.adapters.binding_document.BindingDocument

- Surface: ccf.client.adapters.binding_document.BindingDocument
- Public surface: true
- Change type: reshaped
- Before: `root`, `config`, `resolver: str`, `question: str`, `connection: str |
  None` — three reference strings and one path
- After: `root`, `config`, `plan: str` (the one reference), `question:
  QuestionDeclaration`, `perspective: Perspective`, the eight resolver data
  fields, `artifact_store: Path`, `debt: DebtDeclaration`, `connection:
  Mapping[str, object] | None` (already composed, paths already contained)
- Why: the document changed from *three pointers at deployment code* to *the
  data the SDK builds a resolver from, plus one pointer at a projection*
- Migration: `document.resolver` and `document.question` no longer exist.
  Callers that loaded the resolver factory now read the fields directly; the SDK
  builds the resolver

## ccf.client.adapters.binding_document.ResolverCall

- Surface: ccf.client.adapters.binding_document.ResolverCall
- Public surface: true
- Change type: removed
- Before: a frozen dataclass carrying the `Perspective` and `ProductRequest` a
  deployment's question factory returned
- After: absent. The adapter builds the `ProductRequest` from the document's
  declared question and reads the `Perspective` off the document
- Why: there is no question factory any more, so there is no factory return
  value to type
- Migration: none for a client developer — this type never appeared in the
  client's own surface

## ccf.client.adapters.binding_document.QuestionFactoryProtocol

- Surface: ccf.client.adapters.binding_document.QuestionFactoryProtocol
- Public surface: true
- Change type: removed
- Before: a `@runtime_checkable` Protocol describing the deployment callable
  that turned a client's question into a `ResolverCall`
- After: absent
- Why: `question:` is data. A Protocol describing how a deployment computes
  three strings and two more strings describes a computation that does not
  happen
- Migration: delete the factory; state its values in `question:` and
  `perspective:`

## ccf.client.adapters.binding_document.conforming_resolver

- Surface: ccf.client.adapters.binding_document.conforming_resolver
- Public surface: true
- Change type: removed
- Before: refused a resolver factory whose product did not satisfy
  `ServedProductResolverProtocol`
- After: absent, replaced by `conforming_plan_factory`
- Why: the SDK builds the resolver, so there is no deployment-returned resolver
  to structurally check. The check moved to the one thing a deployment still
  hands over as code
- Migration: none. A deployment substituting a whole resolver does so by not
  using the in-process adapter's binding-document path

## ccf.client.adapters.binding_document.conforming_plan_factory

- Surface: ccf.client.adapters.binding_document.conforming_plan_factory
- Public surface: true
- Change type: added
- Before: absent
- After: refuses a `plan:` reference that does not satisfy
  `ProjectionPlanFactoryProtocol`, which is `@runtime_checkable` and therefore a
  real structural check rather than a comment
- Why: `plan:` is the **single** thing a deployment may hand the SDK as code, so
  it is also the single thing worth verifying is the code it claimed
- Migration: none

## ccf.client.adapters.inprocess.InProcessAdapter

- Surface: ccf.client.adapters.inprocess.InProcessAdapter
- Public surface: true
- Change type: reshaped
- Before: booted, then called the deployment's `resolver` factory and its
  `question` factory, and passed whatever the latter returned straight to the
  former
- After: boots, resolves the one `plan:` reference, and **builds
  `GovernedResolver` itself** from the document's data — selecting `17-11`'s
  `AssemblyDebtScorer` (with `DeclaredFactor` for `C` and `S` at the declared
  values) and the file-backed `ArtifactStore`, because `artifact_store:`
  declares a path and a path is what a file-backed store takes. The typed
  `ProductRequest` is assembled per question from the declared vocabulary, with
  `schema_version` read off the registered product class rather than restated
- Why: `D-IMPL-141`'s ruling. The deployment supplies the projection and
  nothing else
- Migration: a deployment on the rejected shape deletes its resolver factory,
  its question factory, its connection factory and its debt scorer, and keeps
  its projection. The client's own API is unchanged — `ProductClient.for_product`
  and `ask` are byte-identical, and the binding address is unchanged
- Note: this composition is the thing `17-13` is expected to lift into a
  `build_governed_resolver(...)` helper, so a second transport does not grow a
  second copy of it. It lives in the adapter today because there is exactly one
  transport today
