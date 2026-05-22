# WeChat Auto Agent

AI 驱动的微信自动回复助手。基于 LangChain + FastAPI，Qwen 驱动，自动读取微信消息、生成回复、通过桌面微信发送。

## 功能

- 自动检测新消息，AI 生成回复并发送
- 支持桌面微信发送（uiautomation）和手机发送（Midscene ADB）
- 复杂任务自动委派给 Claude CLI
- CLI 模型工具自动发现（Claude / Hermes / OpenCode 等）
- Web 管理界面（:5679）

## 作为 Claude Code 的消息工具

本项目是一个完整的微信自动回复方案，但也可以参考它的核心能力，只把**微信消息读取**部分独立出来，作为 Claude Code 的 Skill 或 MCP 工具使用。

### 思路

`tools/wechat_read.py` 中的三个函数（`search_messages`、`get_new_messages`、`list_contacts`）可以直接被 Claude Code 调用，让 Claude 读取微信群/联系人的消息、图片、文件，辅助开发工作。

这种模式的好处：
- **轻量**：不需要跑整个 agent 和 Web 服务，直接查、直接告诉 Claude
- **灵活**：可以按需组合，只注册需要的工具
- **安全**：数据不出本地，Claude 在本地执行

### 使用场景

- **需求分析**：PM 在群里发了需求文档图片 → Claude 搜到后分析内容、出方案
- **问题排查**：用户发了报错截图 → Claude 在群里搜到图片帮你排查
- **上下文获取**：Claude 直接调用工具搜索聊天记录来理解项目背景
- **信息汇总**："总结一下这个群今天讨论了什么" → Claude 搜消息后汇总

### 参考：作为 Claude Code Skill 使用

像你本地已经配置的 `wechat-cli` Skill 一样，把消息读取命令直接作为 Skill 注册：

```bash
# 查某个人的聊天记录
wechat-cli search "" --chat "联系人" --start-time "2026-05-01" --limit 30

# 查新消息
wechat-cli new-messages

# 搜索联系人
wechat-cli contacts --query "姓名"
```

核心就是一句命令的事——把 `wechat-cli search` 的结果喂给 Claude，它就能理解上下文。你现有的 `wechat-cli` Skill 就是这么工作的。

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
