from __future__ import annotations

from typing import Any

from browser_use.llm.messages import AssistantMessage, BaseMessage, SystemMessage, UserMessage


def serialize_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Convert browser-use messages to the configured Chat Completions wire format."""
    return [_serialize_message(message) for message in messages]


def _serialize_message(message: BaseMessage) -> dict[str, Any]:
    if isinstance(message, UserMessage):
        result = {"role": "user", "content": _serialize_content(message.content)}
    elif isinstance(message, SystemMessage):
        result = {"role": "system", "content": _serialize_content(message.content)}
    elif isinstance(message, AssistantMessage):
        result = {"role": "assistant"}
        if message.content is not None:
            result["content"] = _serialize_content(message.content)
        if message.refusal is not None:
            result["refusal"] = message.refusal
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in message.tool_calls
            ]
    else:  # pragma: no cover - browser-use currently exposes a closed message union
        raise TypeError(f"unsupported browser-use message type: {type(message).__name__}")
    if message.name is not None:
        result["name"] = message.name
    return result


def _serialize_content(content: object) -> object:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return content
    serialized: list[dict[str, Any]] = []
    for part in content:
        if part.type == "text":
            serialized.append({"type": "text", "text": part.text})
        elif part.type == "image_url":
            serialized.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": part.image_url.url,
                        "detail": part.image_url.detail,
                    },
                }
            )
        elif part.type == "refusal":
            serialized.append({"type": "refusal", "refusal": part.refusal})
        else:  # pragma: no cover - browser-use validates the content-part union
            raise TypeError(f"unsupported browser-use content part: {part.type}")
    return serialized
