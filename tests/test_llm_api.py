import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from logic.llm_api import (
    APIPermanentError,
    PromptFormattingError,
    call_llm_api,
    get_llm_summary_with_config,
    render_prompt_messages,
)


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, raise_http=False, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text or json.dumps(self._payload, ensure_ascii=False)
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
    request_json = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.__class__.request_json = kwargs.get("json")
        return self.response


class PromptMessageRenderingTests(unittest.TestCase):
    def test_render_prompt_messages_expands_modules_and_formats_variables(self):
        messages = render_prompt_messages(
            {
                "title": "节点",
                "messages": [
                    {"role": "system", "content": "{{module:style}}"},
                    {"role": "user", "content": "总结 {filename}"},
                ],
                "modules": [{"id": "style", "content": "使用简体中文"}],
            },
            {"filename": "chapter.txt"},
        )

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "使用简体中文"},
                {"role": "user", "content": "总结 chapter.txt"},
            ],
        )

    def test_render_prompt_messages_expands_module_block_in_order(self):
        messages = render_prompt_messages(
            {
                "title": "节点",
                "messages": [
                    {"kind": "message", "role": "user", "content": "开始 {filename}"},
                    {"kind": "module", "module_id": "style"},
                    {"kind": "message", "role": "user", "content": "结束"},
                ],
                "modules": [
                    {
                        "id": "style",
                        "messages": [
                            {"role": "system", "content": "使用简体中文"},
                            {"role": "assistant", "content": "示例 {filename}"},
                        ],
                    }
                ],
            },
            {"filename": "chapter.txt"},
        )

        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "开始 chapter.txt"},
                {"role": "system", "content": "使用简体中文"},
                {"role": "assistant", "content": "示例 chapter.txt"},
                {"role": "user", "content": "结束"},
            ],
        )

    def test_render_prompt_messages_reports_missing_variable(self):
        with self.assertRaisesRegex(PromptFormattingError, "missing"):
            render_prompt_messages(
                {"title": "节点", "messages": [{"role": "user", "content": "{missing}"}]},
                {},
            )

    def test_render_prompt_messages_reports_missing_module(self):
        with self.assertRaisesRegex(PromptFormattingError, "missing_module"):
            render_prompt_messages(
                {
                    "title": "节点",
                    "messages": [
                        {"role": "user", "content": "{{module:missing_module}}"}
                    ],
                },
                {},
            )


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

    async def test_call_llm_api_sends_role_based_messages(self):
        _FakeAsyncClient.response = _FakeResponse(
            {"choices": [{"message": {"content": "valid summary"}}]}
        )
        config = {
            "id": "api1",
            "url": "http://example.test/v1",
            "key": "secret",
            "model": "model",
            "max_retries": 1,
        }
        messages = [
            {"role": "system", "content": "system text"},
            {"role": "user", "content": "user text"},
        ]

        with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
            result, error = await call_llm_api(
                "system text\n\nuser text",
                config,
                lambda *args, **kwargs: None,
                messages=messages,
            )

        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(_FakeAsyncClient.request_json["messages"], messages)

    async def test_failure_log_records_api_input_and_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _FakeAsyncClient.response = _FakeResponse(
                {"choices": [{"message": {"content": "<html>bad</html>"}}]},
                text="<html>bad</html>",
            )
            config = {
                "id": "api1",
                "url": "http://example.test/v1",
                "key": "secret",
                "model": "model",
                "max_retries": 1,
            }
            messages = [{"role": "user", "content": "user prompt"}]

            with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
                result, error = await call_llm_api(
                    "user prompt",
                    config,
                    lambda *args, **kwargs: None,
                    messages=messages,
                    task_info={
                        "novel_folder_path": tmpdir,
                        "stage": "test_stage",
                    },
                )

            self.assertIsNone(result)
            self.assertIsInstance(error, APIPermanentError)
            log_path = Path(tmpdir) / ".summarizer_cache" / "api_log_api1.jsonl"
            log_entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(log_entries[-1]["input_messages"], messages)
            self.assertEqual(log_entries[-1]["input_text"], "user prompt")
            self.assertIn("<html>bad</html>", log_entries[-1]["response_text"])
            self.assertEqual(log_entries[-1]["request_payload"]["model"], "model")

    async def test_get_llm_summary_with_config_passes_rendered_messages(self):
        config = {"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}
        prompt_config = {
            "title": "节点",
            "messages": [
                {"role": "system", "content": "{{module:style}}"},
                {"role": "user", "content": "总结 {filename}"},
            ],
            "modules": [{"id": "style", "content": "简体中文"}],
        }

        with mock.patch(
            "logic.llm_api.call_llm_api",
            new=mock.AsyncMock(return_value=(("summary", None, None), None)),
        ) as call_api:
            summary = await get_llm_summary_with_config(
                config,
                prompt_config,
                {"filename": "chapter.txt"},
                lambda *args, **kwargs: None,
            )

        self.assertEqual(summary, "summary")
        self.assertEqual(
            call_api.await_args.kwargs["messages"],
            [
                {"role": "system", "content": "简体中文"},
                {"role": "user", "content": "总结 chapter.txt"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
