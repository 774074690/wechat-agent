"""LangChain Agent — Qwen 为入口，工具可动态扩展"""
import subprocess, shutil
from datetime import datetime
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.callbacks import BaseCallbackHandler

from config import QWEN_API_BASE, QWEN_API_KEY, QWEN_MODEL, load_contact_config as load_cfg
from tools.wechat_read import search_messages, get_new_messages, list_contacts
from tools.wechat_send import send_wechat_message
from tools.phone_control import send_via_phone


def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class LogCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        for p in prompts:
            print(f"{_ts()} [LLM] >>> 发送提示词({len(p)}字符)", flush=True)

    def on_llm_end(self, response, **kwargs):
        gen = response.generations[0][0]
        txt = gen.text[:100] if gen.text else ""
        msg = gen.message
        tcs = getattr(msg, "tool_calls", None) or msg.additional_kwargs.get("tool_calls", [])
        if tcs:
            for tc in tcs:
                if isinstance(tc, dict):
                    fn = tc.get("function", tc)
                    name = fn.get("name", fn.get("function", "?"))
                    args = fn.get("arguments", "")[:150]
                else:
                    name = getattr(tc, "name", "?")
                    args = str(getattr(tc, "args", ""))[:150]
                print(f"{_ts()} [LLM] <<< 调工具: {name}({args})", flush=True)
        elif txt:
            print(f"{_ts()} [LLM] <<< {txt}", flush=True)
        else:
            print(f"{_ts()} [LLM] <<< (空)", flush=True)

    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"{_ts()} [TOOL] → {serialized.get('name','')} {str(input_str)[:150]}", flush=True)

    def on_tool_end(self, output, **kwargs):
        print(f"{_ts()} [TOOL] ← {str(output)[:150]}", flush=True)


def _build_cli_tool(name: str, command: str):
    """工厂：为某个 CLI 命令创建 tool 函数"""
    def _run(task: str) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        shell_cmd = f'{command} "{task}"'
        print(f"{ts} [CLI] {name} 开始执行...", flush=True)
        lines_out = []
        try:
            proc = subprocess.Popen(
                shell_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            import time as _time
            deadline = _time.time() + 1800
            while _time.time() < deadline:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    line = line.rstrip("\n\r")
                    lines_out.append(line)
                    print(f"{ts} [CLI:{name}] {line[:150]}", flush=True)
            if proc.poll() is None:
                proc.kill()
                print(f"{ts} [CLI] {name} 超时(1800s)", flush=True)
                return f"{name} 超时"
            out = "\n".join(lines_out[-20:]) or f"{name} 返回为空"
            print(f"{ts} [CLI] {name} 完成，共 {len(lines_out)} 行输出", flush=True)
            return out
        except Exception as e:
            print(f"{ts} [CLI] {name} 错误: {e}", flush=True)
            return f"{name} 错误: {e}"

    _run.__name__ = f"run_{name}"
    _run.__doc__ = f"用 {name} 处理复杂任务（编程、技术分析等）。仅当 Qwen 无法处理时使用。"
    return tool(_run)


def _discover_cli_tools() -> list:
    """扫描系统，注册可用的 CLI 模型工具"""
    cli_configs = load_cfg().get("available_cli_tools", {})
    discovered = []
    for name, command in cli_configs.items():
        cmd_name = command.split()[0]
        if shutil.which(cmd_name):
            discovered.append(_build_cli_tool(name, command))
    return discovered


def create_agent():
    cfg = load_cfg()
    personality = cfg.get("personality", "直爽、干脆")
    send_method = cfg.get("send_method", "desktop")

    callbacks = [LogCallback()]
    llm = ChatOpenAI(
        base_url=QWEN_API_BASE,
        api_key=QWEN_API_KEY,
        model=QWEN_MODEL,
        temperature=0.3,
        callbacks=callbacks,
        model_kwargs={"extra_body": {"enable_thinking": False}},
    )

    tools = [
        search_messages,
        get_new_messages,
        list_contacts,
        send_wechat_message,
        send_via_phone,
    ] + _discover_cli_tools()

    tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in tools])

    system_prompt = f"""你是微信自动回复助手，由 Qwen3.6 驱动。可用工具：
{tool_desc}

关键规则：
1. 回复必须调 send_wechat_message(contact="联系人真实姓名", message="内容") 发送
2. contact 参数必须填对方的真实姓名，不能填错人
3. 看到 [图片] [文件] [链接] 时，调 run_claude(task="微信上看下 联系人名 发的图片/文件，分析下")
4. 编程、分析等复杂任务也调 run_claude
5. 当前发送方式: {send_method}
6. 个性: {personality}"""

    return create_react_agent(llm, tools, prompt=system_prompt)
