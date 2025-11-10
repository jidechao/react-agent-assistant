"""ReACT智能助手主程序入口

该模块是程序的主入口点，负责协调所有模块并启动CLI交互界面。

该模块实现了：
- 全局异常处理
- 优雅的退出逻辑
- MCP服务器连接的正确关闭
- 会话的正确保存和关闭
- 信号处理（Ctrl+C等）
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

from src.config import Config, ConfigError
from src.model_provider import CustomModelProvider
from src.session_manager import SessionManager
from src.mcp_manager import MCPManager
from src.agent_core import ReactAgent
from src.cli import CLI


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


async def cleanup_resources(mcp_servers: list, session):
    """清理资源
    
    该函数负责优雅地关闭所有资源：
    1. 关闭所有MCP服务器连接
    2. 保存并关闭会话
    
    Args:
        mcp_servers: MCP服务器列表
        session: 会话实例
    """
    logger.info("正在清理资源...")
    
    cleanup_errors = []
    
    # 关闭MCP服务器连接
    if mcp_servers:
        logger.info(f"正在关闭 {len(mcp_servers)} 个MCP服务器连接...")
        for server in mcp_servers:
            try:
                # 检查服务器是否有disconnect方法
                if hasattr(server, 'disconnect'):
                    await server.disconnect()
                    logger.debug(f"✓ MCP服务器 {server.name} 已关闭")
                else:
                    logger.debug(f"MCP服务器 {server.name} 不需要显式关闭")
            except Exception as e:
                error_msg = f"关闭MCP服务器 {server.name} 时出错: {e}"
                logger.warning(error_msg)
                cleanup_errors.append(error_msg)
        logger.info("✓ 所有MCP服务器连接已关闭")
    
    # 保存并关闭会话
    if session:
        try:
            logger.info("正在保存会话...")
            # 会话会自动保存，这里只需要确保没有未完成的操作
            # 如果会话有close方法，调用它
            if hasattr(session, 'close'):
                await session.close() if asyncio.iscoroutinefunction(session.close) else session.close()
            logger.info("✓ 会话已保存")
        except Exception as e:
            error_msg = f"保存会话时出错: {e}"
            logger.warning(error_msg)
            cleanup_errors.append(error_msg)
    
    if cleanup_errors:
        logger.warning(f"资源清理过程中出现 {len(cleanup_errors)} 个错误")
    else:
        logger.info("✓ 资源清理完成")


async def main():
    """主函数
    
    该函数协调所有模块的初始化和启动：
    1. 加载配置（环境变量和MCP配置）
    2. 创建模型提供者
    3. 创建会话管理器
    4. 加载MCP服务器
    5. 初始化ReactAgent
    6. 启动CLI交互界面
    7. 优雅地清理资源
    
    该函数实现了全局异常处理和资源清理，确保：
    - 所有配置错误都被正确捕获和报告
    - 所有资源在退出时都被正确清理
    - 用户中断（Ctrl+C）被优雅处理
    - 未预期的错误被记录并报告
    """
    mcp_servers = []
    session = None
    exit_code = 0
    
    try:
        logger.info("=" * 60)
        logger.info("ReACT智能助手启动中...")
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
            print("\n提示：")
            print("  1. 复制 .env.example 文件为 .env")
            print("  2. 在 .env 文件中设置必需的环境变量")
            print("  3. 确保 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL 都已设置")
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
            # 创建空配置
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
            print("请检查您的API配置是否正确。")
            exit_code = 1
            return
        
        # 4. 创建会话管理器
        logger.info("正在创建会话管理器...")
        try:
            storage_type = "redis" if env_config.redis_url else "sqlite"
            session = SessionManager.create_session(
                session_id="react_assistant_session",
                storage_type=storage_type,
                redis_url=env_config.redis_url
            )
            logger.info(f"✓ 会话管理器创建成功 (存储类型: {storage_type})")
        except Exception as e:
            logger.warning(f"创建会话管理器失败: {e}，将尝试使用SQLite")
            try:
                # 降级到SQLite
                session = SessionManager.create_session(
                    session_id="react_assistant_session",
                    storage_type="sqlite",
                    redis_url=None
                )
                logger.info("✓ 会话管理器创建成功 (存储类型: sqlite - 降级)")
            except Exception as e2:
                logger.error(f"✗ 创建SQLite会话管理器也失败: {e2}", exc_info=True)
                print(f"\n错误: 无法创建会话管理器: {e2}")
                exit_code = 1
                return
        
        # 5. 加载MCP服务器
        logger.info("正在加载MCP服务器...")
        try:
            mcp_servers = await MCPManager.load_mcp_servers(mcp_config)
            logger.info(f"✓ MCP服务器加载完成，成功加载 {len(mcp_servers)} 个服务器")
            if len(mcp_config.servers) > 0 and len(mcp_servers) == 0:
                logger.warning("警告: 配置了MCP服务器但没有成功加载任何服务器")
        except Exception as e:
            logger.warning(f"加载MCP服务器时出错: {e}，将继续运行但不使用MCP工具")
            mcp_servers = []
        
        # 6. 初始化ReactAgent
        logger.info("正在初始化ReactAgent...")
        try:
            agent = ReactAgent(
                model_provider=model_provider,
                mcp_servers=mcp_servers,
                session=session
            )
            logger.info("✓ ReactAgent初始化成功")
        except Exception as e:
            logger.error(f"✗ 初始化ReactAgent失败: {e}", exc_info=True)
            print(f"\n错误: 初始化ReactAgent失败: {e}")
            exit_code = 1
            return
        
        # 7. 启动CLI交互界面
        logger.info("正在启动CLI交互界面...")
        logger.info("=" * 60)
        try:
            cli = CLI(agent=agent)
            await cli.run()
        except KeyboardInterrupt:
            # 这个异常应该在CLI内部处理，但以防万一
            logger.info("\n收到中断信号（在CLI外部），正在退出...")
        except Exception as e:
            logger.error(f"CLI运行时出错: {e}", exc_info=True)
            print(f"\n错误: CLI运行时出错: {e}")
            exit_code = 1
        
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，正在退出...")
        print("\n\n程序被用户中断")
    except ConfigError as e:
        # 配置错误已经在上面处理过了
        pass
    except Exception as e:
        logger.error(f"程序运行时出现未预期的错误: {e}", exc_info=True)
        print(f"\n错误: 程序运行时出现错误: {e}")
        print("请检查日志以获取更多详细信息。")
        exit_code = 1
    finally:
        # 优雅地清理资源
        logger.info("\n" + "=" * 60)
        try:
            await cleanup_resources(mcp_servers, session)
        except Exception as e:
            logger.error(f"清理资源时出错: {e}", exc_info=True)
            print(f"\n警告: 清理资源时出现错误: {e}")
            exit_code = 1
        
        logger.info("=" * 60)
        logger.info("ReACT智能助手已退出")
        logger.info("=" * 60)
        
        # 如果有错误，使用非零退出码
        if exit_code != 0:
            sys.exit(exit_code)


def setup_signal_handlers():
    """设置信号处理器以支持优雅退出
    
    该函数设置SIGINT和SIGTERM信号处理器，确保程序能够
    优雅地响应中断信号（如Ctrl+C）。
    
    Note:
        在Windows上，SIGTERM可能不可用，因此只设置SIGINT。
    """
    def signal_handler(signum, frame):
        """信号处理函数"""
        logger.info(f"\n收到信号 {signum}，准备退出...")
        # 抛出KeyboardInterrupt以触发正常的清理流程
        raise KeyboardInterrupt
    
    # 设置SIGINT处理器（Ctrl+C）
    signal.signal(signal.SIGINT, signal_handler)
    
    # 在非Windows系统上设置SIGTERM处理器
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
        logger.debug("信号处理器设置完成 (SIGINT, SIGTERM)")
    else:
        logger.debug("信号处理器设置完成 (SIGINT)")


if __name__ == "__main__":
    import warnings
    
    # 忽略 MCP 清理时的 RuntimeWarning
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 运行主函数
    try:
        # 使用自定义事件循环以更好地处理清理
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            # 清理待处理的任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            # 等待所有任务取消（忽略异常）
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
    except KeyboardInterrupt:
        # 已经在main()中处理
        pass
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)
