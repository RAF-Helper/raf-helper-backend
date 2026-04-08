"""Prompt loading and management for agents."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PromptManager:
    """Loads and manages agent prompts from files."""

    def __init__(self, prompts_dir: str = "src/prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}
        logger.info(f"PromptManager initialized: dir={self.prompts_dir}")

    def load(self, name: str, cache: bool = True) -> str:
        """
        Load a prompt from a file.

        Args:
            name: Prompt name (filename without .txt extension)
            cache: Whether to cache the loaded prompt

        Returns:
            Prompt string content
        """
        if name in self._cache and cache:
            return self._cache[name]

        prompt_file = self.prompts_dir / f"{name}.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        content = prompt_file.read_text(encoding="utf-8")
        if cache:
            self._cache[name] = content

        logger.debug(f"Loaded prompt: {name} ({len(content)} chars)")
        return content

    def format(self, name: str, **kwargs) -> str:
        """
        Load and format a prompt with placeholders.

        Args:
            name: Prompt name
            **kwargs: Values to fill in placeholders (e.g., {query}, {context})

        Returns:
            Formatted prompt string
        """
        template = self.load(name)
        try:
            formatted = template.format(**kwargs)
            logger.debug(f"Formatted prompt: {name} with keys={list(kwargs.keys())}")
            return formatted
        except KeyError as e:
            logger.error(f"Missing placeholder in prompt '{name}': {e}")
            raise

    def reload(self, name: Optional[str] = None):
        """Clear prompt cache."""
        if name:
            self._cache.pop(name, None)
            logger.info(f"Cleared cache for prompt: {name}")
        else:
            self._cache.clear()
            logger.info("Cleared all prompt caches")


# Global prompt manager
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
