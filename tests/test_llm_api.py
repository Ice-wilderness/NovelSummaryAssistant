import json
import os
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
from logic.utils import cleanup_api_failure_logs, log_api_failure_to_file


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
    stream_response = None
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

    def stream(self, *args, **kwargs):
        self.__class__.request_json = kwargs.get("json")
        return _FakeStreamContext(self.stream_response)


class _FakeStreamContext:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, body):
        self.body = body

    async def __aiter__(self):
        yield self.body


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
    async def _call_with_response(self, response, events=None):
        _FakeAsyncClient.response = response
        config = {
            "id": "api1",
            "url": "http://example.test/v1",
            "key": "secret",
            "model": "model",
            "max_retries": 1,
        }
        log_callback = (
            (lambda *args, **kwargs: events.append(kwargs))
            if events is not None
            else (lambda *args, **kwargs: None)
        )
        with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
            return await call_llm_api(
                "prompt",
                config,
                log_callback,
            )

    async def _assert_controlled_response_failure(self, payload, expected_message):
        events = []
        result, error = await self._call_with_response(_FakeResponse(payload), events)

        self.assertIsNone(result)
        self.assertIsInstance(error, APIPermanentError)
        self.assertTrue(
            any(expected_message in event.get("message", "") for event in events),
            events,
        )
        tracebacks = "\n".join(
            event.get("traceback_info") or ""
            for event in events
        )
        self.assertNotIn("IndexError", tracebacks)
        self.assertNotIn("TypeError", tracebacks)
        self.assertNotIn("AttributeError", tracebacks)

    async def test_non_stream_empty_choices_is_controlled_failure(self):
        await self._assert_controlled_response_failure(
            {"choices": []},
            "API响应格式无效: 'choices'列表为空",
        )

    async def test_non_stream_non_list_choices_is_controlled_failure(self):
        await self._assert_controlled_response_failure(
            {"choices": {}},
            "API响应格式无效: 'choices'字段必须是列表",
        )

    async def test_non_stream_non_object_choice_is_controlled_failure(self):
        await self._assert_controlled_response_failure(
            {"choices": ["invalid"]},
            "API响应格式无效: 'choices'首项必须是对象",
        )

    async def test_non_stream_scalar_error_is_controlled_failure(self):
        await self._assert_controlled_response_failure(
            {"error": "upstream unavailable"},
            "API返回错误: upstream unavailable",
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

    async def test_stream_http_error_does_not_mask_status_with_response_not_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            request = httpx.Request("POST", "http://example.test/v1/chat/completions")
            _FakeAsyncClient.stream_response = httpx.Response(
                504,
                request=request,
                stream=_FakeAsyncByteStream(b"gateway timeout"),
            )
            config = {
                "id": "api1",
                "url": "http://example.test/v1",
                "key": "secret",
                "model": "model",
                "max_retries": 1,
                "stream": True,
            }

            with mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient):
                result, error = await call_llm_api(
                    "prompt",
                    config,
                    lambda *args, **kwargs: None,
                    task_info={
                        "novel_folder_path": tmpdir,
                        "stage": "test_stage",
                    },
                )

            self.assertIsNone(result)
            self.assertIsInstance(error, APIPermanentError)
            failure_files = list((Path(tmpdir) / ".summarizer_cache" / "api_failures").glob("*.json"))
            self.assertEqual(len(failure_files), 1)
            log_entry = json.loads(failure_files[0].read_text(encoding="utf-8"))
            self.assertEqual(log_entry["status_code"], 504)
            self.assertEqual(log_entry["error_type"], "HTTPStatusError")
            self.assertIn("gateway timeout", log_entry["response_text"])

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

    async def test_failure_log_records_api_input_and_output_per_attempt(self):
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
            failure_files = list((Path(tmpdir) / ".summarizer_cache" / "api_failures").glob("*.json"))
            self.assertEqual(len(failure_files), 1)
            log_text = failure_files[0].read_text(encoding="utf-8")
            self.assertTrue(log_text.startswith("{\n"))
            log_entry = json.loads(log_text)
            self.assertEqual(log_entry["input_messages"], messages)
            self.assertEqual(log_entry["input_text"], "user prompt")
            self.assertIn("<html>bad</html>", log_entry["response_text"])
            self.assertEqual(log_entry["request_payload"]["model"], "model")
            self.assertNotIn("secret", log_text)
            self.assertFalse((Path(tmpdir) / ".summarizer_cache" / "api_log_api1.jsonl").exists())

    async def test_failure_log_preserves_complete_content_and_redacts_secret_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            full_input = "输入" + ("A" * 3000)
            full_response = "输出" + ("B" * 3000)

            await log_api_failure_to_file(
                tmpdir,
                "api1",
                {
                    "timestamp": 1,
                    "stage": "test_stage",
                    "attempt": 1,
                    "input_text": full_input,
                    "response_text": full_response,
                    "headers": {
                        "Authorization": "Bearer secret-token",
                        "x-api-key": "secret-key",
                    },
                    "api_key": "secret-key",
                    "openai_api_key": "another-secret",
                    "api_key_name": "display-name",
                },
            )

            failure_files = list((Path(tmpdir) / ".summarizer_cache" / "api_failures").glob("*.json"))
            self.assertEqual(len(failure_files), 1)
            log_text = failure_files[0].read_text(encoding="utf-8")
            log_entry = json.loads(log_text)
            self.assertEqual(log_entry["input_text"], full_input)
            self.assertEqual(log_entry["response_text"], full_response)
            self.assertEqual(log_entry["headers"]["Authorization"], "[REDACTED]")
            self.assertEqual(log_entry["headers"]["x-api-key"], "[REDACTED]")
            self.assertEqual(log_entry["api_key"], "[REDACTED]")
            self.assertEqual(log_entry["openai_api_key"], "[REDACTED]")
            self.assertEqual(log_entry["api_key_name"], "display-name")
            self.assertNotIn("secret-token", log_text)
            self.assertNotIn("secret-key", log_text)
            self.assertNotIn("another-secret", log_text)

    def test_cleanup_api_failure_logs_removes_old_json_files_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            failure_dir = Path(tmpdir) / ".summarizer_cache" / "api_failures"
            failure_dir.mkdir(parents=True)
            old_file = failure_dir / "old.json"
            recent_file = failure_dir / "recent.json"
            note_file = failure_dir / "note.txt"
            old_file.write_text("{}", encoding="utf-8")
            recent_file.write_text("{}", encoding="utf-8")
            note_file.write_text("keep", encoding="utf-8")
            now = 2_000_000.0
            os.utime(old_file, (now - 3 * 86400, now - 3 * 86400))
            os.utime(recent_file, (now - 3600, now - 3600))

            result = cleanup_api_failure_logs(tmpdir, max_age_days=1, now=now)

            self.assertEqual(result["deleted_count"], 1)
            self.assertFalse(old_file.exists())
            self.assertTrue(recent_file.exists())
            self.assertTrue(note_file.exists())
            self.assertEqual(result["kept_count"], 1)

    def test_cleanup_api_failure_logs_keeps_newest_files_by_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            failure_dir = Path(tmpdir) / ".summarizer_cache" / "api_failures"
            failure_dir.mkdir(parents=True)
            files = []
            for index in range(3):
                path = failure_dir / f"{index}.json"
                path.write_text("{}", encoding="utf-8")
                os.utime(path, (1000 + index, 1000 + index))
                files.append(path)

            result = cleanup_api_failure_logs(tmpdir, max_files=2)

            self.assertEqual(result["deleted_count"], 1)
            self.assertFalse(files[0].exists())
            self.assertTrue(files[1].exists())
            self.assertTrue(files[2].exists())
            self.assertEqual(result["kept_count"], 2)

    async def test_minimum_output_characters_retries_and_writes_failure_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _FakeAsyncClient.response = _FakeResponse(
                {"choices": [{"message": {"content": "short"}}]},
            )
            config = {
                "id": "api1",
                "url": "http://example.test/v1",
                "key": "secret",
                "model": "model",
                "max_retries": 2,
                "minimum_output_characters": 10,
            }

            with (
                mock.patch("logic.llm_api.httpx.AsyncClient", _FakeAsyncClient),
                mock.patch("logic.llm_api.asyncio.sleep", new=mock.AsyncMock()),
            ):
                result, error = await call_llm_api(
                    "user prompt",
                    config,
                    lambda *args, **kwargs: None,
                    task_info={
                        "novel_folder_path": tmpdir,
                        "stage": "test_stage",
                    },
                )

            self.assertIsNone(result)
            self.assertIsInstance(error, APIPermanentError)
            failure_files = list((Path(tmpdir) / ".summarizer_cache" / "api_failures").glob("*.json"))
            self.assertEqual(len(failure_files), 2)
            failure_entry = json.loads(failure_files[0].read_text(encoding="utf-8"))
            self.assertEqual(failure_entry["max_attempts"], 2)
            self.assertIn("低于最少输出字符数限制", failure_entry["error_message"])

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
