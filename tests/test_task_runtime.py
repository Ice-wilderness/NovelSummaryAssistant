import asyncio
import unittest

from webui_backend.task_runtime import TaskRuntime, TaskStatus, TaskType


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

    async def test_exception_moves_task_to_failed(self):
        runtime = TaskRuntime()

        async def runner(record, pause_signal, emit):
            raise RuntimeError("boom")

        record = await runtime.start_task(TaskType.NOVEL_SUMMARY, runner)
        final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status, TaskStatus.FAILED)
        self.assertIn("boom", final.error)


if __name__ == "__main__":
    unittest.main()
