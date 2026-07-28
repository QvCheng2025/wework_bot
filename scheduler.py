"""APScheduler 提醒调度器"""

from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import webhook
import db


_scheduler = None
_webhook_url = ""
_check_seconds = 30


def init_scheduler(webhook_url: str, check_interval_seconds: int = 30):
    """初始化后台调度器"""
    global _scheduler, _webhook_url, _check_seconds
    _webhook_url = webhook_url
    _check_seconds = check_interval_seconds
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _check_reminders,
        IntervalTrigger(seconds=check_interval_seconds),
        id="reminder_checker",
        name="检查待提醒任务",
        replace_existing=True,
    )
    _scheduler.start()


def _check_reminders():
    """定时检查是否需要发送提醒"""
    now = datetime.now()
    tasks = db.get_pending_reminders(now)
    for task in tasks:
        desc = task["task_desc"]
        deadline = task["deadline"]
        user = task["user_name"]

        text = (
            f"  [任务提醒]\n"
            f"任务：{desc}\n"
            f"截止时间：{deadline[:16]}\n"
        )
        if user:
            text += f"创建者：{user}\n"
        text += "\n请及时处理！"

        ok = webhook.send_text(_webhook_url, text)
        if ok:
            db.mark_reminded(task["id"])
            print(f"[提醒] 已发送: {desc} (任务#{task['id']})")
        else:
            print(f"[提醒] 发送失败: {desc} (任务#{task['id']})")


def shutdown():
    """关闭调度器"""
    if _scheduler:
        _scheduler.shutdown(wait=False)
