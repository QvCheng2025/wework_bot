# ============================================================
# 企业微信自建应用 - 配置文件
# Railway 部署时在 Dashboard 设置环境变量
# ============================================================

import os

# --- 企业微信自建应用凭证 ---
CORP_ID = os.environ.get("WECOM_CORP_ID", "")
SECRET = os.environ.get("WECOM_SECRET", "")
AGENT_ID = int(os.environ.get("WECOM_AGENT_ID", "0"))

# --- 回调加密配置 ---
TOKEN = os.environ.get("WECOM_TOKEN", "YOUR_TOKEN")
ENCODING_AES_KEY = os.environ.get("WECOM_ENCODING_AES_KEY", "YOUR_ENCODING_AES_KEY")

# --- 服务器配置 ---
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))

# --- 提醒配置 ---
DEFAULT_REMINDER_MINUTES = int(os.environ.get("REMINDER_MINUTES", "30"))
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL", "30"))
