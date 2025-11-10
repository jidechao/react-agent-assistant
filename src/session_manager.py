"""会话管理模块

该模块负责管理对话历史的持久化存储，支持SQLite和Redis两种存储方式。
"""

import logging
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
