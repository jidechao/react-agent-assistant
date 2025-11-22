"""MCP集成模块

该模块负责加载和管理MCP工具服务器，支持stdio、sse和streamablehttp三种协议。
"""

import logging
from typing import TYPE_CHECKING

import httpx
from agents.mcp import MCPServer, MCPServerSse, MCPServerStdio, MCPServerStreamableHttp

if TYPE_CHECKING:
    from .config import MCPConfig, MCPServerConfig

# 配置日志
logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP相关异常"""
    pass


class MCPManager:
    """MCP管理器
    
    该类负责根据配置加载和管理MCP服务器，支持stdio、sse和streamablehttp三种协议。
    """
    
    @staticmethod
    async def load_mcp_servers(config: "MCPConfig") -> list[MCPServer]:
        """根据配置加载MCP服务器
        
        Args:
            config: MCP配置对象
            
        Returns:
            list[MCPServer]: 成功加载的MCP服务器实例列表
            
        Note:
            如果某个服务器加载失败，会记录错误并跳过该服务器，继续加载其他服务器
        """
        servers: list[MCPServer] = []
        
        for server_config in config.servers:
            try:
                server = MCPManager._create_server(server_config)
                await server.connect()
                servers.append(server)
                logger.info(f"成功加载MCP服务器: {server_config.name} ({server_config.protocol})")
            except Exception as e:
                logger.error(
                    f"加载MCP服务器失败: {server_config.name} ({server_config.protocol}): {e}",
                    exc_info=True
                )
                continue
        
        logger.info(f"共加载 {len(servers)} 个MCP服务器")
        return servers
    
    @staticmethod
    def _create_server(server_config: "MCPServerConfig") -> MCPServer:
        """根据配置创建MCP服务器实例
        
        Args:
            server_config: MCP服务器配置
            
        Returns:
            MCPServer: MCP服务器实例
            
        Raises:
            MCPError: 当协议类型不支持或配置无效时
        """
        protocol = server_config.protocol
        
        if protocol == "stdio":
            return MCPManager.create_stdio_server(
                name=server_config.name,
                command=server_config.command,
                args=server_config.args or [],
                env=server_config.env,
                timeout=server_config.timeout
            )
        elif protocol == "sse":
            return MCPManager.create_sse_server(
                name=server_config.name,
                url=server_config.url,
                timeout=server_config.timeout
            )
        elif protocol == "streamablehttp":
            return MCPManager.create_streamablehttp_server(
                name=server_config.name,
                url=server_config.url,
                timeout=server_config.timeout
            )
        else:
            raise MCPError(f"不支持的协议类型: {protocol}")
    
    @staticmethod
    def create_stdio_server(
        name: str, 
        command: str, 
        args: list[str],
        env: dict[str, str] | None = None,
        timeout: float | int | None = None
    ) -> MCPServerStdio:
        """创建stdio协议的MCP服务器
        
        Args:
            name: 服务器名称
            command: 要执行的命令
            args: 命令参数列表
            env: 环境变量字典（可选）
            timeout: 超时时间（秒），可选。如果未提供，使用默认值60秒
            
        Returns:
            MCPServerStdio: stdio协议的MCP服务器实例
            
        Raises:
            MCPError: 当command为None时
        """
        if not command:
            raise MCPError(f"stdio协议的MCP服务器 {name} 必须提供command参数")
        
        # 设置默认超时时间（如果未指定）
        if timeout is None or timeout <= 0:
            timeout_seconds = 60.0
        else:
            timeout_seconds = float(timeout)
        
        params = {
            "command": command,
            "args": args
        }
        
        if env:
            params["env"] = env
        
        logger.info(f"创建stdio MCP服务器: {name}, timeout={timeout_seconds}s")
        
        return MCPServerStdio(
            params=params,
            name=name,
            cache_tools_list=True,
            client_session_timeout_seconds=timeout_seconds
        )
    
    @staticmethod
    def create_sse_server(name: str, url: str, timeout: float | int | None = None) -> MCPServerSse:
        """创建SSE协议的MCP服务器
        
        Args:
            name: 服务器名称
            url: 服务器URL
            timeout: 超时时间（秒），可选。如果未提供，使用默认值60秒
            
        Returns:
            MCPServerSse: SSE协议的MCP服务器实例
            
        Raises:
            MCPError: 当url为None时
        """
        if not url:
            raise MCPError(f"sse协议的MCP服务器 {name} 必须提供url参数")
        
        # 设置默认超时时间（如果未指定）
        if timeout is None or timeout <= 0:
            timeout_seconds = 60.0
        else:
            timeout_seconds = float(timeout)
        
        params = {
            "url": url,
            "timeout": timeout_seconds
        }
        
        logger.info(f"创建sse MCP服务器: {name}, timeout={timeout_seconds}s")
        
        return MCPServerSse(
            params=params,
            name=name,
            cache_tools_list=True,
            client_session_timeout_seconds=timeout_seconds
        )
    
    @staticmethod
    def create_streamablehttp_server(name: str, url: str, timeout: float | int | None = None) -> MCPServerStreamableHttp:
        """创建StreamableHTTP协议的MCP服务器
        
        根据官方示例代码，使用 httpx_client_factory 来配置自定义超时时间。
        这样可以确保超时设置正确传递到 HTTP 客户端。
        
        Args:
            name: 服务器名称
            url: 服务器URL
            timeout: 超时时间（秒），可选。如果未提供，使用默认值60秒
            
        Returns:
            MCPServerStreamableHttp: StreamableHTTP协议的MCP服务器实例
            
        Raises:
            MCPError: 当url为None时
        """
        if not url:
            raise MCPError(f"streamablehttp协议的MCP服务器 {name} 必须提供url参数")
        
        # 设置默认超时时间（如果未指定）
        if timeout is None or timeout <= 0:
            timeout_seconds = 60.0
        else:
            timeout_seconds = float(timeout)
        
        def create_custom_http_client(
            headers: dict[str, str] | None = None,
            timeout: httpx.Timeout | None = None,
            auth: httpx.Auth | None = None,
        ) -> httpx.AsyncClient:
            """创建自定义HTTP客户端，配置超时时间
            
            根据官方示例，如果timeout参数为None，则使用自定义超时时间。
            这样可以确保超时设置正确传递到HTTP客户端。
            """
            # 如果SDK传入的timeout为None，使用我们配置的超时时间
            if timeout is None:
                timeout = httpx.Timeout(timeout_seconds, read=timeout_seconds * 2)
            return httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                auth=auth
            )
        
        params = {
            "url": url,
            "httpx_client_factory": create_custom_http_client,
            "timeout": timeout_seconds,
            "sse_read_timeout": timeout_seconds * 2
        }
        
        logger.info(f"创建streamablehttp MCP服务器: {name}, timeout={timeout_seconds}s")
        
        return MCPServerStreamableHttp(
            params=params,
            name=name,
            cache_tools_list=True,
            client_session_timeout_seconds=timeout_seconds
        )
