from pathlib import Path
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, TASK_RATES
from app.deps import client_source_dep, current_user, db_dep
from app.exceptions import BizError
from app.models import CreditType, SystemConfig, Task, TaskStatus, TaskType, User
from app.pagination import paginate
from app.responses import ok
from app.schemas import APIResp
from app.services.credit_service import change_credits
from app.utils import count_billable_chars, detect_file_magic, extract_text_from_file, safe_filename

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("app.api.tasks")

TASK_PAPER_EXTENSIONS: dict[TaskType, set[str]] = {
    TaskType.AIGC_DETECT: {".docx", ".pdf", ".txt"},
    TaskType.DEDUP: {".docx"},
    TaskType.REWRITE: {".docx"},
}
TASK_REPORT_EXTENSIONS: dict[TaskType, set[str]] = {
    TaskType.AIGC_DETECT: set(),
    TaskType.DEDUP: {".docx", ".pdf"},
    TaskType.REWRITE: {".docx", ".pdf"},
}


def _parse_task_type(raw: str) -> TaskType:
    try:
        return TaskType(raw)
    except Exception as exc:
        raise BizError(code=4101, message="任务类型不支持") from exc


def _save_upload_to(path: Path, upload: UploadFile, max_bytes: int) -> None:
    data = upload.file.read()
    if not data:
        raise BizError(code=4102, message="上传文件为空")
    if len(data) > max_bytes:
        raise BizError(code=4103, message=f"文件超过{MAX_FILE_SIZE_MB}MB限制")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _format_exts(exts: set[str]) -> str:
    return " / ".join(sorted(exts))


def _validate_paper_extension(task_type: TaskType, ext: str) -> None:
    allowed = TASK_PAPER_EXTENSIONS[task_type]
    if ext not in allowed:
        if task_type in {TaskType.DEDUP, TaskType.REWRITE}:
            raise BizError(code=4104, message="仅支持 Word 文档（.docx）")
        raise BizError(code=4104, message=f"文件格式不支持，仅支持{_format_exts(allowed)}")


def _validate_report_extension(task_type: TaskType, ext: str) -> None:
    allowed = TASK_REPORT_EXTENSIONS[task_type]
    if not allowed:
        raise BizError(code=4106, message="当前任务不支持上传辅助报告")
    if ext not in allowed:
        raise BizError(code=4106, message=f"报告文件格式不支持，仅支持{_format_exts(allowed)}")


def _report_is_full(task_type: TaskType, text: str) -> bool:
    content = " ".join((text or "").split()).lower()
    if not content:
        return False
    if task_type == TaskType.DEDUP:
        markers = [
            "全文",
            "总文字复制比",
            "去除引用复制比",
            "去除本人已发表文献复制比",
            "检测报告",
            "全文标明引文",
        ]
        return sum(1 for marker in markers if marker in content) >= 2
    if task_type == TaskType.REWRITE:
        markers = [
            "aigc",
            "ai生成",
            "疑似ai",
            "检测报告",
            "全文",
            "总体风险",
            "高风险段落",
        ]
        return sum(1 for marker in markers if marker in content) >= 2
    return False


def _validate_report_content(task_type: TaskType, path: Path) -> None:
    if task_type not in {TaskType.DEDUP, TaskType.REWRITE}:
        return
    report_text = extract_text_from_file(path)
    if _report_is_full(task_type, report_text):
        return
    if task_type == TaskType.DEDUP:
        raise BizError(code=4114, message="请上传全文查重报告", http_status=422)
    raise BizError(code=4115, message="请上传全文AIGC检测报告", http_status=422)


def _resolve_task_rate(db: Session, task_type: TaskType) -> int:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "billing")
        .first()
    )
    cfg = row.config_value if row and isinstance(row.config_value, dict) else {}
    key_map = {
        TaskType.AIGC_DETECT: "aigc_rate",
        TaskType.DEDUP: "dedup_rate",
        TaskType.REWRITE: "rewrite_rate",
    }
    key = key_map[task_type]
    value = cfg.get(key)
    if isinstance(value, int) and value > 0:
        return value
    return TASK_RATES[task_type]


@router.get("/rates", response_model=APIResp)
def task_rates(db: Session = Depends(db_dep)) -> APIResp:
    return ok(
        data={
            "aigc_rate": _resolve_task_rate(db, TaskType.AIGC_DETECT),
            "dedup_rate": _resolve_task_rate(db, TaskType.DEDUP),
            "rewrite_rate": _resolve_task_rate(db, TaskType.REWRITE),
        }
    )


@router.post("/submit", response_model=APIResp)
def submit_task(
    task_type: str = Form(...),
    platform: str = Form("cnki"),
    paper: UploadFile = File(...),
    report: UploadFile | None = File(default=None),
    client_source: str = Depends(client_source_dep),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    t = _parse_task_type(task_type)
    ext = Path(paper.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BizError(code=4104, message="文件格式不支持")
    _validate_paper_extension(t, ext)

    upload_dir = settings.upload_dir / str(user.id)
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    src_name = safe_filename(paper.filename or f"source{ext}")
    src_path = upload_dir / src_name
    _save_upload_to(src_path, paper, max_bytes)

    magic = detect_file_magic(src_path)
    if magic and magic != ext:
        src_path.unlink(missing_ok=True)
        raise BizError(code=4105, message="文件内容与扩展名不匹配")

    report_path = None
    if report is not None and report.filename:
        rpt_ext = Path(report.filename).suffix.lower()
        if rpt_ext not in ALLOWED_EXTENSIONS:
            raise BizError(code=4106, message="报告文件格式不支持")
        _validate_report_extension(t, rpt_ext)
        tmp = upload_dir / safe_filename(report.filename)
        _save_upload_to(tmp, report, max_bytes)
        try:
            _validate_report_content(t, tmp)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        report_path = str(tmp)

    text = extract_text_from_file(src_path)
    char_count = count_billable_chars(text)
    rate = _resolve_task_rate(db, t)
    cost = rate * char_count
    if char_count <= 0:
        raise BizError(code=4107, message="文档字符数为0，无法处理")
    if user.credits < cost:
        raise BizError(code=4006, message="积分不足，请先充值")

    task = Task(
        user_id=user.id,
        task_type=t,
        platform=platform.lower(),
        source=client_source,
        status=TaskStatus.PENDING,
        source_filename=src_name,
        source_path=str(src_path),
        report_path=report_path,
        char_count=char_count,
        cost_credits=cost,
    )
    db.add(task)
    db.flush()
    change_credits(
        db,
        user,
        tx_type=CreditType.TASK_CONSUME,
        delta=-cost,
        reason=f"{t.value}任务提交扣费",
        related_id=f"task:{task.id}",
        source=client_source,
    )
    db.commit()
    logger.info(
        "task_submitted",
        extra={
            "task_id": task.id,
            "user_id": user.id,
            "task_type": t.value,
            "char_count": char_count,
            "cost_credits": cost,
        },
    )

    from app.worker_tasks import dispatch_background_task, process_task_async

    dispatch_background_task(process_task_async, task.id)
    return ok(data={"id": task.id, "status": task.status.value, "cost_credits": cost})


@router.get("/my", response_model=APIResp)
def my_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    task_type: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(db_dep),
) -> APIResp:
    base_query = db.query(Task).filter(Task.user_id == user.id)
    if task_type:
        try:
            base_query = base_query.filter(Task.task_type == TaskType(task_type))
        except Exception:
            raise BizError(code=4101, message="任务类型不支持")
    if platform:
        base_query = base_query.filter(Task.platform == platform.lower().strip())
    if status:
        try:
            base_query = base_query.filter(Task.status == TaskStatus(status))
        except Exception:
            raise BizError(code=4110, message="任务状态不支持")
    if start_date:
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            base_query = base_query.filter(Task.created_at >= dt)
        except Exception:
            raise BizError(code=4111, message="开始日期格式错误，应为YYYY-MM-DD")
    if end_date:
        try:
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            dt = dt.replace(hour=23, minute=59, second=59)
            base_query = base_query.filter(Task.created_at <= dt)
        except Exception:
            raise BizError(code=4112, message="结束日期格式错误，应为YYYY-MM-DD")
    total = base_query.count()
    rows = (
        base_query.order_by(desc(Task.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": row.id,
            "task_type": row.task_type.value,
            "platform": row.platform,
            "source": row.source,
            "status": row.status.value,
            "source_filename": row.source_filename,
            "has_report": bool(row.report_path),
            "char_count": row.char_count,
            "cost_credits": row.cost_credits,
            "result_json": row.result_json,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]
    return ok(data={"items": items, "pagination": paginate(total, page, page_size)})


@router.get("/{task_id}", response_model=APIResp)
def task_detail(task_id: int, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    row = db.get(Task, task_id)
    if not row or row.user_id != user.id:
        raise BizError(code=4041, message="任务不存在", http_status=404)
    return ok(
        data={
            "id": row.id,
            "task_type": row.task_type.value,
            "platform": row.platform,
            "source": row.source,
            "status": row.status.value,
            "source_filename": row.source_filename,
            "has_report": bool(row.report_path),
            "char_count": row.char_count,
            "cost_credits": row.cost_credits,
            "result_json": row.result_json,
            "error_message": row.error_message,
            "output_path": row.output_path,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


@router.get("/{task_id}/download")
def task_download(task_id: int, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> FileResponse:
    row = db.get(Task, task_id)
    if not row or row.user_id != user.id:
        raise BizError(code=4041, message="任务不存在", http_status=404)
    if row.status != TaskStatus.COMPLETED or not row.output_path:
        raise BizError(code=4108, message="任务尚未完成")
    path = Path(row.output_path)
    if not path.exists():
        raise BizError(code=4109, message="输出文件不存在")
    return FileResponse(path=str(path), filename=path.name)


@router.delete("/{task_id}", response_model=APIResp)
def delete_task(task_id: int, user: User = Depends(current_user), db: Session = Depends(db_dep)) -> APIResp:
    row = db.get(Task, task_id)
    if not row or row.user_id != user.id:
        raise BizError(code=4041, message="任务不存在", http_status=404)
    if row.status == TaskStatus.RUNNING:
        raise BizError(code=4113, message="处理中任务不可删除")
    db.delete(row)
    db.commit()
    return ok(data={"task_id": task_id, "deleted": True})
