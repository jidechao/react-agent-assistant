"""配置管理模块测试"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.config import Config, ConfigError, EnvConfig, MCPConfig, MCPServerConfig


class TestEnvConfig:
    """测试环境变量配置加载"""
    
    def test_load_env_config_success(self, tmp_path, monkeypatch):
        """测试成功加载环境变量配置"""
        # 清除现有环境变量
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        
        # 创建临时.env文件
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=test_key\n"
            "OPENAI_BASE_URL=https://api.openai.com/v1\n"
            "OPENAI_MODEL=gpt-4\n"
            "REDIS_URL=redis://localhost:6379/0\n"
        )
        
        # 加载配置
        config = Config.load_env_config(str(env_file))
        
        # 验证配置
        assert isinstance(config, EnvConfig)
        assert config.api_key == "test_key"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model_name == "gpt-4"
        assert config.redis_url == "redis://localhost:6379/0"
    
    def test_load_env_config_without_redis(self, tmp_path, monkeypatch):
        """测试加载环境变量配置（不包含Redis）"""
        # 清除现有环境变量
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        
        # 创建临时.env文件
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=test_key\n"
            "OPENAI_BASE_URL=https://api.openai.com/v1\n"
            "OPENAI_MODEL=gpt-4\n"
        )
        
        # 加载配置
        config = Config.load_env_config(str(env_file))
        
        # 验证配置
        assert config.redis_url is None
    
    def test_load_env_config_missing_required_vars(self, tmp_path, monkeypatch):
        """测试缺失必需环境变量时抛出异常"""
        # 清除现有环境变量
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        
        # 创建临时.env文件（缺少OPENAI_MODEL）
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENAI_API_KEY=test_key\n"
            "OPENAI_BASE_URL=https://api.openai.com/v1\n"
        )
        
        # 验证抛出ConfigError
        with pytest.raises(ConfigError) as exc_info:
            Config.load_env_config(str(env_file))
        
        assert "OPENAI_MODEL" in str(exc_info.value)
    
    def test_load_env_config_all_missing(self, tmp_path, monkeypatch):
        """测试所有必需环境变量都缺失时抛出异常"""
        # 清除现有环境变量
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        
        # 创建空的.env文件
        env_file = tmp_path / ".env"
        env_file.write_text("")
        
        # 验证抛出ConfigError
        with pytest.raises(ConfigError) as exc_info:
            Config.load_env_config(str(env_file))
        
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg
        assert "OPENAI_BASE_URL" in error_msg
        assert "OPENAI_MODEL" in error_msg


class TestMCPConfig:
    """测试MCP配置加载"""
    
    def test_load_mcp_config_success(self, tmp_path):
        """测试成功加载MCP配置"""
        # 创建临时mcp_config.json文件
        config_file = tmp_path / "mcp_config.json"
        config_data = {
            "servers": [
                {
                    "name": "filesystem",
                    "protocol": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                },
                {
                    "name": "weather",
                    "protocol": "sse",
                    "url": "http://localhost:8000/sse"
                },
                {
                    "name": "calculator",
                    "protocol": "streamablehttp",
                    "url": "http://localhost:8000/mcp"
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))
        
        # 加载配置
        config = Config.load_mcp_config(str(config_file))
        
        # 验证配置
        assert isinstance(config, MCPConfig)
        assert len(config.servers) == 3
        
        # 验证stdio服务器
        stdio_server = config.servers[0]
        assert stdio_server.name == "filesystem"
        assert stdio_server.protocol == "stdio"
        assert stdio_server.command == "npx"
        assert stdio_server.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        
        # 验证sse服务器
        sse_server = config.servers[1]
        assert sse_server.name == "weather"
        assert sse_server.protocol == "sse"
        assert sse_server.url == "http://localhost:8000/sse"
        
        # 验证streamablehttp服务器
        http_server = config.servers[2]
        assert http_server.name == "calculator"
        assert http_server.protocol == "streamablehttp"
        assert http_server.url == "http://localhost:8000/mcp"
    
    def test_load_mcp_config_empty_servers(self, tmp_path):
        """测试加载空的MCP配置"""
        # 创建临时mcp_config.json文件
        config_file = tmp_path / "mcp_config.json"
        config_data = {"servers": []}
        config_file.write_text(json.dumps(config_data))
        
        # 加载配置
        config = Config.load_mcp_config(str(config_file))
        
        # 验证配置
        assert isinstance(config, MCPConfig)
        assert len(config.servers) == 0
    
    def test_load_mcp_config_file_not_exists(self, tmp_path):
        """测试配置文件不存在时返回空配置"""
        # 使用不存在的文件路径
        config_file = tmp_path / "nonexistent.json"
        
        # 加载配置
        config = Config.load_mcp_config(str(config_file))
        
        # 验证返回空配置
        assert isinstance(config, MCPConfig)
        assert len(config.servers) == 0
    
    def test_load_mcp_config_invalid_json(self, tmp_path):
        """测试JSON格式错误时返回空配置"""
        # 创建格式错误的JSON文件
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text("{ invalid json }")
        
        # 加载配置
        config = Config.load_mcp_config(str(config_file))
        
        # 验证返回空配置
        assert isinstance(config, MCPConfig)
        assert len(config.servers) == 0
    
    def test_load_mcp_config_invalid_protocol(self, tmp_path):
        """测试协议类型错误时返回空配置"""
        # 创建包含无效协议的配置文件
        config_file = tmp_path / "mcp_config.json"
        config_data = {
            "servers": [
                {
                    "name": "test",
                    "protocol": "invalid_protocol",
                    "url": "http://localhost:8000"
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))
        
        # 加载配置
        config = Config.load_mcp_config(str(config_file))
        
        # 验证返回空配置
        assert isinstance(config, MCPConfig)
        assert len(config.servers) == 0
