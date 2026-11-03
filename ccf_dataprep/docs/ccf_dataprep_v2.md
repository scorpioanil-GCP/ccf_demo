# CCF Data Preparation Reference

This document describes the sample knowledge-graph data prepared for the Context Fabric / CCF SDK work. It is intended to be referenced from `CLAUDE.md` when extending sample data across backends.

**Scope of this document:** data model, files produced, ontology sources, instance data content, and how the same dataset was mirrored across stores.  
**Out of scope:** installation or operations of Fluree, MongoDB, Neo4j, or PostgreSQL.

---

## Status — read before using this as guidance

This document is an accurate record of the **completed first-version prep**. Two of its design choices were **superseded on 2026-08-16** by decisions recorded in `CLAUDE.md`. The historical sections below are left as written; the supersessions are:

| Superseded | Now |
|---|---|
| All identifiers synthetic, including LEI-like strings | **Real GLEIF LEIs for public anchor obligors.** Invented entities keep synthetic identifiers, in a visibly distinct format so the two can never be confused. Instance URIs stay under `http://example.org/fibo/`; the real LEI lives in the `lei` attribute, not in the URI. |
| One logical dataset **mirrored** to every backend | Each store is **authoritative for a different slice** (Fluree: relationships, temporal, lineage, policy binding · Postgres: entities, policy reference · MongoDB: document text and passage spans · SQLite: departmental). Duplicating an element into a store that does not own it is now a defect. |

**What is not superseded and remains binding:** the *Canonical FIBO IRI binding* section, the `ex:` application-predicate namespace, the instance URI pattern, and the no-OWL-inference caveat. Those are a shared contract with downstream consumers.

The existing cast — Acme, Beta Holdings, Gamma Bank, Delta Fund, Omega Securities, John Smith, Jane Doe, Hans Müller, Sarah Chen — is **retained** as the synthetic overlay alongside real public anchors.

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



## Canonical FIBO IRI binding (SDK dependency)

FIBO documentation and module names do **not** by themselves pin a single compact local name to a queryable IRI. Sample Turtle, SPARQL, Mongo relationship `type` strings, Neo4j relationship types, and CCF adapters must share one **explicit binding table**.

This section is the contract for the sample dataset and for the CCF SDK. Prefer the **Full IRI** column in code and queries; use **Local name** only as a short label in docs or UI.

### 🔴 The entire v1 starter set below is INVALID — see `known-issues.md` §0.2

**Found 2026-08-17.** All ten starter bindings in the two tables that follow
resolve to nothing. **FIBO factored its foundational vocabulary out into the OMG
Commons Ontology Library**, and four properties were invented outright.

| Recorded below | Correct binding |
| --- | --- |
| `fibo-fnd-aap-agt:Agent` | `cmns-pts:Agent` — `https://www.omg.org/spec/Commons/PartiesAndSituations/Agent` |
| `fibo-fnd-pty-pty:Party` | `cmns-pts:Party` — `https://www.omg.org/spec/Commons/PartiesAndSituations/Party` |
| `fibo-be-le-lp:LegalEntity` | `cmns-org:LegalEntity` — `https://www.omg.org/spec/Commons/Organizations/LegalEntity` |
| `fibo-be-le-fbo:FormalOrganization` | `cmns-org:FormalOrganization` — `https://www.omg.org/spec/Commons/Organizations/FormalOrganization` |
| `fibo-be-corp-corp:Corporation` | `fibo-be-le-cb:Corporation` — `.../BE/LegalEntities/CorporateBodies/Corporation` |
| `fibo-fnd-rel-rel:isIdentifiedBy` | `cmns-id:isIdentifiedBy` — `https://www.omg.org/spec/Commons/Identifiers/isIdentifiedBy` |
| `fibo-fnd-rel-rel:hasIdentity` | **absent** — no equivalent |
| `fibo-fnd-pty-pty:isRelatedTo` | **absent** — no relatedness equivalent; model under `ex:` |
| `hasOwnershipInterestIn` | **absent** — corrected to `fibo-fnd-oac-own:owns` (§0.1, done) |
| `hasControllingInterestIn` | **absent** — corrected to `fibo-fnd-rel-rel:controls` (§0.1, done) |

**The class corrections are NOT yet applied to the loaded data.** 1,500 type
assertions across 500 entities still use the invalid class IRIs. The tables below
are retained verbatim so the defect stays legible against what was loaded — read
them as *what the estate currently holds*, not as the contract.

A corrected mirror article was sent to the vault custodian through the agent
exchange (`~/.agent-exchange/ccf-dataprep/`) and applied there on 2026-08-17.

---

### Class bindings (loaded ontology) — ⚠️ INVALID, see above


| Local name         | Prefix form                         | Full IRI                                                                                                    |
| ------------------ | ----------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Agent              | `fibo-fnd-aap-agt:Agent`            | `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/Agents/Agent`                                |
| Party              | `fibo-fnd-pty-pty:Party`            | `https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/Party`                                       |
| LegalEntity        | `fibo-be-le-lp:LegalEntity`         | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity`                       |
| FormalOrganization | `fibo-be-le-fbo:FormalOrganization` | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/FormalBusinessOrganizations/FormalOrganization` |
| Corporation        | `fibo-be-corp-corp:Corporation`     | `https://spec.edmcouncil.org/fibo/ontology/BE/Corporations/Corporations/Corporation`                        |




### Object-property bindings (loaded ontology)


| Local name               | Prefix form                                 | Full IRI                                                                                            | Notes                                                 |
| ------------------------ | ------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| hasIdentity              | `fibo-fnd-rel-rel:hasIdentity`              | `https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/hasIdentity`                     | Declared; little instance use in sample               |
| isIdentifiedBy           | `fibo-fnd-rel-rel:isIdentifiedBy`           | `https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/isIdentifiedBy`                  | Inverse of hasIdentity                                |
| hasOwnershipInterestIn   | `fibo-be-oac-cown:hasOwnershipInterestIn`   | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn` | Primary ownership edge in samples                     |
| hasControllingInterestIn | `fibo-be-oac-cctl:hasControllingInterestIn` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Control/hasControllingInterestIn` | Control edge; subPropertyOf ownership in starter TBox |
| isRelatedTo              | `fibo-fnd-pty-pty:isRelatedTo`              | `https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/isRelatedTo`                         | Party–party relatedness                               |




### Wave 0 extension — Loans, Guaranty, Syndication, Collateral, Credit Events

**Added 2026-08-16.** Verified term-by-term against a shallow clone of `edmcouncil/fibo` at `master`, cross-checked against the published Production modules at `spec.edmcouncil.org`. Every IRI below was read out of the source RDF, not inferred from a module name.

**Three terms are not where the Context Product specs imply.** The specs name FIBO *modules*; module membership does not pin an IRI, and in these cases it actively misleads:

| Term | Specs imply | **Actually lives in** |
| --- | --- | --- |
| `CreditFacility` | Loans (`LOAN`) | **`FBC/DebtAndEquities/Debt/`** |
| `SyndicatedLoan` | Loans (`LOAN`) | **`SEC/Debt/DistributedLoans/`** |
| `Guaranty` | Loans (`LOAN`) | **`FBC/DebtAndEquities/Guaranty/`** |

Binding any of these under `LOAN/` yields an IRI that resolves to nothing.

#### Prefixes added

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-fbc-dae-dbt` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Debt/` |
| `fibo-fbc-dae-gty` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Guaranty/` |
| `fibo-fbc-dae-cre` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/CreditEvents/` |
| `fibo-sec-dbt-dln` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/` |
| `fibo-loan-ln-ln` | `https://spec.edmcouncil.org/fibo/ontology/LOAN/LoansGeneral/Loans/` |
| `fibo-loan-spc-cln` | `https://spec.edmcouncil.org/fibo/ontology/LOAN/LoansSpecific/CommercialLoans/` |
| `fibo-fnd-agr-ctr` | `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/` |
| `fibo-be-fct-fct` | `https://spec.edmcouncil.org/fibo/ontology/BE/FunctionalEntities/FunctionalEntities/` |

#### Class bindings added

| Local name | Prefix form | Full IRI | Needed by |
| --- | --- | --- | --- |
| CreditFacility | `fibo-fbc-dae-dbt:CreditFacility` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Debt/CreditFacility` | facility-terms-snapshot |
| CommittedCreditFacility | `fibo-fbc-dae-dbt:CommittedCreditFacility` | `.../FBC/DebtAndEquities/Debt/CommittedCreditFacility` | facility-terms-snapshot |
| UncommittedCreditFacility | `fibo-fbc-dae-dbt:UncommittedCreditFacility` | `.../FBC/DebtAndEquities/Debt/UncommittedCreditFacility` | facility-terms-snapshot |
| RevolvingLineOfCredit | `fibo-fbc-dae-dbt:RevolvingLineOfCredit` | `.../FBC/DebtAndEquities/Debt/RevolvingLineOfCredit` | facility type = revolver |
| SubFacility | `fibo-fbc-dae-dbt:SubFacility` | `.../FBC/DebtAndEquities/Debt/SubFacility` | tranche structure |
| DebtTerms | `fibo-fbc-dae-dbt:DebtTerms` | `.../FBC/DebtAndEquities/Debt/DebtTerms` | facility terms |
| Collateral | `fibo-fbc-dae-dbt:Collateral` | `.../FBC/DebtAndEquities/Debt/Collateral` | collateral-and-setoff-coverage |
| PhysicalCollateral | `fibo-fbc-dae-dbt:PhysicalCollateral` | `.../FBC/DebtAndEquities/Debt/PhysicalCollateral` | collateral-and-setoff-coverage |
| NonPhysicalCollateral | `fibo-fbc-dae-dbt:NonPhysicalCollateral` | `.../FBC/DebtAndEquities/Debt/NonPhysicalCollateral` | collateral-and-setoff-coverage |
| Loan | `fibo-loan-ln-ln:Loan` | `https://spec.edmcouncil.org/fibo/ontology/LOAN/LoansGeneral/Loans/Loan` | base loan type |
| SecuredLoan | `fibo-loan-ln-ln:SecuredLoan` | `.../LOAN/LoansGeneral/Loans/SecuredLoan` | |
| UnsecuredLoan | `fibo-loan-ln-ln:UnsecuredLoan` | `.../LOAN/LoansGeneral/Loans/UnsecuredLoan` | |
| CollateralizedLoan | `fibo-loan-ln-ln:CollateralizedLoan` | `.../LOAN/LoansGeneral/Loans/CollateralizedLoan` | |
| GuaranteedLoan | `fibo-loan-ln-ln:GuaranteedLoan` | `.../LOAN/LoansGeneral/Loans/GuaranteedLoan` | credit-exposure-rollup |
| LenderLienPosition | `fibo-loan-ln-ln:LenderLienPosition` | `.../LOAN/LoansGeneral/Loans/LenderLienPosition` | collateral priority |
| PrimaryLienPosition | `fibo-loan-ln-ln:PrimaryLienPosition` | `.../LOAN/LoansGeneral/Loans/PrimaryLienPosition` | **named individual, not a class** — a value of `LenderLienPosition`. "first position in the order of seniority in which the law recognizes lenders' claims against a property". Wave 15 |
| SubordinateLienPosition | `fibo-loan-ln-ln:SubordinateLienPosition` | `.../LOAN/LoansGeneral/Loans/SubordinateLienPosition` | **named individual, not a class** — "secondary or lower position in the order of seniority". Wave 15. Do not confuse with `fibo-sec-dbt-dbti:isSubordinatedTo` (tranche payment priority) or `fibo-fnd-agr-ctr:isSubordinateTo` (a document cross-reference) — three different subordination ideas, one letter apart |
| CommercialLoan | `fibo-loan-spc-cln:CommercialLoan` | `.../LOAN/LoansSpecific/CommercialLoans/CommercialLoan` | |
| Guaranty | `fibo-fbc-dae-gty:Guaranty` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Guaranty/Guaranty` | guarantee edges |
| Guarantor | `fibo-fbc-dae-gty:Guarantor` | `.../FBC/DebtAndEquities/Guaranty/Guarantor` | guarantor schedule |
| JointGuaranty | `fibo-fbc-dae-gty:JointGuaranty` | `.../FBC/DebtAndEquities/Guaranty/JointGuaranty` | |
| NegativePledge | `fibo-fbc-dae-gty:NegativePledge` | `.../FBC/DebtAndEquities/Guaranty/NegativePledge` | a *negative covenant* with a real FIBO term |
| LetterOfCredit | `fibo-fbc-dae-gty:LetterOfCredit` | `.../FBC/DebtAndEquities/Guaranty/LetterOfCredit` | |
| CrossDefaultProvision | `fibo-fbc-dae-cre:CrossDefaultProvision` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/CreditEvents/CrossDefaultProvision` | cross-default edges |
| DefaultEvent | `fibo-fbc-dae-cre:DefaultEvent` | `.../FBC/DebtAndEquities/CreditEvents/DefaultEvent` | 8-K Item 2.04 events |
| CreditEvent | `fibo-fbc-dae-cre:CreditEvent` | `.../FBC/DebtAndEquities/CreditEvents/CreditEvent` | |
| FailureToPay | `fibo-fbc-dae-cre:FailureToPay` | `.../FBC/DebtAndEquities/CreditEvents/FailureToPay` | |
| Bankruptcy | `fibo-fbc-dae-cre:Bankruptcy` | `.../FBC/DebtAndEquities/CreditEvents/Bankruptcy` | |
| SyndicatedLoan | `fibo-sec-dbt-dln:SyndicatedLoan` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/SyndicatedLoan` | syndicated-lending-co-lender |
| FinanceSyndicate | `fibo-sec-dbt-dln:FinanceSyndicate` | `.../SEC/Debt/DistributedLoans/FinanceSyndicate` | syndicate structure |
| FinanceSyndicateMember | `fibo-sec-dbt-dln:FinanceSyndicateMember` | `.../SEC/Debt/DistributedLoans/FinanceSyndicateMember` | syndicate-participant-in |
| AdministrativeAgent | `fibo-sec-dbt-dln:AdministrativeAgent` | `.../SEC/Debt/DistributedLoans/AdministrativeAgent` | EX-10 preamble party |
| LeadArranger | `fibo-sec-dbt-dln:LeadArranger` | `.../SEC/Debt/DistributedLoans/LeadArranger` | |
| SyndicationAgent | `fibo-sec-dbt-dln:SyndicationAgent` | `.../SEC/Debt/DistributedLoans/SyndicationAgent` | |
| LoanParticipationNote | `fibo-sec-dbt-dln:LoanParticipationNote` | `.../SEC/Debt/DistributedLoans/LoanParticipationNote` | |
| BreachOfCovenant | `fibo-fnd-agr-ctr:BreachOfCovenant` | `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/BreachOfCovenant` | covenant breach events |
| CollateralAgreement | `fibo-fnd-agr-ctr:CollateralAgreement` | `.../FND/Agreements/Contracts/CollateralAgreement` | |
| NettingProvision | `fibo-fnd-agr-ctr:NettingProvision` | `.../FND/Agreements/Contracts/NettingProvision` | set-off / netting |
| CloseOutNettingProvision | `fibo-fnd-agr-ctr:CloseOutNettingProvision` | `.../FND/Agreements/Contracts/CloseOutNettingProvision` | |
| ContractualCommitment | `fibo-fnd-agr-ctr:ContractualCommitment` | `.../FND/Agreements/Contracts/ContractualCommitment` | |

#### Object-property bindings added

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| hasBorrower | `fibo-fbc-dae-dbt:hasBorrower` | `.../FBC/DebtAndEquities/Debt/hasBorrower` |
| hasLender | `fibo-fbc-dae-dbt:hasLender` | `.../FBC/DebtAndEquities/Debt/hasLender` |
| isCollateralizedBy | `fibo-fbc-dae-dbt:isCollateralizedBy` | `.../FBC/DebtAndEquities/Debt/isCollateralizedBy` |
| isCollateralizationOf | `fibo-fbc-dae-dbt:isCollateralizationOf` | `.../FBC/DebtAndEquities/Debt/isCollateralizationOf` |
| hasMaturityDate | `fibo-fbc-dae-dbt:hasMaturityDate` | `.../FBC/DebtAndEquities/Debt/hasMaturityDate` |
| hasPrincipal | `fibo-fbc-dae-dbt:hasPrincipal` | `.../FBC/DebtAndEquities/Debt/hasPrincipal` |
| isGuaranteedBy | `fibo-fbc-dae-gty:isGuaranteedBy` | `.../FBC/DebtAndEquities/Guaranty/isGuaranteedBy` |
| hasGuarantor | `fibo-fbc-dae-gty:hasGuarantor` | `.../FBC/DebtAndEquities/Guaranty/hasGuarantor` |
| isGuarantorOf | `fibo-fbc-dae-gty:isGuarantorOf` | `.../FBC/DebtAndEquities/Guaranty/isGuarantorOf` |
| hasGuaranteedAmount | `fibo-fbc-dae-gty:hasGuaranteedAmount` | `.../FBC/DebtAndEquities/Guaranty/hasGuaranteedAmount` |
| hasDefaultThresholdAmount | `fibo-fbc-dae-cre:hasDefaultThresholdAmount` | `.../FBC/DebtAndEquities/CreditEvents/hasDefaultThresholdAmount` |
| hasPrincipalParty | `fibo-fnd-agr-ctr:hasPrincipalParty` | `.../FND/Agreements/Contracts/hasPrincipalParty` |

#### ⚠️ FIBO has no Covenant class — these are `ex:` extensions, not FIBO terms

> **⚠️ SUPERSEDED IN PART, 2026-08-24 (Wave 15).** The `CovenantDefinition` claim
> below — "no FIBO class exists" — is wrong. `fibo-fnd-agr-ctr:ContractualDefinition`
> is an exact fit and is co-typed on every `ex:CovenantDefinition` node. See the
> Wave 15 correction at "the covenant definition chain" below (§ Wave 15,
> ~line 2080) before citing this claim. The rest of this table — `Covenant`,
> `MeasurementPeriod`, and the four object properties — is unaffected and stands.

**This is the most consequential finding of the Wave 0 binding pass.** An exhaustive search of the full `edmcouncil/fibo` repository — every `rdf:about` and every `rdfs:label` across all 295 RDF modules — returns exactly **one** covenant-bearing term: `BreachOfCovenant`. There is no `Covenant` class, no `FinancialCovenant`, no `CovenantDefinition`, and no covenant-linking object property anywhere in FIBO Production.

The flagship product `covenant-in-force-as-of` and `covenant-cross-reference` both model `Covenant`, `CovenantDefinition`, `covenantOf`, `definedBy`, and `measuredBy`. **None of these can be bound to FIBO.** They must live under `ex:` and be labelled as application extensions, not as ontology terms:

| Local name | IRI | Why not FIBO |
| --- | --- | --- |
| Covenant | `http://example.org/fibo/Covenant` | no FIBO class exists |
| CovenantDefinition | `http://example.org/fibo/CovenantDefinition` | ⚠️ **superseded 2026-08-24, see below** — role marker, co-typed with `fibo-fnd-agr-ctr:ContractualDefinition` on every node (verified live 2026-08-24: 49 `ex:CovenantDefinition` nodes, 49 co-typed, 0 without the FIBO class) |
| MeasurementPeriod | `http://example.org/fibo/MeasurementPeriod` | no FIBO class exists |
| covenantOf | `http://example.org/fibo/covenantOf` | no FIBO property exists |
| definedBy | `http://example.org/fibo/definedBy` | no FIBO property exists |
| measuredBy | `http://example.org/fibo/measuredBy` | no FIBO property exists |
| supersededBy | `http://example.org/fibo/supersededBy` | no FIBO property exists |
| crossReferences | `http://example.org/fibo/crossReferences` | no FIBO property exists |

Two real FIBO terms sit adjacent and should be used where they genuinely apply rather than being replaced by the `ex:` extensions: **`fibo-fbc-dae-gty:NegativePledge`** is a negative covenant with a proper binding, and **`fibo-fnd-agr-ctr:BreachOfCovenant`** is the correct type for a breach event. Model the breach with FIBO; model the covenant itself with `ex:`.

Recording this honestly matters more than the inconvenience. A downstream consumer told these are FIBO terms would query for them against a conformant FIBO store and get nothing back.

### 🔴 Wave 8 correction — two v1 starter properties do not exist in FIBO

**Found 2026-08-17.** The Wave 0 pass verified the *Loans-module extensions* it
added. It did not re-verify the **five starter properties inherited from v1**.
Wave 8 did, and two of them are not FIBO terms:

| Recorded in the starter table | Status |
| --- | --- |
| `fibo-be-oac-cown:hasOwnershipInterestIn` → `.../BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn` | **Does not exist.** No such property anywhere in FIBO; the module `BE/OwnershipAndControl/Ownership` **404s** |
| `fibo-be-oac-cctl:hasControllingInterestIn` → `.../BE/OwnershipAndControl/Control/hasControllingInterestIn` | **Does not exist.** Same — module `BE/OwnershipAndControl/Control` **404s** |

Both were confirmed absent two ways: an exhaustive `rdf:about` / `rdfs:label`
search across all **295** RDF modules of a shallow `edmcouncil/fibo` clone, and a
live fetch against published Production. Re-checkable at any time via
`generators/verify_fibo_wave8_confirm.py`, which asserts their absence explicitly.

**The prefixes were real; the namespaces attached to them were not.** FIBO splits
this vocabulary differently than the v1 table assumed:

| Prefix | v1 recorded | **Actual FIBO namespace** |
| --- | --- | --- |
| `fibo-be-oac-cown` | `BE/OwnershipAndControl/Ownership/` | **`BE/OwnershipAndControl/CorporateOwnership/`** |
| `fibo-be-oac-cctl` | `BE/OwnershipAndControl/Control/` | **`BE/OwnershipAndControl/CorporateControl/`** |

Generic ownership and control live under **`FND/OwnershipAndControl/`**, not `BE/`.
`BE/` carries the *corporate* specialisations.

**Blast radius.** `loaders/load_fluree_wave3.py` loaded **565 edges** against these
two predicates — 462 ownership, 103 control — and they are the graph
`corporate-family-tree` traverses. `validators/conditions.py` and
`generators/generate_mnpi.py` also reference them. The data is internally
consistent and **externally unconsumable**: a downstream client querying a
conformant FIBO store for these IRIs gets nothing back. This is exactly the
failure CLAUDE.md's binding protocol exists to prevent.

**Proposed replacements** — all confirmed present in Production:

| Purpose | Use instead |
| --- | --- |
| Generic ownership | `fibo-fnd-oac-own:owns` / `isOwnedBy` |
| Entity-to-entity ownership | `fibo-be-oac-opty:hasOwningEntity` / `hasOwnedEntity` |
| Generic control | `fibo-fnd-oac-ctl:hasControllingParty` / `isControllingPartyOf`, or `fibo-fnd-rel-rel:controls` / `isControlledBy` |
| Parent / subsidiary | `fibo-be-oac-cctl:isSubsidiaryOf` / `hasSubsidiary` / `isParentCompanyOf` |
| **Direct vs ultimate parent** | `fibo-be-oac-cctl:hasDomesticUltimateParent` / `hasGlobalUltimateParent` |

That last row matters: `corporate-family-tree` §B distinguishes direct from
ultimate parent, and FIBO has had dedicated properties for it the whole time. The
invented predicates were both wrong *and* less expressive than the real ones.

> **✅ Remediated 2026-08-17.** 570 triples retracted via
> `loaders/remediate_ownership_iris.py`, then re-loaded on the corrected IRIs.
> Ledger t=25 → 36; 565 edges now carry `owns` (462) and `controls` (103); zero
> remain on the invalid predicates. All four validators pass against the
> corrected IRIs. Full record in `docs/known-issues.md` §0.1.
>
> The invented `control subPropertyOf ownership` axiom was **not** re-asserted —
> FIBO makes the two siblings under `playsActiveRoleThatDirectlyAffects`.
>
> **📤 The vault mirror still publishes the invalid predicates and needs refreshing.**

---

### Wave 8 extension — Ownership/Control, Person, Officers, Accounts, Debt, Rates, Derivatives, Securitization

**Added 2026-08-17.** Every term below was confirmed against **published
Production** by `generators/verify_fibo_wave8_confirm.py` — **121 confirmed, 0
missing**. Machine-readable record: `sources/screening/fibo_wave8_confirmed.json`.

Discovery ran first via `generators/verify_fibo_wave8.py` over candidate module
paths. That pass is *not* sufficient on its own: a wrong module guess is
indistinguishable from a missing term, and it very nearly recorded `Tranche` as
absent from FIBO when it lives in `SEC/Debt/PoolBackedSecurities`. Terms are
therefore discovered by clone-wide grep and confirmed by live fetch.

**Checked and NOT found — deliberately absent from the tables below:**

| Term looked for | Finding |
| --- | --- |
| `BE/LegalEntities/LegalPersons/LegalPerson` | No bare `LegalPerson`. The module declares `CharteredLegalPerson` and `LegallyCompetentNaturalPerson` |
| `IND/InterestRates/InterestRates/FloatingInterestRate` | Not in that module. Use `ReferenceInterestRate`, or `fibo-sec-dbt-bnd:FloatingRateNote` for the instrument |
| A bare `NaturalPerson` class | Does not exist. Use `fibo-fnd-aap-ppl:Person`, or `fibo-be-le-lp:LegallyCompetentNaturalPerson` where legal capacity is meant |
| A generic `Securitization` class | Only *process* classes under `fibo-bp-iss-*` (FIBO **Business Process**, not Production). For the instrument use `fibo-sec-dbt-pbs:AssetBackedSecurity` / `PoolBackedSecurity` / `StructuredFinanceInstrument` |
| A `Waterfall` class | Does not exist anywhere in FIBO. Model as `ex:` if needed |


#### Prefixes added

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-be-le-lp` | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/` |
| `fibo-be-oac-cctl` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateControl/` |
| `fibo-be-oac-cown` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateOwnership/` |
| `fibo-be-oac-exec` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Executives/` |
| `fibo-be-oac-opty` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/OwnershipParties/` |
| `fibo-der-drc-swp` | `https://spec.edmcouncil.org/fibo/ontology/DER/DerivativesContracts/Swaps/` |
| `fibo-der-rtd-rtd` | `https://spec.edmcouncil.org/fibo/ontology/DER/RateDerivatives/RateDerivatives/` |
| `fibo-fbc-fi-fi` | `https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/` |
| `fibo-fbc-pas-caa` | `https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/ClientsAndAccounts/` |
| `fibo-fbc-pas-fpas` | `https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/` |
| `fibo-fnd-aap-ppl` | `https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/People/` |
| `fibo-fnd-org-fm` | `https://spec.edmcouncil.org/fibo/ontology/FND/Organizations/FormalOrganizations/` |
| `fibo-fnd-oac-ctl` | `https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Control/` |
| `fibo-fnd-oac-own` | `https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/` |
| `fibo-ind-fx-fx` | `https://spec.edmcouncil.org/fibo/ontology/IND/ForeignExchange/ForeignExchange/` |
| `fibo-ind-ir-ir` | `https://spec.edmcouncil.org/fibo/ontology/IND/InterestRates/InterestRates/` |
| `fibo-sec-dbt-bnd` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/Bonds/` |
| `fibo-sec-dbt-cdo` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/CollateralizedDebtObligations/` |
| `fibo-sec-dbt-dbti` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DebtInstruments/` |
| `fibo-sec-dbt-mbs` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/MortgageBackedSecurities/` |
| `fibo-sec-dbt-pbs` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/PoolBackedSecurities/` |

#### OWNERSHIP / CONTROL (corrects the v1 starter defect)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| ControlledAffiliate | `fibo-be-oac-cctl:ControlledAffiliate` | `.../BE/OwnershipAndControl/CorporateControl/ControlledAffiliate` |
| EntityOwnership | `fibo-be-oac-opty:EntityOwnership` | `.../BE/OwnershipAndControl/OwnershipParties/EntityOwnership` |
| Ownership | `fibo-fnd-oac-own:Ownership` | `.../FND/OwnershipAndControl/Ownership/Ownership` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasControllingAffiliate | `fibo-be-oac-cctl:hasControllingAffiliate` | `.../BE/OwnershipAndControl/CorporateControl/hasControllingAffiliate` |
| hasControllingParty | `fibo-fnd-oac-ctl:hasControllingParty` | `.../FND/OwnershipAndControl/Control/hasControllingParty` |
| hasDirectOwnership | `fibo-be-oac-opty:hasDirectOwnership` | `.../BE/OwnershipAndControl/OwnershipParties/hasDirectOwnership` |
| hasDomesticUltimateParent | `fibo-be-oac-cctl:hasDomesticUltimateParent` | `.../BE/OwnershipAndControl/CorporateControl/hasDomesticUltimateParent` |
| hasGlobalUltimateParent | `fibo-be-oac-cctl:hasGlobalUltimateParent` | `.../BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent` |
| hasInvestmentOwnership | `fibo-be-oac-opty:hasInvestmentOwnership` | `.../BE/OwnershipAndControl/OwnershipParties/hasInvestmentOwnership` |
| hasOwnedAsset | `fibo-fnd-oac-own:hasOwnedAsset` | `.../FND/OwnershipAndControl/Ownership/hasOwnedAsset` |
| hasOwnedEntity | `fibo-be-oac-opty:hasOwnedEntity` | `.../BE/OwnershipAndControl/OwnershipParties/hasOwnedEntity` |
| hasOwningEntity | `fibo-be-oac-opty:hasOwningEntity` | `.../BE/OwnershipAndControl/OwnershipParties/hasOwningEntity` |
| hasOwningParty | `fibo-fnd-oac-own:hasOwningParty` | `.../FND/OwnershipAndControl/Ownership/hasOwningParty` |
| hasSubsidiary | `fibo-be-oac-cctl:hasSubsidiary` | `.../BE/OwnershipAndControl/CorporateControl/hasSubsidiary` |
| isControlledPartyOf | `fibo-fnd-oac-ctl:isControlledPartyOf` | `.../FND/OwnershipAndControl/Control/isControlledPartyOf` |
| isControllingPartyOf | `fibo-fnd-oac-ctl:isControllingPartyOf` | `.../FND/OwnershipAndControl/Control/isControllingPartyOf` |
| isOwnedBy | `fibo-fnd-oac-own:isOwnedBy` | `.../FND/OwnershipAndControl/Ownership/isOwnedBy` |
| isParentCompanyOf | `fibo-be-oac-cctl:isParentCompanyOf` | `.../BE/OwnershipAndControl/CorporateControl/isParentCompanyOf` |
| isSubsidiaryOf | `fibo-be-oac-cctl:isSubsidiaryOf` | `.../BE/OwnershipAndControl/CorporateControl/isSubsidiaryOf` |
| isWhollyOwnedBy | `fibo-be-oac-cctl:isWhollyOwnedBy` | `.../BE/OwnershipAndControl/CorporateControl/isWhollyOwnedBy` |
| owns | `fibo-fnd-oac-own:owns` | `.../FND/OwnershipAndControl/Ownership/owns` |

#### BENEFICIAL OWNERSHIP (kyc-refresh-beneficial-ownership)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| BeneficialOwner | `fibo-be-oac-cown:BeneficialOwner` | `.../BE/OwnershipAndControl/CorporateOwnership/BeneficialOwner` |
| BeneficialOwnership | `fibo-be-oac-cown:BeneficialOwnership` | `.../BE/OwnershipAndControl/CorporateOwnership/BeneficialOwnership` |
| SignificantShareholder | `fibo-be-oac-cctl:SignificantShareholder` | `.../BE/OwnershipAndControl/CorporateControl/SignificantShareholder` |
| VotingShareholder | `fibo-be-oac-cctl:VotingShareholder` | `.../BE/OwnershipAndControl/CorporateControl/VotingShareholder` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasBeneficialOwner | `fibo-be-oac-cown:hasBeneficialOwner` | `.../BE/OwnershipAndControl/CorporateOwnership/hasBeneficialOwner` |
| isBeneficialOwnerOf | `fibo-be-oac-cown:isBeneficialOwnerOf` | `.../BE/OwnershipAndControl/CorporateOwnership/isBeneficialOwnerOf` |

#### IDENTITY RESOLUTION (kyc-refresh-beneficial-ownership, Wave 13b)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| differentFrom | `owl:differentFrom` | `http://www.w3.org/2002/07/owl#differentFrom` |

**Not FIBO, and deliberately so.** `owl:differentFrom` is the OWL 2 built-in
asserting that two individuals are **not** the same. It is exactly what a
confirmed false-positive pair is: two records that fuzzy-match above the merge
threshold and are nonetheless different people. Asserting it makes the negative
finding a fact in the graph rather than an absence, so a downstream resolver
cannot re-merge the pair by scoring names again.

**`owl:sameAs` is deliberately NOT asserted by Wave 13b.** The design's §1.1
baseline lists it at zero assertions, and it stays there: within this layer,
every cross-registry rendering belongs to a person node that already exists, so
the identity edge is `cmns-id:isIdentifiedBy` to a `PersonName`, not a
`sameAs` between two person nodes. Asserting `sameAs` to make a count move
would state an identity the resolution never concluded. Recorded here so the
next wave knows it was decided, not forgotten.

#### OFFSHORE INTERMEDIARY (kyc-refresh-beneficial-ownership, Wave 13b)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| ServiceProvider | `cmns-org:ServiceProvider` | `https://www.omg.org/spec/Commons/Organizations/ServiceProvider` |

**Verified 2026-08-22** against the live OMG Commons Organizations module
(`https://www.omg.org/spec/Commons/Organizations/`, fetched with
`Accept: application/rdf+xml`). It is an `owl:Class`, `rdfs:subClassOf`
`cmns-pts:AgentRole` and `cmns-rlcmp:FunctionalRole`, with
`skos:definition` *"role of an agent that provides some service, including but
not limited to commercial or professional services"* and a `skos:example` that
names **registration** and **regulatory** services explicitly. That is exactly
a corporate service provider / registered agent.

It is an **AgentRole, not an entity type.** Per rule 7 (no OWL inference), an
intermediary node is typed with the Commons organization classes *and*
`cmns-org:ServiceProvider` explicitly — a query for one will not find the other.

#### PERSON (kyc-refresh-beneficial-ownership)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| LegallyCompetentNaturalPerson | `fibo-be-le-lp:LegallyCompetentNaturalPerson` | `.../BE/LegalEntities/LegalPersons/LegallyCompetentNaturalPerson` |
| Person | `fibo-fnd-aap-ppl:Person` | `.../FND/AgentsAndPeople/People/Person` |
| PersonName | `fibo-fnd-aap-ppl:PersonName` | `.../FND/AgentsAndPeople/People/PersonName` |
| SpecialPurposeVehicle | `fibo-be-le-lp:SpecialPurposeVehicle` | `.../BE/LegalEntities/LegalPersons/SpecialPurposeVehicle` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasPersonName | `fibo-fnd-aap-ppl:hasPersonName` | `.../FND/AgentsAndPeople/People/hasPersonName` |

#### OFFICER / DIRECTOR / EMPLOYMENT (client-360-coverage-graph)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| BoardOfDirectors | `fibo-be-oac-exec:BoardOfDirectors` | `.../BE/OwnershipAndControl/Executives/BoardOfDirectors` |
| ChiefExecutiveOfficer | `fibo-be-oac-exec:ChiefExecutiveOfficer` | `.../BE/OwnershipAndControl/Executives/ChiefExecutiveOfficer` |
| ChiefFinancialOfficer | `fibo-be-oac-exec:ChiefFinancialOfficer` | `.../BE/OwnershipAndControl/Executives/ChiefFinancialOfficer` |
| CorporateOfficer | `fibo-be-oac-exec:CorporateOfficer` | `.../BE/OwnershipAndControl/Executives/CorporateOfficer` |
| Employee | `fibo-fnd-org-fm:Employee` | `.../FND/Organizations/FormalOrganizations/Employee` |
| Employer | `fibo-fnd-org-fm:Employer` | `.../FND/Organizations/FormalOrganizations/Employer` |
| Employment | `fibo-fnd-org-fm:Employment` | `.../FND/Organizations/FormalOrganizations/Employment` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| employs | `fibo-fnd-org-fm:employs` | `.../FND/Organizations/FormalOrganizations/employs` |
| hasCorporateOfficer | `fibo-be-oac-exec:hasCorporateOfficer` | `.../BE/OwnershipAndControl/Executives/hasCorporateOfficer` |
| hasDirector | `fibo-be-oac-exec:hasDirector` | `.../BE/OwnershipAndControl/Executives/hasDirector` |
| isDirectorOf | `fibo-be-oac-exec:isDirectorOf` | `.../BE/OwnershipAndControl/Executives/isDirectorOf` |
| isEmployedBy | `fibo-fnd-org-fm:isEmployedBy` | `.../FND/Organizations/FormalOrganizations/isEmployedBy` |
| isOfficerOf | `fibo-be-oac-exec:isOfficerOf` | `.../BE/OwnershipAndControl/Executives/isOfficerOf` |

#### DEPOSIT ACCOUNTS (collateral-and-setoff, treasury-liquidity)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| Account | `fibo-fbc-pas-caa:Account` | `.../FBC/ProductsAndServices/ClientsAndAccounts/Account` |
| AccountHolder | `fibo-fbc-pas-caa:AccountHolder` | `.../FBC/ProductsAndServices/ClientsAndAccounts/AccountHolder` |
| CertificateOfDeposit | `fibo-fbc-pas-caa:CertificateOfDeposit` | `.../FBC/ProductsAndServices/ClientsAndAccounts/CertificateOfDeposit` |
| DemandDepositAccount | `fibo-fbc-pas-caa:DemandDepositAccount` | `.../FBC/ProductsAndServices/ClientsAndAccounts/DemandDepositAccount` |
| DepositAccount | `fibo-fbc-pas-caa:DepositAccount` | `.../FBC/ProductsAndServices/ClientsAndAccounts/DepositAccount` |
| InvestmentAccount | `fibo-fbc-pas-caa:InvestmentAccount` | `.../FBC/ProductsAndServices/ClientsAndAccounts/InvestmentAccount` |
| TimeDepositAccount | `fibo-fbc-pas-caa:TimeDepositAccount` | `.../FBC/ProductsAndServices/ClientsAndAccounts/TimeDepositAccount` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasPrimaryAccountHolder | `fibo-fbc-pas-caa:hasPrimaryAccountHolder` | `.../FBC/ProductsAndServices/ClientsAndAccounts/hasPrimaryAccountHolder` |

#### Wave 12 addition — investment instrument classes (`treasury-liquidity-position`)

**Added 2026-08-22 (Wave 12 Task 9).** `docs/wave12-design.md` §1.1 measured
"no new FIBO binding required" against the terms named in the spec's own
prose. That check never worked out the concrete per-instrument-kind typing
the task-9 brief's constraint demands ("each position typed for both its
instrument class and the roles it must answer") — a narrower question with a
different answer. Verified live against a shallow `edmcouncil/fibo` clone
(git, no auth), not guessed from module names:

| Term looked for | Finding |
| --- | --- |
| `MoneyMarketFund` | **Zero hits anywhere in the clone.** Closest genuine class: `MutualFund` (`SEC/Funds/Funds`) — a money market fund legally IS a type of open-end/mutual fund; FIBO has no MMF-specific subclass |

New prefixes:

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-sec-dbt-tstd` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/TradedShortTermDebt/` |
| `fibo-sec-fund-fund` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Funds/Funds/` |

| Local name | Prefix form | Full IRI | Notes |
| --- | --- | --- | --- |
| CommercialPaper | `fibo-sec-dbt-tstd:CommercialPaper` | `.../SEC/Debt/TradedShortTermDebt/CommercialPaper` | exact match for `instrument_kind = 'commercial-paper'`; subclass of `MoneyMarketInstrument` |
| MoneyMarketInstrument | `fibo-sec-dbt-tstd:MoneyMarketInstrument` | `.../SEC/Debt/TradedShortTermDebt/MoneyMarketInstrument` | recorded for completeness; not asserted as an instance type by this loader |
| MutualFund | `fibo-sec-fund-fund:MutualFund` | `.../SEC/Funds/Funds/MutualFund` | closest real term for `instrument_kind = 'money-market-fund'` — see finding above |
| TreasuryBill | `fibo-sec-dbt-bnd:TreasuryBill` | `.../SEC/Debt/Bonds/TreasuryBill` | exact match for `instrument_kind = 'treasury-bill'`; subclass of `USTreasurySecurity` AND `MoneyMarketInstrument`. Uses the prefix already bound for `TreasuryBond` etc. |

**`InvestmentAccount` needed no new binding** — already present in the
DEPOSIT ACCOUNTS table above since Wave 8, explicitly tagged
"(collateral-and-setoff, treasury-liquidity)"; `load_fluree_wave12_treasury.py`
is simply its first use.

**`fibo-fnd-agr-ctr:Counterparty` was also found** (real, exact match for the
spec's schema-row "Counterparty" entity — same module as the already-bound
`BreachOfCovenant`) but is deliberately **not** asserted anywhere yet: no
current task's typing constraint names it, and the entity nodes it would
apply to belong to Wave 3/6, not Wave 12. Recorded here so a future task
does not re-discover it from scratch.

**Vault mirror.** `CommercialPaper`, `TreasuryBill`, and `MutualFund` (plus
the `ex:RegulatoryPosture` extension below) are new since the Wave 8 binding
the vault mirror carries — `wiki/context-products/content/fibo-iri-binding`
is stale on all four. This repo is source of truth; the mirror is refreshed
by the custodian, never here. Sent through the agent exchange (see
`~/.agent-exchange/ccf-dataprep/outbox/`) rather than edited in the vault
directly.

#### DEBT INSTRUMENTS / BONDS (rating-and-spread-migration)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| Bond | `fibo-sec-dbt-bnd:Bond` | `.../SEC/Debt/Bonds/Bond` |
| BondCoupon | `fibo-sec-dbt-bnd:BondCoupon` | `.../SEC/Debt/Bonds/BondCoupon` |
| CallableBond | `fibo-sec-dbt-bnd:CallableBond` | `.../SEC/Debt/Bonds/CallableBond` |
| ConvertibleBond | `fibo-sec-dbt-bnd:ConvertibleBond` | `.../SEC/Debt/Bonds/ConvertibleBond` |
| CorporateBond | `fibo-sec-dbt-bnd:CorporateBond` | `.../SEC/Debt/Bonds/CorporateBond` |
| DebtInstrument | `fibo-fbc-fi-fi:DebtInstrument` | `.../FBC/FinancialInstruments/FinancialInstruments/DebtInstrument` |
| DerivativeInstrument | `fibo-fbc-fi-fi:DerivativeInstrument` | `.../FBC/FinancialInstruments/FinancialInstruments/DerivativeInstrument` |
| FixedCouponBond | `fibo-sec-dbt-bnd:FixedCouponBond` | `.../SEC/Debt/Bonds/FixedCouponBond` |
| FloatingRateNote | `fibo-sec-dbt-bnd:FloatingRateNote` | `.../SEC/Debt/Bonds/FloatingRateNote` |
| Future | `fibo-fbc-fi-fi:Future` | `.../FBC/FinancialInstruments/FinancialInstruments/Future` |
| Option | `fibo-fbc-fi-fi:Option` | `.../FBC/FinancialInstruments/FinancialInstruments/Option` |
| SpotContract | `fibo-fbc-fi-fi:SpotContract` | `.../FBC/FinancialInstruments/FinancialInstruments/SpotContract` |
| TradableDebtInstrument | `fibo-sec-dbt-dbti:TradableDebtInstrument` | `.../SEC/Debt/DebtInstruments/TradableDebtInstrument` |
| TreasuryBond | `fibo-sec-dbt-bnd:TreasuryBond` | `.../SEC/Debt/Bonds/TreasuryBond` |
| VariableCouponBond | `fibo-sec-dbt-bnd:VariableCouponBond` | `.../SEC/Debt/Bonds/VariableCouponBond` |
| ZeroCouponBond | `fibo-sec-dbt-bnd:ZeroCouponBond` | `.../SEC/Debt/Bonds/ZeroCouponBond` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| isSubordinated | `fibo-sec-dbt-dbti:isSubordinated` | `.../SEC/Debt/DebtInstruments/isSubordinated` |
| isSubordinatedTo | `fibo-sec-dbt-dbti:isSubordinatedTo` | `.../SEC/Debt/DebtInstruments/isSubordinatedTo` |

#### CREDIT RATINGS / ISSUANCE (rating-and-spread-migration)

**Added 2026-08-19 (Wave 11a Task 8).** `issuedBy` and a credit-grade /
market-observation class had no binding in the contract going into this
task (§3.2 of `docs/wave11a-design.md`). Verified by fetching the Production
RDF/XML modules directly from `spec.edmcouncil.org` — not guessed from module
names, per the standing rule that module membership does not pin an IRI.

New prefixes:

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-fbc-dae-crt` | `https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/CreditRatings/` |
| `fibo-fnd-arr-rt` | `https://spec.edmcouncil.org/fibo/ontology/FND/Arrangements/Ratings/` |

`fibo-fnd-rel-rel` needs no new prefix row — it was already bound in Wave 8
for `hasIdentity` / `isIdentifiedBy` / `controls`.

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| CreditRating | `fibo-fbc-dae-crt:CreditRating` | `.../FBC/DebtAndEquities/CreditRatings/CreditRating` |
| OrganizationCreditRating | `fibo-fbc-dae-crt:OrganizationCreditRating` | `.../FBC/DebtAndEquities/CreditRatings/OrganizationCreditRating` |
| RatingAssessmentEvent | `fibo-fnd-arr-rt:RatingAssessmentEvent` | `.../FND/Arrangements/Ratings/RatingAssessmentEvent` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| isIssuedBy | `fibo-fnd-rel-rel:isIssuedBy` | `.../FND/Relations/Relations/isIssuedBy` |
| concernsParty | `fibo-fbc-dae-crt:concernsParty` | `.../FBC/DebtAndEquities/CreditRatings/concernsParty` |

**Why `OrganizationCreditRating` and not `InstrumentCreditRating`:** Task 6's
245-assertion grade chain rates the OBLIGOR (keyed by `lei`), not a specific
instrument — `CreditRating` has both subclasses, and only one matches the
data's own grain.

**Why `RatingAssessmentEvent` for the confirmed public rating actions:** its
FIBO definition is "individual assessment resulting in a grade or score and
potentially a report describing the score" — exactly the shape of an S&P /
Moody's / Fitch action found and confirmed in a real 8-K, and distinct from
`OrganizationCreditRating` (our own synthetic — internal grade opinion).

**`concernsParty` is reused for both classes.** The Assessments module
(`RatingAssessmentEvent`'s ultimate ancestor) has no generic subject-party
property of its own; `concernsParty` is `subPropertyOf cmns-pts:hasParty`,
the CreditRatings module's general-purpose party link, not scoped in its own
restrictions to one class.

**One `ex:` extension, not two.** An Item 2.03 debt-issuance disclosure has
no Production-ontology class. The only FIBO vocabulary for a securities
issuance *event* lives in `BP/SecuritiesIssuance/DebtIssuance` — FIBO
**Business Process**, out of scope for the same reason the Wave 8
`Securitization` search landed on `ex:` (Production models the instrument,
not the disclosure event). See the Wave 11a row in the extension register
below.

#### RATES / FX REFERENCE (treasury-liquidity, fx-post-trade)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| CurrencyForwardRate | `fibo-ind-fx-fx:CurrencyForwardRate` | `.../IND/ForeignExchange/ForeignExchange/CurrencyForwardRate` |
| CurrencySpotRate | `fibo-ind-fx-fx:CurrencySpotRate` | `.../IND/ForeignExchange/ForeignExchange/CurrencySpotRate` |
| ExchangeRateStructure | `fibo-ind-fx-fx:ExchangeRateStructure` | `.../IND/ForeignExchange/ForeignExchange/ExchangeRateStructure` |
| InterestRateAuthority | `fibo-ind-ir-ir:InterestRateAuthority` | `.../IND/InterestRates/InterestRates/InterestRateAuthority` |
| InterestRateBenchmark | `fibo-ind-ir-ir:InterestRateBenchmark` | `.../IND/InterestRates/InterestRates/InterestRateBenchmark` |
| QuotedExchangeRate | `fibo-ind-fx-fx:QuotedExchangeRate` | `.../IND/ForeignExchange/ForeignExchange/QuotedExchangeRate` |
| ReferenceInterestRate | `fibo-ind-ir-ir:ReferenceInterestRate` | `.../IND/InterestRates/InterestRates/ReferenceInterestRate` |
| SpecificProviderInterestRateBenchmark | `fibo-ind-ir-ir:SpecificProviderInterestRateBenchmark` | `.../IND/InterestRates/InterestRates/SpecificProviderInterestRateBenchmark` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasQuotedExchangeRate | `fibo-ind-fx-fx:hasQuotedExchangeRate` | `.../IND/ForeignExchange/ForeignExchange/hasQuotedExchangeRate` |

#### DERIVATIVES / SWAPS (fx-post-trade-reconciliation)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| ForeignExchangeRateObservable | `fibo-der-rtd-rtd:ForeignExchangeRateObservable` | `.../DER/RateDerivatives/RateDerivatives/ForeignExchangeRateObservable` |
| ForwardRateAgreement | `fibo-der-rtd-rtd:ForwardRateAgreement` | `.../DER/RateDerivatives/RateDerivatives/ForwardRateAgreement` |
| InterestRateDerivativeInstrument | `fibo-der-rtd-rtd:InterestRateDerivativeInstrument` | `.../DER/RateDerivatives/RateDerivatives/InterestRateDerivativeInstrument` |
| Swap | `fibo-der-drc-swp:Swap` | `.../DER/DerivativesContracts/Swaps/Swap` |
| SwapConfirmation | `fibo-der-drc-swp:SwapConfirmation` | `.../DER/DerivativesContracts/Swaps/SwapConfirmation` |
| SwapLeg | `fibo-der-drc-swp:SwapLeg` | `.../DER/DerivativesContracts/Swaps/SwapLeg` |
| SwapLifecycleEvent | `fibo-der-drc-swp:SwapLifecycleEvent` | `.../DER/DerivativesContracts/Swaps/SwapLifecycleEvent` |
| SwapParty | `fibo-der-drc-swp:SwapParty` | `.../DER/DerivativesContracts/Swaps/SwapParty` |
| SwapTerms | `fibo-der-drc-swp:SwapTerms` | `.../DER/DerivativesContracts/Swaps/SwapTerms` |
| UniqueSwapIdentifier | `fibo-der-drc-swp:UniqueSwapIdentifier` | `.../DER/DerivativesContracts/Swaps/UniqueSwapIdentifier` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasSwapIdentifier | `fibo-der-drc-swp:hasSwapIdentifier` | `.../DER/DerivativesContracts/Swaps/hasSwapIdentifier` |

#### TRADE / SETTLEMENT (fx-post-trade-reconciliation)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| SettlementTerms | `fibo-fbc-pas-fpas:SettlementTerms` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/SettlementTerms` |
| Trade | `fibo-fbc-pas-fpas:Trade` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/Trade` |
| TradeIdentifier | `fibo-fbc-pas-fpas:TradeIdentifier` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/TradeIdentifier` |
| TradeLifecycle | `fibo-fbc-pas-fpas:TradeLifecycle` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/TradeLifecycle` |
| TradeLifecycleEvent | `fibo-fbc-pas-fpas:TradeLifecycleEvent` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/TradeLifecycleEvent` |
| TradeLifecycleStage | `fibo-fbc-pas-fpas:TradeLifecycleStage` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/TradeLifecycleStage` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasSettlementDate | `fibo-fbc-pas-fpas:hasSettlementDate` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/hasSettlementDate` |

#### SECURITIZATION / TRANCHE (abs-securitization-surveillance)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| AssetBackedSecurity | `fibo-sec-dbt-pbs:AssetBackedSecurity` | `.../SEC/Debt/PoolBackedSecurities/AssetBackedSecurity` |
| AttachmentPoint | `fibo-sec-dbt-pbs:AttachmentPoint` | `.../SEC/Debt/PoolBackedSecurities/AttachmentPoint` |
| CollateralizedDebtObligation | `fibo-sec-dbt-cdo:CollateralizedDebtObligation` | `.../SEC/Debt/CollateralizedDebtObligations/CollateralizedDebtObligation` |
| DebtPoolStatisticalMeasure | `fibo-sec-dbt-pbs:DebtPoolStatisticalMeasure` | `.../SEC/Debt/PoolBackedSecurities/DebtPoolStatisticalMeasure` |
| DefaultRate | `fibo-sec-dbt-pbs:DefaultRate` | `.../SEC/Debt/PoolBackedSecurities/DefaultRate` |
| DetachmentPoint | `fibo-sec-dbt-pbs:DetachmentPoint` | `.../SEC/Debt/PoolBackedSecurities/DetachmentPoint` |
| MezzanineCDOTranche | `fibo-sec-dbt-cdo:MezzanineCDOTranche` | `.../SEC/Debt/CollateralizedDebtObligations/MezzanineCDOTranche` |
| MortgageBackedSecurity | `fibo-sec-dbt-mbs:MortgageBackedSecurity` | `.../SEC/Debt/MortgageBackedSecurities/MortgageBackedSecurity` |
| PoolBackedSecurity | `fibo-sec-dbt-pbs:PoolBackedSecurity` | `.../SEC/Debt/PoolBackedSecurities/PoolBackedSecurity` |
| PrepaymentSpeed | `fibo-sec-dbt-pbs:PrepaymentSpeed` | `.../SEC/Debt/PoolBackedSecurities/PrepaymentSpeed` |
| SeniorCDOTranche | `fibo-sec-dbt-cdo:SeniorCDOTranche` | `.../SEC/Debt/CollateralizedDebtObligations/SeniorCDOTranche` |
| StructuredFinanceInstrument | `fibo-sec-dbt-pbs:StructuredFinanceInstrument` | `.../SEC/Debt/PoolBackedSecurities/StructuredFinanceInstrument` |
| SubordinatedMBSTranche | `fibo-sec-dbt-cdo:SubordinatedMBSTranche` | `.../SEC/Debt/CollateralizedDebtObligations/SubordinatedMBSTranche` |
| Tranche | `fibo-sec-dbt-pbs:Tranche` | `.../SEC/Debt/PoolBackedSecurities/Tranche` |
| TrancheType | `fibo-sec-dbt-cdo:TrancheType` | `.../SEC/Debt/CollateralizedDebtObligations/TrancheType` |
| TriggerEvent | `fibo-sec-dbt-cdo:TriggerEvent` | `.../SEC/Debt/CollateralizedDebtObligations/TriggerEvent` |
| WeightedAverageCoupon | `fibo-sec-dbt-pbs:WeightedAverageCoupon` | `.../SEC/Debt/PoolBackedSecurities/WeightedAverageCoupon` |
| WeightedAverageLife | `fibo-sec-dbt-pbs:WeightedAverageLife` | `.../SEC/Debt/PoolBackedSecurities/WeightedAverageLife` |
| WeightedAverageMaturity | `fibo-sec-dbt-pbs:WeightedAverageMaturity` | `.../SEC/Debt/PoolBackedSecurities/WeightedAverageMaturity` |

| Property | Prefix form | Full IRI |
| --- | --- | --- |
| hasAttachmentPoint | `fibo-sec-dbt-pbs:hasAttachmentPoint` | `.../SEC/Debt/PoolBackedSecurities/hasAttachmentPoint` |
| hasDetachmentPoint | `fibo-sec-dbt-pbs:hasDetachmentPoint` | `.../SEC/Debt/PoolBackedSecurities/hasDetachmentPoint` |
| hasTrancheType | `fibo-sec-dbt-cdo:hasTrancheType` | `.../SEC/Debt/CollateralizedDebtObligations/hasTrancheType` |
| specifiesTrigger | `fibo-sec-dbt-cdo:specifiesTrigger` | `.../SEC/Debt/CollateralizedDebtObligations/specifiesTrigger` |

---

### Wave 8 addendum — three terms the vault flagged as unbound *and* unlisted

`abs-securitization-surveillance` names `Servicer`, `servicedBy`, and
`SourceDocument` in its schema. None appeared in the Wave 8 tables or on the
do-not-bind list, so the article gave no way to tell whether they were absent
from FIBO or simply not reached. The custodian marked them **provisional-`ex:`**
rather than inferring IRIs — correctly, on the `Tranche` precedent: a wrong
module guess is indistinguishable from a missing term.

Resolved 2026-08-17 by exhaustive search across all 295 modules plus live fetch.

| Term | Verdict | Binding |
| --- | --- | --- |
| `Servicer` | **exists** — the Wave 8 discovery pass simply missed it, because its substring filter had no `servic` token | `fibo-loan-ln-ln:Servicer` → `.../LOAN/LoansGeneral/Loans/Servicer` |
| `servicedBy` | **absent from Production.** Only `fibo-bp-iss-muni:hasServicer` / `services`, which are FIBO **Business Process**, not Production | `ex:servicedBy` |
| `SourceDocument` | **absent under that name**, but the concept exists in OMG Commons | `cmns-doc:Document`, or `cmns-doc:LegalDocument` for filed legal documents; `fibo-fnd-agr-ctr:ContractDocument` for credit agreements specifically |

`Servicer` is the one worth noting: `fibo-loan-ln-ln` was **already a bound
prefix from Wave 0**, so the term was bindable the whole time. The gap was in the
discovery filter, not in FIBO — which is the same failure the `Tranche` case
showed from the other direction, and the reason discovery is now backed by a
confirmation gate rather than trusted on its own.

`SourceDocument` is **not abs-only** — `kyc-refresh-beneficial-ownership` names
it too, so the resolution travels. It also adds a fourth prefix:

| Prefix | Namespace IRI |
| --- | --- |
| `cmns-doc` | `https://www.omg.org/spec/Commons/Documents/` |

---

### Wave 9 + Wave 10 — `ex:` extension register: the bank's operational relations

**No FIBO bindings were added or changed by Wave 9 or Wave 10.** Every FIBO
term either wave needed was already bound (Wave 0's Loans/Guaranty/Collateral
extension or Wave 8's Ownership/Person/Officer extension). What both waves
*did* need to mint is a set of `ex:` local terms, because FIBO models
instruments and agreements but has no vocabulary for the bank's own
operational relation to them — a lien the bank holds, a set-off right it can
exercise, a banker's coverage of a client, a meeting that happened. This
register exists so those terms are recorded once rather than rediscovered per
wave, and so the pattern — now visible across three consecutive waves — is
legible in one place.

**The pattern, stated plainly:** Wave 5 needed it for `Covenant` (§ above —
no FIBO covenant class exists at all). Wave 9 needed it for the collateral and
set-off relations below. Wave 10 needed it for coverage and interaction. Three
separate term lists understate the gap; it is one recurring shape.

#### Wave 9 — collateral, set-off, cross-default (`collateral-and-setoff-coverage`, `credit-exposure-rollup`)

| Local name | Full IRI | Why not FIBO |
| --- | --- | --- |
| `pledgedBy` | `http://example.org/fibo/pledgedBy` | no FIBO property links a `Collateral` instance back to the pledging party as an edge the estate can query |
| `setOffAgainst` | `http://example.org/fibo/setOffAgainst` | no FIBO set-off relation between an exposure and the account/instrument it can be netted against |
| `nettedUnder` | `http://example.org/fibo/nettedUnder` | FIBO's `NettingProvision` (bound, Wave 0) is the *agreement*; nothing links an exposure to it as an edge |
| `crossDefaultsWith` | `http://example.org/fibo/crossDefaultsWith` | FIBO's `CrossDefaultProvision` (bound, Wave 0) is the *clause*; nothing links two facilities that cross-default on each other |

#### Wave 10 — coverage and interaction (`client-360-coverage-graph`)

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `Banker` | class | `http://example.org/fibo/Banker` | no FIBO role class for a bank's own relationship-coverage employee |
| `Interaction` | class | `http://example.org/fibo/Interaction` | no FIBO class for a logged client touchpoint (meeting, call, deal-related contact) |
| `Deal` | class | `http://example.org/fibo/Deal` | no FIBO class for an internal deal/pipeline record an interaction can relate to |
| `coversClient` | property | `http://example.org/fibo/coversClient` | no FIBO property for a banker's coverage assignment to a client entity |
| `participatedIn` | property | `http://example.org/fibo/participatedIn` | no FIBO property linking a person to an interaction they took part in |
| `relatedToDeal` | property | `http://example.org/fibo/relatedToDeal` | no FIBO property linking an interaction to the deal it concerns |

#### Wave 11a — issuance disclosure (`rating-and-spread-migration`)

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `IssuanceEvent` | class | `http://example.org/fibo/IssuanceEvent` | no Production-ontology class for an Item 2.03 debt-issuance disclosure event — the only FIBO vocabulary for it is `BP/SecuritiesIssuance/DebtIssuance`, Business Process, out of scope |
| `filedBy` | property | `http://example.org/fibo/filedBy` | links an `IssuanceEvent` to the obligor that filed it; FIBO's `SEC/Securities/SecuritiesIssuance` module models the offering and the instrument, not the disclosure event itself |

`ex:grade`, `ex:trigger` and the reused `ex:validFrom` / `ex:validTo` /
`ex:assertedAt` / `ex:provenance` / `ex:sourceAccession` / `ex:evidence` on
grade-assertion, issuance and rating-action nodes are plain literal
attributes, not classes or FIBO-alternative relationship terms, so — per this
register's own scope and the precedent set by Wave 5's `covenantType` /
`threshold` / `observedValue` — they are not added as binding-table rows.
`ex:grade` is not a Postgres leak: nothing in Postgres records which grade an
obligor held on a given date (Task 7 loaded only the static 15-row scale, not
the 245-row assertion history), so Fluree is that fact's only home. `notch`,
`rating_band` and `modifier` — the values Postgres *does* own, one join away
via `rating_scale.grade` — are deliberately absent from every grade-assertion
node. See `loaders/load_fluree_wave11a.py`'s module docstring for the full
reasoning.

**Deliberately not minted:** `ex:Director`. FIBO has `CorporateOfficer` as a
real, bound class (Wave 8) but no `Director` class — directorship exists only
as the `isDirectorOf` edge. That asymmetry was checked, found to be genuine
(not a Wave 8 discovery gap), and left standing rather than minted a
symmetric-looking class FIBO itself does not have.

#### Wave 11b — early-warning surveillance (`credit-surveillance-early-warning`)

**Verified 2026-08-20. Four candidates checked, four absent; a fifth term
found by widening the audit, also absent; two near-misses found and
deliberately not reused.** All five enter the register as `ex:` extensions.
**Amended 2026-08-21: a sixth, `ex:item`, was missed and is bound below.** The
sentence this paragraph carried until then — *"All five enter the register"* —
was a complete list of what the audit found, not of what the wave asserts; the
whole-branch review caught the difference.

**How they were checked — and against *two* ontologies, not one.** FIBO
factored its foundational vocabulary out into the OMG Commons Ontology Library
(§0.2 of `docs/known-issues.md`), so a candidate absent from FIBO may still
exist in Commons and anything that assumes a single namespace prefix will miss
it. Both were searched:

| Corpus | How | Extent |
| --- | --- | --- |
| FIBO | shallow `edmcouncil/fibo` clone at `119fa8c` (2026-07-17); every `rdf:about`, every `rdf:ID`, every `rdfs:label` | all **295** RDF modules |
| OMG Commons | live fetch of every module named in `owl:imports` of `https://www.omg.org/spec/Commons/AboutCommons/` | all **22** modules |

The search was on **substrings, across every module** — `signal`, `warning`,
`trigger`, `source`, `about`, `indicator`, `observation`, `alert`, `provider` —
never scoped to a guessed module path. That is the `Tranche` lesson from Wave 8:
a wrong module guess is indistinguishable from a missing term, so an absence
claim is only worth anything if the search could not have missed the module.
Findings were then re-confirmed against live published **Production** at
`https://spec.edmcouncil.org/fibo/ontology/`; the clone is `master` (Dev), a
superset of Production, so absence in the clone entails absence in Production.

`signal` and `warning` return **zero** hits in either corpus — no `rdf:about`,
no `rdf:ID`, no `rdfs:label`, anywhere. `trigger` and `about` return real terms,
handled below.

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `WarningSignal` | class | `http://example.org/fibo/WarningSignal` | zero `signal`- or `warning`-bearing terms across all 295 FIBO modules and all 22 Commons modules. The nearest thing in the credit space, `fibo-fbc-dae-crt:AlertCreditMessage`, is an `owl:NamedIndividual` of `CreditMessageType` — a consumer-credit-bureau message code, not a class and not a surveillance signal |
| `SignalSource` | class | `http://example.org/fibo/SignalSource` | same zero result. FIBO's `…Provider` classes (`fibo-be-fct-pub:MarketDataProvider` and siblings) type a *vendor organisation*, not a feed a signal was derived from; `cmns-doc:hasDataSource` is a property, not a class, and hangs off documents |
| `signalAbout` | property | `http://example.org/fibo/signalAbout` | absent under this or any signal-bearing name. Its generic superproperty **does** exist — see below — but is not bound in its place |
| `triggeredBy` | property | `http://example.org/fibo/triggeredBy` | absent under this name. A same-shaped FIBO property exists and is **not** usable here — see below |
| `PriorObservation` | class | `http://example.org/fibo/PriorObservation` | **not one of the four candidates the task named** — found by widening the audit past them, see below. No `Observation` class exists in either corpus. `fibo-fnd-arr-asmt:ObservedValue` is `rdfs:subClassOf Value` — *"an actual data point collected from an experiment, survey, or observation"* — a measured value, not the per-obligor sweep watermark a delta anchor needs |

**A fifth term, found by not scoping the audit to the four named candidates.**
`ex:PriorObservation` is written by `loaders/load_fluree_wave11b.py` (design
§3.4, plan Step 3 of the loader task) as the one-per-obligor delta anchor, and
it appears in no candidate list. Enumerating every `ex:` token across
`docs/wave11b-plan.md` and `docs/wave11b-design.md` surfaced it. That widening is
the §0.2 lesson from `docs/known-issues.md`: §0.1 fixed the two ownership
*properties* it was pointed at and never re-checked the starter **classes**,
which were all wrong too — found hours later only because a full re-read was
forced. An audit scoped to its symptom finds its symptom. `PriorObservation` is
verified and bound here on the same evidence as the other four.

##### A sixth term — `ex:item` — found only by the whole-branch review

**Correction, 2026-08-21.** Until this date this register recorded **five**
Wave 11b terms, and `docs/known-issues.md` §10.7 stated *"None is Wave 11b's"*
of the unbound-term list. Both claims were false. `loaders/load_fluree_wave11b.py`
also asserts **`ex:item`** — live-verified at **535 triples across 409
`ex:SignalSource` nodes** — and it had no row here and no entry in
`sources/screening/published_claims.json`. It is bound below.

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `item` | property | `http://example.org/fibo/item` | a **literal attribute**, not an edge — the SEC Form 8-K **item code** (`1.01`, `2.03`, `2.04`, `4.01`, `4.02`, `5.02`) carried on the `ex:SignalSource` node — the filed event's own disclosure category. Re-checked offline against the same 295-module `edmcouncil/fibo` clone Task 1 used: **zero** terms whose local name is `item` (`rdf:about` / `rdf:ID`) and **zero** `rdfs:label` reading `item`; the only near neighbour is `fibo-loan-spc-prod:LineItem` (label *"line item"*), a loan-product line item, not a disclosure category. The string `8-K` does not occur anywhere in the corpus. Wave 8 and Wave 11a bound the two *classes* this wave layers on top of two of the codes (`ex:IssuanceEvent` for 2.03, `fibo-fnd-agr-ctr:BreachOfCovenant` for 2.04), but the SEC's item taxonomy itself is a US filing-form artefact with no FIBO vocabulary |

**Why a literal attribute gets a row when Wave 11a's did not.** The Wave 11a
paragraph above ruled that plain literal attributes — `ex:grade`, `ex:validFrom`,
`ex:sourceAccession` and the rest — are *not* added as binding-table rows, on the
Wave 5 `covenantType` / `threshold` / `observedValue` precedent. That precedent is
what hid `ex:item` for an entire wave, so it is **narrowed here rather than
restated**: an attribute earns a row when a downstream query **pivots on its
value**. `ex:item` does. It is the sole discriminator between the six 8-K event
kinds in Fluree; it decides which second `rdf:type` a signal carries (§4.2 of
`docs/wave11b-design.md`); and `ITEM_SEVERITY` in
`generators/generate_signals.py` scores directly off it. An SDK consumer that
cannot see `ex:item` in the mirror cannot ask this product's central question —
*which kind of filing raised this signal*. `ex:grade` is arguably the same shape;
it is deliberately **not** moved here, because it is Wave 11a's row and quietly
re-scoping another wave's decision under a Wave 11b heading is how this register
drifted in the first place.

**The guard that should have caught this was blind.**
`generators/verify_fibo_wave11b_confirm.py` decided "is this term bound?" with a
bare Python `in` against the raw text of this 1,700-line document. Any `ex:` term
whose local name is an ordinary English word therefore matched an unrelated prose
sentence and passed as bound. Three did: `item` — this wave's, bound above — and
two Wave 5 covenant attributes carrying 180 assertions each. The check now
requires a **backticked token** — `` `item` `` or `` `ex:item` `` — or the **full
IRI**.

The two Wave 5 terms are deliberately **not named here**, and that is not
squeamishness: under the tightened rule, writing either of them in a code span
*in this document* would make the check read them as bound again. They are named
in `docs/known-issues.md` §10.7 and frozen in the verifier's `KNOWN_UNBOUND`,
which is where Wave 5 debt belongs — this wave binds its own term and does not
quietly adopt another wave's. That the rule still cannot separate a binding-table
row from a deliberate code-span mention is the residual hole, measured and
recorded in §10.7 rather than left implicit.


**`triggeredBy` is not Wave-11b-only.** `docs/spec-digest.md` (line 346) records
`abs-securitization-surveillance` naming `triggeredBy` alongside `collateralizes`
and `subordinateTo`. The binding above therefore travels to that product; the
other two remain unbound and are that wave's problem, not this one's. Note that
FIBO *does* carry `fibo-sec-dbt-cdo:TriggerEvent` and
`fibo-sec-dbt-cdo:specifiesTrigger` (both bound, Wave 8) for the securitization
sense — a trigger *clause* and the *event kind* it names. Neither is an edge from
a signal to the concrete event that produced it, which is what `ex:triggeredBy`
is for.

##### Two real terms sit adjacent — checked, and deliberately not reused

**Prefix registration for the rejected terms.** The two rows below use compact
forms whose prefixes this document must still register, or a reader cannot
expand the IRI to check the rejection for themselves — which is the entire
value of recording a rejection. `cmns-doc` is already registered (§ Commons
factoring, above); `fibo-fnd-dt-oc` was not, and is added here:

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-fnd-dt-oc` | `https://spec.edmcouncil.org/fibo/ontology/FND/DatesAndTimes/Occurrences/` |

Registered for a **rejected** term, not a bound one. No triple in the estate
uses this prefix and none should; it is here so the rejection is checkable.
Registering a prefix is not binding a term.


Recorded on the `Covenant` precedent above, which names `NegativePledge` and
`BreachOfCovenant` as genuinely-applicable neighbours. These two are the
opposite case: real, findable, and wrong for this purpose. Recording *why*
stops the next reader re-finding them and assuming the extension was lazy.

| Real term | Full IRI | Why it is not the binding for our candidate |
| --- | --- | --- |
| `fibo-fnd-dt-oc:isTriggeredBy` | `https://spec.edmcouncil.org/fibo/ontology/FND/DatesAndTimes/Occurrences/isTriggeredBy` | `rdfs:domain` is `OccurrenceBasedDate` and `rdfs:range` is `OccurrenceKind` — and `OccurrenceBasedDate` carries an `owl:qualifiedCardinality` 1 restriction on it, so the property is *definitional* for that class. Asserting it from a `WarningSignal` to a filing entails, under any reasoner, that the signal is a **date** and its trigger is a **kind** rather than an instance. Both are false. Our need is signal → the concrete event that produced it |
| `cmns-doc:isAbout` | `https://www.omg.org/spec/Commons/Documents/isAbout` | genuine and generic — *"indicates the subject or topic of something, such as a document"*, with no `rdfs:domain` and no `rdfs:range`. It is the honest **conceptual superproperty** of `ex:signalAbout` and is recorded as such. It is not bound in its place for two reasons: query specificity — the product must ask *"which signals concern this obligor"* without also collecting document-aboutness edges, and Fluree runs without reasoning (CLAUDE.md), so a declared `rdfs:subPropertyOf` would buy nothing at query time; and coherence — the subject of the edge is `ex:WarningSignal`, itself an application extension, so a conformant-FIBO consumer would recognise the predicate but not the type, which is no gain in consumability |

`ex:signalAbout` is the closest call in this wave. It is flagged here rather
than buried so it can be cheaply overturned: if a later decision prefers the
Commons predicate, the change is one row and one loader constant.

##### Reused, not created — do not mint duplicates of these

Three needs in this wave are already bound. They are listed here because the
failure mode is a future reader minting `ex:supersedes`, `ex:DebtIssuance` or
`ex:CovenantBreach` beside terms that already exist and already carry data.

| Need in `credit-surveillance-early-warning` | Bind to | Status |
| --- | --- | --- |
| supersession of a warning list by a later one | `ex:supersededBy` → `http://example.org/fibo/supersededBy` | declared since Wave 5; **215 assertions** since Wave 11a. Do **not** mint `ex:supersedes` |
| Item 2.03 debt-issuance signal | `ex:IssuanceEvent` → `http://example.org/fibo/IssuanceEvent`, `ex:filedBy` → `http://example.org/fibo/filedBy` | bound in Wave 11a (§ above) |
| covenant breach *as* a signal | `fibo-fnd-agr-ctr:BreachOfCovenant` → `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Contracts/BreachOfCovenant` | a **real FIBO term**, bound in Wave 0. The covenant itself stays `ex:Covenant`; only the breach is FIBO |

Per §4.3 of `docs/wave11b-design.md` and CLAUDE.md rule 7, a node that is both a
`WarningSignal` and an `ex:IssuanceEvent` — or a `BreachOfCovenant` — carries
**both** `rdf:type` assertions explicitly. Neither is inferred from the other.

**Vault mirror.** All **six** — the five above plus `ex:item` — are outstanding
mirror drift (this paragraph read *"All five"* until 2026-08-21):
`wiki/context-products/content/fibo-iri-binding` does not carry them, this repo
is source of truth, and the mirror is refreshed by the custodian, never by us.
They are recorded in `sources/screening/published_claims.json` with
`claim: not_materialized`, which is the established convention for vault silence
rather than a read (see that file's `_verified_against`).

**They will read as AGREE in `validators/binding_drift.py` until a loader runs,
and that is not a bug.** This wave binds before it generates, so the estate holds
nothing against these IRIs yet; `not_materialized` + an empty estate is a genuine
agreement. The verdicts flip to `CAVEAT_STALE` the moment
`loaders/load_fluree_wave11b.py` lands, and *that* flip is the punch list
generating itself. Recording the terms now is what makes the flip automatic
instead of remembered.

A punch list covering this register — the Wave 10 terms as new drift, the
still-open Wave 9 `DepositAccount` item, and the three-wave pattern above — was
sent to the vault custodian through the agent exchange on 2026-08-18. See
`docs/known-issues.md` §8 and `docs/HANDOFF.md` for the estate counts these
terms carry. **That punch list predates Waves 11a and 11b** and covers neither;
their terms are outstanding mirror drift and need a punch list of their own.

#### Wave 12 — regulatory posture overlay (`treasury-liquidity-position`)

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `RegulatoryPosture` | class | `http://example.org/fibo/RegulatoryPosture` | checked (`RegulatoryPosture`, `RegulatoryClassification`, `RegulatoryRegime`, `JurisdictionalRestriction`, `ComplianceRequirement`): zero hits anywhere in the `edmcouncil/fibo` clone. FIBO models the instrument and the agreement, not a bank's internal jurisdiction/intent posture classification — same recurring shape as `Covenant`, the Wave 9 set-off relations, and Wave 10's coverage/interaction terms |

**Reused, not created:** every `RegulatoryPosture` node also carries
`ex:PolicyVersion` (Wave 5) as a second type — a regulatory posture genuinely
IS a policy version, and the T-box is not redeclared, exactly Wave 11b's
precedent for reusing `ex:IssuanceEvent`. `ex:supersededBy` (Wave 5; 751
assertions in the ledger as of this wave) chains the one engineered version
pair (`(US-NY, reserve-buffer)`, `standard` -> `enhanced-scrutiny`,
2026-06-16) — no new predicate minted for the time-versioning itself.

**Vault mirror.** New since the Wave 8 binding the vault mirror carries;
stale until refreshed. Sent through the agent exchange, not edited in the
vault directly.

#### Wave 18 extension — `syndicated-lending-co-lender`

**Added 2026-08-25 (Task 4, fix round 1).** The 17 FIBO terms below were
confirmed **declared in subject position** in
`sources/fibo/dev.fibo-quickstart.ttl` (`dev`, not `prod` —
`prod.fibo-quickstart.ttl` omits 40 modules, several of which this project
already binds) by `generators/verify_fibo_wave18.py` — **17/17 confirmed, 0
missing**. No `spec.edmcouncil.org` URL was fetched: that endpoint returns
HTTP 200 for names that do not exist, so the only honest check is a grep of
the offline ontology for the IRI in subject position (the term opening its
own Turtle block), never a substring match anywhere in the file.

**Fix round 1 also added 3 `ex:` local names — `SyndicateParticipation`,
`participationOf`, `participationIn` — for the reified commitment-share
node Task 8 builds.** A share is member + facility + amount + filing offset,
an n-ary fact a binary predicate cannot express, so the share needs its own
node with a type and two connecting predicates. The same script checked all
three absent from the ontology **under every prefix**, not only the ones
this task otherwise queries, before minting them — a bare local-name
collision under an unrelated FIBO module would be exactly as wrong as
reusing `administeredBy`'s local name almost was. Machine-readable evidence
for both passes is the script's own printed output, reproduced in
`.superpowers/sdd/wave18-plan/task-4-report.md`.

`SyndicatedLoan`, `FinanceSyndicate`, `FinanceSyndicateMember`,
`AdministrativeAgent`, `LeadArranger`, `SyndicationAgent` and
`LoanParticipationNote` were already bound in the Wave 0 extension table
above and are **re-confirmed here**, unchanged. Three classes and one
membership property were missing and are added now:

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| Bookrunner | `fibo-sec-dbt-dln:Bookrunner` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/Bookrunner` |
| DocumentationAgent | `fibo-sec-dbt-dln:DocumentationAgent` | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/DocumentationAgent` |
| Commitment | `fibo-fnd-agr-agr:Commitment` | `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Agreements/Commitment` — `rdfs:subClassOf cmns-pts:Situation`; a promise-to-act. The commitment SHARE amount (a dollar figure per member) has no FIBO property — it stays `ex:commitmentUsd` on the reified participation edge, see below |

New prefix: `fibo-fnd-agr-agr` → `https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Agreements/`.

**Open question #1, settled: membership uses FIBO-native `cmns-col:isMemberOf`.
Nothing is minted for it.**

`fibo-sec-dbt-dln:FinanceSyndicateMember`'s own OWL restriction reads:

```
rdfs:subClassOf
    fibo-be-fct-fct:SyndicateMember ,
    fibo-fbc-pas-fpas:FinancialServiceProvider ,
    [ a owl:Restriction ;
      owl:onProperty cmns-rlcmp:isPlayedBy ;
      owl:someValuesFrom [
          a owl:Restriction ;
          owl:onProperty cmns-col:isMemberOf ;
          owl:allValuesFrom fibo-sec-dbt-dln:FinanceSyndicate ;
      ] ;
    ]
```

and, independently, `fibo-be-fct-fct:Syndicate` (the parent of
`FinanceSyndicate`) carries `rdfs:subClassOf [ owl:onProperty
cmns-col:hasMember ; owl:someValuesFrom cmns-pts:Party ]` —
`cmns-col:hasMember`'s declared `owl:inverseOf` is `cmns-col:isMemberOf`, so
both anchor points independently converge on the same property. Checked
`cmns-col:isMemberOf` itself: `rdfs:subPropertyOf cmns-col:isIncludedIn`,
`owl:inverseOf cmns-col:hasMember`, **no `rdfs:domain` or `rdfs:range`
declared** — nothing restricts its use to something incompatible with a
financial institution or a syndicate. **Decision: adopt `cmns-col:isMemberOf`
directly** — `institution cmns-col:isMemberOf syndicate`. No `ex:participatesIn`
is minted; the reified participation node that carries the commitment share
(Task 8) is a separate concern from the plain membership edge.

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| isMemberOf | `cmns-col:isMemberOf` | `https://www.omg.org/spec/Commons/Collections/isMemberOf` |

**Open question #2, settled: `administeredBy` is minted under `ex:`. Two FIBO
candidates were checked and both rejected — domain/range evidence below.**

| Candidate | `rdfs:domain` | `rdfs:range` | Verdict |
| --- | --- | --- | --- |
| `fibo-loan-ln-reg:administeredBy` | `fibo-loan-ln-reg:LoanRegulatoryRequirement` | `cmns-rga:RegulatoryAgency` | **Rejected.** A regulator overseeing a rule, not a facility's admin agent. The local name reads perfectly and the semantics are unrelated — CLAUDE.md's *"module membership does not pin an IRI"*, in property form |
| `fibo-sec-fund-civ:administeredBy` | `fibo-sec-sec-pls:CollectiveInvestmentVehicle` | `fibo-sec-fund-fund:FundAdministrator` | **Rejected.** Found while checking the first candidate — same local name, different module (`SEC/Funds/CollectiveInvestmentVehicles/`). A fund's administrator, not a syndicated facility's |

Neither candidate's domain admits a `SyndicatedLoan`. No FIBO property was
found whose domain does. `ex:administeredBy` is minted for the facility →
agent-institution edge.

**`ex:` terms minted this task (16, across both passes)**, for Tasks 8–10 and 14–16:

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `administeredBy` | property | `http://example.org/fibo/administeredBy` | both FIBO candidates checked and rejected above — neither domain admits a credit facility |
| `commitmentUsd` | property | `http://example.org/fibo/commitmentUsd` | the commitment SHARE amount on a reified participation edge; FIBO's `Commitment` class has no amount property |
| `sourcePassage` | property | `http://example.org/fibo/sourcePassage` | links a commitment-share edge to the Mongo passage its figure was read from; no FIBO equivalent |
| `SyndicateParticipation` | class | `http://example.org/fibo/SyndicateParticipation` | **Fix round 1 (T4-R1).** The reified node type for a commitment share — member, facility, amount, and the filing offset it was read from is an n-ary fact a binary predicate cannot express, so it gets its own node. Fluree runs without OWL inference (CLAUDE.md rule 7): a query for participations must find only nodes explicitly typed as one, so the type cannot be left implicit. Checked absent from the ontology under every prefix by `generators/verify_fibo_wave18.py` before minting |
| `participationOf` | property | `http://example.org/fibo/participationOf` | **Fix round 1 (T4-R1).** `SyndicateParticipation` node → the `FinanceSyndicateMember` it belongs to. Checked absent from the ontology under every prefix before minting |
| `participationIn` | property | `http://example.org/fibo/participationIn` | **Fix round 1 (T4-R1).** `SyndicateParticipation` node → the `fibo-sec-dbt-dln:SyndicatedLoan` it is a share of. Checked absent from the ontology under every prefix before minting |
| `votesOn` | property | `http://example.org/fibo/votesOn` | live amendment vote edge, syndicate member → the `ex:AmendmentVote` under vote (corrected below, Task 9 — this row originally said `ex:Amendment`, written before the class it actually points at existed); no FIBO voting vocabulary in scope |
| `votePosture` | property | `http://example.org/fibo/votePosture` | the member's stated position on the vote (§F: "≥ 1 live vote, divergent postures"); no FIBO equivalent |
| `sharesCollateralWith` | property | `http://example.org/fibo/sharesCollateralWith` | **bound, deliberately NOT populated.** Appears in the spec's §B relationship list; nothing in §C or §F requires an edge and no current data supports one. Bound here so a later reader does not mistake the absence for an oversight — see `docs/wave18-design.md` §10 |
| `DisclosureEnvelope` | class | `http://example.org/fibo/DisclosureEnvelope` | the bilateral, versioned `P`/`T` disclosure record between counterparties; no FIBO federation/disclosure vocabulary exists |
| `requestScope` | property | `http://example.org/fibo/requestScope` | what a counterparty asked to see, on a `DisclosureEnvelope` |
| `discloseScope` | property | `http://example.org/fibo/discloseScope` | what was actually disclosed — §F's asymmetric-envelope floor recomputes `requestScope ≠ discloseScope` as sets |
| `declaredTtlSeconds` | property | `http://example.org/fibo/declaredTtlSeconds` | a product declaration's stated TTL, ours and the peer's; §F recomputes `min(remote TTL) < local TTL` from this same property on both sides |
| `attestation` | property | `http://example.org/fibo/attestation` | an attestation record on a position; §F's unattested-claim floor is proven by this property's genuine absence, not a boolean flag |
| `declaredLatencyMs` | property | `http://example.org/fibo/declaredLatencyMs` | a peer product declaration's stated response latency; §F's timeout floor recomputes this against the caller's bound |
| `disclosurePrecision` | property | `http://example.org/fibo/disclosurePrecision` | `exact` or `band`, on a peer position; §F's mixed-precision floor recomputes from the underlying value's shape, never by reading this flag alone (a lesson this estate has paid for before — *"tolerance wider than the bias"*, *"gate blind to its own population"*) |

**Vault mirror.** All 20 terms above (3 new FIBO classes, 1 FIBO membership
property adopted, 16 `ex:` terms minted — 13 from the first pass plus 3 from
fix round 1) are new since the Wave 12 binding the vault mirror carries.
Sent through the agent exchange (a second, corrected bundle superseding the
first — see below), not edited in the vault directly.

**Added 2026-08-26 (Task 9) — the live amendment vote.** Four more `ex:`
local names, verified absent from the ontology under every prefix by the
same `generators/verify_fibo_wave18.py` (re-run for this task) — **7/7
`ex:` terms confirmed absent across both runs (0 collisions), 17/17 FIBO
terms still declared**:

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `AmendmentEvent` | class | `http://example.org/fibo/AmendmentEvent` | a dated, filed amendment/restatement event on a Wave 18 facility. **Deliberately distinct from `ex:Amendment`** (Wave 5, `loaders/load_temporal_wave5.py`, 25 assertions — covenant-in-force-as-of's own bitemporal chain with `bookingLagDays`/`isEngineeredBookingLag` semantics that do not apply here). Reusing that class would inflate a different product's population with facilities it never touches |
| `effectiveDate` | property | `http://example.org/fibo/effectiveDate` | a literal ISO date on an `AmendmentEvent`. `fibo-fnd-agr-ctr:hasEffectiveDate` **was found** (`dev.fibo-quickstart.ttl` ~line 166479) but rejected: it is an `owl:ObjectProperty` ranging over the reified class `cmns-dt:Date` (a date NODE with its own `hasDateValue` literal), not a literal string. Every temporal predicate this estate has ever written (`ex:validFrom`, `ex:assertedAt`, Wave 5/6/7's own effective-date fields) carries a plain ISO literal instead; the one reified exception here would buy nothing but inconsistency — CLAUDE.md's *"module membership does not pin an IRI"*, in property form again |
| `AmendmentVote` | class | `http://example.org/fibo/AmendmentVote` | the live, open vote node itself — distinct from a dated `AmendmentEvent` because a vote in progress has no effective date yet (Task 9 declines to invent one, the same discipline Task 6 applied to a missing filed position) |
| `voteState` | property | `http://example.org/fibo/voteState` | `"open"` (the only value used this wave) on an `AmendmentVote` node |

`ex:amends` (bound above, Wave 5/11c, `http://example.org/fibo/amends`) is
**reused, not re-minted** — `AmendmentEvent → facility` and `AmendmentVote →
facility` both use the same predicate Wave 5 already binds for "links the
amendment event to the facility it amends"; disjoint subjects (`AMD-*` there
vs. this task's `ex:syndicate/amendment/*` and `ex:syndicate/vote/*` nodes),
no domain/range restriction of its own to violate.

**Vault mirror needs refreshing for these four terms**, plus the corrected
`votesOn` description above. Sent through the agent exchange, not edited in
the vault directly.

**Added 2026-08-26 (Task 10) — the two bilateral disclosure envelopes.** Two
more `ex:` local names, verified absent from the ontology under every prefix
by the same `generators/verify_fibo_wave18.py` (re-run for this task) —
**9/9 `ex:` terms confirmed absent across all three runs (0 collisions),
17/17 FIBO terms still declared**:

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `envelopeVersion` | property | `http://example.org/fibo/envelopeVersion` | a version label literal on a `DisclosureEnvelope` node. No existing predicate carries a bare version LABEL on an arbitrary node — the `PolicyVersion` pattern (Waves 5/12/13a) models version as its own NODE type, a different shape |
| `counterparty` | property | `http://example.org/fibo/counterparty` | `DisclosureEnvelope` → the `FinanceSyndicateMember` it is negotiated with. `fibo-fnd-agr-ctr:Counterparty` (a real, declared FIBO class, noted but deliberately unused in the Wave 0 section above) is a PARTY ROLE, not a predicate — it cannot supply the edge itself |

**`ex:validFrom` (bound Wave 11c) is reused, not re-minted, for the
envelope's temporal axis** — §C assigns the envelope `P` **and** `T`. An
earlier Wave 14 draft tried exactly the spelling `ex:effectiveFrom` for a
different node's valid-time start and it was corrected before any write —
*"a second spelling in an append-only store is not a synonym: it is a
predicate half the estate's queries miss"* (Wave 14 section, above).
`ex:effectiveDate` (Task 9, immediately above) is deliberately NOT reused
here either: it is scoped to `AmendmentEvent`'s filed, public date, kept
apart from `ex:Amendment`/`ex:validFrom` specifically to avoid inflating
that product's population — reusing it on an unrelated synthetic-internal
node would blur that same scoping rather than honour it. See
`ccf/syndicate.py::EX_VALID_FROM`'s docstring for the full reasoning.

Two envelope nodes loaded — Bank of America (exact precision, primary
co-lender) and Citibank (band precision) — each carrying `ex:counterparty`,
`ex:requestScope` (repeated), `ex:discloseScope` (repeated),
`ex:envelopeVersion`, `ex:validFrom`, and `ex:provenance = "synthetic —
internal"`. Both envelopes' request/disclose scopes differ as sets from
each other's, and the request scope differs from the disclose scope on
each envelope individually — §F's "≥ 2 asymmetric envelopes" floor.

**Vault mirror needs refreshing for these two terms**, plus the corrected
`validFrom` assertion count above. Sent through the agent exchange, not
edited in the vault directly.

**Added 2026-08-26 (Task 11b) — the R half of "Voting thresholds and
amendment mechanics".** §C assigns this element to BOTH MongoDB (`L`, Task
11 — the filed article text, span offsets) and Fluree (`R`, this task — a
typed relationship). Task 11 built only the first half; no task's brief
covered the second, so the element sat half-delivered. This task also
supplies the data needed to evaluate the live amendment vote on
`FAC-A4A5EE` (Task 9) against a real threshold — Task 16 builds the check;
this only supplies what it checks against.

Five more `ex:` local names, verified absent from the ontology under every
prefix by the same `generators/verify_fibo_wave18.py` (re-run for this
task, its own `EX_MINTED_CHECKED_ABSENT` manifest extended) — **14/14
`ex:` terms confirmed absent across all four runs (0 collisions), 17/17
FIBO terms still declared**. No vote/consent/threshold/quorum/majority
vocabulary exists anywhere in the ontology (checked under every prefix in
subject position), and neither `SEC/Debt/DistributedLoans/` nor
`FND/Agreements/Contracts/` (this estate's other agreement-law module, ~40
declared classes — `ExtensionProvision`, `NettingProvision`,
`DisclosureProvision`, `TerminationProvision`, ...) has an amendment- or
consent-provision class:

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `AmendmentThreshold` | class | `http://example.org/fibo/AmendmentThreshold` | one node per (agreement, consent-standard bucket) — see the node-shape note below |
| `consentStandard` | property | `http://example.org/fibo/consentStandard` | the standard a filing names — `"Required Lenders"`, `"Required Class A/B Lenders"`, `"each affected Lender"`, `"each Class A/B Lender"`, `"all Lenders"` — a small, closed, cross-document vocabulary |
| `consentPercent` | property | `http://example.org/fibo/consentPercent` | the numeric percentage a filing states, present ONLY for the three percentage-of-exposure standards; never invented for a per-Lender veto standard — no filing among the six expresses "each affected Lender" or "all Lenders" as a percentage of anything |
| `amendmentType` | property | `http://example.org/fibo/amendmentType` | which kinds of amendment/waiver require this standard, drawn from the filing's own enumerated carve-out list |
| `thresholdGoverns` | property | `http://example.org/fibo/thresholdGoverns` | `AmendmentThreshold` → the `SyndicatedLoan` facility it governs. **Two real, declared FIBO/Commons properties were checked and rejected for the bare word "governs"**: `cmns-rga:governs` ("has and exercises authority over" — a regulator/polity over a jurisdiction) and `fibo-fnd-txn-sec:governs` (a `SecuritiesTransactionContract` over a secondary-market transaction, `rdfs:subPropertyOf cmns-rga:governs`) — both real, neither domain admits a credit facility. `cmns-cxtdsg:appliesTo` was checked and rejected too, same shape. `thresholdGoverns` avoids the local-name collision outright — this project's own absence-check discipline polices the bare local name across every prefix, not only the ones a task otherwise queries, so a term that reads right cannot silently borrow a real term's shape |

`ex:sourcePassage` (bound Task 8) is **reused, not re-minted** — but its
value on a threshold node is deliberately the SAME raw
`f"{document}#offset={start}-{end}"` string Task 8 uses for commitment
shares, not Task 11's real Mongo `passage_id`. Measured before deciding:
the percentage that names each standard is always defined in the
document's own defined-terms article, never inside Task 11's captured
`voting_threshold` passage in any of the six documents; in two of six
(Bausch, Paychex) even the elevated carve-out clause itself falls just past
that passage's own end offset. A single citation field cannot honestly
point at a real Mongo passage for some threshold nodes and a document
region outside any passage for others — citing the raw document+offset
uniformly is the one scheme true for all sixteen, and it is exactly the
standard this task's own dispatch names as the bar to clear: traceable
"exactly as the commitment shares are." (Fix round 1, 2026-08-26:
`extract_carveouts()` had a citation bug on 4 of 16 nodes — first-match-
anywhere-in-the-document instead of scoped-to-the-article — corrected by
scoping the search to each document's own located voting/amendment
article; this inside/outside conclusion is unchanged but is now verified
against the regenerated artifact, not a human read of the filings. See
`task-11b-findings-r1.md` / `task-11b-report.md`'s "Fix round 1" section.)

**Node shape.** One `ex:AmendmentThreshold` node per (agreement,
consent-standard bucket) — most agreements carry two (a base "Required
Lenders" majority standard plus one elevated "each affected Lender"
carve-out), Paychex carries three and Sabre carries five, because those two
filings state genuinely distinct standards for genuinely distinct kinds of
amendment (Sabre: `Required Class A Lenders` / `Required Class B Lenders` /
`each Class A Lender` / `each Class B Lender` / `all Lenders`) rather than
one flat rule. **16 threshold nodes total across the six agreements, 7 of
which carry `consentPercent`** (the five flat "Required Lenders" documents
plus Sabre's Class A and Class B); the other 9 are per-Lender veto
standards with a named standard and no percentage. Every node links to
every facility the tranche map lists for that agreement, via
`ccf.syndicate.TRANCHE_TO_FACILITIES` (imported, never re-derived) — not
necessarily every Wave 18 facility that agreement carries: Regis carries
four Wave 18 facilities, but only the two `TRANCHE_TO_FACILITIES` lists
(`FAC-01BB3F`, `FAC-5F29AF`) are governed — 24 `thresholdGoverns` edges
total. `FAC-A4A5EE`, the facility carrying Task 9's
live open vote, is governed by 2 of the 16 nodes (RB Global's
`required-lenders`, 50%, and `each-affected-lender`), so the vote now has a
real threshold to be evaluated against — the evaluation itself is Task 16's
build-time check, not stored here (CLAUDE.md: recomputed from the stores,
never a cached outcome).

**One inherited minor folded in.** Task 11's `extract_one` ("record no
passage if the article is absent") had zero test coverage because the real
corpus happens to have zero absent cases — a regression there would have
been caught by neither the data nor any test. `validators/test_syndicate.py
::test_extract_one_records_absence_and_emits_no_passage_when_heading_missing`
adds the missing fixture.

**Vault mirror needs refreshing for these five terms.** Sent through the
agent exchange (a bundle superseding
`2026-08-26T18-38-29Z-wave18-task10-envelope-bindings`), not edited in the
vault directly.

#### Wave 19 extension — `large-exposure-rwa-concentration`

**Added 2026-08-27 (Task 3).** 11 FIBO terms confirmed **declared in subject
position** in `sources/fibo/dev.fibo-quickstart.ttl` (`dev`, not `prod`) by
`generators/verify_fibo_wave19.py` — **11/11 confirmed, 0 missing** — plus a
`KNOWN_PRESENT` matcher control (8 terms, all found) copied from the design
session's own recorded failure: an earlier absence check regexed for a
trailing space and returned "0 hits" for every candidate including `Exposure`
and `Capital`, both plainly declared, because a declaration puts the qname
alone on the line. No `spec.edmcouncil.org` URL was fetched.

##### Prefixes added

| Prefix | Namespace IRI |
| --- | --- |
| `fibo-be-oac-cpty` | `https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/ControlParties/` |
| `fibo-fbc-fct-fse` | `https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/` |
| `fibo-fbc-fct-usfse` | `https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/NorthAmericanEntities/USFinancialServicesEntities/` |

(`fibo-fbc-pas-fpas` is already bound — Wave 8 addition, above.)

##### FIBO class/property bindings added

| Local name | Prefix form | Full IRI | Domain / range (properties) | Role |
| --- | --- | --- | --- | --- |
| Exposure | `fibo-fbc-pas-fpas:Exposure` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/Exposure` | `rdfs:subClassOf cmns-pts:Undergoer` | the exposure amount node |
| ExposureBearer | `fibo-fbc-pas-fpas:ExposureBearer` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/ExposureBearer` | `rdfs:subClassOf cmns-pts:Actor` | the role a bank/obligor plays bearing an exposure |
| ExposureSituation | `fibo-fbc-pas-fpas:ExposureSituation` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/ExposureSituation` | `rdfs:subClassOf cmns-pts:Situation` | **the reification node** — see below |
| hasExposureTo | `fibo-fbc-pas-fpas:hasExposureTo` | `.../FBC/ProductsAndServices/FinancialProductsAndServices/hasExposureTo` | domain `ExposureSituation`, range `Exposure` | connects the situation to the amount, NOT the bearer directly |
| ContractualControl | `fibo-be-oac-cpty:ContractualControl` | `.../BE/OwnershipAndControl/ControlParties/ContractualControl` | `rdfs:subClassOf fibo-fnd-oac-ctl:DeJureControl` | the control leg of a "connected clients" pair |
| MajorityControllingParty | `fibo-be-oac-cpty:MajorityControllingParty` | `.../BE/OwnershipAndControl/ControlParties/MajorityControllingParty` | `rdfs:subClassOf fibo-be-oac-cpty:EntityControllingParty` | the controlling-party role for the control leg |
| Bank | `fibo-fbc-fct-fse:Bank` | `.../FBC/FunctionalEntities/FinancialServicesEntities/Bank` | `rdfs:subClassOf fibo-fbc-fct-fse:DepositoryInstitution` | generic bank type (Task 5) |
| BankHoldingCompany | `fibo-fbc-fct-fse:BankHoldingCompany` | `.../FBC/FunctionalEntities/FinancialServicesEntities/BankHoldingCompany` | `rdfs:subClassOf fibo-fbc-fct-fse:HoldingCompany, fibo-fbc-pas-fpas:FinancialServiceProvider` | bank holding company type (Task 5) |
| NationalBank | `fibo-fbc-fct-usfse:NationalBank` | `.../FBC/FunctionalEntities/NorthAmericanEntities/USFinancialServicesEntities/NationalBank` | `rdfs:subClassOf fibo-fbc-fct-fse:CommercialBank, fibo-fbc-fct-usfse:USBank, fibo-fbc-fct-usjrga:FederalReserveSystemMember` | US national bank charter type (Task 5) |
| isConsolidatedBy | `fibo-be-le-lei:isConsolidatedBy` | `.../BE/LegalEntities/LEIEntities/isConsolidatedBy` | `rdfs:range cmns-org:LegalEntity` | superproperty only — not asserted as data, declared so the two subproperties' `subPropertyOf` axiom resolves (Task 6) |
| isDirectlyConsolidatedBy | `fibo-be-le-lei:isDirectlyConsolidatedBy` | `.../BE/LegalEntities/LEIEntities/isDirectlyConsolidatedBy` | `rdfs:subPropertyOf isConsolidatedBy`, range `cmns-org:LegalEntity` | GLEIF RR-CDF's `IS_DIRECTLY_CONSOLIDATED_BY`, subject = child (Task 6) |
| isUltimatelyConsolidatedBy | `fibo-be-le-lei:isUltimatelyConsolidatedBy` | `.../BE/LegalEntities/LEIEntities/isUltimatelyConsolidatedBy` | `rdfs:subPropertyOf isConsolidatedBy`, range `cmns-org:LegalEntity` | GLEIF RR-CDF's `IS_ULTIMATELY_CONSOLIDATED_BY`, subject = child (Task 6) |

**Task 6 finding: Task 3's verification pass missed these three.** All
three are declared `owl:ObjectProperty` in `sources/fibo/dev.fibo-quickstart.ttl`
(`fibo-be-le-lei:` = `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/`),
each carrying `cmns-av:adaptedFrom "GLEIF Level 2 Relationship Record (RR)
Common Data Format (CDF)..."` — the exact source `ccf_v2.corporate_ownership_record`
was built from. Task 3 searched `isConnectedWith` / `connectedWith` /
`isRelatedTo` while looking for the `ConnectedGroup` member edge and never
tried the consolidation vocabulary. Used here as the predicate that carries
GLEIF's relationship type onto each `connectedTo` edge — see
`loaders/load_group_edges.py`'s docstring for why a predicate choice was
used instead of a reified node or a node-level literal. **Vault mirror
needs refreshing for these three terms too.**

**`hasExposureTo`'s domain is `ExposureSituation`, not `ExposureBearer` or a
bare `Party`.** Loading an exposure edge means an `ExposureSituation` node
sits between the bearer and the `Exposure` amount — the same reified shape
Wave 18 used for `SyndicateParticipation`. A direct `ExposureBearer ->
Exposure` triple would use a predicate whose declared domain does not admit
the subject; recorded here so a later task does not skip the situation node.

**`subsidiaryOf` — checked, and REUSED rather than minted.** The brief's
candidate list for `ex:` minting included a bare `subsidiaryOf` for the
`ConnectedGroup` control-by-ownership edge. FIBO already declares this exact
relation, and this project already binds it (Wave 8, above):

| Local name | Prefix form | Full IRI | Domain / range |
| --- | --- | --- | --- |
| hasSubsidiary *(reused)* | `fibo-be-oac-cctl:hasSubsidiary` | `.../BE/OwnershipAndControl/CorporateControl/hasSubsidiary` | domain `cmns-org:LegalEntity`, range `fibo-be-oac-cctl:Subsidiary` |

`hasSubsidiary` is preferred over its own inverse `isSubsidiaryOf` (domain
`Subsidiary`, range `ControllingAffiliate` — both role classes) because its
domain is the plain `cmns-org:LegalEntity` type nodes already carry, the same
role-typed-range/direct-entity-domain shape this estate already uses for
`hasGlobalUltimateParent` / `hasDomesticUltimateParent` without separately
instantiating the intermediate role individual. Minting `ex:subsidiaryOf`
would have duplicated a predicate this estate already has bound and never
used (`validators/spec_coverage.py`'s `FAMILY_TREE` mapping already notes it
declared nowhere in the loaded graph) — reuse closes that gap instead of
widening it.

**Two "related party" traps checked and rejected**, same shape as Wave 18's
`administeredBy`: a name that reads right, wrong domain.

| Candidate | `rdfs:domain` | `rdfs:range` | Verdict |
| --- | --- | --- | --- |
| `cmns-pts:hasRelatedPartyRole` | `cmns-pts:PartyRole` | `cmns-pts:PartyRole` | **Rejected.** Role-to-role, no "economically connected clients" semantics, and nothing in this estate types a `PartyRole` individual for obligors |
| `fibo-sec-fund-civ:fundHasRelatedParty` | `fibo-sec-sec-pls:CollectiveInvestmentVehicle` | `fibo-sec-fund-civ:FundsProcessingParty` | **Rejected.** Scoped to a fund's processing party (administrator, transfer agent), not a bank's obligor book |

##### `ex:` terms minted this task (16), checked absent under every prefix

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `ConnectedGroup` | class | `http://example.org/fibo/ConnectedGroup` | the Basel "group of connected clients" grouping node; no FIBO class for this concept exists anywhere (checked `Connected*`, `GroupOfConnectedClients`, `RelatedParty*`, `AffiliatedParty*` — see the two rejected traps above) |
| `economicallyDependentOn` | property | `http://example.org/fibo/economicallyDependentOn` | the economic-dependency leg of "connected clients", distinct from the control leg (`ContractualControl`, FIBO-bound above). Checked `EconomicDependence`, `dependentOn`, `isDependentOn`, `hasDependency` — none declared |
| `connectedTo` | property | `http://example.org/fibo/connectedTo` | `ConnectedGroup` → member edge. Checked `isConnectedWith`, `connectedWith`, `isRelatedTo` — none declared |
| `governedByRegime` | property | `http://example.org/fibo/governedByRegime` | `LimitEnvelope` → the regulatory regime version it implements; no regime/version vocabulary exists anywhere in the ontology |
| `RegimeVersion` | class | `http://example.org/fibo/RegimeVersion` | a versioned large-exposure regulatory regime (e.g. Basel III large-exposure framework as of a date); no FIBO class for a regime's version |
| `LimitEnvelope` | class | `http://example.org/fibo/LimitEnvelope` | the node carrying `limitPctOfCapital` / `limitAbsoluteUsd` for a given regime version; no FIBO class bundles a concentration-limit pair this way |
| `InsiderDesignation` | class | `http://example.org/fibo/InsiderDesignation` | a designated-insider flag on a connected-group member, for insider-lending-limit purposes; checked `Insider*` under every prefix — none declared |
| `assertedBy` | property | `http://example.org/fibo/assertedBy` | who asserted a bitemporal fact (`ConnectedGroup` membership, `InsiderDesignation`); this estate's existing bitemporal predicates (`ex:validFrom`, `ex:assertedAt`) are all `ex:` already, no FIBO/PROV vocabulary is loaded here |
| `assertedOn` | property | `http://example.org/fibo/assertedOn` | literal date companion to `assertedBy` |
| `designatedPerson` | property | `http://example.org/fibo/designatedPerson` | `InsiderDesignation` → the `fibo-fnd-aap-ppl:Person` or `cmns-org:LegalEntity` it designates; no FIBO predicate names an insider designation's subject |
| `citesProvision` | property | `http://example.org/fibo/citesProvision` | links an `InsiderDesignation`/`LimitEnvelope` to the regulatory provision text it cites (a MongoDB passage); no citation/provision-reference vocabulary exists in this ontology |
| `effectiveFrom` | property | `http://example.org/fibo/effectiveFrom` | literal ISO date. Same reasoning Wave 18 recorded for `effectiveDate`: `fibo-fnd-agr-ctr:hasEffectiveDate` exists but ranges over the reified class `cmns-dt:Date`, not a literal — every temporal predicate this estate has written carries a plain literal instead |
| `effectiveTo` | property | `http://example.org/fibo/effectiveTo` | literal ISO date, companion to `effectiveFrom`, same reasoning |
| `limitPctOfCapital` | property | `http://example.org/fibo/limitPctOfCapital` | literal numeric percentage on a `LimitEnvelope`; no FIBO predicate carries a bare percentage-of-capital limit |
| `limitAbsoluteUsd` | property | `http://example.org/fibo/limitAbsoluteUsd` | literal numeric absolute-dollar limit on a `LimitEnvelope`, same reasoning |
| `rssd` | property | `http://example.org/fibo/rssd` | literal attribute carrying a bank's Federal Reserve RSSD ID, the same shape as the existing `ex:lei` attribute — an identifier value, not a FIBO relationship |
| `dependencyBasis` | property | `http://example.org/fibo/dependencyBasis` | **added Task 7, 2026-08-27.** Free-text literal naming what an `economicallyDependentOn` judgment rests on (supplier concentration, single-tenant lease, shared funding). Checked absent under every prefix via `verify_fibo_wave19.py`'s own `find_any_prefix_subject()` method before minting — no FIBO term for a dependency's evidentiary basis exists anywhere |
| `effectiveFromIsSnapshot` | property | `http://example.org/fibo/effectiveFromIsSnapshot` | **added Wave 19 final fix wave, 2026-08-27 (Minor 4).** Boolean literal, asserted only on the Reg O `RegimeVersion` node, marking that its `effectiveFrom` is the eCFR retrieval/"current as of" date rather than a verified statutory commencement date — CRR and PRA's `effectiveFrom` values are genuine and carry no such flag. No FIBO term distinguishes a retrieval-date snapshot bound from a commencement date; checked absent under every prefix the same way `dependencyBasis` was |

**Vault mirror needs refreshing for these terms** — all 11 FIBO
classes/properties above are new bindings (none were in the table before
this task: `Exposure`, `ExposureBearer`, `ExposureSituation`,
`hasExposureTo`, `ContractualControl`, `MajorityControllingParty`, `Bank`,
`BankHoldingCompany`, `NationalBank`, plus the reused-not-minted
`hasSubsidiary` reference), and 16 `ex:` terms minted. Not edited in the
vault directly; sent through the agent exchange.

**Task 7, 2026-08-27, adds a 17th `ex:` term** — `dependencyBasis` (row
above) — verified absent the same way, minted for the same reason
(`economicallyDependentOn`, `assertedBy`, `assertedOn` were already bound by
Task 3 and reused as-is, no re-minting). **Vault mirror needs refreshing for
`dependencyBasis`.**

**Wave 19 final fix wave, 2026-08-27, adds an 18th `ex:` term** —
`effectiveFromIsSnapshot` (row above), Minor 4's fix for the Reg O
`effectiveFrom` date reading like a genuine commencement date when it is
actually the eCFR retrieval date. Verified absent against
`dev.fibo-quickstart.ttl` via `find_any_prefix_subject()` the same way as
every other term in this table. **Vault mirror needs refreshing for
`effectiveFromIsSnapshot`.**

---

### Cross-backend relationship type strings

When mirroring out of RDF, loaders used these **stable string tokens** (not full IRIs) in document/column stores. SDK adapters should map both directions.


**Updated 2026-08-17 (Wave 8).** The ownership and control rows changed — the
IRIs they previously named do not exist in FIBO. See *"Wave 8 correction"* above.

| Logical edge | RDF full IRI (above)                            | Mongo / Postgres `type` | Neo4j relationship type |
| ------------ | ----------------------------------------------- | ----------------------- | ----------------------- |
| Ownership    | `.../FND/OwnershipAndControl/Ownership/owns`    | `owns`                  | `OWNS`                  |
| Control      | `.../FND/Relations/Relations/controls`          | `controls`              | `CONTROLS`              |
| Related      | `.../FND/Parties/Parties/isRelatedTo`           | `isRelatedTo`           | `IS_RELATED_TO`         |

> ⚠️ **Superseded tokens.** `hasOwnershipInterestIn` and
> `hasControllingInterestIn` were the tokens through Wave 7 and appear in
> `principal.permitted_edge_types` in any Postgres `ccf_v2` snapshot taken before
> 2026-08-17. An adapter reading an older snapshot must map them forward.




### Application (non-FIBO) predicates under `ex:`

These are **not** FIBO terms. They live under `http://example.org/fibo/` for KYC-style sample attributes. Do not conflate them with FIBO IRIs.

> **⚠ v1 RESIDUE — 14 of the 15 below are NOT MATERIALIZED, and should not be.**
> Measured against ledger `fibo-v2` at `t = 1474`, 2026-08-24: `ex:lei` carries
> 169 assertions and **every other predicate in this table carries zero.**
>
> That is correct, not a gap. Single-writer discipline puts entity attributes
> in Postgres — `legal_name`, `legal_jurisdiction`, `entity_status` and the
> rest are `ccf_v2.legal_entity` columns — and a Fluree node carries `lei`
> plus a display label and nothing else. These predicates are the **v1** shape,
> when every store mirrored the same content.
>
> **Why this matters more than a stale table usually would:** it sits inside
> *"Canonical FIBO IRI binding (SDK dependency)"*, so it reads as contract. A
> consumer building against `ex:legalName` gets an empty result from a store
> that is behaving exactly as designed — the worst kind of failure, because
> nothing is broken. Kept rather than deleted so the v1 names remain
> resolvable, and marked so nobody generates against them.


| Local name                                               | Full IRI                                                  |
| -------------------------------------------------------- | --------------------------------------------------------- |
| lei                                                      | `http://example.org/fibo/lei`                             |
| legalName                                                | `http://example.org/fibo/legalName`                       |
| jurisdiction                                             | `http://example.org/fibo/jurisdiction`                    |
| entityStatus                                             | `http://example.org/fibo/entityStatus`                    |
| clientType                                               | `http://example.org/fibo/clientType`                      |
| riskRating                                               | `http://example.org/fibo/riskRating`                      |
| kycStatus                                                | `http://example.org/fibo/kycStatus`                       |
| onboardingDate                                           | `http://example.org/fibo/onboardingDate`                  |
| fullName                                                 | `http://example.org/fibo/fullName`                        |
| nationality                                              | `http://example.org/fibo/nationality`                     |
| dateOfBirth                                              | `http://example.org/fibo/dateOfBirth`                     |
| role                                                     | `http://example.org/fibo/role`                            |
| ownershipPercent                                         | `http://example.org/fibo/ownershipPercent`                |
| hasRegisteredAddress                                     | `http://example.org/fibo/hasRegisteredAddress`            |
| hasBusinessAddress                                       | `http://example.org/fibo/hasBusinessAddress`              |
| (Address type, street, city, state, postalCode, country) | under `http://example.org/fibo/` as used in sample Turtle |




### Instance URI pattern


| Kind              | Pattern                               | Example                            |
| ----------------- | ------------------------------------- | ---------------------------------- |
| Sample individual | `http://example.org/fibo/{LocalName}` | `http://example.org/fibo/AcmeCorp` |




### Caveats for SDK authors

1. **Module ≠ IRI.** FIBO organizes terms into modules (FND, BE, etc.). The binding table above is what was **actually written into** `fibo-starter.ttl` and instance files—not a guarantee that every local name matches the latest FIBO Production file character-for-character without verification against [https://spec.edmcouncil.org/fibo/](https://spec.edmcouncil.org/fibo/) or the edmcouncil/fibo repo.
2. **Compact vs expanded.** Fluree SPARQL results sometimes returned compact forms (`rdfs:label`, `fibo-fnd-pty-pty:Party`). Transform scripts expand known prefixes; adapters should normalize to full IRIs before comparing across backends.
3. **Short type labels in Mongo/Neo4j.** After transform, `types` arrays often store the **last path segment** only (e.g. `Corporation`, `Party`), not the full IRI. Map back via this table when emitting RDF or SPARQL.
4. **If you realign to official FIBO.** Update this binding table first, then regenerate Turtle, re-export instances, and reload mirrors so all backends and the SDK stay aligned.

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

> **Superseded 2026-08-16.** The table above describes the v1 load and remains accurate for it. Going forward, identifiers split into two populations:
>
> | Population | Identifier | Rationale |
> |---|---|---|
> | **Public anchor obligors** (~50) | **Real GLEIF LEIs** | Several Context Product specs join public sources on LEI → CIK → ticker (GLEIF ↔ EDGAR). Made-up strings cannot join. |
> | **Invented entities** — the existing cast and all synthetic overlay | Synthetic identifiers in a **visibly distinct format** | So a real identifier is never mistaken for a fabricated one, in either direction. |
>
> Record the chosen synthetic format in this document once set. Real-LEI entities are `public` provenance and must carry a source and retrieval date; everything else is `synthetic — internal` or `synthetic — engineered`. See `CLAUDE.md` for the three-class provenance rule.

> **Set 2026-08-23 (Wave 14 Task 12).** The synthetic format is a **`SYN-`
> prefix with hyphens**, e.g. `SYN-SDART-2022-6`. A hyphen cannot occur in a
> real 20-character GLEIF LEI (`[A-Z0-9]` only), so the two populations can
> never be confused visually or by regex — the same guarantee the existing
> `CLI-NNNNNN` internal-client-id convention gives on the other side of the
> crosswalk.
>
> **First trigger: the three ABS deal trusts have no LEI.** Searched and not
> found — not in any prospectus, ABS-EE file or servicer report; no GLEIF
> record by exact legal name; a GLEIF fulltext search shows Santander and
> Toyota trusts registered for 2013–2017 vintages but **none for 2022 or
> 2024**. Per-trust LEI registration appears to have lapsed. The depositors
> have LEIs; the deal trusts do not. `crosswalk.lei` for each trust is
> `SYN-<deal_id>` — `SYN-SDART-2022-6`, `SYN-TAOT-2022-B`, `SYN-SDART-2024-1`
> — `cik` is the trust's real CIK from `sources/absee/deals.json`,
> `provenance` is `synthetic — internal`, and `source` records that no GLEIF
> record exists for the trust, verified against `api.gleif.org` on
> 2026-08-23.
>
> Two alternatives were considered and rejected:
> - **Crosswalk the depositors instead of the trusts.** The depositors (e.g.
>   Santander Consumer USA's securitization arm) do have real LEIs, but the
>   holdings, materialization policy and privacy constraints this wave loads
>   are all about the **trust** — the issuing entity — not its depositor.
>   Crosswalking the depositor would resolve the wrong entity.
> - **A zero-padded CIK as the identifier.** Rejected because a CIK is
>   already a public, numeric identifier with its own column (`crosswalk.cik`)
>   — encoding it a second time into `lei` would duplicate a fact under a
>   different name rather than supply the missing one, and a numeric string
>   is exactly the shape a real LEI segment can take, which is the ambiguity
>   this whole format exists to avoid.
>
> **Schema note.** `crosswalk.lei` and `legal_entity.lei` were `CHAR(20)`,
> sized for a real LEI's fixed width. A shorter synthetic value gets
> blank-padded by `CHAR(n)` and returned with the padding on every read —
> wrong for a value a consumer must match exactly. Both columns were widened
> to `VARCHAR(20)` (same 20-character ceiling, no padding) by
> `loaders/load_abs_overlay_wave14.py`; real, already-20-character LEIs are
> unaffected in content.

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

1. **Use the Canonical FIBO IRI binding table above** for types and core relationship predicates; do not invent new compact names without recording full IRIs in that table. Put application attributes under `http://example.org/fibo/` unless mapping to real FIBO properties.
2. ~~**Prefer synthetic instances** unless explicitly ingesting a named public dataset (e.g. GLEIF).~~ **Superseded 2026-08-16:** real GLEIF LEIs are now in scope for public anchor obligors, alongside synthetic identifiers for invented entities. Record the source and retrieval date for every public element.
3. ~~**Add data in Turtle**, then re-export instances → regenerate Mongo JSONL → reload Mongo / Neo4j / Postgres so all backends stay aligned.~~ **Superseded 2026-08-16:** the mirror model is retired. Each store is authoritative for its own slice; load each from its own generator rather than from a shared export. The validator's job is now to assert each store holds *the slice it owns and nothing it doesn't* — the inverse of what `compare_backends.py` did.
4. **Update this document** (especially the binding table, entity tables, file names, and counts) when the sample set or IRI contract changes.
5. **Do not assume OWL inference** across backends; type entities explicitly for each role you need to query (e.g. both `Corporation` and any app-level tags you filter on).
6. **SDK dependency:** treat this document's § Canonical FIBO IRI binding as a shared contract for adapters, SPARQL builders, and Neo4j/Mongo type strings. When extending FIBO coverage — Loans, Securities, Derivatives, FX, and Collateral modules are all required by the Context Product specs — **add to the binding table first**, then generate data against it. Verify each new term against [spec.edmcouncil.org/fibo](https://spec.edmcouncil.org/fibo/) or the `edmcouncil/fibo` repo; module membership does not pin an IRI.

---



## Explicitly not done in this prep

- Full FIBO Production or official Quickstart TTL bulk load
- ~~Live GLEIF or other public registry ingest~~ — **now in scope as of 2026-08-16.** GLEIF LEI data for public anchor obligors, plus EDGAR, UK Companies House PSC, OFAC, and the other sources named in the Context Product specs. Not done *in this prep*; required for the next one.
- Production-grade identity resolution or golden-record merging — *note:* the next phase deliberately introduces **imperfect** identity resolution (name variants, transliterations, and at least one false-positive pair), because a dataset where every name resolves cleanly makes the resolution logic untestable
- SQLite as a departmental store — **now in scope**; install required, local file, no server
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

### 2026-08-16 — decisions superseding parts of the above

| Decision | Effect |
|---|---|
| **Real GLEIF LEIs** for ~50 public anchor obligors | Enables LEI → CIK → ticker joins the Context Product specs require; invented entities keep synthetic identifiers in a distinct format |
| **Existing cast retained** | Acme et al. become the synthetic overlay; "ACME Corp" also matches the CCF whitepaper's own Chapter 8 worked example |
| **Mirror model retired** | Each store authoritative for its own slice; validator inverts to assert partition rather than agreement |
| **SQLite added** | Departmental store — restricted lists, covenant tracker, prospect notes, limit workbook. Install required |
| **Prior structure not binding** | Pipeline, file layout, and loaders may be redesigned. The IRI binding contract and instance URI pattern are preserved |

### 2026-08-16 — v2 namespaces on the shared host

v2 loads into **fresh namespaces beside v1**, never over it. Rollback is dropping one namespace per store, and v1 remains queryable for comparison.

| Store | v2 target | v1 (read-only) | Note |
|---|---|---|---|
| Fluree | ledger **`fibo-v2`** | `fibo:main` (t=5) | A separate *ledger*, not a branch. Aliases are `name:branch`, so `fibo:v2` would have been a branch of the v1 ledger. Fluree is append-only — a mistaken write could not be undone |
| Postgres | schema **`ccf_v2`** | `public` (14 / 16 rows) | |
| MongoDB | db **`fibo_v2`** | `fibo` (14 / 16 docs) | |
| SQLite | `./data/departmental.sqlite` | — | `sqlite3` 3.45.1 was already installed; only the DB file needed creating |

**The MongoDB host is shared with an unrelated live system.** `rtdetect` holds ~5.5M documents across 99 collections. `ccf/config.py` refuses writes to any database outside `fibo_v2` and deliberately exposes no database-enumeration helper — enumeration is how an unrelated system gets caught in a cleanup loop.

### 2026-08-16 — Neo4j resolved: DROPPED

The `CLAUDE.md` open decision ("keep Neo4j at all?") is closed: **Neo4j is not part of the v2 estate.** The fabric spans four stores — Fluree, Postgres, MongoDB, SQLite.

Evidence gathered before the decision, recorded because it explains what is being given up:

- Deployed instance is 2026.07.1 **community**. **GDS is not installed**, nor APOC. By Q019 §3's test — Neo4j earns its place only if a product needs graph algorithms Fluree lacks — it fails outright.
- Community edition supports **one user database**, so v2 could not have been isolated from v1 the way it is in every other store; only label-namespacing was available, which is weaker.
- Plain Cypher *would* have covered a real gap: Fluree's SPARQL 1.1 dropped bounded `{m,n}` property-path repetition, and Cypher expresses `*1..5` natively (verified against the v1 graph). That was the strongest argument for keeping it, and it was not strong enough to justify a fourth loader and a store that owns nothing.

**What replaces it.** Both capabilities move into code, and neither is difficult at this scale (~500 entities, ~800 edges):

| Need | Replacement |
|---|---|
| Depth-bounded traversal (`corporate-family-tree` `depth=1..5`) | Unioned fixed-length SPARQL patterns, or a recursive FlureeQL query |
| Cycle detection (`corporate-family-tree`, `kyc-refresh-beneficial-ownership`) | Tarjan's SCC in application code, with a visited set maintained by the traversal caller |

This matches Q019 §3's own note that cycle detection "moves into application code" under the Fluree preference, and `CLAUDE.md`'s observation that application-side detection is the cheaper alternative.

The v1 Neo4j graph (14 nodes / 16 relationships) is left untouched at `bolt://192.168.4.76:7687`. `NEO4J_*` entries remain in `.env.example` for that historical instance; no v2 code reads them.

### 2026-08-18 — Wave 10 complete: `client-360-coverage-graph`

**No new FIBO bindings.** Every term Wave 10 needed was already bound —
`Person`, `CorporateOfficer`, `isEmployedBy`, `isOfficerOf`, `isDirectorOf`
came from Wave 8's Ownership/Person/Officer extension. The binding table
itself is unchanged by this wave; what changed is that five bound terms now
carry real assertions ("materialized"), and six new `ex:` terms were minted
(see the extension register above). The vault mirror was flagged for
refresh through the agent exchange on 2026-08-18 — not applied by this
project, per the standing contract.

**Fluree `fibo-v2`:** t=303, 24,565 triples.

| Node type | Count | | Edge type | Count |
|---|---|---|---|---|
| Person | 704 | | isEmployedBy | 701 |
| CorporateOfficer | 323 | | isOfficerOf | 323 |
| Banker | 40 | | isDirectorOf | 435 |
| Interaction | 2,050 | | coversClient | 150 |
| Deal | 32 | | participatedIn | 8,032 |
| | | | relatedToDeal | 129 |

**Postgres `ccf_v2`:**

| Table | Rows | Note |
|---|---|---|
| `person` | 743 | 704 natural / 39 entity |
| `person_role` | 817 | |
| `person_name_variant` | 571 | |
| `person_crosswalk` | 1,315 | |
| `institutional_holder` | 22,476 | 13F, one quarter (`01mar2026-31may2026`), 4,044 distinct managers, 17,410 strong / 5,066 weak issuer-match band — see `known-issues.md` §8.3 for the `manager_cik` defect and §8.15 for the `/XX/` state-suffix issuer-normalisation fix |
| `banker` | 40 | |
| `coverage_assignment` | 150 | |
| `interaction` | 2,050 | |
| `interaction_participant` | 8,032 | |
| `scoring_weight` | 6 | |
| `context_debt` | 133 | roster members with no DEF 14A / 8-K rendering found. **Corrected 2026-08-22 from 136**, which no predicate over the tracked artifacts reproduces: 704 natural roster members − 571 distinct rendered `person_key`s = 133. 136 was most likely the whole table (these 133 plus covenant-shaped rows from Waves 6/9), which the old note mislabelled as all being roster members — see `known-issues.md` §12.9. `context_debt` is estate-wide; this row counts only the `subject_kind='person'` slice Wave 10 owns |
| `principal` | 3 | now carries `sees_need_to_know`; two public-side principals set `FALSE` |

**Sources fetched:** Form 4 — 7,874 filings across 50 issuers, 3 failures
(`known-issues.md` §8.9). DEF 14A — 48 filers (2 MLPs file none, expected).
8-K Item 5.02 — appointment metadata only. Form 13F — one quarter.

**Validators:** `partition.py` 13/13 · `conditions.py` 71 passed / 1 failed
(the deliberate `control-WITHOUT-ownership` gap, §0.4, still open) ·
`traversal.py` 5 clients over the 200-node limit, dense anchor at 524 nodes ·
`projection.py` exit 0 (Wave 7's MNPI wall survived the interaction table
growing 40x) · `bitemporal.py` 3/3 · `test_form4.py` 30/30, plus
`test_persons.py`, `test_renderings.py`, `test_resolve.py`,
`test_coverage_shape.py`.

Full defect record: `docs/known-issues.md` §8. Full estate map and next step:
`docs/HANDOFF.md`.

**Known limitations, defects found, and a full list of what is engineered rather than fetched: `docs/known-issues.md`.** Read it before treating any field as public.

### 2026-08-19 — Wave 11a Task 8: `loaders/load_fluree_wave11a.py`

**Two new prefixes, three real FIBO terms, one `ex:` extension** — see the
"CREDIT RATINGS / ISSUANCE" section above and the Wave 11a row in the `ex:`
extension register. `issuedBy` resolved to `fibo-fnd-rel-rel:isIssuedBy`; the
credit-grade class resolved to `fibo-fbc-dae-crt:OrganizationCreditRating`;
the market-observation class resolved to
`fibo-fnd-arr-rt:RatingAssessmentEvent`. All three verified by live fetch of
the Production RDF/XML, not guessed from module names.
**📤 The vault mirror needs refreshing** for these two prefixes, three
classes, `isIssuedBy`, `concernsParty`, and the new `ex:` pair
(`IssuanceEvent`, `filedBy`).

`ex:supersededBy` — declared since Wave 5, asserted zero times through Wave
10 — went from **0 to 215** on this load: every one of Task 6's 245 grade
assertions that carries a `supersedes` pointer now carries the corresponding
forward edge in Fluree.

**Fluree `fibo-v2`:** t=357 → t=373 on first load, 24,598 → 32,266 triples
(+7,668). Re-run without `--reconcile` advances `t` but holds the triple
count at 32,266 (verified). `--reconcile` retracts and rebuilds all 1,317
owned edges (60 `isIssuedBy` + 254 `concernsParty` + 215 `supersededBy` +
788 `filedBy`) and restores the same 32,266 — verified round-trip.

| Node type | Count | | Edge type | Count |
|---|---|---|---|---|
| DebtInstrument / CorporateBond | 60 | | isIssuedBy | 60 |
| CreditRating / OrganizationCreditRating | 245 | | concernsParty | 254 |
| RatingAssessmentEvent | 9 | | supersededBy | 215 |
| IssuanceEvent | 788 | | filedBy | 788 |

**`dangling` = 0**, checked live before writing a single triple: all 30
instrument/grade-obligor LEIs, all 50 issuance LEIs, and all 4 rating-action
LEIs already resolved via `entity_uri_by_lei()` — no edge points at a
constructed URI.

**Single-writer discipline, checked, not assumed.** `debt_instrument` and
`rating_scale` columns loaded into Postgres by Task 7 (`couponPct`,
`maturity`, `issueDate`, `faceAmountUsd`, `ratingBand`, `seniority`,
`tenorYears`, `notch`, `modifier`) never appear as a Fluree literal —
added to `validators/partition.py`'s `POSTGRES_OWNED_ATTRS` so this is
checked on every future run, not just this one. `ex:grade` is the one
exception, and it is not a leak: no Postgres table records which grade an
obligor held on a given date, so Fluree is that fact's sole home.

**Validators:** `partition.py` 13/13 · `conditions.py` 72 passed / 0 failed
(baseline held, no regression).

### 2026-08-19 — Wave 11a complete: `rating-and-spread-migration`

**No new FIBO bindings beyond Task 8's** (recorded above under "CREDIT
RATINGS / ISSUANCE" and the extension register) — Task 10 is documentation,
a data fix, and the vault punch list, not new generation against new terms.
**This submission adds and removes nothing** from the binding table itself;
it records what Task 8 already bound and what is now materialized, and
carries one deferred docstring correction (§9.9 of `known-issues.md`).

**A defect fixed, not just documented.** `generators/fetch_rating_actions.py`'s
`context_debt` upsert used a bare `ON CONFLICT DO NOTHING`, so `reason` text
from a superseded confirm() heuristic (§9.7) survived three regex-tightening
rounds unrefreshed — 134 of 169 `rating_action` rows described a gate that no
longer existed, even though the classifications under it were correct. Fixed
to `ON CONFLICT (subject_kind, subject_key) WHERE subject_kind IS NOT NULL DO
UPDATE SET reason = EXCLUDED.reason` (a partial-index conflict target,
matching Wave 10's own `ux_context_debt_subject` predicate) and re-run
parse-only against the cached 99 MB corpus. Verified directly: 169 rows
before and after (count unchanged), 0 rows now carry stale wording (was
134), Wave 10's 135 `subject_kind='person'` rows untouched throughout.
`artifact_reproduces_store.py` moved 39/42 → **40/42** on this alone.

**Final Postgres `ccf_v2` (rating-and-spread-migration tables):**

| Table | Rows | Provenance |
|---|---|---|
| `debt_instrument` | 60 | `synthetic — engineered` |
| `spread_observation` | 29,885 | split per column (`benchmark_bp`/`market_oas_bp` public, `idiosyncratic_bp` engineered) |
| `benchmark_curve` | 8,917 | `public` (Treasury) |
| `market_oas_series` | 3,930 | `public` (FRED ICE BofA) |
| `rating_scale` | 15 | `synthetic — internal`, derived from the Task 6 grade artifact |
| `divergence_threshold` | 9 | `synthetic — internal`, originated in the loader |

**Final Fluree `fibo-v2`:** t=408, **32,266 triples**.

| Node type | Count | | Edge type | Count |
|---|---|---|---|---|
| DebtInstrument / CorporateBond | 60 | | isIssuedBy | 60 |
| CreditRating / OrganizationCreditRating | 245 | | concernsParty | 254 |
| RatingAssessmentEvent | 9 | | supersededBy | **215** |
| IssuanceEvent | 788 | | filedBy | 788 |

`ex:supersededBy` — declared since Wave 5, asserted zero times through Wave
10 — now carries **215** assertions, the third declared-but-empty predicate
this project has closed, after `fibo-fnd-rel-rel:controls` and the Covenant
vocabulary (see the extension register above).

**Sources fetched:** Treasury par yield curve, 657 dates (2024-01-02 →
2026-08-18, 13→14 tenors at the 2025-02-18 6-week-bill schema change, §9.6
of `known-issues.md`). Five FRED ICE BofA OAS-by-band series, 786 points
each. EDGAR full-text search for rating-action 8-Ks, restructured to a
per-`(CIK, query)` sweep after the whole-corpus form was found to read only
~10% of its own hits (§9.4) — 178 candidates across 34 anchors, **9
confirmed** rating actions across 4 anchors (Targa Resources, Celanese,
Independence Realty Trust, Vertiv Holdings) after fixing a confirm() regex
that had marked ~30 of 40 candidates as false positives, including one
literal negation (§9.7). 788 Item 2.03 debt-issuance 8-Ks across all 50
anchors, selected by the free `items` metadata field — **a floor, not the
complete public record**: the sweep reads only EDGAR's capped `filings.recent`
index, and 40 of the 50 anchors have unread `filings.files[]` shards (§9).

**FINRA TRACE could not be used as §C names it** — every free-API group root
404s, the one endpoint that returns data is equity ATS volume, and per-CUSIP
bond history is FINRA's licensed product. `known-issues.md` §9.2 has the
full evidence; §9.3 covers why XBRL `companyfacts` cannot substitute for
instrument reference data either (it flattens away the dimensional context
that would attribute a fact to a specific instrument). The sanctioned
substitute is the three-leg spread model in `docs/wave11a-design.md` §2:
real Treasury benchmark + real FRED OAS (both `public`) plus an
idiosyncratic component (`synthetic — engineered`), stored in separate
columns of `spread_observation` so provenance never blends across a row.

**Validators:** `series.py` PASS (divergence 4/3, confirmed-later 1/1,
sparsity 2/2, dominance 0.1893/0.40) · `conditions.py` **82 passed / 0
failed** (baseline of 72 held, 10 new §F checks added) · `partition.py`
13/13 · `artifact_reproduces_store.py` **40/42** (2 remaining failures are
the pre-existing Wave 10 duplicate-row items, `known-issues.md` §8.16,
unrelated to this wave) · `traversal.py`, `projection.py`, `bitemporal.py`,
`cast_audit.py` unchanged and still green · `test_curves.py` 29/29,
`test_instruments.py` 21/21.

Full defect record, the TRACE/XBRL/pagination/confirm() findings, and the
deferred-minors table with verified file:line citations: `docs/known-issues.md`
§9. Full estate map and next step: `docs/HANDOFF.md`.

**📤 The vault mirror needs refreshing.** Sent through the agent exchange on
2026-08-19 — see `docs/HANDOFF.md` §8 for the punch-list summary. It adds
and removes nothing from the binding table; it batches the TRACE spec
finding (headline), the four Task 8 FIBO bindings and two prefixes, the one
`ex:` extension (`IssuanceEvent`/`filedBy`), and `ex:supersededBy` moving
from declared-and-empty to 215 assertions.

### 2026-08-20 — Wave 11a migration transition

Corrective fix against `docs/wave11a-design.md` §2 / `known-issues.md` §9.10
(now FIXED, no longer DOCUMENTED-not-fixed). Full design:
`docs/wave11a-migration-transition-design.md`. **No §C element added, no §F
condition changed, no §C row touched** — this is a change to how the
composed spread responds to a rating-band migration, confined to
`spread_observation` in Postgres.

**No FIBO term was added or changed by this work, so the vault mirror needs
no refresh.** (The converse of the standing rule deserves saying too: a
binding change always gets flagged here; the absence of one this time is
worth stating explicitly rather than leaving silent.)

**The formula.** The composed spread's market leg (`market_oas_bp`) now
steps to the obligor's **in-force rating band** — the band the grade chain
actually shows on that date, not the band fixed at instrument generation —
so it steps exactly at the migration's `asserted_at` date. The transition
ahead of that step is carried entirely by `idiosyncratic_bp` (already
`synthetic — engineered`) via a linear anticipation ramp: `α · gap(d) ·
w(d)`, where `gap(d)` is the real, signed, per-date difference between the
two bands' published OAS indices, and `w(d)` ramps 0→1 linearly over
`[asserted_at − lead, asserted_at)`. `α` and `lead` come from a per-obligor
response profile, so the ramp's magnitude derives from public data but its
shape stays labelled engineered.

**Provenance is unchanged**: `market_oas_bp` stays a real, unblended index
at every date (`public`); the ramp lands only in `idiosyncratic_bp`
(`synthetic — engineered`). No column changes class.

**The observed profile assignment** — an *outcome* of a seeded permutation
over the crossing LEIs (sorted), never a configured input:

| LEI | profile | α (anticipation) | lead (observation dates) |
|---|---|---|---|
| `5493003QENHHS261UR94` | faint | 0.30 | 110 |
| `5493004HBTOTE9DI9P12` | moderate | 0.60 | 40 |
| `549300EQD0ZXRSMG3549` | pronounced | 0.90 | 75 |

**Crossings: 4 across 3 obligors, two of them upgrades** —
`5493003QENHHS261UR94` BB→B @2025-11-19 and B→BB @2026-05-23 (one obligor,
two crossings, one temperament); `5493004HBTOTE9DI9P12` BBB→BB @2026-03-31;
`549300EQD0ZXRSMG3549` B→BB @2026-05-19. Corrects `known-issues.md` §9.10's
original count of one row per obligor (read as 3) — it is 4.

**Measured dominance**: 0.1861 as computed by the generator, 0.1847 as
recomputed by `validators/series.py` from the loaded store — the two differ
slightly and both are recorded rather than reconciled — against the
**unchanged 0.40 ceiling** (0.1893 before this change).

**Change containment**: 1,022 of 29,885 `spread_observation` rows changed,
confined to exactly the 6 instruments belonging to the 3 migrating obligors.
No row added, no row dropped.

**Untouched, verified across the whole branch**: `generate_grades.py` was
touched only by a pure cycle-break refactor (proven byte-identical output);
all 245 grade assertions and the 215-edge supersession chain stand
unmodified; `validators/conditions.py` has no commits against it and holds
at 82 passed / 0 failed; no loader changed; **Fluree was never written**.

**The generator regeneration sequence changed, and is now documented for the
first time** (previously implied only by task numbering in
`docs/wave11a-plan.md`, and that implied order is now wrong):

```
generators/generate_instruments.py
generators/generate_grades.py      # MUST precede spreads
generators/generate_spreads.py     # reads wave11a_grades.json
loaders/load_postgres_wave11a.py
loaders/load_fluree_wave11a.py
```

`generate_spreads.py` used to run *before* `generate_grades.py`; it now runs
*after*, because it reads the grade chains to discover band crossings. A
genuine from-scratch run in the old order (no `wave11a_grades.json` on disk
yet) fails **cleanly**: `load_band_crossings()` raises a `RuntimeError`
naming the required order. This table exists so nobody has to rediscover
that order by hitting the guard, not because the guard itself is confusing.

**The real residual hazard is a *stale* `wave11a_grades.json`.** The guard
only checks that the file exists, not that it reflects the current grade
generation. Regenerate `generate_grades.py` alone (a reseed, a data fix)
without also regenerating `generate_spreads.py` afterward, and the spreads
run will silently succeed against the OLD grade chains — no error, no
loud failure, just a spread series whose migration transitions no longer
match what Fluree holds. `validators/series.py`'s
`_cross_check_artifact` catches this downstream (it derives crossings from
Fluree independently and compares against the artifact), but only if that
validator is actually run before the mismatch ships.

**Validators**: `partition.py` 13/13 · `conditions.py` 82 passed / 0 failed
(unchanged) · `series.py` PASS, now also asserting the migration transition
(≥ 1 crossing exists; the market step and residual jump at each crossing
match the assigned profile within 15% relative tolerance) ·
`artifact_reproduces_store.py` 40/42 (unchanged; the 2 remaining failures are
the pre-existing Wave 10 duplicate-row items, `known-issues.md` §8.16) ·
`test_curves.py` 29/29, `test_instruments.py` 21/21, and the new
`test_migration.py` **28/28** (pure-function tests for the ramp weight, the
profile permutation, lead truncation on adjacent crossings, and negative-gap
upgrades).

### 2026-08-20 — Wave 11b Task 1: the surveillance vocabulary, bound before anything generates

Vocabulary only. **No data was generated, fetched, or loaded**, which is the
point: CLAUDE.md's named expensive failure is generating against invented local
names, so the binding lands first and every later Wave 11b task writes the IRIs
fixed here.

**Five `ex:` extensions minted** — `WarningSignal`, `SignalSource`,
`signalAbout`, `triggeredBy`, `PriorObservation`, all under
`http://example.org/fibo/`. See *"Wave 11b — early-warning surveillance"* in the
`ex:` extension register above for the full verification record.

**Four were the candidates the task named; `PriorObservation` was not.** It was
found by enumerating every `ex:` token in `docs/wave11b-plan.md` and
`docs/wave11b-design.md` rather than checking only the four supplied names — the
§0.2 lesson applied deliberately.

**Verified against two ontologies, not one.** All 295 RDF modules of a shallow
`edmcouncil/fibo` clone (`119fa8c`, 2026-07-17) plus all 22 OMG Commons modules
fetched live from `omg.org`, searching every `rdf:about`, `rdf:ID` and
`rdfs:label` for `signal`, `warning`, `trigger`, `source`, `about`, `indicator`,
`observation`, `alert`, `provider` — never scoped to a guessed module path.
`signal` and `warning` return zero hits in either corpus.

**Two real adjacent terms were found and deliberately not reused:**
`fibo-fnd-dt-oc:isTriggeredBy` (definitional for `OccurrenceBasedDate`; reusing
it would entail a warning signal is a date) and `cmns-doc:isAbout` (a genuine
generic superproperty of `ex:signalAbout`, recorded as such and not bound in its
place). Both are documented above with the reasoning, so the next reader does
not re-find them and assume the extension was lazy.

**Three needs are reused, not created**: `ex:supersededBy` (215 assertions since
Wave 11a), `ex:IssuanceEvent` / `ex:filedBy` (Wave 11a), and the real FIBO term
`fibo-fnd-agr-ctr:BreachOfCovenant`.

**Vault mirror needs refreshing** for all five terms;
`wiki/context-products/content/fibo-iri-binding` does not carry them, and the
Wave 11a terms are still outstanding from the 2026-08-18 punch list too.

> This entry is dated history and is left as written: on 2026-08-20 the wave had
> bound five terms and that was a true statement of Task 1's output. A **sixth**,
> `ex:item`, was asserted by the Fluree loader and bound on 2026-08-21 — see the
> `ex:` extension register, *"A sixth term"*. Task 1 did not miss it; the audit
> that should have caught it later was blind (`known-issues.md` §10.7).

**Validators**: `test_binding_drift.py` **9/9** (unchanged) ·
`binding_drift.py` **16 agree · 23 disagree** — the agreements rose by five and
the disagreements did **not** move, because nothing is loaded against these IRIs
yet. They flip to `CAVEAT_STALE` when `loaders/load_fluree_wave11b.py` lands,
and that flip is the next punch list generating itself.

### 2026-08-21 — Wave 11b complete: `credit-surveillance-early-warning`

Tier 3, Postgres + Fluree, no new store. The catalog's dedicated demonstration
of **supersession as a cascading policy event**: one signal invalidating every
downstream product that touched the affected entity. The data makes that
demonstrable; the fabric performs it (CLAUDE.md, *Explicitly out of scope*).

Design: `docs/wave11b-design.md`. Plan: `docs/wave11b-plan.md`. Known issues and
substitutions: `docs/known-issues.md` §10.

#### What was loaded

**Postgres `ccf_v2` — seven new tables, all authoritative here and nowhere else:**

| Table | Rows | Provenance | Contents |
| --- | ---: | --- | --- |
| `warn_notice` | 3,514 | `public` | TX Socrata `8w53-c4f6` (415) + CA EDD XLSX/PDF (3,099), window 2024-08-19 → 2026-08-19, employer strings preserved verbatim |
| `warn_match` | 36 | mixed | 4 resolved pairs across **3 distinct obligors**, 32 ambiguous pairs across 12 — the lossiness is the deliverable, not a shortfall |
| `gdelt_mention` | 951 | `public` | GDELT DOC API, tone-filtered; 49 rows carry `down_weight_factor` / `down_weight_reason` |
| `signal_event` | 1,603 | 1,590 `public` · 13 `synthetic — engineered` | the unified ledger: 654 `adverse_media`, 534 `8k_event`, 383 `trend_delta`, 27 `spread_widening`, 5 `warn_notice` |
| `signal_weight` | 45 | `synthetic — internal` | signal type × sector × policy version; carries `decay_days` (spec §E's λ_c) as of 2026-08-21 — **NULL for `8k_event`**, which never decays, and never 0 |
| `escalation_threshold` | 6 | `synthetic — internal` | 3 tiered by score, 3 rule-shaped (trend materiality, media down-weight, spread anticipation/confirmation) |
| `trend_delta` | 3,705 | `public` | XBRL `companyfacts` period-over-period; `pct_change` NULL where the prior value is zero, preserved rather than imputed |

**Fluree `fibo-v2` — 38,582 triples at `t=520`** (from 32,266 at `t=408`,
the Wave 11a merge baseline). New assertions:

| Assertion | Count | Notes |
| --- | ---: | --- |
| `ex:WarningSignal` | 538 | 534 real `8k_event` + 1 engineered cascade + 3 composite-case |
| `ex:SignalSource` | 409 | the distinct 8-K filings the signals were derived from |
| `ex:PriorObservation` | 50 | exactly one per anchor obligor — the delta anchor, so the earliest signal has something to supersede |
| `ex:signalAbout` | 595 | 537 signal→obligor, 8 from the cascade signal (1 facility, 2 pledges, 5 drawdowns), 50 from the prior-observation points |
| `ex:triggeredBy` | 535 | signal → the `SignalSource` filing that produced it |
| `ex:supersededBy` | 535 **new** | chronological chains, one per anchor. Total on the predicate is now **750**: Wave 11a's 215 on `syn-g-*` are untouched |

Item 2.03 signals also carry `ex:IssuanceEvent`; Item 2.04 signals also carry
the real FIBO term `fibo-fnd-agr-ctr:BreachOfCovenant`. Per CLAUDE.md rule 7,
both `rdf:type` assertions are explicit — nothing is inferred.

#### Files

| Path | Role |
| --- | --- |
| `generators/fetch_8k_items.py` | 8-K item census from the EDGAR submissions index, `filings.recent` **plus** all shard files |
| `generators/warn_sources.py` | pure parsers for the TX Socrata and CA XLSX/PDF legs |
| `generators/fetch_warn.py` | the three-leg WARN fetch, plus the obligor join |
| `generators/warn_match.py` | pure `normalise` / `score` / `classify` / `match_all` for the deliberately lossy name join |
| `generators/fetch_gdelt.py` | GDELT DOC API, timeline-guided and resumable |
| `generators/generate_trend_deltas.py` | XBRL period-over-period deltas |
| `generators/generate_signals.py` | the unified signal ledger, decay constants, weights, thresholds |
| `generators/narrative_wave11b.py` | the engineered cascade and the composite case |
| `generators/verify_fibo_wave11b_confirm.py` | machine-checkable confirmation of the wave's vocabulary — see below |
| `loaders/load_postgres_wave11b.py` | the seven tables |
| `loaders/load_fluree_wave11b.py` | events, signals, edges, prior-observation points |
| `validators/surveillance.py` | the wave's own gate — cascade, composite, distribution, anchoring, WARN resolution, GDELT concentration |
| `ccf/currency.py` | the design §5 artifact-currency guard (added 2026-08-21) — sha256 of every consumed artifact, verified before reading |
| `validators/test_signals.py` | 72 pure-function cases |
| `validators/test_warn_match.py` | 38 pure-function cases |
| `sources/screening/wave11b_{8k_events,warn,gdelt,trend_deltas,signals,narrative}.json` | the committed artifacts |
| `sources/{warn,gdelt}/manifest.json` | retrieval manifests with dates and query strings |

#### Binding

**Six** `ex:` extensions. Five were minted **before anything generated** —
`WarningSignal`, `SignalSource`, `signalAbout`, `triggeredBy`,
`PriorObservation`. The sixth, **`ex:item`**, was asserted by the Fluree loader
and bound only on 2026-08-21, when the whole-branch review found it carrying 535
triples with no binding row. *(This paragraph said "Five" until then; see the
`ex:` extension register, "A sixth term".)* The full verification record is in
that register, under *"Wave 11b — early-warning surveillance"*; the 2026-08-20
Task 1 entry below records how the first five were checked. All six now carry
data, so all six read **`CAVEAT_STALE`** in `binding_drift.py` — the vault still
tells consumers they do not exist.

**Vault mirror needs refreshing for all six.** Sent through the agent exchange
on 2026-08-21; this repo is source of truth and the custodian applies it. The
Wave 10 and Wave 11a punch lists remain outstanding at the vault and were **not**
re-sent.

One prefix registration was added for a **rejected** term,
`fibo-fnd-dt-oc` — see the note above the "two real terms sit adjacent" table.
Registering a prefix is not binding a term; it is there so a reader can expand
the compact form and check the rejection.

#### Verification artifact

`generators/verify_fibo_wave11b_confirm.py` restores the auditability the Wave 8
`verify_fibo_wave8_confirm.py` established. It confirms, machine-checkably and
**offline**, that every `ex:` term this wave asserts is bound in this document,
that every bound term is materialised in Fluree at the exact IRI recorded here,
and that the reused terms carry the counts claimed. Absence-from-FIBO claims
need the network and are reported as `not re-verified offline` rather than
silently passed.

#### Store partition

`validators/partition.py` grew from 13 checks to **19**, all passing. The four
new claims:

- the seven surveillance tables are present **and populated** in Postgres, and
  appear as neither a Mongo collection nor a SQLite table
- a Fluree surveillance node carries identity, ordering and provenance but **no
  measurement** — severity, score, weight, threshold, the WARN employer and
  dates, the GDELT tone and down-weight all resolve from Postgres
- the supersession chain is mirrored into no Postgres column
- every `ex:signalAbout` target resolves in whichever store owns it — Fluree for
  the facility and its collateral pledges, **Postgres for the five drawdowns**,
  which have no Fluree node by Wave 5's design and correctly should not

That last check is the one worth reading. Adding `signalAbout` to the blind
"points at an untyped node" list reports 5 dangling edges, which looks like Wave
9's phantom-borrower bug returning. It is not the same thing: Wave 9's URI was
*wrong* and the fact was unreachable; these URIs are *right* and the fact lives
in the store that owns it. A partition validator should approve of that, and the
check that does approve of it is strictly stronger — it confirms the Postgres row
exists rather than merely tolerating the missing node.

#### Validator baseline at merge

*(Updated 2026-08-21 by the whole-branch fix wave — the line previously read
`surveillance.py` **PASS (5 claims)** and did not list
`artifact_reproduces_store.py`, which was 40/42 with no Wave 11b coverage at
all.)*

`partition.py` **19/19** · `conditions.py` **91 passed · 0 failed** ·
`surveillance.py` **PASS** (**6** claims — GDELT concentration added) ·
`series.py` **PASS** · `traversal.py`, `bitemporal.py`, `projection.py`
**PASS** · `artifact_reproduces_store.py` **54/56** (14 Wave 11b checks added;
the 2 failures are the pre-existing Wave 10 duplicate-row items,
`known-issues.md` §8.16) ·
`generators/verify_fibo_wave11b_confirm.py` **11 confirmed · 0 missing · 4
deferred to --live · 2 pre-existing debt** ·
11 pure-function suites, **279 cases**, all passing:
`test_form4` 30, `test_persons` 25, `test_renderings` 10, `test_resolve` 8,
`test_coverage_shape` 9, `test_curves` 29, `test_instruments` 21,
`test_migration` 28, `test_binding_drift` 9, `test_signals` 72,
`test_warn_match` 38.

#### Two things this wave changed outside itself

**`loaders/load_fluree_wave11a.py --reconcile` was a live data-loss hazard and
is fixed.** Its docstring claimed sole authorship of four edge predicates and
its code retracted every edge on each, ledger-wide. True when written; false the
moment this wave added 535 `ex:supersededBy` assertions. A real invocation would
have retracted all 750 and rebuilt 215. Retraction is now scoped by **subject**
to the URIs that loader mints, matching the pattern `load_fluree_wave11b.py`
established. `docs/known-issues.md` §10.5 has the full account.

**`docs/wave11b-design.md` §1.3 and §1.5 carried a false claim** — that Avis
Budget Group has 6 real Texas WARN notices. Measured against the full Texas
source rather than the 24-month window; in-window Avis has none. Corrected in
place, with the previous wording quoted, per this estate's convention. The
cascade-anchor decision it appeared to support does not rest on it and stands.

### 2026-08-21 — Wave 11c: the binding debt paid — 45 `ex:` terms bound

`known-issues.md` §10.7 recorded that the estate asserts **67** distinct `ex:`
terms and only **22** carried a real full-IRI row here. The other 45 — 33 with
no mention anywhere in this document, 12 named only inside a code span — are
bound below. The estate is now **67 / 67**.

**Why this was not a documentation chore.** This table is a contract with a
project that has no access to this repository and reads it only through the
vault mirror. A term carrying 2,890 assertions and no row is invisible to that
consumer: it cannot be queried for, cannot be projected, and cannot be
diagnosed when a query silently returns nothing. `ex:provenance` was in that
state — the predicate every product uses to tell public data from engineered
data.

**Two of the 45 were not debt at all.** `ex:schemaNote` and
`ex:effectiveDateNote` carried live assertions written by a loader version no
longer in the repo. Binding them as they stood would have published vocabulary
that a rebuild from an empty ledger cannot produce — a worse failure than
leaving them unbound, because it is invisible until someone rebuilds. Both
writers were restored instead, and `validators/orphan_terms.py` now fails if
any asserted `ex:` term has no writer. See `known-issues.md` §10.7.

**What "bound" now means at the gate.** `KNOWN_UNBOUND` in
`generators/verify_fibo_wave11b_confirm.py` is **empty**. The rule it enforces
collapses from "fail if a term is new AND unbound" to "fail if a term is
unbound" — a rule with no hand-maintained forgiveness list, and so nothing to
rot. A code-span mention has never satisfied that gate and still does not; only
a full-IRI row in the table below does.

Assertion counts are as measured on 2026-08-21 and are a floor, not a schema
constraint — they are recorded so a consumer can tell a term that carries the
dataset from a term that carries three rows.

#### Wave 11c · class extensions

Six invented classes. Each is allowlisted with written rationale in
`validators/partition.py`'s `PERMITTED_EX_TYPES`; none shadows a FIBO type.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `Amendment` | class | `http://example.org/fibo/Amendment` | 25 | FIBO models the amended *contract*, not the amending *event*; the bitemporal products need the event as a node so its effective date and its booking date can diverge |
| `PolicyVersion` | class | `http://example.org/fibo/PolicyVersion` | 2 | no FIBO class for a versioned internal access policy; `FND/Law` covers legal instruments, not a bank's own control state |
| `ContextDebt` | class | `http://example.org/fibo/ContextDebt` | 1 | no FIBO vocabulary for asserted incompleteness. A consumer must be able to *see* a coverage shortfall in the product rather than infer it from an empty result |
| `WallCrossing` | class | `http://example.org/fibo/WallCrossing` | 4 | no FIBO class for the control event that brings a person inside an information barrier |
| `EmbargoWindow` | class | `http://example.org/fibo/EmbargoWindow` | 9 | no FIBO class for a bounded period during which a document is restricted |
| `RegFDEvent` | class | `http://example.org/fibo/RegFDEvent` | 1 | no FIBO class for a Regulation FD disclosure event that *widens* access rather than restricting it |

#### Wave 11c · the bitemporal axis

Three predicates carried by every wave that asserts time-versioned state
(Waves 5, 7, 11a, 11b). They are the reason a single-timeline store cannot
answer this estate's questions: `validFrom`/`validTo` are when a fact was true
in the world, `assertedAt` is when the bank recorded it, and the gap between
them is what `validators/bitemporal.py` proves is non-empty.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `validFrom` | property | `http://example.org/fibo/validFrom` | 3,022 (re-measured 2026-08-26, Wave 18 Task 10 — the 1,724 figure recorded here since Wave 11c was never bumped through Waves 12–17's own additions; Task 10 adds 2 of the 3,022, on `DisclosureEnvelope` nodes, reusing this predicate rather than minting `ex:effectiveFrom` — see `ccf/syndicate.py::EX_VALID_FROM`'s docstring) | FIBO's `FND/DatesAndTimes` supplies date *datatypes*, not a valid-time interval on an arbitrary assertion node |
| `validTo` | property | `http://example.org/fibo/validTo` | 227 | as `validFrom`; open-ended when absent, which is a modelling choice FIBO does not make for us |
| `assertedAt` | property | `http://example.org/fibo/assertedAt` | 274 | no FIBO predicate for assertion time. This is the axis the whole bitemporal demonstration turns on, and no ontology in scope models it |

#### Wave 14 · securitization trigger thresholds and passage anchoring

Four application predicates carried by the `fibo-sec-dbt-cdo:TriggerEvent`
nodes written by `loaders/load_abs_fluree_wave14.py`. Bound **before** the
load, not after: Fluree is append-only, so generating against an unbound name
could not be corrected, only contradicted.

These are `ex:` application attributes rather than candidate FIBO terms, so
**no EDM Council search was run for them** — the "why not FIBO" column below
records the modelling reason each exists, not the result of an absence check.
Contrast the FIBO terms this wave uses (`Tranche`, `TriggerEvent`,
`specifiesTrigger`, `isSubordinatedTo`, `isCollateralizationOf`,
`AssetBackedSecurity`, `PoolBackedSecurity`, `Servicer`), every one of which
was verified against the source and is bound above.

Valid time and assertion time on these nodes use the estate's existing
`ex:validFrom` and `ex:assertedAt` (line 1969 above). An earlier draft of the
Wave 14 plan spelled valid time `ex:effectiveFrom`; that was corrected before
any write, because a second spelling in an append-only store is not a synonym
but a predicate half the estate's queries would miss.

Assertion counts are triples, with distinct subjects in brackets where the
two differ. All figures below were read back from the loaded ledger, not
predicted from the generator.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `thresholdValue` | property | `http://example.org/fibo/thresholdValue` | 10 (10 subjects) | the numeric level a securitization trigger tests against. **Near neighbour, measured rather than assumed:** `ex:threshold` (Waves 5–6) means the same *kind* of thing. Re-queried against the live ledger 2026-08-23: 217 assertions on 217 distinct subjects, in **two** populations — 180 typed `ex:Covenant`, each also carrying `ex:direction`, `ex:testFrequency` and `ex:unit`; and **37 untyped** `COVSRC-*` covenant-source anchor nodes written by `loaders/load_anchors_wave6.py`, which carry `ex:covenantType` and `ex:evidencedBy` but none of those three. All 217 carry `ex:covenantType`. The distinction from `thresholdValue` is that the populations are **disjoint**: zero `TriggerEvent` nodes carry `ex:threshold`, and zero `ex:threshold` subjects carry `ex:thresholdValue`. A consumer wanting both must ask for both |
| `thresholdComponent` | property | `http://example.org/fibo/thresholdComponent` | 12 (10 subjects) | one addend of a threshold defined as a **sum** — e.g. "the sum of (i) 22.80% of the Pool Balance and (ii) 1.50% of ...". Without it `thresholdValue` alone asserts the target *is* 22.80%, which is false. **The one multi-valued predicate in this group** — the count in the Assertions column exceeds the subject count because two composite triggers (`SDART-2022-6` and `SDART-2024-1` overcollateralization) carry two components each; a consumer assuming one per subject will silently drop half of each composite threshold. The count is stated **once**, in the Assertions column, and deliberately not restated here: this cell previously carried its own copy (11 across 9), which was correct before Task 10's engineered amendment added a tenth subject and went stale when the column was updated and the prose was not. Re-measured against the live ledger 2026-08-23. Every valued trigger carries at least one component, and a single-component trigger's component equals its value, so components can be read uniformly without knowing in advance whether a threshold is composite |
| `thresholdUnit` | property | `http://example.org/fibo/thresholdUnit` | 11 (11 subjects) | what the threshold is denominated in — `percent_of_pool`, `amount_or_percent`, `amount`. Deliberately **not** the existing `ex:unit`, and here the covenant-cluster claim does hold on measurement: all 180 `ex:unit` assertions sit on 180 distinct `ex:Covenant`-typed nodes, every one of them alongside `ex:direction`, `ex:testFrequency` and `ex:threshold`, with **zero** untyped subjects (checked 2026-08-23, the same query that disproved the `ex:threshold` claim above). `ex:unit` also carries a documented FIBO label collision — see the covenant table above. A trigger's unit vocabulary is the securitization one and shares no values with it |
| `passageAnchor` | property | `http://example.org/fibo/passageAnchor` | 10 (10 subjects) | the `_id` of the MongoDB `trigger_anchor` row that pins this threshold to the span of prospectus text defining it. The Fluree side of a cross-store lineage join, deliberately an identifier and not a copy of the passage — MongoDB owns passage-level lineage. Distinct from `ex:evidencedBy` (Wave 6), measured 2026-08-23: 43 assertions across **37** distinct subjects — it is multi-valued, some covenant sources cite more than one passage — and all 37 are the untyped `COVSRC-*` nodes, none of which carries `ex:passageAnchor`. Different collection, different id scheme, disjoint subjects |

#### Wave 15 · the covenant definition chain (`covenant-cross-reference`, `covenant-in-force-as-of`)

`ex:definedBy`, `ex:measuredBy` and `ex:crossReferences` had **zero**
assertions and `ex:CovenantDefinition`, `ex:DefinedTerm` and
`ex:MeasurementPeriod` had **zero** instances, while both products were
registered as done. The T4 product summarises itself as "the covenant sits in
one section and its defined terms in another"; nothing in the estate could
express that. Found by `validators/spec_coverage.py`.

Everything below is extracted from filed EX-10 text with document ids and
character offsets — `public`, per §C. The single engineered element is the
unresolvable-definition case, which §F names as engineered.

**Two real FIBO terms, and a correction the specs need.**

| Local name | Compact | Full IRI | Note |
| --- | --- | --- | --- |
| ContractualDefinition | `fibo-fnd-agr-ctr:ContractualDefinition` | `.../FND/Agreements/Contracts/ContractualDefinition` | "contractual element that specifies the meaning of a term in a legal document, whose definition is substitutable for the term whenever it occurs in the body of that document". **Both covenant specs' §C say "no FIBO term exists" for `CovenantDefinition` and `DefinedTerm`. That is wrong** — this is an exact fit, and the vault mirror has been told. Asserted on every definition and defined-term node. The Wave 0 binding-table row for `CovenantDefinition` (~line 258 above) has been annotated superseded and corrected to match this finding |
| Report | `fibo-fnd-arr-rep:Report` | `.../FND/Arrangements/Reporting/Report` | `subClassOf cmns-doc:Document`. The 10-K a definition incorporates a convention from. Carries type, label and `ex:documentId` only — MongoDB stays the single writer for document content |

Found only because `partition.py` refused `ex:DefinedTerm` as shadowing a FIBO
term and the refusal had to be answered with a search of the **complete**
Production ontology rather than an assertion. The `ex:` role types are kept
**alongside** `ContractualDefinition`, never instead of it: FIBO models what a
definition *is*, not which one a covenant is measured by. Verified: 49
`CovenantDefinition` and 158 `DefinedTerm` nodes, **0 without the FIBO class**.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `DefinedTerm` | class | `http://example.org/fibo/DefinedTerm` | 158 | role marker: a contractual definition that another definition *depends on*. Always co-typed `fibo-fnd-agr-ctr:ContractualDefinition` |
| `definedBy` | property | `http://example.org/fibo/definedBy` | 28 | covenant → the definition stating how its ratio is computed. FIBO has no property linking a covenant to its defining clause; it models the breach (`BreachOfCovenant`), not the measurement |
| `measuredBy` | property | `http://example.org/fibo/measuredBy` | 13 | covenant → the `MeasurementPeriod` it is tested over |
| `crossReferences` | property | `http://example.org/fibo/crossReferences` | 216 | definition → a term it depends on (215, intra-document) or a `Report` whose convention it incorporates (1, cross-document). One predicate, and the object's `documentId` is what makes a reference cross-document |
| `declarationConvention` | property | `http://example.org/fibo/declarationConvention` | 48 | which of the three declaration conventions the filer used — `colon`, `means`, `shall_mean`. Recorded per definition so a future parser skew is visible rather than silent: Vertiv files both conventions across two agreements |
| `unresolvedTerm` | property | `http://example.org/fibo/unresolvedTerm` | 2 | the defined term a definition cites and the agreement never declares. Carried by both the definition and its `ContextDebt`, which is what lets the §F condition join them |

**One covenant type added: `net_capital`.** Wave 5's regex had no pattern for
it, and its absence is what would have sent §F's cross-document bullet to the
engineered pile. BGC Group's agreement carries a real net-capital covenant
("Net Excess Capital ... to be less than $300,000,000") whose defined term
incorporates a convention stated elsewhere — "as shown on the Borrower's SEC
Forms 10-Q and 10-K". Real, filed, public; §F does not list this case as
engineered, and it is not.

**Direction is taken from covenant-type semantics, not from the text.** Two
attempts to read it off the comparator were wrong on 100% of the corpus: a
floor is written both as "shall not permit ... to be less than $300,000,000"
and as "Liquidity shall be greater than $10,000,000", and the negation that
tells them apart sits in a section lead-in an arbitrary distance back. Covenant
creation is therefore confined to `net_capital`, whose direction is not in
doubt; every other type stays Wave 6's to anchor.

#### Wave 15 · lien position moves into Fluree (`collateral-and-setoff-coverage`)

`collateral-and-setoff-coverage` §C assigns **lien priority to Fluree** (`R`,
`T`). From Wave 9 until Wave 15 it lived in `ccf_v2.collateral_pledge.priority`
as the free text `first` / `second`, while Fluree held 95 *unqualified*
collateral edges — so walking the graph, a first lien and a second lien were
indistinguishable. That is verbatim the counterfactual the product exists to
refute. `partition.py` passed 30/30 throughout, because every check it makes
runs in the one direction: nothing had leaked *into* a store, and a missing
element cannot leak. `validators/spec_coverage.py` is the other half.

**Priority is reified because it belongs to the (facility, asset) PAIR.**
`COL-00012` and `COL-00044` are each pledged to two facilities at *different*
priorities, so hanging the position on the asset would have to pick one and
silently drop the other — the same shape as the Wave 14 composite-threshold
defect. Each pledge is therefore a node: 95 of them, 93 primary and 2
subordinate, matching the column they replaced exactly.

**Why `ex:CollateralPledge` rather than a FIBO class.** Verified 2026-08-24
against `prod.fibo-quickstart.ttl` and **RE-VERIFIED the same day against
`dev.fibo-quickstart.ttl`**, which is the file that can actually settle an
absence. `prod` carries Release maturity only and omits 40 Provisional modules
(known-issues §19.8), so the original wording here — "the complete FIBO
Production ontology … every module in a single file" — was wrong and the claim
below rested on it. It survives the stronger check: searching `dev` for every
local name containing `Pledge` or `Lien` returns `NegativePledge`,
`LenderLienPosition`, `PrimaryLienPosition`, `SubordinateLienPosition` and
`isLienOn`, and no `CollateralPledge`. Across `prod`: the only term whose local name contains "Pledge" is `NegativePledge` (a
covenant); the Collateral family is `Collateral`, `CollateralAgreement`,
`CollateralizedGuaranty`, `CollateralizedLoan`, `CollateralValueAsOfDate`; the
Lien family is `LenderLienPosition` and its two named individuals. **None
reifies the pledge itself.** `fibo-fnd-agr-ctr:CollateralAgreement` is the near
miss and is deliberately not used — it is a `WrittenContract`, and typing a
(facility, asset, position) triple as a contract repeats the `isSubordinateTo`
error. It also *declares* in `FND/Agreements/Contracts` while the Debt module
merely refers to it, so binding it off a per-module scan would have produced a
fabricated IRI that still greps as present.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `CollateralPledge` | class | `http://example.org/fibo/CollateralPledge` | 95 | the reified pledge of one asset to one facility, carrying its lien position. FIBO models the asset (`Collateral`), the contract (`CollateralAgreement`) and the classifier (`LenderLienPosition`), but not the pledge instance that ties a specific asset to a specific facility at a specific priority |
| `pledgedFacility` | property | `http://example.org/fibo/pledgedFacility` | 95 | pledge → the facility secured. Distinct from `fibo-fbc-dae-dbt:isCollateralizedBy`, which is the direct facility→asset edge and remains loaded: that edge says *what secures this*, this one says *which pledge this is* |
| `pledgedAsset` | property | `http://example.org/fibo/pledgedAsset` | 95 | pledge → the collateral asset. Distinct from `ex:pledgedBy` (Wave 9), which points at the pledgor *entity*, not the asset |
| `lienPosition` | property | `http://example.org/fibo/lienPosition` | 95 | pledge → `fibo-loan-ln-ln:PrimaryLienPosition` or `SubordinateLienPosition`. The object is a **FIBO named individual**, so this is the `ex:` predicate that carries a real FIBO value rather than a literal |

**Single writer.** `collateral_pledge.priority` was **dropped** — the drop is
guarded by the loader, which refuses unless the ledger already holds a position
for every pledge. Both source artifacts retain `priority`, so the move is
reversible by reload.

**Bounded.** Nine facilities carry collateral edges but no `rdf:type` in Fluree
(`load_collateral_wave13a.py` asserts `isCollateralizedBy` without asking
`load_exposure_wave9.py`, the single writer for facility nodes, to create
them). Under no-inference a traversal starting from `CreditFacility` reaches
neither those facilities nor the lien positions written for them, so lien
priority is queryable that way for 41 of 50 facilities. Pre-existing, separate,
and not fixed here.

#### Wave 22 · anchor identity and point anchors (`covenant-cross-reference`)

Two `ex:` terms, bound before the write. Both exist because
`loaders/load_anchors_wave6.py` keyed a node on
`COVSRC-{accession}-{covenant_type[:8]}` — a key that **omits the document**.

**The key was under-specified and it merged real things.**
`sources/screening/covenants_extracted.json` holds **60 document entries across
47 accessions**: one filing appears once per exhibit. XPO, Inc.
`0001104659-26-068522` carries two credit agreements, `ex10-1` and `ex10-2`,
each with its own `leverage`, `fixed_charge_coverage` and `secured_leverage`
covenant at different thresholds and different passage spans. The key cannot
tell them apart, so **six URIs each received two covenants from two different
agreements.**

Everything downstream followed from that. A predicate join over the four
anchor literals returned the cross-product — 79 candidate citations of which
**36 failed their own `passageSha256`**, and 12 sliced to empty because a start
from one agreement paired with an end from the other, once inverted
(`225927 > 167832`). `ex:evidencedBy` was intact at 43/43 throughout, because
each covenant's own anchor was always internally consistent.

`ccf-sdk` found the symptom and measured it exactly (2026-09-13); it was
described as *two unpaired anchors on one node*. It is not — it is **two nodes
that were never separate.** Reifying the anchor, which was the agreed fix
before this, would have produced one node correctly carrying two anchors and
still no way to know it was two covenants.

**Fix: the key gains the document and drops the truncation.** Verified against
the source before writing — `COVSRC-{accession}-{document}-{covenant_type}`
yields **44 URIs for 44 covenants, 0 collisions**, against 38 for 44 before.
Loaded 2026-09-13: the four-literal join now returns **44 rows, 44 of 44
hashing correctly**, against 79 rows with 36 failures. One covenant that the
collision had been overwriting is now present, which is why 44 and not 43.
The truncation to eight characters is also removed: `secured_leverage` and
`fixed_charge_coverage` reduce to `SECURED_` and `FIXED_CH`, which do not
collide today and are one covenant type away from doing so.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `PassageAnchor` | class | `http://example.org/fibo/PassageAnchor` | 44 | the node is a verified span anchor carrying what it evidences. FIBO has **no** text-anchor, citation, excerpt or span term — checked against `dev.fibo-quickstart.ttl` with controls; the only `Passage` is `fibo-fnd-plc-uspsai:Passage`, a **postal address street-type**, and the only anchor is `fibo-fnd-dt-fd:AnchorDate`. Deliberately NOT `ex:Covenant`, which the sibling `COVDEF-*` uses: an evidence node answering a covenant query would make every "covenants in force" traversal collect 43 passage anchors (vault ruling, 2026-09-12) |
| `declaredAt` | property | `http://example.org/fibo/declaredAt` | 170 | the POINT at which a term is declared, for the 170 subjects that have no end offset. Appended **alongside** the existing `startOffset` rather than replacing it: Fluree is append-only, so narrowing `startOffset` would leave the 170 permanently ambiguous and split one concept across two eras. After this, `declaredAt` selects exactly the point anchors, `startOffset` **and** `endOffset` selects exactly the resolvable spans, and `startOffset` alone remains an honest superset (vault ruling, 2026-09-12) |

**Vault mirror.** These **two** terms are new since the last mirror refresh of
`wiki/context-products/content/fibo-iri-binding`.

#### Wave 21 · Florida UCC-1 lien filings (`collateral-and-setoff-coverage`)

Twelve `ex:` terms carried by the filing nodes written by
`loaders/load_ucc_fl_wave21.py`. Every count below is computed from
`sources/ucc_fl/mastec.json`, not estimated. Bound **before** the write, same discipline as
every predicate above: Fluree is append-only, so generating against an unbound
name cannot be corrected, only contradicted.

**Why `ex:` and not FIBO.** Checked against `sources/fibo/dev.fibo-quickstart.ttl`
with a positive control (`LenderLienPosition`, 5 occurrences) and a negative
control (an invented name, 0). `FinancingStatement`, `SecurityInterest`,
`Perfection`, `SecuredParty` and `LienFiling` all return **zero**. The `dev`
quickstart is used deliberately: `prod` omits 40 modules and cannot carry an
absence claim. FIBO models the lien *position* (`LenderLienPosition` and its two
named individuals, bound Wave 9/15) and the collateral (`Collateral`), but not
the **filed public notice** that perfects a security interest and fixes its date
of priority. That instrument is a creature of UCC Article 9, and FIBO does not
reach it.

**`fibo-loan-reln-org:isLienOn` exists, is unbound, and stays unbound.** It
would look like free progress. But the collateral description lives only inside
a scanned `.tif` and is not parsed, so there is nothing for the predicate to
point at — and a bound term with zero instances is precisely the "schema row
satisfied, classifier classified nothing" failure already recorded against
`LenderLienPosition` in this file. It is named here so the next reader knows it
was considered rather than missed.

**No image URL is stored.** `/filing-image` returns a *signed, expiring*
CloudFront link. Persisting one would store a value guaranteed to break; the
UCC number is stored and the link constructed on demand.

**Secured parties are one node per name AS FILED, not per resolved party.** The
Florida pull returns 24 distinct secured-party strings which collapse to 23 under
whitespace normalisation — `'BANC OF AMERICA LEASING & CAPITAL, LLC'` appears
both with and without a trailing space. Normalising in place would erase the
only evidence that the register holds two spellings of one party. The variant is
kept and the resolution recorded separately, which is the same discipline the
debtor-name → LEI crosswalk follows, and is CLAUDE.md rule 5 satisfied by the
source rather than engineered.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `UccFiling` | class | `http://example.org/fibo/UccFiling` | 65 | one filed UCC-1 financing statement. FIBO has no financing-statement term (verified above); the nearest concepts model the lien position and the collateral, not the public filing that perfects them |
| `UccAmendment` | class | `http://example.org/fibo/UccAmendment` | 85 | one UCC-3 event — Continuation, Termination, Amendment, or a secured-party change. This is what makes a lien's state time-dependent, and it is the `T` half of §C's `R, T` |
| `SecuredParty` | class | `http://example.org/fibo/SecuredParty` | 24 | the party named as secured on a filing, keyed on the name **as filed**. Not `fibo-fnd-pty-pty:PartyInRole` — that would assert a resolved identity the register does not supply |
| `filedOn` | property | `http://example.org/fibo/filedOn` | 150 | filing or amendment → its filing date (65 + 85). **This is the element §C marks not-loaded**; filing date is what establishes priority between competing secured parties, which contractual seniority language cannot |
| `lapsesOn` | property | `http://example.org/fibo/lapsesOn` | 64 | filing → statutory expiry. **64, not 65** — one filing carries no expiration date, and the predicate is written only where the registry supplies a value rather than defaulted, so a missing expiry stays visibly missing. Distinct from a Termination: lapse is the clock running out, termination is the secured party releasing |
| `filingNumber` | property | `http://example.org/fibo/filingNumber` | 65 | filing → its UCC number, the registry's own key. Stored instead of the image URL, which is signed and expires |
| `filingStatus` | property | `http://example.org/fibo/filingStatus` | 65 | filing → `Filed` / `Lapsed`, as the registry states it |
| `documentType` | property | `http://example.org/fibo/documentType` | 65 | filing → `UCC1`. Present so a later pull that includes standalone UCC3s does not need a schema change |
| `debtorOfRecord` | property | `http://example.org/fibo/debtorOfRecord` | 65 | filing → the debtor name as filed. Deliberately NOT an edge to a `LegalEntity`: the register keys on legal name, and the match to an LEI is our claim, recorded in Postgres with a score, never asserted here as filed fact |
| `securedPartyOf` | property | `http://example.org/fibo/securedPartyOf` | 66 | filing → `ex:SecuredParty`. **66, not 65** — one filing names two secured parties, which is the ordinary case this product exists to surface and the reason the edge is not a scalar attribute |
| `amendedBy` | property | `http://example.org/fibo/amendedBy` | 85 | filing → `ex:UccAmendment`. Without this edge the amendment nodes are unreachable from the filing and the termination history cannot be walked |
| `amendmentAction` | property | `http://example.org/fibo/amendmentAction` | **87, not 85** | amendment → its action, as the registry words it. Kept verbatim (`Change a secured`, not a tidied synonym) so the value is the registry's and not ours. **87 and not 85: two amendments (`20130840671X`, `200706993541`) carry TWO actions each.** The first published figure counted amendments, which is the wrong unit — `ex:UccAmendment` and `ex:amendedBy` are 85 because those count amendments; this predicate counts ACTIONS. A consumer assuming one action per amendment silently drops half of each of those two |

**Counting terminations gives two right answers, and they differ.** **15
amendments** carry `Termination`; **13 filings** do. `200706993541` is one of the
two double-action nodes (`Termination` + `Amendment`), and a second filing carries
two terminating amendments. Neither number is wrong — they count different units,
which is the same trap as `amendmentAction` above. State which level you mean.
Reported by `ccf-sdk` 2026-09-10 and reproduced here.

**Vault mirror.** These **twelve** terms are new since the last mirror refresh of
`wiki/context-products/content/fibo-iri-binding`. The mirror is downstream of
this file and does not update itself.

#### Wave 14 Task 12 · internal overlay — loan-level privacy ceiling (`abs-securitization-surveillance`)

Three `ex:` terms carried by the `LoanLevelPrivacyConstraint` nodes written by
`loaders/load_abs_overlay_wave14.py` — one node per ABS-EE quasi-identifier
field a below-loan principal must never receive. Bound **before** the write,
same discipline as the Wave 14 threshold predicates above: Fluree is
append-only, so generating against an unbound name could not be corrected,
only contradicted.

These are `ex:` application attributes rather than candidate FIBO terms, so
**no EDM Council search was run for them** — CLAUDE.md's binding rule applies
to FIBO coverage; a policy classification of the bank's own data-handling is
not a fact about the financial world FIBO models. Said plainly rather than
implied: this is not an absence check like the ones above it, it is a
different kind of term.

**Near neighbour found, and not reused.** `ex:ResidencyConstraint` /
`ex:subjectToConstraint` (Wave 13b, `kyc-refresh-beneficial-ownership`, table
below) are the same *shape* — a `Constraint` class plus an edge from the
governed thing to it. Not reused, because the two constraints answer
different questions on different subjects: a residency constraint restricts
*where a person's data may be materialized* and hangs off a `Person` node; a
loan-level privacy constraint restricts *what granularity a field may be
released at* and hangs off nothing — it is queried directly by field name via
`restrictsField`, because the "subject" here is a Postgres column, not a
graph node with anything else to attach an edge to. Modelling this one as
`subjectToConstraint` from a field would need a node for the field, which
does not otherwise exist and would exist for no other purpose.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `LoanLevelPrivacyConstraint` | class | `http://example.org/fibo/LoanLevelPrivacyConstraint` | 4 | not an EDM Council absence check (see above) — a policy object naming a field-level release floor, not a fact FIBO models |
| `restrictsField` | property | `http://example.org/fibo/restrictsField` | 4 | the ABS-EE field name the constraint governs. A literal, not an edge — the field has no node of its own to be an edge's object |
| `minimumGranularity` | property | `http://example.org/fibo/minimumGranularity` | 4 | the coarsest-or-finer floor the field may be released at (`deal`/`tranche`/`cohort`/`loan`, coarse to fine). All four constraint nodes carry `cohort` — the ABS-EE quasi-identifiers stay at cohort-or-coarser even for a principal whose own entitlement ceiling (`abs_granularity_entitlement`) would otherwise let it go to `loan` |

**Vault mirror needs refreshing for all three**, plus the `SYN-` synthetic
identifier format above. Sent through the agent exchange on 2026-08-23
(`2026-08-23T20-03-01Z-wave14-task12-bindings`), ahead of the Wave 14
close-out.

#### Wave 11c · provenance and the engineering marks

CLAUDE.md rule 1 requires three provenance classes labelled per element, and
requires an engineered condition to be labelled honestly rather than presented
as emergent. These predicates are how that rule is enforced *in the data*.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `provenance` | property | `http://example.org/fibo/provenance` | **7,841** (measured 2026-09-12) | carries one of the three CLAUDE.md classes — `public`, `synthetic — internal`, `synthetic — engineered`. FIBO has no provenance vocabulary; PROV-O would be the standard choice and is deliberately not imported, because the three classes here are this project's own taxonomy, not PROV's |
| `edgeProvenance` | property | `http://example.org/fibo/edgeProvenance` | 15 | the same statement about a *relationship* rather than a node. Separate predicate because an edge in this estate has no reified node to hang `ex:provenance` on |
| `effectiveDateProvenance` | property | `http://example.org/fibo/effectiveDateProvenance` | 25 | narrows provenance to one field. An amendment's *count* is public and its *date* is not, so a single node-level class would be wrong in both directions |
| `bookingDateProvenance` | property | `http://example.org/fibo/bookingDateProvenance` | 25 | as above, for the assertion-time side of the same amendment |
| `effectiveDateNote` | property | `http://example.org/fibo/effectiveDateNote` | 25 | names the *derivation*, which a provenance class alone does not: `synthetic — engineered` says a date was invented, not how or why |
| `isEngineeredBookingLag` | property | `http://example.org/fibo/isEngineeredBookingLag` | 3 | marks the three amendments whose booking lag was planted so `as_of` and `known_as_of` return different answers. Queryable, so the engineered set can be isolated rather than remembered |
| `isEngineeredRecordingLag` | property | `http://example.org/fibo/isEngineeredRecordingLag` | 1 | the same mark on the MNPI wall-crossing whose recording lag was planted |

#### Wave 11c · covenant attributes (Waves 5 and 6)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `covenantType` | property | `http://example.org/fibo/covenantType` | 218 | FIBO's `BreachOfCovenant` exists (and is bound); the covenant *taxonomy* — leverage, interest coverage, fixed-charge — does not |
| `threshold` | property | `http://example.org/fibo/threshold` | 217 | the numeric level a covenant tests against; no FIBO property expresses it |
| `unit` | property | `http://example.org/fibo/unit` | 180 | the threshold's unit (ratio, currency, percent). **Name collision, recorded honestly:** `fibo-fnd-plc-adr:Unit` exists — verified at `FND/Places/Addresses.rdf:720`, `edmcouncil/fibo` clone `119fa8c` — as an `owl:NamedIndividual` typed `SecondaryUnitDesignator`, an apartment/suite designator, whose `rdfs:label` is the lowercase string `"unit"`. That is an exact label match, not a case difference, and this project's own absence methodology searches `rdf:about` / `rdf:ID` / `rdfs:label` with no case-folding. Different concept, same string: a consumer resolving by label must not conflate them |
| `direction` | property | `http://example.org/fibo/direction` | 180 | whether the threshold is a floor or a ceiling (`min` / `max`). Without it a threshold is unusable — 3.5x means nothing until you know which side breaches |
| `testFrequency` | property | `http://example.org/fibo/testFrequency` | 180 | how often the covenant is tested; determines which measurement periods exist at all |
| `observedValue` | property | `http://example.org/fibo/observedValue` | 2 | the measured value on a breach event, against which `threshold` is compared |
| `compliantToday` | property | `http://example.org/fibo/compliantToday` | 2 | a current-state convenience flag on a breach event. **Deliberately not authoritative** — the as-of answer comes from the temporal chain, and a consumer that trusts this flag over a time-scoped query will be wrong the moment the chain is extended |

#### Wave 11c · amendment attributes (Wave 5)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `amends` | property | `http://example.org/fibo/amends` | 25 | links the amendment event to the facility it amends. FIBO relates contracts to parties and instruments, not an amendment to its subject agreement |
| `amendmentNumber` | property | `http://example.org/fibo/amendmentNumber` | 25 | ordinal within a facility's amendment sequence; the ordering is what makes supersession queryable |
| `bookingLagDays` | property | `http://example.org/fibo/bookingLagDays` | 25 | the gap between effective date and booked date, precomputed. Derivable from the two dates, and stored anyway because it is the quantity the engineered condition is *about* |

#### Wave 11c · passage anchoring and document lineage (Wave 6)

MongoDB owns passage-level lineage; these predicates are the Fluree side of the
join — enough to reach a passage, not a copy of it.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `evidencedBy` | property | `http://example.org/fibo/evidencedBy` | 43 | links a covenant to the filed passage that evidences it. No FIBO predicate ties an assertion to its source text |
| `documentId` | property | `http://example.org/fibo/documentId` | 37 | the MongoDB document the passage lives in — the cross-store key, without which the lineage claim cannot be followed |
| `startOffset` | property | `http://example.org/fibo/startOffset` | **261 assertions · 255 subjects** (measured 2026-09-12) | character offset of the passage span. Span offsets are how a citation is checked rather than trusted — **but only where an end exists.** On `CovenantDefinition` this is a true span start, paired with `endOffset`. On `DefinedTerm` (158), `MeasurementPeriod` (11) and one `Covenant` it is a **point anchor**: `sources/screening/covenant_definitions.json` gives a component only `declared_at` and `cited_at`, with no end offset anywhere, so **170 of the 255 subjects carry a start that no `endOffset` will ever pair with.** Nothing was dropped by the loader; the source has no end to drop. Flagged by the vault 2026-09-12 |
| `endOffset` | property | `http://example.org/fibo/endOffset` | **91 assertions · 85 subjects** (measured 2026-09-12) | the closing offset of a span that HAS one. **It does not pair 1:1 with `startOffset` and never did** — 255 subjects carry a start, 85 carry an end. The earlier wording, "the closing offset of the same span", implied a pairing that holds only for `CovenantDefinition`; see the `startOffset` row for why the other 170 are point anchors. A consumer that assumes every `startOffset` resolves to a span will fail on two thirds of them |
| `sourceOffset` | property | `http://example.org/fibo/sourceOffset` | 58 | the offset as *extracted*, before anchoring. Kept distinct from `startOffset` so a failed anchor is visible as a disagreement rather than silently corrected |
| `passageSha256` | property | `http://example.org/fibo/passageSha256` | 43 | content hash of the anchored span, so a consumer can detect that the underlying document changed under a citation |
| `anchorVerified` | property | `http://example.org/fibo/anchorVerified` | 37 | asserts the span was re-located in the live document, not merely recorded |
| `reason` | property | `http://example.org/fibo/reason` | 1 | why a `ContextDebt` instance exists — the specific shortfall, e.g. "no passage span contains the extracted offset" |
| `sourceAccession` | property | `http://example.org/fibo/sourceAccession` | 1,265 | the SEC accession number of the filing an assertion derives from. FIBO has no identifier scheme for an EDGAR submission |
| `evidence` | property | `http://example.org/fibo/evidence` | 9 | the quoted text supporting a rating-action assertion (Wave 11a), carried as a literal so the claim can be read without a second store lookup |

#### Wave 11c · MNPI wall (Wave 7)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `principalId` | property | `http://example.org/fibo/principalId` | 4 | the person crossed over the wall. An internal identifier, not a party URI — the wall is enforced on the entitlement subject, which is the bank's own principal |
| `basis` | property | `http://example.org/fibo/basis` | 4 | the stated reason for the crossing; what an audit reads first |
| `recordingLagDays` | property | `http://example.org/fibo/recordingLagDays` | 4 | gap between the crossing happening and being recorded. The MNPI analogue of `bookingLagDays`, and the axis the engineered case moves along |
| `noteId` | property | `http://example.org/fibo/noteId` | 9 | the restricted research note an embargo window applies to |
| `widensAccess` | property | `http://example.org/fibo/widensAccess` | 1 | marks a Reg FD event as *widening* access. Every other control event in the estate narrows it, so a consumer applying "control event ⇒ restrict" uniformly gets this one backwards |

#### Wave 11c · rating assertions (Wave 11a)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `grade` | property | `http://example.org/fibo/grade` | 245 | the internal grade on a grade-assertion node. FIBO's `OrganizationCreditRating` (bound, Wave 11a) models an *agency* rating; this is the bank's own 15-point scale |
| `trigger` | property | `http://example.org/fibo/trigger` | 245 | what caused the grade assertion. Carried on the assertion node so a migration chain explains itself without a join |

#### BENEFICIAL OWNERSHIP QUANTIFICATION (Wave 13b)

| Local name | Prefix form | Full IRI |
| --- | --- | --- |
| hasOwnershipPercentage | `fibo-be-le-lei:hasOwnershipPercentage` | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/hasOwnershipPercentage` |

**Verified 2026-08-22** at `BE/LegalEntities/LEIEntities.rdf:407` in the
`edmcouncil/fibo` clone. An `owl:DatatypeProperty`, `rdfs:subPropertyOf`
`fibo-be-le-lei:isQuantifiedBy`, `rdfs:range` `xsd:decimal`, with
`skos:definition` *"the percentage ownership interest in the owned entity owned
by owning entity, if known"* and `cmns-av:adaptedFrom` the GLEIF LEI-CDF 2.1
specification — the same standard this estate's Level 2 records come from.

**It needs a subject, which is why the ownership is reified.** `A owns B` is an
edge with no node to carry a datatype property, so each chain gets a
`fibo-be-oac-cown:BeneficialOwnership` node — a class bound since Wave 3 and,
until Wave 13b, asserted zero times. Per-hop stakes stay in
`ccf_v2.bo_chain_hop`; only the effective percentage reaches the graph.

#### Wave 13b · beneficial-ownership reification

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `ownershipIn` | property | `http://example.org/fibo/ownershipIn` | 50 | links a `BeneficialOwnership` node to the entity owned. FIBO gives the class and the `hasBeneficialOwner` / `isBeneficialOwnerOf` pair between the PARTIES, but no property tying the reified ownership to its subject entity — without it the node carrying the percentage cannot say what the percentage is *of* |
| `heldBy` | property | `http://example.org/fibo/heldBy` | 50 | the other half: links the reified ownership to the person holding it. Deliberately NOT `hasBeneficialOwner`, which is already asserted entity → person; reusing it here would make one predicate mean two different things depending on its subject's type |

#### Wave 13b · data-residency policy (kyc-refresh-beneficial-ownership)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `ResidencyConstraint` | class | `http://example.org/fibo/ResidencyConstraint` | 1 | a rule restricting where person data may be materialized. **Verified absent 2026-08-22:** an exhaustive `rdf:about` search of the clone returns **zero** terms containing `Constraint` and zero containing `Residency` as a standalone concept. FIBO models a person's residence (`fibo-fnd-aap-ppl:hasResidence`) — a fact about the person — not a policy restricting who may see data about them |
| `subjectToConstraint` | property | `http://example.org/fibo/subjectToConstraint` | 25 | binds a person node to the constraint governing their data. An **object** property: it points at the constraint node and carries no literal, which is what lets it sit on a `Person` without duplicating a Postgres attribute (`validators/partition.py`, "every identity edge is an EDGE") |
| `requiresEntitlement` | property | `http://example.org/fibo/requiresEntitlement` | 1 | the entitlement a principal must hold to see data under the constraint. **Name collision, recorded honestly:** `fibo-fbc-fi-fi:Entitlement` exists, but its `skos:definition` is *"some obligation to deliver some security in the context of corporate actions"* — a delivery obligation, not an access right. Same word, unrelated concept; a consumer resolving by label must not conflate them |
| `appliesToCountry` | property | `http://example.org/fibo/appliesToCountry` | 27 | the countries a residency constraint covers, one assertion each rather than a delimited literal, so a query can ask "does this constraint cover Ireland?" without parsing a string |

#### Wave 13b · identity resolution (kyc-refresh-beneficial-ownership)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `variantId` | property | `http://example.org/fibo/variantId` | 426 | the surrogate key of a `person_name_variant` row. The Fluree `PersonName` node carries **only** this and its type — the name string, its source registry and its rendering are Postgres columns. Same pattern as `ex:documentId` reaching a MongoDB passage: enough to resolve the row, not a copy of it. An earlier version of this loader put all three attributes on the node and `validators/partition.py` failed it, correctly |
| `IdentityResolution` | class | `http://example.org/fibo/IdentityResolution` | 74 | the reified act of deciding whether two records are one person, carrying its own confidence. FIBO has no term for a resolution decision — `cmns-id:isIdentifiedBy` relates a thing to an identifier and says nothing about how confident anyone was |
| `resolvedSubject` | property | `http://example.org/fibo/resolvedSubject` | 148 | links a resolution to each of the two records it judged. Two per resolution |
| `resolutionConfidence` | property | `http://example.org/fibo/resolutionConfidence` | 74 | the score the resolver produced. §D requires **a confidence per resolution, never a silent merge**; without it the graph records a verdict with no basis |
| `screenedAgainst` | property | `http://example.org/fibo/screenedAgainst` | 19 | links a person to the sanctions entry they matched. The listing is public and the person is synthetic, so the edge is the only place that pairing exists. The object's local name **is** the `sanctions_entry.entry_id`, so the edge resolves to Postgres carrying no attribute; the score, the disposition and the listed name are `sanctions_screening_result` columns and stay there |

#### Wave 13b · offshore intermediary layer (kyc-refresh-beneficial-ownership)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `isIntermediaryFor` | property | `http://example.org/fibo/isIntermediaryFor` | 150 | links a corporate service provider to the vehicle it administers. **Verified absent 2026-08-22:** an exhaustive `rdf:about` search across the `edmcouncil/fibo` clone returns **zero** terms containing `intermediar` in any form, and the only `rdfs:label` matches are three entries for a Guyanese securities association whose company name happens to contain the word. `cmns-org:provides` was considered and rejected: it is declared with **no domain and no range** and a `skos:definition` of merely *"makes available"*, while `cmns-org:ServiceProvider`'s own restriction points `provides` at `cmns-org:Service`. Asserting it here would say the agent *makes the company available*, which is not the administration relationship |
| `jurisdictionCode` | property | `http://example.org/fibo/jurisdictionCode` | 494 | the ISO 3166-1 alpha-3 code an offshore vehicle or intermediary sits in. **Scope widened 2026-08-24** (190 → 494): `loaders/load_stub_jurisdictions.py` now also asserts it on 304 Exhibit 21 bridging stubs in `corporate-family-tree`, normalised to the SAME alpha-3 vocabulary — 137 stubs filed in Delaware (118 as `Delaware`, 19 as `DELAWARE`) plus those in 22 other US states all resolve to `USA`, Ontario and British Columbia to `CAN`, England and Wales to `GBR`. Two vocabularies in one predicate would be the Wave 11b unit-field collision, so the filed string goes on `filedJurisdiction` instead. FIBO relates a thing to a jurisdiction through `cmns-cxtdsg:isApplicableIn` (verified 2026-08-22 at `FND/Relations/Relations.rdf:277` — an `owl:ObjectProperty` with **no declared domain or range**) pointing at a jurisdiction **individual**. FIBO enumerates those individuals rather than deriving them, and it does not enumerate the ones this layer needs: searching every `rdf:about` in the clone for `*Jurisdiction` returns 3 for Virgin Islands and 1 for Jersey, but **zero** for Cayman, Seychelles, Panama or the Bahamas. Using the property would mean minting our own jurisdiction individuals under `ex:` anyway, and then carrying a code on them — one more hop to reach the same two-token literal that is the actual join key |

#### Wave 15 · Exhibit 21 subsidiary jurisdictions (corporate-family-tree)

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `filedJurisdiction` | property | `http://example.org/fibo/filedJurisdiction` | 304 | the jurisdiction string **exactly as filed** in an EDGAR Exhibit 21 subsidiary table, before normalisation to the alpha-3 code on `jurisdictionCode`. Not a FIBO concept and could not be: FIBO models the jurisdiction, not the provenance of a particular filer's spelling of it. Carried because normalising is lossy in one direction only — 137 of the 344 stubs are filed in Delaware — 118 spelled `Delaware`, 19 spelled `DELAWARE` — and all become `USA`, and a Delaware LLC and a Nevada LLC then read identically. The pair is the audit trail between the filed text and the code the Policy Operator filters on. Same `isFiboTerm false` + `schemaNote` declaration every `ex:` term carries. |

#### Wave 16 · banker opportunity ranking

**Verified against `sources/fibo/dev.fibo-quickstart.ttl`** (fetched
2026-08-24 from `https://spec.edmcouncil.org/fibo/ontology/master/latest/dev.fibo-quickstart.ttl`,
8,966,028 bytes — the **dev** quickstart, never `prod`, which omits 40
Provisional modules including nine terms this repo already binds). Positive
control (`grep -cP '[:#]LegalEntity\b'`) returned **1887**, proving the grep
pattern finds real terms in this Turtle-syntax file before the negative result
is trusted. `grep -oP '[:#](OpportunitySignal|coveredBy|comparableTo)\b'`
returned **no output** — all three absent, confirmed by a case-insensitive
substring sweep as well.

| Local name | Kind | Full IRI | Why not FIBO |
| --- | --- | --- | --- |
| `OpportunitySignal` | class | `http://example.org/fibo/OpportunitySignal` | no FIBO class for a origination-side opportunity observation. Distinct from Wave 10's `ex:WarningSignal`, which is credit-deterioration: the two carry opposite polarity and must not share a type, or a query for "what should I pitch" collects "what might default" |
| `magnitude` | property | `http://example.org/fibo/magnitude` | new, Task 12, **omitted from the original binding row and the first exchange bundle -- corrected in the final fix wave (2026-08-25).** **Verified absent** via `ccf.fibo.fibo_absent("magnitude")` against `dev.fibo-quickstart.ttl`. Plain-string numeric literal on every `OpportunitySignal` node (`loaders/load_fluree_wave16.py:208,346`) carrying the signal's strength -- asserted 1,270 times, once per signal, current and superseded alike. Permitted in `validators/partition.py`'s `WAVE16_OPPORTUNITY_SIGNAL_PREDICATES` allowlist since the loader was written; the binding-table row was the gap, not the assertion |
| `coveredBy` | property | `http://example.org/fibo/coveredBy` | relates a prospect to the banker covering it. FIBO models employment and agency, not a bank's internal coverage assignment |
| `comparableTo` | property | `http://example.org/fibo/comparableTo` | peer comparability for the sector strategist's ranking. Derived from shared SIC plus size band; the basis is recorded on the edge via `ex:comparabilityBasis` so "comparable" is inspectable rather than implied |
| `comparabilityBasis` | property | `http://example.org/fibo/comparabilityBasis` | new, Task 12. **Verified absent** via `ccf.fibo.fibo_absent("comparabilityBasis")` against `dev.fibo-quickstart.ttl` before generation. **Fix round 1, Finding 2/3:** the human-readable derivation string, asserted PER DIRECTED PAIR (`"shared SIC 6798; size bands 1 vs 3 (peer {other LEI})"`), never per subject -- the first cut grouped by (sic, size_band), which made the string uniform per prospect but destroyed 20 of 25 real same-SIC pairs by splitting a 7-member SIC across 3 size terciles. The fix groups by SIC alone and DISCLOSES the size-band relationship in the string instead of filtering on it; the peer's own LEI is embedded so no two of a subject's several basis literals can ever collide under RDF set semantics. Asserted in lockstep with its `comparableTo` edge (same loop iteration), and `validators/test_ib_rank.py::test_comparable_to_and_basis_counts_match` asserts the two predicates' ledger-wide cardinalities are EQUAL. RDF has no edge-attachment point without reification, so this remains the estate's existing pattern (compare `ex:edgeProvenance`) applied to the same problem |
| `isCurrent` | property | `http://example.org/fibo/isCurrent` | new, Task 12. **Verified absent** via `ccf.fibo.fibo_absent("isCurrent")` against `dev.fibo-quickstart.ttl` before generation. Plain string `"true"`/`"false"` (never a typed boolean, per the no-typed-literals rule) on every `OpportunitySignal` node, so a current-value query can filter the 354 superseded rows out of the 1,270-row ledger without losing them from the graph |
| `primaryBankerId` | property | `http://example.org/fibo/primaryBankerId` | new, Task 12 Fix round 1 (Finding 1). **Verified absent** via `ccf.fibo.fibo_absent("primaryBankerId")` against `dev.fibo-quickstart.ttl`. Plain-string `banker_id` on a prospect entity node, naming which of its (possibly several) `coveredBy` bankers is primary. The first cut of `coveredBy` loaded ONLY the 50 primary `coverage_assignment` rows, which left 24 of 37 bankers with zero coverage edges in a product anchored on the banker (`docs/wave16-design.md` section 1). The fix loads all 150 rows as `coveredBy` and carries primacy here instead, because RDF cannot attach a literal to one specific edge among several sharing a subject and predicate without reifying the relationship, and a per-subject literal is the reification-free equivalent for a fact that is unique per prospect (exactly one primary assignment exists per covered LEI, verified live) |

`loaders/load_fluree_wave16.py` (Task 12, Fix round 1) is the first loader to
materialize `OpportunitySignal`/`coveredBy`/`comparableTo` in the ledger:
1,270 `OpportunitySignal` nodes (916 current, 354 superseded), 1,268
`signalAbout` edges (2 dangling -- two `ma_event_8k` signals key to
`SYN-SDART-*` synthetic ABS-deal identifiers that carry no Fluree entity
node), 354 `supersededBy` edges, 150 `coveredBy` edges (ALL
`coverage_assignment` rows, 37 distinct bankers -- Fix round 1 corrected
this from a primary-only load of 50 that left two-thirds of the roster with
an empty candidate set), 50 `primaryBankerId` literals (one per covered
prospect, naming which of its bankers is primary), and 50 `comparableTo`
edges (25 pairs, both directions, 21 within SIC 6798) with 50 matching
`comparabilityBasis` literals -- grouped by SIC alone; size band is
disclosed per pair in the basis text rather than used as a second grouping
key, which had cut the realized pair count to 5 against a 25-pair ceiling.
`observed_at`/`asserted_at` reuse the estate's existing
`ex:validFrom`/`ex:assertedAt` bitemporal predicates rather than minting new
ones; `ex:signalType`/`ex:observedAt` are deliberately NOT used as Fluree
literals here -- both are `POSTGRES_OWNED_ATTRS` in `validators/partition.py`,
claimed by Wave 11b's `signal_event` columns.

#### Wave 11c · self-describing T-Box metadata

Two predicates that describe *the vocabulary* rather than the data. Bound —
not omitted — because omission was the failure being fixed: a term with data
and no row is invisible downstream whether or not it is "real" vocabulary. They
are marked internal here so a consumer knows not to project them.

| Local name | Kind | Full IRI | Assertions | Why not FIBO |
| --- | --- | --- | --- | --- |
| `isFiboTerm` | property | `http://example.org/fibo/isFiboTerm` | 9 | **internal, not domain vocabulary.** Asserted `false` on every `ex:` class so a consumer holding only the graph can tell an invented class from a FIBO one. `owl:Class` alone does not say which ontology minted it |
| `schemaNote` | property | `http://example.org/fibo/schemaNote` | 9 | **internal, not domain vocabulary.** The prose form of the same statement, pointing at this document. Restored 2026-08-21 after being found orphaned — see `known-issues.md` §10.7 and `validators/orphan_terms.py` |

**Vault mirror.** All 45 rows above are outstanding against
`wiki/context-products/content/fibo-iri-binding`. Sent through the exchange as
a Wave 11c punch list; the custodian applies it.

**`validators/binding_drift.py` does NOT see them, and that is a gap, not a
pass.** This paragraph first claimed it would report all 45 as `CLAIM_MISSING`
— "the estate holds a bound term the vault makes no claim about" — which reads
right and is false. That validator derives its `CLAIM_MISSING` rows from
`sources/screening/fibo_wave8_confirmed.json`, a Wave 8 artifact listing
confirmed **FIBO** terms. No `ex:` term appears in it, so binding these 45
moved its verdict not at all: 11 agree · 29 disagree before and after.

So the newly bound terms are unpublished at the vault and **invisible to the
one check that exists to notice unpublished terms**. Recorded in
`known-issues.md` §10.7 rather than fixed here — extending that validator to
cover `ex:` terms would add 45 fresh failures to a validator already carrying
29, and the two populations need separate handling. The gate that *does* cover
them is `generators/verify_fibo_wave11b_confirm.py`, which now requires a
full-IRI row for every asserted term.

### 2026-08-22 — Wave 12 complete: `treasury-liquidity-position`, `fx-post-trade-reconciliation`

Two Tier 3 products, both Postgres + Fluree, no new store. Design:
`docs/wave12-design.md`. Plan: `docs/wave12-plan.md`. Known issues and
substitutions: `docs/known-issues.md` §12.

Wave 12's principal risk was **not** fetching wrong — every public source used
(FRED, Treasury.gov, DTCC's public SDR) was reachable and correctly shaped. The
risk was inventing badly: the intraday tick series and both FX break
populations are engineered, and the wave's whole argument rests on two
conditions no public source supplies — an 8bp intraday move and a break that
inverts under clock alignment. Both are proven by recomputation
(`validators/intraday.py`, `validators/reconcile.py`), not by row count.

#### What was loaded

**Postgres `ccf_v2` — fifteen new tables, all authoritative here and nowhere
else, plus one extended:**

| Table | Rows | Provenance | Contents |
| --- | ---: | --- | --- |
| `reference_rate` | 10,539 | `public` | FRED — SOFR, 4 published percentiles, 11 DGS constant-maturity tenors; 16 series total |
| `fx_reference_rate` | 3,942 | `public` | FRED H.10 — 5 fetched pairs + `EUR/GBP` derived as a cross (FRED publishes no `DEXEUUK`); 6 pairs, weekly-release calendar |
| `treasury_client` | 15 | derived | every anchor already holding >=1 deposit account (Wave 9) — the client set is *defined*, not selected |
| `investment_position` | 200 | `synthetic — internal` | MMF / commercial paper / T-bill, laddered across 156 distinct maturity dates |
| `concentration_limit` | 60 | `synthetic — internal` | per (holder, counterparty, intent) — the `intent` column is part of the key, not decoration (RULING F1) |
| `permitted_instrument` | 45 | `synthetic — internal` | one mandate per client (RULING F14 — the brief's "~75" assumed per-client versioning that was never built) |
| `intraday_tick` | 11,700 | `synthetic — engineered` | 30 trading days x 5 tenors x 78 five-minute ticks; endpoints are real `benchmark_curve` closes, the within-day path is a seeded Brownian bridge |
| `stale_signal` | 4 | `synthetic — engineered` | 1 deliberately stale (age vs its own `as_of`, never `now()` — RULING F15), 3 fresh, so the staleness gate discriminates |
| `fx_trade` | 500 | `synthetic — engineered` | 6 pairs, sampled from the real G10 Part 43 profile, value dates 2026-08-06→08-13 |
| `system_trade_record` | 1,815 | `synthetic — engineered` | per-system, per-amendment value; **per-system values genuinely differ** (RULING F24 — see Known issues) |
| `break_record` | 60 | `synthetic — engineered` | exactly 7 columns (RULING F22) — `designed_class` is the one deliberate answer-key exception; no computed field is loaded |
| `materiality_threshold` | 3 | `synthetic — engineered` | by intent: `break-investigation` 2.0 pips, `control-review` 5.0, `regulatory-report` 1.0 pips |
| `part43_profile` | 44 | `public` | derived G10 distributions (pair mix, execution-hour mix, action mix, chain lengths) — **no individual real trade is ever loaded** |
| `fx_intraday_tick` | 10,368 | `synthetic — engineered` | per-second-resolvable drift path per pair, the input `align_clocks` reads |
| `fx_pip_size` | 6 | `synthetic — internal` | 0.01 for `USD/JPY`, 0.0001 for the other five (RULING F13) |
| `deposit_account` | 120 (100 new) | mixed | **TWO-WRITER TABLE — see below** |

**`deposit_account` is now a two-writer table.** Wave 9's loader
(`loaders/load_collateral_wave9.py`) wrote the first 20 rows, prefix `DEP-*`,
and contains no `DELETE`/`TRUNCATE` — it upserts. Wave 12's
`loaders/load_postgres_wave12_treasury.py` added 100 more, prefix `W12-*`,
keyed on `account_id` for its own idempotency. **The two writers are disjoint
by prefix and neither reconciles against the other.** The risk this creates is
not in today's code: it is that a *future* reconcile added to Wave 9's loader,
believing itself sole author of the table (exactly the failure
`known-issues.md` §10.5 already recorded once, for a Fluree predicate), would
silently delete Wave 12's 100 rows. `validators/partition.py`'s "deposit_account
carries both writers' rows" check exists so that deletion fails loudly instead
of passing silently. **Read this paragraph before adding a DELETE or TRUNCATE
to either loader.**

**FX pair naming — market convention is a lookup table, not a rule.** Part 43
emits legs unordered (`Notional currency-Leg 1/2`), so a sorted-pair
normalisation reads `JPY/USD` where market convention is `USD/JPY`. USD is the
**base** for `USD/JPY` and `USD/CAD` but the **quote** for `EUR/USD`,
`GBP/USD`, and `AUD/USD` — a rule inferred from any one pair is wrong for at
least one other (the same shape of trap as §1.4's FRED direction map, D
below). `generators/part43.py`'s `_CONVENTION` table is the single point of
truth:

| Pair | Base | Quote |
| --- | --- | --- |
| `EUR/USD` | EUR | USD |
| `USD/JPY` | USD | JPY |
| `AUD/USD` | AUD | USD |
| `USD/CAD` | USD | CAD |
| `GBP/USD` | GBP | USD |
| `EUR/GBP` | EUR | GBP |

Applied once, at the fetch boundary (`normalise_pair`), and reused everywhere
else a pair name is needed — never re-derived. `EUR/GBP` is doubly irregular:
FRED has no `DEXEUUK` series at all, so its `fx_reference_rate` values are a
derived cross (USD-per-EUR) / (USD-per-GBP), provenance `public` with the
derivation recorded per row.

**Fluree `fibo-v2` — 55,691 triples at `t=1191`** (from 38,588 triples, the
Wave 11c merge baseline). New assertions:

| Assertion | Count | Notes |
| --- | ---: | --- |
| `ex:heldAt` | 200 | investment position -> counterparty entity node |
| `ex:concentratedIn` | 200 | investment position -> the same counterparty, second edge for the concentration query |
| `ex:RegulatoryPosture` nodes | 13 | across 12 observed `(jurisdiction, intent)` pairs; one pair carries two time-versioned values via `ex:supersededBy` so `as_of` genuinely flips |
| `fibo-fbc-pas-fpas:Trade` nodes | 500 | first materialized by this loader (bound Wave 8, never asserted before) |
| `ex:observedIn` | 1,815 | trade -> per-system observation node |
| `ex:systemObservedAt` | 1,815 | the observation timestamp — Fluree-owned; RULING F23 (see Known issues) renamed it away from `ex:observedAt`, already Wave 11b's |
| `ex:clockOffsetSeconds` | 3 | one per system: trading=0s, settlement=+47s, risk=-112s — distinctness is load-bearing |
| `ex:amends` | 130 | 105 new (FX amendment chains, `amd-*` subjects) + Wave 5's pre-existing 25 (`AMD-*` subjects) — shared predicate, disjoint subjects, subject-scoped reconcile only |
| `ex:amendmentSeq` | 1,920 | 1,815 on observation nodes + 105 on amendment-event nodes |
| `ReconciliationBreak` nodes | 60 | structure only — `involvesTrade`/`involvesSystemA`/`involvesSystemB`, no `raw_variance`, no `designed_class` (RULING F22 extended to Fluree) |

#### Files

| Path | Role |
| --- | --- |
| `generators/fetch_fred_rates.py`, `generators/fred_series.py` | the eleven FRED series, per-series direction map (§7.4's reciprocal trap) |
| `generators/fetch_treasury.py` (reused, read-only) | `benchmark_curve` — the tick series' real anchor |
| `generators/ticks.py`, `generators/generate_ticks.py` | Brownian-bridge tick interpolation, `max_rolling_move_bp` |
| `generators/generate_treasury.py` | clients, deposits, positions, limits, mandates, the stale signal |
| `generators/fetch_part43.py`, `generators/part43.py` | DTCC public SDR fetch + G10-filtered derived profile, `normalise_pair` |
| `generators/generate_fx_trades.py` | trades, system records, clock offsets, amendment chains, breaks |
| `generators/narrative_wave12.py` | the engineered inversion/survivor break construction |
| `loaders/load_rates_wave12.py` | `reference_rate`, `fx_reference_rate` |
| `loaders/load_postgres_wave12_treasury.py`, `loaders/load_postgres_wave12_fx.py` | the Postgres side of both products |
| `loaders/load_fluree_wave12_treasury.py`, `loaders/load_fluree_wave12_fx.py` | `heldAt`/`concentratedIn`/posture overlay; `observedIn`/`amends`/offsets/break structure |
| `validators/intraday.py` | the treasury gate — 90-minute rolling move, anchor fidelity, tick spacing, naive-allocation breach, staleness |
| `validators/reconcile.py` | the FX gate — inversion, survivor, decomposition closure, break mix, chain shape, rate coverage |
| `validators/test_ticks.py`, `validators/test_fred_series.py`, `validators/test_part43.py`, `validators/test_narrative_wave12.py` | pure-function suites, 11+14+9+8 cases |
| `sources/screening/wave12_{rates,ticks,treasury,part43_profile,fx,fx_ticks}.json` | the committed artifacts |
| `sources/fred/`, `sources/part43/` | retrieval manifests with dates and query strings |

#### Binding

**Four new rows** — three real FIBO terms and one `ex:` extension — added
under *"Wave 12 addition — investment instrument classes"* and *"Wave 12 —
regulatory posture overlay"* above. This falsified design §1.1's "no new FIBO
binding is required by this wave": that claim was checked against the class
names the specs' own §C prose mentions, not against the concrete typing the
loader actually needed. See `docs/known-issues.md` §12 for the full account.

| Term | Kind | Full IRI |
| --- | --- | --- |
| `CommercialPaper` | class | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/TradedShortTermDebt/CommercialPaper` |
| `TreasuryBill` | class | `https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/Bonds/TreasuryBill` |
| `MutualFund` | class | `https://spec.edmcouncil.org/fibo/ontology/SEC/Funds/Funds/MutualFund` |
| `RegulatoryPosture` | `ex:` class | `http://example.org/fibo/RegulatoryPosture` |

**Vault mirror needs refreshing for all four.** Sent through the agent
exchange on 2026-08-22 (`2026-08-22T00-50-00Z-wave12-treasury-bindings`) by
Task 9, ahead of this close-out — not re-sent here. The Wave 10, 11a, 11b, and
11c punch lists remain outstanding at the vault.

`Trade` and `TradeLifecycleEvent` needed no new binding row — both were bound
in Wave 8 and simply never materialized as `owl:Class` nodes until this
loader. `SystemObservation`, `ReconciliationBreak`, and `TradeSystem` are `ex:`
extensions with no FIBO equivalent (a bank's own internal system-observation
apparatus, not a fact about the financial world) but carry no data an
external consumer needs to resolve, so they are recorded in the `ex:`
extension register in `validators/partition.py` rather than as binding-table
rows of their own.

#### Store partition

`validators/partition.py` grew from 19 checks to **25**, all passing. The six
new claims: every Wave 12 Postgres table present and populated; `heldAt` /
`concentratedIn` / `observedIn` / `amends` exist as columns in no Postgres
table; no rate value from `reference_rate`/`fx_reference_rate` is duplicated
onto a Fluree node; no treasury-node or FX-node attribute in the graph beyond
each loader's own allowlist; `deposit_account` genuinely carries both writers'
rows.

#### Validator baseline at merge

`partition.py` **25/25** · `conditions.py` **111 passed · 0 failed** (91 +
10 treasury + 10 FX) · `intraday.py` **9/9** · `reconcile.py` **10/10** ·
`series.py` **PASS** (Wave 11a unmoved) · `surveillance.py` **PASS** (Wave 11b
unmoved) · `traversal.py`, `bitemporal.py`, `projection.py` **PASS** ·
`orphan_terms.py` **86/86** · `binding_drift.py` **11 agree / 32 disagree**
(+3 from the three new FIBO terms, unpublished at the vault until the Task 9
punch list is applied — not a regression) ·
`artifact_reproduces_store.py` **52/56**, exit 1, **pre-existing** (the two
Wave 10 duplicate-row items, `known-issues.md` §8.16, plus the Wave 11a
rating-actions gap) — confirmed none of the four failing lines references any
Wave 12 table or predicate · 15 pure-function suites, all green.

#### Seven defects found and fixed this wave

Full account: `docs/known-issues.md` §12. Headline lesson: a units error
(`max_rolling_move_bp` scaled x100 -> x10000) passed two *synthetic* ramp
tests whose magnitudes were themselves invented, and was only caught once a
test was anchored to a real curve movement (4.10 -> 4.18 IS 8bp) that a
mis-scaled implementation cannot satisfy by construction.

Requirements source: `Q019` and the 21 `context-products` specs in the Obsidian vault, via the `obsidian-vault` MCP server. Working brief: `CLAUDE.md`.


*Document generated from the CCF / FIBO Fluree data-prep conversation for reuse in Claude Code projects via* `CLAUDE.md`*.*
### 2026-08-22 — Wave 13a complete: `credit-memo-context`

Tier 4, Postgres + Fluree + MongoDB. 14 of 21 products. Registered in
`validators/conditions.py` at **8 conditions**, total 111 → **119**.
`validators/memo_debt.py` 6/6 with a six-way mutation self-test.
`orphan_terms` 86 → **90**.

**New tables (Postgres `ccf_v2`).**

| Table | Rows | Note |
|---|---|---|
| `peer_cohort` | 324 | `(sic, tag, frame)` denominators for peer thinness. Two CHECK constraints make a negative or ≥1 thinness unrepresentable |
| `memo_section_template` | 31 | 4 memo types, 29 distinct section names |
| `debt_weight` | 4 | §D step 7 component weights — stored, not coded, so the gate and the product read the same rows |
| `memo_context_debt` | 20 | a **cache**; `memo_debt.py` recomputes and never reads it to validate it |

**Extended.** `peer_entity` 162 → **1,678**, `peer_fact` 2,311 → **22,494**
(7,149 EDGAR filers enumerated across 18 SICs). `facility` 45 → **57**
(15 → 22 borrowers). `collateral_asset` 81 → **91**, `collateral_pledge`
85 → **95**. MongoDB `document` 59 → **136**, `passage` 15,934 → **19,683**,
`memorandum` 22 → **40**. Fluree +30 triples, 2 `PolicyVersion` nodes.

**New `ex:` terms (4).** `ecoaReasoningPathRestricted`,
`regOInsiderThresholdUsd`, `creditLimitEnvelopeUsd`, `debtToleranceDefault` —
application extensions, no FIBO equivalent for a bank-internal credit-memo
policy envelope. **No new FIBO terms; the binding table is unchanged, so the
vault mirror needs no refresh for this wave.**

**Provenance.** Narrative sections and peer cohorts are `public` (SEC EDGAR).
Memoranda, templates, weights and policy envelopes are `synthetic — internal`.
The debt components are `derived`. **Nothing in this wave is
`synthetic — engineered`** — §F5's tolerance breach and §F6's covenant cascade
both fell out of measured data and were not manufactured.

**Two findings worth carrying.** Peer-cohort sizes previously measured this
project's own fetch scope rather than `frames` coverage — 943 of 1,119 cohorts
had every fetched peer reporting, so they demonstrated no sparsity at all.
And extending `facility` armed four latent loaders that derive identity from
position in a query result (`known-issues.md` §13.3); none were triggered, none
are repaired, and they want their own wave.

---

### 2026-08-22 — Wave 13b complete: `kyc-refresh-beneficial-ownership`

Tier 4, Postgres + Fluree + MongoDB. **15 of 21 products.** Registered in
`validators/conditions.py` at **12 conditions**, total 119 → **131**.
`validators/beneficial_ownership.py` 6/6, every gate with a falsification arm.
`partition` 26 → **27** (new check). `orphan_terms` 90 → **103**.

**New tables (Postgres `ccf_v2`).**

| Table | Rows | Note |
|---|---|---|
| `sanctions_entry` | 19,730 | OFAC SDN + Consolidated, `public`. 7,620 individuals |
| `sanctions_name` | 45,511 | every primary name and a.k.a., with OFAC's own `strong`/`weak` alias confidence. `name_norm` written by `ccf.names.normalize` — the same function the resolver scores with |
| `registry_company` | 140 | GLEIF Level 2 entities. NOT `legal_entity`: three `conditions.py` checks count that table without filtering `is_anchor` |
| `corporate_ownership_record` | 280 | ACTIVE DIRECT relationships. 186 cross-border. `cross_border` is a VIEW, never a stored column |
| `psc_person` | 210 | pseudonymized PSC attributes. 40 transliteration-capable, 25 EU-resident |
| `resolution_policy` | 3 | `auto_clear` 0.95 · `review_floor` 0.70 · `merge_threshold` 0.90. **Read by the scorer and by every gate; never hardcoded** |
| `name_variant_rule` | 5 | the §C variant/transliteration rules |
| `sanctions_screening_result` | 19 | all 19 in the review band |
| `bo_threshold` | 18 | keyed `(jurisdiction, intent)` — 3 jurisdictions where intent CHANGES the answer |
| `kyc_refresh_state` | 50 | 19 overdue, 31 current, anchored on a fixed `as_of` |
| `offshore_intermediary` / `offshore_vehicle` / `offshore_administration` | 40 / 150 / 150 | ICIJ-*shaped*, not ICIJ-named |
| `engineered_entity` | 125 | 119 holdcos + 6 cycle members, with the jurisdictions the cycle never had |
| `bo_chain` / `bo_chain_hop` | 50 / 169 | 8 chains at depth ≥ 5; effective percentages recomputed from hops on load |

**Extended, not replaced.** `person` +210 (`person_key_source='psc'`);
`person_name_variant` +426 across four registries; `person_crosswalk` +500;
`principal` +1 row and +1 column (`sees_eu_person_data`).

**MongoDB `fibo_v2`.** New `kyc_document` collection, 32 files (9 ownership
declarations, 5 EU-residency); `passage` +82 with verified span offsets.

**Views.** `v_entity_jurisdiction` and `v_ownership_cross_border` now live in
`ccf/views.py` and are built from whichever source tables exist, so no loader
can rebuild one without a later wave's sources. Key column is `entity_id`, not
`lei` — engineered entities have no LEI.

**Provenance, stated honestly.** The person layer is `synthetic — engineered`,
not `public`. Two measurements forced that label. Companies House publishes PSC
names **already romanized**, so the transliteration ambiguity §F5 wants is not
observable in the source and is reconstructed from the nationality
distribution. And a faithful resample yields **zero** transliteration-capable
persons — British nationals are 147k of 184k — so §F5 could not be met by a
faithful draw at any sample size. `MIN_PER_SCRIPT` forces a 42-person cohort;
every such person carries `stratified: true`.

**Privacy is mechanical, not promised.** The PSC snapshot was fetched to a
scratch path outside the repository, pseudonymized in the same pass that read
it, and deleted. No real→pseudonym mapping exists anywhere. The gate that
proves it is the one that can fail: every emitted name token must come from the
closed bank in `generators/name_bank.py`.
`validators/test_psc_pseudonymization.py` 6/6.

**The snapshot is fetched once, ever.** Everything the person layer needs from
Companies House is a *distribution*, never a record, so those distributions are
extracted, k-anonymised at `k=20` and committed as
`sources/screening/wave13b_psc_distributions.json` — 114 KB of counts, no
identities. The generator prefers that file and does not download at all.

This closes a hole the design accepted rather than solved (§7): re-deriving
used to mean re-downloading 70 MB of real living people's records, and since
Companies House replaces the dated snapshot, exact re-derivation was becoming
impossible anyway. Two tables had to be filtered that a first pass wrongly
called safe — `dob_bands` and `multiplicity` both bottomed out at a count of
**1**, and "one person controls 46 companies" names the register's most
prolific controller. Only `dob_months` (12 rows, min 35,577) and `ceased`
(2 rows, min 83,890) are left unfiltered.

`generate()` takes aggregates on **both** paths, so there is no second code
path that could depend on something the committed file does not carry. A plain
run now REFUSES to redraw the person layer, because `bo_chain`,
`person_name_variant`, `person_crosswalk`, `sanctions_screening_result` and 32
KYC documents all reference those `person_key`s.

**What GLEIF actually contains, measured with no caps.** The full daily golden
copy (485,285 records) gives an anchor-reachable component of 190 entities,
**maximum depth 4, zero chains at depth 5**, and no chain reaching a natural
person. Wave 3's depth finding came from a capped crawl; this one is a
measurement, and it is what makes §F1/§F3's engineering budget defensible.

**Two conditions were passing against the wrong quantity.** The
cross-shareholding check counted cycle MEMBERS — one 3-cycle reporting 3/3
against a floor asking for two cycles, unable to fail at any point. And two of
four planted registry contradictions were labels rather than conditions: both
`understated_pct` plants sat on chains already below the threshold, so
understating concealed nothing. Both found by recomputing rather than reading a
flag. `known-issues.md` §14.7, §14.9.

---

## Wave 14 — `abs-securitization-surveillance` (2026-08-23)

Three auto-loan ABS deals, twelve monthly periods each, loaded from SEC Form
ABS-EE and the accompanying prospectuses and servicer reports. **Depth, not
breadth**, per CLAUDE.md rule 6: 36 deal-periods rather than a wide
cross-section.

### What is loaded, measured against the stores

| Store | Contents | Count |
|---|---|---|
| Postgres `ccf_v2` | `abs_loan_period` | 1,322,453 |
| | `abs_servicer_report` | 36 |
| | `abs_vintage_benchmark` | 24 |
| | `abs_tranche` | 18 |
| | `abs_cohort_performance` | 132 |
| | `abs_holding` | 6 |
| | `abs_repurchase` | 8 |
| | `abs_materialization_policy` | 4 |
| | `abs_deal`, `abs_granularity_entitlement` | 3 each |
| | `abs_cost_measurement` | 4 per stored run |
| MongoDB `fibo_v2` | prospectus + servicer documents | 39 |
| | `trigger_anchor` | 10 |
| Fluree `fibo-v2` | total triples after the wave | 61,764 |

`abs_vintage_benchmark` is keyed `(asset_class, vintage, period)`. Keyed with
`credit_tier` as well, the three deals fell into three separate cells and
`deal_count` was **1 in all 36 rows** — every benchmark was a cohort of one, so
§F condition 7 and §D step 6 compared each deal against itself. Tier is the
*contrast* dimension (design §2), not a grouping one; it survives as
`credit_tiers`. Vintage 2022 now benchmarks 2 deals, `prime+subprime`, which is
the pair the deal selection was made for.

The three trusts carry **`SYN-` synthetic identifiers**, not LEIs: an ABS trust
has no GLEIF registration, so there is nothing real to use and a fabricated
20-character string would be indistinguishable from the real anchors'. This is
the first estate-wide use of the `SYN-` format decided 2026-08-23.

Their `legal_entity` rows are **`public`**, not `synthetic — internal`: the
legal name and CIK come straight from EDGAR and only the surrogate key is
minted, and rule 1 reserves `synthetic — internal` for what is "invented
because it is bank-internal by nature", which a trust's legal identity is not.
The `crosswalk` rows stay `synthetic — internal`, correctly — an
`internal_client_id` genuinely is bank-internal.

**This wave added NO new FIBO object property, and briefly added a wrong one.**
`fibo-sec-dbt-dbti:isSubordinatedTo` was already bound in the Wave 8
securitization block and is the correct term for a tranche waterfall. Task 1
nonetheless added `fibo-fnd-agr-ctr:isSubordinateTo` as a second row — one
letter apart, a near-duplicate of a binding that already existed. That row has
been removed and the 16 edges re-asserted on the term that was already there.
**The mirror needs no new object property from this wave.**

`fibo-fnd-agr-ctr:isSubordinateTo` is the **wrong property** for this: its
domain and range are `WrittenContract` and it means "the primary contract
referenced by a subordinate agreement" — a document cross-reference, not a
payment waterfall — while the 16 edges are tranche → tranche. The already-bound
`fibo-sec-dbt-dbti:isSubordinatedTo` has domain and range
`TradableDebtInstrument` and is defined as "the target security has a higher
priority than the security in question". `Tranche` reaches
`TradableDebtInstrument` through `StructuredFinanceInstrument` →
`PoolBackedSecurity`, so nothing is violated and the subject/object direction is
unchanged. The 16 edges were retracted and re-asserted on the correct term.

**How the first binding passed verification is the durable lesson.** It was
"verified against the EDM Council source" by fetching the term URL and seeing
HTTP 200. That verifies nothing — measured 2026-08-23:

    .../SEC/Debt/PoolBackedSecurities/NotARealTermXYZ  →  HTTP 200, 43,640 bytes

The path prefix is content-negotiated and the local name is **ignored entirely**,
so every term under a real ontology path returns 200 whether it exists or not.
The only valid test is fetching the containing ontology and grepping it for
`rdf:about="&prefix;LocalName"`, which returns 0 for that bogus name. Any
binding in this table justified by "the URL resolves" should be re-checked that
way.

`specifiesTrigger`, `hasTrancheType`, `hasAttachmentPoint` and
`hasDetachmentPoint` are bound in the same table.

### The store partition, and the one deliberate duplicate

Fluree owns deal structure and **trigger thresholds** — what the threshold is,
when it took effect, and which prospectus passage defines it. Postgres owns
every **measured** quantity. MongoDB owns filed text and passage anchors.

One value is deliberately held in **two** stores: the filed delinquency
trigger (24.00 / 24.00 / 4.65). Fluree's `ex:thresholdValue` is authoritative,
and `abs_servicer_report.published_delinquency_trigger` records what the
*servicer report* printed, which is a different filing from the prospectus the
threshold was extracted from.

It was briefly in three. `document.published_measures` carried the parsed
servicer figures — 12 keys across 36 documents, 288 values byte-identical to
`abs_servicer_report`, `delinquency_trigger` among them. That was removed
(RULING F52): the estate was contradicting itself, since
`load_abs_fluree_wave14.py` had already declined to write the same measures for
exactly this reason. `published_measures` now holds `source_format` alone,
which is a property of the document and owned by nothing else.

Keeping a duplicate is only defensible if the agreement is checked, so
`validators/partition.py` asserts it per deal, in both directions, and reddens
on a 0.01 drift, on a deal losing its trigger, or on a deal resolving to two.
Everything else is single-writer: **25** ABS measure predicates are asserted
absent from Fluree, no other threshold column may exist on any `abs_` table,
and 17 measure field names are asserted absent from MongoDB across `document`,
`trigger_anchor` and `passage`, at top level **and** nested — there is no
longer a permitted envelope.

### Provenance

`public` for everything filed — including the two materialized aggregates
`abs_cohort_performance` and `abs_vintage_benchmark`, which are pure functions
of public loan data with nothing invented. `synthetic — internal` for the bank
overlay: holdings, entitlements, materialization policy. **One element is
`synthetic — engineered`** and is labelled so everywhere it appears: the
trigger amendment lowering SDART-2022-6's delinquency trigger from 24.00 to
13.50, effective 2025-11-01 but asserted 2026-01-11, creating a 71-day booking
lag with a period falling inside it. No real auto ABS amends a trigger; the
condition exists only because it was built.

`abs_cost_measurement` carries **no provenance column**. A measurement is not a
data element *with* a source, it *is* one — `measured_at`, `row_basis` and
`repeats` record its origin, and inventing a fourth class for it would break
CLAUDE.md rule 1.

### The measured cost curve

Full figures and method in `docs/wave14-design.md` §7.1. The headline: querying
one deal-period at loan granularity returns **35,814× more rows and accesses
882× more blocks** than at deal granularity, and the three aggregate rungs
(deal, tranche, cohort) are indistinguishable from one another. Cost is not
incurred gradually as granularity descends — it is incurred entirely at the
last step.

The block ratio is exactly reproducible run to run. The *time* multiple is not:
six runs on identical data ranged 55× to 252×, because the denominator is a
sub-millisecond figure on the noise floor. Publish the block ratio.

### Registered

Nine conditions in `validators/conditions.py`, taking the register from 137 to
**146 passed, 0 failed, 0 skipped**. Partition checks went from 27 to 30.

### Graph scale — the §F envelope is not the target (Dave, 2026-08-24)

**Decided: keep the loaded counts. §F's `~30 non-LEI stub entities` is wrong
and its `~500 entities` is a floor we exceed, and neither is a reason to
reshape the graph.**

The two §F lines cannot both hold against what the public sources supply:

    §F asks    ~500 entities  AND  ~30 non-LEI bridging stubs
    implies    ~470 LEI-bearing entities from GLEIF Level 2
    GLEIF supplies, for this cast                              153

Loaded, measured 2026-08-24: **816 `cmns-org:LegalEntity` nodes** — 153
`public`, 343 `synthetic — bridging`, 190 `synthetic — engineered` offshore
vehicles and intermediaries, 128 other `synthetic — engineered`, 2 `public`
reporting-bank — with **778 ownership edges**, which is on §F's ~800.

**Dave's rationale, and it settles the class of question rather than this
instance:** *this is not a production system — the data exists to demonstrate
how to use the CCF SDK.* An envelope figure earns its place when it makes a
behaviour demonstrable. `~800 edges` does that and is met. `~30 stubs`
described a composition — mostly LEI-bearing entities with a bridging fringe —
that the public record cannot produce for any cast of US mid-cap filers,
because their subsidiaries do not register LEIs. Honouring it would shrink the
graph to ~185 entities and make §F's own depth and jurisdiction floors tight,
to match a shape that was never reachable.

So the composition is inverted relative to the envelope and that is correct:
**the bridging class carries the bulk of the graph.** Recorded here rather than
left as a discrepancy for a later wave to rediscover, and sent to the vault to
correct the line.

**This does not license widening anything else.** The decision is about a
figure describing SCALE. A `>= N` that exists to make a condition demonstrable
— an amendment with a booking lag, a cycle, a family at four hops — is still a
floor with a purpose, and hitting the count while missing the condition is
still a failure.

### 2026-08-24 — Wave 16 Task 8b: extend the debt ladder to 48 obligors

`ib-opportunity-synthesis`'s §C Data Catalog names a "Debt maturity ladder"
element (public, Postgres, `E`). Wave 11a's `generate_instruments.py` had
loaded it for only 30 of 50 anchors — `OBLIGOR_COUNT = 30` there is a scope
choice for `rating-and-spread-migration`, not an eligibility ceiling — so
two-fifths of the prospect set carried no DCM signal at all, and §F's
divergence prospect (Braemar Hotels) ranked DCM #20 against a bar of "outside
the top-20" only because most of the field had nothing to rank it by.

**No new FIBO bindings.** This element is Postgres-only structured data, reusing
`debt_instrument` / `spread_observation`'s existing columns unchanged — the
vault mirror needs no refresh from this task.

`generators/extend_debt_ladder_wave16.py` recomputes eligibility live against
Postgres (never hardcoded): of the 20 anchors with no `debt_instrument` row,
18 carry a `LongTermDebt`-family XBRL fact and 2 (American Healthcare REIT,
Inc.; SMITH & WESSON BRANDS, INC.) carry neither and are excluded — giving
either a ladder would misrepresent what `rating-and-spread-migration`'s own
registered condition (`debt_instrument` cross-checked against
`financial_fact`) can support. Two instruments per eligible obligor,
`w16-i-*` ids (Wave 11a's `syn-i-*` rows untouched), both anchored to a real
Item 2.03 filing from `sources/screening/wave11a_issuance.json` (a better
source than `wave11b_8k_events.json` for this purpose — the latter's
`item == '2.03'` rows cover only 42 of 50 anchors, missing 5 of the 18 needed
here): one maturing inside 24 months of `AS_OF_IB` (2026-08-24), one >= 5
years past it.

**The 36 instruments themselves are `synthetic — engineered`, not merely a
detail of the spread series.** Only the `issue_date` is real, anchored to a
public Item 2.03 filing; coupon, maturity, face amount, seniority and rung
are all invented by this generator. That matters here specifically:
Thermon Group Holdings, Inc.'s DCM #3 ranking — the mirror half of §F's
divergence demonstration — rests on `w16-i-01a242`, a bond THIS module
minted, maturing **2028-06-13**: inside the 24-month near-wall horizon **by
construction**, not because the public record happened to show a wall
there. Its spread series carries a widening idiosyncratic trajectory, also
engineered. Presenting Thermon's near-term wall as an emergent property of
loaded data would misstate what produced it; it is the deliberately
engineered mirror of Braemar's genuinely-emergent flat band (see the
Wave 16 divergence discussion above and `docs/wave16-design.md` §6.2,
corrected the same day this note was added).

Of the three legs that make up each `spread_observation` row, `benchmark_bp`
(real Treasury par curve) and `market_oas_bp` (real FRED ICE BofA OAS
series) are `public`; only `idiosyncratic_bp` is invented within the spread
series itself, per-instrument flat or widening (18/36 drew widening) so the
DCM signal discriminates rather than being uniform.

`loaders/load_debt_ladder_wave16.py` upserts on `instrument_id` /
`(instrument_id, obs_date)`, never deletes, and refuses to load any id
lacking the `w16-i-` prefix before touching the database.

**Result:** 48 of 50 anchors now carry debt (was 30). 36 new instruments,
17,964 new spread observations. `debt_instrument` totals 96 rows (60
`syn-i-*` untouched + 36 `w16-i-*`); `spread_observation` totals 47,849
(29,885 + 17,964). `rating-and-spread-migration`'s registered conditions are
floors and all still pass — condition 1 (`obligors with a real LongTermDebt
fact`) rose 30 → 46 (16 of the 18 new obligors carry the exact `LongTermDebt`
tag rather than only a sibling in the family; that is expected and does not
weaken the floor), condition 2 (`debt instruments loaded`) rose 60 → 96.
`validators/conditions.py`: **156 passed, 0 failed, 0 skipped** before and
after (no condition flipped). `validators/partition.py`: **31/31** before
and after, unchanged.

### 2026-08-24 — Wave 16 Task 13: merger corpus into MongoDB, notes extended in SQLite

The last two of the five stores for `ib-opportunity-synthesis`. **No new
FIBO bindings** — this task is data only, both collections/tables reuse
shapes already bound in Wave 6 / Wave 7; the vault mirror needs no refresh.

**MongoDB.** `loaders/load_mongo_wave16.py` reads
`sources/screening/wave16_merger_docs.json` (15 filings: 5 DEFM14A, 4
PREM14A, 3 S-4, 3 S-4/A across 8 anchor entities) and segments each through
the same structure-aligned segmenter Wave 6/13a already use
(`generators/segment_passages.py`, `narrative=True` — these are proxies and
registration statements, not credit agreements), so a passage offset here
means exactly what it means everywhere else in the corpus: an index into
that document's own stored `text`, verified against `sha256`, never
re-searched. `document` grew 178 → 193, `passage` grew 23,100 → 37,305 (14,205
new, 42% structure-aligned). Every new `document` row carries `doc_type` —
`merger_proxy` for DEFM14A/PREM14A, `registration_s4` for S-4/S-4A, the same
vocabulary `generate_opportunity_signals.py`'s `signal_type` already uses for
the identical filings, so a consumer can join Mongo documents to Fluree
`OpportunitySignal` nodes on `source_ref == accession` and see matching
category names on both sides. **The pre-existing 178 documents all carry
`doc_type: None`, a gap from earlier waves — recorded in
`docs/known-issues.md` §21, left untouched rather than back-filled**, since
this loader did not write those rows and for many of them the honest value
is not knowable from here.

**SQLite.** `loaders/load_sqlite_wave16.py` grows `prospect_note` 18 → 50 and
adds three columns: `signal_type` (uniformly `banker_local_note` — the table
IS a banker's local-note log by definition, so this is a correct backfill on
the pre-existing 18, not an invented value), `materiality` (left `NULL` on
the pre-existing 18 — a judgement this task introduces, which nothing
entitles it to assert retroactively for notes it did not write), and
`rank_changing INTEGER DEFAULT 0`. All 32 new rows resolve `banker_id` against
Postgres `coverage_assignment` for that row's own `lei` — never a banker who
does not cover the prospect.

**Choosing the 6 `rank_changing` rows.** `rank_changing` is a CLAIM, proved
later by `validators/ib_rank.py` ranking each affected banker's coverage list
twice (with/without note signals) and diffing the order — this task never
computes or stores a score. But the selection is not arbitrary: since
`banker_local_note` is already a weighted, half-life-decayed signal type in
`generators/generate_ib_perspectives.py` (weight 0.6 under PSP-MA/PSP-DCM,
0.3 under PSP-SECTOR; half-life 60 days), the loader replays
`wave16_signals.json` through those weight vectors with exponential decay
as a **selection heuristic held only in memory**, ranks each banker's own
`coverage_assignment` list under the perspective implied by their desk
(M&A Advisory → PSP-MA; Leveraged Finance / Treasury Services → PSP-DCM;
CIB Coverage / Credit Risk → PSP-SECTOR — a judgement call, since no
banker→perspective table exists yet), and picks the prospect sitting just
below each banker's smallest adjacent-rank score gap. A single high-materiality
note (weight 0.6 or 0.3, magnitude 1.0, undecayed at observation) exceeds
every gap found by more than an order of magnitude, so the claim has a real
chance of holding under whatever exact algorithm Task 14 implements.

Idempotency (both loaders) proven by a named value, not a row count: the
SQLite loader guards on `existing_total >= 50 and existing_flagged >= 5` so a
rerun adds zero rows rather than mining the shrinking pool of note-free
coverage pairs forever (a real bug caught and fixed during this task — the
first cut grew the table by 6 rows on every rerun); the Mongo loader upserts
by `_id` and a rerun leaves both collection counts and one named passage's
`sha256` unchanged.

`validators/test_ib_rank.py` (7 new tests, 45 total, all pass): the
brief's own `>= 50 notes / >= 5 rank_changing` check, the flagged rows are
`materiality='high'` + `signal_type='banker_local_note'`, both loaders'
idempotency, every new note's `(banker_id, lei)` resolves in
`coverage_assignment`, every new `document` carries `doc_type` while the
178-row gap stays exactly 178, and every passage in a full document
re-derives from `text[start_offset:end_offset]` matching both the stored
`text` and `sha256`. `validators/partition.py`: **31/31**.
`validators/conditions.py`: **156 passed, 0 failed** (`ib-opportunity` has no
registered section yet — a later task's job).

### 2026-08-24 — Wave 16 Task 14: the ranking instrument (`validators/ib_rank.py`)

**No new FIBO bindings.** `validators/ib_rank.py` reads Postgres, SQLite and
`sources/screening/wave16_signals.json` — it does not touch Fluree assertions
that were not already bound in Task 12.

`ccf/ib_rank.py` is pure arithmetic (`decay`, `score`, `rank` — no I/O).
`validators/ib_rank.py` recomputes, on every run and never from a stored
flag, the four §F conditions §F cannot express as a `COUNT`:

1. **Divergence** — Braemar Hotels & Resorts Inc. ranks M&A #3 / DCM #22 of
   52 candidate LEIs; Thermon Group Holdings, Inc. mirrors it (DCM #3 / M&A
   #38), from the SAME signal set under `PSP-MA v2` / `PSP-DCM v2`.
2. **Candidate-set containment** — of 4 active `restricted_list` LEIs, **4**
   are exercised (present in some banker's raw coverage, confirmed absent
   from that banker's built candidate set); the §F floor is `>= 2` distinct
   restricted LEIs, not `>= 1` affected banker (Fix round 1, Finding 3).
3. **Note materiality** — **31 of 50** `prospect_note` rows move their OWN
   entity's rank position when included (the §F unit is notes, not
   (banker, LEI) pairs, which over-counts one strong note for every entity
   it passes over — Fix round 1, Finding 2).
4. **Weight replay** — v1 → v2 perspective weights reorder 39 of 52 PSP-MA
   candidates for the same `as_of`.

Fix round 1 also added `require_nonempty_weights()` /
`require_versions_differ()` so an empty or accidentally-identical weight
vector raises instead of silently scoring every LEI at 0.0 and letting the
alphabetical fallback masquerade as a real divergence (Finding 1).

`validators/test_ib_rank.py`: 59 → **67 passed** after the fix round (8 new
fixture tests, each proven both directions — fails on a known-broken input,
passes on the real one).

### 2026-08-24 — Wave 16 Task 15: `ib-opportunity-synthesis` registered — 18 of 21 products

**No new FIBO bindings.** `ex:OpportunitySignal` and its predicates (Task 12)
are only *read* here, not extended.

**`validators/conditions.py`** gains 5 `Check` entries — the four §F floors
that carry a condition, plus nothing for the envelope's shape figures
(~40 bankers, ~200 prospects — not targets, per Dave 2026-08-24):

| Condition | Floor | Actual |
| --- | --- | --- |
| real Schedule 13D filings, in-window and current | 5 | 10 |
| weight-vector versions | 2 | 2 |
| restricted entities inside coverage (distinct LEIs) | 2 | 4 |
| perspective divergence (M&A vs DCM) | 1 | 1 |
| notes moving their own entity's rank | 5 | 31 |

Full-file run: **161 passed · 0 failed · 0 skipped** (156 before this task).
`ib_restricted_in_coverage()` reads `restricted_list` (SQLite) and
`coverage_assignment` (Postgres) as two separate queries and intersects the
LEI sets in Python, since a cross-store SQL `JOIN` between them cannot
execute at all. `_ib_divergence()` / `_ib_note_materiality()` delegate to
`validators/ib_rank.py` rather than reimplementing the recomputation.

**`validators/spec_coverage.py`**: `ib-opportunity-synthesis` added to
`PRODUCTS`/`MANIFEST`. **18 of 18 §C catalog rows accounted for** — 12
probed clean, 5 covered by existing `conditions.py` checks (spread
trajectory → `rating-and-spread-migration`; coverage portfolio →
`client-360-coverage-graph`; wall state/restricted list →
`mnpi-wall-enforcement`; sector news → `credit-surveillance-early-warning`'s
GDELT check; per-perspective weights → this task's own weight-vector-versions
check), 1 deferred. **The deferred row is a genuine, evidenced absence, not
a fetch gap**: "IPO and merger registration pipeline" — S-4 is loaded (6
`registration_s4` documents, the merger-registration half); S-1 has zero
filings across the 53 anchors since 2023, because the cast are established
issuers who do not file IPO registrations.

**`validators/partition.py`**: 7 new checks (31 → **38/38**) — the 6 new
Wave 16 Postgres tables present-and-populated; `debt_instrument` carrying
both `syn-i-*` and `w16-i-*` writers' rows; the `OpportunitySignal`
predicate allowlist plus a presence check (1,270 nodes); `no Wave 16
collection` and `merger corpus present` in MongoDB; `banker-linked prospect
notes present` (50 rows) in SQLite.

### 2026-08-24 — Wave 16 Task 16: docs, validator hardening, and the mirror bundle — wave close

**Two validator hardening fixes**, both defensive rather than functional —
neither changes what the estate's data proves, both change what a future
regression would look like.

1. `validators/spec_coverage.py`'s `read_catalog()` heading match compiles
   with `re.IGNORECASE` (see `docs/known-issues.md` §22). The vault has
   edited `counterparty-reference-snapshot.md`'s §C heading to lowercase
   "catalog"; every other spec, including all seventeen others this estate
   is built against, still reads "Catalog". A case-sensitive match made the
   FOUNDATIONAL product's catalog unreadable and crashed the unfiltered
   validator run before it reached any alphabetically-later product.
   `validators/test_spec_coverage.py::test_catalog_heading_case_is_tolerated`
   constructs both spellings and requires both to parse.
2. `validators/conditions.py`'s `ib_restricted_in_coverage()` no longer
   wraps its whole body in a bare `except Exception: return None`. Only the
   genuine "wave not yet run" precondition — the SQLite departmental file
   absent, or `restricted_list` / `coverage_assignment` genuinely missing
   (`sqlite3.OperationalError` naming "no such table" / `psycopg.errors.
   UndefinedTable`) — still returns `None` and renders SKIP. Any other
   failure (a typo'd column, a renamed table, a bad query) now raises
   `CheckFailure` and renders FAIL, matching the contract every other
   store-crossing condition in the file already follows.

**Full validator suite after both fixes**, counted, not remembered:

| Check | Result |
| --- | --- |
| `uv run --with pytest pytest validators/ -q` | **245 passed** (243 before this task's 2 new parametrized-test cases; the 1 pre-existing failure now passes) |
| `validators/conditions.py` | **161 passed · 0 failed · 0 skipped** |
| `validators/partition.py` | **38/38** |
| Fluree `fibo-v2` | **75,582 triples at t=1665** |
| Postgres `debt_instrument` | **96 rows over 48 distinct obligors** |
| MongoDB `document` / `passage` | **193 / 37,305** |
| SQLite `prospect_note` | **50 rows, 6 `rank_changing`** |
| Branch commits (`main..wave16-ib-opportunity`) | **38** |

**No new FIBO bindings from this task.** The seven terms Wave 16 added —
`OpportunitySignal`, `magnitude`, `coveredBy`, `comparableTo`,
`comparabilityBasis`, `isCurrent`, `primaryBankerId` — were all bound in
Task 12 (see "Wave 16 · banker opportunity ranking" above) and are
unchanged here; this task only verified they are present and sent the
corrected mirror through the agent exchange.

**Correction, final fix wave (2026-08-25): the count above was wrong at the
time it was written.** `ex:magnitude` is asserted 1,270 times by this same
loader and was permitted in `validators/partition.py`'s allowlist from the
start — it was simply never added to the binding table row above or to the
exchange bundle. The bundle named
`2026-08-25T00-50-27Z-wave16-ib-opportunity-bindings` carried only six
terms and is superseded by a new bundle carrying all seven; see "Vault
mirror" below.

**Vault mirror.** Two bundles sent to
`~/.agent-exchange/ccf-dataprep/outbox/`. The first carried six Wave 16
terms (missing `ex:magnitude`) and the vault heading drift note. The
second, sent in the final fix wave, supersedes it, adds the missing
`ex:magnitude` row, and says plainly that the first bundle undercounted.

**18 of 21 Context Products now registered.** Remaining: `aml-typology-match`
(synthetic entities only, hard legal rule), `syndicated-lending-co-lender`
(second Fluree/Postgres fabric, provisioned since 2026-08-23), and
`large-exposure-rwa-concentration` (composes six prerequisites, goes last).

### 2026-08-25 — Final fix wave: whole-branch review, four blockers closed

A whole-branch review of `wave16-ib-opportunity` returned CHANGES REQUIRED
before merge. Closed, in order:

1. **`ex:magnitude` unbound** — see the correction and second exchange
   bundle above.
2. **Engineered data presented as emergent** — `docs/wave16-design.md` §6
   said the divergence pair was "verified, not engineered." True of
   Braemar; false of Thermon, whose DCM ranking rests on `w16-i-01a242`, a
   bond this wave minted with a maturity inside the 24-month horizon by
   construction. Corrected in §6 and in this file's Task 8b entry, which
   also said "only `idiosyncratic_bp` is invented" — true of the three
   spread-observation legs, false of the 36 instruments themselves.
3. **A cross-product metric moved unmeasured** — Wave 16's 17,964 new
   `spread_observation` rows shifted `rating-and-spread-migration`'s
   dominance ratio 0.1854 → ~0.22 with no writer filter in the query that
   computes it. Recorded in `docs/known-issues.md` #24, not silently
   re-scoped (that is a call for whoever owns that condition, not this
   wave).
4. **Coverage portfolios too narrow to reach §F** — real portfolios were
   1-9 LEIs (150 rows / 37 bankers), making "outside the top-20"
   unreachable inside any real banker's candidate set, and leaving
   Braemar covered by zero M&A Advisory bankers. Widened, on the
   project owner's approval, to ~25 prospects per banker with heavy
   overlap (`generators/widen_coverage_wave16.py`,
   `loaders/load_coverage_widen_wave16.py`): 850 new `coverage_assignment`
   rows, existing 150 and every `is_primary` flag untouched, labelled
   `synthetic — engineered` (this overlap is deliberately manufactured,
   not organic). Re-running `loaders/load_fluree_wave16.py` after the
   widening surfaced a real, independent bug in `fetch_prospects()` — a
   `JOIN` against `coverage_assignment` fanned out a `SUM` over
   `debt_instrument`, over- and under-stating `comparabilityBasis` size
   bands once coverage stopped being 1-3 rows per anchor. Fixed with an
   `EXISTS` in place of the `JOIN`.

All four §F conditions in `validators/ib_rank.py` still PASS after the
widening: divergence holds (Braemar M&A #3 / DCM #22, Thermon M&A #38 /
DCM #3, of 52); containment (4 restricted LEIs exercised, need >= 2, 0
violations); note materiality (40 of 50 notes move their own entity's
rank, need >= 5 — down from 45 once condition 3 was filtered to match
condition 2's restricted-entity exclusion, item 5 below); weight replay
(39 of 52 positions move).

Also closed from the same review: `DESK_TO_PERSPECTIVE` deduplicated into
`ccf/ib_rank.py`; a live parity assertion between `wave16_signals.json`
and Fluree's `OpportunitySignal` count; `load_postgres_wave16.py`'s
`projection_plan` cleanup made conditional on the stray columns actually
being present rather than running forever, its `plan_ids` pinned to the
`PP-IB-` prefix, and its restore proof moved before the commit it gates;
`repair_prospect_note_keys_wave16.py`'s round-robin keyed to each note's
own id instead of its position in a global query result; the retracted
`generate_boston_omaha_debt.py` body removed from `docs/wave16-plan.md`
below its already-rewritten banner; and a format assertion added for the
`"{signal_type} -- {lei} -- {observed_at}"` label three modules
(`load_fluree_wave16.py`, `conditions.py`, `spec_coverage.py`) all assume
but nothing previously checked.

Full details were in `.superpowers/sdd/wave16-plan/final-fix-report.md`,
an SDD scratch artifact that is deleted at wave close and must not be
relied on: this section is the durable summary.

### 2026-08-25 — Wave 17 Task 3: FinCEN advisory text and passages into MongoDB

`generators/extract_advisory_passages.py` extracts the four advisory PDFs
selected in Task 1 / fetched in Task 2 with `pypdf` — **this project's
first PDF dependency**, added to `pyproject.toml` because the cached
advisory HTML pages yield only ~2,057 characters of navigation boilerplate
and the advisory body lives solely in the PDF. Text is split into
paragraph-bounded passages (blank-line separated, oversized ones windowed
at 1,500 chars); offsets are computed from the exact string that is then
stored as `document.text`, never from a re-extraction, so a passage span
cannot silently select the wrong words.

`loaders/load_mongo_wave17.py` upserts into the existing `document` /
`passage` collections: **4 documents, 72 passages**
(`FIN-2009-A003` structuring 12, `FIN-2010-A001` trade-based 33,
`FIN-2014-A005` funnel-account 11, `FIN-2017-A003` shell-company 16),
`doc_type: "fincen_advisory"` set on these 4 rows and only these 4 — the
178-row pre-existing `doc_type` gap (`docs/known-issues.md` #21) is
unchanged. `doc_id` / `passage_id` are content-derived (advisory number;
`sha256(passage text)[:12]`), never positional, so a re-run converges by
value: passage `fincen-advisory-fin-2009-a003#142dad3c2762` held identical
text across two consecutive runs, and `document`/`passage` counts (197 /
37,377 total in the shared `fibo_v2` db) were unchanged by the second run.

`validators/partition.py`'s existing `passages anchor to a document` check
covers the new rows for free (0 orphaned across 37,377 passages / 197
documents + 32 KYC files). `validators/test_aml_typology.py` gained the
brief's round-trip test (`text[p["start"]:p["end"]] == p["text"]` for every
advisory passage, `>= 40` required, 72 delivered) plus a `doc_type`/gap
check. Full suite: **251 passed**.

**No new FIBO bindings.** This task writes only MongoDB `document` /
`passage` rows (public advisory text and derived passage spans, per
`aml-typology-match` §C) — no Fluree types or predicates, so the binding
table and its vault mirror are untouched.

**Correction after review (2026-08-25): three findings, all fixed in place.**
Independent live verification confirmed extraction fidelity, idempotency,
provenance labelling, ID derivation and store discipline, but found:

1. **CRITICAL — `passage_id` was excluded from every passage's `$set` body**
   (kept only as `_id`), so `db.passage.find_one({"passage_id": ...})` —
   exactly how Task 4 resolves a citation — returned `None` for all 72 rows.
2. **The round-trip test's failure message referenced `p["passage_id"]`
   only inside the (unevaluated-until-failure) f-string**, so a genuine span
   mismatch would raise `KeyError` instead of reporting it — a failure path
   that had never actually run.
3. **Duplicate field names.** The brief's verbatim test used `doc_id` /
   `start` / `end`; `validators/partition.py`'s orphan check queries
   `document_id`. The first cut wrote both name sets to satisfy both,
   which the controller ruled a defect in the plan, not the implementation:
   **the estate convention wins** — `document_id`, `passage_id`,
   `start_offset`, `end_offset` only, since two fields holding the same
   offset are two things that can drift apart later.

All three are fixed: every artifact field (including `document_id` /
`passage_id`) is now written via `$set`; the loader's every upsert also
`$unset`s the retired `doc_id`/`start`/`end` keys, so the 72 rows already
written under the first cut had those keys actually removed, not merely
left un-set going forward (verified: 0 passages carry a retired key after
the fix); the round-trip test binds `pid = p["passage_id"]` before the
assertion. Two new tests added:
`test_passage_resolves_by_passage_id_field` and
`test_no_advisory_passage_carries_a_retired_alias_field`. Full suite after
the fix: **253 passed**; `validators/partition.py` **38/38**.

### 2026-08-25 — Wave 17 Task 4: typology structural patterns, 10 terms bound (corrected)

`generators/derive_typology_patterns.py` derives the four typology
structural definitions `sources/screening/wave17_typologies.json` from
Task 3's Mongo passages. Each entry cites, by `passage_id`, the passage in
its own advisory that states the laundering **mechanism** — not a filing
threshold, not a footnote — found by a keyword-scored search over that
advisory's passages (never a hardcoded id): `structuring` → FIN-2009-A003
`#f86ed792d5f4` (the $10,000-threshold example bullets), `funnel_account` →
FIN-2014-A005 `#c3631708d875` (the "Funnel Account:" definition),
`trade_based` → FIN-2010-A001 `#f4682dbfa492` (over/under- and
double-invoicing), `shell_company_ownership` → FIN-2017-A003
`#32607b95aa14` (shell companies formed without disclosing their
beneficial owners). Scores separated cleanly in every case (2/1/0, 4/3/2,
3/0/0, 4/2/1) — none was a coin flip.

**The `shell_company_ownership` controller ruling, honored.**
`shell_company_ownership` replaced `rapid_pass_through` in Task 1 (FinCEN
publishes no advisory on the latter). FIN-2017-A003's own case is
residential real estate, which this estate does not model, so the cited
passage is scored with an exclusion list that heavily penalizes any
passage naming a Geographic Targeting Order, Form 8300, or the $10,000
filing trigger — the reporting regime, not the mechanism. The winning
passage states only the mechanism: a shell company "formed without
disclosing the individuals that ultimately own or control them." Its
`params` carry `min_ownership_hops`, `channel: "asset_purchase"`,
`min_amount_usd`, `financing_leg` — no property entities, deeds, or GTO
thresholds — plus the required `abstracted_from_advisory` field stating
plainly that the advisory's case is real estate and this estate exhibits
the mechanism with the asset class abstracted.
`validators/test_aml_typology.py::test_shell_company_ownership_honors_the_controller_ruling`
checks this live: the cited passage's text contains neither "geographic
targeting order", "gto", nor "form 8300", and the abstraction disclosure
is present verbatim.

**`params_source` labels every structural number.** Per typology, a
sibling dict maps each `params` key to `"advisory"` (the advisory states
this number — the $10,000 BSA/CTR threshold, stated in both
`structuring`'s and `funnel_account`'s advisories) or `"chosen"` (no such
number is stated in the text; this estate picked one). Nothing here
presents a chosen number as though the advisory said it.

**Tests**: the brief's two (`test_every_typology_cites_a_resolvable_passage`
— extended to actually check the cited passage's text for one of the
keywords that selected it, since the brief's own docstring promised that
check and its sample code did not perform it — and
`test_typology_params_are_not_all_identical`), plus
`test_params_source_labels_every_param_advisory_or_chosen` and the
controller-ruling test above. **Step 0 fix**: 
`test_no_advisory_passage_carries_a_retired_alias_field` now asserts the
72-row population floor (`>= 40`) before trusting a zero-stray count — the
same "gate blind to its own population" class this estate has recorded
before (a wrong database or a no-op load would have reported "0 strays"
and passed, having verified nothing). `validators/test_aml_typology.py`:
**11 passed** (7 pre-existing + 4 new). Whole-repo suite: **257 passed**.

**Idempotency, proven by value.** Re-running the generator without
touching Mongo produced a byte-identical `wave17_typologies.json`
(`sha256 cce6d14b6257…`); `shell_company_ownership`'s `passage_id`
(`fincen-advisory-fin-2017-a003#32607b95aa14`) survived the re-run
unchanged.

**Review fix round, three items.**

1. **`ex:Alert` pulled from the binding table.** The first cut bound all
   eleven controller-listed terms, `Alert` included, and left its missing
   writer as an open question. Corrected: §C assigns alerts to Postgres,
   Task 12 keeps them there with no Fluree representation, and this wave's
   own Task 3 precedent already covers this exact shape ("no Fluree types
   or predicates, so the binding table ... [is] untouched"). See
   `docs/known-issues.md` #25 for the full record and the superseded
   exchange bundle note.
2. **`params_locator` added.** Every `params_source` key labelled
   `"advisory"` now carries the `passage_id` where that value is actually
   stated — which can differ from the typology's main cited passage.
   `structuring`'s $10,000 is in its own cited passage; `funnel_account`'s
   $10,000 is not in `#c3631708d875` (the mechanism definition, which only
   says "below the cash reporting threshold") but three passages later, in
   `#cca080fb109e`'s "Typical steps" walkthrough — now the recorded
   locator. `test_advisory_labelled_params_are_grounded_in_a_real_passage`
   resolves every locator against Mongo and asserts the value's text form
   is actually present.
3. **`structuring` gets its own `abstracted_from_advisory` note.** Its
   advisory is casino-specific ("Structuring by Casino Patrons and
   Personnel"); the mechanism already generalises and no casino term leaks
   into `params`, but the narrowing was unstated while
   `shell_company_ownership`'s identical narrowing was.
   `test_structuring_carries_its_own_abstraction_note` checks the note
   mentions the casino setting and that no casino-domain term leaks into
   any other `params` value.

Three new tests plus `test_ex_alert_is_not_bound_here` (guards this
artifact specifically, not the doc prose) bring
`validators/test_aml_typology.py` to **14 passed**; whole-repo suite:
**260 passed**.

#### Wave 17 · AML typology-match vocabulary — 10 terms bound, live since Task 13/14 (registered Task 18)

**Verified against `sources/fibo/dev.fibo-quickstart.ttl`**
(8,966,028 bytes, on disk since Wave 16's fetch — never `prod`, which
omits 40 Provisional modules including nine terms this repo already
binds). Positive control (`grep -cP '[:#]LegalEntity\b'`) returned
**1887**. `grep -coP '[:#]<Term>\b'` returned **0** for all ten terms
below, checked individually via `ccf.fibo.fibo_absent`, which raises
rather than returning a guess if the positive control or the file itself
is unusable.

None of the ten has a Fluree/Postgres writer **yet** — this task binds
ahead of use, per CLAUDE.md's "bind upstream, verify, generate, then flag
the mirror." Per `docs/wave17-plan.md`, Task 13's `loaders/load_fluree_wave17.py`
is the first writer for `AMLParty`, `transactedWith`, `matchesTypology`,
`Typology`, `TypologyPattern`, `anchoredToPassage`; Task 14 (same loader,
extended) is the first writer for `FilingPosture`, `postureEffectiveFrom`,
`DispositionRule`, `permitsDisposition`.

**`ex:Alert` was in the controller's original term list and is deliberately
NOT bound here — a correction, not an oversight.** §C assigns "Alert
records and prior-alert history" to Postgres, and Task 12 keeps it there
(`aml_alert` / `aml_alert_link`) with no Fluree representation. Task 3's
own precedent already covers this shape exactly: "No new FIBO bindings.
This task writes only MongoDB rows... no Fluree types or predicates, so
the binding table and its vault mirror are untouched." A Postgres-owned
element gets no RDF class. See `docs/known-issues.md` #25 for the
corrected record — the first cut of this section bound `Alert` anyway and
was fixed on review.

| Local name | Kind | Full IRI | Asserted by | Why not FIBO |
| --- | --- | --- | --- | --- |
| `Typology` | class | `http://example.org/fibo/Typology` | Task 13 — 4 nodes (one per typology_id, dual-typed with `TypologyPattern`, see below) | no FIBO class for a named laundering pattern category (structuring, TBML, …); FIBO models legal/financial structures, not typologies of illicit behavior |
| `TypologyPattern` | class | `http://example.org/fibo/TypologyPattern` | Task 13 — 4 nodes | the structural, parameterized instance of a `Typology` this task derives — distinct from the category itself so the same category can carry more than one structural variant. Today `wave17_typologies.json` carries exactly one derived pattern per typology_id, so one node per typology_id is typed BOTH `Typology` and `TypologyPattern` rather than minting a second node with no bound predicate to link it back |
| `matchesTypology` | property | `http://example.org/fibo/matchesTypology` | Task 13 — 24 edges (one per case, `AMLParty` → the case's typology's dual-typed node) | edge asserting a party's transaction pattern matches a `TypologyPattern`; FIBO has no vocabulary for a suspected-typology match, which is inherently a bank's own analytical claim |
| `transactedWith` | property | `http://example.org/fibo/transactedWith` | Task 13 — 7,736 edges (3,868 unordered pairs, asserted both directions, from all 4,358 transaction rows) | the counterparty-transaction edge between two `AMLParty` nodes this product's network is built from; FIBO's transaction vocabulary models financial instruments and contracts, not a bare has-transacted-with graph edge for pattern-matching |
| `AMLParty` | class | `http://example.org/fibo/AMLParty` | Task 13 — 201 nodes | synthetic-only party type for this product (CLAUDE.md rule 2: AML uses synthetic entities only) — kept distinct from every other party class so a query for real obligors can never pull in an AML-typology entity by accident |
| `FilingPosture` | class | `http://example.org/fibo/FilingPosture` | Task 14 — 2 nodes (`POST-2025-01`, `POST-2026-01`) | a versioned internal filing-disposition policy, effective from a date; no FIBO class for an internal control posture that changes what the bank does with a match over time |
| `DispositionRule` | class | `http://example.org/fibo/DispositionRule` | Task 14 — 16 nodes (4 typologies × 2 dispositions × 2 postures) | one posture's ruling for one typology (close-no-action / escalate-l2 / file-sar / monitor); FIBO has no vocabulary for this kind of internal decision rule |
| `postureEffectiveFrom` | property | `http://example.org/fibo/postureEffectiveFrom` | Task 14 — 2 assertions, plain `YYYY-MM-DD` strings | valid-time predicate on a `FilingPosture`; distinct from the estate's existing bitemporal `validFrom`/`validTo` pair because a posture's effective date is a single anchor, not an interval with a start and a (possibly open) end |
| `permitsDisposition` | property | `http://example.org/fibo/permitsDisposition` | Task 14 — 16 assertions, plain `"true"`/`"false"` string literals | edge from a `DispositionRule` to whether it is permitted under its posture — the predicate the as-of / Policy Blind demonstration evaluates twice, once per posture, to show the same disposition flip from permitted to forbidden |
| `anchoredToPassage` | property | `http://example.org/fibo/anchoredToPassage` | Task 13 — 4 assertions (one per dual-typed typology node, literal `passage_id`, e.g. `fincen-advisory-fin-2009-a003#f86ed792d5f4`) | edge from a `Typology`/`TypologyPattern` node to the MongoDB passage that states it — the citation this whole product's typology claims rest on; FIBO has no cross-store passage-anchoring predicate |

**Vault mirror.** No IRI changed and no term was added by Task 13 or Task
14 — all ten rows above were already sent to the exchange when Task 4
first bound them. Only assertion status changed (0 → live, Task 13 for the
first six, Task 14 for the remaining four), which is an estate-internal
fact the mirror does not need to carry. Nothing further to send.

**Task 18 registration — counts RE-MEASURED live, not read off this table.**
This section's own counts (written by Task 13/14) still matched a fresh
SPARQL query against `fibo-v2` at close-out time: `Typology` 4,
`TypologyPattern` 4, `matchesTypology` 24, `transactedWith` 7,736,
`AMLParty` 201, `FilingPosture` 2, `DispositionRule` 16,
`postureEffectiveFrom` 2, `permitsDisposition` 16, `anchoredToPassage` 4 —
identical to every figure above. The one number that DID move since Task
15/16 wrote it down is `sar_classification`'s row count (SQLite, not a
binding-table row): 24 at Task 15, **12 now** (fix rounds 2-3 re-selected
the filing split), which is why `validators/conditions.py`'s new
`aml-typology-match` block reads it live on every run rather than
restating either figure. All ten terms are now registered in
`validators/partition.py`'s `PERMITTED_EX_TYPES` (closing the
"SHADOWING" gap Task 13's own review flagged and deliberately deferred
here) and mapped row-by-row in `validators/spec_coverage.py` (16 of 16 §C
rows accounted for). See `docs/known-issues.md` for the `ex:Alert`
retraction this registration also closes out.

### 2026-08-25 — Wave 17 Task 16: projection plans for three perspectives (recorded here — the SDD workspace this task's own report lived in is deleted at wave close)

`loaders/load_postgres_wave17.py` gains `load_projection_plans`, reading
the hand-authored `sources/screening/wave17_projection.json` into
`aml_projection_plan` (`perspective`, `elements` jsonb, `provenance`).
Three rows, one per `l1` / `l2` / `examiner`:

- **`l1`** (action-ready triage): `alert_core_facts`,
  `disposition_candidates`, `sanctions_screening_result`,
  `typology_pattern_summary`.
- **`l2`** (investigative history): `alert_core_facts`,
  `counterparty_network`, `ownership_chain`, `prior_alert_lineage`,
  `sar_filing_history`, `typology_pattern_summary`.
- **`examiner`** (defensibility artifacts): all of the above plus
  `policy_version_attribution` and `reasoning_trail` — ten elements total.

**Why `l1` is SAR-safe by construction.** `case_id` was considered and
rejected as an `l1` element even though it names no SAR table directly:
verified live that all 24 SAR-bearing cases have exactly one `case_id`
each and every alert carrying a non-null `case_id` traces to one of those
24, so presence of the field alone would leak filing likelihood. Also
rejected: a per-alert `disposition_outcome`/`filing_status` field (as
opposed to `disposition_candidates`, the generic permitted-menu the
posture computes, which carries no per-alert history) and an
`is_genuine`/`genuine_case_flag` boolean restating the same thing.
`typology_pattern_summary` and `sanctions_screening_result` were kept —
neither resolves 1:1 to SAR-filing status. `validators/aml_typology.py`'s
`sar_confidentiality_holds` (Task 17) is the live recomputed proof; this
entry is the design rationale behind it.

**Idempotency by value.** Two loader runs compared `l1`'s exact `elements`
array (not a row count) and its `provenance` — byte-identical both times;
row count stays 3.

**Tests.** `validators/test_aml_typology.py` gains 3 (the brief's verbatim
element-set test plus two of the author's own, including the idempotency
proof): 114 passed at the time.

### 2026-08-25 — Wave 17 Task 13: nodes, network, ownership, typologies into Fluree

`loaders/load_fluree_wave17.py` is the first writer for six terms Task 4
bound ahead of use: `AMLParty` (class), `Typology` (class), `TypologyPattern`
(class), `matchesTypology`, `transactedWith`, `anchoredToPassage`. Reads
five frozen `sources/screening/wave17_*.json` artifacts and projects them —
nothing here generates.

**Node/edge counts.** 201 `AMLParty` nodes (identity only: `ex:lei` = the
party's `syn_lei`, plus an id-echo `rdfs:label` — no legal name,
jurisdiction, incorporation date or `party_kind`, all Postgres-owned). 4
dual-typed `Typology`/`TypologyPattern` nodes, each carrying
`anchoredToPassage` (a plain-string `passage_id`, matching the
`documentId`/`variantId` cross-store-citation pattern) and `provenance`
(`public`, from the advisory). 100 `hasBeneficialOwner` /
`isBeneficialOwnerOf` edge pairs from Task 9's binding, resolved against
Wave 13b's EXISTING `PSC-*` `BeneficialOwner` nodes (46 available, all 100
bindings resolved, 0 dangling) — never reconstructed. 7,736
`transactedWith` edges (3,868 unordered pairs, both directions) from ALL
4,358 transaction rows, 0 self-loops, 0 dangling. 24 `matchesTypology`
edges, one per case, `AMLParty` → its typology's dual-typed node.

**`Typology` vs `TypologyPattern` — one node, two roles.** The binding
table separates them "so the same category can carry more than one
structural variant," but `wave17_typologies.json` carries exactly one
derived, parameterized structural definition per typology_id today, and no
predicate linking a `Typology` to its `TypologyPattern` is bound. Rather
than invent one (out of scope — this task binds nothing new), each of the
4 typology_id nodes is typed with BOTH classes. `matchesTypology`'s object
and `anchoredToPassage`'s subject are therefore the same node, satisfying
the strengthened floor-1 test (below) without a traversal hop.

**The brief's own floor-1 test was too weak — strengthened.**
`test_every_matches_typology_edge_cites_an_advisory_passage`'s verbatim
body checks two independent counts (`matches > 0`, `anchored > 0`), which
100 unanchored `matchesTypology` edges plus one anchored typology elsewhere
would still pass — the name promises a universal, the body checks two
existentials, this estate's most-recorded defect class. Added: a SPARQL
`FILTER NOT EXISTS` set difference asserting every OBJECT of
`matchesTypology` resolves to a node carrying `anchoredToPassage`, empty or
fail, naming the offending nodes. A second test,
`test_the_anchor_universal_can_actually_fail`, proves the check is not
vacuous: it inserts a throwaway `matchesTypology` edge at a scratch node
with no anchor, confirms the strengthened check names it, then retracts
the scratch triple in a `finally` block (confirmed gone afterward).

**Floor 2 (Task 11's depth-3 network) reverified IN Fluree, not inferred
from the artifact.** Fetched the raw `ex:transactedWith` edges from the
live ledger, built an undirected adjacency in Python, and walked from
CASE-008's subject `AMLP-0049`: depth-2 reachable set **200** of 201 nodes
(excludes `AMLP-0166`), depth-3 reachable set **201** of 201 (includes
it) — identical to the artifact-level computation. `AMLP-0166` confirmed
absent at depth 2 and present at depth 3, from the store, not the JSON.

**Idempotency by value.** Ledger `t` 1859 → 1881 across a plain re-run
(Fluree bumps `t` on every transact call, including a no-op one — an
append-only commit log, not a content-change counter). Named party
`AMLP-0049`'s `transactedWith` edge count: **68 before, 68 after**. Total
ledger triples: **85,027 before, 85,027 after**. The loader also fails
loudly (`return 1`, refuses to write) rather than warning if any
transaction, case, or ownership row cannot resolve cleanly — none did in
this run.

**A Fluree engine quirk, recorded because it broke a test in exactly the
way that matters.** This ledger's SPARQL implementation does not enforce
same-variable-same-value within a single triple pattern: `?s <p> ?s`
matched all 7,736 edges, not zero, when a reflexive-edge guard test first
used it — the correct query needs an explicit `FILTER(?s = ?o)`. No
reflexive edge actually exists (verified independently); this was a test
authoring mistake caught by writing the test before trusting it, not a
loader defect.

**Registration deferred to Task 18 by design.** `validators/partition.py`
now reports `SHADOWING: ['AMLParty', 'Typology', 'TypologyPattern']`
(37/38 checks pass) because `PERMITTED_EX_TYPES` has not been extended yet
— `docs/wave17-plan.md`'s Task 18 owns that edit. All three were verified
absent from `dev.fibo-quickstart.ttl` at binding time (Task 4); this is a
registration gap, not a real FIBO collision.

**Tests.** `validators/test_aml_typology.py` gains 13 tests (node/edge
coverage, the strengthened floor-1 universal and its vacuity proof, the
Fluree-side depth-3 floor, the ownership-binding projection, the
Postgres-owned-attribute leak guard, the `ex:Alert`-absence guard, and the
value-based idempotency proof): **95 passed**. Whole-repo suite: **341
passed**. (Corrected 2026-08-25, Task 14 step 0: this line previously said
15 — the diff added exactly 13 test functions, 82 → 95; the 95 and 341
totals were already right.)

### 2026-08-25 — Wave 17 Task 14: the policy layer — two postures, one flip

`generators/generate_aml_policy.py` writes `sources/screening/wave17_policy.json`
(2 postures, 16 disposition rules); `loaders/load_fluree_wave17.py`
(extended, not replaced) is the first writer for the remaining four Wave 17
terms: `FilingPosture` (class), `DispositionRule` (class),
`postureEffectiveFrom`, `permitsDisposition`.

**The two postures.** `POST-2025-01` (effective `2025-03-01`) and
`POST-2026-01` (effective `2026-01-15`) — both strictly inside the pinned
transaction window `2025-02-24..2026-08-24`, with roughly ten months of
daylight between the two dates so an `as_of` value has real room to land on
either side. `advisory_number` is `null` for BOTH: the four fetched FinCEN
advisories were issued 2009-07-01, 2010-02-18, 2014-05-28 and 2017-08-22 —
none falls inside the transaction window, so none could plausibly have
prompted a posture that only exists within it. This is checked at
generation time against `sources/fincen/selection.json`'s own recorded
`issued` dates (never invented) and re-verified independently by
`test_advisory_anchoring_is_honest_about_the_window`, which first proves
the check is not vacuous by confirming, from the advisories' own dates,
that no in-window candidate exists at all. Both postures are internal
policy tightenings, not advisory-driven — and the data says so honestly.

**The flip.** `TYP-STRUCT` (structuring) is the one typology whose ruling
changes: under `POST-2025-01`, `close-no-action` is `permitted=true` and
`escalate-l2` is `permitted=false`; under `POST-2026-01` this inverts
exactly — `close-no-action` becomes `permitted=false` and `escalate-l2`
becomes `permitted=true`. The other three typologies (`TYP-FUNNEL`,
`TYP-TBML`, `TYP-SHELL`) keep an identical ruling across both postures, by
design — so the one change that does happen reads as deliberate rather
than as noise in a wall of unrelated drift. Full rule set (16 rows,
`permitted` for POST-2025-01 → POST-2026-01):

| typology | disposition | POST-2025-01 | POST-2026-01 |
| --- | --- | --- | --- |
| TYP-STRUCT | close-no-action | **true** | **false** ← flip |
| TYP-STRUCT | escalate-l2 | **false** | **true** ← flip |
| TYP-FUNNEL | monitor | true | true |
| TYP-FUNNEL | file-sar | false | false |
| TYP-TBML | file-sar | true | true |
| TYP-TBML | monitor | false | false |
| TYP-SHELL | monitor | true | true |
| TYP-SHELL | escalate-l2 | false | false |

**No `belongsToPosture` / `forTypology` predicate — the composite key is
the link.** Neither is bound, and this task mints nothing new. `rule_id`
is instead derived from content as `RULE-{posture_id}-{typology_id}-
{disposition}` (e.g. `RULE-POST-2025-01-TYP-STRUCT-close-no-action`), so a
consumer who knows which posture and typology it means can resolve the
same Fluree node directly and read `permitsDisposition` off it — the same
pattern `AMLP-####` / `TYP-*` already use as self-resolving keys.
`advisory_number` stays JSON-only; no Fluree predicate is bound for it.

**`ex:transactedWith` unaffected.** Measured before and after this load:
**7,736** edges over **3,868** unordered pairs, both unchanged — this task
only adds two new node populations and touches no existing predicate.

**Idempotency by value.** `RULE-POST-2025-01-TYP-STRUCT-close-no-action`'s
`permitsDisposition` literal: exactly one assertion, `"true"`, before and
after a plain re-run (no `--reconcile`) — not duplicated into a second,
competing literal. `AMLP-0049`'s `transactedWith` edge count (the existing
Task 13 idempotency proof): unchanged across the same re-run.

**Determinism.** No randomness in `generate_aml_policy.py` — the posture
and rule tables are hand-authored, not sampled — and the artifact is
written with `sort_keys=True`. Verified byte-identical: `git diff --exit-code
sources/screening/wave17_policy.json` after a second run reported no
difference.

**Tests.** `validators/test_aml_typology.py` gains 7 tests (the flip
itself, the plain-string Fluree dates, the pinned-window check, the
advisory-anchoring honesty check with its own vacuity proof, the
Fluree-vs-artifact cross-checks for both `FilingPosture` and
`DispositionRule`, and the value-based idempotency proof): **102 passed**.

### 2026-08-25 — Wave 17 Task 18 complete: `aml-typology-match` registered — 19 of 21 products

The build-vs-registered gap this file's own opening lines warn about
(`facility-terms-snapshot` sat complete-but-uncounted for eleven waves)
closed for Wave 17 in the same session it was built, not eleven waves
later.

**`validators/conditions.py` — an `#19 aml-typology-match (Wave 17)`
block, 11 checks.** Four direct existence counts (typologies loaded >= 4;
filing posture versions with distinct effective dates >= 2; parties
declaring an OFAC near-match >= 1; SAR records with confidentiality
classification >= 3 — all four read live, none restated from an earlier
task's report) plus seven ordering/absence delegates to
`validators/aml_typology.py`'s own seven floor functions (typology
anchoring, depth-3 network, posture flip, SAR confidentiality, OFAC band,
three renderings differ, no-path-to-real-entity), exactly as the Wave 16
block delegates to `validators/ib_rank.py`. The `~200`/`~5,000`/`~150`
envelope figures are shape, not targets (Dave's ruling, restated in the
new block's own comment), and are not registered. The name-guard safety
property (Tasks 5/6) is likewise not registered here — it is not a §F
`>= N` and is already proven, live, against the FINAL artifact, by
`validators/test_aml_typology.py`. Full register: **172 passed · 0 failed
· 0 skipped** (estate-wide, all products).

**`validators/partition.py` — bidirectional, both directions.**
`PERMITTED_EX_TYPES` gains the five classes Task 13/14's own review
flagged and deferred here (`AMLParty`, `Typology`, `TypologyPattern`,
`FilingPosture`, `DispositionRule` — all five re-verified absent from
`dev.fibo-quickstart.ttl` at Task 4's binding time, so this is
registration paid off late, not a fresh FIBO check). `POSTGRES_OWNED_ATTRS`
gains `incorporated`, `incorporationDate`, `partyKind` — the generic
Postgres-owned-attribute scan could not see a future leak of any of the
three onto a Fluree node until now; previously covered only by
`validators/test_aml_typology.py`'s one task-specific regression. New
`WAVE17_PG_TABLES` (five tables). Presence checks added in Fluree (seven:
the five classes plus `transactedWith`/`matchesTypology`/
`anchoredToPassage` edge presence), Postgres (Wave 17 tables present AND
populated), MongoDB (`fincen_advisory` + `sar_narrative` doc_type corpus
present) and SQLite (`sar_classification` present and populated). Absence
checks added: no Wave 17 Postgres-owned table name in Mongo or SQLite, and
— Task 15's `test_sar_classification_lives_only_in_sqlite` regression,
ported into the estate-wide gate rather than left as a lone task-specific
test — no `%sar%`-named table or column anywhere in Postgres. Full run:
**50/50 checks passed**.

**`validators/spec_coverage.py` — 16 of 16 §C rows mapped, `aml-typology-match`
added to both `PRODUCTS` and `MANIFEST`** (it was in neither — the exact
"unregistered is invisible" gap this task exists to close). Confirmed Q019
form by section NAME before mapping a single row: the vault's §F heading
reads "Manufacture envelope", not the v0.3 "Source binding & readiness"
that would parse cleanly under a letter-only match while returning the
wrong section. Fifteen rows PROBE a live store directly; one
(`shell_company_ownership`'s advisory abstraction is a design decision
recorded in the typology record itself, not a §C row, so it does not
appear in this count) — no row needed WAIVED or DEFERRED. The one row
drafted as COVERED in a first pass (`Beneficial ownership`) was converted
to a direct PROBE on review: no `conditions.py` check actually asserts
`aml_party.beneficial_owner_key` today, and this validator's own COVERED
state means "already asserted by a named conditions.py check," not merely
"loaded elsewhere" — citing it without one would have been exactly the
kind of claim this file exists to keep honest. `uv run
validators/spec_coverage.py --product aml-typology-match`: **16 of 16
catalog rows accounted for (16 probed clean)**. (A pre-existing,
unrelated failure in `counterparty-reference-snapshot`'s own manifest —
its vault §C wording has moved since that mapping was written — blocks a
full-repo `spec_coverage.py` run; out of this task's scope, left for
whichever task owns that product next.)

**`validators/aml_typology.py`: 7 passed · 0 failed** (unchanged from
Task 17 — this task registers, it does not re-derive). **`uv run --with
pytest pytest validators/test_aml_typology.py -q`: 139 passed.**

**The `ex:Alert` retraction, closed out.** The uncollected exchange bundle
`2026-08-25T06-55-08Z-wave17-aml-typology-bindings` in
`~/.agent-exchange/ccf-dataprep/outbox/` lists eleven terms including
`ex:Alert`. `ex:Alert` was subsequently retracted — §C assigns alerts to
Postgres, and Task 13 confirmed no such Fluree class was ever created.
Bundles are immutable, so that bundle is superseded rather than edited: a
new bundle names it explicitly and states the ten terms above stand,
`ex:Alert` withdrawn. See `docs/known-issues.md` #25.

**Wave 17 complete.** `aml-typology-match` is registered: every §C row
accounted for, every §F floor with a condition proven by a live query, the
partition gate checking both directions, and the binding table showing
live counts. 19 of 21 catalog products now registered
(`spec_coverage.py`'s `MANIFEST` covers 7 of the 19 `PRODUCTS`; the
remaining unmapped products are pre-existing and out of this task's
scope). Remaining: `syndicated-lending-co-lender`, then
`large-exposure-rwa-concentration` last (composes six prerequisites), per
`docs/wave17-plan.md`'s own build order.

### 2026-08-25 — Wave 17 whole-branch review: three notes for a reader of this data

The final review before merge produced one Important finding and eight
Minor. Three of the Minors are things a learner reading this repo would
otherwise be misled by. They are recorded here, together, because each is a
statement about how to READ the Wave 17 data rather than a defect in it.

#### 1 · `synthetic — engineered` is over-applied on `aml_transaction`, and that is §C's assignment

All **4,358** rows of `aml_transaction` carry `provenance = "synthetic —
engineered"`. That follows the vault's §C row for "All transactions"
faithfully, so it is not a defect and was not changed. But it flattens
exactly the distinction CLAUDE.md's rule 1 exists to preserve, and a reader
should know it.

Only **263** of those rows were injected to create a condition public data
would not supply — Task 11's work: 99 transactions cited by the 24
engineered typology cases, plus 164 ordinary dilution rows added so the
`cash_deposit_geographic_dispersion` and `over_under_invoicing` channels are
not a single-string-match tell. The other **4,095** are Task 10's ordinary
background traffic: heavy-tailed amounts, weekday-skewed dates, ten
channels, no shape at all. They are invented, certainly — but they create no
condition, and under a stricter reading of the three-class rule they are
`synthetic — internal`, not `engineered`.

**Read the label as the catalog's assignment for the table, not as a claim
about the row.** The 263 injected rows are the genuinely engineered ones,
and they are identifiable: `wave17_cases.json` names the 99 by `txn_id`, and
the 164 dilution rows are the non-case rows on the two typology channels.

#### 2 · 0.9048 is not "moderate confidence" — it is the highest score the guard tolerates

§F asks for at least one party that fuzzy-matches a real OFAC entry "at
moderate confidence". The realised figure is
`ccf.aml.similarity("Granite Lakes Business Corp", "GREAT LAKES BUSINESS
COMPANY") = 0.9047619047619048`, against the real SDN entry `SDN-10118`
("GREAT LAKES BUSINESS COMPANY", program DRCONGO).

That is **above** `ccf.aml.BLOCK_THRESHOLD`, which is 0.90. The wave's own
legal guard would REJECT this party if it were drawn today; it exists only
as a declared, tested exception, and
`validators/test_aml_typology.py::test_the_guard_would_have_rejected_the_declared_match`
proves the guard really does fire on it rather than the exception hiding a
hole.

So the honest framing is **"the highest score the guard tolerates, by
construction"**, not "moderate confidence". The brief's own `0.70` floor is
unreachable for a name that must ALSO block: blocking requires
`>= BLOCK_THRESHOLD`, so the reachable band is `0.90 <= x <= 0.92`, and
`validators/aml_typology.py`'s floor 5 asserts `0.70 <= x <= 0.92` — a band
whose lower half no admissible value can occupy. The upper bound is what is
doing the work: it keeps the party a near-match rather than a duplicate.

#### 3 · A stale-claim sweep must be by MEANING, not by phrase

Wave 17 ran a sweep for prose left behind by a rejected design (fix round 3
replaced a materiality ranking with a content digest). The sweep grepped for
two strings — "materiality" and "aggregate transaction exposure" — and
reported clean.

**Three of the final review's nine findings were survivors of that sweep**,
and every one of them avoided both phrases:

- `case_exposure_usd()`'s own docstring still said "Used only to RANK cases
  for the filing decision below" — the first thing an auditor of the filing
  property lands on, describing the design that was rejected.
- `select_filed_case_ids()` claimed "no measured quantity was checked for
  correlation and found clean by luck", which the salt comment eighty lines
  above it contradicts in detail.
- A comment in `validators/aml_typology.py` gave a false reason for a
  correct choice, naming a commit that never touched the loader it blamed.

**The lesson, recorded because this repo has now paid for it twice** (see
also `docs/known-issues.md` #28, a count restated from memory rather than
recounted): a sweep for stale claims must re-read every place the rejected
design could be DESCRIBED — function docstrings, call sites, module
headers, comments, and any string literal that gets loaded into a store —
and ask of each "is this still true?", not "does this contain the word I
searched for". A phrase-based sweep confirms only that the phrase is gone.

### 2026-08-26 — Wave 18 Task 12: the Shared National Credit annual report into MongoDB

`syndicated-lending-co-lender` and `covenant-cross-reference` both name, in
§C, the interagency Shared National Credit (SNC) Program annual report as
the public source for supervisory context on large syndicated credits.
Located by searching federalreserve.gov and occ.gov 2026-08-26.

**Source, retrieved 2026-08-26 (retrieval timestamp `2026-08-27T01:15:26+00:00`
UTC):**
`https://www.occ.gov/publications-and-resources/publications/shared-national-credit-report/files/shared-national-credit-report-2025.pdf`
— "Shared National Credit (SNC) Program Attachment Document — 2025 SNC
Program Charts, 1st and 3rd Quarter 2025 Reviews," jointly issued by the
Board of Governors of the Federal Reserve System, the FDIC and the OCC,
dated January 12, 2026. 407,088 bytes, 12 pages. The Federal Reserve
mirrors the same content at a different URL
(`federalreserve.gov/newsevents/pressreleases/files/bcreg20260112a1.pdf`,
395,743 bytes — different embedded PDF producer metadata, but `pypdf`
extracts byte-for-byte identical text from both, verified 2026-08-26). The
OCC URL was used because it follows a stable
`shared-national-credit-report-<year>.pdf` naming pattern the Fed's
press-release-linked filename does not.

**Extraction:** `pypdf`, reused from `generators/extract_advisory_passages.py`
(Wave 17) rather than adding a second PDF-reading dependency. 20,555
characters extracted. Re-extraction stability was checked specifically for
this file (the estate's known caveat is real for at least one other PDF,
not universal): three separate `uv run python` processes re-extracting the
same downloaded PDF produced the identical sha256 every time. The loader
still does not key any identifier on `text_sha256` — `document_id` is the
stable upstream filename (`shared-national-credit-report-2025`).

**Loaded into MongoDB `fibo_v2`, `document` collection** — one row,
`doc_type="snc_annual_report"`, `provenance="public"`,
`classification="public"`, `source="Federal Reserve / OCC / FDIC — Shared
National Credit Program annual review"`, `url` = the OCC PDF address,
`retrieved_at` recorded. No passages: §C asks for this document as
supervisory context, not as a source of span-level citations, so none were
invented.

**No new FIBO terms.** This document contributes text only, no typed
entities or relationships — nothing to bind, nothing for the vault mirror.

`generators/fetch_snc_report.py` (new), `loaders/load_mongo_wave18.py`
extended (not a second Mongo loader — same `document` schema Task 11
established), `validators/test_syndicate.py` extended with
`test_snc_report_is_loaded_with_its_provenance`. `sources/snc/extract.json`
(derived text + metadata, committed) and `sources/snc/manifest.json`
(fetch provenance, committed); the raw PDF payload stays gitignored, same
as every other fetched payload in this estate.

`uv run --with pytest pytest validators/test_syndicate.py -q`: 72 passed.
`uv run python validators/partition.py`: 50/50 checks passed.

### 2026-08-26 — Wave 18 Task 14: the co-lender's estate, at two disclosure precisions

The first data this project has ever written to a fabric that is not ours.
`syndicated-lending-co-lender` §C files the peer as *"Simulated peer
fabric — a second CCF instance | required to demonstrate A2A | synthetic —
engineered | separate instance"*, and the product's whole point is assembly
across that organizational boundary. So the peer's estate has to be two
things at once: genuinely separate, and genuinely **less precise** than our
own. A peer that answered every question exactly would make the boundary
invisible.

**Where it landed.** Postgres `bofa_syndicated`, schema `colender`, role
`colender` — a different database and a different role from ours, on the
same host and port. Fluree instance `http://192.168.4.76:8093` (4.2.4
container `fluree-demo-42` since the 2026-10-15 cutover; was :8091, 4.1.6
container `fluree-demo`, retired the same night), ledger `bofa/syndicate` — a different instance
from ours, not our instance under another ledger name. The peer's MongoDB is
untouched: its product carries no passage lineage of its own, and §C gives
it none.

| Peer store | Contents after Task 14 |
|---|---|
| Postgres `bofa_syndicated`.`colender`.`peer_position` | 7 rows — 6 exact (Bank of America), 1 band-only (Citibank) |
| Fluree `bofa/syndicate` | 10 triples under `ex:peer/` — 2 typed `FinanceSyndicateMember` counterparty nodes, each carrying `ex:lei`, `rdfs:label`, `ex:disclosurePrecision`, `ex:provenance` |
| Mongo `bofa_syndicated` | still empty, deliberately |

**Three gates before any peer DDL**, in order —
`assert_distinct_fabrics()`, `assert_co_lender_schema()`, then an explicit
`SELECT current_database(), current_user` compared against **hardcoded
literals** (`'bofa_syndicated'`, `'colender'`). The literals are the point:
a gate that read its expected values from `CO_LENDER_PG` would agree with
whatever a mis-edited `.env` handed it, which is precisely the failure it
exists to catch. `_assert_peer_ledger()` does the same for Fluree, where
it matters more — the peer's Fluree is our own host on a different port,
and Fluree is append-only. All five refusals were exercised live before
the load (see the Task 14 report).

**Positions are derived from the store, never typed out.** Every
(counterparty, facility) pair and every dollar figure comes from a live
SPARQL query against our own ledger's `ex:SyndicateParticipation` nodes —
the reified commitment edges Task 8 built from the six filed schedules —
then confirmed against `ccf_v2.facility`. That guarantees the peer's rows
reference facilities we genuinely hold (a peer position on a facility we
do not hold is unassemblable, and nothing downstream would say so), and it
means AHR's two-column positional split is read once, by
`loaders/load_fluree_wave18.py`, rather than re-implemented and left to
drift.

**The mixed-precision floor is engineered, not counted.** §F requires one
counterparty to disclose an exact figure and another only a band. Two
properties make that real:

*The band does not resolve to the figure.* Citibank's band is a lookup on
a fixed published ladder — `(0, $20M, $140M, $500M)` — **not** a function
of the position it covers. Every position between $20M and $140M discloses
the identical band, so reading the generator narrows nothing. What is
engineered is the ladder's boundaries, chosen so the one banded position
lands ≥14.3% away from every naive estimator of a band (midpoint,
geometric mean, both outer quartiles, both terciles). `band_for()`
re-proves that from the ladder on every generation rather than trusting a
comment, and `validators/test_syndicate.py` re-proves it again from the
filed schedule against the loaded rows.

*The banded counterparty carries no exact figure anywhere on the peer
fabric.* Not merely on the rows flagged as banded — the DENOMINATOR, every
row for that counterparty, plus every column of every table in the peer
schema (including tables later tasks add), plus every literal on the peer
ledger. The concealed figure is a public filed number on OUR side, which
is what makes the placement checkable rather than a claim; it is absent
from the peer artifact, the peer's Postgres and the peer's graph.

**Provenance, per row.** Bank of America's six exact rows are
`synthetic — internal`: a peer bank's internal credit opinion and workout
posture are bank-internal by nature, and the share figure follows the same
convention our own `ccf_v2.own_position` rows already use (the filed
schedule total). Citibank's single banded row is `synthetic — engineered`:
it exists specifically to create §F's mixed-precision condition, which is
the definition of the third class.

**The peer's vocabulary is deliberately not ours.** Our `own_position`
rows carry notch grades (`BBB-`, `B+`, `A`) from `ccf_v2.rating_scale`. The
peer's rows carry the Shared National Credit programme's coarse regulatory
categories (`pass`, `special mention`) and its own posture vocabulary
(`standard servicing`, `enhanced monitoring`). Two banks do not share an
internal scale, and pretending they do would invent an agreement that does
not exist. The SNC report in `sources/snc/` carries programme-level
aggregates only, so the *vocabulary* is public and the *values* are
invented — recorded as such.

**Idempotency.** Postgres upserts on `position_id`, which is content-derived
(`sha256(LEI|facility_id)`, prefix `PPOS-`) and never positional; rows the
artifact no longer proposes are deleted, since this loader owns the whole
table. Fluree is append-only, so `reconcile_peer_graph()` retracts every
triple under `ex:peer/` before inserting. Proved by perturbing named values
and re-running, not by comparing counts: a perturbed
`internal_rating`/`workout_posture`/`share_usd` and a widened band were all
restored, a planted stale row was deleted, a planted ledger literal was
retracted, and a third clean run reproduced the identical content digest.

**No new FIBO terms.** Everything the peer nodes carry was already bound:
`fibo-sec-dbt-dln:FinanceSyndicateMember`, `ex:lei`, `ex:provenance`,
`rdfs:label`, and `ex:disclosurePrecision` — the last bound in the Wave 18
section above precisely for this ("`exact` or `band`, on a peer position")
and populated for the first time here. **Nothing for the vault mirror.**

`generators/generate_peer_positions.py` (new),
`loaders/load_peer_wave18.py` (new — the only file in this repository that
writes to the peer fabric), `sources/screening/wave18_peer.json` (new),
`validators/test_syndicate.py` extended by 13 tests.

`uv run --with pytest pytest validators/test_syndicate.py -q`: 89 passed.
`uv run validators/test_fabric_isolation.py`: 7/7 arms green.
`uv run validators/conditions.py`: 172 passed · 0 failed.
`uv run validators/partition.py`: 50/50 checks passed.

**Fix round 1 (same day, Rulings T14-R2 / T14-R3).** Two corrections worth
recording because both are shapes this estate keeps repeating.

*The artifact inverted back to the figure it concealed.* The generator had
published `fraction_of_band_width` and `naive_estimator_margins` into
`sources/screening/wave18_peer.json` beside the band bounds, and those three
quantities recover $70M to within 0.006% by either of two routes. The
docstring calling it "safe to publish: only invertible if you already hold
the true figure" named the reader its author imagined and missed the one
that was there — the bounds, two keys away in the same object. The fields
are gone; the computation stays inside `band_for()`, which is where the
refusal happens. The digit-spelling guard that reported green throughout
now says in its own docstring that a digit scan is all it is.

*The absence checks scanned for the wrong quantity.* The test helper summed
a counterparty's filed commitments across every agreement, while a band is
computed from one `(lei, facility_id)` pair. Those agree only while the
banded counterparty has exactly one filed row in the corpus. Given a second
one — constructed and run live — **all three** needle-based checks went
green while the real figure sat in two places on the peer fabric. The
needle is now derived per banded position. This is `count the unit the
condition names`, on this wave's central floor.

*And the non-empty guard covered columns, not rows.* A table that exists
with zero rows still makes a `SELECT ... LIMIT 1` absence scan report green.
The helper now counts rows in every table it hands out. **Task 15 should
create and populate `peer_product_declaration` in the same run**, or this
guard will refuse the empty table — deliberately.

### 2026-08-26 — Wave 18 Task 15: timeout, attestation, and TTL declarations

Three §F conditions that sound like runtime behaviour — a federated request
that times out, a remote claim nobody attested, a remote TTL shorter than
the local composite — represented as **declarations in data**. The SDK
reads and acts on them; this project only writes the row.

`colender.peer_product_declaration (declaration_id, counterparty, product_id,
declared_ttl_seconds, declared_latency_ms, attestation JSONB NULL,
provenance)`. `declaration_id` is content-derived
(`sha256(counterparty|product_id)`, prefix `PDEC-`), same discipline as
`peer_position.position_id`. `product_id` reuses §B's own addressability
pattern verbatim — `/context-products/cb/syndicate/{facility-id}/
co-lender-position` — rather than inventing a new identifier scheme.

Three rows, one contrast case per floor:

| declaration_id | counterparty | facility | ttl (s) | latency (ms) | attested | provenance |
|---|---|---|---|---|---|---|
| `PDEC-4BEB7CE1F8` | BofA (exact) | FAC-6F4065 | 21,600 (6h) | 650 | yes | `synthetic — internal` |
| `PDEC-AC14CC0870` | Citi (band) | FAC-405B7A | 10,800 (3h) | 7,200 | yes | `synthetic — engineered` |
| `PDEC-14A62D69A5` | BofA (exact) | FAC-A4A5EE | 7,200 (2h) | 900 | **no** | `synthetic — engineered` |

Provenance follows Task 14's own split: the baseline row is an ordinary
invented bank-internal fact (`synthetic — internal`); the two rows that
exist specifically to manufacture a condition public data would not
supply — the timeout, the attestation gap — are `synthetic — engineered`.

**One guarded write into `ccf_v2.context_debt`** — a pre-existing, 303-row
table another wave owns (serial PK, no unique constraint). PREFLIGHT
RULING P2's exact shape: `debt_id` never supplied, insert guarded by
`WHERE NOT EXISTS (... subject_kind='federation_attestation' AND
subject_key=declaration_id)`. `loaders/load_postgres_wave18.py` reads
`sources/screening/wave18_peer.json`'s `declarations` array (the same
artifact the peer loader writes from — not re-typed) and inserts one row
for the unattested declaration. Proved idempotent by a named value, not a
count: `debt_id` stayed `4047` across two runs, and the second run
inserted 0 new rows.

**Task 13's content probe extended.** `_postgres_wave18_tables_contain()`
now scans six tables, not five — `context_debt` added, since Task 15 gave
Wave 18 a write path into it. It still does not cover any other wave's
Postgres tables, the peer's `colender` schema (covered separately by
`test_the_desks_engineered_note_never_crossed_to_the_peer_fabric`), or
SQLite tables other than the tracker.

**Fixture fix.** `validators/test_syndicate.py`'s `_pg()` helper
unconditionally passed `params or ()` to `cur.execute`, which put psycopg
into placeholder-parsing mode even for a query with no `%s` — and
`WHERE reason LIKE '%unattested%'` then raised `only '%s', '%b', '%t' are
allowed as placeholders, got '%u'`. Fixed to pass `params` (`None` when
absent) straight through, which is the first Task 15 test this bit.

**No new FIBO terms; nothing for the vault mirror.** `product_id`,
`declared_ttl_seconds`, `declared_latency_ms`, and `attestation` are plain
Postgres columns, never `ex:`/FIBO IRIs — this task writes no Fluree
triples at all.

`generators/generate_peer_positions.py`, `loaders/load_peer_wave18.py`,
`loaders/load_postgres_wave18.py` extended; `validators/test_syndicate.py`
extended by 8 tests (96 total, up from 89).

`uv run --with pytest pytest validators/test_syndicate.py -q`: 96 passed.
`uv run validators/test_fabric_isolation.py`: 7/7 arms green.
`uv run validators/conditions.py`: 172 passed · 0 failed.
`uv run validators/partition.py`: 50/50 checks passed.

### 2026-08-26 — Wave 18 Task 16: `validators/syndicate.py`, the six §F floors

The wave's regression suite. Six conditions, each **recomputed live from the
loaded stores on every run** — no stored score, no cached rank, no boolean
flag, no `is_asymmetric`, no `granularity`, no `divergent` column. A
build-time validator, not an operator: it registers nothing, composes into
no plan, serves no principal, emits no contract, and writes nothing to
either fabric.

```
uv run validators/syndicate.py     # 6 passed · 0 failed
```

| Floor | What it recomputes | From |
|---|---|---|
| `shares_are_sourced` | every one of the 97 `ex:SyndicateParticipation` offsets resolves, in the **re-extracted** filing, to the lender the node claims, with its amount at that row | Fluree + Postgres + `sources/ex10/` |
| `envelopes_are_asymmetric` | envelopes whose request-set ≠ disclose-set, compared as SETS, both non-empty | Fluree |
| `precision_is_mixed` | one counterparty exact, one band-only, every row of the band counterparty a band, concealed figure absent from the **peer fabric** | peer Postgres + peer Fluree (needle located on our Fluree) |
| `vote_postures_diverge` | distinct `ex:votePosture` values on the one open vote | Fluree |
| `federation_bounds_bind` | latency over/under §B's 5,000 ms; unattested with a contrast **and** a matching `context_debt` row; min TTL < 14,400 s < max TTL | peer Postgres + our Postgres |
| `lineage_is_separable` | every element answers on exactly one fabric; no peer identifier in a local row that fails to declare the claim remote | both fabrics, all four of our stores |

**No `shares_reconcile`.** Preflight Ruling T16-PRE deleted it, measured:
not one of the twelve Wave 18 facilities' share sums closes against
`ccf_v2.facility.commitment_amount` — best case 4.0% off, worst 3391% —
for four legitimate reasons (placeholder rows the filing will not attribute,
amendment exhibits carrying only incremental commitments, tranche captions
spanning two facilities, and Wave 4 totals that are themselves wrong).
**The four causes are recorded in full in `docs/known-issues.md` §34**, so
nobody re-derives the floor and reports the estate broken. `Context` carries
no `share_totals` field (Ruling T16-R1): a populated-but-unread field
holding `recorded_total` is how a deleted condition survives its deletion.

**Ruling T14-R1 — what the mixed-precision floor may claim.** Not "the exact
position cannot be recovered": our own ledger holds
`ex:participationOf <Citibank> → FAC-405B7A ex:commitmentUsd 70000000`, a
real filed commitment-schedule row, and it is public. The floor is about
**what the peer discloses** — every position the peer holds for the banded
counterparty is a band, and no exact figure for it appears in any of the 99
peer cells (17 columns, 2 tables, plus the peer ledger's literals). Our
ledger locates the needle and is deliberately never scanned for it, which
the PASS line states out loud.

> **⚠️ SUPERSEDED, 2026-08-26 (whole-branch review fix, Ruling T16-R2).** The
> paragraph below described the ORIGINAL eight-probe design: eight hand-picked
> element names, checked once. Ruling T16-R2 replaced that with a **derived**
> population — every base table in either Postgres schema, every subject on
> either ledger, read from the estate on every run — precisely so an element
> absent from a hand-written list could no longer pass this floor by never
> being asked. `validators/syndicate.py:365`, `:534` and `:1437` already call
> the eight-probe design "an earlier cut of this file"; this document did not
> say so until now, which is what made it possible to read floor 6 as a check
> over five named Wave 18 elements when it has been a check over every base
> table in both schemas and every subject on both ledgers since T16-R2. Left
> in place as history rather than deleted, per this file's own convention for
> a superseded claim.

**`element_origin` is derived, never read (superseded description below;
see the corrected paragraph that follows).** It is a read-only `@property`
over `Context.element_probes`, which record which fabric ANSWERED each
element's one question — the same SPARQL asked of both ledgers, the same
table name counted in both schemas. Eight elements probed; five answer
locally (`syndicate_participation`, `amendment_vote_posture`,
`disclosure_envelope`, `own_position`, `syndicate_member`) and three
remotely (`disclosure_precision`, `peer_position`,
`peer_product_declaration`). Nothing in either fabric stores an origin, and
a marker somebody wrote down could not establish that no peer claim is
reachable through a local path. It is a property rather than a field so it
cannot be assigned a convenient value — `validators/test_syndicate.py`
asserts that assigning it raises.

**`element_origin`'s population, current design (Ruling T16-R2), measured
live 2026-08-26 from `uv run python validators/syndicate.py`.** The
population is DERIVED, not listed: every base table across `ccf_v2` and the
peer's `colender` Postgres schemas (key `pg:<table>`), plus every subject on
either Fluree ledger (key `graph:<subject IRI>`) — read from the estate on
every run, so a table or node a later wave adds joins the population without
anyone remembering to add it. None of the eight names from the superseded
paragraph above is a probe key any more.

That run measured **11,969** elements total — 113 Postgres tables across
both schemas plus 11,856 ledger subjects across both ledgers — of which
**11,965 answer locally** and **4 answer remotely**: two peer-ledger
subjects (`B4TYDEB6GKMZO031MB27`, `E57ODZWZ7FF32TWEFA76`) and two peer
Postgres tables (`pg:peer_position`, `pg:peer_product_declaration`). Every
one of the 11,969 answers on exactly one fabric.

**This is a measurement, not a guarantee.** The population is derived per
run and will move as the estate grows — the same framing
`docs/known-issues.md` §35 uses for its own live count of this floor's
population. Re-run `validators/syndicate.py` for a current figure rather
than trusting the numbers above past their date; they describe what floor 6
covers in shape (every base table, every ledger subject, on both fabrics),
which does not change, even though the count will.

**The leak scan counts its own denominator, and proves it can see.** Every
peer identifier (10: 7 `PPOS-`, 3 `PDEC-`) is hunted across **all 111**
`ccf_v2` base tables — not a hand-picked Wave 18 subset — plus 37,223 of our
ledger's literals and all 7 SQLite tables. Each store is scanned for a
CONTROL needle in the same pass (`SYNM-`, `#offset=`, `FAC-`); a store
returning zero for its control has stopped looking, and the floor fails
rather than reporting an absence it never established. One local occurrence
exists and is expected: the `ccf_v2.context_debt` row recording
`PDEC-14A62D69A5` as unattested. It is excused only by all four of — the row
is in `context_debt`, its `subject_kind` is `federation_attestation`, its
`subject_key` names an identifier that actually resolves on the peer fabric,
and its own `reason` text names the co-lender fabric.

**One defect this file caught on its first run.** The obvious single query
for participations joins `?member ex:lei ?lei`, which is INNER — and five
syndicate members carry no `ex:lei` (the five named funds, which CLAUDE.md
requires to omit the property rather than carry an empty string). Five of
the 97 participations silently vanished. Caught by `shares_are_sourced`'s
independent `COUNT(*)` denominator, which is the whole reason that guard
exists: a floor that cannot see a row cannot fail on it. The read is now
two queries.

**Every arm was shown capable of saying "no."** Sixteen falsification tests
in `validators/test_syndicate.py` mutate the snapshot — re-point a share at
the wrong lender, displace an offset by 50,000 characters, invent an amount,
symmetrise the envelopes, empty a scope, flatten the vote, hand the band
peer an exact figure, make every counterparty exact, stretch every remote
TTL to 24 hours, make every declaration fast, attest everything, make a peer
element answer locally too, empty the remote side, plant a peer identifier
in a local row — and require the opposite answer each time.

**No new FIBO or `ex:` terms.** This task reads terms Tasks 4–15 bound and
introduces none of its own, so the binding table is unchanged and the vault
mirror needs no refresh on this account.

### 2026-08-27 — Wave 18 Task 17 complete: `syndicated-lending-co-lender` registered — 20 of 21 products

**The count is derived, not incremented.** This file's own opening warning —
`facility-terms-snapshot` sat complete-but-uncounted for eleven waves — is
about trusting a prose list over the register, so the number was recomputed
rather than taken as 19 + 1. `validators/conditions.py` registers **20**
distinct products after this task (counted from the register's own output,
not from this paragraph); the vault's `context-products` topic holds **21**
product specs (25 files less `ccf-sdk-de-requirements`,
`ccf-v2-schema-delta`, `fibo-iri-binding` and `spec-standard-v0-3`, which
are not products). The one unregistered product is
`large-exposure-rwa-concentration`, which composes six prerequisites and is
last in build order by design.

#### What Wave 18 put in each store

| Store | Element | Count |
|---|---|---|
| Postgres `ccf_v2` | `syndicate_member` | 45 (40 with a real GLEIF LEI, 16 of those also an FFIEC RSSD, 5 name-only) |
| Postgres `ccf_v2` | `member_call_report` | 16 (one per RSSD-bearing member) |
| Postgres `ccf_v2` | `own_position` | 5 |
| Postgres `ccf_v2` | `competition_law_rule` | 4 |
| Postgres `ccf_v2` | `syndicate_projection_plan` | 3 |
| Postgres `ccf_v2` | `context_debt` (EXTENDED, not new) | +1 row, `subject_kind='federation_attestation'` |
| Fluree `fibo-v2` | `fibo-sec-dbt-dln:FinanceSyndicateMember` | 45 |
| Fluree `fibo-v2` | `fibo-sec-dbt-dln:SyndicatedLoan` | 12 |
| Fluree `fibo-v2` | `fibo-sec-dbt-dln:FinanceSyndicate` | 6 |
| Fluree `fibo-v2` | `fibo-sec-dbt-dln:AdministrativeAgent` | 4 |
| Fluree `fibo-v2` | `ex:SyndicateParticipation` | 97, each with `ex:commitmentUsd`, `ex:participationOf`, `ex:participationIn` |
| Fluree `fibo-v2` | `ex:AmendmentEvent` | 6, with 6 `ex:effectiveDate` and 12 `ex:amends` |
| Fluree `fibo-v2` | `ex:AmendmentVote` | 1, with 18 `ex:votesOn` / `ex:votePosture` |
| Fluree `fibo-v2` | `ex:AmendmentThreshold` | 16, with 24 `ex:thresholdGoverns` |
| Fluree `fibo-v2` | `ex:DisclosureEnvelope` | 2, 3 `ex:requestScope` / 3 `ex:discloseScope` terms |
| Fluree `fibo-v2` | `cmns-col:isMemberOf` | 64 |
| Fluree `fibo-v2` | `ex:sourcePassage` on Wave 18 nodes | 119 |
| MongoDB `fibo_v2` | `document`, `doc_type="credit_agreement_wave18"` | 6 |
| MongoDB `fibo_v2` | `document`, `doc_type="snc_annual_report"` | 1 (charts only — known-issues §37) |
| MongoDB `fibo_v2` | `passage`, `passage_kind="voting_threshold"` | 6 |
| MongoDB `fibo_v2` | `passage`, `passage_kind="assignment_provision"` | 6 |
| SQLite `data/departmental.sqlite` | `syndicate_desk_tracker` | 12 |
| **Peer** Postgres `bofa_syndicated`.`colender` | `peer_position` | 7 (6 exact, 1 band-only) |
| **Peer** Postgres `bofa_syndicated`.`colender` | `peer_product_declaration` | 3 |
| **Peer** Fluree `bofa/syndicate` | counterparty identity nodes | 2 (10 triples, all under `ex:peer/`) |
| **Peer** MongoDB `bofa_syndicated` | — | 0 collections, deliberately |

#### `validators/conditions.py` — a `#20 syndicated-lending-co-lender (Wave 18)` block, 12 checks

Six direct counts read live against the stores: syndicate members on a real
public identifier (40 ≥ 25 — **resolved** members, excluding the five
name-only funds, so the check cannot go on reading 45 if identifier
resolution regressed); competition-law constraint rules (4 ≥ 1, a §C row
nothing else counted); syndicated facilities with a parsed schedule (10 ≥ 6,
counted as distinct FACILITIES rather than participation nodes); bilateral
disclosure envelopes (2 ≥ 2); peer counterparty identities (2 ≥ 2, the
MINIMUM of the peer's Postgres and its ledger); peer product declarations
(3 ≥ 3).

Six ordering/absence conditions delegate to `validators/syndicate.py`'s own
floor functions through `_run_syndicate_floor`, modelled on `_run_aml_floor`
and inheriting its precondition discipline — `syndicate_member` absent or
the peer fabric unconfigured is a legitimate SKIP; `syndicate_member`
EMPTY, an import break, or any store outage is a FAIL, never a SKIP. The
six are `shares_are_sourced`, `envelopes_are_asymmetric`,
`precision_is_mixed`, `vote_postures_diverge`, `federation_bounds_bind`
(which carries three §F rows at once) and `lineage_is_separable`.

`lineage_is_separable` is registered as a **safety property, not a §F
condition** — §D's validation gates name "lineage provenance separation";
§F lists no `≥ N` for it. Same treatment Wave 17 gave
`no_path_to_real_entity`.

The `~6 facilities` / `~25 members` / `1 peer fabric` envelope figures are
shape rather than targets (Dave, 2026-08-24), but each names a population
without which a condition cannot be evaluated at all, so they are registered
as counts and the conditions registered separately. Full register after this
task: **184 passed · 0 failed · 0 skipped** (was 172).

One `validators.syndicate.Context` is built per `collect()` run and shared
across the six delegates. Measured: `load_context()` costs 21s because it
re-extracts six filings and reads both fabrics, so six loads would add two
minutes to every run. The cache is cleared on entry to `collect()`.

#### `validators/partition.py` — the fabric boundary, in BOTH directions

Six new checks, `50/50 → 56/56`.

Four are the familiar kind, about a new slice: `syndicate_member`'s column
set is **pinned exactly** (a denylist could not see a commitment mirrored in
under a name nobody anticipated); no Fluree-owned Wave 18 name appears as a
column on any of the five Wave 18 tables; `FinanceSyndicateMember` nodes
carry an **allowlist** of seven predicates and nothing else; and
`syndicate_desk_tracker` is SQLite's alone — checked as a table name in
Postgres and MongoDB *and* as its `desk_note` / `tracker_id` column names
anywhere in the Postgres schema, because a gate that selects by the property
it polices cannot see a duplicate under another table name (Ruling T13-R1).

Two are new in kind. **Nothing peer-owned is in our stores**: no
`peer_position` / `peer_product_declaration` table here, no peer-declared
predicate (`ex:disclosurePrecision`, `ex:declaredTtlSeconds`,
`ex:declaredLatencyMs`, `ex:attestation`) on our ledger, no subject under
`ex:peer/` on our ledger, and no peer identifier in any cell of the Wave 18
Postgres tables, `context_debt`, or the SQLite tracker. **Nothing of ours is
in the peer's**: the peer schema holds only its own two tables and no table
name of ours, no `SYNM-` member id or `SDT-` tracker id in any peer cell,
and every subject on the peer ledger is under `ex:peer/`.

Both value scans carry a **positive control**, and neither control is a
planted value. Inward: the scan must find one of our own `member_id`s, which
is certainly in the cells it just read. Outward: it must find our
`facility_id`s in the peer's cells — the crossing §C explicitly permits —
because a scanner blind to the permitted crossing is blind to a forbidden
one. `facility_id`, `lei` and `rssd` are excluded **by name**, never by
omission.

**One inward crossing is permitted, and writing this check is what surfaced
it.** §D step 5 requires an unattested remote claim to be recorded as
Context Debt rather than admitted, so `context_debt.subject_key` legitimately
holds a peer `declaration_id`. The exemption is drawn on the line between a
REFERENCE and a COPY: it covers declaration ids only (never a position id),
only in that row's two columns, only where a `federation_attestation` debt
row really exists, and the check separately asserts the peer's declared TTL
and latency VALUES did not ride in with the identifier.

**Fix round 1 made the code match that sentence, and narrowed it further.**
As first written the exemption was **column**-scoped: `_cell_scan` discards
row identity, so a peer declaration id in the `reason` of *any* of
`context_debt`'s 304 rows was exempted, while this paragraph, `docs/HANDOFF.md`
and the task report all described the one-row rule. Ruling **T17-R1**: fix
the code, not the documents. `context_debt` cells are now ROW-KEYED
(`pg context_debt.<column>#<debt_id>`) and the needle must be the
`subject_key` of the exact row it was found in. Ruling **T17-R2**: because
`validators/syndicate.py`'s `declares_remote()` decides the same question for
floor 6 and **disagrees in both directions** — it requires the reason to name
"co-lender", and it admits any peer identifier including position ids — the
partition exemption is now the **intersection** of the two predicates rather
than a second, differently-shaped hole. Neither implementation was unified
into the other (they serve different floors and both are validated); each
docstring now names the other and says why they differ. The estate's one real
crossing satisfies both, so the check stayed green through the change.

`POSTGRES_OWNED_ATTRS` gains 16 names (`rssd`, `idBasis`, `gleifCategory`,
`rawNames`, `retrievedAt`, `tier1Capital`, `totalAssets`, `totalEquity`,
`reportDate`, `shareUsd`, `internalRating`, `workoutPosture`, `ruleText`,
`constrains`, `perspective`, `elements`), all verified absent from the
ledger at the time of writing. `WAVE18_PG_TABLES` is added to the SQLite
"departmental only" forbidden set. **No new `ex:` type needed permitting** —
Tasks 4, 9, 10 and 11b had already added all five to `PERMITTED_EX_TYPES`.

Every new arm was made to say NO before being trusted, and eight of those
falsifications are committed as tests in `validators/test_syndicate.py`
(166 tests, was 158).

#### `validators/spec_coverage.py` — 16 of 16 §C rows mapped

`syndicated-lending-co-lender` added to both `PRODUCTS` and `MANIFEST`. All
sixteen rows PROBE a live store; none needed WAIVED or DEFERRED — the SNC
report was located by Task 12, so its row carries a live count and a
divergence rather than a gap.

Row matching is now **case-insensitive**, matching what
`read_catalog()`'s §C heading match already did (known-issues §22). It is
not a licence to stop reading the spec: the ambiguity guard stays an error,
and eight rows carry a `divergence` string recording where the estate
delivered something narrower than §C asked —

| §C row | Divergence recorded |
|---|---|
| Syndicate composition | shares are filed and cited but do not sum to the facility total, for four legitimate filing-side reasons (known-issues §32, §34) |
| Amendment events and effective dates | read from the amended EX-10 only; no 8-K Item 1.01 was fetched, so no announcement-vs-effective gap exists |
| Co-lender institution identities | §C names LEI **and** RSSD; both exist for 16 of 45 |
| Co-lender financial condition | 16 Call Reports, bounded by the RSSD gap — a source limit, not a work limit |
| Syndicated-market context | the 2025 SNC attachment is charts only (known-issues §37) |
| Passage spans on agreement text | offsets yes, embeddings no (known-issues §38; 72 Wave 17 advisory passages are in the same state, §42) |
| Own position, rating, and workout posture | 5 of 12 facilities — the 5 the peer also discloses |
| `participatesIn` · `votesOn` edges | `ex:participatesIn` is deliberately not minted; `cmns-col:isMemberOf` is the bound FIBO property, and the commitment share lives on the reified participation node |
| Simulated peer fabric | a TWO-store instance: Postgres + Fluree, no SQLite, an empty MongoDB |

`uv run validators/spec_coverage.py --product syndicated-lending-co-lender`:
**16 of 16 catalog rows accounted for (16 probed clean · 0 covered · 0
waived · 0 deferred)**, exit 0.

A pre-existing, unrelated failure in `counterparty-reference-snapshot`'s own
manifest still aborts a full-repo run — its vault §C wording has moved since
that mapping was written. Confirmed pre-existing by stashing this task's
changes and reproducing it against the unmodified file; case-insensitive
matching can only ADD hits, and that mapping matches **zero** rows either
way. It belongs to whichever task owns that product next.

#### The binding table did not change, so no bundle was needed for it

The `ex:` and FIBO rows in "Wave 18 extension — `syndicated-lending-co-lender`"
above are byte-identical to what
`~/.agent-exchange/ccf-dataprep/outbox/2026-08-26T19-49-47Z-wave18-task11b-threshold-bindings`
carried: 3 FIBO classes, 1 FIBO membership property adopted, 27 `ex:` terms
minted. This task minted nothing and retracted nothing. The only delta in
that section since the bundle was written is one **correction paragraph**
added by Task 11b's fix round 1, recording that a citation bug on 4 of 16
threshold nodes was fixed and the inside/outside conclusion re-verified
against the regenerated artifact. That is a caveat about the data, not a
binding — but a mirror that carries the conclusion without the caveat is
exactly the drift this project keeps recording, so it was sent as a small
corrective bundle naming what it supersedes.

Three Wave 18 bundles (Tasks 9, 10, 11b) remain **uncollected** in the
outbox. The mirror at `wiki/context-products/content/fibo-iri-binding` is
therefore stale by four bundles until the custodian applies them.

#### Wave 18 complete

Every §C row accounted for, every §F condition proven by a live query rather
than counted, the partition gate checking the fabric boundary in both
directions, and the store register above showing live counts.

Final figures **after the whole-branch review fix wave** (re-measured
2026-08-26; the earlier **593** this line named was one fix round stale, and
disagreed with `docs/HANDOFF.md`'s own count for the same run — both now
read from the same live run): `validators/conditions.py` **184
passed · 0 failed · 0 skipped**; `validators/partition.py` **56/56**;
`validators/syndicate.py` **6 passed · 0 failed**;
`validators/test_fabric_isolation.py` **7/7 arms**;
`validators/spec_coverage.py --product syndicated-lending-co-lender`
**16 of 16**; `uv run --with pytest pytest validators/test_syndicate.py -q`
**182 passed**; `uv run --with pytest pytest validators/ -q` **596 passed**
(every boundary sub-condition has a committed falsification, including two
that plant a value in the live estate and restore it within the test).

Remaining: `large-exposure-rwa-concentration`, last in build order because
it composes six prerequisites.

### 2026-08-27 — Wave 19 Task 3: FIBO verification and semantic binding for `large-exposure-rwa-concentration`

`generators/verify_fibo_wave19.py` (copied structure from
`generators/verify_fibo_wave18.py`, per brief) confirms **11/11** FIBO
terms declared in subject position in `sources/fibo/dev.fibo-quickstart.ttl`
and **16/16** candidate `ex:` local names absent from it under every prefix
— exit 0. An 8-term `KNOWN_PRESENT` matcher control (all found) guards
against the design session's own recorded regex defect (a trailing-space
requirement that made every absence verdict, including for `Exposure` and
`Capital`, worthless). Full detail, domain/range for every property, and the
script's output are recorded in the "Wave 19 extension" subsection above and
in `.superpowers/sdd/wave19-plan/task-3-report.md`.

One finding worth flagging on its own: the brief's candidate-for-minting list
included a bare `subsidiaryOf`. It is absent under that exact spelling, but
FIBO already declares `fibo-be-oac-cctl:hasSubsidiary` /
`isSubsidiaryOf` and this project already bound both in the Wave 8 table —
minting a new `ex:subsidiaryOf` would have duplicated an existing predicate.
`hasSubsidiary` is reused instead.

**Vault mirror needs refreshing** — 11 new FIBO bindings and 16 new `ex:`
terms, none previously in the table. The mirror was already stale by four
uncollected Wave 18 bundles; this makes five. Per the Task 3 brief, the
exchange bundle itself is sent in Task 17, not here — this table is the
source the bundle will be built from.

### 2026-08-27 — Wave 19 Task 6: `connectedTo` edges from the real GLEIF control graph

`loaders/load_group_edges.py` created. Reads `ccf_v2.corporate_ownership_record`
ACTIVE rows only (140 `IS_DIRECTLY_CONSOLIDATED_BY` + 140
`IS_ULTIMATELY_CONSOLIDATED_BY` = 280 records over 166 distinct LEIs,
matching the brief exactly) and writes, per record, one FIBO-typed
consolidation edge (`isDirectlyConsolidatedBy` / `isUltimatelyConsolidatedBy`,
child -> parent) plus the generic `ex:connectedTo` edge (184 distinct
(child, parent) pairs — 96 records share a pair across both relationship
types, so `connectedTo`'s edge count is naturally lower than the record
count; RDF triples are a set and components don't care about multiplicity).
**No `ConnectedGroup` node, table, or id is created anywhere** — per
`docs/wave19-design.md` §4, groups are recomputed by `validators/large_exposure.py`
(Task 15) on every run.

**No new node scheme.** Checked live first: 129 of the 166 LEIs already had
a Fluree node from Wave 3's original entity load; resolved via
`entity_uri_by_lei()` (`load_collateral_wave9.py`), never constructed. The
other 37 are `registry_company` (Wave 13b) GLEIF entities no loader had
ever pushed into Fluree — minted using Wave 3's own `local_name()` /
`entity_triples()` (lei + label + the 7-role corporate type chain +
`ex:provenance "public"`, nothing else — single-writer discipline holds,
all attributes stay in Postgres).

**Three new FIBO bindings this task found, that Task 3 missed** —
`isConsolidatedBy` / `isDirectlyConsolidatedBy` / `isUltimatelyConsolidatedBy`
— added to the Wave 19 extension table above. Used as the predicate that
carries GLEIF's relationship type onto each edge, rather than a reified
node or a node-level literal (`load_bo_chains_wave13b.py` already documents
why the latter failed a validator once: an edge attribute standing in as a
node mark breaks the moment the node has more than one edge of that kind,
which 96 of these 166 entities do). **Vault mirror needs refreshing** for
these three terms.

**Verification, against the live ledger, not a fixture:** the brief's
union-find script, folded into the loader's own `main()`, asserts the
graph these edges form has exactly **26 connected components** — the
figure measured against live Postgres during design. Ran twice (fresh load,
then a no-op idempotent re-run): both times, live query over
`?a <connectedTo> ?b` returned 184 edges and **26 components**. Matches; no
edges were dropped and the underlying GLEIF data has not moved since the
design measurement.

**Idempotency, by value:** re-ran with all 166 nodes already present (0
minted the second time; triple count unchanged, 87,088 -> 87,088, ledger
`t` advanced 4028 -> 4029). Picked BESSO LIMITED
(`213800K7ROBLZGACZV98`) — one of the 37 minted nodes, and one whose direct
and ultimate parents differ, the sharpest case for this loader — and
queried by value after the re-run: `isDirectlyConsolidatedBy -> BGC
PARTNERS, INC.` and `isUltimatelyConsolidatedBy -> BGC Group, Inc.`, both
also present as `connectedTo`, label and lei intact on all three nodes. A
triple count alone could not see a relationship type silently collapsing
onto the wrong parent; this check could.

### 2026-08-27 — Wave 19 Task 7: engineered `economicallyDependentOn` edges

`generators/generate_dependency_edges.py` created (writes
`sources/screening/wave19_dependency_edges.json`); `loaders/load_group_edges.py`
extended to load it. Four edges, chosen by measuring the live estate rather
than by picking plausible-sounding names, doing three jobs between them:

1. **A group control-based grouping alone would miss.** Vertiv Holdings Co
   -> TransDigm Group Inc. TransDigm ($14.6bn borrower) has **zero**
   `connectedTo` edges of any kind — not a small component, not a component
   at all — so the merged group cannot be produced by any control traversal.
2. **An edge that changes which limit binds, with no invented limit.**
   TransDigm ($14.600bn, 4.9358% of $295.8bn tier 1) + Vertiv ($7.8865bn,
   2.6662%) = **$22.4865bn, 7.6019%**. Any internal appetite in
   `(4.9358%, 7.6019%]` makes this merged group breach an appetite neither
   predecessor would have breached alone. Task 9 sets the actual number;
   Task 15 recomputes the crossing from the stores. No limit and no breach
   flag exists yet — nothing here asserts a breach.
3. **Closed 3 of the jurisdiction gap's remaining 6.** 9 of 26 control-basis
   groups span >= 3 jurisdictions on their own (`docs/wave19-design.md` §9).
   Every one of the estate's 10 facility-holding singletons is US-only, so
   only a merge of two groups that each already carry a *different* non-US
   country adds a third. Three such pairs, each with a genuinely defensible
   supplier-concentration judgment: Container Store (SE, US) + Griffon
   (AU, US) -> 3; Super Micro (NL, US) + Extreme Networks (IN, US) -> 3;
   Hain Celestial (GB, US) + Tupperware (IN, US) -> 3. A fourth candidate
   (Agilysys/Hain Celestial) was considered and rejected — no plausible
   supply, funding or tenancy link exists between a hospitality-software
   vendor and a packaged-foods company, and the brief is explicit that an
   indefensible merge must not be forced. **9 -> 12 of ~15; the remaining
   shortfall of 3 is a recorded divergence, not closed.**

**All 4 edges are between real, GLEIF-registered public companies — only the
relationship is invented.** Same shape the design doc already committed to
for Reg O (real bank, invented insider). `ex:provenance "public"` on all 8
entity nodes is left untouched; the engineered label goes on
`ex:edgeProvenance` (bound Wave 13b for exactly this — a fact about a
relationship, not a node) with value `synthetic — engineered`, never on
`ex:provenance`, which would falsely relabel a real company's own node.

**Why node-level literals, not reification, for `assertedBy` /
`assertedOn` / `dependencyBasis`.** Task 6's own docstring rejects a
node-level literal for edge attributes specifically because a subject there
could carry two relationship types to different objects. Here each of the 4
subjects carries exactly one outgoing `economicallyDependentOn` edge — the
generator refuses to write its artifact if that stops being true, and the
loader independently re-checks the same invariant against the artifact it
reads — so the literals are unambiguous. `economicallyDependentOn` itself
stays a direct, unreified triple because both the brief's verification
script and `validators/large_exposure.py` (Task 15) query
`?a <economicallyDependentOn> ?b` directly. `ex:dependencyBasis` also embeds
the depended-upon party's name and LEI in its text, the same
self-describing convention `comparabilityBasis` (Wave 12, above) uses for
the same reason.

**Analyst identifier reused, not invented.** `ex:assertedBy "BKR011"` —
Rafael Adeyemi, `role=credit`, `seniority=analyst`, `desk=Credit Risk`,
confirmed live against `ccf_v2.banker` by the loader before every write
(`verify_analyst()`) rather than assumed from the generator's own comment.

**`ex:dependencyBasis` is the only new FIBO-adjacent term this task adds** —
see the Wave 19 extension table above and the "17th `ex:` term" note.
`economicallyDependentOn`, `assertedBy`, `assertedOn` were already bound by
Task 3 and reused as-is. **Vault mirror needs refreshing for
`dependencyBasis`.**

**Verification, against the live ledger:** union-find over `connectedTo`
alone reconfirms Task 6's **26** components, unchanged (these edges add no
`connectedTo` triples). Union-find over `connectedTo` +
`economicallyDependentOn` gives **23** — strictly lower, so the merge
actually merges, per the brief's own required check. Groups spanning >= 3
jurisdictions individually: **9 (control) -> 12 (both)**; collective
country count unchanged at 26 (no new country entered the estate, only
new combinations of existing ones). Ran twice: triple count unchanged
87,109 -> 87,109 on the second run, and a named-edge by-value check
(Vertiv -> TransDigm) found exactly one value each for
`economicallyDependentOn` / `assertedBy` / `assertedOn` / `dependencyBasis`
/ `edgeProvenance` after the re-run — a count alone cannot see a literal
being silently duplicated or reset.

Full arithmetic, per-edge rationale and the `validators/partition.py`
result are in `.superpowers/sdd/wave19-plan/task-7-report.md`.

### 2026-08-27 — Wave 19 Task 9: limit envelope and real regime version history

`generators/generate_limit_envelope.py` (new) and `loaders/load_policy_fluree.py`
(extended, alongside Task 8's insider designation) write **3 `RegimeVersion`
nodes** (all `public`) and **1 `LimitEnvelope`** node (`synthetic —
internal`) into `fibo-v2`. **No new FIBO bindings** — every predicate used
(`effectiveFrom`, `effectiveTo`, `limitPctOfCapital`, `limitAbsoluteUsd`,
`citesProvision`, `governedByRegime`) and both classes (`RegimeVersion`,
`LimitEnvelope`) were already bound by Task 3 above; nothing here changes
the vault mirror's obligations beyond what Task 3 already flagged.

| Regime version | Effective from → to | Limit | Cited passage(s) |
| --- | --- | --- | --- |
| CRR (assimilated UK law) | 2014-01-01 → **2021-12-31** | 25% of eligible capital | `crr-art-395-2021-12-31#491d3c2ccd3e` (Article 395(1)) |
| PRA Large Exposures Part | **2022-01-01** → (open) | 25% | `crr-art-395-2021-12-31#491d3c2ccd3e` (CRR Article 395(1) — the provision that actually **states** the limit; the PRA Part does not restate it) + `pra-large-exposures-01-01-2022#1ee205cc4796` (LE 2.4 — the PRA instrument that **applies/modifies** that limit for a UK firm post-boundary) |
| Regulation O (12 CFR 215.4(b)) | 2026-01-01 (the eCFR "as of" date actually fetched) → (open) | $500,000 absolute | `reg-o-12cfr215#f8f8d951ecdb` (215.4(b)(2)) |

The 2021-12-31/2022-01-01 boundary is SI 2021/1078 — a real regulatory
handover, not an invented one — and alone satisfies §F's "≥ 2 regime
versions with distinct effective dates."

**`effectiveTo` is asserted only when a regime version actually closed.**
CRR gets the literal; PRA and Reg O (both still in force) get **no
`ex:effectiveTo` triple at all** rather than a `9999-12-31` sentinel — a
sentinel sorts correctly but reads as a false claim about when something
ends. Consumers must treat an absent `effectiveTo` as open-ended.

**Internal appetite: 5.0% of tier 1 capital**, re-derived live (not copied
from Task 7's report) against `ccf_v2.bank_capital` (`$295,758,000,000`
exact tier 1, vs. the $295.8bn headline Task 7's report rounded to — the two
reconcile exactly once that rounding is accounted for) and a fresh
union-find over `connectedTo` / `connectedTo`+`economicallyDependentOn`:
largest control-basis group (Bausch Health) **5.4148%**, TransDigm alone
**4.9365%**, TransDigm+Vertiv merged **7.6030%**. 5.0% sits below the first
(a real group breaches house policy while staying compliant under CRR/PRA)
and inside `(4.9365%, 7.6030%]` (Task 7's `economicallyDependentOn` edge
changes which limit binds). `governedByRegime` points the envelope at the
live `pra-2022` `RegimeVersion` node.

**Fix round 1 (coordinator review, 2026-08-27): the first cut wrongly cited
LE 2.3 as the source of the PRA regime's 25% limit.** Measured across the
whole PRA corpus: zero passages contain "must not incur"/"shall not
incur" — the PRA Large Exposures Part states no prohibition anywhere in
what Task 2 fetched. LE 2.3's "25%" is a core-UK-group *notification* duty,
not the prohibition. **LE 2.4** independently shows the true mechanism:
"A firm must exclude from **the limit in Article 395(1) of the CRR**..." —
SI 2021/1078 moved the large-exposures *regime* into the PRA Rulebook on
2022-01-01, but the replacement Part does **not restate** the 25% figure;
it cross-references Article 395(1) by name. The PRA `RegimeVersion` now
cites that same CRR passage (already cited by the CRR version) alongside
LE 2.4, and LE 2.3 is dropped, not re-labelled — nothing in this wave's own
conditions needs a "notification threshold" fact recorded. `loaders/load_policy_fluree.py`
also gained `retract_stale_regime_triples()`: Fluree is append-only, so
correcting a citation set required deleting the stale LE 2.3 triple before
reinserting, scoped to Task 9's own 4 node URIs only (never a blind
predicate-wide delete). Full detail in
`.superpowers/sdd/wave19-plan/task-9-report.md`'s "Fix round 1" section.

**Guard, run live after every write:** every `RegimeVersion` node must carry
`>= 1 citesProvision` value or the load fails — 0 found would raise, not
warn. Ran twice against `fibo-v2`: triple count unchanged on the second run
(87,161 → 87,161), confirming idempotency by value, and
`validators/partition.py` stayed **56/56** (two new `PERMITTED_EX_TYPES`
entries added for `RegimeVersion`/`LimitEnvelope`, same mechanism Task 8
used for `InsiderDesignation`).

Full arithmetic and the loader's live output are in
`.superpowers/sdd/wave19-plan/task-9-report.md`.

### 2026-08-27 — Wave 19 complete: `large-exposure-rwa-concentration` registered — 21 of 21 products

**The count is derived, not incremented**, per this file's own standing
practice (see the 2026-08-27 Wave 18 entry above). `validators/spec_coverage.py`'s
own `PRODUCTS` list holds **21** entries after this wave, counted from the
list itself; the vault's `context-products` topic holds **21** product
articles (25 files less `ccf-sdk-de-requirements`, `ccf-v2-schema-delta`,
`fibo-iri-binding`, and `spec-standard-v0-3`, which are standards, not
products). Both counts were taken independently and agree. There is no
22nd product left to build — this was the last one, deliberately, because
it composes six prerequisites (CLAUDE.md's build order).

#### What Wave 19 put in each store

| Store | Element | Count |
|---|---|---|
| Postgres `ccf_v2` | `bank_capital` (repaired: `unit` column added) | 12 (reporting bank, 12 quarters) |
| Postgres `ccf_v2` | `member_call_report` (repaired: `unit` column added) | 16 (peer institutions; 852218 counted once, shared with `bank_capital`) |
| Postgres `ccf_v2` | `exposure_proposal` (new) | 2 (`BREACHES`, `FITS_AFTER_MITIGATION`, both `is_hypothetical`) |
| Postgres `ccf_v2` | `large_exposure_projection_plan` (new) | 3 (credit-officer, committee, examiner) |
| Fluree `fibo-v2` | `fibo-fbc-fct-fse:Bank` / `BankHoldingCompany` / `fibo-fbc-fct-usfse:NationalBank` nodes | 3 (852218, 651448, holdco 1039502) |
| Fluree `fibo-v2` | `fibo-be-oac-cctl:hasSubsidiary` edges | 2 |
| Fluree `fibo-v2` | `ex:connectedTo` edges (control-basis) | 184, over 26 components |
| Fluree `fibo-v2` | `isDirectlyConsolidatedBy` / `isUltimatelyConsolidatedBy` | 140 + 140 |
| Fluree `fibo-v2` | `ex:economicallyDependentOn` edges (engineered) | 4 — 26 components collapse to 23 once these are added |
| Fluree `fibo-v2` | `ex:RegimeVersion` nodes | 3 (CRR, PRA, Reg O), all `public` |
| Fluree `fibo-v2` | `ex:LimitEnvelope` nodes | 1, `synthetic — internal` |
| Fluree `fibo-v2` | `ex:InsiderDesignation` | 1 person (`SYN-INSIDER-JPM-01`), 2 `designatedPerson` triples |
| MongoDB `fibo_v2` | `document`, regime text (`reg-o`, `crr`, `pra`) | 31 |
| MongoDB `fibo_v2` | `passage`, regime text | 464 (after Task 4's fix round 1 removed 49 spurious roman-numeral splits) |
| MongoDB `fibo_v2` | `document`, methodology | 2, `synthetic — internal` |
| MongoDB `fibo_v2` | `passage`, methodology | 12 |
| SQLite `data/departmental.sqlite` | `large_exposure_limit_workbook` (new) | 5 |

#### `validators/conditions.py` — a `#21 large-exposure-rwa-concentration (Wave 19)` block, 15 checks

7 direct counts (bank capital reports, exposure proposals, ProjectionPlans,
the examiner plan's methodology+replay attribution, economic-dependency
edges, regime versions, the Reg O related-party case) plus 8 delegated
floors recomputed live from the stores at `as_of` time — groups recompute
from `connectedTo`/`economicallyDependentOn` rather than a stored id; a
dependency edge is shown to change which limit binds; CRR/PRA compliance
diverges from a Reg O breach under identical facts; one proposal breaches
**net of mitigation** (not merely gross — floor 4 was tightened mid-wave
specifically so a gross-only breach fails it, see `docs/wave19-plan/progress.md`);
mitigation is shown load-bearing on the other proposal; a real connected
group is shown to breach `debt_tolerance` against `policy_tolerance()` read
live (not a hard-coded bound); the three ProjectionPlans are pairwise
distinct by their `elements_included` sets, not merely three existing rows;
and no `public`-provenance row anywhere asserts, in free text or by
omission of a synthetic label, that the real reporting bank itself breached
a regulatory limit.

#### `validators/partition.py` — `check_wave19()`, 4 checks

No capital figure (11 `bank_capital` column names) lands on a Fluree node —
the same leak class this wave's own `ex:rssd` regression on these bank
nodes demonstrated mid-wave and fixed (commit `0186399`) before this
permanent check existed; no connected-group table exists in Postgres
(groups are recomputed, never stored); every `citesProvision` value is a
passage-id reference, never regime prose, and no Postgres column holds
regime text; no hypothetical proposal has leaked into the real `facility`
table by id or by exact `(borrower_lei, commitment_amount)` match.

#### Final measured state

`validators/conditions.py` **199 passed · 0 failed · 0 skipped** (was 184);
`validators/partition.py` **60/60** (was 56/56);
`validators/large_exposure.py` **8 passed · 0 failed**;
`uv run --with pytest pytest validators/test_large_exposure.py -q` **42 passed**;
`validators/spec_coverage.py --product large-exposure-rwa-concentration`
**17 of 17 §C rows** (12 probed clean · 4 covered by `conditions.py` · 0
waived · 1 deferred — FFIEC 101, see below). All read live from the
register itself, not copied from a prior wave's figures.

#### What was NOT built, and why — two honest gaps, not silent ones

**FFIEC 101 is absent.** What is loaded is FFIEC Call Report Schedules
RC-C/RC-R — bank-**level** FDIC BankFind data. FFIEC 101 (advanced
capital-adequacy detail) is filed at the **consolidated holding-company**
level, on an FR Y-9C capital base this estate does not load. There is no
holding-company chain here for an advanced-approaches RWA-detail row to
attach to; every RWA figure in the estate is the standardized, bank-level
number. Recorded as a `GAP` in `spec_coverage.py`, not waived.

**The jurisdiction span is 12 of a ~15 shape.** 9 of the 26 control-basis
connected components span ≥ 3 jurisdictions on real GLEIF control edges
alone (Wave 15). Task 7's 4 engineered `economicallyDependentOn` edges
closed 3 more of the shortfall via genuinely defensible supplier-concentration
merges — 9 → 12. A 4th candidate (Agilysys ∪ Hain Celestial) was
**considered and rejected**: no plausible supply, funding, or tenancy link
exists between a hospitality-software vendor and a packaged-foods company,
and forcing a merge with no defensible basis would be exactly the
"counted but not created" failure CLAUDE.md warns against. The remaining
shortfall of 3 is a recorded divergence — noted in `conditions.py`'s
`groups recompute` check text, not added to `spec_coverage.py` (that file
maps §C catalog *elements*, and no §C row names a jurisdiction-span
population for a divergence note to attach to; inventing one would be
fabricating a row the vault spec does not contain).

#### The two stale `docs/spec-digest.md` findings this wave corrected

Both dated 2026-08-27 in place, not silently overwritten: the "3 countries
/ 3 non-US entities / thin tail" jurisdiction finding was true on
2026-08-17 and has not been true since Wave 15's GLEIF subsidiary fetch
(30+ countries, 421 entities, 26 groups, 9 spanning ≥ 3 jurisdictions on
control edges alone); and "regime version history" was listed among
`large-exposure-rwa-concentration`'s engineered elements when it is real,
sourced from SI 2021/1078 and the PRA Rulebook's own point-in-time
versions. See `docs/spec-digest.md` for the corrections and
`docs/known-issues.md` §45–§49 for five new findings from this wave (EUR-Lex
blocked, the "omitted" string trap, the capital units defect, the
corpus-wide embedding gap being ~170x larger than previously recorded, and
the cross-reference-citation pattern that bit twice in one wave).

#### No new FIBO/`ex:` terms this task

Registration only. Tasks 3, 6, and 7 minted everything new this wave — see
the "Wave 19 extension" binding-table subsection above for the full list
(11 FIBO classes/properties, 17 `ex:` terms, one FIBO term reused rather
than re-minted). **Vault mirror needs refreshing for all of it** — the
mirror was already stale by four uncollected Wave 18 bundles before this
wave began; Wave 19's additions make it a fifth bundle's worth. Sent
through the agent exchange in Task 17 (this entry's own task), not edited
in the vault directly.

#### Wave 19 complete

Every §C row for `large-exposure-rwa-concentration` accounted for (one
honest `GAP`, not waived); every §F `≥ N` condition proven by a live query
against the loaded stores, several tightened mid-wave specifically because
a first cut satisfied the letter of a condition without the substance (the
PRA citation naming a notification duty instead of the prohibition it
actually invokes; the two hypothetical proposals originally collapsing
into the same demonstration under the product's own `apply_mitigation`
default); `check_wave19()` extending the partition gate in both directions;
and the register agreeing with the vault's own product count. Twenty-one
of twenty-one context products in this catalog are now registered.

### 2026-08-28 — Wave 20: the three T1 gaps closed before rung 1 is built

`counterparty-reference-snapshot` is rung 1 of the build ladder and every
other product inherits its contract machinery. Its §C carried three real,
named absences. All three are now closed; the product reports **4 of 4
catalog rows with zero GAPs**.

**No FIBO terms were added or changed.** Nothing in this wave touched the
ontology, so the IRI binding table above is unchanged and the vault mirror
needs no refresh.

#### Schema changes

| Table | Change |
|---|---|
| `ccf_v2.legal_entity` | `address_{country,city,region}` **renamed** to `legal_address_*`; `hq_address_{country,city,region}` **added** |
| `ccf_v2.crosswalk` | `lei` is now **nullable**. `UNIQUE (lei)` stays — Postgres treats NULLs as distinct, so any number of no-LEI clients coexist under it |
| `ccf_v2.principal_jurisdiction` | **new.** `(principal_id, jurisdiction_prefix)` PK, FK to `principal`. Entitlement grants, provenance `synthetic — internal` |
| `ccf_v2.internal_client` | **new.** PK `internal_client_id`. No-LEI identity from the internal client master, with its KYC state and freshness ceiling |

The rename touched four files (`load_postgres_wave1.py`,
`load_abs_overlay_wave14.py`, `load_gleif_subsidiaries.py`, and the
`spec_coverage.py` prose). The **retained source files under `sources/`
keep their original `address_*` key names** — they are fetched artifacts
carrying a `retrieved_at`, and rewriting one to match a later schema would
falsify the record of what the source returned. Loaders map instead.

#### Gap 3 — the addresses were never labelled

§C names `addresses`, plural; §B names which two. The estate held ONE
triple called `address_*` with nothing recording which of the two it was.
It was the legal domicile. That ambiguity was the worse half of the defect:
a missing address returns nothing and the consumer notices, an unlabelled
one returns Wilmington, Delaware for a company run from Whippany.

Headquarters loaded for **153 of 156** — 103 subsidiaries already held in
`sources/gleif_l1/subsidiaries_l1.json`, 50 anchors fetched by
`generators/fetch_anchor_hq_wave20.py` (50/50 resolved). **65 of 153 name a
genuinely different place**, measured with case and whitespace normalised;
a raw comparison says 69, and 4 of those differ only in case
(`AMPHENOL CORP /DE/` carries `WILMINGTON` against `Wilmington`) and are
one address typed twice.

The 3 without a headquarters are the synthetic ABS deal trusts. GLEIF has
no record of them and never will, and the exclusion is **derived from the
LEI form rather than listed**, so a fourth synthetic entity is excluded
automatically and a real LEI can never be excluded by a stale list.

#### Gap 1 — jurisdiction entitlement, recomputed rather than read

`principal` carried `sees_mnpi`, `sees_need_to_know`, `sees_eu_person_data`
and **no jurisdiction at all**, so the Policy Operator §B binds had nothing
to filter on. `validators/entitlement.py` recomputes visibility from
`legal_entity.legal_jurisdiction` against `principal_jurisdiction` on every
run — no stored flag, no cached set.

| Principal | Scope | Visible |
|---|---|---|
| `PRIN-COV-001` coverage banker | `US` | 74 of 156 |
| `PRIN-RES-002` research analyst | `US, GB, CA` | 102 |
| `PRIN-TRD-003` trader | `GB, HK, JP, SG` | 21 |
| `PRIN-KYC-004` EU KYC analyst | `AT BE DE ES HU IT LU NL SE` | 21 |

A country prefix admits its ISO 3166-2 subdivisions (`US` admits `US-DE`);
entitlement narrows and never widens, so `US-DE` does not admit `US-MD`.
GB is deliberately absent from the EU analyst's scope — the correct
post-Brexit answer, and the loader asserts that absence **by name**, since
a row count cannot see `GB` quietly appearing.

**The estate supplies its own falsifier.** The trader and the EU analyst
each see **21 entities and share none of them**: 4 distinct views, only 3
distinct sizes. A gate comparing how many each principal can see reports 3
and is wrong. The checks compare SETS.

#### Gap 2 — no-LEI internal clients, and the blindness that hid them

The estate held **zero** entities without an LEI. §D: *"an LEI-only anchor
silently excludes privately-held middle-market borrowers, and every
downstream product inherits the exclusion."*

The old manifest could not see it. Its predecessor row was COVERED against
crosswalk floors that are **all inner joins on `lei`** — structurally
incapable of reporting the absence of entities that have none. The floor
read a healthy 50 throughout.

30 borrowers now sit in `internal_client` with `lei IS NULL` and **no
`SYN-` placeholder** — a placeholder resolves, which would defeat §G's
acceptance criterion. Names are assembled from invented components by a
seeded generator, so no real private company is described. Identifiers
start at `CLI-000101`, deliberately offset from the existing `CLI-0000NN`
block, because a contiguous continuation collides the first time the anchor
set grows.

**A separate table, not a nullable `legal_entity.lei`:** that column is the
primary key with 9 foreign keys on it, and §C's single-writer paragraph
names the internal client master as a different authority. Provenance
`synthetic — internal`, §C's stated class — an earlier
`synthetic — engineered` ruling was overturned because `engineered_entity`
holds invented *patterns* while this is operational identity.

#### One existing invariant this wave correctly broke

`crosswalk rows pointing at no entity` counted all 30 no-LEI clients as
orphans — the check's population outgrowing its question. The **resolution
target** was widened, not the new rows exempted: a row WITH an LEI must
still match a `legal_entity`, a row WITHOUT one must match an
`internal_client`, and a NULL-lei row nothing backs is still an orphan.
Verified in a rolled-back transaction that it still bites both ways.

The widening opened a hole in the other direction — an `internal_client`
that no crosswalk row reaches — so `internal clients no crosswalk row
reaches` was added alongside it.

#### Registration

- `conditions.py` **199 → 208** passed, 0 failed.
- `partition.py` **60 → 63** passed. `check_wave20()` adds three checks,
  each carrying a **positive control**, because all three assert an absence
  and an absence check that cannot see anything passes forever: no no-LEI
  client inside `legal_entity` (control finds a known name), no postal
  address on a Fluree node (control sees 449 `ex:lei` assertions), and
  entitlement scope Postgres-only (control counts 17 live grants).
- `spec_coverage.py` — `counterparty-reference-snapshot` 4 of 4 rows,
  2 probed clean, 2 covered, **zero GAPs**.
- 745 tests pass.

### 2026-08-30 — `obligor-financial-spread`: one binding added, and a stated FIBO boundary

`ccf-sdk` asked (exchange, 2026-08-30) why `fibo-iri-binding` carries
product-named vocabulary for eleven products and none for this one, and posed
the question sharply: **does an attribute-level product get ontology bindings
at all, or is `[UNMAP]` the correct and permanent answer for its payload rows?**

Their instinct — *"a wrong binding invented to fill it would be worse than the
gap"* — is right, and the answer is neither of the two options. It is a split,
and it is evidenced rather than asserted.

#### Verified against the EDM Council source, not against URL resolution

Searched the `edmcouncil/fibo` clone at `119fa8c` (295 `.rdf` files) for
`rdf:about` declarations. **A first pass returned zero for every term including
`MonetaryAmount`, which was a broken pattern, not an absence** — FIBO writes
`rdf:about="&fibo-fnd-acc-cur;MonetaryAmount"` in entity-reference form, so a
search for a full IRI can never match. Caught by a positive control on a term
we already bind. See [[edmcouncil-url-resolves-for-fake-terms]] territory: the
grep has to be shown to find something before its zeros mean anything.

#### What IS bindable — the value, and only the value

| Element | Bound term | Full IRI |
|---|---|---|
| `financial_fact.value` + `.unit` | `fibo-fnd-acc-cur:MonetaryAmount` | `https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount` |
| the currency of that amount | `fibo-fnd-acc-cur:hasCurrency` → `fibo-fnd-acc-cur:Currency` | same module |

`MonetaryAmount` is a `cmns-qtu:ScalarQuantityValue` carrying a required
`hasCurrency`. Our `(value numeric, unit text)` pair is exactly that shape —
`unit` holds ISO 4217 codes (USD 15,051 rows, CAD 4).

#### What is ABSENT from FIBO, and is therefore permanently `ex:`

Every one of these was searched for and is not declared anywhere in the source:

`FinancialReport` · `FinancialStatement` · `Revenue` · `Revenues` · `Assets` ·
`Liabilities` · `NetIncome` · `InterestExpense` · `OperatingIncome` ·
`LongTermDebt` · `Depreciation` · `CashEquivalent` · `ReportingPeriod` ·
`DatePeriod` · `ExplicitDatePeriod` · `Filing` · `RegulatoryFiling` ·
`AccountingReport`

Three near-misses exist and **must not be used**: `Income`, `Debt` and
`Amortization` are declared, but FIBO's `Debt` is an *instrument/obligation*
(its neighbours are `CollateralizedDebtObligation`, `BasketOfDebtInstruments`)
— it models what a debt IS, not how much debt appeared on a balance sheet in a
quarter. Binding `LongTermDebt` to it would be exactly the invented binding
`ccf-sdk` warned against.

#### The boundary, stated once

**FIBO models financial ENTITIES, INSTRUMENTS and RELATIONSHIPS. It does not
model FINANCIAL REPORTING.** Not the reported fact, not the line item, not the
fiscal period, not the filing, not the accession, not the restatement chain.
`ccf-sdk`'s reading is confirmed: this is the first product on the ladder whose
payload is *attributes and time* rather than entities and edges, and the
vocabulary genuinely has nothing to say about it — with the single exception of
the amount itself.

So `[UNMAP]` is **correct and permanent** for the reporting-shaped rows, and it
should be recorded as a stated boundary rather than a gap awaiting closure. The
`ex:` predicates already carrying `tag`, `period_end`, `fiscal_period`,
`accession` and `filed_date` are the right and final home for them.

`fibo-iri-binding`'s claim that *"coverage is closed against every spec in this
catalog"* was true in the sense that no term was missing; it read as false
because a product with no section looks unexamined. **The vault mirror needs
refreshing** with this section so the boundary is visible rather than inferred.
