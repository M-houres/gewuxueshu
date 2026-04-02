from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Task, TaskStatus, TaskType, User


def test_admin_can_download_completed_task_result(
    client,
    db_session: Session,
    admin_override,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "task_result.txt"
    output_path.write_text("admin download result", encoding="utf-8")

    user = User(phone="13800007777", nickname="task-user", credits=1000)
    db_session.add(user)
    db_session.flush()

    task = Task(
        user_id=user.id,
        task_type=TaskType.AIGC_DETECT,
        platform="cnki",
        status=TaskStatus.COMPLETED,
        source_filename="paper.txt",
        source_path=str(tmp_path / "paper.txt"),
        output_path=str(output_path),
        char_count=120,
        cost_credits=120,
        result_json={"summary": "done"},
    )
    db_session.add(task)
    db_session.commit()

    resp = client.get(f"/api/v1/admin/tasks/{task.id}/download")
    assert resp.status_code == 200
    assert resp.content == b"admin download result"
