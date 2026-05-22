"""微信消息读取工具 — 封装 wechat-cli"""
import subprocess, json, re
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

from config import WECHAT_CLI

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _cmd(*args: str) -> str:
    r = subprocess.run([WECHAT_CLI] + list(args), capture_output=True, text=True, timeout=60)
    raw = r.stdout.strip()
    # 去掉 [解密] 等非 JSON 前缀行
    if "{" in raw:
        return raw[raw.index("{"):]
    return raw

@tool
def search_messages(chat_name: str, start_date: Optional[str] = None, limit: int = 30) -> str:
    """搜索指定联系人的聊天记录。chat_name 是联系人备注名或群名。"""
    start = start_date or datetime.now().strftime("%Y-%m-%d")
    out = _cmd("search", "", "--chat", chat_name, "--start-time", start, "--limit", str(limit))
    try:
        data = json.loads(out)
        results = data.get("results", [])
        ret = "\n".join(results) if results else "暂无消息"
        print(f"{_ts()} [TOOL_DATA] search_messages({chat_name}) → {len(results)} 条", flush=True)
        for r2 in results[:3]:
            print(f"{_ts()} [TOOL_DATA]   {r2[:80]}", flush=True)
        if len(results) > 3:
            print(f"{_ts()} [TOOL_DATA]   ... 还有 {len(results)-3} 条", flush=True)
        return ret
    except json.JSONDecodeError as e:
        print(f"{_ts()} [TOOL_DATA] search_messages({chat_name}) 解析失败: {e}", flush=True)
        return "查询失败"

@tool
def get_new_messages() -> str:
    """获取新消息（增量检测，只返回未读过的消息）。"""
    out = _cmd("new-messages")
    try:
        data = json.loads(out)
        msgs = data.get("messages", [])
        print(f"{_ts()} [TOOL_DATA] get_new_messages() → {len(msgs)} 条新消息", flush=True)
        for m in msgs:
            print(f"{_ts()} [TOOL_DATA]   [{m.get('chat','')}] {m.get('last_message','')[:60]}", flush=True)
        if not msgs:
            return "没有新消息"
        lines = [f"[{m['chat']}] {m.get('last_message','')}" for m in msgs]
        return "\n".join(lines)
    except json.JSONDecodeError:
        print(f"{_ts()} [TOOL_DATA] get_new_messages() 解析失败", flush=True)
        return "查询失败"

@tool
def list_contacts(query: str = "") -> str:
    """搜索微信联系人。query 可选，搜索名字或备注。"""
    out = _cmd("contacts", "--query", query)
    try:
        contacts = json.loads(out)
        ret = "\n".join([f"{c.get('remark','') or c.get('nick_name','')} ({c['username']})" for c in contacts])
        print(f"{_ts()} [TOOL_DATA] list_contacts({query}) → {len(contacts)} 个", flush=True)
        return ret
    except:
        print(f"{_ts()} [TOOL_DATA] list_contacts({query}) 解析失败", flush=True)
        return "查询失败"
