#!/usr/bin/env python3
"""
CLI Chat Interface for OpenRouter Client

A simple command-line interface to test the OpenRouter LLM client interactively.

Usage:
    uv run python tests/cli_chat.py
    # or
    OPENROUTER_API_KEY=your-key python tests/cli_chat.py

Commands:
    /chat <message>    - Send a chat message (default)
    /stream <message>  - Send a message and stream the response
    /tools            - Enable tool calling mode
    /schema           - Use structured output (requires Pydantic model)
    /model <name>     - Change model (e.g., 'anthropic/claude-sonnet-4.5')
    /temp <value>     - Set temperature (0.0-2.0)
    /help             - Show this help
    /quit             - Exit
"""

import readline
import asyncio
import os
import sys
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.chat.llm import OpenRouterClient, LLMMessage, OpenRouterError
from app.config import Settings
from app.logging_config import setup_logging


class ChatCLI:
    """Interactive CLI for testing the OpenRouter client."""

    def __init__(self):
        self.client: Optional[OpenRouterClient] = None
        self.chat_history: list[LLMMessage] = []
        self.model: str = Settings().openrouter_model
        self.temperature: float = 0.7
        self.max_tokens: Optional[int] = None
        self.conversation_mode: str = "chat"  # 'chat' or 'stream' or 'tools'

    def init_client(self) -> bool:
        """Initialize the OpenRouter client."""
        try:
            # Initialize logging first
            setup_logging(
                log_level="INFO",
                enable_console=False,
            )

            # Load settings from environment
            settings = Settings()
            if not settings.openrouter_api_key:
                print("❌ Error: OPENROUTER_API_KEY environment variable not set")
                print("\nSet it with:")
                print("  export OPENROUTER_API_KEY='your-api-key'")
                print("  or create a .env file with OPENROUTER_API_KEY=your-key")
                return False

            # Override settings if environment variables differ
            if os.getenv("OPENROUTER_MODEL"):
                self.model = os.getenv("OPENROUTER_MODEL")
            if os.getenv("OPENROUTER_TEMPERATURE"):
                self.temperature = float(os.getenv("OPENROUTER_TEMPERATURE"))

            self.client = OpenRouterClient()
            print(f"✅ Connected to OpenRouter")
            print(f"   Model: {self.model}")
            print(f"   Temperature: {self.temperature}")
            print(f"   Base URL: {Settings().openrouter_base_url}")
            print(f"\n📝 Logs are being written to: logs/app.log and logs/llm.log")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize client: {e}")
            return False

    async def chat(self, message: str) -> str:
        """Send a chat message and get response."""
        if not self.client:
            return "❌ Client not initialized"

        # Add user message to history
        self.chat_history.append(LLMMessage(role="user", content=message))

        try:
            response = await self.client.chat(
                messages=self.chat_history,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Add assistant response to history
            self.chat_history.append(LLMMessage(role="assistant", content=response.content))

            # Print usage if available
            if response.usage:
                print(f"\n📊 Usage: {response.usage['prompt_tokens']} prompt, "
                      f"{response.usage['completion_tokens']} completion, "
                      f"{response.usage['total_tokens']} total")

            return response.content

        except OpenRouterError as e:
            return f"❌ API Error: {e}"
        except Exception as e:
            return f"❌ Unexpected error: {e}"

    async def stream_chat(self, message: str):
        """Send a chat message and stream the response."""
        if not self.client:
            print("❌ Client not initialized")
            return

        # Add user message to history
        self.chat_history.append(LLMMessage(role="user", content=message))

        try:
            print("🤖 Assistant: ", end="", flush=True)
            full_response = ""

            async for chunk in self.client.chat_stream(
                messages=self.chat_history,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                print(chunk, end="", flush=True)
                full_response += chunk

            print()  # New line after streaming

            # Add assistant response to history
            self.chat_history.append(LLMMessage(role="assistant", content=full_response))
            print()  # Extra line

        except OpenRouterError as e:
            print(f"\n❌ API Error: {e}")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")

    def print_help(self):
        """Print help information."""
        print(__doc__)
        print("\nCurrent Settings:")
        print(f"  Model: {self.model}")
        print(f"  Temperature: {self.temperature}")
        print(f"  Max Tokens: {self.max_tokens or 'unlimited'}")
        print(f"  Mode: {self.conversation_mode}")
        print(f"  Messages in history: {len(self.chat_history)}")

    def clear_history(self):
        """Clear chat history."""
        self.chat_history = []
        print("✅ Chat history cleared")

    async def run(self):
        """Run the CLI main loop."""
        print("=" * 60)
        print("🤖 OpenRouter CLI Chat")
        print("=" * 60)

        if not self.init_client():
            return 1

        print("\nType your message and press Enter to chat.")
        print("Type /help for commands, /quit to exit.\n")

        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    command = parts[0].lower()

                    if command == "/quit" or command == "/exit":
                        print("👋 Goodbye!")
                        break

                    elif command == "/help":
                        self.print_help()
                        continue

                    elif command == "/clear":
                        self.clear_history()
                        continue

                    elif command == "/chat":
                        self.conversation_mode = "chat"
                        print("✅ Mode: Normal chat (non-streaming)")
                        continue

                    elif command == "/stream":
                        self.conversation_mode = "stream"
                        print("✅ Mode: Streaming responses")
                        continue

                    elif command == "/model":
                        if len(parts) < 2:
                            print("❌ Usage: /model <model-name>")
                            print("   Example: /model anthropic/claude-sonnet-4.5")
                        else:
                            self.model = parts[1]
                            print(f"✅ Model set to: {self.model}")
                        continue

                    elif command == "/temp":
                        if len(parts) < 2:
                            print("❌ Usage: /temp <value>")
                            print("   Range: 0.0 (deterministic) to 2.0 (creative)")
                        else:
                            try:
                                self.temperature = float(parts[1])
                                if not 0.0 <= self.temperature <= 2.0:
                                    raise ValueError("Temperature must be between 0.0 and 2.0")
                                print(f"✅ Temperature set to: {self.temperature}")
                            except ValueError as e:
                                print(f"❌ Invalid temperature: {e}")
                        continue

                    elif command == "/max_tokens":
                        if len(parts) < 2:
                            print("❌ Usage: /max_tokens <number>")
                            print("   Example: /max_tokens 1000")
                        else:
                            try:
                                self.max_tokens = int(parts[1])
                                if self.max_tokens <= 0:
                                    raise ValueError("Must be positive")
                                print(f"✅ Max tokens set to: {self.max_tokens}")
                            except ValueError as e:
                                print(f"❌ Invalid value: {e}")
                        continue

                    elif command == "/show_history":
                        print(f"\n📜 Chat History ({len(self.chat_history)} messages):")
                        for i, msg in enumerate(self.chat_history[-10:], start=max(1, len(self.chat_history)-9)):
                            role = "👤 User" if msg.role == "user" else "🤖 Assistant" if msg.role == "assistant" else "⚙️ System"
                            content_preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                            print(f"  {i}. {role}: {content_preview}")
                        if len(self.chat_history) > 10:
                            print(f"  ... and {len(self.chat_history) - 10} more")
                        continue

                    elif command == "/usage":
                        if self.client:
                            print(f"\n📊 Current Settings:")
                            print(f"   Model: {self.model}")
                            print(f"   Temperature: {self.temperature}")
                            print(f"   Max Tokens: {self.max_tokens or 'unlimited'}")
                            print(f"   History length: {len(self.chat_history)} messages")
                        continue

                    else:
                        print(f"❌ Unknown command: {command}")
                        print("   Type /help for available commands")
                        continue

                # Regular chat message
                if self.conversation_mode == "stream":
                    await self.stream_chat(user_input)
                else:
                    response = await self.chat(user_input)
                    print(f"\n🤖 Assistant: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Type /quit to exit properly.")
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()


def main():
    """Entry point for the CLI."""
    cli = ChatCLI()
    try:
        exit_code = asyncio.run(cli.run())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
