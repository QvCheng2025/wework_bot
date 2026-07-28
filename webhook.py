"""通过企业微信群机器人 Webhook 发送消息"""

import requests


def send_text(webhook_url: str, content: str,
              mentioned_list: list = None) -> bool:
    """发送文本消息到企业微信群

    Args:
        webhook_url: 机器人 webhook 地址
        content: 消息正文（支持 &lt;@userid&gt; 提及）
        mentioned_list: 要 @ 的用户 userid 列表
    """
    body = {
        "msgtype": "text",
        "text": {
            "content": content,
            "mentioned_list": mentioned_list or [],
        },
    }
    try:
        resp = requests.post(webhook_url, json=body, timeout=10)
        result = resp.json()
        return result.get("errcode") == 0
    except Exception:
        return False


def send_markdown(webhook_url: str, content: str) -> bool:
    """发送 Markdown 格式消息"""
    body = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    try:
        resp = requests.post(webhook_url, json=body, timeout=10)
        result = resp.json()
        return result.get("errcode") == 0
    except Exception:
        return False
