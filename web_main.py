"""Web API 服务主程序入口

该模块是 Web API 服务的主入口点，负责启动 WebSocket 服务器。
与 CLI 入口（main.py）完全独立，不影响 CLI 功能。
"""

import asyncio
import logging
import os
import sys
import signal
from pathlib import Path

import websockets

from src.config import Config, ConfigError
from src.model_provider import CustomModelProvider
from src.mcp_manager import MCPManager
from src.agent_core import ReactAgent
from src.web_api import WebSocketHandler


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 禁用 asyncio 的错误日志（MCP 清理时的已知问题）
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


async def cleanup_resources(mcp_servers: list):
    """清理资源
    
    Args:
        mcp_servers: MCP服务器列表
    """
    logger.info("正在清理资源...")
    
    if mcp_servers:
        logger.info(f"正在关闭 {len(mcp_servers)} 个MCP服务器连接...")
        for server in mcp_servers:
            try:
                if hasattr(server, 'disconnect'):
                    await server.disconnect()
                    logger.debug(f"✓ MCP服务器 {server.name} 已关闭")
            except Exception as e:
                logger.warning(f"关闭MCP服务器 {server.name} 时出错: {e}")
        logger.info("✓ 所有MCP服务器连接已关闭")


def create_agent_factory(model_provider: CustomModelProvider, mcp_servers: list):
    """创建 Agent 工厂函数
    
    Args:
        model_provider: 模型提供者实例
        mcp_servers: MCP服务器列表
        
    Returns:
        工厂函数，接受 session 参数并返回 ReactAgent 实例
    """
    def agent_factory(session=None):
        return ReactAgent(
            model_provider=model_provider,
            mcp_servers=mcp_servers,
            session=session
        )
    return agent_factory


async def main():
    """主函数
    
    该函数协调所有模块的初始化和启动：
    1. 加载配置（环境变量和MCP配置）
    2. 创建模型提供者
    3. 加载MCP服务器
    4. 创建 WebSocket 处理器
    5. 启动 WebSocket 服务器
    6. 优雅地清理资源
    """
    mcp_servers = []
    exit_code = 0
    
    try:
        logger.info("=" * 60)
        logger.info("ReACT Web API 服务启动中...")
        logger.info("=" * 60)
        
        # 1. 加载环境变量配置
        logger.info("正在加载环境变量配置...")
        try:
            env_config = Config.load_env_config()
            logger.info("✓ 环境变量配置加载成功")
        except ConfigError as e:
            logger.error(f"✗ 环境变量配置加载失败: {e}")
            print(f"\n错误: {e}")
            print("请检查.env文件并确保所有必需的环境变量已设置。")
            exit_code = 1
            return
        except Exception as e:
            logger.error(f"✗ 加载配置时出现未预期的错误: {e}", exc_info=True)
            print(f"\n错误: 加载配置时出现未预期的错误: {e}")
            exit_code = 1
            return
        
        # 2. 加载MCP配置
        logger.info("正在加载MCP配置...")
        try:
            mcp_config = Config.load_mcp_config()
            logger.info(f"✓ MCP配置加载成功，共 {len(mcp_config.servers)} 个服务器")
        except Exception as e:
            logger.warning(f"加载MCP配置时出错: {e}，将使用空配置继续运行")
            from src.config import MCPConfig
            mcp_config = MCPConfig(servers=[])
        
        # 3. 创建模型提供者
        logger.info("正在创建模型提供者...")
        try:
            model_provider = CustomModelProvider(
                api_key=env_config.api_key,
                base_url=env_config.base_url,
                model_name=env_config.model_name
            )
            logger.info(f"✓ 模型提供者创建成功 (模型: {env_config.model_name})")
        except Exception as e:
            logger.error(f"✗ 创建模型提供者失败: {e}", exc_info=True)
            print(f"\n错误: 创建模型提供者失败: {e}")
            exit_code = 1
            return
        
        # 4. 加载MCP服务器
        logger.info("正在加载MCP服务器...")
        try:
            mcp_servers = await MCPManager.load_mcp_servers(mcp_config)
            logger.info(f"✓ MCP服务器加载完成，成功加载 {len(mcp_servers)} 个服务器")
        except Exception as e:
            logger.warning(f"加载MCP服务器时出错: {e}，将继续运行但不使用MCP工具")
            mcp_servers = []
        
        # 5. 创建 Agent 工厂函数
        agent_factory = create_agent_factory(model_provider, mcp_servers)
        
        # 6. 创建 WebSocket 处理器
        storage_type = "redis" if env_config.redis_url else "sqlite"
        handler = WebSocketHandler(
            agent_factory=agent_factory,
            session_manager_factory=None,  # 不需要工厂函数，直接使用 SessionManager
            storage_type=storage_type,
            redis_url=env_config.redis_url
        )
        
        # 7. 启动 WebSocket 服务器
        port = int(os.getenv("WEB_PORT", "8000"))
        host = os.getenv("WEB_HOST", "localhost")
        
        logger.info("=" * 60)
        logger.info(f"WebSocket 服务器启动在 ws://{host}:{port}")
        logger.info("=" * 60)
        
        # 创建包装函数以确保正确处理连接
        # websockets 14.x 版本：handler 接收 websocket 和可选的 path 参数
        async def connection_handler(websocket, path=None):
            """WebSocket 连接处理器包装函数"""
            # 如果 path 参数未提供，尝试从 websocket 对象获取
            if path is None:
                path = getattr(websocket, 'path', '/')
            
            try:
                await handler.handle_connection(websocket, path)
            except Exception as e:
                # 捕获所有异常，避免影响其他连接
                logger.error(f"WebSocket 连接处理异常: {e}", exc_info=True)
                try:
                    # 检查连接是否仍然打开（websockets 14.x 使用 state 属性）
                    from websockets.protocol import State
                    if websocket.state == State.OPEN:
                        await websocket.close(code=1011, reason=str(e)[:123])
                except Exception:
                    pass  # 忽略关闭时的错误
        
        async with websockets.serve(
            connection_handler, 
            host, 
            port,
            # 添加额外的服务器配置以提高稳定性
            ping_interval=20,  # 每20秒发送一次ping
            ping_timeout=10,   # ping超时时间10秒
            close_timeout=10   # 关闭超时时间10秒
        ) as server:
            logger.info(f"✓ WebSocket 服务器已启动，等待连接...")
            await asyncio.Future()  # 永久运行
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在退出...")
        print("\n\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行时出现未预期的错误: {e}", exc_info=True)
        print(f"\n错误: 程序运行时出现错误: {e}")
        exit_code = 1
    finally:
        # 优雅地清理资源
        logger.info("\n" + "=" * 60)
        try:
            await cleanup_resources(mcp_servers)
        except Exception as e:
            logger.error(f"清理资源时出错: {e}", exc_info=True)
            exit_code = 1
        
        logger.info("=" * 60)
        logger.info("ReACT Web API 服务已退出")
        logger.info("=" * 60)
        
        if exit_code != 0:
            sys.exit(exit_code)


def setup_signal_handlers():
    """设置信号处理器以支持优雅退出"""
    def signal_handler(signum, frame):
        logger.info(f"\n收到信号 {signum}，准备退出...")
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    import warnings
    
    # 忽略 MCP 清理时的 RuntimeWarning
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 运行主函数
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)

