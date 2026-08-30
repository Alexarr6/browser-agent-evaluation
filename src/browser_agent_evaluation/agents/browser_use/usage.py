from __future__ import annotations

import json

import httpx

from browser_agent_evaluation.core.models import UsageEvidence


def usage_delta(before: UsageEvidence, after: UsageEvidence) -> UsageEvidence:
    """Return provider usage attributable to one workflow step."""
    if before.unavailable_reason or after.unavailable_reason:
        return UsageEvidence(
            prompt_tokens=None,
            completion_tokens=None,
            request_count=after.request_count - before.request_count,
            cost_usd=None,
            unavailable_reason=after.unavailable_reason or before.unavailable_reason,
        )
    assert before.prompt_tokens is not None and after.prompt_tokens is not None
    assert before.completion_tokens is not None and after.completion_tokens is not None
    if before.cost_usd is not None and after.cost_usd is not None:
        cost_usd = after.cost_usd - before.cost_usd
    else:
        cost_usd = None
    return UsageEvidence(
        prompt_tokens=after.prompt_tokens - before.prompt_tokens,
        completion_tokens=after.completion_tokens - before.completion_tokens,
        request_count=after.request_count - before.request_count,
        cost_usd=cost_usd,
        unavailable_reason=(
            None
            if cost_usd is not None
            else "configured provider does not report per-request USD cost"
        ),
    )


class ChatCompletionsUsageCapture(httpx.AsyncBaseTransport):
    """Pass through HTTP unchanged while recording Chat Completions response usage."""

    def __init__(self, transport: httpx.AsyncBaseTransport) -> None:
        self._transport = transport
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._cost_usd: float | None = 0.0
        self._request_count = 0
        self._unavailable_reason: str | None = None

    @property
    def usage(self) -> UsageEvidence:
        if self._unavailable_reason:
            return UsageEvidence(
                prompt_tokens=None,
                completion_tokens=None,
                request_count=self._request_count,
                cost_usd=None,
                unavailable_reason=self._unavailable_reason,
            )
        return UsageEvidence(
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            request_count=self._request_count,
            cost_usd=self._cost_usd,
            unavailable_reason=(
                "configured provider does not report per-request USD cost"
                if self._cost_usd is None
                else None
            ),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._transport.handle_async_request(request)
        body = await response.aread()
        self._capture(request, response, body)
        headers = httpx.Headers(response.headers)
        for stale_header in ("content-encoding", "content-length", "transfer-encoding"):
            headers.pop(stale_header, None)
        return httpx.Response(
            status_code=response.status_code,
            headers=headers,
            content=body,
            request=request,
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._transport.aclose()

    def _capture(self, request: httpx.Request, response: httpx.Response, body: bytes) -> None:
        if not request.url.path.endswith("/chat/completions") or response.is_error:
            return
        try:
            usage = json.loads(body).get("usage", {})
            prompt = usage["prompt_tokens"]
            completion = usage["completion_tokens"]
            cost = usage.get("cost")
        except (KeyError, TypeError, ValueError):
            self._unavailable_reason = "provider response lacks comparable usage"
            return
        if not isinstance(prompt, int) or not isinstance(completion, int):
            self._unavailable_reason = "provider response lacks comparable usage"
            return
        self._request_count += 1
        self._prompt_tokens += prompt
        self._completion_tokens += completion
        self._cost_usd = (
            None
            if not isinstance(cost, int | float) or self._cost_usd is None
            else self._cost_usd + cost
        )
