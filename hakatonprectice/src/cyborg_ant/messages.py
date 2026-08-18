"""Projects Session.turns into the API `messages` array."""

from __future__ import annotations

from cyborg_ant.session import Session, Turn


def project_messages(session: Session) -> list[dict]:
    """Project Session.turns into the API `messages` array."""
    messages: list[dict] = []
    turns = session.turns
    i = 0
    while i < len(turns):
        turn = turns[i]
        if turn.kind == "user":
            messages.append({"role": "user", "content": turn.text})
            i += 1
        elif turn.kind == "agent":
            message, i = _consume_assistant_group(turns, i)
            messages.append(message)
        elif turn.kind == "tool_result":
            message, i = _consume_tool_result_group(turns, i)
            messages.append(message)
        else:
            i += 1
    return messages


def _consume_assistant_group(turns: list[Turn], start: int) -> tuple[dict, int]:
    """One agent turn plus any tool_request turns immediately following it."""
    agent_turn = turns[start]
    content: list[dict] = []
    if agent_turn.text:
        content.append({"type": "text", "text": agent_turn.text})

    i = start + 1
    while i < len(turns) and turns[i].kind == "tool_request":
        call = turns[i]
        content.append(
            {
                "type": "tool_use",
                "id": call.tool_use_id,
                "name": call.name,
                "input": call.arguments,
            }
        )
        i += 1
    return {"role": "assistant", "content": content}, i


def _consume_tool_result_group(turns: list[Turn], start: int) -> tuple[dict, int]:
    """A run of consecutive tool_result turns, all in one user message."""
    content: list[dict] = []
    i = start
    while i < len(turns) and turns[i].kind == "tool_result":
        result_turn = turns[i]
        content.append(
            {
                "type": "tool_result",
                "tool_use_id": result_turn.tool_use_id,
                "content": result_turn.result.content,
                "is_error": result_turn.result.is_error,
            }
        )
        i += 1
    return {"role": "user", "content": content}, i
