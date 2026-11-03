# CCF Data Preparation Reference

This document describes the sample knowledge-graph data prepared for the Context Fabric / CCF SDK work. It is intended to be referenced from `CLAUDE.md` when extending sample data across backends.

**Scope of this document:** data model, files produced, ontology sources, instance data content, and how the same dataset was mirrored across stores.  
**Out of scope:** installation or operations of Fluree, MongoDB, Neo4j, or PostgreSQL.

---

## Purpose

Primary goal of the first version of the graph:

- Support a **context fabric** that agents can query for KYC, client relationships, regulatory-style reporting, and related financial-services questions.
- Prefer **public industry ontology semantics** (FIBO) for classes and relationships.
- Start with a **small, curated FIBO subset** plus **synthetic instance data** (clients, counterparties, UBOs, LEIs, addresses).
- Keep the same logical dataset available on multiple backends so agent adapters can be compared.

Ledger / logical dataset name used throughout: `fibo:main` (Fluree). Mongo / Neo4j / Postgres mirrors use the same instance URIs and relationship types.

---



## Ontology source (not invented IRIs)

Instance data is **synthetic**. Class and property IRIs follow the **Financial Industry Business Ontology (FIBO)** published by the EDM Council / OMG.


| Aspect                  | Detail                                                                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Standard                | FIBO (Financial Industry Business Ontology)                                                                                            |
| Publisher               | EDM Council / Object Management Group                                                                                                  |
| Reference site          | [https://spec.edmcouncil.org/fibo/](https://spec.edmcouncil.org/fibo/)                                                                 |
| Source repo (community) | [https://github.com/edmcouncil/fibo](https://github.com/edmcouncil/fibo)                                                               |
| How it was used here    | **Hand-curated small subset** written as Turtle with official FIBO namespace IRIs—not a bulk import of Production/Quickstart ZIP files |




### Namespaces used in the starter ontology


| Prefix (local)      | Namespace                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------- |
| `fibo-fnd-rel-rel`  | `https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/`                      |
| `fibo-fnd-pty-pty`  | `https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/`                          |
| `fibo-fnd-aap-agt`  | `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/Agents/`                   |
| `fibo-fnd-law-lcap` | `https://spec.edmcouncil.org/fibo/ontology/FND/Law/LegalCapacity/`                        |
| `fibo-be-le-lp`     | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/`                |
| `fibo-be-le-fbo`    | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/FormalBusinessOrganizations/` |
| `fibo-be-corp-corp` | `https://spec.edmcouncil.org/fibo/ontology/BE/Corporations/Corporations/`                 |
| `fibo-be-oac-cown`  | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Ownership/`             |
| `fibo-be-oac-cctl`  | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Control/`               |




### Classes declared in the starter set

- `fibo-fnd-aap-agt:Agent`
- `fibo-fnd-pty-pty:Party` (subClassOf Agent)
- `fibo-be-le-lp:LegalEntity` (subClassOf Party)
- `fibo-be-le-fbo:FormalOrganization` (subClassOf LegalEntity)
- `fibo-be-corp-corp:Corporation` (subClassOf FormalOrganization)



### Properties declared in the starter set

- `fibo-fnd-rel-rel:hasIdentity` / `isIdentifiedBy` (inverses)
- `fibo-be-oac-cown:hasOwnershipInterestIn` (domain Party, range LegalEntity)
- `fibo-be-oac-cctl:hasControllingInterestIn` (subPropertyOf hasOwnershipInterestIn)
- `fibo-fnd-pty-pty:isRelatedTo` (Party ↔ Party)

**Note:** Fluree was used without OWL reasoning by default. Queries for `Party` therefore return only entities **explicitly** typed as `Party`, not every `Corporation`, even though the subclass axioms exist in the loaded ontology.

---



## Instance data source

All **clients, counterparties, persons, LEIs, addresses, dates, risk ratings, and KYC fields are synthetic**. They were authored for adapter and agent testing, not extracted from GLEIF, company registries, or other public entity feeds.


| Field category                                            | Source                                         |
| --------------------------------------------------------- | ---------------------------------------------- |
| Entity names (Acme, Beta Holdings, Gamma Bank, etc.)      | Made up                                        |
| LEI-like strings                                          | Made up (20-character alphanumeric style only) |
| Addresses                                                 | Made up                                        |
| UBOs / directors / ownership percents                     | Made up                                        |
| `clientType`, `riskRating`, `kycStatus`, onboarding dates | Made up                                        |
| FIBO type and ownership/control predicates                | Official FIBO IRIs (see above)                 |
| Application namespace for instances                       | `http://example.org/fibo/` (`ex:`)             |


Optional later direction discussed in project setup (not loaded as bulk public data in this prep): GLEIF LEI public data for real legal entities.

---



## Files produced (data and transform artifacts)

Paths below are relative to the working directory used during prep (typically `~/fibo_files` on the development host). Recreate or copy these into the Claude Code project as needed.

### Ontology and instance Turtle (loaded into Fluree `fibo:main`)


| File                        | Role                                                                                                                                          |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `fibo-starter.ttl`          | Curated FIBO class/property subset (TBox-style)                                                                                               |
| `fibo-sample-data.ttl`      | First small instance set (Acme, Beta, John Smith, Jane Doe, one related-to edge)                                                              |
| `fibo-realistic-sample.ttl` | Expanded entities: more corps, persons, addresses, LEIs, KYC-ish attributes                                                                   |
| `fibo-agent-data.ttl`       | Agent-oriented load: clients, counterparties, UBOs, risk/KYC fields, relationship mesh (supersedes/overlaps earlier samples when re-inserted) |




### Export and Mongo intermediate files


| File                       | Role                                                                         |
| -------------------------- | ---------------------------------------------------------------------------- |
| `fibo-export.json`         | Early SPARQL SELECT dump; mostly ontology labels (less useful for instances) |
| `fibo-instances.json`      | SPARQL SELECT of triples with subject under `http://example.org/fibo/`       |
| `mongo-entities.json`      | JSONL entity documents for Mongo (and as intermediate for other loaders)     |
| `mongo-relationships.json` | JSONL relationship documents                                                 |




### Transform and load scripts


| File                  | Role                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `fluree_to_mongo.py`  | Parses `fibo-instances.json` → `mongo-entities.json` + `mongo-relationships.json` (expands compact IRIs, maps predicates) |
| `load_mongo.py`       | Loads JSONL into MongoDB database `fibo`, collections `entities` and `relationships`                                      |
| `load_neo4j.py`       | Loads same JSONL into Neo4j as `:KGEntity` nodes and typed relationships                                                  |
| `load_postgres.py`    | Loads same JSONL into PostgreSQL tables `entities` and `relationships`                                                    |
| `compare_backends.py` | Runs the same logical ownership query on Fluree, MongoDB, Neo4j, and PostgreSQL; prints tables and a presence matrix      |


---



## Logical data content (what was loaded)



### Corporations / organizations (synthetic)


| Local id                            | Label                        | Role in sample                                   |
| ----------------------------------- | ---------------------------- | ------------------------------------------------ |
| `ex:AcmeCorp`                       | Acme Corporation             | Corporate client; controlled/owned by John Smith |
| `ex:BetaHoldings`                   | Beta Holdings LLC            | Investment vehicle; owned by Jane Doe            |
| `ex:GammaBank`                      | Gamma Bank AG                | FI counterparty; linked to Hans Müller           |
| `ex:DeltaFund`                      | Delta Private Equity Fund LP | Fund / investor; LP interest Sarah Chen          |
| `ex:OmegaSecurities`                | Omega Securities Ltd         | Broker / counterparty                            |
| `ex:SearchDemo1` / `ex:SearchDemo2` | Full-text demo labels        | Optional search demos (if loaded)                |


Typical attributes on org instances (application properties under `ex:`):  
`lei`, `legalName`, `jurisdiction`, `entityStatus`, `clientType`, `riskRating`, `kycStatus`, `onboardingDate`.

### Natural persons / parties (synthetic)


| Local id         | Label       | Relationships                            |
| ---------------- | ----------- | ---------------------------------------- |
| `ex:JohnSmith`   | John Smith  | Ownership + controlling interest in Acme |
| `ex:JaneDoe`     | Jane Doe    | Ownership in Beta Holdings               |
| `ex:HansMueller` | Hans Müller | Ownership in Gamma Bank                  |
| `ex:SarahChen`   | Sarah Chen  | Ownership in Delta Fund                  |


Typical person attributes: `fullName`, `nationality`, `dateOfBirth`, `role`, `ownershipPercent`.

### Relationship types mirrored everywhere


| Logical type  | FIBO / app predicate                        | Neo4j type (in loader)        |
| ------------- | ------------------------------------------- | ----------------------------- |
| Ownership     | `fibo-be-oac-cown:hasOwnershipInterestIn`   | `HAS_OWNERSHIP_INTEREST_IN`   |
| Control       | `fibo-be-oac-cctl:hasControllingInterestIn` | `HAS_CONTROLLING_INTEREST_IN` |
| Related party | `fibo-fnd-pty-pty:isRelatedTo`              | `IS_RELATED_TO`               |




### Approximate counts after agent-oriented load + transform

- **~14** entity documents in Mongo JSONL (includes corps, parties, and any extra typed nodes captured from instance triples)
- **~11** relationship edges in Mongo JSONL

Exact counts depend on which Turtle files were inserted and whether search-demo nodes were included.

---



## Backend representations of the same data

No install steps—only how the **same logical graph** was shaped in each store after loaders ran.

### Fluree

- Ledger: `fibo:main`
- Model: RDF triples (Turtle inserts; SPARQL query with `FROM <fibo:main>`)
- Instance URI base: `http://example.org/fibo/`



### MongoDB

- Database: `fibo`
- Collections:
  - `entities`: one document per instance; `_id` / `id` = full URI; `types[]`, `label`, LEI/KYC fields, `source`
  - `relationships`: `_id`, `from`, `to`, `type` (`hasOwnershipInterestIn` | `hasControllingInterestIn` | `isRelatedTo`), `source`



### Neo4j

- Nodes: `:KGEntity` plus extra labels from `types` (e.g. `:Corporation`, `:Party`)
- Properties: `id` (URI), `name` (short local name), `label`, LEI/KYC fields, etc.
- Relationships: `HAS_OWNERSHIP_INTEREST_IN`, `HAS_CONTROLLING_INTEREST_IN`, `IS_RELATED_TO`



### PostgreSQL

- Database used in prep: `parkavedb` (user-specific); tables created inside that database:
  - `entities`: `id` PK (URI text), `name`, `label`, `types` text[], LEI/KYC columns, `attrs` jsonb, `source`
  - `relationships`: `id`, `from_id`, `to_id`, `type`, `source` (FKs to `entities.id`)

---



## Common query interface (designed for CCF adapters)

Abstract backend API proposed for agent-facing code (not all methods implemented as a package in-repo during this prep):

- `get_entity(entity_id)`
- `search_by_label(text, limit=20)`
- `search_by_lei(lei)`
- `list_entities(entity_type=None, client_type=None, risk_rating=None, limit=50)`
- `list_counterparties(limit=50)`
- `get_owners(entity_id)`
- `get_owned_entities(party_id)`
- `get_related(entity_id)`
- `ownership_chain(party_id)`

Normalized entity shape for adapters:

```json
{
  "id": "http://example.org/fibo/AcmeCorp",
  "label": "Acme Corporation",
  "types": ["Corporation"],
  "lei": "...",
  "legalName": "...",
  "jurisdiction": "...",
  "clientType": "...",
  "riskRating": "...",
  "kycStatus": "...",
  "source": "fluree|mongo|neo4j|postgres"
}
```

Ownership-style result shape:

```json
{
  "from": { "id": "...", "label": "John Smith" },
  "to": { "id": "...", "label": "Acme Corporation" },
  "type": "hasOwnershipInterestIn"
}
```

`compare_backends.py` implements one concrete cross-store check: **ownership pairs** (`owner label` → `company label`) on all four backends.

---



## Suggested agent test questions (same intent across backends)

- Who has ownership or controlling interest in Acme Corporation?
- List corporations and their LEIs / jurisdictions.
- List counterparties (clientType containing counterparty / financial institution / broker).
- Show ownership for John Smith / Jane Doe / Hans Müller / Sarah Chen.
- Clients with Medium risk rating and Approved KYC status.
- Entities related to Acme via `isRelatedTo`.

---



## Guidance for extending sample data (Claude Code / CCF SDK)

When adding more sample data for the emerging CCF SDK:

1. **Keep FIBO IRIs** for types and core relationship predicates; put application attributes under `http://example.org/fibo/` (or a project-specific namespace) unless mapping to real FIBO properties.
2. **Prefer synthetic instances** unless explicitly ingesting a named public dataset (e.g. GLEIF); document the source in this file if that changes.
3. **Add data in Turtle** (or JSON-LD) against the same URI scheme, then re-export instances → regenerate `mongo-entities.json` / `mongo-relationships.json` → reload Mongo / Neo4j / Postgres so all backends stay aligned.
4. **Update this document** with new entity tables, file names, and counts when the sample set grows.
5. **Do not assume OWL inference** across backends; type entities explicitly for each role you need to query (e.g. both `Corporation` and any app-level tags you filter on).

---



## Explicitly not done in this prep

- Full FIBO Production or official Quickstart TTL bulk load
- Live GLEIF or other public registry ingest
- Production-grade identity resolution or golden-record merging
- Enabling Fluree MCP end-to-end in the IDE (discussed; data prep completed independently)
- Packaging a full `context_fabric` Python package with all adapters (interface designed; Mongo/Fluree/Neo4j/Postgres loaders and compare script exist as scripts)

---



## Changelog (prep session)


| Item          | Notes                                                                         |
| ------------- | ----------------------------------------------------------------------------- |
| Fluree ledger | `fibo:main` created and populated with starter ontology + synthetic instances |
| Ontology      | Small curated FIBO Foundations / Business Entities subset                     |
| Instances     | Synthetic KYC-oriented graph under `http://example.org/fibo/`                 |
| Mirrors       | MongoDB `fibo`, Neo4j KGEntity graph, PostgreSQL tables in `parkavedb`        |
| Validation    | Ownership query compared across four backends via `compare_backends.py`       |


*Document generated from the CCF / FIBO Fluree data-prep conversation for reuse in Claude Code projects via* `CLAUDE.md`*.*