# TODO List

Comprehensive list of unfinished work, known limitations, and improvement opportunities in the codebase.

## Orchestration & Routing

### `src/app/chat/orchestrator.py`

| Task | Status | Details |
|------|--------|---------|
| Implement routing pipeline | ❌ Not started | `_route()` method raises `NotImplementedError`. Planned: embedding-based semantic routing + LLM fallback for ambiguous queries. Current: only keyword-based fallback (not implemented). |
| Integrate embedding service | ❌ Not started | `_embed()` method stub. Should use OpenRouter embeddings (e.g., `text-embedding-3-small`) via LangChain. |
| LLM-based routing fallback | ❌ Not started | `_llm_route()` method stub. For cases where semantic routing confidence is low, use small fast model to pick best agent. |

**Routing Architecture (from docstring):**
- Stage 1: Semantic routing (embed query → cosine similarity vs agent examples in Postgres)
- Stage 2: LLM fallback when top-2 agents are too close
- Current state: Both stages are stubs; no routing implemented

**Note:** There's also a `RouterAgent` in `src/app/chat/agents/router_agent.py` that is meant to handle routing but also unimplemented.

---

## Agent Implementation

### `src/app/chat/agents/abstract_agent.py`

| Task | Status | Details |
|------|--------|---------|
| Add document access tools | ⚠️ Partial | `tools = []` placeholder. Abstract agent needs tools to fetch source documents from Elasticsearch/DB. |
| Implement PlannerAgent | ❌ Not started | `PlannerAgent.run()` raises `NotImplementedError`. Should create chapter outline from topic. |
| Implement ChapterWriterAgent | ❌ Not started | `ChapterWriterAgent.run()` raises `NotImplementedError`. Should write individual chapters sequentially. |
| Implement ChapterSummarizerAgent | ❌ Not started | `ChapterSummarizerAgent.run()` raises `NotImplementedError`. Should condense earlier chapters for context management. |
| Implement iterative pipeline | ⚠️ Partial | `AbstractAgent.run()` has placeholder `_call_llm()` with stub response. Full pipeline: planner → writer loop with periodic summarization. |

---

### `src/app/chat/agents/presentation_agent.py`

| Task | Status | Details |
|------|--------|---------|
| Implement SlidePlannerAgent | ❌ Not started | `SlidePlannerAgent.run()` raises `NotImplementedError`. Should create slide outline/structure. |
| Implement SliderAgent | ❌ Not started | `SliderAgent.run()` raises `NotImplementedError`. Should create individual slides iteratively using previous summaries. |
| Implement SlideSummarizerAgent | ❌ Not started | `SlideSummarizerAgent.run()` raises `NotImplementedError`. Should summarize earlier slides for context management. |
| Implement full presentation pipeline | ⚠️ Partial | `PresentationAgent.run()` calls `_call_llm()` but doesn't orchestrate subagents. Full pipeline: planner → slider loop with periodic summarization. |

---

### `src/app/chat/agents/router_agent.py`

| Task | Status | Details |
|------|--------|---------|
| Implement RouterAgent.run() | ❌ Not started | Entire method raises `NotImplementedError`. Should perform semantic routing + LLM fallback (similar to Orchestrator._route()). |

---

## Graph/State Machine

### `src/app/chat/graph.py`

| Task | Status | Details |
|------|--------|---------|
| Implement LangGraph state machine | ❌ Not started | Entire file is stub. `build_agent_graph()` raises `NotImplementedError`. Planned nodes: `pii_masker_node`, `router_node`, agent nodes (`support_node`, `events_node`, etc.), summarizer node. |

**Note:** LangGraph integration is future work; orchestrator currently used directly.

---

## Admin API & Data Management ✅

### `src/app/api/routers/admin/staff.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on staff upload | ✅ Complete | Implemented: on create, calls `embedder.embed_text()` for `competences` and `description` (if non-empty) and stores vectors in `*_vector` fields. |
| Re-embed on staff updates | ✅ Complete | Implemented: on PATCH, if `competences` or `description` fields are being updated, regenerates embeddings for the new text. |
| Fix `room` field type | ✅ Complete | Changed from `int` to `str` in ES mapping and all Pydantic schemas to support values like "619a". |

---

### `src/app/api/routers/admin/events.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on events upload | ✅ Complete | Implemented: on create, calls `embedder.embed_text()` for `description` and `participant_requirements` (if non-empty). |
| Re-embed on events updates | ✅ Complete | Implemented: on PATCH, if text fields are updated, regenerates embeddings. |
| Fix `room` field type | N/A | Events don't have a `room` field. |

---

## File Processing ✅

### `src/app/services/file_service.py`

| Task | Status | Details |
|------|--------|---------|
| Generate embeddings during file processing | ✅ Complete | Implemented: after chunking, calls `embedder.embed_batch(chunks)` to generate vectors for all chunks, then indexes with vectors. |

**Impact:** Q&A agent can now perform vector search on uploaded materials (hybrid BM25 + kNN).

---

## Embedding Service ✅

### `src/app/services/embedding_service.py`

| Task | Status | Details |
|------|--------|---------|
| Async wrapper (thread pool) | ✅ Complete | Updated: uses `asyncio.get_running_loop().run_in_executor()` to run synchronous `sentence-transformers` in thread pool, preventing event loop blocking. Added `get_embedding_service()` singleton for reuse. |
| Tune batch sizes for performance | ⚠️ Optional | Could experiment with batch size for `model.encode()` to optimize memory/throughput trade-off. Current: all chunks at once (may use lots of RAM for large files). Consider chunking into smaller batches if needed. |

---

## Elasticsearch Indexing ✅

### `src/app/elastic/index_manager.py`

| Task | Status | Details |
|------|--------|---------|
| Fix `room` field mapping type | ✅ Complete | Changed from `integer` to `keyword` to support room numbers like "619a", "A-101", etc. Note: existing index will need to be recreated/reindexed if already created. |

**Impact:** Staff search with room queries now works correctly for alphanumeric room identifiers.

---

## Design Documents

### `docs/design/llm_comparison.md`

| Task | Status | Details |
|------|--------|---------|
| Keep updated with model performance | 🔄 Ongoing | Contains performance measurements and model recommendations. May need updates as OpenRouter model lineup changes. |
| Clarify fallback strategy per use case | ✅ Done | Final verdict section specifies primary/fallback models for routing, RAG agents, summarizer, abstract/slide agents. |

---

### `docs/design/architecture.md`

| Task | Status | Details |
|------|--------|---------|
| Document LangGraph integration plan | ⚠️ Partial | Mentions LangGraph as future enhancement but no detailed design. |
| Document observability stack | ⚠️ Partial | Mentions Langfuse but no integration details. |
| Document caching strategy | ⚠️ Partial | Mentions Redis caching as future work. |
| Document cost optimization | ⚠️ Partial | Mentions smart routing but no implementation plan. |

---

## Test UI

### `docs/features/test_ui.md`

| Task | Status | Details |
|------|--------|---------|
| Document debug mode requirement | ✅ Done | Explained in doc: test UI only runs with `DEBUG=True` as security gate. |
| Document agent/model selection | ✅ Done | Dropdowns implemented and documented. |
| Document starter messages | ✅ Done | Three starter prompts for quick testing. |

**Note:** Test UI itself is functional (`src/app/chat/test_ui.py`), but Chainlit v2.5.0 API updates complete.

---

## General Notes

### Priority Levels

**🔴 Critical (blocks core functionality):**
1. Routing implementation - system cannot intelligently route queries without this.
2. Abstract agent pipeline - complex use case currently stubbed.
3. Presentation agent pipeline - complex use case currently stubbed.

**🟡 Important (improves quality/resilience):**
4. LangGraph state machine - better orchestration (future).
5. Reindex Elasticsearch with corrected `room` mapping (if already created).

**🟢 Nice-to-have (future enhancements):**
6. Observability (Langfuse) - monitoring, tracing.
7. Caching layer - cost/latency optimization.
8. Cost optimization - smart model routing based on query complexity.

---

### Implementation Order Recommendation

1. ✅ Admin API & Data Management (embeddings) - **JUST COMPLETED**
   - Staff and Events admin endpoints now generate embeddings on upload/update
   - File processing pipeline generates embeddings for uploaded documents
   - Elasticsearch mapping fixed

2. **Orchestrator routing** - next priority to enable smarter agent selection

3. **Abstract & Presentation agents** - complete iterative subagent pipelines

4. **Reindex** Elasticsearch with corrected `room` mapping (if needed)

5. LangGraph integration - optional but improves modularity

---

### Metrics for Completion

- [x] Staff admin: embeddings generated on create/update
- [x] Events admin: embeddings generated on create/update
- [x] File processing: embeddings generated for all chunks
- [x] EmbeddingService: async via thread pool
- [x] Elasticsearch: `room` field mapping fixed
- [ ] `Orchestrator._route()` returns correct agent types without raising `NotImplementedError`
- [ ] `_embed()` returns embedding vectors for test queries
- [ ] `_llm_route()` executes and returns an `AgentType`
- [ ] `AbstractAgent.run()` executes full iterative pipeline (planner → writer → summarizer)
- [ ] `PresentationAgent` subagents (SlidePlanner, Slider, SlideSummarizer) implemented
- [ ] All integration tests pass with real LLM and embedding services

---

**Last updated:** 2026-04-05  
**Branch:** `feature/agentic_tools`  
**Completed:** Admin API & Data Management (embedding integration)
