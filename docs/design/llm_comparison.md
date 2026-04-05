# LLM choosing

## Final verdict

### Routing LLM Fallback

- __Qwen Next 80B A3B Instruct__ due to instant low latency. Model small capabilities should not affect simple routing task;
- __gpt-oss-120b__ as a fallback. Suits the task perfectly and still has great latency;
- __gpt-oss-20b__ as a fallback.

### RAG Agents

__Include__: Events agent, Staff agent, Support agent, QA Agent

- __gpt-oss-120b__ due to good benchmark scores, low latency and full agentic support (tooling, reasoning, structured outputs);
- __Step 3.5 Flash__ as a fallback, has agentic capabilities and good performance;
- __Nemotron 3 Super__ as a fallback, has agentic capabilities and good performance (_Notice: Data Collection_);
- __Qwen3.6 Plus__ as a fallback, has agentic capabilities and good performance.


### Summarizer agent

- __Qwen3.6 Plus__ due to exceptional context window. 65K output should fit most of our scenarios.

_Fallback TBD_.


### Abstract / Slide agents

__Writers__:

- __Step 3.5 Flash__ due to good capabilities and ok context window
- __Nemotron 3 Super__ as a fallback (_Notice: Data Collection_);
- __gpt-oss-120b__ as a fallback.

__Planners, Summarizers, Reviewers__:

- __Qwen3.6 Plus__ due to exceptional context window. 65K output should fit most of our scenarios.

_Fallback TBD_.

_Note: Review agents are not included in the architecture yet and mentioned here as a possible improvement_


## More in-depth


### Deciding factors

For our cases we have these as important parameters:
- __Latency__, due to chat nature of our application;
- __Agentic toolkit__, due to wast usage of agents;
- __Overall model intelligence__, due to working with eduactional materials, concept understanding in context is crucial.

### Model overview

__Qwen3.6 Plus__ is the fastest in tps with large input context window, however limits our abilities with short output token limit.

__Qwen Next 80b A3B Instruct__ supports staggering first token latency but long generation, perfect for fallback llm router, however due to poor provider with low uptime requires fallback model to support it.

__Nemotron 3 Super__ is in the middle of everythin with 262K context window, agentic toolkit and good benchmarks, but is loosing on provider latency (4-7 seconds) but good uptime.

__Step 3.5 Flash__ shows similar to _Nemotron 3 Super_ perfomance with 256K context window, 5s latency with faster (40 agains 20 tps), agentic toolkit and slightly better benchmarks with great uptime.

__gpt-oss-120b__ offers slightly lower benchmark scores in comparison to _Nemotron 3 Super_ and _Step 3.5 Flash_ and twice as less of a context window, however way lower first token latency.


### OR perfomance tests:

- __Qwen3.6 Plus__: 2050 tokens / 45.0s, okay (~1s) first token latency;
- __Qwen3 Next 80B A3B Instruct__: 2050 tokens / 68.8s, instant (<<1s) first token latency;
- __Nemotron 3 Super__: 2050 tokens / 107.0s (125.8s), long (~5s) first token latency;
- __gpt-oss-120b__: 2050 tokens / 68.8s, quick (<1s) first token latency;
- __gpt-oss-20b__: 2050 tokens / 68.9s, quick (<1s) first token latency;
- __Step 3.5 Flash__: 2050 tokens / 55.2s, long (~5s) first token latency.


# LLM Comparison

Here will lie the LLM comparison document with the most interesting free models for OpenRouter with possible applications for our case.

## Overall note

Free openrouter usage supports only for ~50 request a day with 3 rpm rate limit, so one must use OR with attention. Maybe we should implement auto API token switching for fallback rate limiting.


## Qwen3.6 Plus

__OR tag__: `qwen/qwen3.6-plus:free`

### Reasoning

Supports short reasoning providing for better answer quality. But reasoning is limited with output tokens.

### Context

Holds up to 1M input tokens and ~65K output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Performance

- 1.4s First token latency.
- 45 tokens per second.

__OR test__:
2050 tokens / 45.0s, quick first token latency


### Use case

Will be perfect for working with abstract and slides due to enormous context window. However low max output tokens is limiting it's ability in that field.


## Qwen3 Next 80B A3B Instruct

__OR tag__: `qwen/qwen3-next-80b-a3b-instruct:free`

### Reasoning

No reasoning supported

### Context

262.1K Tokens of input and output

### Tools

Supports tool calling, so is suitable for agentic cases.

### Performance

- <1s First token latency.
- 29.8 tokens per second.

__OR test__:
2050 tokens / 68.8s, instant first token latency


__Poor uptime on OR (~65%)__


### Use case

Will be perfect for router due to instant first token latency. Low parameter size and reasoning absense makes it not so applicable for complex use cases. Experience shows, that Qwen 80B models can work poorly with tools and complex structured outputs.


## Nemotron 3 Super

__OR tag__: `nvidia/nemotron-3-super-120b-a12b:free`

__The model collects prompt and completion data that can be used to improve the model.__

### Reasoning

Supports short reasoning providing for better answer quality.

### Context

Works with 262K input and output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Performance

- 4.5s First token latency.
- 20 tokens per second.

__OR test__:
- 2050 tokens / 107.0s (125.8s), long first token latency


### Use case

Long inference latencies from provider are not perfect for quick responses so long-form tasks (abstraction and slides construction) are ok for that model. Decent context window (262k) and benchmark intelligence scores with supported reasoning also makes case to use that model for working with educational materials good choice.

Data collection is not suitable for the most secret use cases, must be cautious about that.



## gpt-oss-120b

__Provider is down, temporary not our case__

__OR tag__: `openai/gpt-oss-120b:free`

### Reasoning

Supports reasoning providing for better answer quality.

### Context

Works with 131K input and output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Performance

- <1s First token latency.
- 30 tokens per second.

__OR test__:
- 2050 tokens / 68.0s, long first token latency


### Use case

Short latencies and agentic capabilities makes this a perfect baseline choice for our agents. The model provides good performance with reasoning allowing for complex tasks. Lower parameter model _openai/gpt-oss-20b:free_ is available, providing similar characteristics but less intelligence.

Also, providers for this model on OpenRouter are quite unstable, requiring decent fallback for this model.


## Step 3.5 Flash

__OR tag__: `stepfun/step-3.5-flash:free`

### Reasoning

Supports reasoning providing for better answer quality.

### Context

Handle 256K of input and output max context.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Performance

- 5s First token latency.
- ~40 tokens per second.

__OR test__:
2050 tokens / 55.2s, long first token latency


### Use case

Will be perfect for working with abstract and slides due to enormous context window. However low max output tokens is limiting it's ability in that field.


# Notes

OpenRouter comparisons links (in triplets):

(gpt-oss-120b vs gpt-oss-20b vs Nemotron 3 Super)[https://openrouter.ai/compare/openai/gpt-oss-20b:free/openai/gpt-oss-20b:free/nvidia/nemotron-3-super-120b-a12b:free]

(Qwen3.6 Plus vs Qwen3 Next 80B A3B Instruct vs Nemotron 3 Super)[https://openrouter.ai/compare/qwen/qwen3.6-plus:free/openai/gpt-oss-20b:free/nvidia/nemotron-3-super-120b-a12b:free]

(Step 3.5 Flash vs Qwen3.6 Plus vs gpt-oss-120b) [https://openrouter.ai/compare/stepfun/step-3.5-flash:free/qwen/qwen3.6-plus:free/openai/gpt-oss-120b:free]
