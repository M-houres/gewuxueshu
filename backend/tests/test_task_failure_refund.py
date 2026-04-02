from pathlib import Path
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app import worker_tasks
from app.models import CreditTransaction, CreditType, Task, TaskStatus, TaskType, User


def test_process_task_failure_refunds_credits(db_session: Session, tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "source.txt"
    source_path.write_text("这是一段用于失败退款测试的文本内容。", encoding="utf-8")

    user = User(phone="13800008888", nickname="refund-user", credits=1000)
    db_session.add(user)
    db_session.flush()

    task = Task(
        user_id=user.id,
        task_type=TaskType.DEDUP,
        platform="cnki",
        status=TaskStatus.PENDING,
        source_filename="source.txt",
        source_path=str(source_path),
        char_count=50,
        cost_credits=200,
    )
    db_session.add(task)
    db_session.flush()

    user.credits = 800
    db_session.add(
        CreditTransaction(
            user_id=user.id,
            tx_type=CreditType.TASK_CONSUME,
            delta=-200,
            balance_before=1000,
            balance_after=800,
            reason="dedup任务提交扣费",
            related_id=f"task:{task.id}",
        )
    )
    db_session.commit()

    def _raise_error(*_args, **_kwargs):
        raise RuntimeError("mock processing failure")

    monkeypatch.setattr(worker_tasks.ProcessingEngine, "process", _raise_error)
    
    @contextmanager
    def _db_session_override():
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    monkeypatch.setattr(worker_tasks, "db_session", _db_session_override)

    result = worker_tasks.process_task_async(task.id)
    assert result["ok"] is False

    db_session.refresh(task)
    db_session.refresh(user)
    assert task.status == TaskStatus.FAILED
    assert task.refund_done is True
    assert "mock processing failure" in (task.error_message or "")
    assert user.credits == 1000

    refund_rows = (
        db_session.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.tx_type == CreditType.TASK_REFUND,
            CreditTransaction.related_id == f"task_refund:{task.id}",
        )
        .all()
    )
    assert len(refund_rows) == 1

    second = worker_tasks.process_task_async(task.id)
    assert second["ok"] is False
    refund_rows = (
        db_session.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == user.id,
            CreditTransaction.tx_type == CreditType.TASK_REFUND,
            CreditTransaction.related_id == f"task_refund:{task.id}",
        )
        .all()
    )
    assert len(refund_rows) == 1
