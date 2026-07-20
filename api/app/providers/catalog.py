from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal


ProviderAdapter = Literal["openai", "anthropic", "google", "openai_compat"]


@dataclass(frozen=True, slots=True)
class ApiProviderDefinition:
    key: str
    display_name: str
    adapter: ProviderAdapter
    default_base_url: str
    allowed_domains: tuple[str, ...]
    requires_api_key: bool
    fallback_models: tuple[str, ...]
    supports_reasoning: bool = False
    allow_local_http: bool = False
    supports_json_schema: bool = True


API_PROVIDER_CATALOG: Final[tuple[ApiProviderDefinition, ...]] = (
    ApiProviderDefinition(
        key="openai",
        display_name="OpenAI",
        adapter="openai",
        default_base_url="https://api.openai.com/v1",
        allowed_domains=("api.openai.com",),
        requires_api_key=True,
        fallback_models=("gpt-5.4", "gpt-5.4-mini", "o3", "o4-mini"),
        supports_reasoning=True,
    ),
    ApiProviderDefinition(
        key="anthropic",
        display_name="Anthropic",
        adapter="anthropic",
        default_base_url="https://api.anthropic.com/v1",
        allowed_domains=("api.anthropic.com",),
        requires_api_key=True,
        fallback_models=("claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"),
        supports_reasoning=True,
    ),
    ApiProviderDefinition(
        key="google",
        display_name="Google Gemini",
        adapter="google",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        allowed_domains=("generativelanguage.googleapis.com",),
        requires_api_key=True,
        fallback_models=("gemini-3-pro-preview", "gemini-3-flash-preview"),
        supports_reasoning=True,
    ),
    ApiProviderDefinition(
        key="deepseek",
        display_name="DeepSeek",
        adapter="openai_compat",
        default_base_url="https://api.deepseek.com",
        allowed_domains=("api.deepseek.com",),
        requires_api_key=True,
        fallback_models=("deepseek-chat", "deepseek-reasoner"),
        supports_reasoning=True,
        supports_json_schema=False,
    ),
    ApiProviderDefinition(
        key="kimi",
        display_name="Kimi",
        adapter="openai_compat",
        default_base_url="https://api.moonshot.cn/v1",
        allowed_domains=("api.moonshot.cn",),
        requires_api_key=True,
        fallback_models=("kimi-k2.5", "moonshot-v1-32k"),
        supports_reasoning=True,
        supports_json_schema=False,
    ),
    ApiProviderDefinition(
        key="qwen",
        display_name="Qwen",
        adapter="openai_compat",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        allowed_domains=("dashscope.aliyuncs.com",),
        requires_api_key=True,
        fallback_models=("qwen3-max", "qwen3-coder-plus", "qwen-plus"),
        supports_reasoning=True,
        supports_json_schema=False,
    ),
    ApiProviderDefinition(
        key="openrouter",
        display_name="OpenRouter",
        adapter="openai_compat",
        default_base_url="https://openrouter.ai/api/v1",
        allowed_domains=("openrouter.ai",),
        requires_api_key=True,
        fallback_models=("openai/gpt-5.4", "anthropic/claude-sonnet-4.6"),
        supports_reasoning=True,
    ),
    ApiProviderDefinition(
        key="mistral",
        display_name="Mistral",
        adapter="openai_compat",
        default_base_url="https://api.mistral.ai/v1",
        allowed_domains=("api.mistral.ai",),
        requires_api_key=True,
        fallback_models=("mistral-large-latest", "codestral-latest"),
        supports_json_schema=False,
    ),
    ApiProviderDefinition(
        key="xai",
        display_name="xAI",
        adapter="openai_compat",
        default_base_url="https://api.x.ai/v1",
        allowed_domains=("api.x.ai",),
        requires_api_key=True,
        fallback_models=("grok-4", "grok-4-fast"),
        supports_reasoning=True,
    ),
    ApiProviderDefinition(
        key="ollama",
        display_name="Ollama",
        adapter="openai_compat",
        default_base_url="http://127.0.0.1:11434/v1",
        allowed_domains=("127.0.0.1", "localhost", "::1", "host.docker.internal"),
        requires_api_key=False,
        fallback_models=("llama3.3", "qwen3", "deepseek-r1"),
        allow_local_http=True,
        supports_json_schema=False,
    ),
    ApiProviderDefinition(
        key="openai_compatible",
        display_name="OpenAI-compatible",
        adapter="openai_compat",
        default_base_url="",
        allowed_domains=(),
        requires_api_key=True,
        fallback_models=(),
        supports_reasoning=True,
        supports_json_schema=False,
    ),
)

_API_BY_KEY: Final = {definition.key: definition for definition in API_PROVIDER_CATALOG}


def get_api_provider(provider_key: str) -> ApiProviderDefinition:
    try:
        return _API_BY_KEY[provider_key]
    except KeyError as exc:
        raise ValueError("unsupported_api_provider") from exc


def api_catalog_payload() -> list[dict[str, object]]:
    return [
        {
            "key": definition.key,
            "display_name": definition.display_name,
            "adapter": definition.adapter,
            "default_base_url": definition.default_base_url,
            "allowed_domains": list(definition.allowed_domains),
            "requires_api_key": definition.requires_api_key,
            "fallback_models": list(definition.fallback_models),
            "supports_reasoning": definition.supports_reasoning,
            "allow_local_http": definition.allow_local_http,
            "supports_json_schema": definition.supports_json_schema,
        }
        for definition in API_PROVIDER_CATALOG
    ]
