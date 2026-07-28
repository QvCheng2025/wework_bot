"""企业微信任务提醒机器人 - Flask 主应用"""

import sys
import os
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from flask import Flask, request, render_template_string

# 确保可以 import 同目录的模块
sys.path.insert(0, os.path.dirname(__file__))

import db
import parser
import webhook as wh
import scheduler as sched
from crypto import WXBizMsgCrypt, parse_message_xml

# ---- lazy crypto init ----

_wx_crypt = None

def get_wx_crypt():
    global _wx_crypt
    if _wx_crypt is None:
        _wx_crypt = WXBizMsgCrypt(
            token=config.TOKEN,
            encoding_aes_key=config.ENCODING_AES_KEY,
            corp_id=getattr(config, "CORP_ID", ""),
        )
    return _wx_crypt


# ---- 加载配置 ----
try:
    import config_local as config  # type: ignore
except ImportError:
    import config as _cfg
    config = _cfg  # type: ignore

app = Flask(__name__)
db.init_db()

# 初始化加解密实例



# ====================================================================
# 企业微信回调路由 (接收群消息)
# ====================================================================

@app.route("/callback", methods=["GET", "POST"])
def callback():
    """企业微信回调 URL 入口"""
    sig = request.args.get("msg_signature", "")
    ts = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if request.method == "GET":
        # URL 验证
        echostr = request.args.get("echostr", "")
        try:
            plain = get_wx_crypt().verify_url(sig, ts, nonce, echostr)
            return plain, 200, {"Content-Type": "text/plain"}
        except Exception as e:
            app.logger.error(f"URL 验证失败: {e}")
            return "fail", 403

    # POST: 接收消息
    xml_body = request.get_data(as_text=True); app.logger.info(f"Raw POST body ({len(xml_body)} bytes): {xml_body[:200]}")
    try:
        plain_xml = get_wx_crypt().decrypt_msg(sig, ts, nonce, xml_body)
    except Exception as e:
        app.logger.error(f"消息解密失败: {e}")
        return "fail", 403

    msg = parse_message_xml(plain_xml)
    app.logger.info(f"收到消息: {msg}")

    if msg["msg_type"] == "text":
        _handle_text_message(msg)

    # 企业微信要求返回空字符串或 "success"
    return "", 200


def _handle_text_message(msg: dict):
    """处理文本消息"""
    content = (msg.get("content") or "").strip()

    # 解析任务
    task_desc, deadline = parser.parse_message(content)

    if not deadline:
        # 未能识别出截止时间，回复帮助信息
        help_text = (
            "没有识别到截止时间。用法示例：\n"
            "  - @机器人 明天下午3点 提交周报\n"
            "  - @机器人 7月30日 10:00 开会\n"
            "  - @机器人 周五下午5点 发版本\n"
            "  - @机器人 3天后 交报告\n"
        )
        wh.send_text(msg.get('chat_id', ''), help_text)
        return

    # 计算提醒时间
    reminder_minutes = getattr(config, "DEFAULT_REMINDER_MINUTES", 30)
    reminder_time = deadline - timedelta(
        minutes=reminder_minutes
    )

    now = datetime.now()
    if reminder_time < now:
        # 提醒时间已过，立即提醒
        reminder_time = now

    # 持久化
    chat_id = msg.get("chat_id", "")
    user_name = msg.get("from_user", "")
    task_id = db.add_task(chat_id, user_name, task_desc, deadline, reminder_time)

    # 回复确认
    confirm = (
        f"  [任务已记录]\n"
        f"任务：{task_desc}\n"
        f"截止时间：{deadline.strftime('%Y-%m-%d %H:%M')}\n"
        f"将提前 {reminder_minutes} 分钟提醒"
    )
    wh.send_text(msg.get('chat_id', ''), confirm)

    app.logger.info(f"任务已创建 #{task_id}: {task_desc} -> {deadline}")


# ====================================================================
# 简易管理面板
# ====================================================================

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>任务提醒面板</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       background:#f5f5f5;color:#333;padding:20px;max-width:900px;margin:0 auto}
  h1{font-size:20px;margin-bottom:16px}
  table{width:100%;border-collapse:collapse;background:#fff;border-radius:6px;
         overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
  th,td{padding:10px 14px;text-align:left;font-size:13px}
  th{background:#f0f0f0;font-weight:600;color:#555}
  tr{border-bottom:1px solid #eee}
  tr:last-child{border-bottom:none}
  .pending{color:#e67e22;font-weight:600}
  .reminded{color:#27ae60}
  .empty{text-align:center;padding:40px;color:#999;font-size:14px}
  .refresh{display:inline-block;margin-left:12px;font-size:12px;color:#3498db;
            cursor:pointer;text-decoration:none}
  .form-section{background:#fff;padding:16px;border-radius:6px;
                 margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
  .form-section h2{font-size:15px;margin-bottom:10px}
  .form-row{display:flex;gap:8px;flex-wrap:wrap}
  .form-row input,.form-row button{padding:8px 12px;border:1px solid #ddd;
        border-radius:4px;font-size:13px}
  .form-row input{flex:1;min-width:150px}
  .form-row button{background:#3498db;color:#fff;border:none;cursor:pointer}
  .form-row button:hover{background:#2980b9}
  .note{font-size:12px;color:#999;margin-top:8px}
</style>
</head>
<body>
<h1>  群任务提醒 - 管理面板
  <a class="refresh" href="javascript:location.reload()">刷新</a>
</h1>

<div class="form-section">
  <h2>手动添加任务</h2>
  <form method="post" action="/add">
    <div class="form-row">
      <input name="task_desc" placeholder="任务描述, 如: 提交周报" required/>
      <input name="deadline" placeholder="截止时间, 如: 2026-07-30 15:00" required/>
      <button type="submit">添加</button>
    </div>
  </form>
  <p class="note">支持格式: YYYY-MM-DD HH:MM / 明天下午3点 / 周五10:00 / 3天后 等</p>
</div>

<table>
<thead><tr><th>ID</th><th>任务</th><th>截止时间</th><th>提醒时间</th><th>状态</th></tr></thead>
<tbody>
{% if tasks %}
  {% for t in tasks %}
  <tr>
    <td>{{ t.id }}</td>
    <td>{{ t.task_desc }}</td>
    <td>{{ t.deadline[:16] }}</td>
    <td>{{ t.reminder_time[:16] }}</td>
    <td><span class="{{ t.status }}">{{ '等待提醒' if t.status=='pending' else '已提醒' }}</span></td>
  </tr>
  {% endfor %}
{% else %}
  <tr><td colspan="5" class="empty">暂无任务</td></tr>
{% endif %}
</tbody>
</table>
</body>
</html>"""


@app.route("/")
def dashboard():
    """任务列表面板"""
    tasks = db.get_all_tasks()
    return render_template_string(_DASHBOARD_HTML, tasks=tasks)


@app.route("/add", methods=["POST"])
def add_task_manual():
    """手动添加任务（兼容无法使用回调的场景）"""
    task_desc = (request.form.get("task_desc") or "").strip()
    deadline_str = (request.form.get("deadline") or "").strip()

    if not task_desc or not deadline_str:
        return "缺少参数", 400

    # 复用 parser 尝试解析时间
    parsed_task, deadline = parser.parse_message(
        f"{task_desc} {deadline_str}"
    )
    if not deadline:
        return f"无法解析截止时间: {deadline_str}", 400

    reminder_minutes = getattr(config, "DEFAULT_REMINDER_MINUTES", 30)
    reminder_time = deadline - timedelta(minutes=reminder_minutes)
    now = datetime.now()
    if reminder_time < now:
        reminder_time = now

    task_id = db.add_task("manual", "", task_desc or parsed_task, deadline, reminder_time)

    return f"任务 #{task_id} 已添加。截止: {deadline}", 200


# ====================================================================
# 启动
# ====================================================================

def main():
    sched.init_scheduler(
        check_interval_seconds=getattr(config, "CHECK_INTERVAL_SECONDS", 30),
    )
    print(f"  服务启动: http://0.0.0.0:{config.PORT}")
    print(f"  回调地址: http://<你的公网地址>:{config.PORT}/callback")
    print(f"  管理面板: http://0.0.0.0:{config.PORT}")
    try:
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=False,
            use_reloader=False,
        )
    finally:
        sched.shutdown()


if __name__ == "__main__":
    main()








