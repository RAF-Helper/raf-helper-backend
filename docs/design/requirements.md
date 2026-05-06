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

## Tool integration

Important point for material tools is to be called with high abstraction level for the agent.

This means, that the agent explicitly calls only `get_materials_fragments(query, return_chunks, k)` and the rest is automatically controlled within the system.

So chat settings that determine context are automatically determined in the tool call.

### Basic tool requirements:
- Material tools only require these parameters explicitly:
  - query: text request to search for;
  - return_chunks: whether to return chunk fragments or the whole document;
  - k: amount of chunks to consider in the final ranging;
- Information of the materials available is handled by the system, e. g. documents to search in or websearch usage;
- Websearch is done separately via Tavily service that calls the api with the same queries from the tools;
- `Staff` and `Events` tools require queries to be searched upon in all vectorized fields and explicit parameters to filter by.


The final implementation is to be decided, but overall the agent must only think about `query`, `chunks`, `k`, while chat environment determines which documents to search in.


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


## Admin panel

Admin UI must be separately available as an understandable frontend UI for population of events and staff indexes by university staff.

__UI Implementation choices__:
- gradio/streamlit UI (for development ONLY);
- Flutter web UI;
- Simple JS/TS web UI (React, Vuejs, etc.).

### Core functionality
1. List the available documents with all of the fields displayed and simple search filtering by name;
2. Add new documents into indexes with specifying all of the fields;
3. Update existing documents;
4. Delete specific documents.

For the MVP the streamlit implementation is enough.
The exact implementation doesn't matter that much but the core funcionality must be done.

The admin panel implies readyness of the index endpoints and embedding/reembedding working properly within them.


## Document parsing

Parsing of uploaded files is needed to extract main content for search of necessary facts and it's structure metadata for appropriate references.

### Strategy

The strategy decision must incorporate these requirements:
- Content extraction covers all of the textual information that can be necessary for retrieval;
- Structural metadata (titles, chapters, points, page numbers, etc.) as levels of the documents structure are extracted and stored as well, to provide for the references ability;
- Main text contents are split into chunks and later embedded for semantic search capabilities;
- All of that is done for various formats and takes into account their differences and nuances.

Chunking strategy is:
- Separation by levels of structural metadata (e. g. by chapters, points, etc. But NOT page numbers);
- Inside the lowest level (e. g. chapter for documents with chapters only or points for documents with chapters, articles and points) the contents are divided with limit on max words in the chunk, taking the words into account;
- Each chunk overlaps with the neighbouring chunks.

Overlap and chunks size are decided in the config (`app.config`) and may differ for slides as they are too different of a format.

The page number must refer to the page that holds the start of the chunk.

The strategy of parsing structure is up to implementation and may be different for any type of document but universal for all kinds of educational material of this extension. Basic ideas include parsing based on style (headings), font size, font boldness. For slides it is, for certain, different and relies on similar slide structure or title slides that are common in most presentations, but may also incorporate similar logic.

[!] LLM-based parsing is too expensive for our scope, so it won't be used.

### Implementation

Implementation must consist of a base class `BaseParser` that defines:
- abstract method `parse(artifact: T) -> Document`;
- abstarct method `load(filename: str) -> T` that will be used to read and extract the contents of the files in any format required for the parse;
- `parse` relies on `load` to extract data from the artifact it produces (whatever is required by the used library). Here `T` is type of the artifact required (may be `Any`).

Requirements for the implementation
- Each class is defined as `XParser(BaseParser)` and overloads the methods above using any libraries and includes any amount of additional methods needed;
- Code lies under `src/app/documents/` with `base.py` and `x.py`, `y.py`, etc. files for each parser;
- Additionaly, `DocumentService` exists to automatically select needed parser based on documents extension, acting as a factory pattern;
- For chunking, `Chunker` or `ChunkingService` exists that accepts string text and returns chunks that are later contructed into `DocumentChunks` in parsers.

### Documents

In minimum, parsers must cover:
- Word documents: .docx, .doc and any older comaptible ones;
- PDFs: .pdf of any format with table, image parsing (ocr), _TODO: Implement image embeddings and captions_;
- Slide presentations: .pptx, .ppt and any older compatible ones;
- Markdown: .md;
- Simple marked text: .rtf and similar;
- Pure text files _also default fallback_: .txt.

If file format can be determined without extension by looking at the contents/header this must be implemented in additional `classify(filename)` function that returns which format it actually is inside the service.


### Models

The pydantic model `Document` must represent the parsed document and consist of:
- `document_chunks`: `list[DocumentChunk]`, with chunks of the main content of the document;
- `id`: `uuid`, autogenerated id of the document;
- `name`: `str`, name of the file/main title;
- `filename`: `str`, name of the file;
- `format`: `enum`, represents the format/extension of the document and used parser;

And `DocumentChunk` model that contains:
- `content`: textual content of the chunks;
- `level1`: title of the first level (e. g. chapter) in strucure;
- `level2`: title of the second level (e. g. article) in strucure;
- `level3`: title of the second level (e. g. point) in strucure;
- `metadata`: json of the extracted structure for the chunk.

Example of metadata:
```json
{
    "level1": "Introduction to Fourier transform",
    "level2": "Application of FFT in audio processing",
    "level3": null,
    "chapter": "Introduction to Fourier transform",
    "article": "Application of FFT in audio processing",
    "page_number": 36
}
```

Therefore it includes main levels and any additional info needed.

The null values are determined by the parsing implementation. Chapter/articles can be extracted using regex and any additional methods. Must support Russian, Belorusan and English.

### Repository

Implement new repository (`DocumentRepository`) that works with elasticsearch and postgres repositories and connects embedding service to retrieve and injest documents.

We need 2 repos, because elasticsearch must include chunks with:
- `document_id`, showing which document/file it belongs;
- `chunk_text`, that stores the text contents of the chunk;
- `chunk_embedding`, that stores vector representation of the content;
- `chunk_reference_level_1`, that stores the title of the heading/chapter/unit at level 1 (the highest);
- `chunk_reference_level_1_embedding`, that stores vector representation of the corresponding level title;
- `chunk_reference_level_2`, that stores the title of the heading/chapter/unit at level 2;
- `chunk_reference_level_2_embedding`, that stores vector representation of the corresponding level title;
- `chunk_reference_level_3`, that stores the title of the heading/chapter/unit at level 3 (the lowest);
- `chunk_reference_level_3_embedding`, that stores vector representation of the corresponding level title;
- `chunk_reference_metadata`, representing any references we extracted (chapters, pages, etc. as well as levels).

In postgres we store:
- `document_id`, the same internal uuid to identify it;
- `filepath`, to show where it is stored on the server;
- `filename`, initial filename as sent by the user;
- `name`, the same as in model;
- `format`, the same as in model.

The files are stored on the server in the `./storage/materials/{uuid}.{extension}` path.

Search pipeline uses elasticsearch repository and implements vector embedding similarity search on chunk embedding and heading embeddings, as well as fulltext fuzzy search matching (including `chunk_reference_metadata` if possible). Combining them to score the document chunks in the end and return top k of them.

_TODO: add reranker, but, for now, just this pipeline_

If `return_chunks` from the tool call is `false` than the whole document content must be returned. As duplicate storage is not good, it needs to reparse the document again to return it's contents.

__If current schemas/mappings require modifications, then appropriate migrations must be made__

### Document service

The document service `DocumentService` implements full parsing and search pipeline, working with embedding service and document repository.

Must implement:
- parsing method with auto selection of appropriate parser and returning of `Document`;
- injestion and retrival methods for embedding, injestion and search of the documents based on query.

It is responsible for all of the high level functionality, while repository only works with uploading documents and searching them based on ready query and embeddings.

### Agentic integration

Inside tools the appropriate call to document service must be called, and after that it is dumped into json and united with web search (if it was used) before passing it into LLM.

### Implementation Steps

For proper testing and incremental implementation of the system it is advised to use these steps:
1. Databases (postgresql and es) preparation, making migrations and adjusting their repositories (at `app.repositores`);
2. Implementing document models and create the document repository with full search pipeline;
3. Implementing base and basic text parsers for initial testing of the whole system;
4. Implement chunking service and integrate into existing parsers;
5. Developing the document service with proper injestion and retrieval and introducing full pipeline into the agentic tools;
6. Adjusting endpoints and routers for proper document upload and add temporary test search endpoint with full pipeline as in agentic tools;
7. Implementing document upload and search UI with streamlit for testing (under src/test_ui/materials) using the backend's API and not direct calls to services;
8. Adjust search tools for agents to implement new logic for documents retrieval according to the requirements;
9. Engineer the rest of the parsers for each extension;
10. Documenting everything and perform heavy testing on real data.


## Routing

### Idea and pipeline

The system should implement robust routing that routes requests properly with chat history in mind.

The routing in multiagentic system is done via Orchestrator agent that processes the user's request with N last messages and determines where to route the request.

### Available routes

Possible routing outcomes (routes):
- `support`: Support agent, all of the questions regatding how to use the app and all of the other unknown questions;
- `summary`: Summarizer agent, User requests summary of some document(s) or some topic(s);
- `qa`: QA agent, user asked some kind of question that is related to the materials or educational one that requires search;
- `events`: Events agent, Questions regarding upcoming events and bonuses for participating in them;
- `staff`: Staff agent, questions about staff;
- `ar`: Returns command to open AR module, questions about getting to some room/place on the faculty;
- `abstract`: Abstract agent, user asked to construct an abstract for the given topic;
- `slides`: Slides (Presentation) agent, user asked to make a presentation on the topic.

### Pipeline

The routing flow in Orchestator agent is:
1. Intent-wise comparison:
  
    - 1.1. The request is embedded and compared with similar entries in postgres using pgvector;
  
    - 1.2. Up to N examples are retrieved and ordered by their score;
  
    - 1.3. The route with the most relevant examples and the highest scores is used if minimal threshold is met;

2. If threshold is too low ro diff of top-k routes is too low, we use fallback Router subagent:
  
    - 2.1 Router sub agent receives the request and chat history to determine the route using LLM call;

3. Request is routed to appropriate agent or function (in case of AR module).

The routing is core functionality to the missing graph of the multiagent system.

### Database requirements

The table for storing intents is required:
- id: serial (internal id for the intent, PK);
- text: text (text of the intent example);
- text_embedding: vector(N) (vector of size N (determined by embedder));
- route_id: int4 (id of the route to go, FK).

With table for routes:
- id: serial (internal id of route, PK);
- name: varchar(16) (slug of the route).

So pgvector is required to be installed. Tables are created in schema `vector` (not `public`).
