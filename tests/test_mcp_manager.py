"""MCP管理模块测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.mcp_manager import MCPManager, MCPError
from src.config import MCPConfig, MCPServerConfig
from agents.mcp import MCPServerStdio, MCPServerSse, MCPServerStreamableHttp


class TestMCPManager:
    """测试MCP管理器"""
    
    def test_create_stdio_server(self):
        """测试创建stdio协议的MCP服务器"""
        name = "filesystem"
        command = "npx"
        args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        
        server = MCPManager.create_stdio_server(name, command, args)
        
        assert isinstance(server, MCPServerStdio)
        assert server.name == name
    
    def test_create_stdio_server_without_command(self):
        """测试创建stdio服务器但未提供command时抛出异常"""
        name = "filesystem"
        command = None
        args = []
        
        with pytest.raises(MCPError) as exc_info:
            MCPManager.create_stdio_server(name, command, args)
        
        assert "command" in str(exc_info.value).lower()
    
    def test_create_sse_server(self):
        """测试创建SSE协议的MCP服务器"""
        name = "weather"
        url = "http://localhost:8000/sse"
        
        server = MCPManager.create_sse_server(name, url)
        
        assert isinstance(server, MCPServerSse)
        assert server.name == name
    
    def test_create_sse_server_without_url(self):
        """测试创建SSE服务器但未提供url时抛出异常"""
        name = "weather"
        url = None
        
        with pytest.raises(MCPError) as exc_info:
            MCPManager.create_sse_server(name, url)
        
        assert "url" in str(exc_info.value).lower()
    
    def test_create_streamablehttp_server(self):
        """测试创建StreamableHTTP协议的MCP服务器"""
        name = "calculator"
        url = "http://localhost:8000/mcp"
        
        server = MCPManager.create_streamablehttp_server(name, url)
        
        assert isinstance(server, MCPServerStreamableHttp)
        assert server.name == name
    
    def test_create_streamablehttp_server_without_url(self):
        """测试创建StreamableHTTP服务器但未提供url时抛出异常"""
        name = "calculator"
        url = None
        
        with pytest.raises(MCPError) as exc_info:
            MCPManager.create_streamablehttp_server(name, url)
        
        assert "url" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_empty_config(self):
        """测试加载空的MCP配置"""
        config = MCPConfig(servers=[])
        
        servers = await MCPManager.load_mcp_servers(config)
        
        assert servers == []
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_stdio(self):
        """测试加载stdio协议的MCP服务器"""
        server_config = MCPServerConfig(
            name="filesystem",
            protocol="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        config = MCPConfig(servers=[server_config])
        
        with patch.object(MCPServerStdio, 'connect', new_callable=AsyncMock) as mock_connect:
            servers = await MCPManager.load_mcp_servers(config)
            
            assert len(servers) == 1
            assert isinstance(servers[0], MCPServerStdio)
            assert servers[0].name == "filesystem"
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_sse(self):
        """测试加载SSE协议的MCP服务器"""
        server_config = MCPServerConfig(
            name="weather",
            protocol="sse",
            url="http://localhost:8000/sse"
        )
        config = MCPConfig(servers=[server_config])
        
        with patch.object(MCPServerSse, 'connect', new_callable=AsyncMock) as mock_connect:
            servers = await MCPManager.load_mcp_servers(config)
            
            assert len(servers) == 1
            assert isinstance(servers[0], MCPServerSse)
            assert servers[0].name == "weather"
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_streamablehttp(self):
        """测试加载StreamableHTTP协议的MCP服务器"""
        server_config = MCPServerConfig(
            name="calculator",
            protocol="streamablehttp",
            url="http://localhost:8000/mcp"
        )
        config = MCPConfig(servers=[server_config])
        
        with patch.object(MCPServerStreamableHttp, 'connect', new_callable=AsyncMock) as mock_connect:
            servers = await MCPManager.load_mcp_servers(config)
            
            assert len(servers) == 1
            assert isinstance(servers[0], MCPServerStreamableHttp)
            assert servers[0].name == "calculator"
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_multiple(self):
        """测试加载多个MCP服务器"""
        server_configs = [
            MCPServerConfig(
                name="filesystem",
                protocol="stdio",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            ),
            MCPServerConfig(
                name="weather",
                protocol="sse",
                url="http://localhost:8000/sse"
            )
        ]
        config = MCPConfig(servers=server_configs)
        
        with patch.object(MCPServerStdio, 'connect', new_callable=AsyncMock), \
             patch.object(MCPServerSse, 'connect', new_callable=AsyncMock):
            servers = await MCPManager.load_mcp_servers(config)
            
            assert len(servers) == 2
            assert isinstance(servers[0], MCPServerStdio)
            assert isinstance(servers[1], MCPServerSse)
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_connection_failure(self):
        """测试MCP服务器连接失败时跳过该服务器"""
        server_config = MCPServerConfig(
            name="filesystem",
            protocol="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        )
        config = MCPConfig(servers=[server_config])
        
        with patch.object(MCPServerStdio, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            servers = await MCPManager.load_mcp_servers(config)
            
            # 连接失败的服务器应该被跳过
            assert len(servers) == 0
    
    @pytest.mark.asyncio
    async def test_load_mcp_servers_partial_failure(self):
        """测试部分MCP服务器连接失败"""
        server_configs = [
            MCPServerConfig(
                name="filesystem",
                protocol="stdio",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            ),
            MCPServerConfig(
                name="weather",
                protocol="sse",
                url="http://localhost:8000/sse"
            )
        ]
        config = MCPConfig(servers=server_configs)
        
        # 第一个服务器连接失败，第二个成功
        with patch.object(MCPServerStdio, 'connect', new_callable=AsyncMock) as mock_stdio_connect, \
             patch.object(MCPServerSse, 'connect', new_callable=AsyncMock) as mock_sse_connect:
            mock_stdio_connect.side_effect = Exception("Connection failed")
            
            servers = await MCPManager.load_mcp_servers(config)
            
            # 只有成功连接的服务器被加载
            assert len(servers) == 1
            assert isinstance(servers[0], MCPServerSse)
