"""发送消息工具 — 桌面微信"""
import subprocess, sys, os
from datetime import datetime
from langchain_core.tools import tool

WX_SEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wx_send.py")

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def send_wechat_message(contact: str, message: str) -> str:
    """通过桌面微信发消息给指定联系人。contact 是备注名。"""
    print(f"{_ts()} [TOOL_DATA] send_wechat_message(contact=\"{contact}\", message=\"{message[:50]}...\")", flush=True)
    r = subprocess.run(
        [sys.executable, WX_SEND, contact, message],
        capture_output=True, text=True, timeout=30
    )
    result = r.stdout.strip() or "发送失败"
    print(f"{_ts()} [TOOL_DATA] send_wechat_message → {result[:100]}", flush=True)
    return result
