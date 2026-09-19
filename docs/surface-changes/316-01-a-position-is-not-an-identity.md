# 316-01 — a position is not an identity

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `592ade1b`
(*fix(assembly): D-IMPL-316 — a position is not an identity (CP04C-F-01)*, 2026-09-10), which
shipped without a surface-change fragment. The measurement that opened it: a URI was
`entity_class://content_hash({payload_key: value})`, so the payload key's name was inside the
identity; endpoint selection reads two payload fields through two rules, so the same company
hashed differently in each position — three real nodes became five entities, and a mutual pair
became four. This fragment claims exactly the one public name `592ade1b` reshaped.

## ccf.assembly.worker.EntityResolutionRule

- Surface: ccf.assembly.worker.EntityResolutionRule
- Public surface: true
- Change type: reshaped
- Before: `entity_class`, `identity_keys`, `attribute_keys` — each declared identity key was read from the payload field of the same name, so a rule whose source names the value positionally (`parent_uri`, `child_uri`) put the field's name into the identity
- After: adds `identity_sources: Mapping[str, str]` — declared identity key → the payload field that supplies its value; defaulted to empty and hash-transparent, so a rule declaring nothing reads and hashes as it did. A remap of a key the rule does not declare as identity is refused at validation rather than ignored
- Why: `D-IMPL-316` (`592ade1b`) — this field changes where an identity value is read from; it does not change what constitutes identity. The declared key is still what is hashed
- Migration: none for a rule that reads each identity key from a field of the same name; a rule reading a value positionally declares the mapping, and the same value then mints the same URI from either position
