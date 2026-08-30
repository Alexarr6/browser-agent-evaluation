from __future__ import annotations

import asyncio
import gzip

import httpx

from browser_agent_evaluation.agents.browser_use.usage import ChatCompletionsUsageCapture


def test_usage_capture_preserves_response_and_accumulates_provider_cost() -> None:
    asyncio.run(_capture_response())


async def _capture_response() -> None:
    async def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3, "cost": 0.02},
            },
            request=request,
        )

    capture = ChatCompletionsUsageCapture(httpx.MockTransport(responder))
    async with httpx.AsyncClient(transport=capture) as client:
        response = await client.post("https://provider.example/v1/chat/completions", json={})

    assert response.json()["choices"][0]["message"]["content"] == "ok"
    assert capture.usage.prompt_tokens == 12
    assert capture.usage.completion_tokens == 3
    assert capture.usage.cost_usd == 0.02


def test_usage_capture_returns_decoded_gzip_body_without_stale_encoding_headers() -> None:
    asyncio.run(_gzip_response())


async def _gzip_response() -> None:
    raw = b'{"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":2,"cost":0.003}}'

    async def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=gzip.compress(raw),
            headers={"content-encoding": "gzip"},
            request=request,
        )

    capture = ChatCompletionsUsageCapture(httpx.MockTransport(responder))
    async with httpx.AsyncClient(transport=capture) as client:
        response = await client.post("https://provider.example/v1/chat/completions", json={})

    assert response.json()["usage"]["cost"] == 0.003
    assert "content-encoding" not in response.headers


def test_usage_capture_rejects_missing_provider_cost() -> None:
    asyncio.run(_missing_cost())


async def _missing_cost() -> None:
    async def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3}},
            request=request,
        )

    capture = ChatCompletionsUsageCapture(httpx.MockTransport(responder))
    async with httpx.AsyncClient(transport=capture) as client:
        await client.post("https://provider.example/v1/chat/completions", json={})

    assert capture.usage.cost_usd is None
    assert (
        capture.usage.unavailable_reason
        == "configured provider does not report per-request USD cost"
    )
