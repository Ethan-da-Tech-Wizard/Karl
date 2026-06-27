"""Tests for TaskSupervisor — task registry, lifecycle, and cancellation."""

from __future__ import annotations

import time
import threading
import unittest

from app.engine.task_supervisor import TaskSupervisor, TaskStatus


def _fresh() -> TaskSupervisor:
    """Return a brand-new TaskSupervisor instance, isolated from the singleton."""
    TaskSupervisor.reset_instance()
    sup = TaskSupervisor.instance()
    return sup


class TestTaskRegistration(unittest.TestCase):

    def setUp(self):
        self.sup = _fresh()

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_register_returns_unique_ids(self):
        id1 = self.sup.register("task A")
        id2 = self.sup.register("task B")
        self.assertNotEqual(id1, id2)

    def test_register_explicit_task_id(self):
        tid = self.sup.register("explicit", task_id="fixed-id-123")
        self.assertEqual(tid, "fixed-id-123")

    def test_registered_task_is_running(self):
        tid = self.sup.register("job")
        self.assertEqual(self.sup.status(tid), TaskStatus.RUNNING)

    def test_unknown_task_returns_none_status(self):
        self.assertIsNone(self.sup.status("no-such-id"))

    def test_progress_zero_at_registration(self):
        tid = self.sup.register("job")
        self.assertAlmostEqual(self.sup.progress(tid), 0.0)

    def test_update_progress_clamped(self):
        tid = self.sup.register("job")
        self.sup.update_progress(tid, 0.5)
        self.assertAlmostEqual(self.sup.progress(tid), 0.5)
        self.sup.update_progress(tid, 2.0)   # above 1.0
        self.assertAlmostEqual(self.sup.progress(tid), 1.0)
        self.sup.update_progress(tid, -1.0)  # below 0.0
        self.assertAlmostEqual(self.sup.progress(tid), 0.0)

    def test_error_empty_at_registration(self):
        tid = self.sup.register("job")
        self.assertEqual(self.sup.error(tid), "")


class TestTaskLifecycle(unittest.TestCase):

    def setUp(self):
        self.sup = _fresh()

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_finish_transitions_to_finished(self):
        tid = self.sup.register("job")
        self.sup.finish(tid)
        self.assertEqual(self.sup.status(tid), TaskStatus.FINISHED)

    def test_finish_sets_progress_to_one(self):
        tid = self.sup.register("job")
        self.sup.finish(tid)
        self.assertAlmostEqual(self.sup.progress(tid), 1.0)

    def test_fail_transitions_to_error(self):
        tid = self.sup.register("job")
        self.sup.fail(tid, "something broke")
        self.assertEqual(self.sup.status(tid), TaskStatus.ERROR)

    def test_fail_stores_error_message(self):
        tid = self.sup.register("job")
        self.sup.fail(tid, "disk full")
        self.assertEqual(self.sup.error(tid), "disk full")

    def test_finish_on_unknown_id_is_noop(self):
        self.sup.finish("ghost-id")  # must not raise

    def test_fail_on_unknown_id_is_noop(self):
        self.sup.fail("ghost-id", "whatever")  # must not raise

    def test_active_tasks_includes_running(self):
        tid = self.sup.register("active")
        self.assertTrue(any(r.task_id == tid for r in self.sup.active_tasks()))

    def test_active_tasks_excludes_finished(self):
        tid = self.sup.register("done")
        self.sup.finish(tid)
        self.assertFalse(any(r.task_id == tid for r in self.sup.active_tasks()))

    def test_all_tasks_returns_all(self):
        t1 = self.sup.register("t1")
        t2 = self.sup.register("t2")
        self.sup.finish(t1)
        ids = {r.task_id for r in self.sup.all_tasks()}
        self.assertIn(t1, ids)
        self.assertIn(t2, ids)


class TestCancellation(unittest.TestCase):

    def setUp(self):
        self.sup = _fresh()

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_cancel_transitions_to_cancelling(self):
        class _Stoppable:
            def request_stop(self):
                pass

        tid = self.sup.register("job", cancellable=_Stoppable())
        result = self.sup.cancel(tid)
        self.assertTrue(result)
        self.assertEqual(self.sup.status(tid), TaskStatus.CANCELLING)

    def test_cancel_calls_request_stop(self):
        stop_called = []

        class _Stoppable:
            def request_stop(self):
                stop_called.append(True)

        tid = self.sup.register("job", cancellable=_Stoppable())
        self.sup.cancel(tid)
        self.assertEqual(stop_called, [True])

    def test_cancel_without_cancellable_returns_false(self):
        tid = self.sup.register("no-cancel")
        result = self.sup.cancel(tid)
        # status transitions to CANCELLING even without cancellable
        self.assertEqual(self.sup.status(tid), TaskStatus.CANCELLING)
        self.assertFalse(result)

    def test_cancel_finished_task_is_noop(self):
        tid = self.sup.register("job")
        self.sup.finish(tid)
        result = self.sup.cancel(tid)
        self.assertFalse(result)
        self.assertEqual(self.sup.status(tid), TaskStatus.FINISHED)

    def test_cancel_unknown_id_returns_false(self):
        self.assertFalse(self.sup.cancel("ghost"))

    def test_cancel_all_cancels_all_active(self):
        stop_counts = []

        class _Stoppable:
            def request_stop(self):
                stop_counts.append(1)

        self.sup.register("a", cancellable=_Stoppable())
        self.sup.register("b", cancellable=_Stoppable())
        count = self.sup.cancel_all()
        self.assertEqual(count, 2)
        self.assertEqual(sum(stop_counts), 2)

    def test_cancel_all_skips_finished(self):
        tid = self.sup.register("done")
        self.sup.finish(tid)
        count = self.sup.cancel_all()
        self.assertEqual(count, 0)

    def test_request_stop_exception_does_not_propagate(self):
        """A crashing request_stop() must not take down cancel()."""
        class _Buggy:
            def request_stop(self):
                raise RuntimeError("intentional crash in request_stop")

        tid = self.sup.register("buggy", cancellable=_Buggy())
        # Must not raise
        try:
            self.sup.cancel(tid)
        except RuntimeError:
            self.fail("cancel() let request_stop() exception escape")


class TestCleanupHooks(unittest.TestCase):

    def setUp(self):
        self.sup = _fresh()

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_cleanup_hook_called_on_finish(self):
        called = []
        tid = self.sup.register("job", cleanup_hook=lambda: called.append("finish"))
        self.sup.finish(tid)
        self.assertEqual(called, ["finish"])

    def test_cleanup_hook_called_on_fail(self):
        called = []
        tid = self.sup.register("job", cleanup_hook=lambda: called.append("fail"))
        self.sup.fail(tid, "oops")
        self.assertEqual(called, ["fail"])

    def test_multiple_cleanup_hooks_all_called(self):
        called = []
        tid = self.sup.register("job")
        self.sup.add_cleanup_hook(tid, lambda: called.append(1))
        self.sup.add_cleanup_hook(tid, lambda: called.append(2))
        self.sup.finish(tid)
        self.assertEqual(sorted(called), [1, 2])

    def test_failing_cleanup_hook_does_not_stop_others(self):
        called = []

        def _bad():
            raise RuntimeError("hook crash")

        def _good():
            called.append("good")

        tid = self.sup.register("job")
        self.sup.add_cleanup_hook(tid, _bad)
        self.sup.add_cleanup_hook(tid, _good)
        self.sup.finish(tid)  # must not raise
        self.assertIn("good", called)

    def test_add_cleanup_hook_unknown_id_is_noop(self):
        self.sup.add_cleanup_hook("ghost", lambda: None)  # must not raise


class TestSingleton(unittest.TestCase):

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_instance_is_singleton(self):
        a = TaskSupervisor.instance()
        b = TaskSupervisor.instance()
        self.assertIs(a, b)

    def test_reset_produces_fresh_instance(self):
        a = TaskSupervisor.instance()
        a.register("job")
        TaskSupervisor.reset_instance()
        b = TaskSupervisor.instance()
        self.assertEqual(b.all_tasks(), [])

    def test_singleton_thread_safe(self):
        """Concurrent instance() calls must all return the same object."""
        TaskSupervisor.reset_instance()
        results = []

        def _get():
            results.append(TaskSupervisor.instance())

        threads = [threading.Thread(target=_get) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        first = results[0]
        self.assertTrue(all(r is first for r in results))


class TestCancellationWithRealThread(unittest.TestCase):
    """Integration: cancel() via TaskSupervisor reaches a real worker thread."""

    def setUp(self):
        self.sup = _fresh()

    def tearDown(self):
        TaskSupervisor.reset_instance()

    def test_real_thread_stops_when_cancelled(self):
        stop_event = threading.Event()
        completed_normally = []

        class _Worker(threading.Thread):
            def request_stop(self):
                stop_event.set()

            def run(self):
                for _ in range(200):
                    if stop_event.is_set():
                        return
                    time.sleep(0.01)
                completed_normally.append(True)

        worker = _Worker()
        tid = self.sup.register("worker", cancellable=worker)
        worker.start()

        # Give the thread a moment to start, then cancel
        time.sleep(0.05)
        self.sup.cancel(tid)
        worker.join(timeout=3.0)

        self.assertFalse(worker.is_alive(), "worker thread should have stopped")
        self.assertEqual(completed_normally, [], "worker must not have run to completion")
        self.sup.finish(tid)

    def test_finish_after_thread_completes(self):
        ran = []

        class _Worker(threading.Thread):
            def request_stop(self):
                pass

            def run(self):
                time.sleep(0.02)
                ran.append(True)

        worker = _Worker()
        tid = self.sup.register("worker", cancellable=worker)
        worker.start()
        worker.join()
        self.sup.finish(tid)

        self.assertEqual(ran, [True])
        self.assertEqual(self.sup.status(tid), TaskStatus.FINISHED)


class TestModelLoaderGuard(unittest.TestCase):
    """ModelLoader.is_instance_locked() returns True while generation is active."""

    def test_locked_during_active_count(self):
        from app.engine.model_loader import ModelLoader
        # Save original state
        orig_count = ModelLoader._active_generation_count
        orig_locked = ModelLoader._instance_locked
        try:
            ModelLoader._active_generation_count = 1
            ModelLoader._instance_locked = True
            self.assertTrue(ModelLoader.is_instance_locked())
        finally:
            ModelLoader._active_generation_count = orig_count
            ModelLoader._instance_locked = orig_locked

    def test_unlocked_when_no_active(self):
        from app.engine.model_loader import ModelLoader
        orig_count = ModelLoader._active_generation_count
        orig_locked = ModelLoader._instance_locked
        try:
            ModelLoader._active_generation_count = 0
            ModelLoader._instance_locked = False
            self.assertFalse(ModelLoader.is_instance_locked())
        finally:
            ModelLoader._active_generation_count = orig_count
            ModelLoader._instance_locked = orig_locked


if __name__ == "__main__":
    unittest.main()
