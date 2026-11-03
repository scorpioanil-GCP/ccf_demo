#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

EXPORT = Path("fibo-instances.json")
ENTITIES_OUT = Path("mongo-entities.json")
RELS_OUT = Path("mongo-relationships.json")

def expand(term: str) -> str:
    if not term:
        return term
    # already full IRI
    if term.startswith("http://") or term.startswith("https://"):
        return term
    # common compact forms seen from Fluree
    prefixes = {
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf:": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "ex:": "http://example.org/fibo/",
        "fibo-fnd-pty-pty:": "https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/",
        "fibo-be-corp-corp:": "https://spec.edmcouncil.org/fibo/ontology/BE/Corporations/Corporations/",
        "fibo-be-oac-cown:": "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Ownership/",
        "fibo-be-oac-cctl:": "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Control/",
        "fibo-be-le-lp:": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/",
        "fibo-be-le-fbo:": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/FormalBusinessOrganizations/",
        "fibo-fnd-aap-agt:": "https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/Agents/",
        "fibo-fnd-rel-rel:": "https://spec.edmcouncil.org/fibo/ontology/FND/Relations/Relations/",
    }
    for pfx, ns in prefixes.items():
        if term.startswith(pfx):
            return ns + term[len(pfx):]
    return term

PRED_MAP = {
    "http://www.w3.org/2000/01/rdf-schema#label": "label",
    "http://example.org/fibo/lei": "lei",
    "http://example.org/fibo/legalName": "legalName",
    "http://example.org/fibo/jurisdiction": "jurisdiction",
    "http://example.org/fibo/entityStatus": "entityStatus",
    "http://example.org/fibo/clientType": "clientType",
    "http://example.org/fibo/riskRating": "riskRating",
    "http://example.org/fibo/kycStatus": "kycStatus",
    "http://example.org/fibo/onboardingDate": "onboardingDate",
    "http://example.org/fibo/fullName": "fullName",
    "http://example.org/fibo/nationality": "nationality",
    "http://example.org/fibo/dateOfBirth": "dateOfBirth",
    "http://example.org/fibo/role": "role",
    "http://example.org/fibo/ownershipPercent": "ownershipPercent",
}

REL_PREDS = {
    "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn": "hasOwnershipInterestIn",
    "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/Control/hasControllingInterestIn": "hasControllingInterestIn",
    "https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/isRelatedTo": "isRelatedTo",
}

TYPE_PRED = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

def val(binding):
    return binding.get("value") if binding else None

def main():
    data = json.loads(EXPORT.read_text())
    bindings = data.get("results", {}).get("bindings", [])

    entities = defaultdict(lambda: {"types": [], "source": "fluree:fibo:main"})
    relationships = []

    for row in bindings:
        s = expand(val(row.get("s")))
        p = expand(val(row.get("p")))
        o_raw = val(row.get("o"))
        o = expand(o_raw) if row.get("o", {}).get("type") == "uri" else o_raw

        if not s or not p:
            continue
        if not s.startswith("http://example.org/fibo/"):
            continue

        if p == TYPE_PRED:
            short = o.rsplit("/", 1)[-1] if isinstance(o, str) else o
            if short and short not in entities[s]["types"]:
                entities[s]["types"].append(short)
            continue

        if p in REL_PREDS:
            relationships.append({
                "from": s,
                "to": o,
                "type": REL_PREDS[p],
                "source": "fluree:fibo:main",
            })
            continue

        field = PRED_MAP.get(p)
        if field:
            entities[s][field] = o
        else:
            # keep unknown instance predicates under attrs
            short = p.rsplit("/", 1)[-1].rsplit("#", 1)[-1]
            entities[s].setdefault("attrs", {})[short] = o

    entity_docs = []
    for uri, doc in entities.items():
        doc["_id"] = uri
        doc["id"] = uri
        entity_docs.append(doc)

    for i, rel in enumerate(relationships, start=1):
        rel["_id"] = f"rel:{i}"

    with ENTITIES_OUT.open("w") as f:
        for doc in entity_docs:
            f.write(json.dumps(doc) + "\n")
    with RELS_OUT.open("w") as f:
        for doc in relationships:
            f.write(json.dumps(doc) + "\n")

    print(f"Wrote {len(entity_docs)} entities -> {ENTITIES_OUT}")
    print(f"Wrote {len(relationships)} relationships -> {RELS_OUT}")

if __name__ == "__main__":
    main()
