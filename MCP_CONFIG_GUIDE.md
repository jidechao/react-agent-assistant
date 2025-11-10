# MCP 服务器配置指南

本文档说明如何配置 MCP (Model Context Protocol) 服务器。

## 配置文件位置

MCP 配置文件位于项目根目录：`mcp_config.json`

## 配置文件结构

```json
{
  "servers": [
    {
      "name": "服务器名称",
      "protocol": "协议类型",
      "command": "命令（stdio协议）",
      "args": ["参数列表"],
      "url": "服务器URL（sse/streamablehttp协议）",
      "env": {
        "环境变量名": "环境变量值"
      },
      "description": "服务器描述（可选）"
    }
  ]
}
```

## 支持的协议类型

### 1. stdio 协议

通过标准输入输出与本地进程通信。

**必需字段：**
- `name`: 服务器名称
- `protocol`: "stdio"
- `command`: 要执行的命令
- `args`: 命令参数列表

**可选字段：**
- `env`: 环境变量字典

**示例：**

```json
{
  "name": "filesystem",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"],
  "env": {
    "NODE_ENV": "production",
    "DEBUG": "false"
  }
}
```

### 2. sse 协议

通过 Server-Sent Events 与远程服务器通信。

**必需字段：**
- `name`: 服务器名称
- `protocol`: "sse"
- `url`: 服务器 URL

**示例：**

```json
{
  "name": "custom-api",
  "protocol": "sse",
  "url": "http://localhost:8000/sse"
}
```

### 3. streamablehttp 协议

通过 HTTP 流式传输与远程服务器通信。

**必需字段：**
- `name`: 服务器名称
- `protocol`: "streamablehttp"
- `url`: 服务器 URL

**示例：**

```json
{
  "name": "amap-maps",
  "protocol": "streamablehttp",
  "url": "https://mcp.amap.com/mcp?key=your_api_key"
}
```

## 环境变量配置

### 为什么需要环境变量？

某些 MCP 服务器需要 API 密钥、访问令牌或其他敏感信息。使用环境变量可以：
- 保护敏感信息不被提交到版本控制
- 在不同环境中使用不同的配置
- 遵循安全最佳实践

### 如何配置环境变量

#### 方法 1：在 mcp_config.json 中直接配置

```json
{
  "name": "github",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here",
    "GITHUB_API_URL": "https://api.github.com"
  }
}
```

#### 方法 2：使用系统环境变量（推荐）

1. 在 `.env` 文件中定义环境变量：

```bash
# MCP 服务器环境变量
GITHUB_TOKEN=ghp_your_token_here
AMAP_API_KEY=your_amap_key_here
```

2. 在代码中读取并传递给 MCP 配置（需要自定义实现）

## 常用 MCP 服务器配置示例

### 1. 文件系统服务器

允许 Agent 读写指定目录中的文件。

```json
{
  "name": "filesystem",
  "protocol": "stdio",
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "D:\\project\\my-project"
  ],
  "description": "文件系统访问工具"
}
```

**注意：** Windows 路径需要使用双反斜杠 `\\` 或正斜杠 `/`

### 2. GitHub 服务器

提供 GitHub 仓库访问能力。

```json
{
  "name": "github",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token"
  },
  "description": "GitHub 仓库访问工具"
}
```

**获取 GitHub Token：**
1. 访问 https://github.com/settings/tokens
2. 生成新的 Personal Access Token
3. 选择所需的权限范围

### 3. 高德地图服务器

提供地图、位置、路径规划等服务。

```json
{
  "name": "amap-maps",
  "protocol": "streamablehttp",
  "url": "https://mcp.amap.com/mcp?key=your_amap_key",
  "description": "高德地图服务"
}
```

**获取高德地图 API Key：**
1. 访问 https://lbs.amap.com/
2. 注册并创建应用
3. 获取 Web 服务 API Key

### 4. Brave Search 服务器

提供网络搜索能力。

```json
{
  "name": "brave-search",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-brave-search"],
  "env": {
    "BRAVE_API_KEY": "your_brave_api_key"
  },
  "description": "Brave 搜索引擎"
}
```

### 5. PostgreSQL 数据库服务器

提供数据库查询能力。

```json
{
  "name": "postgres",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres"],
  "env": {
    "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/dbname"
  },
  "description": "PostgreSQL 数据库访问"
}
```

## 安全最佳实践

### 1. 不要在配置文件中硬编码敏感信息

❌ **错误做法：**
```json
{
  "env": {
    "API_KEY": "sk-1234567890abcdef"
  }
}
```

✅ **正确做法：**
- 使用环境变量
- 使用密钥管理服务
- 使用配置管理工具

### 2. 将 mcp_config.json 添加到 .gitignore

如果配置文件包含敏感信息，确保不会被提交到版本控制：

```bash
# .gitignore
mcp_config.json
```

提供一个示例配置文件：
```bash
mcp_config.example.json  # 提交到版本控制
```

### 3. 限制文件系统访问范围

只授予必要的目录访问权限：

```json
{
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "/path/to/specific/directory"  // 不要使用根目录
  ]
}
```

## 故障排查

### 问题 1：MCP 服务器加载失败

**可能原因：**
- 命令或路径不正确
- 缺少必需的环境变量
- 网络连接问题（远程服务器）

**解决方法：**
1. 检查日志输出
2. 验证命令是否可以在终端中独立运行
3. 确认所有必需的环境变量已设置

### 问题 2：stdio 协议服务器无法启动

**可能原因：**
- Node.js 或 npx 未安装
- npm 包不存在或版本不兼容

**解决方法：**
```bash
# 检查 Node.js 和 npx
node --version
npx --version

# 手动安装 MCP 服务器包
npm install -g @modelcontextprotocol/server-filesystem
```

### 问题 3：环境变量未生效

**可能原因：**
- 环境变量名称拼写错误
- 环境变量值格式不正确

**解决方法：**
1. 检查环境变量名称是否与服务器文档一致
2. 验证环境变量值的格式
3. 查看服务器日志获取详细错误信息

## 更多资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 服务器列表](https://github.com/modelcontextprotocol/servers)
- [创建自定义 MCP 服务器](https://modelcontextprotocol.io/docs/building-servers)

## 示例配置文件

完整的示例配置文件请参考：`mcp_config.example.json`
