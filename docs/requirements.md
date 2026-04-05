# Requirements

This document contains requirements to parts of the system to be met at the end of the development. The document is WIP, so must be updated on-the-go and is not yet completed.

## LLM

LLMs are being used by API here, without any on-prem usage, as it is not the case here, due to data being not so privacy-sensitive and complications of using on-prem solutions (GPU infra and low model intelligence).

Project assumes usage of OpenRouter as main provider, yet support modularity for easy drop-in replacement just in case.

Client should support:
- Selecting different models;
- Model fallback;
- Tool calling (maybe even mcp servers);
- Response streaming;
- Structured output.

All of that should be in easy, readable, upgradable, modular way with best practices application.

All of that may use LangChain or custom communication with the client, requires more thought and comparison.

## Embeddings

The embeddings should be fully configurable and modular for easy swap.

The base class implements the init and embed methods.

Config specifies the dimension for ES index.

The provider class extends the base class to provide the functional for embeddings. The baseline is sentence transformers provider, where default is bge-m3 model with sentence-transformers as a library.

## ES Repository

ES is used here storage of all the data RAG needs. Interaction between agents and the knowledge base will be done in form of tools, that should call the repository methods and other code necessary for retrieving and transforming the data.

The repository tools must accept the query and some additional parameters for filtering.

The logic for constructing the query must stay inside the repository methods.

However the logic for specifying the query parameters (e. g. event dates, staff person's room, etc.) should be in the higher level code inside tools themselves.

__IMPORTANT NOTE__: Retrieval pipelines do not run with the incoming query (before passing to LLM). The llm agent decides on which query to use in which tool call all by itself and it is the only way to retrieve data via RAG for the agent.

## Tools

Tools for each agent must go like this

__IMPORTANT NOTE__: Check on optional parameters support by each model.

### Events Agent

- `get_events_documents(query: str, ...)` — tool for retrieval of relevant documents by query.

### Staff Agent

- `get_staff_documents(query: str, ...)` — tool for retrieval of relevant documents by query.

### QA Agent

- `get_materials_fragments(query: str, ...)` — tool for retrieval of document fragments by query.

### Summarizer

- `get_materials_fragments(query: str, ...)` — tool for retrieval of document fragments by query.

### Chapter Writer

- `get_materials_fragments(query: str, ...)` — tool for retrieval of document fragments by query.

### Slider

- `get_materials_fragments(query: str, ...)` — tool for retrieval of document fragments by query.

Overall the tool pool will consist of:
- `get_events_documents(query: str, bonus_amount: Optional[int], date_from: Optional[str], date_to: Optional[str], k=k)` — tool for retrieval of relevant event documents by query.
- `get_staff_documents(query: str, position: Optional[str], room: Optional[str], department: Optional[str], name: Optional[str], k=k)` — tool for retrieval of relevant staff documents by query.
- `get_materials_fragments(query: str, return_chunks=False, k=k)` — tool for retrieval of document fragments by query.

## Tool Pipelines

__Note__: overall notes on requirements for now:
- No reranking;
- k is passed alongside each tool as an argument with default value of 3 (5 for materials).

__Each of the tools follow similar pipeline:__

### Pipeline for `Staff Index`

1. Embed the `query` into vector embeddings (using `sentence-transformers`/`transformers`/`spacy`);
2. Construct the ES search query with:
- cosine similarity search and keyword fuzzy match in `competences`, `description`;
- filter by matches in `position`, `room`, `department`, `name` based on extra arguments;
3. _TBD, Optional:_ ~~rerank the results with reranker (bge reranker or similar), takes time and resources;~~
4. Provide the full top-k documents.

### Pipeline for `Events Index`

1. Embed the `query` into vector embeddings (using `sentence-transformers`/`transformers`/`spacy`);
2. Construct the ES search query with:
- cosine similarity search and keyword fuzzy match in `name`, `participant_requirements`, `description`;
- filter by only actual events (`today` is before `date_from`) OR filter by matches in `date_from`, `date_to`;
- filter by equals or more `bonus_amount` if supplied;
3. _TBD, Optional:_ ~~rerank the results with reranker (bge reranker or similar), takes time and resources;~~
4. Provide the full top-k documents.

### Pipeline for `Materials Index`

1. Embed the `query` into vector embeddings (using `sentence-transformers`/`transformers`/`spacy`);
2. Construct the ES search query with:
- cosine similarity search and keyword fuzzy match in `chunk_text`;
- filter by `document_id` that in the context;
3. _TBD, Optional:_ ~~rerank the results with reranker (bge reranker or similar), takes time and resources;~~
4. Provide the full top-k documents OR just top-k chunks based on `return_chunks`, _TODO: decide or leave as an argument_:
- If `return_chunks=True`, return the chunks from the retrieval process;
- If `return_chunks=False`, return full documents from the storage by `document_id` in the chunks.


## Agent Prompting 

### Prompts

Prompts are loaded on init for each agent by specifying prompt name. All of the prompts are stored under src/prompts/...

Agent's prompts must be named according to the prompt name and subagents must lie under prompts/parnet_agent/subagent_prompt.txt.

### History

Depending on the agent, chat history is passed up to N messages or not passed at all, relying on the formating prompt or pasting the input as user message right after system prompt.

- __Router Agent__ chat history of N messages;
- __Support Agent__ chat history of N messages;
- __Events Agent__ chat history of N messages;
- __Staff Agent__ chat history of N messages;
- __QA Agent__ chat history of N messages;
- __Summarizer Agent__ chat history of N messages;
- __Abstract Agent__:
    - __Planner Agent__ chat history of N messages;
    - __Chapter Writer Agent__ No history, just previous chapters and plan in the prompt;
    - __Chapter Summarizer Agent__ No history, just previous chapters and plan in the prompt;
- __Presentation Agent__:
    - __Planner Agent__ chat history of N messages;
    - __Slider Agent__ No history, just previous slides and plan in the prompt;
    - __Slide Summarizer Agent__ No history, just previous slides and plan in the prompt;
