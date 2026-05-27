import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from webui_backend.task_runtime import TaskRunOutcome, TaskRuntime, TaskStatus, TaskType


class TaskRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_success_records_result_and_events(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            emit(event_type="progress", message="half", progress_text="Halfway")
            return "done"

        record = await runtime.start_task(TaskType.ARTICLE_SUMMARY, runner, {"folder": "x"})
        final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status, TaskStatus.SUCCESS)
        self.assertEqual(final.result_summary, "done")
        self.assertEqual(final.progress_text, "Halfway")
        self.assertTrue(any(event.event_type == "progress" for event in final.events))

    async def test_pause_and_resume_update_status(self):
        runtime = TaskRuntime()
        gate = asyncio.Event()
        pause_observed = asyncio.Event()

        async def runner(record, pause_signal, emit):
            gate.set()
            while not pause_signal.is_set():
                await asyncio.sleep(0.01)
            pause_observed.set()
            await asyncio.to_thread(pause_signal.wait)
            return "resumed"

        record = await runtime.start_task(TaskType.CUSTOM_SUMMARY, runner)
        await gate.wait()

        paused = runtime.pause_task(record.task_id)
        self.assertEqual(paused.status, TaskStatus.PAUSED)
        self.assertEqual(paused.events[-1].status, TaskStatus.PAUSED.value)
        await pause_observed.wait()

        resumed = runtime.resume_task(record.task_id)
        self.assertEqual(resumed.status, TaskStatus.RUNNING)
        final = await runtime.wait_for_terminal(record.task_id)
        self.assertEqual(final.status, TaskStatus.SUCCESS)

    async def test_cancel_moves_task_to_cancelled(self):
        runtime = TaskRuntime()
        started = asyncio.Event()

        async def runner(record, pause_signal, emit):
            started.set()
            await asyncio.sleep(10)

        record = await runtime.start_task(TaskType.CHAPTER_SPLIT, runner)
        await started.wait()
        runtime.cancel_task(record.task_id)
        final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status, TaskStatus.CANCELLED)

    async def test_cancel_after_terminal_preserves_existing_state(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            return "done"

        record = await runtime.start_task(TaskType.CHAPTER_SPLIT, runner)
        final = await runtime.wait_for_terminal(record.task_id)

        cancelled = runtime.cancel_task(record.task_id)

        self.assertEqual(final.status, TaskStatus.SUCCESS)
        self.assertEqual(cancelled.status, TaskStatus.SUCCESS)
        self.assertEqual(cancelled.result_summary, "done")

    async def test_exception_moves_task_to_failed(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            raise RuntimeError("boom")

        record = await runtime.start_task(TaskType.NOVEL_SUMMARY, runner)
        final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status, TaskStatus.FAILED)
        self.assertIn("boom", final.error)

    async def test_failed_result_moves_task_to_failed(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            return "failed"

        record = await runtime.start_task(TaskType.NOVEL_SUMMARY, runner)
        final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status, TaskStatus.FAILED)
        self.assertEqual(final.error, "failed")
        self.assertTrue(any(event.event_type == "error" for event in final.events))

    async def test_structured_partial_outcome_is_terminal_and_serialized(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            return TaskRunOutcome(
                status=TaskStatus.PARTIAL_FAILED,
                result_summary="kept output",
                error="missing sections",
                warnings=["section 2 failed"],
                data={"failed_sections": [{"filename": "b.txt"}]},
            )

        record = await runtime.start_task(TaskType.ARTICLE_SUMMARY, runner)
        final = await runtime.wait_for_terminal(record.task_id)
        data = final.to_dict()

        self.assertEqual(final.status, TaskStatus.PARTIAL_FAILED)
        self.assertFalse(runtime.has_active_task())
        self.assertIsNotNone(final.finished_at)
        self.assertEqual(final.result_summary, "kept output")
        self.assertEqual(final.error, "missing sections")
        self.assertEqual(final.warnings, ["section 2 failed"])
        self.assertEqual(final.result_data["failed_sections"][0]["filename"], "b.txt")
        self.assertEqual(data["status"], "partial_failed")
        self.assertEqual(data["warnings"], ["section 2 failed"])
        self.assertEqual(data["result_data"]["failed_sections"][0]["filename"], "b.txt")
        self.assertEqual(final.events[-1].status, "partial_failed")
        self.assertEqual(final.events[-1].data["warnings"], ["section 2 failed"])

    async def test_persists_task_summary_on_start_and_terminal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = TaskRuntime(tmpdir)

            async def runner(record, pause_signal, emit):
                emit(event_type="progress", message="half", progress_text="Halfway")
                return "done"

            record = await runtime.start_task(TaskType.ARTICLE_SUMMARY, runner, {"folder": Path("x")})
            summary_path = Path(tmpdir) / f"{record.task_id}.json"
            self.assertTrue(summary_path.exists())
            start_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(start_summary["task_id"], record.task_id)

            final = await runtime.wait_for_terminal(record.task_id)
            terminal_summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(final.status, TaskStatus.SUCCESS)
            self.assertEqual(terminal_summary["status"], "success")
            self.assertEqual(terminal_summary["result_summary"], "done")
            self.assertEqual(terminal_summary["params_summary"], {"folder": "x"})
            self.assertEqual(len(terminal_summary["events"]), 1)
            self.assertEqual(terminal_summary["events"][0]["status"], "success")

    async def test_loads_persisted_terminal_summary_after_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = TaskRuntime(tmpdir)

            async def runner(record, pause_signal, emit):
                return TaskRunOutcome(
                    status=TaskStatus.PARTIAL_FAILED,
                    result_summary="kept",
                    error="missing input",
                    warnings=["input b failed"],
                    data={"failed": ["b"]},
                )

            record = await runtime.start_task(TaskType.CUSTOM_SUMMARY, runner)
            await runtime.wait_for_terminal(record.task_id)

            restarted = TaskRuntime(tmpdir)
            loaded = restarted.get_task(record.task_id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.status, TaskStatus.PARTIAL_FAILED)
            self.assertEqual(loaded.result_summary, "kept")
            self.assertEqual(loaded.warnings, ["input b failed"])
            self.assertFalse(restarted.has_active_task())
            self.assertEqual(loaded.events[-1].status, "partial_failed")

    async def test_loads_non_terminal_summary_as_interrupted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = TaskRuntime(tmpdir)
            started = asyncio.Event()

            async def runner(record, pause_signal, emit):
                started.set()
                await asyncio.sleep(10)

            record = await runtime.start_task(TaskType.NOVEL_SUMMARY, runner)
            await started.wait()
            restarted = TaskRuntime(tmpdir)
            loaded = restarted.get_task(record.task_id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.status, TaskStatus.INTERRUPTED)
            self.assertIn("后端重启", loaded.error or "")
            self.assertTrue(loaded.warnings)
            self.assertFalse(restarted.has_active_task())
            self.assertEqual(loaded.events[-1].status, "interrupted")
            self.assertEqual(loaded.events[-1].data["previous_status"], "running")

            runtime.cancel_task(record.task_id)
            await runtime.wait_for_terminal(record.task_id)

    async def test_invalid_persisted_summary_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "bad.json").write_text("{not json", encoding="utf-8")
            Path(tmpdir, "wrong-id.json").write_text(
                json.dumps({"task_id": "../bad", "task_type": "model_fetch", "status": "success"}),
                encoding="utf-8",
            )

            runtime = TaskRuntime(tmpdir)

            self.assertEqual(runtime.list_tasks(), [])


if __name__ == "__main__":
    unittest.main()
