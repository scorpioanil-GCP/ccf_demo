# The deployment manifest

The deployment manifest is the one document naming what a deployment puts in
force: every artifact, the graph adapter, the credential references, and — per
entry — whether the artifact is registered and pinned or merely loaded. It is
itself a versioned, content-hashable artifact, so *"what was this deployment
configured to put in force"* is answerable by reading one thing.

Everything on this page is reached through the wiring package, `ccf.deployment`.

## The day-1 import

**Import from `ccf.deployment`. Do not import from its submodules.**

```py
from ccf.deployment import load_and_boot
```

`ccf.deployment.__all__` carries sixteen names — the boot entry point, the
boot result, the operator-registry builder, the binder refusal, the manifest
contracts, the pin records, and the artifact-class resolution helpers. All
sixteen are importable from the package. The dotted module paths beneath it —
`ccf.deployment.manifest`, `ccf.deployment.classes`, `ccf.deployment.pins`,
`ccf.deployment.operators`, `ccf.deployment.binder` — are **implementation
detail**, not a second published spelling of the same thing.

The convention earns a page because its absence cost something measurable. The
SDK's generated surface record lists every public name at its fully-qualified
module path, so a package that re-exports a name lists it twice: once at
`ccf.deployment.X` and once at `ccf.deployment.<submodule>.X`. Read as a
migration note, one release's additions then read as roughly twice as many new
concepts as were actually added. Naming one preferred spelling is what makes the
count mean what a reader assumes it means.

**Be precise about what the convention does not claim.** `ccf.deployment` is the
**wiring** surface — how a deployment is assembled, not how it runs. A day-1
path legitimately imports from `ccf.projection`, `ccf.products`, `ccf.replay`
and `ccf.controlplane` as well, and each of those packages has its own top-level
surface. This is a spelling rule for one package, not an instruction to collapse
the API into a single module.

::: ccf.deployment.load_and_boot

::: ccf.deployment.BootedFabric

## `role` governs registration and pinning, never visibility

Every manifest entry declares a `role`, and it is required with no default.
`register` puts the artifact into the Control Plane registry and into the pin
set; `load` parses and validates it and hands it back, without registering it
and without pinning it. The distinction is a replay boundary rather than a
convenience: registering an artifact content-hashes it into Control Plane state,
and the registered artifact set is dimension 2 of the five-dimension Decision
Replay record.

The subtlety that has to be stated in full, because half of it misleads: a
`role: load` artifact **is** returned to the caller on `BootedFabric.artifacts`,
keyed by its manifest key, exactly as a `role: register` one is — **and** it is
still absent from `pins`, still absent from the Control Plane registry, and
still absent from replay dimension 2. `artifacts` is a parse result handed back
to the caller; `pins` is the record of what was put in force. Reading the first
sentence alone gives an adopter a `load` artifact that looks registered because
it is reachable, which is exactly the wrong model — reachability is not
registration, and `role` never governed visibility in the first place.

The practical consequence is that an adopter needing a parsed artifact in hand —
operator-parameters documents to feed a registry builder, say — names its own
manifest keys against `booted.artifacts`, which is explicit deployment
configuration, rather than filtering the Control Plane registry by type.

## `registration` names a governance path

Every entry also declares `registration`, and it is likewise required with no
default: `typed` or `versioned`. It names which of the Control Plane's two
registration paths the entry travels — the plain typed registration, or the
versioned one with its hash-verified bump check.

The refusal that fires here is worth stating exactly, because it is narrower
than it first sounds. A manifest **may** name any of the SDK's six
author-versioned classes, as `registration: versioned`; the boot path then
registers them through the versioned route with its bump check. What is refused
is declaring `registration: typed` for such a class, because the typed route
runs no bump check and the author's own version claim would go unheld.

That refusal is class-wide rather than role-scoped: it runs over `role: load`
entries too, so a `load` entry naming an author-versioned class must still say
`versioned`, describing a path it will not travel. A check with an exemption is
a default wearing a different name, and a role-conditional one would let an
entry be admitted under `load` and then discover its registration mode was wrong
after a one-word edit to `register`.

Separately, the `ccf.` class-id prefix is **reserved**: a manifest entry naming a
`ccf.`-prefixed class id the SDK does not ship is refused at load, before any
document is read. Without the reservation, any document carrying the right three
top-level keys could register and pin under an SDK class name.

## The manifest contracts

::: ccf.controlplane.artifacts.DeploymentManifest

::: ccf.controlplane.artifacts.ManifestEntry

::: ccf.controlplane.artifacts.SecretReference

## Naming the graph adapter

`backend` is a **name only**. There is no connection field of any kind: a
connection string is a deployment *environment* value, and putting one into a
versioned, content-hashed document would persist it into the audit plane. The
manifest names the adapter; the caller supplies that adapter's own settings at
boot, and the two are reconciled loudly at load.

The field's pattern — `^[a-z][a-z0-9_]*$` — is a **shape** rule only. Which
names actually exist is not a property of a document; it is a property of the
deployment that parses it, so membership is checked at load against the adapter
registry's `declared_names()`. The field carried a fixed six-name enumeration
until the registry seam landed; a hard-coded list could only ever say what
someone had typed, while the registry says what is installed — third-party
adapters included. The cost is one-directional and accepted: a typo is caught at
load rather than at parse, and the exported schema no longer completes the field
in an editor. `ccf backends list` answers the question the enumeration used to.

`backend_secrets` names credentials **by reference**: each entry pairs an
adapter config field with the environment variable holding its value, and the
value never appears in the document. Each config field may be satisfied by
exactly one reference. See
[manage keys and secrets](../../how-to/security-and-deployment.md) for the
deployment side, [storage and Context Graph Protocols](../protocols/storage-and-graph.md)
for the registry surface, and
[write a graph backend adapter](../../how-to/write-a-graph-backend-adapter.md)
for the adapter author's side of the same boundary.
