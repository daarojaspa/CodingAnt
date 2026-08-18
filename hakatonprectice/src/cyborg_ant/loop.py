"""Runs one user request to an answer or a stated stop reason."""

from __future__ import annotations

import time
from collections.abc import Callable

from cyborg_ant.config import Config
from cyborg_ant.errors import RetriesExhaustedError
from cyborg_ant.messages import project_messages
from cyborg_ant.model_client import ModelClient, ModelResponse
from cyborg_ant.request_tracker import RequestOutcome, RequestTracker
from cyborg_ant.retry import RetryPolicy, Sleeper
from cyborg_ant.session import Session, StopReason, Turn, Usage
from cyborg_ant.tool_dispatch import execute_tool_calls
from cyborg_ant.tools import ToolRegistry

REFUSAL_MARKER = "REFUSAL:"


def _refusal_rule(text: str | None) -> str | None:
    """The rule name if `text` opens with the constitution refusal marker, else None."""
    if text is None or not text.startswith(REFUSAL_MARKER):
        return None
    return text[len(REFUSAL_MARKER) :].splitlines()[0].strip()


def run_request(
    session: Session,
    user_text: str,
    *,
    request_id: str,
    config: Config,
    model_client: ModelClient,
    registry: ToolRegistry,
    system_prompt: str,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Sleeper = time.sleep,
) -> RequestOutcome:
    """Drive one user request through the model/tool loop to an answer or a stop reason."""
    session.append(Turn(kind="user", text=user_text))
    session.logbook.emit("request_start", request_id=request_id, user_text=user_text)
    _log_turn(session, request_id, -1, "user", text=user_text)

    tracker = RequestTracker(session, request_id, clock)
    tool_retry_policy = RetryPolicy(
        attempts=config.retry_attempts,
        base_seconds=config.backoff_base_seconds,
        ratio=config.backoff_ratio,
    )

    for iteration in range(config.max_iterations):
        try:
            response = _call_model(
                model_client, session, request_id, iteration, system_prompt, registry, tracker
            )
        except RetriesExhaustedError as exc:
            return tracker.finish(
                StopReason.RETRIES_EXHAUSTED,
                None,
                iteration + 1,
                retry_attempts=exc.attempts,
                retry_waits=exc.waits,
            )

        outcome = _handle_response(session, request_id, iteration, response, tracker)
        if outcome is not None:
            return outcome

        execute_tool_calls(
            session,
            response.tool_calls,
            registry,
            request_id=request_id,
            iteration=iteration,
            sleeper=sleeper,
            clock=clock,
            retry_policy=tool_retry_policy,
            tracker=tracker,
        )

    return tracker.finish(StopReason.ITERATION_CAP_REACHED, None, config.max_iterations)


def _call_model(
    model_client: ModelClient,
    session: Session,
    request_id: str,
    iteration: int,
    system_prompt: str,
    registry: ToolRegistry,
    tracker: RequestTracker,
) -> ModelResponse:
    def on_retry(attempt: int, of: int, error_type: str, wait: float) -> None:
        tracker.record_retry(wait)
        _log_retry(session, request_id, iteration, "model_call", attempt, of, error_type, wait)

    return model_client.create(
        system=system_prompt,
        messages=project_messages(session),
        tools=registry.schemas(),
        on_retry=on_retry,
    )


def _handle_response(
    session: Session,
    request_id: str,
    iteration: int,
    response: ModelResponse,
    tracker: RequestTracker,
) -> RequestOutcome | None:
    """Append/log the response and, if it ends the request, return its outcome — else None."""
    _append_agent_turn(session, response)
    _log_turn(
        session,
        request_id,
        iteration,
        "agent",
        text=response.text,
        stop_reason=response.stop_reason,
        usage=response.usage,
    )
    tracker.record_response(response)

    if response.stop_reason == "max_tokens" and not response.tool_calls:
        return tracker.finish(StopReason.TOKEN_CAP_REACHED, response.text, iteration + 1)
    if not response.tool_calls:
        rule = _refusal_rule(response.text)
        if rule is not None:
            return tracker.finish(StopReason.REFUSED, response.text, iteration + 1, rule=rule)
        return tracker.finish(StopReason.ANSWERED, response.text, iteration + 1)
    return None


def _log_turn(
    session: Session, request_id: str, iteration: int, kind: str, **fields: object
) -> None:
    session.logbook.emit("turn", request_id=request_id, iteration=iteration, kind=kind, **fields)


def _log_retry(
    session: Session,
    request_id: str,
    iteration: int,
    operation: str,
    attempt: int,
    of: int,
    error_type: str,
    wait_seconds: float,
) -> None:
    session.logbook.emit(
        "retry",
        request_id=request_id,
        iteration=iteration,
        operation=operation,
        attempt=attempt,
        of=of,
        error_type=error_type,
        wait_seconds=wait_seconds,
    )


def _append_agent_turn(session: Session, response: ModelResponse) -> None:
    session.append(
        Turn(
            kind="agent",
            text=response.text,
            stop_reason=response.stop_reason,
            usage=Usage(**response.usage),
        )
    )
    for call in response.tool_calls:
        session.append(
            Turn(
                kind="tool_request",
                tool_use_id=call["id"],
                name=call["name"],
                arguments=call["input"],
            )
        )
