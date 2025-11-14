"""MCP集成模块

该模块负责加载和管理MCP工具服务器，支持stdio、sse和streamablehttp三种协议。
"""

import logging
from typing import TYPE_CHECKING

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
                
                # 尝试连接服务器
                await server.connect()
                
                servers.append(server)
                logger.info(f"成功加载MCP服务器: {server_config.name} ({server_config.protocol})")
                
            except Exception as e:
                logger.error(
                    f"加载MCP服务器失败: {server_config.name} ({server_config.protocol}): {e}"
                )
                # 继续加载其他服务器
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
                env=server_config.env
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
        env: dict[str, str] | None = None
    ) -> MCPServerStdio:
        """创建stdio协议的MCP服务器
        
        Args:
            name: 服务器名称
            command: 要执行的命令
            args: 命令参数列表
            env: 环境变量字典（可选）
            
        Returns:
            MCPServerStdio: stdio协议的MCP服务器实例
            
        Raises:
            MCPError: 当command为None时
        """
        if not command:
            raise MCPError(f"stdio协议的MCP服务器 {name} 必须提供command参数")
        
        logger.debug(f"创建stdio MCP服务器: {name}, command={command}, args={args}, env={env}")
        
        params = {
            "command": command,
            "args": args
        }
        
        # 如果提供了环境变量，添加到params中
        if env:
            params["env"] = env
        
        return MCPServerStdio(
            params=params,
            name=name,
            cache_tools_list=True  # 缓存工具列表以提高性能
        )
    
    @staticmethod
    def create_sse_server(name: str, url: str, timeout: int | None = None) -> MCPServerSse:
        """创建SSE协议的MCP服务器
        
        Args:
            name: 服务器名称
            url: 服务器URL
            timeout: 超时时间（秒），可选
            
        Returns:
            MCPServerSse: SSE协议的MCP服务器实例
            
        Raises:
            MCPError: 当url为None时
        """
        if not url:
            raise MCPError(f"sse协议的MCP服务器 {name} 必须提供url参数")
        
        params = {"url": url}
        if timeout is not None and timeout > 0:
            params["timeout"] = timeout
            logger.debug(f"创建sse MCP服务器: {name}, url={url}, timeout={timeout}s")
        else:
            logger.debug(f"创建sse MCP服务器: {name}, url={url}")
        
        return MCPServerSse(
            params=params,
            name=name,
            cache_tools_list=True  # 缓存工具列表以提高性能
        )
    
    @staticmethod
    def create_streamablehttp_server(name: str, url: str, timeout: int | None = None) -> MCPServerStreamableHttp:
        """创建StreamableHTTP协议的MCP服务器
        
        Args:
            name: 服务器名称
            url: 服务器URL
            timeout: 超时时间（秒），可选
            
        Returns:
            MCPServerStreamableHttp: StreamableHTTP协议的MCP服务器实例
            
        Raises:
            MCPError: 当url为None时
        """
        if not url:
            raise MCPError(f"streamablehttp协议的MCP服务器 {name} 必须提供url参数")
        
        params = {"url": url}
        if timeout is not None and timeout > 0:
            params["timeout"] = timeout
            logger.debug(f"创建streamablehttp MCP服务器: {name}, url={url}, timeout={timeout}s")
        else:
            logger.debug(f"创建streamablehttp MCP服务器: {name}, url={url}")
        
        return MCPServerStreamableHttp(
            params=params,
            name=name,
            cache_tools_list=True  # 缓存工具列表以提高性能
        )
