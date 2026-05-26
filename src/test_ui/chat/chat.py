"""Chainlit test UI for the multi-agent system (direct agent calls)."""

import os
from typing import Optional
import chainlit as cl
from chainlit.input_widget import Select

from app.chat.agents.staff_agent import StaffAgent
from app.chat.agents.events_agent import EventsAgent
from app.chat.agents.qa_agent import QAAgent
from app.chat.agents.summarizer_agent import SummarizerAgent
from app.chat.agents.presentation_agent import PresentationAgent
from app.chat.agents.support_agent import SupportAgent
from app.chat.agents.abstract_agent import AbstractAgent
from app.chat.llm.openrouter_client import OpenRouterClient
from app.pii.presidio_masker import PIIMasker
from app.chat.state import AgentInput
from app.config import settings
from app.schemas.agent import AgentType, SummarizationMode

# Agent mapping
AGENT_CLASSES = {
    AgentType.staff: StaffAgent,
    AgentType.events: EventsAgent,
    AgentType.qa: QAAgent,
    AgentType.summarizer: SummarizerAgent,
    AgentType.presentation: PresentationAgent,
    AgentType.support: SupportAgent,
    AgentType.abstract: AbstractAgent,
}

# Mapping from display labels to internal agent types (for settings UI)
AGENT_DISPLAY_TO_TYPE = {
    "Staff": "staff",
    "Events": "events",
    "Q&A": "qa",
    "Summarizer": "summarizer",
    "Presentation": "presentation",
    "Support": "support",
    "Abstract": "abstract",
}
# Reverse mapping for convenience
AGENT_TYPE_TO_DISPLAY = {v: k for k, v in AGENT_DISPLAY_TO_TYPE.items()}

# Model display labels and mapping to model IDs
MODEL_LABELS = [
    "Qwen 3.6 Plus (free) ⭐ Fast, 📚 Huge context",
    "Qwen 3 Next 80B (free) ⚡ Instant first token",
    "Step 3.5 Flash (free) 🏆 Best for tool agents",
    "gpt-oss-120b (free) 🎯 Good balance",
    "gpt-oss-20b (free) 🎯 Good balance",
    "Nemotron 3 Super (free) 🎯 balance & 📚 262K context",
]

MODEL_LABEL_TO_ID = {
    "Qwen 3.6 Plus (free) ⭐ Fast, 📚 Huge context": "qwen/qwen3.6-plus:free",
    "Qwen 3 Next 80B (free) ⚡ Instant first token": "qwen/qwen3-next-80b-a3b-instruct:free",
    "Step 3.5 Flash (free) 🏆 Best for tool agents": "stepfun/step-3.5-flash:free",
    "gpt-oss-120b (free) 🎯 Good balance": "openai/gpt-oss-120b:free",
    "gpt-oss-20b (free) 🎯 Good balance": "openai/gpt-oss-20b:free",
    "Nemotron 3 Super (free) 🎯 balance & 📚 262K context": "nvidia/nemotron-3-super-120b-a12b:free",
}


async def get_agent(agent_type: AgentType, model: Optional[str] = None):
    """Create an agent instance with the specified LLM model."""
    # Create LLM client with optional model override
    llm_client = OpenRouterClient(model=model) if model else OpenRouterClient()
    agent_class = AGENT_CLASSES.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class(llm_client)


@cl.on_settings_update
async def on_settings_update(settings_dict: dict):
    """Handle settings changes (agent and model selection)."""
    agent_display = settings_dict.get("agent")
    model_display = settings_dict.get("model")

    # Convert display labels to internal values
    cl.user_session.set("agent", AGENT_DISPLAY_TO_TYPE.get(agent_display, "staff"))
    cl.user_session.set("model", MODEL_LABEL_TO_ID.get(model_display) if model_display else None)


@cl.on_chat_start
async def start_chat():
    """Send a welcome message and configuration options."""
    if not settings.debug:
        await cl.Message(
            content="⚠️ Test UI is only available in DEBUG mode. Set DEBUG=True in .env"
        ).send()
        return

    # Use display labels for dropdown (these are what users see)
    agent_labels = list(AGENT_DISPLAY_TO_TYPE.keys())
    model_labels = MODEL_LABELS

    chat_settings = await cl.ChatSettings(
        [
            Select(
                id="agent",
                label="Agent",
                values=agent_labels,
                initial_index=0,
            ),
            Select(
                id="model",
                label="Model (override)",
                values=model_labels,
                initial_index=0,
            ),
        ]
    ).send()

    # Convert display labels to internal values and store in session
    agent_display = chat_settings.get("agent", agent_labels[0])
    model_display = chat_settings.get("model", model_labels[0])

    cl.user_session.set("agent", AGENT_DISPLAY_TO_TYPE.get(agent_display, "staff"))
    cl.user_session.set("model", MODEL_LABEL_TO_ID.get(model_display))

    welcome_msg = """# RAF Helper Backend — Test UI

Test individual agents with real-time chat.

**Available agents:**
- **Staff** — Search faculty directory (with PII unmasking)
- **Events** — Find university events
- **Q&A** — Answer from uploaded materials
- **Summarizer** — Summarize documents
- **Presentation** — Generate presentations
- **Support** — General assistance
- **Abstract** — Abstract generation (stub)

**Configuration:**
- Select an agent and model from the ⚙️ menu
- Chat history is maintained per session
- PII masking is applied automatically
"""
    await cl.Message(content=welcome_msg).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming chat messages."""
    if not settings.debug:
        await cl.Message(content="❌ Test UI is disabled in production mode.").send()
        return

    try:
        # Get selections
        selected_agent = cl.user_session.get("agent", "staff")
        selected_model = cl.user_session.get("model")

        agent_type = AgentType(selected_agent)

        # Get or create agent for this session (model fixed per session)
        # For simplicity, create new agent per message (could be cached)
        agent = await get_agent(agent_type, model=selected_model)

        # Retrieve chat history from session
        history = cl.user_session.get("history", [])

        # Apply PII masking to user message
        pii_masker = PIIMasker()
        masked, spans = await pii_masker.mask_text_with_spans(message.content)

        # Build AgentInput
        inp = AgentInput(
            message=message.content,
            masked_message=masked,
            chat_id=0,
            user_id=0,
            history=history,
            file_ids=[],
            use_web_search=False,
            summarization_mode=SummarizationMode.default,
            forced_agent=None,
            pii_spans=spans,
        )

        # Process with agent
        response = await agent.run(inp)

        # Update history (append user message and assistant response)
        history.append({"role": "user", "content": message.content})
        history.append({"role": "assistant", "content": response.content})
        cl.user_session.set("history", history[-20:])  # Keep last 20 turns

        # Build response with metadata
        meta_parts = []
        if response.metadata:
            if "tool_calls" in response.metadata:
                meta_parts.append(f"🔧 Tools: {len(response.metadata['tool_calls'])} calls")
            if "usage" in response.metadata:
                usage = response.metadata["usage"]
                total = usage.get("total_tokens", 0)
                meta_parts.append(f"📊 Tokens: {total}")
        meta_str = " | ".join(meta_parts) if meta_parts else ""

        content = f"**Agent:** {response.agent_used.value}"
        if meta_str:
            content += f"\n{meta_str}"
        content += f"\n\n{response.content}"

        await cl.Message(content=content, metadata=response.metadata).send()

    except Exception as e:
        import traceback
        traceback.print_exc()
        await cl.Message(content=f"❌ Error: {str(e)}", author="System").send()


@cl.set_starters
async def set_starters():
    """Provide starter messages to help users get started."""
    return [
        cl.Starter(
            label="Find staff (Russian)",
            message="Найдите мне преподавателя Николай Николаича",
            icon="👤",
        ),
        cl.Starter(
            label="Search events",
            message="Какие мероприятия запланированы на эту неделю?",
            icon="📅",
        ),
        cl.Starter(
            label="Q&A on materials",
            message="Что говорится в документации о требованиях?",
            icon="📚",
        ),
    ]
