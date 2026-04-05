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

## Admin API & Data Management

### `src/app/api/routers/admin/staff.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on staff upload | ❌ Not started | Line 35: `# TODO: generate embeddings for each chunk here before bulk indexing.` After file upload and chunking, need to call `EmbeddingService` to create vectors before indexing in ES. |
| Re-embed on staff updates | ❌ Not started | Line 76: `# TODO: re-embed changed text fields before updating.` When staff record is updated, regenerate embeddings for affected chunks. |

**Context:** Staff endpoint handles bulk upload via Excel → text chunks → Elasticsearch. Embedding step is missing.

---

### `src/app/api/routers/admin/events.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on events upload | ❌ Not started | Line 33: `# TODO:` likely same as staff - need to embed event descriptions before indexing. |
| Re-embed on events updates | ❌ Not started | Line 79: `# TODO: re-embed changed text fields.` When events are modified, regenerate embeddings. |

**Note:** Events admin router likely parallels staff router; embedding step pending.

---

## File Processing

### `src/app/services/file_service.py`

| Task | Status | Details |
|------|--------|---------|
| Generate embeddings during file processing | ❌ Not started | Line 146: `# TODO: generate embeddings for each chunk here before bulk indexing.` After chunking uploaded files, need to call `EmbeddingService` and store vectors with chunks. |

**Impact:** Without this, RAG search for uploaded materials (Q&A agent) cannot perform vector search; only BM25 keyword search works.

---

## Embedding Service

### `src/app/services/embedding_service.py`

| Task | Status | Details |
|------|--------|---------|
| Consider async wrapper | ⚠️ Optional | Line 67 comment notes sentence-transformers is synchronous; running in thread pool would be ideal for async contexts. Currently each call blocks event loop. May need `asyncio.to_thread()` or move to separate service. |

**Current state:** Service works but is synchronous; acceptable for low load but could block async I/O under concurrency.

---

## Elasticsearch Indexing

### `src/app/elastic/index_manager.py`

| Task | Status | Details |
|------|--------|---------|
| Fix `room` field mapping type | ⚠️ Data bug | Line 35: `"room": {"type": "integer"}, # TODO: mistake: room must be string for 619a and similar.` For staff data, room numbers like "619a" are strings, not integers. Mapping needs correction and reindexing. |

**Impact:** Staff search with room queries may fail or produce incorrect results.

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

**Note:** Abstract agent is the only agent that uses subagents in an iterative multi-stage pipeline. Currently non-functional.

---

## Graph/State Machine

### `src/app/chat/graph.py`

| Task | Status | Details |
|------|--------|---------|
| Implement LangGraph state machine | ❌ Not started | Entire file is stub. `build_agent_graph()` raises `NotImplementedError`. Planned nodes: `pii_masker_node`, `router_node`, agent nodes (`support_node`, `events_node`, etc.), summarizer node. |

**Note:** LangGraph integration is future work; orchestrator currently used directly.

---

## Admin API & Data Management

### `src/app/api/routers/admin/staff.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on staff upload | ❌ Not started | Line 35: `# TODO: generate embeddings for each chunk here before bulk indexing.` After file upload and chunking, need to call `EmbeddingService` to create vectors before indexing in ES. |
| Re-embed on staff updates | ❌ Not started | Line 76: `# TODO: re-embed changed text fields before updating.` When staff record is updated, regenerate embeddings for affected chunks. |

**Context:** Staff endpoint handles bulk upload via Excel → text chunks → Elasticsearch. Embedding step is missing.

---

### `src/app/api/routers/admin/events.py`

| Task | Status | Details |
|------|--------|---------|
| Generate vectors on events upload | ❌ Not started | Line 33: `# TODO:` likely same as staff - need to embed event descriptions before indexing. |
| Re-embed on events updates | ❌ Not started | Line 79: `# TODO: re-embed changed text fields.` When events are modified, regenerate embeddings. |

**Note:** Events admin router likely parallels staff router; embedding step pending.

---

## File Processing

### `src/app/services/file_service.py`

| Task | Status | Details |
|------|--------|---------|
| Generate embeddings during file processing | ❌ Not started | Line 146: `# TODO: generate embeddings for each chunk here before bulk indexing.` After chunking uploaded files, need to call `EmbeddingService` and store vectors with chunks. |

**Impact:** Without this, RAG search for uploaded materials (Q&A agent) cannot perform vector search; only BM25 keyword search works.

---

## Embedding Service

### `src/app/services/embedding_service.py`

| Task | Status | Details |
|------|--------|---------|
| Consider async wrapper | ⚠️ Optional | Line 67 comment notes sentence-transformers is synchronous; running in thread pool would be ideal for async contexts. Currently each call blocks event loop. May need `asyncio.to_thread()` or move to separate service. |

**Current state:** Service works but is synchronous; acceptable for low load but could block async I/O under concurrency.

---

## Elasticsearch Indexing

### `src/app/elastic/index_manager.py`

| Task | Status | Details |
|------|--------|---------|
| Fix `room` field mapping type | ⚠️ Data bug | Line 35: `"room": {"type": "integer"}, # TODO: mistake: room must be string for 619a and similar.` For staff data, room numbers like "619a" are strings, not integers. Mapping needs correction and reindexing. |

**Impact:** Staff search with room queries may fail or produce incorrect results.

---

## Test UI

### `docs/features/test_ui.md`

| Task | Status | Details |
|------|--------|---------|
| Document debug mode requirement | ✅ Done | Explained in doc: test UI only runs with `DEBUG=True` as security gate. |
| Document agent/model selection | ✅ Done | Dropdowns implemented and documented. |
| Document starter messages | ✅ Done | Three starter prompts for quick testing. |

**Note:** Test UI itself is functional (`src/app/chat/test_ui.py`), but documentation is up to date.

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

## Configuration

### `src/app/config.py`

| Task | Status | Details |
|------|--------|---------|
| Verify all required env vars documented | ✅ Done | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `DEBUG` documented. |

---

## Logging

### `src/app/logging_config.py`

| Task | Status | Details |
|------|--------|---------|
| Confirm LLM logs separation | ✅ Done | `logs/llm.log` filters LLM-specific logs; configured at app startup. |
| Consider log rotation | ⚠️ Optional | Currently no size-based rotation; may need `RotatingFileHandler` for long-running deployments. |

---

## General Notes

### Priority Levels

**🔴 Critical (blocks core functionality):**
1. Routing implementation - system cannot intelligently route queries without this.
2. File processing embeddings - Q&A agent cannot perform vector search on uploaded docs.
3. Admin API embedding generation - staff/events indexing incomplete.

**🟡 Important (improves quality/resilience):**
4. Abstract agent pipeline - complex use case currently stubbed.
5. Elasticsearch `room` mapping fix - data quality issue.
6. Embedding service async - performance optimization for high concurrency.

**🟢 Nice-to-have (future enhancements):**
7. LangGraph integration - better orchestration, not essential.
8. Observability (Langfuse) - monitoring, tracing.
9. Caching layer - cost/latency optimization.
10. Cost optimization - smart model routing.

---

### Implementation Order Recommendation

1. **Orchestrator routing** - enables smarter agent selection, reduces wrong-agent errors.
2. **File processing embeddings** - makes Q&A agent actually useful for RAG.
3. **Admin API embeddings** - completes staff/events search pipelines.
4. **Abstract agent** - fulfills promised abstract generation capability.
5. **Elasticsearch mapping fix** - data integrity; may require reindex.

---

### Metrics for Completion

- [ ] `Orchestrator._route()` returns correct agent types without raising `NotImplementedError`
- [ ] `_embed()` returns embedding vectors for test queries
- [ ] `_llm_route()` executes and returns an `AgentType`
- [ ] Staff and Events admin endpoints generate embeddings for uploaded data
- [ ] File upload processing generates embeddings for each chunk
- [ ] `AbstractAgent.run()` executes full iterative pipeline (planner → writer → summarizer loop)
- [ ] `room` field in staff ES index is `keyword` or `text` type (not `integer`)
- [ ] All integration tests pass with real LLM and embedding services

---

**Last updated:** 2026-04-05  
**Branch:** `feature/agentic_tools`
