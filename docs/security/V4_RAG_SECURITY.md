# ZONATA V4 — KNOWLEDGE GATEWAY & PRE-RETRIEVAL RAG SECURITY
**Pre-Retrieval Authorization, Granular Citation Lineage, & Zero Post-Filter Leakage**

## 1. The Pre-Retrieval Authorization Paradigm
Standard naive RAG systems retrieve top-K semantic hits across all documents and filter out unauthorized items in application memory. This creates severe vulnerability to memory dumps, prompt injection, and timing side-channels.

**ZONATA V4 Enforces Pre-Retrieval Authorization**:
- Authorization boundaries (Tenant ID, Company ID, Clearance Level, Department ACL, Active Deletion State) are compiled directly into the database query (`core/knowledge_gateway.py`).
- Unauthorized chunks are **never fetched from disk**, never loaded into RAM, and never passed to the LLM context window.

```sql
SELECT c.chunk_id, c.object_id, c.text_content, c.content_hash,
       c.classification_level, c.source_system, c.allowed_departments,
       c.allowed_roles, c.allowed_identities, d.title
FROM knowledge_index_chunks c
JOIN corporate_data_objects d ON c.object_id = d.object_id
WHERE c.tenant_id = ?
  AND c.company_id = ?
  AND c.deletion_state = 'ACTIVE'
  AND d.deletion_state = 'ACTIVE'
  AND c.classification_level IN (?, ?, ...)
```

---

## 2. Granular Citation & Provenance Lineage
Every chunk returned by `KnowledgeGateway.retrieve_permission_aware()` contains:
- `chunk_id`: Unique chunk identifier.
- `object_id`: Source document reference.
- `content_hash`: Cryptographic hash verifying chunk content has not been tampered with.
- `classification_level`: Inherited classification.
- Lineage is recorded in `data_lineage_graph`, binding retrieved chunks to the AI Employee's response.
