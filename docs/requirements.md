# Requirements

This document contains requirements to parts of the system to be met at the end of the development. The document is WIP, so must be updated on-the-go and is not yet completed.

## LLM

LLMs are being used by API here, without any on-prem usage, as it is not the case here, due to data being not so privacy-sensitive and complications of using on-prem solutions (GPU infra and low model intelligence).

Project assumes usage of OpenRouter as main provider, yet support modularity for easy drop-in replacement just in case.

Client should support:
- Selecting different models;
- Tool calling (maybe even mcp servers);
- Response streaming;
- Structured output.

All of that should be in easy, readable, upgradable, modular way with best practices application.

All of that may use LangChain or custom communication with the client, requires more thought and comparison.
