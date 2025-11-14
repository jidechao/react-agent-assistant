"""MCP 超时配置测试"""

import pytest
from unittest.mock import Mock, patch

from src.config import MCPServerConfig, MCPConfig
from src.mcp_manager import MCPManager, MCPError


class TestMCPTimeoutConfig:
    """测试 MCP 超时配置"""
    
    def test_sse_server_with_timeout(self):
        """测试 SSE 服务器支持超时配置"""
        with patch('src.mcp_manager.MCPServerSse') as mock_sse:
            server = MCPManager.create_sse_server(
                name="test_sse",
                url="http://localhost:8000/sse",
                timeout=30
            )
            
            # 验证超时参数被传递
            mock_sse.assert_called_once()
            call_kwargs = mock_sse.call_args[1]
            assert "timeout" in call_kwargs["params"]
            assert call_kwargs["params"]["timeout"] == 30
    
    def test_sse_server_without_timeout(self):
        """测试 SSE 服务器不配置超时"""
        with patch('src.mcp_manager.MCPServerSse') as mock_sse:
            server = MCPManager.create_sse_server(
                name="test_sse",
                url="http://localhost:8000/sse"
            )
            
            # 验证超时参数不存在
            mock_sse.assert_called_once()
            call_kwargs = mock_sse.call_args[1]
            assert "timeout" not in call_kwargs["params"]
    
    def test_streamablehttp_server_with_timeout(self):
        """测试 StreamableHTTP 服务器支持超时配置"""
        with patch('src.mcp_manager.MCPServerStreamableHttp') as mock_http:
            server = MCPManager.create_streamablehttp_server(
                name="test_http",
                url="http://localhost:8000/mcp",
                timeout=60
            )
            
            # 验证超时参数被传递
            mock_http.assert_called_once()
            call_kwargs = mock_http.call_args[1]
            assert "timeout" in call_kwargs["params"]
            assert call_kwargs["params"]["timeout"] == 60
    
    def test_streamablehttp_server_without_timeout(self):
        """测试 StreamableHTTP 服务器不配置超时"""
        with patch('src.mcp_manager.MCPServerStreamableHttp') as mock_http:
            server = MCPManager.create_streamablehttp_server(
                name="test_http",
                url="http://localhost:8000/mcp"
            )
            
            # 验证超时参数不存在
            mock_http.assert_called_once()
            call_kwargs = mock_http.call_args[1]
            assert "timeout" not in call_kwargs["params"]
    
    def test_mcp_config_with_timeout(self):
        """测试 MCP 配置支持超时字段"""
        config_data = {
            "servers": [
                {
                    "name": "test_sse",
                    "protocol": "sse",
                    "url": "http://localhost:8000/sse",
                    "timeout": 30
                },
                {
                    "name": "test_http",
                    "protocol": "streamablehttp",
                    "url": "http://localhost:8000/mcp",
                    "timeout": 60
                }
            ]
        }
        
        config = MCPConfig(**config_data)
        
        assert len(config.servers) == 2
        assert config.servers[0].timeout == 30
        assert config.servers[1].timeout == 60
    
    def test_mcp_config_without_timeout(self):
        """测试 MCP 配置不包含超时字段（向后兼容）"""
        config_data = {
            "servers": [
                {
                    "name": "test_sse",
                    "protocol": "sse",
                    "url": "http://localhost:8000/sse"
                }
            ]
        }
        
        config = MCPConfig(**config_data)
        
        assert len(config.servers) == 1
        assert config.servers[0].timeout is None
    
    def test_timeout_zero_or_negative(self):
        """测试超时值为零或负数时被忽略"""
        with patch('src.mcp_manager.MCPServerSse') as mock_sse:
            # 测试超时为 0
            server = MCPManager.create_sse_server(
                name="test_sse",
                url="http://localhost:8000/sse",
                timeout=0
            )
            call_kwargs = mock_sse.call_args[1]
            assert "timeout" not in call_kwargs["params"]
            
            # 测试超时为负数
            server = MCPManager.create_sse_server(
                name="test_sse",
                url="http://localhost:8000/sse",
                timeout=-1
            )
            call_kwargs = mock_sse.call_args[1]
            assert "timeout" not in call_kwargs["params"]

