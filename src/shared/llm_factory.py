"""LLM Factory for supporting multiple LLM providers."""

import os
from typing import Optional, Literal
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatTongyi

from ..shared.utils import setup_logging

logger = setup_logging(__name__)

# Supported LLM providers
LLMProvider = Literal["gpt", "grok", "gemini", "claude", "qwen"]

# Default models for each provider
DEFAULT_MODELS = {
    "gpt": "gpt-4o-mini",
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
    "qwen": "DASHSCOPE_API_KEY",  # Alibaba Cloud DashScope
}


def get_llm(
    provider: LLMProvider,
    model: Optional[str] = None,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> any:
    """Create an LLM instance for the specified provider.
    
    Args:
        provider: LLM provider name (gpt, grok, gemini, claude, qwen)
        model: Model name (defaults to provider's default model)
        temperature: Temperature for generation
        api_key: API key (defaults to environment variable)
        
    Returns:
        LangChain LLM instance
        
    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported LLM provider: {provider}. Supported: {list(DEFAULT_MODELS.keys())}")
    
    # Get model name
    if model is None:
        model = DEFAULT_MODELS[provider]
    
    # Get API key
    if api_key is None:
        env_var = API_KEY_ENV_VARS[provider]
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set for {provider}")
    
    logger.info(f"Initializing {provider} LLM with model: {model}")
    
    # Create LLM instance based on provider
    if provider == "gpt":
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            temperature=temperature,
        )
    elif provider == "grok":
        return ChatGroq(
            model=model,
            groq_api_key=api_key,
            temperature=temperature,
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )
    elif provider == "claude":
        return ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            temperature=temperature,
        )
    elif provider == "qwen":
        return ChatTongyi(
            model=model,
            dashscope_api_key=api_key,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def get_llm_from_config(
    config_key: str = "DEBATE_LLM_PROVIDER",
    default_provider: LLMProvider = "gpt",
    model: Optional[str] = None,
    temperature: float = 0.7,
) -> any:
    """Get LLM from environment configuration.
    
    Args:
        config_key: Environment variable name for provider selection
        default_provider: Default provider if not specified
        model: Model name (optional, uses provider default if not specified)
        temperature: Temperature for generation
        
    Returns:
        LangChain LLM instance
    """
    provider_str = os.getenv(config_key, default_provider).lower()
    
    # Map common aliases
    provider_map = {
        "openai": "gpt",
        "gpt-4": "gpt",
        "gpt-3.5": "gpt",
        "anthropic": "claude",
        "google": "gemini",
        "alibaba": "qwen",
        "dashscope": "qwen",
    }
    
    provider = provider_map.get(provider_str, provider_str)
    
    if provider not in DEFAULT_MODELS:
        logger.warning(f"Unknown provider '{provider_str}', using default: {default_provider}")
        provider = default_provider
    
    return get_llm(provider, model=model, temperature=temperature)

