"""Console entry point: reads input, prints replies, carries history, exits on the exit word."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

from cyborg_ant.config import Config
from cyborg_ant.logbook import Logbook, new_run_id
from cyborg_ant.loop import RequestOutcome, run_request
from cyborg_ant.model_client import ModelClient
from cyborg_ant.prompts import SYSTEM_PROMPT
from cyborg_ant.sandbox import SandboxProbeResult, probe
from cyborg_ant.session import Session, StopReason
from cyborg_ant.tools import ToolRegistry, build_registry


def main() -> None:
    load_dotenv()
    config = Config(project_root=Path.cwd())
    sandbox = probe(config.project_root)
    if not sandbox.available:
        print(f"[run_bash is not available: {sandbox.reason}]")
    session = _init_session(config, sandbox)
    registry = build_registry(config, confirm=_confirm, sandbox_available=sandbox.available)
    model_client = ModelClient(config)

    _run_session(session, config, model_client, registry)


def _run_session(
    session: Session,
    config: Config,
    model_client: ModelClient,
    registry: ToolRegistry,
    *,
    repl_loop: Callable[[Session, Config, ModelClient, ToolRegistry, list[int]], None]
    | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Run the REPL to completion, closing the log with a stop reason no matter how it ends.

    SIGINT's default handler raises KeyboardInterrupt in the main thread; catching it here (not
    swallowing it further down) is what lets the `finally` below always write `session_end`.
    """
    repl_loop = repl_loop or _repl_loop
    session_started = clock()
    counter = [0]
    via = "exit_word"
    try:
        repl_loop(session, config, model_client, registry, counter)
    except KeyboardInterrupt:
        via = "sigint"
        print("\n[interrupted]")
    finally:
        session.logbook.emit(
            "session_end",
            stop_reason=StopReason.USER_EXIT.value,
            via=via,
            requests=counter[0],
            duration_seconds=clock() - session_started,
        )
        session.logbook.close()


def _confirm(prompt: str) -> bool:
    print(prompt)
    answer = input("> ").strip().lower()
    return answer in ("y", "yes")


def _init_session(config: Config, sandbox: SandboxProbeResult) -> Session:
    run_id = new_run_id()
    log_path = config.project_root / ".agent_runs" / f"{run_id}.jsonl"
    logbook = Logbook(log_path, run_id=run_id, cap_bytes=config.log_value_cap_bytes)
    logbook.emit(
        "session_start",
        project_root=str(config.project_root),
        config=_config_log_fields(config),
        sandbox={"available": sandbox.available, "backend": "bwrap", "version": sandbox.version},
    )
    return Session(run_id=run_id, logbook=logbook)


def _config_log_fields(config: Config) -> dict:
    return {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "effort": config.effort,
        "retry_attempts": config.retry_attempts,
        "backoff_base_seconds": config.backoff_base_seconds,
        "backoff_ratio": config.backoff_ratio,
        "command_timeout_seconds": config.command_timeout_seconds,
        "max_iterations": config.max_iterations,
        "read_word_ceiling": config.read_word_ceiling,
    }


def _repl_loop(
    session: Session,
    config: Config,
    model_client: ModelClient,
    registry: ToolRegistry,
    counter: list[int],
) -> None:
    """Run the REPL, tallying requests into `counter[0]` so it survives a KeyboardInterrupt."""
    while True:
        try:
            user_text = input("you: ")
        except EOFError:
            return
        if user_text.strip() == config.exit_word:
            return

        counter[0] += 1
        outcome = run_request(
            session,
            user_text,
            request_id=f"req-{counter[0]}",
            config=config,
            model_client=model_client,
            registry=registry,
            system_prompt=SYSTEM_PROMPT,
        )
        _print_outcome(outcome)


def _print_outcome(outcome: RequestOutcome) -> None:
    if outcome.answer_text:
        print(f"agent: {outcome.answer_text}")
    if outcome.truncated:
        print("[cut short by the token budget]")
    if outcome.stop_reason != StopReason.ANSWERED:
        print(f"[request ended: {outcome.stop_reason.value}]")


if __name__ == "__main__":
    main()
