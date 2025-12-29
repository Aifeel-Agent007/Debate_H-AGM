"""Multi-LLM client for debate evaluation (backward compatibility wrapper)."""

from typing import Optional

from debate_evaluator.llm_client import MultiLLMClient, DebateEvaluatorClient as BaseClient
from debate_evaluator.config import Settings, get_settings


class DebateEvaluatorClient(BaseClient):
    """Multi-LLM client wrapper for backward compatibility."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize client with settings."""
        if settings:
            provider = getattr(settings, 'llm_provider', 'gpt')
            model = getattr(settings, 'openai_model', 'gpt-4o')
            api_key = getattr(settings, 'openai_api_key', None)
            temperature = getattr(settings, 'openai_temperature', 0.3)
            max_tokens = getattr(settings, 'openai_max_tokens', 4096)
            timeout = getattr(settings, 'openai_timeout', 120.0)
        else:
            provider = None  # Will use environment variables
            model = None
            api_key = None
            temperature = 0.3
            max_tokens = 4096
            timeout = 120.0
        
        super().__init__(
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    
    @property
    def model(self) -> str:
        """Current model name (backward compatibility)."""
        return self.model_name
