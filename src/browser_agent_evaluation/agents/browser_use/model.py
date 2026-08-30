from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, TypeVar, overload

import httpx

# browser-use calls load_dotenv() during import; runtime credentials are injected explicitly.
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")

from browser_use.llm.base import BaseChatModel  # noqa: E402
from browser_use.llm.exceptions import ModelProviderError, ModelRateLimitError  # noqa: E402
from browser_use.llm.messages import BaseMessage  # noqa: E402
from browser_use.llm.schema import SchemaOptimizer  # noqa: E402
from browser_use.llm.views import ChatInvokeCompletion, ChatInvokeUsage  # noqa: E402
from pydantic import BaseModel, ValidationError

from browser_agent_evaluation.agents.browser_use.serialization import serialize_messages
from browser_agent_evaluation.core.budget import ModelBudget
from browser_agent_evaluation.core.pricing import provider_cost_or_model_estimate
from browser_agent_evaluation.providers.chat_completions import DEFAULT_MODEL

T = TypeVar("T", bound=BaseModel)


@dataclass
class BrowserUseChatModel(BaseChatModel):
    """Adapt browser-use to a configured Chat Completions endpoint."""

    _verified_api_keys = True

    api_key: str
    http_client: httpx.AsyncClient
    budget: ModelBudget
    trial_id: str
    endpoint: str
    model: str = DEFAULT_MODEL
    max_completion_tokens: int | None = None
    last_raw_content: str = field(default="", init=False)
    response_diagnostics: list[str] = field(default_factory=list, init=False)

    @property
    def provider(self) -> str:
        return "configured-chat-completions"

    @property
    def name(self) -> str:
        return self.model

    @property
    def model_name(self) -> str:
        return self.model

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: None = None, **kwargs: Any
    ) -> ChatInvokeCompletion[str]: ...

    @overload
    async def ainvoke(
        self, messages: list[BaseMessage], output_format: type[T], **kwargs: Any
    ) -> ChatInvokeCompletion[T]: ...

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        output_format: type[T] | None = None,
        **kwargs: Any,
    ) -> ChatInvokeCompletion[T] | ChatInvokeCompletion[str]:
        serialized = serialize_messages(messages)
        if output_format is not None:
            schema = SchemaOptimizer.create_optimized_json_schema(output_format)
            serialized.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "Return exactly one JSON object matching this schema. The response must be "
                        "valid json and must not be wrapped in Markdown. JSON schema: "
                        + json.dumps(schema, separators=(",", ":"))
                    ),
                },
            )
        self.budget.before_request(self.trial_id)
        request_payload: dict[str, object] = {
            "model": self.model,
            "messages": serialized,
        }
        if output_format is not None:
            request_payload["response_format"] = {"type": "json_object"}
        if self.max_completion_tokens is not None:
            request_payload["max_completion_tokens"] = self.max_completion_tokens
        response = await self.http_client.post(
            f"{self.endpoint.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=request_payload,
            timeout=120,
        )
        if response.status_code == 429:
            raise ModelRateLimitError(message="provider rate limit", model=self.name)
        if response.is_error:
            body = response.text[:1_000]
            detail = f": {body}" if body else ""
            raise ModelProviderError(
                message=f"provider returned HTTP {response.status_code}{detail}",
                status_code=response.status_code,
                model=self.name,
            )
        payload = response.json()
        finish_reason = _finish_reason(payload)
        usage = _usage(payload)
        if usage is None:
            raise ModelProviderError("provider response lacks comparable usage", model=self.name)
        self.budget.consume_usage(
            self.trial_id,
            _provider_cost(payload, model=self.model),
            usage.prompt_tokens,
            usage.completion_tokens,
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError) as error:
            raise ModelProviderError("provider response lacks content", model=self.name) from error
        if not isinstance(content, str):
            raise ModelProviderError("provider response content is not text", model=self.name)
        self.last_raw_content = content[:8_000]
        if output_format is None:
            return ChatInvokeCompletion(completion=content, usage=usage)
        try:
            normalized = _normalize_browser_use_output(content)
            parsed = output_format.model_validate(normalized)
        except (ModelProviderError, ValidationError) as error:
            event = (
                "invalid_json"
                if isinstance(error, ModelProviderError)
                else "schema_validation_failed"
            )
            self.response_diagnostics.append(
                _response_diagnostic(
                    event=event,
                    content=content,
                    finish_reason=finish_reason,
                    error=error,
                )
            )
            message = (
                "provider output is not JSON"
                if isinstance(error, ModelProviderError)
                else "Browser-use output failed local schema validation"
            )
            raise ModelProviderError(message=message, model=self.name) from error
        return ChatInvokeCompletion(completion=parsed, usage=usage)

    @property
    def evidence_trace(self) -> str:
        """Return bounded diagnostics before the last response for persisted evidence."""
        diagnostics = "\n".join(self.response_diagnostics[-4:])
        if diagnostics:
            return f"{diagnostics}\n--- last model output ---\n{self.last_raw_content}"
        return self.last_raw_content


def _finish_reason(payload: dict[str, object]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    finish_reason = choices[0].get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _response_diagnostic(
    *, event: str, content: str, finish_reason: str | None, error: Exception
) -> str:
    return json.dumps(
        {
            "browser_use_adapter_event": event,
            "content_characters": len(content),
            "finish_reason": finish_reason,
            "parse_error": str(error),
            "content_tail": content[-1_000:],
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _normalize_browser_use_output(content: str) -> object:
    stripped = content.strip()
    if stripped.startswith("```json\n") and stripped.endswith("\n```"):
        stripped = stripped[8:-4].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ModelProviderError("provider output is not JSON", model=DEFAULT_MODEL) from error
    if not isinstance(payload, dict):
        return payload
    if set(payload) == {"agent_output"} and isinstance(payload["agent_output"], dict):
        payload = payload["agent_output"]
    if "action" in payload and isinstance(payload["action"], dict):
        payload = {**payload, "action": [payload["action"]]}
    return payload


def _provider_cost(payload: dict[str, object], *, model: str) -> float | None:
    usage = payload.get("usage")
    return provider_cost_or_model_estimate(usage, model=model) if isinstance(usage, dict) else None


def _usage(payload: dict[str, object]) -> ChatInvokeUsage | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if not isinstance(prompt, int) or not isinstance(completion, int):
        return None
    return ChatInvokeUsage(
        prompt_tokens=prompt,
        prompt_cached_tokens=None,
        prompt_cache_creation_tokens=None,
        prompt_image_tokens=None,
        completion_tokens=completion,
        total_tokens=prompt + completion,
    )
