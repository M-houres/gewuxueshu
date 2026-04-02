import time

from app.config import get_settings
from app.worker_tasks import dispatch_background_task, wait_for_local_tasks


class DummyTask:
    name = "tests.dummy_task"

    def __init__(self, sink: list[int]) -> None:
        self.sink = sink

    def delay(self, *_args, **_kwargs) -> None:
        raise AssertionError("local fallback should not call celery delay")

    def __call__(self, value: int) -> None:
        time.sleep(0.01)
        self.sink.append(value)


def test_dispatch_background_task_falls_back_to_single_local_queue(monkeypatch) -> None:
    settings = get_settings()
    old_env = settings.app_env
    settings.app_env = "dev"

    try:
        sink: list[int] = []
        task = DummyTask(sink)
        monkeypatch.setattr("app.worker_tasks._celery_broker_available", lambda: False)

        assert wait_for_local_tasks(1.0)
        for item in range(3):
            mode = dispatch_background_task(task, item)
            assert mode == "local-queue"

        assert wait_for_local_tasks(2.0)
        assert sink == [0, 1, 2]
    finally:
        settings.app_env = old_env
