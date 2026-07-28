"""SQLite 持久化层 —— 存储任务和提醒记录"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                user_name TEXT DEFAULT '',
                task_desc TEXT NOT NULL,
                deadline TEXT NOT NULL,
                reminder_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                reminded_at TEXT
            )
        """)
        conn.commit()


def add_task(chat_id: str, user_name: str, task_desc: str,
             deadline: datetime, reminder_time: datetime) -> int:
    """添加一条任务，返回 task id"""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tasks (chat_id, user_name, task_desc,
               deadline, reminder_time, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (chat_id, user_name, task_desc,
             deadline.isoformat(), reminder_time.isoformat(),
             datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid


def get_pending_reminders(now: datetime) -> list:
    """获取所有到期未提醒的任务"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
                 AND reminder_time <= ?
               ORDER BY reminder_time ASC""",
            (now.isoformat(),)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_reminded(task_id: int):
    """标记任务已提醒"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'reminded', reminded_at = ? WHERE id = ?",
            (datetime.now().isoformat(), task_id)
        )
        conn.commit()


def get_all_tasks(limit: int = 50) -> list:
    """获取所有任务（用于面板展示）"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
