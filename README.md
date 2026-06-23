# 桌面侧边栏工具 (Desktop SideBar Tool)

一个常驻桌面的侧边栏工具，集成 AI 聊天、任务管理、文件操作、网页/软件监控与桌宠动画。UI 基于 PyQt5，AI 采用“规划-执行-审查”链路，能够把自然语言指令转成可执行的桌面操作。

## ✅ 主要功能

- **AI 聊天与工具调用**：ChatPanel 内置 AgentSession，支持流式输出、任务执行与历史记忆。
- **任务清单**：支持任务层级、拖拽排序、按日期切换、历史归档与统计。
- **文件与文档**：桌面文件读取/搜索，常用文件记录，Markdown/Word/CSV/PDF 处理。
- **网页与软件监控**：后台采集浏览器与软件窗口信息，写入知识库。
- **远程聊天网页**：FastAPI + WebSocket 提供移动端聊天页面与流式展示。
- **桌宠动画**：独立动画层窗口，支持序列帧与随机动画切换。
- **智能记账**：基于自然语言的收支记录与统计，数据存储于本地知识库。
- **邮件增强**：支持周期性（日/周/月/年）定时发送邮件。

## 🚀 快速开始

### 1) 环境与依赖

项目未提供统一的根目录 requirements.txt，依赖按模块拆分：

- **桌面主程序（必需）**
  - PyQt5
  - requests
  - uiautomation（网页/软件监控）
- **远程聊天网页（可选）**
  - fastapi
  - uvicorn
  - websockets（客户端在 .remote_chat/client/requirements.txt）
- **动画序列处理工具（可选）**
  - Pillow
  - PyQt5（tools/ani_gen_tools/sprite_processor/requirements.txt）

可按需安装：

```bash
pip install PyQt5 requests uiautomation
```

### 2) 统一配置 (New!)

所有第三方服务配置已整合至根目录下的 `config.json` 文件。请参照以下格式创建或修改：

```json
{
  "llm": {
    "api_key": "your_api_key",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1"
  },
  "email": {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_ssl": true,
    "smtp_user": "your_email@qq.com",
    "smtp_auth_code": "your_auth_code",
    "default_sender": "your_email@qq.com",
    "default_recipient": "your_email@qq.com"
  },
  "github": {
    "token": "your_github_token"
  }
}
```

> **注意**：旧版的 `硅基流动 AI API.txt`、`邮箱smtp`、`github token` 文件已被废弃，请使用 `config.json`。

### 3) 启动主程序

```bash
python ui_main.py
```

启动后会自动拉起网页监控与软件监控后台进程，并显示侧边栏 + 动画层窗口。

## 🧭 主程序流程

1. `ui_main.py` 创建 `QApplication`
2. 启动网页/软件监控后台进程
3. 创建 `DesktopSideBar`（侧边栏主 UI）
4. 创建 `AnimationLayerWindow`（桌宠动画层）

## 🧱 目录结构

- **入口**
  - `ui_main.py`
  - `config.json`（配置文件）
- **UI 层**
  - `ui/`：侧边栏、聊天、任务清单、文件面板、历史记录、设置面板
- **核心层**
  - `core/`：AgentSession + Planner/Executor/Reviewer
- **技能层**
  - `ai_tools/`、`ai_files_tools/`、`ai_web_tools/`
  - `ai_time_tools/`（含邮件与记账工具）
  - `ai_github_tools/`
- **监控与知识库**
  - `ai_konwledge/soft_konwledge/`
  - `ai_konwledge/web_konwledge/`
  - `ai_konwledge/money_knowledge.json`（记账数据）
- **动画资源**
  - `ani/`
- **远程聊天**
  - `.remote_chat/server/`（FastAPI 服务）
  - `.remote_chat/client/`（桌面端 WebSocket 客户端）
- **工具**
  - `tools/ani_gen_tools/sprite_processor/`（序列帧处理）
  - `tools/config_loader.py`（配置加载器）

## 🧠 AI Agent 架构

- `core/core_agent/Agent.py`：AgentSession，负责规划 → 执行 → 审查闭环
- `agent_planner.py`：生成执行计划
- `agent_excuter.py`：调用技能执行任务
- `agent_reviewer.py`：审查与回溯重规划

## 🗂️ 数据与配置落地

- **任务历史**：`history_data/history_data.json`
- **任务统计**：`history_data/token_usage_stats.json`
- **聊天记忆**：`core/core_data/core_chat_memory.json`
- **聊天记录（UI）**：`core/core_data/ui_chat_history.html`
- **网页监控数据**：`ai_konwledge/web_konwledge/konwledge.json`
- **软件监控数据**：`ai_konwledge/soft_konwledge/konwledge.json`
- **记账数据**：`ai_konwledge/money_knowledge.json`
- **监控配置**：`ai_konwledge/*/monitor_config.json`
- **动画状态**：`ani/animation_state.json`
- **UI 状态**：`ui/ui_state.json`
- **全局配置**：`config.json`

## 🌐 远程聊天网页

1. 启动服务端（读取 `.remote_chat/server/config.json`）
   ```bash
   python .remote_chat/server/server_app.py
   ```
2. 启动主程序后，ChatPanel 会加载 `.remote_chat/client` 并建立 WebSocket 连接
3. 浏览器访问 `http://<host>:<port>/` 查看移动端聊天界面

## 📌 技能注册说明

技能统一注册在 `ai_tools/skill_registry.py`，元数据在：

- `ai_tools/skills_metadata.json`
- `ai_tools/skills_metadata_brief.json`

### 新增技能模块

#### 💰 智能记账 (ai_money)
位于 `ai_time_tools/ai_money.py`，提供收支记录与查询功能：
- `add_transaction`：添加收支记录
- `get_transactions`：查询记录
- `get_summary`：获取统计信息

#### 📧 邮件增强 (ai_email)
位于 `ai_time_tools/ai_email.py`，增强了定时发送功能：
- `schedule_send_email`：支持 `recurrence` 参数，可配置 `daily`, `weekly`, `monthly`, `yearly` 或自定义间隔的周期性邮件。任务会自动持久化保存，重启程序不丢失。
- `add_realtime_email_task`：添加实时邮件任务，在每日首次启动程序时，自动调用 AI 生成内容（如新闻早报）并发送。
- `delete_email_task`：删除已设置的定时或实时邮件任务。
- `get_email_tasks`：查询当前所有的邮件任务列表。

## 🧑‍💻 GitHub 技能

位置：`ai_github_tools/`

### 依赖

- requests
- 本机已安装 git 并可在 PATH 中执行

### Token 配置

默认读取 `config.json` 中的 `github.token`。

### 主要能力

- 仓库管理：`list_github_repos`、`get_github_repo`、`create_github_repo`、`delete_github_repo`、`update_github_repo`
- 分支管理：`list_github_branches`、`create_github_branch`、`delete_github_branch`
- 文件管理：`list_github_contents`、`upload_github_file`、`delete_github_file`
- 本地与远程：`create_repo_from_local_path`、`git_clone_repo`、`git_pull_repo`、`git_checkout_branch`、`git_merge_branch`、`git_push_repo`

### 使用示例

创建仓库：

```json
{"action":"call_skill","name":"create_github_repo","arguments":{"name":"demo-repo","description":"demo","private":false}}
```

上传本地文件到仓库：

```json
{"action":"call_skill","name":"upload_github_file","arguments":{"owner":"your_name","repo":"demo-repo","local_path":"D:/path/to/file.txt","target_path":"docs/file.txt","branch":"main","commit_message":"add file"}}
```

从本地路径创建仓库并推送：

```json
{"action":"call_skill","name":"create_repo_from_local_path","arguments":{"local_path":"D:/path/to/project","repo_name":"project-repo","branch":"main","private":true}}
```

## 🧩 可选工具：序列帧处理

位于 `tools/ani_gen_tools/sprite_processor/`，提供命令行与独立 UI：

```bash
python tools/ani_gen_tools/sprite_processor/main.py
python tools/ani_gen_tools/sprite_processor/ui.py
```

---
*Last Updated: 2026-02-26*
