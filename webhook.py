"""通过企业微信自建应用 API 发送消息到群聊"""

import time
import requests
import config as _config

_token_cache = {"value": None, "expires_at": 0}


def _get_access_token() -> str:
    """获取 access_token，缓存到过期前 5 分钟"""
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    resp = requests.get(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": _config.CORP_ID, "corpsecret": _config.SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取 access_token 失败: {data}")

    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"] - 300
    return _token_cache["value"]


def send_text(chat_id: str, content: str) -> bool:
    """发送文本消息到指定群聊

    chat_id: 企业微信群聊 ChatId（从回调消息中获取）
    """
    if not chat_id:
        print("[webhook] chat_id 为空，跳过发送")
        return False

    token = _get_access_token()
    body = {
        "chatid": chat_id,
        "msgtype": "text",
        "text": {"content": content},
        "safe": 0,
    }
    try:
        resp = requests.post(
            "https://qyapi.weixin.qq.com/cgi-bin/appchat/send",
            params={"access_token": token},
            json=body,
            timeout=10,
        )
        result = resp.json()
        ok = result.get("errcode") == 0
        if not ok:
            print(f"[webhook] 发送失败: {result}")
        return ok
    except Exception as e:
        print(f"[webhook] 发送异常: {e}")
        return False
