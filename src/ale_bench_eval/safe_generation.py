from collections.abc import Sequence
from contextlib import nullcontext
from functools import wraps
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, Any

from google.genai.errors import ClientError
from pydantic_ai import (
    Agent,
    ModelHTTPError,
    ModelRetry,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, UserContent
from pydantic_ai.models import openai as pydantic_openai
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIChatModelSettings,
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.models.openrouter import OpenRouterModel, OpenRouterModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.run import AgentRunResult
from pydantic_ai.usage import RequestUsage

from ale_bench_eval.shared_async_loop import shared_async_loop

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.settings import ModelSettings

OPENAI_COMPATIBLE_PROVIDERS = {
    "azure",
    "deepseek",
    "cerebras",
    "fireworks",
    "github",
    "grok",
    "heroku",
    "moonshotai",
    "ollama",
    "openai",
    "openai-chat",
    "together",
    "vercel",
    "litellm",
    "nebius",
    "ovhcloud",
    "gateway",
}

_CACHE_WRITE_PATCH_MARKER = "_ale_bench_cache_write_patch"


def patch_openai_cache_write_tokens() -> None:
    """Preserve GPT-5.6 cache-write usage until genai-prices handles the new field."""
    original_map_usage = pydantic_openai._map_usage  # noqa: SLF001
    if getattr(original_map_usage, _CACHE_WRITE_PATCH_MARKER, False):
        return

    @wraps(original_map_usage)
    def patched_map_usage(
        response: Any,  # noqa: ANN401
        provider: str,
        provider_url: str,
        model: str,
    ) -> RequestUsage:
        mapped_usage = original_map_usage(response, provider, provider_url, model)
        if mapped_usage.cache_write_tokens:
            return mapped_usage

        response_usage = getattr(response, "usage", None)
        if response_usage is None:
            return mapped_usage

        usage_data = response_usage.model_dump(exclude_none=True)
        token_details = usage_data.get("input_tokens_details") or usage_data.get("prompt_tokens_details") or {}
        cache_write_tokens = token_details.get("cache_write_tokens", 0)
        if isinstance(cache_write_tokens, int) and not isinstance(cache_write_tokens, bool) and cache_write_tokens >= 0:
            mapped_usage.cache_write_tokens = cache_write_tokens
        return mapped_usage

    setattr(patched_map_usage, _CACHE_WRITE_PATCH_MARKER, True)
    setattr(pydantic_openai, "_map_usage", patched_map_usage)  # noqa: B010


patch_openai_cache_write_tokens()


class MaxTokenError(RuntimeError):
    pass


def parse_model_config(model_config: dict[str, Any]) -> dict[str, Any]:
    """Parse the model configuration dictionary."""
    required_keys = [("model_name", str), ("provider", str), ("settings", dict)]
    missing_keys = [
        key
        for key, expected_type in required_keys
        if key not in model_config or not isinstance(model_config[key], expected_type)
    ]
    if missing_keys:
        msg = f"Missing or invalid keys in model configuration: {', '.join(missing_keys)}"
        raise ValueError(msg)
    not_allowed_keys = ["timeout"]
    for key in not_allowed_keys:
        if key in model_config["settings"]:
            msg = f"Key '{key}' is not allowed in model configuration settings."
            raise ValueError(msg)
    return model_config


def build_agent_from_config(
    model_config: dict[str, Any],
    system_prompt: str | Sequence[str],
    timeout: float,
    num_retries: int,
) -> Agent:
    """Build an Agent instance from the model configuration dictionary."""
    model_name = model_config["model_name"]
    provider = model_config["provider"]
    settings = model_config["settings"]

    model: Model
    model_settings: ModelSettings
    if provider == "openai":
        model = OpenAIResponsesModel(model_name=model_name)
        model_settings = OpenAIResponsesModelSettings(timeout=timeout, **settings)
    elif provider == "anthropic":
        model = AnthropicModel(model_name=model_name)
        model_settings = AnthropicModelSettings(timeout=timeout, **settings)
    elif provider == "google":
        model = GoogleModel(model_name=model_name)
        model_settings = GoogleModelSettings(timeout=timeout, **settings)
    elif provider == "bedrock":
        model = BedrockConverseModel(model_name=model_name)
        model_settings = BedrockModelSettings(timeout=timeout, **settings)
    elif provider == "openrouter":
        model = OpenRouterModel(model_name=model_name)
        model_settings = OpenRouterModelSettings(timeout=timeout, **settings)
    elif provider in OPENAI_COMPATIBLE_PROVIDERS:
        model = OpenAIChatModel(model_name=model_name, provider=provider)
        model_settings = OpenAIChatModelSettings(timeout=timeout, **settings)
    elif provider == "vllm-chat":
        base_url = model_config.get("base_url")
        api_key = model_config.get("api_key")
        model = OpenAIChatModel(model_name=model_name, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
        model_settings = OpenAIChatModelSettings(timeout=timeout, **settings)
    elif provider == "vllm-responses":
        base_url = model_config.get("base_url")
        api_key = model_config.get("api_key")
        model = OpenAIResponsesModel(model_name=model_name, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
        model_settings = OpenAIResponsesModelSettings(timeout=timeout, **settings)
    else:
        msg = f"Unsupported provider: {provider}"
        raise ValueError(msg)
    return Agent(
        model=model,
        model_settings=model_settings,
        system_prompt=system_prompt,
        retries=num_retries,
    )


def validate_model_response(model_response: ModelMessage) -> None:
    """Validate the final model response and raise if response is unusable."""
    if not isinstance(model_response, ModelResponse):
        msg = "Model did not return a valid response."
        raise TypeError(msg)
    if model_response.finish_reason == "length":
        msg = "Model response was cut off due to length limit."
        raise MaxTokenError(msg)
    if model_response.finish_reason in ["error", "content_filter"]:
        msg = f"Model response ended with finish_reason: {model_response.finish_reason}"
        raise RuntimeError(msg)


def safe_generation(
    model_config: dict[str, Any],
    user_prompt: str | Sequence[UserContent] | None = None,
    message_history: list[ModelMessage] | None = None,
    system_prompt: str | Sequence[str] = (),
    timeout: float = 60.0,
    num_retries: int = 3,
    llm_semaphore: BoundedSemaphore | None = None,
) -> AgentRunResult[str]:
    agent = build_agent_from_config(
        model_config=model_config,
        system_prompt=system_prompt,
        timeout=timeout,
        num_retries=num_retries,
    )

    try:
        with llm_semaphore if llm_semaphore is not None else nullcontext():
            result = shared_async_loop().run(
                agent.run(user_prompt=user_prompt, message_history=message_history),
            )
        model_response = result.all_messages()[-1]
        validate_model_response(model_response)
    except ClientError as e:
        error_message = e.message or ""
        if "exceeds the maximum number of tokens" in error_message:
            msg = "Input exceeds the model's maximum token limit."
            raise MaxTokenError(msg) from e
        msg = f"Model API returned an HTTP error: {e}"
        raise RuntimeError(msg) from e
        # NOTE: If too long string is input, sometime returned `exceeded your current quota`
    except ModelHTTPError as e:
        body = e.body or {}
        msg = ""
        if isinstance(body, dict):
            body_dict: dict[str, Any] = {str(key): value for key, value in body.items()}
            message = body_dict.get("message")
            error = body_dict.get("error")
            if isinstance(message, str):
                msg = message
            elif isinstance(error, dict):
                error_dict: dict[str, Any] = {str(key): value for key, value in error.items()}
                error_message = error_dict.get("message")
                if isinstance(error_message, str):
                    msg = error_message
            if not msg:
                msg = str(body_dict)
        else:
            msg = str(body)
        if any(
            s in msg.lower()
            for s in [
                "string too long",
                "exceeds the context window",
                "maximum context length",
            ]
        ):
            msg = "Input exceeds the model's maximum token limit."
            raise MaxTokenError(msg) from e
        msg = f"Model API returned an HTTP error: {e}"
        raise RuntimeError(msg) from e
        # NOTE: If too long string is input, sometime raised HTTP 500 error
    except MaxTokenError:
        raise
    except UnexpectedModelBehavior as e:
        if isinstance(e.__cause__, ModelRetry):
            msg = f"Function call failed after retries: {e}"
            raise TypeError(msg) from e
        # NOTE: If too long string is input, sometime raised this error and e.message is "Received empty model response"
        # NOTE: Maybe because the token limit is exceeded in internal reasoning and the model returns an empty response
        raise
    except UsageLimitExceeded as e:
        msg = f"Model usage limit exceeded: {e}"
        raise RuntimeError(msg) from e
    except Exception as e:
        msg = f"An unexpected error occurred during model generation: {e}"
        raise RuntimeError(msg) from e
    else:
        return result
