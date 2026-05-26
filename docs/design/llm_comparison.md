# LLM choosing

## Final verdict

### Routing LLM Fallback

Requires the quickest response time but isn't dependent on context length or high intelligence as routing task is relatively simple.

__Suitable models__:
- __Ling-2.6-flash__ as a fallback. Has great latency but may lack intelligence (_TODO: test it out_);
- __Qwen3 Next 80B A3B Instruct__ due to instant low latency. Model small capabilities should not affect simple routing task;
- __gpt-oss-120b__ as a fallback. Suits the task perfectly and still has great latency;
- __gpt-oss-20b__ as a fallback.
- __Gemma 4 31B__ as a fallback (_Notice: latency_).

### RAG Agents

__Include__: Events agent, Staff agent, Support agent, QA Agent

The most general task that requires intelligence and agentic toolkit. Latency is quite important here and impactful on the user's experience but not the highest priority.

__Suitable models__:
- __Gemma 4 31B__ due to excellent benchmark scores and full agentuc toolkit (tooling, reasoning, structured outputs);
- __MiniMax 2.5__ as a fallback, has agentic capabilities and good performance;
- __Nemotron 3 Super__ as a fallback, has agentic capabilities and good performance (_Notice: Data Collection_);
- __Ling-2.6-flash__ as a fallback, has some agentic capabilities but may lack performance;
- __gpt-oss-120b__ as a fallback due to full agentic support and low latency;


### Summarizer agent

Requires big context window and less of a latency problem.

__Suitable models__:
- __Nemotron 3 Super__ due to the biggest context window available.
- __Gemma 4 31B__ due to good intelligence and context window. 33K output should fit most of our scenarios.
- __Qwen3 Next 80B A3B Instruct__ actually has good context window and low latency but less intelligence and poor provider with low uptime (_TODO: test it out_).
- __Ling-2.6-flash__ due to good context window. 33K output should fit most of our scenarios.


### Abstract / Slide agents

Here latency is not problem at all, but context and intelligence are.

__Writers__:

- __Gemma 4 31B__ due to excellent benchmark scores for size and good context size;
- __Nemotron 3 Super__ as a capable model with good context but ridiculous latency (_Notice: Data Collection_);
- __Ling-2.6-flash__ as a fallback, has some agentic capabilities but may lack performance;
- __gpt-oss-120b__ as a fallback.

__Planners, Summarizers, Reviewers__:

- __Gemma 4 31B__ has good benchmark but output context is relatively small (33K); 
- __Nemotron 3 Super__ has good performance and context but high latency (_Notice: Data Collection_).
- __Ling-2.6-flash__ as a fallback, has some agentic capabilities but may lack performance;

_Note: Review agents are not included in the architecture yet and mentioned here as a possible improvement_


## More in-depth

### Deciding factors

For our cases we have these as important parameters:
- __Latency__, due to chat nature of our application;
- __Agentic toolkit__, due to wast usage of agents;
- __Overall model intelligence__, due to working with eduactional materials, concept understanding in context is crucial.

### Model overview

- __Gemma 4 31B__ shows very good performance in all fields but sometimes falls with 500 so requires proper fallback;
- __MiniMax M2.5__ is quite good reasoning model with very limited context (197K input & 8K output), slow tps and with faulty provider that sometimes unavailable, but when it works, it does great;
- __Nemotron 3 Super__ performs well with 262K context window, agentic toolkit and good benchmarks, but is loosing on provider latency (5-10 seconds) but good uptime.
- __Ling-2.6-flash__ non-reasoning model with quick response time and ok capabilites serves good for low-response cases and as a fallback;
- __Qwen3 Next 80b A3B Instruct__ supports staggering first token latency but long generation, perfect for fallback llm router, however due to poor provider with low uptime requires fallback model to support it;
- __gpt-oss-120b__ is in the middle of everythin, offers lower intelligence in comparison to _Nemotron 3 Super_, _Gemma 4 31B_ and similar to _Ling-2.6-flash_ but still good, offers twice as less of a context window, however way lower first token latency and good uptime.


### OR perfomance tests:

- __Gemma 4 31B__: 2050 tokens / 72.9s, ok (~2s) first token latency;
- __MiniMax M2.5__: 2050 tokens / 159.9s, ok (~2s) first token latency;
- __Nemotron 3 Super__: 2050 tokens / 78.6s (107.0s), long (5 to 10s) first token latency;
- __Ling-2.6-flash__: 2050 tokens / 34.0s, long first token latency.
- __Qwen3 Next 80B A3B Instruct__: 2050 tokens / 68.8s, instant (<<1s) first token latency;
- __gpt-oss-120b__: 2050 tokens / 53.2s, quick (<1s) first token latency
- __gpt-oss-20b__: 2050 tokens / 45.1s, quick (<1s) first token latency


# LLM Comparison

Here will lie the LLM comparison document with the most interesting free models for OpenRouter with possible applications for our case.

## Overall note

Free openrouter usage supports only for ~50 request a day with 3 rpm rate limit, so one must use OR with attention. Maybe we should implement auto API token switching for fallback rate limiting.


## Gemma 4 31B

__OR tag__: `google/gemma-4-31b-it:free`

### Reasoning

Supports reasoning providing for better answer quality.

### Context

Works with 262K input and 33K output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Intelligence

Shows good benchmarking scores and intelligence level for the tasks. However falls behind some of the larger models like minimax.

### Performance

- 2s First token latency.
- 29 tokens per second.

__OR test__:
- 2050 tokens / 72.9s, ok first token latency

__Provider frequently fails (with 500 error)__

### Use case

Overall great model for agentic cases with good intelligence for it's level, agentic toolkit and good context window. But provider sometimes returns 500 errors (at least returned), so requires fallback.


## MiniMax M2.5

__OR tag__: `minimax/minimax-m2.5:free`

### Reasoning

Supports reasoning providing for better answer quality. But reasoning is limited with output tokens.

### Context

Holds up to 196.6K input tokens and 8.2K output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Intelligence

Shows good benchmarking scores and intelligence level for the tasks.

### Performance

- ~2s First token latency.
- 13 tokens per second.

__OR test__:
2050 tokens / 159.9s, ok first token latency

__Provider frequently fails (unavailable)__

### Use case

Good variant for all agentic cases, but poor uptime, extremely low output of 8K and slow token output limits its usage seriously and requires decent fallback.


## Ling-2.6-flash

__OR tag__: `inclusionai/ling-2.6-flash:free`

### Reasoning

No reasoning supported.

### Context

Handles 262K of input and 32.8K of output max context.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Intelligence

Shows lower benchmarking scores and intelligence level due to lack of reasoning. However may be considered good for it's tasks.

### Performance

- <1s First token latency.
- ~60 tokens per second.

__OR test__:
2050 tokens / 34.0s, long first token latency

### Use case

Will be perfect for routing due to extremely fast response and absense of reasoning tokens. Limited usage for other scenarios due to relatively lower intelligence but is usable as a fallback. Multilingual performance is yet to be tested.


## Qwen3 Next 80B A3B Instruct

__OR tag__: `qwen/qwen3-next-80b-a3b-instruct:free`

### Reasoning

No reasoning supported

### Context

262.1K Tokens of input and output

### Tools

Supports tool calling, so is suitable for agentic cases.

### Intelligence

Shows lower benchmarking scores and intelligence level due to lack of reasoning. However may be considered good for it's tasks.

### Performance

- <1s First token latency.
- 29.8 tokens per second.

__OR test__:
2050 tokens / 68.8s, instant first token latency

__Poor uptime on OR (~65%)__

### Use case

Will be perfect for router due to instant first token latency. Low parameter size and reasoning absense makes it not so applicable for complex use cases. Experience shows, that Qwen 80B models can work poorly with tools and complex structured outputs in multilingual tasks.


## Nemotron 3 Super

__OR tag__: `nvidia/nemotron-3-super-120b-a12b:free`

__The model collects prompt and completion data that can be used to improve the model.__

### Reasoning

Supports reasoning providing for better answer quality.

### Context

Works with 262K input and output tokens max.

### Tools

Supports tool calling, so is suitable for agentic cases.

### Intelligence

Shows overall good benchmarking scores and intelligence level. However is generally a bit worse than gemma4 and minimax.

### Performance

- 10s First token latency.
- 30 tokens per second.

__OR test__:
- 2050 tokens / 78.6s (107.0s), long first token latency


### Use case

Long inference latencies from provider are not perfect for quick responses. So long-form tasks (abstraction and slides construction) are good for that model. Decent context window (262k) and benchmark intelligence scores with supported reasoning also makes case to use that model for working with educational materials a good choice.

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

### Intelligence

Show ok benchmarking scores and intelligence level due to age. Good multilingually and stands as a good fallback.

### Performance

- <1s First token latency.
- 39 tokens per second.

__OR test__:
- 2050 tokens / 53.2s, quick first token latency

### Use case

Short latencies and agentic capabilities makes this good choice as a fallback for routing and some agents. The model provides ok performance with reasoning allowing for complex tasks, however due to its age it's stands in the middle of everything so is placed as a fallback option.
Lower parameter model _openai/gpt-oss-20b:free_ is available, providing similar characteristics but even less intelligence, being outperformed by _Ling-2.6-flash_.


# Notes

OpenRouter comparisons links (in triplets):

(gpt-oss-20b vs gpt-oss-120b vs Ling-2.6-flash)[https://openrouter.ai/compare/openai/gpt-oss-20b:free/openai/gpt-oss-120b:free/inclusionai/ling-2.6-flash:free]

(Gemma 4 31B vs Qwen3 Next 80B A3B Instruct vs Ling-2.6-flash) [https://openrouter.ai/compare/google/gemma-4-31b-it:free/qwen/qwen3-next-80b-a3b-instruct:free/inclusionai/ling-2.6-flash:free]

(MiniMax M2.5 vs Nemotron 3 Super vs gpt-oss-120b)[https://openrouter.ai/compare/minimax/minimax-m2.5:free/nvidia/nemotron-3-super-120b-a12b:free/openai/gpt-oss-120b:free]

(Gemma 4 31B vs MiniMax M2.5 vs gpt-oss-120b)[https://openrouter.ai/compare/google/gemma-4-31b-it:free/minimax/minimax-m2.5:free/openai/gpt-oss-120b:free]

(MiniMax M2.5 vs Gemma 4 31B vs Ling-2.6-flash)[https://openrouter.ai/compare/minimax/minimax-m2.5:free/google/gemma-4-31b-it:free/inclusionai/ling-2.6-flash:free]

(Gemma 4 31B vs Qwen3 Next 80B A3B Instruct vs Nemotron 3 Super)[https://openrouter.ai/compare/google/gemma-4-31b-it:free/qwen/qwen3-next-80b-a3b-instruct:free/nvidia/nemotron-3-super-120b-a12b:free]
