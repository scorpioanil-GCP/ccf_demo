# 15-10 — the deployment manifest and the load-validate-register-boot entry point

Plan 15-10 replaces the hand-written registration prologue that preceded every
`boot()` call — fourteen lines in `examples/00-quickstart` producing four pins —
with one call over one content-hashable document.

**`boot()` itself is unchanged and remains directly callable.** `git diff
src/ccf/boot.py` is empty for this plan. D-14 is additive: what changes is what
*produces* the pins, never what `boot` requires of them. Every existing call site
keeps working, and a deployment that prefers to wire by hand still can.

The migration, in one place, for the quickstart shape:

```python
# before
registry = ControlPlaneRegistry()
spec_version = registry.register(keys["resolution_spec"], _resolution_spec(ontology))
policy_version = registry.register(keys["policy_bundle"], control["policy_bundle"])
table = parse_artifact(halflife["half_life_table"], HALF_LIFE_TABLE)
profile = parse_artifact(halflife["debt_profile"], DEBT_PROFILE)
assert isinstance(table, HalfLifeTable)
assert isinstance(profile, DebtProfile)
registry.register(keys["half_life_table"], table)
registry.register(keys["debt_profile"], profile)
handle = boot(
    database_path=root / "quickstart.sqlite3",
    registry=registry,
    resolution_spec_key=keys["resolution_spec"],
    resolution_spec_version=spec_version,
    policy_bundle_key=keys["policy_bundle"],
    policy_bundle_version=policy_version,
)

# after
booted = load_and_boot(
    root / "manifest.yaml",
    registry=ControlPlaneRegistry(),
    database_path=str(root / "quickstart.sqlite3"),
)
```

Three things the `after` deliberately does **not** absorb: it does not execute
operators, does not run the three validation gates, and does not build a
product's lineage record. The adopter reads `booted.pins` and passes them to
`build_replay_record` itself, because D-06 requires that line to stay in adopter
code — the moment the SDK selects which bindings are in force, dimension 2 of
the Decision Replay record is assembled by a rule nobody in the deployment wrote
down. `tests/products/test_gate_independence.py` and the
`cinv02-deployment-gates` lint rule hold that line; this plan does not weaken
either.

## ccf.controlplane.artifacts.ManifestEntry

- Surface: ccf.controlplane.artifacts.ManifestEntry
- Public surface: true
- Change type: added
- Before: absent — a deployment's artifact set existed only as a sequence of
  hand-written `register`/`register_typed` calls in example code, so "what is in
  force here" was answerable only by reading a script
- After: a contract declaring `path`, `key`, `class_id`, and
  `role: Literal["register", "load"]`, with a `field_validator` refusing any
  path containing `*`, `?`, or `[`
- Why: **`role` is D-IMPL-80 (RESOLVED 2026-08-04, Dave) and it is required with
  no default.** `register` puts the artifact into the Control Plane registry and
  into the pin set; `load` parses and validates it through the same seam and
  hands it back to the caller, but never registers and never pins it. The
  distinction exists because registering an artifact content-hashes it into
  Control Plane state, and by D-06's own rationale the registered artifact set
  is dimension 2 of the five-dimension Decision Replay record (whitepaper
  §7.10.1) — so registering a signal batch would make re-authoring an events
  file change "what was in force" exactly as a policy-bundle bump does. Events
  are what the fabric *observed*; the Control Plane is what it was *permitted to
  do*. The field has **no default** because either default would have the SDK
  deciding that boundary on the adopter's behalf, which is the objection
  `boot()` already raises against every other default (D-IMPL-38). Globs are
  refused for the same replay reason: a pattern would make what was in force a
  function of directory contents at boot time, recorded by no artifact
  (T-15-10-01)
- Migration: enumerate every artifact, one entry each, and state `role` on every
  one — an entry omitting it is a parse failure. Name `ccf.signal-batch` with
  `role: load`; `role: register` on that class is refused outright

## ccf.controlplane.artifacts.DeploymentManifest

- Surface: ccf.controlplane.artifacts.DeploymentManifest
- Public surface: true
- Change type: added
- Before: absent
- After: a `VersionedArtifact` declaring `artifacts: tuple[ManifestEntry, ...]`
  with `min_length=1`, `backend: Literal["sqlite", "postgres"]`,
  `resolution_spec_key`, `policy_bundle_key`, and an optional `tenant_id`, plus
  two `model_validator`s — one refusing duplicate keys, one refusing a manifest
  whose two boot pins do not name `role: register` entries
- Why: the manifest is itself a content-hashable artifact, so "what did this
  deployment put in force" is one versioned answer rather than a directory
  listing. **The backend is a kind only (D-08)** — there is no DSN field and no
  database-path field, because a connection string is an environment value that
  `boot()` already documents as never persisted, and a versioned content-hashed
  artifact is exactly where it must not land (T-15-10-05). **Duplicate keys are
  refused (C-9)** because two entries sharing a key make `version_for(key)`
  ambiguous and the boot result's `artifacts[key]` order-dependent, and both
  feed replay; duplicate *paths* under distinct keys are permitted deliberately,
  since one document may legitimately be in force under two names. **`tenant_id`
  is optional (Q3)** because D-IMPL-05 makes tenancy a first-class runtime axis
  and a manifest-pinned tenant would stop one manifest serving a multi-tenant
  deployment — exactly one of the manifest and the caller must supply it, and
  both-absent and a conflicting pair are each refused rather than resolved by
  precedence
- Migration: author one `manifest.yaml` per deployment. The document root
  carries the artifact's own `semver` lane, as every other artifact class does;
  entry paths resolve relative to the manifest file's own directory, never the
  process's working directory

## ccf.controlplane.artifacts.DEPLOYMENT_MANIFEST

- Surface: ccf.controlplane.artifacts.DEPLOYMENT_MANIFEST
- Public surface: true
- Change type: added
- Before: absent
- After: `ArtifactClass(class_id="ccf.deployment-manifest", contract=DeploymentManifest)`,
  registered in `ccf.deployment.classes.SDK_ARTIFACT_CLASSES`
- Why: the manifest is parsed through the same `load_artifact` seam as every
  artifact it names, so it gets the same float refusal, the same zone-less
  timestamp refusal, and the same D-02 timestamp-resolver suppression rather
  than a second parsing path with its own rules
- Migration: none — `load_and_boot` resolves the class itself

## ccf.controlplane.artifacts.ArtifactRole

- Surface: ccf.controlplane.artifacts.ArtifactRole
- Public surface: true
- Change type: added
- Before: absent
- After: `Literal["register", "load"]`, the type of `ManifestEntry.role`
- Why: named rather than inlined so that `SDK_ARTIFACT_ROLES` and
  `refuse_role_the_sdk_fixes` type against the same two values the contract
  accepts. D-IMPL-80 is enforced in two places and a drift between them is the
  failure mode worth designing out
- Migration: none

## ccf.deployment.ManifestEntry

- Surface: ccf.deployment.ManifestEntry
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: the manifest contracts are defined in `ccf.controlplane.artifacts`
  alongside every other artifact contract, but they are read and written by
  adopters as *deployment* wiring. Re-exporting means an adopter imports one
  package. They live where they do rather than in `ccf.deployment.manifest`
  because `artifacts -> deployment.manifest -> deployment.classes -> artifacts`
  closes an import cycle at import time — the same class of constraint 15-07
  recorded for `artifact_base.py`
- Migration: none — both import paths resolve

## ccf.deployment.DeploymentManifest

- Surface: ccf.deployment.DeploymentManifest
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: as `ccf.deployment.ManifestEntry` above
- Migration: none — both import paths resolve

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: added
- Before: absent — every deployment hand-wrote its registration prologue and
  then called `boot()` with pins it had collected itself
- After: `load_and_boot(manifest_path, *, registry, database_path=None,
  postgres_dsn=None, tenant_id=None) -> BootedFabric`
- Why: four properties, each of which the hand-written prologue could lose
  silently.
  **Preflight before registration.** The tenant resolution, the D-IMPL-80 role
  check, and the declared-backend-versus-supplied-argument check all run before
  any artifact document is read. A manifest declaring `postgres` with no DSN
  *parses* perfectly well, so a backend check placed beside the `boot` call
  would register every artifact and fail afterwards — leaving Control Plane
  state from a fabric that never booted, which is a replay-integrity problem
  rather than an untidiness (T-15-10-02; raised by cross-AI review against the
  plan's step ordering and verified real).
  **Two-phase parse-then-register.** Every document is parsed before any is
  registered, so a malformed document at entry seven leaves the registry
  untouched instead of half-populated (T-15-10-08). A failure *inside* the
  registration loop can still leave earlier entries registered; that is accepted
  and documented rather than rolled back, because registration is
  content-addressed and audited, so a corrected re-run registers identical
  content to identical versions and the audit log shows both attempts — a
  Control Plane that silently un-registers is worse than one that records a
  retry.
  **No `resolve_latest`, ever.** Its absence from the module is asserted; that
  is the "latest" `boot()` refuses (T-15-10-04).
  **No registry constructed here.** The Control Plane is a caller argument, so
  the adopter keeps one audit sequence; a registry built behind the adopter's
  back would split it in two (whitepaper §7.8.2)
- Migration: replace the registration prologue and the `boot()` call with one
  `load_and_boot`. Supply exactly the connection argument the manifest's
  declared backend needs — supplying the other one, or neither, is refused.
  The returned handle's disposal contract is unchanged: `booted.handle.close()`,
  or `with booted.handle:`. One call is easy to put in a loop over manifests or
  tenants, and a loop that never closes leaks a connection per iteration and
  will eventually be refused a boot by the single-writer check

## ccf.deployment.load_and_boot

- Surface: ccf.deployment.load_and_boot
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: the package root is the import an adopter reaches for
- Migration: none — both import paths resolve

## ccf.deployment.manifest.BootedFabric

- Surface: ccf.deployment.manifest.BootedFabric
- Public surface: true
- Change type: added
- Before: absent — `boot()` returned a bare `FabricHandle` and the caller kept
  its pins in local variables
- After: a frozen dataclass with exactly four attributes: `handle: FabricHandle`,
  `pins: ResolvedPins`, `tenant_id: str`, and
  `artifacts: Mapping[str, CCFContract]`
- Why: a dataclass rather than a `CCFContract` because it carries a live handle,
  which has no canonical serialization and never belongs in a content hash —
  the reasoning `ArtifactClass` already records. **`artifacts` carries both
  roles; `pins` carries `register` only.** `artifacts` is D-IMPL-80's return
  path: the ruling requires `role: load` entries to come back to the caller
  rather than being registered, and returning the register-role ones alongside
  them costs nothing and closes a second gap — without it, an adopter needing
  the parsed operator-parameters artifacts would re-read them off disk or
  `isinstance`-filter them out of the registry, and that filtering idiom copied
  across nine examples is a new duplication class of exactly the sort this phase
  exists to remove. `role` governs registration and pinning, **never
  visibility**: a `role: load` artifact appearing in `artifacts` is still absent
  from `pins`, from the registry, and from replay dimension 2
- Migration: `booted.handle` is the old return value; `booted.pins` replaces the
  local version variables; `booted.artifacts[key]` replaces re-reading a
  document. Keep the MAX_TTL and product-class registrations in adopter code —
  the TTL pin must stay an independently authored registration or Gate 3
  compares a ceiling against itself

## ccf.deployment.BootedFabric

- Surface: ccf.deployment.BootedFabric
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: returned by `load_and_boot`, so it is imported from the same place
- Migration: none — both import paths resolve

## ccf.deployment.pins.ResolvedPins

- Surface: ccf.deployment.pins.ResolvedPins
- Public surface: true
- Change type: added
- Before: absent — pins lived as loose local variables named `spec_version`,
  `policy_version`, and so on
- After: a contract carrying `entries: tuple[ArtifactPin, ...]` and **exactly
  one** public method, `version_for(key) -> str`
- Why: the constraint is the design. A convenience like
  `pins.policy_bindings()` would shorten the adopter's
  `build_replay_record(policy_bindings=...)` line while moving the *selection*
  of which bindings are in force out of the deployment's code and into the SDK —
  a governance-boundary move wearing an ergonomics costume, and dimension 2 of
  the replay record then assembled by a rule nobody wrote down. `version_for` is
  **lookup**, not selection: the caller already knows the key it wants. The
  record carries `role: register` entries only (D-IMPL-80), so `version_for`
  raising for a `role: load` key is correct behavior rather than a lookup bug —
  a load-role artifact has no version because nothing registered it. A test pins
  the public method set exactly, so a later convenience fails CI rather than
  landing quietly
- Migration: replace the loose version variables with
  `booted.pins.version_for(key)`, naming the manifest key

## ccf.deployment.ResolvedPins

- Surface: ccf.deployment.ResolvedPins
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: reached through `booted.pins`, so it is imported from the same place
- Migration: none — both import paths resolve

## ccf.deployment.pins.ArtifactPin

- Surface: ccf.deployment.pins.ArtifactPin
- Public surface: true
- Change type: added
- Before: absent
- After: a contract carrying `key`, `version`, and `class_id`
- Why: `version` is what `register_typed` returned — a content hash (D-IMPL-26)
  — so pin identity *is* content identity, which is what makes two loads of one
  manifest produce a byte-identical pin set. `class_id` is carried so a reader
  of the pin set can say what kind of thing was in force without re-resolving it
- Migration: none — constructed by `load_and_boot`

## ccf.deployment.ArtifactPin

- Surface: ccf.deployment.ArtifactPin
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: as its siblings
- Migration: none — both import paths resolve

## ccf.deployment.pins.UnpinnedArtifactError

- Surface: ccf.deployment.pins.UnpinnedArtifactError
- Public surface: true
- Change type: added
- Before: absent
- After: a `LookupError` raised by `version_for` when no pin answers to a key
- Why: raised rather than returning `None`, on the registry's own
  no-silent-default posture (D-IMPL-38): a caller reaching for a pin has already
  decided it needs one, and a value nobody chose would push the failure to
  whatever reads the version next. The message names the key, because the two
  situations that raise it — key absent from the manifest, and key present under
  `role: load` — need to be distinguishable at the point of failure
- Migration: none, unless catching it

## ccf.deployment.UnpinnedArtifactError

- Surface: ccf.deployment.UnpinnedArtifactError
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: as its siblings
- Migration: none — both import paths resolve

## ccf.deployment.classes.SDK_ARTIFACT_ROLES

- Surface: ccf.deployment.classes.SDK_ARTIFACT_ROLES
- Public surface: true
- Change type: added
- Before: absent — D-IMPL-80 was defended by docstrings on `SignalBatch` and
  `SIGNAL_BATCH` and a comment in `SDK_ARTIFACT_CLASSES`, all of which a
  manifest author can simply not read
- After: `dict[str, ArtifactRole]` mapping a class id to the role the SDK
  **fixes** for it. Exactly one entry today: `ccf.signal-batch -> "load"`
- Why: 15-09 recorded that nothing yet *prevented* an adopter writing
  `role: register` against `ccf.signal-batch`, and that no CI failure would
  fire — leaving the ruling enforced by prose. This is the machine-checkable
  half: the required `role` field stops the choice being made silently, and
  this mapping stops it being made wrongly for the one class where the SDK
  knows the answer. It lives beside the class registry because the fact is a
  property of the *class*, not of any manifest. **Every class absent from the
  mapping is the adopter's call, and that is the default** — the SDK fixes a
  role only where it can say why (T-15-10-07)
- Migration: none, unless a manifest declared `role: register` against
  `ccf.signal-batch`, which is now refused before anything is registered

## ccf.deployment.SDK_ARTIFACT_ROLES

- Surface: ccf.deployment.SDK_ARTIFACT_ROLES
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: as its siblings
- Migration: none — both import paths resolve

## ccf.deployment.classes.refuse_role_the_sdk_fixes

- Surface: ccf.deployment.classes.refuse_role_the_sdk_fixes
- Public surface: true
- Change type: added
- Before: absent
- After: `refuse_role_the_sdk_fixes(class_id, role) -> None`, raising
  `ValueError` when the declared role contradicts `SDK_ARTIFACT_ROLES`
- Why: the check runs in `load_and_boot`'s preflight, before any document is
  read and before anything is registered, so a manifest that would have put raw
  event data into replay dimension 2 never gets far enough to register anything
  at all. It is a function rather than a `ManifestEntry` validator because the
  contract lives in `ccf.controlplane.artifacts`, which cannot import
  `ccf.deployment` without closing an import cycle. It **refuses rather than
  corrects**: silently rewriting the entry would leave the manifest saying one
  thing and the deployment doing another, and the manifest is the document the
  audit plane reads back
- Migration: none — called by `load_and_boot`

## ccf.deployment.refuse_role_the_sdk_fixes

- Surface: ccf.deployment.refuse_role_the_sdk_fixes
- Public surface: true
- Change type: added
- Before: absent
- After: re-exported at the `ccf.deployment` package root
- Why: as its siblings
- Migration: none — both import paths resolve
