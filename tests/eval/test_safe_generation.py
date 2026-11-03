import json
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

pytest.importorskip("pydantic_ai", reason="Install ale-bench[eval] to run evaluation tests")

import httpx2
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ThinkingPart, UserPromptPart
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.run import AgentRunResult

from ale_bench_eval import safe_generation as generation
from ale_bench_eval.shared_async_loop import shared_async_loop

MODEL = "inclusionai/ling-3.1-flash"
USAGE = {
    "prompt_tokens": 20,
    "completion_tokens": 8,
    "total_tokens": 28,
    "prompt_tokens_details": {"cached_tokens": 5},
    "completion_tokens_details": {"reasoning_tokens": 6},
}


def config(**overrides: object) -> dict[str, Any]:
    return {
        "model_name": MODEL,
        "provider": "openrouter",
        "settings": {"max_tokens": 262144, "extra_body": {"provider": {"order": ["novita"]}}},
        **overrides,
    }


def chunk(delta: dict[str, Any], finish_reason: str | None = None) -> dict[str, Any]:
    return {
        "id": "gen-test",
        "model": MODEL,
        "created": 1793664000,
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


class ResponseStream(httpx2.AsyncByteStream):
    def __init__(self, events: list[dict[str, Any]], *, read_error: bool = False, done: bool = True) -> None:
        self.events = events
        self.read_error = read_error
        self.closed = False
        self.done = done

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b": OPENROUTER PROCESSING\n\n"
        for event in self.events:
            yield f"data: {json.dumps(event)}\n\n".encode()
        if self.read_error:
            msg = "Connection reset by peer"
            raise httpx2.ReadError(msg)
        if self.done:
            yield b"data: [DONE]\n\n"

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def mock_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Callable[[Callable[[httpx2.Request], httpx2.Response]], None]]:
    clients = []

    def install(handler: Callable[[httpx2.Request], httpx2.Response]) -> None:
        client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        clients.append(client)
        provider = OpenRouterProvider(api_key="offline-test", http_client=client)
        monkeypatch.setattr(generation, "_infer_provider_with_retries", lambda name: provider)

    yield install
    for client in clients:
        shared_async_loop().run(client.aclose())


@pytest.mark.parametrize("stream_setting", [None, True])
@pytest.mark.parametrize("usage_only", [False, True])
def test_streaming_preserves_result_history_usage_and_settings(
    mock_provider: Callable[..., None], stream_setting: bool | None, usage_only: bool
) -> None:
    final_chunk = chunk({}, "stop")
    if usage_only:
        final_chunk["choices"] = []
    final_chunk["usage"] = USAGE  # OpenRouter's final usage chunk repeats the finish reason.
    wire = ResponseStream(
        [
            chunk(
                {
                    "role": "assistant",
                    "reasoning_details": [{"type": "reasoning.text", "text": "Consider the answer.", "index": 0}],
                }
            ),
            chunk({"content": "O"}),
            chunk({"content": "K"}, "stop"),
            final_chunk,
        ]
    )
    requests = []
    semaphore = BoundedSemaphore(1)

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert not semaphore.acquire(blocking=False)
        requests.append(json.loads(request.content))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=wire)

    mock_provider(handler)
    history: list[ModelMessage] = [ModelRequest(parts=[UserPromptPart(content="Earlier prompt")])]
    model_config = config() if stream_setting is None else config(stream=stream_setting)
    result = generation.safe_generation(model_config, "Reply with OK", message_history=history, llm_semaphore=semaphore)
    assert isinstance(result, AgentRunResult)
    assert result.output == "OK"
    assert result.response.finish_reason == "stop"
    assert result.response.provider_response_id == "gen-test"
    assert result.all_messages()[0] == history[0]
    assert len(history) == 1  # Do not mutate the caller's history.
    assert any(isinstance(part, ThinkingPart) for part in result.response.parts)
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 8
    assert result.usage.cache_read_tokens == 5
    assert b"Consider the answer." in result.all_messages_json()
    assert len(requests) == 1
    assert requests[0]["stream"] is True
    assert requests[0]["max_tokens"] == 262144
    assert requests[0]["provider"]["order"] == ["novita"]
    assert wire.closed
    assert semaphore.acquire(blocking=False)
    semaphore.release()


def test_explicit_non_streaming(mock_provider: Callable[..., None]) -> None:
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "id": "gen-test",
                "object": "chat.completion",
                "created": 1793664000,
                "model": MODEL,
                "provider": "Novita",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "OK"}, "finish_reason": "stop"}],
                "usage": USAGE,
            },
        )

    mock_provider(handler)
    result = generation.safe_generation(config(stream=False), "Reply with OK")
    assert isinstance(result, AgentRunResult)
    assert result.output == "OK"
    assert result.usage.output_tokens == 8
    assert len(requests) == 1
    assert requests[0]["stream"] is False


@pytest.mark.parametrize("failure", ["length", "error", "content_filter", "read_error", "sse_error", "eof"])
def test_stream_failure_does_not_return_partial_output_or_fall_back(
    mock_provider: Callable[..., None], failure: str
) -> None:
    events = [chunk({"role": "assistant", "content": "partial answer"})]
    if failure in {"length", "error", "content_filter"}:
        events.append(chunk({}, failure))
    elif failure == "sse_error":
        events.append({"error": {"code": 504, "message": "A Timeout Occurred"}})
    wire = ResponseStream(events, read_error=failure == "read_error")
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=wire)

    mock_provider(handler)
    semaphore = BoundedSemaphore(1)
    expected = {
        "length": (generation.MaxTokenError, "cut off"),
        "error": (RuntimeError, "finish_reason: error"),
        "content_filter": (RuntimeError, "finish_reason: content_filter"),
        "read_error": (RuntimeError, "model generation"),
        "sse_error": (RuntimeError, "504"),
        "eof": (UnexpectedModelBehavior, "without a provider finish reason"),
    }
    error_type, message = expected[failure]
    with pytest.raises(error_type, match=message):
        generation.safe_generation(config(), "Reply", llm_semaphore=semaphore)
    assert len(requests) == 1
    assert requests[0]["stream"] is True
    assert wire.closed
    assert semaphore.acquire(blocking=False)
    semaphore.release()


@pytest.mark.parametrize("value", ["false", "true", None, 0, 1, {}, []])
def test_invalid_stream_setting(value: object) -> None:
    with pytest.raises(ValueError, match="must be a boolean"):
        generation.safe_generation(config(stream=value), "Not sent")


@pytest.mark.parametrize("settings", [{"stream": True}, {"extra_body": {"stream": False}}])
def test_reject_stream_in_api_settings(settings: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="top level"):
        generation.parse_model_config(config(settings=settings))


def test_existing_model_configs_are_valid() -> None:
    paths = list((Path(__file__).resolve().parents[2] / "llm_configs").glob("*.json"))
    assert paths
    for path in paths:
        generation.parse_model_config(json.loads(path.read_text()))


@pytest.mark.parametrize("finish", [True, False])
@pytest.mark.parametrize("done", [True, False])
def test_openai_compatible_stream_requires_actual_finish_reason(
    monkeypatch: pytest.MonkeyPatch, finish: bool, done: bool
) -> None:
    events = [chunk({"role": "assistant", "content": "OK"})]
    if finish:
        events.append(chunk({}, "stop"))
        events[-1]["usage"] = USAGE
    wire = ResponseStream(events, done=done)
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=wire)

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    provider = OpenAIProvider(api_key="offline-test", http_client=client)
    monkeypatch.setattr(generation, "OpenAIProvider", lambda **kwargs: provider)
    try:
        if finish:
            result = generation.safe_generation(config(provider="vllm-chat"), "Reply")
            assert isinstance(result, AgentRunResult)
            assert result.output == "OK"
            assert result.usage.output_tokens == 8
        else:
            with pytest.raises(UnexpectedModelBehavior, match="without a provider finish reason"):
                generation.safe_generation(config(provider="vllm-chat"), "Reply")
        assert len(requests) == 1
        assert requests[0]["stream"] is True
        assert wire.closed
    finally:
        shared_async_loop().run(client.aclose())


def test_pre_stream_http_error(mock_provider: Callable[..., None]) -> None:
    requests = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        return httpx2.Response(504, json={"error": {"code": 504, "message": "A Timeout Occurred"}})

    mock_provider(handler)
    with pytest.raises(RuntimeError, match="504"):
        generation.safe_generation(config(), "Reply")
    assert requests
    assert all(request["stream"] is True for request in requests)


@pytest.mark.parametrize("raw_reason", ["stop", "completed", "end_turn", "STOP"])
def test_stream_terminal_metadata_across_providers(
    stub_agent: Callable[[ModelResponse], Mock], raw_reason: str
) -> None:
    response = ModelResponse(
        parts=[TextPart(content="OK")],
        finish_reason="stop",
        provider_details={"finish_reason": raw_reason},
    )
    agent = stub_agent(response)
    result = generation.safe_generation(config(), "Reply")
    assert result.response is response
    agent.run.assert_not_awaited()
    agent.run_stream.assert_called_once()


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google", "openrouter", "together", "vllm-chat"])
@pytest.mark.parametrize("stream", [True, False])
def test_synthesized_stop_is_not_proof_of_stream_completion(
    stub_agent: Callable[[ModelResponse], Mock], provider: str, stream: bool
) -> None:
    response = ModelResponse(parts=[TextPart(content="partial answer")], finish_reason="stop", provider_name=provider)
    agent = stub_agent(response)
    model_config = config(provider=provider, stream=stream)
    if stream:
        with pytest.raises(UnexpectedModelBehavior, match="without a provider finish reason"):
            generation.safe_generation(model_config, "Reply")
        agent.run.assert_not_awaited()
        agent.run_stream.assert_called_once()
    else:
        # Explicit non-streaming opt-out retains the existing response validation.
        result = generation.safe_generation(model_config, "Reply")
        assert result.response is response
        agent.run.assert_awaited_once()
        agent.run_stream.assert_not_called()


@pytest.fixture
def stub_agent(monkeypatch: pytest.MonkeyPatch) -> Callable[[ModelResponse], Mock]:
    """Exercise generation branching with provider-normalized responses, without network calls."""

    def install(response: ModelResponse) -> Mock:
        result = Mock(spec=AgentRunResult, response=response)
        result.all_messages.return_value = [response]
        stream = Mock(result=result, get_output=AsyncMock())
        stream_context = MagicMock()
        stream_context.__aenter__.return_value = stream
        agent = Mock(run=AsyncMock(return_value=result))
        agent.run_stream.return_value = stream_context
        monkeypatch.setattr(generation, "build_agent_from_config", lambda **kwargs: agent)
        return agent

    return install
