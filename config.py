# ============================================================
# 企业微信机器人 - 配置文件
# 优先级：环境变量 > config_local.py > config.py 默认值
# Railway 部署时，在 Dashboard 设置环境变量即可，无需修改此文件
# ============================================================

import os

# --- 群机器人 Webhook 地址（用于发送消息）---
WEBHOOK_URL = os.environ.get(
    "WECOM_WEBHOOK_URL",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY_HERE",
)

# --- 回调加密配置（用于接收消息）---
TOKEN = os.environ.get("WECOM_TOKEN", "YOUR_TOKEN")
ENCODING_AES_KEY = os.environ.get("WECOM_ENCODING_AES_KEY", "YOUR_ENCODING_AES_KEY")

# --- 服务器配置 ---
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

# --- 提醒配置 ---
DEFAULT_REMINDER_MINUTES = int(os.environ.get("REMINDER_MINUTES", "30"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL", "30"))
