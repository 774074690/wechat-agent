# WeChat Auto Agent

AI 驱动的微信自动回复助手。基于 LangChain + FastAPI，Qwen 驱动，自动读取微信消息、生成回复、通过桌面微信发送。

## 功能

- 自动检测新消息，AI 生成回复并发送
- 支持桌面微信发送（uiautomation）和手机发送（Midscene ADB）
- 复杂任务自动委派给 Claude CLI
- CLI 模型工具自动发现（Claude / Hermes / OpenCode 等）
- Web 管理界面（:5679）

## 与 Claude Code 集成

本项目可作为 Claude Code 的"微信消息工具"，让 Claude 直接读取微信群/联系人的消息、图片、文件，辅助开发工作。

### 使用场景

- **需求分析**：PM 在群里发了需求文档 → Claude 看到后直接理解需求、出方案
- **问题排查**：用户发了报错截图到群里 → Claude 看到图片帮你分析
- **信息汇总**：群里讨论了一堆方案 → Claude 总结成要点
- **上下文获取**："看看任运辉上周发的流程图上说了什么" → Claude 搜索聊天记录获取上下文

### 配置方式

在 Claude Code 的项目中加入以下 MCP 配置（`.claude/settings.local.json`）：

```json
{
  "mcpServers": {
    "wechat-agent": {
      "command": "python",
      "args": ["path/to/app.py"]
    }
  }
}
```

或者在 Claude Code 中直接通过命令行调用：

```bash
# 查某个人的聊天记录
curl http://localhost:5679/api/chat -d '{"message":"搜索李吴科今天发的消息"}'

# 查群消息
curl http://localhost:5679/api/chat -d '{"message":"看看聊天群今天讨论了什么"}'

# 分析上下文
curl http://localhost:5679/api/chat -d '{"message":"搜索任运辉最近发的图片和文件"}'
```

启动服务后，Claude Code 通过 API 就能调取微信聊天记录来辅助工作。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制环境变量模板并修改：

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

微信联系人名单在 `wechat-agent/wechat_agent.json` 中配置：

```json
{
  "enabled_contacts": ["联系人A", "联系人B"],
  "send_method": "desktop",
  "personality": "直爽、干脆"
}
```

### 3. 启动

```bash
python app.py
```

浏览器打开 http://localhost:5679

## 前置依赖

- **wechat-cli** — 读取微信本地数据库：`npm install -g @dxz1/wechat-cli-win32-x64`
- **微信桌面版** — 用于发送消息（需要登录）
- **AI 模型** — Qwen3.6 或兼容的 OpenAI API

## 项目结构

```
├── app.py                 # FastAPI 主服务
├── agent.py               # LangChain Agent
├── config.py              # 配置加载（环境变量）
├── tools/
│   ├── wechat_read.py     # 微信消息读取
│   ├── wechat_send.py     # 桌面微信发送
│   ├── phone_control.py   # 手机 Midscene 发送
│   ├── wx_send.py         # uiautomation 发送脚本
│   └── midscene_send.js   # Midscene 手机控制
└── templates/
    └── index.html         # Web 管理界面
```
