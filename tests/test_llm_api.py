import unittest
from unittest import mock

import httpx

from logic.llm_api import APIPermanentError, call_llm_api


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, raise_http=False):
        self._payload = payload or {}
        self.status_code = status_code
        request = httpx.Request("POST", "http://example.test/v1/chat/completions")
        self._httpx_response = httpx.Response(status_code, request=request)
        self._raise_http = raise_http

    def raise_for_status(self):
        if self._raise_http:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self._httpx_response.request,
                response=self._httpx_response,
            )

    def json(self):
        return self._payload


class _FakeAsyncClient:
    response = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self.response


class LlmApiErrorJudgmentTests(unittest.IsolatedAsyncioTestCase):
    async def _call_with_response(self, response):
        _FakeAsyncClient.response = response
        config = {
            "id": "api1",
            "url": "http://example.test/v1",
            "key": "secret",
            "model": "model",
            "max_retries": 1,
        }
        with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
            return await call_llm_api(
                "prompt",
                config,
                lambda *args, **kwargs: None,
            )

    async def test_empty_response_becomes_permanent_error(self):
        result, error = await self._call_with_response(
            _FakeResponse({"choices": [{"message": {"content": ""}}]})
        )

        self.assertIsNone(result)
        self.assertIsInstance(error, APIPermanentError)

    async def test_html_response_becomes_permanent_error(self):
        result, error = await self._call_with_response(
            _FakeResponse({"choices": [{"message": {"content": "<html>bad</html>"}}]})
        )

        self.assertIsNone(result)
        self.assertIsInstance(error, APIPermanentError)

    async def test_rate_limit_becomes_permanent_error_when_retries_exhausted(self):
        result, error = await self._call_with_response(
            _FakeResponse(status_code=429, raise_http=True)
        )

        self.assertIsNone(result)
        self.assertIsInstance(error, APIPermanentError)

    async def test_id_only_config_is_used_as_log_source(self):
        _FakeAsyncClient.response = _FakeResponse(
            {"choices": [{"message": {"content": "valid summary"}}]}
        )
        events = []
        config = {
            "id": "api1",
            "url": "http://example.test/v1",
            "key": "secret",
            "model": "model",
            "max_retries": 1,
        }

        with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
            result, error = await call_llm_api(
                "prompt",
                config,
                lambda *args, **kwargs: events.append(kwargs),
            )

        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertTrue(events)
        self.assertEqual(events[0]["source_id"], "api1")


if __name__ == "__main__":
    unittest.main()
