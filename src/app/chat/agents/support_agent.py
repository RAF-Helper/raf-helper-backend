"""Support agent implementation."""

from .base import BaseAgent, AgentContext


class SupportAgent(BaseAgent):
    """Handles general support and system capability queries."""

    async def process(self, context: AgentContext, query: str) -> str:
        """Process general support queries."""
        prompt = f"""You are a support assistant for the Raf Helper system.

Your responsibilities:
- Answer questions about what the system can do
- Provide usage guidance
- Help users understand available features
- Be friendly and helpful

User query: {query}

Provide a helpful response:"""
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.content
