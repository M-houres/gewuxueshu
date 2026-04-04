from datetime import datetime
from functools import lru_cache
import logging
from pathlib import Path
from queue import Queue
import threading
import time

from celery import Celery
import redis

from app.config import get_settings
from app.database import db_session
from app.models import CreditType, Order, ReferralReward, RewardType, Task, TaskStatus, User
from app.services.credit_service import change_credits
from app.services.processing_engine import ProcessingEngine
from app.services.referral_service import grant_pay_rewards, grant_register_rewards

settings = get_settings()
logger = logging.getLogger("app.worker_tasks")

celery_app = Celery(
    "wuhongai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_track_started=True,
    timezone="Asia/Shanghai",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

_local_task_queue: Queue[tuple[object, tuple, dict, str]] = Queue()
_local_worker_lock = threading.Lock()
_local_worker_thread: threading.Thread | None = None


@lru_cache(maxsize=1)
def _celery_broker_probe():
    broker_url = str(settings.celery_broker_url or "").strip()
    if not broker_url.startswith(("redis://", "rediss://")):
        return None
    return redis.Redis.from_url(
        broker_url,
        decode_responses=True,
        socket_connect_timeout=0.3,
        socket_timeout=0.3,
    )


def _celery_broker_available() -> bool:
    probe = _celery_broker_probe()
    if probe is None:
        return True
    try:
        probe.ping()
        return True
    except redis.RedisError:
        return False


def _run_task_locally(task, args: tuple, kwargs: dict, task_name: str) -> None:
    try:
        task(*args, **kwargs)
    except Exception:
        logger.exception("local_task_dispatch_failed", extra={"task_name": task_name})


def _local_worker_loop() -> None:
    while True:
        task, args, kwargs, task_name = _local_task_queue.get()
        try:
            _run_task_locally(task, args, kwargs, task_name)
        finally:
            _local_task_queue.task_done()


def _ensure_local_worker() -> None:
    global _local_worker_thread
    with _local_worker_lock:
        if _local_worker_thread and _local_worker_thread.is_alive():
            return
        _local_worker_thread = threading.Thread(
            target=_local_worker_loop,
            daemon=True,
            name="local-task-worker",
        )
        _local_worker_thread.start()


def wait_for_local_tasks(timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + max(timeout_seconds, 0)
    while time.monotonic() < deadline:
        if _local_task_queue.unfinished_tasks == 0:
            return True
        time.sleep(0.01)
    return _local_task_queue.unfinished_tasks == 0


def dispatch_background_task(task, *args, **kwargs) -> str:
    task_name = getattr(task, "name", getattr(task, "__name__", "unknown_task"))
    if settings.app_env == "prod":
        task.delay(*args, **kwargs)
        return "celery"

    if _celery_broker_available():
        try:
            task.delay(*args, **kwargs)
            return "celery"
        except Exception:
            logger.warning(
                "celery_dispatch_failed_fallback_local",
                exc_info=True,
                extra={"task_name": task_name},
            )
    else:
        logger.warning("celery_broker_unavailable_fallback_local", extra={"task_name": task_name})

    try:
        _ensure_local_worker()
        _local_task_queue.put((task, args, kwargs, task_name))
        return "local-queue"
    except Exception:
        logger.warning(
            "local_queue_dispatch_failed_run_inline",
            exc_info=True,
            extra={"task_name": task_name},
        )
        _run_task_locally(task, args, kwargs, task_name)
        return "inline"


def _refund_task(db, task: Task) -> None:
    if task.refund_done:
        return
    user = db.query(User).filter(User.id == task.user_id).with_for_update().first()
    if user is None:
        return
    change_credits(
        db,
        user,
        tx_type=CreditType.TASK_REFUND,
        delta=task.cost_credits,
        reason=f"任务失败退还积分(task_id={task.id})",
        related_id=f"task_refund:{task.id}",
        source=task.source,
    )
    task.refund_done = True
    db.flush()


@celery_app.task(name="tasks.process_task")
def process_task_async(task_id: int) -> dict:
    with db_session() as db:
        task = db.query(Task).filter(Task.id == task_id).with_for_update().first()
        if task is None:
            return {"ok": False, "reason": "task_not_found"}
        if task.status == TaskStatus.COMPLETED:
            return {"ok": True, "task_id": task.id, "status": task.status.value}

        task.status = TaskStatus.RUNNING
        task.error_message = None
        db.flush()
        try:
            source_path = Path(task.source_path)
            output_dir = settings.output_dir / str(task.user_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_ext = ".pdf" if task.task_type.value == "aigc_detect" else source_path.suffix.lower()
            if not output_ext:
                output_ext = ".txt"
            output_path = output_dir / f"task_{task.id}_result{output_ext}"

            engine = ProcessingEngine(db)
            result = engine.process(
                task.task_type,
                task.platform,
                source_path,
                output_path,
                task_id=task.id,
                report_path=Path(task.report_path) if task.report_path else None,
                processing_mode=task.processing_mode,
            )

            task.status = TaskStatus.COMPLETED
            task.output_path = result.output_path
            task.result_json = result.result_json
            task.error_message = None
            task.updated_at = datetime.utcnow()
            db.flush()
            return {"ok": True, "task_id": task.id, "status": task.status.value}
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.updated_at = datetime.utcnow()
            _refund_task(db, task)
            db.flush()
            return {"ok": False, "task_id": task.id, "error": str(exc)}


@celery_app.task(name="tasks.grant_order_referral_rewards", bind=True, max_retries=3)
def grant_order_referral_rewards_async(self, order_id: int) -> dict:
    retry_delays = [60, 300, 900]
    with db_session() as db:
        order = db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if order is None:
            return {"ok": False, "reason": "order_not_found"}
        if order.status != "paid":
            return {"ok": False, "reason": "order_not_paid"}
        try:
            grant_pay_rewards(db, order)
            return {"ok": True, "order_id": order_id}
        except Exception as exc:
            if self.request.retries < self.max_retries:
                countdown = retry_delays[self.request.retries]
                raise self.retry(exc=exc, countdown=countdown)
            return {"ok": False, "order_id": order_id, "error": str(exc)}


@celery_app.task(name="tasks.grant_register_rewards", bind=True, max_retries=3)
def grant_register_rewards_async(self, relation_id: int) -> dict:
    retry_delays = [60, 300, 900]
    with db_session() as db:
        from app.models import ReferralRelation

        relation = db.query(ReferralRelation).filter(ReferralRelation.id == relation_id).with_for_update().first()
        if relation is None:
            return {"ok": False, "reason": "relation_not_found"}
        try:
            grant_register_rewards(db, relation)
            return {"ok": True, "relation_id": relation_id}
        except Exception as exc:
            if self.request.retries < self.max_retries:
                countdown = retry_delays[self.request.retries]
                raise self.retry(exc=exc, countdown=countdown)
            return {"ok": False, "relation_id": relation_id, "error": str(exc)}


def _tx_type_from_reward_type(reward_type: RewardType) -> CreditType:
    mapping = {
        RewardType.REGISTER_INVITE: CreditType.REFERRAL_INVITE,
        RewardType.REGISTER_BONUS: CreditType.REFERRAL_BONUS,
        RewardType.FIRST_PAY: CreditType.REFERRAL_FIRST_PAY,
        RewardType.RECURRING_PAY: CreditType.REFERRAL_RECURRING,
    }
    return mapping[reward_type]


@celery_app.task(name="tasks.retry_referral_reward")
def retry_referral_reward_async(reward_id: int) -> dict:
    with db_session() as db:
        reward = db.query(ReferralReward).filter(ReferralReward.id == reward_id).with_for_update().first()
        if reward is None:
            return {"ok": False, "reason": "reward_not_found"}
        if reward.status == "sent":
            return {"ok": True, "reward_id": reward.id, "status": "sent"}

        inviter = db.query(User).filter(User.id == reward.inviter_id).with_for_update().first()
        if inviter is None:
            reward.status = "failed"
            reward.retry_count += 1
            db.flush()
            return {"ok": False, "reason": "inviter_not_found"}

        tx_type = _tx_type_from_reward_type(reward.reward_type)
        change_credits(
            db,
            inviter,
            tx_type=tx_type,
            delta=reward.credits,
            reason=f"推广奖励重试:{reward.reward_type.value}",
            related_id=reward.reward_key,
            source=reward.source,
        )
        reward.status = "sent"
        reward.sent_at = datetime.utcnow()
        reward.retry_count += 1
        db.flush()
        return {"ok": True, "reward_id": reward.id, "status": reward.status}
