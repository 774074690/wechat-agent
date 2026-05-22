"""FastAPI 主服务 — Web UI + Agent API 一体化"""
import asyncio, json, logging, os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import load_contact_config as load_config, save_contact_config as save_config, LOG_PATH, WECHAT_CLI, PORT, SELF_NAMES
from agent import create_agent

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

agent_executor = None
polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_executor, polling_task
    agent_executor = create_agent()
    polling_task = asyncio.create_task(poll_loop())
    add_log("[DAEMON] 自启动")
    yield
    if polling_task and not polling_task.done():
        polling_task.cancel()

app = FastAPI(lifespan=lifespan)

# ── 日志 ──

def add_log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── Web UI ──

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cfg = load_config()
    logs = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            logs = f.readlines()[-50:]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "contacts": ", ".join(cfg.get("enabled_contacts", [])),
        "send_method": cfg.get("send_method", "desktop"),
        "running": polling_task is not None and not polling_task.done(),
        "logs": "".join(logs[-50:]),
    })

# ── API ──

@app.post("/api/daemon/toggle")
async def toggle_daemon():
    global polling_task
    if polling_task and not polling_task.done():
        polling_task.cancel()
        add_log("[DAEMON] 已停止")
        return {"status": "stopped"}
    polling_task = asyncio.create_task(poll_loop())
    add_log("[DAEMON] 已启动")
    return {"status": "started"}

@app.post("/api/contacts")
async def update_contacts(request: Request):
    data = await request.json()
    cfg = load_config()
    cfg["enabled_contacts"] = [c.strip() for c in data.get("contacts", "").split(",") if c.strip()]
    save_config(cfg)
    add_log(f"[CONFIG] 联系人更新: {cfg['enabled_contacts']}")
    return {"msg": "已保存"}

@app.post("/api/send-method")
async def update_method(request: Request):
    data = await request.json()
    cfg = load_config()
    cfg["send_method"] = data.get("method", "desktop")
    save_config(cfg)
    add_log(f"[CONFIG] 发送方式: {cfg['send_method']}")
    return {"msg": "已保存"}

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    msg = data.get("message", "")
    add_log(f"[CHAT] 用户: {msg[:50]}")
    result = await agent_executor.ainvoke({"messages": [("human", msg)]})
    messages = result.get("messages", [])
    reply = messages[-1].content if messages else ""
    add_log(f"[CHAT] 回复: {reply[:100]}")
    return {"reply": reply}

@app.get("/api/logs")
async def get_logs():
    logs = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            logs = f.readlines()[-50:]
    return {"logs": "".join(logs)}

@app.get("/api/status")
async def get_status():
    cfg = load_config()
    import shutil
    cli_available = {}
    for name, cmd in cfg.get("available_cli_tools", {}).items():
        cli_available[name] = shutil.which(cmd.split()[0]) is not None
    return {
        "running": polling_task is not None and not polling_task.done(),
        "contacts": cfg.get("enabled_contacts", []),
        "send_method": cfg.get("send_method", "desktop"),
        "cli_tools": cli_available,
    }

# ── 后台轮询 ──

async def poll_loop():
    import subprocess, json, re
    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── 启动检测：用 new-messages 拿所有新消息 ──
    async def startup_check():
        cfg = load_config()
        contacts = cfg.get("enabled_contacts", [])
        add_log(f"[启动] 检查新消息...")
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: subprocess.run(
                [WECHAT_CLI, "new-messages"], capture_output=True, text=True, timeout=30)
        )
        try:
            raw = r.stdout.strip()
            data = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
        except:
            data = {}
        msgs = data.get("messages", [])
        relevant = [m for m in msgs if m.get("chat") in contacts]
        if not relevant:
            add_log(f"[启动] 没有未处理的新消息")
            return
        add_log(f"[启动] 发现 {len(relevant)} 条新消息")
        for msg in relevant:
            chat = msg.get("chat", "")
            sender = msg.get("sender", "")
            content = msg.get("last_message", "")
            add_log(f"[启动]   [{chat}] {sender}: {content[:50]}")
            if sender in SELF_NAMES:
                add_log(f"[启动]   自己发的，跳过")
                continue
            add_log(f"[启动]   → 拉上下文，调 agent 回复 {chat}")
            r2 = await asyncio.get_event_loop().run_in_executor(
                None, lambda c=chat: subprocess.run(
                    [WECHAT_CLI, "search", "", "--chat", c, "--start-time", today_str, "--limit", "15"],
                    capture_output=True, text=True, timeout=30)
            )
            try:
                raw2 = r2.stdout.strip()
                ctx_data = json.loads(raw2[raw2.index("{"):]) if "{" in raw2 else {}
                context = "\n".join(ctx_data.get("results", [])[-10:])
            except:
                context = f"[{chat}] {sender}: {content}"
            result = await agent_executor.ainvoke({
                "messages": [("human",
                    f"这是 [{chat}] 聊天记录：\n{context}\n\n调 run_claude(task=\"微信上看下 {chat} 发的图片\")，然后 send_wechat_message 发送。个性：{cfg.get('personality','')}")]
            })
            reply = (result.get("messages", []) or [None])[-1]
            reply_text = reply.content if reply else ""
            add_log(f"[启动]   agent: {reply_text[:100]}")

    await startup_check()
    add_log("[启动] 启动检测完成，进入实时监听")

    while True:
        try:
            cfg = load_config()
            contacts = cfg.get("enabled_contacts", [])
            if not contacts:
                await asyncio.sleep(1); continue

            # 轮询新消息
            r = await asyncio.get_event_loop().run_in_executor(
                None, lambda: subprocess.run(
                    [WECHAT_CLI, "new-messages"], capture_output=True, text=True, timeout=30)
            )
            try:
                raw = r.stdout.strip()
                data = json.loads(raw[raw.index("{"):])
            except (json.JSONDecodeError, ValueError):
                await asyncio.sleep(1); continue

            new_msgs = data.get("messages", [])

            # 每 30 秒打印监听状态
            poll_loop._count = getattr(poll_loop, "_count", 0) + 1
            if poll_loop._count % 30 == 0:
                add_log(f"[监听] 最后检测: {datetime.now().strftime('%H:%M:%S')}，新消息数: {len(new_msgs)}")

            if new_msgs:
                relevant = [m for m in new_msgs if m.get("chat") in contacts]
                add_log(f"[轮询] new-messages 返回 {len(new_msgs)} 条，匹配联系人 {len(relevant)} 条")
                for m in new_msgs:
                    add_log(f"[轮询]   原始: [{m.get('chat','')}] {m.get('last_message','')[:50]}")
                if relevant:
                    for msg in relevant:
                        add_log(f"[检测] {msg['chat']}: {msg.get('last_message','')[:60]}")
                    contexts = []
                    for msg in relevant:
                        r2 = await asyncio.get_event_loop().run_in_executor(
                            None, lambda c=msg["chat"]: subprocess.run(
                                [WECHAT_CLI, "search", "", "--chat", c, "--start-time", today_str, "--limit", "15"],
                                capture_output=True, text=True, timeout=30)
                        )
                        try:
                            raw2 = r2.stdout.strip()
                            ctx = json.loads(raw2[raw2.index("{"):])
                            ctx_lines = ctx.get("results", [])[-10:]
                            contexts.append(f"[{msg['chat']}]\n" + "\n".join(ctx_lines))
                        except Exception as e:
                            add_log(f"[轮询]   拉上下文失败: {e}")
                    add_log(f"[轮询] 调 agent 生成回复...")
                    prompt_parts = ["有新消息，以下是相关聊天记录：\n" + "\n---\n".join(contexts)]
                    for msg in relevant:
                        prompt_parts.append(f"请回复 [{msg['chat']}]，调用 send_wechat_message(contact=\"{msg['chat']}\", message=...) 发送")
                    prompt_parts.append(f"个性: {cfg.get('personality','')}")
                    result = await agent_executor.ainvoke({
                        "messages": [("human", "\n".join(prompt_parts))]
                    })
                    msgs = result.get("messages", [])
                    reply = msgs[-1].content if msgs else ""
                    add_log(f"[回复] agent 输出: {reply[:200]}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            add_log(f"[ERROR] {e}")
        await asyncio.sleep(1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
