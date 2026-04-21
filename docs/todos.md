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