# Project TODO List

## Document Parsing
- [ ] Implement summarization for full text of documents that overwhelm the model's context (`src/app/services/document_service.py`)

## Orchestration & Routing
- [ ] Implement routing pipeline in `src/app/chat/orchestrator.py` (Semantic routing + LLM fallback)
- [ ] Integrate embedding service in `src/app/chat/orchestrator.py` for semantic routing
- [ ] Implement `RouterAgent.run()` in `src/app/chat/agents/router_agent.py`

## Agent Implementation
- [ ] Add tools for document access in `AbstractAgent` (`src/app/chat/agents/abstract_agent.py`)
- [ ] Implement `PlannerAgent` in `src/app/chat/agents/abstract_agent.py`
- [ ] Implement `ChapterWriterAgent` in `src/app/chat/agents/abstract_agent.py`
- [ ] Implement `ChapterSummarizerAgent` in `src/app/chat/agents/abstract_agent.py`
- [ ] Implement full iterative pipeline in `AbstractAgent` (`src/app/chat/agents/abstract_agent.py`)
- [ ] Implement `SlidePlannerAgent` in `src/app/chat/agents/presentation_agent.py`
- [ ] Implement `SliderAgent` in `src/app/chat/agents/presentation_agent.py`
- [ ] Implement `SlideSummarizerAgent` in `src/app/chat/agents/presentation_agent.py`
- [ ] Implement full presentation pipeline in `PresentationAgent` (`src/app/chat/agents/presentation_agent.py`)

## Graph & State Machine
- [ ] Implement nodes and edges in `src/app/chat/graph.py` (LangGraph state machine)
- [ ] Implement `build_agent_graph()` in `src/app/chat/graph.py`
