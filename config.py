import json, os, shutil
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE, "agent.log")

# ── 加载 .env 文件 ──
_ENV_LOADED = False
def _load_dotenv():
    global _ENV_LOADED
    if _ENV_LOADED: return
    _ENV_LOADED = True
    for p in [os.path.join(BASE, ".env"), os.path.join(BASE, ".env.example")]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

# ── 读取环境变量 ──
def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

def env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").lower()
    if not v: return default
    return v in ("true", "1", "yes")

# ── AI 模型配置 ──
QWEN_API_BASE = env("QWEN_API_BASE", "http://localhost:8000/v1")
QWEN_API_KEY = env("QWEN_API_KEY", "")
QWEN_MODEL = env("QWEN_MODEL", "qwen3.6-27b-fp8")

MIDSCENE_ENV = {
    "MIDSCENE_MODEL_BASE_URL": env("MIDSCENE_MODEL_BASE_URL", "http://localhost:8000/v1"),
    "MIDSCENE_MODEL_API_KEY": env("MIDSCENE_MODEL_API_KEY", ""),
    "MIDSCENE_MODEL_NAME": env("MIDSCENE_MODEL_NAME", "qwen3.6-27b-fp8"),
    "MIDSCENE_MODEL_FAMILY": env("MIDSCENE_MODEL_FAMILY", "qwen3.6"),
    "MIDSCENE_MODEL_REASONING_ENABLED": "false",
}

# ── wechat-cli 路径（自动检测） ──
def _find_wechat_cli() -> str:
    custom = env("WECHAT_CLI_PATH")
    if custom and os.path.exists(custom):
        return custom
    # 常见安装路径
    candidates = [
        os.path.expanduser("~/AppData/Roaming/npm/node_modules/@dxz1/wechat-cli-win32-x64/bin/wechat-cli.exe"),
        os.path.expanduser("~/AppData/Roaming/npm/wechat-cli.cmd"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # 最后试 PATH
    which = shutil.which("wechat-cli")
    if which:
        return which
    return "wechat-cli"  # 兜底

WECHAT_CLI = _find_wechat_cli()

PORT = int(env("PORT", "5679"))

# ── 微信自身昵称（用于过滤自己发的消息） ──
SELF_NAMES = tuple(
    name.strip() for name in env("SELF_NAMES", "我").split(",") if name.strip()
)

# ── 微信联系人配置 ──
def load_contact_config() -> dict:
    """加载 wechat_agent.json（联系人名单、个性等）"""
    paths = [
        os.path.join(os.path.dirname(BASE), "wechat-agent", "wechat_agent.json"),
        os.path.join(BASE, "wechat_agent.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {"enabled_contacts": [], "send_method": "desktop", "personality": "直爽、干脆，像哥们聊天"}

def save_contact_config(cfg: dict):
    p = os.path.join(os.path.dirname(BASE), "wechat-agent", "wechat_agent.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
