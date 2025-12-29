"""Multi-LLM client for debate evaluation."""

import os
from typing import Optional, Literal
from openai import OpenAI
import anthropic
try:
    from google import genai
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        genai = None
from groq import Groq
try:
    from dashscope import Generation
except ImportError:
    Generation = None

from debate_evaluator.config import Settings, get_settings

# Supported LLM providers
LLMProvider = Literal["gpt", "grok", "gemini", "claude", "qwen"]

# Default models for each provider
DEFAULT_MODELS = {
    "gpt": "gpt-4o",
    "grok": "mixtral-8x7b-32768",
    "gemini": "gemini-pro",
    "claude": "claude-3-5-sonnet-20241022",
    "qwen": "qwen-turbo",
}

# API key environment variables
API_KEY_ENV_VARS = {
    "gpt": "OPENAI_API_KEY",
    "grok": "GROQ_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}


class MultiLLMClient:
    """Multi-LLM client for debate evaluation."""
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        """Initialize multi-LLM client.
        
        Args:
            provider: LLM provider (defaults to EVAL_LLM_PROVIDER env var or "gpt")
            model: Model name (defaults to provider's default)
            api_key: API key (defaults to environment variable)
            temperature: Temperature for generation
            max_tokens: Maximum tokens
            timeout: Request timeout
        """
        # Get provider from environment if not specified
        if provider is None:
            provider_str = os.getenv("EVAL_LLM_PROVIDER", "gpt").lower()
            provider_map = {
                "openai": "gpt",
                "anthropic": "claude",
                "google": "gemini",
                "alibaba": "qwen",
                "dashscope": "qwen",
            }
            provider = provider_map.get(provider_str, provider_str)
        
        if provider not in DEFAULT_MODELS:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        self.provider = provider
        self.model = model or DEFAULT_MODELS[provider]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Get API key
        if api_key is None:
            env_var = API_KEY_ENV_VARS[provider]
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"{env_var} environment variable not set for {provider}")
        
        self.api_key = api_key
        
        # Initialize client based on provider
        if provider == "gpt":
            self._client = OpenAI(api_key=api_key, timeout=timeout)
        elif provider == "claude":
            self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        elif provider == "gemini":
            if genai is None:
                raise ImportError("google-genai package not installed. Install with: pip install google-genai")
            try:
                self._client = genai.Client(api_key=api_key)
            except AttributeError:
                # Fallback to google.generativeai
                import google.generativeai as genai_module
                genai_module.configure(api_key=api_key)
                self._client = genai_module
        elif provider == "grok":
            self._client = Groq(api_key=api_key, timeout=timeout)
        elif provider == "qwen":
            # DashScope doesn't need explicit client initialization
            self._client = None
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Chat completion API call.
        
        Args:
            system_prompt: System prompt
            user_message: User message
            temperature: Temperature (optional)
            max_tokens: Max tokens (optional)
            
        Returns:
            LLM response text
        """
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        if self.provider == "gpt":
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temp,
                max_tokens=max_tok,
            )
            return response.choices[0].message.content or ""
        
        elif self.provider == "claude":
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tok,
                temperature=temp,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        
        elif self.provider == "gemini":
            response = self._client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_message}"}]}
                ],
                generation_config={
                    "temperature": temp,
                    "max_output_tokens": max_tok,
                },
            )
            return response.text
        
        elif self.provider == "grok":
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temp,
                max_tokens=max_tok,
            )
            return response.choices[0].message.content or ""
        
        elif self.provider == "qwen":
            from dashscope import Generation
            response = Generation.call(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temp,
                max_tokens=max_tok,
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content or ""
            else:
                raise ValueError(f"Qwen API error: {response.message}")
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    @property
    def model_name(self) -> str:
        """Current model name."""
        return self.model


# Backward compatibility: DebateEvaluatorClient
class DebateEvaluatorClient(MultiLLMClient):
    """Backward compatible client wrapper."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize with settings (backward compatibility)."""
        if settings:
            provider = getattr(settings, 'llm_provider', 'gpt')
            model = getattr(settings, 'openai_model', 'gpt-4o')
            api_key = getattr(settings, 'openai_api_key', None)
            temperature = getattr(settings, 'openai_temperature', 0.3)
            max_tokens = getattr(settings, 'openai_max_tokens', 4096)
            timeout = getattr(settings, 'openai_timeout', 120.0)
        else:
            # Use environment variables
            provider = os.getenv("EVAL_LLM_PROVIDER", "gpt")
            model = os.getenv("EVAL_LLM_MODEL", "gpt-4o")
            api_key = None
            temperature = float(os.getenv("EVAL_LLM_TEMPERATURE", "0.3"))
            max_tokens = int(os.getenv("EVAL_LLM_MAX_TOKENS", "4096"))
            timeout = float(os.getenv("EVAL_LLM_TIMEOUT", "120.0"))
        
        super().__init__(
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

