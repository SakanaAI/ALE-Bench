from collections.abc import Sequence
from typing import Any

from google.genai.errors import ClientError
from pydantic_ai import (
    Agent,
    ModelHTTPError,
    ModelRetry,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, UserContent
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.models.bedrock import BedrockConverseModel, BedrockModelSettings
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIChatModelSettings,
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.run import AgentRunResult
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
    "openrouter",
    "together",
    "vercel",
    "litellm",
}


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
        raise ValueError(f"Missing or invalid keys in model configuration: {', '.join(missing_keys)}")
    not_allowed_keys = ["timeout"]
    for key in not_allowed_keys:
        if key in model_config["settings"]:
            raise ValueError(f"Key '{key}' is not allowed in model configuration settings.")
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
        model_settings = OpenAIResponsesModelSettings(timeout=timeout, **settings)  # type: ignore[typeddict-item]
    elif provider == "anthropic":
        model = AnthropicModel(model_name=model_name)
        model_settings = AnthropicModelSettings(timeout=timeout, **settings)  # type: ignore[typeddict-item]
    elif provider == "google":
        model = GoogleModel(model_name=model_name)
        model_settings = GoogleModelSettings(timeout=timeout, **settings)  # type: ignore[typeddict-item]
    elif provider == "bedrock":
        model = BedrockConverseModel(model_name=model_name)
        model_settings = BedrockModelSettings(timeout=timeout, **settings)  # type: ignore[typeddict-item]
    elif provider in OPENAI_COMPATIBLE_PROVIDERS:
        model = OpenAIChatModel(model_name=model_name, provider=provider)
        model_settings = OpenAIChatModelSettings(timeout=timeout, **settings)  # type: ignore[typeddict-item]
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    agent = Agent(
        model=model,
        model_settings=model_settings,
        system_prompt=system_prompt,
        retries=num_retries,
    )
    return agent


def safe_generation(
    model_config: dict[str, Any],
    user_prompt: str | Sequence[UserContent] | None = None,
    message_history: list[ModelMessage] | None = None,
    system_prompt: str | Sequence[str] = (),
    timeout: float = 60.0,
    num_retries: int = 3,
) -> AgentRunResult[str]:
    agent = build_agent_from_config(
        model_config=model_config,
        system_prompt=system_prompt,
        timeout=timeout,
        num_retries=num_retries,
    )

    try:
        result = agent.run_sync(user_prompt=user_prompt, message_history=message_history)
        model_response = result.all_messages()[-1]
        if isinstance(model_response, ModelResponse):
            if model_response.finish_reason == "length":
                raise MaxTokenError("Model response was cut off due to length limit.")
            elif model_response.finish_reason in ["error", "content_filter"]:
                raise RuntimeError(f"Model response ended with finish_reason: {model_response.finish_reason}")
        else:
            raise RuntimeError("Model did not return a valid response.")
        return result
    except ClientError as e:
        if "exceeds the maximum number of tokens" in e.message:  # type: ignore
            raise MaxTokenError("Input exceeds the model's maximum token limit.") from e
        raise RuntimeError(f"Model API returned an HTTP error: {e}") from e
        # NOTE: If too long string is input, sometime returned `exceeded your current quota`
    except ModelHTTPError as e:
        if any(
            [
                "string too long" in e.body["message"],  # type: ignore
                "exceeds the context window" in e.body["message"],  # type: ignore
                "maximum context length" in e.body["message"],  # type: ignore
            ]
        ):
            raise MaxTokenError("Input exceeds the model's maximum token limit.") from e
        raise RuntimeError(f"Model API returned an HTTP error: {e}") from e
        # NOTE: If too long string is input, sometime raised HTTP 500 error
    except MaxTokenError:
        raise
    except UnexpectedModelBehavior as e:
        if isinstance(e.__cause__, ModelRetry):
            raise RuntimeError(f"Function call failed after retries: {e}") from e
        # NOTE: If too long string is input, sometime raised this error and e.message is "Received empty model response"
        # NOTE: Maybe because the token limit is exceeded in internal reasoning and the model returns an empty response
        raise
    except UsageLimitExceeded as e:
        raise RuntimeError(f"Model usage limit exceeded: {e}") from e
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred during model generation: {e}") from e
