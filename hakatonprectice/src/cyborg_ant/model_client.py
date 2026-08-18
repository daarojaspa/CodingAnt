"""Wraps the Anthropic SDK; owns request shape, retries, and stop_reason."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import anthropic

from cyborg_ant.config import Config
from cyborg_ant.errors import RETRYABLE_MODEL_ERRORS
from cyborg_ant.retry import Clock, OnRetry, RetryPolicy, Sleeper, call_with_retry


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[dict[str, Any]]
    stop_reason: str
    usage: dict[str, int]


class ModelClient:
    """Thin wrapper around the Anthropic SDK. The SDK's own retry loop is disabled; ours runs."""

    def __init__(
        self,
        config: Config,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        sleeper: Sleeper = time.sleep,
        clock: Clock = time.monotonic,
        on_retry: OnRetry | None = None,
    ) -> None:
        self._config = config
        self._client = client or anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=60.0)
        self._sleeper = sleeper
        self._clock = clock
        self._on_retry = on_retry
        self._policy = RetryPolicy(
            attempts=config.retry_attempts,
            base_seconds=config.backoff_base_seconds,
            ratio=config.backoff_ratio,
        )

    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_retry: OnRetry | None = None,
    ) -> ModelResponse:
        response = call_with_retry(
            lambda: self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                system=system,
                messages=messages,
                tools=tools,
                output_config={"effort": self._config.effort},
            ),
            retryable=RETRYABLE_MODEL_ERRORS,
            policy=self._policy,
            sleeper=self._sleeper,
            clock=self._clock,
            on_retry=on_retry or self._on_retry,
        )
        return _to_model_response(response)


def _to_model_response(response: Any) -> ModelResponse:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append({"id": block.id, "name": block.name, "input": block.input})

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0)
        or 0,
    }

    return ModelResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=response.stop_reason,
        usage=usage,
    )
