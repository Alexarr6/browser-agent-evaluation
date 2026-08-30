from browser_use.llm.messages import AssistantMessage, Function, ToolCall, UserMessage

from browser_agent_evaluation.agents.browser_use.serialization import serialize_messages


def test_serializes_browser_use_messages_without_provider_specific_serializer() -> None:
    messages = [
        UserMessage(content="Inspect the page"),
        AssistantMessage(
            content=None,
            tool_calls=[
                ToolCall(
                    id="call-1",
                    function=Function(name="browser_click", arguments='{"target":"e1"}'),
                )
            ],
        ),
    ]

    assert serialize_messages(messages) == [
        {"role": "user", "content": "Inspect the page"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "browser_click",
                        "arguments": '{"target":"e1"}',
                    },
                }
            ],
        },
    ]
