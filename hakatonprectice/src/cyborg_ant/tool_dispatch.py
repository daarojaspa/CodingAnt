"""Executes tool_use blocks against the registry, with a bounded retry on transient OSErrors."""

from __future__ import annotations

import time

from cyborg_ant.errors import RETRYABLE_TOOL_ERRORS, RetriesExhaustedError
from cyborg_ant.request_tracker import RequestTracker
from cyborg_ant.retry import Clock, RetryPolicy, Sleeper, call_with_retry
from cyborg_ant.session import Session, Turn
from cyborg_ant.tools import ToolRegistry, ToolResult


def execute_tool_calls(
    session: Session,
    tool_calls: list[dict],
    registry: ToolRegistry,
    *,
    request_id: str,
    iteration: int,
    sleeper: Sleeper = time.sleep,
    clock: Clock = time.monotonic,
    retry_policy: RetryPolicy | None = None,
    tracker: RequestTracker | None = None,
) -> None:
    """Execute every tool_use block from one response; append every result before returning."""
    for call in tool_calls:
        session.logbook.emit(
            "tool_call",
            request_id=request_id,
            iteration=iteration,
            tool_use_id=call["id"],
            name=call["name"],
            arguments=call["input"],
        )
        start = time.perf_counter()
        result = _dispatch_with_retry(
            call, registry, session, request_id, iteration, sleeper, clock, retry_policy, tracker
        )
        duration = time.perf_counter() - start
        session.append(Turn(kind="tool_result", tool_use_id=call["id"], result=result))
        session.logbook.emit(
            "tool_result",
            request_id=request_id,
            iteration=iteration,
            tool_use_id=call["id"],
            name=call["name"],
            outcome=result.outcome,
            duration_seconds=duration,
            content=result.content,
            metadata=result.metadata,
        )


def _dispatch_with_retry(
    call: dict,
    registry: ToolRegistry,
    session: Session,
    request_id: str,
    iteration: int,
    sleeper: Sleeper,
    clock: Clock,
    retry_policy: RetryPolicy | None,
    tracker: RequestTracker | None,
) -> ToolResult:
    """Retry a tool call that raises a transient OSError. Tools never raise for handled errors."""
    if retry_policy is None:
        return _dispatch(call, registry)

    def on_retry(attempt: int, of: int, error_type: str, wait: float) -> None:
        if tracker is not None:
            tracker.record_retry(wait)
        session.logbook.emit(
            "retry",
            request_id=request_id,
            iteration=iteration,
            operation="tool_call",
            attempt=attempt,
            of=of,
            error_type=error_type,
            wait_seconds=wait,
        )

    try:
        return call_with_retry(
            lambda: _dispatch(call, registry),
            retryable=RETRYABLE_TOOL_ERRORS,
            policy=retry_policy,
            sleeper=sleeper,
            clock=clock,
            on_retry=on_retry,
        )
    except RetriesExhaustedError as exc:
        return ToolResult(
            outcome="error",
            content=f"tool '{call['name']}' failed after {exc.attempts} attempts: {exc}",
        )


def _dispatch(call: dict, registry: ToolRegistry) -> ToolResult:
    spec = registry.get(call["name"])
    if spec is None:
        return ToolResult(outcome="invalid", content=f"unknown tool '{call['name']}'")
    return spec.func(call["input"])
