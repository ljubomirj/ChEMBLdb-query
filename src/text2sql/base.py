#!/usr/bin/env python3
"""
Base class for Text-to-SQL providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class Text2SQLProvider(ABC):
    """Abstract base class for text-to-SQL generation providers."""

    @abstractmethod
    def generate_sql(
        self,
        question: str,
        schema_docs: str,
        conversation_history: Optional[list] = None
    ) -> Optional[str]:
        """
        Generate SQL query from natural language question.

        Args:
            question: Natural language question from user
            schema_docs: Database schema documentation
            conversation_history: Optional conversation history for retry context

        Returns:
            SQL query string, or None if generation failed
        """
        pass

    def generate_text(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """
        Generate free-form text completion for a chat-style messages array.

        This is used for non-SQL tasks (e.g., query interpretation, judging).
        Providers may override this; default implementation is unsupported.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support generate_text()")

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is ready to use.

        Returns:
            True if provider can generate SQL, False otherwise
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name for logging and display.

        Returns:
            Human-readable provider name
        """
        pass

    def close(self):
        """
        Clean up resources (optional).
        Override if provider needs cleanup.
        """
        pass
