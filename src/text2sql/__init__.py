#!/usr/bin/env python3
"""
Text-to-SQL provider factory and exports.
"""

import os
import logging
from typing import Optional

from .base import Text2SQLProvider
from .local_llm import LocalLLMProvider
from .openrouter import OpenRouterProvider, RECOMMENDED_MODELS
from .openai_direct import OpenAIProvider
from .gemini_direct import GeminiProvider
from .env import load_dotenv_once
from .cerebras import CerebrasProvider
from .zai import ZAIProvider
from .deepseek import DeepSeekProvider

# Try to import Anthropic provider (optional dependency)
try:
    from .anthropic_direct import AnthropicProvider
    HAS_ANTHROPIC = True
except ImportError:
    AnthropicProvider = None
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)

__all__ = [
    'Text2SQLProvider',
    'LocalLLMProvider',
    'OpenRouterProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'ZAIProvider',
    'CerebrasProvider',
    'DeepSeekProvider',
    'AnthropicProvider',
    'create_provider',
    'RECOMMENDED_MODELS',
    'HAS_ANTHROPIC'
]


def create_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    verbose: bool = False,
    **kwargs
) -> Text2SQLProvider:
    """
    Factory function to create appropriate text-to-SQL provider.

    Args:
        provider: Provider type - 'auto', 'anthropic', 'openai', 'gemini', 'openrouter', 'zai', 'cerebras', 'deepseek', or 'local'
        model: Model identifier (provider-specific)
        verbose: If True, enable verbose output for debugging
        **kwargs: Additional provider-specific configuration

    Returns:
        Configured Text2SQLProvider instance

    Raises:
        ValueError: If provider type is unknown

    Examples:
        >>> # Auto-detect (prefers Anthropic for Claude, OpenRouter otherwise, then Z.AI)
        >>> provider = create_provider('auto')

        >>> # Force Anthropic direct API for Claude models
        >>> provider = create_provider('anthropic', model='claude-sonnet-4.5')

        >>> # Force OpenAI direct API with specific model
        >>> provider = create_provider('openai', model='gpt-5.1-codex')

        >>> # Force OpenRouter with specific model
        >>> provider = create_provider('openrouter', model='openai/gpt-5.1-codex-mini', temperature=1.0)

        >>> # Force Gemini direct API with specific model
        >>> provider = create_provider('gemini', model='gemini-3-flash-preview')

        >>> # Force Z.AI with specific model
        >>> provider = create_provider('zai', model='glm-4.7')

        >>> # Force DeepSeek with specific model
        >>> provider = create_provider('deepseek', model='deepseek-reasoner')

        >>> # Force local LLM with specific model
        >>> provider = create_provider('local', model='Qwen/Qwen2.5-7B-Instruct')

        >>> # Enable verbose output
        >>> provider = create_provider('auto', verbose=True)
    """
    load_dotenv_once()
    if not provider:
        provider = (os.getenv('TEXT2SQL_PROVIDER') or '').strip().lower() or 'openrouter'

    def _is_claude_model(model_name: Optional[str]) -> bool:
        """Check if model is a Claude model."""
        if not model_name:
            return False
        model_lower = model_name.lower()
        return 'claude' in model_lower or model_name.startswith('anthropic/')

    if provider == 'auto':
        # If model is Claude and Anthropic API available, use Anthropic direct
        if _is_claude_model(model) and HAS_ANTHROPIC and os.getenv('ANTHROPIC_API_KEY'):
            logger.info("Auto-selecting Anthropic direct API (Claude model + API key found)")
            return AnthropicProvider(
                model=model or 'claude-sonnet-4.5',
                verbose=verbose,
                **kwargs
            )
        # Otherwise try OpenRouter (if API key available)
        elif os.getenv('OPENROUTER_API_KEY'):
            logger.info("Auto-selecting OpenRouter (API key found)")
            return OpenRouterProvider(
                model=model or 'openai/gpt-5.1-codex-mini',
                verbose=verbose,
                **kwargs
            )
        elif os.getenv('OPENAI_API_KEY'):
            logger.info("Auto-selecting OpenAI (API key found)")
            return OpenAIProvider(
                model=model or 'gpt-5.1-codex',
                verbose=verbose,
                **kwargs
            )
        elif os.getenv('GEMINI_API_KEY'):
            logger.info("Auto-selecting Gemini (API key found)")
            return GeminiProvider(
                model=model or 'gemini-3-flash-preview',
                verbose=verbose,
                **kwargs
            )
        elif os.getenv('CEREBRAS_API_KEY'):
            logger.info("Auto-selecting Cerebras (API key found)")
            return CerebrasProvider(
                model=model or 'zai-glm-4.7',
                verbose=verbose,
                **kwargs
            )
        elif os.getenv('ZAI_API_KEY'):
            logger.info("Auto-selecting Z.AI (API key found)")
            return ZAIProvider(
                model=model or 'glm-4.7',
                verbose=verbose,
                **kwargs
            )
        else:
            logger.info("Auto-selecting Local LLM (no API keys found)")
            return LocalLLMProvider(
                model_name=model or 'Qwen/Qwen2.5-3B-Instruct',
                **kwargs
            )

    elif provider == 'anthropic':
        if not HAS_ANTHROPIC:
            raise ValueError(
                "Anthropic provider not available. "
                "Install with: uv sync"
            )
        return AnthropicProvider(
            model=model or 'claude-sonnet-4.5',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'openrouter':
        return OpenRouterProvider(
            model=model or 'openai/gpt-5.1-codex-mini',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'openai':
        return OpenAIProvider(
            model=model or 'gpt-5.1-codex',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'gemini':
        return GeminiProvider(
            model=model or 'gemini-3-flash-preview',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'zai':
        return ZAIProvider(
            model=model or 'glm-4.7',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'cerebras':
        return CerebrasProvider(
            model=model or 'zai-glm-4.7',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'deepseek':
        return DeepSeekProvider(
            model=model or 'deepseek-reasoner',
            verbose=verbose,
            **kwargs
        )

    elif provider == 'local':
        return LocalLLMProvider(
            model_name=model or 'Qwen/Qwen2.5-3B-Instruct',
            **kwargs
        )

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Choose from: 'auto', 'anthropic', 'openai', 'gemini', 'openrouter', 'zai', 'cerebras', 'deepseek', 'local'"
        )
