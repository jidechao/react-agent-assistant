"""会话管理模块

该模块负责管理对话历史的持久化存储，支持SQLite和Redis两种存储方式。
"""

import logging
import sqlite3
from pathlib import Path
from typing import Literal

from agents import Session, SQLiteSession

# 配置日志
logger = logging.getLogger(__name__)


class SessionError(Exception):
    """会话管理相关异常"""
    pass


class SessionManager:
    """会话管理器
    
    该类负责创建和管理会话实例，支持SQLite和Redis两种存储方式。
    当Redis连接失败时，会自动降级到SQLite存储。
    """
    
    def __init__(self, session: Session):
        """初始化会话管理器
        
        Args:
            session: Session实例
        """
        self.session = session
    
    @staticmethod
    def create_session(
        session_id: str,
        storage_type: Literal["sqlite", "redis"] = "sqlite",
        redis_url: str | None = None
    ) -> Session:
        """创建会话实例
        
        Args:
            session_id: 会话唯一标识符
            storage_type: 存储类型，"sqlite"或"redis"，默认为"sqlite"
            redis_url: Redis连接URL（当storage_type为"redis"时必需）
            
        Returns:
            Session: Session实例（SQLiteSession或RedisSession）
            
        Raises:
            ValueError: 当storage_type为"redis"但redis_url未提供时
            SessionError: 当会话创建失败时
        """
        try:
            if storage_type == "sqlite":
                return SessionManager._create_sqlite_session(session_id)
            elif storage_type == "redis":
                return SessionManager._create_redis_session(session_id, redis_url)
            else:
                raise ValueError(f"不支持的存储类型: {storage_type}")
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise SessionError(f"创建会话失败: {e}") from e
    
    async def get_items(self) -> list:
        """获取会话中的所有项目
        
        Returns:
            list: 会话历史项目列表
        """
        try:
            return await self.session.get_items()
        except Exception as e:
            logger.error(f"获取会话项目失败: {e}")
            return []
    
    async def add_items(self, items: list) -> None:
        """向会话中添加项目
        
        Args:
            items: 要添加的项目列表
        """
        try:
            await self.session.add_items(items)
            logger.debug(f"成功添加 {len(items)} 个项目到会话")
        except Exception as e:
            logger.error(f"添加会话项目失败: {e}")
            raise SessionError(f"添加会话项目失败: {e}") from e
    
    async def clear(self) -> None:
        """清空会话历史
        """
        try:
            await self.session.clear()
            logger.info("会话历史已清空")
        except Exception as e:
            logger.error(f"清空会话失败: {e}")
            raise SessionError(f"清空会话失败: {e}") from e
    
    async def get_history_length(self) -> int:
        """获取会话历史长度
        
        Returns:
            int: 会话历史中的项目数量
        """
        try:
            items = await self.get_items()
            return len(items)
        except Exception as e:
            logger.error(f"获取会话历史长度失败: {e}")
            return 0
    
    @staticmethod
    def _create_sqlite_session(session_id: str) -> SQLiteSession:
        """创建SQLite会话
        
        Args:
            session_id: 会话唯一标识符
            
        Returns:
            SQLiteSession: SQLite会话实例
        """
        logger.info(f"创建SQLite会话: {session_id}")
        return SQLiteSession(session_id=session_id)
    
    @staticmethod
    def _create_redis_session(session_id: str, redis_url: str | None) -> Session:
        """创建Redis会话，失败时降级到SQLite
        
        Args:
            session_id: 会话唯一标识符
            redis_url: Redis连接URL
            
        Returns:
            Session: Redis会话实例，如果连接失败则返回SQLite会话实例
            
        Raises:
            ValueError: 当redis_url未提供时
        """
        if not redis_url:
            raise ValueError("使用Redis存储时必须提供redis_url参数")
        
        try:
            # 尝试导入RedisSession
            from agents.extensions.memory import RedisSession
            
            logger.info(f"尝试创建Redis会话: {session_id}")
            
            # 使用from_url方法创建Redis会话
            session = RedisSession.from_url(
                session_id=session_id,
                url=redis_url
            )
            
            logger.info(f"成功创建Redis会话: {session_id}")
            return session
            
        except ImportError as e:
            logger.warning(f"RedisSession不可用，降级到SQLite: {e}")
            return SessionManager._create_sqlite_session(session_id)
        except Exception as e:
            logger.warning(f"Redis连接失败，降级到SQLite: {e}")
            return SessionManager._create_sqlite_session(session_id)
    
    @staticmethod
    async def list_sessions(
        storage_type: Literal["sqlite", "redis"] = "sqlite",
        redis_url: str | None = None
    ) -> list[str]:
        """列出所有会话ID
        
        Args:
            storage_type: 存储类型，"sqlite"或"redis"，默认为"sqlite"
            redis_url: Redis连接URL（当storage_type为"redis"时必需）
            
        Returns:
            list[str]: 会话ID列表
            
        Raises:
            SessionError: 当查询会话列表失败时
        """
        try:
            if storage_type == "sqlite":
                return await SessionManager._list_sqlite_sessions()
            elif storage_type == "redis":
                return await SessionManager._list_redis_sessions(redis_url)
            else:
                raise ValueError(f"不支持的存储类型: {storage_type}")
        except Exception as e:
            logger.error(f"查询会话列表失败: {e}")
            raise SessionError(f"查询会话列表失败: {e}") from e
    
    @staticmethod
    async def delete_session(
        session_id: str,
        storage_type: Literal["sqlite", "redis"] = "sqlite",
        redis_url: str | None = None
    ) -> None:
        """删除指定会话及其所有聊天记录
        
        Args:
            session_id: 要删除的会话ID
            storage_type: 存储类型，"sqlite"或"redis"，默认为"sqlite"
            redis_url: Redis连接URL（当storage_type为"redis"时必需）
            
        Raises:
            SessionError: 当删除会话失败时
        """
        try:
            # 创建临时会话来访问删除功能
            session = SessionManager.create_session(
                session_id=session_id,
                storage_type=storage_type,
                redis_url=redis_url
            )
            
            # 清空会话（删除所有记录）
            # 注意：Session 接口使用 clear_session() 方法，而不是 clear()
            if hasattr(session, 'clear_session'):
                await session.clear_session()
            elif hasattr(session, 'clear'):
                # 兼容旧版本或自定义实现
                await session.clear()
            else:
                # 如果都没有，尝试直接删除 Redis 键（仅 Redis）
                if storage_type == "redis" and redis_url:
                    await SessionManager._delete_redis_session_keys(session_id, redis_url)
                else:
                    raise SessionError(f"无法清空会话: {session_id}，会话类型不支持清空操作")
            
            logger.info(f"成功删除会话: {session_id}")
            
        except Exception as e:
            logger.error(f"删除会话失败: {session_id}, 错误: {e}")
            raise SessionError(f"删除会话失败: {session_id}, 错误: {e}") from e
    
    @staticmethod
    async def _list_sqlite_sessions() -> list[str]:
        """列出所有SQLite会话ID
        
        Returns:
            list[str]: 会话ID列表
        """
        try:
            # SQLiteSession 默认使用 ~/.agents/sessions.db
            # 我们需要查询数据库获取所有不同的 session_id
            db_path = Path.home() / ".agents" / "sessions.db"
            
            if not db_path.exists():
                logger.debug("SQLite数据库不存在，返回空列表")
                return []
            
            sessions = []
            conn = sqlite3.connect(str(db_path))
            try:
                cursor = conn.cursor()
                # 查询所有不同的 session_id
                # 假设表名为 sessions 或类似的名称
                # 需要根据实际的 agents 库实现调整
                cursor.execute("SELECT DISTINCT session_id FROM sessions")
                rows = cursor.fetchall()
                sessions = [row[0] for row in rows if row[0]]
            finally:
                conn.close()
            
            logger.debug(f"找到 {len(sessions)} 个SQLite会话")
            return sessions
            
        except Exception as e:
            logger.warning(f"查询SQLite会话列表失败: {e}，返回空列表")
            return []
    
    @staticmethod
    async def _list_redis_sessions(redis_url: str | None) -> list[str]:
        """列出所有Redis会话ID
        
        Args:
            redis_url: Redis连接URL
            
        Returns:
            list[str]: 会话ID列表
        """
        try:
            if not redis_url:
                logger.warning("Redis URL未提供，返回空列表")
                return []
            
            # 尝试导入Redis客户端
            try:
                import redis.asyncio as aioredis
            except ImportError:
                import redis
                aioredis = None
            
            if aioredis:
                # 使用异步Redis客户端
                client = await aioredis.from_url(redis_url)
                try:
                    # RedisSession 通常使用键模式 "agents:session:{session_id}:*"
                    # 获取所有匹配的键
                    keys = await client.keys("agents:session:*")
                    # 从键中提取 session_id
                    sessions = set()
                    for key in keys:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        # 假设键格式为 "agents:session:{session_id}:..."
                        parts = key_str.split(":")
                        if len(parts) >= 3:
                            sessions.add(parts[2])
                    sessions_list = list(sessions)
                    await client.aclose()
                    logger.debug(f"找到 {len(sessions_list)} 个Redis会话")
                    return sessions_list
                except Exception as e:
                    await client.aclose()
                    raise e
            else:
                # 使用同步Redis客户端
                import redis
                client = redis.from_url(redis_url)
                try:
                    keys = client.keys("agents:session:*")
                    sessions = set()
                    for key in keys:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        parts = key_str.split(":")
                        if len(parts) >= 3:
                            sessions.add(parts[2])
                    sessions_list = list(sessions)
                    logger.debug(f"找到 {len(sessions_list)} 个Redis会话")
                    return sessions_list
                finally:
                    client.close()
                    
        except Exception as e:
            logger.warning(f"查询Redis会话列表失败: {e}，返回空列表")
            return []
    
    @staticmethod
    async def _delete_redis_session_keys(session_id: str, redis_url: str) -> None:
        """删除 Redis 会话的所有键
        
        Args:
            session_id: 会话ID
            redis_url: Redis连接URL
        """
        try:
            # 尝试导入Redis客户端
            try:
                import redis.asyncio as aioredis
            except ImportError:
                import redis
                aioredis = None
            
            if aioredis:
                # 使用异步Redis客户端
                client = await aioredis.from_url(redis_url)
                try:
                    # 删除所有匹配的键
                    keys = await client.keys(f"agents:session:{session_id}:*")
                    if keys:
                        await client.delete(*keys)
                        logger.debug(f"删除了 {len(keys)} 个Redis键")
                    await client.aclose()
                except Exception as e:
                    await client.aclose()
                    raise e
            else:
                # 使用同步Redis客户端
                import redis
                client = redis.from_url(redis_url)
                try:
                    keys = client.keys(f"agents:session:{session_id}:*")
                    if keys:
                        client.delete(*keys)
                        logger.debug(f"删除了 {len(keys)} 个Redis键")
                finally:
                    client.close()
                    
        except Exception as e:
            logger.error(f"删除Redis会话键失败: {e}", exc_info=True)
            raise
