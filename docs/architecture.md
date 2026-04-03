# Architecture

# Backend architecture description

# Stack

## API Web Server

### FastAPI

Simple and easy to use.

### SQLAlchemy

For entity-based database interactions.

### Alembic

For managing migrations, because it integrates with SQLAlchemy.

## Database

### PostgreSQL

For user data, chat history and file metadata;

- Widely supported and easy to use;
- Supports many modern capabilities.

### ElasticSearch

For document chunks and their metadata indexing.

- Powerful search engine;
- Supports semantic and hybrid search with complex queries.

## Authentication

### Firebase

Handles authentication, handling password storage and tokens for us.

- For itʼs simplicity to set up and serverless capabilities;
- Supports JWT verification in client libraries (`firebase_admin` for python).


# Scenarios description

## Sign Up / Log In


1. Requires only @bsu.by emails to be used;
2. All accounts must be verified via Email Verification in Firebase Auth;
3. Userʼs metadata is stored additionally in PostgreSQL.

### Sign Up flow
1. User enters email and password;
2. It is sent to firebase for account creation;
3. Email verification is requested immediately;
4. Service is unavailable until email verification is complete (like paywall but authwall idk);
5. When verification is complete, database entry is updated and user is allowed to use the app.

### Log In flow
1. User enters email and password;
2. It is verified via Firebase;
3. User obtains JWT token;

### NOTES
1. Each request is supplied with Authorization header contains JWT token from firebase;
2. Each request is verified on backend via firebase libraries (e. g. firebase_admin);
3. Email checks for @bsu.by are performed on frontend and backend;
4. Example of JWT: JWT.IO.

## File uploading

1. Files are uploaded to bucket (or just a folder on a server) and metadata is kept in PostgreSQL;
2. Then comes the chunking, algorithm may be adjusted, preliminary simple recursive chanking
with max length is ok enough;
3. After that chunks are uploaded to Elasticsearch index (reindex may take some time but itʼs
fine).

## Chatting

Requests are all processsed via Microsoft Presidio for PII Removal, before heading to Agents, so
not to leak any important info and all queries will be anonymous for LLMs.

We use OpenRouter as an LLM provider.

Chat history is loaded each agent from PostgreSQL, depends on the agentʼs task.

For ES queries filtering is applied to only use specified documents in the current context.

## Other

AR map will be exposed to download if needed.


# Database Schemas

## PostgreSQL

See `docs/postgres_schema.md`

## ElasticSearch

### Staff Index
- name: text
- surname: text
- fathers_name [optional]: text
- position: text
- room: int
- department: text
- competences [vectorized]: text + dense_vector
description [vectorized]: text + dense_vector

### Events Index
- name: text
- date_from: datetime
- date_to: datetime
-description [vectorized]: text + dense_vector
- bonus_amount: int
- participant_amount: int
- participant_requirements [vectorized]: text + dense_vector

### Context Materials Index
- document_id: int
- chunk_text [vectorized]: text + dense_vector


# Multi Agent System Description

## Description

Multiagent system for chat interaction with the user. Uses Orchestrator agent to route incoming
queries. Exception for user-specified usage scenario or agent (e. g. selecting Abstract
construction or Events information) to bypass router agent directly into necessary agent is also
possible

### Context Materials

System is used as chat interaction where each chat has its own context in form of uploaded
materials (files: lectures, books, etc.) into Materials Index as well as ability to connect web
search. So if web search is selected in the context, all of the agents connected to Context
Materials may also use web search via Tavily.

### Indexes

Indexes here represent ES indexes or other DB tables with stored documents (like event
descriptions or quiz data).

Indexes are populated programmatically (for Materials Index) or via admin UI pages (for
Events and Staff Indexes).


### PII masking

To prevent PII from getting into the LLM, it is replaced with mask tokens like [NAME]
[PHONE_NUMBER], [GROUP], etc. Using Microsoft Presidio with some custom rules.

### Routing

For general cases, all requests go through orchestrator. It is planned to have functional to skip
router by specifying the target agent in the request, so request can be processed better.

## Proposed Stack

### LLM API Provider

OpenRouter with Qwen3 Model family

- Works good with russian language;
- Relatively cheap yet performant;
- Available in our region.

### LLM Orchestration

LangGraph with LangChain for multiagent interactions and tooling.

- Modern production-ready frameworks;
- LangChain + LangGraph have good integration;
- Provides many pre-written interfaces for LLMs and usage scenarios.

Tavily for web search capabilities in tools.

- Easy to use and integrate;
- Cheaper and flexible plans (compared to alternatives, such as Apify)

### LLM Observability

Deploy Langfuse for observability and tracing of LLM calls, as well as prompt versioning system
for agents.

### Indexes

ElasticSearch

- Provides complex search scenarios in robust querying language;
- Has semantic search capabilities.

## Agents description

### Orchestrator (Router)

Router agent that determines which agent to invoke based on userʼs query and chat history.
Consists of two stages:

- Semantic routing – determines agent to route based on the collection of examples for each
agent and using semantic similarity to find collection with the most similarity and route there;
- LLM fallback – Is used as a fallback if two or more collections are too similar to each other.
May be used all the time and use semantic routing as advice, but this may increase pricing
significantly.

### Support Agent

Processes irrelevant queries and questiong on system abilities. Combines this data to suggest
usage scenarios in answers to irrelevant queries.

### Events Agent

Used for questions and searching of actual events, giving relevant information.

### Staff Agent

Consults about faculty staff. Suggests on who to visit based on the userʼs problem or what
specific person does and where to find them. Connected to the Staff Index where all the info is
stored.

### QA Agent

Used for answering different questiong about the materials in the chat context. Performs RAG
retrieval for searching relevant

### Summarizer

Performs summarization of materials in the chat context. Provides at least 3 different
summarization modes:

- Brief (for small quick info);
- Default (general summary);
- Deep Dive (performs informative summary, focusing on user specified spheres).

Each mode has specific prompt and it is dynamically loaded based on userʼs preferences
(request or chat history)


### Abstract Agent

Makes abstracts for users based on materials in the chat context. Subagents:

### Planner

Constructs plan for chapters based on research of the topic in the context materials.

### Chapter Writer

Constructs each chapter based on context materials and previous chapters

Chapters are fed this way for making N-th chapter:

- Full N-1 chapter;
- Summary of N-2, ..., 1 chapter.

## Chapter Summarizer

Summarizes N-2, ..., 1 chapters into one text.

It is all done iteratively for each chapter ensuring that models wonʼt get lost at context.

After, will be adapted to LaTeX template for ease of use by the user.

### Presentation Agent

Consists of subagent for generating presentations:

### Planner

Based on query and context materials makes a plan for each slide to explain something.

### Slider

Constructs each slide iteratively based on plan and summary of all of previous slides.

### Slide summarizer

Summarizes slides.

In the end it is all a power point presentation file made with python_pptx or whatever.


