# Source Model & Provenance Rules

## Repository roles

### `drcastillo/ccf` — conceptual and whitepaper authority

Primary source for:

- CCF conceptual model and narrative;
- Context Product concepts;
- CCF architecture and enterprise-integration content;
- whitepaper source Markdown;
- Mermaid diagrams;
- static figures and graphics;
- published whitepaper lineage and release artifacts.

**Preferred reuse order:** structured Markdown / Mermaid / source graphics first; published PDF second. The PDF is a released snapshot and validation artifact, not the preferred extraction surface when structured source already exists.

### `drcastillo/obsidian-vault` — financial-services use-case authority

Primary source for:

- use cases extracted and developed from the CCF body of work;
- the business/decision problem a Context Product must solve;
- context-product requirements and prerequisites;
- the shape of realistic financial-services scenarios;
- data characteristics required to demonstrate those scenarios.

### `drcastillo/ccf_dataprep` — example-data authority

Primary source for:

- public-data acquisition used for CCF examples;
- engineered datasets;
- loaders and generators;
- synthetic or derived relationships/linkages;
- source provenance;
- database population and validation logic;
- the realistic data estate used by SDK examples.

### `drcastillo/ccf_code` — SDK behavior authority

Primary source for:

- SDK implementation;
- public API and configuration surface;
- executable behavior;
- tests;
- example implementations;
- SDK-facing documentation that is directly validated by code.

When prose and executable behavior disagree, the disagreement must be surfaced. The adoption project must not silently choose one interpretation and present it as settled.

### `drcastillo/ccf_adoption` — adoption and distribution authority

Primary source for:

- learning paths;
- portal navigation and information architecture;
- tutorials and adoption-oriented explanations;
- SDK reference material derived from authoritative source repositories;
- financial-services walkthroughs;
- reproducibility guidance;
- security/assurance presentation;
- adoption checklists and release artifacts.

It is **not** authoritative for upstream SDK behavior or whitepaper semantics.

## Claim-level source priority

| Claim type | Preferred authority |
|---|---|
| CCF purpose / conceptual architecture | `ccf` structured source |
| Published whitepaper version | `ccf` release artifact + provenance |
| Financial-services use-case requirement | `obsidian-vault` |
| Dataset/source/relationship construction | `ccf_dataprep` |
| SDK API or runtime behavior | `ccf_code` implementation + tests |
| Example behavior | `ccf_code` executable example + tests |
| Adoption explanation / learning sequence | `ccf_adoption`, grounded in the above |
| Vulnerability assessment | assessment artifact/version approved for publication |

## Evidence lineage

For substantial financial-services examples, prefer a visible lineage of:

```text
CCF concept / whitepaper
        ↓
Vault use-case requirement
        ↓
ccf_dataprep source + engineered estate
        ↓
ccf_code executable example + tests
        ↓
ccf_adoption learning / walkthrough artifact
```

Not every page requires all five layers, but the portal should preserve enough provenance that a reader can move from an adoption claim back to authoritative evidence.

## Asset reuse rules

1. Reuse existing `ccf` Markdown, Mermaid, and graphics when they remain accurate and improve the adoption experience.
2. Do not edit the upstream artifact in its source repository.
3. If an asset is copied into `ccf_adoption`, retain a provenance record containing source repository, source path, and source commit or blob when practical.
4. If a copied graphic or diagram is materially adapted, mark it as **adapted from** the source rather than presenting it as byte-identical.
5. Prefer re-rendering Mermaid from source when styling needs to change, rather than editing a rendered PNG as if it were source.
6. Avoid extracting diagrams from the PDF when the same diagram exists as Mermaid or a source figure.
7. Avoid recreating a graphic with generative imagery when an authoritative source asset already communicates the concept adequately.

## Whitepaper handling

The current whitepaper in `ccf_adoption/01-whitepaper/` is a versioned distribution snapshot. Its authoritative development source remains `drcastillo/ccf`.

The adoption site may quote, summarize, reinterpret, or visually reuse the whitepaper's structured source to improve learning, but it must not imply that the adoption copy is the authoring source.

## Conflict handling

When sources disagree materially:

1. Record the conflict.
2. Identify the source/version/commit on each side.
3. Determine whether it is a stale-prose issue, implementation defect, example defect, data issue, unresolved architectural decision, or publication lag.
4. Stop the affected claim or artifact at the nearest checkpoint if the conflict changes meaning or correctness.
5. Escalate for architecture-owner decision when no authoritative resolution exists.
6. Never silently normalize competing values or wording.

## Source freshness

Each major phase should record the source commits used for its inventory or validation. Before final release, refresh the source inventory and identify material drift since the phase snapshots.

## Public-web material

External public sources may support explanatory or comparative material when needed, but they do not supersede the four project source repositories for CCF-specific claims. Any external material that becomes load-bearing must be cited and reviewed at the relevant checkpoint.
