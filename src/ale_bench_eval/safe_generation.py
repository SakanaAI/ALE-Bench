from collections.abc import Sequence
from contextlib import nullcontext
from threading import BoundedSemaphore
from typing import TYPE_CHECKING, Any

from google.genai.errors import ClientError
from google.genai.types import HttpRetryOptions
from pydantic_ai import (
    Agent,
    ModelHTTPError,
    ModelRetry,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, UserContent
from pydantic_ai.models import infer_model
from pydantic_ai.models.openai import (
    OpenAIChatModel,
    OpenAIResponsesModel,
)
from pydantic_ai.providers import infer_provider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.run import AgentRunResult
from pydantic_ai.settings import ModelSettings

from ale_bench_eval.shared_async_loop import shared_async_loop

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.providers import Provider


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


def _infer_provider_with_retries(provider_name: str) -> "Provider[Any]":
    if provider_name == "google":
        return GoogleProvider(
            retry_options=HttpRetryOptions(
                attempts=4,  # Initial request plus three retries; separate from Agent validation retries.
                initial_delay=2,
                exp_base=2,
                max_delay=30,
                jitter=1,
                http_status_codes=[502, 503, 504],
            ),
        )
    return infer_provider(provider_name)


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
    if provider == "vllm-chat":
        base_url = model_config.get("base_url")
        api_key = model_config.get("api_key")
        model = OpenAIChatModel(model_name=model_name, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
    elif provider == "vllm-responses":
        base_url = model_config.get("base_url")
        api_key = model_config.get("api_key")
        model = OpenAIResponsesModel(model_name=model_name, provider=OpenAIProvider(base_url=base_url, api_key=api_key))
    else:
        model = infer_model(f"{provider}:{model_name}", provider_factory=_infer_provider_with_retries)
    # Settings types are TypedDicts; provider-specific keys remain intact at runtime.
    model_settings = ModelSettings(timeout=timeout, **settings)
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
