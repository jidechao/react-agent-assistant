# MCP 环境变量配置示例

## 快速开始

### 1. 基本配置（无环境变量）

```json
{
  "servers": [
    {
      "name": "filesystem",
      "protocol": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/directory"]
    }
  ]
}
```

### 2. 带环境变量的配置

```json
{
  "servers": [
    {
      "name": "github",
      "protocol": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  ]
}
```

## 实际使用案例

### 案例 1：GitHub 集成

**需求：** 让 AI 助手能够访问和操作 GitHub 仓库

**配置：**
```json
{
  "name": "github",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxxxxxxxx"
  }
}
```

**获取 Token：**
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：`repo`, `read:org`, `read:user`
4. 生成并复制 token

### 案例 2：数据库访问

**需求：** 让 AI 助手能够查询数据库

**配置：**
```json
{
  "name": "postgres",
  "protocol": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres"],
  "env": {
    "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/mydb"
  }
}
```

### 案例 3：多个环境变量

**需求：** 配置需要多个环境变量的服务

**配置：**
```json
{
  "name": "custom-service",
  "protocol": "stdio",
  "command": "node",
  "args": ["./custom-mcp-server.js"],
  "env": {
    "API_KEY": "your_api_key",
    "API_SECRET": "your_api_secret",
    "BASE_URL": "https://api.example.com",
    "DEBUG": "true",
    "TIMEOUT": "30000"
  }
}
```

## 安全建议

### ❌ 不推荐：直接在配置文件中写入敏感信息

```json
{
  "env": {
    "API_KEY": "sk-1234567890abcdef"  // 不要这样做！
  }
}
```

### ✅ 推荐：使用环境变量或密钥管理

**方法 1：使用 .env 文件**

1. 在 `.env` 文件中定义：
```bash
GITHUB_TOKEN=ghp_your_token_here
```

2. 在代码中读取并动态生成配置（需要自定义实现）

**方法 2：使用系统环境变量**

```bash
# Linux/Mac
export GITHUB_TOKEN=ghp_your_token_here

# Windows PowerShell
$env:GITHUB_TOKEN="ghp_your_token_here"

# Windows CMD
set GITHUB_TOKEN=ghp_your_token_here
```

**方法 3：使用密钥管理服务**
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

## 测试配置

运行测试脚本验证配置：

```bash
python test_mcp_env.py
```

## 常见问题

### Q: 环境变量没有生效？

**A:** 检查以下几点：
1. 环境变量名称是否正确
2. JSON 格式是否正确（注意逗号和引号）
3. 服务器是否支持该环境变量

### Q: 如何知道服务器需要哪些环境变量？

**A:** 查看服务器文档：
- GitHub: https://github.com/modelcontextprotocol/servers/tree/main/src/github
- 其他服务器：查看对应的 README

### Q: 可以使用相对路径吗？

**A:** 可以，但建议使用绝对路径以避免路径问题：

```json
{
  "args": [
    "-y",
    "@modelcontextprotocol/server-filesystem",
    "D:\\project\\my-project"  // 绝对路径
  ]
}
```

## 更多示例

查看完整配置示例：
- `mcp_config.example.json` - 示例配置文件
- `MCP_CONFIG_GUIDE.md` - 详细配置指南
