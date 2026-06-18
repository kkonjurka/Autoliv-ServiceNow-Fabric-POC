# Jayne — History

## Project Context
- **Project:** Autoliv ServiceNow to Microsoft Fabric POC
- **Stack:** Azure AI Search, vector retrieval
- **User:** @kkonjuramicrosoft

## Learnings

### 2026-06-17 — Retrieval Layer Design Complete

**Delivered:** docs/RETRIEVAL_DESIGN.md + decision document

**Key Design Decisions:**
1. **Three-index architecture** (KB articles, incident content, attachments) for clean separation of concerns and targeted search patterns
2. **Hybrid search** (BM25 keyword + vector embeddings) balances exact phrase matching with semantic understanding of synonyms/intent
3. **Azure AI Search + Azure OpenAI embeddings** for native hybrid support and seamless integration
4. **Signal-based ranking** boosts results for quick resolutions, zero reopens, and popular KB articles
5. **Metadata filtering** applied post-search to reduce false negatives while maintaining precision
6. **No binary content in indexes** — only searchable text and metadata (keeps POC lightweight)

**Observations:**
- Hybrid search consistently outperforms keyword-only in retrieval quality
- Three indexes reduce maintenance burden vs. single monolithic index (can update KB independently from incidents)
- Signal boosting makes ranking interpretable and tunable without resorting to pure ML ranking models
- Grounding with source URLs is non-negotiable for trustworthiness in IT support workflows

**Integration Points:**
- Foundry orchestrator routes user queries to retrieval system based on intent
- Results include source URLs, metadata, and match rationale for answer composition
- Retrieval system is separate from Fabric Data Agent (unstructured vs. structured data)

**Next Handoff:** Implementation team (indexing scripts, search API, orchestrator integration)
