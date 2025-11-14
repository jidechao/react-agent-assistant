# ReACT 智能助手

一个基于 OpenAI Agents SDK 的智能助手系统，实现了 ReACT 推理模式（Reasoning and Acting），支持多轮工具调用、对话历史管理、流式响应、MCP 工具集成以及现代化的 Web 用户界面。

## 📋 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置指南](#配置指南)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [许可证](#许可证)

## ✨ 功能特性

### 核心功能

- **🧠 ReACT 推理模式**
  - **观察 (Observe)**：仔细分析用户问题和当前可用信息
  - **思考 (Think)**：推理需要采取什么行动来解决问题
  - **行动 (Act)**：使用可用工具执行必要操作
  - **记忆 (Memory)**：记住之前的对话和操作结果

- **🔧 多轮工具调用**
  - 支持复杂任务的多步骤工具调用
  - 自动整合多次工具调用的结果
  - 智能决策何时需要继续调用工具

- **💾 对话历史管理**
  - 使用 Redis 存储对话历史
  - 自动保存和加载对话历史
  - 保持多次会话的上下文连续性
  - **多会话管理**：支持创建、切换、删除多个独立会话

- **⚡ 流式响应**
  - 实时输出生成内容
  - 打字机效果的交互体验
  - 降低首字节响应时间

- **🔌 自定义模型提供者**
  - 灵活配置 OpenAI 或兼容服务的 API
  - 支持自定义 base URL
  - 支持多种模型选择

- **🛠️ MCP 工具集成**
  - 支持 stdio 协议（标准输入输出）
  - 支持 SSE 协议（Server-Sent Events）
  - 支持 StreamableHTTP 协议
  - 支持 SSE 和 StreamableHTTP 的超时配置
  - 动态加载和管理工具服务器

- **🌐 Web 界面**
  - 现代化的 Web 用户界面（类似 ChatGPT）
  - 多会话管理（创建、切换、删除）
  - 实时流式响应展示
  - 工具调用和输出的可视化
  - WebSocket 实时通信
  - **Markdown 渲染**：助手消息支持完整的 Markdown 格式渲染
    - 标题、段落、列表等基本格式
    - 代码块语法高亮（支持多种编程语言）
    - 表格、引用、链接等高级格式
    - GitHub Flavored Markdown 支持
    - 流式 Markdown 渲染（实时更新）

### 技术亮点

- ✅ 异步 IO 设计，高效处理并发操作
- ✅ 模块化架构，易于扩展和维护
- ✅ 完善的错误处理和资源清理机制
- ✅ 优雅的命令行交互界面
- ✅ 现代化的 Web 用户界面（React + TypeScript + Tailwind CSS）
- ✅ 完整的单元测试覆盖
- ✅ 类型注解和文档字符串

## 🛠️ 技术栈

### 后端
- **Python 3.8+**
- **OpenAI Agents SDK** - Agent 框架和工具集成
- **FastAPI/WebSockets** - WebSocket 服务器
- **Redis** - 会话存储（必需）
- **Pydantic** - 配置验证
- **python-dotenv** - 环境变量管理

### 前端
- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式框架
- **Vite** - 构建工具
- **react-markdown** - Markdown 渲染
- **remark-gfm** - GitHub Flavored Markdown 支持
- **react-syntax-highlighter** - 代码块语法高亮

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户交互层                                │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  命令行界面 CLI   │      │   Web 界面        │           │
│  │   (main.py)      │      │  (React + TS)    │           │
│  └──────────────────┘      └──────────────────┘           │
└────────────────────────┬───────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  WebSocket  │  │  CLI 接口   │  │  Web API    │
│  服务器     │  │             │  │  (web_api)  │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent 核心层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ReACT 推理   │  │ 工具调用     │  │ 流式输出     │      │
│  │ 引擎         │  │ 管理器       │  │ 处理器       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ 模型提供者  │  │ 会话管理    │  │ MCP 工具集成│
│ (Custom     │  │ (Redis)     │  │ (stdio/sse/ │
│  Provider)  │  │             │  │  http)      │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    配置管理层                                 │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ .env 配置    │  │ mcp_config   │                         │
│  │ 加载器       │  │ .json 加载器 │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- **Python 3.8+**
- **Redis**（必需，用于会话存储）
- **Node.js 16+**（仅 Web 界面需要）
- **npm** 或 **yarn**（仅 Web 界面需要）

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd react-agent-assistant
```

2. **安装和启动 Redis**

```bash
# Windows (使用 Chocolatey)
choco install redis-64

# macOS (使用 Homebrew)
brew install redis
brew services start redis

# Linux (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis-server

# 验证 Redis 是否运行
redis-cli ping
# 应该返回: PONG
```

3. **安装后端依赖**

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

4. **安装前端依赖**（仅 Web 界面需要）

```bash
cd web
npm install
cd ..
```

5. **配置环境变量**

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，设置您的 API 密钥和配置
```

6. **配置 MCP 工具**（可选）

```bash
# 复制示例配置文件
cp mcp_config.example.json mcp_config.json

# 编辑 mcp_config.json，配置您的 MCP 服务器
```

### 运行程序

#### 方式一：命令行界面（CLI）

```bash
python main.py
```

#### 方式二：Web 界面

1. **启动后端 WebSocket 服务器**：

```bash
python web_main.py
```

服务器默认运行在 `ws://localhost:8000`

2. **启动前端开发服务器**（新终端窗口）：

```bash
cd web
npm run dev
```

前端默认运行在 `http://localhost:5173`（Vite 默认端口）

3. **访问 Web 界面**：

打开浏览器访问 `http://localhost:5173`

## ⚙️ 配置指南

### 1. 环境变量配置

创建 `.env` 文件（从 `.env.example` 复制）：

```env
# OpenAI API 配置
OPENAI_API_KEY=your_api_key_here          # 必需：您的 API 密钥
OPENAI_BASE_URL=https://api.openai.com/v1 # 必需：API 基础 URL
OPENAI_MODEL=gpt-4                         # 必需：使用的模型名称

# Redis 配置（必需）
REDIS_URL=redis://localhost:6379/0        # 必需：Redis 连接 URL

# Web 服务配置（可选）
WEB_PORT=8000                              # WebSocket 服务器端口（默认 8000）
WEB_HOST=localhost                         # WebSocket 服务器主机（默认 localhost）
```

**配置说明：**

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥或兼容服务的密钥 | `sk-...` |
| `OPENAI_BASE_URL` | API 端点 URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 模型名称 | `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| `REDIS_URL` | **必需** Redis 连接 URL | `redis://localhost:6379/0` |
| `WEB_PORT` | （可选）WebSocket 服务器端口 | `8000` |
| `WEB_HOST` | （可选）WebSocket 服务器主机 | `localhost` |

**使用其他 API 服务：**

如果您使用的是兼容 OpenAI 接口的其他服务，只需修改 `OPENAI_BASE_URL`：

```env
OPENAI_BASE_URL=https://your-api-service.com/v1
```

### 2. MCP 工具配置

创建 `mcp_config.json` 文件（从 `mcp_config.example.json` 复制）：

```json
{
  "servers": [
    {
      "name": "filesystem",
      "protocol": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"]
    },
    {
      "name": "weather",
      "protocol": "sse",
      "url": "http://localhost:8000/sse",
      "timeout": 30
    },
    {
      "name": "calculator",
      "protocol": "streamablehttp",
      "url": "http://localhost:8000/mcp",
      "timeout": 30
    }
  ]
}
```

**协议说明：**

| 协议 | 说明 | 必需字段 | 可选字段 | 适用场景 |
|------|------|----------|----------|----------|
| `stdio` | 通过标准输入输出通信 | `command`, `args` | `env` | 本地命令行工具 |
| `sse` | 通过 Server-Sent Events 通信 | `url` | `timeout`, `env` | 支持 SSE 的 HTTP 服务 |
| `streamablehttp` | 通过 HTTP 流式请求通信 | `url` | `timeout`, `env` | 标准 HTTP API 服务 |

**超时配置：**
- `timeout`：超时时间（秒），仅对 SSE 和 StreamableHTTP 协议有效
- 如果未配置，将使用默认超时或无限等待（取决于协议实现）

**注意：** 如果不需要 MCP 工具，可以删除 `mcp_config.json` 文件或将 `servers` 数组设为空 `[]`。

## 📖 使用指南

### CLI 界面使用

启动后，您将看到欢迎界面：

```
============================================================
欢迎使用 ReACT 智能助手！
============================================================

这是一个基于 ReACT 推理模式的智能助手，能够：
  • 观察和理解您的问题
  • 思考解决方案
  • 使用工具执行操作
  • 记住对话历史

输入 'exit' 或 'quit' 退出程序
输入 Ctrl+C 也可以随时退出

============================================================

您: 
```

### Web 界面使用

#### 会话管理

- **创建新会话**：点击左侧"新建会话"按钮
- **切换会话**：点击左侧会话列表中的任意会话
- **删除会话**：点击会话右侧的删除按钮（会同时删除该会话的所有聊天记录）
- **默认会话**：首次访问时自动创建一个默认会话

#### 发送消息

- 在底部输入框中输入您的问题
- 按 `Enter` 键或点击"发送"按钮发送消息
- AI 助手会实时流式返回响应，呈现打字机效果

#### 消息显示

- **用户消息**：显示在右侧，蓝色背景
- **助手消息**：显示在左侧，白色背景
  - 支持完整的 Markdown 格式渲染
  - 代码块自动语法高亮
  - 表格、列表、链接等格式友好显示
- **工具调用**：显示为独立卡片
  - 工具调用卡片：显示工具名称和调用参数（默认折叠）
  - 工具输出卡片：显示工具执行结果（默认折叠）
  - 状态指示：显示"执行中..."或"已完成"

#### Markdown 渲染功能

助手消息支持以下 Markdown 格式：

- **标题**：`# H1`, `## H2`, `### H3`
- **列表**：有序列表和无序列表
- **代码块**：自动语法高亮（支持多种编程语言）
  - 使用三个反引号包裹代码块
  - 指定语言类型：\`\`\`python
- **内联代码**：使用单个反引号包裹
- **链接**：自动识别并渲染为可点击链接
- **表格**：支持 GitHub Flavored Markdown 表格
- **引用**：使用 `>` 标记引用内容
- **粗体/斜体**：`**粗体**`, `*斜体*`

## 📁 项目结构

```
react-agent-assistant/
├── src/                      # 后端源代码
│   ├── agent_core.py        # Agent 核心逻辑（ReACT 推理）
│   ├── cli.py               # CLI 交互界面
│   ├── config.py            # 配置管理
│   ├── mcp_manager.py      # MCP 工具管理器
│   ├── model_provider.py    # 模型提供者
│   ├── session_manager.py  # 会话管理器
│   └── web_api.py           # WebSocket API 服务
├── web/                     # 前端源代码
│   ├── src/
│   │   ├── components/      # React 组件
│   │   │   ├── ChatWindow.tsx      # 聊天窗口组件
│   │   │   ├── MessageInput.tsx    # 消息输入组件
│   │   │   └── SessionList.tsx     # 会话列表组件
│   │   ├── services/        # 服务层
│   │   │   └── websocket.ts # WebSocket 客户端
│   │   ├── types/           # TypeScript 类型定义
│   │   ├── App.tsx          # 主应用组件
│   │   └── main.tsx         # 入口文件
│   ├── package.json         # 前端依赖配置
│   └── vite.config.ts       # Vite 构建配置
├── tests/                   # 单元测试
├── openspec/                # OpenSpec 规范文档
├── main.py                  # CLI 入口
├── web_main.py              # Web 服务入口
├── requirements.txt          # Python 依赖
├── mcp_config.json          # MCP 工具配置
└── README.md                # 项目文档
```

## 🛠️ 开发指南

### 后端开发

1. **运行测试**：

```bash
pytest
```

2. **代码格式**：

项目使用 Python 标准代码风格，建议使用 `black` 或 `autopep8` 格式化代码。

### 前端开发

1. **开发模式**：

```bash
cd web
npm run dev
```

2. **构建生产版本**：

```bash
cd web
npm run build
```

3. **预览生产构建**：

```bash
cd web
npm run preview
```

4. **代码检查**：

```bash
cd web
npm run lint
```

### 添加新的 MCP 工具

1. 在 `mcp_config.json` 中添加服务器配置
2. 根据协议类型配置相应字段
3. 重启服务即可使用新工具

### 自定义 Markdown 样式

Markdown 样式定义在 `web/src/components/ChatWindow.tsx` 中的 `ReactMarkdown` 组件的 `components` 属性中。您可以修改 Tailwind CSS 类来自定义样式。

## ❓ 常见问题

### Web 界面无法连接

1. 确保后端 WebSocket 服务器正在运行（`python web_main.py`）
2. 检查 `WEB_PORT` 环境变量是否与前端配置一致
3. 检查浏览器控制台是否有错误信息

### MCP 工具无法加载

1. 检查 `mcp_config.json` 文件格式是否正确
2. 对于 stdio 协议，确保命令和参数正确
3. 对于 SSE/StreamableHTTP 协议，确保 URL 可访问且超时配置合理
4. 查看后端日志了解详细错误信息

### 会话历史丢失

1. 确保 Redis 服务正在运行
2. 检查 Redis 连接 URL 是否正确（`REDIS_URL` 环境变量）
3. 检查 Redis 服务是否可访问
4. 查看后端日志了解详细错误信息

### Markdown 渲染问题

1. 确保前端依赖已正确安装（`npm install`）
2. 检查浏览器控制台是否有 JavaScript 错误
3. 代码块语法高亮需要指定语言类型

## 📄 许可证

[本开源软件遵循 MIT 许可证]
