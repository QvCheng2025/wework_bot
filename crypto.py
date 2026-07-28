"""企业微信消息加解密模块 —— 实现 WXBizMsgCrypt 协议"""

import base64
import hashlib
import random
import string
import struct
import socket
import time
import xml.etree.ElementTree as ET

from Crypto.Cipher import AES


class WXBizMsgCrypt:
    """企业微信回调消息加解密"""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str = ""):
        self.token = token
        self.corp_id = corp_id
        # AESKey = Base64_Decode(EncodingAESKey + "=")
        self.aes_key = base64.b64decode(encoding_aes_key + "=")

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def verify_url(self, msg_signature: str, timestamp: str,
                   nonce: str, echostr: str) -> str:
        """验证回调 URL 有效性（GET 请求）"""
        sig = self._signature(timestamp, nonce, echostr)
        if sig != msg_signature:
            raise ValueError("签名验证失败")
        return self._decrypt(echostr)

    def decrypt_msg(self, msg_signature: str, timestamp: str,
                    nonce: str, xml_body: str) -> str:
        """解密 POST 消息体，返回明文 XML 字符串"""
        root = ET.fromstring(xml_body)
        encrypt = root.find("Encrypt").text

        sig = self._signature(timestamp, nonce, encrypt)
        if sig != msg_signature:
            raise ValueError("签名验证失败")

        return self._decrypt(encrypt)

    def encrypt_msg(self, reply_xml: str, nonce: str,
                    timestamp: str = "") -> dict:
        """加密回复消息，返回 {encrypt, msg_signature, timestamp, nonce}"""
        ts = timestamp or str(int(time.time()))
        encrypt = self._encrypt(reply_xml)
        sig = self._signature(ts, nonce, encrypt)
        return {
            "encrypt": encrypt,
            "msg_signature": sig,
            "timestamp": ts,
            "nonce": nonce,
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        """SHA1(sort(token, timestamp, nonce, encrypt))"""
        parts = sorted([self.token, timestamp, nonce, encrypt])
        sha1 = hashlib.sha1()
        sha1.update("".join(parts).encode("utf-8"))
        return sha1.hexdigest()

    def _decrypt(self, ciphertext: str) -> str:
        """AES-CBC 解密"""
        raw = base64.b64decode(ciphertext)
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        plain = cipher.decrypt(raw)

        # 去除 PKCS#7 填充
        pad = plain[-1]
        content = plain[:-pad]

        # 结构: random(16) + msg_len(4) + msg + corp_id
        xml_len = socket.ntohl(struct.unpack("I", content[16:20])[0])
        result = content[20:20 + xml_len].decode("utf-8")
        return result

    def _encrypt(self, msg: str) -> str:
        """AES-CBC 加密"""
        rand = "".join(random.choices(
            string.ascii_letters + string.digits, k=16
        )).encode("utf-8")
        msg_bytes = msg.encode("utf-8")
        msg_len = struct.pack("!I", len(msg_bytes))

        raw = rand + msg_len + msg_bytes + self.corp_id.encode("utf-8")

        # PKCS#7 填充至 32 字节倍数
        block_size = 32
        pad = block_size - len(raw) % block_size
        raw += bytes([pad] * pad)

        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        encrypted = cipher.encrypt(raw)
        return base64.b64encode(encrypted).decode("ascii")


def parse_message_xml(xml_str: str) -> dict:
    """解析企业微信回调消息的 XML，提取关键字段"""
    root = ET.fromstring(xml_str)
    return {
        "to_user": root.findtext("ToUserName", ""),
        "from_user": root.findtext("FromUserName", ""),
        "create_time": root.findtext("CreateTime", ""),
        "msg_type": root.findtext("MsgType", ""),
        "content": root.findtext("Content", ""),
        "msg_id": root.findtext("MsgId", ""),
        "chat_id": root.findtext("ChatId", ""),
        "chat_type": root.findtext("ChatType", ""),
    }
