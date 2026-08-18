"""ToolResult and the tool registry: schemas out, dispatch in."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from cyborg_ant.config import Config
    from cyborg_ant.tools.write_file import ConfirmFn

Outcome = Literal["ok", "error", "refused", "invalid"]


@dataclass
class ToolResult:
    """The observation returned from one tool invocation, on every path."""

    outcome: Outcome
    content: str
    metadata: dict = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return self.outcome != "ok"


ToolCallable = Callable[[dict], ToolResult]


@dataclass
class ToolSpec:
    schema: dict
    func: ToolCallable


class ToolRegistry:
    """Name -> (json_schema, callable). The only place all tool names appear together."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, schema: dict, func: ToolCallable) -> None:
        self._tools[name] = ToolSpec(schema=schema, func=func)

    def schemas(self) -> list[dict]:
        return [spec.schema for spec in self._tools.values()]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def build_registry(
    config: Config, *, confirm: ConfirmFn, sandbox_available: bool = False
) -> ToolRegistry:
    """Build the tool registry for one session.

    `run_bash` is registered only when `sandbox_available` is True — omitted entirely, not
    degraded, when the startup probe failed (research §R1).
    """
    from cyborg_ant.tools.read_file import SCHEMA as READ_FILE_SCHEMA
    from cyborg_ant.tools.read_file import read_file
    from cyborg_ant.tools.write_file import SCHEMA as WRITE_FILE_SCHEMA
    from cyborg_ant.tools.write_file import write_file

    registry = ToolRegistry()
    registry.register("read_file", READ_FILE_SCHEMA, partial(read_file, config=config))
    registry.register(
        "write_file", WRITE_FILE_SCHEMA, partial(write_file, config=config, confirm=confirm)
    )

    if sandbox_available:
        from cyborg_ant.tools.run_bash import SCHEMA as RUN_BASH_SCHEMA
        from cyborg_ant.tools.run_bash import run_bash

        registry.register("run_bash", RUN_BASH_SCHEMA, partial(run_bash, config=config))

    return registry
